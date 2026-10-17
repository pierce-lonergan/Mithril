//! Decode the C harness's framed messages and compute the out-of-process integrity bracket
//! (MEASUREMENT-SERVICE.md section 3 step 8a). Mirrors `service/proto/x4proto.h`. The bracket is the
//! *trusted* record: it runs here, in the orchestrator, where no workload code runs. A run counts only
//! if the orchestrator's wall bracket agrees with the harness clock, the job charged no CPU after
//! STOP, and the orchestrator's own rehash of the output section equals the harness hash and the
//! golden/incumbent hash. Any failure is an integrity failure (rejected + quarantined), never a void.

pub const MAGIC: u32 = 0x3450_3458;
pub const VERSION: u32 = 1;

pub const T_HELLO: u32 = 1;
pub const T_START: u32 = 2;
pub const T_STOP: u32 = 3;
pub const T_CENSUS: u32 = 4;
pub const T_REPORT: u32 = 5;
pub const T_FAIL: u32 = 6;
pub const T_PROBES: u32 = 7;

pub const R_COUNT: usize = 30; // X4P_R_COUNT (fields VERSION..=SELFCHECK_FLAGS, 0..=29)

/// A decoded message from the harness.
#[derive(Clone, Debug)]
pub struct Msg {
    pub mtype: u32,
    pub seq: u32,
    pub vals: Vec<u64>,
}

/// Parse a byte stream of 16-byte headers + u64 payloads. Returns an error on bad magic or short read.
pub fn parse(buf: &[u8]) -> Result<Vec<Msg>, String> {
    let mut msgs = Vec::new();
    let mut off = 0usize;
    while off + 16 <= buf.len() {
        let magic = u32::from_le_bytes(buf[off..off + 4].try_into().unwrap());
        let mtype = u32::from_le_bytes(buf[off + 4..off + 8].try_into().unwrap());
        let plen = u32::from_le_bytes(buf[off + 8..off + 12].try_into().unwrap()) as usize;
        let seq = u32::from_le_bytes(buf[off + 12..off + 16].try_into().unwrap());
        off += 16;
        if magic != MAGIC {
            return Err(format!("bad magic {:08x} at {}", magic, off - 16));
        }
        if plen % 8 != 0 || off + plen > buf.len() {
            return Err(format!("bad payload len {} at {}", plen, off));
        }
        let mut vals = Vec::with_capacity(plen / 8);
        for i in (0..plen).step_by(8) {
            vals.push(u64::from_le_bytes(buf[off + i..off + i + 8].try_into().unwrap()));
        }
        off += plen;
        msgs.push(Msg { mtype, seq, vals });
    }
    Ok(msgs)
}

/// The report field indices (x4proto.h enum x4p_report_field).
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
}

/// The typed run report.
#[derive(Clone, Debug)]
pub struct Report {
    pub v: Vec<u64>,
}

impl Report {
    pub fn from_msg(m: &Msg) -> Result<Report, String> {
        if m.mtype != T_REPORT {
            return Err("not a REPORT".into());
        }
        if m.vals.len() < R_COUNT {
            return Err(format!("short report: {}", m.vals.len()));
        }
        Ok(Report { v: m.vals.clone() })
    }
    pub fn get(&self, i: usize) -> u64 {
        self.v[i]
    }
    pub fn delta_h_ns(&self) -> u64 {
        self.v[rf::T1_NS].saturating_sub(self.v[rf::T0_NS])
    }
    pub fn harness_hash(&self) -> [u64; 4] {
        [self.v[rf::HASH0], self.v[rf::HASH0 + 1], self.v[rf::HASH0 + 2], self.v[rf::HASH0 + 3]]
    }
}

/// The orchestrator's own measurements of the run, taken outside the sandbox.
#[derive(Clone, Debug)]
pub struct OrchestratorBracket {
    /// QPC delta between receiving START and STOP, in ns (06 section 6.7, the reserved core).
    pub delta_o_ns: u64,
    /// Job CPU (user+kernel) charged after STOP, in 100-ns ticks (JOBOBJECT_BASIC_ACCOUNTING_INFORMATION).
    pub cpu_after_stop_100ns: u64,
    /// The orchestrator's SHA-256 of the copied output section.
    pub orch_hash: [u64; 4],
    /// The golden/incumbent hash this run is graded against.
    pub golden_hash: [u64; 4],
}

/// Pilot-derived integrity tolerances the orchestrator holds (section 5.4). All provisional until the
/// pilot fills them in; the design caps tau_clock at 0.1% of delta_o and floors it at 1 ms.
#[derive(Clone, Copy, Debug)]
pub struct Tolerances {
    pub tau_clock_ns: u64,
    pub kappa_post_100ns: u64,
    pub spin_budget_cycles: u64,
    pub idle_budget_cycles: u64,
}

impl Tolerances {
    /// tau_clock = max(1 ms, 2*pilot_max|dh-do|), capped at 0.1% of delta_o.
    pub fn tau_clock(pilot_max_abs_diff_ns: u64, delta_o_ns: u64) -> u64 {
        let base = (2 * pilot_max_abs_diff_ns).max(1_000_000);
        let cap = delta_o_ns / 1000; // 0.1%
        base.min(cap.max(1_000_000))
    }
}

/// The verdict on a single run.
#[derive(Clone, Debug, PartialEq)]
pub enum RunVerdict {
    Accept,
    IntegrityFail(String),
}

/// Apply the full run-acceptance contract (section 3 steps 6-8a; prereg section 4 "Run"). Returns
/// Accept only if every in-process check passed *and* the out-of-process bracket agrees.
pub fn decide_run(rep: &Report, br: &OrchestratorBracket, tol: &Tolerances) -> RunVerdict {
    macro_rules! fail {
        ($($arg:tt)*) => { return RunVerdict::IntegrityFail(format!($($arg)*)); };
    }
    if rep.get(rf::VERSION) != VERSION as u64 {
        fail!("report version {}", rep.get(rf::VERSION));
    }
    if rep.get(rf::CENSUS_ERRORS) != 0 {
        fail!("census errors {} (fails closed)", rep.get(rf::CENSUS_ERRORS));
    }
    if rep.get(rf::IO_OUTSTANDING) != 0 {
        fail!("I/O not joined: {} outstanding", rep.get(rf::IO_OUTSTANDING));
    }
    if rep.get(rf::NEW_UNREGISTERED) != 0 {
        fail!("thread census: {} unregistered threads created after t0 (a3/a3b)", rep.get(rf::NEW_UNREGISTERED));
    }
    if rep.get(rf::REGISTERED_UNPARKED) != 0 {
        fail!("{} registered threads unjoined/unparked at t1 (a3)", rep.get(rf::REGISTERED_UNPARKED));
    }
    if rep.get(rf::POST_T1_VIOLATIONS) != 0 {
        fail!("post-t1 CPU rule: {} threads over allowance (a3b)", rep.get(rf::POST_T1_VIOLATIONS));
    }
    if rep.get(rf::MXCSR_BAD_THREADS) != 0 {
        fail!("MXCSR not default on {} threads (a9)", rep.get(rf::MXCSR_BAD_THREADS));
    }
    if rep.get(rf::MXCSR_ENTRY_BAD) != 0 {
        fail!("MXCSR not default at entry on {} registered threads (a9)", rep.get(rf::MXCSR_ENTRY_BAD));
    }
    if rep.get(rf::AFFINITY_BAD) != 0 {
        fail!("{} threads outside the job affinity mask (a31)", rep.get(rf::AFFINITY_BAD));
    }
    if rep.get(rf::PRIORITY_BAD) != 0 {
        fail!("{} threads not at normal priority (a31)", rep.get(rf::PRIORITY_BAD));
    }
    if rep.get(rf::POISON_RESIDUAL_WORDS) != 0 {
        fail!("output not fully written: {} poison words remain (a4/a13)", rep.get(rf::POISON_RESIDUAL_WORDS));
    }
    if rep.get(rf::SLACK_MODIFIED_BYTES) != 0 {
        fail!("write past the output extent: {} slack bytes changed", rep.get(rf::SLACK_MODIFIED_BYTES));
    }
    // out-of-process bracket (step 8a)
    let dh = rep.delta_h_ns();
    let diff = if dh > br.delta_o_ns { dh - br.delta_o_ns } else { br.delta_o_ns - dh };
    if diff > tol.tau_clock_ns {
        fail!("clock bracket |dh-do| = {} ns exceeds tau_clock {} ns (a5)", diff, tol.tau_clock_ns);
    }
    if br.cpu_after_stop_100ns > tol.kappa_post_100ns {
        fail!("job charged {} x100ns CPU after STOP, over kappa_post {} (a3b)", br.cpu_after_stop_100ns, tol.kappa_post_100ns);
    }
    if rep.harness_hash() != br.orch_hash {
        fail!("harness hash != orchestrator rehash (work continued after STOP, a3b)");
    }
    if br.orch_hash != br.golden_hash {
        fail!("output hash != golden/incumbent (a4/a7/a10/a13/a18)");
    }
    RunVerdict::Accept
}

#[cfg(test)]
mod tests {
    use super::*;

    fn good_report() -> Report {
        let mut v = vec![0u64; R_COUNT];
        v[rf::VERSION] = VERSION as u64;
        v[rf::T0_NS] = 1_000_000_000;
        v[rf::T1_NS] = 1_010_000_000; // dh = 10 ms
        v[rf::HASH0] = 0xaa;
        v[rf::HASH0 + 1] = 0xbb;
        v[rf::HASH0 + 2] = 0xcc;
        v[rf::HASH0 + 3] = 0xdd;
        v[rf::OUT_BYTES] = 4096;
        Report { v }
    }
    fn good_bracket() -> OrchestratorBracket {
        OrchestratorBracket {
            delta_o_ns: 10_050_000, // 50 us off dh
            cpu_after_stop_100ns: 0,
            orch_hash: [0xaa, 0xbb, 0xcc, 0xdd],
            golden_hash: [0xaa, 0xbb, 0xcc, 0xdd],
        }
    }
    fn tol() -> Tolerances {
        Tolerances {
            tau_clock_ns: Tolerances::tau_clock(100_000, 10_050_000),
            kappa_post_100ns: 1000,
            spin_budget_cycles: 0,
            idle_budget_cycles: 0,
        }
    }

    #[test]
    fn r_count_matches_last_field() {
        // R_COUNT must be exactly one past the last report field, or valid reports are rejected.
        assert_eq!(R_COUNT, rf::SELFCHECK_FLAGS + 1);
    }

    #[test]
    fn parse_roundtrips_a_report() {
        let rep = good_report();
        let mut buf = Vec::new();
        buf.extend_from_slice(&MAGIC.to_le_bytes());
        buf.extend_from_slice(&T_REPORT.to_le_bytes());
        buf.extend_from_slice(&((R_COUNT * 8) as u32).to_le_bytes());
        buf.extend_from_slice(&7u32.to_le_bytes());
        for &x in &rep.v {
            buf.extend_from_slice(&x.to_le_bytes());
        }
        let msgs = parse(&buf).unwrap();
        assert_eq!(msgs.len(), 1);
        let r = Report::from_msg(&msgs[0]).unwrap();
        assert_eq!(r.delta_h_ns(), 10_000_000);
    }

    #[test]
    fn clean_run_accepts() {
        assert_eq!(decide_run(&good_report(), &good_bracket(), &tol()), RunVerdict::Accept);
    }

    #[test]
    fn unregistered_thread_is_integrity_fail() {
        let mut r = good_report();
        r.v[rf::NEW_UNREGISTERED] = 1;
        assert!(matches!(decide_run(&r, &good_bracket(), &tol()), RunVerdict::IntegrityFail(_)));
    }

    #[test]
    fn timer_overwrite_fails_the_bracket() {
        // harness claims dh = 10 ms but the orchestrator saw delta_o = 10.05 ms; now shave 1 ms off dh
        let mut r = good_report();
        r.v[rf::T1_NS] = r.v[rf::T0_NS] + 9_000_000; // 1 ms short
        let v = decide_run(&r, &good_bracket(), &tol());
        assert!(matches!(v, RunVerdict::IntegrityFail(ref s) if s.contains("clock bracket")), "{v:?}");
    }

    #[test]
    fn cpu_after_stop_fails() {
        let mut br = good_bracket();
        br.cpu_after_stop_100ns = 5000; // over kappa_post 1000
        assert!(matches!(decide_run(&good_report(), &br, &tol()), RunVerdict::IntegrityFail(_)));
    }

    #[test]
    fn hash_mismatch_fails() {
        let mut br = good_bracket();
        br.orch_hash = [1, 2, 3, 4];
        assert!(matches!(decide_run(&good_report(), &br, &tol()), RunVerdict::IntegrityFail(_)));
    }

    #[test]
    fn tau_clock_floor_and_cap() {
        // floor 1 ms when delta_o tiny
        assert_eq!(Tolerances::tau_clock(0, 1000), 1_000_000);
        // cap at 0.1% of a large delta_o: 0.1% of 10 s = 10 ms, 2*pilot=... choose pilot big
        assert_eq!(Tolerances::tau_clock(100_000_000, 10_000_000_000), 10_000_000);
    }
}
