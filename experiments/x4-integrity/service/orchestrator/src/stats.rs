//! Statistical helpers for the calibration gate: exact-enough binomial OC, Clopper-Pearson, the tail
//! check, the stationarity voids S1-S4 (sentinel mean, variance envelope, trend, median envelope) and
//! the pooled mean test (MEASUREMENT-SERVICE.md section 5.3, 8.7; prereg section 7). These are the
//! "computed by a function that does not receive the e-process state" rules: every function here takes
//! sensor readings, run times and calibration/sentinel blocks only -- never any wealth.
//!
//! The float binomial uses the same log-space pmf recurrence as the reference `binom_cdf_f`, so the
//! OC figures agree with `x4_calibration.py` to the printed precision.

use std::f64::consts::PI;

/// ln(1 - p), stable for small p (matches math.log1p(-p)).
fn log1m(p: f64) -> f64 {
    (-p).ln_1p()
}

/// P(X <= k), X ~ Bin(n, p), by the log-space pmf recurrence (reference `binom_cdf_f`).
pub fn binom_cdf(k: i64, n: i64, p: f64) -> f64 {
    if k < 0 {
        return 0.0;
    }
    if k >= n || p <= 0.0 {
        return 1.0;
    }
    if p >= 1.0 {
        return 0.0;
    }
    let mut lt = (n as f64) * log1m(p);
    let step = p.ln() - log1m(p);
    let mut s = lt.exp();
    for i in 0..k {
        lt += (((n - i) as f64) / ((i + 1) as f64)).ln() + step;
        s += lt.exp();
    }
    s.min(1.0)
}

/// P(X >= k), X ~ Bin(n, p).
pub fn binom_sf(k: i64, n: i64, p: f64) -> f64 {
    if k <= 0 {
        return 1.0;
    }
    (1.0 - binom_cdf(k - 1, n, p)).max(0.0)
}

/// One-sided Clopper-Pearson upper bound: the p with P(X <= k | p) = 1 - conf (reference `cp_upper`).
pub fn clopper_pearson_upper(k: i64, n: i64, conf: f64) -> f64 {
    if k >= n {
        return 1.0;
    }
    let (mut lo, mut hi) = (0.0f64, 1.0f64);
    for _ in 0..60 {
        let mid = 0.5 * (lo + hi);
        if binom_cdf(k, n, mid) > 1.0 - conf {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    0.5 * (lo + hi)
}

/// Tail check (section 8.7): deny credit iff P(Bin(n_b, p0) >= k_b) <= level.
pub fn tail_reject(k_b: i64, n_b: i64, p0: f64, level: f64) -> bool {
    binom_sf(k_b, n_b, p0) <= level
}

/// Standard normal CDF via erf.
pub fn normal_cdf(x: f64) -> f64 {
    0.5 * (1.0 + erf(x / 2.0f64.sqrt()))
}

/// Abramowitz-Stegun 7.1.26 erf; max abs error ~1.5e-7, enough for the two-sided 1% gates.
fn erf(x: f64) -> f64 {
    let t = 1.0 / (1.0 + 0.3275911 * x.abs());
    let y = 1.0
        - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592)
            * t
            * (-x * x).exp();
    if x >= 0.0 {
        y
    } else {
        -y
    }
}

/// Inverse standard normal CDF (Acklam's algorithm); used for z_0.995 etc.
pub fn normal_inv_cdf(p: f64) -> f64 {
    const A: [f64; 6] = [
        -3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02, 1.383577518672690e+02,
        -3.066479806614716e+01, 2.506628277459239e+00,
    ];
    const B: [f64; 5] = [
        -5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02, 6.680131188771972e+01,
        -1.328068155288572e+01,
    ];
    const C: [f64; 6] = [
        -7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00, -2.549732539343734e+00,
        4.374664141464968e+00, 2.938163982698783e+00,
    ];
    const D: [f64; 4] = [
        7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00,
    ];
    let plow = 0.02425;
    let phigh = 1.0 - plow;
    if p < plow {
        let q = (-2.0 * p.ln()).sqrt();
        (((((C[0] * q + C[1]) * q + C[2]) * q + C[3]) * q + C[4]) * q + C[5])
            / ((((D[0] * q + D[1]) * q + D[2]) * q + D[3]) * q + 1.0)
    } else if p <= phigh {
        let q = p - 0.5;
        let r = q * q;
        (((((A[0] * r + A[1]) * r + A[2]) * r + A[3]) * r + A[4]) * r + A[5]) * q
            / (((((B[0] * r + B[1]) * r + B[2]) * r + B[3]) * r + B[4]) * r + 1.0)
    } else {
        let q = (-2.0 * (1.0 - p).ln()).sqrt();
        -(((((C[0] * q + C[1]) * q + C[2]) * q + C[3]) * q + C[4]) * q + C[5])
            / ((((D[0] * q + D[1]) * q + D[2]) * q + D[3]) * q + 1.0)
    }
}

/// Regularised lower incomplete gamma P(df/2, x/2) by series (reference `chi2_cdf`; df <= 200).
pub fn chi2_cdf(x: f64, df: f64) -> f64 {
    if x <= 0.0 {
        return 0.0;
    }
    let a = df / 2.0;
    let z = x / 2.0;
    let mut term = 1.0 / a;
    let mut s = term;
    let mut k = 0.0;
    loop {
        k += 1.0;
        term *= z / (a + k);
        s += term;
        if term < s * 1e-15 || k > 10000.0 {
            break;
        }
    }
    (( -z + a * z.ln() - ln_gamma(a)).exp() * s).min(1.0)
}

pub fn chi2_quantile(p: f64, df: f64) -> f64 {
    let (mut lo, mut hi) = (0.0f64, 10.0 * df + 100.0);
    for _ in 0..100 {
        let mid = 0.5 * (lo + hi);
        if chi2_cdf(mid, df) < p {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    0.5 * (lo + hi)
}

/// Lanczos ln(Gamma(x)) for x > 0.
fn ln_gamma(x: f64) -> f64 {
    const G: [f64; 8] = [
        676.5203681218851, -1259.1392167224028, 771.32342877765313, -176.61502916214059,
        12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7,
    ];
    if x < 0.5 {
        (PI / (PI * x).sin()).ln() - ln_gamma(1.0 - x)
    } else {
        let x = x - 1.0;
        let mut a = 0.99999999999980993;
        let t = x + 7.5;
        for (i, &g) in G.iter().enumerate() {
            a += g / (x + (i as f64) + 1.0);
        }
        0.5 * (2.0 * PI).ln() + (x + 0.5) * t.ln() - t + a.ln()
    }
}

/// S1 -- sentinel mean (label asymmetry). Void iff |mean d_sent| > z_0.995 * sigma_hat / sqrt(k).
/// `sent` are the symmetric-clipped d of the unflagged sentinel blocks.
pub fn s1_sentinel_mean(sent: &[f64], sigma_hat: f64) -> bool {
    if sent.is_empty() {
        return false;
    }
    let k = sent.len() as f64;
    let mean = sent.iter().sum::<f64>() / k;
    let z995 = normal_inv_cdf(0.995);
    mean.abs() > z995 * sigma_hat / k.sqrt()
}

/// S2 -- variance envelope. Void iff Sum(x^2)/m is outside [chi2_0.005,m / m, chi2_0.995,m / m] * sigma^2.
/// `clipped` are the clipped d of the unflagged calibration+sentinel blocks.
pub fn s2_variance_envelope(clipped: &[f64], sigma_hat: f64) -> bool {
    let m = clipped.len();
    if m < 2 {
        return false;
    }
    let ss = clipped.iter().map(|v| v * v).sum::<f64>() / (m as f64);
    let lo_q = chi2_quantile(0.005, m as f64) / (m as f64);
    let hi_q = chi2_quantile(0.995, m as f64) / (m as f64);
    let s2 = sigma_hat * sigma_hat;
    !(lo_q * s2 <= ss && ss <= hi_q * s2)
}

/// S3 -- trend. Two-sided Mann-Kendall at alpha 0.01 on an arm's per-run log-times, Hamed-Rao factor
/// restricted to lag 1, always applied, floored at 1, after Sen-slope detrending. Returns the void
/// decision (|z| > z_0.995) for this one arm; the caller voids if *either* arm rejects.
pub fn s3_trend_void(arm_logtimes: &[f64]) -> bool {
    let z = mann_kendall_lag1_z(arm_logtimes);
    z.abs() > normal_inv_cdf(0.995)
}

/// Mann-Kendall z with the lag-1-restricted Hamed-Rao correction (reference `mk_z`'s third return).
pub fn mann_kendall_lag1_z(x: &[f64]) -> f64 {
    let n = x.len();
    if n < 2 {
        return 0.0;
    }
    let mut s = 0i64;
    for i in 0..n - 1 {
        for j in i + 1..n {
            let v = x[j] - x[i];
            s += (v > 0.0) as i64 - (v < 0.0) as i64;
        }
    }
    let var0 = (n as f64) * ((n - 1) as f64) * (2.0 * (n as f64) + 5.0) / 18.0;
    let mut var_l1 = var0;
    if n > 3 {
        // Sen's slope
        let mut slopes = Vec::new();
        for i in 0..n - 1 {
            for j in i + 1..n {
                slopes.push((x[j] - x[i]) / ((j - i) as f64));
            }
        }
        slopes.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let b = median_sorted(&slopes);
        let det: Vec<f64> = (0..n).map(|i| x[i] - b * (i as f64)).collect();
        // rank of the detrended series
        let mut order: Vec<usize> = (0..n).collect();
        order.sort_by(|&p, &q| det[p].partial_cmp(&det[q]).unwrap());
        let mut rk = vec![0.0f64; n];
        for (r, &i) in order.iter().enumerate() {
            rk[i] = (r + 1) as f64;
        }
        let mr = rk.iter().sum::<f64>() / (n as f64);
        let dev: Vec<f64> = rk.iter().map(|v| v - mr).collect();
        let den = dev.iter().map(|v| v * v).sum::<f64>();
        let norm = (n as f64) * ((n - 1) as f64) * ((n - 2) as f64);
        let rho1 = if den > 0.0 {
            (0..n - 1).map(|i| dev[i] * dev[i + 1]).sum::<f64>() / den
        } else {
            0.0
        };
        let factor = 1.0 + 2.0 * ((n - 1) as f64) * ((n - 2) as f64) * ((n - 3) as f64) * rho1 / norm;
        var_l1 = var0 * factor.max(1.0);
    }
    if s == 0 {
        return 0.0;
    }
    let sc = (s - if s > 0 { 1 } else { -1 }) as f64;
    sc / var_l1.sqrt()
}

/// S4 -- incumbent median envelope. Void iff the incumbent session median leaves grand ± max(3*s_between, 1%).
pub fn s4_median_void(session_median: f64, grand_median: f64, s_between: f64) -> bool {
    let band = (3.0 * s_between).max(0.01);
    (session_median - grand_median).abs() > band
}

/// Pooled two-sided z-test of the mean A/A d (section 8.2 tightening secondary): reject at alpha.
pub fn pooled_mean_reject(mean_d: f64, se: f64, alpha: f64) -> bool {
    let z = mean_d / se;
    let crit = normal_inv_cdf(1.0 - alpha / 2.0);
    z.abs() > crit
}

/// Per-arm discard asymmetry: exact two-sided binomial test of B-discards against A-discards at p=0.5.
/// Returns the two-sided p-value; the caller flags if p <= alpha (section 5.3).
pub fn discard_asymmetry_p(a_discards: i64, b_discards: i64) -> f64 {
    let n = a_discards + b_discards;
    if n == 0 {
        return 1.0;
    }
    let k = a_discards.min(b_discards);
    let two = 2.0 * binom_cdf(k, n, 0.5);
    two.min(1.0)
}

fn median_sorted(xs: &[f64]) -> f64 {
    let n = xs.len();
    if n % 2 == 1 {
        xs[n / 2]
    } else {
        0.5 * (xs[n / 2 - 1] + xs[n / 2])
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn binomial_oc_matches_reference() {
        // README table 1: P(Bin(100,p)<=2) = 0.9206 / 0.1183 / 0.0113 at 1% / 5% / 8%.
        assert!((binom_cdf(2, 100, 0.01) - 0.9206).abs() < 5e-4);
        assert!((binom_cdf(2, 100, 0.05) - 0.1183).abs() < 5e-4);
        assert!((binom_cdf(2, 100, 0.08) - 0.0113).abs() < 5e-4);
        assert!((binom_cdf(5, 100, 0.08) - 0.1799).abs() < 5e-4);
    }

    #[test]
    fn clopper_pearson_upper_bounds_zero_count() {
        // P(X<=0|p)=0.05 => (1-p)^n=0.05 => p = 1 - 0.05^(1/n).
        let n = 100;
        let p = clopper_pearson_upper(0, n, 0.95);
        let want = 1.0 - 0.05f64.powf(1.0 / n as f64);
        assert!((p - want).abs() < 1e-6, "{p} vs {want}");
    }

    #[test]
    fn normal_inv_cdf_z995() {
        assert!((normal_inv_cdf(0.995) - 2.5758293035489).abs() < 1e-6);
    }

    #[test]
    fn chi2_median_near_df() {
        // median of chi^2_m is ~ m*(1-2/9m)^3; check order of magnitude and monotonicity
        let q_lo = chi2_quantile(0.005, 8.0);
        let q_hi = chi2_quantile(0.995, 8.0);
        assert!(q_lo < 8.0 && q_hi > 8.0 && q_lo > 0.0);
    }

    #[test]
    fn mann_kendall_detects_monotone_increase() {
        let up: Vec<f64> = (0..24).map(|i| i as f64 * 0.01).collect();
        assert!(s3_trend_void(&up));
        let flat = vec![0.5f64; 24];
        assert!(!s3_trend_void(&flat));
    }

    #[test]
    fn s1_flags_shifted_sentinels() {
        let sigma = 0.02;
        let sent = vec![0.05, 0.05, 0.05, 0.05]; // far above 0
        assert!(s1_sentinel_mean(&sent, sigma));
        let zero = vec![0.0, 0.0, 0.0, 0.0];
        assert!(!s1_sentinel_mean(&zero, sigma));
    }

    #[test]
    fn s4_band_is_max_of_3sbetween_and_1pct() {
        assert!(s4_median_void(0.02, 0.0, 0.001)); // band = max(0.003, 0.01) = 0.01; 0.02 outside
        assert!(!s4_median_void(0.005, 0.0, 0.001)); // inside 0.01
    }

    #[test]
    fn pooled_mean_rejects_large_shift() {
        assert!(pooled_mean_reject(0.005, 0.00058, 0.01));
        assert!(!pooled_mean_reject(0.0001, 0.00058, 0.01));
    }

    #[test]
    fn discard_asymmetry_symmetric_is_high_p() {
        assert!(discard_asymmetry_p(10, 10) > 0.5);
        assert!(discard_asymmetry_p(0, 20) < 0.01);
    }
}
