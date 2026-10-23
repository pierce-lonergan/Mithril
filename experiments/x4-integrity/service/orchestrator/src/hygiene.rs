//! The noise pilot's hygiene rules (docs/m0/prereg/X4-noise-pilot.md section 10; MEASUREMENT-SERVICE
//! sections 4.1, 5.3; X4 pilot track, 2026-10-23): three tiers, each decided by a function whose
//! inputs are sensor readings only. No function here receives a run time, a block statistic d or any
//! e-process wealth, so no discard or void can select on outcomes (blindness).
//!
//! - Night refusal (pre-start only): `night_refusals` -- any failing item and no session starts.
//! - Block discard: the pre-run gate (2-s CPU load, the start state: disk queue 0 and writes at most
//!   1 MiB/s, waited for up to 60 s; revision 4: the run core's LPs each at most 10% for a one-LP run
//!   type, `core_quiet`) through `scheduler::LoadGate`, and `bg_discard` (Defender, indexer, Windows
//!   Update servicing and idle-maintenance CPU above 1% of one core over the *planned* block time).
//! - Session hygiene void: `session_void` against the session-start baseline (interactive input, a
//!   new console/RDP session, an excluded process starting or using CPU, a started-only image
//!   starting, another Mithril job, GPU utilisation, NVMe temperature at a block start, a power-scheme
//!   change; the window cut is the driver's).
//!
//! Revision 4 (review 2026-10-23): the process lists these rules read are the union of every process
//! a 250-ms poller saw since the baseline (block start), not two endpoint snapshots, so a process that
//! starts and exits between checks, or exits mid-block, is counted up to its last poll. A process is
//! identified by pid, image and creation time (pid reuse); the driver's own children (parent pid) are
//! exempt. The bg denominator is the planned block time, a constant per run type, so slower blocks
//! (which contain run times) are never less likely to be discarded.
//!
//! Sensors are read by `sensors_win` (Windows, read-only documented interfaces). A sensor that cannot
//! be read is `None`; in a PILOT night every sensor must be readable at the start (a refusal) and a
//! later unreadable sample voids the session (fail closed); a DRY-RUN records it.

use crate::pilotcfg::{Grade, PilotConfig};
use crate::scheduler::GateReading;

/// One process as the sensors see it.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct ProcSample {
    pub pid: u32,
    /// Image name, lower case, without ".exe".
    pub image: String,
    /// QueryProcessCycleTime, or None when the process could not be opened for query.
    pub cycles: Option<u64>,
    /// Parent pid (Toolhelp), to exempt the driver's own children.
    pub parent: u32,
    /// Creation time (GetProcessTimes, 100 ns FILETIME), to tell a reused pid from the same process.
    pub created: Option<u64>,
    /// Revision 5 (review round 5): the process's kernel + user time in 100 ns from the PDH
    /// `\Process(*)\% Processor Time` raw value, read only when the process cannot be opened (a
    /// non-elevated driver cannot open Defender, the indexer or other SYSTEM services [M]); its
    /// creation time then comes from `\Process(*)\Elapsed Time`. Tick-based (15.6 ms quanta).
    pub cpu_100ns: Option<u64>,
}

impl ProcSample {
    /// The same process (pid, image and, when both are known, creation time).
    pub fn same(&self, o: &ProcSample) -> bool {
        self.pid == o.pid && self.image == o.image && (self.created.is_none() || o.created.is_none() || self.created == o.created)
    }
    /// Whether any CPU reading exists (cycles, or the PDH time of an unopenable process).
    pub fn cpu_readable(&self) -> bool {
        self.cycles.is_some() || self.cpu_100ns.is_some()
    }
}

/// CPU a process used since `then` (the same process earlier, or None if it was not there), in
/// cycles at `rate_hz`: from the cycle counts when the process could be opened, else from the PDH time
/// (100 ns) converted at the calibrated rate. None = unreadable now, or readable only by the other
/// source then (fail closed: the caller counts it as unknown).
pub fn cpu_cycles_since(now: &ProcSample, then: Option<&ProcSample>, rate_hz: u64) -> Option<u64> {
    if let Some(c) = now.cycles {
        return match then {
            None => Some(c),
            Some(t) => match t.cycles {
                Some(tc) => Some(c.saturating_sub(tc)),
                None => None,
            },
        };
    }
    let t100 = now.cpu_100ns?;
    let d = match then {
        None => t100,
        Some(t) => t100.saturating_sub(t.cpu_100ns?),
    };
    Some((d as u128 * rate_hz as u128 / 10_000_000u128) as u64)
}

/// Merge a newer reading into a union of every process seen: update the cycles of a process already
/// held (a cycle count never decreases; a missing reading keeps the last one), append a new one.
pub fn merge_seen(seen: &mut Vec<ProcSample>, now: &[ProcSample]) {
    for p in now {
        match seen.iter_mut().find(|s| s.same(p)) {
            Some(s) => {
                if let Some(c) = p.cycles {
                    s.cycles = Some(s.cycles.map_or(c, |o| o.max(c)));
                }
                if let Some(c) = p.cpu_100ns {
                    s.cpu_100ns = Some(s.cpu_100ns.map_or(c, |o| o.max(c)));
                }
                if s.created.is_none() {
                    s.created = p.created;
                }
            }
            None => seen.push(p.clone()),
        }
    }
}

/// Normalise an image or list entry: lower case, no ".exe".
pub fn norm_image(s: &str) -> String {
    let l = s.trim().to_ascii_lowercase();
    l.strip_suffix(".exe").map(|x| x.to_string()).unwrap_or(l)
}
pub fn image_in(image: &str, list: &[String]) -> bool {
    let i = norm_image(image);
    list.iter().any(|x| norm_image(x) == i)
}

/// A session-level snapshot (taken at the session start as the baseline, then before every run and
/// after every block).
#[derive(Clone, Debug, Default, PartialEq)]
pub struct SessionSense {
    /// GetLastInputInfo tick of the session this process runs in (None: unavailable).
    pub input_tick: Option<u32>,
    /// Whether this process runs in the active console session (GetLastInputInfo sees only its own
    /// session's input).
    pub in_console_session: Option<bool>,
    /// WTS sessions: (id, station name, state); state 0 = WTSActive.
    pub sessions: Option<Vec<(u32, String, u32)>>,
    pub procs: Vec<ProcSample>,
    pub gpu_util_pct: Option<f64>,
    pub nvme_temp_c: Option<f64>,
    pub scheme_guid: Option<String>,
}

fn cyc_to_pct_core(cycles: u64, wall_ns: u64, rate_hz: u64) -> f64 {
    if wall_ns == 0 || rate_hz == 0 {
        return f64::INFINITY;
    }
    cycles as f64 / (wall_ns as f64 / 1e9 * rate_hz as f64) * 100.0
}

/// CPU cycles each listed image used over a block: `before` = the processes alive at the block start,
/// `seen` = every process seen during the block (the poller's union, exited ones included, with their
/// last cycle count). A process absent at the start contributes all its cycles; one that could not
/// be queried counts as unknown. Revision 5: a process that cannot be opened is charged its PDH time
/// at the calibrated rate (`cpu_cycles_since`).
pub fn image_cycles(before: &[ProcSample], seen: &[ProcSample], image: &str, rate_hz: u64) -> Option<u64> {
    let mut total = 0u64;
    for a in seen.iter().filter(|p| norm_image(&p.image) == norm_image(image)) {
        let then = before.iter().find(|b| b.same(a));
        total = total.saturating_add(cpu_cycles_since(a, then, rate_hz)?);
    }
    Some(total)
}

/// Block discard on background activity over the block (Defender, indexer, Windows Update servicing,
/// idle maintenance): any listed image above `bg_cpu_max_pct_of_core` of one core over the run type's
/// **planned** block time `planned_block_ns` (revision 4: a fixed cycle budget per run type, never the
/// observed block time, which contains the run times).
pub fn bg_discard(cfg: &PilotConfig, before: &[ProcSample], seen: &[ProcSample], planned_block_ns: u64, rate_hz: u64) -> Option<String> {
    let mut hits = Vec::new();
    for img in &cfg.bg_images {
        match image_cycles(before, seen, img, rate_hz) {
            Some(c) => {
                let pct = cyc_to_pct_core(c, planned_block_ns, rate_hz);
                if pct > cfg.bg_cpu_max_pct_of_core {
                    hits.push(format!("{} {:.3}% of one core over the planned block", norm_image(img), pct));
                }
            }
            None => hits.push(format!("{} CPU unreadable", norm_image(img))),
        }
    }
    if hits.is_empty() {
        None
    } else {
        Some(format!("background activity over the block: {}", hits.join(", ")))
    }
}

/// The run core rule (revision 4; record section 3 "its SMT sibling idle"): for a run type whose job
/// mask is one LP, every LP of `core_mask` (that LP and its SMT sibling) must be at most `max_pct`
/// busy over the 2-s window. A missing per-LP reading fails closed when `strict` (PILOT), as every
/// other sensor; a dry run records it. Returns the failing LPs.
pub fn core_quiet(per_lp_pct: &[(String, f64)], core_mask: u64, max_pct: f64, strict: bool) -> Result<(), String> {
    let mut bad = Vec::new();
    for lp in (0..64u32).filter(|b| core_mask >> b & 1 == 1) {
        match per_lp_pct.iter().find(|(n, _)| n.parse::<u32>().ok() == Some(lp)) {
            Some((_, x)) if *x <= max_pct => {}
            Some((_, x)) => bad.push(format!("LP {} {:.1}%", lp, x)),
            None if strict => bad.push(format!("LP {} unreadable", lp)),
            None => {}
        }
    }
    if bad.is_empty() {
        Ok(())
    } else {
        Err(bad.join(", "))
    }
}

/// The start state of MEASUREMENT 4.1 (absolute items only in the pilot): disk queue 0 (an integer
/// count; `disk_queue_max` 0 in the record) and the write rate at most `disk_write_max_bytes_s` over
/// the sample window.
pub fn start_state_ok(cfg: &PilotConfig, queue: Option<f64>, write_bps: Option<f64>) -> bool {
    matches!((queue, write_bps), (Some(q), Some(w)) if q < cfg.disk_queue_max + 0.5 && w <= cfg.disk_write_max_bytes_s)
}

/// The pre-run gate reading: an unreadable load fails closed (100%). `run_core_quiet` is the
/// `core_quiet` verdict (true for a run type whose mask is wider than one LP).
pub fn gate_reading(load_2s_pct: Option<f64>, start_state: bool, in_window: bool, profile_ok: bool, run_core_quiet: bool) -> GateReading {
    GateReading {
        profile_hash_matches: profile_ok,
        quiet_window_active: in_window,
        cpu_load_2s_pct: load_2s_pct.unwrap_or(100.0),
        background_idle: true, // judged over the block by bg_discard
        nvme_temp_ok: true,    // a session void at a block start (session_void)
        no_large_writes: start_state,
        run_core_quiet,
    }
}

/// Session hygiene void against the baseline. `now.procs` is every process seen since the baseline
/// (the poller's union) merged with a fresh snapshot. `own_pids` are this orchestrator's processes;
/// a process whose parent is one of them (the harness child, nvidia-smi, powercfg, the profile's
/// PowerShell query) is the driver's own and exempt. `block_start` marks the check made before the
/// first run of a block (the NVMe temperature rule applies there). Fail-closed on an unreadable
/// sensor in a PILOT night.
pub fn session_void(cfg: &PilotConfig, base: &SessionSense, now: &SessionSense, own_pids: &[u32], rate_hz: u64, block_start: bool) -> Option<String> {
    let strict = cfg.grade == Grade::Pilot;
    let own = |p: &ProcSample| own_pids.contains(&p.pid) || own_pids.contains(&p.parent);
    let mut why: Vec<String> = Vec::new();
    match (base.input_tick, now.input_tick) {
        (Some(a), Some(b)) if a != b => why.push(format!("interactive input (last-input tick {} -> {})", a, b)),
        (_, None) | (None, _) if strict => why.push("input sensor unavailable".into()),
        _ => {}
    }
    match (&base.sessions, &now.sessions) {
        (Some(b), Some(n)) => {
            for s in n {
                let known = b.iter().any(|x| x.0 == s.0 && x.1 == s.1);
                let became_active = s.2 == 0 && b.iter().any(|x| x.0 == s.0 && x.2 != 0);
                if !known || became_active {
                    why.push(format!("new or newly active session {} '{}' (state {})", s.0, s.1, s.2));
                }
            }
        }
        _ if strict => why.push("session list unavailable".into()),
        _ => {}
    }
    let thr_cycles = (cfg.excluded_cpu_max_ms / 1000.0 * rate_hz as f64) as u64;
    for p in now.procs.iter().filter(|p| image_in(&p.image, &cfg.excluded_images) && !own(p)) {
        match base.procs.iter().find(|b| b.same(p)) {
            None => why.push(format!("excluded process started: {} (pid {})", p.image, p.pid)),
            Some(b) => match (b.cycles, p.cycles, b.cpu_100ns, p.cpu_100ns) {
                (Some(x), Some(y), _, _) if y.saturating_sub(x) > thr_cycles => {
                    why.push(format!("excluded process used CPU: {} (pid {}, {} cycles)", p.image, p.pid, y - x))
                }
                (Some(_), Some(_), _, _) => {}
                // revision 5: a process the driver cannot open is read through PDH (100 ns, tick-based)
                (None, None, Some(x), Some(y)) if (y.saturating_sub(x) as f64) > cfg.excluded_cpu_max_ms * 1e4 => {
                    why.push(format!("excluded process used CPU: {} (pid {}, {} x 100 ns, PDH)", p.image, p.pid, y - x))
                }
                (None, None, Some(_), Some(_)) => {}
                _ if strict => why.push(format!("excluded process {} (pid {}) unreadable", p.image, p.pid)),
                _ => {}
            },
        }
    }
    // started-only images (revision 4): a remote login (sshd), an agent's or a task's shell
    for p in now.procs.iter().filter(|p| image_in(&p.image, &cfg.excluded_started_images) && !own(p)) {
        if !base.procs.iter().any(|b| b.same(p)) {
            why.push(format!("excluded process started: {} (pid {}, parent {})", p.image, p.pid, p.parent));
        }
    }
    for p in &now.procs {
        let i = norm_image(&p.image);
        if (i.starts_with("x4svc") || i.starts_with("x4harness")) && !own(p) {
            why.push(format!("another Mithril measurement process: {} (pid {})", p.image, p.pid));
        }
    }
    match now.gpu_util_pct {
        Some(g) if g > cfg.gpu_util_max_pct => why.push(format!("GPU utilisation {:.0}% > {:.0}%", g, cfg.gpu_util_max_pct)),
        None if strict => why.push("GPU utilisation unavailable".into()),
        _ => {}
    }
    if block_start {
        match now.nvme_temp_c {
            Some(t) if t >= cfg.nvme_temp_max_c => why.push(format!("NVMe temperature {:.0} C >= {:.0} C at a block start", t, cfg.nvme_temp_max_c)),
            None if strict => why.push("NVMe temperature unavailable".into()),
            _ => {}
        }
    }
    if base.scheme_guid != now.scheme_guid {
        why.push(format!("active power scheme changed ({:?} -> {:?})", base.scheme_guid, now.scheme_guid));
    }
    if why.is_empty() {
        None
    } else {
        Some(why.join("; "))
    }
}

/// One pre-start item.
#[derive(Clone, Debug, PartialEq)]
pub struct NightItem {
    pub name: String,
    pub ok: bool,
    /// A failing required item refuses the night; an advisory one is reported only (for example an
    /// excluded process that is running: the record voids only when it starts or uses CPU).
    pub required: bool,
    pub detail: String,
}

/// Night refusal: the required pre-start items that fail (an empty list = the night may start).
pub fn night_refusals(items: &[NightItem]) -> Vec<&NightItem> {
    items.iter().filter(|i| !i.ok && i.required).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::pilotcfg::{parse, tests::DRY};

    fn p(pid: u32, image: &str, cycles: u64) -> ProcSample {
        ProcSample { pid, image: image.into(), cycles: Some(cycles), ..Default::default() }
    }
    fn base() -> SessionSense {
        SessionSense {
            input_tick: Some(100),
            in_console_session: Some(true),
            sessions: Some(vec![(1, "Console".into(), 0), (0, "Services".into(), 4)]),
            procs: vec![p(10, "claude", 1_000), p(20, "msmpeng", 5_000), p(30, "x4svc", 1)],
            gpu_util_pct: Some(0.0),
            nvme_temp_c: Some(45.0),
            scheme_guid: Some("g".into()),
        }
    }
    fn pilot_cfg() -> PilotConfig {
        let mut c = parse(DRY).unwrap();
        c.grade = Grade::Pilot;
        c
    }

    #[test]
    fn a_quiet_session_is_not_voided() {
        let c = parse(DRY).unwrap();
        assert_eq!(session_void(&c, &base(), &base(), &[30], 4_000_000_000, true), None);
        assert_eq!(session_void(&pilot_cfg(), &base(), &base(), &[30], 4_000_000_000, true), None);
    }

    #[test]
    fn each_session_trigger_fires_alone() {
        let c = parse(DRY).unwrap();
        let fire = |f: &dyn Fn(&mut SessionSense)| {
            let mut n = base();
            f(&mut n);
            session_void(&c, &base(), &n, &[30], 4_000_000_000, true).unwrap_or_default()
        };
        assert!(fire(&|n| n.input_tick = Some(101)).contains("interactive input"));
        assert!(fire(&|n| n.sessions.as_mut().unwrap().push((3, "RDP-Tcp#0".into(), 0))).contains("session 3"));
        assert!(fire(&|n| n.procs[0].cycles = Some(1_001)).contains("excluded process used CPU: claude"));
        assert!(fire(&|n| n.procs.push(p(40, "node", 0))).contains("excluded process started: node"));
        assert!(fire(&|n| n.procs.push(p(41, "x4harness_hearth", 0))).contains("another Mithril"));
        // revision 4: started-only images (DRY lists sshd) void on start, not on CPU use
        assert!(fire(&|n| n.procs.push(p(42, "sshd", 0))).contains("excluded process started: sshd"));
        // the driver's own children (parent = an own pid) are exempt: its harness, its helpers
        let own_child = |img: &str| ProcSample { pid: 43, image: img.into(), cycles: Some(9), parent: 30, created: None, cpu_100ns: None };
        for img in ["x4harness_hearth", "sshd", "node"] {
            assert_eq!(fire(&|n| n.procs.push(own_child(img))), "", "{img}");
        }
        assert!(fire(&|n| n.gpu_util_pct = Some(6.0)).contains("GPU utilisation 6%"));
        assert!(fire(&|n| n.nvme_temp_c = Some(70.0)).contains("NVMe temperature 70"));
        assert!(fire(&|n| n.scheme_guid = Some("h".into())).contains("power scheme"));
        // NVMe temperature is a block-start rule only
        let mut n = base();
        n.nvme_temp_c = Some(80.0);
        assert_eq!(session_void(&c, &base(), &n, &[30], 4_000_000_000, false), None);
        // background images are not "excluded": MsMpEng CPU is a block discard, not a void
        let mut n = base();
        n.procs[1].cycles = Some(9_000_000_000);
        assert_eq!(session_void(&c, &base(), &n, &[30], 4_000_000_000, true), None);
        // a started-only image already running at the baseline may use CPU
        let mut b = base();
        b.procs.push(p(44, "sshd", 100));
        let mut n = b.clone();
        n.procs[3].cycles = Some(9_000_000);
        assert_eq!(session_void(&c, &b, &n, &[30], 4_000_000_000, true), None);
        // pid reuse: the same pid and image with a different creation time is a new process
        let mut b = base();
        b.procs[0].created = Some(1);
        let mut n = b.clone();
        n.procs[0] = ProcSample { pid: 10, image: "claude".into(), cycles: Some(5), parent: 0, created: Some(2), cpu_100ns: None };
        assert!(session_void(&c, &b, &n, &[30], 4_000_000_000, true).unwrap().contains("excluded process started: claude"));
    }

    #[test]
    fn the_poller_union_keeps_exited_processes() {
        // a process seen once by the poller and gone at the check still counts
        let mut seen: Vec<ProcSample> = vec![p(10, "claude", 1_000)];
        merge_seen(&mut seen, &[p(10, "claude", 1_000), p(50, "cl", 10)]);
        merge_seen(&mut seen, &[p(10, "claude", 1_000)]); // cl.exe has exited
        assert_eq!(seen.len(), 2);
        merge_seen(&mut seen, &[ProcSample { pid: 10, image: "claude".into(), cycles: None, ..Default::default() }]);
        assert_eq!(seen[0].cycles, Some(1_000)); // an unreadable poll keeps the last count
        let c = parse(&DRY.replace("excluded_images = claude, node", "excluded_images = claude, node, cl")).unwrap();
        let mut n = base();
        n.procs = seen.clone();
        assert!(session_void(&c, &base(), &n, &[30], 4_000_000_000, false).unwrap().contains("excluded process started: cl"));
        // a TiWorker that exited mid-block is charged up to its last poll
        let before = vec![p(20, "msmpeng", 0)];
        let mut during = before.clone();
        merge_seen(&mut during, &[p(20, "msmpeng", 0), p(22, "TiWorker", 3_000_000_000)]);
        merge_seen(&mut during, &[p(20, "msmpeng", 0)]);
        assert!(bg_discard(&c, &before, &during, 60_000_000_000, 4_000_000_000).unwrap().contains("tiworker"));
    }

    #[test]
    fn the_run_core_rule() {
        let per = vec![("2".to_string(), 3.0), ("3".to_string(), 9.9), ("28".to_string(), 50.0)];
        assert!(core_quiet(&per, 0xc, 10.0, true).is_ok());
        assert!(core_quiet(&per, 0xc, 5.0, true).unwrap_err().contains("LP 3 9.9%"));
        assert!(core_quiet(&per, 0x3000_0000, 10.0, true).unwrap_err().contains("LP 29 unreadable")); // fail closed
        assert!(core_quiet(&per, 0x3000_0000, 100.0, false).is_ok()); // a dry run records it
        assert!(!gate_reading(Some(1.0), true, true, true, false).run_core_quiet);
    }

    #[test]
    fn unreadable_sensors_fail_closed_only_in_a_pilot() {
        let mut n = base();
        n.input_tick = None;
        n.gpu_util_pct = None;
        n.nvme_temp_c = None;
        assert_eq!(session_void(&parse(DRY).unwrap(), &base(), &n, &[30], 4_000_000_000, true), None);
        let v = session_void(&pilot_cfg(), &base(), &n, &[30], 4_000_000_000, true).unwrap();
        assert!(v.contains("input sensor unavailable") && v.contains("GPU utilisation unavailable") && v.contains("NVMe temperature unavailable"));
    }

    #[test]
    fn background_cpu_over_the_block_discards() {
        let c = parse(DRY).unwrap();
        let before = vec![p(20, "msmpeng", 0), p(21, "searchindexer", 0)];
        // a 40-s planned block at 4e9 cycles/s: 1% of one core = 1.6e9 cycles
        let quiet = vec![p(20, "msmpeng", 1_000_000_000), p(21, "searchindexer", 0)];
        assert_eq!(bg_discard(&c, &before, &quiet, 40_000_000_000, 4_000_000_000), None);
        let busy = vec![p(20, "msmpeng", 2_000_000_000), p(21, "searchindexer", 0)];
        assert!(bg_discard(&c, &before, &busy, 40_000_000_000, 4_000_000_000).unwrap().contains("msmpeng 1.250%"));
        // a TiWorker that started during the block counts in full
        let started = vec![p(20, "msmpeng", 0), p(21, "searchindexer", 0), p(22, "TiWorker", 3_000_000_000)];
        assert!(bg_discard(&c, &before, &started, 40_000_000_000, 4_000_000_000).unwrap().contains("tiworker"));
        // unreadable counts as a discard
        let unread = vec![ProcSample { pid: 20, image: "msmpeng".into(), cycles: None, ..Default::default() }];
        assert!(bg_discard(&c, &before, &unread, 40_000_000_000, 4_000_000_000).unwrap().contains("unreadable"));
    }

    #[test]
    fn an_unopenable_process_is_read_through_pdh_time() {
        // revision 5 (review round 5): a non-elevated driver cannot open MsMpEng; its PDH time counts
        let c = parse(DRY).unwrap();
        let t = |pid: u32, image: &str, t100: u64| ProcSample { pid, image: image.into(), cycles: None, cpu_100ns: Some(t100), ..Default::default() };
        let before = vec![t(20, "msmpeng", 1_000_000), p(21, "searchindexer", 0)];
        // 40-s planned block: 1% of one core = 0.4 s = 4e6 x 100 ns
        let quiet = vec![t(20, "msmpeng", 1_000_000 + 3_000_000), p(21, "searchindexer", 0)];
        assert_eq!(bg_discard(&c, &before, &quiet, 40_000_000_000, 4_000_000_000), None);
        let busy = vec![t(20, "msmpeng", 1_000_000 + 5_000_000), p(21, "searchindexer", 0)];
        assert!(bg_discard(&c, &before, &busy, 40_000_000_000, 4_000_000_000).unwrap().contains("msmpeng 1.250%"));
        // a TiWorker that cannot be opened, started and exited during the block, is charged in full
        let mut during = before.clone();
        merge_seen(&mut during, &[t(22, "TiWorker", 9_000_000)]);
        assert!(bg_discard(&c, &before, &during, 40_000_000_000, 4_000_000_000).unwrap().contains("tiworker"));
        // a reading by neither source stays unreadable (a discard)
        let none = vec![ProcSample { pid: 20, image: "msmpeng".into(), ..Default::default() }];
        assert!(bg_discard(&c, &before, &none, 40_000_000_000, 4_000_000_000).unwrap().contains("unreadable"));
        assert!(t(1, "x", 1).cpu_readable() && !ProcSample::default().cpu_readable());
        assert_eq!(cpu_cycles_since(&t(1, "x", 30), Some(&t(1, "x", 10)), 4_000_000_000), Some(8_000));
        assert_eq!(cpu_cycles_since(&t(1, "x", 30), Some(&p(1, "x", 10)), 4_000_000_000), None);
        // an excluded process read through PDH voids on any increase, and is quiet without one
        let mut b = base();
        b.procs.push(t(60, "wslhost", 500));
        let mut n = b.clone();
        assert_eq!(session_void(&pilot_cfg_with(&c, "wslhost"), &b, &n, &[30], 4_000_000_000, false), None);
        n.procs[3].cpu_100ns = Some(501);
        assert!(session_void(&pilot_cfg_with(&c, "wslhost"), &b, &n, &[30], 4_000_000_000, false).unwrap().contains("excluded process used CPU: wslhost"));
        n.procs[3].cpu_100ns = None;
        assert!(session_void(&pilot_cfg_with(&c, "wslhost"), &b, &n, &[30], 4_000_000_000, false).unwrap().contains("wslhost (pid 60) unreadable"));
    }
    fn pilot_cfg_with(c: &PilotConfig, extra: &str) -> PilotConfig {
        let mut x = c.clone();
        x.grade = Grade::Pilot;
        x.excluded_images.push(extra.to_string());
        x
    }

    #[test]
    fn start_state_and_gate_reading() {
        let c = parse(DRY).unwrap();
        assert!(start_state_ok(&c, Some(0.0), Some(1000.0)));
        assert!(!start_state_ok(&c, Some(1.0), Some(0.0)));
        assert!(!start_state_ok(&c, Some(0.0), Some(2_000_000.0)));
        assert!(!start_state_ok(&c, None, Some(0.0)));
        let r = gate_reading(None, true, true, true, true);
        assert_eq!(r.cpu_load_2s_pct, 100.0); // unreadable load fails the gate closed
        let it = |n: &str, ok: bool, required: bool| NightItem { name: n.into(), ok, required, detail: String::new() };
        assert_eq!(night_refusals(&[it("a", true, true), it("b", false, true), it("c", false, false)]).len(), 1);
        assert_eq!(norm_image("MsMpEng.exe"), "msmpeng");
        assert!(image_in("Claude.exe", &["claude".to_string()]));
    }
}
