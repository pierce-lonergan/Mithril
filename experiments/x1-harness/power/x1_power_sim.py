#!/usr/bin/env python3
"""X1 power simulation: operating characteristics of the X1 kill rules (Mithril M0).

Status: DRAFT instrument for docs/m0/prereg/X1-writability.md (ROADMAP §3.2, DR-017).
Revised 2026-10-16 after an independent same-family review (prereg §12): new blocks 9-13, the
model-family x arm interaction, the CABW "undefined family" rule, template-cluster degrees of
freedom, observed within-family SDs, and the §6.3 recomputation procedure (--recompute).
Extended 2026-10-16 (evening) by the packet track for docs/m0/prereg/X1-amendment-1.md (the Owner's
X1 rule "Claude kills; pass provisional"): blocks 14-19 simulate ONE kill-carrying model family
(F = 1). With F = 1 the item x model-family terms (tau_if) and the three-way item x arm x family
term (tau_iaf) are no longer averaged over two families: they become part of the one family's item
difficulty and item x arm interaction, so the effective item x arm logit SD is
sqrt(tau_ia^2 + tau_iaf^2) = 1.118 x the scenario value [D]. --recompute takes --families 1 and
--cap. Blocks 1-13 are unchanged (same keys, same streams).

What it does
------------
Simulates the task-clustered X1 held-out design and estimates how often each pre-registered
decision rule fires as a function of the true gaps, the item count and the between-item variance:

* K1, VP@1 kill:  fires when the estimated gap Rust - Mithril exceeds 15 points.
* K2, CABW kill:  fires when the estimated CABW(Mithril) - CABW(Rust) exceeds 5 points.
* the disjunction K1 or K2 (DR-017 kills are disjunctive), over a surface of true VP gaps
  g in {0, 5, 10, 15} and true CABW gaps h in {0, 10} (block 9);
* the one-family-only Owner referral of prereg §7.7 (no pooled kill, but K1 or K2 holds on one
  model family's own estimate), with and without a fixed model-family x arm interaction (block 11);
* amber (a) (tooling arm beats Mithril by > 10 points) and amber (b) (traits ablation costs
  > 5 points), as review-trigger operating characteristics;
* the realised MDE fact `harness.x1.mde_points` that DR-017's revisit trigger reads, and the share
  of replicates whose CABW standard error exceeds 3.90 points (prereg §6.5, Owner question);
* the §6.3 calibration procedure: how often the upper-80% bounds from 24 calibration items reach the
  true dispersion (block 12), and the n-recomputation rule itself (--recompute; block 13).

Every output number is [S] (simulated by this script). Every input number is [G] (judgment)
unless the comment says otherwise. Nothing here is a measurement of any model.

Data-generating model (logit scale; see DESIGN.md §14 and the prereg §6.2)
-------------------------------------------------------------------------
For item i (in task family T(i)), model family f, arm a, one attempt ends in one of three states:
  accepted  (submitted AND passes the arm's own checker + visible tests), probability alpha
  accepted-and-correct (hidden oracle passes) = verified pass, probability alpha * (1 - c)
  accepted-but-wrong (hidden oracle rejects), probability alpha * c
  not accepted (counts as a fail for VP@1), probability 1 - alpha
The record defines a verified pass as "submitted AND the hidden oracle passes" (prereg §4.8), and
attempts that end by a budget limit or `abandon` are fails, as "not accepted" is here. The record
makes the fourth state "submitted, not accepted, oracle passes" empty by construction outside the
kit arm (every visible-test case is also an oracle case; `mithi vectors` runs the full check first;
a build failure fails the oracle). Its rate is reported per arm, not simulated.
with
  logit alpha = a0[a] + phi_a[f] + Tfx_a[T] + TAfx_a[a][T] + u_a[i] + v_a[i,a] + w_a[i,f] + x_a[i,f,a]
                (+ d * s_f on arm 1 only, s_f = +1 for family A and -1 for family B: the fixed
                 model-family x arm interaction `famxarm`, 0 unless a block sets it)
  logit c     = c0[a] + phi_c[f] + Tfx_c[T] + TAfx_c[a][T] + u_c[i] + v_c[i,a] + w_c[i,f] + x_c[i,f,a]
Task families are fixed strata (the eight ROADMAP families), so their effects are fixed numbers
(evenly spaced normal quantiles), and the true gap is defined over those eight families with equal
weight. u, v, w, x are independent normal random effects (u_a, u_c correlated with rho).
Template block (4b): items can share templates (k_tmpl items per template); a share s_tmpl of the
item-level variances of u and v then sits at the template level, total variances unchanged, and the
SEs cluster on templates with degrees of freedom = template clusters - 8.
The arm intercepts a0[a], c0[a] are solved numerically (2-D Gauss-Hermite quadrature) so that the
population VP@1 and CABW of each arm hit their targets exactly; the "true gap" is therefore the
estimand itself, not a logit coefficient. With famxarm != 0 the pooled targets still hold exactly,
and the two model families' own gaps diverge.

Analysis simulated (the pre-registered decision statistic)
----------------------------------------------------------
VP@1 gap: the balanced, task-family-stratified mean difference of per-cell pass proportions,
task families and model families weighted equally (= the identity-link mixed model's fixed effect
in a balanced design; = GEE identity link with item clusters). SE: stratified item-cluster-robust.
CABW: per (model family, arm) stratified ratio estimator sum(wrong & accepted)/sum(accepted),
model families weighted equally; SE by item-cluster linearisation (delta method), stratified.
If an arm has no accepted attempt in a model family, that family's CABW gap is undefined and the
pooled gap uses the other family alone; if neither family is defined, K2 cannot fire (prereg §7.2).
Kill decisions use the point estimates only (ROADMAP/05 §13 point-estimate rules).

Run
---
  python x1_power_sim.py --out results                       # every block (173 s in total on the shared laptop, 2026-10-16)
  python x1_power_sim.py --out results --blocks vp --merge    # one block, merged into existing results
  python x1_power_sim.py --out results --quick                # smoke test (few reps)
  python x1_power_sim.py --recompute --vp-ref 0.42 --cabw-ref 0.18 --sd-d-up 0.31 --sd-e-up 0.40          --recompute-out recompute.json                       # prereg §6.3 steps 3-4 (20,000 reps per point);
                                                              # the inputs shown are placeholders, not data
  python x1_power_sim.py --out results --blocks f1_oc,f1_surface,f1_confirm,f1_templates,f1_attempts,f1_base_rates,f1_calib --merge
                                                              # the F = 1 blocks 14-19 (X1-amendment-1)
  python x1_power_sim.py --recompute --families 1 --cap 256 ...   # §6.3 steps 3-4 with one kill-carrying family
Requires numpy only (run with numpy 2.5.4, Python 3.12.10). The seed is fixed (MASTER_SEED); each
configuration's stream is derived from the seed and a CRC32 of its key, so adding configurations
never changes existing results, and a block can be re-run alone with --merge.
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import platform
import sys
import time
import zlib
from statistics import NormalDist

import numpy as np

MASTER_SEED = 20261016
N_TF = 8                     # ROADMAP §3.2: eight task families
KILL_VP = 0.15               # ROADMAP §3.2 [target]: VP@1 gap > 15 points
KILL_CABW = 0.05             # ROADMAP §3.2 [target]: CABW worse than Rust's by > 5 points
AMBER_A = 0.10               # ROADMAP §3.2 [target]: Rust + tooling beats Mithril by > 10 points
AMBER_B = 0.05               # ROADMAP §3.2: traits ablation costs > 5 points
Z90 = NormalDist().inv_cdf(0.90)          # 1.2816
MDE_FACTOR = 2.0 * Z90                     # one-sided alpha 0.10, power 0.90 -> 2.563 * SE
SE_C_REQ = KILL_CABW / Z90                 # 3.90 points: the CABW SE at which a point rule meets 10%/90%
MC_Z = NormalDist().inv_cdf(0.975)         # Monte Carlo 95% bounds in the n rule (prereg §6.3 step 4)

# ---------------------------------------------------------------- parameters [G]
COMMON = dict(
    vp_ref=0.50,        # [G] population VP@1 of the reference arm (Rust)
    cabw_ref=0.20,      # [G] population CABW of the reference arm (Rust)
    tau_i_a=1.5,        # [G] item difficulty SD on logit(alpha)
    tau_i_c=1.0,        # [G] item SD on logit(c) (e.g. weak visible tests)
    rho=0.0,            # [G] corr(u_a, u_c); sensitivity at -0.5
    tau_T_a=0.75,       # [G] task-family spread on logit(alpha) (fixed strata)
    tau_T_c=0.50,       # [G] task-family spread on logit(c)
    tau_TA_a=0.40,      # [G] task-family x arm spread on logit(alpha)
    tau_TA_c=0.30,      # [G] task-family x arm spread on logit(c)
    tau_if_a=0.50,      # [G] item x model-family SD on logit(alpha)
    tau_if_c=0.40,      # [G] item x model-family SD on logit(c)
    phi_a=0.25,         # [G] model-family main effect on logit(alpha): +/- this
    phi_c=0.15,         # [G] model-family main effect on logit(c): -/+ this
    famxarm=0.0,        # [G] fixed model-family x arm interaction on arm 1's logit(alpha): +d in family A,
                        # -d in family B (e.g. an authorship advantage of one family in one arm); block 11
    k_tmpl=1,           # items per template (parametric variants of one task); 1 = independent items
    s_tmpl=0.0,         # [G] share of the item-level variances (intercept and item x arm) that sits
                        # at the template level when k_tmpl > 1; total variances are unchanged
)
# The item x arm SD is the quantity that decides power (05 §13 calls its probability-scale
# counterpart sigma_ta). Four levels [G]; the three-way item x arm x model-family SD is half of it.
SCENARIOS = {
    "low": 0.35,
    "mid": 0.70,
    "high": 1.05,
    "stress": 1.40,
}
# Ladder used by the §6.3 recomputation when the calibration bounds exceed "stress" [G]
LADDER = dict(SCENARIOS, **{"stress+1": 1.75, "stress+2": 2.10, "stress+3": 2.45})
PLAN_SCENARIO = "high"      # the scenario the planned n is sized for; the recomputation never goes below it

# ---------------------------------------------------------------- numerics helpers
_gx, _gw = np.polynomial.hermite_e.hermegauss(24)
_gw = _gw / _gw.sum()
GH_Z1 = np.repeat(_gx, _gx.size)
GH_Z2 = np.tile(_gx, _gx.size)
GH_W = np.outer(_gw, _gw).ravel()


def expit(x):
    return 1.0 / (1.0 + np.exp(-x))


def t_quantile(p, df):
    """Student t quantile via the Cornish-Fisher expansion (Abramowitz & Stegun 26.7.5)."""
    z = NormalDist().inv_cdf(p)
    g1 = (z**3 + z) / 4
    g2 = (5 * z**5 + 16 * z**3 + 3 * z) / 96
    g3 = (3 * z**7 + 19 * z**5 + 17 * z**3 - 15 * z) / 384
    g4 = (79 * z**9 + 776 * z**7 + 1482 * z**5 - 1920 * z**3 - 945 * z) / 92160
    return z + g1 / df + g2 / df**2 + g3 / df**3 + g4 / df**4


def _gammainc_lower_reg(a, x):
    """Regularised lower incomplete gamma P(a, x) (series below a+1, Lentz continued fraction above)."""
    if x <= 0.0:
        return 0.0
    lead = math.exp(-x + a * math.log(x) - math.lgamma(a))
    if x < a + 1.0:
        term = 1.0 / a
        s, ap = term, a
        for _ in range(2000):
            ap += 1.0
            term *= x / ap
            s += term
            if abs(term) < abs(s) * 1e-16:
                break
        return s * lead
    tiny = 1e-300
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    h = d
    for i in range(1, 2000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-16:
            break
    return 1.0 - lead * h


def chi2_ppf(p, k):
    """Chi-square quantile by bisection on the regularised incomplete gamma function."""
    lo, hi = 0.0, 20.0 + 10.0 * k
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if _gammainc_lower_reg(k / 2.0, mid / 2.0) < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def spread(k, sd, perm_seed):
    """k evenly spaced normal quantiles with SD-scale sd, in a fixed permuted order."""
    q = np.array([NormalDist().inv_cdf((j + 0.5) / k) for j in range(k)]) * sd
    if k > 1:
        q = q[np.random.default_rng(perm_seed).permutation(k)]
    return q


class Params:
    def __init__(self, scen_sd, n_tf=N_TF, n_fam=2, n_arms=2, **over):
        p = dict(COMMON)
        p.update(over)
        self.__dict__.update(p)
        self.tau_ia = scen_sd
        self.tau_iaf = scen_sd / 2
        self.n_tf, self.n_fam, self.n_arms = n_tf, n_fam, n_arms
        sign = np.array([1.0, -1.0])[:n_fam] if n_fam > 1 else np.array([0.0])
        self.phi_a_v = self.phi_a * sign
        self.phi_c_v = -self.phi_c * sign
        self.fx_v = self.famxarm * sign          # model-family x arm interaction, arm 1 only
        self.T_a = spread(n_tf, self.tau_T_a, 11)
        self.T_c = spread(n_tf, self.tau_T_c, 12)
        # arm 0 is the reference arm; task-family x arm deviations only on the other arms
        self.TA_a = [np.zeros(n_tf)] + [spread(n_tf, self.tau_TA_a, 20 + k) for k in range(1, n_arms)]
        self.TA_c = [np.zeros(n_tf)] + [spread(n_tf, self.tau_TA_c, 30 + k) for k in range(1, n_arms)]
        self.sa = math.sqrt(self.tau_i_a**2 + self.tau_ia**2 + self.tau_if_a**2 + self.tau_iaf**2)
        self.sc = math.sqrt(self.tau_i_c**2 + self.tau_ia**2 + self.tau_if_c**2 + self.tau_iaf**2)
        self.r = self.rho * self.tau_i_a * self.tau_i_c / (self.sa * self.sc)
        self.key = json.dumps(dict(p, scen_sd=scen_sd, n_tf=n_tf, n_fam=n_fam, n_arms=n_arms), sort_keys=True)

    def describe(self):
        keys = list(COMMON) + ["tau_ia", "tau_iaf", "n_tf", "n_fam"]
        return {k: getattr(self, k) for k in keys}


def arm_moments(P, arm, a0, c0):
    """Population E[alpha] and E[alpha*c] per (model family, task family) for one arm."""
    eta_a = a0 + P.phi_a_v[:, None] + P.T_a[None, :] + P.TA_a[arm][None, :]
    if arm == 1 and P.famxarm != 0.0:
        eta_a = eta_a + P.fx_v[:, None]
    eta_c = c0 + P.phi_c_v[:, None] + P.T_c[None, :] + P.TA_c[arm][None, :]
    za = GH_Z1
    zc = P.r * GH_Z1 + math.sqrt(1 - P.r**2) * GH_Z2
    al = expit(eta_a[..., None] + P.sa * za)
    cc = expit(eta_c[..., None] + P.sc * zc)
    AC = (al * GH_W).sum(-1)
    AW = (al * cc * GH_W).sum(-1)
    return AC, AW


def estimands(AC, AW):
    vp = (AC - AW).mean(axis=1).mean()                 # task families, then model families, equal
    cabw = (AW.mean(axis=1) / AC.mean(axis=1)).mean()  # stratified ratio per model family
    return vp, cabw


def _bisect(f, lo=-14.0, hi=14.0, it=48):
    flo = f(lo)
    for _ in range(it):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return 0.5 * (lo + hi)


_CAL_CACHE = {}


def solve_arm(P, arm, vp_t, cabw_t):
    """Arm intercepts (a0, c0) such that the arm's population VP@1 and CABW equal the targets."""
    key = (P.key, arm, round(vp_t, 12), round(cabw_t, 12))
    if key in _CAL_CACHE:
        return _CAL_CACHE[key]
    a0, c0 = 0.5, -1.4
    for _ in range(30):
        a0 = _bisect(lambda a: estimands(*arm_moments(P, arm, a, c0))[0] - vp_t)
        c0 = _bisect(lambda c: estimands(*arm_moments(P, arm, a0, c))[1] - cabw_t)
        vp, cabw = estimands(*arm_moments(P, arm, a0, c0))
        if abs(vp - vp_t) < 1e-8 and abs(cabw - cabw_t) < 1e-8:
            break
    if abs(vp - vp_t) > 1e-6 or abs(cabw - cabw_t) > 1e-6:
        raise RuntimeError(f"calibration failed: arm {arm} vp {vp} vs {vp_t}, cabw {cabw} vs {cabw_t}")
    _CAL_CACHE[key] = (a0, c0)
    return a0, c0


# ---------------------------------------------------------------- simulation
def strat_se(d, tf, n_T, n_tf, cl=None):
    """Stratified cluster-robust SE of sum_T (1/n_tf) * mean_{i in T} d_i.

    Strata are task families; clusters are templates (items when cl is None). For each stratum the
    variance of the item mean is estimated from cluster totals (CR1-type small-sample factor G/(G-1)).
    With one item per cluster this is the usual s_T^2 / n_T.
    """
    if cl is None:
        var = np.zeros(d.shape[0])
        for T in range(n_tf):
            sel = tf == T
            var += (1.0 / n_tf) ** 2 * d[:, sel].var(axis=1, ddof=1) / n_T[T]
        return np.sqrt(var)
    n_cl = cl.max() + 1
    M = np.zeros((d.shape[1], n_cl))
    M[np.arange(d.shape[1]), cl] = 1.0
    S = d @ M
    n_c = M.sum(0)
    cl_tf = np.array([tf[np.flatnonzero(cl == c)[0]] for c in range(n_cl)])
    var = np.zeros(d.shape[0])
    for T in range(n_tf):
        sel = cl_tf == T
        G = sel.sum()
        dbar = S[:, sel].sum(1) / n_T[T]
        resid = S[:, sel] - n_c[sel][None, :] * dbar[:, None]
        var += (1.0 / n_tf) ** 2 * (G / (G - 1)) * (resid**2).sum(1) / n_T[T] ** 2
    return np.sqrt(var)


def within_sd(x, tf, n_tf):
    """Per replicate: pooled within-task-family SD of item-level values x (reps, n); df = n - n_tf.

    This is the observed-scale dispersion that the §6.3 recomputation estimates from the
    calibration items (prereg §6.3 step 2) and matches against this simulation.
    """
    ss = np.zeros(x.shape[0])
    df = 0
    for T in range(n_tf):
        xs = x[:, tf == T]
        ss += ((xs - xs.mean(axis=1, keepdims=True)) ** 2).sum(axis=1)
        df += xs.shape[1] - 1
    return np.sqrt(ss / max(df, 1))


def simulate(P, targets, m, n, reps, rng, return_items=False):
    """targets: list of (vp, cabw) per arm (arm 0 = reference). m: attempts per cell per arm.

    Returns a dict of per-replicate statistics for the contrast reference(0) vs comparison(1).
    The random draws below are in a fixed order; do not reorder them (results are keyed by config).
    """
    A = len(targets)
    F = P.n_fam
    coef = [solve_arm(P, a, *targets[a]) for a in range(A)]
    tf = np.arange(n) % P.n_tf
    n_T = np.bincount(tf, minlength=P.n_tf)
    tmpl = tf + P.n_tf * ((np.arange(n) // P.n_tf) // P.k_tmpl)   # same family, consecutive rounds
    _, tmpl = np.unique(tmpl, return_inverse=True)
    n_tm = tmpl.max() + 1
    m_arr = np.asarray(m, dtype=np.int64).reshape(1, 1, 1, A)

    fa = np.empty((F, P.n_tf, A))
    fc = np.empty((F, P.n_tf, A))
    for a in range(A):
        fa[:, :, a] = coef[a][0] + P.phi_a_v[:, None] + P.T_a[None, :] + P.TA_a[a][None, :]
        if a == 1 and P.famxarm != 0.0:
            fa[:, :, a] = fa[:, :, a] + P.fx_v[:, None]
        fc[:, :, a] = coef[a][1] + P.phi_c_v[:, None] + P.T_c[None, :] + P.TA_c[a][None, :]
    fa_i = np.transpose(fa[:, tf, :], (1, 0, 2))[None]   # (1, n, F, A)
    fc_i = np.transpose(fc[:, tf, :], (1, 0, 2))[None]

    st, si = math.sqrt(P.s_tmpl), math.sqrt(1 - P.s_tmpl)

    def lvl(shape_tail):
        # item-level normal = template part (shared by the template's items) + item part
        if P.s_tmpl == 0.0:
            return rng.standard_normal((reps, n) + shape_tail)
        t = rng.standard_normal((reps, n_tm) + shape_tail)[:, tmpl]
        return st * t + si * rng.standard_normal((reps, n) + shape_tail)

    z1 = lvl((1, 1))
    z2 = P.rho * z1 + math.sqrt(1 - P.rho**2) * lvl((1, 1))
    eta_a = (fa_i + P.tau_i_a * z1
             + P.tau_ia * lvl((1, A))
             + P.tau_if_a * rng.standard_normal((reps, n, F, 1))
             + P.tau_iaf * rng.standard_normal((reps, n, F, A)))
    eta_c = (fc_i + P.tau_i_c * z2
             + P.tau_ia * lvl((1, A))
             + P.tau_if_c * rng.standard_normal((reps, n, F, 1))
             + P.tau_iaf * rng.standard_normal((reps, n, F, A)))
    cl = tmpl if P.k_tmpl > 1 else None
    alpha = expit(eta_a)
    cpr = expit(eta_c)
    acc = rng.binomial(np.broadcast_to(m_arr, alpha.shape), alpha)
    wrong = rng.binomial(acc, cpr)
    vpass = acc - wrong

    wt = (1.0 / (P.n_tf * n_T[tf]))[None, :, None, None]      # stratum weights, sum to 1 per (f, a)
    p_hat = vpass / m_arr
    vp_fa = (p_hat * wt).sum(1)                                 # (reps, F, A)
    gap_f = vp_fa[..., 0] - vp_fa[..., 1]                       # (reps, F): per-model-family gaps
    gap = gap_f.mean(-1)                                        # reference minus comparison
    d_i = (p_hat[..., 0] - p_hat[..., 1]).mean(-1)              # (reps, n)
    se = strat_se(d_i, tf, n_T, P.n_tf, cl)
    # naive SE that treats every attempt as independent (shown only to quantify the error)
    se_naive = np.sqrt(((vp_fa * (1 - vp_fa)) / (n * m_arr[0, 0])).sum(-1).sum(-1)) / F

    a_hat = acc / m_arr
    w_hat = wrong / m_arr
    Nw = (w_hat * wt).sum(1)
    Dn = (a_hat * wt).sum(1)
    empty = (Dn <= 0).any(axis=(1, 2))
    Dn_safe = np.where(Dn > 0, Dn, 1.0)
    R = np.where(Dn > 0, Nw / Dn_safe, 0.0)
    e = (w_hat - R[:, None] * a_hat) / Dn_safe[:, None]
    valid = (Dn > 0).all(axis=-1)                               # (reps, F): both arms have accepted attempts
    if valid.all():
        cgap_f = R[..., 1] - R[..., 0]
        cgap = cgap_f.mean(-1)                                  # comparison minus reference
        e_i = (e[..., 1] - e[..., 0]).mean(-1)
        c_undef = np.zeros(reps, dtype=bool)
    else:
        # prereg §7.2: a family whose arm has no accepted attempt is dropped from the CABW gap
        nv = valid.sum(-1)
        cgap_f = np.where(valid, R[..., 1] - R[..., 0], np.nan)
        cgap = np.where(nv > 0, np.where(valid, R[..., 1] - R[..., 0], 0.0).sum(-1) / np.maximum(nv, 1), np.nan)
        e_i = (np.where(valid[:, None, :], e[..., 1] - e[..., 0], 0.0).sum(-1)
               / np.maximum(nv, 1)[:, None])
        c_undef = nv == 0
    se_c = strat_se(e_i, tf, n_T, P.n_tf, cl)

    p_true = alpha * (1 - cpr)
    d_true = (p_true[..., 0] - p_true[..., 1]).mean(-1)
    sig_ta = d_true.std(axis=1, ddof=1).mean()
    within = np.zeros(reps)
    for T in range(P.n_tf):
        within += d_true[:, tf == T].var(axis=1, ddof=1) / P.n_tf
    sig_ta_within = np.sqrt(within).mean()
    sd_p_ref = p_true[..., 0].mean(-1).std(axis=1, ddof=1).mean()
    sd_d_obs_rep = within_sd(d_i, tf, P.n_tf)
    sd_e_obs_rep = within_sd(e_i, tf, P.n_tf)
    out = dict(gap=gap, gap_f=gap_f, se=se, se_naive=se_naive, cgap=cgap, cgap_f=cgap_f, se_c=se_c,
               empty=empty, c_undef=c_undef,
               sig_ta=sig_ta, sig_ta_within=sig_ta_within, sd_p_ref=sd_p_ref,
               sd_d_within_obs=float(sd_d_obs_rep.mean()), sd_e_within_obs=float(sd_e_obs_rep.mean()),
               n=n, n_cl=(n_tm if P.k_tmpl > 1 else n), n_tf=P.n_tf, reps=reps)
    if return_items:
        out["d_i"] = d_i
        out["sd_d_obs_rep"] = sd_d_obs_rep
        out["sd_e_obs_rep"] = sd_e_obs_rep
    return out


def _f(v):
    if isinstance(v, (int, str)) or v is None:
        return v
    v = float(v)
    return None if math.isnan(v) else v


def summarise(S, true_gap, true_cgap, thr_vp=KILL_VP, thr_c=KILL_CABW):
    reps = S["reps"]
    df = max(S["n_cl"] - S["n_tf"], 1)          # clusters - 8 (items, or templates in block 4b)
    tq = t_quantile(0.95, df)
    kill_vp = S["gap"] > thr_vp
    kill_c = S["cgap"] > thr_c                  # NaN (undefined CABW gap) never fires
    kill_any = kill_vp | kill_c
    fam_breach = ((S["gap_f"] > thr_vp) | (S["cgap_f"] > thr_c)).any(axis=-1)
    mde = MDE_FACTOR * S["se"]
    under = mde > 0.15
    defined = ~S["c_undef"]
    cg = S["cgap"][defined]
    sec = S["se_c"][defined]
    out = dict(
        p_kill_vp=kill_vp.mean(), p_kill_cabw=kill_c.mean(), p_kill_any=kill_any.mean(),
        p_kill_any_not_underpowered=(kill_any & ~under).mean(),
        p_refer_one_family=(~kill_any & fam_breach).mean(),
        p_gap_gt_10=(S["gap"] > AMBER_A).mean(),
        mean_gap=S["gap"].mean(), sd_gap=S["gap"].std(ddof=1), mean_se=S["se"].mean(),
        cover90=(np.abs(S["gap"] - true_gap) <= tq * S["se"]).mean(),
        cover90_naive=(np.abs(S["gap"] - true_gap) <= NormalDist().inv_cdf(0.95) * S["se_naive"]).mean(),
        mean_se_naive=S["se_naive"].mean(),
        mean_cgap=cg.mean() if cg.size else None, sd_cgap=cg.std(ddof=1) if cg.size > 1 else None,
        mean_se_c=sec.mean() if sec.size else None,
        cover90_c=(np.abs(cg - true_cgap) <= tq * sec).mean() if cg.size else None,
        p_se_c_gt_390=(sec > SE_C_REQ).mean() if sec.size else None,
        sd_gap_family=np.nanstd(S["gap_f"], ddof=1, axis=0).mean(),
        sd_cgap_family=np.nanstd(S["cgap_f"], ddof=1, axis=0).mean(),
        mde_mean=mde.mean(), p_underpowered=under.mean(), p_empty_arm=S["empty"].mean(),
        p_cabw_undefined=S["c_undef"].mean(),
        sigma_ta=S["sig_ta"], sigma_ta_within=S["sig_ta_within"], sd_p_ref=S["sd_p_ref"],
        sd_d_within_obs=S["sd_d_within_obs"], sd_e_within_obs=S["sd_e_within_obs"],
        df=df, mc_se_at_10pct=math.sqrt(0.09 / reps),
    )
    return {k: _f(v) for k, v in out.items()}


def cfg_rng(key):
    return np.random.default_rng([MASTER_SEED, zlib.crc32(key.encode())])


def mc_bounds(p, reps):
    """Monte Carlo 95% bounds of a simulated probability (normal approximation)."""
    h = MC_Z * math.sqrt(max(p * (1 - p), 0.0) / reps)
    return p - h, p + h


# ---------------------------------------------------------------- requirement sets
# The OC points the record's requirements are evaluated at (prereg §6.2):
#   R-VP    (ROADMAP §3.2):  P(K1 | g=5, h=0) <= 0.10 and P(K1 | g=25, h=0) >= 0.90
#   R-CABW  (05 §13 analogue, binding here, made precise): for every g in {0, 5, 10, 15}:
#           P(K2 | g, h=0) <= 0.10 and P(K2 | g, h=10) >= 0.90
#   R-JOINT (ROADMAP §3.2 read for the disjunctive kill): P(K1 or K2 | g=5, h=0) <= 0.10
SURFACE_POINTS = [(0.0, 0.0), (0.0, 0.10), (0.05, 0.0), (0.05, 0.10), (0.10, 0.0), (0.10, 0.10),
                  (0.15, 0.0), (0.15, 0.10), (0.25, 0.0)]
SURFACE_G = (0.0, 0.05, 0.10, 0.15)


def check_requirements(get, reps, mc):
    """get(g, h, col) -> simulated probability. mc=True applies the Monte Carlo 95% bound rule."""
    def le(p):
        return (mc_bounds(p, reps)[1] if mc else p) <= 0.10

    def ge(p):
        return (mc_bounds(p, reps)[0] if mc else p) >= 0.90

    r_vp = le(get(0.05, 0.0, "p_kill_vp")) and ge(get(0.25, 0.0, "p_kill_vp"))
    r_c = all(le(get(g, 0.0, "p_kill_cabw")) and ge(get(g, 0.10, "p_kill_cabw")) for g in SURFACE_G)
    r_j = le(get(0.05, 0.0, "p_kill_any"))
    return dict(r_vp=r_vp, r_cabw=r_c, r_joint=r_j, all=r_vp and r_c and r_j)


def simulate_chunked(P, targets, m, n, reps, rng, chunk=5000):
    """simulate() in chunks of `chunk` replicates drawn sequentially from one stream (bounds memory)."""
    if reps <= chunk:
        return simulate(P, targets, m, n, reps, rng)
    parts = []
    left = reps
    while left > 0:
        k = min(chunk, left)
        parts.append(simulate(P, targets, m, n, k, rng))
        left -= k
    out = {}
    for key, v in parts[0].items():
        if isinstance(v, np.ndarray):
            out[key] = np.concatenate([p[key] for p in parts])
        elif key in ("n", "n_cl", "n_tf"):
            out[key] = v
        elif key == "reps":
            out[key] = reps
        else:
            out[key] = float(sum(p[key] * p["reps"] for p in parts) / reps)
    return out


def oc_point(P, scen, n, g, h, reps, block, base=None):
    vr, cr = base if base else (P.vp_ref, P.cabw_ref)
    key = f"{block}|{scen}|n={n}|m={(5, 5)}|g={g:.3f}|h={h:.3f}|{json.dumps({'base': [vr, cr]}, sort_keys=True)}"
    if P.n_fam != 2:                       # F = 1 (X1-amendment-1); F = 2 keys are unchanged
        key += f"|F={P.n_fam}"
    S = simulate_chunked(P, [(vr, cr), (vr - g, cr + h)], (5, 5), n, reps, cfg_rng(key))
    return summarise(S, g, h), key


# ---------------------------------------------------------------- experiment grid
BLOCK_ORDER = ["vp", "cabw", "sens", "items_vs_attempts", "amber_b", "templates", "pilot", "bootstrap",
               "surface", "base_rates", "famxarm", "calib_check", "confirm",
               # F = 1 (one kill-carrying family; X1-amendment-1), added 2026-10-16 evening
               "f1_oc", "f1_surface", "f1_confirm", "f1_templates", "f1_attempts", "f1_base_rates", "f1_calib"]
F1_BLOCKS = ("f1_oc", "f1_surface", "f1_confirm", "f1_templates", "f1_attempts", "f1_base_rates", "f1_calib")
F1_CONFIRM_SCENARIOS = ("high", "stress")   # "high" is the planning floor (§6.3); "stress" is reported only
SIDE_BLOCKS = ("sens", "items_vs_attempts", "amber_b", "templates", "pilot", "base_rates", "famxarm")


def run(out_dir, reps, quick, blocks, merge, scen_filter=None):
    t_all = time.perf_counter()
    rows = []
    old = None
    path_json = os.path.join(out_dir, "x1_power_results.json")

    def replaced(r):
        if r["block"] not in blocks:
            return False
        return (r["block"] not in ("surface", "f1_surface") or scen_filter is None
                or r["scenario"] in scen_filter)

    if merge and os.path.exists(path_json):
        with open(path_json, encoding="utf-8") as fh:
            old = json.load(fh)
        rows = [r for r in old["rows"] if not replaced(r)]
    block_runs = dict(old["meta"].get("block_runs", {})) if old else {}
    boot = old.get("bootstrap_check") if old else None
    calib = old.get("calibration_check") if old else None
    confirm = old.get("confirm") if old else None
    f1_confirm = old.get("f1_confirm") if old else None
    f1_calib = old.get("f1_calibration_check") if old else None

    n_grid = [60, 64, 80, 96, 100, 120]
    reps_side = max(reps // 2, 100)     # sensitivity, ambers, pilot and side blocks use half the replicates
    vp_gaps = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25]
    c_gaps = [0.0, 0.025, 0.05, 0.075, 0.10]
    surf_n = {"low": [64, 72, 80, 96], "mid": [64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160],
              "high": [64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160],
              "stress": [64, 72, 80, 88, 96, 104, 112, 120, 128, 136, 144, 152, 160]}
    if quick:
        n_grid, vp_gaps, c_gaps = [64], [0.05, 0.25], [0.0, 0.10]
        surf_n = {s: [96] for s in SCENARIOS}

    def add(block, scen, P, targets, m, n, true_gap, true_cgap, extra=None, thr_vp=KILL_VP, thr_c=KILL_CABW,
            nrep=None):
        key = f"{block}|{scen}|n={n}|m={m}|g={true_gap:.3f}|h={true_cgap:.3f}|{json.dumps(extra, sort_keys=True)}"
        if nrep is None:
            nrep = reps if block in ("vp", "cabw", "surface", "f1_oc", "f1_surface") else reps_side
        S = simulate(P, targets, m, n, nrep, cfg_rng(key))
        r = dict(block=block, scenario=scen, n=n, m=list(m), true_gap=true_gap, true_cgap=true_cgap,
                 extra=extra or {}, key=key, reps=nrep)
        r.update(summarise(S, true_gap, true_cgap, thr_vp, thr_c))
        rows.append(r)
        return r

    ref = COMMON
    for block in [b for b in BLOCK_ORDER if b in blocks]:
        t0 = time.perf_counter()
        if block == "vp":
            # 1. VP@1 kill OC (CABW gap 0): Rust (arm 0) vs Mithril (arm 1), m = 5 per cell (ROADMAP §10)
            for scen, sd in SCENARIOS.items():
                P = Params(sd)
                for n in n_grid:
                    for g in vp_gaps:
                        add("vp", scen, P, [(ref["vp_ref"], ref["cabw_ref"]), (ref["vp_ref"] - g, ref["cabw_ref"])],
                            (5, 5), n, g, 0.0)
        elif block == "cabw":
            # 2. CABW kill OC at a VP gap of 10 points (the original single nuisance point; block 9 has the rest)
            for scen, sd in SCENARIOS.items():
                P = Params(sd)
                for n in n_grid:
                    for h in c_gaps:
                        add("cabw", scen, P,
                            [(ref["vp_ref"], ref["cabw_ref"]), (ref["vp_ref"] - 0.10, ref["cabw_ref"] + h)],
                            (5, 5), n, 0.10, h)
        elif block == "sens" and not quick:
            # 3. sensitivity at n = 64 (and 120), decisive points only
            sens = {
                "tau_i_low": dict(tau_i_a=0.75, tau_i_c=0.5),
                "tau_i_high": dict(tau_i_a=2.5, tau_i_c=1.67),
                "vp_ref_0.30": dict(vp_ref=0.30),
                "vp_ref_0.75_cabw_0.10": dict(vp_ref=0.75, cabw_ref=0.10),
                "cabw_ref_0.35": dict(cabw_ref=0.35),
                "rho_-0.5": dict(rho=-0.5),
                "family_effects_x2": dict(phi_a=0.5, phi_c=0.3, tau_if_a=1.0, tau_if_c=0.8),
            }
            for name, over in sens.items():
                for scen in ("mid", "high"):
                    P = Params(SCENARIOS[scen], **over)
                    vr, cr = P.vp_ref, P.cabw_ref
                    for n in (64, 120):
                        for g in (0.05, 0.25):
                            add("sens", scen, P, [(vr, cr), (vr - g, cr)], (5, 5), n, g, 0.0, {"sens": name})
                        for h in (0.0, 0.10):
                            add("sens", scen, P, [(vr, cr), (vr - 0.10, cr + h)], (5, 5), n, 0.10, h, {"sens": name})
        elif block == "items_vs_attempts" and not quick:
            # 4. attempts versus items (equal or similar attempt budgets)
            for scen in ("mid", "high"):
                P = Params(SCENARIOS[scen])
                for n, m in ((64, 3), (64, 5), (64, 8), (60, 10), (120, 5), (120, 3), (96, 5)):
                    add("items_vs_attempts", scen, P,
                        [(ref["vp_ref"], ref["cabw_ref"]), (ref["vp_ref"] - 0.10, ref["cabw_ref"])], (m, m), n, 0.10, 0.0)
        elif block == "amber_b" and not quick:
            # 5. amber (b): Mithril (m = 5, reference arm) vs Mithril without traits (m = 3); fires when
            #    VP(Mithril) - VP(no traits) > 5 points. Base VP of Mithril 0.40 [G].
            for scen in ("mid", "high"):
                P = Params(SCENARIOS[scen])
                for n in (64, 96, 120):
                    for g in (0.0, 0.025, 0.05, 0.075, 0.10):
                        add("amber_b", scen, P, [(0.40, 0.20), (0.40 - g, 0.20)], (5, 3), n, g, 0.0, thr_vp=AMBER_B)
        elif block == "templates" and not quick:
            # 6. amber (a) uses block "vp" rows (column p_gap_gt_10): tooling arm and Mithril both m = 5.
            # 6b. templates: items generated as parametric variants of shared templates are correlated.
            #     Coverage uses df = template clusters - 8 (revised 2026-10-16; was items - 8).
            for scen in ("mid", "high"):
                for k, sh in ((2, 0.5), (3, 0.5), (2, 0.8)):
                    P = Params(SCENARIOS[scen], k_tmpl=k, s_tmpl=sh)
                    vr, cr = P.vp_ref, P.cabw_ref
                    for n in (96, 120):
                        ex = {"k_tmpl": k, "s_tmpl": sh}
                        for g in (0.05, 0.25):
                            add("templates", scen, P, [(vr, cr), (vr - g, cr)], (5, 5), n, g, 0.0, ex)
                        for h in (0.0, 0.10):
                            add("templates", scen, P, [(vr, cr), (vr - 0.10, cr + h)], (5, 5), n, 0.10, h, ex)
        elif block == "pilot" and not quick:
            # 7. local pilot: one task family, one local model, 10 items x 3 attempts x 2 arms, base VP 0.25 [G]
            for scen in ("mid", "high"):
                P = Params(SCENARIOS[scen], n_tf=1, n_fam=1, vp_ref=0.25, cabw_ref=0.20)
                for g in (0.0, 0.10, 0.20):
                    add("pilot", scen, P, [(0.25, 0.20), (0.25 - g, 0.20)], (3, 3), 10, g, 0.0)
        elif block == "bootstrap" and not quick:
            # 8. cluster bootstrap check of the analytic stratified SE (one configuration)
            P = Params(SCENARIOS["mid"])
            boot = bootstrap_check(P, n=64, reps=200, B=400, rng=cfg_rng("bootstrap"))
        elif block == "surface":
            # 9. OC surface over true gaps (g, h) at candidate n (multiples of 8): R-VP, R-CABW, R-JOINT
            for scen in (scen_filter or list(SCENARIOS)):
                P = Params(SCENARIOS[scen])
                for n in surf_n[scen]:
                    for g, h in SURFACE_POINTS:
                        add("surface", scen, P,
                            [(ref["vp_ref"], ref["cabw_ref"]), (ref["vp_ref"] - g, ref["cabw_ref"] + h)],
                            (5, 5), n, g, h)
        elif block == "base_rates" and not quick:
            # 10. base-rate sensitivity of the surface (Rust VP@1 0.30; Rust CABW 0.35) at larger n
            for name, over in (("vp_ref_0.30", dict(vp_ref=0.30)), ("cabw_ref_0.35", dict(cabw_ref=0.35))):
                for scen in ("mid", "high"):
                    P = Params(SCENARIOS[scen], **over)
                    vr, cr = P.vp_ref, P.cabw_ref
                    for n in (96, 128, 160):
                        for g, h in SURFACE_POINTS[:-1]:
                            add("base_rates", scen, P, [(vr, cr), (vr - g, cr + h)], (5, 5), n, g, h,
                                {"base": name})
        elif block == "famxarm" and not quick:
            # 11. one-family-only referral (prereg §7.7) with a fixed model-family x arm interaction d
            for d in (0.0, 0.5, 1.0):
                for scen in ("mid", "high"):
                    P = Params(SCENARIOS[scen], famxarm=d)
                    for g, h in ((0.05, 0.0), (0.10, 0.0), (0.10, 0.10)):
                        add("famxarm", scen, P,
                            [(ref["vp_ref"], ref["cabw_ref"]), (ref["vp_ref"] - g, ref["cabw_ref"] + h)],
                            (5, 5), 96, g, h, {"famxarm": d})
        elif block == "calib_check" and not quick:
            # 12. the §6.3 calibration procedure: 24 calibration items (3 per task family), m = 5, both families
            calib = calibration_check(n_cal=24, reps=4000)
        elif block == "confirm":
            # 13. the §6.3 step-4 rule at the planning scenario and base rates, 20,000 replicates per point
            confirm = recompute_n(PLAN_SCENARIO, LADDER[PLAN_SCENARIO], (ref["vp_ref"], ref["cabw_ref"]),
                                  n_list=[96, 104, 112, 120] if not quick else [96],
                                  reps=20000 if not quick else 400, stop_at_first=True, label="confirm")
        # ------------------------------------------------------------ F = 1 (X1-amendment-1)
        elif block == "f1_oc":
            # 14. one kill-carrying family: P(K1), P(K2), P(K1 or K2) at true VP gaps 0..25 points (CABW gap 0)
            f1_n = [60, 96, 128, 160, 192, 224] if not quick else [96]
            for scen, sd in SCENARIOS.items():
                P = Params(sd, n_fam=1)
                for n in f1_n:
                    for g in vp_gaps:
                        add("f1_oc", scen, P, [(ref["vp_ref"], ref["cabw_ref"]), (ref["vp_ref"] - g, ref["cabw_ref"])],
                            (5, 5), n, g, 0.0, {"F": 1})
        elif block == "f1_surface":
            # 15. one family: block 9's surface (R-VP, R-CABW, R-JOINT) over a grid that runs past the cap of 160
            f1_surf_n = {"low": list(range(64, 193, 16)), "mid": list(range(64, 257, 16)),
                         "high": list(range(64, 257, 16)), "stress": list(range(64, 257, 16))}
            if quick:
                f1_surf_n = {s: [96] for s in SCENARIOS}
            for scen in (scen_filter or list(SCENARIOS)):
                P = Params(SCENARIOS[scen], n_fam=1)
                for n in f1_surf_n[scen]:
                    for g, h in SURFACE_POINTS:
                        add("f1_surface", scen, P,
                            [(ref["vp_ref"], ref["cabw_ref"]), (ref["vp_ref"] - g, ref["cabw_ref"] + h)],
                            (5, 5), n, g, h, {"F": 1})
        elif block == "f1_confirm":
            # 16. one family: the §6.3 step-4 rule (20,000 replicates, MC bounds), n = 96, 104, ... upward
            f1_confirm = {}
            for scen in (F1_CONFIRM_SCENARIOS if not quick else ("high",)):
                f1_confirm[scen] = recompute_n(scen, LADDER[scen], (ref["vp_ref"], ref["cabw_ref"]),
                                               n_list=list(range(96, 321, 8)) if not quick else [96],
                                               reps=20000 if not quick else 400, stop_at_first=True,
                                               label="f1_confirm", n_fam=1)
        elif block == "f1_templates" and not quick:
            # 17. one family, items generated as parametric variants of shared templates (2-3 per template)
            for scen in ("mid", "high"):
                for k, sh in ((2, 0.5), (3, 0.5), (2, 0.8)):
                    P = Params(SCENARIOS[scen], n_fam=1, k_tmpl=k, s_tmpl=sh)
                    for n in (96, 128, 160, 192, 224):
                        for g, h in SURFACE_POINTS:
                            add("f1_templates", scen, P,
                                [(ref["vp_ref"], ref["cabw_ref"]), (ref["vp_ref"] - g, ref["cabw_ref"] + h)],
                                (5, 5), n, g, h, {"F": 1, "k_tmpl": k, "s_tmpl": sh})
        elif block == "f1_attempts" and not quick:
            # 18. one family: attempts per primary cell m = 3, 5 (ROADMAP §10) or 10, high scenario
            P = Params(SCENARIOS["high"], n_fam=1)
            for m in (3, 5, 10):
                for n in (96, 128, 160, 192):
                    for g, h in SURFACE_POINTS:
                        add("f1_attempts", "high", P,
                            [(ref["vp_ref"], ref["cabw_ref"]), (ref["vp_ref"] - g, ref["cabw_ref"] + h)],
                            (m, m), n, g, h, {"F": 1, "m": m})
        elif block == "f1_base_rates" and not quick:
            # 19a. one family: base-rate sensitivity (Rust VP@1 0.30; Rust CABW 0.35), high scenario
            for name, over in (("vp_ref_0.30", dict(vp_ref=0.30)), ("cabw_ref_0.35", dict(cabw_ref=0.35))):
                P = Params(SCENARIOS["high"], n_fam=1, **over)
                vr, cr = P.vp_ref, P.cabw_ref
                for n in (128, 160, 192, 224, 256):
                    for g, h in SURFACE_POINTS:
                        add("f1_base_rates", "high", P, [(vr, cr), (vr - g, cr + h)], (5, 5), n, g, h,
                            {"F": 1, "base": name})
        elif block == "f1_calib" and not quick:
            # 19b. one family: the §6.3 calibration procedure (24 calibration items, m = 5: 240 attempts)
            f1_calib = calibration_check(n_cal=24, reps=4000, n_fam=1)
        else:
            continue
        bname = (block if not (block in ("surface", "f1_surface") and scen_filter)
                 else f"{block}[{','.join(scen_filter)}]")
        block_runs[bname] = dict(elapsed_s=round(time.perf_counter() - t0, 1),
                                 run_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                                 reps=(20000 if block in ("confirm", "f1_confirm") else
                                       4000 if block in ("calib_check", "f1_calib") else
                                       200 if block == "bootstrap" else
                                       reps if block in ("vp", "cabw", "surface", "f1_oc", "f1_surface")
                                       else reps_side))

    rows.sort(key=lambda r: BLOCK_ORDER.index(r["block"]) if r["block"] in BLOCK_ORDER else 99)
    recs = recommend(rows, n_grid)
    recs_surface = recommend_surface(rows)
    f1_reqs = dict(
        f1_oc=requirements_vp_only(rows, "f1_oc"),
        f1_surface=requirements_grouped(rows, "f1_surface"),
        f1_templates=requirements_grouped(rows, "f1_templates", ("k_tmpl", "s_tmpl")),
        f1_attempts=requirements_grouped(rows, "f1_attempts", ("m",)),
        f1_base_rates=requirements_grouped(rows, "f1_base_rates", ("base",)),
    )
    elapsed = time.perf_counter() - t_all
    meta = dict(
        script="experiments/x1-harness/power/x1_power_sim.py", master_seed=MASTER_SEED, reps=reps,
        quick=quick, numpy=np.__version__, python=sys.version.split()[0], platform=platform.platform(),
        machine_note=("shared laptop; blocks 1-13 were run while the Owner's benchmark was also running, the "
                      "F = 1 blocks 14-19 after it had ended (19:00 PT, 2026-10-16); blocks may be run "
                      "separately (--blocks/--merge) to keep each invocation short; "
                      "runtimes are indicative only"),
        elapsed_s_last_invocation=round(elapsed, 1), block_runs=block_runs, common_params=COMMON,
        scenarios_tau_ia=SCENARIOS, ladder_tau_ia=LADDER, plan_scenario=PLAN_SCENARIO,
        thresholds=dict(kill_vp=KILL_VP, kill_cabw=KILL_CABW, amber_a=AMBER_A, amber_b=AMBER_B),
        mde_factor=MDE_FACTOR, se_c_req=SE_C_REQ, gh_nodes_per_dim=_gx.size,
    )
    os.makedirs(out_dir, exist_ok=True)
    with open(path_json, "w", encoding="utf-8") as fh:
        json.dump(dict(meta=meta, rows=rows, recommendations=recs, recommendations_surface=recs_surface,
                       bootstrap_check=boot, calibration_check=calib, confirm=confirm,
                       f1_requirements=f1_reqs, f1_confirm=f1_confirm, f1_calibration_check=f1_calib),
                  fh, indent=1)
    with open(os.path.join(out_dir, "x1_power_tables.md"), "w", encoding="utf-8") as fh:
        fh.write(render(meta, rows, recs, recs_surface, boot, calib, confirm))
        fh.write(render_f1(rows, f1_reqs, f1_confirm, f1_calib))
    print(f"done: {len(rows)} rows ({', '.join(blocks)}), {elapsed:.1f} s")


def bootstrap_check(P, n, reps, B, rng):
    """Compare the analytic stratified SE of the VP gap with a stratified item bootstrap.

    The bootstrap resamples items with replacement within each task family (the strata), keeps
    each item's whole set of attempts together (all arms, both model families), and recomputes the
    stratified gap. This is the cluster bootstrap over items that 05 §13 names as the robustness check.
    """
    targets = [(COMMON["vp_ref"], COMMON["cabw_ref"]), (COMMON["vp_ref"] - 0.10, COMMON["cabw_ref"])]
    S = simulate(P, targets, (5, 5), n, reps, rng, return_items=True)
    tf = np.arange(n) % P.n_tf
    n_T = np.bincount(tf, minlength=P.n_tf)
    tf_b = np.concatenate([np.full(n_T[T], T) for T in range(P.n_tf)])
    w_b = 1.0 / (P.n_tf * n_T[tf_b])
    boot_se = np.empty(reps)
    for r in range(reps):
        d = S["d_i"][r]
        idx = np.concatenate([rng.choice(np.flatnonzero(tf == T), size=(B, n_T[T]), replace=True)
                              for T in range(P.n_tf)], axis=1)
        boot_se[r] = (d[idx] * w_b).sum(1).std(ddof=1)
    return dict(n=n, reps=reps, B=B, mean_analytic_se=float(S["se"].mean()),
                mean_bootstrap_se=float(boot_se.mean()), empirical_sd_of_gap=float(S["gap"].std(ddof=1)))


def ladder_reference(base, reps=300, n=480, n_fam=2):
    """Observed within-family SDs of d_i and e_i (m = 5, n_fam families) per ladder level, at base rates.

    These are what the calibration bounds are matched against (prereg §6.3 step 3). Evaluated at a
    VP gap of 10 points and a CABW gap of 0 [G], with many items so that they are population values.
    n_fam = 1 for one kill-carrying family (X1-amendment-1); the calibration run then has one family too.
    """
    vr, cr = base
    out = {}
    for name, sd in LADDER.items():
        P = Params(sd, vp_ref=vr, cabw_ref=cr, n_fam=n_fam)
        key = f"ladder_ref|{name}|base={vr:.4f},{cr:.4f}" + ("" if n_fam == 2 else f"|F={n_fam}")
        S = simulate(P, [(vr, cr), (vr - 0.10, cr)], (5, 5), n, reps, cfg_rng(key))
        out[name] = dict(tau_ia=sd, sd_d=S["sd_d_within_obs"], sd_e=S["sd_e_within_obs"],
                         sigma_ta_within=float(S["sig_ta_within"]))
    return out


def select_scenario(ref, sd_d_up, sd_e_up, floor=PLAN_SCENARIO):
    """Smallest ladder level, not below `floor`, whose reference SDs are at least both upper bounds."""
    names = list(LADDER)
    start = names.index(floor)
    for name in names[start:]:
        if ref[name]["sd_d"] >= sd_d_up and ref[name]["sd_e"] >= sd_e_up:
            return name
    return None     # beyond the ladder: custom parameters fitted to the bounds are needed (prereg §6.3 step 3)


def calibration_check(n_cal, reps, n_fam=2):
    """Block 12 (and 19b with n_fam = 1): do the step-2 upper-80% bounds from n_cal calibration items reach
    the true dispersion?

    For each true scenario, simulate the calibration run (Rust and Mithril, m = 5, both families) and
    compute the pooled within-family SDs s_d, s_e (df = n_cal - 8) and their upper-80% chi-square
    bounds. Report P(bound >= the population value) and P(selected ladder level >= the true level).
    The card-tuning bias that the review identified (iteration items) is NOT modelled; the dedicated
    calibration set exists to avoid it.
    """
    base = (COMMON["vp_ref"], COMMON["cabw_ref"])
    ref = ladder_reference(base, n_fam=n_fam)
    df = n_cal - N_TF
    fac = math.sqrt(df / chi2_ppf(0.20, df))
    names = list(LADDER)
    out = dict(n_cal=n_cal, df=df, chi2_20=chi2_ppf(0.20, df), factor=fac, reps=reps, base=list(base),
               n_fam=n_fam, ladder_reference=ref, scenarios={})
    for scen in ("mid", "high", "stress"):
        P = Params(SCENARIOS[scen], n_fam=n_fam)
        key = f"calib_check|{scen}|n={n_cal}" + ("" if n_fam == 2 else f"|F={n_fam}")
        S = simulate(P, [base, (base[0] - 0.10, base[1])], (5, 5), n_cal, reps, cfg_rng(key), return_items=True)
        d_up = S["sd_d_obs_rep"] * fac
        e_up = S["sd_e_obs_rep"] * fac
        true_idx = names.index(scen)
        sel = [select_scenario(ref, du, eu, floor="low") for du, eu in zip(d_up, e_up)]
        sel_idx = np.array([names.index(s) if s else len(names) for s in sel])
        out["scenarios"][scen] = dict(
            p_d_bound_covers=float((d_up >= ref[scen]["sd_d"]).mean()),
            p_e_bound_covers=float((e_up >= ref[scen]["sd_e"]).mean()),
            p_selected_at_least_true=float((sel_idx >= true_idx).mean()),
            p_selected_at_least_true_with_floor_high=float((np.maximum(sel_idx, names.index("high")) >= true_idx).mean()),
            median_d_up=float(np.median(d_up)), median_e_up=float(np.median(e_up)))
    return out


def recompute_n(scen_name, tau_ia, base, n_list, reps, stop_at_first=True, label="recompute", n_fam=2):
    """Prereg §6.3 step 4: smallest n in n_list meeting R-VP, R-CABW and R-JOINT with Monte Carlo bounds.

    n_fam = 1 for one kill-carrying family (X1-amendment-1); the default 2 reproduces block 13.
    """
    P = Params(tau_ia, vp_ref=base[0], cabw_ref=base[1], n_fam=n_fam)
    res = dict(scenario=scen_name, tau_ia=tau_ia, base=list(base), reps=reps, n_fam=n_fam, points={},
               n_final=None)
    for n in n_list:
        pts = {}
        for g, h in SURFACE_POINTS:
            r, key = oc_point(P, scen_name, n, g, h, reps, label, base)
            pts[f"{g:.2f},{h:.2f}"] = dict(p_kill_vp=r["p_kill_vp"], p_kill_cabw=r["p_kill_cabw"],
                                          p_kill_any=r["p_kill_any"], sd_cgap=r["sd_cgap"], key=key)

        def get(g, h, col):
            return pts[f"{g:.2f},{h:.2f}"][col]

        req_mc = check_requirements(get, reps, mc=True)
        req_pt = check_requirements(get, reps, mc=False)
        res["points"][str(n)] = dict(points=pts, mc_rule=req_mc, point_rule=req_pt)
        if req_mc["all"] and res["n_final"] is None:
            res["n_final"] = n
            if stop_at_first:
                break
    return res


def recommend(rows, n_grid):
    """Smallest n in the grid meeting the ORIGINAL requirements (CABW at VP gap 10 only), per scenario."""
    out = {}
    for scen in SCENARIOS:
        rec = {}
        vp_ok, c_ok = [], []
        for n in n_grid:
            def pk(block, g, h, col):
                for r in rows:
                    if (r["block"] == block and r["scenario"] == scen and r["n"] == n
                            and abs(r["true_gap"] - g) < 1e-9 and abs(r["true_cgap"] - h) < 1e-9):
                        return r[col], r
                return None, None
            p5, _ = pk("vp", 0.05, 0.0, "p_kill_vp")
            any5, _ = pk("vp", 0.05, 0.0, "p_kill_any")
            p25, r25 = pk("vp", 0.25, 0.0, "p_kill_vp")
            c0, _ = pk("cabw", 0.10, 0.0, "p_kill_cabw")
            c10, r10 = pk("cabw", 0.10, 0.10, "p_kill_cabw")
            if p5 is not None and p5 <= 0.10 and p25 >= 0.90:
                vp_ok.append(n)
            if c0 is not None and c0 <= 0.10 and c10 >= 0.90:
                c_ok.append(n)
            rec[f"n{n}"] = dict(p_kill_vp_at_5=p5, p_kill_vp_at_25=p25, p_kill_cabw_at_0=c0,
                                p_kill_any_at_joint_null=any5,
                                p_kill_cabw_at_10=c10,
                                sd_gap=r25["sd_gap"] if r25 else None, sd_cgap=r10["sd_cgap"] if r10 else None)
        rec["min_n_vp"] = min(vp_ok) if vp_ok else None
        rec["min_n_cabw"] = min(c_ok) if c_ok else None
        # extrapolation [D from S]: required SD of the estimate for each rule, scaled by 1/sqrt(n)
        nmax = max(n_grid)
        last = rec.get(f"n{nmax}")
        if last and last["sd_cgap"]:
            rec["n_req_cabw_extrapolated"] = math.ceil(nmax * (last["sd_cgap"] / SE_C_REQ) ** 2)
        if last and last["sd_gap"]:
            req_v = (0.25 - KILL_VP) / Z90  # 7.80 points
            rec["n_req_vp_extrapolated"] = math.ceil(nmax * (last["sd_gap"] / req_v) ** 2)
        out[scen] = rec
    return out


def recommend_surface(rows):
    """Block 9: per scenario and n, the extended requirements (point rule and MC-bound rule)."""
    out = {}
    for scen in SCENARIOS:
        ns = sorted({r["n"] for r in rows if r["block"] == "surface" and r["scenario"] == scen})
        per_n = {}
        min_pt, min_mc = None, None
        for n in ns:
            sel = {(round(r["true_gap"], 3), round(r["true_cgap"], 3)): r for r in rows
                   if r["block"] == "surface" and r["scenario"] == scen and r["n"] == n}
            if len(sel) < len(SURFACE_POINTS):
                continue
            reps = next(iter(sel.values()))["reps"]

            def get(g, h, col):
                return sel[(round(g, 3), round(h, 3))][col]

            pt = check_requirements(get, reps, mc=False)
            mc = check_requirements(get, reps, mc=True)
            per_n[str(n)] = dict(
                point_rule=pt, mc_rule=mc,
                max_p_k2_null=max(get(g, 0.0, "p_kill_cabw") for g in SURFACE_G),
                argmax_g_null=max(SURFACE_G, key=lambda g: get(g, 0.0, "p_kill_cabw")),
                min_p_k2_alt=min(get(g, 0.10, "p_kill_cabw") for g in SURFACE_G),
                argmin_g_alt=min(SURFACE_G, key=lambda g: get(g, 0.10, "p_kill_cabw")),
                p_any_joint_null=get(0.05, 0.0, "p_kill_any"), p_any_g10_h0=get(0.10, 0.0, "p_kill_any"),
                p_k1_5=get(0.05, 0.0, "p_kill_vp"), p_k1_25=get(0.25, 0.0, "p_kill_vp"))
            if pt["all"] and min_pt is None:
                min_pt = n
            if mc["all"] and min_mc is None:
                min_mc = n
        out[scen] = dict(per_n=per_n, min_n_point_rule=min_pt, min_n_mc_rule_at_these_reps=min_mc)
    return out


# ---------------------------------------------------------------- F = 1 summaries (X1-amendment-1)
def requirements_grouped(rows, block, group_keys=()):
    """Per (scenario, extra[group_keys], m, n) of `block`: R-VP, R-CABW and R-JOINT on the point
    estimate and with the Monte Carlo 95% bounds at the block's replicate count, plus the decisive
    probabilities. Groups missing a surface point are skipped. Rows keep their generation order."""
    groups = {}
    for r in rows:
        if r["block"] != block:
            continue
        gk = (r["scenario"],) + tuple(r["extra"].get(k) for k in group_keys) + (tuple(r["m"]), r["n"])
        groups.setdefault(gk, {})[(round(r["true_gap"], 3), round(r["true_cgap"], 3))] = r
    out = []
    for gk, sel in groups.items():
        if any((round(g, 3), round(h, 3)) not in sel for g, h in SURFACE_POINTS):
            continue
        reps = next(iter(sel.values()))["reps"]

        def get(g, h, col, sel=sel):
            return sel[(round(g, 3), round(h, 3))][col]

        d = dict(scenario=gk[0])
        d.update({k: v for k, v in zip(group_keys, gk[1:-2])})
        d.update(m=list(gk[-2]), n=gk[-1], reps=reps,
                 point_rule=check_requirements(get, reps, mc=False),
                 mc_rule=check_requirements(get, reps, mc=True),
                 max_p_k2_null=max(get(g, 0.0, "p_kill_cabw") for g in SURFACE_G),
                 min_p_k2_alt=min(get(g, 0.10, "p_kill_cabw") for g in SURFACE_G),
                 p_any_joint_null=get(0.05, 0.0, "p_kill_any"),
                 p_k1_5=get(0.05, 0.0, "p_kill_vp"), p_k1_25=get(0.25, 0.0, "p_kill_vp"),
                 sd_gap_at_25=get(0.25, 0.0, "sd_gap"), sd_cgap_at_15_10=get(0.15, 0.10, "sd_cgap"))
        out.append(d)
    return out


def min_n_by_group(reqs, group_keys=()):
    """Smallest n per (scenario, group) meeting every requirement: point rule, and MC rule at the block's reps."""
    out = {}
    for d in reqs:
        k = " / ".join([d["scenario"]] + [f"{g}={d[g]}" for g in group_keys])
        e = out.setdefault(k, dict(point=None, mc=None, n_max_simulated=0))
        e["n_max_simulated"] = max(e["n_max_simulated"], d["n"])
        if d["point_rule"]["all"] and (e["point"] is None or d["n"] < e["point"]):
            e["point"] = d["n"]
        if d["mc_rule"]["all"] and (e["mc"] is None or d["n"] < e["mc"]):
            e["mc"] = d["n"]
    return out


def requirements_vp_only(rows, block):
    """ROADMAP §3.2's own requirement (R-VP only): P(K1 | gap 5) <= 0.10 and P(K1 | gap 25) >= 0.90 (CABW gap 0)."""
    sel = {}
    for r in rows:
        if r["block"] == block and abs(r["true_cgap"]) < 1e-9:
            sel.setdefault((r["scenario"], r["n"]), {})[round(r["true_gap"], 3)] = r
    out = []
    for (scen, n), by_g in sel.items():
        if 0.05 not in by_g or 0.25 not in by_g:
            continue
        reps = by_g[0.05]["reps"]
        p5, p25 = by_g[0.05]["p_kill_vp"], by_g[0.25]["p_kill_vp"]
        out.append(dict(scenario=scen, n=n, reps=reps, p_k1_5=p5, p_k1_25=p25,
                        r_vp_point=p5 <= 0.10 and p25 >= 0.90,
                        r_vp_mc=mc_bounds(p5, reps)[1] <= 0.10 and mc_bounds(p25, reps)[0] >= 0.90))
    return out


def render_f1(rows, reqs, f1_confirm, f1_calib):
    """Markdown for blocks 14-19 (F = 1, one kill-carrying model family; X1-amendment-1)."""
    if not any(r["block"] in F1_BLOCKS for r in rows) and not f1_confirm and not f1_calib:
        return ""
    L = ["## 14-19. One kill-carrying model family (F = 1; new 2026-10-16, evening; X1-amendment-1)\n",
         "Every number is **[S]** under the **[G]** inputs above, with one model family instead of two: the item x "
         "model-family and three-way terms are no longer averaged over families, so the effective item x arm "
         "logit SD is 1.118 x the scenario value [D]. Base rates 0.50 / 0.20 unless stated; m = 5 attempts per "
         "primary cell unless stated. Kill rules as above (point estimates). 'pt' = the point estimates meet the "
         "requirement; 'mc' = the Monte Carlo 95% bounds meet it at the block's replicate count.\n"]
    oc = [r for r in rows if r["block"] == "f1_oc"]
    if oc:
        L.append(f"### 14. P(kill) by true VP@1 gap, CABW gap 0 ({oc[0]['reps']:,} replicates per point)\n")
        L.append("| scenario | n | P(K1) at gap 0 / 5 / 10 / 15 / 20 / 25 | P(K1 or K2) at gap 0 / 5 / 10 / 15 / 20 / 25 | "
                 "SD of gap est. at 10 (pts) | SD of CABW gap est. at 10 (pts) | ROADMAP R-VP pt / mc |")
        L.append("|---|---|---|---|---|---|---|")
        vpo = {(d["scenario"], d["n"]): d for d in reqs.get("f1_oc", [])}
        keys = []
        for r in oc:
            if (r["scenario"], r["n"]) not in keys:
                keys.append((r["scenario"], r["n"]))
        for scen, n in keys:
            by_g = {round(r["true_gap"], 3): r for r in oc if r["scenario"] == scen and r["n"] == n}
            gs = sorted(by_g)
            k1 = " / ".join(fmt(by_g[g]["p_kill_vp"]) for g in gs)
            ka = " / ".join(fmt(by_g[g]["p_kill_any"]) for g in gs)
            r10 = by_g.get(0.1)
            sdg = fmt(100 * r10["sd_gap"], 1) if r10 else "-"
            sdc = fmt(100 * r10["sd_cgap"], 1) if r10 and r10.get("sd_cgap") is not None else "-"
            v = vpo.get((scen, n))
            rv = f"{'yes' if v['r_vp_point'] else 'no'} / {'yes' if v['r_vp_mc'] else 'no'}" if v else "-"
            L.append(f"| {scen} | {n} | {k1} | {ka} | {sdg} | {sdc} | {rv} |")
        L.append("")
        L.append("ROADMAP §3.2's own requirement (R-VP: P(K1) <= 0.10 at a true 5-point gap and >= 0.90 at 25), "
                 "smallest n in this grid meeting it on the point estimate / with MC bounds:\n")
        L.append("| scenario | min n (pt) | min n (mc) |")
        L.append("|---|---|---|")
        for scen in SCENARIOS:
            ds = [d for d in reqs.get("f1_oc", []) if d["scenario"] == scen]
            if not ds:
                continue
            pt = min([d["n"] for d in ds if d["r_vp_point"]], default=None)
            mc = min([d["n"] for d in ds if d["r_vp_mc"]], default=None)
            L.append(f"| {scen} | {fmt(pt)} | {fmt(mc)} |")
        L.append("")

    def req_table(title, block, group_keys, note):
        ds = reqs.get(block, [])
        if not ds:
            return
        L.append(f"### {title} ({ds[0]['reps']:,} replicates per point)\n")
        if note:
            L.append(note + "\n")
        hdr = ["scenario"] + list(group_keys) + ["n", "max P(K2 | h=0) over g", "min P(K2 | h=10) over g",
                                                   "P(K1 or K2) at (5,0)", "P(K1) at (5,0) / (25,0)",
                                                   "SD CABW gap at (15,10) (pts)", "pt", "mc"]
        L.append("| " + " | ".join(hdr) + " |")
        L.append("|" + "---|" * len(hdr))
        for d in ds:
            vals = [d["scenario"]] + [str(d[k]) for k in group_keys] + [
                str(d["n"]), fmt(d["max_p_k2_null"]), fmt(d["min_p_k2_alt"]), fmt(d["p_any_joint_null"]),
                f"{fmt(d['p_k1_5'])} / {fmt(d['p_k1_25'])}",
                fmt(100 * d["sd_cgap_at_15_10"], 1) if d["sd_cgap_at_15_10"] is not None else "-",
                "yes" if d["point_rule"]["all"] else "no", "yes" if d["mc_rule"]["all"] else "no"]
            L.append("| " + " | ".join(vals) + " |")
        L.append("")
        mins = min_n_by_group(ds, group_keys)
        L.append("Smallest n meeting R-VP, R-CABW and R-JOINT (blank = none up to the largest n simulated):\n")
        L.append("| group | point rule | MC rule at this block's replicates | largest n simulated |")
        L.append("|---|---|---|---|")
        for k, v in mins.items():
            L.append(f"| {k} | {fmt(v['point'])} | {fmt(v['mc'])} | {v['n_max_simulated']} |")
        L.append("")

    req_table("15. OC surface with one family", "f1_surface", (),
              "R-CABW is checked at every g in {0, 5, 10, 15}; R-JOINT at (5, 0).")
    if f1_confirm:
        for scen, c in f1_confirm.items():
            L.append(f"### 16. Step-4 rule with one family: scenario {scen} ({c['reps']:,} replicates per point)\n")
            L.append(f"Item x arm logit SD {c['tau_ia']}, base rates {c['base'][0]:.2f} / {c['base'][1]:.2f}. "
                     "A requirement is met when the MC 95% upper bound of P(kill | null) <= 0.10 and the MC 95% "
                     "lower bound of P(kill | alt) >= 0.90. Only the last two n tried are tabulated in full. "
                     f"**n_final at these inputs: {fmt(c['n_final'])}.**\n")
            ns = list(c["points"])
            L.append("| n | R-VP | R-CABW | R-JOINT | max P(K2 | h=0) over g | min P(K2 | h=10) over g | "
                     "P(K1 or K2) at (5,0) | P(K1) at (25,0) |")
            L.append("|---|---|---|---|---|---|---|---|")
            for n in ns:
                v = c["points"][n]
                p = v["points"]
                mx0 = max(p[f"{g:.2f},0.00"]["p_kill_cabw"] for g in SURFACE_G)
                mn10 = min(p[f"{g:.2f},0.10"]["p_kill_cabw"] for g in SURFACE_G)
                L.append(f"| {n} | {v['mc_rule']['r_vp']} | {v['mc_rule']['r_cabw']} | {v['mc_rule']['r_joint']} | "
                         f"{fmt(mx0, 4)} | {fmt(mn10, 4)} | {fmt(p['0.05,0.00']['p_kill_any'], 4)} | "
                         f"{fmt(p['0.25,0.00']['p_kill_vp'], 4)} |")
            L.append("")
            for n in ns[-2:]:
                L.append(f"Full points at n = {n}:\n")
                L.append("| point (g, h) | P(K1) | P(K2) | P(K1 or K2) | SD CABW gap (pts) |")
                L.append("|---|---|---|---|---|")
                for k, p in c["points"][n]["points"].items():
                    L.append(f"| ({k}) | {fmt(p['p_kill_vp'], 4)} | {fmt(p['p_kill_cabw'], 4)} | "
                             f"{fmt(p['p_kill_any'], 4)} | "
                             f"{fmt(100 * p['sd_cgap'], 2) if p['sd_cgap'] is not None else '-'} |")
                L.append("")
    req_table("17. One family, templates shared by 2-3 held-out items", "f1_templates",
              ("k_tmpl", "s_tmpl"),
              "k = held-out items per template; s = share of the item-level variance at the template level. "
              "Kill decisions use point estimates, so template clustering changes the OC only through the "
              "estimator's variance.")
    req_table("18. One family, attempts per primary cell (high scenario)", "f1_attempts",
              ("m",), "m = attempts per (item, arm) cell in both primary arms; ROADMAP §10 plans m = 5.")
    req_table("19a. One family, base-rate sensitivity (high scenario)", "f1_base_rates",
              ("base",), "")
    if f1_calib:
        c = f1_calib
        L.append("### 19b. The §6.3 calibration procedure with one family\n")
        L.append(f"{c['n_cal']} calibration items, m = 5, one family ({c['n_cal'] * 5 * 2} attempts [D]); "
                 f"{c['reps']} replicates; bound factor {c['factor']:.3f} (df = {c['df']}).\n")
        L.append("| level | item x arm logit SD | SD of d_i (pts) | SD of e_i (pts) | sigma_ta within |")
        L.append("|---|---|---|---|---|")
        for name, v in c["ladder_reference"].items():
            L.append(f"| {name} | {v['tau_ia']} | {100 * v['sd_d']:.1f} | {100 * v['sd_e']:.1f} | "
                     f"{v['sigma_ta_within']:.3f} |")
        L.append("")
        L.append("| true scenario | P(d bound >= true) | P(e bound >= true) | P(selected level >= true) | same, with the "
                 "floor at high |")
        L.append("|---|---|---|---|---|")
        for scen, v in c["scenarios"].items():
            L.append(f"| {scen} | {v['p_d_bound_covers']:.3f} | {v['p_e_bound_covers']:.3f} | "
                     f"{v['p_selected_at_least_true']:.3f} | {v['p_selected_at_least_true_with_floor_high']:.3f} |")
        L.append("")
    return "\n".join(L) + "\n"


def fmt(x, d=3):
    return "-" if x is None else (f"{x:.{d}f}" if isinstance(x, float) else str(x))


def render(meta, rows, recs, recs_surface, boot, calib, confirm):
    L = []
    L.append("# X1 power simulation: results [S]\n")
    L.append("Generated by `x1_power_sim.py`. Every number below is **[S]**: simulated by this script "
             "under the **[G]** inputs listed in the metadata. None is a measurement of any model.\n")
    L.append(f"- master seed `{meta['master_seed']}`, {meta['reps']} replicates per configuration in blocks 1, 2 "
             f"and 9, {max(meta['reps'] // 2, 100)} in blocks 4-7, 10 and 11, 4,000 in block 12 and 20,000 in "
             f"block 13; numpy {meta['numpy']}, Python {meta['python']}, {meta['platform']} "
             f"({meta['machine_note']}).")
    br = meta.get("block_runs", {})
    if br:
        L.append("- Block runtimes (s): " + ", ".join(f"{b} {v['elapsed_s']}" for b, v in br.items()) +
                 f"; total {round(sum(v['elapsed_s'] for v in br.values()), 1)} s.")
    L.append(f"- Monte Carlo SE of a probability near 0.10 or 0.90: about "
             f"{math.sqrt(0.09 / meta['reps']):.4f} at {meta['reps']} replicates, "
             f"{math.sqrt(0.09 / 20000):.4f} at 20,000.")
    L.append("- Kill rules: K1 when the estimated gap Rust - Mithril > 15 points; K2 when "
             "CABW(Mithril) - CABW(Rust) > 5 points (point estimates, ROADMAP §3.2).")
    L.append("- Item x arm SD on the logit scale by scenario: " +
             ", ".join(f"{k} {v}" for k, v in meta["scenarios_tau_ia"].items()) +
             "; sigma_ta columns give the implied probability-scale SD (05 §13's sigma_ta).")
    L.append("- Revised 2026-10-16 after review (prereg §12): blocks 9-13 are new; block 4b's coverage now "
             "uses df = template clusters - 8; the CABW gap drops a model family with no accepted attempt "
             "in an arm (only the pilot rows can be affected). Every other row reproduces the previous "
             "run's numbers exactly (same keys, same streams).\n")

    def table(block, cols, title, filt=lambda r: True):
        L.append(f"## {title}\n")
        hdr = ["scenario", "n", "m", "true gap", "true CABW gap"] + [c[0] for c in cols]
        L.append("| " + " | ".join(hdr) + " |")
        L.append("|" + "---|" * len(hdr))
        for r in rows:
            if r["block"] != block or not filt(r):
                continue
            tag = r["extra"].get("sens") or r["extra"].get("base")
            vals = [r["scenario"] + (f" ({tag})" if tag else ""),
                    str(r["n"]), "/".join(map(str, r["m"])),
                    f"{100 * r['true_gap']:.1f}", f"{100 * r['true_cgap']:.1f}"]
            vals += [c[1](r) for c in cols]
            L.append("| " + " | ".join(vals) + " |")
        L.append("")

    pct = lambda k: (lambda r: "-" if r.get(k) is None else f"{100 * r[k]:.1f}")
    pr = lambda k: (lambda r: "-" if r.get(k) is None else f"{r[k]:.3f}")
    table("vp", [("P(VP kill)", pr("p_kill_vp")), ("P(CABW kill)", pr("p_kill_cabw")),
                 ("P(any kill)", pr("p_kill_any")), ("P(one-family referral)", pr("p_refer_one_family")),
                 ("P(gap>10) = amber (a) OC", pr("p_gap_gt_10")),
                 ("SD of gap est. (pts)", pct("sd_gap")), ("mean SE (pts)", pct("mean_se")),
                 ("90% CI cover", pr("cover90")), ("naive-SE cover", pr("cover90_naive")),
                 ("mean MDE (pts)", pct("mde_mean")), ("P(MDE>15)", pr("p_underpowered")),
                 ("sigma_ta", pr("sigma_ta")), ("sigma_ta within family", pr("sigma_ta_within"))],
          "1. VP@1 kill operating characteristics (CABW gap 0)")
    table("cabw", [("P(CABW kill)", pr("p_kill_cabw")), ("P(VP kill)", pr("p_kill_vp")),
                   ("P(any kill)", pr("p_kill_any")), ("mean CABW gap est. (pts)", pct("mean_cgap")),
                   ("SD of CABW gap est. (pts)", pct("sd_cgap")), ("mean SE (pts)", pct("mean_se_c")),
                   ("90% CI cover", pr("cover90_c")), ("P(SE_c > 3.90 pts)", pr("p_se_c_gt_390"))],
          "2. CABW kill operating characteristics (VP@1 gap 10 points)")
    L.append("## 3. Smallest item count in the grid meeting each ORIGINAL requirement\n")
    L.append("Superseded as the sizing rule by block 9 (the CABW requirement at every true VP gap in "
             "{0, 5, 10, 15} plus the joint requirement); kept for traceability. VP@1 requirement (ROADMAP §3.2 "
             "[target]): P(kill) <= 0.10 at a true 5-point gap and >= 0.90 at 25. Original CABW requirement: "
             "P(kill) <= 0.10 at a true CABW gap of 0 and >= 0.90 at 10, at a VP gap of 10 only. Extrapolated "
             "counts are [D] from [S]: n_max x (simulated SD / required SD)^2, with required SD 7.80 points "
             "(VP@1) and 3.90 points (CABW).\n")
    L.append("| scenario | min n, VP@1 rule | min n, CABW rule (VP gap 10 only) | n needed, CABW (extrapolated) | n needed, VP@1 (extrapolated) |")
    L.append("|---|---|---|---|---|")
    for scen, rec in recs.items():
        L.append(f"| {scen} | {fmt(rec['min_n_vp'])} | {fmt(rec['min_n_cabw'])} | "
                 f"{fmt(rec.get('n_req_cabw_extrapolated'))} | {fmt(rec.get('n_req_vp_extrapolated'))} |")
    L.append("")
    L.append("Per item count: P(VP kill) at a true gap of 5 / 25; P(CABW kill) at a true CABW gap of 0 / 10 "
             "(VP gap 10); P(any kill) at the joint null (VP gap 5, CABW gap 0).\n")
    L.append("| scenario | n | P(VP kill) 5 / 25 | P(CABW kill) 0 / 10 | P(any kill), joint null |")
    L.append("|---|---|---|---|---|")
    for scen, rec in recs.items():
        for k, v in rec.items():
            if not k.startswith("n") or not isinstance(v, dict):
                continue
            L.append(f"| {scen} | {k[1:]} | {fmt(v.get('p_kill_vp_at_5'))} / {fmt(v.get('p_kill_vp_at_25'))} | "
                     f"{fmt(v.get('p_kill_cabw_at_0'))} / {fmt(v.get('p_kill_cabw_at_10'))} | "
                     f"{fmt(v.get('p_kill_any_at_joint_null'))} |")
    L.append("")
    table("sens", [("P(VP kill)", pr("p_kill_vp")), ("P(CABW kill)", pr("p_kill_cabw")),
                   ("SD gap (pts)", pct("sd_gap")), ("SD CABW gap (pts)", pct("sd_cgap")),
                   ("sigma_ta", pr("sigma_ta"))],
          "4. Sensitivity (decisive points only)")
    L.append("## 4b. Template correlation (items as parametric variants of shared templates)\n")
    L.append("k = items per template; s = share of the item-level variance that sits at the template level. "
             "SEs in this block cluster on templates; coverage uses df = template clusters - 8. Decisive points only.\n")
    L.append("| scenario | k | s | n | true gap | true CABW gap | P(VP kill) | P(CABW kill) | SD gap (pts) | SD CABW gap (pts) | 90% CI cover (VP, template-clustered) | 90% CI cover (CABW) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        if r["block"] != "templates":
            continue
        L.append(f"| {r['scenario']} | {r['extra']['k_tmpl']} | {r['extra']['s_tmpl']} | {r['n']} | "
                 f"{100 * r['true_gap']:.1f} | {100 * r['true_cgap']:.1f} | {r['p_kill_vp']:.3f} | "
                 f"{r['p_kill_cabw']:.3f} | {100 * r['sd_gap']:.1f} | {100 * r['sd_cgap']:.1f} | {r['cover90']:.3f} | "
                 f"{fmt(r.get('cover90_c'))} |")
    L.append("")
    table("items_vs_attempts", [("SD gap (pts)", pct("sd_gap")), ("SD CABW gap (pts)", pct("sd_cgap")),
                                ("P(VP kill)", pr("p_kill_vp")), ("P(CABW kill)", pr("p_kill_cabw"))],
          "5. Items versus attempts (true VP gap 10, CABW gap 0)")
    table("amber_b", [("P(amber b fires: gap > 5)", pr("p_kill_vp")), ("SD gap (pts)", pct("sd_gap"))],
          "6. Amber (b) traits ablation: Mithril (m=5) minus Mithril without traits (m=3)")
    table("pilot", [("SD gap (pts)", pct("sd_gap")), ("P(gap est. > 15)", pr("p_kill_vp")),
                    ("mean SE (pts)", pct("mean_se")), ("P(CABW undefined)", pr("p_cabw_undefined"))],
          "7. Local pilot (1 task family, 1 local model, 10 items x 3 attempts x 2 arms)")
    if boot:
        L.append("## 8. Bootstrap check of the analytic stratified SE (mid scenario, n=64, gap 10)\n")
        L.append(f"Mean analytic SE {100 * boot['mean_analytic_se']:.2f} points; mean stratified item-bootstrap SE "
                 f"{100 * boot['mean_bootstrap_se']:.2f} points (B={boot['B']}, {boot['reps']} replicates); "
                 f"empirical SD of the gap estimate {100 * boot['empirical_sd_of_gap']:.2f} points.\n")

    # 9. surface
    if any(r["block"] == "surface" for r in rows):
        L.append("## 9. Operating-characteristic surface (base rates 0.50 / 0.20; new 2026-10-16)\n")
        L.append("Requirements (prereg §6.2): R-VP P(K1 | 5, 0) <= 0.10 and P(K1 | 25, 0) >= 0.90; R-CABW "
                 "P(K2 | g, 0) <= 0.10 and P(K2 | g, 10) >= 0.90 for every g in {0, 5, 10, 15}; R-JOINT "
                 "P(K1 or K2 | 5, 0) <= 0.10. Points are (true VP gap g, true CABW gap h) in points. "
                 "'pt' = point estimate meets every requirement; 'mc' = the Monte Carlo 95% bounds meet them "
                 "at this block's replicate count (the record's step-4 rule uses 20,000 replicates, block 13).\n")
        L.append("| scenario | n | P(K2 | h=0) at g = 0 / 5 / 10 / 15 | P(K2 | h=10) at g = 0 / 5 / 10 / 15 | "
                 "P(K1 or K2) at (5,0) / (10,0) / (15,0) | P(K1) at (5,0) / (25,0) | SD CABW gap at (15,10) (pts) | pt | mc |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for scen in SCENARIOS:
            ns = sorted({r["n"] for r in rows if r["block"] == "surface" and r["scenario"] == scen})
            for n in ns:
                sel = {(round(r["true_gap"], 3), round(r["true_cgap"], 3)): r for r in rows
                       if r["block"] == "surface" and r["scenario"] == scen and r["n"] == n}
                g0 = " / ".join(fmt(sel[(g, 0.0)]["p_kill_cabw"]) for g in SURFACE_G)
                g10 = " / ".join(fmt(sel[(g, 0.1)]["p_kill_cabw"]) for g in SURFACE_G)
                anyv = " / ".join(fmt(sel[(g, 0.0)]["p_kill_any"]) for g in (0.05, 0.10, 0.15))
                k1 = f"{fmt(sel[(0.05, 0.0)]['p_kill_vp'])} / {fmt(sel[(0.25, 0.0)]['p_kill_vp'])}"
                sdc = fmt(100 * sel[(0.15, 0.1)]["sd_cgap"], 1)
                rs = recs_surface.get(scen, {}).get("per_n", {}).get(str(n), {})
                ptok = "yes" if rs.get("point_rule", {}).get("all") else "no"
                mcok = "yes" if rs.get("mc_rule", {}).get("all") else "no"
                L.append(f"| {scen} | {n} | {g0} | {g10} | {anyv} | {k1} | {sdc} | {ptok} | {mcok} |")
        L.append("")
        L.append("Smallest n (multiples of 8 in the grid) meeting every requirement:\n")
        L.append("| scenario | point rule | MC-bound rule at 2,000 replicates |")
        L.append("|---|---|---|")
        for scen, v in recs_surface.items():
            L.append(f"| {scen} | {fmt(v['min_n_point_rule'])} | {fmt(v['min_n_mc_rule_at_these_reps'])} |")
        L.append("")
    if any(r["block"] == "base_rates" for r in rows):
        L.append("## 10. Base-rate sensitivity of the surface (new 2026-10-16)\n")
        L.append("| base rates | scenario | n | P(K2 | h=0) at g = 0 / 5 / 10 / 15 | P(K2 | h=10) at g = 0 / 5 / 10 / 15 | P(K1 or K2) at (5,0) |")
        L.append("|---|---|---|---|---|---|")
        keys = sorted({(r["extra"]["base"], r["scenario"], r["n"]) for r in rows if r["block"] == "base_rates"},
                      key=lambda k: (k[0], ["low", "mid", "high", "stress"].index(k[1]), k[2]))
        for b, scen, n in keys:
            sel = {(round(r["true_gap"], 3), round(r["true_cgap"], 3)): r for r in rows
                   if r["block"] == "base_rates" and r["extra"]["base"] == b and r["scenario"] == scen and r["n"] == n}
            g0 = " / ".join(fmt(sel[(g, 0.0)]["p_kill_cabw"]) for g in SURFACE_G)
            g10 = " / ".join(fmt(sel[(g, 0.1)]["p_kill_cabw"]) for g in SURFACE_G)
            L.append(f"| {b} | {scen} | {n} | {g0} | {g10} | {fmt(sel[(0.05, 0.0)]['p_kill_any'])} |")
        L.append("")
    if any(r["block"] == "famxarm" for r in rows):
        L.append("## 11. One-family-only referral with a model-family x arm interaction (n = 96; new 2026-10-16)\n")
        L.append("d = fixed interaction on the comparison arm's acceptance logit, +d in family A and -d in "
                 "family B; pooled true gaps are held at (g, h). Referral = no pooled kill, but K1 or K2 holds on "
                 "one family's own estimate (prereg §7.7).\n")
        L.append("| d | scenario | true gap | true CABW gap | P(any pooled kill) | P(one-family referral) | SD per-family gap (pts) | SD per-family CABW gap (pts) | SD pooled gap (pts) |")
        L.append("|---|---|---|---|---|---|---|---|---|")
        for r in rows:
            if r["block"] != "famxarm":
                continue
            L.append(f"| {r['extra']['famxarm']} | {r['scenario']} | {100 * r['true_gap']:.1f} | "
                     f"{100 * r['true_cgap']:.1f} | {fmt(r['p_kill_any'])} | {fmt(r['p_refer_one_family'])} | "
                     f"{fmt(100 * r['sd_gap_family'], 1)} | {fmt(100 * r['sd_cgap_family'], 1)} | "
                     f"{fmt(100 * r['sd_gap'], 1)} |")
        L.append("")
    if calib:
        L.append("## 12. The §6.3 calibration procedure (new 2026-10-16)\n")
        L.append(f"{calib['n_cal']} calibration items (3 per task family), m = 5, both families, base rates "
                 f"{calib['base'][0]:.2f} / {calib['base'][1]:.2f}, true VP gap 10, CABW gap 0; {calib['reps']} "
                 f"replicates. Upper-80% bound factor sqrt(df / chi2_df(0.20)) = {calib['factor']:.3f} with df = "
                 f"{calib['df']} (chi2 quantile {calib['chi2_20']:.3f}). The card-tuning bias of iteration items "
                 "is not modelled; the dedicated calibration set exists to avoid it.\n")
        L.append("Reference (population) observed within-family SDs per ladder level, m = 5, both families:\n")
        L.append("| level | item x arm logit SD | SD of d_i (pts) | SD of e_i (pts) | sigma_ta within |")
        L.append("|---|---|---|---|---|")
        for name, v in calib["ladder_reference"].items():
            L.append(f"| {name} | {v['tau_ia']} | {100 * v['sd_d']:.1f} | {100 * v['sd_e']:.1f} | {v['sigma_ta_within']:.3f} |")
        L.append("")
        L.append("| true scenario | P(d bound >= true) | P(e bound >= true) | P(selected level >= true) | same, with the floor at high | median d bound (pts) | median e bound (pts) |")
        L.append("|---|---|---|---|---|---|---|")
        for scen, v in calib["scenarios"].items():
            L.append(f"| {scen} | {v['p_d_bound_covers']:.3f} | {v['p_e_bound_covers']:.3f} | "
                     f"{v['p_selected_at_least_true']:.3f} | {v['p_selected_at_least_true_with_floor_high']:.3f} | "
                     f"{100 * v['median_d_up']:.1f} | {100 * v['median_e_up']:.1f} |")
        L.append("")
    if confirm:
        L.append("## 13. Step-4 rule at the planning scenario, 20,000 replicates per point (new 2026-10-16)\n")
        L.append(f"Scenario {confirm['scenario']} (item x arm logit SD {confirm['tau_ia']}), base rates "
                 f"{confirm['base'][0]:.2f} / {confirm['base'][1]:.2f}, {confirm['reps']} replicates per point "
                 f"(MC SE about {math.sqrt(0.09 / confirm['reps']):.4f} near 0.10 or 0.90). A requirement is met when "
                 "the MC 95% upper bound of P(kill | null) <= 0.10 and the MC 95% lower bound of P(kill | alt) >= 0.90. "
                 f"**n_final at these inputs: {fmt(confirm['n_final'])}.**\n")
        L.append("| n | point (g, h) | P(K1) | P(K2) | P(K1 or K2) | SD CABW gap (pts) |")
        L.append("|---|---|---|---|---|---|")
        for n, v in confirm["points"].items():
            for k, p in v["points"].items():
                L.append(f"| {n} | ({k}) | {fmt(p['p_kill_vp'], 4)} | {fmt(p['p_kill_cabw'], 4)} | "
                         f"{fmt(p['p_kill_any'], 4)} | {fmt(100 * p['sd_cgap'], 2) if p['sd_cgap'] is not None else '-'} |")
            L.append(f"| {n} | requirements (MC rule) | R-VP {v['mc_rule']['r_vp']} | R-CABW {v['mc_rule']['r_cabw']} | "
                     f"R-JOINT {v['mc_rule']['r_joint']} | all {v['mc_rule']['all']} |")
        L.append("")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results")
    ap.add_argument("--reps", type=int, default=2000)
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--blocks", default=",".join(BLOCK_ORDER),
                    help="comma-separated blocks to (re)compute: " + ",".join(BLOCK_ORDER))
    ap.add_argument("--merge", action="store_true", help="keep rows of other blocks from the existing results")
    ap.add_argument("--scenarios", default=None, help="surface block only: comma-separated scenarios to (re)compute")
    ap.add_argument("--recompute", action="store_true", help="prereg §6.3 steps 3-4 from calibration outputs")
    ap.add_argument("--vp-ref", type=float)
    ap.add_argument("--cabw-ref", type=float)
    ap.add_argument("--sd-d-up", type=float, help="upper-80%% bound of the within-family SD of d_i (fraction)")
    ap.add_argument("--sd-e-up", type=float, help="upper-80%% bound of the within-family SD of e_i (fraction)")
    ap.add_argument("--recompute-reps", type=int, default=20000)
    ap.add_argument("--recompute-out", default=None, help="write the recomputation JSON here (UTF-8) instead of stdout")
    ap.add_argument("--families", type=int, default=2, choices=(1, 2),
                    help="--recompute only: kill-carrying model families (1 under X1-amendment-1)")
    ap.add_argument("--cap", type=int, default=160,
                    help="--recompute only: largest n tried (multiple of 8; the record's budget cap, 160 by default)")
    a = ap.parse_args()
    if a.recompute:
        out = {}
        for label, base in (("calibration", (a.vp_ref, a.cabw_ref)), ("base_case", (COMMON["vp_ref"], COMMON["cabw_ref"]))):
            ref = ladder_reference(base, n_fam=a.families)
            scen = select_scenario(ref, a.sd_d_up, a.sd_e_up)
            if scen is None:
                out[label] = dict(base=list(base), scenario=None, note="bounds beyond the ladder: fit custom parameters")
                continue
            out[label] = recompute_n(scen, LADDER[scen], base, n_list=list(range(96, a.cap + 1, 8)),
                                     reps=a.recompute_reps, stop_at_first=True, label=f"recompute_{label}",
                                     n_fam=a.families)
        finals = [v.get("n_final") for v in out.values()]
        out["n_final"] = None if any(f is None for f in finals) else max(finals)
        out["inputs"] = dict(vp_ref=a.vp_ref, cabw_ref=a.cabw_ref, sd_d_up=a.sd_d_up, sd_e_up=a.sd_e_up,
                             reps=a.recompute_reps, floor=PLAN_SCENARIO, n_list=f"96..{a.cap} step 8",
                             families=a.families)
        if a.recompute_out:
            with open(a.recompute_out, "w", encoding="utf-8") as fh:
                json.dump(out, fh, indent=1)
        else:
            print(json.dumps(out, indent=1))
        return
    blocks = [b.strip() for b in a.blocks.split(",") if b.strip()]
    scen_filter = [x.strip() for x in a.scenarios.split(",")] if a.scenarios else None
    run(a.out, 200 if a.quick else a.reps, a.quick, blocks, a.merge, scen_filter)


if __name__ == "__main__":
    main()
