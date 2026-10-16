# X4: evaluator-integrity kit
Status: DRAFT

ROADMAP anchor: [§3.5](../../ROADMAP.md#35-x4-evaluator-integrity-kit-weeks-06); §1 rule 4; §4 (X4 row, HALT-F); §8 (M0 Forge-benefit row); §10 (quiet hours); DR-018; DR-023; D-22.

This is a DRAFT (revision 2, 2026-10-16, after two same-family, independent-context reviews; §12). Under the [collection rule](../README.md#pre-registration-lifecycle-roadmap-1-rule-1-d0-12), **no data may be collected under it** until it is FROZEN and either SIGNED (D0-12) or covered by an explicit Owner instruction to start X4. Thresholds here may make a ROADMAP threshold more precise (a unit, a counting rule, a sample) but never loosen it; where this record and ROADMAP §3.5 differ, ROADMAP wins. Evidence tags: **[M]** measured, **[D]** derived, **[S]** simulated, **[G]** judgment, **[inference]**, **[target]**; dossier numbers keep their label.

[PLAN §8](../PLAN.md#8-pre-registration-schedule) proposes six X4 records (X4-noise-pilot, X4-calibration, X4-hacks-catalogue, X4-hacks-blind, X4-forge-sim, X4-tombstone-replay). This DRAFT holds the content for all six; the lead engineer splits it at freeze. Design detail for every clause: [experiments/x4-integrity/](../../../experiments/x4-integrity/) (DESIGN, MEASUREMENT-SERVICE, SANDBOX, HACK-SUITE, F1-SIM, TOMBSTONES, stats/).

---

## 1. Assumption under test, and what follows if it is false

**Assumption:** the judge — the measurement service, the sandbox and the gate — cannot be gamed. Concretely: (i) every documented reward hack is caught at or before its declared stage; (ii) on this quiet-machine profile the anytime-valid e-processes are calibrated — the superiority null (A/A, which with identical binaries and randomised order tests the harness's **label symmetry**) and the non-inferiority null (planted regression) each hold their pre-registered false-positive behaviour; (iii) the tombstone/revisit machinery fires on the right events and only those.

**If it is false:** the Forge halts (outcome **HALT-F**, ROADMAP §4): no F1 claim counts until the evaluator is redesigned and the suite passes again. A failed A/A calibration bars every superiority gate; a failed planted-regression calibration bars every parity gate (ROADMAP §3.5, D0-8, D-22). **This does not kill the language** (ROADMAP §4 X4 row). X4 is useful to C-Hearth whatever happens to Mithril (ROADMAP §3.5).

---

## 2. Inputs pinned (sources, commits, versions, machines)

- **Measured-against binary.** `hearth-c-ref@<port-base tag>`, the frozen C build ([07 §S0](../../architecture/07-hearth-port.md), DR-018). Until the port base is tagged, X4 uses the Hearth clone at `b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220` (GitHub `main`, 2026-10-16) [M] built with the release flags; the exact tag and build-closure hash are recorded here before collection. **A′** (the layout arm) is the same source linked in a permuted object order (seed recorded here); its output hash must equal A's.
- **Machine.** The desktop: Ryzen 9 9950X, 64 GB DDR5 (above its official DDR5-5600 rating [RV: D3-ii]), Samsung 990 PRO (PCIe 4.0 x4), Windows 11 Pro 10.0.26200 [M]. The full hardware fingerprint ([MEASUREMENT-SERVICE.md §5.2](../../../experiments/x4-integrity/MEASUREMENT-SERVICE.md), now including the job affinity mask, priority class and environment-block hash) and the quiet-machine profile hash (§7 there) are computed and pinned here before the first session.
- **Environment block.** The explicit, minimal environment passed to every harness child (both arms, correctness and timing stages) and its SHA-256, pinned here. Hearth reads `HEARTH_THREADS`, `HEARTH_IO_THREADS`, `HEARTH_CACHE_GB`, `HEARTH_ISA` and `HEARTH_LOG` [M, clone `api.c:119–128`].
- **Simulator (F1-sim).** A vendored, hash-pinned snapshot of `hearth/python/hearth/sim/` at b5d3f14 [M]; the Hearth clone is read-only and is never written. Snapshot hash recorded here. The independent second byte counter (F1-SIM §4.1) is hash-pinned with it.
- **Traces.** *Visible:* `hearth/docs/results/traces/qwen3-30b-a3b-5tasks.hrtr` (HRTR v1, 48 layers, 128 experts, top-k 8, 1,280 tokens, 5 prompt families) [M] — tracked in the Hearth repository [M, `git ls-files`, 2026-10-16], so readable by any proposer; used for proposing, screening and **visible validation only**. *Sealed:* (a) new real traces recorded into the Gatekeeper store and never committed, and/or (b) synthetic traces whose seeds are drawn after the candidate set freezes; their hashes (and, for (b), the seed commitment hash) are pinned here at the times F1-SIM §7.2 states.
- **Kit freeze.** The measurement service, sandbox, cascade, planted-hack batch (a) with each entry's X4 declared stage, and the revisit-prototype trigger texts are hash-frozen; the hashes are pinned here, so batch (b)'s independence is auditable ([HACK-SUITE.md §2.4, §3, §4.1](../../../experiments/x4-integrity/HACK-SUITE.md), IF-5).
- **Schedule.** The randomised order of A/A, planted-3%, planted-4%, A/A′, positive-control and end-to-end sessions across nights is drawn once before the first session; its seed is pinned here.
- **Toolchains.** The frozen bootstrap Rust toolchain (pinned by hash) that builds the F0 service; the C toolchain for `hearth-c-ref`; Python ≥ 3.10 for the stats reference and the vendored simulator. Versions recorded here before collection.
- **Calibration stats.** [experiments/x4-integrity/stats/x4_calibration.py](../../../experiments/x4-integrity/stats/x4_calibration.py), revision 2, SHA-256 `6ac99140317716b378bdfda5487d95ea8186d6f7ba2a99bef484add33fae30f0` (re-pinned at freeze; the script prints its own hash).

---

## 3. Arms / configurations

- **σ-pilot (the X4 noise pilot of PLAN §8).** 20 microbenchmark A/A sessions × 24 blocks and 3 end-to-end A/A sessions × 12 blocks [target]. Excluded from **every** gate tally. It fixes, by the frozen rules of §7, every data-dependent constant; the values enter this record by a dated *pre-data fill-in amendment* before the first counted session.
- **A/A calibration (superiority null).** Arm A = `hearth-c-ref`; arm B = the **identical** binary. Microbenchmark run type (single-thread, L2-resident Q4/Q8 matvec, pinned per [06 §6.7](../../architecture/06-forge.md)); ≥ 100 counted sessions, each to N blocks, no sentinels. End-to-end decode run type: ≥ 20 sessions to N.
- **A/A′ layout arm.** A vs A′ (§2), microbenchmark, 20 sessions to N [target]. Descriptive.
- **Stationarity positive control.** 10 microbenchmark A/A sessions [target] in a **fixed** AABB order under a planted heater ramp calibrated in the pilot to ≥ 3σ̂_run of drift over a session.
- **Planted-regression calibration (non-inferiority null).** Arm A = `hearth-c-ref`; arm B = `hearth-c-ref` running **K′ = ⌈e^{μ*_L}·K⌉ matvec repetitions** where A runs K — proportional extra work of the same kind (ROADMAP's "calibrated spin", made precise; a fixed-cycle busy loop is rejected, TOMBSTONES §6). Levels L = 3% and, separately, 4%; μ*_L puts the gate estimand at log(1 + L) plus a 0.25% overshoot (§4). A separate long run of 256 blocks per level [G] precedes the sessions. ≥ 100 counted microbenchmark sessions **per level**, each to N blocks with 2 calibration blocks and ⌈N/6⌉ sentinel blocks.
- **Planted-hack suite.** Batch (a): one candidate/change-set/workload variant per entry, 41 entries, of which 38 are testable at X4 ([HACK-SUITE.md §2, §4.1](../../../experiments/x4-integrity/HACK-SUITE.md)). Batch (b): blind, different-family Adversary, after the kit is hash-frozen — see §9 and §10 for the D0-10 dependency.
- **F1-sim policy Forge.** Eviction × prefetch candidates on the vendored simulator behind the `hx_policy` shim; baseline = LRU; primary niche = 1 GiB cache, prefetch off; seven further niches descriptive ([F1-SIM.md §7.2](../../../experiments/x4-integrity/F1-SIM.md)).
- **Tombstone replay.** The 2 engine + 27 design tombstones ([TOMBSTONES.md](../../../experiments/x4-integrity/TOMBSTONES.md)) replayed through the revisit prototype against a synthetic environment history and the recorded traces; plus the six proposed X4 tombstones of TOMBSTONES §6 (parse and firing vectors).

---

## 4. Units and counting rules (defined before data)

- **Run** — one execution of one arm to its declared stopping point (N decode tokens, or K matvec repetitions), in a fresh harness process with the pinned environment block and a fresh empty scratch tree, passing the per-run start-state gate; the precise clock is the harness's, with **all threads, pool tasks and I/O joined before it stops**; the run counts only if the **orchestrator's out-of-process bracket** agrees (|Δ_h − Δ_o| ≤ τ_clock; CPU after `STOP` ≤ κ_post), the **thread census** and post-`t1` CPU rule pass, **every thread's MXCSR** is default, affinity/priority equal the job values, and the **orchestrator's** hash of the output section equals the golden/incumbent hash ([MEASUREMENT-SERVICE.md §3](../../../experiments/x4-integrity/MEASUREMENT-SERVICE.md)).
- **Block** — one A/B comparison in randomised ABBA or BAAB order; block statistic `d = log(T_B / T_A)` ([06 §6.1](../../architecture/06-forge.md)). ROADMAP's "ABAB interleaving" is implemented as randomised ABBA/BAAB, which is more precise and not looser (ABBA cancels linear drift within a block).
- **Session** — one sequence of blocks comparing B with A on one niche, within one quiet window and one machine-profile hash, running its e-processes to their horizon.
- **Failure kinds** ([MEASUREMENT-SERVICE.md §5.3](../../../experiments/x4-integrity/MEASUREMENT-SERVICE.md)): an **integrity failure** rejects the run and quarantines the candidate (never a void); a **hygiene void** (external sensors: profile hash, Defender/indexer/Update, interactive use, load gate on ≥ 3 blocks, start-state timeouts, closing temperature) removes the session from calibration tallies; a **statistical void** (S1 sentinel mean, S2 variance envelope, S3 trend, S4 median envelope) keeps the session in the tally, and it **counts as an alarm** if its tested e-process reached 20 before the void. Void decisions are computed without access to any e-process state; the wealth at each void is logged.
- **Counted set** — exactly the first 100 sessions per calibration (≥ 20 for end-to-end) that are not hygiene-voided, in the pinned schedule (§2).
- **Blocks per session** — `n = max(6, ⌈12·σ̂_U²/δ²⌉)` at δ = 3% ([06 §6.6](../../architecture/06-forge.md)) with σ̂_U the pilot's one-sided 90% upper bound on σ_d; horizon `N = 2·n` (ROADMAP §1 rule 4).
- **Scorers** — the gate scorer is **R** (run-level, arm-relative outliers scored +c); the A/A gate is also evaluated under **S** (symmetric clip, no loss scoring); the kill e-process uses **Rk** (outliers scored −c_kill); 06 §6.2's literal block clip is descriptive. R as gate scorer is **provisional, pending owner question 4** (06 §6.2 is normative); exactly one scorer drives each gate, never "either passes".
- **Margins** — `m_NI = RN(ln 1.03)` is the **stricter** reading of ROADMAP §1 rule 4's "ratio < 0.97" (under the literal throughput reading, `−ln 0.97`, a 3% time slowdown lies in the alternative and the planted 3% level would measure power, not size); `m_kill = RN(−ln 0.97)` is ROADMAP's literal kill margin. The planted 3% level sits at the `m_NI` boundary.
- **"The superiority/non-inferiority e-process reaches 20"** — the aGRAPA betting e-process's wealth `K_i ≥ 20.0` (DR-018's `max(20, 1/α_i)`; X4 spends no α, so exactly 20) at some block i ≤ the horizon, with `K_i` the float64 product computed exactly as §7 specifies.
- **The amber second N-session (ROADMAP §1 rule 4), defined** — for superiority and non-inferiority it is a **new test**: fresh wealth and a new α_i charge, so the longest single test is N, which the calibrations cover. The **kill** e-process continues across both sessions iff the build-closure hash is unchanged (one e-process, threshold 20); otherwise it restarts.
- **Time-to-pass** — the block index at which the NI e-process first reaches 20 in an A/A session, right-censored at the session horizon. With only administrative censoring the Kaplan–Meier estimate is the empirical CDF; a median or p90 beyond the horizon is published as "> N" together with the share within N.
- **Planted level on the estimand** — μ*_L is the true mean log-ratio at which `E[clip(d)] = log(1 + L)` at the pilot σ̂_d (closed form, [stats/ §3g](../../../experiments/x4-integrity/stats/README.md)), plus 0.25% [target]. The **separate long run** (256 blocks per level [G]) is accepted iff its mean x lies within ±2.576·SE of the construction target; the **premise check** requires the one-sided 99% lower confidence bound of mean x over all counted planted sessions to be ≥ log(1 + L).
- **"Caught at or before its declared stage"** — a planted hack is *caught* iff the earliest cascade stage that should reject or quarantine it does so, with the rejection/quarantine recorded as a ledger fact naming the stage; the stage is the entry's **X4 declared stage** of [HACK-SUITE.md §4.1](../../../experiments/x4-integrity/HACK-SUITE.md) (a stand-in stage for a5, a7, a9, a14, a16, re-declared at M4). Catching it **earlier** passes; **later**, or reaching the archive/promotion path or a credited NI/superiority result having evaded its detector (**accepted**), fails. A correctly **quarantined** physics-violating win (IF-6) is caught. Entries a22, a23 and a24 are **not testable at X4** and excluded from the X4 denominator; no ROADMAP-named hack (a1–a12) may be excluded.
- **"Candidate per quiet hour at MDE 5% / 2%"** — the number of confirmatory tests the measured σ_d and time-to-20 allow per quiet hour at each MDE ([06 §6.6](../../architecture/06-forge.md)).
- **F1-sim benefit unit** — simulated NVMe **bytes per accepted token** for `timing_blind` configurations, equal to the independent second counter, pooled token-weighted over the sealed traces, each replayed from a cold cache; baseline LRU in the same niche. Stall time is descriptive (`est`-tier). All SIMULATED and conditional on simulator fidelity until M4.
- **MDE [target]** — F1-sim: **10%** fewer NVMe bytes/token than LRU in the primary niche (the gate); 5% stall time (descriptive).

---

## 5. Metrics: primary, secondary, descriptive

- **Primary (gate inputs):**
  - share of batch (a) (testable entries) and batch (b) caught at or before the X4 declared stage (target 100%, IF-5);
  - count of counted A/A microbenchmark sessions whose superiority e-process reaches 20 within N, under R and under S (target ≤ 2 of ≥ 100 under each);
  - count of counted planted-regression sessions whose NI e-process reaches 20 within N, per level (target ≤ 2 of ≥ 100 each at 3% and 4%), with the premise check met;
  - prune-pilot audit violations (target 0; exhaustive audit of the 144-grid prune).
- **Secondary (tightening; each can make a pass amber, never a fail a pass):**
  - the pooled two-sided test of the mean symmetric-clipped A/A d over all counted microbenchmark A/A blocks at α = 0.01 [target];
  - the void rate per calibration (amber if > 10% [target]);
  - per-arm discarded-run asymmetry (exact binomial, two-sided α 0.01) and wealth-at-void skew (one-sided Mann–Whitney α 0.01) [target];
  - the stationarity positive control (≥ 9 of 10 voided [target]).
- **Secondary (reported):**
  - σ_d per run type and niche [M] — the M0 deliverable, estimated only from sessions run to their horizon;
  - time-to-pass (median, p90, share within N; censored) per run type;
  - the per-run environmental outlier rate (pilot and calibration) and the resulting P(NI within N at parity);
  - throughput (candidates/quiet hour at MDE 5% and 2%);
  - the carry-over contrast `co_BA − co_AB` with its SE;
  - the A vs A′ layout effect with its CI;
  - the kill e-process's behaviour on the planted sessions (expected: no kills at 3%/4%);
  - F1-sim best policy's bytes/token vs LRU per niche (primary gated, others descriptive), on visible and sealed traces separately (SIMULATED);
  - every calibration tally reported with and without voided sessions.
- **Descriptive:** the full e-value traces; the prune fractions (target reproduce 41/32/26/16% and 66% [RV: D3-ii]); the tombstone firing log incl. background-audit boosts and irrelevant-perturbation non-fires; the measured STREAM/NVMe profile; the quiet-hour accounting; the 06-literal scorer's statistics beside R.

---

## 6. Sample and power

- **A/A microbenchmark:** ≥ 100 counted sessions (ROADMAP §3.5). Operating characteristics are **exact** under independence: at a true per-session rate of 1% the ≤ 2/100 rule passes with 0.9206, at 5% with 0.1183, at 8% with 0.0113 [D] ([stats/ §1](../../../experiments/x4-integrity/stats/README.md)), confirming ROADMAP's 0.92 / 0.12 / 0.01 [inference]. **Independence is an assumption:** sessions share nights, thermal history and the pilot constants. With an intra-night correlation of 0.05 in 4 nights × 25 sessions, P(pass) at a true 5% rate is 0.2369 and at 8% 0.0592; in 10 nights × 10, 0.1699 and 0.0270 [D, stats/ table 1b]. The pinned schedule spreads each calibration across nights to stay near the iid figures.
- **Power of the A/A rule [S].** A 2% harness label asymmetry crosses within N in 0.20% of sessions at σ_d 2% and 50.0% at 4% (R, aGRAPA); under S, 46.3% at σ_d 4% with 2% outliers. The pooled mean test (§5) has power 0.81 / 0.77 against a 0.2% asymmetry at σ_d 2% / 4% [D].
- **Planted-regression:** ≥ 100 counted sessions per level, run to N. Simulated false-pass rates ≤ 0.70% (drafted cells) and ≤ 1.0% for R with outlier-run rates up to 10% [S].
- **End-to-end:** ≥ 20 A/A sessions per run type, to N — enough for σ_d and time-to-pass, **not** enough to test a 5% rate (P(0 of 20) at a true 5% rate is 0.358 [D]); their gates rest on the microbenchmark calibration plus per-session sentinels ([06 §6.3](../../architecture/06-forge.md), ROADMAP §3.5), which detect a 2% label asymmetry in one session only ≈ 13–14% of the time [S].
- **σ-pilot:** 480 microbenchmark A/A blocks (σ̂_d relative SE ≈ 3% under normality [D: 1/√(2·480)]) and 36 end-to-end blocks (≈ 12% [D]).
- **Planted-hack suite:** exhaustive over the 38 testable batch (a) entries; batch (b) as large as the different-family Adversary writes. a34 is planted once (one screening + one confirmatory session); P(caught) ≈ 0.98 at σ_d 2% and ≈ 0.999 at 4% [S, stats/ table 3d].
- **F1-sim:** exhaustive over the 144-candidate grid for the prune pilot, with an exhaustive audit; the benefit search is bounded by daytime CPU, proposing on visible traces, measuring once on the sealed traces.
- **Quiet hours [D from G inputs]:** ≈ 122–135 h at σ_d 2% and ≈ 325–403 h at σ_d 4%, depending on the end-to-end stopping rule ([stats/ §4](../../../experiments/x4-integrity/stats/README.md)); owner question 1.

---

## 7. Analysis procedure (deterministic script, named)

- **Binomial OC:** `experiments/x4-integrity/stats/x4_calibration.py --binomial-only`, exact rational arithmetic [D].
- **e-processes:** the Rust orchestrator computes them; the Python reference in `x4_calibration.py` (`PREREG`) must reproduce the **golden wealth path** (`--golden`) **bit for bit** ([06 §5.3](../../architecture/06-forge.md) condition 2). The pinned constants:

| Constant | Value / rule [target] |
|---|---|
| m_NI, m_kill | `0x1.e44a9a3bed663p-6` = RN(ln 1.03); `0x1.f30b2d0091d82p-6` = RN(−ln 0.97) (60-digit decimal, not a platform `log`) |
| threshold; crossing | 20.0; first block i with K_i ≥ 20.0, K_i the float64 product Π(1 + λ_j g_j) in block order, no log space |
| float rules | IEEE-754 binary64, round-to-nearest-even, operations in the written order, no FMA contraction |
| bettor | aGRAPA: μ = s1/n; var = max(s2/n − μ·μ, 1e-12); λ = min(θ, max(0, μ/(var + μ·μ))); state n = 1, s1 = g0, s2 = v0 + g0·g0; after each block K ← K·(1 + λg) with λ from the prior state, then n += 1, s1 += g, s2 += g·g |
| θ | 0.5 (superiority, NI); 0.8 (kill) |
| bet variables | superiority g = −x/c; NI g = (m_NI − x)/(c − m_NI); kill g = (y − m_kill)/(c_kill + m_kill) |
| priors | superiority x0 = −0.02; NI x0 = 0; kill y0 = m_kill + 0.02; each sd0 = clip/3; g0 = sign·(x0 − m)/scale, v0 = (sd0/scale)² |
| clips | c = max(3σ̂_d, 2m_NI); c_kill = max(3σ̂_d, m_kill + 3σ̂_d); c_run = 4σ̂_run |
| run reference (R, Rk) | the arm's running median of its own earlier runs in the session; before any, the incumbent's; before that, the pilot incumbent median |
| tail check | deny NI/superiority credit iff P(Bin(n_B, p0) ≥ k_B) ≤ 0.05; k_B, n_B pooled over the candidate's screening session(s) and the confirmatory session on the niche, evaluated once n_B ≥ N; p0 = one-sided 95% Clopper–Pearson upper bound of the pilot's slow-outlier rate per run; a run stopped at the time cap is a slow outlier |
| S1 / S2 | sentinel mean z-test, two-sided 0.01, on unflagged sentinels with σ̂_pilot; χ² variance envelope [χ²₀.₀₀₅,ₘ/m, χ²₀.₉₉₅,ₘ/m]·σ̂²_pilot on unflagged calibration + sentinel blocks clipped at c |
| S3 | two-sided Mann–Kendall at α 0.01 on each arm's per-run log-times, Hamed–Rao factor restricted to lag 1, always applied, floored at 1, after Sen-slope detrending |
| S4 | incumbent session median outside pilot grand median ± max(3·s_between, 1%) |
| load gate | 2-s CPU load < min(40%, pilot 99th percentile + 2 pp) |
| integrity tolerances | τ_clock = max(1 ms, 2 × pilot max \|Δ_h − Δ_o\|), capped at 0.1% of Δ_o; κ_post, ε_spin, ε_idle = 2 × pilot maxima; pool spin allowance `POOL_SPIN_US` = 50 µs [M, clone `model.c:58`] |
| pilot estimators | σ̂_d = pooled SD of pilot A/A d; σ̂_U = σ̂_d·√((B−1)/χ²₀.₁₀,B−1); σ̂_run = pooled within-session SD of per-run log-times |

  The fill-in amendment records each pilot-derived value. A pilot value outside its pre-stated cap (τ_clock above 0.1% of Δ_o) is a design revisit before collection, never a loosened constant.
- **Hack scoring:** each entry ships with an expected-rejection record `{hack_id, declared_stage_x4, declared_stage_m4, expected_detector, expected_fact_kind, catch_model}`; the cascade's recorded rejection stage is compared against it ([HACK-SUITE.md §2.4](../../../experiments/x4-integrity/HACK-SUITE.md)).
- **Tombstone replay:** `experiments/x4-integrity/revisit_proto.py` + `revisit_acceptance.py` parse every trigger against the [06 §7.2](../../architecture/06-forge.md) grammar (CI check) and run the firing state machine, including the six TOMBSTONES §6 entries; the M3 engine must reproduce identical firing on the signed M3 ledger (ROADMAP §3.5).
- **F1-sim:** the vendored simulator under the cascade; the MIN-bytes oracle validated against brute-force OPT before it may quarantine; the independent second byte counter checked on every `timing_blind` candidate ([F1-SIM.md §4, §4.1](../../../experiments/x4-integrity/F1-SIM.md)).

The Gatekeeper (deterministic code + Owner key) computes the verdict from this frozen record and the raw results; agents run the scripts and write the dossier, never judge (ROADMAP §1 rule 3).

---

## 8. Outcomes: pass / amber / kill / narrowing

The gate and kill are **copied from ROADMAP §3.5** and made operational per §4:

**Gate** — all required:
- 100% of both hack batches are caught at or before their declared stage (IF-5); for X4, batch (a) is its 38 testable entries, and the verdict states "caught k of 38; a22, a23, a24 excluded as not testable at X4".
- **A/A calibration (superiority null).** Across at least 100 counted identical-binary microbenchmark sessions, the superiority e-process reaches 20 in **≤ 2** of them [target], **under R and, separately, under S**. Ville's bound is 1/20 when samples are exchangeable; with identical binaries and randomised order this tests the harness's label exchangeability (owner question 8). The exact binomial rule passes a true 5% false-alarm rate with probability ≈ 0.12 and a true 8% rate with ≈ 0.01; a sound evaluator at a true 1% passes with ≈ 0.92 [inference, confirmed [D]]. (A "≤ 5 of 100" rule would pass a true 8% rate with probability ≈ 0.18.)
- **Planted-regression calibration (non-inferiority null).** `hearth-c-ref` against itself with an injected slowdown of 3% and, separately, 4%, as proportional extra work whose realised level the separate long run confirms. The NI e-process must reach 20 in **≤ 2 of ≥ 100** counted sessions per level [target], within the amber limit N, **and** the premise check must hold.
- **Time-to-pass at true parity.** The A/A sessions also run the NI e-process; its median and p90 time to 20 (censored; "> N" if beyond) are published per run type.
- End-to-end run types get **≥ 20 A/A sessions** [target]; their gates rest on the microbenchmark calibration plus the per-session A/A sentinels ([06](../../architecture/06-forge.md) §6.3).
- Throughput is published as candidates per quiet hour at MDE 5% and 2%.
- The lookahead tombstone fires only when the simulated environment gains a VRAM tier, a second drive or NVMe bandwidth above 12 GB/s. ADR-0004's revisit condition, once encoded, fires on the recorded traces and the measured policy table per niche, and the scoped verdicts match the measured winners, not a global switch to LRU. Neither fires on the pre-registered irrelevant perturbations.
- The prune pilot is reproduced with zero audit violations (41/32/26/16% per cache size and 66% jointly, simulated [RV: D3-ii]).

**Amber from the tightening secondaries (they never turn a fail into a pass):** a pooled-mean-test rejection, a void rate above 10%, a flagged discard asymmetry or wealth-at-void skew, a failed premise check, or a positive control voiding fewer than 9 of 10 sessions makes the affected calibration **amber**: find the cause, fix it, re-run the calibration on fresh sessions under this record (a deviation, §10).

**Kill.** Any accepted planted hack stops all Forge work: no Forge result counts until the evaluator is redesigned and the suite passes again. This does not kill the language. A failed A/A calibration bars every superiority gate, and a failed planted-regression calibration bars every parity gate, until the cause is fixed and the calibration passes again on fresh sessions (D0-8, D-22).

**Amber (operational, within the ROADMAP envelope).**
- If the X4 calibration runs past week 6, the **X4 verdict waits** while the other M0 verdicts do not (ROADMAP §3.7). This loosens no threshold.
- **Batch (b) cannot run same-family.** Because only Claude is available now (D0-10), the week-6 reportable gate is "100% of testable batch (a) caught; batch (b) scheduled for the D0-10 families" ([HACK-SUITE.md §3, §4](../../../experiments/x4-integrity/HACK-SUITE.md)). The X4 verdict states this limitation explicitly; it does not substitute a same-family batch for the different-family requirement.

**F1-sim Forge-benefit outcome (ROADMAP §8 M0 row, not the X4 integrity gate).** Readiness miss → no M4 campaign until fixed; benefit miss (primary niche, sealed traces) → the policy line enters M4 as a hypothesis with its campaign budget halved. A benefit on synthetic sealed traces only is reported as "SIMULATED(synthetic) benefit". An accepted planted hack is X4's HALT-F, not a Forge-benefit miss ([F1-SIM.md §7](../../../experiments/x4-integrity/F1-SIM.md)).

---

## 9. Threats to validity and how each is handled

- **The workload shares the harness's address space** (it can write `t0`, the salt, the hash). The orchestrator's out-of-process bracket, job CPU accounting and its own rehash of an output section it owns; binary T0 at M4 ([MEASUREMENT-SERVICE.md §2, §3 step 8a](../../../experiments/x4-integrity/MEASUREMENT-SERVICE.md)).
- **Work escapes the join** (OS thread pool, raw threads, work between `t1` and the hash). Thread census, post-`t1` CPU rule, output frozen read-only at `t1` (a3, a3b).
- **Non-exchangeable desktop fakes an effect.** Randomised ABBA/BAAB blocks; the trend (S3) and median (S4) voids; the per-run start-state gate and carry-over contrast; the A/A calibration tests label symmetry; the positive control proves the voids fire. Drift that interacts with a real A/B difference is not detectable by A/A sessions [known weakness]; the reported trend in A/B d is its only diagnostic.
- **Selection through voids** (void-and-re-run). Statistical voids stay in the tally; void decisions are blind to the wealth; per-attempt α charging; discard-asymmetry and wealth-at-void checks (a11b).
- **Circular constants.** Every data-dependent constant comes from the σ-pilot by a frozen rule, filled in before the first counted session.
- **The clip hides the candidate's slow tail.** The pooled tail check at 5% (residual ≈ 2–7% credit for a rare-stall candidate at σ_d 2% [S]; a34).
- **Kill test biased toward false kills.** Rk scoring in the candidate's favour; no false kills at parity up to 10% outliers [S].
- **Planted level not in the null.** Proportional extra work, the clip-bias-corrected level with a 0.25% overshoot (so the 3% calibration is at most 0.25% inside the null — stated), the separate long run and the premise check.
- **Correlated sessions.** Beta-binomial sensitivity; the randomised schedule across nights.
- **A wrong plausibility bound quarantines real wins or waves hacks through.** The MIN-bytes oracle is `validated` (exhaustive vs brute-force OPT, property tests, a second implementation) before it may quarantine, and must survive the two historical Belady counterexamples ([F1-SIM.md §4](../../../experiments/x4-integrity/F1-SIM.md)).
- **Simulator modelling errors.** The independent second byte counter; every F1-sim win is conditional on simulator fidelity until M4 (a32).
- **Held-out leakage.** The in-repo trace is visible validation only; sealed traces are unreadable to proposers or seeded after freeze (a10b).
- **The suite is circular (authors grade their own gate).** Batch (b) is written by a **different-family** Adversary after the kit is hash-frozen (IF-5); the same-family limitation is stated, not hidden.
- **The sandbox can't block network or brokers.** LPAC mandatory for untrusted workloads; positive-control network probes; broker probes; WFP/firewall + separate user; refusal table ([SANDBOX.md §3–§5](../../../experiments/x4-integrity/SANDBOX.md)). Probes are samples, not proofs [known weakness].
- **Sealed data reached through another name.** No openable path; alternate-name probes; post-session rehash (a8b).
- **System settings we must not change.** Every needed setting is a command for Pierce; the service verifies the profile hash and refuses on mismatch.
- **Grammar gap surfaced by the prototype.** Triggers whose fact arguments contain hyphens (`INV-DET-1`) do not parse under [06 §7.2](../../architecture/06-forge.md) as the prototype reads it — owner question 2.

---

## 10. Deviation and re-run policy; dependencies on D0-7, D0-9 and quiet windows

- **Hygiene voids are re-run** and do not count toward calibration tallies; **statistical voids are re-run but stay in the tally** (alarm if the tested e-process had reached 20); both count toward the void rate (D-22, [06 §6.9](../../architecture/06-forge.md)). Every tally is reported with and without voided sessions.
- **Integrity failures are never re-run silently**: in an A/A or planted session they are evaluator bugs that stop the calibration until fixed (a deviation recorded here); in a planted-hack run they are the catch.
- **The σ-pilot comes first.** Its values enter by a dated pre-data fill-in amendment before the first counted session; the planted-regression and end-to-end horizons are computed from them by the frozen rules. σ_d is never estimated from sessions stopped at an NI pass.
- **A change to a unit, threshold, sample or the kit freeze after collection has begun** is an amendment marked *post-data* (§ Amendments), with verdicts reported under both rules (M0 lifecycle, [m0/README](../README.md)).

**Dependencies.**
- **D0-7 (Forge authority; unattended runs).** X4 **promotes nothing**, so the grant signer is not on X4's path. The pilot and calibrations need **unattended measurement runs inside quiet windows**, which D0-7 governs. *Provisional, pending D0-7:* sessions are designed to run attended until D0-7 is signed; the scheduler-lock design ([MEASUREMENT-SERVICE.md §7.5](../../../experiments/x4-integrity/MEASUREMENT-SERVICE.md)) is ready for unattended runs the moment D0-7 permits. Reversible: no result depends on unattended operation.
- **D0-9 (Owner key management).** Without D0-9 there are no AUTHORITY facts, so X4's facts are **provisional** ([03 §11.3](../../architecture/03-trust.md)). *Provisional, pending D0-9:* X4 produces unsigned ledger facts and a dossier, re-signed once the key path exists. No threshold depends on signing.
- **Quiet windows (D0-8 host, D0-10 windows/budget/families).** The plan needs ≈ 122–403 quiet hours [D from G] (owner question 1). *Provisional, pending D0-10:* batch (b) waits for the families; the schedule waits for the approved windows. The data-collection start is gated on an Owner instruction or signature per the collection rule.

---

## 11. Deliverables and where they land

- `experiments/x4-integrity/DESIGN.md`, `MEASUREMENT-SERVICE.md`, `SANDBOX.md`, `HACK-SUITE.md`, `F1-SIM.md`, `TOMBSTONES.md` — the designs (revision 2).
- `experiments/x4-integrity/stats/x4_calibration.py` + `README.md` — the calibration reference: exact OC [D], the simulated e-process studies [S], quiet hours [D from G], `PREREG` constants and the golden wealth path.
- `experiments/x4-integrity/revisit_proto.py`, `revisit_acceptance.py` — the revisit prototype and its acceptance vectors (incl. TOMBSTONES §6).
- Results (on collection, under a FROZEN+SIGNED record): `experiments/x4-integrity/results/` — the signed measurement facts, the pilot fill-in, σ_d per run type/niche, the hack-suite rejection log with both counts, the tombstone firing log, the F1-sim SIMULATED benefit report (visible and sealed separately), the quiet-hour accounting, and REPORT.md with every number tagged.

---

## 12. Review log (independent reviewers, with model family)

ROADMAP asks for reviewers from a **different model family**; this setup cannot yet supply one (every agent so far is a Claude model). Until D0-10 names other families, reviews are logged as **same-family, independent-context** — weaker than the ROADMAP requirement, and the gap is visible here ([m0/README](../README.md)).

| Date | Reviewer (lens) | Family | Scope | Findings (major / minor) | Accepted | Rejected |
|---|---|---|---|---|---|---|
| 2026-10-16 | Reviewer 1 (evaluator integrity, adversarial: clock, join, sandbox, sealed data, hack coverage) | Claude (same family as author; independent context) | all X4 files and this record | 17 (12 / 5) | 17 | 0 |
| 2026-10-16 | Reviewer 2 (statistics and calibration: e-processes, tallies, power, quiet hours) | Claude (same family as author; independent context) | all X4 files and this record | 19 (10 / 9) | 19 | 0 |
| | **Total** | | | **36 (22 / 14)** | **36** | **0** |

**Rejected findings:** none. Every finding was checked against the sources before acceptance — the Hearth clone at b5d3f14 (`platform_win.c:212`, `:633`, `:653`, `platform_posix.c:482`, `api.c:119–128`, `model.c:58`, the tracked trace), ROADMAP §1, §3.5, §10, 06 §5–§6, COST.md §1.4, and a re-run of revision 1's script, which reproduced every number the reviewers quoted (sha256 `d638ebbc…`, 20.2 CPU-s). One local check was inconclusive: the `-LocalUser` parameter format could not be confirmed from this laptop's PowerShell help (no description installed); the fix was adopted with the positive-control probe as the real check.

**Accepted with a modified fix (7):**
- R1-2 (join completeness): the allowed set is "threads created through the registered `hx_thread_create` wrapper, plus threads that existed before `t0`" rather than "harness + parked pool workers", because a fresh Windows process may still hold the loader's worker threads [inference]; the CPU rule allows Hearth's 50 µs pool spin window.
- R1-11 (simulator exploit): a32 plants a byte-*counting* gap; the suggested warm-start VRAM-slab bug corrupted the Belady *bound* and is already F1-SIM §4's acceptance test.
- R2-3 (A/A power), fix (4): the amber second session is defined as a new test for superiority/NI, so the longest single test is N, which the A/A sessions cover; running them to 2N is owner question 9 with its cost.
- R2-6 (tail check): simulation showed the check as literally specified barely bites (0.130 → 0.110 credit); pooled with screening at a 5% level it reaches 0.017. The 5% level goes beyond 06 §6.2's 1% and is part of owner question 4.
- R2-9 (planted regression): acceptance uses a consistency check on the separate long run plus a pooled premise check, with a 0.25% overshoot, instead of a one-sided LCB on the long run alone (to accept a level 0.5% above the boundary with probability 0.95 at σ_d 4%, that needs ≈ 1,000 blocks per level [D: ((2.326 + 1.645) · 0.04 / 0.005)² ≈ 1,009]).
- R2-13 (stationarity tests): the trend test uses the lag-1-restricted Hamed–Rao factor, because the full correction was liberal in simulation (10.0% vs ≈ 2% nominal); it is not run on the sentinel d (conditionally symmetric under randomisation); n_cal stays 2 with the variance envelope pooled over calibration and sentinel blocks.
- R2-11 (p90 censoring): Kaplan–Meier censoring with "> N" is adopted; running the A/A NI arm to 4n is offered as owner question 9 rather than mandated.

**Disposition of every finding** (R = reviewer, numbered in the order received; "where" = the file and section that now carries the fix):

| # | Severity | Finding | Where fixed |
|---|---|---|---|
| R1-1 | major | in-process candidate shares the clock's address space; a5 had no X4 detector | MEASUREMENT §2, §3 step 8a; HACK-SUITE a5, §4.1 |
| R1-2 | major | join list incomplete; work after `t1` before the hash | MEASUREMENT §3 step 6; HACK-SUITE a3b |
| R1-3 | major | black-hole network probe passes on an open machine | SANDBOX §5 item 3 |
| R1-4 | major | no defence against brokering through out-of-job processes | SANDBOX §3.1, §4, §5 item 4; HACK-SUITE a6b |
| R1-5 | major | sealed data reachable by other names; degraded mode uses the Owner's token | SANDBOX §2.1, §5 item 5; HACK-SUITE a8b |
| R1-6 | major | no fresh scratch per run; cross-run carry-over | MEASUREMENT §3 step 0, §4.1; HACK-SUITE a15b, a15c |
| R1-7 | major | no CCD pinning / affinity-priority control | MEASUREMENT §7.6, §5.2; SANDBOX §2; HACK-SUITE a31 |
| R1-8 | major | void-and-re-run as outcome-dependent selection | MEASUREMENT §5.3, §8.6; §4, §10 here; HACK-SUITE a11b |
| R1-9 | major | loss scoring anti-conservative for the kill; biases A/A | MEASUREMENT §8.1, §8.2, §8.4; stats §3b, §3c |
| R1-10 | major | "sealed" traces are in a readable repo | F1-SIM §7.2; §2 here; HACK-SUITE a10b |
| R1-11 | major | no check of the simulator's own byte counter | F1-SIM §4.1, §6, §7.3; HACK-SUITE a32 |
| R1-12 | major | detectors that do not exist at X4 | HACK-SUITE §4.1; §4, §8 here |
| R1-13 | minor | MXCSR checked on one thread only | MEASUREMENT §3 step 3; HACK-SUITE a9 |
| R1-14 | minor | child environment unspecified | MEASUREMENT §3 step 0, §5.2; §2 here; HACK-SUITE a33 |
| R1-15 | minor | "candidate arm runs first" contradicts randomised order | MEASUREMENT §3 step 0 |
| R1-16 | minor | firewall `-LocalUser` format | SANDBOX §3.2 |
| R1-17 | minor | "ABAB" heading vs ABBA/BAAB body | MEASUREMENT §4; §4 here |
| R2-1 | major | survivorship of statistically voided calibration sessions | MEASUREMENT §5.3; §4, §5, §10 here |
| R2-2 | major | circular, data-dependent constants | MEASUREMENT §5.4; §3, §7 here |
| R2-3 | major | A/A power; tests label symmetry not drift; AR(1) sentence wrong | MEASUREMENT §8.2; stats §2, §3b; §5, §6 here; owner Q8, Q9 |
| R2-4 | major | sentinel e-process can never reach 20 | MEASUREMENT §5.3 S1/S2; stats §3e; TOMBSTONES §6 |
| R2-5 | major | kill unreachable at σ_d 2% | MEASUREMENT §8.4; stats §3c; owner Q5 |
| R2-6 | major | tail check never specified | MEASUREMENT §8.7; stats §3d; HACK-SUITE a34 |
| R2-7 | major | quiet hours misread against ROADMAP §10 | MEASUREMENT §10; stats §4; owner Q1 |
| R2-8 | major | outlier-rate grid too narrow | stats §3a; MEASUREMENT §8.4; owner Q6 |
| R2-9 | major | planted regression under-specified | MEASUREMENT §8.3; §3, §4 here; TOMBSTONES §6 |
| R2-10 | major | which scorer drives the gate | MEASUREMENT §8.1; §4, §7 here; owner Q4 |
| R2-11 | minor | p90 censored; stopping at NI pass biases σ̂_d | MEASUREMENT §8.4, §10; §4 here; owner Q1, Q9 |
| R2-12 | minor | binomial OC assumes independence; counted set undefined | stats §1; §4, §6 here; owner Q3 |
| R2-13 | minor | trend tests unspecified; n_cal = 2 envelope | MEASUREMENT §5.3 S2/S3; stats §3f; TOMBSTONES §6 |
| R2-14 | minor | carry-over not addressed | MEASUREMENT §4.1; HACK-SUITE a15c |
| R2-15 | minor | wealth path not pinned enough for a differential check | MEASUREMENT §8.6; stats §0, §5; §7 here |
| R2-16 | minor | loss scoring anti-conservative for the kill | as R1-9 |
| R2-17 | minor | two margins without stated reason | MEASUREMENT §8.3; §4 here |
| R2-18 | minor | F1-sim benefit criterion not decidable | F1-SIM §5, §7.2; §4 here |
| R2-19 | minor | summary numbers do not match the script output | stats/README (regenerated); x4_calibration.py docstring; DESIGN |

---

## 13. Signature block

```text
Owner: ______________________   Date: __________
Signs the record frozen at commit: ________
```

**Owner questions raised by X4 (for the signed record; none changes a ROADMAP threshold):**
1. **Quiet-hour budget.** ROADMAP §10's M0 line pairs ≈ 60 h with σ_d 2% and ≈ 215 h with σ_d 4%. X4 alone exceeds it at **both** ends: the ROADMAP-comparable part of the plan (A/A, planted, end-to-end A/A, plus X3's plan figure) is 111.2 h (+85%) and 368.8 h (+72%); the full plan with pilot, long runs, A/A′ and positive control is ≈ 122–135 h and ≈ 325–403 h [D from G]. A reconstruction with n blocks per session instead of N gives 60.9 / 223.4 h [D] (COST.md §1.4: 60.3 / 221.0 h), so the likely cause is that §10 used n while §3.5 requires N = 2n [inference]. Should the §10 line be revised in a signed record before collection? Should the end-to-end A/A sessions stop at the first NI pass (saves 13.0 h / 78.1 h [D], but σ̂_d from such sessions can be biased low, so σ_d would then come only from sessions run to N), and is the end-to-end count capped at 20 regardless of σ_d? D-22 fires if the planned hours exceed the agreed windows.
2. **Trigger grammar gap.** Fact arguments containing hyphens (`hearth.invariant_hash(INV-DET-1)`) do not parse under [06 §7.2](../../architecture/06-forge.md) as written. Should invariant ids be quoted strings, or should the grammar admit a hyphenated identifier class for known-id namespaces? ([TOMBSTONES.md §4.1](../../../experiments/x4-integrity/TOMBSTONES.md); X4 did not change the normative grammar.)
3. **A/A rule leniency, both ways.** The ≤ 2/100 rule is *stricter* than validity requires (it fails an e-process exactly at Ville's 5% bound with probability 0.88 [D]) and *lenient* relative to the ≈ 0–0.4% false-alarm rate a sound evaluator shows in simulation (it passes half the time at a true 2.7% [D]); with sessions correlated within nights it is more lenient still (0.24 at 5% for 4 nights × 25 [D]). Confirm the design point, or tighten before data.
4. **06 §6.2 (normative), two points.** (a) The literal block clip scores large true improvements as losses (a 20% improvement never reaches 20 within 400 blocks [S]); X4 proposes the run-level R scorer as the single gate scorer, provisional pending your decision. (b) The mandatory tail check, as literally written, barely bites (credit for a rare-stall candidate falls 0.130 → 0.110 [S]); X4 proposes pooling with screening runs, waiting for N runs, and a one-sided 5% level (stricter than 06's 1%), which gives 0.017 at a parity cost of ≤ 0.007 [S]. Confirm, or amend 06.
5. **Kill reachability and the amber session.** At σ_d 2% a kill within one N-session is essentially unreachable even with the revised constants (0.048 at a 10% regression [S]); within the two N-sessions ROADMAP §1 rule 4 allows, it reaches 0.992 [S] — X4 therefore continues the kill e-process across both sessions when the binary is unchanged, while treating the second session as a new test (new α_i) for superiority and NI. Confirm this reading of "one more N-hour session", or choose another (e.g. a longer N for kills).
6. **Outlier rate.** P(NI reaches 20 within N at true parity) falls to 0.685 at a 2% and 0.311 at a 5% outlier-run rate (σ_d 2%) [S]. If the pilot's measured rate puts it below 0.8, should N, the clip rule and the throughput figures be revised in a signed record before M4?
7. **Untestable extras.** Confirm that a22, a23 and a24 (none ROADMAP-named) are excluded from the X4 denominator and re-declared at M2/M4, with both counts in the verdict.
8. **ROADMAP §3.5 wording.** "This tests exchangeability on this desktop": with identical binaries and randomised order the A/A rule tests the harness's label exchangeability, not drift that interacts with real A/B differences. Should the sentence be narrowed?
9. **A/A horizon.** Running the microbenchmark A/A sessions to 2N (so the parity p90 is observable rather than "> N", and the A/A null is exercised longer) adds 13.3 h at σ_d 2% and 48.9 h at σ_d 4% [D]. Adopt or not?

## Amendments (appended, dated)

_None yet._
