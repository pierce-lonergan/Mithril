# X4-calibration: A/A, planted-regression and end-to-end A/A calibrations of the measurement service
Status: DRAFT

ROADMAP anchor: [§3.5](../../ROADMAP.md#35-x4-evaluator-integrity-kit-weeks-06) (A/A calibration, planted-regression calibration, time-to-pass, end-to-end A/A, throughput); §1 rule 4 (non-inferiority, N, the amber second session, the kill); §3.7 (X4 "waits"); §4 (X4 row); §10 (quiet hours); DR-018; D-22; [06 §6](../../architecture/06-forge.md). Design: [MEASUREMENT-SERVICE.md §4, §5.3–§5.4, §8, §10](../../../experiments/x4-integrity/MEASUREMENT-SERVICE.md) and [stats/](../../../experiments/x4-integrity/stats/README.md). Split out of the [X4-integrity DRAFT](X4-integrity.md) (revision 2: §3 calibration arms, §4–§8 calibration clauses, owner questions 1, 3–6, 8, 9). Pilot inputs: [X4-noise-pilot](X4-noise-pilot.md) (revision 5).

This is a **DRAFT** (revision 2, 2026-10-23, written by the x4cal track, a Claude agent, after one same-family, independent-context review of revision 1 with 12 findings, §12; **revision 2 itself is not yet reviewed**). Under the [collection rule](../README.md#pre-registration-lifecycle-roadmap-1-rule-1-d0-12) **no data may be collected under it**, the separate long runs included, until it is FROZEN and SIGNED (D0-12; chat signature as the interim form, OWNER-ANSWERS batch 3). It may make a ROADMAP threshold more precise (a unit, a counting rule, a sample), never loosen it; where it and ROADMAP §3.5 differ, ROADMAP wins. Where it and the X4-integrity DRAFT differ on a calibration clause, this record governs the calibration and the difference is listed in §10.3. Evidence tags: **[M]** measured, **[D]** derived, **[S]** simulated, **[G]** judgment, **[inference]**, **[target]**. Owner decisions are Pierce's and are marked *provisional, pending …*; rows adopted under his written delegation cite [DELEGATED.md](../DELEGATED.md). Notation: **L** is the horizon in A/B blocks (§4); **ℓ** ∈ {3%, 4%} is a planted level.

**Freeze gate.** This record may be frozen only when all six hold:
1. Pierce has answered **C07**, both points (§3a; not delegable, DELEGATED P23), from a packet that quotes §3a's current numbers (§10.3 item 8).
2. Every other §13 field holds his answer or the value registered for a blank.
3. **One** statistics-reference revision is committed that implements all four C07 combinations (a-R or a-L with b-P or b-L) behind a flag; prints golden wealth paths for R, L06, S and Rk, test vectors for T-pooled and T-06, and at least one planted-session golden vector with opening and sentinel blocks under §4's run-reference rule; folds in this record's two scratch studies (`c07_branches.py`, `x4cal_r2.py`; §2), so that every [S] number of §3a and §6.1 is re-tagged to its SHA-256; and has that SHA-256 written into §2. It is due before sitting 2 (§10.2), so that the freeze then needs only Pierce's answer and that SHA.
4. A same-family, independent-context review of the text to be frozen is logged in §12.
5. X4-noise-pilot §3a registers the same C29 value as this record (ALL if blank), and its §7(b) uses N_rt = L_rt by that value and this record's long-run size (§10.3 items 1 and 2).
6. X3's record agrees with this record on the run type (the §2 row, priority class included) and on §4's coverage rule, or it declares its G2 and G3 passes PASS-PROVISIONAL with respect to this calibration (§10.3 item 3).

It must be FROZEN **before the first noise-pilot night** (X4-noise-pilot freeze gate and §10), because the pilot's σ̂ and outlier rates are data that bear on C07 and C29: an answer given after the first pilot night is post-data. Under DELEGATED P1 the freeze may land between sittings.

**Where it stands** [M, 2026-10-23, revision 2]. Not freezable. Condition 1: C07 is open (sitting 2, Sun 2026-10-25, at the earliest; [PACKET](../sittings/2026-10-25/PACKET.md) item 4 still quotes older numbers, §10.3 item 8). Condition 3: the reference at revision 2 implements branch (a-R, b-P) only, and its golden path covers R and Rk only (§2). Conditions 5 and 6: the noise pilot registers BLOCKS for C29; X3 runs `x3_bench` at HIGH priority and carries wealth across its two N-sessions. Condition 4: revision 2 is unreviewed. Nothing has been collected under it.

---

## 1. Assumption under test, and what follows if it is false

**Assumption.** On the quiet-machine profile the X4 measurement service's anytime-valid e-processes hold their pre-registered error behaviour on `hearth-c-ref`: (i) the **superiority null** (A/A: identical binaries, randomised ABBA/BAAB order) is not rejected more often than the ROADMAP rule tolerates, which tests the harness's **label symmetry** ([MEASUREMENT §8.2](../../../experiments/x4-integrity/MEASUREMENT-SERVICE.md), X4 owner question 8, OWNER-QUEUE D25); (ii) the **non-inferiority null** (a planted, realised slowdown of 3% and of 4%) is not rejected more often than the ROADMAP rule tolerates, which A/A sessions cannot test (ROADMAP §1 rule 4). It also produces the M0 deliverables that size every later parity budget: σ_d per run type and niche, time-to-pass at true parity, and throughput (ROADMAP §3.5, 06 §6.6).

**If it is false.** A failed A/A calibration bars every superiority gate, and a failed planted-regression calibration bars every parity gate, until the cause is fixed and the calibration passes again on fresh sessions (ROADMAP §3.5 kill; D0-8; D-22). X3's parity verdict stays PASS-PROVISIONAL or becomes barred (C25, answered 2026-10-23, OWNER-ANSWERS batch 3 / R8; [X3 record §7.6](X3-generator.md)). The language is not killed (ROADMAP §4 X4 row). How a failed calibration maps into the M0 verdict (a bar beside the rows, PLAN §3.8, DELEGATED P8) is the M0-verdict record's; this record reports the state of each calibration (§8).

---

## 2. Inputs pinned (sources, commits, versions, machines)

- **Reference binary.** `hearth-c-ref` stand-in: a clean build of the Hearth clone at `b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220`, built on D: (DELEGATED P20, adopted 2026-10-23; PLAN §3.4), by the exact commands of [X4-noise-pilot §2](X4-noise-pilot.md#2-inputs-pinned-sources-commits-versions-machines) (`build_pilot.bat`, MSVC `cl` 19.44.35229, CMake 4.4.3, Ninja 1.12.1, Rust 1.91.1 for the service) [M there]. **The calibration runs the very files the pilot ran**: `x4harness_hearth.exe`, `x4svc.exe` and `x4sb_probe.exe` with the SHA-256 values of the noise-pilot pre-night amendment. The MSVC build is not bit-reproducible [M, IMPLEMENTATION.md], so a rebuild is a new pin; a new pin before the first counted session is a pre-data amendment and needs a new noise pilot for that binary (σ̂ is per binary); after it, it is a restart (§10.1).
- **A′, the layout arm.** The same sources and flags, linked with the harness's link inputs in a permuted order: a Fisher–Yates shuffle (from the last index down) driven by SplitMix64 seeded with the first 16 hex digits of SHA-256(`"X4-calibration/A-prime/"` ‖ the freeze-commit hash as 40 lowercase hex digits), with unbiased bounded draws as in the pilot's §2. Its SHA-256 must differ from A's and its output hash must equal A's golden; otherwise A′ is a design revisit and is not run. Pinned in fill-in part 1 (§ Amendments).
- **Run types.** Exactly the two rows of the [X4-noise-pilot §3](X4-noise-pilot.md#3-arms--configurations) table, field by field: `mb-q4-avx512` (workload `mb_q4_avx512`, `x3_bench`'s shape under C25; K, LP `p`, job mask, 60 s time cap, 2 GiB job memory, environment block, priority class) and `e2e-decode` (N = 2,048 decode tokens [target], the real Qwen3-30B-A3B Q4 file read-only under C02, the C01 placement `0xbfffffff` with `HEARTH_THREADS` 16, `HEARTH_IO_THREADS` 8, `HEARTH_CACHE_GB` 8, cold direct I/O, the time cap max(600 s, 3 × t_run,plan), 24 GiB). C01, C02 and C25 were answered 2026-10-23 with their defaults (OWNER-ANSWERS batch 3, R8; *provisional, pending ratification at sitting 2*). Any field that differs from the pilot's row means the pilot does not cover it, and a new pilot is needed for that row.
- **Priority class.** `NORMAL_PRIORITY_CLASS`, the same as the pilot (MEASUREMENT §7.6 [target]); *provisional, pending Pierce's answer* (§13; PACKET item 5). A HIGH answer before freeze changes this line, the pilot's §3 row and X3's §8.2 together; after the first pilot night it needs a new pilot.
- **Machine and profile.** The desktop DESKTOP-8RS9J1J (Ryzen 9 9950X, 64 GB DDR5, Samsung 990 PRO, Windows 11 Pro 10.0.26200) [M, X4-noise-pilot §2], clock on US Eastern time [M there]; the pins files Pierce makes from the launch context (X4-noise-pilot §11, PRE-NIGHT A7). A profile mismatch refuses the night or voids the session as in the pilot (§4, failure kinds).
- **Configuration.** A calibration configuration derived from the filled `pilot.cfg`, changing only what this record adds (the calibration schedule, the per-arm K′, the opening calibration and sentinel blocks with their separate run-reference state (§4), the long runs, the positive-control ramp, A′, grade `CALIBRATION`), pinned by its canonical SHA-256 (`x4svc config-hash` rule, X4-noise-pilot §7) in fill-in part 1. The driver mode that runs it does not exist yet (§10.2).
- **Pilot-derived constants.** From the X4-noise-pilot **post-pilot amendment**, by its frozen §7(a) rules: σ̂_d, B, σ̂_U, n, σ̂_run, p0, the pilot incumbent median per run type, the S4 grand median and s_between, the load-gate threshold, the §4.1 start-state envelopes, and every integrity tolerance (2 × the pilot maxima, under the §3 ceilings). The pilot's §7(a) also computes n, c, c_kill and c_run, by the same rules as §7 here; this record adds L and B_lr (§4) and, under tail branch (b-L) only, p_blk (§3a).
- **Statistics reference.** [`experiments/x4-integrity/stats/x4_calibration.py`](../../../experiments/x4-integrity/stats/x4_calibration.py), revision 2, SHA-256 `6ac99140317716b378bdfda5487d95ea8186d6f7ba2a99bef484add33fae30f0` [M, re-hashed 2026-10-23]. It implements branch (a-R, b-P), and the 06-literal scorer as a descriptive statistic; it does **not** implement the 06-literal tail check T-06, and its golden wealth path (`--golden`) covers R and Rk only, not S or L06, and no planted session [M, `golden_path`, read 2026-10-23]. **Re-pinned at freeze** at the one revision that freeze-gate condition 3 describes. This record's [S] numbers beyond the reference's tables come from two scratch studies that import revision 2 unchanged; they are kept in the x4cal track's scratch directory, not in the repository, and must be folded into the reference before freeze (§10.2):
  - `c07_branches.py` (the C07 branches of §3a): SHA-256 `c36fc1b42fbe900a538f1b6b708816522a8ab13279750578fb74f080184f5ae8`, seed 20261023, 30.0 CPU-s, CPython 3.12.10 on the laptop [M]; output SHA-256 `3e6b92fe7e3470967c381c0370ce88b1b6c2f097e0e8a281a8a348fb1eea9b4a`.
  - `x4cal_r2.py` (revision 2: horizons 2n–6n, the run-reference rule, the long run and the premise check, quiet hours): SHA-256 `76f0f657102227cb9a2e1f5cf6082acf2bc3e65ad838ecd7fdb480d23490d5e8`, seed 20261023, 45.8 CPU-s, CPython 3.12.10 on the laptop [M]; output SHA-256 `a762ad9c707442deb2a247dee5af2dfb443e2e5e7e92eef283b96595da6f9f32`.
- **Schedule seed.** `seed` = the first 16 hex digits of SHA-256 of the ASCII bytes `"X4-calibration"` followed by the freeze-commit hash (40 lowercase hex digits). The slot list of §6.2 is shuffled once with it by the pilot's §2 procedure (Fisher–Yates, SplitMix64, unbiased bounded draws); each session's ABBA/BAAB draws and sentinel positions use SplitMix64 seeded by the first 16 hex digits of SHA-256(`"X4-calibration/session/"` ‖ seed hex ‖ `"/"` ‖ slot id), with the pilot's order mapping (`scheduler::next_order`). The schedule is drawn before the first session and printed in fill-in part 1.

---

## 3. Arms / configurations

Every calibration runs on the two pilot run types of §2, inside quiet windows (23:00–07:00 PT, D0-10d, *provisional, pending ratification*), unattended (D0-7a = YES, R8), at the nights-per-week rate the noise pilot's §7(b) computes and Pierce re-signs (DELEGATED P7). Both arms are trusted C, so the sandbox runs in its degraded-job-only mode, as in the pilot. No calibration session ever stops at a crossing: every e-process runs to the horizon L (§4) and its crossing block is recorded (DELEGATED P21).

| Calibration | Arm A | Arm B | Run type | Units | Blocks per unit | Role |
|---|---|---|---|---|---|---|
| **A/A** (superiority null) | pinned harness, K calls | the identical binary, K calls | `mb-q4-avx512` | 100 counted sessions (≥ 100, ROADMAP) | L A/B blocks | **gate** |
| **Planted 3%** (non-inferiority null) | K calls | the identical binary, **K′₃** calls (§4) | `mb-q4-avx512` | 100 counted sessions | 2 opening A/A calibration blocks, then L A/B blocks and ⌈L/6⌉ A/A sentinel blocks in random order | **gate** |
| **Planted 4%** | K calls | K′₄ calls | `mb-q4-avx512` | 100 counted sessions | as planted 3% | **gate** |
| Separate long run, per level ℓ | K | K′_ℓ | `mb-q4-avx512` | 1 accepted run, at most 3 attempts | B_lr = max(256, ⌈(2.576·σ̂_d/0.0025)²⌉) A/B blocks [G]; may span windows (§4) | confirms the realised ratio; fixes K′_ℓ (§4) |
| **End-to-end A/A** | pinned harness, N = 2,048 tokens | identical | `e2e-decode` | 20 counted units (≥ 20, ROADMAP) | L A/B blocks; a unit may span windows (§4) | σ_d, time-to-pass; not a false-alarm gate |
| A/A′ layout | K | A′ (§2), K | `mb-q4-avx512` | 20 sessions [target] | L | descriptive |
| Stationarity positive control | K_j ramp (§4) | identical binary, the same K_j ramp | `mb-q4-avx512` | 10 counted sessions [target] | L, fixed AABB order | ≥ 9 of 10 must void (tightening) |

**Changed from the X4-integrity DRAFT (listed again in §10.3):** the positive control plants its drift as a deterministic work ramp instead of a "planted heater ramp calibrated in the pilot" (the pilot has no heater step [M, X4-noise-pilot §3–§7], and a heater process or thread would itself trip the Mithril-image, load and thread-census rules [inference]); the horizon is L blocks, which depends on C29 (§4); an end-to-end A/A unit may span windows; e2e is one run type at M0 (later end-to-end run types need their own ≥ 20 A/A units before their stage's pre-registration); the separate long run confirms the realised ratio on the raw d and is sized by σ̂_d (X4-integrity: 256 blocks on the scored x); the premise check is two-sided (an upper bound on the realised d is added).

The **planted mechanism** is proportional extra work of the same kind: arm B runs K′ matvec calls where A runs K (ROADMAP's "calibrated spin", made precise; a fixed-cycle busy loop is rejected, TOMBSTONES §6). The output Y is the same whatever the call count, so the output hash equals the golden in both arms. A/A′ measures layout noise that identical binaries cannot show; it is descriptive.

### 3a. C07: the gate scorer and the tail check (Pierce's choice; both branches fully specified)

C07 amends normative [06 §6.2](../../architecture/06-forge.md), which governs every milestone, and is **not delegable** (DELEGATED P23; OWNER-QUEUE C07, class B). This record registers no default: it does not freeze until Pierce answers. Point (a) and point (b) are separable, and all four combinations are fully specified; PACKET item 4 offers three of them (CONFIRM both = (a-R, b-P); "(b) only" = (a-L, b-P); "keep 06 literally" = (a-L, b-L)), and (a-R, b-L) is admissible too. **Recommendation** (X4's provisional default, P23): CONFIRM both. Whichever he picks becomes the text at freeze; the other branch stays here marked "not adopted".

**What does not depend on C07 (both branches).** The clip c = max(3σ̂_d, 2·m_NI) (06 §6.2 has each slot fix c before collection, "for example" from the A/A 99th percentile; this rule is the pre-registered c in every branch); the S statistic x = clip(d, −c, c), which the A/A gate must also pass; the kill e-process and its Rk scorer (06 §6.2 does not define a kill; ROADMAP §1 rule 4 does); the run-reference rule of R and Rk (only A/B-block runs, §4); the bettor and every constant of §7; the horizon L; the separate long run and premise part P2, which use the raw d (§4); the counted sets; the rule that **no calibration tally applies the tail check** (each tally counts e-process crossings, which ROADMAP §3.5 names; a tail denial could only hide a crossing, so applying it would loosen the tally). Every session computes **every** scorer (R, L06, S, Rk); only the chosen one drives a gate, the other is reported as descriptive, and two scorers never jointly pass a gate (no "either passes").

**Point (a): the gate scorer of superiority and non-inferiority.**

| | (a-R) CONFIRM: run-level R | (a-L) KEEP 06 §6.2: the literal block clip (L06) |
|---|---|---|
| Outlier unit | a **run** that deviates from its own arm's running median (earlier A/B-block runs of this session; before the arm has any, arm A's; before that, the pilot incumbent median; §4) by more than c_run = 4σ̂_run; a run stopped at the time cap is an outlier | a **block** with \|d\| > c; a block holding a run stopped at the time cap is an outlier block |
| Score x | a block holding an outlier run: **+c**; otherwise clip(d, −c, c) | outlier block: **+c**, whichever arm was slow; otherwise d |
| Planted level μ*_ℓ (true mean log-ratio at which the estimand equals log(1 + ℓ), d ~ N(μ, σ̂_d²), before the +0.25% overshoot) | E[clip(d, −c, c)] = μ[Φ(b) − Φ(a)] + σ̂_d[φ(a) − φ(b)] + c[1 − Φ(b)] − c·Φ(a) | E[x] = μ[Φ(b) − Φ(a)] + σ̂_d[φ(a) − φ(b)] + c[1 − Φ(b) + Φ(a)] |
| | with a = (−c − μ)/σ̂_d, b = (c − μ)/σ̂_d; the root by 100 bisection steps on [log(1 + ℓ), log(1 + ℓ) + 0.05] | same |
| A/A gate passes iff | ≤ 2 of 100 under R **and** ≤ 2 of 100 under S | ≤ 2 of 100 under L06 **and** ≤ 2 of 100 under S |
| Planted level μ*_ℓ, premise part P1, time-to-pass, throughput | on R's x | on L06's x |

The separate long run and premise part P2 use the raw d in both branches (§4). The two planted levels differ by at most 2.2 × 10⁻⁵ in log-ratio at σ_d 2–4% [D, `c07_branches.py`], because at μ ≈ 0.03 the literal rule's lower tail (d < −c) has probability ≤ 10⁻⁴.

**Point (b): the tail check (06 §6.2's mandatory slow-tail rule).**

| | (b-P) CONFIRM: pooled, one-sided 5% (T-pooled) | (b-L) KEEP 06 §6.2: block count at the crossing, one-sided 1% (T-06) |
|---|---|---|
| Counted | k_B = B's slow outlier **runs** by R's run rule (a capped B run counts), n_B = B's A/B-block runs (§4) | k_blk = the confirmatory session's slow outlier **blocks**: d > c, or a block holding a B run stopped at the time cap; n_blk = its scored A/B blocks |
| Pooled over | the candidate's screening session(s) and the confirmatory session on that niche | the confirmatory session only |
| Evaluated | once, at the later of the crossing and the first block at which n_B ≥ L (the session continues past the crossing until then) | once, at the crossing block |
| Null rate | p0 = one-sided 95% Clopper–Pearson upper bound of the pilot's slow-outlier rate per run (X4-noise-pilot §4, R replay) | p_blk = the pilot's point estimate, per run type, of the one-direction A/A block rate: (counted pilot blocks with d > c, a block holding a capped B run counting as d > c) ÷ (counted pilot blocks), c from §7 |
| Deny credit iff | P(Bin(n_B, p0) ≥ k_B) ≤ 0.05 | P(Bin(n_blk, p_blk) ≥ k_blk) ≤ 0.01 (with p_blk = 0, any slow outlier block denies) |

In both, the check only removes credit and spends no α. In a calibration session there is no screening session, so T-pooled pools that session alone. Its only uses here are the "credited" time-to-pass share (§5) and the tail facts of each session; it never enters a tally.

**What each branch does, simulated** [S unless marked; `c07_branches.py` (aGRAPA, 4,000 null sessions or 1,000 per cell) and the reference's tables 2e, 3a–3d; outlier runs 10–15% slow in either arm; σ_d and N as in the reference (N = 2n: 12 at σ_d 2%, 44 at 4%); §6.1 gives the A/A and planted rows at 3n, 4n and 6n]:
- **Superiority power** (the reason for point (a)): under L06 a true 20% improvement never reaches 20 within 400 blocks (share 0.000 at σ_d 1%, 2%, 4%), and a 5% improvement at σ_d 2% needs a median of 155 blocks against 10 under R [S, reference table 2e].
- **A/A false alarms within N = 2n** (no asymmetry, outlier-run rates 0–10%): R ≤ 0.0015, L06 ≤ 0.0015, S ≤ 0.0043. Both branches sit far inside the ≤ 2/100 rule.
- **Planted 3% and 4%, NI reaching 20 within N = 2n at each branch's own level + 0.25%** (outlier-run rates 0 and 2%): R ≤ 0.0013, L06 ≤ 0.0022.
- **NI within N at true parity** (time-to-pass share), σ_d 2% / outlier-run rate 0, 1%, 2%, 5%, 10%: R 0.952, 0.816, 0.658, 0.345, 0.053; L06 0.950, 0.876, 0.813, 0.576, 0.331. At σ_d 4%: R 0.980, 0.944, 0.913, 0.792, 0.612; L06 0.979, 0.956, 0.945, 0.890, 0.764. L06 holds parity power better under environmental outliers, because R loss-scores a block when any of its four runs is an outlier.
- **Rare-stall credit** (share of sessions whose NI crossing within N is credited; B only, 15% of runs 30% slow, true mean log-ratio 0.039 > m_NI), σ_d 2%: no check 0.127 (R) / 0.144 (L06); T-pooled 0.011 / 0.010; T-06 0.078 / 0.096. 10% of runs 50% slow: T-pooled 0.073 / 0.055; T-06 0.221 / 0.213. At σ_d 4% every such case is ≤ 0.020 under T-06 and ≤ 0.011 under T-pooled, except 5% of runs 30% slow (T-pooled 0.161 / 0.170, T-06 0.261 / 0.298). **Cost at parity** (no outliers): T-pooled 0.942–0.980 credited, T-06 0.943–0.968, against 0.947–0.980 uncredited.
- **So neither point moves one way only.** (a-R) makes superiority reachable (a loosening for superiority claims) and spends parity power under outliers; (a-L) keeps superiority nearly unreachable for large true effects. (b-P) leaves less rare-stall credit than (b-L) at σ_d 2% (0.010–0.011 against 0.078–0.096 for 15% of runs 30% slow; 0.055–0.073 against 0.213–0.221 for 10% of runs 50% slow) and costs less parity power at σ_d 4%. No ROADMAP threshold moves in any branch (e ≥ 20; ≤ 2/100).

**Implementation each branch needs before freeze or collection** (§10.2): (a-L) the Rust `Lit06` scorer must score a block with a capped run as +c (today it returns before reading the capped flags [M, `eprocess.rs` `try_score`, 2026-10-23]), and the reference must print L06 golden wealth paths; (b-L) the T-06 counter, p_blk in the pilot estimator's output or in this record's judge, and reference vectors; either way, the Rust e-process must reproduce the chosen branch's golden paths bit for bit, the planted-session vector of freeze-gate condition 3 included.

### 3b. Owner answers and adopted DELEGATED rows this record applies

| Item | Source | What it fixes here |
|---|---|---|
| C01 placement, C02 model file, C25 x3_bench, D0-7a unattended | OWNER-ANSWERS batch 3 (R8), *provisional, pending ratification at sitting 2* | §2 run types; unattended windows; the microbenchmark is `x3_bench`'s shape |
| C05, stopping part: A/A **to the horizon**, never stopped at an NI pass, micro and e2e | DELEGATED **P21** (adopted 2026-10-23) | §3, §4; the micro 2L option and the ROADMAP §10 revision stay Pierce's (§13) |
| C06: the ≤ 2/100 A/A rule, confirmed | **P22** | §8 gate |
| C07 | **P23: not delegable** | §3a; freeze waits |
| C08: the kill e-process continues across the two N-sessions of an unchanged binary | **P24** | §4 coverage paragraph; the kill is reported here, never tallied (§5) |
| C09: P(NI within N at parity) < 0.8 → revise N, the clip rule and the throughput figures by a new signed record before M4 | **P25** | §8 trigger, fixed now |
| C24: m_NI = RN(ln 1.03) is the canonical boundary | **P38** | §4, §7 |
| C31: X3 carries wealth across its two attempts | **P42** (an X3 rule) | §4 coverage rule: a carried e-process is covered only up to the calibration's horizon in total; §10.3 item 3 |
| C03: clean `b5d3f14` stand-in on D: | **P20** | §2 |
| A17: the rate rule (4–7 nights a week, 25% contingency) | **P7** | the noise pilot's §7(b) sets the calibration's nights |
| B01: M0-verdict composition (X4 "waits"; bars beside rows) | **P8** | §8 states |
| Freezes may land between sittings | **P1** | freeze gate |
| Qwen3 jobs never in a window | **P13** | the excluded images of the pilot's §10 apply |
| C29: what counts toward N | **class B, no row** (OWNER-QUEUE; PACKET item 6) | §4 L; ALL registered if blank |

No role in this record needs a different model family (Q17 is not on its path).

---

## 4. Units and counting rules (defined before data)

- **Run, block, d.** As in [X4-noise-pilot §4](X4-noise-pilot.md#4-units-and-counting-rules-defined-before-data) and MEASUREMENT §3: one arm to its stopping point in a fresh process, accepted only if every integrity check passes with the pilot-derived tolerances (no observe mode); T = Δ_h in ns; a block is one ABBA or BAAB comparison of 4 runs; d = ½(ln T_B1 + ln T_B2 − ln T_A1 − ln T_A2), the block's mean log-ratio (06 §6.1). Runs, blocks and sentinels carry the record's grade `CALIBRATION`.
- **n and L, the horizon in A/B blocks.** n_rt = max(6, ⌈12·σ̂_U,rt²/δ²⌉), δ = 3%, σ̂_U from the pilot (the X4-noise-pilot §7(a) rule). ROADMAP §1 rule 4's amber limit N is "twice the hours §10 plans", and §10 plans n × 4·t_run × c with c ≈ 1.5. How many A/B blocks N holds depends on **C29** (class B, Pierce's; OWNER-QUEUE C29, PACKET item 6):
  - **ALL** (cool-downs and gaps count toward N): **L = 2·n** A/B blocks per run type. Registered if C29 is blank at freeze (OWNER-QUEUE conventions: a class-B default that loosens never registers by lapse).
  - **BLOCKS** (only A/B block time counts): **L = 3·n** per run type (2 × 1.5 × n, as X3 §4.12 reads N for every configuration, microbenchmarks included).

  Only A/B blocks count toward L; opening calibration blocks, sentinels and discarded blocks do not.
- **Coverage** (ROADMAP §3.5: the calibration "covers the longest a real parity gate can run"). A gate is covered by a calibration of this record only if (i) every e-process it gates on, **carried wealth included**, can span at most that calibration's horizon in A/B blocks **in total over all its sessions** (L, or 2L where Pierce signs it, below); (ii) it scores its blocks by §7's rules (the same scorer, constants, run-reference rule and bettor); and (iii) it runs the same run-type row (§2), priority class included. A pass of a gate that is not covered is **PASS-PROVISIONAL** with respect to this calibration. This record pins no production rule for the amber second N-session of ROADMAP §1 rule 4: a gate that restarts its wealth there (a new test with a fresh α_i charge) is covered when each session's e-process spans at most the horizon; a gate that carries its wealth forward (X3 under DELEGATED P42) runs one e-process over both sessions and is covered only when their A/B blocks together are at most the horizon (§10.3 item 3). The kill e-process continuing across the sessions of an unchanged binary (DELEGATED P24) is not calibrated by a tally here; §5 reports its crossings.
- **Owner horizon options (§13; neither changes a threshold).** If Pierce signs **2L for the microbenchmark A/A units** (C05, X4 Q9), they run to 2L, the A/A tally counts crossings within 2L (the stricter count) and also reports them within L, and time-to-pass is censored at 2L. If he signs **2L for the planted sessions** (§10.3 item 3), they run 2L A/B blocks with ⌈2L/6⌉ sentinels, and the tally counts crossings within 2L and also reports them within L. Registered: L for both (DELEGATED P21; ROADMAP's "to the amber limit N").
- **Session.** One sequence of blocks of one calibration on one run type, inside one quiet window and one machine-profile hash, run to L with no stop at any crossing. It starts only if its planned end, (blocks × 4 × (t_run,plan × c_rt + o_rt) + 120 s), is no later than 06:45 PT, using the pilot's t_run,plan, o_rt and c_rt (1 microbenchmark, 1.5 end-to-end), and the driver takes the first unrun slot in schedule order whose planned end fits (the pilot's §6 rule: clock and schedule only, never data). A microbenchmark session whose planned length exceeds 7.5 h is a design revisit [D: at 15 s per run, L would have to exceed 450 blocks].
- **End-to-end unit.** At σ̂_U above about 3.7% (ALL) or 3.0% (BLOCKS) an `e2e-decode` session to L exceeds one 7.75-h window [D from G: t_run 120 s × 1.5 + 5 s overhead per run]. An e2e A/A **unit** is therefore L A/B blocks in one or more **segments**, each a contiguous stretch inside one window holding as many whole blocks as the planned-end rule allows (a segment that cannot hold one block does not start); the e-processes continue across segments (block order is the unit's); an unfinished unit resumes first on the next calibration night; S2–S4 are evaluated per segment; a hygiene void in any segment voids the unit. A unit that fits in one window is one segment, the same thing as a session.
- **Counted set.** Per calibration, exactly the first 100 units (20 for e2e A/A, 10 for the positive control, 20 for A/A′) in schedule order that are **not hygiene-voided** and that ended `completed`. A statistical void is a flag set on a completed unit after its last block (S1–S4 read the whole unit); such a unit stays in the set and **counts as an alarm** if its tested e-process reached 20 at any block ≤ L. Units ended `integrity_stop`, `error`, `interrupted` or `cut` are excluded like a hygiene void (the pilot's §4 ends), and every tally is reported with and without voided units.
- **Failure kinds** (MEASUREMENT §5.3; the pilot's tiers with its fill-in thresholds): an **integrity failure** in any calibration run is an evaluator bug that stops the calibration (§10.1), never a void; a **hygiene void** (the X4-noise-pilot §10 night refusals, block discards and session voids, with the pilot-derived load gate and start-state envelopes, the image lists Pierce signs there, and a discard count ≥ 3) removes the unit; a **statistical void** S1 (sentinel mean; planted sessions only), S2 (variance envelope; A/A units: all blocks; planted: calibration and sentinel blocks), S3 (trend, per arm), S4 (incumbent median) keeps it. Void and discard decisions take no run time, d or wealth; the wealth at each void is logged.
- **Which runs enter the run reference.** Only the runs of **A/B blocks** enter the R and Rk histories (each arm's running median; before an arm has any, arm A's; before that, the pilot incumbent median) and the per-arm slow-run counts k_B, n_B of T-pooled. The runs of a planted session's 2 opening calibration blocks and of its sentinel blocks are flagged for S1/S2 by the same run rule (c_run) against a **separate** scorer state that holds only that session's calibration and sentinel runs (per label; label B falls back to label A's history, then to the pilot incumbent median), as the reference's `sentinel_study` does; they never change an A/B block's score, any wealth or any tail-check count. A/A units have no calibration or sentinel blocks. Why: the B-labelled runs of those blocks run K calls, so in B's history they would pull B's reference toward A's level and score early A/B blocks +c whenever c_run < μ_plant,ℓ (σ̂_run below ≈ 0.8%); at σ_run 0.5% the session mean x then rises by 0.0066 above its formula value instead of 0.0023 [S, `x4cal_r2.py` B; no crossing under either rule in any cell, 4,000 sessions each].
- **Crossing.** "The e-process reaches 20" means K_i ≥ 20.0 at some A/B block i ≤ L, K_i the float64 product of §7 (DR-018: max(20, 1/α_i); X4 spends no α, so exactly 20). The tested e-process is superiority in A/A units and non-inferiority in planted sessions.
- **Margins.** m_NI = RN(ln 1.03) = `0x1.e44a9a3bed663p-6`, the canonical boundary (DELEGATED P38), the stricter reading of ROADMAP's "ratio < 0.97"; m_kill = RN(−ln 0.97) = `0x1.f30b2d0091d82p-6`, ROADMAP's literal kill margin.
- **Planted level and K′.** μ_plant,ℓ = μ*_ℓ + 0.0025 [target], μ*_ℓ by the chosen scorer's formula (§3a) at σ̂_d; the provisional K′_ℓ = ⌈e^{μ_plant,ℓ} · K⌉. The 3% calibration is therefore **planned** 0.25% inside the null, and the premise check verifies that it is **at most 0.5%** inside (P2, one-sided 99%); that leniency is stated, not hidden.
- **Separate long run** (one per level, before that level's first counted session; not counted). **B_lr = max(256, ⌈(2.576·σ̂_d/0.0025)²⌉)** A/B blocks at K′_ℓ [G: its 99% half-width equals the 0.25% overshoot], that is 425 blocks at σ_d 2% and 1,699 at 4% [D]. It may span windows in segments of whole blocks under the planned-end rule (each segment starts with the 120-s settle). It confirms the **realised ratio** (ROADMAP §3.5's words) on the raw block statistic d, which neither the scorer's outlier rule nor the first block's reference moves [S, `x4cal_r2.py` C2]: d̄ is the mean of its B′ non-discarded blocks (blocks holding a capped run excluded, as σ_d) and s_d their SD. **Accepted iff |d̄ − μ_plant,ℓ| ≤ 2.576 · s_d/√B′.** Otherwise K′_ℓ ← ⌈K′_ℓ · e^{μ_plant,ℓ − d̄}⌉ and the run is repeated on fresh blocks; at most 3 attempts, then a design revisit before data. Every attempt is recorded with d̄, s_d, the gate scorer's x̄ and the target. K′_ℓ enters by fill-in part 2.
- **Premise check** (per level, after its counted set is complete). k = 100 counted sessions, each run to L; t = t₀.₉₉,ₖ₋₁; each bound is taken over **session means**, so correlation within a session cannot shrink it. Both parts must hold:
  - **P1, in the null:** x̄ − t·s_m/√k ≥ log(1 + ℓ), x̄ the mean of the sessions' mean gate-scorer x and s_m their SD (the e-process's own estimand);
  - **P2, not easier than planned:** d̄ + t·s_dm/√k ≤ μ_plant,ℓ + 0.0025 (= μ*_ℓ + 0.005), d̄ the mean of the sessions' mean raw d and s_dm their SD. P2 caps the realised timing log-ratio, the level ROADMAP names. It is not put on x̄, because the gate scorer's x overstates a level by its +c outlier scoring (+0.0021 at an outlier-run rate of 2%, σ_d 2%; +0.0023 from the first block alone at σ_run 0.5% [S, `x4cal_r2.py` B]), as it does for a real regression in a parity gate; a cap on x̄ would turn a correctly planted level amber, or push K′ down until the timing ratio fell below 3% by an amount no rule bounds.
- **Time-to-pass.** In each counted A/A unit, the A/B block index at which the **non-inferiority** e-process first reaches 20, right-censored at L. With administrative censoring only, its distribution is the empirical CDF; the median and p90 are nearest-rank, published as "> L" when beyond, with the share within L; in hours, × w_rt/3600, w_rt the median wall time per A/B block of that run type's counted A/A units [M]. Reported raw and "credited" (after the chosen tail check).
- **σ_d (the M0 deliverable).** Per run type and niche: the RMS of d about 0 over every non-discarded A/B block of the counted A/A units (all run to L; `stats::rms_about_zero`), **blocks holding a capped run excluded, as X4-noise-pilot §4, their count reported**; df = B, with the two-sided 90% χ² interval [σ̂·√(B/χ²₀.₉₅,B), σ̂·√(B/χ²₀.₀₅,B)]. Planted, A/A′ and positive-control blocks are excluded.
- **Throughput** (published, never gated). Per run type and MDE m ∈ {5%, 2%}: tests per quiet hour = 3600 / (B_m · w_rt), B_m = max(6, ⌈12·σ̂_d,rt²/m²⌉) (06 §6.6, e ≥ 20, calibration blocks, sentinels and set-up excluded) [D from M]; beside it, at δ = 3%, 3600 / (median time-to-pass in blocks × w_rt), or "≤ 3600/(L·w_rt)" when the median is beyond L.
- **Void rate.** Per calibration, and broken down by end kind: (every unit that started and was voided or excluded: hygiene voids, statistical voids, and units ended `integrity_stop`, `error`, `interrupted` or `cut`) ÷ units started, until its counted set is complete.
- **Positive-control drift.** Run j (0-based, both arms, in launch order; **j counts every launched run of the session, discarded blocks' runs included**) runs K_j = ⌈K · e^{r·j}⌉ calls with r = 3·σ̂_run/(4L − 1), so the timed work drifts by at least 3σ̂_run in log-time over the session (the MEASUREMENT §8.2 target); every block is AABB. A unit counts as voided by the control only if S3, S4 or the start-state gate voids it; any other hygiene void replaces it with a spare.

---

## 5. Metrics: primary, secondary, descriptive

- **Primary (gate inputs).**
  - A/A: the number of counted microbenchmark A/A sessions whose superiority e-process reaches 20 within L, under the gate scorer of §3a and, separately, under S (target ≤ 2 of 100 each).
  - Planted: per level (3%, 4%), the number of counted sessions whose non-inferiority e-process reaches 20 within L under the gate scorer (target ≤ 2 of 100 each), with the premise check (P1 and P2) met.
  - Completion: 20 counted e2e A/A units; time-to-pass and throughput published.
- **Secondary, tightening** (each can turn a pass into amber, never a fail into a pass): the pooled two-sided z-test of the mean S-clipped A/A d over every counted microbenchmark A/A block, α = 0.01 [target], with the registered block-level SE s/√B (positive correlation within a unit can only make it reject more often, which errs toward amber); the void rate per calibration (amber above 10% [target]); per-arm discarded-run asymmetry (exact two-sided binomial at p = 0.5, α = 0.01) and wealth-at-void skew (one-sided Mann–Whitney toward low log-wealth against the same block index in non-voided units, α = 0.01) [target]; the premise check (P1, P2); the positive control (≥ 9 of 10 voided [target]).
- **Secondary, reported.** σ_d per run type with its interval [M]; per planted level, the realised mean d and its ratio e^{d̄} − 1 beside x̄, with both premise bounds; time-to-pass raw and credited (median, p90, share within L); throughput; the P25 statistic (§8); per-run outlier rate; the carry-over contrast co_BA − co_AB with its SE; the A vs A′ mean d with its 95% interval over session means, and each MDE at or below the larger end of its absolute value flagged; the kill e-process's crossings in A/A units (false kills, expected 0) and planted sessions (power at small regressions, expected ≈ 0) [S, reference table 3c]; every tally under the unchosen scorer of §3a and under the 06-literal scorer, descriptive; every attempt's tally after a re-run (§10.1).
- **Descriptive.** Full per-run, per-block and wealth records; S1–S4 statistics; the long-run attempts; sensor and void logs; quiet-hour accounting.

---

## 6. Sample and power

### 6.1 Operating characteristics

- **A/A rule, exact** [D, reference §1]: at a true per-session false-alarm rate of 1% the ≤ 2/100 rule passes with 0.9206, at 5% with 0.1183, at 8% with 0.0113, confirming ROADMAP's 0.92 / 0.12 / 0.01 [inference]. It fails an e-process sitting exactly at Ville's 5% bound with probability 0.88 and passes half the time at 2.67% [D]. DELEGATED P22 confirms the rule; it may only be tightened before data.
- **Independence is an assumption.** With an intra-night correlation of 0.05, P(pass) at a true 5% rate is 0.2369 in 4 nights × 25 sessions and 0.1699 in 10 × 10; at 8%, 0.0592 and 0.0270 [D, reference table 1b]. The schedule (§6.2) spreads each calibration over every calibration night.
- **Power of the A/A rule against a label asymmetry** [S, reference tables 2b, 3b]: a 2% asymmetry crosses within N in 0.20% of sessions at σ_d 2% and 50.0% at 4% (R); under S, 46.3% at σ_d 4% with 2% outliers. The pooled mean test has power 0.81 / 0.77 against a 0.2% asymmetry at σ_d 2% / 4% [D]. Under L06 the same 2%-asymmetry cells give 0.0015 (σ_d 2%) and 0.374 (σ_d 4%) [S, reference table 2b], so branch (a-L) detects an asymmetry somewhat less often than (a-R); S is the more sensitive statistic in both.
- **Planted regression** [S]: ≤ 0.70% false passes in every drafted cell of reference table 2a, ≤ 1.0% for R at outlier-run rates up to 10% (table 3a), ≤ 0.22% for either branch at its own level within 2n (§3a).
- **Longer horizons** [S, `x4cal_r2.py` A1–A3; 4,000 sessions per cell, time-to-pass 1,000; σ_d 2% and 4%; outlier-run rates 0–10% (A/A) or 0–2% (planted)]. A/A false alarms within 3n / 4n / 6n are at most 0.0030 / 0.0053 / 0.0095 under R, 0.0035 / 0.0053 / 0.0083 under L06 and 0.0070 / 0.0112 / 0.0152 under S (σ_d 4%; at σ_d 2% every cell is ≤ 0.0085). The rule then passes a sound evaluator less often: P(≤ 2 of 100) is 0.93 at a true 0.95% and 0.80 at 1.52% [D]; that is a cost of the stricter horizon, never a loosening. Planted false passes at each branch's own level + 0.25% stay ≤ 0.0053 (R) and ≤ 0.0067 (L06) up to 6n. The time-to-pass share at true parity within 3n is ≥ 0.886 (R) and ≥ 0.954 (L06) at outlier-run rates 0–2%. These are the horizons a BLOCKS answer (3n), a 2L option under ALL (4n) or both (6n) would use.
- **The [S] numbers assume σ_run = σ_d** (c_run = 4σ_d), as the reference's model makes them. If σ̂_run is below ≈ 0.8%, c_run falls below μ_plant and the first A/B block of every planted session is scored +c: the false-pass rate stays 0.0000 and P1 only gains [S, `x4cal_r2.py` B].
- **Premise check and long run** [D, `x4cal_r2.py` C1, normal approximation; S, C1b]. The counted set's one-sided 99% half-width is 0.0011–0.0014 (σ_d 2–4%, L = 2n or 3n), so the two parts pass together with probability 0.925–0.997 at a level exactly as planned, 0.55–0.79 when the realised level is 0.1% off the plan and 0.06–0.10 when 0.2% off. The long run's acceptance half-width is ±0.0025 (revision 1's 256 blocks: ±0.0032 at σ_d 2%, ±0.0064 at 4%). If the provisional K′ misses the plan by δ (non-proportional timing), the chance of an amber premise after the long run is 0.055–0.079 at δ = 0, 0.43–0.47 at 0.1%, 0.78–0.80 at 0.2% and 0.47–0.50 at 0.3% (256 blocks: 0.91–0.94 at 0.2%, 0.76–0.995 at 0.3%); the long run ends in a design revisit with probability ≤ 0.016. An amber premise costs a re-run of that level (§8), never a pass.
- **End-to-end:** 20 units estimate σ_d and time-to-pass; they cannot test a 5% false-alarm rate (P(0 of 20) at 5% = 0.358 [D]). End-to-end gates rest on the microbenchmark calibration plus per-session sentinels (ROADMAP §3.5; 06 §6.3), which detect a 2% label asymmetry within one session only ≈ 13–14% of the time [S, reference table 3e].
- **σ_d precision:** 100 × L microbenchmark blocks (≥ 1,200) give σ̂_d a relative SE of at most ≈ 2.0% under normality [D: 1/√(2·1,200)]; 20 × L e2e blocks (≥ 240), at most ≈ 4.6% [D].

### 6.2 Schedule

Slot list, shuffled once by the §2 seed: `aa-mb-001…130`, `pl3-mb-001…130`, `pl4-mb-001…130`, `aap-mb-01…26`, `pc-mb-01…13`, `aa-e2e-01…26` (30% spares [G]). The two long runs (`lr3`, `lr4`) run first, in that order, each to acceptance or its third attempt (a long run may span windows, §4), before any counted session. A calibration whose counted set is complete skips its remaining slots. If a calibration's spares run out, its void rate is already above 10% (amber, §8); a continuation of 30 slots per calibration is drawn by the same rule with the suffix `"/2"` appended to the seed string.

**Night split** (fixed now; it reads only the clock and the two schedules). Nights may also hold X3-parity sessions. On a night that holds both, the driver first runs the X3-parity sessions that X3's frozen schedule assigns to that night, in X3's order and under the same planned-end rule, then this record's slots by §4's rule until none fits. The noise pilot's nights and `mithc profile measure`'s night hold neither (PLAN §6.3 night order, items 1–2). Fill-in part 1 prints the resulting plan; it chooses nothing.

### 6.3 Quiet hours [D from G]

Inputs [G]: a 10 s microbenchmark run plus the per-run overhead o_rt ≈ 5 s (X4-noise-pilot §6, revision 4) = 15 s, the figure §4 uses; an end-to-end run 120 s × 1.5 + 5 s = 185 s; 120 s set-up per session and per started 7.5 h of a long run; long runs of B_lr blocks (§4), one attempt per level; this record's units only (pilot and X3 excluded) [D, `x4cal_r2.py` D]:

| | σ_d 2% (n = 6) | σ_d 4% (n = 22) |
|---|---|---|
| C29 = ALL (L = 2n): A/A / planted / e2e / A/A′ / positive control / long runs / **total** | 23.3 / 60.0 / 50.0 / 4.7 / 2.3 / 14.2 / **154.6 h** | 76.7 / 186.7 / 181.6 / 15.3 / 7.7 / 56.9 / **524.8 h** |
| C29 = BLOCKS (L = 3n): the same | 33.3 / 83.3 / 74.7 / 6.7 / 3.3 / 14.2 / **215.6 h** | 113.3 / 270.0 / 272.0 / 22.7 / 11.3 / 56.9 / **746.2 h** |
| Owner option, micro A/A to 2L (C05 / X4 Q9) | +20.0 h (ALL), +30.0 h (BLOCKS) | +73.3 h (ALL), +110.0 h (BLOCKS) |
| Owner option, planted to 2L (§10.3 item 3, X3 carried wealth) | +46.7 h (ALL), +70.0 h (BLOCKS) | +170.0 h (ALL), +256.7 h (BLOCKS) |

Revision 1's figures (10 s per microbenchmark run with no overhead, 256-block long runs) were 118.2 / 166.5 h at σ_d 2% and 376.9 / 552.2 h at 4% [D]; they were about a quarter low. ROADMAP §10's M0 line is ≈ 60 h at σ_d 2% and ≈ 215 h at 4%; X4 alone exceeds it at both ends (X4 owner question 1; COST §1.4). That line is an estimate [inference], not a threshold: exceeding it loosens nothing, but its revision is Pierce's (C05, §13), and an unclamped nights-per-week above 7 in the noise pilot's §7(b) is a D-22 trigger fact, with X4 "waiting" (amber, ROADMAP §3.7). That formula must use this record's L and B_lr (§10.3, item 2).

---

## 7. Analysis procedure (deterministic, named)

**e-processes.** The Rust orchestrator computes them live; the judge (below) recomputes them from the raw per-run records with the reference, and the two must agree **bit for bit** on every K_i (06 §5.3 condition 2). A mismatch is an evaluator integrity failure (§10.1). Pinned constants [target]:

| Constant | Value / rule |
|---|---|
| m_NI, m_kill | `0x1.e44a9a3bed663p-6` = RN(ln 1.03); `0x1.f30b2d0091d82p-6` = RN(−ln 0.97) (60-digit decimal, never a platform `log`) |
| threshold; crossing | 20.0; first A/B block i ≤ L with K_i ≥ 20.0, K_i = Π(1 + λ_j g_j) in block order in float64, no log space |
| float rules | IEEE-754 binary64, round-to-nearest-even, operations in the written order, no FMA contraction |
| bettor | aGRAPA only: μ = s1/n; var = max(s2/n − μ·μ, 1e-12); λ = min(θ, max(0, μ/(var + μ·μ))); state n = 1, s1 = g0, s2 = v0 + g0·g0; after each block K ← K·(1 + λg) with λ from the prior state, then n += 1, s1 += g, s2 += g·g |
| θ | 0.5 (superiority, non-inferiority); 0.8 (kill) |
| bet variables | superiority g = −x/c; non-inferiority g = (m_NI − x)/(c − m_NI); kill g = (y − m_kill)/(c_kill + m_kill) |
| priors | superiority x0 = −0.02; NI x0 = 0; kill y0 = m_kill + 0.02; each sd0 = clip/3; g0 = sign·(x0 − m)/scale, v0 = (sd0/scale)² |
| clips | c = max(3σ̂_d, 2·m_NI); c_kill = max(3σ̂_d, m_kill + 3σ̂_d); c_run = 4σ̂_run (pilot values, per run type) |
| gate scorer | §3a point (a): R or L06, as Pierce answers C07 |
| other scorers | S = clip(d, −c, c) (A/A second statistic); Rk = R with outlier blocks scored −c_kill (kill); the unchosen gate scorer, descriptive |
| run reference (R, Rk) | the arm's running median of its own earlier **A/B-block** runs in the unit; before any, arm A's; before that, the pilot incumbent median. Opening calibration and sentinel runs: a separate state, for S1/S2 flags only (§4) |
| tail check | §3a point (b): T-pooled or T-06, as Pierce answers C07; never applied to a tally |
| long run; premise check | §4: d̄ against μ_plant,ℓ at ±2.576·s_d/√B′; P1 on the gate scorer's session-mean x, P2 on the session-mean raw d, each one-sided 99% (t₀.₉₉,₉₉) |
| S1 / S2 | sentinel mean z-test, two-sided 0.01, on unflagged sentinels with σ̂_pilot; χ² envelope [χ²₀.₀₀₅,ₘ/m, χ²₀.₉₉₅,ₘ/m]·σ̂²_pilot on unflagged calibration + sentinel blocks (A/A units: all blocks) clipped at c |
| S3 | two-sided Mann–Kendall at α 0.01 on each arm's per-run log-times, Hamed–Rao factor restricted to lag 1, always applied, floored at 1, after Sen-slope detrending |
| S4 | incumbent session median outside the pilot grand median ± max(3·s_between, 1%) |
| load gate, start state, integrity tolerances | the X4-noise-pilot §7(a) fill-in values, per run type |

**The judge.** A deterministic script, `experiments/x4-integrity/calibration/judge.py` (to be written; pinned by SHA-256 in fill-in part 1; tested on DRY-RUN and synthetic records before the first counted session; it judges nothing until this record is SIGNED). It reads only `night-*` directories whose manifests say grade `CALIBRATION`, closed or stopped, with this record's freeze commit and the pinned configuration hash (the pilot's §7 manifest and hash rules), recomputes every e-process, applies §4's counted-set rules, and writes `verdict.json` with every count of §5, each with and without voided units, and each calibration's state by §8's precedence. Every number it emits carries its tag.

**Fill-in rules (mechanical; § Amendments).** Part 1, after the noise pilot's post-pilot amendment and before any collection under this record: the pilot constants of §2; L by §4 and the C29 answer; B_lr, μ_plant,ℓ and the provisional K′_ℓ by §4; p_blk if (b-L); the binary pins (A′ included), the configuration's canonical SHA-256, the schedule and the night plan that §6.2's split rule gives, the judge's SHA-256, and the P25 pilot statistic (§8). Part 2, after the long runs: the accepted K′_ℓ with every attempt's d̄, s_d, x̄ and target. A value outside a rule's bound (a tolerance above its pilot ceiling, a long run not accepted in 3 attempts, a microbenchmark session over 7.5 h) is a design revisit before data, never a loosened constant.

The Gatekeeper (deterministic code + Owner key) computes the verdict from this frozen record and the raw results; agents run the scripts and write the dossier, never judge (ROADMAP §1 rule 3).

---

## 8. Outcomes: pass / amber / fail / incomplete, each with its action

Copied from ROADMAP §3.5 and made operational by §4. Each calibration ends in one state, written to `verdict.json`.

**Precedence.** A calibration's state is the most severe that applies, in the order **fail > amber > incomplete > pass**. A tally above 2 of 100 is fail whatever the premise check, the secondaries or the completeness of the counted set say; a tally that reaches 3 is final at once, since later units can only add to it. Amber never turns a fail into anything else. Incomplete applies only while no fail has occurred, and any amber flag already raised is reported with it.

| Calibration | Pass | Amber (written action) | Fail | Incomplete |
|---|---|---|---|---|
| **A/A** | ≤ 2 of 100 under the gate scorer **and** ≤ 2 of 100 under S | pooled mean test rejects, void rate > 10%, discard asymmetry or wealth-at-void skew flagged, or the positive control voids < 9 of 10: find the cause, fix it, re-run the A/A calibration on fresh sessions (§10.1) | > 2 of 100 under either: **bars every superiority gate** until the cause is fixed and the calibration passes again on fresh sessions | counted set not complete: X4 "waits" at week 6 (ROADMAP §3.7) |
| **Planted 3%**, **planted 4%** (each) | ≤ 2 of 100 under the gate scorer, premise check met (P1 and P2) | premise check fails (P1 or P2): set the new planned level μ′ = μ_plant,ℓ + s, s = P1's shortfall (log(1 + ℓ) minus its bound) or 0; K′_ℓ ← ⌈K′_ℓ · e^{μ′ − d̄}⌉, d̄ the counted set's mean d; confirm it by a long run against μ′ (§4); re-run that level on fresh sessions, with P2's cap at μ′ + 0.0025. Void rate > 10% or a flagged asymmetry: as above | > 2 of 100, whatever the premise check says: **bars every parity gate** until fixed and passed again on fresh sessions | as above; X3's parity component is barred while incomplete (PLAN §3.8) |
| **End-to-end A/A** | 20 counted units, time-to-pass and σ_d published | void rate > 10%: find the cause, fix, continue on fresh units | — (not a false-alarm gate; its false alarms are reported) | as above |
| **Positive control** | ≥ 9 of 10 voided | < 9 of 10: the A/A calibration is amber (above) | — | — |

**The calibration part of the X4 gate passes** when A/A, planted 3% and planted 4% all pass, the e2e A/A is complete, the positive control passes, and time-to-pass, σ_d and throughput are published. A failed calibration is reported as `fail` with its bar; whether it also sets X4 = kill (the HALT-F row) is the M0-verdict record's mapping (PLAN §3.8, DELEGATED P8), not this record's.

**P25 trigger** (C09, fixed now). Two statistics per run type: (1) at fill-in part 1, the share of the pilot's counted microbenchmark sessions whose non-inferiority e-process, replayed under the gate scorer with the fill-in constants, reaches 20 within min(L, 24) blocks [M, replay]. When L ≤ 24 it decides. When L > 24, a share ≥ 0.8 within 24 blocks implies a share ≥ 0.8 within L and decides; a share < 0.8 is "not determinable", and statistic (2) decides. (2) After the calibration, the share of counted A/A units whose non-inferiority e-process reaches 20 within L [M]. If either is below **0.8** [target], the trigger fact is recorded and a new record revising N, the clip rule and the throughput figures must be signed by Pierce before M4 (DELEGATED P25). It changes nothing in this M0 calibration.

**D-22 facts** (recorded, never decided here; ROADMAP §9, 06 §6.9): a void rate above 10%; a failed calibration; an unclamped nights-per-week above 7 in the noise pilot's §7(b); a window conflict with Pierce's use.

---

## 9. Threats to validity and how each is handled

- **Non-exchangeable desktop fakes an effect.** Randomised ABBA/BAAB; S3/S4 voids; the per-run start-state gate and the carry-over contrast. The A/A rule tests label symmetry only; drift that interacts with a real A/B difference is invisible to it [known weakness]; the trend in A/B d is reported.
- **Selection through voids.** Statistical voids stay in the tally and count as alarms; void decisions never see wealth; the discard-asymmetry and wealth-at-void checks; every tally with and without voids; the void rate counts every excluded unit by end kind; spares are taken in schedule order only.
- **Circular constants.** Every data-dependent constant comes from the pilot by the frozen §7(a) rules, or from the long runs by §4's mechanical rule, before the first counted session.
- **Planted level not in the null, or further inside it than planned.** Proportional extra work; the level computed on the gate scorer's estimand plus a stated 0.25% overshoot; the long run confirming the realised ratio on d; the two-sided premise check on session means (P1 in the null on the gate scorer's x; P2 at most 0.25% above the plan on d).
- **Sentinel and calibration runs leak into the run reference.** Only A/B-block runs enter the R/Rk histories (§4).
- **The calibration covers less than a gate runs.** §4's coverage rule: every e-process, carried wealth included, must span at most the calibration's horizon in total, under §7's scoring and the §2 row; otherwise the gate's pass is PASS-PROVISIONAL. X3's carried wealth is covered only by planted sessions to 2L (§13) and only if X3's other rules fit (§10.3 item 3; freeze-gate condition 6).
- **Repeated attempts.** A re-run needs a named change, and every attempt's tally is reported with the number of attempts (§10.1).
- **The clip hides a slow tail.** The tail check (§3a); its residual credit is stated per branch.
- **Correlated sessions.** Beta-binomial sensitivity (§6.1); the schedule spreads every calibration over all nights.
- **e2e units spanning windows.** Night-to-night shifts enter between segments; randomised order keeps A/A d conditionally symmetric, and S2–S4 run per segment.
- **The positive control is a work ramp, not heat.** It proves that S3/S4 fire on a drift in per-run log-times, which is what they test; it does not exercise the thermal start-state envelope, which is unavailable for the CPU package on this desktop anyway [M, X4-noise-pilot §10: no ACPI thermal-zone counter].
- **Same-family review only.** Every review is Claude, same family, independent context; the gap to ROADMAP's different-family requirement is stated (§12).

---

## 10. Deviation and re-run policy; dependencies; cross-record items

### 10.1 Deviations and re-runs

- **Hygiene voids** are replaced by spares and do not count; **statistical voids** stay in the tally; both, and every other excluded unit, count toward the void rate.
- **An integrity failure** in a calibration run stops every calibration (an evaluator bug), never re-run silently. A later night refuses to start until a dated amendment clears it (the pilot's `integrity_cleared` mechanism). A fix that changes a pinned hash or widens a tolerance is a **restart**: every earlier counted unit of every calibration is kept, reported and excluded, and the counted sets start again on fresh units; a widened tolerance needs a dated amendment before the restart and may never exceed its pilot ceiling.
- **Re-runs after amber or fail** need a dated amendment, before the re-run's first session, that names the cause and a **change**: to a pinned hash, to the configuration (K′ included) or to a void rule. A re-run with nothing changed is not allowed. Every attempt's tally is reported, and the verdict cites the number of attempts.
- **Any change** to a unit, threshold, sample or pin after collection has begun is an amendment marked *post-data*, with verdicts reported under both rules (README lifecycle). Thresholds never move once data have been seen.

### 10.2 Dependencies (before the first counted session; before freeze where marked)

- **Pierce:** C07 (freeze); the §13 fields; the signature (collection, long runs included).
- **The X4 track (lead engineer):** (before sitting 2, for freeze-gate condition 3) the one reference revision with all four C07 combinations behind a flag, golden paths for R, L06, S and Rk, T-pooled and T-06 vectors, a planted-session golden vector with opening and sentinel blocks under §4's run-reference rule, and both scratch studies of §2 folded in; (collection) the Rust e-process passing the differential test for the chosen branch (and, under (a-L), `Lit06` scoring capped runs +c); a `CALIBRATION` driver mode (schedule and night split, per-arm K′, opening and sentinel blocks with their separate run-reference state, AABB order and the K_j ramp by launch order, A′, long runs and e2e units across windows, counted-set tracking, the pilot's progress, manifest and crash rules); the A′ build; the judge; a DRY-RUN night per calibration type through the judge.
- **The noise pilot:** SIGNED, run, and its post-pilot amendment committed (σ̂, tolerances, p0, rate), and the nights-per-week re-signed by Pierce.
- **D0-9** (key): without it X4's facts are provisional (03 §11.3), re-signed later; no threshold depends on it.

### 10.3 Cross-record items (for the lead engineer; outside this track's files)

1. **C29's registered value** (freeze-gate condition 5). X4-noise-pilot §3a registers "A/B block time only" (BLOCKS) for C29; OWNER-QUEUE classes C29 B and excludes it from default-on-lapse because it loosens, and PACKET item 6 says the records freeze with ALL. This record registers ALL; the pilot's §3a must match before this record freezes.
2. **The noise pilot's §7(b) H_cal** (freeze-gate condition 5) uses N_rt = 2·n for every term and 2 × 256 long-run blocks. It must use this record's L (3n under BLOCKS) and B_lr (425 blocks at σ_d 2%, 1,699 at 4%). BLOCKS raises X4's hours by ≈ 61 h at σ_d 2% and ≈ 221 h at 4% over ALL [D, §6.3].
3. **X3 coverage** (freeze-gate condition 6). (a) X3 §4.12 lets N hold L_k = 3n_k blocks (BLOCKS); under ALL, X3's N holds 2n_k. (b) X3's second N-session **carries its wealth forward** (DELEGATED P42; X3 §7.5), so one X3 e-process spans both sessions, up to 2L A/B blocks; under §4's coverage rule only planted sessions to 2L cover it (§13; +46.7–256.7 h, §6.3). (c) X3's e-processes use their own constants (c_pass, a_reg; X3 D§8.5) and score blocks by 06 §6.2's literal rule with its own clip c_pass, not §7's; and X3 runs `x3_bench` at `HIGH_PRIORITY_CLASS` (X3 DESIGN §8.2) where §2 registers NORMAL. Under §4's coverage rule any one of (b) beyond the signed horizon, (c)'s scoring or (c)'s priority class leaves X3's G2 uncovered. Before this record freezes, X3's record must agree on the run type and the coverage rule, or declare its G2 and G3 passes PASS-PROVISIONAL with respect to this calibration (X3 §7.6 then applies).
4. **MEASUREMENT-SERVICE §5.4 and §8.2** say the positive control's heater ramp is "calibrated in the pilot"; the pilot has no such step. This record uses the work ramp (§4); the design file should follow.
5. **06 §6.1's session** is one window. Real end-to-end parity gates at σ_d above ≈ 3.7% face the same multi-window question as §4's e2e units; their stage records should adopt the same unit rule or say why not.
6. **`mithc profile measure`.** PLAN §8 lists it under this record's collection, but it runs on pilot-week night 4 (X4-noise-pilot §6), before this record can be SIGNED with its fill-in. It is descriptive (the phys and emp bounds) and is **not** pre-registered here; it needs its own small record or a section of the pilot's before that night.
7. **The X4-integrity DRAFT** now points here for every calibration clause (pointer edits, 2026-10-23); its §3, §4–§8 calibration text, owner questions 1, 3–6, 8 and 9, and its §13 are superseded for the calibration where they differ (the heater, N = 2n fixed, the e2e session rule, the 256-block long run on x, the one-sided premise check).
8. **PACKET item 4, DELEGATED P23 and OWNER-QUEUE C07** (freeze-gate condition 1) quote older numbers from the reference's table 3d: tail credit 0.130 → 0.110 under the literal check, 0.017 pooled, a parity cost ≤ 0.007, and "keep 06 literally: the calibration is then re-simulated". §3a now gives all four combinations, simulated: for 15% of runs 30% slow at σ_d 2%, T-06 0.078–0.096 and T-pooled 0.010–0.011 against 0.127–0.144 unchecked; the parity cost and the other cells are in §3a. Before sitting 2, PACKET item 4 (and the P23 rationale and the OWNER-QUEUE C07 row) should cite §3a, so that Pierce answers C07 from this record's numbers.
9. **The micro A/A 2L cost shown for C05** (PACKET line 564, OWNER-QUEUE line 169, DELEGATED P21, PLAN lines 974 and 1597, COST line 111) is +13.3 h at σ_d 2% and +48.9 h at 4%, from 10 s per run with no overhead. With the per-run overhead it is +20.0 h and +73.3 h under ALL (+30.0 h and +110.0 h under BLOCKS) [D, §6.3]. Those records should cite §6.3 before Pierce answers C05.

---

## 11. Deliverables and where they land

- This record; the reference revision for the chosen C07 branch (`experiments/x4-integrity/stats/`); the judge (`experiments/x4-integrity/calibration/judge.py`, planned); the calibration configuration and the A′ build script change (`experiments/x4-integrity/pilot/` or a sibling `calibration/` folder, planned).
- Results, on collection under the FROZEN and SIGNED record: `experiments/x4-integrity/results/calibration/`: the long-run attempts; the raw per-run, per-block and wealth records; the void and sensor logs; `verdict.json`; REPORT.md with σ_d per run type and niche, time-to-pass, throughput, the P25 statistics, the A/A′ floor, each planted level's realised mean d and ratio beside x̄ with both premise bounds, and every tally with and without voids and per attempt, every number tagged.

---

## 12. Review log (independent reviewers, with model family)

ROADMAP asks for reviewers from a **different model family**; this setup has only Claude, so reviews are logged as **same-family, independent-context**, which is weaker than the requirement ([m0/README](../README.md)). The calibration clauses inherited from the X4-integrity DRAFT were reviewed there twice on 2026-10-16 (36 findings, all accepted; [X4-integrity §12](X4-integrity.md#12-review-log-independent-reviewers-with-model-family)).

| Date | Reviewer (lens) | Family | Scope | Findings (blocker / major / minor) | Accepted | Rejected |
|---|---|---|---|---|---|---|
| 2026-10-23 | Reviewer 1 (adversarial, whole record) | Claude, same family, independent context | revision 1 | 0 / 7 / 5 | 12 (4 with a changed fix, below) | 0 (two sub-fixes replaced, below) |
| — | none yet for revision 2 | — | revision 2 | — | — | — |

**Round 1 dispositions (revision 2, 2026-10-23, x4cal track reviser).** Each finding was checked against the record, the reference and the cited records before it was accepted.
1. *(major) The realised planted level had no upper control.* **Accepted**, verified: the 256-block long run accepted a level ±0.0032 (σ_d 2%) or ±0.0064 (4%) from its target, and the premise check was one-sided [D, `x4cal_r2.py` C1]. Fixes: the two-sided premise check (P1, P2); the long run sized B_lr = max(256, ⌈(2.576·σ̂_d/0.0025)²⌉) as proposed, its hours re-derived (§6.3); the realised mean d reported in fill-in part 2 and REPORT. **Changed:** the upper bound is put on the raw d, not on the gate scorer's x̄, and the long run confirms d, not x (§4 gives the reason: R's +c scoring inflates x̄ by ≈ 0.002 at 2% outlier runs [S, B]). **Sub-fix replaced:** accepting a long run only when both one-sided 99% bounds lie in [log(1 + ℓ), log(1 + ℓ) + 0.005] at the proposed size would reject a perfectly calibrated K′ 80% of the time (P(accept) 0.197–0.198 [D, C1]), so the long run keeps a two-sided 99% consistency test, whose half-width at that size is the 0.25% overshoot.
2. *(major) Whether opening and sentinel runs enter the R/Rk history was unstated.* **Accepted**, verified (`run_sessions` has no such blocks; `eprocess.rs` `arm_hist` falls back B → A → pilot median). Fix: §4's run-reference rule (A/B-block runs only; a separate state for S1/S2 flags), §7's table, the planted golden vector in freeze-gate condition 3, and the σ_run sensitivity (§6.1) [S, B]. **Sub-fix replaced:** adding the opening and sentinel blocks to the reference's planted simulation changes no tally under the adopted rule, since the A/B scorer never sees them; the study shows it (B) and the golden vector tests it.
3. *(major) States could overlap and a pure retry was allowed.* **Accepted.** §8 precedence (fail > amber > incomplete > pass; a tally of 3 is final); §10.1 re-runs need a named change, every attempt reported and cited.
4. *(major) Coverage was per session, not per e-process; the record pinned a production rule contrary to P42.* **Accepted.** §4's coverage rule (carried wealth included, scoring and run type too); the "production rule, pinned here" bullet is removed; §3b cites P42; §10.3 item 3. **Changed:** instead of registering 2L on a blank unless X3 adopts the rule, the freeze waits for X3 (condition 6), so a blank can register L without lapsing into the looser reading.
5. *(major) The night-split rule was to be authored in fill-in part 1.* **Accepted.** The rule is fixed in §6.2; fill-in part 1 only prints the plan.
6. *(major) The freeze gate was unmeetable as written and omitted the cross-record conditions.* **Accepted.** Freeze-gate conditions 3 (one reference revision with all four combinations, due before sitting 2), 5 and 6. **Changed:** the reference itself is outside this track's files; committing it is a §10.2 item for the X4 track.
7. *(major) PACKET item 4 quotes numbers the record no longer has.* **Accepted**, verified (PACKET lines 283–290; DELEGATED P23; OWNER-QUEUE C07). §10.3 item 8 and freeze-gate condition 1; the PACKET edit is the lead engineer's.
8. *(minor) L meant both the horizon and the level.* **Accepted:** the level is ℓ throughout.
9. *(minor) §6.3 left out the per-run overhead.* **Accepted**, verified (revision 1 used 10 s; §4 used 15 s). Re-derived with 15 s and 185 s per run and the new long runs; the §13 brackets follow; §10.3 item 9 lists the other records that quote the old 2L cost.
10. *(minor) P25 statistic (1) discarded a decisive case.* **Accepted** (§8).
11. *(minor) σ_d, the void rate and the ramp index were loose.* **Accepted** (§4: capped-run blocks excluded from σ_d; the void rate counts every excluded unit by end kind; j counts launched runs).
12. *(minor) Nothing was simulated beyond 2n.* **Accepted:** 3n, 4n and 6n rows for A/A (R, L06, S), planted 3% and 4% and time-to-pass [S, `x4cal_r2.py` A], in §6.1; to be folded into the reference (condition 3).

---

## 13. Signature block

Every Owner choice this record holds open is a field here, fixed before freeze (C07) or by the signature, before any data. A blank field registers the value in brackets, which is the stricter or the operative one.

```text
Owner: ______________________   Date: __________
Signs the record frozen at commit: ________   (and, if signed after it, fill-in part 1 at commit: ________)
Records (each before the first noise-pilot night unless marked):
  C07 (a) gate scorer: R | L06 ______                         [no default: the record does not freeze without it]
  C07 (b) tail check: T-pooled 5% | T-06 1% ______            [no default: the record does not freeze without it]
  C29 what counts toward N: BLOCKS | ALL ______               [ALL: L = 2n; §4]
  Priority class (pilot, x3_bench, this record): NORMAL | HIGH __ [NORMAL; §2; the same answer as X4-noise-pilot §13]
  C05 micro A/A horizon: L | 2L ______                        [L; DELEGATED P21; +20.0-110.0 h for 2L, §6.3]
  C05 ROADMAP §10 M0 quiet-hour line: revise | leave ______    [leave: an estimate, not a threshold; D-22 facts recorded]
  Planted horizon (X3 carried wealth, §10.3 item 3): L | 2L __ [L: ROADMAP's literal "to the amber limit N"; a carried
                                                                X3 pass beyond L is then PASS-PROVISIONAL (§4; freeze-gate
                                                                condition 6); 2L: +46.7-256.7 h, §6.3]
Before the first counted session: the nights-per-week figure of X4-noise-pilot §7(b) (re-signed there).
```

**Every remaining owner input this record depends on** (each with its source; none is delegable unless a DELEGATED row is cited):
1. **C07**, both points (§3a). Not delegable (P23). Blocks the freeze and therefore the first pilot night. PACKET item 4 (to be updated to §3a's numbers, §10.3 item 8).
2. **C29** (class B; PACKET item 6). Blank registers ALL.
3. **Priority class** NORMAL or HIGH (PACKET item 5; the lead engineer may adopt NORMAL as a DELEGATED row, since the records disagree). Blank registers NORMAL.
4. **C05's Pierce-only parts:** the microbenchmark A/A horizon (L registered by P21; 2L is his option) and the ROADMAP §10 quiet-hour revision (X4 Q1).
5. **The planted horizon** for X3's carried wealth (§10.3 item 3); L registered, under which a carried X3 pass beyond L stays PASS-PROVISIONAL.
6. **The signature** of this record (D0-12; chat as the interim form, key from sitting 2), and the **nights-per-week** re-signature after the pilot (R5, P7).
7. **Ratification at sitting 2** of R8 (C01, C02, C25, D0-7a) and of the adopted rows P1, P7, P8, P20–P22, P24, P25, P38 and P42 (DELEGATED review).
8. **The noise pilot's own §13 fields**, which this record inherits: the GEMS image names, the MITHRIL-MEASURE plan 24/7 or nightly, the Defender exclusion, C: free space, the R1-11 init-wall reading, Plan A or B for the rate rule (X4-noise-pilot §13), and his pre-night settings (B10, PRE-NIGHT A1–A9).
9. **Not blocking, later:** D25 (narrow ROADMAP §3.5's "exchangeability" wording, X4 Q8); C04 (what "the end of week 6" means for X4 "waits"); C30 (X3's §10 n-formula question, after the pilot); A18 (D0-8, and whether GEMS counts as his own use for D-22); D0-9b (the long-term key).

## Amendments (appended, dated)

_None yet._ Pre-registered kinds:
- **Fill-in part 1** (after the noise pilot's post-pilot amendment, before any collection under this record; no new signature unless Pierce chooses to sign with it): only mechanically determined values, listed in §7. Every value is recomputable from cited inputs by a rule of this record.
- **Fill-in part 2** (after the long runs; no new signature): the accepted K′₃ and K′₄ with every attempt's d̄, s_d, x̄ and target, and each level's realised ratio e^{d̄} − 1.
- **Clearing amendments** for an integrity stop (§10.1), dated, naming the cause and the fix.
- **Re-run amendments** after amber or fail (§10.1), dated, naming the cause and the change.
- **Post-data amendments**, marked as such, with verdicts reported under both rules.
