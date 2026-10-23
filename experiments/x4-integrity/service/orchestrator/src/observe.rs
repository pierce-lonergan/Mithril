//! Observe mode of the noise pilot (docs/m0/prereg/X4-noise-pilot.md section 3; X4 pilot track,
//! 2026-10-23). The pilot *estimates* the integrity tolerances, so it must not be censored by the
//! provisional placeholder values of them: each pilot-derived tolerance runs at its pre-stated hard
//! ceiling, the observed value is recorded per run, and a value above its ceiling is an integrity
//! failure exactly as in a calibration (it stops the pilot). This module holds the ceilings and the
//! per-run observed values; `proto::decide_run` judges, with `Tolerances::observe_ceiling` set.
//!
//! Evidence classes: the bracket, the window cores, the init window and the post-STOP cycles are
//! out-of-process (the orchestrator's own stamps); the per-class post-t1 maxima come from the
//! in-process CENSUS rows (the harness shares an address space with the workload; trusted C here).

use crate::proto::{Observed, Tolerances, CENSUS_W};

/// Hearth's pool spin window, `POOL_SPIN_US` = 50 us (model.c:58 at b5d3f14 [M, clone]).
pub const POOL_SPIN_NS: u64 = 50_000;

/// CENSUS row flags used here (x4proto.h).
const CF_REGISTERED: u64 = 0x002;
const CF_HARNESS: u64 = 0x008;
const CF_PARKED: u64 = 0x200;
const CF_POST_T1_NEW: u64 = 0x800;

/// The hard ceilings of X4-noise-pilot section 3 for one run type [target].
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Ceilings {
    /// kappa_post: process cycles after STOP (2.0e9 in the record).
    pub kappa_post_cycles: u64,
    /// epsilon_spin: post-t1 CPU of a parked registered thread beyond the 50 us pool spin (50 us).
    pub eps_spin_ns: u64,
    /// epsilon_idle: post-t1 CPU of any other thread (1 ms).
    pub eps_idle_ns: u64,
    /// init_max: launch -> START receipt, wall and process cycles.
    pub init_max_ns: u64,
    pub init_max_cycles: u64,
    /// Cores beyond the declared threads in [START, STOP], in thousandths (250 = 0.25 core).
    pub extra_cores_milli: u64,
    /// REPORT -> exit: the child must exit within this grace (revision 4; enforced by the sandbox).
    pub exit_grace_ns: u64,
}

impl Ceilings {
    /// The service tolerances that enforce these ceilings (tau_clock at 0.1% of delta_o).
    pub fn tolerances(&self) -> Tolerances {
        Tolerances {
            pilot_max_abs_diff_ns: 0,
            kappa_post_cycles: self.kappa_post_cycles,
            init_max_ns: self.init_max_ns,
            init_max_cycles: self.init_max_cycles,
            extra_cores_milli: self.extra_cores_milli,
            observe_ceiling: true,
        }
    }
    /// The harness's per-thread post-t1 allowances in cycles at the orchestrator-calibrated rate:
    /// (parked registered threads: pool spin + eps_spin, every other thread: eps_idle).
    pub fn harness_cycles(&self, rate_hz: u64) -> (u64, u64) {
        let c = |ns: u64| (ns as u128 * rate_hz as u128 / 1_000_000_000u128) as u64;
        (c(POOL_SPIN_NS + self.eps_spin_ns).max(1), c(self.eps_idle_ns).max(1))
    }
}

/// Largest post-t1 cycles per class from the CENSUS payload: (spin class = parked registered
/// threads, idle class = every other non-harness thread present at t1). Rows created after t1 and
/// the harness thread are excluded, as in the harness's own rule.
pub fn post_t1_maxima(census: &[u64]) -> (u64, u64) {
    let (mut spin, mut idle) = (0u64, 0u64);
    for row in census.chunks(CENSUS_W) {
        if row.len() != CENSUS_W {
            continue;
        }
        let flags = row[1];
        if flags & (CF_HARNESS | CF_POST_T1_NEW) != 0 {
            continue;
        }
        let post = row[3].saturating_sub(row[2]);
        if flags & CF_REGISTERED != 0 && flags & CF_PARKED != 0 {
            spin = spin.max(post);
        } else {
            idle = idle.max(post);
        }
    }
    (spin, idle)
}

/// The per-run observed value of every observe-mode quantity (None = not observable on this run).
#[derive(Clone, Debug, Default, PartialEq)]
pub struct ObserveValues {
    pub delta_o_ns: Option<u64>,
    pub delta_h_ns: Option<u64>,
    /// |delta_h - delta_o| and the ceiling it was judged by (0.1% of delta_o).
    pub abs_diff_ns: Option<u64>,
    pub tau_ceiling_ns: Option<u64>,
    pub post_stop_cycles: Option<u64>,
    /// REPORT receipt -> exit (the process's teardown): recorded, not judged (proto::Observed).
    pub teardown_cycles: Option<u64>,
    /// REPORT receipt -> exit, wall (revision 4): judged by the exit grace.
    pub teardown_wall_ns: Option<u64>,
    pub post_t1_spin_max_cycles: Option<u64>,
    pub post_t1_idle_max_cycles: Option<u64>,
    pub init_wall_ns: Option<u64>,
    pub init_cycles: Option<u64>,
    /// Cores used in [START, STOP] and the excess over the declared threads.
    pub window_cores: Option<f64>,
    pub extra_cores: Option<f64>,
}

pub fn observe(o: &Observed) -> ObserveValues {
    let delta_o = match (o.start_ns, o.stop_ns) {
        (Some(a), Some(b)) if b > a => Some(b - a),
        _ => None,
    };
    let delta_h = o.report.as_ref().and_then(|r| r.delta_h_ns());
    let abs_diff = match (delta_h, delta_o) {
        (Some(h), Some(d)) => Some(h.abs_diff(d)),
        _ => None,
    };
    let post_stop = match (o.cycles_stop, o.cycles_report.or(o.cycles_exit)) {
        (Some(s), Some(e)) => Some(e.saturating_sub(s)),
        _ => None,
    };
    let teardown = match (o.cycles_report, o.cycles_exit) {
        (Some(r), Some(e)) => Some(e.saturating_sub(r)),
        _ => None,
    };
    let teardown_wall = match (o.report_ns, o.exit_ns) {
        (Some(r), Some(e)) => Some(e.saturating_sub(r)),
        _ => None,
    };
    let (spin, idle) = match &o.census {
        Some(c) => {
            let (s, i) = post_t1_maxima(c);
            (Some(s), Some(i))
        }
        None => (None, None),
    };
    let window = match (delta_o, o.cycles_start, o.cycles_stop) {
        (Some(d), Some(a), Some(b)) if d > 0 && o.cycle_rate_hz > 0 => Some(b.saturating_sub(a) as f64 / (d as f64 / 1e9 * o.cycle_rate_hz as f64)),
        _ => None,
    };
    ObserveValues {
        delta_o_ns: delta_o,
        delta_h_ns: delta_h,
        abs_diff_ns: abs_diff,
        tau_ceiling_ns: delta_o.map(|d| d / 1000),
        post_stop_cycles: post_stop,
        teardown_cycles: teardown,
        teardown_wall_ns: teardown_wall,
        post_t1_spin_max_cycles: spin,
        post_t1_idle_max_cycles: idle,
        init_wall_ns: o.start_ns,
        init_cycles: o.cycles_start,
        window_cores: window,
        extra_cores: window.map(|w| w - o.declared_threads as f64),
    }
}

fn opt_u(v: Option<u64>) -> String {
    v.map(|x| x.to_string()).unwrap_or_else(|| "null".into())
}
fn opt_f(v: Option<f64>) -> String {
    match v {
        Some(x) if x.is_finite() => format!("{:.6}", x),
        _ => "null".into(),
    }
}
fn margin(v: Option<u64>, ceiling: u64) -> String {
    match v {
        Some(x) if ceiling > 0 => format!("{:.6}", x as f64 / ceiling as f64),
        _ => "null".into(),
    }
}

/// The observed epsilon of a post-t1 maximum, net of the allowance the record does not estimate: for
/// the spin class the 50-us pool spin is subtracted (revision 4, review 2026-10-23: section 7(a)
/// doubles the *net* maximum and adds the pool spin back only in the harness allowance), for the idle
/// class nothing. (cycles, microseconds at `rate_hz`).
pub fn eps_net(raw_cycles: Option<u64>, subtract_ns: u64, rate_hz: u64) -> (Option<u64>, Option<f64>) {
    match raw_cycles {
        Some(x) if rate_hz > 0 => {
            let sub = (subtract_ns as u128 * rate_hz as u128 / 1_000_000_000u128) as u64;
            let net = x.saturating_sub(sub);
            (Some(net), Some(net as f64 / rate_hz as f64 * 1e6))
        }
        _ => (None, None),
    }
}

impl ObserveValues {
    /// A JSON object: every value, its ceiling and its margin (value / ceiling; > 1 fails the run).
    pub fn json(&self, c: &Ceilings, rate_hz: u64) -> String {
        let (spin_c, idle_c) = c.harness_cycles(rate_hz);
        let (spin_net, spin_net_us) = eps_net(self.post_t1_spin_max_cycles, POOL_SPIN_NS, rate_hz);
        let (_, idle_us) = eps_net(self.post_t1_idle_max_cycles, 0, rate_hz);
        let extra_margin = match self.extra_cores {
            Some(x) if c.extra_cores_milli > 0 => format!("{:.6}", x / (c.extra_cores_milli as f64 / 1000.0)),
            _ => "null".into(),
        };
        format!(
            concat!(
                "{{\"delta_o_ns\":{},\"delta_h_ns\":{},",
                "\"abs_diff_ns\":{},\"tau_ceiling_ns\":{},\"tau_margin\":{},",
                "\"post_stop_cycles\":{},\"kappa_post_ceiling\":{},\"kappa_post_margin\":{},\"teardown_cycles\":{},",
                "\"teardown_wall_ns\":{},\"exit_grace_ns\":{},\"exit_grace_margin\":{},",
                "\"post_t1_spin_max_cycles\":{},\"spin_ceiling_cycles\":{},\"spin_margin\":{},",
                "\"eps_spin_observed_cycles\":{},\"eps_spin_observed_us\":{},",
                "\"post_t1_idle_max_cycles\":{},\"idle_ceiling_cycles\":{},\"idle_margin\":{},\"eps_idle_observed_us\":{},",
                "\"init_wall_ns\":{},\"init_wall_ceiling_ns\":{},\"init_wall_margin\":{},",
                "\"init_cycles\":{},\"init_cycles_ceiling\":{},\"init_cycles_margin\":{},",
                "\"window_cores\":{},\"extra_cores\":{},\"extra_cores_ceiling\":{:.3},\"extra_cores_margin\":{}}}"
            ),
            opt_u(self.delta_o_ns),
            opt_u(self.delta_h_ns),
            opt_u(self.abs_diff_ns),
            opt_u(self.tau_ceiling_ns),
            match (self.abs_diff_ns, self.tau_ceiling_ns) {
                (Some(a), Some(t)) if t > 0 => format!("{:.6}", a as f64 / t as f64),
                _ => "null".into(),
            },
            opt_u(self.post_stop_cycles),
            c.kappa_post_cycles,
            margin(self.post_stop_cycles, c.kappa_post_cycles),
            opt_u(self.teardown_cycles),
            opt_u(self.teardown_wall_ns),
            c.exit_grace_ns,
            margin(self.teardown_wall_ns, c.exit_grace_ns),
            opt_u(self.post_t1_spin_max_cycles),
            spin_c,
            margin(self.post_t1_spin_max_cycles, spin_c),
            opt_u(spin_net),
            opt_f(spin_net_us),
            opt_u(self.post_t1_idle_max_cycles),
            idle_c,
            margin(self.post_t1_idle_max_cycles, idle_c),
            opt_f(idle_us),
            opt_u(self.init_wall_ns),
            c.init_max_ns,
            margin(self.init_wall_ns, c.init_max_ns),
            opt_u(self.init_cycles),
            c.init_max_cycles,
            margin(self.init_cycles, c.init_max_cycles),
            opt_f(self.window_cores),
            opt_f(self.extra_cores),
            c.extra_cores_milli as f64 / 1000.0,
            extra_margin,
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::proto::tests::good_observed;

    fn row(flags: u64, t1: u64, h: u64) -> Vec<u64> {
        vec![1, flags, t1, h, 0x1F80, 0, 1, 0]
    }

    #[test]
    fn ceilings_map_to_observe_tolerances_and_harness_cycles() {
        let c = Ceilings { kappa_post_cycles: 2_000_000_000, eps_spin_ns: 50_000, eps_idle_ns: 1_000_000, init_max_ns: 2_000_000_000, init_max_cycles: 8_600_000_000, extra_cores_milli: 250, exit_grace_ns: 5_000_000_000 };
        let t = c.tolerances();
        assert!(t.observe_ceiling);
        assert_eq!(t.kappa_post_cycles, 2_000_000_000);
        assert_eq!(t.tau(10_000_000_000), Some(10_000_000));
        // 100 us and 1 ms at 4.296e9 cycles/s
        assert_eq!(c.harness_cycles(4_296_000_000), (429_600, 4_296_000));
    }

    #[test]
    fn post_t1_maxima_split_by_class() {
        let mut census = Vec::new();
        census.extend(row(CF_HARNESS, 0, 9_000_000)); // the harness thread: excluded
        census.extend(row(CF_REGISTERED | CF_PARKED, 100, 300)); // spin class: 200
        census.extend(row(CF_REGISTERED | CF_PARKED, 100, 150)); // spin class: 50
        census.extend(row(CF_REGISTERED, 0, 70)); // registered, unparked: idle class
        census.extend(row(0x001, 10, 40)); // pre-init thread: idle class, 30
        census.extend(row(CF_POST_T1_NEW, 0, 0)); // created after t1: excluded (it fails elsewhere)
        assert_eq!(post_t1_maxima(&census), (200, 70));
        assert_eq!(post_t1_maxima(&[]), (0, 0));
    }

    #[test]
    fn observe_values_from_the_bracket() {
        let mut o = good_observed();
        o.census = Some(row(CF_REGISTERED | CF_PARKED, 5, 25));
        let v = observe(&o);
        assert_eq!(v.delta_o_ns, Some(2_000_000_300));
        assert_eq!(v.delta_h_ns, Some(2_000_000_000));
        assert_eq!(v.abs_diff_ns, Some(300));
        assert_eq!(v.tau_ceiling_ns, Some(2_000_000));
        assert_eq!(v.post_stop_cycles, Some(100));
        assert_eq!(v.post_t1_spin_max_cycles, Some(20));
        assert_eq!(v.init_wall_ns, Some(5_000));
        assert!(v.extra_cores.unwrap() < 0.0);
        let c = Ceilings { kappa_post_cycles: 1_000, eps_spin_ns: 50_000, eps_idle_ns: 1_000_000, init_max_ns: 1_000_000_000, init_max_cycles: 1_000_000, extra_cores_milli: 250, exit_grace_ns: 5_000_000_000 };
        let j = v.json(&c, 4_000_000_000);
        assert!(j.starts_with("{\"delta_o_ns\":2000000300,"));
        assert!(j.contains("\"kappa_post_margin\":0.100000"));
        assert!(j.ends_with('}'));
        // epsilon net of the pool spin: 20 raw spin-class cycles are below 50 us, so net 0
        assert!(j.contains("\"eps_spin_observed_cycles\":0,"), "{j}");
        assert_eq!(eps_net(Some(300_000), POOL_SPIN_NS, 4_000_000_000), (Some(100_000), Some(25.0)));
        assert_eq!(eps_net(Some(4_000), 0, 4_000_000_000), (Some(4_000), Some(1.0)));
        assert_eq!(eps_net(None, 0, 4_000_000_000), (None, None));
        // teardown wall from the REPORT and exit stamps
        let mut o2 = good_observed();
        o2.report_ns = Some(1_000);
        o2.exit_ns = Some(301_000);
        assert_eq!(observe(&o2).teardown_wall_ns, Some(300_000));
    }
}
