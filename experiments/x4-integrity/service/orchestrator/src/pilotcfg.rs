//! The noise-pilot night configuration, schedule and clock rules (docs/m0/prereg/X4-noise-pilot.md
//! sections 2, 3, 6, 10; X4 pilot track, 2026-10-23). Pure and unit-tested; the Windows driver is
//! `pilot.rs`.
//!
//! - The configuration is a strict `key = value` file with `[run_type <id>]` sections; an unknown,
//!   duplicate or malformed key is an error, never ignored. `grade` is `DRY-RUN`, `PILOT` or `DEV`
//!   (short dev runs only; no night runs under it).
//! - `PILOT` refuses unless the freeze commit and the signature tag are named and the seed equals the
//!   record's rule (section 2): the first 16 hex digits of SHA-256 of the ASCII bytes
//!   `"X4-noise-pilot"` followed by the freeze commit as 40 lowercase hex digits. A `PILOT`
//!   configuration may not use a `dry_*` workload; a `DRY-RUN` configuration may use nothing else.
//!   (Revision 4, review 2026-10-23.) `PILOT` also refuses unless **every** constant the record fixes
//!   holds exactly (`pilot_rules`): the thresholds, windows, schedule, run types and their order,
//!   workloads, outputs, environment blocks, observe-mode ceilings and the image lists (each a
//!   superset of the record's section 10 list). Only the pre-night amendment's mechanical values
//!   (hashes, K, goldens, pins, seed, t_run,plan(e2e), the per-run overhead) are free, and those are
//!   committed with the amendment. The signature itself is not verified here (record section 10).
//! - Scratch and data paths (revision 4): every grade's scratch lies at least two levels under
//!   `D:\mithril\` or `D:\mithril-data\` (the driver wipes `<scratch>\run`); a `DRY-RUN` scratch never
//!   lies under `D:\mithril-data\` (the pilot's data area); `PILOT` keeps both under `D:\mithril-data\`.
//! - Session order: the run types' sessions (`<id>-01`, `<id>-02`, ...) in configuration order,
//!   shuffled by Fisher-Yates with SplitMix64(seed) and unbiased bounded draws. Each session's
//!   ABBA/BAAB seed is the first 16 hex digits of SHA-256("X4-noise-pilot/session/" + seed hex +
//!   "/" + session id).
//! - Time: every rule is in US Pacific time (the desktop's clock runs on US Eastern [M]); PT is
//!   computed from UTC by the US rule (DST from the second Sunday of March 02:00 to the first Sunday
//!   of November 02:00 local). A session starts only if its planned end, blocks x 4 x (t_run,plan x c
//!   + o_rt) + setup, is no later than `last_end_pt` (06:45); the driver takes the first unrun session
//!   in seed order that fits. `o_rt` (`overhead_s`) is the per-run overhead outside the timed run
//!   (gate windows, launch, init, teardown), a pre-night-amendment value (revision 4).
//! - Revision 5 (review 2026-10-23, round 5): `pilot_rules` holds every fixed value by *equality*
//!   (the e2e time cap = max(600, 3 x t_run,plan), the job memory limits, the disk-write limit, the
//!   record path, the pinned paths, and the image lists equal to the record's; the GEMS and Qwen3
//!   server names given at signing go in their own key, `excluded_images_at_signing`). The mechanical
//!   pre-night values that no rule can recompute (K, o_rt, t_run,plan(e2e), hashes, goldens) are bound
//!   by the **canonical configuration SHA-256** (`config_canonical_sha256`: the file without its
//!   `integrity_cleared` lines), which the pre-night amendment records and `pilot-night --pilot
//!   --config-sha256` and the estimator require.

use crate::sha256;
use crate::scheduler::SplitMix64;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Grade {
    DryRun,
    Pilot,
    /// Short dev runs only (`x4svc dev-run`): any workload, never a night (`pilot-night` refuses it).
    Dev,
}

impl Grade {
    pub fn label(self) -> &'static str {
        match self {
            Grade::DryRun => "DRY-RUN",
            Grade::Pilot => "PILOT",
            Grade::Dev => "DEV",
        }
    }
}

/// One run type (a column of X4-noise-pilot section 3).
#[derive(Clone, Debug, PartialEq)]
pub struct RunType {
    pub id: String,
    pub harness: String,
    pub harness_sha256: Option<String>,
    pub workload: String,
    pub param: u64,
    pub out_bytes: u64,
    pub affinity: u64,
    pub threads: u32,
    /// NORMAL_PRIORITY_CLASS (0x20) or HIGH_PRIORITY_CLASS (0x80).
    pub priority_class: u32,
    pub memory_gib: u64,
    pub env: Vec<(String, String)>,
    /// The golden output SHA-256 (64 hex); `None` only in a dry run (`golden = learn`: the first
    /// accepted run's hash becomes the reference for the rest of the dry night).
    pub golden: Option<String>,
    pub kappa_post_cycles: u64,
    pub eps_spin_us: u64,
    pub eps_idle_us: u64,
    pub init_max_ms: u64,
    pub init_max_cycles: u64,
    pub extra_cores_milli: u64,
    pub time_cap_s: u64,
    pub sessions: u32,
    pub blocks: u32,
    pub t_run_plan_s: f64,
    pub cooldown_factor: f64,
    /// Committed pins file for `verify-profile --collection` (PILOT).
    pub pins: Option<String>,
    /// o_rt: planned per-run overhead outside the timed run (gate windows, launch, init, teardown), s.
    pub overhead_s: f64,
    /// After REPORT the child must exit within this grace, or the job is terminated and the run fails
    /// `no_exit_after_report` (out of process; record section 3, revision 4).
    pub exit_grace_ms: u64,
    /// `init_max_cycles = derive`: init_max_ms x threads x the night's calibrated cycle rate (record
    /// section 3's end-to-end rule), computed at night start.
    pub init_max_cycles_derive: bool,
}

impl RunType {
    /// The pre-START cycle ceiling at the night's calibrated rate.
    pub fn init_max_cycles_at(&self, rate_hz: u64) -> u64 {
        if self.init_max_cycles_derive {
            (self.init_max_ms as u128 * self.threads as u128 * rate_hz as u128 / 1000) as u64
        } else {
            self.init_max_cycles
        }
    }
    pub fn env_get(&self, key: &str) -> Option<&str> {
        self.env.iter().find(|(k, _)| k == key).map(|(_, v)| v.as_str())
    }
}

/// The constants X4-noise-pilot fixes (sections 3, 3a, 6, 10; revision 4). A PILOT configuration must
/// equal them (`pilot_rules`); image lists must contain them.
pub mod record {
    pub const LOAD_MAX_PCT: f64 = 40.0;
    pub const CORE_LOAD_MAX_PCT: f64 = 10.0;
    pub const BG_CPU_MAX_PCT_OF_CORE: f64 = 1.0;
    pub const GPU_UTIL_MAX_PCT: f64 = 5.0;
    pub const NVME_TEMP_MAX_C: f64 = 70.0;
    pub const SESSION_SETUP_S: f64 = 120.0;
    /// Section 10: agent and build images, WSL, Mithril binaries other than this pilot's, the
    /// launchers observed on the desktop; the GEMS images and the local Qwen3 server are added at
    /// signing.
    pub const EXCLUDED: &[&str] = &[
        "claude", "node", "cl", "link", "cargo", "rustc", "python", "pythonw", "mithi", "mithc", "vmmemWSL", "vmmem", "wsl", "wslhost", "OneDrive", "Overwolf",
        "CurseForge", "EpicGamesLauncher",
    ];
    /// Section 10: a new process of these images voids (a remote login, an agent's shell, a script);
    /// CPU use of one already running at the session start does not. The driver's own children are
    /// exempt (parent pid).
    pub const STARTED: &[&str] = &["sshd", "sshd-session", "powershell", "pwsh", "cmd"];
    /// Section 10: Defender, the indexer, Windows Update servicing and idle-maintenance tasks.
    pub const BG: &[&str] = &[
        "MsMpEng", "MpDefenderCoreService", "MpCmdRun", "SearchIndexer", "SearchProtocolHost", "SearchFilterHost", "TiWorker", "TrustedInstaller", "MoUsoCoreWorker",
        "wuauclt", "UsoClient", "CompatTelRunner", "defrag", "ngen", "ngentask", "mscorsvw", "DismHost", "cleanmgr", "wermgr",
    ];
    /// C02's answer (OWNER-ANSWERS batch 3, R8).
    pub const MODEL_PATH: &str = "C:\\Users\\pierce lonergan\\hearth-data\\qwen3-30b-a3b-q4.hearth";
    /// Section 3 (revision 5): the record's path, the pinned binaries' and pins files' locations, the
    /// data and scratch directories, and the job memory limits per run type [G].
    pub const RECORD: &str = "docs/m0/prereg/X4-noise-pilot.md";
    pub const DATA_DIR: &str = "D:\\mithril-data\\x4\\pilot";
    pub const SCRATCH: &str = "D:\\mithril-data\\x4\\scratch";
    pub const HARNESS: &str = "D:\\mithril-data\\x4\\bin\\x4harness_hearth.exe";
    pub const PROBE: &str = "D:\\mithril-data\\x4\\bin\\x4sb_probe.exe";
    pub const PINS_DIR: &str = "D:\\mithril-data\\x4\\pins\\";
    pub const SIGNED_TAG: &str = "prereg-sign-x4-noise-pilot";
    pub const DISK_WRITE_MAX_BYTES_S: f64 = 1_048_576.0;
    pub const MEMORY_GIB_MB: u64 = 2;
    pub const MEMORY_GIB_E2E: u64 = 24;
    /// Plausibility bounds on the two mechanical schedule values (revision 5) [G]: o_rt above 15 s,
    /// or t_run,plan(e2e) above 600 s (36 end-to-end blocks would need over 36 h), is a design revisit
    /// before data, never a configuration value.
    pub const OVERHEAD_MAX_S: f64 = 15.0;
    pub const E2E_T_RUN_PLAN_MAX_S: f64 = 600.0;
}

/// The canonical configuration SHA-256 (revision 5): SHA-256 of the file's lines, each without a
/// trailing CR, joined by LF with a final LF, after removing every line whose key is
/// `integrity_cleared`. A dated clearing amendment adds only such a line, so the hash the pre-night
/// amendment records stays valid across it (record section 7); every other change is a new hash.
pub fn config_canonical_sha256(text: &str) -> String {
    let mut s = String::with_capacity(text.len());
    for raw in text.split('\n') {
        let l = raw.strip_suffix('\r').unwrap_or(raw);
        let key = l.split('=').next().unwrap_or("").trim();
        if l.contains('=') && key == "integrity_cleared" {
            continue;
        }
        s.push_str(l);
        s.push('\n');
    }
    // a file ending in LF yields one empty last piece: drop the extra LF it added
    if text.ends_with('\n') && s.ends_with("\n\n") {
        s.pop();
    }
    sha256::hex(&sha256::digest(s.as_bytes()))
}

#[derive(Clone, Debug, PartialEq)]
pub struct PilotConfig {
    pub grade: Grade,
    pub record: String,
    pub freeze_commit: Option<String>,
    pub signed_tag: Option<String>,
    pub seed_hex: String,
    pub data_dir: String,
    pub scratch: String,
    /// Every excluded image the sensors use: `excluded_images` (in PILOT exactly the record's list)
    /// plus `excluded_images_at_signing` (revision 5).
    pub excluded_images: Vec<String>,
    /// The `excluded_images` key as written (PILOT: equal to `record::EXCLUDED`).
    pub excluded_images_listed: Vec<String>,
    /// Images named at signing (record section 13: GEMS images, the local Qwen3 server's image if not
    /// already listed); PILOT needs the key, which may be empty.
    pub excluded_images_at_signing: Option<Vec<String>>,
    /// Images whose *start* voids a session (revision 4: sshd, shells); see `record::STARTED`.
    pub excluded_started_images: Vec<String>,
    pub bg_images: Vec<String>,
    pub load_max_pct: f64,
    /// For a run type whose job mask is one LP: that LP and its SMT sibling must each be at most this
    /// busy over the 2-s window (record section 3 "its SMT sibling idle"; revision 4).
    pub core_load_max_pct: f64,
    /// Integrity stops cleared by a dated amendment: (session id, amendment commit). PILOT only.
    pub integrity_cleared: Vec<(String, String)>,
    pub bg_cpu_max_pct_of_core: f64,
    pub gpu_util_max_pct: f64,
    pub nvme_temp_max_c: f64,
    pub nvme_volume: char,
    pub disk_write_max_bytes_s: f64,
    /// Largest disk queue (an integer count) the start state accepts: 0 in the record.
    pub disk_queue_max: f64,
    pub settle_timeout_s: u64,
    pub load_window_ms: u64,
    pub disk_window_ms: u64,
    pub excluded_cpu_max_ms: f64,
    pub window_start_pt_min: u32,
    pub window_end_pt_min: u32,
    pub last_end_pt_min: u32,
    pub orchestrator_lp: u32,
    pub session_setup_s: f64,
    /// The sandbox self-test's outside positive-control exe (`x4sb_probe.exe`); PILOT.
    pub probe_exe: Option<String>,
    /// Pinned SHA-256 of `x4svc.exe` itself and of the probe exe (PILOT; the pre-night amendment).
    pub x4svc_sha256: Option<String>,
    pub probe_sha256: Option<String>,
    /// DRY-RUN plants only: the LP mask the plant processes run on (0 = inherit the orchestrator's).
    pub plant_affinity: u64,
    pub run_types: Vec<RunType>,
}

fn hhmm(v: &str) -> Result<u32, String> {
    let (h, m) = v.split_once(':').ok_or_else(|| format!("time {:?} is not HH:MM", v))?;
    let (h, m): (u32, u32) = (h.trim().parse().map_err(|_| format!("bad hour in {:?}", v))?, m.trim().parse().map_err(|_| format!("bad minute in {:?}", v))?);
    if h > 23 || m > 59 {
        return Err(format!("time {:?} out of range", v));
    }
    Ok(h * 60 + m)
}
fn is_hex(v: &str, n: usize) -> bool {
    v.len() == n && v.chars().all(|c| c.is_ascii_hexdigit())
}
fn parse_u64(v: &str) -> Result<u64, String> {
    match v.strip_prefix("0x").or_else(|| v.strip_prefix("0X")) {
        Some(h) => u64::from_str_radix(h, 16).map_err(|_| format!("bad hex {:?}", v)),
        None => v.replace('_', "").parse().map_err(|_| format!("bad integer {:?}", v)),
    }
}
fn parse_f64(v: &str) -> Result<f64, String> {
    let x: f64 = v.parse().map_err(|_| format!("bad number {:?}", v))?;
    if x.is_finite() {
        Ok(x)
    } else {
        Err(format!("non-finite number {:?}", v))
    }
}
fn list(v: &str) -> Vec<String> {
    v.split(',').map(|s| s.trim().to_string()).filter(|s| !s.is_empty()).collect()
}

/// The record's seed rule (section 2).
pub fn seed_from_freeze(freeze_commit: &str) -> String {
    let mut b = b"X4-noise-pilot".to_vec();
    b.extend_from_slice(freeze_commit.to_ascii_lowercase().as_bytes());
    sha256::hex(&sha256::digest(&b))[..16].to_string()
}

pub fn session_seed(seed_hex: &str, session_id: &str) -> u64 {
    let s = format!("X4-noise-pilot/session/{}/{}", seed_hex.to_ascii_lowercase(), session_id);
    u64::from_str_radix(&sha256::hex(&sha256::digest(s.as_bytes()))[..16], 16).expect("16 hex")
}

/// An unbiased draw in [0, bound) (bound >= 1) by rejection.
fn below(rng: &mut SplitMix64, bound: u64) -> u64 {
    let zone = u64::MAX - (u64::MAX % bound);
    loop {
        let r = rng.next_u64();
        if r < zone {
            return r % bound;
        }
    }
}

/// One planned session.
#[derive(Clone, Debug, PartialEq)]
pub struct PlannedSession {
    pub id: String,
    pub run_type: usize,
    pub seed: u64,
}

impl PilotConfig {
    pub fn seed_u64(&self) -> u64 {
        u64::from_str_radix(&self.seed_hex, 16).expect("validated")
    }
    /// Every session of the pilot, in seed order (section 6).
    pub fn schedule(&self) -> Vec<PlannedSession> {
        let mut v: Vec<PlannedSession> = Vec::new();
        for (i, rt) in self.run_types.iter().enumerate() {
            for k in 1..=rt.sessions {
                let id = format!("{}-{:02}", rt.id, k);
                v.push(PlannedSession { seed: session_seed(&self.seed_hex, &id), id, run_type: i });
            }
        }
        let mut rng = SplitMix64::new(self.seed_u64());
        for i in (1..v.len()).rev() {
            let j = below(&mut rng, i as u64 + 1) as usize;
            v.swap(i, j);
        }
        v
    }
    /// Planned seconds of one block: 4 x (t_run,plan x c + o_rt). Also the fixed denominator of the
    /// background-CPU discard (revision 4: never the observed block time, which contains run times).
    pub fn planned_block_s(&self, rt: &RunType) -> f64 {
        4.0 * (rt.t_run_plan_s * rt.cooldown_factor + rt.overhead_s)
    }
    /// Planned seconds of one session of run type `rt`: blocks x 4 x (t_run,plan x c + o_rt) + setup.
    pub fn planned_secs(&self, rt: &RunType) -> f64 {
        rt.blocks as f64 * self.planned_block_s(rt) + self.session_setup_s
    }
    /// Whether an integrity stop of `session` has been cleared by an amendment named in the config.
    pub fn integrity_cleared_for(&self, session: &str) -> Option<&str> {
        self.integrity_cleared.iter().find(|(s, _)| s == session).map(|(_, c)| c.as_str())
    }
    pub fn run_type(&self, id: &str) -> Option<&RunType> {
        self.run_types.iter().find(|r| r.id == id)
    }
}

/// Parse and validate a configuration.
pub fn parse(text: &str) -> Result<PilotConfig, String> {
    let mut g: Vec<(String, String, usize)> = Vec::new();
    let mut rts: Vec<(String, Vec<(String, String, usize)>)> = Vec::new();
    for (n, raw) in text.lines().enumerate() {
        let line = raw.trim();
        let ln = n + 1;
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        if let Some(h) = line.strip_prefix('[') {
            let h = h.strip_suffix(']').ok_or_else(|| format!("line {}: unterminated section", ln))?;
            let id = h.strip_prefix("run_type ").ok_or_else(|| format!("line {}: unknown section [{}]", ln, h))?.trim();
            if id.is_empty() || !id.chars().all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_') {
                return Err(format!("line {}: bad run type id {:?}", ln, id));
            }
            if rts.iter().any(|r| r.0 == id) {
                return Err(format!("line {}: duplicate run type {:?}", ln, id));
            }
            rts.push((id.to_string(), Vec::new()));
            continue;
        }
        let (k, v) = line.split_once('=').ok_or_else(|| format!("line {}: no '='", ln))?;
        let (k, v) = (k.trim().to_string(), v.trim().to_string());
        // revision 5: a template placeholder never parses as a value (a list would take it as names)
        if v.contains("<FILL") {
            return Err(format!("line {}: {} is still a template placeholder ({})", ln, k, v));
        }
        match rts.last_mut() {
            Some(r) => r.1.push((k, v, ln)),
            None => g.push((k, v, ln)),
        }
    }

    let take = |kvs: &[(String, String, usize)], key: &str| -> Result<Option<String>, String> {
        let hits: Vec<&(String, String, usize)> = kvs.iter().filter(|x| x.0 == key).collect();
        match hits.len() {
            0 => Ok(None),
            1 => Ok(Some(hits[0].1.clone())),
            _ => Err(format!("line {}: duplicate key {:?}", hits[1].2, key)),
        }
    };
    const GLOBAL: &[&str] = &[
        "grade", "record", "freeze_commit", "signed_tag", "seed", "data_dir", "scratch", "excluded_images", "excluded_started_images", "bg_images",
        "load_max_pct", "core_load_max_pct", "bg_cpu_max_pct_of_core", "gpu_util_max_pct", "nvme_temp_max_c", "nvme_volume", "disk_write_max_bytes_s",
        "disk_queue_max", "settle_timeout_s", "load_window_ms", "disk_window_ms", "excluded_cpu_max_ms", "window_start_pt", "window_end_pt", "last_end_pt",
        "orchestrator_lp", "session_setup_s", "probe_exe", "x4svc_sha256", "probe_sha256", "plant_affinity", "integrity_cleared",
        "excluded_images_at_signing",
    ];
    const RT: &[&str] = &[
        "harness", "harness_sha256", "workload", "param", "out_bytes", "affinity", "threads", "priority", "memory_gib", "env", "golden",
        "kappa_post_cycles", "eps_spin_us", "eps_idle_us", "init_max_ms", "init_max_cycles", "extra_cores_milli", "time_cap_s", "sessions",
        "blocks", "t_run_plan_s", "cooldown_factor", "pins", "overhead_s", "exit_grace_ms",
    ];
    for (k, _, ln) in &g {
        if !GLOBAL.contains(&k.as_str()) {
            return Err(format!("line {}: unknown key {:?}", ln, k));
        }
    }
    let req = |kvs: &[(String, String, usize)], key: &str| -> Result<String, String> { take(kvs, key)?.ok_or_else(|| format!("missing key {:?}", key)) };
    let grade = match req(&g, "grade")?.as_str() {
        "DRY-RUN" => Grade::DryRun,
        "PILOT" => Grade::Pilot,
        "DEV" => Grade::Dev,
        o => return Err(format!("grade {:?} is not DRY-RUN, PILOT or DEV", o)),
    };
    let f = |key: &str, def: f64| -> Result<f64, String> { take(&g, key)?.map(|v| parse_f64(&v)).unwrap_or(Ok(def)) };
    let u = |key: &str, def: u64| -> Result<u64, String> { take(&g, key)?.map(|v| parse_u64(&v)).unwrap_or(Ok(def)) };
    let seed_hex = req(&g, "seed")?.to_ascii_lowercase();
    if !is_hex(&seed_hex, 16) {
        return Err("seed must be 16 hex digits".into());
    }
    let freeze_commit = take(&g, "freeze_commit")?.map(|s| s.to_ascii_lowercase());
    let signed_tag = take(&g, "signed_tag")?;
    if grade == Grade::Pilot {
        let fc = freeze_commit.as_deref().ok_or("PILOT needs freeze_commit (the record's freeze commit)")?;
        if !is_hex(fc, 40) {
            return Err("freeze_commit must be 40 hex digits".into());
        }
        if signed_tag.as_deref().map_or(true, |t| t.trim().is_empty()) {
            return Err("PILOT needs signed_tag (the Owner's signature tag on the freeze commit)".into());
        }
        let want = seed_from_freeze(fc);
        if want != seed_hex {
            return Err(format!("seed {} is not the record's rule from the freeze commit ({})", seed_hex, want));
        }
    }
    let nvme_volume = {
        let v = take(&g, "nvme_volume")?.unwrap_or_else(|| "C".into());
        let c = v.chars().next().unwrap_or('C').to_ascii_uppercase();
        if v.len() != 1 || !c.is_ascii_alphabetic() {
            return Err("nvme_volume must be one drive letter".into());
        }
        c
    };
    let scratch = req(&g, "scratch")?;
    if scratch.len() < 2 || scratch[..2].eq_ignore_ascii_case("C:") {
        return Err("scratch must not be on C: (the no-new-data-on-C: rule)".into());
    }
    // the driver wipes <scratch>\run and <scratch>\selftest: only a dedicated Mithril folder at least
    // two levels deep (review 2026-10-23: scratch = D:\ would have deleted D:\run)
    if !path_under(&scratch, &["d:\\mithril\\", "d:\\mithril-data\\"], 2) {
        return Err(format!("scratch {:?} must lie at least two levels under D:\\mithril\\ or D:\\mithril-data\\", scratch));
    }
    if grade == Grade::DryRun && path_under(&scratch, &["d:\\mithril-data\\"], 1) {
        return Err("a DRY-RUN scratch may not lie under D:\\mithril-data\\ (the pilot's data area)".into());
    }
    let mut integrity_cleared = Vec::new();
    for e in list(&take(&g, "integrity_cleared")?.unwrap_or_default()) {
        let (sid, commit) = e.split_once('@').ok_or_else(|| format!("integrity_cleared {:?} is not <session id>@<amendment commit>", e))?;
        if !is_hex(commit.trim(), 40) || sid.trim().is_empty() {
            return Err(format!("integrity_cleared {:?} is not <session id>@<40-hex amendment commit>", e));
        }
        integrity_cleared.push((sid.trim().to_string(), commit.trim().to_ascii_lowercase()));
    }
    let excluded_images_listed = list(&req(&g, "excluded_images")?);
    let excluded_images_at_signing = take(&g, "excluded_images_at_signing")?.map(|v| list(&v));
    if grade == Grade::Pilot && excluded_images_at_signing.is_none() {
        return Err("PILOT needs excluded_images_at_signing (the GEMS images and any server image named at signing, record section 13; may be empty)".into());
    }
    let mut excluded_images = excluded_images_listed.clone();
    for e in excluded_images_at_signing.iter().flatten() {
        if !crate::hygiene::image_in(e, &excluded_images) {
            excluded_images.push(e.clone());
        }
    }
    let mut cfg = PilotConfig {
        grade,
        record: take(&g, "record")?.unwrap_or_default(),
        freeze_commit,
        signed_tag,
        seed_hex,
        data_dir: take(&g, "data_dir")?.unwrap_or_default(),
        scratch,
        excluded_images,
        excluded_images_listed,
        excluded_images_at_signing,
        excluded_started_images: list(&take(&g, "excluded_started_images")?.unwrap_or_default()),
        bg_images: list(&req(&g, "bg_images")?),
        core_load_max_pct: f("core_load_max_pct", record::CORE_LOAD_MAX_PCT)?,
        integrity_cleared,
        load_max_pct: f("load_max_pct", 40.0)?,
        bg_cpu_max_pct_of_core: f("bg_cpu_max_pct_of_core", 1.0)?,
        gpu_util_max_pct: f("gpu_util_max_pct", 5.0)?,
        nvme_temp_max_c: f("nvme_temp_max_c", 70.0)?,
        nvme_volume,
        disk_write_max_bytes_s: f("disk_write_max_bytes_s", 1_048_576.0)?,
        disk_queue_max: f("disk_queue_max", 0.0)?,
        settle_timeout_s: u("settle_timeout_s", 60)?,
        load_window_ms: u("load_window_ms", 2000)?,
        disk_window_ms: u("disk_window_ms", 1000)?,
        excluded_cpu_max_ms: f("excluded_cpu_max_ms", 0.0)?,
        window_start_pt_min: hhmm(&take(&g, "window_start_pt")?.unwrap_or_else(|| "23:00".into()))?,
        window_end_pt_min: hhmm(&take(&g, "window_end_pt")?.unwrap_or_else(|| "07:00".into()))?,
        last_end_pt_min: hhmm(&take(&g, "last_end_pt")?.unwrap_or_else(|| "06:45".into()))?,
        orchestrator_lp: u("orchestrator_lp", 0)? as u32,
        session_setup_s: f("session_setup_s", 120.0)?,
        probe_exe: take(&g, "probe_exe")?,
        x4svc_sha256: take(&g, "x4svc_sha256")?.map(|s| s.to_ascii_lowercase()),
        probe_sha256: take(&g, "probe_sha256")?.map(|s| s.to_ascii_lowercase()),
        plant_affinity: u("plant_affinity", 0)?,
        run_types: Vec::new(),
    };
    for h in [&cfg.x4svc_sha256, &cfg.probe_sha256].into_iter().flatten() {
        if !is_hex(h, 64) {
            return Err("x4svc_sha256 and probe_sha256 must be 64 hex".into());
        }
    }
    if cfg.grade == Grade::Pilot {
        if !path_under(&cfg.data_dir, &["d:\\mithril-data\\"], 2) || !path_under(&cfg.scratch, &["d:\\mithril-data\\"], 2) {
            return Err("PILOT keeps data_dir and scratch at least two levels under D:\\mithril-data\\".into());
        }
        if cfg.load_window_ms != 2000 || cfg.disk_window_ms != 1000 || cfg.settle_timeout_s != 60 {
            return Err("PILOT uses the record's sensor windows (2-s load, 1-s disk, 60-s settle)".into());
        }
        if cfg.disk_queue_max != 0.0 || cfg.disk_write_max_bytes_s > 1_048_576.0 {
            return Err("PILOT uses the record's start state (disk queue 0, writes <= 1 MiB/s)".into());
        }
        if cfg.probe_exe.is_none() || cfg.x4svc_sha256.is_none() || cfg.probe_sha256.is_none() {
            return Err("PILOT needs probe_exe, probe_sha256 and x4svc_sha256 (the pre-night amendment's pins)".into());
        }
    }
    for (id, kvs) in &rts {
        for (k, _, ln) in kvs {
            if !RT.contains(&k.as_str()) {
                return Err(format!("line {}: unknown key {:?} in [run_type {}]", ln, k, id));
            }
        }
        let ctx = |e: String| format!("[run_type {}]: {}", id, e);
        let ru = |key: &str| -> Result<u64, String> { parse_u64(&req(kvs, key).map_err(ctx)?).map_err(ctx) };
        let rf = |key: &str| -> Result<f64, String> { parse_f64(&req(kvs, key).map_err(ctx)?).map_err(ctx) };
        let mut env = Vec::new();
        for (k, v, ln) in kvs.iter().filter(|x| x.0 == "env") {
            let _ = k;
            let (ek, ev) = v.split_once('=').ok_or_else(|| format!("line {}: env needs K=V", ln))?;
            env.push((ek.trim().to_string(), ev.trim().to_string()));
        }
        let golden = match req(kvs, "golden").map_err(ctx)?.to_ascii_lowercase() {
            g if is_hex(&g, 64) => Some(g),
            g if g == "learn" && cfg.grade != Grade::Pilot => None,
            g => return Err(ctx(format!("golden {:?} must be 64 hex (or `learn` in a dry run)", g))),
        };
        let priority_class = match req(kvs, "priority").map_err(ctx)?.as_str() {
            "normal" => 0x20,
            "high" => 0x80,
            p => return Err(ctx(format!("priority {:?} is not normal or high", p))),
        };
        let harness_sha256 = take(kvs, "harness_sha256")?.map(|s| s.to_ascii_lowercase());
        if let Some(h) = &harness_sha256 {
            if !is_hex(h, 64) {
                return Err(ctx("harness_sha256 must be 64 hex".into()));
            }
        }
        let (init_max_cycles, init_max_cycles_derive) = match req(kvs, "init_max_cycles").map_err(ctx)?.as_str() {
            "derive" => (0, true),
            v => (parse_u64(v).map_err(ctx)?, false),
        };
        let rt = RunType {
            id: id.clone(),
            harness: req(kvs, "harness").map_err(ctx)?,
            harness_sha256,
            workload: req(kvs, "workload").map_err(ctx)?,
            param: ru("param")?,
            out_bytes: ru("out_bytes")?,
            affinity: ru("affinity")?,
            threads: ru("threads")? as u32,
            priority_class,
            memory_gib: ru("memory_gib")?,
            env,
            golden,
            kappa_post_cycles: ru("kappa_post_cycles")?,
            eps_spin_us: ru("eps_spin_us")?,
            eps_idle_us: ru("eps_idle_us")?,
            init_max_ms: ru("init_max_ms")?,
            init_max_cycles,
            extra_cores_milli: ru("extra_cores_milli")?,
            time_cap_s: ru("time_cap_s")?,
            sessions: ru("sessions")? as u32,
            blocks: ru("blocks")? as u32,
            t_run_plan_s: rf("t_run_plan_s")?,
            cooldown_factor: rf("cooldown_factor")?,
            pins: take(kvs, "pins")?,
            overhead_s: rf("overhead_s")?,
            exit_grace_ms: match take(kvs, "exit_grace_ms")? {
                Some(v) => parse_u64(&v).map_err(ctx)?,
                None => 5000,
            },
            init_max_cycles_derive,
        };
        if rt.out_bytes == 0 || rt.out_bytes % 64 != 0 {
            return Err(ctx("out_bytes must be a non-zero multiple of 64".into()));
        }
        if rt.affinity == 0 || rt.threads == 0 || rt.blocks == 0 || rt.sessions == 0 || rt.memory_gib == 0 || rt.exit_grace_ms == 0 {
            return Err(ctx("affinity, threads, blocks, sessions, memory_gib and exit_grace_ms must be non-zero".into()));
        }
        if rt.cooldown_factor < 1.0 || rt.t_run_plan_s <= 0.0 || rt.overhead_s < 0.0 {
            return Err(ctx("cooldown_factor >= 1, t_run_plan_s > 0 and overhead_s >= 0".into()));
        }
        if rt.affinity & (1u64 << (cfg.orchestrator_lp % 64)) != 0 {
            return Err(ctx(format!("affinity {:#x} contains the orchestrator's reserved LP {}", rt.affinity, cfg.orchestrator_lp)));
        }
        let dry_wl = rt.workload.starts_with("dry_");
        match cfg.grade {
            Grade::DryRun if !dry_wl => return Err(ctx("a DRY-RUN configuration runs only dry_* workloads".into())),
            Grade::Pilot if dry_wl => return Err(ctx("a PILOT configuration may not run a dry_* workload".into())),
            Grade::Pilot if rt.harness_sha256.is_none() || rt.pins.is_none() || rt.golden.is_none() => {
                return Err(ctx("PILOT needs harness_sha256, pins and golden".into()))
            }
            Grade::Pilot if rt.priority_class != 0x20 => {
                return Err(ctx("the record pins NORMAL_PRIORITY_CLASS (section 3); a change is a record amendment".into()))
            }
            _ => {}
        }
        cfg.run_types.push(rt);
    }
    if cfg.run_types.is_empty() {
        return Err("no [run_type ...] section".into());
    }
    if cfg.grade == Grade::Pilot {
        let v = pilot_rules(&cfg);
        if !v.is_empty() {
            return Err(format!("PILOT differs from the record's fixed values (a change is a record amendment): {}", v.join("; ")));
        }
    }
    Ok(cfg)
}

/// `p` lies under one of `prefixes` (lower case, with a trailing backslash) and has at least
/// `min_levels` directory components below the drive root.
fn path_under(p: &str, prefixes: &[&str], min_levels: usize) -> bool {
    let l = p.trim().to_ascii_lowercase().replace('/', "\\");
    if l.contains("..") || l.len() < 3 {
        return false;
    }
    prefixes.iter().any(|pre| l.starts_with(pre)) && l[3..].split('\\').filter(|c| !c.is_empty()).count() >= min_levels
}

fn contains_all(have: &[String], want: &[&str]) -> Vec<String> {
    want.iter().filter(|w| !have.iter().any(|h| crate::hygiene::norm_image(h) == crate::hygiene::norm_image(w))).map(|w| w.to_string()).collect()
}
/// Entries of `have` that are not in `want` (normalised image names).
fn extras(have: &[String], want: &[&str]) -> Vec<String> {
    have.iter().filter(|h| !want.iter().any(|w| crate::hygiene::norm_image(h) == crate::hygiene::norm_image(w))).cloned().collect()
}
fn same_path(a: &str, b: &str) -> bool {
    a.trim().replace('/', "\\").eq_ignore_ascii_case(b)
}

/// Every value X4-noise-pilot fixes, checked for a PILOT configuration (revision 4; review
/// 2026-10-23: the parser had held only the sensor windows, the start state and the priority). An
/// empty result = the configuration is the record's. The pre-night amendment's mechanical values
/// (hashes, K = mb param, goldens, pins, the LP masks by `x4svc topology`, checked at the night start,
/// t_run,plan(e2e) and the per-run overheads) are checked for range only.
pub fn pilot_rules(c: &PilotConfig) -> Vec<String> {
    let mut v: Vec<String> = Vec::new();
    let mut eq = |name: &str, have: f64, want: f64| {
        if (have - want).abs() > 1e-9 {
            v.push(format!("{} = {} (record: {})", name, have, want));
        }
    };
    eq("load_max_pct", c.load_max_pct, record::LOAD_MAX_PCT);
    eq("core_load_max_pct", c.core_load_max_pct, record::CORE_LOAD_MAX_PCT);
    eq("bg_cpu_max_pct_of_core", c.bg_cpu_max_pct_of_core, record::BG_CPU_MAX_PCT_OF_CORE);
    eq("gpu_util_max_pct", c.gpu_util_max_pct, record::GPU_UTIL_MAX_PCT);
    eq("nvme_temp_max_c", c.nvme_temp_max_c, record::NVME_TEMP_MAX_C);
    eq("excluded_cpu_max_ms", c.excluded_cpu_max_ms, 0.0);
    eq("session_setup_s", c.session_setup_s, record::SESSION_SETUP_S);
    eq("window_start_pt", c.window_start_pt_min as f64, (23 * 60) as f64);
    eq("window_end_pt", c.window_end_pt_min as f64, (7 * 60) as f64);
    eq("last_end_pt", c.last_end_pt_min as f64, (6 * 60 + 45) as f64);
    eq("plant_affinity", c.plant_affinity as f64, 0.0);
    eq("disk_write_max_bytes_s", c.disk_write_max_bytes_s, record::DISK_WRITE_MAX_BYTES_S);
    eq("disk_queue_max", c.disk_queue_max, 0.0);
    if c.nvme_volume != 'C' {
        v.push(format!("nvme_volume = {} (record: C, the model's 990 PRO)", c.nvme_volume));
    }
    // revision 5: the lists EQUAL the record's (an extra background image adds discards, an extra
    // excluded one voids; neither is the record's); the names given at signing have their own key
    for (name, have, want) in [("excluded_images", &c.excluded_images_listed, record::EXCLUDED), ("excluded_started_images", &c.excluded_started_images, record::STARTED), ("bg_images", &c.bg_images, record::BG)] {
        let miss = contains_all(have, want);
        if !miss.is_empty() {
            v.push(format!("{} lacks the record's {:?}", name, miss));
        }
        let extra = extras(have, want);
        if !extra.is_empty() {
            v.push(format!("{} has entries the record does not list {:?} (names given at signing go in excluded_images_at_signing)", name, extra));
        }
    }
    if c.record.trim() != record::RECORD {
        v.push(format!("record = {:?} (record: {})", c.record, record::RECORD));
    }
    if c.signed_tag.as_deref().map(str::trim) != Some(record::SIGNED_TAG) {
        v.push(format!("signed_tag = {:?} (record section 13: {})", c.signed_tag, record::SIGNED_TAG));
    }
    for (name, have, want) in [("data_dir", c.data_dir.as_str(), record::DATA_DIR), ("scratch", c.scratch.as_str(), record::SCRATCH), ("probe_exe", c.probe_exe.as_deref().unwrap_or(""), record::PROBE)] {
        if !same_path(have, want) {
            v.push(format!("{} = {:?} (record: {})", name, have, want));
        }
    }
    for rt in &c.run_types {
        if !same_path(&rt.harness, record::HARNESS) {
            v.push(format!("[{}] harness = {:?} (record: {})", rt.id, rt.harness, record::HARNESS));
        }
        let want_pins = format!("{}{}.txt", record::PINS_DIR, rt.id);
        if !same_path(rt.pins.as_deref().unwrap_or(""), &want_pins) {
            v.push(format!("[{}] pins = {:?} (record: {})", rt.id, rt.pins, want_pins));
        }
        // o_rt is ceil(...) whole seconds and at least the 3 s of gate windows + 1 s of snapshot; above
        // 15 s (three times the 5 s the dev runs indicate [G]) it is a design revisit, not a value
        // (a larger o_rt widens the planned-block background budget, record section 9)
        if rt.overhead_s.fract() != 0.0 || rt.overhead_s < 4.0 || rt.overhead_s > record::OVERHEAD_MAX_S {
            v.push(format!("[{}] overhead_s = {} (record: a whole number of seconds in [4, {}], by the section Amendments rule)", rt.id, rt.overhead_s, record::OVERHEAD_MAX_S));
        }
    }
    if c.run_types.len() == 2 && c.run_types[0].harness_sha256 != c.run_types[1].harness_sha256 {
        v.push("the two run types pin different harness_sha256 (record: one binary, x4harness_hearth.exe)".into());
    }
    let ids: Vec<&str> = c.run_types.iter().map(|r| r.id.as_str()).collect();
    if ids != ["mb-q4-avx512", "e2e-decode"] {
        v.push(format!("run types {:?} (record: [mb-q4-avx512, e2e-decode] in that order, which the seed's shuffle depends on)", ids));
        return v;
    }
    let env_is = |rt: &RunType, want: &[(&str, &str)]| -> bool {
        let mut a: Vec<(String, String)> = rt.env.clone();
        let mut b: Vec<(String, String)> = want.iter().map(|(k, x)| (k.to_string(), x.to_string())).collect();
        a.sort();
        b.sort();
        a == b
    };
    // (field, have, want) per run type
    let common = |rt: &RunType, v: &mut Vec<String>| {
        let mut chk = |n: &str, h: f64, w: f64| {
            if (h - w).abs() > 1e-9 {
                v.push(format!("[{}] {} = {} (record: {})", rt.id, n, h, w));
            }
        };
        chk("kappa_post_cycles", rt.kappa_post_cycles as f64, 2.0e9);
        chk("eps_spin_us", rt.eps_spin_us as f64, 50.0);
        chk("eps_idle_us", rt.eps_idle_us as f64, 1000.0);
        chk("extra_cores_milli", rt.extra_cores_milli as f64, 250.0);
        chk("exit_grace_ms", rt.exit_grace_ms as f64, 5000.0);
        chk("priority (0x20 = normal)", rt.priority_class as f64, 0x20 as f64);
    };
    let mb = &c.run_types[0];
    common(mb, &mut v);
    fn chk(v: &mut Vec<String>, rt: &RunType, n: &str, h: f64, w: f64) {
        if (h - w).abs() > 1e-9 {
            v.push(format!("[{}] {} = {} (record: {})", rt.id, n, h, w));
        }
    }
    if mb.workload != "mb_q4_avx512" {
        v.push(format!("[mb-q4-avx512] workload {} (record: mb_q4_avx512)", mb.workload));
    }
    chk(&mut v, mb, "out_bytes", mb.out_bytes as f64, 960.0);
    chk(&mut v, mb, "threads", mb.threads as f64, 1.0);
    chk(&mut v, mb, "affinity LPs", mb.affinity.count_ones() as f64, 1.0);
    chk(&mut v, mb, "init_max_ms", mb.init_max_ms as f64, 2000.0);
    chk(&mut v, mb, "init_max_cycles", if mb.init_max_cycles_derive { -1.0 } else { mb.init_max_cycles as f64 }, 8.6e9);
    chk(&mut v, mb, "time_cap_s", mb.time_cap_s as f64, 60.0);
    chk(&mut v, mb, "sessions", mb.sessions as f64, 20.0);
    chk(&mut v, mb, "blocks", mb.blocks as f64, 24.0);
    chk(&mut v, mb, "t_run_plan_s", mb.t_run_plan_s, 10.0);
    chk(&mut v, mb, "cooldown_factor", mb.cooldown_factor, 1.0);
    chk(&mut v, mb, "memory_gib", mb.memory_gib as f64, record::MEMORY_GIB_MB as f64);
    if mb.param == 0 {
        v.push("[mb-q4-avx512] param (K) must be the pre-night amendment's K".into());
    }
    if !env_is(mb, &[("HEARTH_ISA", "avx512"), ("HEARTH_LOG", "0"), ("CUDA_VISIBLE_DEVICES", "-1")]) {
        v.push(format!("[mb-q4-avx512] env {:?} (record: HEARTH_ISA=avx512, HEARTH_LOG=0, CUDA_VISIBLE_DEVICES=-1)", mb.env));
    }
    let e = &c.run_types[1];
    common(e, &mut v);
    if e.workload != "e2e_decode" {
        v.push(format!("[e2e-decode] workload {} (record: e2e_decode)", e.workload));
    }
    chk(&mut v, e, "param (N)", e.param as f64, 2048.0);
    chk(&mut v, e, "out_bytes", e.out_bytes as f64, 607_744.0);
    chk(&mut v, e, "init_max_ms", e.init_max_ms as f64, 120_000.0);
    if !e.init_max_cycles_derive {
        v.push("[e2e-decode] init_max_cycles must be `derive` (init_max_ms x threads x the night's calibrated rate)".into());
    }
    chk(&mut v, e, "sessions", e.sessions as f64, 3.0);
    chk(&mut v, e, "blocks", e.blocks as f64, 12.0);
    chk(&mut v, e, "cooldown_factor", e.cooldown_factor, 1.5);
    chk(&mut v, e, "memory_gib", e.memory_gib as f64, record::MEMORY_GIB_E2E as f64);
    // revision 5: t_run,plan(e2e) is ceil(...) whole seconds; the cap EQUALS max(600, 3 x t_run,plan)
    // (a larger cap would let a slow run pass as a measured one instead of a capped outlier)
    if e.t_run_plan_s.fract() != 0.0 || e.t_run_plan_s < 1.0 || e.t_run_plan_s > record::E2E_T_RUN_PLAN_MAX_S {
        v.push(format!("[e2e-decode] t_run_plan_s = {} (record: a whole number of seconds in [1, {}], by the section Amendments rule; above it the pilot cannot fit its nights and is a design revisit)", e.t_run_plan_s, record::E2E_T_RUN_PLAN_MAX_S));
    }
    let cap = (600.0f64).max(3.0 * e.t_run_plan_s);
    if (e.time_cap_s as f64 - cap).abs() > 1e-9 {
        v.push(format!("[e2e-decode] time_cap_s = {} (record: max(600, 3 x t_run_plan_s) = {})", e.time_cap_s, cap));
    }
    let want_env: [(&str, &str); 7] = [
        ("HEARTH_ISA", "avx512"),
        ("HEARTH_LOG", "0"),
        ("CUDA_VISIBLE_DEVICES", "-1"),
        ("HEARTH_THREADS", "16"),
        ("HEARTH_IO_THREADS", "8"),
        ("HEARTH_CACHE_GB", "8"),
        ("X4_MODEL_PATH", record::MODEL_PATH),
    ];
    if !env_is(e, &want_env) {
        v.push(format!("[e2e-decode] env {:?} (record section 3 under C01/C02's answers: {:?})", e.env, want_env));
    }
    let declared: u32 = ["HEARTH_THREADS", "HEARTH_IO_THREADS"].iter().filter_map(|k| e.env_get(k)).filter_map(|x| x.parse::<u32>().ok()).sum();
    chk(&mut v, e, "threads (HEARTH_THREADS + HEARTH_IO_THREADS)", e.threads as f64, declared as f64);
    v
}

// ---------------------------------------------------------------------------------- time (PT)

/// Days since 1970-01-01 of a proleptic Gregorian date (H. Hinnant's algorithm).
pub fn days_from_civil(y: i64, m: u32, d: u32) -> i64 {
    let y = if m <= 2 { y - 1 } else { y };
    let era = if y >= 0 { y } else { y - 399 } / 400;
    let yoe = y - era * 400;
    let mp = (m as i64 + 9) % 12;
    let doy = (153 * mp + 2) / 5 + d as i64 - 1;
    let doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    era * 146097 + doe - 719468
}
pub fn civil_from_days(z: i64) -> (i64, u32, u32) {
    let z = z + 719468;
    let era = if z >= 0 { z } else { z - 146096 } / 146097;
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    (if m <= 2 { y + 1 } else { y }, m, d)
}
/// 0 = Sunday.
pub fn weekday(days: i64) -> u32 {
    (days + 4).rem_euclid(7) as u32
}
fn nth_sunday(y: i64, m: u32, n: u32) -> i64 {
    let first = days_from_civil(y, m, 1);
    let to_sun = (7 - weekday(first)) % 7;
    first + to_sun as i64 + 7 * (n as i64 - 1)
}
/// Offset of US Pacific time from UTC at a UTC instant (seconds; -7 h in DST, else -8 h).
pub fn pt_offset_secs(utc: i64) -> i64 {
    let (y, _, _) = civil_from_days(utc.div_euclid(86400));
    let start = nth_sunday(y, 3, 2) * 86400 + 10 * 3600; // 02:00 PST
    let end = nth_sunday(y, 11, 1) * 86400 + 9 * 3600; // 02:00 PDT
    if utc >= start && utc < end {
        -7 * 3600
    } else {
        -8 * 3600
    }
}
/// PT wall-clock seconds since 1970-01-01 00:00 PT for a UTC instant.
pub fn pt_local(utc: i64) -> i64 {
    utc + pt_offset_secs(utc)
}
/// The UTC instant of a PT wall-clock time; in the repeated hour of the autumn change it is the
/// earlier (PDT) instant, the conservative choice for a deadline.
pub fn pt_local_to_utc(local: i64) -> i64 {
    let a = local + 7 * 3600;
    if pt_offset_secs(a) == -7 * 3600 {
        a
    } else {
        local + 8 * 3600
    }
}
/// "YYYY-MM-DD HH:MM PT" for a UTC instant.
pub fn pt_string(utc: i64) -> String {
    let l = pt_local(utc);
    let (y, m, d) = civil_from_days(l.div_euclid(86400));
    let s = l.rem_euclid(86400);
    format!("{:04}-{:02}-{:02} {:02}:{:02}:{:02} {}", y, m, d, s / 3600, s % 3600 / 60, s % 60, if pt_offset_secs(utc) == -7 * 3600 { "PDT" } else { "PST" })
}

/// The quiet window containing `utc`, as (night date as days since epoch of the evening it starts,
/// window start UTC, last-end UTC, window end UTC); None outside the window.
pub fn night_window(cfg: &PilotConfig, utc: i64) -> Option<(i64, i64, i64, i64)> {
    let l = pt_local(utc);
    let day = l.div_euclid(86400);
    let min = (l.rem_euclid(86400) / 60) as u32;
    let night = if min >= cfg.window_start_pt_min {
        day
    } else if min < cfg.window_end_pt_min {
        day - 1
    } else {
        return None;
    };
    let start = pt_local_to_utc(night * 86400 + cfg.window_start_pt_min as i64 * 60);
    let last_end = pt_local_to_utc((night + 1) * 86400 + cfg.last_end_pt_min as i64 * 60);
    let end = pt_local_to_utc((night + 1) * 86400 + cfg.window_end_pt_min as i64 * 60);
    Some((night, start, last_end, end))
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;

    pub(crate) const DRY: &str = "
# dry
grade = DRY-RUN
seed = 0123456789abcdef
scratch = D:\\mithril\\x4c\\scratch
excluded_images = claude, node, x4plant_gems
excluded_started_images = sshd
bg_images = MsMpEng, SearchIndexer, TiWorker
load_window_ms = 100
orchestrator_lp = 30
[run_type mb-q4-avx512]
harness = D:\\mithril\\x4c\\bin\\x4harness_hearth.exe
workload = dry_mb_tiny
param = 256
out_bytes = 960
affinity = 0x4
threads = 1
priority = normal
memory_gib = 2
env = HEARTH_ISA=avx512
env = HEARTH_LOG=0
golden = learn
kappa_post_cycles = 2000000000
eps_spin_us = 50
eps_idle_us = 1000
init_max_ms = 2000
init_max_cycles = 8600000000
extra_cores_milli = 250
time_cap_s = 60
sessions = 20
blocks = 24
t_run_plan_s = 10
cooldown_factor = 1
overhead_s = 5
[run_type e2e-decode]
harness = D:\\mithril\\x4c\\bin\\x4harness_hearth.exe
workload = dry_mb_tiny
param = 256
out_bytes = 960
affinity = 0x7
threads = 1
priority = normal
memory_gib = 2
golden = learn
kappa_post_cycles = 2000000000
eps_spin_us = 50
eps_idle_us = 1000
init_max_ms = 120000
init_max_cycles = derive
extra_cores_milli = 250
time_cap_s = 60
sessions = 3
blocks = 12
t_run_plan_s = 120
cooldown_factor = 1.5
overhead_s = 5
";

    /// pilot.cfg.template with every <FILL> replaced by a dummy value (freeze commit `FC`).
    pub(crate) const FC: &str = "a3add8b0000000000000000000000000000000ff";
    pub(crate) fn filled_pilot() -> String {
        let h = "b".repeat(64);
        format!(
            "grade = PILOT
record = docs/m0/prereg/X4-noise-pilot.md
freeze_commit = {fc}
signed_tag = prereg-sign-x4-noise-pilot
seed = {seed}
data_dir = D:\\mithril-data\\x4\\pilot
scratch = D:\\mithril-data\\x4\\scratch
probe_exe = D:\\mithril-data\\x4\\bin\\x4sb_probe.exe
probe_sha256 = {h}
x4svc_sha256 = {h}
excluded_images = {ex}
excluded_images_at_signing = gems-worker
excluded_started_images = {st}
bg_images = {bg}
load_max_pct = 40
core_load_max_pct = 10
bg_cpu_max_pct_of_core = 1
gpu_util_max_pct = 5
nvme_temp_max_c = 70
nvme_volume = C
disk_write_max_bytes_s = 1048576
disk_queue_max = 0
settle_timeout_s = 60
load_window_ms = 2000
disk_window_ms = 1000
excluded_cpu_max_ms = 0
window_start_pt = 23:00
window_end_pt = 07:00
last_end_pt = 06:45
orchestrator_lp = 30
session_setup_s = 120

[run_type mb-q4-avx512]
harness = D:\\mithril-data\\x4\\bin\\x4harness_hearth.exe
harness_sha256 = {h}
workload = mb_q4_avx512
param = 1761170
out_bytes = 960
affinity = 0x4
threads = 1
priority = normal
memory_gib = 2
env = HEARTH_ISA=avx512
env = HEARTH_LOG=0
env = CUDA_VISIBLE_DEVICES=-1
golden = {h}
kappa_post_cycles = 2000000000
eps_spin_us = 50
eps_idle_us = 1000
init_max_ms = 2000
init_max_cycles = 8600000000
extra_cores_milli = 250
exit_grace_ms = 5000
time_cap_s = 60
sessions = 20
blocks = 24
t_run_plan_s = 10
cooldown_factor = 1
overhead_s = 5
pins = D:\\mithril-data\\x4\\pins\\mb-q4-avx512.txt

[run_type e2e-decode]
harness = D:\\mithril-data\\x4\\bin\\x4harness_hearth.exe
harness_sha256 = {h}
workload = e2e_decode
param = 2048
out_bytes = 607744
affinity = 0xbfffffff
threads = 24
priority = normal
memory_gib = 24
env = HEARTH_ISA=avx512
env = HEARTH_LOG=0
env = CUDA_VISIBLE_DEVICES=-1
env = HEARTH_THREADS=16
env = HEARTH_IO_THREADS=8
env = HEARTH_CACHE_GB=8
env = X4_MODEL_PATH={model}
golden = {h}
kappa_post_cycles = 2000000000
eps_spin_us = 50
eps_idle_us = 1000
init_max_ms = 120000
init_max_cycles = derive
extra_cores_milli = 250
exit_grace_ms = 5000
time_cap_s = 600
sessions = 3
blocks = 12
t_run_plan_s = 120
cooldown_factor = 1.5
overhead_s = 6
pins = D:\\mithril-data\\x4\\pins\\e2e-decode.txt
",
            fc = FC,
            seed = seed_from_freeze(FC),
            h = h,
            ex = record::EXCLUDED.join(", "),
            st = record::STARTED.join(", "),
            bg = record::BG.join(", "),
            model = record::MODEL_PATH
        )
    }

    #[test]
    fn dry_config_parses_and_schedules_23_sessions() {
        let c = parse(DRY).unwrap();
        assert_eq!(c.grade, Grade::DryRun);
        assert_eq!(c.run_types.len(), 2);
        assert_eq!(c.run_types[0].env, vec![("HEARTH_ISA".to_string(), "avx512".to_string()), ("HEARTH_LOG".to_string(), "0".to_string())]);
        assert_eq!(c.load_window_ms, 100);
        assert_eq!(c.excluded_started_images, vec!["sshd".to_string()]);
        let s = c.schedule();
        assert_eq!(s.len(), 23);
        assert_eq!(s.iter().filter(|x| x.run_type == 1).count(), 3);
        let mut ids: Vec<&str> = s.iter().map(|x| x.id.as_str()).collect();
        ids.sort();
        ids.dedup();
        assert_eq!(ids.len(), 23);
        assert_eq!(s, c.schedule()); // deterministic
        // blocks x 4 x (t_run,plan x c + o_rt) + setup
        assert_eq!(c.planned_secs(&c.run_types[0]), 24.0 * 4.0 * (10.0 + 5.0) + 120.0);
        assert_eq!(c.planned_secs(&c.run_types[1]), 12.0 * 4.0 * (180.0 + 5.0) + 120.0);
        assert_eq!(c.planned_block_s(&c.run_types[0]), 60.0);
        assert_ne!(session_seed("0123456789abcdef", "mb-q4-avx512-01"), session_seed("0123456789abcdef", "mb-q4-avx512-02"));
        // init_max_cycles = derive: 120 s x 1 thread x rate
        assert!(c.run_types[1].init_max_cycles_derive);
        assert_eq!(c.run_types[1].init_max_cycles_at(4_296_000_000), 120 * 4_296_000_000);
        assert_eq!(c.run_types[0].init_max_cycles_at(4_296_000_000), 8_600_000_000);
        assert_eq!(c.run_types[0].exit_grace_ms, 5000);
    }

    #[test]
    fn strictness_grade_and_path_guards() {
        assert!(parse(&DRY.replace("grade = DRY-RUN", "grade = DRY-RUN\ncolour = blue")).is_err());
        assert!(parse(&DRY.replace("param = 256\nout_bytes = 960\naffinity = 0x4", "param = 256\nparam = 1\nout_bytes = 960\naffinity = 0x4")).is_err());
        assert!(parse(&DRY.replacen("workload = dry_mb_tiny", "workload = mb_q4_avx512", 1)).is_err());
        assert!(parse(&DRY.replace("scratch = D:", "scratch = C:")).is_err());
        assert!(parse(&DRY.replacen("out_bytes = 960", "out_bytes = 100", 1)).is_err());
        assert!(parse(&DRY.replacen("overhead_s = 5\n", "", 1)).is_err());
        // a run's mask may not contain the orchestrator's reserved LP
        assert!(parse(&DRY.replace("orchestrator_lp = 30", "orchestrator_lp = 2")).is_err());
        // scratch: a dedicated folder two levels under D:\mithril\ or D:\mithril-data\, never D:\
        for bad in ["D:\\", "D:\\mithril", "D:\\run", "D:\\mithril\\..\\x", "E:\\mithril\\x4c\\scratch"] {
            assert!(parse(&DRY.replace("scratch = D:\\mithril\\x4c\\scratch", &format!("scratch = {}", bad))).is_err(), "{bad}");
        }
        // a DRY-RUN scratch never lies in the pilot's data area
        assert!(parse(&DRY.replace("scratch = D:\\mithril\\x4c\\scratch", "scratch = D:\\mithril-data\\x4\\scratch")).is_err());
        assert!(parse(&DRY.replace("grade = DRY-RUN", "grade = DEV").replace("scratch = D:\\mithril\\x4c\\scratch", "scratch = D:\\mithril-data\\x4\\scratch")).is_ok());
    }

    #[test]
    fn the_filled_template_is_the_record_and_every_loosening_is_refused() {
        let p = filled_pilot();
        let c = parse(&p).unwrap_or_else(|e| panic!("{e}"));
        assert_eq!(c.grade, Grade::Pilot);
        assert!(pilot_rules(&c).is_empty());
        // the shape of the PILOT preconditions
        assert!(parse(&p.replace("freeze_commit", "#")).is_err());
        assert!(parse(&p.replace(&format!("seed = {}", seed_from_freeze(FC)), "seed = 0123456789abcdef")).is_err());
        assert!(parse(&p.replacen(&format!("golden = {}", "b".repeat(64)), "golden = learn", 1)).is_err());
        assert!(parse(&p.replacen("workload = mb_q4_avx512", "workload = dry_mb_tiny", 1)).is_err());
        assert!(parse(&p.replacen(&format!("harness_sha256 = {}\n", "b".repeat(64)), "", 1)).is_err());
        // integrity_cleared: <session id>@<40-hex amendment commit>
        let cleared = p.replacen("session_setup_s = 120", &format!("session_setup_s = 120\nintegrity_cleared = mb-q4-avx512-03@{}", "e".repeat(40)), 1);
        assert_eq!(parse(&cleared).unwrap().integrity_cleared_for("mb-q4-avx512-03"), Some("e".repeat(40).as_str()));
        assert!(parse(&p.replacen("session_setup_s = 120", "session_setup_s = 120\nintegrity_cleared = x@1", 1)).is_err());
        // every record value: one mutation each must refuse (review 2026-10-23)
        let muts: &[(&str, &str)] = &[
            ("load_max_pct = 40", "load_max_pct = 100"),
            ("core_load_max_pct = 10", "core_load_max_pct = 50"),
            ("bg_cpu_max_pct_of_core = 1", "bg_cpu_max_pct_of_core = 1000000000"),
            ("gpu_util_max_pct = 5", "gpu_util_max_pct = 101"),
            ("nvme_temp_max_c = 70", "nvme_temp_max_c = 200"),
            ("nvme_volume = C", "nvme_volume = D"),
            ("disk_queue_max = 0", "disk_queue_max = 3"),
            ("disk_write_max_bytes_s = 1048576", "disk_write_max_bytes_s = 9048576"),
            ("settle_timeout_s = 60", "settle_timeout_s = 600"),
            ("load_window_ms = 2000", "load_window_ms = 100"),
            ("disk_window_ms = 1000", "disk_window_ms = 100"),
            ("excluded_cpu_max_ms = 0", "excluded_cpu_max_ms = 5"),
            ("window_start_pt = 23:00", "window_start_pt = 22:00"),
            ("window_end_pt = 07:00", "window_end_pt = 08:00"),
            ("last_end_pt = 06:45", "last_end_pt = 07:30"),
            ("session_setup_s = 120", "session_setup_s = 0"),
            ("session_setup_s = 120", "session_setup_s = 120\nplant_affinity = 0x10"),
            ("excluded_images = claude, ", "excluded_images = "),
            ("sshd, ", ""),
            ("MsMpEng, ", ""),
            ("kappa_post_cycles = 2000000000", "kappa_post_cycles = 9000000000"),
            ("eps_spin_us = 50", "eps_spin_us = 500"),
            ("eps_idle_us = 1000", "eps_idle_us = 9000"),
            ("init_max_ms = 2000", "init_max_ms = 9000"),
            ("init_max_cycles = 8600000000", "init_max_cycles = 86000000000"),
            ("init_max_cycles = derive", "init_max_cycles = 12372480000000"),
            ("init_max_ms = 120000", "init_max_ms = 900000"),
            ("extra_cores_milli = 250", "extra_cores_milli = 2000"),
            ("exit_grace_ms = 5000", "exit_grace_ms = 60000"),
            ("time_cap_s = 60", "time_cap_s = 6000"),
            ("time_cap_s = 600", "time_cap_s = 300"),
            ("sessions = 20", "sessions = 5"),
            ("blocks = 24", "blocks = 10"),
            ("sessions = 3", "sessions = 2"),
            ("blocks = 12", "blocks = 6"),
            ("t_run_plan_s = 10", "t_run_plan_s = 1"),
            ("cooldown_factor = 1\n", "cooldown_factor = 1.2\n"),
            ("cooldown_factor = 1.5", "cooldown_factor = 1"),
            ("overhead_s = 5", "overhead_s = 1"),
            ("out_bytes = 960", "out_bytes = 64"),
            ("out_bytes = 607744", "out_bytes = 960"),
            ("param = 2048", "param = 8"),
            ("param = 1761170", "param = 0"),
            ("threads = 1", "threads = 2"),
            ("affinity = 0x4", "affinity = 0xc"),
            ("threads = 24", "threads = 20"),
            ("priority = normal", "priority = high"),
            ("env = HEARTH_LOG=0\nenv = CUDA_VISIBLE_DEVICES=-1\ngolden", "env = HEARTH_LOG=0\ngolden"),
            ("env = HEARTH_THREADS=16", "env = HEARTH_THREADS=8"),
            ("env = HEARTH_CACHE_GB=8", "env = HEARTH_CACHE_GB=1"),
            ("env = HEARTH_ISA=avx512\nenv = HEARTH_LOG=0\nenv = CUDA_VISIBLE_DEVICES=-1\nenv = HEARTH_THREADS", "env = HEARTH_ISA=avx2\nenv = HEARTH_LOG=0\nenv = CUDA_VISIBLE_DEVICES=-1\nenv = HEARTH_THREADS"),
            ("env = HEARTH_CACHE_GB=8", "env = HEARTH_CACHE_GB=8\nenv = EXTRA=1"),
            ("qwen3-30b-a3b-q4.hearth", "other.hearth"),
            ("workload = e2e_decode", "workload = mb_q4_avx512"),
            ("data_dir = D:\\mithril-data\\x4\\pilot", "data_dir = D:\\mithril\\x4c\\pilot"),
            ("scratch = D:\\mithril-data\\x4\\scratch", "scratch = D:\\mithril\\x4c\\scratch"),
            // revision 5 (review round 5): each was accepted before
            ("time_cap_s = 600", "time_cap_s = 100000"),
            ("memory_gib = 2", "memory_gib = 1"),
            ("memory_gib = 24", "memory_gib = 1"),
            ("memory_gib = 24", "memory_gib = 60"),
            ("disk_write_max_bytes_s = 1048576", "disk_write_max_bytes_s = 1"),
            ("excluded_images = claude", "excluded_images = explorer, claude"),
            ("bg_images = MsMpEng", "bg_images = svchost, MsMpEng"),
            ("excluded_started_images = sshd", "excluded_started_images = explorer, sshd"),
            ("excluded_images_at_signing = gems-worker\n", ""),
            ("record = docs/m0/prereg/X4-noise-pilot.md", "record = docs/m0/prereg/SOMETHING-ELSE.md"),
            ("signed_tag = prereg-sign-x4-noise-pilot", "signed_tag = x"),
            ("probe_exe = D:\\mithril-data\\x4\\bin\\x4sb_probe.exe", "probe_exe = D:\\mithril-data\\x4\\bin\\other.exe"),
            ("harness = D:\\mithril-data\\x4\\bin\\x4harness_hearth.exe\nharness_sha256 = bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\nworkload = e2e", "harness = D:\\mithril-data\\x4\\bin\\other.exe\nharness_sha256 = bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\nworkload = e2e"),
            ("harness_sha256 = bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\nworkload = e2e", "harness_sha256 = cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc\nworkload = e2e"),
            ("pins = D:\\mithril-data\\x4\\pins\\e2e-decode.txt", "pins = D:\\mithril-data\\x4\\pins\\other.txt"),
            ("overhead_s = 5", "overhead_s = 5.5"),
            ("overhead_s = 6", "overhead_s = 3"),
            ("t_run_plan_s = 120", "t_run_plan_s = 120.5"),
            ("overhead_s = 5", "overhead_s = 1000"),
            ("overhead_s = 6", "overhead_s = 16"),
        ];
        for (from, to) in muts {
            assert!(p.contains(from), "fixture lacks {from:?}");
            let m = p.replacen(from, to, 1);
            assert!(parse(&m).is_err(), "PILOT accepted the mutation {from:?} -> {to:?}");
        }
        // swapping the run types' order changes the seeded shuffle: refused
        let i = p.find("[run_type mb-q4-avx512]").unwrap();
        let j = p.find("[run_type e2e-decode]").unwrap();
        let swapped = format!("{}{}\n{}", &p[..i], &p[j..], &p[i..j]);
        assert!(parse(&swapped).is_err());
        // the e2e time cap follows a longer t_run,plan: max(600, 3 x plan), exactly
        let long = p.replacen("t_run_plan_s = 120", "t_run_plan_s = 250", 1);
        assert!(parse(&long).is_err());
        assert!(parse(&long.replacen("time_cap_s = 600", "time_cap_s = 750", 1)).is_ok());
        assert!(parse(&long.replacen("time_cap_s = 600", "time_cap_s = 751", 1)).is_err());
        // t_run,plan(e2e) above 600 s is a design revisit (the reviewer's 5000 s with a 15000 s cap)
        let huge = p.replacen("t_run_plan_s = 120", "t_run_plan_s = 5000", 1).replacen("time_cap_s = 600", "time_cap_s = 15000", 1);
        assert!(parse(&huge).unwrap_err().contains("t_run_plan_s = 5000"));
        let edge = p.replacen("t_run_plan_s = 120", "t_run_plan_s = 600", 1).replacen("time_cap_s = 600", "time_cap_s = 1800", 1);
        assert!(parse(&edge).is_ok());
        // names given at signing extend the sensors' list without touching the record's list
        let c2 = parse(&p.replacen("excluded_images_at_signing = gems-worker", "excluded_images_at_signing = gems-worker, gems-queue", 1)).unwrap();
        assert!(crate::hygiene::image_in("gems-queue.exe", &c2.excluded_images) && crate::hygiene::image_in("claude", &c2.excluded_images));
        assert!(parse(&p.replacen("excluded_images_at_signing = gems-worker", "excluded_images_at_signing =", 1)).is_ok());
        assert!(parse(&p.replacen("excluded_images_at_signing = gems-worker", "excluded_images_at_signing = <FILL: names, or empty>", 1)).unwrap_err().contains("placeholder"));
    }

    /// The committed template (experiments/x4-integrity/pilot/pilot.cfg.template), every placeholder
    /// filled with a dummy value of the right shape (revision 5: the template and the record agree).
    pub(crate) fn filled_template() -> String {
        let path = concat!(env!("CARGO_MANIFEST_DIR"), "/../../pilot/pilot.cfg.template");
        let t = std::fs::read_to_string(path).unwrap_or_else(|e| panic!("{path}: {e} (copy experiments/x4-integrity/pilot beside service)"));
        let h = "b".repeat(64);
        t.lines()
            .map(|l| {
                if !l.contains("<FILL") || l.trim_start().starts_with('#') {
                    return l.to_string();
                }
                let k = l.split('=').next().unwrap().trim();
                let v = match k {
                    "freeze_commit" => FC.to_string(),
                    "seed" => seed_from_freeze(FC),
                    "probe_sha256" | "x4svc_sha256" | "harness_sha256" | "golden" => h.clone(),
                    "excluded_images_at_signing" => "gems-worker".to_string(),
                    "param" => "1761170".to_string(),
                    "overhead_s" => "5".to_string(),
                    "time_cap_s" => "600".to_string(),
                    "t_run_plan_s" => "150".to_string(),
                    other => panic!("unexpected placeholder key {other}"),
                };
                format!("{} = {}", k, v)
            })
            .collect::<Vec<_>>()
            .join("\n")
    }

    #[test]
    fn the_committed_template_filled_is_the_record() {
        let t = filled_template();
        let c = parse(&t).unwrap_or_else(|e| panic!("{e}"));
        assert!(pilot_rules(&c).is_empty());
        assert_eq!(c.excluded_images_at_signing.as_deref(), Some(&["gems-worker".to_string()][..]));
        // the unfilled template never parses
        let raw = std::fs::read_to_string(concat!(env!("CARGO_MANIFEST_DIR"), "/../../pilot/pilot.cfg.template")).unwrap();
        assert!(parse(&raw).is_err());
    }

    #[test]
    fn the_canonical_configuration_hash_ignores_only_integrity_cleared() {
        let p = filled_pilot();
        let h = config_canonical_sha256(&p);
        let cleared = p.replacen("session_setup_s = 120", &format!("session_setup_s = 120\nintegrity_cleared = mb-q4-avx512-03@{}", "e".repeat(40)), 1);
        assert_eq!(config_canonical_sha256(&cleared), h);
        // CRLF and LF copies of one file hash alike; any other change does not
        assert_eq!(config_canonical_sha256(&p.replace('\n', "\r\n")), h);
        assert_ne!(config_canonical_sha256(&p.replacen("overhead_s = 5", "overhead_s = 6", 1)), h);
        assert_ne!(config_canonical_sha256(&p.replacen("session_setup_s = 120", "session_setup_s = 120\n# integrity_cleared = x", 1)), h);
        assert_ne!(config_canonical_sha256(&format!("{}\nseed = 0", p)), h);
        assert_eq!(config_canonical_sha256("a = 1\nb = 2\n"), config_canonical_sha256("a = 1\nb = 2"));
        assert_eq!(config_canonical_sha256("a = 1\nb = 2\n"), sha256::hex(&sha256::digest(b"a = 1\nb = 2\n")));
    }

    #[test]
    fn pacific_time_rules() {
        // 2026-10-23 15:02:09 UTC = 08:02:09 PDT
        let t = days_from_civil(2026, 10, 23) * 86400 + 15 * 3600 + 2 * 60 + 9;
        assert_eq!(pt_string(t), "2026-10-23 08:02:09 PDT");
        assert_eq!(civil_from_days(days_from_civil(2026, 10, 23)), (2026, 10, 23));
        assert_eq!(weekday(days_from_civil(2026, 10, 23)), 5); // a Friday
        // DST ends Sun 2026-11-01 at 09:00 UTC; starts Sun 2026-03-08 at 10:00 UTC
        let end = days_from_civil(2026, 11, 1) * 86400 + 9 * 3600;
        assert_eq!(pt_offset_secs(end - 1), -7 * 3600);
        assert_eq!(pt_offset_secs(end), -8 * 3600);
        let start = days_from_civil(2026, 3, 8) * 86400 + 10 * 3600;
        assert_eq!(pt_offset_secs(start - 1), -8 * 3600);
        assert_eq!(pt_offset_secs(start), -7 * 3600);
        // round trip, and the repeated hour resolves to the earlier instant
        assert_eq!(pt_local_to_utc(pt_local(t)), t);
        let rep = days_from_civil(2026, 11, 1) * 86400 + 3600 + 1800; // 01:30 local, twice
        assert_eq!(pt_local_to_utc(rep), days_from_civil(2026, 11, 1) * 86400 + 8 * 3600 + 1800);
    }

    #[test]
    fn night_window_bounds() {
        let c = parse(DRY).unwrap();
        // 2026-10-25 23:30 PDT = 2026-10-26 06:30 UTC: inside the night of 10-25
        let t = days_from_civil(2026, 10, 26) * 86400 + 6 * 3600 + 30 * 60;
        let (night, start, last, end) = night_window(&c, t).unwrap();
        assert_eq!(civil_from_days(night), (2026, 10, 25));
        assert_eq!(pt_string(start), "2026-10-25 23:00:00 PDT");
        assert_eq!(pt_string(last), "2026-10-26 06:45:00 PDT");
        assert_eq!(pt_string(end), "2026-10-26 07:00:00 PDT");
        // 08:00 PT is outside
        assert!(night_window(&c, days_from_civil(2026, 10, 26) * 86400 + 15 * 3600).is_none());
        // 06:59 PT belongs to the previous evening's night
        let t2 = days_from_civil(2026, 10, 26) * 86400 + 13 * 3600 + 59 * 60;
        assert_eq!(civil_from_days(night_window(&c, t2).unwrap().0), (2026, 10, 25));
    }
}
