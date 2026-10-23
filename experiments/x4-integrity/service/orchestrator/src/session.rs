//! The session engine (review R2-12): run results -> per-run log-times (ln ns) -> randomised ABBA/BAAB
//! blocks from a pinned seed -> scorers -> e-processes, behind the load gate.
//!
//! - Runs come from a `RunSource` (on Windows, `sandbox::run_once` through the job and the bracket; in
//!   tests, a scripted source). Only accepted runs enter a block. An integrity failure stops the session
//!   at once (an evaluator bug in a calibration, the catch in a planted-hack run); it is never re-run.
//!   A time-capped run is scored as a slow outlier (section 8.7).
//! - Blindness (section 5.3): the gate decision (`LoadGate::decide`) takes sensor readings only. The
//!   wealth at every discard and at a void is *logged after* the decision, never passed to it.
//! - Gating (X4 pilot track, 2026-10-23): the gate is read before **every run**, not only before a
//!   block, so a gate that drops mid-block discards the block (MEASUREMENT section 4: "if the gate
//!   drops mid-block, the block is discarded"); the block order is drawn when its first run is
//!   entered, so a discard before any run consumes no draw. Two further sensor-only hooks: a
//!   session-level hygiene void (checked before every run and after every block) and a post-block
//!   discard (background CPU over the block, X4-noise-pilot section 10). A post-block discard counts
//!   toward the same three-discard limit.
//! - Order per run (revision 4): `before_run` (the cool-down), `session_void`, `read` (the gate), then
//!   the run, so nothing waits between the gate reading and the launch.
//! - Log-times are ln(nanoseconds) of the harness interval delta_h = t1 - t0 of an accepted run (the
//!   record's T, section 4); the fact states the unit.
//!
//! This module never touches the machine. Nothing here has been run on real sessions: A/A, planted and
//! pilot sessions are data and run only under a signed record.

use crate::eprocess::{block_d, clip_for, clip_kill_for, threshold, Arm, BlockScorer, EProcess, Scorer, Test, THETA, THETA_KILL};
use crate::scheduler::{next_order, GateDecision, GateReading, LoadGate, Order, SplitMix64};
use crate::stats;

/// The outcome of one run, as the session sees it.
#[derive(Clone, Debug, PartialEq)]
pub enum RunResult {
    Accepted { ns: u64 },
    TimeCapped { cap_ns: u64 },
    Integrity(String),
}

pub trait RunSource {
    fn run(&mut self, arm: Arm) -> RunResult;
}

pub trait GateSensor {
    /// A block attempt begins (before its first run's checks). Default: nothing.
    fn block_start(&mut self) {}
    /// Called before each run's checks, before `session_void` and `read` (revision 4, review
    /// 2026-10-23): the end-to-end cool-down waits here, so the gate reading and the hygiene snapshot
    /// directly precede the launch rather than coming a cool-down earlier. Default: nothing.
    fn before_run(&mut self) {}
    /// The pre-run gate reading (sensor readings only).
    fn read(&mut self) -> GateReading;
    /// A session-level hygiene void found by the sensors (interactive input, an excluded process, GPU
    /// use, NVMe temperature, the window cut), or None. Sensor-only; never sees run times or wealth.
    fn session_void(&mut self) -> Option<String> {
        None
    }
    /// The sensor-only verdict on the block just run (e.g. Defender/indexer/TiWorker CPU over the
    /// block): Some(reason) discards it unscored.
    fn after_block(&mut self) -> Option<String> {
        None
    }
}

#[derive(Clone, Debug)]
pub struct SessionConfig {
    /// The pinned schedule seed for this session's ABBA/BAAB draws.
    pub seed: u64,
    /// Scored blocks to run (the horizon N, or n).
    pub horizon: usize,
    pub sigma_hat_d: f64,
    pub sigma_hat_run: f64,
    /// Pilot incumbent median of per-run ln(ns) (the R/Rk reference before any history).
    pub pilot_median_ln_ns: f64,
    pub alpha_i: Option<f64>,
    pub load_threshold_pct: f64,
}

#[derive(Clone, Debug)]
pub struct BlockRecord {
    /// Index (0-based) of this block's first run among all runs the session launched, so a record
    /// writer can map the block to its four run records (discarded blocks also consume runs).
    pub first_run: usize,
    pub order: Order,
    pub runs: [(Arm, f64); 4],
    pub capped: [bool; 4],
    pub d: f64,
    pub x_r: f64,
    pub x_s: f64,
    pub x_rk: f64,
    pub x_lit: f64,
    pub k_sup: f64,
    pub k_ni: f64,
    pub k_kill: f64,
    pub k_sup_s: f64,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Wealth {
    pub sup: f64,
    pub ni: f64,
    pub kill: f64,
}

#[derive(Clone, Debug, PartialEq)]
pub enum SessionEnd {
    Completed,
    HygieneVoid { reason: String, wealth_at_void: Wealth },
    IntegrityStop { reason: String },
}

#[derive(Clone, Debug)]
pub struct SessionResult {
    pub blocks: Vec<BlockRecord>,
    /// (index of the next block, wealth at the discard) -- logged after the blind decision.
    pub discards: Vec<(usize, Wealth)>,
    /// The sensor reason of each discard, in the same order.
    pub discard_reasons: Vec<String>,
    pub end: SessionEnd,
    /// First scored block (1-based) at which each e-process reached max(20, 1/alpha_i).
    pub cross_sup: Option<usize>,
    pub cross_ni: Option<usize>,
    pub cross_kill: Option<usize>,
    pub cross_sup_s: Option<usize>,
    /// S3 statistical void (either arm's trend test rejects); stays in the tally.
    pub s3_void: bool,
    pub carry_over: Option<(f64, f64)>,
    pub slow_b: u64,
    pub runs_b: u64,
}

pub fn run_session(cfg: &SessionConfig, src: &mut dyn RunSource, sensor: &mut dyn GateSensor) -> SessionResult {
    let c = clip_for(cfg.sigma_hat_d);
    let ck = clip_kill_for(cfg.sigma_hat_d);
    let cr = 4.0 * cfg.sigma_hat_run;
    let pm = cfg.pilot_median_ln_ns;
    let mut sr = BlockScorer::new(Scorer::R, c, cr, pm);
    let mut ss = BlockScorer::new(Scorer::S, c, cr, pm);
    let mut sk = BlockScorer::new(Scorer::Rk, ck, cr, pm);
    let mut sl = BlockScorer::new(Scorer::Lit06, c, cr, pm);
    let mut sup = EProcess::make(Test::Superiority, c, THETA);
    let mut ni = EProcess::make(Test::NonInferiority, c, THETA);
    let mut kill = EProcess::make(Test::Kill, ck, THETA_KILL);
    let mut sup_s = EProcess::make(Test::Superiority, c, THETA);
    let thr = threshold(cfg.alpha_i);
    let mut gate = LoadGate::new(cfg.load_threshold_pct);
    let mut rng = SplitMix64::new(cfg.seed);

    let mut res = SessionResult {
        blocks: Vec::new(),
        discards: Vec::new(),
        discard_reasons: Vec::new(),
        end: SessionEnd::Completed,
        cross_sup: None,
        cross_ni: None,
        cross_kill: None,
        cross_sup_s: None,
        s3_void: false,
        carry_over: None,
        slow_b: 0,
        runs_b: 0,
    };
    let wealth = |s: &EProcess, n: &EProcess, k: &EProcess| Wealth { sup: s.wealth(), ni: n.wealth(), kill: k.wealth() };

    let mut runs_launched = 0usize;
    'blocks: while res.blocks.len() < cfg.horizon {
        sensor.block_start();
        let first_run = runs_launched;
        let mut order: Option<Order> = None;
        let mut runs = [(Arm::A, 0.0f64); 4];
        let mut capped = [false; 4];
        for i in 0..4 {
            sensor.before_run();
            // the blind decisions: sensor readings in, decision out; wealth is only logged afterwards
            if let Some(reason) = sensor.session_void() {
                res.end = SessionEnd::HygieneVoid { reason, wealth_at_void: wealth(&sup, &ni, &kill) };
                return res;
            }
            let reading = sensor.read();
            match gate.decide(&reading) {
                GateDecision::Enter => {}
                GateDecision::Discard => {
                    res.discards.push((res.blocks.len(), wealth(&sup, &ni, &kill)));
                    res.discard_reasons.push(format!("pre-run gate before run {} of the block: {}", i + 1, LoadGate::why(&reading, gate.cpu_threshold_pct)));
                    continue 'blocks;
                }
                GateDecision::VoidSession => {
                    res.end = SessionEnd::HygieneVoid {
                        reason: if reading.profile_hash_matches {
                            format!("load gate failed on 3 blocks (last: {})", LoadGate::why(&reading, gate.cpu_threshold_pct))
                        } else {
                            "profile hash mismatch".into()
                        },
                        wealth_at_void: wealth(&sup, &ni, &kill),
                    };
                    return res;
                }
            }
            let o = *order.get_or_insert_with(|| next_order(&mut rng));
            let arm = o.arms()[i];
            runs_launched += 1;
            let l = match src.run(arm) {
                RunResult::Accepted { ns } if ns > 0 => (ns as f64).ln(),
                RunResult::Accepted { .. } => {
                    res.end = SessionEnd::IntegrityStop { reason: "zero-length run".into() };
                    return res;
                }
                RunResult::TimeCapped { cap_ns } => {
                    capped[i] = true;
                    (cap_ns.max(1) as f64).ln()
                }
                RunResult::Integrity(why) => {
                    res.end = SessionEnd::IntegrityStop { reason: why };
                    return res;
                }
            };
            runs[i] = (arm, l);
        }
        let order = order.expect("four runs entered");
        if let Some(reason) = sensor.session_void() {
            res.end = SessionEnd::HygieneVoid { reason, wealth_at_void: wealth(&sup, &ni, &kill) };
            return res;
        }
        if let Some(reason) = sensor.after_block() {
            match gate.note_discard() {
                GateDecision::VoidSession => {
                    res.end = SessionEnd::HygieneVoid { reason: format!("3 discarded blocks (last: {})", reason), wealth_at_void: wealth(&sup, &ni, &kill) };
                    return res;
                }
                _ => {
                    res.discards.push((res.blocks.len(), wealth(&sup, &ni, &kill)));
                    res.discard_reasons.push(format!("after the block: {}", reason));
                    continue 'blocks;
                }
            }
        }
        let d = block_d(&runs);
        let scored = (|| -> Result<(f64, f64, f64, f64), String> {
            Ok((sr.try_score(d, &runs, &capped)?, ss.try_score(d, &runs, &capped)?, sk.try_score(d, &runs, &capped)?, sl.try_score(d, &runs, &capped)?))
        })();
        let (x_r, x_s, x_rk, x_lit) = match scored {
            Ok(v) => v,
            Err(e) => {
                res.end = SessionEnd::IntegrityStop { reason: e };
                return res;
            }
        };
        let (k_sup, k_ni, k_kill, k_sup_s) = (sup.update(x_r), ni.update(x_r), kill.update(x_rk), sup_s.update(x_s));
        let i = res.blocks.len() + 1;
        let first = |slot: &mut Option<usize>, k: f64| {
            if slot.is_none() && k >= thr {
                *slot = Some(i);
            }
        };
        first(&mut res.cross_sup, k_sup);
        first(&mut res.cross_ni, k_ni);
        first(&mut res.cross_kill, k_kill);
        first(&mut res.cross_sup_s, k_sup_s);
        res.blocks.push(BlockRecord { first_run, order, runs, capped, d, x_r, x_s, x_rk, x_lit, k_sup, k_ni, k_kill, k_sup_s });
    }

    // statistical secondaries on the completed session (blind: run times only)
    let per_arm = |a: Arm| -> Vec<f64> { res.blocks.iter().flat_map(|b| b.runs.iter().filter(move |r| r.0 == a).map(|r| r.1)).collect() };
    res.s3_void = stats::s3_trend_void(&per_arm(Arm::A)) || stats::s3_trend_void(&per_arm(Arm::B));
    let co: Vec<[(bool, f64); 4]> = res
        .blocks
        .iter()
        .map(|b| [(b.runs[0].0 == Arm::B, b.runs[0].1), (b.runs[1].0 == Arm::B, b.runs[1].1), (b.runs[2].0 == Arm::B, b.runs[2].1), (b.runs[3].0 == Arm::B, b.runs[3].1)])
        .collect();
    res.carry_over = stats::carry_over_contrast(&co);
    res.slow_b = sr.slow_b;
    res.runs_b = sr.nruns_b;
    res
}

#[cfg(test)]
mod tests {
    use super::*;

    struct Scripted {
        a_ns: u64,
        b_ns: u64,
        k: usize,
        fail_at: Option<usize>,
        cap_at: Option<usize>,
    }
    impl RunSource for Scripted {
        fn run(&mut self, arm: Arm) -> RunResult {
            self.k += 1;
            if Some(self.k) == self.fail_at {
                return RunResult::Integrity("census".into());
            }
            if Some(self.k) == self.cap_at {
                return RunResult::TimeCapped { cap_ns: 30_000_000_000 };
            }
            // deterministic small wobble so d varies
            let w = (self.k % 7) as u64 * 1_000_000;
            RunResult::Accepted { ns: if arm == Arm::A { self.a_ns + w } else { self.b_ns + w } }
        }
    }
    struct Quiet {
        busy_first: usize,
        n: usize,
        profile_ok: bool,
    }
    impl GateSensor for Quiet {
        fn read(&mut self) -> GateReading {
            self.n += 1;
            GateReading {
                profile_hash_matches: self.profile_ok,
                quiet_window_active: true,
                cpu_load_2s_pct: if self.n <= self.busy_first { 90.0 } else { 1.0 },
                background_idle: true,
                nvme_temp_ok: true,
                no_large_writes: true,
                run_core_quiet: true,
            }
        }
    }
    fn cfg() -> SessionConfig {
        SessionConfig {
            seed: 20261016,
            horizon: 12,
            sigma_hat_d: 0.02,
            sigma_hat_run: 0.02,
            pilot_median_ln_ns: (10e9f64).ln(),
            alpha_i: None,
            load_threshold_pct: 40.0,
        }
    }

    #[test]
    fn blocks_follow_the_seed_and_wealth_matches_direct_updates() {
        let mut src = Scripted { a_ns: 10_000_000_000, b_ns: 10_000_000_000, k: 0, fail_at: None, cap_at: None };
        let r = run_session(&cfg(), &mut src, &mut Quiet { busy_first: 0, n: 0, profile_ok: true });
        assert_eq!(r.end, SessionEnd::Completed);
        assert_eq!(r.blocks.len(), 12);
        let mut rng = SplitMix64::new(20261016);
        let c = clip_for(0.02);
        let mut sup = EProcess::make(Test::Superiority, c, THETA);
        for b in &r.blocks {
            assert_eq!(b.order, next_order(&mut rng));
            let arms: Vec<Arm> = b.runs.iter().map(|x| x.0).collect();
            assert_eq!(arms, b.order.arms().to_vec());
            assert_eq!(b.d.to_bits(), block_d(&b.runs).to_bits());
            assert_eq!(sup.update(b.x_r).to_bits(), b.k_sup.to_bits());
        }
        // identical arms around the pilot median: no first-block outlier, no crossing
        assert_eq!(r.slow_b, 0);
        assert_eq!(r.cross_sup, None);
    }

    #[test]
    fn discards_log_wealth_and_the_third_voids() {
        let mut src = Scripted { a_ns: 10_000_000_000, b_ns: 10_000_000_000, k: 0, fail_at: None, cap_at: None };
        let r = run_session(&cfg(), &mut src, &mut Quiet { busy_first: 3, n: 0, profile_ok: true });
        assert_eq!(r.discards.len(), 2);
        assert!(matches!(r.end, SessionEnd::HygieneVoid { .. }));
        assert!(r.blocks.is_empty());
        let r = run_session(&cfg(), &mut src, &mut Quiet { busy_first: 0, n: 0, profile_ok: false });
        assert!(matches!(r.end, SessionEnd::HygieneVoid { ref reason, .. } if reason.contains("profile")));
    }

    #[test]
    fn integrity_failure_stops_the_session() {
        let mut src = Scripted { a_ns: 10_000_000_000, b_ns: 10_000_000_000, k: 0, fail_at: Some(6), cap_at: None };
        let r = run_session(&cfg(), &mut src, &mut Quiet { busy_first: 0, n: 0, profile_ok: true });
        assert_eq!(r.blocks.len(), 1);
        assert_eq!(r.end, SessionEnd::IntegrityStop { reason: "census".into() });
    }

    #[test]
    fn time_capped_run_scores_its_block_as_an_outlier() {
        let mut src = Scripted { a_ns: 10_000_000_000, b_ns: 10_000_000_000, k: 0, fail_at: None, cap_at: Some(2) };
        let r = run_session(&cfg(), &mut src, &mut Quiet { busy_first: 0, n: 0, profile_ok: true });
        assert!(r.blocks[0].capped.iter().any(|&c| c));
        assert_eq!(r.blocks[0].x_r, clip_for(0.02));
        assert_eq!(r.blocks[0].x_rk, -clip_kill_for(0.02));
    }

    /// A sensor scripted per call: the gate turns busy at read `busy_at`, the block hook discards at
    /// call `discard_at`, the session hook voids at call `void_at`.
    struct Scripted2 {
        reads: usize,
        busy_at: usize,
        afters: usize,
        discard_at: Vec<usize>,
        voids: usize,
        void_at: usize,
    }
    impl GateSensor for Scripted2 {
        fn read(&mut self) -> GateReading {
            self.reads += 1;
            GateReading {
                profile_hash_matches: true,
                quiet_window_active: true,
                cpu_load_2s_pct: if self.reads == self.busy_at { 90.0 } else { 1.0 },
                background_idle: true,
                nvme_temp_ok: true,
                no_large_writes: true,
                run_core_quiet: true,
            }
        }
        fn session_void(&mut self) -> Option<String> {
            self.voids += 1;
            if self.voids == self.void_at {
                Some("planted: interactive input".into())
            } else {
                None
            }
        }
        fn after_block(&mut self) -> Option<String> {
            self.afters += 1;
            if self.discard_at.contains(&self.afters) {
                Some("planted: MsMpEng CPU".into())
            } else {
                None
            }
        }
    }
    fn src() -> Scripted {
        Scripted { a_ns: 10_000_000_000, b_ns: 10_000_000_000, k: 0, fail_at: None, cap_at: None }
    }

    #[test]
    fn a_gate_drop_mid_block_discards_the_block() {
        // read 3 = the third run of the first block: the block is dropped after two runs
        let mut s = src();
        let r = run_session(&cfg(), &mut s, &mut Scripted2 { reads: 0, busy_at: 3, afters: 0, discard_at: vec![], voids: 0, void_at: 0 });
        assert_eq!(r.end, SessionEnd::Completed);
        assert_eq!(r.blocks.len(), 12);
        assert_eq!(r.discards.len(), 1);
        assert!(r.discard_reasons[0].contains("before run 3") && r.discard_reasons[0].contains("90.00%"));
        assert_eq!(s.k, 2 + 12 * 4); // two runs of the dropped block were spent
    }

    #[test]
    fn post_block_discards_count_toward_the_void_limit() {
        let mut s = src();
        let r = run_session(&cfg(), &mut s, &mut Scripted2 { reads: 0, busy_at: 0, afters: 0, discard_at: vec![2, 5], voids: 0, void_at: 0 });
        assert_eq!(r.end, SessionEnd::Completed);
        assert_eq!(r.discards.len(), 2);
        assert!(r.discard_reasons.iter().all(|x| x.starts_with("after the block")));
        let mut s = src();
        let r = run_session(&cfg(), &mut s, &mut Scripted2 { reads: 0, busy_at: 0, afters: 0, discard_at: vec![1, 2, 3], voids: 0, void_at: 0 });
        assert!(matches!(r.end, SessionEnd::HygieneVoid { ref reason, .. } if reason.contains("MsMpEng")));
        assert!(r.blocks.is_empty());
    }

    #[test]
    fn a_session_void_from_the_sensors_ends_the_session() {
        // void_at 6: before run 1 of block 2 is check 6 (5 checks per block: 4 pre-run, 1 after)
        let mut s = src();
        let r = run_session(&cfg(), &mut s, &mut Scripted2 { reads: 0, busy_at: 0, afters: 0, discard_at: vec![], voids: 0, void_at: 6 });
        assert!(matches!(r.end, SessionEnd::HygieneVoid { ref reason, .. } if reason.contains("input")));
        assert_eq!(r.blocks.len(), 1);
        // a void found after the block's runs leaves that block unscored
        let mut s = src();
        let r = run_session(&cfg(), &mut s, &mut Scripted2 { reads: 0, busy_at: 0, afters: 0, discard_at: vec![], voids: 0, void_at: 5 });
        assert!(r.blocks.is_empty());
        assert_eq!(s.k, 4);
    }

    /// Records the call order of the sensor hooks and the runs (revision 4).
    struct Ordered {
        log: std::rc::Rc<std::cell::RefCell<Vec<&'static str>>>,
    }
    impl GateSensor for Ordered {
        fn before_run(&mut self) {
            self.log.borrow_mut().push("cooldown");
        }
        fn session_void(&mut self) -> Option<String> {
            self.log.borrow_mut().push("void");
            None
        }
        fn read(&mut self) -> GateReading {
            self.log.borrow_mut().push("read");
            GateReading { profile_hash_matches: true, quiet_window_active: true, cpu_load_2s_pct: 1.0, background_idle: true, nvme_temp_ok: true, no_large_writes: true, run_core_quiet: true }
        }
        fn after_block(&mut self) -> Option<String> {
            self.log.borrow_mut().push("after");
            None
        }
    }
    struct OrderedSrc {
        log: std::rc::Rc<std::cell::RefCell<Vec<&'static str>>>,
    }
    impl RunSource for OrderedSrc {
        fn run(&mut self, _arm: Arm) -> RunResult {
            self.log.borrow_mut().push("run");
            RunResult::Accepted { ns: 10_000_000_000 }
        }
    }

    #[test]
    fn the_cooldown_precedes_the_checks_and_the_gate_directly_precedes_the_run() {
        let log = std::rc::Rc::new(std::cell::RefCell::new(Vec::new()));
        let mut c = cfg();
        c.horizon = 1;
        let r = run_session(&c, &mut OrderedSrc { log: log.clone() }, &mut Ordered { log: log.clone() });
        assert_eq!(r.end, SessionEnd::Completed);
        let per_run = ["cooldown", "void", "read", "run"];
        let want: Vec<&str> = per_run.iter().cycle().take(16).copied().chain(["void", "after"]).collect();
        assert_eq!(*log.borrow(), want);
    }

    #[test]
    fn a_large_true_improvement_crosses_superiority() {
        let mut src = Scripted { a_ns: 10_000_000_000, b_ns: 8_000_000_000, k: 0, fail_at: None, cap_at: None };
        let mut c = cfg();
        c.horizon = 24;
        c.sigma_hat_run = 0.1; // keep the 20% faster arm inside c_run
        let r = run_session(&c, &mut src, &mut Quiet { busy_first: 0, n: 0, profile_ok: true });
        assert!(r.cross_sup.is_some());
        assert!(r.cross_sup.unwrap() >= 8); // 1.5x per block at most: >= 8 blocks to 20
    }
}
