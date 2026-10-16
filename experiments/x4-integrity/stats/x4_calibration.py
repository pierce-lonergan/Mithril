#!/usr/bin/env python3
"""X4 calibration statistics (design-phase reference implementation).

Revision 2 (2026-10-16), after two same-family, independent-context reviews. Standard library only
(Python >= 3.10), deterministic for a given --seed. Five jobs:

1. Exact binomial operating characteristics (OC) of the A/A rule of ROADMAP §3.5 ("the superiority
   e-process reaches 20 in <= 2 of 100 sessions") and of the "<= 5 of 100" alternative, plus a
   beta-binomial and a night-clustered sensitivity for correlated sessions. Results are [D].
2. The Monte Carlo study [S] of the e-processes AS FIRST DRAFTED (tables 2a-2f). Kept unchanged so the
   numbers the reviewers quote stay reproducible. Table 2d (kill) uses the drafted, superseded kill
   scoring; section 3 has the revised kill.
3. Revision studies [S]: outlier-rate grid; A/A with the symmetric clip; the revised kill e-process;
   the mandatory tail check (06 §6.2); the sentinel rules; Hamed-Rao Mann-Kendall; planted-level clip
   bias; drift with fixed versus randomised order.
4. Quiet-machine hours [D from G inputs], with a ROADMAP §10-style reconstruction for comparison.
5. A golden wealth path (float64, hex) for the Rust differential test (MEASUREMENT-SERVICE.md §8.6).

Block noise, outlier rates, stall models and drift are assumptions [G]; nothing here is measured.
The constants the gate uses are in PREREG (printed, and dumped with --json).

Usage
  python -I x4_calibration.py                 # everything (about 40 CPU-seconds on the laptop)
  python -I x4_calibration.py --binomial-only
  python -I x4_calibration.py --golden        # just the golden wealth path (instant)
  python -I x4_calibration.py --sessions-null 20000 --sessions-ttp 10000 --json out.json

The e-process code here is the *reference* implementation that the measurement service's Rust
implementation is differentially tested against, bit for bit (MEASUREMENT-SERVICE.md §8.6).
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
import random
import statistics
import sys
import time
from decimal import Decimal, getcontext
from fractions import Fraction
from math import comb, log, lgamma, exp, sqrt, ceil

# --------------------------------------------------------------------------------------
# 0. Pinned constants. Transcendentals are specified, not taken from the platform libm:
#    each is the float64 nearest to the real value, via 60-digit decimal arithmetic [D].
#    (math.log(1.03) on this laptop is 8 ulps away from RN(ln 1.03): it computes ln of fl(1.03).)
# --------------------------------------------------------------------------------------
getcontext().prec = 60
M_NI = float((Decimal(103) / Decimal(100)).ln())          # 0x1.e44a9a3bed663p-6
M_KILL = float(-(Decimal(97) / Decimal(100)).ln())        # 0x1.f30b2d0091d82p-6
ONS_GAIN = float(Decimal(2) / (Decimal(2) - Decimal(3).ln()))
THRESHOLD = 20.0
THETA = 0.5          # bet cap, superiority and non-inferiority [target]
THETA_KILL = 0.8     # bet cap, kill e-process [target] (section 3c)
Z995 = statistics.NormalDist().inv_cdf(0.995)

PREREG = {
    "m_ni": {"value": M_NI, "hex": M_NI.hex(), "def": "RN(ln(103/100)); the stricter reading of ROADMAP 'ratio < 0.97'"},
    "m_kill": {"value": M_KILL, "hex": M_KILL.hex(), "def": "RN(-ln(97/100)); ROADMAP §1 rule 4 kill margin, literal"},
    "ons_gain": {"value": ONS_GAIN, "hex": ONS_GAIN.hex(), "def": "RN(2/(2-ln 3)); ONS alternative only, not gated"},
    "threshold": THRESHOLD,
    "cross_rule": "first block i with K_i >= 20.0, K_i the float64 product prod(1 + lam_j*g_j) in block order; no log space",
    "theta": THETA, "theta_kill": THETA_KILL,
    "gate_scorer": "R (run-level, arm-relative outliers scored +c); provisional pending owner question 4 (06 §6.2)",
    "aa_secondary_scorer": "S (symmetric clip, no loss scoring); the A/A gate must pass under R and under S",
    "kill_scorer": "Rk (run-level outliers scored -c_kill, i.e. in the candidate's favour)",
    "clip_rule": "c = max(3*sigma_hat_d, 2*m_ni)",
    "clip_kill_rule": "c_kill = max(3*sigma_hat_d, m_kill + 3*sigma_hat_d)",
    "c_run_rule": "c_run = 4*sigma_hat_run (sigma_hat_run: pooled within-session SD of per-run log-times, pilot)",
    "run_reference": "an arm's running median of its own earlier runs in the session; before it has any, the "
                     "incumbent's running median; before that, the pilot incumbent median",
    "bettor": "aGRAPA: mu = s1/n; var = max(s2/n - mu*mu, 1e-12); lam = min(theta, max(0.0, mu/(var + mu*mu)))",
    "bettor_state": "n = 1, s1 = g0, s2 = v0 + g0*g0 (one prior pseudo-observation); after each block: "
                    "K = K*(1 + lam*g) with lam from the state before g, then n += 1, s1 += g, s2 += g*g",
    "priors": {"sup": "x0 = -0.02, sd0 = c/3", "ni": "x0 = 0.0, sd0 = c/3", "kill": "x0 = m_kill + 0.02, sd0 = c_kill/3",
               "map": "g0 = sign*(x0 - m)/scale, v0 = (sd0/scale)^2; upper tests: sign -1, scale c - m; "
                      "kill: sign +1, scale c_kill + m_kill"},
    "float_rules": "IEEE-754 binary64, round to nearest even, operations in the order written, no FMA contraction",
    "tail_check": "deny NI/superiority credit iff P(Bin(n_B, p0) >= k_B) <= 0.05, k_B = slow-outlier runs of B and "
                  "n_B = B runs, pooled over the candidate's screening session(s) and the confirmatory session on "
                  "that niche, evaluated once n_B >= N (the session continues past the crossing until then); "
                  "p0 = one-sided 95% Clopper-Pearson upper bound of the pilot A/A slow-outlier rate per run; "
                  "a run stopped at the time cap counts as a slow outlier",
    "sentinel_rule": "void iff |mean d_sent| > z_0.995*sigma_hat/sqrt(k) (label asymmetry) or the chi-square "
                     "variance test on the clipped calibration+sentinel d rejects two-sided at 0.01",
    "trend_rule": "two-sided Hamed-Rao (1998) Mann-Kendall at alpha 0.01 on each arm's per-run log-times",
}


# --------------------------------------------------------------------------------------
# 1. Exact binomial operating characteristics, plus correlated-session sensitivity
# --------------------------------------------------------------------------------------

def binom_cdf_exact(k: int, n: int, p: Fraction) -> Fraction:
    """P(X <= k) for X ~ Binomial(n, p), exactly."""
    q = 1 - p
    return sum(Fraction(comb(n, i)) * p**i * q**(n - i) for i in range(k + 1))


ROADMAP_INFERENCE = {  # ROADMAP §3.5, labelled [inference] there
    ("<=2/100", "0.01"): 0.92,
    ("<=2/100", "0.05"): 0.12,
    ("<=2/100", "0.08"): 0.01,
    ("<=5/100", "0.08"): 0.18,
}


def betabinom_pmf(n: int, alpha: float, beta: float) -> list:
    lb = lgamma(alpha) + lgamma(beta) - lgamma(alpha + beta)
    out = []
    for k in range(n + 1):
        lc = lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1)
        out.append(exp(lc + lgamma(k + alpha) + lgamma(n - k + beta) - lgamma(n + alpha + beta) - lb))
    return out


def convolve(a: list, b: list) -> list:
    out = [0.0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                out[i + j] += x * y
    return out


def correlated_pass(p: float, rho: float, clusters: int, per: int, k: int = 2) -> float:
    """P(X <= k) when 'clusters' nights of 'per' sessions each have a night-level rate ~ Beta with
    mean p and intra-night correlation rho [D, numerical]."""
    a = p * (1 - rho) / rho
    b = (1 - p) * (1 - rho) / rho
    one = betabinom_pmf(per, a, b)
    tot = [1.0]
    for _ in range(clusters):
        tot = convolve(tot, one)
    return sum(tot[: k + 1])


def binomial_report() -> dict:
    rows = []
    for rule_k, label in ((2, "<=2/100"), (5, "<=5/100")):
        for p_str in ("0.005", "0.01", "0.02", "0.03", "0.05", "0.08", "0.10"):
            p = Fraction(p_str)
            pr = binom_cdf_exact(rule_k, 100, p)
            rows.append({"rule": label, "true_rate": p_str, "p_pass_exact": str(pr),
                         "p_pass": float(pr),
                         "roadmap_inference": ROADMAP_INFERENCE.get((label, p_str))})
    checks = []
    for (label, p_str), claimed in ROADMAP_INFERENCE.items():
        k = 2 if label == "<=2/100" else 5
        val = float(binom_cdf_exact(k, 100, Fraction(p_str)))
        checks.append({"rule": label, "true_rate": p_str, "roadmap": claimed,
                       "exact": val, "agrees_to_2dp": round(val, 2) == claimed})

    def p_at(target, k):
        lo, hi = 0.0, 0.5
        for _ in range(60):
            mid = (lo + hi) / 2
            v = float(binom_cdf_exact(k, 100, Fraction(mid).limit_denominator(10**9)))
            lo, hi = (mid, hi) if v > target else (lo, mid)
        return (lo + hi) / 2
    quantiles = {label: {str(t): p_at(t, k) for t in (0.9, 0.5, 0.1)}
                 for k, label in ((2, "<=2/100"), (5, "<=5/100"))}
    e2e = [{"rule": "<=0/20", "true_rate": p, "p_pass": float(binom_cdf_exact(0, 20, Fraction(p)))}
           for p in ("0.01", "0.05", "0.10")]
    corr = []
    for p in (0.01, 0.05, 0.08):
        corr.append({"true_rate": p, "rho": 0.05,
                     "iid": float(binom_cdf_exact(2, 100, Fraction(str(p)))),
                     "betabinomial_100": correlated_pass(p, 0.05, 1, 100),
                     "nights_4x25": correlated_pass(p, 0.05, 4, 25),
                     "nights_10x10": correlated_pass(p, 0.05, 10, 10)})
    return {"rows": rows, "roadmap_checks": checks, "rate_at_pass_prob": quantiles, "e2e_context": e2e,
            "correlated": corr}


# --------------------------------------------------------------------------------------
# 2. Block statistic, clipping and the betting e-processes
# --------------------------------------------------------------------------------------

def score_block(d: float, c: float) -> float:
    """06 §6.2 literal: symmetric clip; an outlier block (|d| > c) is scored +c."""
    return d if -c <= d <= c else c


class Bettor:
    """Predictable bet fraction lam in [0, theta] on a variable g >= -1 with E[g | past] <= 0 under H0.
    K_n = prod(1 + lam_i * g_i) is then a nonnegative supermartingale under H0 (theta <= 1), so by
    Ville's inequality P(sup_n K_n >= 1/alpha) <= alpha."""

    def __init__(self, kind: str, theta: float, prior_g: float, prior_var: float):
        self.kind, self.theta = kind, theta
        self.K = 1.0
        self.n, self.s1, self.s2 = 1.0, prior_g, prior_var + prior_g * prior_g
        self.lam = min(theta, max(0.0, theta / 2))
        self.A = 1.0
        self.grid = [theta * f for f in (0.1, 0.2, 0.4, 0.6, 0.8, 1.0)]
        self.Kj = [1.0] * len(self.grid)

    def bet(self) -> float:
        if self.kind == "agrapa":
            mu = self.s1 / self.n
            var = max(self.s2 / self.n - mu * mu, 1e-12)
            return min(self.theta, max(0.0, mu / (var + mu * mu)))
        if self.kind == "ons":
            return self.lam
        raise ValueError(self.kind)

    def update(self, g: float) -> float:
        if self.kind == "mixture":
            self.Kj = [k * (1.0 + l * g) for k, l in zip(self.Kj, self.grid)]
            self.K = sum(self.Kj) / len(self.Kj)
            return self.K
        lam = self.bet()
        self.K *= 1.0 + lam * g
        if self.kind == "agrapa":
            self.n += 1.0; self.s1 += g; self.s2 += g * g
        else:  # ONS (online Newton step on log-wealth)
            z = g / (1.0 + lam * g)
            self.A += z * z
            self.lam = min(self.theta, max(0.0, lam + ONS_GAIN * z / self.A))
        return self.K


class EProcess:
    """H0 'E[x] >= m' (side 'upper': superiority m = 0, non-inferiority m = m_NI) or
    H0 'E[x] <= m' (side 'lower': the kill test)."""

    def __init__(self, m: float, c: float, side: str, kind: str, theta: float = THETA,
                 prior_x: float = 0.0, prior_sd: float | None = None):
        if side == "upper":
            if not c > m:
                raise ValueError("clip c must exceed the margin m")
            self.scale, self.sign = c - m, -1.0      # g = (m - x)/(c - m) >= -1
        else:
            self.scale, self.sign = c + m, 1.0       # g = (x - m)/(c + m) >= -1
        self.m, self.c = m, c
        sd = prior_sd if prior_sd is not None else c / 3.0
        self.b = Bettor(kind, theta, self._g(prior_x), (sd / self.scale) ** 2)

    def _g(self, x: float) -> float:
        return self.sign * (x - self.m) / self.scale

    @property
    def K(self) -> float:
        return self.b.K

    def update(self, x: float) -> float:
        return self.b.update(self._g(x))


KINDS = ("agrapa", "ons", "mixture")


def blocks_planned(sigma: float, delta: float = 0.03) -> int:
    """ROADMAP §10 / 06 §6.6: n = max(6, 12 sigma^2 / delta^2) blocks."""
    return max(6, math.ceil(12.0 * sigma * sigma / (delta * delta) - 1e-9))


ORDERS = ("ABBA", "BAAB")


class SessionModel:
    """Run-level generator for one session [G]. Each run's log-time is arm_effect + Gaussian noise
    (optionally AR(1) across runs). With probability p_run a run (either arm) is hit by a 10-15%
    environmental slowdown (06 §6 cites 10-15% outliers on this desktop). Optional, for section 3:
    B-only stalls (probability stall_p, magnitude stall_mag), a linear drift 'ramp' per run, and a
    fixed block order. With independent runs the block statistic d has SD sigma (= sigma_d)."""

    def __init__(self, rng, mu, sigma, p_run=0.0, phi=0.0, stall_p=0.0, stall_mag=0.0, ramp=0.0, order=None):
        self.rng, self.mu, self.sigma, self.p_run, self.phi = rng, mu, sigma, p_run, phi
        self.stall_p, self.stall_l, self.ramp, self.order = stall_p, log(1.0 + stall_mag), ramp, order
        self.prev = 0.0
        self.t = 0

    def run(self, arm):
        e = self.rng.gauss(0.0, self.sigma)
        if self.phi:
            e = self.phi * self.prev + math.sqrt(1.0 - self.phi * self.phi) * e
        self.prev = e
        ell = (self.mu if arm == "B" else 0.0) + e
        if self.ramp:
            ell += self.ramp * self.t
        self.t += 1
        if self.p_run and self.rng.random() < self.p_run:
            ell += log(self.rng.uniform(1.10, 1.15))
        if self.stall_p and arm == "B" and self.rng.random() < self.stall_p:
            ell += self.stall_l
        return ell

    def block(self):
        order = self.order or ORDERS[self.rng.random() < 0.5]
        runs = [(a, self.run(a)) for a in order]
        b = [l for a, l in runs if a == "B"]; aa = [l for a, l in runs if a == "A"]
        d = 0.5 * (sum(b) - sum(aa))
        return d, runs


def median(xs):
    n = len(xs)
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


class Scorer:
    """Turns blocks into the bounded statistic x.
    '06': 06 §6.2 literal: x = d if |d| <= c, else +c.
    'R' : run-level, arm-relative outliers (the gate scorer): a run is an outlier if it deviates from
          its own arm's running median (earlier runs of this session only, so the rule is predictable)
          by more than c_run; a block with an outlier run is scored +c; otherwise x = clip(d, -c, c).
          Before an arm has history its reference is the incumbent's; before that, the pilot incumbent
          median (0 here).
    'S' : symmetric clip, no loss scoring: x = clip(d, -c, c). A/A secondary gate.
    'Rk': as R, but a block with an outlier run is scored -c (the kill test; favours the candidate).
    Slow-direction outlier runs are counted per arm for the tail check."""

    def __init__(self, kind, c, c_run):
        self.kind, self.c, self.c_run = kind, c, c_run
        self.sorted = {"A": [], "B": []}
        self.slow = {"A": 0, "B": 0}
        self.nruns = {"A": 0, "B": 0}

    def score(self, d, runs):
        c = self.c
        if self.kind == "06":
            return d if -c <= d <= c else c
        out = False
        for a, l in runs:
            h = self.sorted[a] or self.sorted["A"]
            ref = median(h) if h else 0.0
            dev = l - ref
            if abs(dev) > self.c_run:
                out = True
                if dev > 0:
                    self.slow[a] += 1
        for a, l in runs:
            bisect.insort(self.sorted[a], l)
            self.nruns[a] += 1
        self.last_out = out
        if self.kind == "S":
            return max(-c, min(c, d))
        if out:
            return -c if self.kind == "Rk" else c
        return max(-c, min(c, d))


def clip_for(sigma: float, k_sigma: float = 3.0, k_m: float = 2.0) -> float:
    """Pre-registered block clip: c = max(k_sigma * sigma_hat, k_m * m_NI)."""
    return max(k_sigma * sigma, k_m * M_NI)


def clip_kill_for(sigma: float) -> float:
    """Revised kill clip: c_kill = max(3 sigma_hat, m_kill + 3 sigma_hat) (headroom on the slow side)."""
    return max(3.0 * sigma, M_KILL + 3.0 * sigma)


def make_proc(test, kind, c, theta=THETA):
    if test == "sup":
        return EProcess(0.0, c, "upper", kind, theta=theta, prior_x=-0.02)
    if test == "ni":
        return EProcess(M_NI, c, "upper", kind, theta=theta, prior_x=0.0)
    if test == "kill":
        return EProcess(M_KILL, c, "lower", kind, theta=theta, prior_x=M_KILL + 0.02)
    raise ValueError(test)


def simulate(mu, sigma, horizon, n_sessions, rng, test, scoring="R", p_run=0.0, phi=0.0,
             threshold=THRESHOLD, kinds=KINDS):
    """Section 2 (as drafted). Per strategy: first block index reaching `threshold`, or horizon + 1."""
    c = clip_for(sigma); c_run = 4.0 * sigma
    times = {k: [] for k in kinds}
    xsum = 0.0; xn = 0
    for _ in range(n_sessions):
        model = SessionModel(rng, mu, sigma, p_run, phi)
        sc = Scorer(scoring, c, c_run)
        procs = {k: make_proc(test, k, c) for k in kinds}
        alive = set(kinds)
        for i in range(1, horizon + 1):
            d, runs = model.block()
            x = sc.score(d, runs)
            xsum += x; xn += 1
            for k in list(alive):
                if procs[k].update(x) >= threshold:
                    times[k].append(i); alive.discard(k)
            if not alive:
                break
        for k in alive:
            times[k].append(horizon + 1)
    out = {"mean_x_observed": xsum / max(xn, 1)}
    for k in kinds:
        t = sorted(times[k])
        out[k] = {"rate": sum(1 for v in t if v <= horizon) / len(t),
                  "median": t[len(t) // 2], "p90": t[int(0.9 * len(t))],
                  "mean_min_t_h": sum(min(v, horizon) for v in t) / len(t)}
    return out


# --------------------------------------------------------------------------------------
# 3. Revision studies (aGRAPA, the pre-registered bettor, only)
# --------------------------------------------------------------------------------------

def q_censored(times, horizon, q):
    """Quantile under administrative censoring at `horizon` (Kaplan-Meier reduces to the empirical CDF
    here): the smallest t with F(t) >= q, or None when that lies beyond the horizon ('> H')."""
    ts = sorted(times)
    k = max(1, math.ceil(q * len(ts)))
    v = ts[k - 1]
    return v if v <= horizon else None


def log1m(p):
    return math.log1p(-p)


def binom_cdf_f(k: int, n: int, p: float) -> float:
    """P(X <= k), X ~ Bin(n, p), float, by the pmf recurrence in log space."""
    if k < 0:
        return 0.0
    if k >= n or p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 0.0
    lt = n * log1m(p); step = log(p) - log1m(p)
    s = exp(lt)
    for i in range(k):
        lt += log((n - i) / (i + 1.0)) + step
        s += exp(lt)
    return min(1.0, s)


def binom_sf(k: int, n: int, p: float) -> float:
    """P(X >= k), X ~ Bin(n, p), float."""
    if k <= 0:
        return 1.0
    return max(0.0, 1.0 - binom_cdf_f(k - 1, n, p))


_CP = {}


def cp_upper(k: int, n: int, conf: float = 0.95) -> float:
    """One-sided Clopper-Pearson upper bound: p with P(X <= k | p) = 1 - conf."""
    key = (k, n, conf)
    if key in _CP:
        return _CP[key]
    if k >= n:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if binom_cdf_f(k, n, mid) > 1.0 - conf else (lo, mid)
    _CP[key] = 0.5 * (lo + hi)
    return _CP[key]


def tail_reject(k_b: int, n_b: int, p0: float, level: float = 0.01) -> bool:
    return binom_sf(k_b, n_b, p0) <= level


class PilotTail:
    """Draws, per session, the pilot-based p0 of the tail check: simulate the per-run slow-outlier flag
    rate of an A/A pilot (R scorer) once, then per session draw the pilot count ~ Bin(n_runs, rate)
    and return its one-sided 95% Clopper-Pearson upper bound. Pilot: 20 sessions x 24 blocks [target]."""

    def __init__(self, rng, sigma, p_run, n_sess=200, blocks=24):
        c = clip_for(sigma)
        flags = runs = 0
        for _ in range(n_sess):
            m = SessionModel(rng, 0.0, sigma, p_run)
            sc = Scorer("R", c, 4.0 * sigma)
            for _ in range(blocks):
                d, r = m.block(); sc.score(d, r)
            flags += sc.slow["A"] + sc.slow["B"]; runs += sc.nruns["A"] + sc.nruns["B"]
        self.rate = flags / runs
        self.n_pilot = 20 * blocks * 4
        self.rng = rng

    def draw(self):
        # inverse-transform Bin(n_pilot, rate) via a geometric-skip sampler (exact for Bernoulli trials)
        k = 0; i = 0; p = self.rate
        if p <= 0.0:
            return cp_upper(0, self.n_pilot)
        lq = log1m(p)
        while True:
            u = self.rng.random()
            i += 1 + int(log(1.0 - u) / lq)
            if i > self.n_pilot:
                break
            k += 1
        return cp_upper(k, self.n_pilot)


TAIL_RULES_DEFAULT = (("at_crossing", 0, 0),)


def run_sessions(rng, n_sessions, *, mu, sigma, horizon, tests, p_run=0.0, phi=0.0, stall=(0.0, 0.0),
                 ramp=0.0, order=None, tail=None, tail_rules=TAIL_RULES_DEFAULT, theta_kill=THETA_KILL,
                 c_kill=None, report_within=None):
    """tests: tuples (label, test, scorer_kind[, clip, theta]). Returns, per label, the crossing rate
    within `horizon` (and within report_within if given), the censored median/p90 and mean x. With a
    `tail` sampler, upper tests also report, per tail rule (name, screening_blocks_pooled, min_B_runs),
    the share of sessions whose crossing is credited after the tail check. A rule with min_B_runs keeps
    the session running after the crossing until the pooled B-run count reaches it (or the horizon)."""
    c = clip_for(sigma); c_run = 4.0 * sigma
    ck = c_kill if c_kill is not None else clip_kill_for(sigma)
    res = {t[0]: {"times": [], "xsum": 0.0, "xn": 0, "denied": {r[0]: 0 for r in tail_rules}} for t in tests}
    max_screen = max((r[1] for r in tail_rules), default=0) if tail else 0
    for _ in range(n_sessions):
        p0 = tail.draw() if tail else None
        scr = {"k": 0, "n": 0}
        if max_screen:
            sm = SessionModel(rng, mu, sigma, p_run, phi, stall[0], stall[1])
            ss = Scorer("R", c, c_run)
            for _ in range(max_screen):
                d, r = sm.block(); ss.score(d, r)
            scr = {"k": ss.slow["B"], "n": ss.nruns["B"]}
        model = SessionModel(rng, mu, sigma, p_run, phi, stall[0], stall[1], ramp, order)
        live = []
        for t in tests:
            label, test, sk = t[0], t[1], t[2]
            cc = t[3] if len(t) > 3 and t[3] is not None else (ck if test == "kill" else c)
            th = t[4] if len(t) > 4 else (theta_kill if test == "kill" else THETA)
            live.append([label, Scorer(sk, cc, c_run), make_proc(test, "agrapa", cc, th), test])
        done = set(); pending = {}   # (label, rule) -> True while a crossed test waits for its tail sample

        def evaluate(label, sc, rule, final=False):
            name, screen, min_runs = rule[:3]
            level = rule[3] if len(rule) > 3 else 0.01
            k = sc.slow["B"] + (scr["k"] if screen else 0)
            n = sc.nruns["B"] + (scr["n"] if screen else 0)
            if n < min_runs and not final:
                return False
            if tail_reject(k, n, p0, level):
                res[label]["denied"][name] += 1
            return True

        for i in range(1, horizon + 1):
            d, runs = model.block()
            for label, sc, pr, test in live:
                x = sc.score(d, runs)
                r = res[label]; r["xsum"] += x; r["xn"] += 1
                if label in done:
                    for rule in tail_rules:
                        if (label, rule[0]) in pending and evaluate(label, sc, rule):
                            del pending[(label, rule[0])]
                    continue
                if pr.update(x) >= THRESHOLD:
                    r["times"].append(i); done.add(label)
                    if tail and test != "kill":
                        for rule in tail_rules:
                            if not evaluate(label, sc, rule):
                                pending[(label, rule[0])] = True
            if len(done) == len(live) and not pending:
                break
        for (label, rname) in list(pending):
            sc = next(s for l, s, *_ in live if l == label)
            evaluate(label, sc, next(r for r in tail_rules if r[0] == rname), final=True)
        for label, *_ in live:
            if label not in done:
                res[label]["times"].append(horizon + 1)
    out = {}
    for label, r in res.items():
        ts = r["times"]
        crossed = sum(1 for v in ts if v <= horizon)
        o = {"rate": crossed / len(ts), "median": q_censored(ts, horizon, 0.5), "p90": q_censored(ts, horizon, 0.9),
             "mean_x": r["xsum"] / max(r["xn"], 1)}
        if report_within:
            o["rate_within_%d" % report_within] = sum(1 for v in ts if v <= report_within) / len(ts)
        if tail:
            o["credited"] = {name: (crossed - dn) / len(ts) for name, dn in r["denied"].items()}
        out[label] = o
    return out


# --- stationarity statistics ---------------------------------------------------------

def mk_z(x):
    """Two-sided Mann-Kendall z, three ways: (uncorrected; Hamed & Rao 1998 with every lag whose rank
    autocorrelation is significant at 5%; the PRE-REGISTERED form: the Hamed-Rao factor restricted to
    lag 1, always applied, floored at 1). All detrend by Sen's slope before ranking."""
    n = len(x)
    s = 0
    for i in range(n - 1):
        xi = x[i]
        for j in range(i + 1, n):
            v = x[j] - xi
            s += (v > 0) - (v < 0)
    var0 = n * (n - 1) * (2 * n + 5) / 18.0
    var_hr = var_l1 = var0
    if n > 3:
        slopes = sorted((x[j] - x[i]) / (j - i) for i in range(n - 1) for j in range(i + 1, n))
        b = median(slopes)
        det = [x[i] - b * i for i in range(n)]
        order = sorted(range(n), key=det.__getitem__)
        rk = [0.0] * n
        for r, i in enumerate(order):
            rk[i] = r + 1.0
        mr = sum(rk) / n
        dev = [v - mr for v in rk]
        den = sum(v * v for v in dev)
        lim = 1.959963984540054 / sqrt(n)
        acc = 0.0; rho1 = 0.0
        norm = n * (n - 1) * (n - 2)
        for k in range(1, n - 2):
            rho = sum(dev[i] * dev[i + k] for i in range(n - k)) / den
            if k == 1:
                rho1 = rho
            if abs(rho) > lim:
                acc += (n - k) * (n - k - 1) * (n - k - 2) * rho
        var_hr = max(var0 * (1.0 + 2.0 * acc / norm), 1e-12)
        var_l1 = var0 * max(1.0, 1.0 + 2.0 * (n - 1) * (n - 2) * (n - 3) * rho1 / norm)
    if s == 0:
        return 0.0, 0.0, 0.0
    sc = s - (1 if s > 0 else -1)
    return sc / sqrt(var0), sc / sqrt(var_hr), sc / sqrt(var_l1)


def chi2_cdf(x, df):
    """Regularised lower incomplete gamma P(df/2, x/2), by its series (adequate for df <= 200)."""
    if x <= 0:
        return 0.0
    a, z = df / 2.0, x / 2.0
    term = 1.0 / a; s = term; k = 0
    while True:
        k += 1
        term *= z / (a + k)
        s += term
        if term < s * 1e-15 or k > 10000:
            break
    return min(1.0, exp(-z + a * log(z) - lgamma(a)) * s)


def chi2_q(p, df):
    lo, hi = 0.0, 10.0 * df + 100.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if chi2_cdf(mid, df) < p else (lo, mid)
    return 0.5 * (lo + hi)


def sentinel_study(rng, sigma, n_sessions, p_run, asym, n_cal=2, share=1.0 / 6.0):
    """Per planted-regression session: k = ceil(share*N) sentinel blocks + n_cal calibration blocks, all
    A/A. B-labelled runs are 'asym' faster if the harness treats labels asymmetrically. sigma_hat from a
    pilot of 480 A/A blocks. Returns the void rates of the mean test, the variance test, either, and the
    largest wealth the drafted sentinel e-process (superiority, theta 0.5) could reach [D]."""
    N = 2 * blocks_planned(sigma); k = math.ceil(share * N); c = clip_for(sigma)
    m = n_cal + k
    qtab = {df: (chi2_q(0.005, df) / df, chi2_q(0.995, df) / df) for df in range(1, m + 1)}
    v_mean = v_var = v_any = 0
    for _ in range(n_sessions):
        s_hat = sigma * sqrt(rng.gammavariate(479 / 2.0, 2.0) / 479.0)
        model = SessionModel(rng, -asym, sigma, p_run)
        sc = Scorer("R", c, 4.0 * sigma)
        keep = []      # (is_sentinel, d) for blocks without a run-outlier flag (outliers are loss-scored)
        for j in range(m):
            d, runs = model.block()
            sc.score(d, runs)
            if not sc.last_out:
                keep.append((j >= n_cal, max(-c, min(c, d))))
        sent = [v for s, v in keep if s]
        mt = bool(sent) and abs(sum(sent) / len(sent)) > Z995 * s_hat / sqrt(len(sent))
        vt = False
        if len(keep) >= 2:
            df = len(keep)
            ss = sum(v * v for _, v in keep) / df
            lo_q, hi_q = qtab[df]
            vt = not (lo_q <= ss / (s_hat * s_hat) <= hi_q)
        v_mean += mt; v_var += vt; v_any += (mt or vt)
    return {"N": N, "k_sentinels": k, "df_variance_max": m,
            "max_wealth_drafted_rule": (1.0 + THETA) ** k,
            "void_mean": v_mean / n_sessions, "void_var": v_var / n_sessions, "void_any": v_any / n_sessions}


def mk_study(rng, sigma, n_sessions, *, p_run=0.0, phi=0.0, ramp_total=0.0, order=None, blocks=None):
    """A/A sessions of N blocks: share voided by the two-sided MK test (alpha 0.01) on either arm's
    per-run log-times, Hamed-Rao corrected and uncorrected; and the superiority false-alarm rate (R)."""
    N = blocks or 2 * blocks_planned(sigma)
    ramp = ramp_total / (4.0 * N) if ramp_total else 0.0
    c = clip_for(sigma)
    hr = un = l1 = fa = 0; dsum = 0.0
    for _ in range(n_sessions):
        model = SessionModel(rng, 0.0, sigma, p_run, phi, ramp=ramp, order=order)
        sc = Scorer("R", c, 4.0 * sigma); pr = make_proc("sup", "agrapa", c)
        arms = {"A": [], "B": []}; crossed = False
        for _ in range(N):
            d, runs = model.block()
            dsum += d
            for a, l in runs:
                arms[a].append(l)
            if not crossed and pr.update(sc.score(d, runs)) >= THRESHOLD:
                crossed = True
        fa += crossed
        za, zb = mk_z(arms["A"]), mk_z(arms["B"])
        un += max(abs(za[0]), abs(zb[0])) > Z995
        hr += max(abs(za[1]), abs(zb[1])) > Z995
        l1 += max(abs(za[2]), abs(zb[2])) > Z995
    return {"N": N, "void_uncorrected": un / n_sessions, "void_hamed_rao_all_lags": hr / n_sessions,
            "void_lag1_floored": l1 / n_sessions, "sup_false_alarm": fa / n_sessions,
            "mean_d": dsum / (n_sessions * N)}


def clip_bias_level(sigma: float, m: float) -> float:
    """Smallest true mean log-ratio mu with E[clip(d, -c, c)] = m for d ~ N(mu, sigma^2) [D, closed form
    plus bisection]. Symmetric-clip part only; the R scorer's +c outlier scoring only raises E[x]."""
    c = clip_for(sigma)
    nd = statistics.NormalDist()

    def eclip(mu):
        a = (c - mu) / sigma; b = (-c - mu) / sigma
        up = sigma * nd.pdf(a) - (c - mu) * (1.0 - nd.cdf(a))           # E[(d - c)+]
        dn = sigma * nd.pdf(b) + (-c - mu) * nd.cdf(b)                  # E[(-c - d)+]
        return mu - up + dn
    lo, hi = m, m + 0.05
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if eclip(mid) < m else (lo, mid)
    return 0.5 * (lo + hi)


# --------------------------------------------------------------------------------------
# 4. Quiet-hour arithmetic [D from G inputs]
# --------------------------------------------------------------------------------------

T_MICRO, T_E2E, C_E2E, SETUP_S = 10.0, 120.0, 1.5, 120.0   # [G] (06 §6.6 illustrative; ROADMAP §10 c)
X3_PLAN_H = {0.02: 3.6, 0.04: 13.2}  # X3 prereg §6 plan figure at a true ratio of 1.0 [inference there]
X3_EXPECTED_H = {0.02: 9.0, 0.04: 24.0}  # X3 prereg §6 "≈ 9-24 quiet hours" incl. pilot and sentinels


def quiet_hours(sigma: float, e2e_mean_blocks: float | None = None, aa_horizon_mult: int = 1) -> dict:
    n = blocks_planned(sigma); N = 2 * n
    mb, eb = 4 * T_MICRO, 4 * T_E2E * C_E2E
    sent = math.ceil(N / 6.0); n_cal = 2
    pilot = 20 * (24 * mb + SETUP_S) + 3 * (12 * eb + SETUP_S)         # sigma-independent [target]
    aa = 100 * (aa_horizon_mult * N * mb + SETUP_S)                      # pure A/A: no cal/sentinels
    planted = 200 * ((N + n_cal + sent) * mb + SETUP_S)
    e2e_blocks = N if e2e_mean_blocks is None else e2e_mean_blocks
    e2e = 20 * (e2e_blocks * eb + SETUP_S)
    aa_prime = 20 * (N * mb + SETUP_S)                                   # A vs A' (link-order variant)
    posctl = 10 * (N * mb + SETUP_S)                                     # stationarity positive control
    spin = 2 * 256 * mb                                                  # separate long run, 2 levels
    x3 = X3_PLAN_H[sigma] * 3600.0
    roadmap_comparable = aa + planted + e2e + x3
    tot = pilot + aa + planted + e2e + aa_prime + posctl + spin + x3
    h = lambda s: round(s / 3600.0, 1)
    # ROADMAP §10-style reconstruction (COST.md §1.4 'central'): A/A at n, planted at N, e2e at n, X3 plan
    rs = 100 * n * mb + 200 * N * mb + 20 * n * eb + x3
    return {"sigma_d": sigma, "n": n, "N_blocks": N, "pilot_h": h(pilot), "micro_AA_h": h(aa),
            "micro_planted_h": h(planted), "e2e_AA_h": h(e2e), "AA_prime_h": h(aa_prime),
            "posctl_h": h(posctl), "spin_confirm_h": h(spin), "X3_placeholder_h": h(x3),
            "roadmap_comparable_h": h(roadmap_comparable), "total_h": h(tot),
            "nights_of_8h": round(tot / 3600.0 / 8.0, 1), "roadmap_style_reconstruction_h": h(rs)}


# --------------------------------------------------------------------------------------
# 5. Golden wealth path (for the Rust differential test)
# --------------------------------------------------------------------------------------

def golden_path(seed: int = 20261016, sigma: float = 0.02, blocks: int = 24) -> dict:
    """A fixed block sequence and the three pre-registered wealth paths, every float in hex. The Rust
    e-process must reproduce every K_i bit for bit (PREREG['float_rules'])."""
    rng = random.Random(seed)
    c, ck = clip_for(sigma), clip_kill_for(sigma)
    model = SessionModel(rng, 0.0, sigma, 0.02)
    sR, sK = Scorer("R", c, 4.0 * sigma), Scorer("Rk", ck, 4.0 * sigma)
    procs = {"sup": make_proc("sup", "agrapa", c), "ni": make_proc("ni", "agrapa", c),
             "kill": make_proc("kill", "agrapa", ck, THETA_KILL)}
    rows = []
    for i in range(1, blocks + 1):
        d, runs = model.block()
        x, xk = sR.score(d, runs), sK.score(d, runs)
        k = {t: (procs[t].update(xk if t == "kill" else x)).hex() for t in ("sup", "ni", "kill")}
        rows.append({"i": i, "runs": [(a, l.hex()) for a, l in runs], "d": d.hex(), "x": x.hex(), "x_kill": xk.hex(),
                     "K": k})
    return {"seed": seed, "sigma_hat": sigma, "c": c.hex(), "c_kill": ck.hex(), "c_run": (4.0 * sigma).hex(),
            "rows": rows}


# --------------------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", type=int, default=20261016)
    ap.add_argument("--sessions-null", type=int, default=2000)
    ap.add_argument("--sessions-ttp", type=int, default=1000)
    ap.add_argument("--sessions-rev", type=int, default=1000, help="sessions per cell in section 3")
    ap.add_argument("--binomial-only", action="store_true")
    ap.add_argument("--golden", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    t0 = time.process_time()
    src = open(__file__, "rb").read()
    out = {"script_sha256": hashlib.sha256(src).hexdigest(), "seed": a.seed,
           "python": sys.version.split()[0], "prereg": PREREG}
    if a.golden:
        g = golden_path(a.seed); out["golden"] = g
        print(json.dumps(g, indent=1))
        if a.json:
            with open(a.json, "w", encoding="utf-8") as f:
                json.dump(out, f, indent=1, default=str)
        return 0

    print("## 0. Pinned constants\n")
    print(f"m_NI = {M_NI!r} ({M_NI.hex()}); m_kill = {M_KILL!r} ({M_KILL.hex()}); "
          f"math.log(1.03) on this platform = {math.log(1.03).hex()} (not used)\n")

    b = binomial_report(); out["binomial"] = b
    print("## 1. Exact binomial OC of the A/A rule [D]\n")
    print("| rule | true false-alarm rate | P(pass) exact | ROADMAP [inference] |")
    print("|---|---|---|---|")
    for r in b["rows"]:
        print(f"| {r['rule']} | {r['true_rate']} | {r['p_pass']:.4f} | {r['roadmap_inference'] or ''} |")
    print("\nROADMAP figure check:", "; ".join(
        f"{c['rule']}@{c['true_rate']}: exact {c['exact']:.4f} vs {c['roadmap']} -> "
        f"{'agrees' if c['agrees_to_2dp'] else 'DIFFERS'}" for c in b["roadmap_checks"]))
    print("True rate at which each rule passes with prob 0.9 / 0.5 / 0.1:",
          {k: {t: round(v, 4) for t, v in d.items()} for k, d in b["rate_at_pass_prob"].items()})
    print("\n### 1b. Correlated sessions: P(<= 2 of 100) when sessions share nights (rho = 0.05) [D]\n")
    print("| true mean rate | iid binomial | beta-binomial (one cluster of 100) | 4 nights x 25 | 10 nights x 10 |")
    print("|---|---|---|---|---|")
    for r in b["correlated"]:
        print(f"| {r['true_rate']} | {r['iid']:.4f} | {r['betabinomial_100']:.4f} | {r['nights_4x25']:.4f} | "
              f"{r['nights_10x10']:.4f} |")
    if a.binomial_only:
        print(f"\nCPU {time.process_time() - t0:.1f} s")
        return 0

    rng = random.Random(a.seed)
    sims = {}
    fmt = lambda v, h: (str(v) if v <= h else f">{h}")
    print("\n## 2. Betting e-processes AS DRAFTED, simulated [S]; sigma_d, outliers and AR(1) are assumptions [G]\n")
    print(f"m_NI = {M_NI:.6f}; m_kill = {M_KILL:.6f}; block clip c = max(3 sigma, 2 m_NI); "
          f"run-outlier threshold c_run = 4 sigma; bet cap theta = 0.5; outlier runs: 10-15% slow\n")
    print("### 2a. Planted-regression calibration: P(NI e-process reaches 20 within N blocks)\n")
    print("| sigma_d | P(outlier run) | scoring | true time log-ratio | mean x | N | aGRAPA | ONS | mixture |")
    print("|---|---|---|---|---|---|---|---|---|")
    levels = [("time x1.03", log(1.03)), ("thr 0.97", -log(0.97)), ("time x1.04", log(1.04)), ("thr 0.96", -log(0.96))]
    for sigma in (0.02, 0.04):
        N = 2 * blocks_planned(sigma)
        for p_run in (0.0, 0.005):
            for scoring in ("R", "06"):
                for name, mu in levels:
                    r = simulate(mu, sigma, N, a.sessions_null, rng, "ni", scoring, p_run)
                    sims[f"ni_null|{sigma}|{p_run}|{scoring}|{name}"] = r
                    print(f"| {sigma:.0%} | {p_run} | {scoring} | {name} ({mu:.5f}) | {r['mean_x_observed']:.5f} | {N} | "
                          f"{r['agrapa']['rate']:.4f} | {r['ons']['rate']:.4f} | {r['mixture']['rate']:.4f} |")
    print("\n### 2b. A/A calibration: P(superiority e-process reaches 20 within N blocks)\n")
    print("| sigma_d | P(outlier run) | AR(1) phi | label asymmetry | scoring | N | aGRAPA | ONS | mixture |")
    print("|---|---|---|---|---|---|---|---|---|")
    for sigma in (0.02, 0.04):
        N = 2 * blocks_planned(sigma)
        for p_run, phi, asym in ((0.0, 0.0, 0.0), (0.005, 0.0, 0.0), (0.0, 0.6, 0.0),
                                 (0.0, 0.0, 0.005), (0.0, 0.0, 0.01), (0.0, 0.0, 0.02)):
            for scoring in ("R", "06"):
                r = simulate(-asym, sigma, N, a.sessions_null, rng, "sup", scoring, p_run, phi)
                sims[f"aa_sup|{sigma}|{p_run}|{phi}|{asym}|{scoring}"] = r
                print(f"| {sigma:.0%} | {p_run} | {phi} | {asym:.1%} | {scoring} | {N} | {r['agrapa']['rate']:.4f} | "
                      f"{r['ons']['rate']:.4f} | {r['mixture']['rate']:.4f} |")
    print("\n### 2c. Time-to-pass at true parity (NI e-process reaches 20)\n")
    print("| sigma_d | P(outlier run) | scoring | N | strategy | median | p90 | share within N | E[min(T, N)] |")
    print("|---|---|---|---|---|---|---|---|---|")
    ttp_res = {}
    for sigma in (0.02, 0.04):
        N = 2 * blocks_planned(sigma)
        for p_run in (0.0, 0.005):
            for scoring in ("R", "06"):
                r = simulate(0.0, sigma, 400, a.sessions_ttp, rng, "ni", scoring, p_run)
                rN = simulate(0.0, sigma, N, a.sessions_ttp, rng, "ni", scoring, p_run)
                sims[f"ttp_ni|{sigma}|{p_run}|{scoring}"] = r
                sims[f"ttpN_ni|{sigma}|{p_run}|{scoring}"] = rN
                ttp_res[(sigma, p_run, scoring, "N")] = rN
                for k in KINDS:
                    print(f"| {sigma:.0%} | {p_run} | {scoring} | {N} | {k} | {fmt(r[k]['median'], 400)} | "
                          f"{fmt(r[k]['p90'], 400)} | {rN[k]['rate']:.3f} | {rN[k]['mean_min_t_h']:.1f} |")
    print("\n### 2d. Kill e-process AS DRAFTED (outliers scored +c, clip c, theta 0.5; superseded by 3c)\n")
    print("| sigma_d | P(outlier run) | true time log-ratio | N | aGRAPA | ONS | mixture |")
    print("|---|---|---|---|---|---|---|")
    for sigma in (0.02, 0.04):
        N = 2 * blocks_planned(sigma)
        for p_run in (0.0, 0.005):
            for name, mu in (("parity", 0.0), ("time x1.06", log(1.06)), ("time x1.10", log(1.10))):
                r = simulate(mu, sigma, N, a.sessions_null // 2, rng, "kill", "R", p_run)
                sims[f"kill|{sigma}|{p_run}|{name}"] = r
                print(f"| {sigma:.0%} | {p_run} | {name} | {N} | {r['agrapa']['rate']:.4f} | "
                      f"{r['ons']['rate']:.4f} | {r['mixture']['rate']:.4f} |")
    print("\n### 2e. Superiority: blocks to e >= 20 at a true improvement (no outliers), horizon 400\n")
    print("| sigma_d | true improvement | scoring | strategy | median | p90 | share by 400 |")
    print("|---|---|---|---|---|---|---|")
    n_e = max(200, a.sessions_ttp // 4)
    for sigma in (0.01, 0.02, 0.04):
        for imp in (0.02, 0.05, 0.20):
            for scoring in ("R", "06"):
                r = simulate(-log(1.0 + imp), sigma, 400, n_e, rng, "sup", scoring)
                sims[f"sup_power|{sigma}|{imp}|{scoring}"] = r
                for k in KINDS:
                    print(f"| {sigma:.0%} | {imp:.0%} | {scoring} | {k} | {fmt(r[k]['median'], 400)} | "
                          f"{fmt(r[k]['p90'], 400)} | {r[k]['rate']:.3f} |")
    print("\n### 2f. Sensitivity of the drafted constants (aGRAPA, scoring R, no outliers)\n")
    print("| sigma_d | theta | clip c | NI@parity median/p90 | kill@x1.06 median | kill@x1.10 median | "
          "NI reaches 20 within N at time x1.03 |")
    print("|---|---|---|---|---|---|---|")
    n_f = max(200, a.sessions_ttp // 4)
    for sigma in (0.02, 0.04):
        N = 2 * blocks_planned(sigma)
        for theta in (0.5, 0.8):
            for kc in ((2, 3) if sigma == 0.02 else (2,)):
                c = max(3 * sigma, kc * M_NI)
                res = {}
                for key, mu, test, hor, n in (("ni", 0.0, "ni", 400, n_f), ("k6", log(1.06), "kill", 400, n_f),
                                              ("k10", log(1.10), "kill", 400, n_f),
                                              ("null", log(1.03), "ni", N, a.sessions_null // 2)):
                    ts = []
                    for _ in range(n):
                        model = SessionModel(rng, mu, sigma)
                        sc = Scorer("R", c, 4.0 * sigma)
                        if test == "ni":
                            pr = EProcess(M_NI, c, "upper", "agrapa", theta=theta, prior_x=0.0)
                        else:
                            pr = EProcess(M_KILL, c, "lower", "agrapa", theta=theta, prior_x=M_KILL + 0.02)
                        t = hor + 1
                        for i in range(1, hor + 1):
                            d, runs = model.block()
                            if pr.update(sc.score(d, runs)) >= THRESHOLD:
                                t = i; break
                        ts.append(t)
                    ts.sort()
                    res[key] = (ts[len(ts) // 2], ts[int(0.9 * len(ts))], sum(1 for v in ts if v <= hor) / len(ts))
                sims[f"sens|{sigma}|{theta}|{c:.4f}"] = res
                print(f"| {sigma:.0%} | {theta} | {c:.3f} | {res['ni'][0]}/{res['ni'][1]} | {fmt(res['k6'][0], 400)} | "
                      f"{fmt(res['k10'][0], 400)} | {res['null'][2]:.4f} |")
    out["sim"] = sims
    t_sec2 = time.process_time() - t0

    # ---------------- section 3: revision studies ----------------
    rev = {}
    rng3 = random.Random(a.seed + 3)
    nr = a.sessions_rev
    fq = lambda v, h: (str(v) if v is not None else f">{h}")
    print("\n## 3. Revision studies [S] (aGRAPA; separate RNG stream seed+3; noise, outliers, stalls, drift [G])\n")

    print("### 3a. Outlier-rate grid at true parity: NI share within N; A/A superiority false alarms (R and S)\n")
    print("| sigma_d | P(outlier run) | N | NI within N (R) | NI median / p90 (censored at N) | mean x (R) "
          "| planted x1.03 NI false pass (R) | A/A sup false alarm R / S |")
    print("|---|---|---|---|---|---|---|---|")
    for sigma in (0.02, 0.04):
        N = 2 * blocks_planned(sigma)
        for p_run in (0.0, 0.005, 0.01, 0.02, 0.05, 0.10):
            r = run_sessions(rng3, nr, mu=0.0, sigma=sigma, horizon=N, p_run=p_run,
                             tests=[("ni", "ni", "R"), ("supR", "sup", "R"), ("supS", "sup", "S")])
            rp = run_sessions(rng3, nr, mu=log(1.03), sigma=sigma, horizon=N, p_run=p_run, tests=[("ni", "ni", "R")])
            rev[f"3a|{sigma}|{p_run}"] = {"parity": r, "planted103": rp}
            print(f"| {sigma:.0%} | {p_run} | {N} | {r['ni']['rate']:.3f} | {fq(r['ni']['median'], N)} / "
                  f"{fq(r['ni']['p90'], N)} | {r['ni']['mean_x']:.5f} | {rp['ni']['rate']:.4f} | "
                  f"{r['supR']['rate']:.4f} / {r['supS']['rate']:.4f} |")

    print("\n### 3b. A/A with label asymmetry and outliers: superiority false alarm within N, R vs S scorer\n")
    print("| sigma_d | P(outlier run) | label asymmetry (B faster) | R | S | pooled-mean test power [D] |")
    print("|---|---|---|---|---|---|")
    nd = statistics.NormalDist()
    for sigma in (0.02, 0.04):
        N = 2 * blocks_planned(sigma)
        for p_run in (0.02, 0.05):
            for asym in (0.0, 0.01, 0.02):
                r = run_sessions(rng3, nr, mu=-asym, sigma=sigma, horizon=N, p_run=p_run,
                                 tests=[("supR", "sup", "R"), ("supS", "sup", "S")])
                se = sigma / sqrt(100 * N)
                powd = (1 - nd.cdf(Z995 - asym / se)) + nd.cdf(-Z995 - asym / se)
                rev[f"3b|{sigma}|{p_run}|{asym}"] = {**r, "pooled_power": powd, "pooled_se": se}
                print(f"| {sigma:.0%} | {p_run} | {asym:.1%} | {r['supR']['rate']:.4f} | {r['supS']['rate']:.4f} | "
                      f"{powd:.3f} (SE {se:.5f}) |")
    for asym in (0.001, 0.002, 0.005):
        for sigma in (0.02, 0.04):
            N = 2 * blocks_planned(sigma); se = sigma / sqrt(100 * N)
            rev[f"3b_pooled|{sigma}|{asym}"] = (1 - nd.cdf(Z995 - asym / se)) + nd.cdf(-Z995 - asym / se)
    print("\nPooled two-sided test of the mean A/A d over 100 x N blocks at alpha 0.01 [D]: power at asymmetry "
          + "; ".join(f"{asym:.1%}: {rev[f'3b_pooled|0.02|{asym}']:.3f} (sigma 2%) / {rev[f'3b_pooled|0.04|{asym}']:.3f} (4%)"
                      for asym in (0.001, 0.002, 0.005)))

    print("\n### 3c. Kill e-process: drafted vs revised (aGRAPA)\n")
    print("Drafted: outliers scored +c, clip c, theta 0.5. Revised: outliers scored -c_kill, "
          "c_kill = max(3 sigma, m_kill + 3 sigma), theta 0.5 or 0.8. 'within 2N' is the product across the two "
          "N-sessions an unchanged binary may get (one e-process; fresh randomisation in session 2).\n")
    print("| sigma_d | variant | scenario | P(outlier run) | kill within N | kill within 2N | median (censored at 2N) |")
    print("|---|---|---|---|---|---|---|")
    variants = [("drafted", "R", lambda s: clip_for(s), 0.5), ("rev th0.5", "Rk", clip_kill_for, 0.5),
                ("rev th0.8", "Rk", clip_kill_for, 0.8)]
    for sigma in (0.02, 0.04):
        N = 2 * blocks_planned(sigma)
        nk = nr if sigma == 0.02 else max(200, nr // 2)
        scen = [("parity", 0.0, p) for p in (0.0, 0.02, 0.05, 0.10)] + [
            ("kill boundary 1/0.97", M_KILL, 0.0), ("kill boundary 1/0.97", M_KILL, 0.02),
            ("time x1.06", log(1.06), 0.0), ("time x1.10", log(1.10), 0.0)]
        for name, mu, p_run in scen:
            tests = [(lab, "kill", sk, cf(sigma), th) for lab, sk, cf, th in variants]
            r = run_sessions(rng3, nk if not name.startswith("time") else max(200, nk // 2), mu=mu, sigma=sigma,
                             horizon=2 * N, p_run=p_run, tests=tests, report_within=N)
            rev[f"3c|{sigma}|{name}|{p_run}"] = r
            for lab, *_ in variants:
                o = r[lab]
                print(f"| {sigma:.0%} | {lab} | {name} | {p_run} | {o['rate_within_%d' % N]:.4f} | {o['rate']:.4f} | "
                      f"{fq(o['median'], 2 * N)} |")
    print("\nLargest kill wealth reachable within N if every block sits at the clip [D]:")
    for sigma in (0.02, 0.04):
        N = 2 * blocks_planned(sigma)
        for lab, sk, cf, th in variants:
            cc = cf(sigma); gmax = (cc - M_KILL) / (cc + M_KILL); f = 1 + th * gmax
            mb = math.ceil(log(THRESHOLD) / log(f))
            rev[f"3c_max|{sigma}|{lab}"] = {"g_max": gmax, "factor": f, "min_blocks": mb, "max_wealth_N": f ** N}
            print(f"  sigma {sigma:.0%}, {lab}: c = {cc:.4f}, g_max = {gmax:.3f}, factor {f:.3f}, "
                  f">= {mb} blocks to 20, max wealth in N = {N}: {f ** N:.1f}")

    print("\n### 3d. Tail check (06 §6.2): NI at true parity with environmental outliers, and B-only rare stalls\n")
    print("p0 = 95% Clopper-Pearson upper bound of a simulated 20 x 24-block A/A pilot's slow-outlier rate; "
          "deny NI credit iff P(Bin(n_B, p0) >= k_B) <= 0.01. Rules: 'crossing' = B runs of the confirmatory "
          "session at the crossing (06 literal); 'pooled N' / 'pooled 2N' = also pool the candidate's 6-block "
          "screening session and wait until the pooled B-run count reaches N / 2N; 'pooled N, 5%' = pooled N at a "
          "one-sided 5% level (the rule X4 pre-registers).\n")
    print("| sigma_d | scenario | true E[log ratio] | NI reaches 20 within N | credited: crossing | "
          "credited: pooled N | credited: pooled 2N | credited: pooled N, 5% |")
    print("|---|---|---|---|---|---|---|---|")
    for sigma in (0.02, 0.04):
        N = 2 * blocks_planned(sigma)
        rules = (("crossing", 0, 0), ("pooled_N", 6, N), ("pooled_2N", 6, 2 * N), ("pooled_N_5pct", 6, N, 0.05))
        cases = [("parity, outliers 0", 0.0, 0.0, (0.0, 0.0)), ("parity, outliers 0.005", 0.0, 0.005, (0.0, 0.0)),
                 ("parity, outliers 0.02", 0.0, 0.02, (0.0, 0.0)), ("parity, outliers 0.05", 0.0, 0.05, (0.0, 0.0)),
                 ("B: 15% runs 30% slow", 0.0, 0.0, (0.15, 0.30)), ("B: 10% runs 50% slow", 0.0, 0.0, (0.10, 0.50)),
                 ("B: 5% runs 30% slow", 0.0, 0.0, (0.05, 0.30))]
        for name, mu, p_run, stall in cases:
            tail = PilotTail(rng3, sigma, p_run)
            r = run_sessions(rng3, nr, mu=mu, sigma=sigma, horizon=N, p_run=p_run, stall=stall,
                             tests=[("ni", "ni", "R")], tail=tail, tail_rules=rules)
            el = stall[0] * log(1 + stall[1])
            rev[f"3d|{sigma}|{name}"] = {**r["ni"], "pilot_flag_rate": tail.rate}
            cr = r["ni"]["credited"]
            print(f"| {sigma:.0%} | {name} | {el:.4f} | {r['ni']['rate']:.3f} | {cr['crossing']:.3f} | "
                  f"{cr['pooled_N']:.3f} | {cr['pooled_2N']:.3f} | {cr['pooled_N_5pct']:.3f} |")

    print("\n### 3e. Sentinels in planted-regression sessions (n_cal = 2, share 1/6)\n")
    print("| sigma_d | P(outlier run) | label asymmetry | k sentinels | drafted rule: max wealth [D] | "
          "void: mean test | void: variance test | void: either |")
    print("|---|---|---|---|---|---|---|---|")
    for sigma in (0.02, 0.04):
        for p_run, asym in ((0.0, 0.0), (0.005, 0.0), (0.02, 0.0), (0.05, 0.0), (0.0, 0.01), (0.0, 0.02)):
            r = sentinel_study(rng3, sigma, 2 * nr, p_run, asym)
            rev[f"3e|{sigma}|{p_run}|{asym}"] = r
            print(f"| {sigma:.0%} | {p_run} | {asym:.1%} | {r['k_sentinels']} | {r['max_wealth_drafted_rule']:.2f} | "
                  f"{r['void_mean']:.4f} | {r['void_var']:.4f} | {r['void_any']:.4f} |")

    print("\n### 3f. Trend voids (two-sided MK, alpha 0.01, either arm) and drift with fixed vs randomised order\n")
    print("| sigma_d | noise / drift | order | sessions | void: uncorrected | void: Hamed-Rao all sig. lags | "
          "void: lag-1, floored (pre-registered) | A/A sup false alarm (R) | mean d |")
    print("|---|---|---|---|---|---|---|---|---|")
    for sigma in (0.02, 0.04):
        nm = max(200, nr // 2) if sigma == 0.02 else max(100, nr // 10)
        for label, kw in (("iid, outliers 0.005", {"p_run": 0.005}), ("AR(1) phi 0.6", {"phi": 0.6}),
                          ("ramp 3 sigma total", {"ramp_total": 3 * sigma}),
                          ("ramp 3 sigma total", {"ramp_total": 3 * sigma, "order": "AABB"}),
                          ("ramp 0.25 total", {"ramp_total": 0.25, "order": "BBAA"}),
                          ("ramp 0.25 total", {"ramp_total": 0.25})):
            r = mk_study(rng3, sigma, nm, **kw)
            od = kw.get("order", "random ABBA/BAAB")
            rev[f"3f|{sigma}|{label}|{od}"] = {**r, "sessions": nm}
            print(f"| {sigma:.0%} | {label} | {od} | {nm} | {r['void_uncorrected']:.3f} | "
                  f"{r['void_hamed_rao_all_lags']:.3f} | {r['void_lag1_floored']:.3f} | {r['sup_false_alarm']:.3f} | "
                  f"{r['mean_d']:+.5f} |")

    print("\n### 3g. Planted level: true mean log-ratio at which E[clip(d)] equals the margin [D]\n")
    for sigma in (0.02, 0.04):
        for name, m in (("3%", M_NI), ("4%", float((Decimal(104) / Decimal(100)).ln()))):
            mu_star = clip_bias_level(sigma, m)
            rev[f"3g|{sigma}|{name}"] = {"margin": m, "mu_star": mu_star, "bias": mu_star - m}
            print(f"  sigma {sigma:.0%}, level {name}: margin {m:.6f}, needed true mean {mu_star:.6f} "
                  f"(clip bias {mu_star - m:+.6f} = {100 * (exp(mu_star - m) - 1):+.3f}% in time)")
    out["revision"] = rev
    t_sec3 = time.process_time() - t0 - t_sec2

    print("\n## 4. X4 quiet-machine hours [D from G inputs]\n")
    print("Per run 10 s micro, 120 s e2e x 1.5 cool-down, 120 s setup per session [G]. Pilot = 20 micro A/A "
          "sessions x 24 blocks + 3 e2e A/A sessions x 12 blocks [target], sigma-independent. X3 = X3 prereg §6 "
          "plan figure [inference there].\n")
    print("| sigma_d | N | pilot | micro A/A | micro planted | e2e A/A | A/A' | pos. control | spin confirm | X3 | "
          "ROADMAP-comparable | total h | 8-h nights | ROADMAP-style reconstruction |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    qh = []
    for sigma in (0.02, 0.04):
        stopN = ttp_res[(sigma, 0.0, "R", "N")]["agrapa"]["mean_min_t_h"]
        for label, e2e_blocks, mult in (("e2e to N", None, 1), ("e2e stop at NI pass", stopN, 1),
                                        ("micro A/A to 2N (owner option)", None, 2)):
            q = quiet_hours(sigma, e2e_blocks, mult); q["rule"] = label; qh.append(q)
            print(f"| {sigma:.0%} | {q['N_blocks']} | {q['pilot_h']} | {q['micro_AA_h']} | {q['micro_planted_h']} | "
                  f"{q['e2e_AA_h']} | {q['AA_prime_h']} | {q['posctl_h']} | {q['spin_confirm_h']} | "
                  f"{q['X3_placeholder_h']} | {q['roadmap_comparable_h']} | {q['total_h']} ({label}) | "
                  f"{q['nights_of_8h']} | {q['roadmap_style_reconstruction_h']} |")
    out["quiet_hours"] = qh
    out["golden"] = golden_path(a.seed)
    out["cpu_seconds"] = round(time.process_time() - t0, 1)
    out["cpu_seconds_by_section"] = {"1+2": round(t_sec2, 1), "3": round(t_sec3, 1)}
    print(f"\nCPU {out['cpu_seconds']} s (sections 1-2: {t_sec2:.1f}, section 3: {t_sec3:.1f}); "
          f"script sha256 {out['script_sha256'][:16]}; seed {a.seed}")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=1, default=str)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
