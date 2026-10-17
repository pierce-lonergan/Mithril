//! The bit-exact differential test (MEASUREMENT-SERVICE.md section 8.6): the Rust e-process must
//! reproduce the Python reference's golden wealth path for every block, bit for bit (IEEE-754
//! binary64, round-to-nearest-even, operations in the written order, no FMA contraction). The fixture
//! is generated from `x4_calibration.py --golden`; a crossing is the first block with K_i >= 20.0.

#[path = "golden_fixture.rs"]
#[allow(dead_code)]
mod golden_fixture;

use golden_fixture as g;
use x4svc::eprocess::{block_d, Agrapa, Arm, BlockScorer, EProcess, Scorer, Test, THETA, THETA_KILL};

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

    // clips must themselves match the reference constants bit for bit
    assert_eq!(x4svc::eprocess::clip_for(g::SIGMA_HAT).to_bits(), g::C);
    assert_eq!(x4svc::eprocess::clip_kill_for(g::SIGMA_HAT).to_bits(), g::C_KILL);

    let mut sc_r = BlockScorer::new(Scorer::R, c, c_run);
    let mut sc_k = BlockScorer::new(Scorer::Rk, c_kill, c_run);
    let mut sup = EProcess::make(Test::Superiority, c, THETA);
    let mut ni = EProcess::make(Test::NonInferiority, c, THETA);
    let mut kill = EProcess::make(Test::Kill, c_kill, THETA_KILL);

    for (bi, b) in g::BLOCKS.iter().enumerate() {
        let runs: Vec<(Arm, f64)> =
            b.runs.iter().map(|r| (arm(r.arm), f64::from_bits(r.logtime))).collect();

        // d
        let d = block_d(&runs);
        assert_eq!(d.to_bits(), b.d, "block {} d", bi + 1);

        // scorers
        let x = sc_r.score(d, &runs);
        let xk = sc_k.score(d, &runs);
        assert_eq!(x.to_bits(), b.x, "block {} x (R scorer)", bi + 1);
        assert_eq!(xk.to_bits(), b.x_kill, "block {} x_kill (Rk scorer)", bi + 1);

        // wealth paths
        let ks = sup.update(x);
        let kn = ni.update(x);
        let kk = kill.update(xk);
        assert_eq!(ks.to_bits(), b.k_sup, "block {} K_sup", bi + 1);
        assert_eq!(kn.to_bits(), b.k_ni, "block {} K_ni", bi + 1);
        assert_eq!(kk.to_bits(), b.k_kill, "block {} K_kill", bi + 1);
    }
}

#[test]
fn agrapa_prior_state_matches_reference_first_bet() {
    // A fresh superiority bettor: prior_x=-0.02, c=0.06. The first wealth after the golden block 1 x
    // is k_sup of block 1; reconstruct it through EProcess to confirm the prior mapping and bet order.
    let c = f64::from_bits(g::C);
    let mut sup = EProcess::make(Test::Superiority, c, THETA);
    let x = f64::from_bits(g::BLOCKS[0].x);
    let k = sup.update(x);
    assert_eq!(k.to_bits(), g::BLOCKS[0].k_sup);
    // and the standalone Agrapa used directly reproduces the same step
    let scale = c - 0.0;
    let g0 = -1.0 * (-0.02 - 0.0) / scale;
    let v0 = (c / 3.0 / scale) * (c / 3.0 / scale);
    let mut b = Agrapa::new(THETA, g0, v0);
    let gx = -1.0 * (x - 0.0) / scale;
    assert_eq!(b.update(gx).to_bits(), g::BLOCKS[0].k_sup);
}
