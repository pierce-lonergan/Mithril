//! The session engine (review R2-12): run results -> per-run log-times (ln ns) -> randomised ABBA/BAAB
//! blocks from a pinned seed -> scorers -> e-processes, behind the load gate.
//!
//! - Runs come from a `RunSource` (on Windows, `sandbox::run_once` through the job and the bracket; in
//!   tests, a scripted source). Only accepted runs enter a block. An integrity failure stops the session
//!   at once (an evaluator bug in a calibration, the catch in a planted-hack run); it is never re-run.
//!   A time-capped run is scored as a slow outlier (section 8.7).
//! - Blindness (section 5.3): the gate decision (`LoadGate::decide`) takes sensor readings only. The
//!   wealth at every discard and at a void is *logged after* the decision, never passed to it.
//! - Log-times are ln(nanoseconds); the fact states the unit.
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
    fn read(&mut self) -> GateReading;
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

    while res.blocks.len() < cfg.horizon {
        // the blind decision: sensor reading in, decision out; wealth is only logged afterwards
        let reading = sensor.read();
        match gate.decide(&reading) {
            GateDecision::Enter => {}
            GateDecision::Discard => {
                res.discards.push((res.blocks.len(), wealth(&sup, &ni, &kill)));
                continue;
            }
            GateDecision::VoidSession => {
                res.end = SessionEnd::HygieneVoid {
                    reason: if reading.profile_hash_matches { "load gate failed on 3 blocks".into() } else { "profile hash mismatch".into() },
                    wealth_at_void: wealth(&sup, &ni, &kill),
                };
                return res;
            }
        }
        let order = next_order(&mut rng);
        let arms = order.arms();
        let mut runs = [(Arm::A, 0.0f64); 4];
        let mut capped = [false; 4];
        for (i, &arm) in arms.iter().enumerate() {
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
        res.blocks.push(BlockRecord { order, runs, capped, d, x_r, x_s, x_rk, x_lit, k_sup, k_ni, k_kill, k_sup_s });
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
