//! The noise-pilot night driver (docs/m0/prereg/X4-noise-pilot.md sections 3, 6, 10, 11; X4 pilot
//! track, 2026-10-23). It wires the session engine (`session::run_session`: randomised ABBA/BAAB from
//! the pinned seed, the load gate, the blind void rules) to real runs (`sandbox::run_once` through the
//! Job Object and the out-of-process bracket, in observe mode) and to the read-only hygiene sensors.
//!
//! Two modes, chosen by the configuration's `grade` and the command line together:
//! - **PILOT** (`pilot-night --pilot`): refuses unless the configuration is the record's (pilotcfg:
//!   every fixed value, the freeze commit, the signature tag's name and the rule's seed), every
//!   pre-start item holds (night refusal), and the clock is inside the quiet window. Records go to
//!   `data_dir`, stamped `PILOT`. Nobody but Pierce (or the job wrapper he approves) starts it, and
//!   only under the signed record. `--max-sessions` and `--plants` are refused with it (main.rs).
//! - **DRY-RUN** (`pilot-night --dry-run`): runs a whole night's schedule on a virtual Pacific clock
//!   (each run advances it by its planned t_run, its planned cool-down and the real time the checks,
//!   the launch and the teardown took; each session by the setup time), on the `dry_mb_tiny`
//!   workload, with real sensors and relaxed dry thresholds; then, with `--plants`, plants a trigger
//!   for every section 10 sensor and checks that its tier fires. Every record line is stamped
//!   `DRY-RUN`; the output goes under `<scratch>\dry\`, never to `data_dir`. Dry runs are shorter
//!   than 1 s, so the bracket is ineligible on them (`bracket_too_short`); the dry driver records that
//!   and counts the run, and treats every other integrity failure as the pilot would.
//!
//! Revision 4 (review 2026-10-23), in order of a run: the cool-down waits in `before_run`, before the
//! checks; `session_void` takes a full snapshot (GPU and NVMe at every check) merged with what the
//! 250-ms process poller saw since the session's baseline; the gate settles the start state first and
//! reads the 2-s load last (GetSystemTimes; the run core's LPs for a one-LP run type), so nothing
//! waits between the gate and the launch; the run is bracketed by a PDH collect (per-LP load and
//! effective clock over [launch, exit]); after the block, background CPU is judged over the planned
//! block time and the other CPU on the machine (system busy - job - this process) is recorded. Each
//! session starts with the profile check (PILOT), a real `session_setup_s` settle and a fresh
//! baseline; progress.txt gets a synced `started` line before the first run and the manifest is
//! rewritten after every session.
//!
//! The e-processes the engine computes are descriptive placeholders here (sigma 2%, the planned run
//! time as the reference median): the pilot has no gate (section 8) and its estimators are computed
//! offline from `runs.jsonl` (section 4). Wealth at discards and voids is logged as the engine does.

#![cfg(windows)]

use crate::eprocess::Arm;
use crate::hygiene::{self, NightItem, ProcSample, SessionSense};
use crate::observe::{self, Ceilings};
use crate::pilotcfg::{self, Grade, PilotConfig, PlannedSession, RunType};
use crate::profile::StateReader;
use crate::proto::RunVerdict;
use crate::runenv::{self, EnvBlock};
use crate::sandbox::{self, JobLimits, RunSpec};
use crate::scheduler::GateReading;
use crate::sensors_win::{self as sw, Sensors};
use crate::session::{self, GateSensor, RunResult, RunSource, SessionConfig, SessionEnd, SessionResult};
use crate::sha256;
use std::cell::{Cell, RefCell};
use std::collections::HashSet;
use std::fs::File;
use std::io::Write;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

/// The process poller's period (revision 4) [target]: a listed process living less than one period
/// between two checks can be missed (record section 10).
pub const POLL_MS: u64 = 250;

// ------------------------------------------------------------------------------------- helpers

pub fn jstr(s: &str) -> String {
    let mut o = String::with_capacity(s.len() + 2);
    o.push('"');
    for c in s.chars() {
        match c {
            '"' => o.push_str("\\\""),
            '\\' => o.push_str("\\\\"),
            '\n' => o.push_str("\\n"),
            '\r' => o.push_str("\\r"),
            '\t' => o.push_str("\\t"),
            c if (c as u32) < 0x20 => o.push_str(&format!("\\u{:04x}", c as u32)),
            c => o.push(c),
        }
    }
    o.push('"');
    o
}
fn jf(v: Option<f64>) -> String {
    match v {
        Some(x) if x.is_finite() => format!("{:.4}", x),
        _ => "null".into(),
    }
}
fn jpairs(v: &[(String, f64)]) -> String {
    let parts: Vec<String> = v.iter().map(|(k, x)| format!("{}:{}", jstr(k), jf(Some(*x)))).collect();
    format!("{{{}}}", parts.join(","))
}
pub fn file_sha256(path: &str) -> Result<String, String> {
    let b = std::fs::read(path).map_err(|e| format!("read {}: {}", path, e))?;
    Ok(sha256::hex(&sha256::digest(&b)))
}
pub fn utc_now() -> f64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs_f64()).unwrap_or(0.0)
}
fn stamp(utc: f64) -> String {
    let t = utc as i64;
    let (y, m, d) = pilotcfg::civil_from_days(t.div_euclid(86400));
    let s = t.rem_euclid(86400);
    format!("{:04}{:02}{:02}T{:02}{:02}{:02}Z", y, m, d, s / 3600, s % 3600 / 60, s % 60)
}
fn jdropped(v: &[(String, u32)]) -> String {
    let parts: Vec<String> = v.iter().map(|(k, s)| format!("{}:\"{:#x}\"", jstr(k), s)).collect();
    format!("{{{}}}", parts.join(","))
}
fn mask_lps(m: u64) -> Vec<u32> {
    (0..64u32).filter(|b| m >> b & 1 == 1).collect()
}

/// Wall time: real, or a virtual Pacific night (dry run).
pub struct Clock {
    virt: Option<Cell<f64>>,
}
impl Clock {
    pub fn real() -> Self {
        Clock { virt: None }
    }
    pub fn virtual_at(t: f64) -> Self {
        Clock { virt: Some(Cell::new(t)) }
    }
    pub fn now(&self) -> f64 {
        match &self.virt {
            Some(c) => c.get(),
            None => utc_now(),
        }
    }
    pub fn is_virtual(&self) -> bool {
        self.virt.is_some()
    }
    /// Time passing (a virtual clock only; real time passes by itself).
    pub fn pass(&self, s: f64) {
        if let Some(c) = &self.virt {
            c.set(c.get() + s);
        }
    }
    /// The real time a step took, carried onto a virtual clock (revision 4: a dry night's schedule
    /// then shows the checks' real cost, not only the plan).
    pub fn pass_real(&self, since: Instant) {
        self.pass(since.elapsed().as_secs_f64());
    }
    pub fn set(&self, t: f64) {
        if let Some(c) = &self.virt {
            c.set(t);
        }
    }
    /// A deliberate wait: sleeps on a real clock, advances a virtual one.
    pub fn wait(&self, s: f64) {
        match &self.virt {
            Some(c) => c.set(c.get() + s),
            None if s > 0.0 => std::thread::sleep(Duration::from_secs_f64(s)),
            None => {}
        }
    }
}

struct Out {
    dir: String,
    runs: File,
    blocks: File,
    voids: File,
    sensors: File,
    sessions: File,
    plants: File,
}
impl Out {
    fn open(dir: &str) -> Result<Out, String> {
        std::fs::create_dir_all(dir).map_err(|e| format!("create {}: {}", dir, e))?;
        let f = |n: &str| File::create(format!("{}\\{}", dir, n)).map_err(|e| format!("create {}\\{}: {}", dir, n, e));
        Ok(Out { dir: dir.to_string(), runs: f("runs.jsonl")?, blocks: f("blocks.jsonl")?, voids: f("voids.log")?, sensors: f("sensors.jsonl")?, sessions: f("sessions.jsonl")?, plants: f("plants.jsonl")? })
    }
}
fn wl(f: &mut File, line: &str) {
    let _ = writeln!(f, "{}", line);
    let _ = f.flush();
}

// ---------------------------------------------------------------------------- process poller

/// A background thread (on the orchestrator's reserved LP: it inherits the pinned mask) that takes a
/// filtered process snapshot every `POLL_MS` and keeps the union of every listed process it saw, with
/// its last cycle count and the poll generation that last saw it (revision 4, review 2026-10-23).
struct Poller {
    seen: Arc<Mutex<Vec<(ProcSample, u64)>>>,
    gen: Arc<AtomicU64>,
    stop: Arc<AtomicBool>,
    handle: Option<std::thread::JoinHandle<()>>,
}
impl Poller {
    fn start(filter: Arc<dyn Fn(&str) -> bool + Send + Sync>) -> Poller {
        let seen: Arc<Mutex<Vec<(ProcSample, u64)>>> = Arc::new(Mutex::new(Vec::new()));
        let gen = Arc::new(AtomicU64::new(0));
        let stop = Arc::new(AtomicBool::new(false));
        let (s2, g2, st2) = (seen.clone(), gen.clone(), stop.clone());
        let handle = std::thread::spawn(move || {
            while !st2.load(Ordering::Relaxed) {
                let snap = sw::processes_where(|i| filter(i));
                {
                    let mut v = s2.lock().unwrap();
                    let g = g2.fetch_add(1, Ordering::SeqCst) + 1;
                    merge_gen(&mut v, &snap, g);
                }
                std::thread::sleep(Duration::from_millis(POLL_MS));
            }
        });
        Poller { seen, gen, stop, handle: Some(handle) }
    }
    /// A new session: the union restarts from the baseline.
    fn reset(&self, base: &[ProcSample]) {
        let mut v = self.seen.lock().unwrap();
        let g = self.gen.load(Ordering::SeqCst);
        v.clear();
        merge_gen(&mut v, base, g);
    }
    fn mark(&self) -> u64 {
        self.gen.load(Ordering::SeqCst)
    }
    /// Every process seen by a poll after generation `g` (exited ones included), merged with `now`.
    fn seen_after(&self, g: u64, now: &[ProcSample]) -> Vec<ProcSample> {
        let mut out: Vec<ProcSample> = self.seen.lock().unwrap().iter().filter(|(_, lg)| *lg > g).map(|(p, _)| p.clone()).collect();
        hygiene::merge_seen(&mut out, now);
        out
    }
    /// Every process seen since the session baseline, merged with `now`.
    fn union(&self, now: &[ProcSample]) -> Vec<ProcSample> {
        let mut out: Vec<ProcSample> = self.seen.lock().unwrap().iter().map(|(p, _)| p.clone()).collect();
        hygiene::merge_seen(&mut out, now);
        out
    }
}
impl Drop for Poller {
    fn drop(&mut self) {
        self.stop.store(true, Ordering::Relaxed);
        if let Some(h) = self.handle.take() {
            let _ = h.join();
        }
    }
}
fn merge_gen(v: &mut Vec<(ProcSample, u64)>, now: &[ProcSample], g: u64) {
    for p in now {
        match v.iter_mut().find(|(s, _)| s.same(p)) {
            Some((s, lg)) => {
                if let Some(c) = p.cycles {
                    s.cycles = Some(s.cycles.map_or(c, |o| o.max(c)));
                }
                *lg = g;
            }
            None => v.push((p.clone(), g)),
        }
    }
}

/// The images the process sensors read: excluded, started-only, background and Mithril binaries.
fn proc_filter(cfg: &PilotConfig) -> Arc<dyn Fn(&str) -> bool + Send + Sync> {
    let set: HashSet<String> = cfg.excluded_images.iter().chain(cfg.excluded_started_images.iter()).chain(cfg.bg_images.iter()).map(|s| hygiene::norm_image(s)).collect();
    Arc::new(move |i: &str| set.contains(i) || i.starts_with("x4svc") || i.starts_with("x4harness"))
}

/// A dry-run plant: one trigger per section 10 sensor (DRY-RUN only).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PlantKind {
    None,
    Excluded,
    Started,
    Mithril,
    Load,
    CoreLoad,
    Writes,
    Nvme,
    Defender,
    Input,
    Session,
    Gpu,
    Scheme,
    Cut,
    Integrity,
}
impl PlantKind {
    pub fn label(self) -> &'static str {
        match self {
            PlantKind::None => "control (no plant)",
            PlantKind::Excluded => "excluded process starts and exits between checks (real: x4plant_gems.exe, 1 s)",
            PlantKind::Started => "started-only image starts (real: x4plant_shell.exe)",
            PlantKind::Mithril => "another Mithril measurement process (real: x4harness_foreign.exe)",
            PlantKind::Load => "CPU load before a run (real: 3 busy threads)",
            PlantKind::CoreLoad => "the run core busy before a run (real: 1 busy thread on the run LP)",
            PlantKind::Writes => "disk writes before a run (real: 256 MiB to the dry scratch)",
            PlantKind::Nvme => "NVMe temperature at a block start (real sensor, dry threshold below it)",
            PlantKind::Defender => "Defender CPU over a block (injected reading)",
            PlantKind::Input => "interactive input (injected reading)",
            PlantKind::Session => "a new RDP session (injected reading)",
            PlantKind::Gpu => "GPU utilisation (injected reading)",
            PlantKind::Scheme => "power-scheme change (injected reading)",
            PlantKind::Cut => "session cut by 07:00 PT (virtual clock)",
            PlantKind::Integrity => "integrity failure: wrong golden (real run)",
        }
    }
}

struct PlantState {
    kind: PlantKind,
    exe: String,
    dir: String,
    checks: usize,
    reads: usize,
    note: String,
    affinity: u64,
}

/// Everything a night shares.
pub struct Ctx {
    pub night: String,
    pub grade: Grade,
    pub clock: Clock,
    pub sensors: Sensors,
    pub rate: u64,
    pub own_pid: u32,
    /// (window start, last session end, window end), UTC seconds.
    pub window: (f64, f64, f64),
    /// The physical cores (LP masks), for the run core rule.
    pub cores: Vec<u64>,
    out: RefCell<Out>,
    seq: Cell<u64>,
    salt: Cell<u64>,
    plant: RefCell<PlantState>,
    poller: Poller,
    /// When the last gate's load window ended (the gap to the launch is recorded per run).
    last_load_end: Cell<Option<Instant>>,
    /// Whether the last check spawned the GPU query (recorded with the next load sample).
    gpu_query_before_load: Cell<bool>,
    /// The job CPU (100 ns) of every run so far (for the other-CPU record per block).
    job_cpu_100ns: Cell<u64>,
    /// The previous run's (NVMe-bound, delta_o ns), across sessions: the e2e cool-down.
    prev_run: Cell<Option<(bool, u64)>>,
}

impl Ctx {
    fn next_salt(&self) -> u64 {
        // orchestrator-chosen, unpredictable to the workload (a SplitMix step over QPC-derived state)
        let mut z = self.salt.get().wrapping_add(0x9e37_79b9_7f4a_7c15) ^ (utc_now().to_bits().rotate_left(17));
        z = (z ^ (z >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
        z ^= z >> 31;
        self.salt.set(z);
        z | 1
    }
    fn void_line(&self, kind: &str, session: &str, text: &str) {
        let t = self.clock.now();
        wl(&mut self.out.borrow_mut().voids, &format!("{} {} {} [{}] session={} {}", self.grade.label(), stamp(t), pilotcfg::pt_string(t as i64), kind, session, text));
    }
    /// The core (LP mask) holding a one-LP run type's LP, for the run core rule; 0 = not applicable.
    fn run_core(&self, rt: &RunType) -> u64 {
        if rt.affinity.count_ones() != 1 {
            return 0;
        }
        self.cores.iter().copied().find(|c| c & rt.affinity != 0).unwrap_or(rt.affinity)
    }
}

/// Start a plant (dry only). `detach`: the plant re-launches itself and its launcher exits, so its
/// parent is not this driver (whose own children the process sensors exempt).
fn spawn_plant(exe: &str, args: &[String], affinity: u64, detach: bool) -> Result<std::process::Child, String> {
    use std::os::windows::process::CommandExt;
    // a plant inherits the orchestrator's one-LP mask unless the dry configuration names a wider one
    // (a 3-thread load plant on one LP adds only one LP of load) [M, dry run 2026-10-23]
    let mut c = std::process::Command::new(exe);
    c.args(args).env("CUDA_VISIBLE_DEVICES", "-1").creation_flags(0x0800_0000);
    if affinity != 0 {
        c.env("X4PLANT_AFFINITY", format!("{:#x}", affinity));
    }
    if detach {
        c.env("X4PLANT_DETACH", "1");
    }
    c.spawn().map_err(|e| format!("spawn {}: {}", exe, e))
}

/// A session snapshot (every check: the slow sensors too, revision 4). `procs` is the fresh filtered
/// snapshot; the caller merges the poller's union into it.
fn snapshot(cfg: &PilotConfig, ctx: &Ctx) -> SessionSense {
    let (tick, console) = sw::last_input();
    let filter = proc_filter(cfg);
    ctx.gpu_query_before_load.set(true);
    SessionSense {
        input_tick: tick,
        in_console_session: console,
        sessions: sw::wts_sessions(),
        procs: sw::processes_where(|i| filter(i)),
        gpu_util_pct: sw::gpu_util().ok(),
        nvme_temp_c: sw::nvme_temp_c(cfg.nvme_volume).ok(),
        scheme_guid: sw::active_scheme_guid(),
    }
}

// ------------------------------------------------------------------------------- run source

struct Src<'c> {
    ctx: &'c Ctx,
    rt: &'c RunType,
    session: String,
    env: EnvBlock,
    scratch_run: String,
    ceilings: Ceilings,
    golden: [u64; 4],
    runs: usize,
    seqs: Vec<u64>,
}

fn fresh_scratch(dir: &str) -> Result<(), String> {
    let p = std::path::Path::new(dir);
    if p.exists() {
        std::fs::remove_dir_all(p).map_err(|e| format!("cannot wipe scratch {}: {}", dir, e))?;
    }
    std::fs::create_dir_all(p).map_err(|e| format!("cannot create scratch {}: {}", dir, e))?;
    if std::fs::read_dir(p).map_err(|e| e.to_string())?.count() != 0 {
        return Err(format!("scratch {} not empty after the wipe", dir));
    }
    Ok(())
}

/// One run through the Job Object and the bracket, in observe mode; the verdict, the observed values
/// and the run record. Shared by the session source and the dry golden-learning run. Returns the
/// run's seq, the outcome and the wall time the whole launch-to-teardown took.
fn one_run(ctx: &Ctx, rt: &RunType, env: &EnvBlock, scratch_run: &str, ceilings: &Ceilings, golden: [u64; 4], session: &str, arm: &str, run_in_session: usize) -> (u64, Result<sandbox::RunOutcome, String>, f64) {
    let seq = ctx.seq.get() + 1;
    ctx.seq.set(seq);
    let t_wall = Instant::now();
    // the empty scratch is made right after the previous run (revision 4), so between the gate and
    // the launch lies only this emptiness check, not a wipe and create on the USB disk (a dry night
    // showed 0.1-0.4 s spikes there [M])
    let ready = std::fs::read_dir(scratch_run).map(|mut d| d.next().is_none()).unwrap_or(false);
    if let Err(e) = if ready { Ok(()) } else { fresh_scratch(scratch_run) } {
        return (seq, Err(e), t_wall.elapsed().as_secs_f64());
    }
    let (spin, idle) = ceilings.harness_cycles(ctx.rate);
    let limits = JobLimits { active_process_limit: 1, process_memory_bytes: (rt.memory_gib as usize) << 30, affinity_mask: rt.affinity as usize, priority_class: rt.priority_class };
    let spec = RunSpec {
        harness_exe: &rt.harness,
        workload: &rt.workload,
        param: rt.param,
        out_bytes: rt.out_bytes,
        salt: ctx.next_salt(),
        golden_hash: golden,
        limits,
        env,
        scratch_dir: scratch_run,
        tol: ceilings.tolerances(),
        time_cap_ms: (rt.time_cap_s * 1000).min(u32::MAX as u64) as u32,
        declared_threads: rt.threads,
        cycle_rate_hz: ctx.rate,
        spin_cycles: spin,
        idle_cycles: idle,
        exit_grace_ms: rt.exit_grace_ms.min(u32::MAX as u64) as u32,
    };
    let t0 = ctx.clock.now();
    // the gap from the end of the gate's load window to the launch (revision 4: should be ~ms)
    let gap_ms = ctx.last_load_end.get().map(|t| t.elapsed().as_secs_f64() * 1000.0);
    ctx.sensors.run_bracket_open();
    let out = sandbox::run_once(&spec);
    let lp = ctx.sensors.run_bracket_close();
    // wipe and recreate the scratch for the next run now, outside the gate-to-launch path; a failure
    // here is caught by the next run's emptiness check, which then wipes again or refuses
    let _ = fresh_scratch(scratch_run);
    let wall = t_wall.elapsed().as_secs_f64();
    let line = match &out {
        Err(e) => format!(
            "{{\"grade\":{},\"night\":{},\"session\":{},\"run_type\":{},\"seq\":{},\"run\":{},\"arm\":{},\"utc\":{:.3},\"pt\":{},\"verdict\":\"LaunchError\",\"error\":{}}}",
            jstr(ctx.grade.label()), jstr(&ctx.night), jstr(session), jstr(&rt.id), seq, run_in_session, jstr(arm), t0, jstr(&pilotcfg::pt_string(t0 as i64)), jstr(e)
        ),
        Ok(o) => {
            let ob = &o.observed;
            let v = observe::observe(ob);
            let (verdict, fails) = match &o.verdict {
                RunVerdict::Accept => ("Accept".to_string(), String::from("[]")),
                RunVerdict::TimeCapped => ("TimeCapped".to_string(), String::from("[]")),
                RunVerdict::IntegrityFail(fs) => {
                    let parts: Vec<String> = fs.iter().map(|f| format!("{{\"check\":{},\"class\":{},\"detail\":{}}}", jstr(f.check), jstr(f.class.label()), jstr(&f.detail))).collect();
                    ("IntegrityFail".to_string(), format!("[{}]", parts.join(",")))
                }
            };
            format!(
                concat!(
                    "{{\"grade\":{},\"night\":{},\"session\":{},\"run_type\":{},\"seq\":{},\"run\":{},\"arm\":{},\"utc\":{:.3},\"pt\":{},",
                    "\"verdict\":{},\"failures\":{},\"observe\":{},\"salt\":\"{:016x}\",\"hash_at_stop\":{},\"hash_at_exit\":{},",
                    "\"exit_code\":{},\"peak_process_memory\":{},\"env_sha256\":{},\"affinity\":\"{:#x}\",\"declared_threads\":{},\"cycle_rate_hz\":{},",
                    "\"gate_gap_ms\":{},\"run_wall_s\":{:.3},\"job_cpu_100ns\":{},\"run_lp_load_pct\":{},\"run_lp_clamped\":{},\"run_lp_dropped\":{},\"run_eff_mhz\":{}}}"
                ),
                jstr(ctx.grade.label()),
                jstr(&ctx.night),
                jstr(session),
                jstr(&rt.id),
                seq,
                run_in_session,
                jstr(arm),
                t0,
                jstr(&pilotcfg::pt_string(t0 as i64)),
                jstr(&verdict),
                fails,
                v.json(ceilings, ctx.rate),
                ob.salt,
                ob.hash_at_stop.map(|h| jstr(&sha256::hex_u64x4(&h))).unwrap_or_else(|| "null".into()),
                ob.hash_at_exit.map(|h| jstr(&sha256::hex_u64x4(&h))).unwrap_or_else(|| "null".into()),
                ob.exit_code.map(|c| c.to_string()).unwrap_or_else(|| "null".into()),
                ob.peak_process_memory,
                jstr(&env.sha256_hex),
                rt.affinity,
                rt.threads,
                ctx.rate,
                jf(gap_ms),
                wall,
                ob.job_cpu_after_stop_100ns.map(|x| x.to_string()).unwrap_or_else(|| "null".into()),
                jpairs(&lp.per_lp_pct),
                lp.clamped_lps,
                jdropped(&lp.dropped),
                jpairs(&lp.eff_mhz),
            )
        }
    };
    wl(&mut ctx.out.borrow_mut().runs, &line);
    if let Ok(o) = &out {
        ctx.job_cpu_100ns.set(ctx.job_cpu_100ns.get() + o.observed.job_cpu_after_stop_100ns.unwrap_or(0));
    }
    (seq, out, wall)
}

impl RunSource for Src<'_> {
    fn run(&mut self, arm: Arm) -> RunResult {
        let label = if arm == Arm::A { "A" } else { "B" };
        let (seq, out, wall) = one_run(self.ctx, self.rt, &self.env, &self.scratch_run, &self.ceilings, self.golden, &self.session, label, self.runs);
        self.seqs.push(seq);
        self.runs += 1;
        let o = match out {
            Ok(o) => o,
            Err(e) => {
                self.ctx.clock.pass(self.rt.t_run_plan_s + wall);
                self.ctx.void_line("INTEGRITY", &self.session, &format!("seq={} launch error: {}", seq, e));
                return RunResult::Integrity(format!("launch error: {}", e));
            }
        };
        // virtual clock: the planned run plus the real time outside the timed region (launch, init,
        // teardown, scratch); a real clock has passed by itself
        let outside = (wall - o.delta_o_ns as f64 / 1e9).max(0.0);
        self.ctx.clock.pass(self.rt.t_run_plan_s.max(o.delta_o_ns as f64 / 1e9) + outside);
        self.ctx.prev_run.set(Some((self.rt.cooldown_factor > 1.0, o.delta_o_ns)));
        // T = delta_h of an accepted run (record section 4); delta_o enters only the bracket
        let dh = o.observed.report.as_ref().and_then(|r| r.delta_h_ns());
        match &o.verdict {
            RunVerdict::Accept => RunResult::Accepted { ns: dh.unwrap_or(0) },
            RunVerdict::TimeCapped => RunResult::TimeCapped { cap_ns: self.rt.time_cap_s * 1_000_000_000 },
            RunVerdict::IntegrityFail(fs) => {
                let only_short = fs.iter().all(|f| f.check == "bracket_too_short");
                if self.ctx.grade == Grade::DryRun && only_short {
                    // DRY-RUN only: a sub-second run cannot be bracketed; counted, and recorded as such
                    return RunResult::Accepted { ns: dh.unwrap_or(0) };
                }
                let why: Vec<String> = fs.iter().map(|f| format!("{} [{}]", f.check, f.class.label())).collect();
                let msg = format!("seq={} integrity failure: {}", seq, why.join(", "));
                self.ctx.void_line("INTEGRITY", &self.session, &msg);
                RunResult::Integrity(msg)
            }
        }
    }
}

// ------------------------------------------------------------------------------------ gate

struct Gate<'c> {
    ctx: &'c Ctx,
    cfg: &'c PilotConfig,
    rt: &'c RunType,
    session: String,
    base: SessionSense,
    profile_ok: bool,
    /// Core parking read at the session start; re-read after every block (revision 4).
    parking: Option<(u32, u32)>,
    first: bool,
    block_no: usize,
    block_before: Vec<ProcSample>,
    block_gen: u64,
    block_sys: Option<(u64, u64, u64)>,
    block_own: Option<u64>,
    block_job: u64,
    block_t: Instant,
    block_seq0: u64,
    /// The run core rule's core mask (0 = the rule does not apply to this run type).
    core: u64,
}

impl Gate<'_> {
    fn plant_session(&self, now: &mut SessionSense) -> Option<String> {
        let mut p = self.ctx.plant.borrow_mut();
        p.checks += 1;
        if p.checks != 2 {
            return None;
        }
        let note = match p.kind {
            PlantKind::Input => {
                now.input_tick = Some(now.input_tick.unwrap_or(0).wrapping_add(1));
                Some("injected input tick + 1".to_string())
            }
            PlantKind::Session => {
                if let Some(s) = now.sessions.as_mut() {
                    s.push((99, "RDP-Tcp#planted".into(), 0));
                }
                Some("injected session 99 RDP-Tcp#planted".to_string())
            }
            PlantKind::Gpu => {
                now.gpu_util_pct = Some(50.0);
                Some("injected GPU 50%".to_string())
            }
            PlantKind::Scheme => {
                now.scheme_guid = Some("00000000-0000-0000-0000-000000000000".into());
                Some("injected power scheme".to_string())
            }
            _ => None,
        };
        if let Some(n) = &note {
            p.note = n.clone();
        }
        note
    }
    /// Excluded / started-only / Mithril plants: a detached process that lives about 1 s and exits
    /// before the next check (the poller must see it), started before check 2.
    fn plant_spawn_before_snapshot(&self) {
        let mut p = self.ctx.plant.borrow_mut();
        if p.checks + 1 != 2 {
            return;
        }
        let name = match p.kind {
            PlantKind::Excluded => "x4plant_gems.exe",
            PlantKind::Started => "x4plant_shell.exe",
            PlantKind::Mithril => "x4harness_foreign.exe",
            _ => return,
        };
        let dst = format!("{}\\{}", p.dir, name);
        let _ = std::fs::create_dir_all(&p.dir);
        let r = std::fs::copy(&p.exe, &dst).map_err(|e| e.to_string()).and_then(|_| spawn_plant(&dst, &["1000".into(), "1".into()], p.affinity, true));
        p.note = match r {
            Ok(mut c) => {
                let _ = c.wait(); // the launcher exits at once; the plant runs on, parented elsewhere
                format!("started {} detached (busy 1 s, 1 thread), then waited 2 s so it has exited before the check", dst)
            }
            Err(e) => format!("plant spawn failed: {}", e),
        };
        drop(p);
        // the plant lives 1 s: by the snapshot it has exited, so only the poller can have seen it
        std::thread::sleep(Duration::from_millis(2000));
    }
}

impl GateSensor for Gate<'_> {
    fn block_start(&mut self) {
        self.first = true;
        self.block_no += 1;
        let filter = proc_filter(self.cfg);
        self.block_gen = self.ctx.poller.mark();
        self.block_before = sw::processes_where(|i| filter(i));
        self.block_sys = sw::system_times();
        self.block_own = sw::own_cpu_100ns();
        self.block_job = self.ctx.job_cpu_100ns.get();
        self.block_t = Instant::now();
        self.block_seq0 = self.ctx.seq.get() + 1;
    }
    fn before_run(&mut self) {
        // the end-to-end cool-down (ROADMAP section 10): (c - 1) x the previous NVMe-bound run's
        // delta_o, across sessions too, before this run's checks (revision 4)
        if self.rt.cooldown_factor > 1.0 {
            if let Some((true, d)) = self.ctx.prev_run.get() {
                let s = if self.ctx.clock.is_virtual() { (self.rt.cooldown_factor - 1.0) * self.rt.t_run_plan_s } else { (self.rt.cooldown_factor - 1.0) * d as f64 / 1e9 };
                self.ctx.clock.wait(s);
            }
        }
    }
    fn read(&mut self) -> GateReading {
        let t_read = Instant::now();
        let cfg = self.cfg;
        // planted load / writes (dry only), started just before the sample
        let kind = self.ctx.plant.borrow().kind;
        let read_no = {
            let mut p = self.ctx.plant.borrow_mut();
            p.reads += 1;
            p.reads
        };
        let mut plant_child = None;
        if read_no == 2 && (kind == PlantKind::Load || kind == PlantKind::Writes || kind == PlantKind::CoreLoad) {
            let p = self.ctx.plant.borrow();
            let total = cfg.settle_timeout_s * 1000 + cfg.load_window_ms + 3000;
            let (args, aff): (Vec<String>, u64) = match kind {
                PlantKind::Load => (vec![format!("{}", total), "3".into()], p.affinity),
                PlantKind::CoreLoad => (vec![format!("{}", total), "1".into()], self.rt.affinity),
                _ => (vec![format!("{}", cfg.settle_timeout_s * 1000 + 3000), "1".into(), "256".into(), format!("{}\\plantwrite.bin", p.dir)], p.affinity),
            };
            let _ = std::fs::create_dir_all(&p.dir);
            plant_child = spawn_plant(&p.exe, &args, aff, false).ok();
            drop(p);
            self.ctx.plant.borrow_mut().note = format!("x4plant {:?} on {:#x} started: {}", args, aff, plant_child.is_some());
            std::thread::sleep(Duration::from_millis(200));
        }
        // revision 4: the start state first (it may wait up to 60 s), the 2-s load last, so the load
        // reading directly precedes the launch; the GPU query of the snapshot lies before both
        let after_gpu = self.ctx.gpu_query_before_load.replace(false);
        let t_settle = Instant::now();
        let (mut q, mut w, mut m);
        let mut ok;
        loop {
            let s = self.ctx.sensors.disk_sample(cfg.disk_window_ms);
            q = s.0;
            w = s.1;
            m = s.2;
            ok = hygiene::start_state_ok(cfg, q, w);
            if ok || t_settle.elapsed() >= Duration::from_secs(cfg.settle_timeout_s) {
                break;
            }
        }
        let settle_ms = t_settle.elapsed().as_millis();
        let load = self.ctx.sensors.load_sample(cfg.load_window_ms);
        self.ctx.last_load_end.set(Some(Instant::now()));
        if let Some(mut c) = plant_child {
            if kind != PlantKind::Writes {
                let _ = c.kill(); // a busy plant; the write plant ends by itself and deletes its file
            }
            let _ = c.wait();
        }
        let core = if self.core == 0 { Ok(()) } else { hygiene::core_quiet(&load.per_lp_pct, self.core, cfg.core_load_max_pct, cfg.grade == Grade::Pilot) };
        let now = self.ctx.clock.now();
        let in_window = now >= self.ctx.window.0 && now < self.ctx.window.2;
        let r = hygiene::gate_reading(load.sys_total_pct, ok, in_window, self.profile_ok, core.is_ok());
        let seq = self.ctx.seq.get() + 1; // the run this reading gates
        wl(
            &mut self.ctx.out.borrow_mut().sensors,
            &format!(
                concat!(
                    "{{\"grade\":{},\"night\":{},\"session\":{},\"for_seq\":{},\"utc\":{:.3},\"load_total_pct\":{},\"load_pdh_total_pct\":{},\"load_per_lp_pct\":{},",
                    "\"clamped_lps\":{},\"dropped_lps\":{},\"run_core\":\"{:#x}\",\"run_core_quiet\":{},\"eff_mhz\":{},\"acpi_thermal_k\":{},\"disk_queue\":{},\"disk_write_bps\":{},",
                    "\"modified_page_bytes\":{},\"settle_ms\":{},\"start_state_ok\":{},\"in_window\":{},\"after_gpu_query\":{},\"poll_ms\":{}}}"
                ),
                jstr(self.ctx.grade.label()),
                jstr(&self.ctx.night),
                jstr(&self.session),
                seq,
                now,
                jf(load.sys_total_pct),
                jf(load.total_pct),
                jpairs(&load.per_lp_pct),
                load.clamped_lps,
                jdropped(&load.dropped),
                self.core,
                match &core {
                    Ok(()) => "true".to_string(),
                    Err(e) => jstr(e),
                },
                jpairs(&load.eff_mhz),
                jpairs(&load.thermal_k),
                jf(q),
                jf(w),
                jf(m),
                settle_ms,
                ok,
                in_window,
                after_gpu,
                POLL_MS
            ),
        );
        self.ctx.clock.pass_real(t_read);
        r
    }
    fn session_void(&mut self) -> Option<String> {
        let t = Instant::now();
        let first = self.first;
        self.first = false;
        self.plant_spawn_before_snapshot();
        let mut now = snapshot(self.cfg, self.ctx);
        now.procs = self.ctx.poller.union(&now.procs);
        let _ = self.plant_session(&mut now);
        let mut why = Vec::new();
        if self.ctx.clock.now() >= self.ctx.window.2 {
            why.push("session cut by the end of the quiet window (07:00 PT)".to_string());
        }
        if let Some(v) = hygiene::session_void(self.cfg, &self.base, &now, &[self.ctx.own_pid], self.ctx.rate, first) {
            why.push(v);
        }
        self.ctx.clock.pass_real(t);
        if why.is_empty() {
            None
        } else {
            let r = why.join("; ");
            self.ctx.void_line("SESSION-VOID", &self.session, &r);
            Some(r)
        }
    }
    fn after_block(&mut self) -> Option<String> {
        let t = Instant::now();
        let filter = proc_filter(self.cfg);
        let mut seen = self.ctx.poller.seen_after(self.block_gen, &sw::processes_where(|i| filter(i)));
        if self.ctx.plant.borrow().kind == PlantKind::Defender {
            if let Some(p) = seen.iter_mut().find(|p| p.image == "msmpeng") {
                p.cycles = p.cycles.map(|c| c + 1_000_000_000_000);
            } else {
                seen.push(ProcSample { pid: 1, image: "msmpeng".into(), cycles: Some(1_000_000_000_000), ..Default::default() });
            }
            self.ctx.plant.borrow_mut().note = "injected 1e12 MsMpEng cycles over the block".into();
        }
        let planned_ns = (self.cfg.planned_block_s(self.rt) * 1e9) as u64;
        let mut r = hygiene::bg_discard(self.cfg, &self.block_before, &seen, planned_ns, self.ctx.rate);
        // the other CPU on the machine over the block (descriptive): system busy - job - this process
        let sys = sw::system_times();
        let busy = match (self.block_sys, sys) {
            (Some(a), Some(b)) => sw::busy_100ns(a, b),
            _ => None,
        };
        let own = match (self.block_own, sw::own_cpu_100ns()) {
            (Some(a), Some(b)) => Some(b.saturating_sub(a)),
            _ => None,
        };
        let job = self.ctx.job_cpu_100ns.get().saturating_sub(self.block_job);
        let other = match (busy, own) {
            (Some(b), Some(o)) => Some(b.saturating_sub(job).saturating_sub(o)),
            _ => None,
        };
        // core parking under the same scheme GUID (revision 4): a change discards this block and voids
        // the session at the next gate (profile_ok = false)
        let park = crate::profile_win::WinState.core_parking_min_max();
        if park != self.parking {
            self.profile_ok = false;
            let x = format!("core parking changed ({:?} -> {:?})", self.parking, park);
            r = Some(match r {
                Some(s) => format!("{}; {}", s, x),
                None => x,
            });
        }
        wl(
            &mut self.ctx.out.borrow_mut().sensors,
            &format!(
                "{{\"grade\":{},\"night\":{},\"session\":{},\"kind\":\"block_cpu\",\"block_attempt\":{},\"first_seq\":{},\"last_seq\":{},\"wall_s\":{:.3},\"planned_block_s\":{:.3},\"system_busy_core_s\":{},\"job_core_s\":{:.4},\"orchestrator_core_s\":{},\"other_core_s\":{},\"core_parking\":{:?},\"bg_discard\":{}}}",
                jstr(self.ctx.grade.label()),
                jstr(&self.ctx.night),
                jstr(&self.session),
                self.block_no,
                self.block_seq0,
                self.ctx.seq.get(),
                self.block_t.elapsed().as_secs_f64(),
                self.cfg.planned_block_s(self.rt),
                jf(busy.map(|x| x as f64 / 1e7)),
                job as f64 / 1e7,
                jf(own.map(|x| x as f64 / 1e7)),
                jf(other.map(|x| x as f64 / 1e7)),
                format!("{:?}", park),
                r.as_deref().map(jstr).unwrap_or_else(|| "null".into())
            ),
        );
        if let Some(x) = &r {
            self.ctx.void_line("DISCARD", &self.session, x);
        }
        self.ctx.clock.pass_real(t);
        r
    }
}

// ------------------------------------------------------------------------------- one session

fn session_cfg(rt: &RunType, seed: u64, horizon: usize, load_max: f64) -> SessionConfig {
    SessionConfig {
        seed,
        horizon,
        sigma_hat_d: 0.02,
        sigma_hat_run: 0.02,
        pilot_median_ln_ns: (rt.t_run_plan_s * 1e9).ln(),
        alpha_i: None,
        load_threshold_pct: load_max,
    }
}

fn ceilings_of(rt: &RunType, rate: u64) -> Ceilings {
    Ceilings {
        kappa_post_cycles: rt.kappa_post_cycles,
        eps_spin_ns: rt.eps_spin_us * 1000,
        eps_idle_ns: rt.eps_idle_us * 1000,
        init_max_ns: rt.init_max_ms * 1_000_000,
        init_max_cycles: rt.init_max_cycles_at(rate),
        extra_cores_milli: rt.extra_cores_milli,
        exit_grace_ns: rt.exit_grace_ms * 1_000_000,
    }
}

fn end_label(e: &SessionEnd) -> (&'static str, String) {
    match e {
        SessionEnd::Completed => ("completed", String::new()),
        // a session cut by 07:00 PT is a hygiene void, written as its own end (revision 4: section 9
        // reports sigma_d with and without the cut sessions' blocks)
        SessionEnd::HygieneVoid { reason, .. } if reason.starts_with("session cut") => ("cut", reason.clone()),
        SessionEnd::HygieneVoid { reason, .. } => ("hygiene_void", reason.clone()),
        SessionEnd::IntegrityStop { reason } => ("integrity_stop", reason.clone()),
    }
}

/// verify-profile --collection --pins for one run type (affinity, priority, env block): the
/// fingerprint hash, or why not.
fn profile_check(cfg: &PilotConfig, rt: &RunType) -> Result<String, String> {
    let pf = rt.pins.as_ref().ok_or("no pins file")?;
    let pins = crate::profile::parse_pins(&std::fs::read_to_string(pf).map_err(|e| e.to_string())?)?;
    let mut spec = crate::profile::ProfileSpec::default();
    spec.expected_scheme_guid = pins.scheme_guid;
    spec.expected_fingerprint_hash = pins.fingerprint_sha256;
    let scratch_run = format!("{}\\run", cfg.scratch.trim_end_matches('\\'));
    let env = runenv::build(&std::env::var("SystemRoot").unwrap_or_else(|_| "C:\\Windows".into()), &scratch_run, &rt.env)?;
    let fp = crate::profile_win::read_fingerprint(rt.affinity, rt.priority_class, &env.sha256_hex);
    crate::profile::verify_for_collection(&spec, &crate::profile_win::WinState, &fp).map(|vp| vp.hash().to_string())
}

fn run_session_for(ctx: &Ctx, cfg: &PilotConfig, rt: &RunType, id: &str, seed: u64, horizon: usize, golden: [u64; 4]) -> Result<SessionResult, String> {
    let scratch_run = format!("{}\\run", cfg.scratch.trim_end_matches('\\'));
    let system_root = std::env::var("SystemRoot").unwrap_or_else(|_| "C:\\Windows".into());
    let env = runenv::build(&system_root, &scratch_run, &rt.env)?;
    let t_start = ctx.clock.now();
    let t_setup = Instant::now();
    // the profile, re-verified at every session start (PILOT; revision 4): a mismatch voids at the
    // first gate (profile_ok = false), an unreadable profile fails closed
    let (profile_ok, profile_note) = if ctx.grade == Grade::Pilot {
        match profile_check(cfg, rt) {
            Ok(h) => (true, h),
            Err(e) => (false, format!("REFUSED: {}", e.lines().next().unwrap_or(""))),
        }
    } else {
        (true, "not checked (dry run: no pins)".to_string())
    };
    // the session set-up: a real settle on a real clock (revision 4), so a microbenchmark session does
    // not start straight after an end-to-end one with the package and the NVMe heat-soaked
    ctx.clock.wait(cfg.session_setup_s);
    let settle = ctx.sensors.load_sample(cfg.load_window_ms);
    let run_lps: Vec<String> = mask_lps(rt.affinity).iter().map(|x| x.to_string()).collect();
    let eff_run: Vec<f64> = settle.eff_mhz.iter().filter(|(n, _)| run_lps.iter().any(|r| r == n || n.ends_with(&format!(",{}", r)))).map(|(_, x)| *x).collect();
    let eff_mean = if eff_run.is_empty() { None } else { Some(eff_run.iter().sum::<f64>() / eff_run.len() as f64) };
    let mut base = snapshot(cfg, ctx);
    ctx.poller.reset(&base.procs);
    base.procs = ctx.poller.union(&base.procs);
    let nvme_at_settle = base.nvme_temp_c;
    let parking = crate::profile_win::WinState.core_parking_min_max();
    ctx.clock.pass_real(t_setup);
    let mut gate = Gate {
        ctx,
        cfg,
        rt,
        session: id.to_string(),
        base,
        profile_ok,
        parking,
        first: true,
        block_no: 0,
        block_before: Vec::new(),
        block_gen: 0,
        block_sys: None,
        block_own: None,
        block_job: 0,
        block_t: Instant::now(),
        block_seq0: 0,
        core: ctx.run_core(rt),
    };
    let mut src = Src { ctx, rt, session: id.to_string(), env, scratch_run, ceilings: ceilings_of(rt, ctx.rate), golden, runs: 0, seqs: Vec::new() };
    let res = session::run_session(&session_cfg(rt, seed, horizon, cfg.load_max_pct), &mut src, &mut gate);
    let t_end = ctx.clock.now();
    {
        let mut out = ctx.out.borrow_mut();
        for (i, b) in res.blocks.iter().enumerate() {
            let seqs: Vec<String> = (0..4).map(|k| src.seqs.get(b.first_run + k).map(|s| s.to_string()).unwrap_or_else(|| "null".into())).collect();
            let arms: Vec<&str> = b.runs.iter().map(|r| if r.0 == Arm::A { "\"A\"" } else { "\"B\"" }).collect();
            let lns: Vec<String> = b.runs.iter().map(|r| format!("{:.9}", r.1)).collect();
            wl(
                &mut out.blocks,
                &format!(
                    "{{\"grade\":{},\"night\":{},\"session\":{},\"block\":{},\"order\":\"{:?}\",\"seqs\":[{}],\"arms\":[{}],\"ln_delta_h_ns\":[{}],\"capped\":{:?},\"d\":{:.9},\"wealth_placeholder\":{{\"sup\":{:.6},\"ni\":{:.6},\"kill\":{:.6}}}}}",
                    jstr(ctx.grade.label()),
                    jstr(&ctx.night),
                    jstr(id),
                    i + 1,
                    b.order,
                    seqs.join(","),
                    arms.join(","),
                    lns.join(","),
                    b.capped,
                    b.d,
                    b.k_sup,
                    b.k_ni,
                    b.k_kill
                ),
            );
        }
        let (end, reason) = end_label(&res.end);
        let dr: Vec<String> = res.discard_reasons.iter().map(|r| jstr(r)).collect();
        wl(
            &mut out.sessions,
            &format!(
                concat!(
                    "{{\"grade\":{},\"night\":{},\"session\":{},\"run_type\":{},\"seed\":\"{:016x}\",\"start_utc\":{:.3},\"start_pt\":{},\"end_utc\":{:.3},\"end_pt\":{},",
                    "\"planned_s\":{:.1},\"actual_s\":{:.1},\"profile\":{},\"settle_eff_mhz_run_lps\":{},\"settle_nvme_c\":{},\"end\":{},\"reason\":{},\"blocks\":{},\"runs\":{},",
                    "\"discards\":{},\"discard_reasons\":[{}],\"s3_trend_reported\":{},\"carry_over\":{}}}"
                ),
                jstr(ctx.grade.label()),
                jstr(&ctx.night),
                jstr(id),
                jstr(&rt.id),
                seed,
                t_start,
                jstr(&pilotcfg::pt_string(t_start as i64)),
                t_end,
                jstr(&pilotcfg::pt_string(t_end as i64)),
                cfg.planned_secs(rt),
                t_end - t_start,
                jstr(&profile_note),
                jf(eff_mean),
                jf(nvme_at_settle),
                jstr(end),
                jstr(&reason),
                res.blocks.len(),
                src.runs,
                res.discards.len(),
                dr.join(","),
                res.s3_void,
                match res.carry_over {
                    Some((a, b)) => format!("[{:.6},{:.6}]", a, b),
                    None => "null".into(),
                }
            ),
        );
    }
    for (i, ((next, w), r)) in res.discards.iter().zip(res.discard_reasons.iter()).enumerate() {
        ctx.void_line("DISCARD-LOGGED", id, &format!("#{} next_block={} reason={} wealth_after_decision(sup,ni,kill)=({:.4},{:.4},{:.4})", i + 1, next + 1, r, w.sup, w.ni, w.kill));
    }
    if let SessionEnd::HygieneVoid { reason, wealth_at_void } = &res.end {
        ctx.void_line("VOID-LOGGED", id, &format!("reason={} wealth_after_decision(sup,ni,kill)=({:.4},{:.4},{:.4})", reason, wealth_at_void.sup, wealth_at_void.ni, wealth_at_void.kill));
    }
    Ok(res)
}

// --------------------------------------------------------------------------------- pre-start

fn item(name: &str, ok: bool, detail: String) -> NightItem {
    NightItem { name: name.to_string(), ok, required: true, detail }
}

/// The pre-start items (section 10 night refusal), read-only. `strict` = PILOT.
pub fn prestart_items(cfg: &PilotConfig, sensors: &Sensors, strict: bool) -> Vec<NightItem> {
    let mut v = Vec::new();
    let me = std::env::current_exe().map(|p| p.display().to_string()).unwrap_or_default();
    let pin_item = |name: &str, path: &str, pin: &Option<String>| -> NightItem {
        let h = file_sha256(path);
        let ok = match (&h, pin) {
            (Ok(h), Some(p)) => h == p,
            (Ok(_), None) => !strict,
            (Err(_), _) => false,
        };
        item(name, ok, format!("{} sha256 {} (pinned {:?})", path, h.unwrap_or_else(|e| e), pin))
    };
    v.push(pin_item("x4svc binary sha256 equals the pin", &me, &cfg.x4svc_sha256));
    if let Some(p) = &cfg.probe_exe {
        v.push(pin_item("probe exe sha256 equals the pin", p, &cfg.probe_sha256));
    }
    for rt in &cfg.run_types {
        match file_sha256(&rt.harness) {
            Ok(h) => {
                let ok = rt.harness_sha256.as_ref().map_or(!strict, |p| *p == h);
                v.push(item(&format!("[{}] harness sha256 equals the pin", rt.id), ok, format!("{} {} (pinned {:?})", rt.harness, h, rt.harness_sha256)));
            }
            Err(e) => v.push(item(&format!("[{}] harness present", rt.id), false, e)),
        }
        if let Some((_, path)) = rt.env.iter().find(|(k, _)| k == "X4_MODEL_PATH") {
            let vol = path.chars().next().unwrap_or('?');
            let bus = sw::volume_bus_type(vol);
            let ok = matches!(bus, Ok(t) if t != 7) && std::fs::File::open(path).is_ok();
            v.push(item(
                &format!("[{}] model file readable and not on a USB disk", rt.id),
                ok,
                format!("{} on {}: bus {}", path, vol, match bus {
                    Ok(t) => format!("{} ({})", t, sw::bus_type_name(t)),
                    Err(e) => e,
                }),
            ));
        }
        if strict {
            let r = profile_check(cfg, rt);
            v.push(item(&format!("[{}] verify-profile --collection --pins MET", rt.id), r.is_ok(), r.unwrap_or_else(|e| e.lines().next().unwrap_or("").to_string())));
        }
    }
    // placement by the record's topology rule (section 3): mb LP p, e2e every LP but the reserved one
    let topo = sw::topology();
    let n_lps: usize = topo.as_ref().map(|t| t.cores.iter().map(|c| c.count_ones() as usize).sum()).unwrap_or(0);
    match topo.as_ref().ok().and_then(|t| t.pilot_masks()) {
        Some((p, reserved, all_but)) => {
            let mb_ok = cfg.run_types.first().map_or(false, |r| r.affinity == p);
            let e2e_ok = cfg.run_types.get(1).map_or(false, |r| r.affinity == all_but);
            let orch_ok = 1u64 << cfg.orchestrator_lp == reserved;
            v.push(item(
                "placement equals the record's topology rule (x4svc topology)",
                (mb_ok && e2e_ok && orch_ok) || !strict,
                format!("mb {:#x} (rule {:#x}), e2e {:#x} (rule {:#x}), orchestrator LP {} (rule LP {})", cfg.run_types.first().map_or(0, |r| r.affinity), p, cfg.run_types.get(1).map_or(0, |r| r.affinity), all_but, cfg.orchestrator_lp, reserved.trailing_zeros()),
            ));
        }
        None => v.push(item("placement equals the record's topology rule (x4svc topology)", !strict, format!("{:?}", topo.err()))),
    }
    // the load sensor over the record's window, every LP read (revision 4). PDH marks an instance
    // PDH_CSTATUS_INVALID_DATA (0xc0000bba) now and then at 100-200 ms windows, never in 11 reads at
    // 2 s [M, 2026-10-23]; up to 3 reads, so one transient instance does not refuse a night
    let mut l = sensors.load_sample(cfg.load_window_ms);
    let mut attempts = 1;
    while attempts < 3 && !(l.sys_total_pct.is_some() && n_lps > 0 && l.per_lp_pct.len() == n_lps) {
        l = sensors.load_sample(cfg.load_window_ms);
        attempts += 1;
    }
    v.push(item(
        "sensor: CPU load (GetSystemTimes; PDH per LP, every LP)",
        l.sys_total_pct.is_some() && n_lps > 0 && l.per_lp_pct.len() == n_lps,
        format!(
            "read {}: machine {:?}% (PDH _Total {:?}%) over {} ms, {} of {} LPs ({} clamped from PDH_CALC_NEGATIVE_VALUE; dropped {:?}), eff clock on {} LPs, {} thermal zones",
            attempts,
            l.sys_total_pct.map(|x| (x * 100.0).round() / 100.0),
            l.total_pct.map(|x| (x * 100.0).round() / 100.0),
            cfg.load_window_ms,
            l.per_lp_pct.len(),
            n_lps,
            l.clamped_lps,
            l.dropped.iter().map(|(n, s)| format!("{}:{:#x}", n, s)).collect::<Vec<_>>(),
            l.eff_mhz.len(),
            l.thermal_k.len()
        ),
    ));
    let (q, w, m) = sensors.disk_sample(cfg.disk_window_ms);
    v.push(item("sensor: disk queue, write rate, modified page list (PDH)", q.is_some() && w.is_some(), format!("queue {:?}, write {:?} B/s, modified {:?} B", q, w, m)));
    let procs = sw::processes();
    let unread: Vec<String> = procs.iter().filter(|p| p.cycles.is_none() && (hygiene::image_in(&p.image, &cfg.bg_images) || hygiene::image_in(&p.image, &cfg.excluded_images))).map(|p| p.image.clone()).collect();
    v.push(item("sensor: process CPU (listed images readable)", !procs.is_empty() && unread.is_empty(), format!("{} processes; unreadable listed images {:?}", procs.len(), unread)));
    let (tick, console) = sw::last_input();
    v.push(item("sensor: interactive input (driver in the console session)", tick.is_some() && console == Some(true), format!("tick {:?}, in console session {:?}", tick, console)));
    let s = sw::wts_sessions();
    v.push(item("sensor: session list (WTS)", s.is_some(), format!("{:?}", s)));
    let g = sw::gpu_util();
    v.push(item("sensor: GPU utilisation (nvidia-smi query)", g.is_ok(), format!("{:?}", g)));
    let t = sw::nvme_temp_c(cfg.nvme_volume);
    v.push(item(&format!("sensor: NVMe temperature of {}: (storage query)", cfg.nvme_volume), t.is_ok(), format!("{:?}", t)));
    let sch = sw::active_scheme_guid();
    v.push(item("sensor: active power scheme", sch.is_some(), format!("{:?}", sch)));
    // how the driver was launched (revision 4): a task registered with the default settings runs at
    // BELOW_NORMAL (Task Scheduler priority 7) [M, review]; the record pins NORMAL and normal memory
    // priority; elevation and integrity are recorded
    let own = sw::own_process();
    v.push(item(
        "driver at NORMAL_PRIORITY_CLASS and MEMORY_PRIORITY_NORMAL",
        own.priority_class == Some(0x20) && own.memory_priority == Some(5),
        format!("priority class {:?}, memory priority {:?}, elevated {:?}, integrity RID {:?}", own.priority_class.map(|x| format!("{:#x}", x)), own.memory_priority, own.elevated, own.integrity_rid.map(|x| format!("{:#x}", x))),
    ));
    let present: Vec<String> = procs.iter().filter(|p| hygiene::image_in(&p.image, &cfg.excluded_images)).map(|p| format!("{}({})", p.image, p.pid)).collect();
    let mut adv = item("no excluded process running at the start (advisory: one that stays idle does not void)", present.is_empty(), format!("{:?}", present));
    adv.required = false;
    v.push(adv);
    v
}

fn selftest_mode(cfg: &PilotConfig) -> Result<String, String> {
    let me = std::env::current_exe().map_err(|e| e.to_string())?;
    let probe = cfg.probe_exe.as_ref().ok_or("no probe_exe")?;
    let harness = &cfg.run_types[0].harness;
    // the self-test's scratch probe requires an EMPTY directory: a fresh one of its own (the scratch
    // root holds the dry-run records; a non-empty scratch made the self-test refuse [M, 2026-10-23])
    let st = format!("{}\\selftest", cfg.scratch.trim_end_matches('\\'));
    fresh_scratch(&st)?;
    // the job gets the first run type's affinity limit, so the widen-affinity probe tests the job
    // limit a pilot run has (revision 4: without it the verdict depended on the launcher's mask)
    let aff = format!("{:#x}", cfg.run_types[0].affinity);
    let out = std::process::Command::new(me).args(["selftest", "--harness", harness, "--probe-exe", probe, "--scratch", &st, "--affinity", &aff]).output().map_err(|e| e.to_string());
    let _ = std::fs::remove_dir_all(&st);
    let out = out?;
    let text = String::from_utf8_lossy(&out.stdout).to_string();
    text.lines().find_map(|l| l.strip_prefix("mode: ").map(|m| m.trim().to_string())).ok_or_else(|| "no mode line".into())
}

// --------------------------------------------------------------------------------- progress

pub struct NightOpts {
    pub dry: bool,
    pub plants: bool,
    pub max_sessions: Option<usize>,
    pub plant_exe: Option<String>,
}

/// progress.txt (record section 6): `<id> started <grade> <night> seed=<hex> harness=<sha>
/// x4svc=<sha>` (synced before the session's first run), then `<id> <end> <grade> <night>`.
#[derive(Debug, Default, PartialEq)]
pub struct Progress {
    /// Every session with a started line (none is ever re-run).
    pub started: Vec<String>,
    /// (session, end) for every end line.
    pub ended: Vec<(String, String)>,
    /// (session, seed, harness sha, x4svc sha) of every started line.
    pub pins: Vec<(String, String, String, String)>,
}
pub fn parse_progress(text: &str) -> Progress {
    let mut p = Progress::default();
    for l in text.lines() {
        let f: Vec<&str> = l.split_whitespace().collect();
        if f.len() < 2 {
            continue;
        }
        if f[1] == "started" {
            p.started.push(f[0].to_string());
            let kv = |k: &str| f.iter().find_map(|x| x.strip_prefix(k)).unwrap_or("").to_string();
            p.pins.push((f[0].to_string(), kv("seed="), kv("harness="), kv("x4svc=")));
        } else {
            if !p.started.iter().any(|s| s == f[0]) {
                p.started.push(f[0].to_string()); // a pre-revision-4 file: the end line alone
            }
            p.ended.push((f[0].to_string(), f[1].to_string()));
        }
    }
    p
}
impl Progress {
    pub fn interrupted(&self) -> Vec<String> {
        self.started.iter().filter(|s| !self.ended.iter().any(|(e, _)| e == *s)).cloned().collect()
    }
    pub fn integrity_stops(&self) -> Vec<String> {
        self.ended.iter().filter(|(_, e)| e == "integrity_stop").map(|(s, _)| s.clone()).collect()
    }
}
fn append_synced(path: &str, line: &str) -> Result<(), String> {
    let mut f = std::fs::OpenOptions::new().create(true).append(true).open(path).map_err(|e| format!("{}: {}", path, e))?;
    writeln!(f, "{}", line).map_err(|e| e.to_string())?;
    f.sync_all().map_err(|e| e.to_string())
}

// --------------------------------------------------------------------------------- the night

/// Run one night. Returns the process exit code: 0 done, 1 refused, 3 setup error, 4 integrity stop.
pub fn run_night(cfg: &PilotConfig, cfg_path: &str, opts: &NightOpts) -> i32 {
    let want = if opts.dry { Grade::DryRun } else { Grade::Pilot };
    if cfg.grade != want {
        eprintln!("pilot-night: the configuration's grade is {} but the command asked for {}; refusing", cfg.grade.label(), want.label());
        return 1;
    }
    let cfg_sha = file_sha256(cfg_path).unwrap_or_default();
    let real_now = utc_now();
    // the window: real (PILOT) or a virtual night starting at the next window start (DRY-RUN)
    let (night_label, window, clock) = if opts.dry {
        let l = pilotcfg::pt_local(real_now as i64);
        let day = l.div_euclid(86400);
        let start = pilotcfg::pt_local_to_utc(day * 86400 + cfg.window_start_pt_min as i64 * 60) as f64;
        let last = pilotcfg::pt_local_to_utc((day + 1) * 86400 + cfg.last_end_pt_min as i64 * 60) as f64;
        let end = pilotcfg::pt_local_to_utc((day + 1) * 86400 + cfg.window_end_pt_min as i64 * 60) as f64;
        (format!("dry-{}", stamp(real_now)), (start, last, end), Clock::virtual_at(start))
    } else {
        let mut now = real_now as i64;
        let mut w = pilotcfg::night_window(cfg, now);
        if w.is_none() {
            // launched shortly before the window: wait for it (at most one hour), never start outside it
            let next = pilotcfg::night_window(cfg, now + 3600).map(|x| x.1);
            match next {
                Some(s) if s > now => {
                    eprintln!("pilot-night: waiting {} s for the window start ({})", s - now, pilotcfg::pt_string(s));
                    std::thread::sleep(Duration::from_secs((s - now) as u64));
                    now = utc_now() as i64;
                    w = pilotcfg::night_window(cfg, now);
                }
                _ => {}
            }
        }
        match w {
            Some((night, s, l, e)) => {
                let (y, m, d) = pilotcfg::civil_from_days(night);
                (format!("{:04}-{:02}-{:02}", y, m, d), (s as f64, l as f64, e as f64), Clock::real())
            }
            None => {
                eprintln!("pilot-night: outside the quiet window ({}); refusing", pilotcfg::pt_string(now));
                return 1;
            }
        }
    };
    let dir = if opts.dry {
        format!("{}\\dry\\{}", cfg.scratch.trim_end_matches('\\'), night_label)
    } else {
        format!("{}\\night-{}", cfg.data_dir.trim_end_matches('\\'), night_label)
    };
    if std::path::Path::new(&dir).exists() {
        eprintln!("pilot-night: {} exists; a night's records are never overwritten", dir);
        return 1;
    }
    let out = match Out::open(&dir) {
        Ok(o) => o,
        Err(e) => {
            eprintln!("pilot-night: {}", e);
            return 3;
        }
    };
    let sensors = match Sensors::open() {
        Ok(s) => s,
        Err(e) => {
            eprintln!("pilot-night: sensors: {}", e);
            return 3;
        }
    };
    let plant_exe = opts.plant_exe.clone().unwrap_or_else(|| std::path::Path::new(&cfg.run_types[0].harness).with_file_name("x4plant.exe").display().to_string());
    // revision 4: pin first, so the pre-start items, the self-test and every child they start run on
    // the orchestrator's reserved LP (the self-test's job gets the run type's own mask)
    if let Err(e) = sw::pin_own_process(1u64 << cfg.orchestrator_lp) {
        eprintln!("pilot-night: {}", e);
        return 3;
    }
    // ---- pre-start (night refusal)
    let strict = cfg.grade == Grade::Pilot;
    let mut items = prestart_items(cfg, &sensors, strict);
    if strict || cfg.probe_exe.is_some() {
        let m = selftest_mode(cfg);
        items.push(item("selftest mode is degraded-job-only", matches!(&m, Ok(x) if x == "degraded-job-only"), format!("{:?}", m)));
    }
    // ---- progress across nights (section 6): the started set, interrupted sessions, integrity stops,
    // and the pins every earlier session ran with
    let progress_path = format!("{}\\progress.txt", if opts.dry { dir.clone() } else { cfg.data_dir.trim_end_matches('\\').to_string() });
    let progress = parse_progress(&std::fs::read_to_string(&progress_path).unwrap_or_default());
    let me_sha = std::env::current_exe().ok().and_then(|p| file_sha256(&p.display().to_string()).ok()).unwrap_or_default();
    let harness_sha: Vec<String> = cfg.run_types.iter().map(|r| file_sha256(&r.harness).unwrap_or_default()).collect();
    let uncleared: Vec<String> = progress.integrity_stops().into_iter().filter(|s| cfg.integrity_cleared_for(s).is_none()).collect();
    items.push(item("no uncleared integrity stop in progress.txt (cleared only by a dated amendment: integrity_cleared)", uncleared.is_empty(), format!("{:?}", uncleared)));
    let foreign: Vec<String> = progress
        .pins
        .iter()
        .filter(|(sid, seed, h, x)| {
            let rt = cfg.schedule().iter().find(|s| &s.id == sid).map(|s| s.run_type);
            seed != &cfg.seed_hex || x != &me_sha || rt.map_or(true, |i| h != &harness_sha[i])
        })
        .map(|(s, ..)| s.clone())
        .collect();
    items.push(item("progress.txt sessions ran with tonight's seed and binaries (a pinned-hash change is a restart in a new data_dir)", foreign.is_empty(), format!("{:?}", foreign)));
    let rate = sandbox::calibrate_cycle_rate();
    let cores = sw::topology().map(|t| t.cores).unwrap_or_default();
    let ctx = Ctx {
        night: night_label.clone(),
        grade: cfg.grade,
        clock,
        sensors,
        rate,
        own_pid: sw::own_pid(),
        window,
        cores,
        out: RefCell::new(out),
        seq: Cell::new(0),
        salt: Cell::new(rate ^ (real_now.to_bits())),
        plant: RefCell::new(PlantState { kind: PlantKind::None, exe: plant_exe, dir: format!("{}\\plant", dir), checks: 0, reads: 0, note: String::new(), affinity: cfg.plant_affinity }),
        poller: Poller::start(proc_filter(cfg)),
        last_load_end: Cell::new(None),
        gpu_query_before_load: Cell::new(false),
        job_cpu_100ns: Cell::new(0),
        prev_run: Cell::new(None),
    };
    println!("== X4 noise-pilot night [{}] {} -> {}", cfg.grade.label(), night_label, dir);
    println!("window {} .. last end {} .. end {}{}", pilotcfg::pt_string(window.0 as i64), pilotcfg::pt_string(window.1 as i64), pilotcfg::pt_string(window.2 as i64), if opts.dry { " (virtual clock)" } else { "" });
    println!("orchestrator pinned to LP {}; cycle rate {} Hz; process poller every {} ms", cfg.orchestrator_lp, rate, POLL_MS);

    let mut refused = Vec::new();
    for it in &items {
        println!("  [{}] {} -- {}", if it.ok { " ok " } else if strict && it.required { "FAIL" } else { "note" }, it.name, it.detail);
        if !it.ok && it.required {
            refused.push(it.name.clone());
        }
        ctx.void_line(if it.ok { "PRESTART-OK" } else { "PRESTART-FAIL" }, "-", &format!("{} -- {}", it.name, it.detail));
    }
    // structural items refuse a dry run too: the harness must exist
    let structural = items.iter().any(|i| !i.ok && i.name.contains("harness present"));
    if (strict && !refused.is_empty()) || structural {
        println!("night refused: {:?}", refused);
        write_manifest(&ctx, cfg, cfg_path, &cfg_sha, &progress_path, "refused", &refused.join("; "));
        return 1;
    }
    // sessions started on an earlier night and never ended (a crash, a restart, a power loss): a
    // hygiene void, written as `interrupted`, never re-run (section 6)
    for s in progress.interrupted() {
        println!("  session {} was started and never ended: recorded as interrupted (not re-run)", s);
        if let Err(e) = append_synced(&progress_path, &format!("{} interrupted {} {}", s, ctx.grade.label(), night_label)) {
            eprintln!("progress: {}", e);
            return 3;
        }
        ctx.void_line("VOID-LOGGED", &s, "reason=interrupted (started on an earlier night, no end line)");
    }

    // ---- goldens: pinned, or learned by one dry run per run type (DRY-RUN only)
    let mut goldens: Vec<[u64; 4]> = Vec::new();
    for rt in &cfg.run_types {
        match &rt.golden {
            Some(g) => goldens.push(sha256::parse_hex_u64x4(g).expect("validated")),
            None => {
                let scratch_run = format!("{}\\run", cfg.scratch.trim_end_matches('\\'));
                let env = match runenv::build(&std::env::var("SystemRoot").unwrap_or_else(|_| "C:\\Windows".into()), &scratch_run, &rt.env) {
                    Ok(e) => e,
                    Err(e) => {
                        eprintln!("env: {}", e);
                        return 3;
                    }
                };
                let (_, o, _) = one_run(&ctx, rt, &env, &scratch_run, &ceilings_of(rt, rate), [0; 4], "golden-learn", "A", 0);
                match o.ok().and_then(|o| o.observed.hash_at_exit) {
                    Some(h) => {
                        println!("  [{}] learned golden {} (dry only)", rt.id, sha256::hex_u64x4(&h));
                        goldens.push(h);
                    }
                    None => {
                        eprintln!("  [{}] could not learn a golden", rt.id);
                        return 3;
                    }
                }
            }
        }
    }

    // ---- the schedule
    let sched: Vec<PlannedSession> = cfg.schedule();
    let mut done: Vec<String> = parse_progress(&std::fs::read_to_string(&progress_path).unwrap_or_default()).started;
    let mut ran = 0usize;
    let mut code = 0;
    loop {
        if opts.max_sessions.map_or(false, |m| ran >= m) {
            break;
        }
        let now = ctx.clock.now();
        let next = sched.iter().find(|s| !done.contains(&s.id) && now + cfg.planned_secs(&cfg.run_types[s.run_type]) <= window.1);
        let s = match next {
            Some(s) => s.clone(),
            None => break,
        };
        let rt = &cfg.run_types[s.run_type];
        println!("-- session {} ({}) at {}", s.id, rt.id, pilotcfg::pt_string(now as i64));
        // the started line, synced before the first run (revision 4): a session killed mid-way is
        // never re-run with the same seed
        if let Err(e) = append_synced(&progress_path, &format!("{} started {} {} seed={} harness={} x4svc={}", s.id, ctx.grade.label(), night_label, cfg.seed_hex, harness_sha[s.run_type], me_sha)) {
            eprintln!("progress: {}", e);
            code = 3;
            break;
        }
        done.push(s.id.clone());
        let res = match run_session_for(&ctx, cfg, rt, &s.id, s.seed, rt.blocks as usize, goldens[s.run_type]) {
            Ok(r) => r,
            Err(e) => {
                eprintln!("session {}: {}", s.id, e);
                code = 3;
                break;
            }
        };
        let (end, reason) = end_label(&res.end);
        println!("   {} blocks, {} discards, end {} {}", res.blocks.len(), res.discards.len(), end, reason);
        if let Err(e) = append_synced(&progress_path, &format!("{} {} {} {}", s.id, end, ctx.grade.label(), night_label)) {
            eprintln!("progress: {}", e);
            code = 3;
            break;
        }
        ran += 1;
        if let SessionEnd::IntegrityStop { .. } = res.end {
            println!("INTEGRITY FAILURE: the pilot stops here (an evaluator bug until fixed; never re-run silently; later nights refuse until a dated amendment clears it)");
            code = 4;
        }
        write_manifest(&ctx, cfg, cfg_path, &cfg_sha, &progress_path, if code == 4 { "stopped" } else { "open" }, "");
        if code == 4 {
            break;
        }
    }
    let remaining: Vec<&str> = sched.iter().filter(|s| !done.contains(&s.id)).map(|s| s.id.as_str()).collect();
    println!("night over at {}: {} sessions run tonight; {} unrun: {:?}", pilotcfg::pt_string(ctx.clock.now() as i64), ran, remaining.len(), remaining);
    if code == 0 && !remaining.is_empty() {
        let now = ctx.clock.now();
        if let Some(s) = sched.iter().find(|s| !done.contains(&s.id)) {
            println!("start rule: the next unrun session {} needs {:.0} s; {} + that > last end {}", s.id, cfg.planned_secs(&cfg.run_types[s.run_type]), pilotcfg::pt_string(now as i64), pilotcfg::pt_string(window.1 as i64));
        }
    }

    // ---- planted triggers (DRY-RUN only)
    if opts.dry && opts.plants && code == 0 {
        if let Err(e) = plant_suite(&ctx, cfg, &goldens) {
            eprintln!("plants: {}", e);
            code = 3;
        }
    }
    write_manifest(&ctx, cfg, cfg_path, &cfg_sha, &progress_path, if code == 0 { "closed" } else { "stopped" }, "");
    code
}

fn write_manifest(ctx: &Ctx, cfg: &PilotConfig, cfg_path: &str, cfg_sha: &str, progress_path: &str, status: &str, note: &str) {
    let dir = ctx.out.borrow().dir.clone();
    let own = sw::own_process();
    let mut lines = vec![
        format!("grade={}", cfg.grade.label()),
        format!("status={}", status),
        format!("note={}", note),
        format!("night={}", ctx.night),
        format!("record={}", cfg.record),
        format!("freeze_commit={}", cfg.freeze_commit.clone().unwrap_or_else(|| "none".into())),
        format!("signed_tag={} (name only: the driver does not verify the signature; record section 10)", cfg.signed_tag.clone().unwrap_or_else(|| "none".into())),
        format!("seed={}", cfg.seed_hex),
        format!("config={} sha256={}", cfg_path, cfg_sha),
        format!("cycle_rate_hz={}", ctx.rate),
        format!("process_poll_ms={}", POLL_MS),
        format!(
            "driver_priority_class={} memory_priority={} elevated={} integrity_rid={}",
            own.priority_class.map(|x| format!("{:#x}", x)).unwrap_or_else(|| "unreadable".into()),
            own.memory_priority.map(|x| x.to_string()).unwrap_or_else(|| "unreadable".into()),
            own.elevated.map(|x| x.to_string()).unwrap_or_else(|| "unreadable".into()),
            own.integrity_rid.map(|x| format!("{:#x}", x)).unwrap_or_else(|| "unreadable".into())
        ),
        format!("written_utc={:.3}", utc_now()),
    ];
    for rt in &cfg.run_types {
        lines.push(format!("harness[{}]={} sha256={}", rt.id, rt.harness, file_sha256(&rt.harness).unwrap_or_else(|e| e)));
    }
    if let Ok(me) = std::env::current_exe() {
        lines.push(format!("x4svc={} sha256={}", me.display(), file_sha256(&me.display().to_string()).unwrap_or_else(|e| e)));
    }
    // the void log first, then every record file and progress.txt (section 10: hashed before any
    // estimator runs; rewritten after every session, so a killed driver leaves a manifest too)
    for f in ["voids.log", "runs.jsonl", "blocks.jsonl", "sessions.jsonl", "sensors.jsonl", "plants.jsonl"] {
        let p = format!("{}\\{}", dir, f);
        lines.push(format!("sha256[{}]={}", f, file_sha256(&p).unwrap_or_else(|e| e)));
    }
    lines.push(format!("sha256[progress.txt]={} ({})", file_sha256(progress_path).unwrap_or_else(|e| e), progress_path));
    let _ = std::fs::write(format!("{}\\manifest.txt", dir), lines.join("\n") + "\n");
}

// ------------------------------------------------------------------------- planted triggers

fn plant_suite(ctx: &Ctx, cfg: &PilotConfig, goldens: &[[u64; 4]]) -> Result<(), String> {
    println!("== planted triggers (DRY-RUN): each a 2-block session of {}", cfg.run_types[0].id);
    let rt = &cfg.run_types[0];
    // firing thresholds for the plants: the record's values, except where a plant needs a threshold it
    // can reach within this track's 3-thread budget (load, NVMe); background images, the GPU and the
    // run core stay relaxed in sessions whose plant is not about them, because daytime GEMS/Defender
    // activity would otherwise confound every row.
    let base_load = ctx.sensors.load_sample(1000).sys_total_pct.unwrap_or(0.0);
    let base_write = ctx.sensors.disk_sample(cfg.disk_window_ms).1.unwrap_or(-1.0);
    println!("  baselines: machine load {:.2}%, disk writes {:.0} B/s, NVMe {:?}", base_load, base_write, sw::nvme_temp_c(cfg.nvme_volume));
    let temp_now = sw::nvme_temp_c(cfg.nvme_volume).ok();
    let kinds = [
        PlantKind::None,
        PlantKind::Excluded,
        PlantKind::Started,
        PlantKind::Mithril,
        PlantKind::Load,
        PlantKind::CoreLoad,
        PlantKind::Writes,
        PlantKind::Nvme,
        PlantKind::Defender,
        PlantKind::Input,
        PlantKind::Session,
        PlantKind::Gpu,
        PlantKind::Scheme,
        PlantKind::Cut,
        PlantKind::Integrity,
    ];
    let mut all_ok = true;
    for (i, &k) in kinds.iter().enumerate() {
        let mut c = cfg.clone();
        c.load_max_pct = 100.0;
        c.core_load_max_pct = 100.0;
        // MsMpEng above one full core over a dry block was seen [M, dry run 2026-10-23]
        c.bg_cpu_max_pct_of_core = 1e9;
        c.gpu_util_max_pct = 101.0;
        c.nvme_temp_max_c = 200.0;
        c.disk_write_max_bytes_s = 1e15;
        c.disk_queue_max = 1e9;
        c.settle_timeout_s = 2;
        let expect: &str = match k {
            PlantKind::None => "completed",
            PlantKind::Excluded => "excluded process started: x4plant_gems",
            PlantKind::Started => "excluded process started: x4plant_shell",
            PlantKind::Mithril => "another Mithril measurement process",
            PlantKind::Load => {
                // a 1-s window: shorter ones quantise per-LP load to clock ticks (15.6 ms) [M, dry run]
                c.load_window_ms = 1000;
                c.load_max_pct = base_load + 4.0;
                "2-s CPU load"
            }
            PlantKind::CoreLoad => {
                c.load_window_ms = 1000;
                c.core_load_max_pct = 10.0;
                "run core busy"
            }
            PlantKind::Writes => {
                c.disk_write_max_bytes_s = 1_048_576.0;
                c.disk_queue_max = 0.0;
                "start state not reached"
            }
            PlantKind::Nvme => {
                if let Some(t) = temp_now {
                    c.nvme_temp_max_c = t - 1.0;
                }
                "NVMe temperature"
            }
            PlantKind::Defender => {
                c.bg_cpu_max_pct_of_core = 1.0;
                "msmpeng"
            }
            PlantKind::Input => "interactive input",
            PlantKind::Session => "session 99",
            PlantKind::Gpu => {
                // the injected 50% at check 2, or a real reading above 5% earlier (GEMS in daytime):
                // either shows the sensor-to-void path; the reason line says which
                c.gpu_util_max_pct = 5.0;
                "GPU utilisation"
            }
            PlantKind::Scheme => "power scheme changed",
            PlantKind::Cut => "session cut",
            PlantKind::Integrity => "golden_hash",
        };
        {
            let mut p = ctx.plant.borrow_mut();
            p.kind = k;
            p.checks = 0;
            p.reads = 0;
            p.note.clear();
        }
        let golden = if k == PlantKind::Integrity { [1, 2, 3, 4] } else { goldens[0] };
        let id = format!("plant-{:02}-{:?}", i, k).to_lowercase();
        if k == PlantKind::Cut {
            ctx.clock.set(ctx.window.2 - 30.0 - c.session_setup_s);
        } else {
            ctx.clock.set(ctx.window.0);
        }
        let res = run_session_for(ctx, &c, rt, &id, 0x5eed_0000 + i as u64, 2, golden)?;
        // the detached plants live 1 s; let every planted process finish before the next row
        std::thread::sleep(Duration::from_millis(1500));
        let (end, reason) = end_label(&res.end);
        let discards = res.discard_reasons.join(" | ");
        let observed = format!("end={} reason={} discards={}", end, reason, discards);
        let ok = if k == PlantKind::None { end == "completed" && res.discards.is_empty() } else { observed.contains(expect) };
        all_ok &= ok;
        let note = ctx.plant.borrow().note.clone();
        println!("  [{}] {:<78} expect {:?}: {}", if ok { "FIRED" } else if k == PlantKind::None { "FAIL " } else { "MISS " }, k.label(), expect, observed);
        wl(
            &mut ctx.out.borrow_mut().plants,
            &format!(
                "{{\"grade\":\"DRY-RUN\",\"plant\":{},\"label\":{},\"expect\":{},\"ok\":{},\"end\":{},\"reason\":{},\"discards\":{},\"note\":{},\"threshold_load_pct\":{:.3},\"threshold_core_pct\":{:.1},\"threshold_nvme_c\":{:.1},\"baseline_load_pct\":{:.3}}}",
                jstr(&format!("{:?}", k)),
                jstr(k.label()),
                jstr(expect),
                ok,
                jstr(end),
                jstr(&reason),
                jstr(&discards),
                jstr(&note),
                c.load_max_pct,
                c.core_load_max_pct,
                c.nvme_temp_max_c,
                base_load
            ),
        );
    }
    {
        let mut p = ctx.plant.borrow_mut();
        p.kind = PlantKind::None;
    }
    // the start rule, checked without running: at 06:44 PT nothing of the schedule fits
    let at = ctx.window.1 - 60.0;
    let fits = cfg.run_types.iter().any(|rt| at + cfg.planned_secs(rt) <= ctx.window.1);
    println!("  [{}] start rule at {}: a session starts only if blocks x 4 x (t_run x c + o_rt) + setup ends by {}: fits={}", if !fits { "HELD " } else { "MISS " }, pilotcfg::pt_string(at as i64), pilotcfg::pt_string(ctx.window.1 as i64), fits);
    all_ok &= !fits;
    println!("planted triggers: {}", if all_ok { "every tier fired as expected" } else { "SOME DID NOT FIRE (see above)" });
    if all_ok {
        Ok(())
    } else {
        Err("a planted trigger did not fire".into())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn progress_lines_started_ended_interrupted_and_pins() {
        let t = "mb-q4-avx512-03 started PILOT 2026-10-25 seed=abc harness=h1 x4svc=x1\n\
                 mb-q4-avx512-03 completed PILOT 2026-10-25\n\
                 e2e-decode-01 started PILOT 2026-10-25 seed=abc harness=h2 x4svc=x1\n\
                 mb-q4-avx512-07 started PILOT 2026-10-26 seed=abc harness=h1 x4svc=x1\n\
                 mb-q4-avx512-07 integrity_stop PILOT 2026-10-26\n\
                 mb-q4-avx512-09 hygiene_void PILOT 2026-10-24\n";
        let p = parse_progress(t);
        assert_eq!(p.started, vec!["mb-q4-avx512-03", "e2e-decode-01", "mb-q4-avx512-07", "mb-q4-avx512-09"]);
        assert_eq!(p.interrupted(), vec!["e2e-decode-01".to_string()]);
        assert_eq!(p.integrity_stops(), vec!["mb-q4-avx512-07".to_string()]);
        assert_eq!(p.pins[1], ("e2e-decode-01".to_string(), "abc".to_string(), "h2".to_string(), "x1".to_string()));
    }
}
