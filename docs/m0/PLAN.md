# M0 sprint plan

Status: living document, first version 2026-10-16, revision 2 the same day after a same-family
review (§15). The plan track maintains it. Every other track updates its own rows in the
[status table](#12-status-table) in the same change that lands its work.

[ROADMAP](../ROADMAP.md) is authoritative for every gate, amber band, kill and cost. This plan
schedules the work and names who waits on what. It sets no threshold. Where it makes a ROADMAP rule
more precise, it says so and points to the pre-registration record that must carry the precision.
Owner decisions D0-1 to D0-12 belong to Pierce alone. Wherever work has to start before he signs,
this plan says "provisional, pending D0-x", and that work is kept reversible.

**Contents**
0. [Conventions](#0-conventions)
1. [Summary](#1-summary)
2. [Setup as of 2026-10-16](#2-setup-as-of-2026-10-16)
3. [Tracks](#3-tracks)
4. [Dependencies and D0 waits](#4-dependencies-and-d0-waits)
5. [Schedule](#5-schedule)
6. [Machine calendar](#6-machine-calendar)
7. [Owner-hour asks](#7-owner-hour-asks)
8. [Pre-registration schedule](#8-pre-registration-schedule)
9. [Review protocol](#9-review-protocol)
10. [Risk register](#10-risk-register)
11. [Rejected plan options (tombstones)](#11-rejected-plan-options-tombstones)
12. [Status table](#12-status-table)
13. [Owner questions](#13-owner-questions)
14. [Change log](#14-change-log)
15. [Review log](#15-review-log)

---

## 0. Conventions

- **Tags.** The tags are those of [README](README.md#evidence-tags): [M], [D], [S], [G],
  [inference] and [target]. ROADMAP figures keep ROADMAP's label. A table whose caption carries a tag
  applies it to every cell that has no tag of its own.
- **Weeks.** Week 0 (W0) began on Friday 2026-10-16 [M, sprint brief]. Week k runs from the Friday
  7k days after 2026-10-16 to the Thursday six days later. The dates below come from
  `scratchpad/plan/check.py` [D].

  | W0 | W1 | W2 | W3 | W4 | W5 | W6 |
  |---|---|---|---|---|---|---|
  | 10-16..10-22 | 10-23..10-29 | 10-30..11-05 | 11-06..11-12 | 11-13..11-19 | 11-20..11-26 | 11-27..12-03 |

  | W7 | W8 | W9 | W10 | W11 | W12 |
  |---|---|---|---|---|---|
  | 12-04..12-10 | 12-11..12-17 | 12-18..12-24 | 12-25..12-31 | 2027-01-01..01-07 | 01-08..01-14 |

- **Two cadences.** *Plan A* runs at ROADMAP's peak owner rate of about 33 h/week [inference, ROADMAP
  §10], with the verdict in W6. *Plan B* runs at 15 h/week and takes about 13 weeks
  [inference, ROADMAP §10]: 195 h / 15 h per week = 13 weeks [D]. Gates hang on deliverables, not
  dates (ROADMAP §2), so the cadence moves dates and never moves a threshold.
- **Operative schedule until D0-10b is signed: Plan B** (provisional, pending D0-10b). This matches
  [D0_BRIEF](../D0_BRIEF.md) D0-10b item 7, which says the team plans to ROADMAP's 15 h/week stretch
  case until Pierce signs. Builder work that needs no Owner hours runs at the same pace under both
  plans. The plans differ in when Owner-bound steps land: signatures, freeze commits, and the X1
  suite and X2 table reviews. If Pierce signs about 33 h/week, Plan A applies. Any other signed rate
  is re-planned at the next checkpoint. Both plans have checkpoints (§5.1, §5.2), owner tables (§7.1,
  §7.2), a night calendar (§6.3) and freeze/sign weeks (§8).
- **Status words** (status table): `todo`, `doing`, `blocked: <what>`, `draft`, `frozen@<commit>`,
  `signed@<date>`, `done`, and `verdict: pass | amber | kill | narrowing | waits`.
- **Roles in this sprint.** *Builders* are the track agents, which write code, records and reports.
  *Reviewers* are independent agent contexts with an adversarial brief (§9). The *Gatekeeper* is
  made of deterministic scripts in `experiments/<exp>/` plus the Owner's signature; agents may run
  those scripts but never judge (ROADMAP §1 rule 3). The *Owner* is Pierce. Commits, freezes and
  signatures are made by Pierce or by a session he has authorised to commit. No track agent commits.
  Every freeze therefore waits for a commit slot (R26).
- **Rules freeze, then fill-in** (used in §8). Where a record needs a value that comes from data, the
  record is FROZEN with the **rule** that computes the value and a placeholder for the value. This
  happens before any data the rule reads, and before any development data the record's counting
  rules could be tuned to. The value is filled in later by a dated amendment (README lifecycle). The
  amendment cites the rule, names the data it read, and states that no data the record *judges* has
  been seen. The Owner signs the record at the fill-in commit.

---

## 1. Summary

M0 decides, before the expensive parts exist, whether Mithril continues as a language, narrows, or
becomes tools over Rust/C (ROADMAP §4). Five experiments (X0–X4), the core-calculus note (CC) and the
owner decisions (D0) feed a verdict that the Gatekeeper computes and the Owner signs.

Three resources bind, in this order [G]:

1. **Owner decisions, above all D0-10.** D0-10 approves the budget, the cadence, the harness model
   families and the quiet windows. Without it no metered API spend is approved, no second model
   family exists and no quiet night is scheduled. X1's kill needs at least two frontier families
   (ROADMAP §1 rule 5). X1's task authors must come from a different family than the card editors,
   and its planted Dc corpus from a family other than `mithi`'s author (05 §13, ROADMAP §3.2). X4's
   blind batch needs an Adversary from another family. CC and X2's lockstep proof need a Prover from
   another family. Every agent today is a Claude model [M, sprint brief]. **Until D0-10 lands and a
   second family is provisioned, the team can build but cannot evaluate any gate except X0's, and
   X0's only once its record is SIGNED.**
2. **Owner hours.** About 195 h in total [inference, ROADMAP §3.7], about 33 h/week at peak
   [inference, ROADMAP §10]. ROADMAP §10 says owner time goes to table entries, the X1 suite,
   pre-registrations and D0. Of those, reviewing the X1 suite and the X2 semantics table is the longest
   owner-bound chain [G]. Freeze commits and signatures also queue on Pierce (R26).
3. **Quiet-machine nights on the shared desktop.** ROADMAP §10 gives about 60–215 quiet hours, or
   8–27 nights of 8 h [inference]. The reconstruction in §6.2 gives the following [D]:
   - 60.3 h at σ_d = 2% and 221.0 h at σ_d = 4% when A/A sessions last about one planned test;
   - 90.9 h and 333.4 h when every A/A session runs to the amber limit N.

   The plan therefore asks for nights as D0_BRIEF D0-10d recommends: 7 a week from W2. A derived rule
   (§6.3) lowers that rate once the noise pilot has measured σ_d (provisional, pending D0-10d). At
   4 nights a week and σ_d = 4%, the planted-regression calibration finishes on the last night of W6
   with no slack, and X3's verdict, which needs that calibration (§3.4), lands in W7 [D, §6.3].

**Critical path** [G]. At Plan A cadence: D0-10 (W0) → second family provisioned (W1) → X1 suite,
sealed reserve and planted corpus (W1–W3) → CC's X1-subset rules frozen and `mithi` precondition (W3)
→ X1 held-out runs (W4–W5) → M0 verdict (W6). At Plan B cadence, which is operative until D0-10b is
signed, the X1 suite review sets the path and the verdict lands around W12. X2 runs in parallel. Its
verdict date depends on Q9: at the end of calendar W6 (Plan A, or Plan B-cal in §7.2), or in the
scheduled verdict week.

**What the team does this week without the Owner** [G]:
- X0 collection (the Owner's instruction of 2026-10-16 authorises it once its record is frozen; see
  [X0-census](prereg/X0-census.md));
- drafting every pre-registration record, with the rules parts of X1-heldout, X2-gate, X3-parity and
  X4-calibration ready for an early freeze (§8);
- building X1's grammar, cards, `mithi`, tooling kit and harness;
- X2's semantics-table schema, rewrite-rule proofs (Z3 or exhaustive binary32 on the laptop),
  transliteration and checker spike;
- X3's generator design (code from W1);
- X4's measurement service, sandbox, the **desktop job wrapper** (§6.1), catalogue hack batch, MIN-bytes
  oracle, simulator Forge and revisit prototype;
- the core-calculus note.

None of this collects data under an unsigned record.

---

## 2. Setup as of 2026-10-16

Facts tagged [M, brief] were measured by the orchestrator and given to this track in the sprint
brief. The plan track did not re-measure them. Facts tagged [M, plan] were observed by the plan
track on 2026-10-16, at the time given.

| Item | Fact | Tag |
|---|---|---|
| Laptop | Windows 11, Ryzen 9 7940HS (Zen 4, AVX-512), 62 GB RAM; no C compiler installed; shared with a benchmark until 19:00 PT today | [M, brief] |
| Desktop | Ryzen 9 9950X (Zen 5), 62 GB RAM, RTX 5070; MSVC 14.44; WSL2 Ubuntu 24.04 with GCC 13.3; CMake; reached over SSH | [M, brief] |
| Desktop limits | Mithril jobs capped at 8 threads; < 500 MB of new data on C:; big data on D:, a slow USB HDD; other projects run there; quiet windows are negotiated with Pierce. This plan reads the 8-thread cap as an **aggregate** over all Mithril jobs, not a per-job cap (Q2) | [M, brief]; reading [G] |
| GPU | The RTX 5070 belongs to another project's queue; Mithril never uses it | [M, brief] |
| Measurement host | The desktop, per D0-8's recommendation. **Not decided:** provisional, pending D0-8 | [M, brief]; decision open |
| Hearth | GitHub `main` = `b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220`, committed 2026-10-05T23:15:13−04:00, equal to the desktop's HEAD | [M, plan: `git log` on the read-only clone]; HEAD equality [M, brief] |
| Hearth clone size | 5.9 MB including 1.6 MB of `.git` (the read-only scratch clone) | [M, plan: `du`, 11:41 PT] |
| Hearth working tree | 21 uncommitted R3 entries on the desktop (17 modified, 4 untracked), not on GitHub | [M, brief] |
| Hearth simulator | `hearth.sim` is Python and needs only numpy (Hearth `docs/SIMULATOR.md`), so it runs on the laptop | [M, plan: read] |
| Model families | All agents are Claude models; no second family is provisioned | [M, brief] |
| X0 toolchain | LLVM (portable) download and XED build in WSL in progress. The X0 track's scratch scripts name LLVM 23.1.3 and XED tag v2026.08.23. The plan track has not verified that either is installed; [TOOLCHAINS.md](../../experiments/x0-census/TOOLCHAINS.md) is authoritative once written. It did not exist at 11:40 PT | [M, brief] for "in progress"; versions [M, plan: read scripts]; install unverified; TOOLCHAINS.md absent [M, plan: `find`, 11:40 PT] |
| X0 scripts | `experiments/x0-census/scripts/` holds `x0_extract.py`, `x0_decode.py`, `x0obj.py`, `x0_flags.py`, `runbook/` and `smoke/`; `x0_decode.py` defaults to 8 parallel XED processes (`-j`, line 153) | [M, plan: `find` and read, 11:40 PT] |
| Paths the tracks created | `experiments/x0-census/`, `experiments/x1-harness/` (with `power/`), `experiments/x2-semantics/` (with `semantics/`), `docs/m0/core-calculus.md` | [M, plan: `find`, 11:40 PT] |
| D0 brief | `docs/D0_BRIEF.md` was absent at 11:25 PT. It was present at 11:40 PT (file time 11:35 PT), status DRAFT | [M, plan: `find`, `ls`] |
| Claude Code plan | Max plan. At 18:17Z: weekly all-models 10%, 5-hour 3%. At 18:45Z: weekly 13%, 5-hour 16%, 5-hour reset at 22:59:59Z; extra usage disabled | [M, plan: `get_usage`, 2026-10-16T18:17Z and 18:45Z] |

---

## 3. Tracks

Each track lists its deliverables, its ROADMAP gate, its budget (ROADMAP's figures, [inference]),
the tracks it depends on, the D0 items it waits on, and what it can do now. Proposed paths are
proposals; where a track has already created a path, this plan adopts it.

### 3.1 X0: instruction census (ROADMAP §3.1, weeks 0–1.5)

- **Deliverables.**
  - The [X0-census](prereg/X0-census.md) record, frozen before the first Hearth object is compiled.
  - `experiments/x0-census/TOOLCHAINS.md`.
  - `results/census.json` and `REPORT.md`.
  - An independent re-derivation of P1–P5 by a separate agent.
  - **The census handoff to X2:** `census.json` frozen by SHA-256, together with the record's
    FP-sensitivity classification (X0 record §4 item 4). X2's table scope and fuzz iclass set name
    that hash (§3.3).
  - The loop-correspondence patterns, handed to X2's lockstep proof.
  - A draft flag-defect issue if one is found, which the Owner decides whether to file.
- **Gate, amber, narrowing.** As in ROADMAP §3.1, made operational in the record's §8. The narrowing
  is judged jointly with X2, in X2's verdict week.
- **Budget.** $0.5–1.5k and ~10 owner h [inference, ROADMAP §3.1].
- **Depends on.** Nothing upstream. Feeds X2 (scope, fuzz set, loop shapes) and X3 (release-compiler
  codegen facts).
- **Waits on.** Collection is authorised by the Owner's instruction of 2026-10-16, as the record states.
  The Gatekeeper evaluates the verdict only once the record is SIGNED (D0-12), with the signature form
  of D0-9a.
- **Now.** Toolchain setup, scripts, freeze, and compiling configurations A–D on the desktop in
  daytime. In W0, X0 is the only Mithril desktop job and may use all 8 threads. From W1 its jobs go
  through the job wrapper (§6.1) and pass `-j` explicitly to fit their token share.

### 3.2 X1: cold-agent writability (ROADMAP §3.2, weeks 0–5)

- **Deliverables.**
  - The Lark grammar v0.
  - The Tier 0 card (≤ 8 KB [target, ROADMAP §3.2]) and the Tier 1 card.
  - `mithi`, a Rust tree-walking interpreter and type checker (~4–6k lines [inference, P5 §10.1]).
  - The M0 tooling kit: a rust-analyzer `todo!()` shim plus the false-friend lint over Rust
    (~10 owner h and $1–2k [inference, ROADMAP §3.2]).
  - The sealed suite: ≥ 80 items, about 20 for card iteration and ≥ 60 held out
    [target, ROADMAP §3.2], across T-Q4, T-ACTQ, T-NORM, T-ROUTE, T-EVICT, T-STORE, T-FMT and T-CTRL.
    Every oracle kills ≥ 95% of mutants [target].
  - **A sealed held-out reserve** (proposal, for the X1-heldout rules). Family B authors, oracle-checks
    and seals held-out items up to n_max. n_max is the n that the power rule gives at the pre-registered
    conservative σ_ta. The n rule then takes the first n items in a random order whose seed is fixed in
    the rules freeze. 120 is an example n_max [G]. The X1 power simulation's smallest passing n across
    its low, mid, high and stress scenarios is 60, 64, 96 and 100 under the CABW rule [S,
    `experiments/x1-harness/power/results/x1_power_tables.md` §3]. Authored in W2–W3 (Plan A). Owner
    review: Q16.
  - The planted Dc corpus (≥ 100 items [target]), written by a family other than `mithi`'s author.
  - The harness: six arms, 8 checker calls per task [P5]. It must be resumable at attempt level
    (R25).
  - **A Rust arm on the card-iteration items** (proposal, pending Q16 and D0-10a). 05 §13 defines σ_ta
    as the SD of the item-specific *Mithril-minus-Rust* arm effect. ROADMAP §10's card-iteration
    design runs only the 2 Mithril arms, so σ_ta cannot be estimated from it. The Rust arm needs no
    card, so one epoch is enough [G]: 20 items × 5 attempts × 2 families = 200 attempts, $0.1–0.4k
    [D at ROADMAP §10's $0.5–2 per attempt]. If the Owner declines it, the X1-heldout rules use a
    pre-registered prior floor for σ_ta instead. The X1 track proposes the value. For scale, the
    power simulation's scenarios imply σ_ta of 0.11, 0.18, 0.24 and 0.30 [S, same file, §1 at n = 60].
  - The Gatekeeper analysis script (the mixed-effects model of 05 §13).
  - The local-model pilot (10 items × 3 attempts × 2 arms = 60 attempts [inference, ROADMAP §10]).
    Its machine hours under the 8-thread cap are unverified; see the local pilot item below.
  - The report.
  - Paths: `experiments/x1-harness/` (created by the X1 track [M, plan]). The first version's
    `x1-writability/` proposal is withdrawn. The sealed suite, the reserve, reference solutions and
    oracles live **outside any repository**, in the Gatekeeper store (Q5).
- **Gate and kill.** ROADMAP §3.2: Rust − Mithril VP@1 ≤ 15 points and CABW no more than 5 points worse
  than Rust's. Either breach is the kill (STOP-L). Amber triggers (a)–(c) as written there.
- **Budget.** $7–15k and ~55 owner h, including the kit and the checker precondition
  [inference, ROADMAP §3.2]. The measurement share is ≈ 2.9k held-out attempts ($1.4–5.8k) plus
  ≈ 1.2k card-iteration attempts ($0.6–2.4k) [inference, ROADMAP §10]. If the n rule asks for more than
  60 items, the held-out share grows by 48 attempts per item [D, ROADMAP §10: (5 × 3 + 3 × 3) × 2];
  see [COST §1.3](COST.md#13-measurement-budget-inside-the-api-lines).
- **Depends on.**
  - CC: the X1-subset rules must be frozen, and the hand derivations available, before the `mithi`
    precondition.
  - X4: the sandbox, reused for harness isolation [G].
- **Waits on.**
  - D0-10: the budget, the API keys and pinned model versions for at least two frontier families, and
    the choice of local model.
  - **D0-11b, needed in W0**, before family B authors anything (D0_BRIEF D0-11b; ROADMAP lists D0-11
    as needed by M1).
  - D0-12: signatures on the card-iteration, precondition and held-out records before those runs.
  - The location of the sealed store (Q5).
  - Where the Rust and LLVM toolchains for `mithi` and the harness may live (Q4).
- **Now.**
  - Grammar, cards, `mithi` and the kit.
  - The harness, family templates, oracle and mutant infrastructure.
  - Drafting the X1 records, with the X1-heldout rules ready to freeze in W2 (§8).
  - Claude may draft the cards. Task items are authored by the second family once it exists, because
    05 §13 requires task authors from a different family than the card editors. **Proposed:** Claude
    edits the cards and the second family writes the tasks, the reserve and the planted corpus. This
    is provisional, pending D0-10c and D0-11b.
- **Kit cut-off (made more precise; for the X1-heldout record).** The kit's acceptance tests are frozen
  with the X1-heldout rules (W2 in Plan A). The W4 fill-in names a kit commit before the first held-out
  attempt. The kit counts as "ready" only if those tests pass on that commit. Otherwise the arm is
  dropped from X1 and amber (a) waits for M1 (ROADMAP §3.2).
- **Local pilot under the cap.** ROADMAP's 5–10 h assumes "loaded 9950X time" at about 20 tok/s
  [inference, ROADMAP §3.2]. Under the daytime cap of 8 threads, decode may run on one CCD, and one CCD
  caps at 64 GB/s [R08, via 06 §6.7]. Hearth's thread scaling under an 8-thread cap is not verified
  here. Before X1-local-pilot freezes, the pilot's machine hours are re-estimated from a short
  measured tok/s run under 8 threads, in daytime. If agentic attempts then come close to the harness
  time-outs, Pierce chooses between a daytime cap exception and fewer attempts (Q18).

### 3.3 X2: T1/T2 checker spike (ROADMAP §3.3, weeks 0–5, verdict in W6)

- **Deliverables.**
  - Semantics entries for every census iclass, keyed by XED iclass, with an explicit FP-environment
    layer.
  - The Zen 5 fuzz campaign over the FP-sensitive iclasses. Bochs is the second oracle, and the vector
    budget per iclass is pre-registered. Iclasses that Bochs cannot emulate are listed in the record
    as single-oracle (R23).
  - The `mithcheck` spike: T1, which matches FP DAGs modulo the audited exact-rewrite list (with the
    NaN-order side condition), and T2, which discharges ranges (the 3,810 and 32,512 bounds [R07]).
  - Rewrite rules, each proved by Z3 FPA or exhaustive binary32.
  - The lockstep loop rule, extended to the shapes X0 finds, with a written proof reviewed by a
    Prover from a different family.
  - The Q4, Q8, F32 and act-q8 AVX2/AVX-512 kernels, transliterated into intrinsic-level IR with lane
    maps.
  - The `numerics_v1` pool (≥ 200 mutants [target]), with kill rates under G, G+C and T1+T2.
  - The report.
  - Paths: `experiments/x2-semantics/` (created by the X2 track [M, plan]). The first version's
    `x2-checker/` proposal is withdrawn; the X2 track names any further paths.
- **Gate, amber and kill.** As in ROADMAP §3.3: ≤ 30 proved rules, 100% acceptance, 100% FP-mutant
  rejection, zero false accepts. Amber at 31–40 rules adds one week. The kill is judged at the end of
  week 6; see Q9 on what "week 6" means at Plan B cadence, and Plan B-cal (§7.2).
- **Budget.** $3–6k and ~40 owner h, mostly reviewing table entries [inference, ROADMAP §3.3].
- **Depends on X0.**
  - **Scope.** The census union sets the table scope. Until the census lands, table work starts from
    the intrinsic-implied form set (~105 forms and 74 mnemonics [G02]). That scope is provisional and
    is reconciled against `census.json`.
  - **Fuzz iclass set (made more precise; for the X2-fuzz record).** The set is the FP-sensitive
    iclasses of `census.json@sha256:<hash>`, under X0's FP-sensitivity classification. If X2-fuzz
    must freeze before the census hash exists, the set is the FP-sensitive forms of the B_iform scope.
    The record then also carries an amendment rule, written before any vector runs: each iclass the
    census adds gets the same per-iclass vector budget, and is admitted by a dated amendment before
    its first vector.
  - **Amber scope.** X0's amber (> 20 FP-sensitive mnemonics [target]) narrows the table to the
    release compilers (ROADMAP §3.1), so the fuzz set waits for X0's verdict or uses the rule above.
  - **Loop shapes** for the lockstep proof.
- **Waits on.**
  - X0's `census.json` hash and FP-sensitivity classification (above), or the amendment rule.
  - A frozen X2-fuzz record, then SIGNED or covered by an Owner instruction, before any vector runs on
    silicon. Under the README collection rule an instruction suffices. D0_BRIEF's D0-12
    recommendation would require a signature for sampled runs. This is pending D0-12.
  - D0-10: a different-family Prover for the lockstep proof. Daytime desktop use under the 8-thread
    cap is already allowed [M, brief].
  - D0-12: the gate record. Its counting rules freeze early (§8).
- **Mutant sealing (made more precise; for the X2-mutants record).** The `numerics_v1` pool is
  written and hash-committed before T1's rule list is frozen. The pool's contents stay in the
  Gatekeeper store, unseen by the T1 builders, until the rule list is frozen. This stops the rule
  list being tuned to the mutants [G].
- **Gate counting rules (made more precise; for the X2-gate record, frozen by W2).** These are fixed
  before T1 runs on the real variants (W3 in Plan A):
  - what counts as one "rule";
  - what counts as a "per-kernel `assumed` axiom";
  - the test for "a false accept traceable to a fixable table bug";
  - the reading of "end of week 6" chosen by the Owner (Q9).
- **Now.** The table schema, SDM-derived entries for the B_iform scope, the fuzz harness and the Bochs
  build (WSL on the desktop; the plan track does not know whether Bochs is installed there), Z3 proofs
  (venv on the laptop), transliteration, and the checker spike.

### 3.4 X3: one meaning regenerates the triplets (ROADMAP §3.4, weeks 1–4)

- **Deliverables.**
  - A throwaway generator: Python DAG-preserving primitives, or Exo's DAG-preserving subset (Exo has no
    IEEE-exact mode [R05]). It generates scalar, AVX2 and AVX-512 Q4 and Q8 matvec C.
  - A scratch Hearth linked through `hx_kernels`, passing `test_quant` (117,681 checks [R11]) and
    `test_isa_identity`.
  - A/B runs under MSVC and under clang-cl. The clang-cl build is a proxy for the SysV Clang build.
    clang-cl comes from X0's portable LLVM install (R23).
  - A line count for the schedule text.
  - T1 acceptance of the generated variants, if X2 is ready by then.
  - The report. Proposed path: `experiments/x3-generator/` (not created yet).
- **Gate, amber and kill.** As in ROADMAP §3.4. The primary metric is single-thread L2-resident Q4/Q8
  matvec throughput per ISA, non-inferior at δ = 3% under each release compiler [target]. Decode
  serves only as a guard.
- **Reference binary (made more precise; for X3-parity and X4-calibration; Q17).** ROADMAP compares
  against `hearth-c-ref` (§1 rule 4, §3.5). That tag comes from S0, which waits on the R3 commit with
  no date (§3.9). In M0 the stand-in is a **clean checkout of `b5d3f14`**, not the desktop working
  tree with its 21 R3 entries. It is built with Hearth's release flags (the X0 record's
  `compile_commands.json` source) under MSVC, and under clang-cl for the proxy arm. Each binary's
  SHA-256 is pinned in the record. The clean checkout is about 5.9 MB as cloned [M, plan], so it fits
  the C: budget. Build outputs go to D: unless they fit the remaining C: budget. S0's tag is not a
  prerequisite for M0. X3's hand-written arm and X4's planted-regression binary are both this stand-in.
- **Counting rule (made more precise; for the X3-parity record).** "Schedule text ≤ 30% of the
  hand-written lines" counts non-blank, non-comment physical lines. The schedule side is all schedule
  source for the Q4 and Q8 matvec variants. The hand-written side is the corresponding function
  bodies and helpers in `quant_avx2.c` and `quant_avx512.c` at `b5d3f14`, with both lists named in
  the record. This rule is **frozen before the first schedule line is written** (start of W1 under
  both cadences), ahead of the rest of the record. It is a proposal for the X3 track to adopt or
  replace before that freeze.
- **Calibration dependency.** A failed planted-regression calibration bars every parity gate
  (ROADMAP §3.5). The X3-parity record should therefore state that its parity verdict becomes final
  only once X4's microbenchmark planted-regression calibration has passed. Under Plan A with
  calibration nights from W3 [D, §6.3]:
  - at 7 nights a week, X3 is final in W3 (σ_d = 2%) or W5 (σ_d = 4%);
  - at 4 nights a week and σ_d = 4%, planted regression ends on the last night of W6 with no slack,
    and X3, whose decode guard runs next, lands in W7.

  ROADMAP §3.7 says that verdicts other than X4's do not wait, so this is a live conflict. See Q8.
- **Budget.** $1–3k and ~20 owner h [inference, ROADMAP §3.4]. Quiet hours: 2.9 h (σ_d = 2%) to
  10.8 h (σ_d = 4%) per attempt [D, §6.2: X3 microbenchmark plus decode guard], plus tuning re-runs.
- **Depends on.** X4: the measurement service. If the service is not live, ≥ 10 runs per arm
  [P5, ROADMAP §3.4]. X2 is optional (T1 on the generated variants).
- **Waits on.** D0-10d (quiet windows). D0-8 (host; provisional, pending D0-8). D0-12 (the X3-parity
  record SIGNED before the first A/B session). D0-7a or the Owner's consent to unattended night runs
  (Q1). Q17 (reference binary).
- **Now (from W1).** The generator, codegen and bit-identity tests, built in desktop daytime.

### 3.5 X4: evaluator-integrity kit (ROADMAP §3.5, weeks 0–6)

- **Deliverables.**
  - Measurement service v0:
    - the runtime owns the clock, poisons fresh allocations and records a hardware fingerprint;
    - ABAB interleaving behind a load gate, with a stationarity check;
    - the quiet-machine profile;
    - e-values with α accounting;
    - output as `Quantity`;
    - `mithc profile measure` (STREAM per CCD and all-core, and the NVMe request-size × QD grid; see
      Q3 on the data it reads). **It is a measurement**: it runs in a quiet window, after the noise
      pilot, and its all-core STREAM needs more than 8 threads (Q2). See §6.3.
  - **The desktop job wrapper**, due by the start of W1. It is the supervisor's daytime half:
    - an aggregate 8-token semaphore shared by all Mithril desktop jobs, whichever track starts them
      and from wherever, SSH from the laptop included;
    - refusal to start any job inside a declared quiet window;
    - start and end stamps with the token count, which feed COST §2.

    Ad hoc SSH commands that use more than 1 thread are not allowed (§6.1).
  - The sandbox: a Windows Job Object with no network, read-only goldens and supervisor-held limits.
  - The planted-hack suite, **in this order** (made more precise; for the hack records):
    1. The X4-hacks-catalogue record is frozen. It fixes the hack list and each hack's declared stage.
    2. Engineering runs of the catalogue hacks against the unfrozen kit. Their outputs are discarded
       and labelled *development*.
    3. The kit is hash-frozen (end of W2 in Plan A).
    4. In parallel: the gated catalogue run (a) on the frozen kit, after X4-hacks-catalogue is SIGNED,
       and the blind batch (b) written by a different-family Adversary. **A gated catalogue miss on
       the frozen kit is an accepted planted hack, which is HALT-F (ROADMAP §3.5).** The record says so.
    5. The blind run.

    If the Owner prefers the gated catalogue run before the freeze, the freeze and the blind-batch
    commissioning move to W3, and X4-hacks-blind moves a week later (Q20).
  - F1-sim on a scratch `hearth.sim` behind an `hx_policy` shim. The MIN-bytes oracle is validated
    against brute-force OPT on small traces before anything else. **The held-out traces are hash-sealed
    in W1**, before F1-sim development starts.
  - Tombstone import and replay, with the acceptance tests of 06 §7.6, and a `mithc revisit`
    prototype that parses the 06 §7.2 grammar.
  - The calibrations:
    - A/A: ≥ 100 microbenchmark sessions;
    - planted regression: ≥ 100 sessions at 3% and ≥ 100 at 4%;
    - ≥ 20 end-to-end A/A sessions.

    The **A/A stopping rule** is fixed in the X4-calibration rules before the first session (§8). The
    proposal is for the X4 track to adopt or replace [G]:
    - Microbenchmark A/A sessions run to N whatever the non-inferiority e-process does, with
      superiority monitored throughout. This mirrors ROADMAP §3.5's rule that planted-regression
      sessions run to N "so the calibration covers the longest a real parity gate can run". The
      non-inferiority time-to-pass is recorded when e first reaches 20.
    - End-to-end A/A sessions stop at non-inferiority e ≥ 20 or at N, whichever comes first, with
      superiority monitored throughout. Time-to-pass is censored at N.

    Hours under each choice are in §6.2 and Q15.
  - Publication of time-to-pass (median and p90), σ_d per run type and niche, and throughput per quiet
    hour.
  - The prune pilot reproduced.
  - The report. Proposed path: `experiments/x4-integrity/` (not created yet).
- **Reference binary.** The planted-regression calibration runs the M0 stand-in for `hearth-c-ref`
  (§3.4) against itself with an injected slowdown.
- **Gate and kill.** As in ROADMAP §3.5: 100% of both hack batches caught at or before their declared
  stage; ≤ 2 of ≥ 100 for each calibration [target]. An accepted planted hack is HALT-F.
- **Budget.** $3–8k and ~40 owner h [inference, ROADMAP §3.5]. Quiet hours: the bulk of the 60–215
  [inference, ROADMAP §10]; §6.2 gives a reconstruction with a bound.
- **Optional.** The quiet-machine head-to-head of C-Hearth against llama.cpp is context only. **This
  plan defers it** unless nights are left over after the calibrations [G], because it competes for
  the scarcest resource.
- **Depends on.** Nothing upstream for the build. Its calibration parameters (the clip c and the amber
  limit N) come by a frozen rule from the noise pilot, which runs under its own record (§8).
- **Waits on.**
  - D0-7a: unattended runs inside quiet windows. The noise pilot is the first unattended night (W2),
    so D0-7a, or Pierce's consent under Q1, is needed by then.
  - D0-9: (a) the interim signature form, needed with the first signature in W1; (b) per D0_BRIEF,
    the hardware Owner key before the kit hash-freeze (≈ W2).
  - D0-8: the host (provisional).
  - D0-10: quiet windows, the budget, and a second family for the blind batch.
  - D0-12.
  - **Machine-hygiene settings** (power plan, Defender and indexing exclusions). These are Owner
    security trade-offs (06 §6.7). Agents do not change system or security settings; they write the
    checklist, and Pierce applies what he chooses, before the noise pilot.
- **Now.** The service, the job wrapper, the sandbox, the catalogue batch, the MIN/OPT oracle, F1-sim,
  tombstone import and the revisit prototype. The Python parts run on the laptop after 19:00 PT on
  2026-10-16.

### 3.6 CC: core-calculus note (ROADMAP §3.6, weeks 0–5)

- **Deliverables.** The note, at `docs/m0/core-calculus.md` (created by the CC track [M, plan]; the
  first version's `CORE-CALCULUS.md` proposal is withdrawn). `docs/architecture/01` is not edited in
  M0. The note contains:
  - the judgement forms;
  - effects as authority, and grades as fidelity and determinism;
  - the non-escaping kind;
  - projections and `deterministic(by: E)`;
  - deterministic trap semantics;
  - theorem statements.

  It also contains hand derivations of every canonical snippet and a trace from each Tier 0 rule to
  the note.
- **Gate.** As in ROADMAP §3.6. A Prover and an Adversary from another family review it, and the Owner
  signs.
- **Budget.** $1–2k and ~20 owner h [inference, ROADMAP §3.6].
- **Feeds X1.** The X1-subset rules are frozen when the `mithi` precondition runs. A later change that
  would flip an X1 verdict is an amendment that applies from M1 (ROADMAP §3.2).
- **Waits on.** D0-10 (the different-family reviewers) and D0-12 (the Owner's signature).
- **Now.** All drafting.

### 3.7 D0: owner decisions (ROADMAP §11, from W0, ~10 owner h)

- **Deliverable.** `docs/D0_BRIEF.md`, with recommendations and signature lines (README). It is not
  this track's file. It has been present since 11:35 PT [M, plan].
- **Order.** ROADMAP's "needed by" column is kept unchanged. A second column gives the earlier date
  that this plan's own schedule creates. Pierce should order his decisions by that second column.

  | ROADMAP "needed by" (§11) | Item | Needed by in this plan | Why |
  |---|---|---|---|
  | W0 | **D0-10, D0-12** | W0 (D0-10d: windows agreed in W0, first night W2) | budget, families, cadence, nights; signatures |
  | M1 | **D0-11** | **(b) W0**, before family B authors anything | 05 §13; D0_BRIEF D0-11b |
  | X4 | **D0-9** | **(a) W1**, before X0's signature; (b) ≈ W2, before the kit hash-freeze | D0_BRIEF D0-9a ("Week 0, with the first signature") and D0-9b |
  | X4 | **D0-7** | **(a) W2**, before the noise pilot's first unattended night (or Q1 consent) | the pilot runs unattended at night |
  | M4 | D0-8 | W2, for the provisional use of the desktop as host | X3 and X4 measure on it from the pilot on |
  | S0 | D0-2 | not on M0's path | S0 only (§3.9) |
  | M1's S1 | D0-3 | not on M0's path; M0 uses a stand-in for `hearth-c-ref` (§3.4, Q17) | S0 tag |
  | End of M0 | **D0-1** | W6 (Plan A) or ≈ W12 (Plan B) | M0 verdict |
  | S4 / S6a | D0-5 | — | — |
  | M5 | D0-6 | — | — |
  | S6 | D0-4 | — | — |

- **D0-8.** Its "needed by" is M4, but X3 and X4 measure on the desktop in M0, so the plan uses the
  desktop provisionally, pending D0-8. Calibration is per host, so a different choice means
  re-calibrating on the new host, not discarding the X3 and X4 code.
- None of these is decided. Nothing in this plan presents any of them as decided.

### 3.8 M0 verdict (ROADMAP §3.7, §4)

- **Deliverables.**
  - A `prereg/M0-verdict.md` record, frozen and signed **before any experiment verdict is known**
    (planned in W1, before X0's verdict).
  - A deterministic mapping script in `experiments/m0-verdict/`, which reads each experiment's signed
    verdict file and outputs every applicable row of ROADMAP §4.
  - The verdict dossier.
  - The Owner's signature.
- **Proposed mapping (for the record; the ambiguous cases are Q7).**

  ```text
  rows  = []
  state(e) in {pass, amber, kill, narrowing, waits, barred}
  kills = { e in {X1, X2, X3} : state(e) == kill }
  if kills >= {X1, X2}:                    rows += STOP-ALL
  elif X1 in kills:                        rows += STOP-L  (X1)
  if kills >= {X2, X3}:                    rows += STOP-L  (X2 and X3)
  if kills == {X2}:                        rows += NARROW  (X2 alone: N2 dropped; continue only if X1 and X3 pass)
  if kills == {X3}:                        rows += NARROW  (X3 alone: explicit-SIMD .mith checked by T1)
  if X0 == narrowing:                      rows += NARROW  (object audit deferred)
  if X4 == kill:                           rows += HALT-F
  if D0-1 == declined:                     rows += STOP-L  (D0-1)
  bars: a failed A/A calibration bars superiority gates; a failed planted-regression calibration bars
        parity gates (ROADMAP §3.5). Bars are reported beside the rows; they are not rows.
  barred X3: if the planted-regression calibration has failed or is incomplete, X3's parity component
        is barred and state(X3) = barred. A barred X3 is neither pass nor kill. It counts as pending,
        so the verdict waits (provisional, pending Q7).
  X2-alone clause: "continue only if X1 and X3 pass" reads state == pass. An X1 or X3 that is amber,
        waits or barred leaves the clause undecided, and the verdict waits (provisional, pending Q7).
  pending: X4 may be "waits" (ROADMAP §3.7). Any other experiment still pending or barred blocks the
           verdict (gates hang on deliverables, ROADMAP §2).
  output: all rows, plus the most severe class, ordered STOP-ALL > STOP-L > NARROW, with HALT-F
          independent of that order.
  ```

  The M0-verdict record may not freeze while the two "provisional, pending Q7" lines are open.
  Either Pierce answers Q7 first, or the record freezes with these lines as written.
- **Waits on.** D0-1 (needed by the end of M0), D0-12, D0-10 (if declined, there is no M0) and Q7.

### 3.9 S0 (adjacent: Hearth-side, not an M0 gate)

ARCHITECTURE §13 lists the S0 corpus among M0's deliverables, and 07 §4 places S0 in M0. S0 is C-side
work that rests on maintainer and Owner actions:
- committing R3 and repairing the task DAG;
- the constitutional ADRs;
- ADR-0010 (D0-2);
- the `hearth-c-ref@port-base-1` tag;
- the corpus, generated twice (D0-3).

This plan schedules **no agent work on S0** until R3 is committed. S0 is needed by M1's S1, not by the
M0 verdict [inference, ROADMAP §11 "needed by"]. X0's report states whether the R3 working-tree diff
touches a dispatched kernel. M0's measurements use the clean-`b5d3f14` stand-in for `hearth-c-ref`
(§3.4), so they do not wait on S0's tag (Q17).

---

## 4. Dependencies and D0 waits

```text
D0-10 ─┬─> 2nd family + API keys ─> X1 suite, reserve + planted corpus ─> card iteration (+ Rust arm) ─┐
       │                                                                                              ├─> mithi precondition ─> X1 held-out ─> X1 verdict ─┐
       │   CC note ─> X1-subset rules frozen + hand derivations ──────────────────────────────────────┘                                                    │
       ├─> quiet windows ─> noise pilot ─> profile ─> X3 A/B + X4 calibration (records signed) ─> X3, X4 verdicts ─────────────────────────────────────────┤
       └─> different-family reviews (CC, lockstep proof, X4 blind batch, R-diff backlog) ──────────────────────────────────────────────────────────────────┤
X0 census.json (hash + FP-sensitivity) ─> X2 fuzz iclass set + table scope + loop shapes ─> T1/T2 spike ─> X2 verdict ─> X0 narrowing (joint) ───────────────┤
X4 service + job wrapper ─> X3 A/B    X4-hacks-catalogue frozen ─> dev runs ─> kit hash-freeze ─> gated catalogue run ‖ blind batch ─> blind run          │
clean b5d3f14 reference binary (Q17) ─> X3 A/B, planted regression                                                                                        │
D0-12 (+ D0-9a form) ─> every SIGNED record         D0-1 ─────────────────────────────────────────────────────────────────────────────────────────────────> M0 verdict
```

| Track | Can run with no Owner decision | Blocks on | Provisional work (reversible) |
|---|---|---|---|
| X0 | everything, including collection (Owner instruction, 2026-10-16) | D0-12 (with D0-9a) for the verdict | none |
| X1 | grammar, cards, `mithi`, kit, harness, templates, record drafts | D0-10 (2nd family, API, local model), D0-11b (W0), D0-12, Q4, Q5, Q16, Q18 | Claude as card editor and 2nd family as task author, pending D0-10c / D0-11b |
| X2 | table drafts, Z3 proofs, transliteration, T1/T2 spike, mutant generator | **X0 `census.json` frozen (hash) and FP-sensitivity classification** (or the amendment rule of §3.3); fuzz-record signature or Owner instruction; D0-10 (Prover); D0-12; Q9 before the X2-gate rules freeze | B_iform scope until the census lands |
| X3 | generator, codegen, daytime builds and bit-identity tests | D0-10d (nights), D0-7a or Q1, D0-12, Q2, Q17 | the desktop as host, pending D0-8 |
| X4 | service, job wrapper, sandbox, catalogue batch, MIN/OPT, F1-sim, revisit prototype | D0-7a, D0-9, D0-10, D0-12; Owner-applied hygiene settings; Q2, Q3, Q15, Q17 | the desktop as host, pending D0-8; signature form pending D0-9a (Q6) |
| CC | all drafting | D0-10 (reviewers), D0-12 | none |
| M0 verdict | mapping script and record draft | D0-1, D0-10, D0-12; Q7 | the two "pending Q7" lines of §3.8 |

Realistic expectation [G]: if D0-10 slips by k weeks, X1, and with it the M0 verdict, slips by about
k weeks. X0, the build halves of X2–X4 and the CC draft do not slip. Without D0-10 at all, ROADMAP
§11 says there is no M0. If X0 slips past W1, X2's fuzz set and table scope slip with it (R27).

---

## 5. Schedule

### 5.1 Plan A: ~33 owner h/week, verdict in W6

The dates are W0 = 2026-10-16 onward [D]. The phases are [G], aligned with ROADMAP §2's [inference]
timeline. Plan A applies only if Pierce signs about 33 h/week under D0-10b; until then Plan B (§5.2)
is operative.

```text
week (Fri start)  W0 10-16  W1 10-23  W2 10-30  W3 11-06  W4 11-13  W5 11-20  W6 11-27  (W7 12-04)
D0                [D0-10, D0-11b, D0-12; D0-9a][D0-7a, D0-9b, D0-8 ...]          [D0-1]
X0                [census ........][verdict]                                   [narrowing w/ X2]
X1                [grammar, cards, mithi, kit, harness ...]
                           [suite + reserve + planted corpus (2nd family)][iter][pre][held-out ][report]
                                                                                [local pilot, days]
X2                [table, Z3, transliteration ......][T1/T2 spike ..........][final run][verdict] (amber: W7)
                           [Zen 5 fuzz, days, after census hash .]
X3                          [generator ..........][A/B nights][tuning     ][report]
X4                [service + sandbox + wrapper][pilot+profile][calibration nights ............] (may wait)
                  [catalogue dev][freeze][gated cat. ‖ blind batch][blind run][F1-sim, replay, revisit]
CC                [note ......................................][2nd-family review][signed]
M0 verdict                  [record frozen + signed]                           [dossier, signature]
```

**Checkpoints** (each gives what must be true by the end of the week):

| # | By (Thu) | What must be true |
|---|---|---|
| C0 | W0, 10-22 | D0-10, D0-11b and D0-12 signed, or a date set for them; D0-9a's signature form chosen. X0 record frozen. Q1–Q6, Q9 and Q17 answered. Harness host and toolchain locations approved. Two weekly signing/commit slots set. Job-wrapper design agreed |
| C1 | W1, 10-29 | X0 census, re-derivation and review done; `census.json` hash and FP-sensitivity classification handed to X2; X0 record SIGNED; X0 verdict computed. M0-verdict record frozen and SIGNED. X2-fuzz record frozen, naming the census hash (or the amendment rule), and fuzzing on silicon only after that. 2nd family provisioned. X3 counting rule frozen before the first schedule line; generator emits its first ISA. X4 service skeleton measuring on the desktop (engineering dry runs, outputs discarded). Job wrapper live. F1-sim held-out traces hash-sealed |
| C2 | W2, 11-05 | **Rules frozen** before the data they could be tuned to: X1-heldout (analysis model, n rule, σ_ta estimator and floor, exclusions, reserve order seed, kit acceptance tests) before the first card-iteration attempt; X2-gate (counting rules, Q9 reading) before T1 runs on the real variants; X3-parity and X4-calibration (N and c rules, A/A stopping rule) before the noise pilot. `mithi` covers the X1 subset. Card-iteration items (~20) and the planted corpus delivered; reserve authoring started. X4-hacks-catalogue frozen; catalogue engineering runs done; kit hash-frozen at the end of W2. Noise-pilot and profile nights run. `numerics_v1` pool sealed. X3 generator emits all three ISAs and passes `test_quant` in daytime. Reference binary built and hashed |
| C3 | W3, 11-12 | CC X1-subset rules frozen. `mithi` precondition passed. Card iteration done (≤ 3 epochs), with the Rust arm if approved. Reserve sealed. Provider attempts per hour measured. X3-parity and X4-calibration filled in and SIGNED, nights running. Gated catalogue run on the frozen kit done; blind batch written. X2 rule list frozen and mutant kill rates measured. CC draft complete |
| C4 | W4, 11-19 | σ_ta computed by the frozen rule; n filled in; X1-heldout SIGNED; held-out runs under way at the concurrency sized in W3. Blind batch run. X2 lockstep proof under different-family review. X3 tuning window open if X3 misses parity. Planted regression done if σ_d ≈ 2% (in W3 at 7 nights a week, W4 at 4); at σ_d = 4% it ends in W5 at 7 nights a week [D, §6.3] |
| C5 | W5, 11-26 | Held-out runs complete and analysed by the Gatekeeper script. Local pilot done (daytime). X3 report (final only if planted regression has passed, §3.4). CC signed. X2 final verdict run on the frozen checker. (Thursday 11-26 is US Thanksgiving; the plan assumes no Owner hours that day [G].) |
| C6 | W6, 12-03 | X2 verdict and the joint X0 narrowing judgement. All verdict files signed. D0-1 decided. M0 dossier assembled; the Owner signs the verdict. X4 may be "waits" |
| (C7) | W7, 12-10 | Only if X2 is amber (31–40 rules): one more week, then X2 is judged again (ROADMAP §3.3) |

**Week by week** (Builder work; the Owner's part is in §7):

- **W0 (10-16..10-22).**
  - X0: toolchains recorded, record frozen, configurations A–D compiled and decoded.
  - X1: grammar v0 draft, Tier 0 outline, `mithi` skeleton, harness skeleton, record drafts (the
    X1-heldout rules first).
  - X2: table schema, B_iform entries, fuzz-harness design, the `numerics_v1` mutant taxonomy, X2
    record drafts (X2-gate counting rules first), and a laptop venv for Z3 after 19:00 PT.
  - X3: the counting rule drafted, ready for freezing before W1's first schedule line.
  - X4: service and sandbox skeletons, job-wrapper design, the catalogue hack list, the hygiene
    checklist for Pierce, and X4 record drafts.
  - CC: outline.
  - Plan: PLAN.md and COST.md.
- **W1 (10-23..10-29).**
  - X0: census complete, report, re-derivation, review, verdict; census hash handed to X2.
  - X1: grammar v0 near freeze; Tier 0 and Tier 1 cards; `mithi` type checker; family templates;
    the 2nd family starts the card-iteration items.
  - X2: entries for the census union; fuzzing in daytime once the census hash and the X2-fuzz record
    exist; Bochs build; transliteration.
  - X3: counting rule frozen; generator prototype; the Python-versus-Exo choice (owner review).
  - X4: service, load gate, fingerprint, job wrapper live, MIN/OPT oracle; F1-sim held-out traces
    hash-sealed.
  - CC: sections drafted.
- **W2 (10-30..11-05).**
  - Rules freezes: X1-heldout, X2-gate, X3-parity, X4-calibration (§8).
  - X1: `mithi` covers the subset; kit started; card-iteration items delivered; oracle mutant-kill
    checks; reserve authoring starts (family B).
  - X2: T1 DAG matcher, rewrite list, T2 ranges, Z3 proofs; mutant pool sealed.
  - X3: all ISAs generated; scratch Hearth passes `test_quant` and `test_isa_identity`; the reference
    binary is built from a clean `b5d3f14` and hashed.
  - X4: X4-hacks-catalogue frozen; catalogue engineering runs (development); kit hash-frozen at the end
    of the week; noise-pilot and profile nights; σ_d estimates fill in N and c by the frozen rules;
    F1-sim on the laptop.
  - CC: Tier 0 trace.
- **W3 (11-06..11-12).**
  - X1: card iteration (laptop host), with the Rust arm if approved; attempts per hour measured;
    planted corpus run; precondition verdict; the kit's "ready or dropped" status recorded; reserve
    sealed.
  - X2: T1 accepts the real variants under the frozen counting rules; rule count tracked; kill rates
    under G, G+C and T1+T2.
  - X3: A/B nights (MSVC, clang-cl).
  - X4: A/A microbenchmark nights; gated catalogue run on the frozen kit; blind batch written (family
    B); tombstone import; revisit prototype; replay tests.
  - CC: draft complete, same-family review.
- **W4 (11-13..11-19).**
  - X1: σ_ta and n by the frozen rule; X1-heldout filled in and SIGNED; held-out runs (≈ 2.9k attempts
    at n = 60 [inference, ROADMAP §10]; 48 more per extra item [D]).
  - X2: lockstep proof for X0's loop shapes, to a different-family Prover; table/silicon mismatches
    fixed.
  - X3: a tuning window if the primary metric misses parity. It lasts at most two weeks: the kill is
    "still < 90% after two weeks of tuning" (ROADMAP §3.4).
  - X4: planted-regression nights; blind batch run; F1-sim held-out traces unsealed under their
    record.
  - CC: different-family Prover and Adversary.
- **W5 (11-20..11-26).**
  - X1: analysis (Gatekeeper script); local pilot (daytime; hours per Q18); report.
  - X2: final run on the frozen checker; report draft.
  - X3: report.
  - X4: planted regression ends (σ_d = 4%, 7 nights a week); X3 decode guard; end-to-end A/A nights.
  - CC: Owner signs.
- **W6 (11-27..12-03).**
  - X2 verdict, judged together with X0's narrowing.
  - All verdict files signed.
  - M0 dossier, D0-1, and the Owner's signature on the M0 verdict.
  - X4 runs on if its calibration is incomplete ("waits").

### 5.2 Plan B: 15 owner h/week, verdict about W12 (operative until D0-10b is signed)

At 15 h/week the Owner-bound chains stretch, and the machine-bound work (nights) does not. The phases
are [G]; the dates are [D] from the week table.

```text
week   W0    W1    W2    W3    W4    W5    W6    W7    W8    W9    W10   W11   W12
start  10-16 10-23 10-30 11-06 11-13 11-20 11-27 12-04 12-11 12-18 12-25 01-01 01-08
D0     [D0-10,11b,12,9a][D0-7a,9b,8]                                          [D0-1]
X0     [census][verdict]                                                 [narrowing]
X1     [grammar, cards, mithi, kit ......][suite + reserve + corpus authoring and Owner review ...][iter][pre][held-out][report]
X2     [table, Z3, transliteration ..............][T1/T2 spike, rule proofs ..........][final][verdict]
X3           [generator ..............][A/B nights][tuning][report]
X4     [service, sandbox, wrapper, catalogue dev][pilot][calibration nights ..........][blind][report]
CC     [note .............................................................][review][signed]
```

**Plan B checkpoints** [G for content; dates D]:

| # | By (Thu) | What must be true |
|---|---|---|
| B-C0 | W0, 10-22 | As C0 |
| B-C1 | W1, 10-29 | X0 census, re-derivation, review; census hash to X2; X0 SIGNED; X0 verdict. M0-verdict SIGNED. X2-fuzz SIGNED (after the census hash) and fuzzing. 2nd family provisioned. Job wrapper live. F1-sim traces sealed. X3 counting rule frozen |
| B-C2 | W3, 11-12 | Rules freezes done as in C2 (the X1-heldout rules freeze at the latest before the first card-iteration attempt). Kit hash-frozen. Noise-pilot and profile nights run. `numerics_v1` sealed. `mithi` covers the subset. X3 passes `test_quant`. Reference binary built and hashed |
| B-C3 | W5, 11-26 | X3-parity and X4-calibration SIGNED (by W4) and nights running. Gated catalogue run done; blind batch written. X2 rule list frozen and kill rates measured. Card-iteration items reviewed |
| B-C4 | W7, 12-10 | Planted regression done at σ_d ≤ 4% with ≥ 4 nights a week (W7 at σ_d = 4% and 4 nights a week, central A/A [D, §6.3]). X3 report. Blind batch run. Card iteration done (with the Rust arm if approved). X2 lockstep proof under R-diff review. Suite and reserve review about half done |
| B-C5 | W9, 12-24 | Suite, reserve and planted corpus reviewed and sealed. CC X1-subset rules frozen; `mithi` precondition passed. X2 final run on the frozen checker (if Q9 = the scheduled verdict week) |
| B-C6 | W11, 2027-01-07 | X1-heldout filled in and SIGNED; held-out runs complete. X2 verdict and joint X0 narrowing. CC signed. X4 calibrations complete (at σ_d = 4% and 4 nights a week, end-to-end A/A ends in W10 [D]) |
| B-C7 | W12, 01-14 | Gatekeeper analysis; all verdict files signed; D0-1 decided; M0 verdict signed |

- The X1 suite review runs at about 5 owner h/week from W3 to W9 (§7.2), so held-out runs land around
  W10–W11 [G].
- X3 and X4 nights can start as soon as their records are signed (W3–W4), because nights cost machine
  time, not Owner time. The ordering rule of §7.2 puts those signatures first. The calibrations
  finish well before X1 does at σ_d ≤ 4% and ≥ 4 nights a week. The exception is the bound case
  (all A/A sessions to N) at σ_d = 4%, which runs to W14 at 4 nights a week and to W9 at 7 [D, §6.3].
- The calendar spans US holidays on 2026-11-26, 2026-12-25 and 2027-01-01. Plan B assumes the Owner's
  15 h/week continues through them; Q11 asks whether it does.
- **X2's "end of week 6".** If Q9 resolves it as calendar W6 (2026-12-03), Plan B gives X2 only 22 of
  its 40 owner hours by then [D, §7.2]. The table review would be about half done when X2 is judged.
  For that case §7.2 has **Plan B-cal**, which front-loads X2 (40 h by W6) and takes the hours from
  X1, X4 and CC. Pierce must choose between Plan B and Plan B-cal before the X2-gate rules freeze (W2).
- ROADMAP §3.7's "X4's calibration runs past week 6" has the same ambiguity at Plan B cadence. This
  plan reads it as the X4 verdict waiting until its calibration completes. That is amber either way
  (Q9).

---

## 6. Machine calendar

### 6.1 Rules

- **Desktop daytime** means any time outside a quiet window. Mithril jobs use at most 8 threads **in
  aggregate**, add under 500 MB of new data to C:, and put big data on D: [M, brief; aggregate
  reading G, Q2]. This covers builds, X0 compiles, X2 fuzzing, X3 builds and correctness tests, Bochs,
  the reference-binary build, and the X1 local-model pilot. Local model runs, fuzzing and builds never
  overlap a quiet window (DR-023, ROADMAP §3.2).
- **Job wrapper.** From W1, every Mithril desktop job goes through the job wrapper (§3.5). The wrapper
  holds the 8-token semaphore, refuses starts inside quiet windows and logs stamps. Ad hoc SSH
  commands that use more than 1 thread are not allowed. In W0, before the wrapper exists, X0 is the
  only multi-threaded Mithril desktop job. Any other track's desktop command uses 1 thread.
- **Desktop quiet windows** are negotiated with Pierce (D0-10d). Inside one, the supervisor holds a
  machine-wide lock: no agent sessions, compiles, audits or local generation (06 §6.8). The lock
  covers jobs from any origin, SSH from the laptop included; the wrapper is how daytime jobs honour it.
  This plan also asks that other projects' jobs and the RTX 5070 queue be idle (Q1), because they
  share power, heat and memory with the measured runs [G]. The windows carry, in order (§6.3):
  - the X4 noise pilot;
  - `mithc profile measure`;
  - X3 A/B;
  - X4 calibration.

  Nothing else runs in them.
- **Laptop** work: all agent sessions; the X1 harness host (API attempts plus sandboxed compiles, once
  LLVM and Rust are installed; Q4); Python work (Z3, `hearth.sim`, MIN/OPT, tombstone replay, the
  revisit prototype, Gatekeeper analysis scripts). The laptop is shared with a benchmark until
  19:00 PT on 2026-10-16 [M, brief]. Until then only light work runs there: scripts under about
  1 CPU-minute (sprint rule). The laptop never hosts a measurement used by a gate (§11, tombstone 2).
  It may run an optional Zen 4 fuzz cross-check as a secondary arm that cannot change a verdict [G].
  Its uptime as harness host is a risk (R25).
- **Why X1 runs on the laptop** [G]: X1's ≈ 4.1k API attempts (2.9k + 1.2k [D, ROADMAP §10]) are
  network-bound and run in parallel. On the desktop they would compete with the 8-thread daytime cap,
  and at night with the quiet windows. On the laptop they can run at any hour (§11, tombstone 1).

### 6.2 Quiet-hour demand, reconstructed

ROADMAP §10 gives ≈ 60–215 quiet hours for M0 [inference]. The reconstruction below [D] uses
06 §6.6's formula: n = max(6, ⌈12·σ_d²/δ²⌉) blocks at δ = 3%, and a planned test lasts
n × 4·t_run × c.

Assumptions:
- microbenchmark t_run = 10 s with c = 1 (L2-resident, no NVMe), so 40-second blocks;
- end-to-end t_run = 2 min with c = 1.5 (06 §6.6, ROADMAP §10);
- planted-regression sessions run to the amber limit N = 2 × planned (ROADMAP §3.5);
- X3 has 8 microbenchmark confirmatory tests (Q4 and Q8 × AVX2 and AVX-512 × 2 release compilers)
  plus 2 decode-guard tests;
- A/A sessions last **one planned test** (central) or **N = 2 × planned** (bound). ROADMAP §3.5 asks
  the A/A sessions to publish the median and p90 non-inferiority time-to-pass. A session that must
  show its time-to-pass cannot always stop at one planned length, so the central case is the least
  conservative choice and the bound case is the most conservative.

| Component | σ_d = 2% (n = 6), central | σ_d = 2%, A/A to N (bound) | σ_d = 4% (n = 22), central | σ_d = 4%, A/A to N (bound) |
|---|---|---|---|---|
| X4 planted regression, 2 × 100 microbenchmark sessions to N | 26.7 h | 26.7 h | 97.8 h | 97.8 h |
| X4 A/A, 100 microbenchmark sessions | 6.7 h | 13.3 h | 24.4 h | 48.9 h |
| X4 end-to-end A/A, 20 sessions | 24.0 h | 48.0 h | 88.0 h | 176.0 h |
| X3 microbenchmark, 8 tests | 0.5 h | 0.5 h | 2.0 h | 2.0 h |
| X3 decode guard, 2 tests | 2.4 h | 2.4 h | 8.8 h | 8.8 h |
| **Total** | **60.3 h ≈ 7.5 nights** | **90.9 h ≈ 11.4 nights** | **221.0 h ≈ 27.6 nights** | **333.4 h ≈ 41.7 nights** |

*All cells [D]: `scratchpad/plan/check.py`, revision 2, 2026-10-16.*

- **The proposed stopping rule (§3.5)** runs microbenchmark A/A to N and stops end-to-end A/A at
  non-inferiority e ≥ 20 or N. It costs between 66.9 h and 90.9 h at σ_d = 2%, and between 245.4 h and
  333.4 h at σ_d = 4% [D]. The lower figure assumes end-to-end A/A averages one planned test.
- **Outside the formula** [G]: the noise pilot (2–3 nights) and `mithc profile measure` (STREAM per
  CCD and all-core plus the NVMe grid, estimated at 2–4 h, one night). Neither has been measured.
- At σ_d = 4%, both the bound case and the proposed rule exceed ROADMAP's 215 h. This plan changes no
  ROADMAP figure. It asks for the nights (§6.3) and raises the gap in Q15.

The reconstruction lands near ROADMAP's range but is not ROADMAP's derivation. Like 06 §6.6, it
leaves out calibration blocks, sentinels, settling, voided sessions and X3 tuning re-runs, all of which
add hours. The plan therefore asks for a contingency on top (Q12). It uses ROADMAP's figure as the
cost line and the reconstruction to size the night ask.

### 6.3 Night pattern (proposal, provisional, pending D0-10d)

- W2–W6 contain 35 calendar nights [D]. At 8 h a night, the W2–W6 capacity is 160 h at 4 nights a
  week, 200 h at 5 and 280 h at 7 [D: 5 weeks × r × 8 h]. The pilot and profile take about 4 nights
  [G] in W2.
- **Ask.** 8-hour windows [inference, ROADMAP §10 uses 8 h nights] at times Pierce chooses (for example
  23:00–07:00 PT [G]), **7 nights a week from W2**, as [D0_BRIEF](../D0_BRIEF.md) D0-10d recommends.
  This is the only rate that covers ROADMAP's 215 h top figure by W6 under Plan A. The capacity is
  280 h, or 248 h after the pilot and profile [D].
- **Rule for lowering the rate after the pilot** (proposal for D0-10d; inputs [G], arithmetic [D]):
  1. Take the σ_d estimate that the X4-noise-pilot record names, for example an upper confidence
     bound for the microbenchmark run type.
  2. Use the A/A stopping rule as frozen in X4-calibration.
  3. Compute the reconstruction × (1 + contingency), with 25% as Q12 proposes.
  4. Choose the smallest rate r whose calibration nights cover that figure by the horizon of the
     cadence in force: **end of W6 under Plan A** (calibration W3–W6), **end of W10 under Plan B**
     (calibration W4–W10).

  | σ_d (microbenchmark) | n | Central h | Bound h | Plan A rate, central | Plan A rate, bound | Plan B rate, central | Plan B rate, bound |
  |---|---|---|---|---|---|---|---|
  | 1.5% | 6 | 60.3 | 90.9 | 3 | 4 | 2 | 3 |
  | 2.0% | 6 | 60.3 | 90.9 | 3 | 4 | 2 | 3 |
  | 2.5% | 9 | 90.4 | 136.4 | 4 | 6 | 3 | 4 |
  | 3.0% | 13 | 130.6 | 197.0 | 6 | > 7 | 3 | 5 |
  | 3.5% | 17 | 170.8 | 257.6 | 7 | > 7 | 4 | 6 |
  | 4.0% | 22 | 221.0 | 333.4 | > 7 | > 7 | 5 | > 7 |

  *Rates in nights per week, each including the 25% contingency [D: `check.py`]. "> 7" means the
  calibration cannot finish by the horizon. X4 then waits, which is amber (ROADMAP §3.7). The
  D-22 trigger fact "parity-gate quiet hours exceed the available windows" is recorded
  (ROADMAP §9).*

  Under Plan A, 4 nights a week covers the central case with contingency only up to σ_d ≈ 2.7%, and
  the bound case only up to σ_d ≈ 2.1% [D].
- **When planted regression and X3 finish** [D: `check.py`; no voids; pilot 3 nights and profile
  1 night in W2; calibration from W3 (Plan A) or W4 (Plan B)]:

  | Cadence | σ_d | Nights/week | Planted regression done | X3 done (planted + decode guard) | All calibration done |
  |---|---|---|---|---|---|
  | Plan A, central A/A | 2% | 4 | W4 | W4 | W4 |
  | Plan A, central A/A | 2% | 7 | W3 | W3 | W4 |
  | Plan A, central A/A | 4% | 4 | **W6, last night, no slack** | **W7** | W9 |
  | Plan A, central A/A | 4% | 7 | W5 | W5 | W6 (3 h slack) |
  | Plan A, bound | 4% | 4 | W7 | W7 | W13 |
  | Plan A, bound | 4% | 7 | W5 | W5 | W8 |
  | Plan B, central A/A | 2% | 4 | W5 | W5 | W5 |
  | Plan B, central A/A | 4% | 4 | W7 | W8 | W10 |
  | Plan B, central A/A | 4% | 7 | W6 | W6 | W7 |
  | Plan B, bound | 4% | 4 | W8 | W8 | W14 |
  | Plan B, bound | 4% | 7 | W6 | W6 | W9 |

  If the X3-parity and X4-calibration records are signed by the end of W2, calibration can use the
  nights of W2 left over after the pilot. Each finish then moves earlier by up to the 3 W2 nights at
  7 a week [D: 7 − 4].
- **Night order** [G]:
  1. the noise pilot (2–3 nights);
  2. `mithc profile measure` (one night; all-core STREAM needs the thread cap lifted inside windows,
     Q2);
  3. X3's microbenchmark A/B and the X4 microbenchmark A/A, interleaved by night;
  4. the planted-regression microbenchmark sessions, which X3's parity verdict needs (§3.4);
  5. X3's decode guard, which X3's verdict needs;
  6. the end-to-end A/A last (X4 only; X4 may wait).

  End-to-end runs use production placement across both CCDs (06 §6.7), which needs more than the
  8-thread cap (Q2).

**Plan A calendar at the 7-nights ask** [G for content; finish weeks D from the table above]:

| Week | Desktop daytime (wrapper, ≤ 8 threads in aggregate) | Desktop quiet nights | Laptop |
|---|---|---|---|
| W0 | LLVM and XED setup; X0 compiles and decodes (X0 alone may use 8 threads) | none | agent sessions; light until 19:00 PT on 10-16; venv (Z3, numpy) |
| W1 | X0 twin builds and re-runs; X2 fuzz bring-up (vectors only after the census hash and the X2-fuzz record); Bochs build; X4 dry runs (outputs discarded); job wrapper live | none | harness, `mithi`, MIN/OPT; F1-sim held-out traces sealed |
| W2 | X2 fuzz; X3 builds and correctness tests; reference-binary build; X4 catalogue engineering runs | noise pilot (2–3 nights [G]); profile measurement (1 night [G]); other nights only if X3-parity and X4-calibration are signed | harness bring-up; F1-sim |
| W3 | X2 fuzz tail; X3 builds; X4 gated catalogue run on the frozen kit (in a window if a hack's declared stage needs one) | X3 A/B; X4 A/A microbenchmark; planted regression (done in W3 if σ_d ≈ 2%) | card iteration (+ Rust arm); tombstone replay; attempts per hour measured |
| W4 | X3 tuning builds; local-pilot tok/s check under 8 threads | planted regression continues at higher σ_d; X3 decode guard and end-to-end A/A (all done in W4 if σ_d ≈ 2%) | held-out attempts |
| W5 | X1 local pilot (hours per Q18) | planted regression done at σ_d = 4%; X3 decode guard; end-to-end A/A | X1 analysis |
| W6 | — | end-to-end A/A (ends in W6 at σ_d = 4% with central A/A; to W8 in the bound case) | verdict scripts and dossier |

**Plan B night calendar** [G]. Same order. The pilot and profile run in W2. Calibration nights run
from W4, or from W3 if the records are signed then. At 4 nights a week calibration ends in W5
(σ_d = 2%) or W10 (σ_d = 4%, central). At 7 nights a week it ends in W7 at σ_d = 4% [D, table above].
The ask is the same 7 nights a week. Under Plan B the lowering rule allows 4 nights a week up to
σ_d = 3.5% (central A/A) or 2.5% (bound), and 5 nights at σ_d = 4% central [D, rate table].

---

## 7. Owner-hour asks

ROADMAP's split by experiment [inference, ROADMAP §3]: D0 10, X0 10, X1 55, X2 40, X3 20, X4 40 and
CC 20, for 195 h in total [D: sum]. Weekly splits are [G]. The arithmetic is checked by
`scratchpad/plan/check.py` [D].

Two loads sit inside these hours rather than on top of them [G]:
- **Freeze and signature commits.** Two fixed signing/commit slots a week, as D0_BRIEF D0-10b
  recommends. Freezes are batched into them (R26).
- **R-diff review reading** (§9). There are at most 23 reviews [D: 17 records + 6 verdicts] at about
  0.5 h each [G], so ≈ 11.5 h [D]. The hours come from the owning track's allocation, because
  ROADMAP counts pre-registration work in M0's ~195 h.

### 7.1 Plan A (peak 33 h/week)

| Track | W0 | W1 | W2 | W3 | W4 | W5 | W6 | Total |
|---|---|---|---|---|---|---|---|---|
| D0 | 6 | 2 | 1 | 0 | 0 | 0 | 1 | 10 |
| X0 | 2 | 4 | 2 | 0 | 0 | 0 | 2 | 10 |
| X1 | 5 | 10 | 8 | 10 | 8 | 8 | 6 | 55 |
| X2 | 3 | 6 | 8 | 8 | 7 | 4 | 4 | 40 |
| X3 | 0 | 3 | 4 | 4 | 4 | 3 | 2 | 20 |
| X4 | 4 | 5 | 6 | 7 | 6 | 6 | 6 | 40 |
| CC | 2 | 3 | 4 | 4 | 4 | 2 | 1 | 20 |
| **Week** | **22** | **33** | **33** | **33** | **29** | **23** | **22** | **195** |

*Cells [G]; totals [D].*

What Pierce does each week [G]:
- **W0 (22 h).**
  - Read the D0 brief; decide or schedule D0-10, D0-11b, D0-12 and D0-9a, then D0-7a, D0-9b and
    D0-8.
  - Set the two weekly signing/commit slots.
  - Answer Q1–Q6, Q9 (needed before the X2-gate rules freeze) and Q17.
  - Review X0's frozen record, and sign it once X0's review log is complete.
  - Approve the direction of X1's grammar and Tier 0 card.
  - Review X2's table schema.
  - Choose and apply the quiet-profile settings himself (the X4 checklist).
  - Approve the CC outline.
- **W1 (33 h).**
  - X0: review the report and the FP-sensitivity classification; sign X0 in D0-9a's form.
  - Sign the M0-verdict record (with Q7 answered, or with the "pending Q7" lines as written).
  - X1: review the cards and family specs.
  - Sign X2-fuzz once it names the census hash, then review the first table entries.
  - Commit X3's counting-rule freeze; choose Python or Exo.
  - Sign the X4 noise-pilot record or instruction, and answer D0-7a or Q1 for unattended nights.
  - CC: review sections.
- **W2 (33 h).**
  - Commit the rules freezes: X1-heldout, X2-gate, X3-parity, X4-calibration, X4-hacks-catalogue.
  - X1: review the suite (batch 1), the oracles, and the first reserve items (Q16).
  - X2: review table entries.
  - Review the catalogue batch.
  - Commit the kit hash-freeze (D0-9b per D0_BRIEF).
  - CC: review.
- **W3 (33 h).**
  - Sign X1-card-iteration (before the first attempt) and X1-precondition.
  - Sign X2-mutants and review the rule list.
  - Sign the X3-parity and X4-calibration fill-ins, and X4-hacks-catalogue before the gated run.
  - X1: review the suite (batch 2) and the rest of the reserve.
- **W4 (29 h).**
  - Sign the X1-heldout fill-in, after reading the power curve.
  - Review the lockstep proof and the table/silicon fixes.
  - Review X3 tuning.
  - Sign X4-hacks-blind, X4-forge-sim and X4-tombstone-replay.
  - Review CC's findings.
- **W5 (23 h).**
  - Review the X1 results.
  - Sign the X2-gate record (its rules were frozen in W2) before the verdict run.
  - Review the X3 report.
  - Review the X4 interim results.
  - Sign CC.
- **W6 (22 h).**
  - Decide D0-1.
  - Make the joint X0/X2 narrowing judgement.
  - Review the X1 and X2 reports, and any R-diff findings still open.
  - Review the M0 dossier and sign the verdict.

### 7.2 Plan B (15 h/week; operative until D0-10b is signed)

| Track | W0 | W1 | W2 | W3 | W4 | W5 | W6 | W7 | W8 | W9 | W10 | W11 | W12 | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D0 | 6 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 10 |
| X0 | 2 | 3 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 1 | 10 |
| X1 | 3 | 4 | 4 | 5 | 5 | 5 | 5 | 5 | 5 | 5 | 4 | 3 | 2 | 55 |
| X2 | 2 | 3 | 3 | 3 | 3 | 4 | 4 | 4 | 4 | 4 | 3 | 2 | 1 | 40 |
| X3 | 0 | 0 | 1 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 1 | 20 |
| X4 | 2 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 4 | 3 | 4 | 40 |
| CC | 0 | 0 | 1 | 2 | 2 | 1 | 1 | 1 | 1 | 1 | 2 | 3 | 5 | 20 |
| **Week** | 15 | 15 | 15 | 15 | 15 | 15 | 15 | 15 | 15 | 15 | 15 | 15 | 15 | **195** |

*Cells [G]; totals [D]. By the end of W6: X2 22 h, X1 31 h, X4 20 h, CC 7 h [D].*

**Plan B-cal: the variant for the case where Q9 means calendar W6.** X2 and the joint X0 narrowing
are then judged at the end of W6 (2026-12-03). X2 gets all 40 h by then, and X0's narrowing hours move
to W6. The hours come from X1, X4 and CC in W0–W6 and go back to them in W7–W12.

| Track | W0 | W1 | W2 | W3 | W4 | W5 | W6 | W7 | W8 | W9 | W10 | W11 | W12 | Total |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D0 | 6 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 10 |
| X0 | 2 | 3 | 2 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 1 | 10 |
| X1 | 2 | 3 | 3 | 3 | 3 | 3 | 2 | 6 | 6 | 7 | 7 | 6 | 4 | 55 |
| X2 | 3 | 5 | 6 | 6 | 6 | 7 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 40 |
| X3 | 0 | 0 | 1 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 2 | 1 | 20 |
| X4 | 2 | 2 | 2 | 3 | 3 | 2 | 2 | 4 | 4 | 4 | 4 | 4 | 4 | 40 |
| CC | 0 | 0 | 0 | 1 | 1 | 1 | 0 | 3 | 3 | 2 | 2 | 3 | 4 | 20 |
| **Week** | 15 | 15 | 15 | 15 | 15 | 15 | 15 | 15 | 15 | 15 | 15 | 15 | 15 | **195** |

*Cells [G]; totals [D] (`check.py`: every track total matches ROADMAP's split).*

The cost of Plan B-cal: X1 has 19 h by W6 instead of 31 h [D], so the suite review finishes about
12 h later. At X1's W7–W11 rate of 6–7 h/week that is about two weeks [G], and the M0 verdict moves to
about W13–W14 [G]. Plan B-cal must be chosen before the X2-gate rules freeze (W2), because the X2-gate
record states which week the kill is judged in.

**Ordering rule at 15 h/week** [G]:
1. Signatures and freeze commits that unblock machine time (the nights) or a second family come
   first.
2. Then the reviews on the critical path: the X1 suite, then the X2 table.
3. Then everything else.

A week below 70% of its planned hours is re-planned at the next checkpoint (§12) [G].

**Review packets** [G]. Every Owner review arrives as a packet of at most 2 pages. It contains:
- what is asked (sign, decide or review);
- the diff against ROADMAP thresholds, each "equal" or "more precise", never looser;
- the numbers, with tags;
- the open questions;
- the reviewer findings;
- a time box.

The packets are how Owner hours stay inside the plan.

---

## 8. Pre-registration schedule

The rule (README): no data is collected except under a FROZEN record that is SIGNED, or covered by an
explicit Owner instruction. The Gatekeeper evaluates nothing until a record is SIGNED. D0_BRIEF's
D0-12 recommendation would narrow the instruction route to deterministic, exhaustive runs (X0 only).
The rows marked "an instruction suffices" are therefore provisional, pending D0-12. The record IDs below
are proposals; the owning track names the file. "Rules by" is the rules freeze of §0. Where it is
"—", the record is frozen whole.

| Record | Gates this collection | Must be FROZEN before | Rules by (A / B) | SIGNED (or Owner instruction) before | Plan A: freeze / sign | Plan B: freeze / sign | D0 |
|---|---|---|---|---|---|---|---|
| [X0-census](prereg/X0-census.md) | compiling Hearth objects, decoding | the first Hearth object is compiled (TOOLCHAINS.md written first) | — | instruction given 2026-10-16; signature before the Gatekeeper verdict | W0 / W1 | W0 / W1 | D0-12, D0-9a |
| M0-verdict | the mapping from experiment verdicts to §4 rows | the first experiment verdict is known; not with §3.8's "pending Q7" lines open unless they stay as written | — | the same | W1 / W1 | W1 / W1 | D0-12, D0-1; Q7 |
| X1-card-iteration | card-iteration attempts (training items only; ≤ 3 epochs; the Rust arm on the same items if approved) | the first iteration attempt | — | the same | W2 / W3 | W5 / W6 | D0-10, D0-12; Q16 |
| X1-precondition | `mithi` against hidden references, the planted corpus and CC's derivations; freezes `mithi`'s hash | the precondition run | — | the same | W3 / W3 | W8 / W9 | D0-10 (corpus family), D0-12 |
| X1-heldout | the held-out runs (the kill) | rules: the first **card-iteration** attempt. Rules: analysis model (05 §13), exclusions, stopping, kit acceptance tests, the σ_ta estimator with its conservative choice and prior floor, n = max(60, n required by the power rule at that σ_ta) capped at n_max, the reserve's random-order seed, and what happens if a pinned model version is withdrawn mid-batch. Fill-in: σ_ta, n, the item hashes and the kit commit, before the first held-out attempt | W2 / W5 | the first held-out attempt | W2 → fill-in W4 / W4 | W5 → fill-in W10 / W10 | D0-10, D0-12 |
| X1-local-pilot | local-model pilot runs (reported, not part of the kill) | the first pilot attempt; machine hours from a measured tok/s run under 8 threads (Q18) | — | the same | W4 / W5 | W9 / W10 | D0-10c (local model), D0-10d |
| X2-fuzz | vectors on silicon (Zen 5), Bochs comparison | the first vector. The iclass set is the FP-sensitive iclasses of `census.json@sha256:<hash>`, or the B_iform scope plus the census amendment rule (§3.3). Single-oracle iclasses are listed | — | the same (an instruction suffices, pending D0-12) | W1, after the census hash / W1 | W1 / W1 | D0-12 |
| X2-mutants | the kill-rate measurement under G, G+C and T1+T2 | T1's rule list is frozen; the pool is hash-sealed first | — | the same | W3 / W3 | W7 / W7 | D0-12 |
| X2-gate | the verdict run of the frozen T1 on the real variants and the mutants | rules: before T1 runs on the real variants. Rules: what counts as a rule; per-kernel `assumed` axiom; the fixable-table-bug test; the week reading (Q9; Plan B or B-cal) | W2 / W2 | the verdict run | W2 / W5 | W2 / W10 (W6 under B-cal) | D0-10 (Prover), D0-12; Q9 |
| X3-parity | A/B sessions | the first A/B session. It states N's and c's rules, the arms, the reference binary's hash (§3.4) and the counting rule. The counting rule is frozen before the first schedule line | counting rule W1 / W1; rest W2 / W3 | the first A/B session | W2 → fill-in W3 / W3 | W3 → fill-in W4 / W4 | D0-8 (provisional), D0-10, D0-12; Q17 |
| X4-noise-pilot | quiet-night noise runs, descriptive only, never pooled into a calibration. States which σ_d estimate feeds §6.3's rate rule | the first quiet night | — | the same (an instruction suffices, pending D0-12) | W2 / W2 | W2 / W2 | D0-10d, **D0-7a or Q1** (unattended) |
| X4-calibration | A/A, planted-regression and end-to-end A/A sessions; `mithc profile measure`. Fixes c's and N's rules, the A/A stopping rule (§3.5) and the reference binary's hash | rules: the first noise-pilot night. Fill-in: N and c from the pilot by the frozen rules | W2 / W2 | the first calibration session | W2 → fill-in W3 / W3 | W2 → fill-in W4 / W4 | D0-7a, D0-8 (provisional), D0-10, D0-12; Q15, Q17 |
| X4-hacks-catalogue | the gated run of the frozen kit against batch (a); each hack's declared stage. States that a gated miss is HALT-F | the catalogue engineering runs (so the hack list and stages are fixed before kit tuning) | — | the gated catalogue run, after the kit hash-freeze | W2 / W3 | W2 / W4 | D0-12 |
| X4-hacks-blind | running the frozen kit against batch (b) | the blind run; the kit is hash-frozen before the batch is written | — | the same | W3 / W4 | W4 / W6 | D0-10 (Adversary), D0-12 |
| X4-forge-sim | F1-sim on sealed held-out traces; the MDE | the held-out traces are unsealed; traces hash-sealed in W1, before F1-sim development; MIN/OPT validated first | — | the same | W3 / W4 | W5 / W6 | D0-12 |
| X4-tombstone-replay | the replay acceptance tests (06 §7.6), with the irrelevant perturbations listed in advance | the first replay | — | the same | W3 / W4 | W5 / W7 | D0-12 |
| CC-gate | `mithi`'s acceptance of the canonical snippets; the Tier 0 trace | that acceptance check (aligned with X1-precondition) | — | signed at the gate | W3 / W5 | W8 / W11 | D0-10 (reviewers), D0-12 |

*Weeks [G]. "W2 → fill-in W4 / W4" means the record is frozen with its rules in W2, the fill-in
amendment lands in W4, and the Owner signs at the fill-in commit in W4.*

**Amendments.** A threshold never moves after data has been seen (ROADMAP §1 rule 1). The parameters
that must come from data, such as X1's σ_ta, X4's clip c and the amber limit N, are fixed as **rules**
in the frozen record. They are computed from data the record does not judge: card-iteration items
(with the Rust arm, or the prior floor) and the noise pilot. Only the computed value is filled in. The
same pattern now covers the counting rules that development data could otherwise shape: X2-gate's
rule unit and axiom definition, and X3's line count. Those are frozen before T1 runs on the real
variants and before the first schedule line. That keeps every threshold and counting rule fixed
before the data it judges, and before the development data it could be fitted to.

---

## 9. Review protocol

**Two review grades** (README §Independence):

| Grade | Who | Label in the review log | Satisfies |
|---|---|---|---|
| R-same | a Claude agent in a fresh context, with an adversarial brief and no access to the author's transcript or intermediate state, and without write access to the reviewed files | `same-family, independent-context` | README's "independent review" for records and results. **Never** a ROADMAP "different family" requirement |
| R-diff | an agent from a different model family (after D0-10) | `different-family` | every ROADMAP requirement for another family |

**Where ROADMAP requires a different family** (these items stay open until an R-diff exists; an
R-same stand-in is logged as preparation, never as the requirement met):
- X1: at least two participant families; the planted Dc corpus written by a family other than
  `mithi`'s author; task authors from a different family than the card editors (05 §13).
- X2: the Prover who reviews the lockstep loop-rule proof.
- X4: the blind batch's Adversary.
- CC: the Prover and the Adversary.

**Procedure for every record and every result:**
1. The author finishes. The reviewer receives only frozen inputs: the record text at a named commit or
   hash, the scripts and the raw outputs.
2. The reviewer works through this checklist:
   1. every threshold equals ROADMAP's or is more precise;
   2. units and counting rules are defined before the data, and before any development data they
      could be fitted to;
   3. every outcome has an action;
   4. the analysis script is named and deterministic: two runs give the same output hash;
   5. every number is tagged;
   6. the D0 dependencies are stated;
   7. for results, the figures are re-derived independently from the raw outputs (as X0 §7 requires).
3. Findings are graded *blocker*, *major* or *minor*. A blocker stops the freeze or the verdict.
4. The review-log row records the date, the reviewer (model ID and session), the grade, the scope, the
   input commit or hash, the findings by severity, and the outcome (accept, accept with changes, or
   reject).
5. **R-diff backlog.** Once family B is provisioned, each SIGNED gate-bearing record and each computed
   verdict gets an R-diff review in the week after its signature. Records signed before family B
   existed are reviewed in the first two weeks after provisioning. All of them are done before the M0
   verdict is signed [G]. At most 23 reviews [D: 17 records in §8 + 6 verdicts]. The Owner's reading
   is about 0.5 h per review [G], ≈ 11.5 h [D], inside each track's hours (§7). Their metered cost is
   in family B's line ([COST §1.3](COST.md#13-measurement-budget-inside-the-api-lines)). ROADMAP asks
   for different-family review throughout; this plan defers it only because no second family exists
   yet.

**Separation of roles** [G]: a Builder never reviews its own track's records. The Gatekeeper scripts
are written by one agent and re-derived by another. No agent edits a sealed artifact after its hash is
committed.

---

## 10. Risk register

Likelihood (L) and impact (I) are [G]: H, M or L.

| # | Risk | L | I | Early signal | Mitigation |
|---|---|---|---|---|---|
| R1 | D0-10 slips, so there is no budget, no second family and no nights | M | H | C0 missed | D0 brief first; everything that needs no data proceeds; slip X1 one-for-one and say so |
| R2 | A second model family cannot be provisioned (access, terms, cost) | M | H | no API key by C1 | provider-agnostic harness adapters; list candidate families for D0-10; R-same stand-ins clearly labelled; X1 kill cannot run without it (ROADMAP §1 rule 5) |
| R3 | Owner hours below plan | H | H | a week < 70% of plan | Plan B is the operative default until D0-10b; review packets ≤ 2 pages; ordering rule (§7.2) |
| R4 | Too few quiet windows (other projects, GPU queue) | M | H | fewer nights agreed than §6.3's rate rule needs for the pilot's σ_d | night order (§6.3); X4 "waits" is amber (ROADMAP §3.7); record the D-22 trigger facts (ROADMAP §9) |
| R5 | High σ_d, so 215+ quiet hours are needed (≥ 245 h at σ_d = 4% under the proposed A/A rule [D]) | M | M | noise pilot gives σ_d ≥ 3% | hygiene checklist; microbenchmark first; contingency (Q12); A/A stopping rule (Q15); D-22 |
| R6 | The 8-thread cap conflicts with end-to-end placement across both CCDs and all-core STREAM | H | M | Q2 unanswered | ask for the cap to lift inside quiet windows; otherwise the X4 end-to-end A/A and X3's decode guard run under a declared reduced placement, which changes the run type and is stated in the record, and all-core STREAM is not measured |
| R7 | Storage limits: < 500 MB on C:, D: is a slow USB HDD; the model file and NVMe grid need fast storage | H | M | Q3 unanswered | read Hearth's existing model file in place, read-only; never stream benchmark data from D:; the NVMe grid reads existing files only |
| R8 | The WSL2 virtual disk on C: grows with toolchains (Rust, Bochs, LLVM) | M | M | C: free space shrinks | install under `/mnt/d` or on the laptop; log C: free space before and after each install |
| R9 | Hearth R3 working tree (21 entries) diverges from `b5d3f14` | H | L | X0 report | X0 states whether the R3 diff touches a dispatched kernel; a separate record if it does; M0 measures a clean `b5d3f14` stand-in (§3.4); S0 waits for the R3 commit |
| R10 | `mithi` is not ready or unsound in time; precondition fails | M | H | the subset is not covered by C2 | start in W0; the subset is small; precondition before any held-out run (ROADMAP §3.2 re-scoring rule) |
| R11 | Tooling kit not ready | M | L | not ready by C3 | pre-declared cut-off (§3.2): arm dropped, amber (a) waits for M1 |
| R12 | σ_ta is large, so more than 60 items are needed; or σ_ta cannot be estimated at all | M | M | card-iteration σ_ta, or no Rust arm approved | Rust arm on card iteration or a pre-registered prior floor (Q16); sealed reserve up to n_max authored in W2–W3, so growth costs no W4 authoring; dollars in COST §1.3; the threshold never moves |
| R13 | Contamination: sealed items are readable by Builder agents on the same machine | H | H | sealed paths readable in a Builder session | sealed store outside the repo, encrypted, with the key held by the Gatekeeper process or the Owner (Q5); canary strings (05 §13) |
| R14 | Correlated same-family errors (author and reviewer both Claude) | H | M | R-diff finds what R-same missed | R-diff backlog (§9 step 5); §11 tombstone 3 |
| R15 | Agents tune the checker to the mutants, the counting rules to the rule count, or the cards to the held-out items | M | H | rules, counting definitions or card atoms appear after a sealed artifact or development data was seen | mutant sealing (§3.3); rules freezes (§8); held-out runs once, after the card is frozen; atom-isolation check (05 §13) |
| R16 | API overrun (≈ 4.1k attempts at n = 60, $0.5–2 each [inference, ROADMAP §10], plus family B's metered authoring) | M | M | burn above the COST.md alert | stop-loss in [COST.md §5](COST.md#5-alerts-and-stop-loss): held-out runs start only if the remaining approved budget covers n × 48 × $2 [D]; an in-progress held-out batch is not stopped by the 80% rule |
| R17 | The Claude Code subscription's 5-hour or weekly limit throttles the agent team | H | M | Account-wide 5-hour usage rose 3% → 8% → 16% at 18:17Z, 18:29Z and 18:45Z; the weekly window rose 10% → 11% → 13% [M, plan]. Extrapolated, the 5-hour window runs out about 1.2 h before its 23:00Z reset [D, COST row 3]. This is a start-up burst, not a rate | pace by `get_usage` readings (≥ 4 per work block) logged in COST.md; stagger the tracks; the Owner decides on extra usage (disabled [M, plan]) |
| R18 | Supply chain: downloaded toolchains (LLVM, XED, Bochs) | L | M | signature or attestation failure | verify signatures or attestations; pin and hash every archive in TOOLCHAINS.md |
| R19 | X3's parity verdict rests on an incomplete planted-regression calibration | M (H at σ_d ≥ 3.5% and < 7 nights/week [D, §6.3]) | M | X3 A/B finishes before the calibration | X3-parity makes its verdict final only after the calibration (§3.4); 7-nights ask (§6.3); Q8 |
| R20 | Holiday weeks (2026-11-26, 2026-12-25, 2027-01-01) in Plan B | M | L | Owner calendar | Q11; re-plan at the checkpoint |
| R21 | Signature form before D0-9 is challenged later | L | M | — | D0-9a's interim form (D0_BRIEF), re-signed with the D0-9b key once it exists (Q6) |
| R22 | Quiet-profile settings left unapplied (power plan, Defender, indexing) | M | M | void rate in the noise pilot | Pierce applies the settings he chooses before the pilot; the service detects and voids and never changes them (06 §6.7) |
| R23 | Toolchain availability. Bochs may not emulate every census iclass (AVX-512 VNNI and other forms; not verified here), leaving one oracle for those iclasses. clang-cl for X3's Clang arm exists only if X0's portable LLVM install succeeds. Exo and its Python dependencies are unverified. Rust, rust-analyzer and a C compiler on the laptop (none today [M, brief]) are uninstalled | M | M | a census iclass without Bochs support; TOOLCHAINS.md has no clang-cl; Q4 unanswered by C0 | X2-fuzz lists single-oracle iclasses; the laptop Zen 4 cross-check runs as a secondary arm that cannot change a verdict; X3 falls back to the Python generator if Exo fails; Q4 in W0 |
| R24 | Provider throughput: rate limits, outages, or a pinned model version withdrawn during the held-out window. At n = 60, 2,880 attempts × 5–10 min = 240–480 attempt-hours [D; per-attempt time is ROADMAP §3.2's local-model figure, API latency not measured]. Finishing in 14 days, running continuously, needs ≥ 2 concurrent attempts; in 7 days ≥ 3 [D] | M | H | attempts per hour measured in card iteration (W3) project held-out completion past W5 | measure the rate in W3 and size concurrency before X1-heldout is signed; the record states what happens if a pinned version is withdrawn mid-batch, before data |
| R25 | Laptop uptime as harness host: sleep, Windows Update reboots, other benchmarks | M | M | interrupted attempts in card iteration | resumable harness (attempt-level checkpoints); an interrupted attempt is an infrastructure failure, re-run under 05 §13's exclusion rule; power plan and update hours are Pierce's settings |
| R26 | Commit bottleneck: no track agent commits, so every freeze, fill-in and landing waits on Pierce or an authorised session, and that time is not in the owner-hour tables | H | M | a frozen-ready record waits > 3 days for a commit | two fixed signing/commit slots a week (D0_BRIEF D0-10b), with freezes batched into them (§7) |
| R27 | X0 slips past W1, so X2's table scope and fuzz set slip | M | M | TOOLCHAINS.md not written by the end of W0 | X2 works on the B_iform scope; X2-fuzz's census amendment rule (§3.3); X2's verdict week does not move (Q9) |
| R28 | Aggregate desktop threads exceed the 8-thread cap, or a desktop job starts inside a quiet window (for example over SSH from the laptop) | M | H | wrapper not live by W1; the wrapper log shows > 8 tokens or a start inside a window | job wrapper (§3.5, §6.1); ad hoc multi-thread SSH jobs not allowed; a job inside a window voids that night's sessions (06 §6.8) |

---

## 11. Rejected plan options (tombstones)

These options were considered and rejected while writing this plan. They are written in the
[DECISIONS §4](../DECISIONS.md#4-design-tombstones) format, with triggers in the 06 §7.2 grammar. They
are **proposals** for DECISIONS.md: admitting them is an AUTHORITY operation that needs the Owner
(DECISIONS §1). The first four were buried on 2026-10-16 in the first version, and the last three in
revision 2 the same day. Fact names not yet recorded in any ledger evaluate to `unknown` and never
fire (06 §7.2).

```text
tombstone m0_x1_attempts_on_measurement_host {
    verdict: costlier                      // ~4.1k API attempts would contend with the 8-thread daytime cap and the quiet windows
    scope:   { milestone: m0, host: desktop_9950x, workload: x1_api_attempts }
    class:   H
    revisit_when: hw.measurement_host_count >= 2 || !owner.laptop_harness_host_approved
    evidence: [ROADMAP §3.2, §10] [PLAN §6.1]
    // survivor: the laptop hosts X1's API attempts; only the local-model pilot uses the desktop, in daytime
}

tombstone m0_laptop_measurement_host {
    verdict: unpredictable                 // mobile part, shared with benchmarks, not the host D0-8 recommends
    scope:   { milestone: m0, host: laptop_7940hs, run_types: {x3_parity, x4_calibration} }
    class:   H
    revisit_when: owner.measurement_host == laptop_7940hs
    evidence: [ROADMAP §11 D0-8] [06 §6.7]
    // survivor: the laptop runs simulation, analysis and the X1 harness; an optional Zen 4 fuzz cross-check cannot change a verdict
}

tombstone m0_same_family_review_as_cross_family {
    verdict: misleading                    // same-family reviewers share training priors, so their misses may correlate with the author's
    scope:   { milestone: m0, requirement: different_family_review }
    class:   F                             // under the assumption that same-family review misses are correlated
    revisit_when: meas.review_miss_corr(family: same) <= prereg(review.max_miss_corr)
    evidence: [ROADMAP §1 rule 5] [README "Independence"] [ARCHITECTURE §16 risk 8]
    // survivor: R-same reviews, labelled as such; the different-family item stays open until D0-10
}

tombstone m0_daytime_calibration {
    verdict: misleading                    // A/A calibration tests exchangeability on the declared quiet profile; daytime load breaks it
    scope:   { milestone: m0, host: desktop_9950x, window: daytime, run_types: {x4_aa, x4_planted, x3_parity} }
    class:   V
    revisit_when: meas.load_gate_pass_rate(window: daytime) >= prereg(x4.daytime_gate_rate)
               && meas.sigma_d(run: microbench, window: daytime) <= meas.sigma_d(run: microbench, window: quiet)
    evidence: [ROADMAP §3.5] [06 §6.1, §6.8]
    // survivor: daytime dry runs are engineering checks with outputs discarded; calibration and parity sessions run only in quiet windows
}

tombstone m0_fixed_four_night_ask {
    verdict: infeasible                    // 4 nights/week from W2 = 160 h by W6, below ROADMAP's 215 h; at sigma_d = 4% planted regression ends on W6's last night and X3 lands in W7
    scope:   { milestone: m0, cadence: plan_a, host: desktop_9950x, decision: d0_10d_night_rate_before_pilot }
    class:   H
    revisit_when: meas.sigma_d(run: microbench, window: quiet) <= prereg(plan.four_night_sigma_max)
    evidence: [ROADMAP §10] [D0_BRIEF D0-10d] [PLAN §6.3, check.py rev 2]
    // survivor: ask 7 nights/week (D0_BRIEF D0-10d); lower by the post-pilot rate rule of §6.3
}

tombstone m0_aa_one_planned_test_budget {
    verdict: misleading                    // sizing A/A at one planned test understates hours: A/A must also publish p90 time-to-pass (ROADMAP §3.5)
    scope:   { milestone: m0, run_types: {x4_aa_micro, x4_aa_e2e}, use: night_budget }
    class:   V
    revisit_when: x4.aa_stopping_rule == stop_at_planned_length
               || meas.aa_time_to_pass_p90(run: microbench) <= 1 * meas.planned_test_time(run: microbench)
    evidence: [ROADMAP §3.5] [PLAN §6.2]
    // survivor: §6.2 shows central and bound; the night ask is sized on the frozen stopping rule
}

tombstone m0_sigma_ta_from_mithril_arms_only {
    verdict: misleading                    // 05 §13's sigma_ta is the item x (Mithril - Rust) effect; two Mithril arms cannot estimate it
    scope:   { milestone: m0, experiment: x1, input: card_iteration_design_roadmap_s10 }
    class:   F                             // under the assumption that item x arm effects differ between arm pairs
    revisit_when: x1.card_iteration_arms >= {mithril_t01, rust}
    evidence: [05 §13 "Power"] [ROADMAP §10 measurement table]
    // survivor: Rust arm on card-iteration items, or a pre-registered prior floor (Q16)
}
```

---

## 12. Status table

Every track updates its own rows when work lands (status words as in §0). "As of" is the date of the
last update. Rows marked [M, plan] were checked by the plan track at 11:40 PT on 2026-10-16; the
others reflect the sprint brief or are not started. "Due" gives the checkpoint week under Plan A /
Plan B. "Gates" names the collection or step that the row unblocks.

| ID | Deliverable | Track | Status | Due (A / B) | Gates | Evidence | As of |
|---|---|---|---|---|---|---|---|
| S01 | D0 brief (`docs/D0_BRIEF.md`) | D0 | draft (present [M, plan]) | W0 / W0 | every D0 signature | [D0_BRIEF](../D0_BRIEF.md) | 10-16 |
| S02 | D0-10a–d signed (budget, cadence, families, windows) | Owner | blocked: Owner | W0 / W0 | metered spend, 2nd family, nights, cadence | — | 10-16 |
| S03 | D0-11b signed (role split) | Owner | blocked: Owner | W0 / W0 | family-B authoring | — | 10-16 |
| S04 | D0-12 signed | Owner | blocked: Owner | W0 / W0 | every Gatekeeper verdict | — | 10-16 |
| S05 | D0-9a signature form | Owner | blocked: Owner | W1 / W1 | X0's signature and every later one | — | 10-16 |
| S06 | D0-7a (or Q1 consent) for unattended nights | Owner | blocked: Owner | W2 / W2 | noise pilot, X3 A/B, calibration | — | 10-16 |
| S07 | D0-9b Owner key | Owner | blocked: Owner | W2 / W3 | kit hash-freeze (per D0_BRIEF) | — | 10-16 |
| S08 | Q1–Q6, Q9, Q17 answered | Owner | blocked: Owner | W0 / W0 | toolchains, store, windows, X2-gate rules, reference binary | §13 | 10-16 |
| S09 | Two weekly signing/commit slots set | Owner | blocked: D0-10b | W0 / W0 | every freeze (R26) | — | 10-16 |
| S10 | Quiet windows agreed (nights/week, times, GEMS paused) | Owner | blocked: D0-10d | W0 / W0 | all quiet nights | — | 10-16 |
| S11 | Hygiene settings applied by Pierce | Owner | blocked: Owner (checklist from X4) | W1 / W1 | a valid noise pilot | — | 10-16 |
| S12 | Second family provisioned (keys, pinned versions) | Owner | blocked: D0-10c | W1 / W1 | X1 authoring, blind batch, Provers, R-diff | — | 10-16 |
| S13 | Desktop job wrapper (8 tokens, window refusal, stamps) | X4 | todo | W1 / W1 | all multi-thread desktop jobs from W1 | — | 10-16 |
| S14 | X0 record | X0 | draft [M, plan] | freeze W0, sign W1 / same | X0 compiles; X0 verdict | [X0-census](prereg/X0-census.md) | 10-16 |
| S15 | X0 toolchains (LLVM, XED) and TOOLCHAINS.md | X0 | doing [M, brief]; TOOLCHAINS.md absent [M, plan] | W0 / W0 | X0 compiles | `scripts/runbook/` | 10-16 |
| S16 | X0 scripts | X0 | doing [M, plan] | W0 / W0 | — | `experiments/x0-census/scripts/` | 10-16 |
| S17 | X0 `census.json`, REPORT.md, re-derivation | X0 | blocked: S14 freeze, S15 | W1 / W1 | X0 verdict | — | 10-16 |
| S18 | Census handoff (hash + FP-sensitivity classification) | X0 → X2 | blocked: S17 | W1 / W1 | X2 fuzz vectors, table scope | — | 10-16 |
| S19 | M0-verdict record and mapping script | verdict | blocked: Q7 (or "pending Q7" lines as written) | W1 / W1 | mapping verdicts to §4 rows | §3.8 | 10-16 |
| S20 | Lark grammar v0 | X1 | todo | W1 / W2 | cards | — | 10-16 |
| S21 | Tier 0 and Tier 1 cards | X1 | todo | W1 / W3 | card iteration | — | 10-16 |
| S22 | `mithi` | X1 | blocked: Q4 (Rust toolchain location) | W2 / W5 | precondition | — | 10-16 |
| S23 | M0 tooling kit | X1 | blocked: Q4 | W3 / W9 | tooling arm | — | 10-16 |
| S24 | X1 harness (six arms, sandbox, resumable) | X1 | todo | W2 / W5 | all X1 attempts | `experiments/x1-harness/` | 10-16 |
| S25 | X1 power simulation | X1 | draft (results present [M, plan]) | W2 / W5 | X1-heldout n rule | `experiments/x1-harness/power/` | 10-16 |
| S26 | X1-card-iteration record (+ Rust arm if approved) | X1 | todo | W2 → W3 / W5 → W6 | card-iteration attempts | — | 10-16 |
| S27 | X1-heldout rules freeze, then fill-in | X1 | todo | W2 → W4 / W5 → W10 | held-out runs | — | 10-16 |
| S28 | X1-precondition record | X1 | todo | W3 / W9 | precondition run | — | 10-16 |
| S29 | X1-local-pilot record (tok/s under 8 threads first) | X1 | blocked: D0-10c (local model), Q18 | W4 → W5 / W9 → W10 | pilot runs | — | 10-16 |
| S30 | Card-iteration items (~20) | X1 | blocked: D0-10c, D0-11b, Q5 | W2 / W5 | card iteration | — | 10-16 |
| S31 | Held-out ≥ 60 + reserve to n_max, oracles ≥ 95% mutant kill | X1 | blocked: D0-10c, D0-11b, Q5, Q16 | W3 / W9 | held-out runs | — | 10-16 |
| S32 | Planted Dc corpus ≥ 100 | X1 | blocked: D0-10c | W2 / W8 | precondition | — | 10-16 |
| S33 | Card iteration done (≤ 3 epochs); attempts per hour measured | X1 | blocked: S26, S30 | W3 / W7 | σ_ta; held-out concurrency | — | 10-16 |
| S34 | `mithi` precondition passed | X1 | blocked: S28, S32, S61 | W3 / W9 | held-out runs | — | 10-16 |
| S35 | Held-out runs and Gatekeeper analysis | X1 | blocked: S27, S34 | W5 / W11 | X1 verdict | — | 10-16 |
| S36 | Local pilot | X1 | blocked: S29 | W5 / W10 | (reported only) | — | 10-16 |
| S37 | Semantics table | X2 | doing [M, plan: files present] | W5 / W9 | T1 | `experiments/x2-semantics/semantics/` | 10-16 |
| S38 | X2-fuzz record; Zen 5 fuzz and Bochs | X2 | blocked: S18 (or amendment rule) | W1 / W1 | vectors on silicon | — | 10-16 |
| S39 | `numerics_v1` ≥ 200 sealed; X2-mutants record | X2 | blocked: Q5 (store) | W2 → W3 / W6 → W7 | kill-rate measurement | — | 10-16 |
| S40 | X2-gate rules freeze; record signed | X2 | blocked: Q9 | W2 → W5 / W2 → W10 | X2 verdict run | — | 10-16 |
| S41 | `mithcheck` T1/T2 spike and rule proofs | X2 | todo | W4 / W9 | X2 verdict | — | 10-16 |
| S42 | Lockstep proof, R-diff Prover | X2 | blocked: S17; D0-10c | W4 / W8 | X2 verdict, X0 narrowing | — | 10-16 |
| S43 | X2 report and verdict | X2 | todo | W6 / W11 (W6 under B-cal) | M0 verdict | — | 10-16 |
| S44 | X3-parity: counting rule, rules, fill-in | X3 | todo | W1, W2 → W3 / W1, W3 → W4 | A/B sessions | — | 10-16 |
| S45 | Reference binary (clean `b5d3f14`; MSVC and clang-cl; hashed) | X3 | blocked: Q17 | W2 / W3 | X3 A/B, planted regression | — | 10-16 |
| S46 | Generator and scratch Hearth | X3 | todo (from W1) | W2 / W4 | A/B | — | 10-16 |
| S47 | X3 A/B nights | X3 | blocked: S10, S06, Q2, S44 | W3 / W4 | X3 verdict | — | 10-16 |
| S48 | X3 report (final after planted regression) | X3 | todo | W5 / W7 | M0 verdict | — | 10-16 |
| S49 | Measurement service v0 | X4 | todo | W1 / W1 | every quiet-night run | — | 10-16 |
| S50 | Sandbox (Job Object) | X4 | todo | W2 / W3 | hacks; X1 harness isolation | — | 10-16 |
| S51 | X4-noise-pilot record; pilot nights; σ_d published | X4 | blocked: S10, S06, S11 | W2 / W2 | N and c; night rate | — | 10-16 |
| S52 | `mithc profile measure` (one quiet night) | X4 | blocked: Q2, Q3, S10 | W2 / W2 | phys/emp bounds | — | 10-16 |
| S53 | X4-calibration rules, fill-in, sessions; time-to-pass, σ_d, throughput published | X4 | blocked: S06, S10, S04, Q15 | W2 → W3, nights W3–W6 / W2 → W4, nights W4–W10 | X3 finality; X4 verdict | — | 10-16 |
| S54 | X4-hacks-catalogue record; dev runs; kit hash-freeze; gated run | X4 | blocked: S07 (freeze step, per D0_BRIEF) | W2 → W3 / W2 → W4 | blind batch; X4 verdict | — | 10-16 |
| S55 | Blind batch (family B) and blind run | X4 | blocked: S12, S54 | W4 / W6 | X4 verdict | — | 10-16 |
| S56 | MIN/OPT oracle and F1-sim; held-out traces sealed | X4 | todo (laptop after 19:00 PT on 10-16) | traces W1; sim W4 / W1; W6 | X4-forge-sim | — | 10-16 |
| S57 | Tombstone import, revisit prototype, replay tests | X4 | todo | W4 / W7 | X4 verdict | — | 10-16 |
| S58 | Prune pilot reproduced | X4 | todo | W4 / W7 | X4 verdict | — | 10-16 |
| S59 | X4 report | X4 | todo | W6 / W11 | M0 verdict (may wait) | — | 10-16 |
| S60 | Core-calculus note | CC | doing [M, plan: file present, 11:38 PT] | W3 / W8 | CC gate | [core-calculus.md](core-calculus.md) | 10-16 |
| S61 | CC X1-subset rules frozen | CC | todo | W3 / W9 | `mithi` precondition | — | 10-16 |
| S62 | CC-gate record; R-diff review; signature | CC | blocked: D0-10c | W5 / W11 | M0 verdict | — | 10-16 |
| S63 | R-diff review backlog (§9 step 5) | reviewers | blocked: S12 | week after each signature | M0 verdict signature | — | 10-16 |
| S64 | PLAN.md | plan | draft (revision 2) | living | — | this file | 10-16 |
| S65 | COST.md | plan | draft | living | stop-loss (§5) | [COST.md](COST.md) | 10-16 |
| S66 | S0: R3 commit, ADR-0010, port base, corpus | Hearth / Owner | blocked: R3 commit, D0-2, D0-3 | not an M0 gate | M1's S1 | — | 10-16 |
| S67 | M0 verdict signed | Owner | blocked: S14–S63 | W6 / W12 | M0 outcome | — | 10-16 |

**Checkpoint review.** At each checkpoint (§5.1 or §5.2), the plan track:
- compares the status table with the checkpoint row;
- re-plans the slipped items;
- updates the risk register's signals;
- records the Owner's actual hours from COST.md against §7.

---

## 13. Owner questions

None of these is decided. Each item proposes something and names the decision it rests on.

1. **Quiet windows (D0-10d).** Which nights, at what times, and how many per week? The proposal
   matches D0_BRIEF D0-10d: 7 nights a week of 8 h from W2, which may be lowered after the noise pilot
   by the rule in §6.3. At 4 nights a week and σ_d = 4%, X3 lands in W7 and X4's calibration in W9
   [D, §6.3]. Inside a window, are other projects' jobs and the RTX 5070 queue idle? Are unattended
   Mithril runs allowed in those windows? D0-7a covers this. The noise pilot (W2) is the first
   unattended night, and X3's A/B is not the Forge.
2. **Thread cap.** Is the 8-thread cap an aggregate over all Mithril desktop jobs, as this plan reads
   it? May it lift inside quiet windows for end-to-end decode (production placement across both CCDs,
   06 §6.7) and for `mithc profile measure`'s all-core STREAM? If not, the end-to-end run type is
   declared with reduced placement, which changes what X4's end-to-end calibration covers, and
   all-core STREAM is not measured.
3. **Model and test data.** May X3's decode guard, X4's end-to-end A/A and the NVMe grid read the
   existing Qwen3-30B-A3B Q4 file on the desktop's NVMe, in place and read-only? Where is it? Nothing
   used for timing should stream from the USB HDD.
4. **Toolchains.** May Rust (for `mithi`, rust-analyzer and the Rust arm), a portable LLVM and a C
   compiler be installed on the laptop as the X1 harness host? On the desktop, may WSL installs grow
   the virtual disk on C:, or must they go to D:?
5. **Gatekeeper store.** Where do the sealed suites, the reserve, reference solutions, oracles and the
   mutant pool live? The proposal is outside every repository, encrypted, with a key the Builder
   sessions do not hold. Who holds the key? Is the Mithril repository public?
6. **Signature form before D0-9.** D0_BRIEF D0-9a recommends a signed git tag over each freeze commit,
   made with Pierce's own key. This plan follows whatever D0-9a says and keeps its first version's
   fallback (Pierce commits the signature block himself, naming the freeze commit) only if D0-9a is
   declined. Who makes freeze commits in this sprint, and in which weekly slots?
7. **M0 verdict composition.** ROADMAP §3.7 says the Gatekeeper "picks a row of §4", but several rows
   can apply at once, for example X3 kill plus X0 narrowing. The proposal: report every applicable
   row, with the most severe class governing (§3.8). Also:
   - "X2 kill alone … continue only if X1 and X3 pass": does an X1 or X3 amber count as a pass?
   - How does an X3 that is **barred** (failed planted-regression calibration) or still **waiting**
     count in that clause, and in the rule that pending experiments block the verdict? The draft
     treats both as "not a pass" and lets the verdict wait (provisional, pending Q7).
8. **X3 versus calibration timing.** May X3's parity verdict be computed before X4's microbenchmark
   planted-regression calibration has passed? The proposal: compute it, but make it final only after
   the calibration passes. This is not an edge case. At σ_d = 4% and 4 nights a week, planted
   regression ends on the last night of W6 with no slack, and X3 lands in W7. That is expected, not
   unlucky [D, §6.3]. At 7 nights a week, X3 lands in W5. Does a W7 X3 fit ROADMAP §3.7's "the other
   verdicts do not [wait]"? If not, the 7-nights rate is what keeps X3 on time.
9. **"End of week 6" at Plan B cadence.** X2's kill is judged "at the end of week 6" (ROADMAP §3.3),
   but ROADMAP §2 says gates hang on deliverables, except M1's schedule kill. At 15 h/week, is X2's
   deadline calendar week 6 (2026-12-03) or the scheduled verdict week? This plan does not choose. The
   choice has to be in the X2-gate rules before any data, by W2, and it is the Owner's. Calendar W6
   means Plan B-cal (§7.2): X2 is front-loaded and the M0 verdict moves to about W13–W14 [G]. The
   same question applies to X3's "two weeks of tuning" and to ROADMAP §3.7's "X4's calibration runs
   past week 6".
10. **API provisioning (D0-10).** Which providers and which pinned model versions for the X1 arms?
    Which local model for the pilot? Is there a weekly cap on metered spend?
11. **Plan A or Plan B.** Which cadence (D0-10b), and are any weeks off (2026-11-26, the 2026-12-25
    week, 2027-01-01)? Until D0-10b is signed, Plan B is operative (§0).
12. **Quiet-hour contingency.** ROADMAP's 60–215 h, like 06 §6.6, leaves out calibration blocks,
    sentinels, settling and voids. Should a contingency be held on top? The proposal is +25% [G],
    which also enters §6.3's rate rule. It is a cost question for D0-10. No threshold changes.
13. **Owner-hour logging.** Is a weekly total per track enough for COST.md?
14. **ROADMAP observation (no change made).** X2's kill clause is the one date-based kill in M0, and
    ROADMAP §2's exception names only M1's schedule kill. If calendar week 6 is meant, ROADMAP §2
    could say so. If not, ROADMAP §3.3 could say "the M0 verdict week". This plan edits neither
    (Q9).
15. **A/A stopping rule and the quiet-hour budget.** ROADMAP §3.5 asks the A/A sessions to publish
    median and p90 non-inferiority time-to-pass. The proposal (§3.5), for the X4 track to adopt or
    replace:
    - microbenchmark A/A sessions run to N, with superiority monitored throughout;
    - end-to-end A/A sessions (≥ 20 [target]) stop at non-inferiority e ≥ 20 or at N.

    Stopping end-to-end sessions at the planned length instead would censor the p90 when it exceeds
    the planned length, so this plan does not propose that. Under the proposal, M0 needs
    245.4–333.4 quiet hours at σ_d = 4% [D, §6.2], above ROADMAP §10's 215 h [inference].
    *ROADMAP observation, no change made:* §10's M0 row may be short at high σ_d. Its "8–27 nights"
    figure does not show the A/A stopping rule it assumes.
16. **σ_ta and the held-out reserve.** ROADMAP §10's card-iteration design (20 × 5 × 3 epochs × 2
    Mithril arms × 2 families) cannot estimate σ_ta as 05 §13 defines it (Mithril − Rust). Options:
    - (a) add a Rust arm on the ~20 card-iteration items: 200 attempts, $0.1–0.4k [D];
    - (b) pre-register a conservative prior floor for σ_ta, proposed by the X1 track.

    Also:
    - Approve a sealed reserve up to n_max (example 120 [G]), authored in W2–W3.
    - Pierce either reviews all n_max items up front, which costs hours not in ROADMAP's 55, or
      reviews the first 60 up front and the rest in W4 only if the n rule draws them, which delays
      the held-out start by that review time.

    *ROADMAP observation, no change made:* §10's card-iteration row and 05 §13's recompute rule do
    not fit together.
17. **Reference binary.** May M0 measure a clean checkout of `b5d3f14`, built with Hearth's release
    flags (MSVC, and clang-cl for the proxy arm), as the stand-in for `hearth-c-ref`? Its hash would
    be pinned in X3-parity and X4-calibration. The S0 tag would then not be a prerequisite (§3.4).
    Where should the clean checkout and its build live: D:, or inside the C: budget?
18. **X1 local pilot under the cap.** Either grant a daytime exception to the 8-thread cap for the
    pilot's 5–10 h [inference, ROADMAP §3.2], or accept a re-estimate from a short measured tok/s run
    under 8 threads. The result goes into the X1-local-pilot record before it freezes.
19. **Family-B metered sub-cap (D0-10a).** Family B's authoring and reviews are metered and draw on
    the same approved amount before the held-out runs ([COST §1.3, §5](COST.md#5-alerts-and-stop-loss)).
    Should D0-10a set a sub-cap for them, inside X1's and the other experiments' caps?
20. **Gated catalogue run before or after the kit freeze.** The proposal (§3.5): engineering runs on
    the unfrozen kit, then freeze, then the gated run, where a miss is HALT-F. The alternative is to
    run the gated catalogue before the freeze, which moves the freeze, blind-batch commissioning and
    X4-hacks-blind one week later. Which does Pierce prefer?
21. **Collection by instruction (D0-12).** The README collection rule lets an Owner instruction cover
    a frozen, unsigned record. D0_BRIEF's D0-12 recommendation limits that to deterministic,
    exhaustive runs (X0). Which applies to X2-fuzz and the X4 noise pilot? §8 marks both "pending
    D0-12".

---

## 14. Change log

| Date | Change | By |
|---|---|---|
| 2026-10-16 | First version: tracks, dependencies, Plan A and Plan B, machine calendar, owner hours, pre-registration schedule, review protocol, risks, plan tombstones, status table, owner questions | plan track (Claude, same-family; not yet reviewed) |
| 2026-10-16 | Revision 2 after one same-family review of 18 findings (§15). Changes: Plan B operative until D0-10b; night ask aligned with D0_BRIEF D0-10d plus a post-pilot rate rule; A/A bound column and stopping-rule proposal; Plan B checkpoints, night calendar and Plan B-cal; σ_ta Rust arm or floor plus the sealed reserve; X0 → X2 census dependency; rules freezes before development data; explicit kit/catalogue order; job wrapper and aggregate thread cap; `mithc profile measure` in the night order; reference-binary stand-in; D0 "needed by in this plan" column; barred-X3 mapping lines; R-diff backlog schedule; R23–R28; three tombstones; rebuilt status table; Q15–Q21; adopted the track-created paths | plan reviser (Claude, same family as author; independent context) |

---

## 15. Review log

| Date | Reviewer | Family | Lens | Scope (input) | Findings by severity | Outcome |
|---|---|---|---|---|---|---|
| 2026-10-16 | Reviewer 1 | Claude (same family as author; independent context) | schedule, dependencies and resource feasibility. The lens name was not relayed; this is inferred from the findings and the reviewer's scratch directory `review-plan-sched` | PLAN.md and COST.md first version (file times 11:31 and 11:30 PT), `check.py`, D0_BRIEF, ROADMAP | blocker 0, major 13, minor 5 (18 in all) | 18 accepted (3 with modifications, below), 0 rejected |
| 2026-10-16 | Reviewer 2 | Claude (same family as author; independent context) | not relayed | not relayed | none relayed to the reviser | — |

**Accepted with modification.**
- *Night ask (finding 1).* The reviewer proposed a fixed drop to 4 nights a week below σ_d = 2.5%.
  Revision 2 uses a derived rule instead (§6.3). It also corrects the capacity in the reviewer's
  recompute: with calibration records signed in W3 (§8), W3–W6 capacity at 4 nights a week is 128 h,
  not 136 h.
- *A/A sessions (finding 2).* The proposed Owner question asked whether end-to-end A/A sessions may
  stop at the planned length. Revision 2 does not propose that, because stopping there would censor
  the p90 time-to-pass that ROADMAP §3.5 publishes. Q15 instead proposes stopping at
  non-inferiority e ≥ 20 or at N.
- *Cadence (finding 3).* Plan B-cal takes X2's extra hours from X1, X4 and CC, not only from X1 and
  CC. It also moves X0's narrowing hours to W6, because the narrowing is judged jointly with X2. The
  checkpoints run B-C0 to B-C7, because the verdict week (W12) needs its own row.

**Rejected findings.** None. Each finding was checked against the sources: ROADMAP §1, §3, §10 and
§11; D0_BRIEF lines 48–53, 251 and 317–319; 05 §13 lines 783–810; 06 §5.2, §6.6–§6.8;
`x0_decode.py` line 153; the X0 record §2 and §4; the X1 power tables; directory listings and file
times; and `get_usage` at 18:45Z.

**Same-family caveat.** Both reviewers and the reviser are Claude models. This review satisfies
README's independent-review requirement for a draft plan, not any ROADMAP different-family
requirement (§9).
