# X3: one meaning plus schedules regenerates the Q4/Q8 matvec triplets
Status: DRAFT (to be FROZEN at the commit that first adds it with this line changed to FROZEN)
ROADMAP anchor: [§3.4](../../ROADMAP.md#34-x3-one-meaning-regenerates-the-triplets-weeks-14);
§1 rule 4; §10 (quiet-machine hours); DR-018; DR-021; DR-008.

Design: [experiments/x3-generator/DESIGN.md](../../../experiments/x3-generator/DESIGN.md), cited as
"D§n". It is normative for every definition this record cites by section. Revised on 2026-10-16
after two same-family reviews (§12).

Owner authorisation: none recorded as of 2026-10-16. Under the
[collection rule](../README.md#pre-registration-lifecycle-roadmap-1-rule-1-d0-12), no gate data may be
collected until this record is FROZEN and either SIGNED (D0-12) or covered by an explicit Owner
instruction to start X3.
- Building and unit-testing the generator is development, not collection (§4.9).
- The Owner questions in D§14 (Q1–Q18) must be answered and folded into this text before it is
  FROZEN.

Owner decisions this record depends on:
- D0-12, sign-off;
- D0-10d, quiet windows;
- D0-7a, unattended measurement;
- D0-10a, budget;
- D0-3, the comparator lineage.

Until D0-3 is signed, the comparator is **provisional, pending D0-3** (§2).

## 1. Assumption under test, and what follows if it is false

**Assumption** (ROADMAP §3, table row X3): "One meaning plus schedules regenerates the
scalar/AVX2/AVX-512 triplets at parity."

Concretely, one exact meaning of Hearth's Q4/Q8 matmul slot (NUMERICS §3, canonical order), plus
per-ISA schedules built only from DAG-preserving primitives (D§4), must generate C for the six
variants {Q4, Q8} × {scalar, AVX2, AVX-512}. That C must be:
- bit-identical to Hearth's hand kernels;
- non-inferior to them in speed under each release compiler;
- written with schedule text no longer than 30% of the hand-written lines.

**If it is false** (ROADMAP §3, §4): "'One generator replaces the triplets' leaves the plan." Kernels
become explicit-SIMD `.mith` checked by T1. That is the NARROW outcome "X3 kill alone". With an X2
kill as well, the outcome is STOP-L: "No kernel benefit; format, store and ledger alone do not
justify a language [P5 §10.1]".

## 2. Inputs pinned

| Input | Pin |
|---|---|
| Hearth source | `b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220` (GitHub `main`, 2026-10-16), the same pin as X0. Blob ids [M, x3 track, 2026-10-16]: `quant.c` e95496945c25…, `quant_avx2.c` a2004d22fd50…, `quant_avx512.c` 9c7586b16e58…, `hx_quant.h` df7e75e3e14f…, `engine/tests/test_quant.c` b4e9785353c7…, `docs/NUMERICS.md` 7c558db51dd2…, `tests/golden/test_golden_invariants.py` a1acdbaf25f3…. The desktop working tree's uncommitted R3 changes are out of scope |
| Comparator (arm A) | `hearth-c-ref@b5d3f14`: the pristine tree above, built with the release flags. Provisional, pending D0-3. If D0-3 names a different tag before collection starts, a pre-data amendment re-pins it and re-measures H (§4.7) |
| Scratch tree (arm B) | The same tree plus `x3-seam.patch` (D§6), with its SHA-256 recorded at freeze, built with `HEARTH_X3_GEN=ON` |
| Toolchains | Exactly X0's configurations, recorded in `experiments/x0-census/TOOLCHAINS.md`: A, MSVC `cl` 14.44.35207 (release, win-x64); B, `clang-cl` 23.1.3 (proxy for the SysV Clang build, not a release compiler); D, WSL2 `clang` 23.1.3 (release, Linux; bit-identity only). Per-file command lines come from `compile_commands.json` for `CMAKE_BUILD_TYPE=Release`, and every translation unit's expanded `-cc1` line is recorded for both arms |
| Toolchain facts measured by X0 [M, X0 track, 2026-10-16] | Under B: `/O2` expands to `-O3`; `/fp:precise` expands to **`-ffp-contract=on`** and a scalar `a*b+c` became `vfmadd213ss` under `/arch:AVX2` and `/arch:AVX512`; `/arch:AVX2` → `-target-cpu haswell`, `/arch:AVX512` → `-target-cpu skylake-avx512`; `_mm512_dpbusd_epi32` does **not** compile with `quant_avx512.c`'s B flags and does with `-mavx512vnni`. A, C and D do not contract (D§6) |
| Shared flag deviations (provisional, pending D§14 Q8) | B: `-mavx512vnni` on `quant_avx512.c` and `x3_q_avx512.c` in both arms. Only if arm A fails D§7 step 4 under B: `/clang:-ffp-contract=off` in both arms. Each is listed by name before collection |
| Machine | The desktop: Ryzen 9 9950X, Windows 11. The machine-profile hash (06 §5.2), the measurement LP, its SMT sibling and the reserved sampler LP are recorded by the pilot. The laptop is never used for X3 data |
| Generator | `experiments/x3-generator/x3gen` at the commit recorded for each variant. The meaning hash is frozen at the end of sprint week 1; the schedule hash at window close (§4.8). Python and `black` versions are recorded |
| Decode container | Recorded by SHA-256 before collection: the real Qwen3-30B-A3B Q4 container if it is present in the data directory, otherwise the synthetic one (D§14 Q10) |
| Layout variants | K = 3 link-order variants per arm and compiler, built by the harness's link step from the same objects; each variant's SHA-256 and linker map recorded (D§6) |
| Services | The X4 measurement service hash, if used (§7.6). The X2 `mithcheck` hash, if X2 is ready (§4.10) |
| Simulator | `experiments/x3-generator/scripts/oc_sim.py`, SHA-256 `7b9162e9a1159567ff59884458ebe54b1d46b62e1da7606896deac2c5293ab33` (the copy listed in D Appendix C), which produced §6 |
| Seeds | Derived from the SHA-256 of this record's freeze commit (D§8.4). Confirmation uses seeds never used in tuning |

## 3. Arms and configurations

- **Arm A**: hand kernels (`hearth-c-ref@b5d3f14`).
- **Arm B**: generated kernels in the scratch tree.
- Both arms are built by the same compiler with identical flags. Only `hearth_core` differs: the two
  generated Q4/Q8 table entries per ISA, plus the inactive `#ifdef` lines.
- The harnesses (`x3_bench`, `x3_decode`) are the same source in both arms. Each arm and compiler has
  K = 3 layout variants; every block draws one at random for its A runs and one for its B runs
  (D§8.4). All variants sit at paths of equal length and run with the same environment block.

| Set | Configurations | Count | Role |
|---|---|---|---|
| Bit-identity | 6 variants × {MSVC, clang-cl, WSL2 clang} | 18 | gate (G1) |
| Primary throughput | {MSVC, clang-cl} × {scalar, AVX2, AVX-512} × {Q4, Q8}; T = 1; L2-resident; one thread | 12 | **confirmatory** (G2) |
| Decode guard | {MSVC, clang-cl} × dispatched ISA (AVX-512); cached Qwen3-30B-A3B Q4 | 2 | **confirmatory** (G3) |
| Descriptive | L2 T = 8 (12); decode with `isa = avx2` (2); the one-binary layout control (D§8.6); the B-gnu bracket arm (D§6); per-call trace runs (D§8.2); `test_quant`'s bench table; census diff; llvm-mca [S] | — | reported, never gated, run only if quiet hours remain |

ROADMAP §3.4 measures the Clang arm with clang-cl on this desktop. Every clang-cl number is labelled
"proxy for SysV Clang".

## 4. Units and counting rules (defined before data)

1. **Variant.** One generated function `hx_x3_mm_{q8,q4}_{scalar,avx2,avx512}` with the
   `hx_matmul_fn` contract (`hx_quant.h:49-57`). The table holds exactly six [M at build: the script
   checks the count].
2. **Admissible variant.** It must meet all of:
   - generated by x3gen from the frozen meaning;
   - only primitives P1–P15 applied (D§4.2);
   - the global checks C1–C4 pass (D§4.3), with the checker having rejected all 28 planted lane
     programs and accepted the six hand-kernel transliterations (D§4.5);
   - zero uses of a banned item B1–B12 (D§4.4), by the provenance lint;
   - the C is byte-identical to the printer's output, with no hand edits, and passes printer rule 5
     (one FP operation per C full-expression, D§5.1);
   - built with the pinned flags.
3. **Bit-identical.** All nine steps of the protocol in D§7 pass for the variant under the compiler
   concerned (step 9 only if X2 is ready). Step 4: `test_quant --no-bench` reports 0 failures and a
   check count **equal to arm A's count** under the same compiler on the same machine. For context,
   117,681 checks at T02-kernels-gen-002 [R11]; that is not a threshold.
4. **Run, block, block statistic.**
   - **Run.** One fresh process. Micro: its timed segment is exactly two `hx_now_ns` reads around R
     kernel calls, with nothing else in the loop (D§8.2). Decode: T is the increase of
     `hearth_stats.wall_s` over 256 timed tokens, with logits hashed outside it (D§8.3). Its time is
     T in seconds.
   - **Block.** Four runs, in ABBA or BAAB order, for one configuration. Pair 1 is positions (1, 2)
     and pair 2 is positions (3, 4).
   - **Block statistic.** d = ½[ln(T_B^(1)/T_A^(1)) + ln(T_B^(2)/T_A^(2))], where the superscript is
     the pair.
   - **Throughput ratio.** ρ = throughput_B / throughput_A ≈ e^(−E[d]).
5. **Primary shape** (D§8.2). n = 4096 columns; T = 1; Q4 240 rows (522,240 B); Q8 112 rows
   (473,088 B) [D from `test_quant.c:1526-1537`]; weights filled as in `test_quant.c:1452-1456`.
   R is fixed per configuration by the pilot so that an A run's timed segment lasts about 10 s
   [target].
6. **Cached decode** (D§8.3). A run counts only if `cache_misses` grows by 0 over its timed segment,
   `hearth_model_info.isa` is AVX-512, `n_threads` equals the pilot's value, and B's per-step logits
   hashes equal A's.
7. **Lines.**
   - H = **303** [M, x3 track, 2026-10-16]: X3-LOC-C over the closure of the dispatched Q4/Q8 entries
     in `quant_avx2.c` (129) and `quant_avx512.c` (174) (D§9.1–§9.2; script in D Appendix A).
   - S is X3-LOC-PY over `x3gen/hearth/` excluding `meaning.py` and `tests/`, plus any lint-flagged
     library lines and tuned-parameter entries (D§9.1).
   - **S_max = ⌊0.30·H⌋ = 90** [target, D].
8. **Tuning window** (D§10). It opens at T_start = min(T0, the start of sprint week 3) and closes at
   T_start + 14 calendar days.
   - T0 is the first x3gen commit at which all six variants pass D§7 steps 1–7 under MSVC and
     clang-cl.
   - The schedules are frozen by hash at window close.
9. **Gate data versus development data.** Gate data are:
   - (i) the pilot A/A blocks;
   - (ii) the confirmatory A/B blocks, run only on frozen schedules after window close;
   - (iii) the D§7 protocol run after window close.

   Everything else is development or exploratory data. It is labelled as such and never used by the
   verdict script.
10. **X2 ready.** Both must hold before the confirmatory phase starts:
    - X2's `mithcheck` spike has a frozen hash;
    - the X2 record or report states that T1 accepts all of Hearth's hand Q4/Q8 AVX2 and AVX-512
      variants.

    Otherwise G5 does not apply, and the report says "T1 not run".
11. **X4 states.** live-calibrated, live-uncalibrated or fallback, as in D§8.6, recorded when the
    confirmatory phase starts. **Non-inferiority calibration** means a planted-regression
    calibration (ROADMAP §3.5's rule: ≤ 2 of ≥ 100 sessions per level reach 20, sessions run to N)
    that has passed on the same harness binary hashes and run type as X3's data (D§8.6).
12. **N consumption.** Each valid A/B block of configuration k consumes 4·t_run,k of N_k.
    Calibration, sentinel and void blocks consume none. So N_k holds L_k = 3·n_k A/B blocks [D:
    N_k = 2 × n_k × 4·t_run,k × 1.5]. Wall-clock hours are reported beside. Whether ROADMAP §10's
    c ≈ 1.5 should count toward N is D§14 Q14.
13. **t_run.** Per run type and compiler, the median wall time of the pilot's A/A blocks (first run's
    start to last run's end) divided by 4, frozen at pilot end (D§8.5).
14. **Session.** A contiguous stretch inside one quiet window, for one compiler and run type: 2 A/A
    calibration blocks per active configuration, then at most n_k A/B blocks per active
    configuration, plus one A/A sentinel per 4 A/B blocks, interleaved at random (D§8.4). Decisions
    are taken only at the end of a valid session (§7.4).

## 5. Metrics

**Primary (gate inputs)**

| ID | Metric | Unit |
|---|---|---|
| G1 | Bit-identity: every variant is admissible and bit-identical under MSVC, clang-cl and WSL2 Clang | pass/fail × 18 |
| G2 | Primary throughput non-inferiority: the pass e-process K_k per primary configuration, under §7.4's rules, plus the non-inferiority calibration status (§4.11) | e-value × 12 |
| G3 | Decode non-inferiority: K_k per decode configuration, likewise | e-value × 2 |
| G4 | Schedule text S against S_max = 90 | lines |
| G5 | If X2 is ready: T1 verdict on the four SIMD lane programs (Q4/Q8 × AVX2/AVX-512) | accept/reject × 4 |
| G6 | Banned-primitive uses in gate variants | count |

**Secondary (reported; no threshold)**
- Per configuration:
  - the regression wealths M97 and M90;
  - the point ratio exp(−mean d) and the clipped ratios exp(−mean x) and exp(−mean x^θ);
  - outlier blocks beyond c_pass, slow and fast;
  - the point ratio per layout variant, and the "layout-sensitive" label (D§8.6);
  - estimand conflicts (§7.4);
  - A/B blocks run, the block index of each decision, N_k in blocks, wall-clock hours.
- The pilot quantities σ̂_AA, Q99, c_pass, a_reg, t_run and n_k per run type and compiler, and the
  OC table recomputed at σ̂_AA (§6).
- Void counts and void rate by reason (load gate, sibling, clock probe, calibration envelope,
  sentinel, trend, median envelope, cache miss, assertion, output hash).
- S_tok/H_tok (H_tok = 4,188 [M]); M, L and I in lines; (M + S)/H; generated C lines per file.

**Descriptive**
- The T = 8 L2 ratios.
- The AVX2 decode ratio.
- The one-binary layout-control ratios and the B-gnu bracket-arm ratios.
- `test_quant`'s built-in bench table (labelled "not interleaved").
- Census diff of hand and generated hot loops.
- llvm-mca block throughputs [S].
- Absolute GB/s, as context only. For comparison: 69.6 GB/s (measured, busy machine) [R11].

## 6. Sample and power

- **Design.** Sequential. Each confirmatory configuration runs anytime-valid betting e-processes
  (§7.3) until a decision (§7.4) or its limit N_k. There is no fixed n.
- **Plan** (ROADMAP §10, quoted). "Hours per attempt ≈ Σ over confirmatory configurations of
  n × 4·t_run × c, with n = max(6, 12·σ_d²/δ²) blocks at δ = 3% … and c ≈ 1.5 for NVMe
  cool-downs." With t_run = 13 s micro and 15–40 s decode [inference, D§8.7]: 1.9–2.4 h at
  σ_d = 1–2% and 6.8–8.7 h at σ_d = 4% [D]. Each configuration's n_k, N_k and L_k are recomputed by
  the frozen rule from the pilot's σ̂_AA and t_run (or X4's); that is not an amendment.
- **Expected and worst-case quiet hours** (D§8.7), including calibration and sentinel blocks,
  session-end decisions and the pilot: at true parity 4.6–6.4 h (σ_d = 1%), 7.5–9.9 h (2%) and
  13.4–17.5 h (4%) [S + D]; at a true ratio of 0.99, 6.5–26.3 h [S + D]; worst case, every
  configuration through the full inconclusive path, 19.0–71.8 h [D].
- **Floor.** No Pass, R97 or R90 is declared before 6 valid A/B blocks, that is at least 12 runs per
  arm, which meets ROADMAP §3.4's "≥ 10 runs per arm [P5]". That figure is a floor only. **No
  fixed-n test, interval or point estimate is ever a gate input.**
- **Operating characteristics** [S]: `oc_sim.py` (§2; D Appendix C), 3,000 replicates per row,
  seed 20261016, run by the x3 reviser on 2026-10-16. Model: d = −ln ρ + Gaussian noise of SD σ_d;
  the pilot is simulated (20 A/A blocks micro, 10 decode); L = 3n; Monte Carlo SE ≤ 0.009 [D].
  Per configuration (micro; decode within 0.035 of these rows, D§8.8):

  | σ_d | True ratio | P(Pass), first N | P(Pass), after the inconclusive path | P(R97) | P(R90) |
  |---|---|---|---|---|---|
  | 1% | 1.00 | 1.000 | 1.000 | 0.000 | 0.000 |
  | 1% | 0.99 | 1.000 | 1.000 | 0.000 | 0.000 |
  | 1% | 1/1.03 | 0.002 | 0.012 | 0.001 | 0.000 |
  | 1% | 0.97 | 0.001 | 0.005 | 0.003 | 0.000 |
  | 1% | 0.95 | 0.000 | 0.000 | 1.000 | 0.000 |
  | 1% | 0.90 | 0.000 | 0.000 | 1.000 | 0.000 |
  | 1% | 0.85 | 0.000 | 0.000 | 0.000 | 1.000 |
  | 2% | 1.00 | 1.000 | 1.000 | 0.000 | 0.000 |
  | 2% | 0.99 | 0.900 | 1.000 | 0.000 | 0.000 |
  | 2% | 1/1.03 | 0.002 | 0.009 | 0.000 | 0.000 |
  | 2% | 0.97 | 0.001 | 0.007 | 0.005 | 0.000 |
  | 2% | 0.95 | 0.000 | 0.000 | 1.000 | 0.000 |
  | 2% | 0.90 | 0.000 | 0.000 | 1.000 | 0.000 |
  | 2% | 0.85 | 0.000 | 0.000 | 0.000 | 1.000 |
  | 4% | 1.00 | 0.988 | 0.999 | 0.000 | 0.000 |
  | 4% | 0.99 | 0.863 | 0.983 | 0.000 | 0.000 |
  | 4% | 1/1.03 | 0.020 | 0.026 | 0.010 | 0.000 |
  | 4% | 0.97 | 0.010 | 0.014 | 0.018 | 0.000 |
  | 4% | 0.95 | 0.000 | 0.000 | 0.988 | 0.000 |
  | 4% | 0.90 | 0.000 | 0.000 | 0.993 | 0.007 |
  | 4% | 0.85 | 0.000 | 0.000 | 0.000 | 1.000 |

  Gate level, 12 micro and 2 decode configurations at one common true ratio, assumed independent
  [S + D]:

  | σ_d | True ratio | P(gate Pass), first N | P(gate Pass), after the full path | Same under the L = 2n reading of N |
  |---|---|---|---|---|
  | 1% | 1.00 | 1.000 | 1.000 | 1.000 / 1.000 |
  | 1% | 0.99 | 1.000 | 1.000 | 0.982 / 1.000 |
  | 2% | 1.00 | 0.995 | 1.000 | 0.535 / 1.000 |
  | 2% | 0.99 | 0.231 | 0.996 | 0.000 / 0.764 |
  | 4% | 1.00 | 0.822 | 0.990 | 0.546 / 0.982 |
  | 4% | 0.99 | 0.118 | 0.751 | 0.009 / 0.464 |

  In these runs no configuration at 1.00 or 0.99 reached R97 or R90, so P(amber (b)) =
  1 − P(gate Pass) in those rows. With 5% symmetric outliers at 5σ_d (σ_d = 2%), P(Pass | 1.00) is
  0.946 in the first N and 0.999 after the path, and P(Pass | 0.97) is 0.008 (D§8.8).
- **Power target** [target]: gate-level P(Pass | true parity) ≥ 0.8 after the full inconclusive
  path. It holds at σ_d ≤ 4% in the table above, under both readings of N [S]. Before the first A/B
  block, `oc_sim.py` is re-run at the pilot's σ̂_AA and the result recorded. If the target fails
  there, the report says so before any A/B data, and the Owner decides whether to proceed under this
  record or replace it with a new signed record (ROADMAP §1 rule 1; D§14 Q15). At a common true
  ratio of 0.99 with σ_d = 4% the gate-level value is 0.751 [S]; ROADMAP §10's n-formula understates
  bounded-bet sample sizes there (D§14 Q15). This record does not lengthen N.
- **False pass.** For one configuration at the non-inferiority boundary, P(K ever reaches 20) ≤ 1/20
  (Ville), over both attempts, because the inconclusive path carries the wealth forward (§7.5): the
  product is a test supermartingale for the composite null "every evaluated variant is inferior".
  This assumes blocks are exchangeable given the past, which X4's calibrations test. The gate needs
  all 14 throughput configurations to pass, so a false gate pass needs every truly inferior
  configuration to pass falsely, and the gate-level false-pass probability is ≤ 1/20. Simulated: at
  most 0.026 per configuration at the β boundary and 0.014 at the ROADMAP boundary [S].
- **False kill.** For one configuration at a true ratio of exactly 0.90, P(M90 ever reaches 20)
  ≤ 1/20 over both attempts. No multiplicity correction is made across the 12 primary
  configurations (D§14 Q4). Family-wise the union bound is 12/20 only if every configuration sits
  exactly at 0.90; the true probability falls quickly as ratios move above 0.90. Simulated: at most
  0.007 per configuration at 0.90 [S].
- **Time to pass.** When X4 publishes median and 90th-percentile time-to-pass at parity for the
  microbenchmark and end-to-end run types (ROADMAP §3.5), those figures are reported beside the
  plan.

## 7. Analysis procedure

All verdicts come from deterministic scripts in `experiments/x3-generator/scripts/`. The scripts'
commit hash is recorded in the result manifest. Agents run them and never judge (ROADMAP §1 rule 3).

| Script | Input | Output |
|---|---|---|
| `count_lines.py` | Hearth b5d3f14; x3gen tree | H, S, H_tok, S_tok, lint report |
| `bitid.py` | Build trees, binaries | D§7 steps 1–9 results; per-variant G1; G6 |
| `ab_session.py` (fallback only) | Binaries and layout variants, configuration list, seeds | Run and session records (D Appendix B) |
| `eprocess.py` | Run and session records; the frozen pilot quantities | K, M97, M90 per configuration and block; sentinel e-values; voids; N consumption |
| `oc_sim.py` | σ̂_AA per run type and compiler | The OC table at the pilot's σ̂ (§6) |
| `verdict.py` | This record's thresholds block (§7.1), the outputs above | The verdict record (D Appendix B) |

### 7.1 Thresholds (machine-readable; the verdict script reads this block)

```json
{
  "experiment": "X3",
  "hearth_commit": "b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220",
  "delta": 0.03,
  "beta_ni_log_time": 0.029558802,
  "theta97_log_time": 0.030459207,
  "theta90_log_time": 0.105360516,
  "e_threshold": 20,
  "pilot_sigma_rule": "sigma_aa = sqrt(mean(d^2)) over the pilot A/A blocks of the run type and compiler",
  "q99_rule": "empirical 0.99-quantile of |d| over the same blocks, linear interpolation (type 7)",
  "t_run_rule": "median pilot A/A block wall time (first run start to last run end) / 4",
  "pilot_quantities_frozen_at": "start of the confirmatory phase",
  "c_pass_rule": "max(q99, theta97 + 3 * sigma_aa)",
  "pass_statistic": "x = d if |d| <= c_pass else c_pass",
  "a_reg_rule": "max(q99, 4 * sigma_aa)",
  "regression_statistic": "v = clamp(d - theta, -a_reg, a_reg) for theta in {theta97, theta90}",
  "betting": "aGRAPA: lambda = clip(m / (s2 + m^2), 0, cap); m, s2 running with one pseudo-observation",
  "bet_cap_fraction": 0.9,
  "bet_caps": { "K": "0.9 / (c_pass - beta)", "M97": "0.9 / a_reg", "M90": "0.9 / a_reg", "sentinel": "0.9 / a_reg" },
  "pseudo_observation": { "K": ["beta", "sigma_aa^2"], "M97": [0, "sigma_aa^2"], "M90": [0, "sigma_aa^2"], "sentinel": [0, "sigma_aa^2"] },
  "sentinel_test": "E = (E_plus + E_minus) / 2 on v = clamp(d, -a_reg, a_reg), per session; E >= 20 voids the session",
  "blocks_plan": "max(6, ceil(12 * sigma_aa^2 / delta^2))",
  "hours_plan": "n * 4 * t_run * 1.5 / 3600",
  "N_rule": "2 * hours_plan",
  "N_consumption": "4 * t_run per valid A/B block; calibration, sentinel and void blocks consume none",
  "L_blocks_rule": "3 * n",
  "session_ab_blocks_rule": "min(n, L - A/B blocks counted in the current attempt), per active configuration",
  "decision_points": "end of each session that passed every void check; all scheduled blocks run",
  "min_blocks_before_decision": 6,
  "precedence": ["R90", "R97", "PASS"],
  "pass_unavailable_after_R97": true,
  "inconclusive_path": { "window_days": 7, "budget": "one more L", "wealth": "carried forward (product)", "threshold": 20 },
  "min_runs_per_arm_fallback_floor": 10,
  "aa_calibration_blocks_per_config_per_session": 2,
  "sentinel_every_ab_blocks": 4,
  "calibration_envelope": "void if m * mean(d^2 over the m opening A/A blocks) / sigma_aa^2 > chi2_quantile(0.99, m)",
  "pilot_aa_blocks": { "micro_per_compiler": 20, "decode_per_compiler": 10 },
  "load_gate": { "units": "per logical processor unless machine-wide", "sample_ms": 250,
                 "sibling_max_pct": 1, "same_ccd_other_lp_max_pct": 5,
                 "machine_pre_2s_mean_pct": 2, "machine_during_mean_pct": 3, "machine_during_max_pct": 10,
                 "defender_indexer_max_pct_of_one_lp": 1 },
  "priority_class": "HIGH",
  "clock_probe": { "when": "before warm-up and after the timed segment", "within_run_max_dev": 0.015, "session_median_max_dev": 0.03 },
  "trend": { "statistic": "stratified Mann-Kendall on time / configuration session median", "p": 0.01,
             "sen_drift_over_session": 0.02, "void_if": "both" },
  "median_envelope": 0.05,
  "layout_variants_per_arm_compiler": 3,
  "trace_runs_gate_input": false,
  "decode_zero_miss_pilot_min_fraction": 0.95,
  "gate_power_target_parity_full_path": 0.8,
  "planted_suite_min": 28,
  "H_loc": 303, "H_tok": 4188, "S_max_loc": 90,
  "tuning_window_days": 14,
  "tuning_start_latest": "start of sprint week 3",
  "primary_configs": 12, "decode_configs": 2, "bitid_variant_compiler_pairs": 18,
  "oc_sim_sha256": "7b9162e9a1159567ff59884458ebe54b1d46b62e1da7606896deac2c5293ab33"
}
```

### 7.2 Block statistics

For each valid A/B block of configuration k, compute d (§4.4) and:
- **Pass test**, loss-scored: x = d if \|d\| ≤ c_pass, else +c_pass (06 §6.2). Outlier blocks count
  as losses for B whichever arm was slow.
- **Regression tests**, centred: v^θ = clamp(d − θ, −a_reg, a_reg) for θ ∈ {θ97, θ90}. The estimand
  is E[θ + v^θ]; under noise symmetric about the true mean it is on the same side of θ as the true
  mean (D§8.5; D§14 Q18).

c_pass, a_reg, σ̂_AA and t_run come from the pilot (or from X4's A/A data for the same harness and
run type when X4 is live) and are frozen when the confirmatory phase starts. They never change
afterwards, even if X4 goes live later.

### 7.3 E-processes

Each configuration's e-processes run over its valid A/B blocks in time order, across valid sessions,
and across both attempts of the inconclusive path (§7.5). Every process uses aGRAPA (Waudby-Smith and
Ramdas, arXiv:2010.09686): W_t = Π_{j≤t}(1 + λ_j·v_j), λ_{t+1} = clip(m_t/(s²_t + m_t²), 0, cap),
m_t = (m_0 + Σ v)/(t + 1), s²_t = (s²_0 + Σ (v_j − m_t)²)/(t + 1), with the caps and pseudo-observations
of §7.1.

- **Pass test K**, H0: E[x | past] ≥ β. v = β − x. **Pass_k ⇔ K reaches 20.** This is ROADMAP's
  e-process "against "ratio < 0.97"" reaching 20, with the boundary taken at the stricter ln(1.03)
  (D§8.5, D§14 Q5).
- **Regression tests**, H0^θ: E[θ + v^θ | past] ≤ θ. **R97_k ⇔ M97 reaches 20**: the anytime-valid
  upper confidence bound on ρ is below 0.97, a confirmed regression. **R90_k ⇔ M90 reaches 20**: the
  upper confidence bound is below 0.90.
- **Sentinels.** Per session, a two-sided aGRAPA test on the A/A sentinel blocks pooled across the
  session's configurations (§7.1). E ≥ 20 voids the session (06 §6.3).
- **Calibration envelope.** The session is void if its opening A/A calibration blocks give
  m·mean(d²)/σ̂²_AA > χ²_{m, 0.99} (06 §6.1 step 2; D§8.4).

### 7.4 Stopping, per configuration, in the confirmatory phase

1. Decisions are taken only at the end of a session that passed every void check, after all of the
   session's scheduled blocks have run.
2. "Reaches 20" means W_t ≥ 20 at some valid A/B block index t ≥ 6 of the configuration's e-process.
   **No Pass, R97 or R90 is declared before 6 valid A/B blocks.**
3. At each session end, in this order of precedence:
   - R90_k: a confirmed ratio below 0.90; the configuration stops;
   - R97_k: Pass becomes unavailable for k for good; M90 keeps running until N_k;
   - Pass_k, only if R97_k has not fired; the configuration stops.
4. If K and M97 have both reached 20 by the same session end, in either order, the configuration is
   R97 and the report records an estimand conflict. No session is voided for this reason.
5. When k's A/B blocks reach L_k (N_k consumed): R97 without R90 is a confirmed ratio below 0.97 and
   not below 0.90; neither K nor M97 at 20 is **inconclusive** (§7.5).

### 7.5 The inconclusive path (ROADMAP §1 rule 4, quoted)

"**Inconclusive is amber, not kill.** If the e-process has not reached 20 after N hours, where N is
twice the hours §10 plans from M0's measured σ_d [target], the configuration gets gap attribution
(counters, `mithc explain`), one bounded tuning window and one more N-hour session. If it is still
inconclusive, a signed record ships the module behind its seam with C as the default, and a scoped
tombstone keeps the question open. A kill needs a confirmed regression: the anytime-valid upper
confidence bound on the ratio falls below 0.97."

For X3:
- **Gap attribution** is D§10's: census diff, llvm-mca [S], the layout-variant ratios, the one-binary
  control and per-call traces from separate descriptive runs. `mithc explain` does not exist yet, and
  Windows counters need an Owner-installed profiler.
- **The bounded tuning window** is 7 calendar days [target, D§14 Q9]. Only the inconclusive
  configurations' schedules may change.
- **The second N-session continues K, M97 and M90 with the wealth carried forward** (product over
  both attempts), on the re-frozen schedules, with a fresh L_k budget, the same frozen pilot
  quantities and threshold 20 (D§8.5). The per-configuration false-pass bound stays 1/20 (§6). A
  carried Pass supports "at least one of the evaluated variants is non-inferior"; the verdict record
  names every schedule hash. The alternative, a split α with threshold 40 per attempt, is D§14 Q17.
- **Week 6.** The path cannot finish by the week-6 Gatekeeper verdict when T_start is at the start of
  week 3 (D§8.6). If it is still open then, X3 is reported as **"amber (b) pending: second session
  for {configurations} scheduled by date D"**, and the final row follows when the path ends. Whether
  ROADMAP §3.7 allows that is D§14 Q16.
- **X3 ships nothing at M0.** "C as the default" means the hand kernels stay, with the scoped
  tombstone `x3_parity_unresolved` (D§13).
- **Kill confirmation for X3** is R90, per X3's own kill clause. R97 alone is amber (a).

### 7.6 X4 service, fallback and calibration

The service is used as in D§8.6.
- In the live-calibrated state, with a non-inferiority calibration on the same harness binaries and
  run type (§4.11), verdicts are final.
- Otherwise a G2 or G3 Pass is **PASS-PROVISIONAL**: it does not satisfy the gate and cannot seed
  M2's schedule space until a non-inferiority calibration on the same harness binaries and run type
  has passed (X4 with `x3_bench`, or X3-local with Owner approval; D§8.6, D§14 Q6). If that
  calibration fails, G2 and G3 are barred (ROADMAP §3.5) until a re-measurement after the fix.
- R97 and R90 stand unless the A/A calibration of the same harness fails, which bars them until a
  re-measurement.
- The verdict is computed in week 6 in every state (ROADMAP §3.7).

### 7.7 Independent re-derivation

A separate agent context re-derives the following from the raw run and session records, the build
logs and §7.1 alone, without the scripts' intermediate state:
- H and S;
- the pilot quantities, every K, M97 and M90 at each decision point, and the voids;
- the outcome row.

Its figures must match exactly.

## 8. Outcomes

**ROADMAP §3.4, copied exactly:**

> - **Gate.** Bit-identical output; the primary metric non-inferior at δ = 3% under every release
>   compiler; decode non-inferior as a guard. Schedule text is at most 30% of the hand-written lines.
>   If X2 is ready, T1 also accepts the generated variants.
> - **Amber.** 90–97% of hand-kernel speed on the primary metric under any release compiler: the gap
>   goes to M2 as a named item with gap attribution.
> - **Kill.** Still < 90% after two weeks of tuning, or bit-identity needs primitives that do not
>   preserve the DAG. "One generator" then leaves the plan, and kernels become explicit-SIMD `.mith`
>   checked by T1.

**ROADMAP §1 rule 4, copied exactly:**

> Non-inferiority holds when the e-process against "ratio < 0.97" reaches 20 [target].

The inconclusive rule is quoted in §7.5.

**Made operational** (precedence: kill over amber over pass):

| Outcome | Condition | Action |
|---|---|---|
| **Pass** | All of: G1 passes for all 18 variant–compiler pairs; Pass_k (§7.4) for all 12 primary configurations and both decode configurations; a non-inferiority calibration has passed on the same harness binaries and run type (§4.11); S ≤ 90; G5 accepts all four if X2 is ready; G6 = 0 | "One meaning plus schedules" stays in the plan. P_X3 seeds M2's KIR schedule space (02 §8). Ledger record and report |
| **Amber (a)**, a confirmed gap of 3–10% | Some primary configuration ends with R97 and without R90 (§7.4), and no kill condition holds | ROADMAP: "the gap goes to M2 as a named item with gap attribution." One item per configuration, with D§10's attribution |
| **Amber (b)**, inconclusive | Some primary or decode configuration is still inconclusive after the full §7.5 path. While the path is open at the week-6 verdict: "amber (b) pending" with the scheduled date | A signed record and the scoped tombstone `x3_parity_unresolved`. Hand kernels stay. The M2 item says "unresolved, σ_d-limited" |
| **Amber (c)**, proposed by this record; ROADMAP is silent (D§14 Q3) | (i) Decode guard R97 or R90, or (ii) S > 90, or (iii) G5 rejects a variant because of T1 incompleteness, shown by an independent DAG diff that finds the variant equal to the meaning | A named M2 item per cause. **Pending the Owner's answer before FROZEN.** If the Owner rejects this row, the cause is recorded as "gate not met" without a band, and §1 rule 2 is breached; that must be resolved before freeze |
| **Amber (d)**, proposed by this record: pass pending calibration (D§14 Q6) | Every Pass condition holds except the non-inferiority calibration (PASS-PROVISIONAL, §7.6) | Action: the calibration runs. The row becomes Pass when it passes; if it fails, G2 and G3 are barred and re-measured after the fix. M2 may not seed from P_X3 meanwhile |
| **Kill (a)** | After window close, some primary configuration reaches R90; or some (dtype, ISA, release compiler) has no admissible bit-identical variant at window close (counted as < 90%, D§14 Q3) | ROADMAP §4, "X3 kill alone": NARROW. Kernels become explicit-SIMD `.mith` checked by T1. With an X2 kill as well: STOP-L. Write the tombstone `one_generator_for_kernel_triplets` (D§13) from the signed report |
| **Kill (b)** | G6 > 0 for any variant submitted to the gate. Or the report shows, with DAG-diff evidence, that no admissible bit-identical variant can exist for some configuration without a banned item (D§4.4) | As kill (a) |
| **Tooling failure** (not a scientific outcome) | Harness, build, script or service defects; void sessions | Fix, log, re-run (§10). Never an outcome row |

A T1 rejection traced to a real DAG change makes that variant inadmissible. Unless fixed within the
window, it counts toward kill (a).

## 9. Threats to validity

| Threat | Handling |
|---|---|
| Generator and checker share an author, so their bugs can be correlated | Oracles independent of x3gen: `ref_qrow`, the pinned hashes and `memcmp` identities in `test_quant`; the cross-binary corpus (D§7 step 6); T1 if X2 is ready. The checker recomputes identities from load and store addresses and treats lane maps as untrusted hints (D§4.3). Before T0 it must reject all 28 planted lane programs and accept the six hand-kernel transliterations (D§4.5) |
| The checker trusts an unvalidated multi-instruction idiom | C3's bit-vector layer proves each integer-consumer lane by enumeration (≤ 2^16 cases); one named lemma for the AVX2 sign trick; one named multi-op `isa/` entry (`scalar.h2f_bits`), validated over all 65,536 inputs (D§4.3, D§5.1) |
| The test oracle mis-rounds binary32 | `rne_f32` with explicit overflow and NaN handling, tested against compiled C (D§5.1) |
| The corpus violates P1 or P2 | Activation codes and sums come only from the scalar `act_quantize_q8`; special values only in W's bytes, W.d and A.d (D§7 step 6) |
| Code layout and alignment differ between the two binaries | K = 3 link-order variants per arm and compiler, drawn per block; equal-length paths; a fixed environment block; per-variant ratios and a "layout-sensitive" label; the one-binary control for attribution (D§6, D§8.2, D§8.4, D§8.6) |
| Common work inside the timed segment compresses the ratio toward 1 | Two clock reads around the R calls only; traces only in separate descriptive runs; decode timed by `wall_s` with hashing outside (D§8.2, D§8.3) |
| Frequency, thermal and background drift | Quiet windows; the per-LP load gate with sibling and same-CCD voids; the clock probe before and after each run; the calibration envelope; A/A sentinels; trend (p and magnitude) and median-envelope voids (D§8.4) |
| Exchangeability fails, so Ville does not hold | X4 calibrations; a G2/G3 Pass is PASS-PROVISIONAL until a non-inferiority calibration passes on the same harness (§7.6). Simulated one-sided outliers move the tests with the mean of d, as expected (D§8.8) |
| The tests are underpowered, so X3 collapses to amber (b) by construction | Clips sized from the pilot's σ̂ (§7.2); the OC table (§6) published here and re-run at the pilot's σ̂; a gate-level power target (§6) |
| A configuration is re-tested after inconclusive and gets two chances to pass | The wealth is carried forward, so the bound stays 1/20 (§7.5) |
| The clang-cl proxy is not SysV Clang (ABI, flags, CRT, contraction, tuning target) | Labelled proxy; X0's measured differences listed (§2); bit-identity also on WSL2 Clang; the B-gnu bracket arm (descriptive); the tombstone `clang_parity_as_msvc_evidence` keeps the MSVC arm confirmatory |
| clang-cl contraction or missing VNNI enabling (both measured by X0) | Printer rule 5; object FMA scan (D§7 step 3); `-cc1` lines recorded; shared flag deviations listed before data (§2) |
| The meaning is mis-transcribed | Independent review against `NUMERICS.md:38-62` and `quant.c:388-427`; the meaning differential (D§3.5) |
| The benchmark shape is overfitted | B12 bans shape specialisation; `test_quant` covers 26 row counts, 9 column counts and T 1–9 (`test_quant.c:1149-1152`); the decode guard |
| Winner's curse from tuning on the confirmation machine and shape | Schedules frozen before confirmation; fresh seeds; exploratory data never pooled (06 §6.4) |
| Line-count gaming | `black`; the specificity lint; single-intrinsic `isa/` entries with one named exception; the token ratio reported (D§9) |
| Test-count drift | The reference count is arm A's on the same day and compiler |
| Comparator drift (R3, S0) | Pinned to b5d3f14; a pre-data amendment if D0-3 re-pins |
| Same-family reviewers | Logged as "Claude (same family as author; independent context)" (m0/README) |

## 10. Deviation and re-run policy

- **Tooling defects** (harness, build, script, service). Fix, log, re-run. Data from void sessions
  are kept and never pooled.
- **A schedule or primitive change after confirmatory blocks have started** is allowed only inside
  the §7.5 bounded window, and only for inconclusive configurations. Their e-processes continue with
  the wealth carried forward (§7.5); every block's schedule hash is recorded.
- **Any output-hash mismatch on any measured run.** The variant is inadmissible at once and its
  timing data are void. Fix it inside an open window. If no window is open, kill (a) applies through
  "no admissible variant".
- **A toolchain, OS, BIOS, microcode or profile-hash change mid-experiment** voids the affected
  sessions. A re-run happens under the new pin only by a pre-data amendment for the remaining
  configurations.
- **A change to a unit, threshold or configuration set after collection has begun** is an amendment
  marked *post-data*. Verdicts are reported under both the original and the amended rule. Thresholds
  never move once data have been seen (ROADMAP §1 rule 1).
- **Computations under the frozen rules are not amendments**: the pilot quantities, n_k, N_k, L_k
  and the OC table at the pilot's σ̂ (§6).
- **If the decode zero-miss pilot check fails** (fewer than 95% of pilot decode runs with zero
  misses), the decode configuration is amended before any A/B data (D§8.3).
- **Adding a descriptive arm** (for example GCC, or WSL2 timing) is allowed and cannot change the
  verdict.

## 11. Deliverables

| Path | Contents |
|---|---|
| `experiments/x3-generator/x3gen/` | The generator: meaning, schedules, checker, printer, instruction tables, tests, the planted suite and the hand-kernel transliterations |
| `experiments/x3-generator/generated/` | The six generated variants, `x3_gen.h`, and the `.lanes.json` T1 exports, with provenance headers |
| `experiments/x3-generator/patches/x3-seam.patch` | The scratch-tree patch |
| `experiments/x3-generator/harness/` | `x3_bench.c`, `x3_decode.c`, the layout-variant link script |
| `experiments/x3-generator/scripts/` | The scripts of §7, including `oc_sim.py` (D Appendix C) |
| `experiments/x3-generator/results/` | Manifests (hashes of raw blobs kept in the data directory, outside the repo, DR-019), `x3.json` (the ledger record), `verdict.json` |
| `experiments/x3-generator/REPORT.md` | Every number tagged; gap attributions; M2 named items; proposed tombstones; the instruction census of the generated variants (input to X2's table scope) |

## 12. Review log

| Date | Reviewer | Family | Scope | Outcome |
|---|---|---|---|---|
| 2026-10-16 | Reviewer 1: statistics, measurement protocol, quiet-hour cost, calendar | Claude (same family as author; independent context) | This record and D§8, §10, §11, §16 | 15 findings (1 blocker, 9 major, 5 minor); 15 accepted, 0 rejected |
| 2026-10-16 | Reviewer 2: checker soundness, instruction semantics, toolchains, Exo classification, test oracle | Claude (same family as author; independent context) | D§2–§7, §9, §12 | 9 findings (0 blocker, 3 major, 6 minor); 9 accepted, 0 rejected |

All 24 findings were verified against the sources by the reviser (also Claude, a separate context)
before being applied, two with refinements and one with a corrected citation; the per-finding record
is D§17. No finding was rejected, so there are no rejection lines.

Until D0-10c names other families, reviews are logged as "same-family, independent-context", which
is weaker than ROADMAP asks (m0/README).

## 13. Signature block

```text
Owner: ______________________   Date: __________
Signs the record frozen at commit: ________
Owner answers to DESIGN §14 (Q1-Q18) folded in at commit: ________
```

## Amendments

None.
