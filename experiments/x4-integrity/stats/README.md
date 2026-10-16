# X4 calibration statistics

**Track:** x4-integrity. **Status:** DESIGN-phase reference implementation, revision 2. **Date:** 2026-10-16.
Anchors: ROADMAP §3.5 (A/A rule, planted-regression calibration, time-to-pass), §1 rule 4, §10 (quiet hours); [06-forge §6](../../../docs/architecture/06-forge.md); DR-018. Revision 2 follows two same-family, independent-context reviews ([prereg review log](../../../docs/m0/prereg/X4-integrity.md#12-review-log-independent-reviewers-with-model-family)).

[`x4_calibration.py`](x4_calibration.py) — standard-library Python (≥ 3.10), deterministic per `--seed`. Default run: **37.1 CPU-seconds** (sections 1–2: 21.5 s, section 3: 15.7 s) [M, this laptop, CPython 3.12.10, 2026-10-16]; script SHA-256 `6ac99140317716b378bdfda5487d95ea8186d6f7ba2a99bef484add33fae30f0`, seed 20261016. Every number below was copied from that run's output; each [S] number names its table and variant (σ_d, outlier-run rate p_run, scorer, bettor). Revision 1 (SHA-256 `d638ebbc…`, 20.2 CPU-s) is superseded; its section-2 tables are reproduced **unchanged** by revision 2 (verified by diff), so numbers the reviewers quoted from them still reproduce.

```
python -I x4_calibration.py                  # everything: sections 0-4
python -I x4_calibration.py --binomial-only  # the exact OC tables (instant)
python -I x4_calibration.py --golden         # the golden wealth path for the Rust differential test
python -I x4_calibration.py --json out.json  # also dump structured results (incl. PREREG constants, golden path)
python -I x4_calibration.py --sessions-null 20000 --sessions-ttp 10000 --sessions-rev 5000   # tighter Monte Carlo
```

Scorers: **R** = run-level, arm-relative outliers scored +c (the gate scorer, provisional pending owner question 4); **S** = symmetric clip, no loss scoring (the A/A gate's second statistic); **Rk** = R with outliers scored −c_kill (the kill test); **06** = 06 §6.2's literal block clip (descriptive). Bettor aGRAPA unless stated. Outlier runs are 10–15% slow, either arm. All noise, outlier, stall and drift models are assumptions [G]; nothing here is measured except the CPU time and the constant check.

## 0. Pinned constants [D]

`m_NI = RN(ln 1.03) = 0x1.e44a9a3bed663p-6`, `m_kill = RN(−ln 0.97) = 0x1.f30b2d0091d82p-6`, computed with 60-digit decimal arithmetic. This laptop's `math.log(1.03)` returns `0x1.e44a9a3bed66bp-6`, **8 ulps away** [M, CPython 3.12.10], because it takes the log of fl(1.03). A Rust implementation calling `(1.03f64).ln()` would differ from the real-number margin the same way, so the differential check pins the hex constants (§5).

## 1. Exact operating characteristics of the A/A rule — [D]

`P(pass) = P(Binomial(100, p) ≤ 2)`, exact rational arithmetic.

| rule | true false-alarm rate | P(pass) exact [D] | ROADMAP §3.5 [inference] |
|---|---|---|---|
| ≤ 2/100 | 1% | 0.9206 | 0.92 |
| ≤ 2/100 | 5% | 0.1183 | 0.12 |
| ≤ 2/100 | 8% | 0.0113 | 0.01 |
| ≤ 5/100 | 8% | 0.1799 | 0.18 |

All four ROADMAP figures agree to two decimals [D]. The ≤ 2/100 rule passes with probability 0.9 / 0.5 / 0.1 at true rates of 1.11% / 2.67% / 5.23% [D] (≤ 5/100: 3.18% / 5.65% / 9.08%).

**Leniency, both ways (reworded in revision 2).** The rule is **stricter than validity requires**: an e-process sitting exactly at Ville's bound (5%) fails it with probability 0.88 [D]. It is **lenient relative to what a sound evaluator shows here**: simulated A/A false-alarm rates are ≈ 0–0.4% (tables 2b, 3a), yet the rule still passes half the time at 2.67%.

**Independence assumption, and its sensitivity [D, table 1b].** The binomial OC assumes independent, identically distributed sessions. Sessions share nights, thermal history and the pilot's c and N. With a night-level rate drawn from a Beta distribution (intra-night correlation 0.05):

| true mean rate | iid | one cluster of 100 (beta-binomial) | 4 nights × 25 | 10 nights × 10 |
|---|---|---|---|---|
| 1% | 0.9206 | 0.8724 | 0.8697 | 0.8901 |
| 5% | 0.1183 | 0.4172 | 0.2369 | 0.1699 |
| 8% | 0.0113 | 0.2091 | 0.0592 | 0.0270 |

Correlation makes the rule more lenient toward a broken evaluator; spreading sessions over many nights (the pre-registered randomised schedule) keeps it close to the iid figures. The counted set is exactly the first 100 sessions that are not hygiene-voided, in that schedule.

## 2. The e-processes as first drafted — [S] (tables 2a–2f, unchanged)

- **Planted-regression calibration (table 2a).** Across all 32 drafted cells the NI e-process reached 20 within N in **≤ 0.70%** of sessions (max 0.0070: σ_d 4%, p_run 0.005, 06 scorer, ×1.03, aGRAPA; R scorer max 0.0060 at the same cell). Revision 1 wrote "< 0.7%"; it is ≤ 0.7%. The literal 06 scorer at ×1.03, σ_d 2%, p_run 0 has **mean x 0.02898 < m_NI 0.02956**: clipping puts the planted 3% level slightly inside the NI *alternative* for that estimand (§3g fixes the level).
- **A/A false alarm (table 2b).** ≤ 0.10% within N in every no-asymmetry cell (max 0.0010: σ_d 4%, p_run 0, 06 scorer). **The AR(1) φ = 0.6 rows are 0.0000 at both σ_d.** Revision 1's sentence that AR(1) drift "raises it" was contradicted by its own output and is withdrawn: with identical binaries and randomised ABBA/BAAB order, d is conditionally symmetric whatever the drift, so the A/A rule tests harness label asymmetry, not drift. Label-asymmetry power (R, aGRAPA): σ_d 2% → 0.0020 at a 2% asymmetry (N = 12 leaves only blocks 8–12 for a crossing, since 20 needs ≥ 8 blocks at θ = 0.5 [D: log 20 / log 1.5 = 7.39]); σ_d 4% → 0.0500 at 1% and 0.5000 at 2%.
- **Time-to-pass at true parity (table 2c).** R, aGRAPA, p_run 0: median 9, p90 11, share within N 0.947 (σ_d 2%); median 23, p90 36, share 0.968 (σ_d 4%). Across the four σ_d-2% aGRAPA variants (R/06 × p_run 0/0.005) the share within N spans **0.882–0.960** and the p90 **11–13** (N = 12). Revision 1's "p90 ≈ 13" and "≈ 95–97% within N" are replaced by these ranges.
- **Kill as drafted (table 2d).** σ_d 2%: 0.0000 even at a true ×1.10 — unreachable, because with c = 0.06 and θ = 0.5 the per-block factor is ≤ 1.163, so 20 needs ≥ 20 blocks and the largest wealth within N = 12 is 6.1 [D, section 3c]. σ_d 4%: ×1.10 → 1.0000, ×1.06 → 0.7240 (R, p_run 0). Revision 1's "full power at a 10% regression" held at σ_d 4% only.
- **Superiority power (table 2e).** The literal 06 scorer never detects a 20% improvement (share by 400 blocks 0.000 at σ_d 1%, 2% and 4%) and needs a median of 155 blocks for a 5% improvement at σ_d 2%, against 10 under R. This is the evidence for owner question 4.
- **Sensitivity (table 2f).** θ = 0.8 for NI raises the planted ×1.03 crossing rate to 0.0140 at σ_d 2% and 4%; θ stays 0.5 for superiority and NI.

## 3. Revision studies — [S] (separate RNG stream, seed + 3; 1,000 sessions per cell unless stated)

**3a. Outlier-rate grid at true parity (R, aGRAPA).** Share of NI e-processes reaching 20 within N, by outlier-run rate:

| σ_d (N) | 0 | 0.5% | 1% | 2% | 5% | 10% |
|---|---|---|---|---|---|---|
| 2% (12) | 0.959 | 0.886 | 0.794 | 0.685 | 0.311 | 0.089 |
| 4% (44) | 0.976 | 0.949 | 0.946 | 0.915 | 0.803 | 0.603 |

Loss-scoring spends evidence: at a 5% outlier rate, NI passes within N in under a third of parity sessions at σ_d 2%. Validity holds across the grid: planted ×1.03 NI false passes ≤ 0.0100 (max: σ_d 4%, p_run 2%) and A/A superiority false alarms ≤ 0.0040 (S, σ_d 4%, p_run 5%). The per-run outlier rate is therefore a pilot metric, and owner question 6 applies if it puts the share below 0.8.

**3b. A/A with label asymmetry and outliers, R vs S (within N).** σ_d 4%, p_run 2%: 1% asymmetry → R 0.0480, S 0.0620; 2% → R 0.3630, S 0.4630. σ_d 4%, p_run 5%: 2% → R 0.2170, S 0.4270. σ_d 2%: ≤ 0.0060 in every cell (N too short). S is the more sensitive statistic, which is why the A/A gate must pass under both. The **pooled two-sided test of mean A/A d** over 100 × N blocks (SE 0.058% at σ_d 2%, 0.060% at 4% [D]) has power 0.199/0.179 at a 0.1% asymmetry, 0.813/0.771 at 0.2% and 1.000 at 0.5% [D].

**3c. Kill e-process, drafted vs revised.** Revised = Rk scoring (outliers −c_kill), c_kill = max(3σ, m_kill + 3σ), θ_kill 0.8, continued across the two N-sessions of an unchanged binary.

| σ_d | scenario | drafted: within N / 2N | revised θ 0.5: N / 2N | **revised θ 0.8: N / 2N** |
|---|---|---|---|---|
| 2% | parity, p_run 0–10% | 0 / 0 | 0 / 0 | **0 / 0** |
| 2% | kill boundary (1/0.97), p_run 0 and 2% | 0 / 0 | 0 / 0 | **0 / 0** |
| 2% | ×1.06 | 0 / 0.072 | 0 / 0.050 | **0 / 0.664** |
| 2% | ×1.10 | 0 / 1.000 | 0 / 0.950 | **0.048 / 0.992** |
| 4% | parity, p_run 0–10% | 0 / 0 | 0 / 0 | **0 / 0** |
| 4% | kill boundary, p_run 2% | 0 / 0.006 | 0 / 0 | **0 / 0.004** |
| 4% | ×1.06 | 0.736 / 1.000 | 0.508 / 0.996 | **0.888 / 1.000** |
| 4% | ×1.10 | 1.000 / 1.000 | 1.000 / 1.000 | **1.000 / 1.000** |

(parity cells: 1,000 sessions at σ_d 2%, 500 at 4%; regression cells: 500 / 250.) Largest per-block factor [D]: drafted 1.163 (σ_d 2%) / 1.298 (4%); revised θ 0.8: 1.397 / 1.531, so ≥ 9 / ≥ 8 blocks to 20. **At σ_d 2% a kill still needs both N-sessions** (owner question 5). The drafted variant's 0.006 at the kill boundary with outliers is the anti-conservative loss scoring at work.

**3d. Tail check (06 §6.2).** p0 = one-sided 95% Clopper–Pearson upper bound of a simulated 20 × 24-block A/A pilot's slow-outlier rate. Share of sessions whose NI crossing is *credited* after the check:

| σ_d | scenario (true mean log-ratio) | NI within N | at crossing, 1% (06 literal) | pooled with screening, n_B ≥ N, 1% | pooled, 2N, 1% | **pooled, N, 5% (pre-registered)** |
|---|---|---|---|---|---|---|
| 2% | parity, p_run 0 | 0.954 | 0.954 | 0.954 | 0.954 | **0.951** |
| 2% | parity, p_run 0.5% | 0.897 | 0.897 | 0.896 | 0.896 | **0.893** |
| 2% | parity, p_run 2% / 5% | 0.675 / 0.349 | same | same | same | **0.675 / 0.349** |
| 2% | B: 15% of runs 30% slow (0.0394) | 0.130 | 0.110 | 0.038 | 0.038 | **0.017** |
| 2% | B: 10% of runs 50% slow (0.0405) | 0.284 | 0.265 | 0.138 | 0.138 | **0.065** |
| 2% | B: 5% of runs 30% slow (0.0131) | 0.551 | 0.539 | 0.432 | 0.432 | **0.291** |
| 4% | parity, p_run 0 / 5% | 0.977 / 0.809 | same | same / 0.808 | same / 0.808 | **0.977 / 0.802** |
| 4% | B: 15% of runs 30% slow | 0.011 | 0.003 | 0.001 | 0.000 | **0.001** |
| 4% | B: 10% of runs 50% slow | 0.061 | 0.029 | 0.015 | 0.002 | **0.014** |

The literal check at the crossing barely bites, because sessions that cross are those that happened to have few stalls. Pooling with the screening session and a 5% level cuts credit for the reviewers' rare-stall case from 0.130 to 0.017 at σ_d 2% while costing ≤ 0.007 of credited parity sessions. **Residual:** ≈ 2–7% of rare-stall attempts are still credited at σ_d 2%. (Reviewer 2's probe reported 11.6% for the first stall case at σ_d 2%; this run gives 0.130 for the same case without the check, consistent within Monte Carlo error.)

**3e. Sentinels in planted-regression sessions (n_cal 2, sentinel share 1/6, 2,000 sessions).** The drafted sentinel rule (sentinel superiority e ≥ 20) is vacuous: k = 2 sentinels at σ_d 2% cap the wealth at 2.25, and k = 8 at 4% reach 20 only if all 8 sit at the clip (25.6) [D]. The replacement (S1 mean z-test + S2 χ² variance envelope, both two-sided 0.01, on blocks without a run-outlier flag): false voids 1.85% / 1.90% / 1.75% / 2.30% at p_run 0 / 0.5% / 2% / 5% (σ_d 2%) and 1.65% / 2.20% / 3.30% / 6.00% (σ_d 4%); a 2% label asymmetry voids a session 14.1% (σ_d 2%) and 13.25% (σ_d 4%) of the time. Per-session sentinels are weak; the pooled test (3b) carries the asymmetry check.

**3f. Trend voids (two-sided MK at α 0.01 on either arm's per-run log-times; A/A sessions of N blocks).**

| σ_d (sessions) | noise / drift | order | uncorrected | Hamed–Rao, all significant lags | **lag-1, floored (pre-registered)** | mean d |
|---|---|---|---|---|---|---|
| 2% (500) | iid, p_run 0.5% | random | 0.026 | 0.100 | **0.022** | +0.00005 |
| 2% (500) | AR(1) φ 0.6 | random | 0.088 | 0.140 | **0.060** | −0.00023 |
| 2% (500) | linear drift 3σ over the session | random / AABB | 0.984 / 0.980 | 0.984 / 0.984 | **0.976 / 0.960** | −0.00010 / +0.00245 |
| 2% (500) | linear drift 25% | BBAA / random | 1.000 | 1.000 | **1.000** | −0.01048 / −0.00011 |
| 4% (100) | iid, p_run 0.5% | random | 0.010 | 0.030 | **0.010** | +0.00012 |
| 4% (100) | AR(1) φ 0.6 | random | 0.110 | 0.150 | **0.040** | −0.00106 |
| 4% (100) | drift 3σ / 25% | any | 1.000 | 1.000 | **1.000** | — |

The full Hamed–Rao correction is liberal at 24–88 runs per arm; the lag-1 form is close to the ≈ 2% nominal (two arms at 1%) under iid noise and halves the AR(1) excess. Fixed orders bias mean d under drift (BBAA: −0.0105, i.e. B looks 1% faster); randomised order does not. No A/A superiority false alarm occurred in any 3f cell (N is short).

**3g. Planted level on the estimand [D].** True mean log-ratio μ* at which E[clip(d)] equals the margin, d ~ N(μ, σ²): 3% level +0.060% (σ_d 2%) and +0.017% (4%) above log 1.03 in time; 4% level +0.184% and +0.033%. The pre-registered level adds a 0.25% overshoot on top (MEASUREMENT-SERVICE §8.3).

## 4. Quiet-machine hours — [D from G inputs]

Inputs [G]: 10 s micro run, 120 s e2e run × 1.5 cool-down, 120 s setup per session; pilot = 20 micro A/A sessions × 24 blocks + 3 e2e sessions × 12 blocks [target], σ-independent; micro A/A to N; planted sessions N + 2 calibration + ⌈N/6⌉ sentinel blocks; A/A′ 20 sessions; positive control 10 sessions; separate long run 2 × 256 blocks; X3 = its prereg §6 plan figure (3.6 / 13.2 h [inference there]).

| σ_d (N) | pilot | micro A/A | micro planted | e2e A/A to N (stop at NI pass) | A/A′ | pos. ctl | long run | X3 | ROADMAP-comparable | **total** | 8-h nights |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2% (12) | 13.3 | 16.7 | 42.2 | 48.7 (35.7) | 3.3 | 1.7 | 5.7 | 3.6 | 111.2 (98.2) | **135.1 (122.1)** | 16.9 (15.3) |
| 4% (44) | 13.3 | 52.2 | 126.7 | 176.7 (98.6) | 10.4 | 5.2 | 5.7 | 13.2 | 368.8 (290.6) | **403.4 (325.3)** | 50.4 (40.7) |

Owner option, micro A/A to 2N (observable p90): totals 148.5 h (σ_d 2%) and 452.3 h (4%).

**Against ROADMAP §10 (corrected in revision 2).** ROADMAP §10's M0 row sits in the column "Quiet h per attempt, σ_d = 2% / 4%", so "≈ 60–215" pairs **60 h with σ_d 2% and 215 h with σ_d 4%**. Revision 1 said X4 "brackets" that line at the low-σ_d end; it does not. **X4 alone exceeds ROADMAP §10's M0 line at both σ_d ends**: the ROADMAP-comparable part is +85% at σ_d 2% (111.2 vs 60) and +72% at 4% (368.8 vs 215); the full plan is +104–125% and +51–88%. A ROADMAP-style reconstruction (A/A at n, planted at N, end-to-end at n, no setup, plus X3) gives **60.9 h and 223.4 h** [D], matching COST.md §1.4's 60.3 / 221.0 h [D there]. The likely cause is that §10 used n blocks per session where §3.5 requires N = 2n [inference]. X4 may not edit §10; owner question 1 carries it, and D-22's "planned hours exceed the available windows" disjunct is the one at risk.

**Stopping the end-to-end A/A sessions at the first NI pass** saves 13.0 h (σ_d 2%) and 78.1 h (4%) [D] but is optional stopping on favourable trajectories: σ̂_d from those sessions can be biased low [inference], and σ_d is the M0 deliverable. If the Owner takes the option, σ_d is estimated only from sessions run to N.

## 5. Golden wealth path and the differential test

`--golden` prints 24 blocks (σ̂ 0.02, 2% outlier runs, seed 20261016) with every run log-time, d, x (R), x_kill (Rk) and the three wealth paths (superiority, NI, kill) as hex floats, plus c, c_kill and c_run in hex. The Rust e-process must reproduce every `K_i` **bit for bit** under `PREREG["float_rules"]` (binary64, round-to-nearest-even, operations in the written order, no FMA contraction). Revision 1's "agree to within floating-point tolerance" left crossings near 20 undecided and is withdrawn.

## Role in the X4 gate

This script is the **reference implementation** the measurement service's Rust e-process is differentially tested against ([MEASUREMENT-SERVICE.md §8.6](../MEASUREMENT-SERVICE.md)), one of the three things a `validated`-grade statistical computation needs ([06 §5.3](../../../docs/architecture/06-forge.md) condition 2). Its `PREREG` dictionary is the single source of the gate constants copied into the prereg §7.
