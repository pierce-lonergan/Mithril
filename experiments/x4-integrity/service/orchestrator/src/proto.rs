//! Protocol v2 between the C harness (child) and this orchestrator, and the run-acceptance contract
//! (MEASUREMENT-SERVICE.md section 3 steps 6-8a). Mirrors `service/proto/x4proto.h`; the unit tests
//! below pin every shared constant.
//!
//! Trust classes. Every check is labelled with where its evidence comes from:
//! - `OutOfProcess`: computed here from what the orchestrator observed itself (its QPC bracket, the
//!   process cycle count it sampled at START/STOP/exit, its own copies and hashes of the output
//!   section it owns, the exit code, the frame order). No workload code runs in this process.
//! - `InProcess`: a field the harness computed inside the child, which shares its address space with
//!   the workload. Precise for cooperative workloads; forgeable by an adversarial one. For untrusted
//!   workloads only `OutOfProcess` checks may be cited as detector evidence (IMPLEMENTATION.md).
//! A run is accepted only if *no* check of either class fails. All failing checks are reported.
//!
//! Cycle partition (review round 3, 2026-10-16/17). The frames are written by a process the workload
//! shares, so a hostile workload can forge the whole stream (START, STOP, CENSUS, REPORT) and exit
//! itself. The out-of-process checks therefore charge every CPU cycle of the child, from launch to
//! exit, to exactly one of three windows, each with its own bound, wherever the frames land:
//! pre-START (launch -> START receipt: `init_max_ns` wall and `init_max_cycles`, so work laundered
//! into the untimed init is bounded), the timed window (START -> STOP receipt: at most
//! `declared_threads + extra_cores` cores' worth of cycles per wall-second, so parallel work that
//! exits before the in-process census still counts), and post-STOP (`kappa_post_cycles`, a coarse
//! ceiling, never cited as the fine a3b detector). The output must equal the golden in the
//! orchestrator's own copy at STOP receipt, so a forged early STOP cannot shorten the window below
//! the work that produced the output.

use crate::sha256;

pub const MAGIC: u32 = 0x3450_3458;
pub const VERSION: u32 = 2;

pub const T_HELLO: u32 = 1;
pub const T_START: u32 = 2;
pub const T_STOP: u32 = 3;
pub const T_CENSUS: u32 = 4;
pub const T_REPORT: u32 = 5;
pub const T_FAIL: u32 = 6;
pub const T_PROBES: u32 = 7;

pub const PAGE: u64 = 4096;
pub const OUT_ALIGN: u64 = 64;
pub const POISON_BYTE: u8 = 0xA5;
pub const POISON_WORD: u64 = 0xA5A5_A5A5_A5A5_A5A5;
pub const MXCSR_DEFAULT: u64 = 0x1F80;
pub const MXCSR_CTRL_MASK: u64 = 0xFFC0;
pub const THREAD_PRIORITY_NORMAL: u64 = 0;

/// X4P_OUT_OFFSET: at least one page, and the extent ends on a page boundary.
pub fn out_offset(n: u64) -> u64 {
    PAGE + ((PAGE - (n % PAGE)) % PAGE)
}
/// X4P_SECTION_BYTES: head + extent + one trailing (guard) page.
pub fn section_bytes(n: u64) -> u64 {
    out_offset(n) + n + PAGE
}
/// out_bytes must be a non-zero multiple of 64 (both sides reject anything else).
pub fn out_bytes_valid(n: u64) -> bool {
    n != 0 && n % OUT_ALIGN == 0
}

/// HELLO payload indices.
pub mod hf {
    pub const VERSION: usize = 0;
    pub const PID: usize = 1;
    pub const PAGE: usize = 2;
    pub const SECTION_BYTES: usize = 3;
    pub const OUT_OFFSET: usize = 4;
    pub const OUT_BYTES: usize = 5;
    pub const N: usize = 6;
}

/// REPORT payload indices (x4proto.h enum x4p_report_field, v2).
pub mod rf {
    pub const VERSION: usize = 0;
    pub const T0_NS: usize = 1;
    pub const T1_NS: usize = 2;
    pub const HASH0: usize = 3;
    pub const OUT_BYTES: usize = 7;
    pub const POISON_RESIDUAL_WORDS: usize = 8;
    pub const SLACK_MODIFIED_BYTES: usize = 9;
    pub const SALT: usize = 10;
    pub const THREADS_AT_CENSUS: usize = 11;
    pub const NEW_UNREGISTERED: usize = 12;
    pub const REGISTERED_CREATED: usize = 13;
    pub const REGISTERED_UNPARKED: usize = 14;
    pub const POST_T1_VIOLATIONS: usize = 15;
    pub const MXCSR_BAD_THREADS: usize = 16;
    pub const MXCSR_ENTRY_BAD: usize = 17;
    pub const AFFINITY_BAD: usize = 18;
    pub const PRIORITY_BAD: usize = 19;
    pub const PRIORITY_CLASS: usize = 20;
    pub const PROCESS_AFFINITY: usize = 21;
    pub const TSC_HZ: usize = 22;
    pub const WORKLOAD_RC: usize = 23;
    pub const IO_OUTSTANDING: usize = 24;
    pub const CENSUS_ERRORS: usize = 25;
    pub const HARNESS_TID: usize = 26;
    pub const MXCSR_HARNESS: usize = 27;
    pub const POST_T1_MAX_CYCLES: usize = 28;
    pub const SELFCHECK_FLAGS: usize = 29;
    pub const MXCSR_EXIT_BAD: usize = 30;
    pub const PRIORITY_EXIT_BAD: usize = 31;
    pub const PRIORITY_HARNESS: usize = 32;
    pub const POST_T1_NEW_THREADS: usize = 33;
    pub const T1_SNAP_LAG_NS: usize = 34;
    pub const EXPECTED_AFFINITY: usize = 35;
    pub const OUT_OFFSET: usize = 36;
    pub const FREEZE_OK: usize = 37;
    pub const COUNT: usize = 38;
}
pub const R_COUNT: usize = rf::COUNT;
pub const CENSUS_W: usize = 8;
pub const PROBE_W: usize = 6;
/// Largest census the harness can send: (X4H_MAX_THREADS + 64) rows.
pub const CENSUS_MAX_ROWS: usize = 2048 + 64;
/// Largest payload accepted from the child (bytes); anything larger is a protocol violation.
pub const MAX_PAYLOAD: usize = CENSUS_MAX_ROWS * CENSUS_W * 8;

/// FAIL codes (x4p_fail_code).
pub fn fail_code_name(c: u64) -> &'static str {
    match c {
        1 => "ARGS",
        2 => "MAP",
        3 => "WORKLOAD",
        4 => "FAULT",
        5 => "JOIN_TIMEOUT",
        6 => "INTERNAL",
        _ => "UNKNOWN",
    }
}

/// One decoded frame.
#[derive(Clone, Debug, PartialEq)]
pub struct Frame {
    pub mtype: u32,
    pub seq: u32,
    pub vals: Vec<u64>,
}

/// Decode one frame at the start of `buf`. `Ok(None)` means the frame is not complete yet (the caller
/// keeps the bytes and reads more); `Ok(Some((frame, consumed)))` returns the exact byte count used.
pub fn decode_one(buf: &[u8]) -> Result<Option<(Frame, usize)>, String> {
    if buf.len() < 16 {
        return Ok(None);
    }
    let word = |i: usize| u32::from_le_bytes([buf[i], buf[i + 1], buf[i + 2], buf[i + 3]]);
    let (magic, mtype, plen, seq) = (word(0), word(4), word(8) as usize, word(12));
    if magic != MAGIC {
        return Err(format!("bad magic {:08x}", magic));
    }
    if plen % 8 != 0 || plen > MAX_PAYLOAD {
        return Err(format!("bad payload length {}", plen));
    }
    if buf.len() < 16 + plen {
        return Ok(None);
    }
    let vals = (0..plen / 8)
        .map(|i| {
            let o = 16 + 8 * i;
            let mut b = [0u8; 8];
            b.copy_from_slice(&buf[o..o + 8]);
            u64::from_le_bytes(b)
        })
        .collect();
    Ok(Some((Frame { mtype, seq, vals }, 16 + plen)))
}

/// Incremental framer: feed bytes as they arrive, get back only complete frames. A frame split across
/// two reads is held until it is complete (it is never mis-stamped or skipped).
#[derive(Default)]
pub struct Framer {
    buf: Vec<u8>,
}

impl Framer {
    pub fn new() -> Self {
        Framer { buf: Vec::new() }
    }
    pub fn push(&mut self, bytes: &[u8]) -> Result<Vec<Frame>, String> {
        self.buf.extend_from_slice(bytes);
        let mut out = Vec::new();
        let mut off = 0usize;
        while let Some((f, used)) = decode_one(&self.buf[off..])? {
            out.push(f);
            off += used;
        }
        self.buf.drain(..off);
        Ok(out)
    }
    /// Bytes held that do not form a complete frame (must be 0 at EOF).
    pub fn pending(&self) -> usize {
        self.buf.len()
    }
}

/// Decode a whole byte stream; trailing bytes that do not form a frame are an error.
pub fn parse_all(buf: &[u8]) -> Result<Vec<Frame>, String> {
    let mut f = Framer::new();
    let frames = f.push(buf)?;
    if f.pending() != 0 {
        return Err(format!("{} trailing bytes", f.pending()));
    }
    Ok(frames)
}

/// Which exchange the child is in.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Exchange {
    /// HELLO(0) START(1) STOP(2) CENSUS(3) REPORT(4)
    Run,
    /// HELLO(0) PROBES(1)
    SelfTest,
}

impl Exchange {
    fn expected(self) -> &'static [u32] {
        match self {
            Exchange::Run => &[T_HELLO, T_START, T_STOP, T_CENSUS, T_REPORT],
            Exchange::SelfTest => &[T_HELLO, T_PROBES],
        }
    }
}

fn payload_ok(mtype: u32, n: usize) -> bool {
    match mtype {
        T_HELLO => n == hf::N,
        T_START | T_STOP => n == 0,
        T_CENSUS => n % CENSUS_W == 0 && n / CENSUS_W <= CENSUS_MAX_ROWS,
        T_REPORT => n == R_COUNT,
        T_FAIL => n == 4,
        T_PROBES => n % PROBE_W == 0,
        _ => false,
    }
}

/// Strict, online frame-order validation. The exchange is exactly the expected sequence with
/// `seq` equal to the position, or a prefix of it followed by exactly one FAIL whose `seq` is its
/// position. Any duplicate, reordering, bad seq, unknown type, wrong payload size or any frame after
/// the terminal frame is a protocol violation (an out-of-process integrity failure).
#[derive(Clone, Debug)]
pub struct SeqValidator {
    ex: Exchange,
    pos: u32,
    terminal: bool,
    pub failed_frame: Option<Vec<u64>>,
}

impl SeqValidator {
    pub fn new(ex: Exchange) -> Self {
        SeqValidator { ex, pos: 0, terminal: false, failed_frame: None }
    }
    /// Accept the next frame or return the violation.
    pub fn accept(&mut self, f: &Frame) -> Result<(), String> {
        if self.terminal {
            return Err(format!("frame type {} after the terminal frame", f.mtype));
        }
        if f.seq != self.pos {
            return Err(format!("frame type {} has seq {} at position {}", f.mtype, f.seq, self.pos));
        }
        if !payload_ok(f.mtype, f.vals.len()) {
            return Err(format!("frame type {} has a bad payload of {} words", f.mtype, f.vals.len()));
        }
        if f.mtype == T_FAIL {
            self.terminal = true;
            self.failed_frame = Some(f.vals.clone());
            self.pos += 1;
            return Ok(());
        }
        let exp = self.ex.expected();
        let want = exp[self.pos as usize];
        if f.mtype != want {
            return Err(format!("frame type {} at position {} (expected {})", f.mtype, self.pos, want));
        }
        self.pos += 1;
        if self.pos as usize == exp.len() {
            self.terminal = true;
        }
        Ok(())
    }
    /// The exchange reached its last expected frame (not a FAIL).
    pub fn complete(&self) -> bool {
        self.terminal && self.failed_frame.is_none()
    }
    pub fn position(&self) -> u32 {
        self.pos
    }
}

/// Validate a complete frame list (offline form of `SeqValidator`).
pub fn validate_sequence(ex: Exchange, frames: &[Frame]) -> Result<(), String> {
    let mut v = SeqValidator::new(ex);
    for f in frames {
        v.accept(f)?;
    }
    if !v.terminal {
        return Err(format!("sequence ended at position {} without its terminal frame", v.pos));
    }
    Ok(())
}

/// The typed REPORT.
#[derive(Clone, Debug)]
pub struct Report {
    pub v: Vec<u64>,
}

impl Report {
    pub fn from_frame(f: &Frame) -> Result<Report, String> {
        if f.mtype != T_REPORT || f.vals.len() != R_COUNT {
            return Err(format!("not a v{} REPORT ({} words)", VERSION, f.vals.len()));
        }
        Ok(Report { v: f.vals.clone() })
    }
    pub fn get(&self, i: usize) -> u64 {
        self.v[i]
    }
    /// t1 - t0, or None when t1 <= t0 (a poked or zero-length interval is never a duration).
    pub fn delta_h_ns(&self) -> Option<u64> {
        let (t0, t1) = (self.v[rf::T0_NS], self.v[rf::T1_NS]);
        if t1 > t0 {
            Some(t1 - t0)
        } else {
            None
        }
    }
    pub fn harness_hash(&self) -> [u64; 4] {
        [self.v[rf::HASH0], self.v[rf::HASH0 + 1], self.v[rf::HASH0 + 2], self.v[rf::HASH0 + 3]]
    }
}

/// Where a check's evidence comes from (see the module comment).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum TrustClass {
    OutOfProcess,
    InProcess,
}

impl TrustClass {
    pub fn label(self) -> &'static str {
        match self {
            TrustClass::OutOfProcess => "out-of-process",
            TrustClass::InProcess => "in-process",
        }
    }
}

/// One failed check.
#[derive(Clone, Debug, PartialEq)]
pub struct Failure {
    pub check: &'static str,
    pub class: TrustClass,
    pub detail: String,
}

/// The verdict on one run.
#[derive(Clone, Debug, PartialEq)]
pub enum RunVerdict {
    Accept,
    /// The timed region did not end before the time cap; the orchestrator stopped the job. Not an
    /// integrity failure: the session scores it as a slow outlier (MEASUREMENT section 8.7).
    TimeCapped,
    IntegrityFail(Vec<Failure>),
}

impl RunVerdict {
    pub fn failed_checks(&self) -> Vec<&'static str> {
        match self {
            RunVerdict::IntegrityFail(v) => v.iter().map(|f| f.check).collect(),
            _ => Vec::new(),
        }
    }
    pub fn is_accept(&self) -> bool {
        matches!(self, RunVerdict::Accept)
    }
}

/// What the orchestrator itself observed for one run (all out-of-process).
#[derive(Clone, Debug, Default)]
pub struct Observed {
    /// What the orchestrator asked for.
    pub requested_out_bytes: u64,
    pub salt: u64,
    pub child_pid: u64,
    pub declared_affinity: u64,
    pub declared_priority_class: u64,
    pub golden_hash: [u64; 4],
    /// Frame-order violation, if any (the job is terminated at once when one is seen).
    pub protocol_error: Option<String>,
    pub hello: Option<Vec<u64>>,
    pub fail_frame: Option<Vec<u64>>,
    pub report: Option<Report>,
    /// QPC stamps (ns since the orchestrator resumed the child's first thread) at receipt of HELLO,
    /// START and STOP. `start_ns` is therefore the out-of-process pre-START (init) wall time.
    pub hello_ns: Option<u64>,
    pub start_ns: Option<u64>,
    pub stop_ns: Option<u64>,
    /// QueryProcessCycleTime of the child at HELLO, START, STOP and after exit. `cycles_start` is the
    /// child's whole pre-START CPU (loader, static initialisers, harness setup, workload init).
    pub cycles_hello: Option<u64>,
    pub cycles_start: Option<u64>,
    pub cycles_stop: Option<u64>,
    pub cycles_exit: Option<u64>,
    /// Job user+kernel time (100 ns, clock-tick granular): descriptive only.
    pub job_cpu_after_stop_100ns: Option<u64>,
    /// Orchestrator SHA-256 of the extent copied when STOP arrived, and again after exit.
    pub hash_at_stop: Option<[u64; 4]>,
    pub hash_at_exit: Option<[u64; 4]>,
    /// Bytes outside the extent that changed: head bytes not equal to the poison byte, trailing-page
    /// bytes not equal to zero (`outside_changed`).
    pub outside_changed_at_stop: u64,
    pub outside_changed_at_exit: u64,
    /// Aligned words of the extent still equal to the poison word or the salt, at STOP.
    pub poison_residual_at_stop: Option<u64>,
    pub exit_code: Option<u32>,
    /// The process did not exit on its own within the grace period after its last frame.
    pub no_exit: bool,
    /// The watchdog stopped the job at the time cap.
    pub watchdog_fired: bool,
    pub peak_process_memory: u64,
    /// Threads the run type declares (the comparison is at matched thread count); 0 fails closed.
    pub declared_threads: u32,
    /// Process-cycle units per second of one running thread, calibrated by the orchestrator on its
    /// own thread (QueryThreadCycleTime against QPC), never the harness-reported TSC rate. 0 = not
    /// calibrated, which fails the window check closed.
    pub cycle_rate_hz: u64,
}

/// Pilot-derived integrity tolerances (section 5.4). Every value is provisional until the X4 noise
/// pilot fills it in by the frozen rule (prereg section 7; docs/m0/prereg/X4-noise-pilot.md).
#[derive(Clone, Copy, Debug)]
pub struct Tolerances {
    /// The pilot's largest |dh - do| (ns).
    pub pilot_max_abs_diff_ns: u64,
    /// kappa_post in CPU cycles of the child process after STOP (QueryProcessCycleTime). A coarse
    /// ceiling: it must exceed the harness's own post-STOP census and hash.
    pub kappa_post_cycles: u64,
    /// Pre-START bounds (launch -> START receipt): wall ns and child process cycles. Per run type.
    pub init_max_ns: u64,
    pub init_max_cycles: u64,
    /// Cores allowed in the timed window beyond the declared threads, in thousandths of a core.
    pub extra_cores_milli: u64,
}

impl Tolerances {
    /// tau_clock = max(1 ms, 2 * pilot max |dh - do|), and it must not exceed 0.1% of delta_o.
    /// When the floor or the pilot term exceeds the cap, the run is too short for the bracket and is
    /// ineligible (None): the stricter reading of the rule, never a loosened tolerance.
    pub fn tau_clock(pilot_max_abs_diff_ns: u64, delta_o_ns: u64) -> Option<u64> {
        let base = pilot_max_abs_diff_ns.saturating_mul(2).max(1_000_000);
        let cap = delta_o_ns / 1000;
        if base > cap {
            None
        } else {
            Some(base)
        }
    }
}

/// Count aligned words equal to the poison word (or the salt in the first and last 8 words).
pub fn poison_residual(extent: &[u8], salt: u64) -> u64 {
    let words = extent.len() / 8;
    let mut n = 0u64;
    for i in 0..words {
        let mut b = [0u8; 8];
        b.copy_from_slice(&extent[8 * i..8 * i + 8]);
        let v = u64::from_le_bytes(b);
        let want = if i < 8 || i + 8 >= words { salt } else { POISON_WORD };
        if v == want {
            n += 1;
        }
    }
    n
}

/// Bytes outside the extent that changed, from the orchestrator's own read-only view: head bytes that
/// are not the poison byte, plus trailing-page bytes that are not zero. The trailing page is
/// PAGE_NOACCESS only in the child's own view, which a workload can lift (VirtualProtect) or bypass
/// (a second view of the section), so the orchestrator compares it itself (review round 3, R1-5). A
/// pagefile-backed section starts zero-filled, so any non-zero trailing byte is a write past the
/// extent; nothing in the protocol writes there.
pub fn outside_changed(section: &[u8], out_bytes: u64) -> u64 {
    let off = out_offset(out_bytes) as usize;
    let end = off + out_bytes as usize;
    let head = section[..off].iter().filter(|&&b| b != POISON_BYTE).count();
    let tail = section[end..].iter().filter(|&&b| b != 0).count();
    (head + tail) as u64
}

/// SHA-256 of the extent in the report's four-u64 shape (bytes in order).
pub fn extent_hash(section: &[u8], out_bytes: u64) -> [u64; 4] {
    let off = out_offset(out_bytes) as usize;
    sha256::digest_u64x4(&section[off..off + out_bytes as usize])
}

/// The full run-acceptance contract. Every check is evaluated; Accept only if none fails.
pub fn decide_run(o: &Observed, tol: &Tolerances) -> RunVerdict {
    use TrustClass::{InProcess as IP, OutOfProcess as OOP};
    let mut f: Vec<Failure> = Vec::new();
    macro_rules! fail {
        ($check:expr, $class:expr, $detail:expr $(,)?) => {
            f.push(Failure { check: $check, class: $class, detail: $detail })
        };
    }

    // ---- out-of-process: protocol, exit, bracket, accounting, the orchestrator's own copies
    if let Some(e) = &o.protocol_error {
        fail!("protocol", OOP, e.clone());
    }
    if let Some(ff) = &o.fail_frame {
        fail!("harness_fail", IP, format!("FAIL {} ({:?})", fail_code_name(ff[0]), ff));
    }
    let stopped = o.stop_ns.is_some();
    if o.watchdog_fired && !stopped && o.protocol_error.is_none() && o.fail_frame.is_none() {
        return RunVerdict::TimeCapped;
    }
    if o.watchdog_fired && stopped {
        fail!("no_exit", OOP, "the watchdog stopped the job after STOP".into());
    }
    if o.no_exit {
        fail!("no_exit", OOP, "the child did not exit after its last frame".into());
    }
    match o.exit_code {
        Some(0) => {}
        Some(c) => fail!("exit_code", OOP, format!("exit code {:#x}", c)),
        None => fail!("exit_code", OOP, "no exit code".into()),
    }
    let (start, stop) = (o.start_ns, o.stop_ns);
    let delta_o = match (start, stop) {
        (Some(a), Some(b)) if b > a => Some(b - a),
        _ => {
            fail!("start_stop", OOP, format!("START {:?} / STOP {:?} not both observed in order", start, stop));
            None
        }
    };
    // pre-START window: work laundered into the untimed init (or before main) is bounded here, from
    // the orchestrator's own stamps, whoever wrote the START frame (review round 3, R1-1)
    if let Some(s) = start {
        if s > tol.init_max_ns {
            fail!("pre_start_wall", OOP, format!("{} ns from launch to START > init_max {} ns", s, tol.init_max_ns));
        }
        match o.cycles_start {
            Some(c) if c > tol.init_max_cycles => {
                fail!("pre_start_cycles", OOP, format!("{} cycles before START > init_max {}", c, tol.init_max_cycles))
            }
            Some(_) => {}
            None => fail!("pre_start_cycles", OOP, "cycle count at START unavailable".into()),
        }
    }
    // timed window: at most declared_threads + extra cores' worth of cycles per wall-second, so
    // parallel work by threads that exit before the census still counts (review round 3, R1-2).
    // Evaluated where the bracket is eligible; a shorter run is already ineligible.
    if let (Some(d_o), Some(cs), Some(ct)) = (delta_o, o.cycles_start, o.cycles_stop) {
        if Tolerances::tau_clock(tol.pilot_max_abs_diff_ns, d_o).is_some() {
            if o.declared_threads == 0 || o.cycle_rate_hz == 0 {
                fail!("window_cores", OOP, format!("declared_threads {} / cycle rate {} not set", o.declared_threads, o.cycle_rate_hz));
            } else {
                let used = ct.saturating_sub(cs) as u128;
                let milli = o.declared_threads as u128 * 1000 + tol.extra_cores_milli as u128;
                let allowed = milli * d_o as u128 * o.cycle_rate_hz as u128 / 1_000_000_000_000u128;
                if used > allowed {
                    let cores = used as f64 / (d_o as f64 / 1e9 * o.cycle_rate_hz as f64);
                    fail!(
                        "window_cores",
                        OOP,
                        format!("{:.2} cores used in [START, STOP] > declared {} + {:.3}", cores, o.declared_threads, tol.extra_cores_milli as f64 / 1000.0),
                    );
                }
            }
        }
    }
    if let (Some(cs), Some(ce)) = (o.cycles_stop, o.cycles_exit) {
        let post = ce.saturating_sub(cs);
        if post > tol.kappa_post_cycles {
            fail!("post_stop_cycles", OOP, format!("{} cycles after STOP > kappa_post {}", post, tol.kappa_post_cycles));
        }
    } else if stopped {
        fail!("post_stop_cycles", OOP, "cycle count at STOP or exit unavailable".into());
    }
    match (o.hash_at_stop, o.hash_at_exit) {
        (Some(hs), Some(he)) => {
            if hs != he {
                fail!("rehash_stop_exit", OOP, "output changed after STOP (copy at STOP != copy at exit)".into());
            }
            if hs != o.golden_hash {
                fail!("golden_hash", OOP, "output hash at STOP != golden/incumbent".into());
            }
        }
        _ => {
            if stopped {
                fail!("golden_hash", OOP, "no orchestrator copy of the output".into());
            }
        }
    }
    if o.outside_changed_at_stop != 0 || o.outside_changed_at_exit != 0 {
        fail!(
            "outside_extent_oop",
            OOP,
            format!("bytes outside the extent changed: {} at STOP, {} at exit", o.outside_changed_at_stop, o.outside_changed_at_exit),
        );
    }
    if let Some(r) = o.poison_residual_at_stop {
        if r != 0 {
            fail!("poison_residual_oop", OOP, format!("{} poison/salt words left in the extent at STOP", r));
        }
    }

    // ---- HELLO (child-written, checked against what the orchestrator asked for)
    if let Some(h) = &o.hello {
        let n = o.requested_out_bytes;
        let ok = h[hf::VERSION] == VERSION as u64
            && h[hf::PID] == o.child_pid
            && h[hf::PAGE] == PAGE
            && h[hf::SECTION_BYTES] == section_bytes(n)
            && h[hf::OUT_OFFSET] == out_offset(n)
            && h[hf::OUT_BYTES] == n;
        if !ok {
            fail!("hello", IP, format!("HELLO {:?} does not match the launch (pid {}, out_bytes {})", h, o.child_pid, n));
        }
    }

    // ---- the REPORT (in-process fields) and the bracket that compares it with what we saw
    let rep = match &o.report {
        Some(r) => r,
        None => {
            if o.fail_frame.is_none() && o.protocol_error.is_none() {
                fail!("report", OOP, "no REPORT".into());
            }
            return finish(f);
        }
    };
    let g = |i: usize| rep.get(i);
    if g(rf::VERSION) != VERSION as u64 {
        fail!("version", IP, format!("report version {}", g(rf::VERSION)));
    }
    if g(rf::OUT_BYTES) != o.requested_out_bytes || g(rf::OUT_OFFSET) != out_offset(o.requested_out_bytes) {
        fail!("layout", IP, format!("out_bytes {} / offset {}", g(rf::OUT_BYTES), g(rf::OUT_OFFSET)));
    }
    if g(rf::SALT) != o.salt {
        fail!("salt", IP, "report salt != the orchestrator's".into());
    }
    if o.declared_affinity != 0 && g(rf::EXPECTED_AFFINITY) != o.declared_affinity {
        fail!("expected_affinity", IP, format!("harness compared against {:#x}, declared {:#x}", g(rf::EXPECTED_AFFINITY), o.declared_affinity));
    }
    if g(rf::PRIORITY_CLASS) != o.declared_priority_class {
        fail!("priority_class", IP, format!("priority class {:#x}", g(rf::PRIORITY_CLASS)));
    }
    let dh = rep.delta_h_ns();
    if dh.is_none() {
        fail!("t1_le_t0", IP, format!("t1 {} <= t0 {}", g(rf::T1_NS), g(rf::T0_NS)));
    }
    if let (Some(dh), Some(d_o)) = (dh, delta_o) {
        match Tolerances::tau_clock(tol.pilot_max_abs_diff_ns, d_o) {
            None => fail!("bracket_too_short", OOP, format!("delta_o {} ns: tau_clock floor exceeds 0.1% of the run", d_o)),
            Some(tau) => {
                let diff = dh.abs_diff(d_o);
                if diff > tau {
                    fail!("clock_bracket", OOP, format!("|dh - do| = {} ns > tau_clock {} ns (a5)", diff, tau));
                }
            }
        }
    }
    if let Some(hs) = o.hash_at_stop {
        if rep.harness_hash() != hs {
            fail!("harness_vs_orch_hash", OOP, "harness hash != orchestrator copy at STOP".into());
        }
    }
    let nz = |i: usize| g(i) != 0;
    let checks: [(&'static str, usize, &str); 14] = [
        ("census_errors", rf::CENSUS_ERRORS, "census/freeze API failures (fails closed)"),
        ("io_outstanding", rf::IO_OUTSTANDING, "I/O not joined"),
        ("new_unregistered", rf::NEW_UNREGISTERED, "threads not created through the wrapper (a3/a3b)"),
        ("registered_unparked", rf::REGISTERED_UNPARKED, "registered threads unjoined/unparked at t1 (a3)"),
        ("post_t1_cpu", rf::POST_T1_VIOLATIONS, "threads over their post-t1 CPU allowance (a3b)"),
        ("post_t1_new_threads", rf::POST_T1_NEW_THREADS, "threads created after t1 (a3b)"),
        ("mxcsr_threads", rf::MXCSR_BAD_THREADS, "threads with non-default MXCSR at the census (a9)"),
        ("mxcsr_entry", rf::MXCSR_ENTRY_BAD, "registered threads with non-default MXCSR at entry (a9)"),
        ("mxcsr_exit", rf::MXCSR_EXIT_BAD, "registered threads with non-default MXCSR at return (a9)"),
        ("affinity", rf::AFFINITY_BAD, "threads off the declared affinity mask (a31)"),
        ("priority", rf::PRIORITY_BAD, "threads not at normal priority at the census (a31)"),
        ("priority_exit", rf::PRIORITY_EXIT_BAD, "registered threads not at normal priority at return (a31)"),
        ("poison_residual", rf::POISON_RESIDUAL_WORDS, "poison words left in the output (a4/a13)"),
        ("slack_modified", rf::SLACK_MODIFIED_BYTES, "head bytes before the extent changed"),
    ];
    for (name, idx, what) in checks {
        if nz(idx) {
            fail!(name, IP, format!("{} = {}: {}", name, g(idx), what));
        }
    }
    if g(rf::FREEZE_OK) != 1 {
        fail!("freeze", IP, "VirtualProtect(PAGE_READONLY) of the output view failed".into());
    }
    if g(rf::MXCSR_HARNESS) & MXCSR_CTRL_MASK != MXCSR_DEFAULT {
        fail!("mxcsr_harness", IP, format!("harness-thread MXCSR {:#x} after run() (a9)", g(rf::MXCSR_HARNESS)));
    }
    if g(rf::PRIORITY_HARNESS) != THREAD_PRIORITY_NORMAL {
        fail!("priority_harness", IP, format!("harness-thread priority {} after run() (a31)", g(rf::PRIORITY_HARNESS) as i64));
    }
    if g(rf::WORKLOAD_RC) != 0 {
        fail!("workload_rc", IP, format!("workload status {}", g(rf::WORKLOAD_RC) as i64));
    }
    finish(f)
}

fn finish(f: Vec<Failure>) -> RunVerdict {
    if f.is_empty() {
        RunVerdict::Accept
    } else {
        RunVerdict::IntegrityFail(f)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn frame(mtype: u32, seq: u32, n: usize) -> Frame {
        Frame { mtype, seq, vals: vec![0; n] }
    }
    fn good_run() -> Vec<Frame> {
        vec![frame(T_HELLO, 0, hf::N), frame(T_START, 1, 0), frame(T_STOP, 2, 0), frame(T_CENSUS, 3, 8), frame(T_REPORT, 4, R_COUNT)]
    }
    fn bytes(fs: &[Frame]) -> Vec<u8> {
        let mut b = Vec::new();
        for f in fs {
            b.extend_from_slice(&MAGIC.to_le_bytes());
            b.extend_from_slice(&f.mtype.to_le_bytes());
            b.extend_from_slice(&((f.vals.len() * 8) as u32).to_le_bytes());
            b.extend_from_slice(&f.seq.to_le_bytes());
            for v in &f.vals {
                b.extend_from_slice(&v.to_le_bytes());
            }
        }
        b
    }

    #[test]
    fn layout_and_counts_match_x4proto_h() {
        assert_eq!(R_COUNT, 38);
        assert_eq!(rf::FREEZE_OK + 1, R_COUNT);
        assert_eq!(hf::N, 6);
        assert_eq!(out_offset(4096), 4096);
        assert_eq!(out_offset(64), 4096 + 4032);
        assert_eq!((out_offset(64) + 64) % PAGE, 0);
        assert_eq!(section_bytes(4096), 4096 + 4096 + 4096);
        assert!(out_bytes_valid(4096) && !out_bytes_valid(0) && !out_bytes_valid(100));
    }

    #[test]
    fn framer_holds_split_frames() {
        let b = bytes(&good_run());
        let mut fr = Framer::new();
        let mut got = Vec::new();
        for chunk in b.chunks(7) {
            got.extend(fr.push(chunk).unwrap());
        }
        assert_eq!(fr.pending(), 0);
        assert_eq!(got, good_run());
        assert!(parse_all(&b[..b.len() - 3]).is_err());
    }

    #[test]
    fn strict_order_accepts_only_the_exact_sequence() {
        assert!(validate_sequence(Exchange::Run, &good_run()).is_ok());
        // duplicate STOP (a forged early STOP followed by the real one)
        let mut dup = good_run();
        dup.insert(3, frame(T_STOP, 3, 0));
        assert!(validate_sequence(Exchange::Run, &dup).is_err());
        // forged STOP with a foreign seq
        let mut bad = good_run();
        bad[2].seq = 999;
        assert!(validate_sequence(Exchange::Run, &bad).is_err());
        // reordered
        let mut re = good_run();
        re.swap(3, 4);
        assert!(validate_sequence(Exchange::Run, &re).is_err());
        // extra frame after REPORT
        let mut extra = good_run();
        extra.push(frame(T_FAIL, 5, 4));
        assert!(validate_sequence(Exchange::Run, &extra).is_err());
        // truncated
        assert!(validate_sequence(Exchange::Run, &good_run()[..3]).is_err());
        // prefix + FAIL is a complete (failed) exchange
        let pf = vec![frame(T_HELLO, 0, hf::N), frame(T_FAIL, 1, 4)];
        assert!(validate_sequence(Exchange::Run, &pf).is_ok());
        // wrong payload size
        let mut wp = good_run();
        wp[1] = frame(T_START, 1, 1);
        assert!(validate_sequence(Exchange::Run, &wp).is_err());
        // self-test exchange
        let st = vec![frame(T_HELLO, 0, hf::N), frame(T_PROBES, 1, 12)];
        assert!(validate_sequence(Exchange::SelfTest, &st).is_ok());
        assert!(validate_sequence(Exchange::Run, &st).is_err());
    }

    #[test]
    fn tau_clock_never_exceeds_the_cap() {
        assert_eq!(Tolerances::tau_clock(0, 100_000_000), None); // 100 ms run: 1 ms > 0.1 ms
        assert_eq!(Tolerances::tau_clock(0, 1_000_000_000), Some(1_000_000));
        assert_eq!(Tolerances::tau_clock(600_000, 1_000_000_000), None); // 1.2 ms > 1 ms cap
        assert_eq!(Tolerances::tau_clock(400_000, 10_000_000_000), Some(1_000_000));
        assert_eq!(Tolerances::tau_clock(3_000_000, 10_000_000_000), Some(6_000_000));
        for d in [0u64, 1, 999_999_999, 5_000_000_000] {
            if let Some(t) = Tolerances::tau_clock(0, d) {
                assert!(t <= d / 1000);
            }
        }
    }

    pub(crate) fn good_observed() -> Observed {
        let n = 4096u64;
        let mut v = vec![0u64; R_COUNT];
        v[rf::VERSION] = VERSION as u64;
        v[rf::T0_NS] = 1_000_000_000;
        v[rf::T1_NS] = 3_000_000_000; // 2 s
        for i in 0..4 {
            v[rf::HASH0 + i] = 10 + i as u64;
        }
        v[rf::OUT_BYTES] = n;
        v[rf::OUT_OFFSET] = out_offset(n);
        v[rf::SALT] = 77;
        v[rf::MXCSR_HARNESS] = 0x1FA0; // a sticky status flag only
        v[rf::FREEZE_OK] = 1;
        v[rf::PRIORITY_CLASS] = 0x20;
        Observed {
            requested_out_bytes: n,
            salt: 77,
            child_pid: 1234,
            declared_affinity: 0,
            declared_priority_class: 0x20,
            golden_hash: [10, 11, 12, 13],
            hello: Some(vec![VERSION as u64, 1234, PAGE, section_bytes(n), out_offset(n), n]),
            report: Some(Report { v }),
            start_ns: Some(5_000),
            stop_ns: Some(5_000 + 2_000_000_300),
            cycles_start: Some(1),
            cycles_stop: Some(100),
            cycles_exit: Some(200),
            hash_at_stop: Some([10, 11, 12, 13]),
            hash_at_exit: Some([10, 11, 12, 13]),
            poison_residual_at_stop: Some(0),
            exit_code: Some(0),
            declared_threads: 1,
            cycle_rate_hz: 4_000_000_000,
            ..Default::default()
        }
    }
    pub(crate) fn tol() -> Tolerances {
        Tolerances { pilot_max_abs_diff_ns: 100_000, kappa_post_cycles: 1_000, init_max_ns: 1_000_000_000, init_max_cycles: 1_000_000, extra_cores_milli: 250 }
    }
    fn fails_with(o: &Observed, check: &str) -> bool {
        decide_run(o, &tol()).failed_checks().contains(&check)
    }

    #[test]
    fn clean_run_accepts() {
        assert_eq!(decide_run(&good_observed(), &tol()), RunVerdict::Accept);
    }

    #[test]
    fn each_check_fires_alone() {
        let mut o = good_observed();
        o.protocol_error = Some("dup STOP".into());
        assert!(fails_with(&o, "protocol"));

        let mut o = good_observed();
        o.stop_ns = None;
        assert!(fails_with(&o, "start_stop"));

        let mut o = good_observed();
        o.cycles_exit = Some(100 + 1_001);
        assert!(fails_with(&o, "post_stop_cycles"));

        let mut o = good_observed();
        o.hash_at_exit = Some([0, 0, 0, 0]);
        assert!(fails_with(&o, "rehash_stop_exit"));

        let mut o = good_observed();
        o.golden_hash = [1, 2, 3, 4];
        assert!(fails_with(&o, "golden_hash"));

        let mut o = good_observed();
        o.exit_code = Some(1);
        assert!(fails_with(&o, "exit_code"));

        let mut o = good_observed();
        o.outside_changed_at_stop = 3;
        assert!(fails_with(&o, "outside_extent_oop"));

        let mut o = good_observed();
        o.poison_residual_at_stop = Some(5);
        assert!(fails_with(&o, "poison_residual_oop"));

        for (idx, name) in [
            (rf::WORKLOAD_RC, "workload_rc"),
            (rf::MXCSR_EXIT_BAD, "mxcsr_exit"),
            (rf::PRIORITY_EXIT_BAD, "priority_exit"),
            (rf::NEW_UNREGISTERED, "new_unregistered"),
            (rf::POST_T1_NEW_THREADS, "post_t1_new_threads"),
            (rf::CENSUS_ERRORS, "census_errors"),
        ] {
            let mut o = good_observed();
            o.report.as_mut().unwrap().v[idx] = 7;
            assert!(fails_with(&o, name), "{name}");
        }
        let mut o = good_observed();
        o.report.as_mut().unwrap().v[rf::MXCSR_HARNESS] = 0x1F80 | 0x8040;
        assert!(fails_with(&o, "mxcsr_harness"));
        let mut o = good_observed();
        o.report.as_mut().unwrap().v[rf::PRIORITY_HARNESS] = 2;
        assert!(fails_with(&o, "priority_harness"));
        let mut o = good_observed();
        o.report.as_mut().unwrap().v[rf::FREEZE_OK] = 0;
        assert!(fails_with(&o, "freeze"));
        let mut o = good_observed();
        o.report.as_mut().unwrap().v[rf::T1_NS] = 999_999_995;
        assert!(fails_with(&o, "t1_le_t0"));
        let mut o = good_observed();
        o.report.as_mut().unwrap().v[rf::T0_NS] -= 2_000_000; // claims 2 ms more than the bracket
        assert!(fails_with(&o, "clock_bracket"));
        let mut o = good_observed();
        o.hello.as_mut().unwrap()[hf::PID] = 9;
        assert!(fails_with(&o, "hello"));
    }

    #[test]
    fn every_cycle_is_charged_to_a_bounded_window() {
        // pre-START wall: init laundering (launch -> START 2 s > 1 s)
        let mut o = good_observed();
        o.start_ns = Some(2_000_000_000);
        o.stop_ns = Some(2_000_000_000 + 2_000_000_300);
        assert_eq!(decide_run(&o, &tol()).failed_checks(), vec!["pre_start_wall"]);
        // pre-START cycles (and fail-closed when unavailable)
        let mut o = good_observed();
        o.cycles_start = Some(2_000_000);
        o.cycles_stop = Some(2_000_100);
        o.cycles_exit = Some(2_000_200);
        assert_eq!(decide_run(&o, &tol()).failed_checks(), vec!["pre_start_cycles"]);
        let mut o = good_observed();
        o.cycles_start = None;
        assert!(fails_with(&o, "pre_start_cycles"));
        // timed window: 3 cores' worth of cycles over a 2 s bracket, declared 1 (+0.25)
        let mut o = good_observed();
        let three = 3u64 * 2 * 4_000_000_000;
        o.cycles_stop = Some(1 + three);
        o.cycles_exit = Some(1 + three + 100);
        assert_eq!(decide_run(&o, &tol()).failed_checks(), vec!["window_cores"]);
        o.declared_threads = 3; // the same cycles at a declared 3 threads pass
        assert_eq!(decide_run(&o, &tol()), RunVerdict::Accept);
        // 1.2 cores at declared 1 is inside the 0.25 slack
        let mut o = good_observed();
        let c = 12u64 * 2 * 4_000_000_000 / 10;
        o.cycles_stop = Some(1 + c);
        o.cycles_exit = Some(1 + c + 100);
        assert_eq!(decide_run(&o, &tol()), RunVerdict::Accept);
        // uncalibrated rate or no declared threads fails closed
        let mut o = good_observed();
        o.cycle_rate_hz = 0;
        assert!(fails_with(&o, "window_cores"));
        let mut o = good_observed();
        o.declared_threads = 0;
        assert!(fails_with(&o, "window_cores"));
    }

    #[test]
    fn short_runs_are_ineligible_not_accepted() {
        let mut o = good_observed();
        o.report.as_mut().unwrap().v[rf::T1_NS] = 1_000_500_000; // 0.5 ms
        o.stop_ns = Some(5_000 + 500_000);
        assert_eq!(decide_run(&o, &tol()).failed_checks(), vec!["bracket_too_short"]);
    }

    #[test]
    fn watchdog_before_stop_is_time_capped_after_stop_is_integrity() {
        let mut o = good_observed();
        o.stop_ns = None;
        o.report = None;
        o.watchdog_fired = true;
        o.exit_code = Some(0xC0DE);
        assert_eq!(decide_run(&o, &tol()), RunVerdict::TimeCapped);
        let mut o = good_observed();
        o.watchdog_fired = true;
        assert!(fails_with(&o, "no_exit"));
    }

    #[test]
    fn poison_helpers() {
        let n = 128usize;
        let salt = 0x1122_3344_5566_7788u64;
        let mut e = vec![POISON_BYTE; n];
        for i in 0..8 {
            e[8 * i..8 * i + 8].copy_from_slice(&salt.to_le_bytes());
            e[n - 64 + 8 * i..n - 64 + 8 * i + 8].copy_from_slice(&salt.to_le_bytes());
        }
        assert_eq!(poison_residual(&e, salt), 16);
        let full: Vec<u8> = (0..n).map(|i| (i * 31 + 7) as u8).collect();
        assert_eq!(poison_residual(&full, salt), 0);
        let nb = 64u64;
        let mut sec = vec![POISON_BYTE; section_bytes(nb) as usize];
        assert_eq!(outside_changed(&sec, nb), PAGE); // a poisoned trailing page is not the zero page
        let off = out_offset(nb) as usize;
        let end = off + nb as usize;
        for b in &mut sec[end..] {
            *b = 0; // the trailing page starts zero-filled
        }
        assert_eq!(outside_changed(&sec, nb), 0);
        sec[off - 1] = 0; // in the head before the extent: counted
        sec[off] = 3; // inside the extent: not counted
        assert_eq!(outside_changed(&sec, nb), 1);
        sec[end + 5] = 1; // past the extent, in the trailing page (a lifted guard): counted
        assert_eq!(outside_changed(&sec, nb), 2);
    }
}
