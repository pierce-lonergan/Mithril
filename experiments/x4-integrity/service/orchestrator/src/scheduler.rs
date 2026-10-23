//! The interleaving scheduler, the load gate and the three void kinds (MEASUREMENT-SERVICE.md
//! section 4, 5.3). ROADMAP's "ABAB interleaving" is implemented as randomised ABBA/BAAB, which is
//! more precise and not looser (ABBA cancels linear drift within a block). The scheduler is **behind a
//! load gate**: a block is only *entered* once the gate passes. Void decisions here are blind to any
//! e-process wealth -- this module never imports the e-process.

use crate::eprocess::Arm;

/// A small deterministic PRNG (SplitMix64) seeded from the pinned schedule seed, so the ABBA/BAAB
/// order is reproducible and auditable (prereg section 2: "its seed is pinned").
#[derive(Clone, Debug)]
pub struct SplitMix64 {
    state: u64,
}

impl SplitMix64 {
    pub fn new(seed: u64) -> Self {
        SplitMix64 { state: seed }
    }
    pub fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9e3779b97f4a7c15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94d049bb133111eb);
        z ^ (z >> 31)
    }
    /// A uniform in [0,1).
    pub fn next_f64(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / ((1u64 << 53) as f64)
    }
}

/// The two randomised block orders.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Order {
    Abba,
    Baab,
}

impl Order {
    pub fn arms(self) -> [Arm; 4] {
        match self {
            Order::Abba => [Arm::A, Arm::B, Arm::B, Arm::A],
            Order::Baab => [Arm::B, Arm::A, Arm::A, Arm::B],
        }
    }
}

/// Draw the next block order (fair coin), matching the reference's `ORDERS[rng.random() < 0.5]`
/// semantics: when the draw is < 0.5 the order is BAAB (index 1), else ABBA (index 0).
pub fn next_order(rng: &mut SplitMix64) -> Order {
    if rng.next_f64() < 0.5 {
        Order::Baab
    } else {
        Order::Abba
    }
}

/// The three kinds of failure, kept apart (section 5.3). An integrity failure rejects the run and
/// quarantines the candidate; a hygiene void removes the session from tallies; a statistical void
/// keeps it in the tally (and counts as an alarm if its e-process had already crossed).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FailureKind {
    Integrity,
    Hygiene,
    Statistical,
}

/// The load gate (section 4). Interleaving is entered only when every condition holds. The threshold
/// is the pilot's rule: min(40%, pilot 99th percentile of pre-run 2-s load + 2 pp). Three or more
/// discarded blocks in one session make it a hygiene void.
#[derive(Clone, Debug)]
pub struct LoadGate {
    pub cpu_threshold_pct: f64,
    pub discards: u32,
    pub discard_limit: u32,
}

/// One pre-block sensor reading the gate consumes. All are external sensors (no e-process state).
#[derive(Clone, Copy, Debug)]
pub struct GateReading {
    pub profile_hash_matches: bool,
    pub quiet_window_active: bool,
    pub cpu_load_2s_pct: f64,
    pub background_idle: bool,
    pub nvme_temp_ok: bool,
    pub no_large_writes: bool,
    /// The run core's LPs (a one-LP run type's LP and its SMT sibling) each quiet over the 2-s window
    /// (X4-noise-pilot section 3/10, revision 4); true where the rule does not apply.
    pub run_core_quiet: bool,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum GateDecision {
    Enter,
    Discard,
    VoidSession,
}

impl LoadGate {
    pub fn new(cpu_threshold_pct: f64) -> Self {
        LoadGate { cpu_threshold_pct, discards: 0, discard_limit: 3 }
    }
    /// Decide whether to enter a block. A profile-hash mismatch voids the session at once; any other
    /// failed condition discards the block, and the third discard voids the session.
    pub fn decide(&mut self, r: &GateReading) -> GateDecision {
        if !r.profile_hash_matches {
            return GateDecision::VoidSession; // hygiene void, section 5.3
        }
        let ok = r.quiet_window_active
            && r.cpu_load_2s_pct < self.cpu_threshold_pct
            && r.background_idle
            && r.nvme_temp_ok
            && r.no_large_writes
            && r.run_core_quiet;
        if ok {
            return GateDecision::Enter;
        }
        self.note_discard()
    }
    /// Count a discard found by another sensor-only check (a post-block discard, X4-noise-pilot
    /// section 10); the third discard of a session voids it.
    pub fn note_discard(&mut self) -> GateDecision {
        self.discards += 1;
        if self.discards >= self.discard_limit {
            GateDecision::VoidSession
        } else {
            GateDecision::Discard
        }
    }
    /// Which condition of a reading failed (for the void log; never an input to a decision).
    pub fn why(r: &GateReading, cpu_threshold_pct: f64) -> String {
        let mut v: Vec<String> = Vec::new();
        if !r.profile_hash_matches {
            v.push("profile hash mismatch".into());
        }
        if !r.quiet_window_active {
            v.push("outside the quiet window".into());
        }
        if !(r.cpu_load_2s_pct < cpu_threshold_pct) {
            v.push(format!("2-s CPU load {:.2}% >= {:.2}%", r.cpu_load_2s_pct, cpu_threshold_pct));
        }
        if !r.background_idle {
            v.push("background services active".into());
        }
        if !r.nvme_temp_ok {
            v.push("NVMe temperature".into());
        }
        if !r.no_large_writes {
            v.push("start state not reached (disk queue / writes)".into());
        }
        if !r.run_core_quiet {
            v.push("run core busy (the run LP or its SMT sibling)".into());
        }
        if v.is_empty() {
            "none".into()
        } else {
            v.join("; ")
        }
    }
}

/// n = max(6, ceil(12*sigma_U^2/delta^2)); N = 2n (section 5.4, delta = 3%).
pub fn blocks_planned(sigma_u: f64, delta: f64) -> u32 {
    let raw = 12.0 * sigma_u * sigma_u / (delta * delta);
    let n = (raw - 1e-9).ceil() as i64;
    (n.max(6)) as u32
}
pub fn horizon(sigma_u: f64, delta: f64) -> u32 {
    2 * blocks_planned(sigma_u, delta)
}

/// Load-gate threshold rule (section 5.4): min(40%, pilot 99th pct of pre-run 2-s load + 2 pp).
pub fn load_gate_threshold(pilot_p99_load_pct: f64) -> f64 {
    40.0f64.min(pilot_p99_load_pct + 2.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn orders_are_abba_and_baab() {
        assert_eq!(Order::Abba.arms(), [Arm::A, Arm::B, Arm::B, Arm::A]);
        assert_eq!(Order::Baab.arms(), [Arm::B, Arm::A, Arm::A, Arm::B]);
    }

    #[test]
    fn order_draw_is_deterministic_and_balanced() {
        let mut rng = SplitMix64::new(20261016);
        let mut a = 0;
        let mut b = 0;
        for _ in 0..10000 {
            match next_order(&mut rng) {
                Order::Abba => a += 1,
                Order::Baab => b += 1,
            }
        }
        assert!((a as i64 - b as i64).abs() < 400, "a={a} b={b}");
        // reproducible
        let mut r2 = SplitMix64::new(20261016);
        let first = next_order(&mut r2);
        let mut r3 = SplitMix64::new(20261016);
        assert_eq!(first, next_order(&mut r3));
    }

    #[test]
    fn profile_mismatch_voids_immediately() {
        let mut g = LoadGate::new(40.0);
        let r = GateReading {
            profile_hash_matches: false,
            quiet_window_active: true,
            cpu_load_2s_pct: 1.0,
            background_idle: true,
            nvme_temp_ok: true,
            no_large_writes: true,
            run_core_quiet: true,
        };
        assert_eq!(g.decide(&r), GateDecision::VoidSession);
    }

    #[test]
    fn three_discards_void_the_session() {
        let mut g = LoadGate::new(40.0);
        let busy = GateReading {
            profile_hash_matches: true,
            quiet_window_active: true,
            cpu_load_2s_pct: 90.0,
            background_idle: true,
            nvme_temp_ok: true,
            no_large_writes: true,
            run_core_quiet: true,
        };
        assert_eq!(g.decide(&busy), GateDecision::Discard);
        assert_eq!(g.decide(&busy), GateDecision::Discard);
        assert_eq!(g.decide(&busy), GateDecision::VoidSession);
    }

    #[test]
    fn blocks_planned_matches_reference() {
        // sigma 2% -> n=max(6, ceil(12*0.0004/0.0009)) = max(6,6)=6 -> N=12
        assert_eq!(blocks_planned(0.02, 0.03), 6);
        assert_eq!(horizon(0.02, 0.03), 12);
        // sigma 4% -> 12*0.0016/0.0009 = 21.33 -> 22 -> N=44
        assert_eq!(blocks_planned(0.04, 0.03), 22);
        assert_eq!(horizon(0.04, 0.03), 44);
    }

    #[test]
    fn gate_threshold_caps_at_40() {
        assert_eq!(load_gate_threshold(50.0), 40.0);
        assert!((load_gate_threshold(10.0) - 12.0).abs() < 1e-9);
    }
}
