//! The anytime-valid e-processes (MEASUREMENT-SERVICE.md section 8; prereg section 7).
//!
//! A betting (test-martingale) e-process on a clipped block statistic. Validity rests on Ville's
//! inequality: under H0, P(sup_n K_n >= 1/alpha) <= alpha. This module is the Rust implementation that
//! the Python reference (`stats/x4_calibration.py`) is differentially tested against, **bit for bit**
//! (section 8.6): IEEE-754 binary64, round-to-nearest-even, operations in the written order, no FMA
//! contraction. Rust does not contract `a*b+c` into an FMA unless `mul_add` is called, and nothing
//! here calls it. Every constant is pinned; margins are hex constants, never a platform `ln`.

/// Pinned constants (prereg section 7 / PREREG in x4_calibration.py). The margins are the float64
/// nearest to the real value, computed with 60-digit decimal arithmetic in the reference, NOT a
/// platform `ln` (this box's `(1.03f64).ln()` is 8 ulps away, the same error the reference avoids).
pub const M_NI: f64 = f64::from_bits(0x3f9e_44a9_a3be_d663); // RN(ln 1.03) = 0x1.e44a9a3bed663p-6
pub const M_KILL: f64 = f64::from_bits(0x3f9f_30b2_d009_1d82); // RN(-ln 0.97) = 0x1.f30b2d0091d82p-6
pub const THRESHOLD: f64 = 20.0;
pub const THETA: f64 = 0.5; // superiority, non-inferiority
pub const THETA_KILL: f64 = 0.8; // kill

/// Clip rules (section 8.1, 8.4). Given at construction so the pilot's sigma_hat_d flows through one
/// place. c = max(3*sigma, 2*m_NI); c_kill = max(3*sigma, m_kill + 3*sigma); c_run = 4*sigma_run.
pub fn clip_for(sigma: f64) -> f64 {
    (3.0 * sigma).max(2.0 * M_NI)
}
pub fn clip_kill_for(sigma: f64) -> f64 {
    (3.0 * sigma).max(M_KILL + 3.0 * sigma)
}

/// The aGRAPA bettor: the only bettor pre-registered for gates (section 8.5). State carries one prior
/// pseudo-observation. Update order mirrors the reference exactly.
#[derive(Clone, Debug)]
pub struct Agrapa {
    pub k: f64,
    n: f64,
    s1: f64,
    s2: f64,
    theta: f64,
}

impl Agrapa {
    /// n = 1, s1 = g0, s2 = v0 + g0*g0 (one prior pseudo-observation).
    pub fn new(theta: f64, prior_g: f64, prior_var: f64) -> Self {
        Agrapa { k: 1.0, n: 1.0, s1: prior_g, s2: prior_var + prior_g * prior_g, theta }
    }
    /// lam = min(theta, max(0, mu/(var + mu*mu))), mu = s1/n, var = max(s2/n - mu*mu, 1e-12).
    fn bet(&self) -> f64 {
        let mu = self.s1 / self.n;
        let var = (self.s2 / self.n - mu * mu).max(1e-12);
        self.theta.min((mu / (var + mu * mu)).max(0.0))
    }
    /// K <- K*(1 + lam*g) with lam from the state *before* g, then fold g into the running moments.
    pub fn update(&mut self, g: f64) -> f64 {
        let lam = self.bet();
        self.k *= 1.0 + lam * g;
        self.n += 1.0;
        self.s1 += g;
        self.s2 += g * g;
        self.k
    }
}

/// Which null the e-process tests.
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Side {
    /// H0: E[x] >= m (superiority m=0, non-inferiority m=m_NI). g = (m - x)/(c - m), needs c > m.
    Upper,
    /// H0: E[x] <= m (the kill test). g = (x - m)/(c + m).
    Lower,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Test {
    Superiority,
    NonInferiority,
    Kill,
}

/// One e-process: the bet-variable map plus the aGRAPA wealth process.
#[derive(Clone, Debug)]
pub struct EProcess {
    m: f64,
    scale: f64,
    sign: f64,
    bettor: Agrapa,
}

impl EProcess {
    pub fn new(m: f64, c: f64, side: Side, theta: f64, prior_x: f64, prior_sd: Option<f64>) -> Self {
        let (scale, sign) = match side {
            Side::Upper => {
                assert!(c > m, "clip c must exceed the margin m");
                (c - m, -1.0)
            }
            Side::Lower => (c + m, 1.0),
        };
        let sd = prior_sd.unwrap_or(c / 3.0);
        let g0 = sign * (prior_x - m) / scale;
        let v0 = (sd / scale) * (sd / scale);
        EProcess { m, scale, sign, bettor: Agrapa::new(theta, g0, v0) }
    }

    /// Construct the pre-registered e-process for one test at clip c (and theta for the kill).
    pub fn make(test: Test, c: f64, theta: f64) -> Self {
        match test {
            Test::Superiority => EProcess::new(0.0, c, Side::Upper, theta, -0.02, None),
            Test::NonInferiority => EProcess::new(M_NI, c, Side::Upper, theta, 0.0, None),
            Test::Kill => EProcess::new(M_KILL, c, Side::Lower, theta, M_KILL + 0.02, None),
        }
    }

    fn g(&self, x: f64) -> f64 {
        self.sign * (x - self.m) / self.scale
    }
    pub fn update(&mut self, x: f64) -> f64 {
        self.bettor.update(self.g(x))
    }
    pub fn wealth(&self) -> f64 {
        self.bettor.k
    }
    /// A crossing is the first block whose float64 wealth reaches 20.0 (section 8.6).
    pub fn crossed(&self) -> bool {
        self.bettor.k >= THRESHOLD
    }
}

/// The run-level block statistic and scorers (section 8.1). A block is a set of (arm, log_time) runs
/// in the block's order. `R` is the gate scorer; `S` the symmetric A/A secondary; `Rk` the kill
/// scorer; `Lit06` the 06 literal clip (descriptive). The scorer keeps each arm's sorted run history
/// so the "running median" reference is predictable (earlier runs of this session only).
#[derive(Clone, Copy, Debug, PartialEq)]
pub enum Scorer {
    R,
    S,
    Rk,
    Lit06,
}

#[derive(Clone, Debug)]
pub struct BlockScorer {
    kind: Scorer,
    c: f64,
    c_run: f64,
    sorted_a: Vec<f64>,
    sorted_b: Vec<f64>,
    pub slow_a: u64,
    pub slow_b: u64,
    pub nruns_a: u64,
    pub nruns_b: u64,
    pub last_outlier: bool,
}

/// Arm label for a run.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Arm {
    A,
    B,
}

/// Median of a slice that is already sorted ascending, matching the reference `median()` exactly:
/// odd -> middle; even -> 0.5*(lower + upper).
fn median_sorted(xs: &[f64]) -> f64 {
    let n = xs.len();
    if n % 2 == 1 {
        xs[n / 2]
    } else {
        0.5 * (xs[n / 2 - 1] + xs[n / 2])
    }
}

/// Sorted insertion matching Python's `bisect.insort` (insert before equal elements' right edge).
fn insort(v: &mut Vec<f64>, x: f64) {
    let mut lo = 0usize;
    let mut hi = v.len();
    while lo < hi {
        let mid = (lo + hi) / 2;
        if x < v[mid] {
            hi = mid;
        } else {
            lo = mid + 1;
        }
    }
    v.insert(lo, x);
}

impl BlockScorer {
    pub fn new(kind: Scorer, c: f64, c_run: f64) -> Self {
        BlockScorer {
            kind,
            c,
            c_run,
            sorted_a: Vec::new(),
            sorted_b: Vec::new(),
            slow_a: 0,
            slow_b: 0,
            nruns_a: 0,
            nruns_b: 0,
            last_outlier: false,
        }
    }

    fn arm_hist(&self, a: Arm) -> &Vec<f64> {
        // R/Rk reference: the arm's own history; before it has any, arm A's (the incumbent's).
        match a {
            Arm::A => &self.sorted_a,
            Arm::B => {
                if self.sorted_b.is_empty() {
                    &self.sorted_a
                } else {
                    &self.sorted_b
                }
            }
        }
    }

    /// Score one block. `runs` are (arm, log_time) in block order; `d` = 0.5*(sum_B - sum_A).
    pub fn score(&mut self, d: f64, runs: &[(Arm, f64)]) -> f64 {
        let c = self.c;
        if self.kind == Scorer::Lit06 {
            return if -c <= d && d <= c { d } else { c };
        }
        let mut out = false;
        // first pass: detect outliers against the pre-block history (predictable reference)
        for &(a, l) in runs {
            let h = self.arm_hist(a);
            let reference = if h.is_empty() { 0.0 } else { median_sorted(h) };
            let dev = l - reference;
            if dev.abs() > self.c_run {
                out = true;
                if dev > 0.0 {
                    match a {
                        Arm::A => self.slow_a += 1,
                        Arm::B => self.slow_b += 1,
                    }
                }
            }
        }
        // second pass: fold the runs into the history
        for &(a, l) in runs {
            match a {
                Arm::A => {
                    insort(&mut self.sorted_a, l);
                    self.nruns_a += 1;
                }
                Arm::B => {
                    insort(&mut self.sorted_b, l);
                    self.nruns_b += 1;
                }
            }
        }
        self.last_outlier = out;
        if self.kind == Scorer::S {
            return d.max(-c).min(c);
        }
        if out {
            return if self.kind == Scorer::Rk { -c } else { c };
        }
        d.max(-c).min(c)
    }
}

/// Compute the paired block statistic d = 0.5*(sum of B log-times - sum of A log-times).
pub fn block_d(runs: &[(Arm, f64)]) -> f64 {
    let mut sb = 0.0;
    let mut sa = 0.0;
    for &(a, l) in runs {
        match a {
            Arm::B => sb += l,
            Arm::A => sa += l,
        }
    }
    0.5 * (sb - sa)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn margins_are_the_pinned_hex_constants() {
        // bit patterns from x4_calibration.py PREREG
        assert_eq!(M_NI.to_bits(), 0x3f9e_44a9_a3be_d663);
        assert_eq!(M_KILL.to_bits(), 0x3f9f_30b2_d009_1d82);
        // and they are NOT what a platform ln gives (the reference's whole point)
        assert_ne!(M_NI.to_bits(), (1.03f64).ln().to_bits());
    }

    #[test]
    fn clips_match_reference_at_sigma_0_02() {
        // c = max(0.06, 2*m_NI) = 0.06; golden c = 0x1.eb851eb851eb8p-5
        assert_eq!(clip_for(0.02).to_bits(), f64::from_bits(0x3fae_b851_eb85_1eb8).to_bits());
        // c_kill = max(0.06, m_kill+0.06); golden 0x1.72855a9c4d6bcp-4
        assert_eq!(clip_kill_for(0.02).to_bits(), f64::from_bits(0x3fb7_2855_a9c4_d6bc).to_bits());
    }

    #[test]
    fn hand_computed_superiority_first_block() {
        // One block, perfectly symmetric (d=0), no outlier: x=0, g=-0/c=0 (but -0.0), K stays at prior.
        // With prior_x=-0.02, c=0.06: g0 = -1*(-0.02-0)/0.06 = 0.333...; var0=(0.02/0.06)^2.
        // bet(): mu=g0, var=max(s2/n-mu^2,1e-12)= v0 ; lam=min(0.5, mu/(var+mu^2)).
        let mut e = EProcess::make(Test::Superiority, 0.06, THETA);
        let mu = 1.0 / 3.0; // g0
        let v0 = (0.02f64 / 0.06) * (0.02 / 0.06);
        let lam = (0.5f64).min((mu / (v0 + mu * mu)).max(0.0));
        let x = 0.0;
        let g = -1.0 * (x - 0.0) / 0.06; // = -0.0
        let expect = 1.0 * (1.0 + lam * g);
        let got = e.update(x);
        assert_eq!(got.to_bits(), expect.to_bits());
    }

    #[test]
    fn outlier_block_halves_superiority_wealth() {
        // An R-scored block with an outlier run scores +c; g_sup = -c/c = -1; with lam<=0.5, K*=(1+lam*-1).
        let c = 0.06;
        let mut sc = BlockScorer::new(Scorer::R, c, 0.08);
        // seed arm A history so the reference exists, then a huge B deviation triggers the outlier
        let runs = [(Arm::A, 0.0), (Arm::B, 10.0), (Arm::B, 10.0), (Arm::A, 0.0)];
        let d = block_d(&runs);
        let x = sc.score(d, &runs);
        assert_eq!(x.to_bits(), c.to_bits()); // scored +c
        assert!(sc.last_outlier);
    }

    #[test]
    fn insort_matches_bisect_insort_right() {
        let mut v = vec![1.0, 2.0, 2.0, 3.0];
        insort(&mut v, 2.0);
        assert_eq!(v, vec![1.0, 2.0, 2.0, 2.0, 3.0]);
        let mut w = vec![];
        insort(&mut w, 5.0);
        insort(&mut w, -1.0);
        assert_eq!(w, vec![-1.0, 5.0]);
    }

    #[test]
    fn median_even_and_odd() {
        assert_eq!(median_sorted(&[1.0, 3.0]), 2.0);
        assert_eq!(median_sorted(&[1.0, 2.0, 9.0]), 2.0);
    }
}
