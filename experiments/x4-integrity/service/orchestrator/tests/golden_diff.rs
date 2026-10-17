//! The bit-exact differential test (MEASUREMENT-SERVICE.md section 8.6): the Rust e-process must
//! reproduce the Python reference's wealth paths for every block, bit for bit (IEEE-754 binary64,
//! round-to-nearest-even, operations in the written order, no FMA contraction). The fixture is
//! generated from the (unchanged, sha-pinned) `x4_calibration.py` by scratchpad/x4fix/gen_fixture.py:
//! the original `--golden` 24-block sequence, plus extra sequences that make every path bet on many
//! blocks (review R2-14), plus the Mann-Kendall / Clopper-Pearson / chi2 reference vectors.
//!
//! The reference's Scorer hard-codes the run reference at 0.0 for its centred simulation, so the Rust
//! BlockScorer is driven with pilot_median = 0.0 here to match it; the live path (session.rs) passes
//! the pilot incumbent median instead.

#[path = "golden_fixture.rs"]
#[allow(dead_code)]
mod g;

use x4svc::eprocess::{block_d, clip_for, clip_kill_for, Agrapa, Arm, BlockScorer, EProcess, Scorer, Test, THETA, THETA_KILL};
use x4svc::stats::{chi2_quantile, clopper_pearson_upper, mann_kendall_lag1_z};

fn arm(a: u8) -> Arm {
    if a == 0 {
        Arm::A
    } else {
        Arm::B
    }
}

#[test]
fn golden_wealth_path_is_bit_exact() {
    let c = f64::from_bits(g::C);
    let c_kill = f64::from_bits(g::C_KILL);
    let c_run = f64::from_bits(g::C_RUN);
    assert_eq!(clip_for(g::SIGMA_HAT).to_bits(), g::C);
    assert_eq!(clip_kill_for(g::SIGMA_HAT).to_bits(), g::C_KILL);

    let mut sc_r = BlockScorer::new(Scorer::R, c, c_run, 0.0);
    let mut sc_k = BlockScorer::new(Scorer::Rk, c_kill, c_run, 0.0);
    let mut sup = EProcess::make(Test::Superiority, c, THETA);
    let mut ni = EProcess::make(Test::NonInferiority, c, THETA);
    let mut kill = EProcess::make(Test::Kill, c_kill, THETA_KILL);

    for (bi, b) in g::BLOCKS.iter().enumerate() {
        let runs: Vec<(Arm, f64)> = b.runs.iter().map(|r| (arm(r.arm), f64::from_bits(r.logtime))).collect();
        let d = block_d(&runs);
        assert_eq!(d.to_bits(), b.d, "block {} d", bi + 1);
        let x = sc_r.score(d, &runs);
        let xk = sc_k.score(d, &runs);
        assert_eq!(x.to_bits(), b.x, "block {} x (R)", bi + 1);
        assert_eq!(xk.to_bits(), b.x_kill, "block {} x_kill (Rk)", bi + 1);
        assert_eq!(sup.update(x).to_bits(), b.k_sup, "block {} K_sup", bi + 1);
        assert_eq!(ni.update(x).to_bits(), b.k_ni, "block {} K_ni", bi + 1);
        assert_eq!(kill.update(xk).to_bits(), b.k_kill, "block {} K_kill", bi + 1);
    }
}

#[test]
fn extra_sequences_are_bit_exact() {
    // review R2-14: the single golden sequence bets on only 2 (sup) / 1 (kill) blocks; these cases
    // bet on 40/40/60/26 distinct wealth values across the four paths, over 180 blocks.
    let mut bad: Vec<String> = Vec::new();
    for case in g::CASES {
        let (c, ck, cr) = (f64::from_bits(case.c), f64::from_bits(case.ck), f64::from_bits(case.cr));
        if clip_for(case.sigma).to_bits() != case.c || clip_kill_for(case.sigma).to_bits() != case.ck {
            bad.push(format!("{} clip", case.name));
        }
        let mut sr = BlockScorer::new(Scorer::R, c, cr, 0.0);
        let mut ss = BlockScorer::new(Scorer::S, c, cr, 0.0);
        let mut sk = BlockScorer::new(Scorer::Rk, ck, cr, 0.0);
        let mut sl = BlockScorer::new(Scorer::Lit06, c, cr, 0.0);
        let mut sup = EProcess::make(Test::Superiority, c, THETA);
        let mut ni = EProcess::make(Test::NonInferiority, c, THETA);
        let mut kill = EProcess::make(Test::Kill, ck, THETA_KILL);
        let mut sups = EProcess::make(Test::Superiority, c, THETA);
        let mut chk = |n: &str, i: usize, got: f64, want: u64| {
            if got.to_bits() != want {
                bad.push(format!("{} block {} {}: {:#018x} != {:#018x}", case.name, i + 1, n, got.to_bits(), want));
            }
        };
        for (i, row) in case.rows.iter().enumerate() {
            let runs: Vec<(Arm, f64)> = row.runs.iter().map(|r| (if r.b { Arm::B } else { Arm::A }, f64::from_bits(r.l))).collect();
            let d = block_d(&runs);
            chk("d", i, d, row.d);
            let (r, s, rk, l) = (sr.score(d, &runs), ss.score(d, &runs), sk.score(d, &runs), sl.score(d, &runs));
            chk("R", i, r, row.r);
            chk("S", i, s, row.s);
            chk("Rk", i, rk, row.rk);
            chk("06", i, l, row.lit);
            chk("Ksup", i, sup.update(r), row.ksup);
            chk("Kni", i, ni.update(r), row.kni);
            chk("Kkill", i, kill.update(rk), row.kkill);
            chk("KsupS", i, sups.update(s), row.ksups);
        }
    }
    assert!(bad.is_empty(), "{} mismatches: {:?}", bad.len(), &bad[..bad.len().min(8)]);
}

#[test]
fn stats_match_reference() {
    for (v, z) in g::MK {
        assert!((mann_kendall_lag1_z(v) - z).abs() < 1e-9, "MK {} vs {}", mann_kendall_lag1_z(v), z);
    }
    for &(k, n, p) in g::CP {
        assert!((clopper_pearson_upper(k, n, 0.95) - p).abs() < 1e-12);
    }
    for &(p, df, q) in g::CHI {
        assert!(((chi2_quantile(p, df) - q) / q).abs() < 1e-9);
    }
}

#[test]
fn agrapa_prior_state_matches_reference_first_bet() {
    let c = f64::from_bits(g::C);
    let mut sup = EProcess::make(Test::Superiority, c, THETA);
    let x = f64::from_bits(g::BLOCKS[0].x);
    assert_eq!(sup.update(x).to_bits(), g::BLOCKS[0].k_sup);
    let scale = c - 0.0;
    let g0 = -1.0 * (-0.02 - 0.0) / scale;
    let v0 = (c / 3.0 / scale) * (c / 3.0 / scale);
    let mut b = Agrapa::new(THETA, g0, v0);
    let gx = -1.0 * (x - 0.0) / scale;
    assert_eq!(b.update(gx).to_bits(), g::BLOCKS[0].k_sup);
}
