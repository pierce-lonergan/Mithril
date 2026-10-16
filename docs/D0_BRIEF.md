# D0 brief: the owner decisions D0-1 to D0-12

Status: **DRAFT for the Owner's signature.** Prepared 2026-10-16 by the d0 track (a Claude agent) and
revised the same day after two same-family reviews (§9). Not reviewed by a second model family (§3).
Nothing in this brief is decided until Pierce signs it as described below.

ROADMAP §11 is authoritative for every D0 item: its wording, its "needed by" and its "if declined".
This brief may make a deadline earlier or a rule more precise. It never loosens one, except where a
signature line explicitly offers a loosening as a labelled option that only you can grant (D0-12x
and D0-7x). Those options are never the recommendation. Where this brief thinks ROADMAP is wrong or
unclear, it says so in §7 and changes nothing.

**How to sign.** Under article A10 ("authority is a signature, never a sentence",
[03 §1](architecture/03-trust.md)), the authority is a signed git tag, not the ticked file.
1. **Tick.** In your own commit, change `[ ]` to `[x]` on each line you decide. Exactly one box per
   line. Fill AMEND text and Value fields on the same commit. An unticked line is not decided.
2. **One session, one commit, one tag.** Each signing session is one commit by you plus one signed,
   annotated tag `d0-sign-<n>` (n = 1, 2, …) on that commit, made with the key chosen in D0-9a.
3. **The tag message decides.** It lists every item decided in that session, one per line, in the
   grammar of Appendix B (`D0-12: YES`, `D0-10b: YES; H=15 h/week; signing slots=Tue, Fri`,
   `D0-12x: ROADMAP`). An item counts as decided only if a verified tag names it with the same choice,
   text and values as the ticked line at that tag's commit.
4. **Void rules.** A ticked line that no verified tag names is void. A ticked line, AMEND text or Value
   field changed after the tag that named it is void until a new tag names it again.
5. **Value fields.** A filled Value field is part of the decision. A YES whose Value differs from the
   `(rec …)` printed beside it counts as AMEND. A line marked `Value (required)` with a blank field is
   not decided (unless you chose NO).
6. **Who writes what.** Agents never tick boxes, fill Value fields, write AMEND text, write tag
   messages or type your name. The `Tag:` field on each line is a readable mirror you may fill.
7. **Checking.** Appendix B's verifier applies rules 3–5 and lists void lines. It is provisional,
   pending D0-9a; agents may install it in `experiments/` only.

**Evidence tags** follow [m0/README.md](m0/README.md). Conventions specific to this brief:
- **[M·d0]**: checked by this track on 2026-10-16 against the read-only Hearth clone at commit
  `b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220` (committed 2026-10-05; GitHub `main` as cloned
  2026-10-16), or against the named Mithril or local file, by reading the cited line or running the
  cited command. **[M·d0 read]** marks a value read from a file whose measurement this track did not
  repeat. The breaker checks can be reproduced with Appendix A.
- All week numbers are [inference] from ROADMAP §2's timeline unless a PLAN section is cited.
- Owner-hour and dollar figures for single decisions are this track's [inference] or [G], unless a
  ROADMAP section is cited.

**What this brief cannot see.** The desktop's Hearth working tree holds uncommitted "R3" changes
(17 files and 3 handovers, per [07 §4](architecture/07-hearth-port.md)). They are not in the clone.
Facts that exist only there are cited from the dossiers and marked *not verifiable at b5d3f14*:
the 0.9 heat-decay default, the grown `hearth_options`/`hearth_stats` structs and
`docs/results/policy-default.md`.

**Contents**
1. Summary, sorted by deadline
2. Week 0: needed now
3. One model family so far
4. The decisions (in deadline order), with the total owner ask at the end
5. Hearth-maintainer decisions without a D0 number
6. Tombstones this brief proposes
7. Owner questions, with answer lines
8. What this brief could not verify
9. Review log
- Appendix A: reproducing the breaker checks
- Appendix B: the signing-tag verifier
- Sources

---

## 1. Summary, sorted by deadline

Sorting rule [inference, ROADMAP §2]: a milestone deadline means the milestone's start, and a stage
inside a milestone comes after that start. M1, M1's S1 and S1 all fall at about month 1.5; ties are
listed in D0 order. "First blocked step" is the earliest work that stops; the deadline itself never
moves later than ROADMAP §11.

| Deadline | Item | Decision | Recommendation | If unsigned by then |
|---|---|---|---|---|
| Week 0 (per gate; first: X0) | [D0-12](#41-d0-12-pre-registration-sign-off) | Sign each gate's frozen record before collection | Yes, as ROADMAP §11 says | No gate can be evaluated |
| Week 0, before X0's first compile | [D0-12x](#41-d0-12-pre-registration-sign-off) | Any collection before signature? | No exception (ROADMAP as written). The X0 exception is offered as a loosening only you can grant | No collection under any record before its signature |
| Week 0 | [D0-12i](#41-d0-12-pre-registration-sign-off) | Did you give the instruction the X0 record quotes? | None: a fact only you know | The X0 record's authorisation line stays unconfirmed |
| Week 0, with the first signature | [D0-9a](#43-d0-9-owner-key-management) | Interim signing method and key | Signed `d0-sign-<n>` tags, with a hardware key that needs a touch | No record can be SIGNED; typed names are forgeable |
| Week 0 | [D0-10a](#42-d0-10-budget-cadence-model-families-quiet-windows) | Metered API budget, in tranches | T1 up to $3k [G] now; T2 with each X1 measurement record; T3 on request. Ceiling $35.5k [D] | No metered (non-subscription) API spend; Family B work cannot start |
| Week 0 | [D0-10b](#42-d0-10-budget-cadence-model-families-quiet-windows) | Owner hours per week, and rhythm | A figure you can sustain. The calendar stretches; no threshold moves | The M0 calendar is unknown |
| Week 0 | [D0-10c](#42-d0-10-budget-cadence-model-families-quiet-windows) | Model families, roles, API access | Claude plus one non-Anthropic frontier family, plus a local pilot. You hold the keys | X1 cannot run (§1 rule 5); reviews stay same-family |
| Week 0 (first use ≈ week 2) | [D0-10d](#42-d0-10-budget-cadence-model-families-quiet-windows) | Quiet windows on the 9950X | 4 pilot nights of 8 h, then a rate set from the measured σ_d (PLAN §6.3's rule, at most 7) and re-signed; co-tenant jobs paused | X3's A/B and X4's calibration cannot run |
| X4 (first blocked step ≈ week 2) | [D0-7a](#44-d0-7-forge-authority) | Unattended measurement | Only inside quiet windows (ROADMAP §11) | No unattended quiet night |
| X4 (first blocked step: unattended F1-sim, ≈ week 2) | [D0-7x](#44-d0-7-forge-authority) | Unattended daytime F1-sim | ROADMAP's wording (F1-sim attended). The daytime option is a loosening only you can grant | F1-sim runs attended |
| X4 (first use: grants at M6) | [D0-7b](#44-d0-7-forge-authority) | Who signs grants | You | No grants, so no opt-in profiles |
| X4 (first use: the first default change, at the latest after S4) | [D0-7c](#44-d0-7-forge-authority) | `timing_only` defaults by ADR only | Yes | Defaults could change without an ADR |
| X4 (first blocked step: none in M0 if D0-9a's tags are accepted [inference]) | [D0-9b](#43-d0-9-owner-key-management) | Hardware-token Owner key, recovery path, separate gate account. **Needs buying 2 tokens (price not researched) and an OS-account setup** | Yes | No ledger AUTHORITY facts from M3 |
| S0, with the R3 commit | [D0-5a](#45-d0-5-hearth-defect-decisions) | `struct_size` fields | Add them in the R3 commit | S6a cannot export `hearth.h` exactly; one B1 item lost |
| S0 corpus (≈ week 3 to finish S0 in M0) | [D0-2, 2a, 2b](#46-d0-2-adr-0010-specified-transcendentals) | ADR-0010, specified transcendentals | `canon_v1` expf, `cr` sinf/cosf, before the corpus | Corpus built on platform libm, then re-baselined |
| End of M0 (first blocked step ≈ weeks 2–3 if S0 needs it, Q12) | [D0-1](#47-d0-1-may-mithril-be-the-cores-source) | Mithril-generated C as the core's source | Option A, landed as an ADR on its own | M0 verdict STOP-L |
| M1 | [D0-11a](#48-d0-11-spec-authority) | Who seals specs | You, as an AUTHORITY act | Spec escrow cannot start |
| M1 | [D0-11b](#48-d0-11-spec-authority) | Different families for Author and Builder | Yes | Maintainers write all specs |
| M1's S1 | [D0-3](#49-d0-3-s0-freeze-hearth-c-ref-and-the-hash-corpus) | S0 freeze, `hearth-c-ref`, hash corpus as a golden tier | Yes, reproduced twice | No bit-exact oracle, so no port |
| S1 (ROADMAP: S4/S6a) | [D0-5b](#45-d0-5-hearth-defect-decisions) | MXCSR guard | Set and restore at every entry; set and assert in workers | One B1 item lost; T1's precondition unchecked |
| S1 | [D0-11c](#48-d0-11-spec-authority) | `validated` as an INV-VERIFY evidence class | Yes, by a Hearth ADR | S1's kernels have no admissible `validated` grade |
| M4 | [D0-8](#410-d0-8-measurement-host) | Measurement host | The desktop; a second box when D-22 fires | Campaigns bounded by measured throughput |
| S4 (before R3 only if R3 keeps 0.9) | [D0-5c](#45-d0-5-hearth-defect-decisions) | Heat-decay value | 0.9, signed only after `policy-default.md` is committed and read; otherwise DEFER with R3 at 0.995 | ADR-0004 and the code keep disagreeing |
| S4 | [D0-5d](#45-d0-5-hearth-defect-decisions) | Mirror hashing or a qualified INV-DET-1 | Decide now; land the qualification in its own ADR by S4; per-slab hashes in FORMAT v2 | O4 (lossless tiers by per-slab hash) cannot be claimed |
| M5 | [D0-6a, 6b, 6c](#411-d0-6-gpu-scope) | RTX 5070 in scope, `nvcuda.dll`, display on the iGPU | Defer all three to M5; the VRAM tier stays reserved | CPU-only; the GPU becomes a tombstone |
| S6 (M5) | [D0-4](#412-d0-4-normativity) | When meanings become normative | Status quo: NUMERICS.md and C normative through S6 | Dual normativity with a drift check |
| Before B2's pre-registration (before M6) | [D0-10e](#42-d0-10-budget-cadence-model-families-quiet-windows) | B2 margin: 3 or 5 points | Defer until M0/M1 variance is measured | B2 cannot be pre-registered |

The unnumbered Hearth-maintainer decisions (HM-1 to HM-9b) are in §5. The total owner ask, in hours,
is at the end of §4.

---

## 2. Week 0: needed now

ROADMAP §2 starts X0, X1, X2, X4 and the core-calculus note in week 0, and X3 in week 1. Each row
names the decisions that experiment needs and the first step that stops without them. Claude agent
work runs on the existing subscription and needs no D0-10a money (§4.2, D0-10a).

| Work (start) | Needs signed | First step that stops without it | Why |
|---|---|---|---|
| **X0** census (week 0; verdict at the end of week 1.5) | **D0-12, D0-12x, D0-12i**, with D0-9a | Under D0-12x = ROADMAP: X0's first compile. Under D0-12x = X0: the Gatekeeper's verdict | **Collection: provisional, pending D0-12.** ROADMAP §11 requires the signature before collection. The [m0/README.md](m0/README.md) exception applies only if you choose D0-12x = X0 in a signed tag (D0-9a). The X0 record is DRAFT [M·d0, status line] and quotes an Owner instruction of 2026-10-16 (D0-12i). X0 compiles are daytime builds. ROADMAP §3.1 asks for no quiet window and no second family |
| **X1** writability (week 0) | **D0-10c** and D0-10a (T1) now; D0-12 before card-iteration and held-out runs, with D0-10a's T2 released by those records; D0-10d's day/night split before the local pilot | Family B writing the sealed suite and the `mithi` planted corpus (week 0) | Suite writing dominates X1's cost ($7–15k, ~55 h [inference, §3.2]). Task authors must come from a different family than the card editors ([05 §13](architecture/05-agent-protocol.md), guards); the planted corpus from a family other than `mithi`'s author (§3.2). The kill needs ≥ 2 frontier families (§1 rule 5, §3.2). Only Claude is available today. D0-11b is not needed for this (§4.8, Q1) |
| **X2** checker spike (week 0) | D0-12 before fuzz and mutant runs; D0-10c and D0-10a (T1) for the Prover by ≈ week 5 | The first Zen 5 fuzz batch | The fuzz vector budget is pre-registered (§3.3). The lockstep-loop proof needs a Prover from a different family (§3.3). Fuzzing is daytime only (§3.2, DR-023) |
| **X3** one meaning (week 1) | **D0-10d, D0-7a**; D0-12 before the A/B | The interleaved A/B per release compiler (≈ weeks 2–3) | The A/B runs unattended on quiet nights (§2, "quiet" row; §3.4) |
| **X4** evaluator integrity (week 0) | **D0-10d, D0-7a**; D0-10c and D0-10a (T1) for the Adversary; D0-12 before calibration; D0-7x before any unattended F1-sim; D0-7b, D0-7c and D0-9b by X4 (ROADMAP §11) | The first unattended quiet night: the noise pilot (≈ week 2 [inference, PLAN §6.3]); commissioning the blind batch after the kit hash-freeze (≈ week 2) | The blind batch needs an Adversary from a different family (§3.5). Calibration needs ≥ 100 A/A sessions plus ≥ 100 per planted level [target, §3.5], run overnight. The kit freeze can be signed with a D0-9a tag [inference] |
| **Core-calculus note** (week 0) | Nothing to draft; D0-10c and D0-10a (T1) by ≈ week 4 | The Prover and Adversary review | §3.6 needs reviewers from another family, and you sign the note |
| **S0**, C side (M0 per [07 §4](architecture/07-hearth-port.md); not in ROADMAP §2) | HM-5a (R3 commit), D0-5a, **D0-1** (if S0's step 2 includes it, Q12), D0-2, D0-3, D0-9a | Tagging `hearth-c-ref@port-base-1`, then the corpus | 07 §4 sets the S0 order: commit R3 → constitutional ADRs (§9) → ADR-0010 → tag → corpus twice. ARCHITECTURE §13.1 item 2 takes D0-1 and D0-2 early "because S0 and the M0 verdict depend on them". D0-5c is needed for S0 only if R3 keeps 0.9 |

**Signatures needed this week, in the order that unblocks most:**

1. **D0-12, D0-12x and D0-12i, with D0-9a.** These make every later signature meaningful. Under
   D0-12x = ROADMAP, X0's first compile waits for your signature on X0's record.
2. **D0-10c.** Family B unblocks X1's suite writing, the longest pole.
3. **D0-10a (tranche T1) with D0-10b.** The metered money and the calendar.
4. **D0-10d.** Co-tenant jobs can then be rescheduled before the first quiet night (≈ week 2).

The readings these signatures assume are §7 Q4, Q5, Q14 and Q15; each has its own answer line.

**Other week-0 owner asks (from [PLAN](m0/PLAN.md) checkpoint C0, as read on 2026-10-16):** PLAN
Q1–Q6, Q9 and Q17 answered (PLAN Q1 overlaps D0-10d, PLAN Q6 overlaps D0-9a); the harness host and
toolchain locations approved; two weekly signing/commit slots set; the job-wrapper design agreed.
PLAN C0 also lists D0-11b, following this brief's earlier draft; this revision returns D0-11b to M1
(Q1). PLAN Q19 and Q21 are answered by D0-10a's T1 and by D0-12x.

**Week-0 owner time:** ≈ 2.75 h to decide [D: item-6 figures of D0-12, D0-12x/12i, D0-9a and
D0-10a–d], plus 0.25–1 h of key setup for D0-9a [G], 1–3 h of accounts and keys (D0-10c) and 1–2 h of
settings (D0-10d) [inference], plus 1–2 h to review and sign X0's record if D0-12x = ROADMAP
[inference].

**Next, before the first quiet night (≈ week 2):** D0-7a. **By ≈ weeks 2–3:** D0-5a with HM-5a;
D0-1, if Q12 says S0's step 2 includes it; D0-2; D0-7x before any unattended F1-sim.

---

## 3. One model family so far

Every agent that has worked on Mithril so far is a Claude model. That covers the design agents
(README, "How this design was produced"), the M0 tracks, the author of this brief and both reviewers
of it (§9). So every ROADMAP requirement for a *different* model family is unmet today:

| Requirement | Where | State on 2026-10-16 |
|---|---|---|
| ≥ 2 model families in every agent gate | ROADMAP §1 rule 5; DR-017 | Unmet |
| X1 participants from ≥ 2 frontier families | §3.2; 05 §13 | Unmet |
| X1 `mithi` planted corpus written by a family other than `mithi`'s author | §3.2 | Unmet |
| Task authors from a different family than the card editors | 05 §13 (guards) | Unmet |
| X2 lockstep proof reviewed by a Prover from a different family | §3.3 | Unmet |
| X4 blind hack batch written by an Adversary from a different family | §3.5 | Unmet |
| Core note reviewed by a Prover and an Adversary from another family | §3.6 | Unmet |
| Sealed specs: Author and Builder from different families. A same-family record caps strength at `tested` | [03 §8.4–8.5](architecture/03-trust.md); D0-11b | Not yet due (M1) |
| M1 held-out batch written by a family other than the card editors' | §5, M1 | Not yet due |
| F1-A gains hold on ≥ 2 families; comprehension preconditions on ≥ 2 families | §8; 07 §5 | Not yet due |

**Consequences.**
- Until D0-10c names a second family and you have provided access, M0 reviews are logged
  "same-family, independent-context" ([m0/README.md](m0/README.md)). That is weaker than ROADMAP
  asks.
- No X1 kill can be evaluated.
- ROADMAP §11's recommendations were also drafted by Claude agents. This brief adds no independent
  check of them.

---

## 4. The decisions (in deadline order)

Each item gives:
1. the decision;
2. the recommendation;
3. the evidence;
4. needed by, first blocked step, and what "declined" means;
5. dependencies;
6. cost [inference];
7. provisional work;
8. signature lines.

Where a YES rests on a reading of ROADMAP that §7 asks about, the item says "This YES assumes
Q<n> = <answer>; if you answer Q<n> otherwise, tick AMEND."

### 4.1 D0-12 Pre-registration sign-off

1. **Decisions.**
   - **D0-12.** Will you sign each gate's frozen pre-registration record, naming its freeze commit,
     before data is collected under it? This is ROADMAP §11's recommendation: "The Owner signs each
     record before collection".
   - **D0-12x.** Is any collection allowed before your signature? ROADMAP §11 allows none, and
     ARCHITECTURE §13.1 item 1 repeats "signed before collection". [m0/README.md](m0/README.md)'s
     collection rule is looser: it allows collection under a FROZEN record plus your explicit
     instruction, with no verdict until SIGNED. The X0 record relies on it, and so do two rows of
     PLAN §8 (X2-fuzz and X4-noise-pilot: "an instruction suffices"). Granting that rule is an
     **amendment of ROADMAP §11's D0-12, a loosening that only you can make.** m0/README itself says
     "Nothing here may loosen a ROADMAP threshold". The options:
     - **ROADMAP**: no exception. X0's record is signed before X0's first compile.
     - **X0**: an exception for X0 only, the one M0 measurement that is deterministic and exhaustive,
       with no sampling and no stopping rule. Collection under FROZEN plus your instruction; no
       verdict until SIGNED. Loosens ROADMAP §11 for X0.
     - **X0+PILOT**: as X0, plus the X4 noise pilot, which is descriptive and never pooled (PLAN
       §8). Loosens ROADMAP §11 for both. Its data do feed the rules that fix X4's clip c and amber
       limit N (PLAN §8, amendments), so the case for it is weaker than for X0 [inference].
   - **D0-12i.** Did you give the instruction the X0 record quotes: "Start the parts that need no
     owner decision: X0, instruction census"? The record quotes it, but a repository file cannot
     carry your authority (A10).
2. **Recommendation.**
   - **D0-12: YES**, as ROADMAP §11 says.
   - **D0-12x: ROADMAP.** X0's record is short and its analysis is deterministic. Signing it before
     the first compile costs about 1–2 owner h in week 0 [inference] and keeps ROADMAP as written.
     The X0 and X0+PILOT options are offered because the X0 record and PLAN already assume them; this
     brief does not recommend a loosening.
   - **D0-12i:** no recommendation. Tick what is true. Under D0-12x = ROADMAP, the instruction
     authorises preparing X0, never collecting.
   - Under every option, X1, the X2 fuzz and mutant runs, the X3 A/B and the X4 calibration are
     sampled or sequential and wait for your signature. See tombstone
     `sampled_collection_before_signature` (§6).
3. **Evidence.**
   - ROADMAP §1 rule 1: a record is written before any data. You sign it, it becomes an AUTHORITY
     fact, and thresholds never move once data has been seen.
   - Rule 3: the Gatekeeper is deterministic code plus the Owner key.
   - The X0 record is DRAFT [M·d0, its status line].
   - About 17 records fall due in M0 [M·d0: the rows of PLAN §8].
4. **Needed by.** Per gate (ROADMAP §11). The first is X0: before its first compile under
   D0-12x = ROADMAP, or before its verdict at the end of week 1.5 (§3.1) under D0-12x = X0.
   - *Declined:* "The gate cannot be evaluated" (ROADMAP §11), so there is no M0 verdict.
   - *Delayed:* no data is collected under any record until it is signed (ROADMAP), or only X0's
     data under your instruction (X0).
   - *Effect on PLAN:* if signed as recommended, PLAN §8's X0-census row (instruction, then a
     signature before the verdict) moves X0's signature before its first compile, and the X2-fuzz and
     X4-noise-pilot rows ("an instruction suffices, pending D0-12") need their records signed before W1
     and W2. PLAN §7.1 already schedules signing X0 in W0–W1, "Sign X2-fuzz" and "Sign the X4
     noise-pilot record or instruction" in W1, so what changes is the timing and form, about 1–2 h per
     record [inference]. D0-12x answers PLAN Q21. PLAN is not this track's file.
5. **Dependencies.** D0-9a (the signature's form); D0-10b (hours to read records).
6. **Cost.** 0.5 h to decide D0-12 and 0.25 h for D0-12x and D0-12i [inference]. Then 1–2 owner h
   per record: ≈ 17 records per PLAN §8, so ≈ 17–34 h [D: 17 × 1–2 h]. PLAN §7.1 schedules these
   signatures inside the X tracks' hours, so they sit inside ROADMAP's ~195 h [inference]. No API
   cost.
7. **Provisional.** Agents keep records DRAFT and build tooling. They test it only on smoke inputs,
   such as `experiments/x0-census/scripts/smoke/`. A record is frozen by a commit you make or
   authorise, because agents in this sprint do not commit. No Hearth data is collected under any
   record until D0-12 is signed, or until you choose D0-12x = X0 in a signed tag.

D0-12x = ROADMAP assumes Q4 = ROADMAP; if you answer Q4 otherwise, tick AMEND or another option.

```text
D0-12   [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
D0-12x  [ ] ROADMAP (recommended)   [ ] X0   [ ] X0+PILOT   [ ] AMEND: ________   Tag: d0-sign-__
D0-12i  [ ] CONFIRMED   [ ] WITHDRAWN   Tag: d0-sign-__
```

### 4.2 D0-10 Budget, cadence, model families, quiet windows

ROADMAP §11 gives one row: needed in week 0 (the B2 margin before M6). If declined: "No M0". It is
split here into five parts so that each can be signed separately. Declining any of D0-10a to D0-10d
still means "No M0"; each part names the mechanism.

#### D0-10a M0 metered API budget, measurement included

1. **Decision.** How much *metered* API spend do you approve for M0, how is it released, and under
   which stop-loss rule?
2. **Recommendation.**
   - **Claude agent work is not in this budget.** The agent team (orchestrator, tracks, reviewers)
     runs in Claude Code on a Max subscription, which costs $0 in the API column
     ([COST.md](m0/COST.md) §2, [M, `get_usage`, 2026-10-16T18:17Z] as recorded by the plan track).
     D0-10a neither covers nor blocks that work. The subscription's limits are a throughput
     constraint (PLAN risk R17).
   - **D0-10a approves metered spend only:** Family B (D0-10c), harness attempts and any other
     metered key. Release it in tranches:

     | Tranche | Covers | Released by | Amount |
     |---|---|---|---|
     | T1 | Family B authoring and review: X1 sealed tasks, oracles, reference solutions and the `mithi` planted corpus; the X4 blind batch; the X2 lockstep-proof and core-note reviews. Harness smoke runs | This signature (week 0) | Up to **$3k** [G] |
     | T2a | X1 card iteration, ≈ 1.2k attempts | Your signature on the X1-card-iteration record | $0.6–2.4k [inference, §10] |
     | T2b | X1 held-out runs, ≈ 2.9k attempts at 60 items | Your signature on the X1-heldout record | $1.4–5.8k at 60 items [inference, §10]; more if the record's fill-in sets n > 60 (COST.md §5) |
     | T3 | Anything else, up to the ceilings below | A signed tag, on request with a COST.md snapshot | — |

   - **Ceilings** per experiment, at the top of each ROADMAP range:

     | Experiment | Ceiling |
     |---|---|
     | X0 | $1.5k |
     | X1 | $15k |
     | X2 | $6k |
     | X3 | $3k |
     | X4 | $8k |
     | Core note | $2k |
     | **Sum** | **$35.5k** [D: sum of ceilings], within ROADMAP's M0 line of $16–36k [inference, §3.7] |

   - **Stop-loss:** COST.md §5's levels, as read on 2026-10-16: notify at 50% of the approved
     amount; stop new X1 runs at 80% (a held-out batch already under way runs to its fixed n); do not
     start the held-out runs unless the remaining approved budget covers n × 48 × p_high ($5.76k at
     n = 60 [D, COST.md §5]); for Family B, notify at 50% of T1 and stop new authoring at 100%. In
     addition, an experiment that reaches its ceiling stops. Money moves between tranches or
     experiments only by a signed tag (D0-9a), never by a note.
   - Hardware is not included: the key tokens (D0-9b) and any second box (D0-8).
3. **Evidence.**
   - Per-experiment costs: §3.1–3.6, summing to $15.5–35.5k [D; COST.md §1.2], against M0's $16–36k
     [inference, §3.7].
   - Measurement (§10): X1 held-out ≈ 2.9k attempts, $1.4–5.8k; card iteration ≈ 1.2k attempts,
     $0.6–2.4k. Total ≈ 4,080 attempts and $2.04–8.16k [D], priced at $0.5–2 per agentic attempt
     [inference, §10].
   - Whether that measurement sits inside X1's $7–15k is this brief's [inference], not a ROADMAP
     statement. §10 says only that the API figures "sit inside the milestone lines above", and §3.2
     says suite writing "dominates" X1's cost. Read as inside X1, $8.2k of measurement would leave at
     most $6.8k for suite writing [D: 15 − 8.2]. Read as separate, the ceilings would sum to $43.7k
     [D: 35.5 + 8.2], above ROADMAP's $36k. See Q14.
   - T1's $3k is a judgment with no price research behind it [G]. ROADMAP's lines assumed metered
     spend for all agent work [inference, COST.md §2]; with Claude on the subscription, only Family
     B's share is metered. The 80% alert brings T1 back to you before it binds. T1 is the Family-B
     sub-cap that PLAN Q19 asks about.
   - Metered spend to date: $0 [G: no metered keys provisioned, COST.md row 1].
4. **Needed by.** Week 0 (T1). T2a and T2b with their records.
   - *Declined:* No M0 (ROADMAP §11, D0-10). Mechanism: with no metered spend no second family can
     work, so X1 cannot run under §1 rule 5.
5. **Dependencies.** D0-10c (Family B's attempts are inside this budget); D0-12 (the T2 releases);
   D0-9a (tags); D0-8 and D0-9b (hardware, not costed).
6. **Cost.** This item is the cost. Owner time: 0.5 h now, then about 0.25 h a week to read COST.md
   [inference].
7. **Provisional.** No metered API spend. X0 and all drafting run on the subscription only.

This YES assumes Q14 = INSIDE; if you answer Q14 otherwise, tick AMEND.

```text
D0-10a  Value (required): T1 cap = ____ (rec $3k); stop-loss = ____ (rec COST.md §5 plus ceilings)
D0-10a  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
```

#### D0-10b Cadence: owner hours per week

1. **Decision.** How many hours a week will you give M0, and in what rhythm?
2. **Recommendation.** Sign a weekly figure you can sustain. The plan stretches to fit it, and no
   threshold moves (ROADMAP §10).
   - Rhythm: two fixed signing slots a week, plus asynchronous review.
   - Queue order: see Q13. ARCHITECTURE §16 risk 6 orders the review queue "by evidence grade". PLAN
     §7.2's ordering rule puts first "Signatures and freeze commits that unblock machine time (the
     nights) or a second family" [G]. This item does not choose between them.

   | Hours/week | M0 length [D: 195 h / H] |
   |---|---|
   | 33 | ≈ 6 weeks (the ROADMAP plan) |
   | 20 | ≈ 10 weeks |
   | 15 | 13 weeks |
   | 10 | ≈ 20 weeks |

3. **Evidence.**
   - M0 needs ~195 owner h [inference, §3.7, §10]. That is the sum of D0 10 h, X0 10 h, X1 55 h,
     X2 40 h, X3 20 h, X4 40 h and the note's 20 h [D].
   - Peak load is about 33 h/week; at 15 h/week M0 runs about 13 weeks (§10).
   - Owner review is the binding constraint (§10).
   - D0 runs from week 0 and takes about 10 owner h in all [inference, §3.7]. The week-0 items
     (D0-12, D0-12x/12i, D0-9a, D0-10a–d) take ≈ 2.75 h to decide [D: sum of their item 6], plus the
     setup hours listed in §2. The total owner ask, including work outside ROADMAP's 195 h, is at the
     end of §4.
4. **Needed by.** Week 0. Without it the calendar is unknown and the quiet-night plan cannot be
   sized.
   - *Declined:* No M0 (ROADMAP §11, D0-10). Mechanism: with no committed hours no record can be
     signed (D0-12), so no gate can be evaluated.
5. **Dependencies.** All other items draw on these hours.
6. **Cost.** About 0.25 h [inference].
7. **Provisional.** The team plans to ROADMAP's stretch case, 15 h/week, until you sign. This is a
   reversible planning assumption.

```text
D0-10b  Value (required): H = ____ h/week; signing slots = ________
D0-10b  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
```

#### D0-10c Harness model families, and how API access is provided

1. **Decision.** Which model families take part in M0, which roles does each hold, and how does
   the harness reach them?
2. **Recommendation.**
   - **Family A: Claude** (Anthropic), already in use. It edits the Mithril card and writes
     `mithi`, because it wrote the design.
   - **Family B: one non-Anthropic frontier family of your choice.** OpenAI and Google are the
     obvious candidates [inference; current offerings not checked here]. The exact model versions
     are pinned in each pre-registration. Family B:
     - writes X1's sealed tasks, oracles, reference solutions and the `mithi` planted corpus;
     - is X4's blind-batch Adversary;
     - is the Prover for X2's lockstep proof;
     - is the Prover and Adversary for the core note.
   - Both A and B take part in X1 as participants (but see Q15).
   - **Local:** one Hearth-served model runs as the X1 pilot: 60 attempts, 5–10 machine h, daytime
     only [inference, §3.2]. It joins every arm from M1. Qwen3-30B-A3B is the model with measured
     Hearth figures [R11]; you pick the exact checkpoint.
   - **Access.**
     - You open and hold the provider accounts and keys.
     - Keys live outside the repository and outside cloud-synced folders. Only a harness runner
       that you start reads them. Agents never see or handle a key.
     - Use a provider-side spend limit where the provider offers one [not verified here], plus a
       harness-side meter that stops at the D0-10a tranche.
     - Before any sealed item leaves the machine, confirm each provider's data-use terms for API
       inputs. Sealed suites must not reach training data (05 §13, contamination rule). Their
       canary strings only detect a leak after the fact.
     - The harness logs the model id and version on every attempt.
3. **Evidence.**
   - ROADMAP §1 rule 5 and §3.2: ≥ 2 families. 05 §13: "One family drafted Mithril's card, so the
     second also serves as the independent-writer test".
   - [inference] The analysis model `success ~ arm * family + ...` (05 §13) treats family as a
     factor. This brief infers that the task-authoring family may also take part. 05 §13 does not
     address a family that wrote the sealed tasks also attempting them; its guard is only "task
     authors from a different family than the card editors". See Q15.
   - Errors of similar models correlate (Goel et al. [RV: D2-E], via 03 §8.5).
   - Family B's share of X1 measurement: ≈ 2,040 attempts, $1.0–4.1k [D: half of 4,080 × $0.5–2].
   - Hearth's server already speaks OpenAI- and Anthropic-compatible HTTP
     (`python/hearth/server.py:1-4` [M·d0]). Whether it supports the tool calls an agentic harness
     needs is not verified.
4. **Needed by.** Week 0. X1's suite writing stops first.
   - *Declined:* No M0 (ROADMAP §11, D0-10). Mechanism: X1 cannot run under §1 rule 5, so there is no
     M0 verdict; the m0 reviews also stay same-family.
5. **Dependencies.** D0-10a; D0-12; D0-10d (daytime slots for the local pilot).
6. **Cost.** 0.5 h to decide and 1–3 h to set up the accounts and keys [inference]. Dollars are
   inside D0-10a.
7. **Provisional, pending D0-10c.** Claude builds family-agnostic harness infrastructure on the
   subscription: the runner, scoring, oracle execution, mutant generation, and the power and IRT
   code. No sealed item content is written and no metered attempt is run.

This YES assumes Q5 = CONFIRM and Q15 = YES; if you answer either otherwise, tick AMEND.

```text
D0-10c  Value (required): Family B = ________; local model = ________
D0-10c  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
```

#### D0-10d Quiet-machine windows on the 9950X

1. **Decision.** When is the desktop quiet for measurement, how many nights, and what stops during
   those hours, including the GEMS project's GPU queue and the other CPU jobs?
2. **Recommendation.** A staged window, sized from measurement rather than from the worst case.
   - **Stage 1, the pilot week.** 8 h a night, **4 nights**, from the first night after the
     measurement service v0 passes its acceptance check ([inference] ≈ week 1.5–2). They carry the X4
     noise pilot (2–3 nights) and the profile measurement (1 night) (PLAN §6.3 [G]).
   - **Checkpoint.** After the noise pilot measures σ_d, the rate from the next week is the smallest
     number of nights a week whose capacity covers the reconstructed demand × (1 + contingency) by the
     verdict horizon of the cadence in force: the end of W6 under Plan A, the end of W10 under Plan B.
     This is PLAN §6.3's rule; the demand per test is n × 4·t_run × c hours with
     n = max(6, 12·σ_d²/δ²) blocks at δ = 3% (ROADMAP §10). The team proposes the rate; you re-sign it
     by tag. At most 7.
   - **End.** When X3's and X4's planned quiet hours are met, not at a fixed week.
   - **Inside a window:**
     - no agent sessions, compiles, object audits or local-model generation (06 §6.8, DR-023);
     - **the GEMS GPU queue and other CPU jobs paused**;
     - no interactive use by you; it voids the running session (06 §6.8).
   - **Outside the windows:** X0 compiles, X2 fuzzing, builds and the X1 local pilot, never
     overlapping a window.
   - **System and security settings are yours, not the agents'.** They include a measurement power
     plan, a Defender scan exclusion for the data directory, Windows Update maintenance hours and
     the indexer. The service only detects these and voids sessions (06 §6.7).
   - **If GEMS cannot pause:** tombstone `quiet_window_cotenancy` (§6) records it, and D-22 can fire
     (D0-8, Q7).
3. **Evidence.**
   - M0 quiet need: 60–215 h, or 8–27 nights of 8 h [inference, §10]. That covers X3 per release
     compiler, plus X4's 300 microbenchmark sessions and ≥ 20 end-to-end A/A [target, §3.5].
   - PLAN §6.2's reconstruction: 60.3 h (≈ 7.5 nights) at σ_d = 2% and 221.0 h (≈ 27.6 nights) at
     σ_d = 4% [D, PLAN §6.2]. PLAN §6.3's rate table, with a 25% contingency, gives 3 nights a week
     at σ_d = 2% and more than 7 at σ_d = 4% under Plan A, and 2 and 5 under Plan B [D, PLAN §6.3,
     central A/A case].
   - **Why not a fixed rate.** A fixed 4 nights is not safe: at σ_d = 4% under Plan A, X3 finishes in
     W7 [D, PLAN §6.3], and ROADMAP §3.7 lets only X4's verdict wait. A fixed 7 nights from W2, ≈ 248 h
     to week 6 [D: 31 × 8 h], is what this brief's earlier draft asked and what PLAN §6.3 and PLAN Q1
     now follow. It is above the top of ROADMAP's 60–215 h, asked before σ_d is known, and tied to a
     week-6 end that D0-10b's 15 h/week planning case (about 13 weeks) does not reach. The staged
     window asks for the pilot nights now and lets the measured σ_d set the rest.
   - Hearth's own 9950X measurements ran on a shared machine at 10–86% CPU load (measured; Hearth
     `governance/handovers/H03-forward-gen-001.json:124` [M·d0 read]).
   - **GEMS** [M·d0 read, 2026-10-16; not verified beyond these files]: the RTX 5070 "belongs to
     another project's queue" (PLAN §2, tagged [M, brief]). The `GEMS_Challenge` repository on the
     laptop (commit `2752b35`, 2026-10-16) keeps an `ops/gpu_calendar.md` that plans GPU jobs and
     CPU/network jobs by night (PT), and `ops/eligibility_E1_plan.md:127` records runs on "the same
     RTX 5070 / CUDA build". That this is the desktop's card is [inference] (its remote tooling
     includes `tools/remote/desk_gpu.sh`).
   - σ_d per run type is itself an M0 deliverable (06 §6.6).
   - [inference] GPU jobs use host CPU threads, DRAM bandwidth, PCIe DMA and package power. A
     CPU-load gate can pass while any of these disturbs a DRAM-bound measurement, and X4's A/A test
     checks exchangeability on this desktop.
4. **Needed by.** Week 0 (ROADMAP §11), so that the jobs can be rescheduled. The first use is
   ≈ week 2.
   - *Delayed:* every lost night pushes X3 and X4 back.
   - *Declined:* No M0 (ROADMAP §11, D0-10). Mechanism: no parity or calibration measurement can run,
     so X3 and X4 cannot be judged.
5. **Dependencies.** D0-7a; D0-8 (D-22); D0-10b.
6. **Cost.** No API cost. 0.5 h to decide, and 1–2 owner h for the settings [inference].
   - **You:** no interactive desktop use during windows, 8 h × nights a week: 32 h in the pilot week,
     then 16–56 h a week at 2–7 nights [D: nights × 8 h], depending on σ_d and your cadence.
   - **GEMS:** loses its GPU queue and night CPU jobs on those nights. Its own calendar schedules
     night work [M·d0 read]; the cost to GEMS is not estimated here.
7. **Provisional.** The measurement service and load gate are built and tested in daytime. Every
   session is marked "not quiet, void for gates". No gate-grade measurement is taken.

```text
D0-10d  Value (required): pilot-week nights = __ (rec 4); window = __:__-__:__ local; first night = ______; co-tenant jobs paused = ___ (rec yes); rate after the pilot = ______ (rec PLAN §6.3 rule, re-signed)
D0-10d  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
```

#### D0-10e B2 margin (deferred to before M6)

1. **Decision.** Is B2's agent non-inferiority margin 3 points or 5 points?
2. **Recommendation.** DEFER. Choose before B2's pre-registration, using the item variance σ_ta
   measured at X1 and M1. P3 or P5 means choosing now.
3. **Evidence** (ROADMAP §7, §10).
   - 3 points needs ≈ 4k attempts per arm, ≈ 12k in total, and $6–24k. M6 then costs $20–55k.
   - 5 points needs ≈ 1.5k attempts per arm. M6 then costs $16–40k.
   - All of these are [inference].
   - The margin may widen before collection, never after.
4. **Needed by.** Before B2's pre-registration (before M6). *Declined (no choice by then):* B2
   cannot be pre-registered. ROADMAP gives the B2 margin its own date, so this part does not carry
   D0-10's "No M0".
5. **Dependencies.** D0-10a for M6; X1's measured σ_ta.
6. **Cost.** None now.
7. **Provisional.** Nothing.

```text
D0-10e  [ ] DEFER (recommended)   [ ] P3   [ ] P5   [ ] AMEND: ________   Tag: d0-sign-__
```

### 4.3 D0-9 Owner key management

ROADMAP §11: needed by X4. Recommendation: "Offline or hardware-backed key with a written recovery
path". If declined: "No AUTHORITY facts, so no promotion". It is split here because a signing method
is needed with the first signature (§7 Q2).

1. **Decisions.**
   - **(a)** How do you sign during M0, before the ledger exists, and with what key?
   - **(b)** How is the long-term Owner key held and recovered?
2. **Recommendation.**
   - **(a)** You sign each D0 session with a signed `d0-sign-<n>` tag ("How to sign"), and each
     frozen record and each verdict with a signed git tag over its freeze commit. The typed lines
     only mirror the tags. **Use a key agents cannot use:**
     - **HW** (recommended): a hardware-backed key that needs a physical touch per signature.
     - **PASS**: a passphrase-protected key held outside the OS account the agent sessions run
       under, or with any signing agent's passphrase caching turned off [inference]. The interim
       choice if no token is at hand by your first signature.
     - **SOFT**: a plain software key on the account agents run under. A tag made with it is no
       stronger than a typed name (tombstone `software_key_on_agent_account`, §6); choosing it accepts
       that A10 gap for M0.

     Git can sign tags with OpenPGP or SSH keys [not verified on the laptop]; the tool is your
     choice. Record the key's fingerprint in the Value line, so that Appendix B's output can be
     checked against it.
   - **(b)** Two hardware tokens, as 03 §11.3 describes:
     - a primary token that needs a physical touch per signature, and a backup kept offline, both
       listed in `.mith/trust/roots.toml` (from M3);
     - a written recovery path kept offline;
     - high-impact AUTHORITY approved a second time from a second device.

     The gate key is held by a separate local account or VM that agents cannot read. Until that
     separation exists, gate signatures defend only against accidental and in-protocol tampering
     (03 §11.3). **This needs buying two tokens (price not researched) and setting up that account,
     a system and security change only you make.** If you choose HW for (a), the same primary token
     can serve both, and the purchase moves to week 0.
3. **Evidence.**
   - A10 (03 §1). AUTHORITY covers admitting specs and goldens, defaults, grants, α
     replenishment, canon admission, TCB changes and key rotation (03 §4.4).
   - ROADMAP §1 rules 1 and 3 put the Owner key in every gate evaluation.
   - The agent sessions of this sprint run under your Windows account [M·d0: this session's scratch
     directory is under `C:\Users\PIERCE~1\AppData\Local\Temp`], so a software key in that account is
     reachable from them [inference].
   - 03 §11.3's key management, ledger signing (03 §4.3) and AUTHORITY facts (03 §4.4) are v0, M3.
     ROADMAP §3.5's tombstone import uses "a `mithc revisit` prototype", not ledger admission.
4. **Needed by.**
   - (a) With the first signature: week 0.
   - (b) X4 (ROADMAP §11). First blocked step: [inference] none in M0 if (a)'s signed tags are
     accepted for X4's kit freeze and calibration records; required before the first ledger
     AUTHORITY fact (M3).
   - *Declined (a):* no record can be SIGNED, so no gate can be evaluated (D0-12). *Declined (b):*
     "No AUTHORITY facts, so no promotion" (ROADMAP §11).
5. **Dependencies.** D0-12 depends on (a). From M3, ledger AUTHORITY acts depend on (b): D0-7b's
   grants (M6), D0-11a's sealing once the ledger exists, and re-baselines under D0-3. Before M3 they
   use (a).
6. **Cost.** (a): 0.25 h to decide, plus 0.25–1 h of key setup [G]. (b): 0.25 h to decide; 2–4 h for
   the tokens and the recovery note, and 1–3 h for the separate account [inference]. The tokens are
   hardware that ROADMAP §10 does not cost. Recurring from M3: each high-impact AUTHORITY act needs
   a second approval from a second device (03 §11.3), about 0.1–0.25 h per act [G].
7. **Provisional.**
   - (a): **nothing; hard block.** No signature exists until you make one.
   - (b): agents draft the `roots.toml` format and the verification scripts, including Appendix B's
     verifier, in `experiments/` only. Agents never create, hold or see any key.

```text
D0-9a  Value (required): key fingerprint = ________
D0-9a  [ ] HW (recommended)   [ ] PASS   [ ] SOFT   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
D0-9b  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
```

### 4.4 D0-7 Forge authority

ROADMAP §11: needed by **X4**, for all three parts. Recommendation: "Owner signs grants; defaults by
ADR; unattended only inside quiet windows". If declined: attended runs only. Later sources give later
*first uses* (03 §4.4: grants at v1, M6; 07 §9.3 item 8: the first live-engine Forge run, after S4).
This brief keeps ROADMAP's X4 as the deadline for every part (Q11).

1. **Decisions.**
   - **(a)** May measurement runs run unattended on the desktop, and when?
   - **(x)** May X4's F1-sim (simulation and proposer work, no measurement) run unattended in the
     daytime?
   - **(b)** Who signs standing grants?
   - **(c)** Do `timing_only` defaults change only by Owner ADR?
2. **Recommendation.**
   - **(a) YES.** Unattended **measurement**, meaning the X4 noise pilot, the X3 A/B, the X4
     calibration and later confirmation runs, happens only inside declared quiet windows, under the
     sandbox (Job Object, no network, read-only goldens; §3.5). The supervisor yields to your use and
     voids the session (06 §6.8). This is ROADMAP §11's wording.
   - **(x) ROADMAP**, read literally: F1-sim runs attended. The DAYSIM option would let it run
     unattended in the daytime under the normal agent rules and never inside a window, which matches
     06 §6.8's day/night split and DR-023; M0 has no promotion authority, and grants arrive at v1, M6
     (03 §4.4). DAYSIM is broader than ROADMAP §11's "unattended only inside quiet windows", so it is
     an amendment only you can grant (Q6). This brief does not recommend it.
   - **(b)** You sign every grant. You set q, γ and the α budgets (03 §7.2).
   - **(c) Yes.** Every shipped default, `timing_only` included, needs an Owner-signed ADR with its
     dossier (DR-015).
3. **Evidence.**
   - DGM faked its logs, and o3 hacked 30.4% of RE-Bench runs [R01, via DR-015].
   - ADR-0004 was overturned by measurement [R02 §10].
   - The specimen grant has q = 0.20 and γ uniform over 40 [target], so its first test needs
     e ≥ 200 (06 §8.2).
   - Defaults are ADR-gated from v0 (M3) (03 §7.3).
4. **Needed by.** X4 (ROADMAP §11), every part.
   - (a) First blocked step: the first unattended quiet night, whichever comes first of the X4 noise
     pilot, X3's A/B and X4's calibration (≈ week 2 [inference, PLAN §6.3]).
   - (x) First blocked step: any unattended run of X4's F1-sim, which PLAN puts on the laptop from
     W2 (PLAN §6.3 [G]).
   - (b) First use: grants at M6 (03 §4.4).
   - (c) First use: the first default change, at the latest the first live-engine Forge run after S4
     (07 §9.3 item 8).
   - *Declined:* attended runs only (ROADMAP §11). Someone would then have to be present for 60–215
     quiet h [inference, §10], and X4's verdict slips (amber, §3.7).
5. **Dependencies.** D0-10d; D0-9b (grants are signed); D0-8.
6. **Cost.** About 0.5 h for all four lines [inference].
7. **Provisional, pending D0-7a.** Daytime, attended test sessions marked void for gates. No
   unattended night run.

DAYSIM on D0-7x assumes Q6 = MEASUREMENT.

```text
D0-7a  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
D0-7x  [ ] ROADMAP (recommended)   [ ] DAYSIM   [ ] AMEND: ________   Tag: d0-sign-__
D0-7b  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
D0-7c  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
```

### 4.5 D0-5 Hearth defect decisions

ROADMAP §11: needed by S4/S6a. Recommendation: "Decide now; land each before the stage that needs
it". If declined: B1 defect items shrink. The parts have different deadlines. 07 §9.3 puts
`struct_size` at S0 (item 3) and MXCSR at S1 (item 5); ARCHITECTURE §17 puts `struct_size` with the
R3 commit and gives no stage for MXCSR. This brief uses the earlier dates, because they are stricter
(Q10).

1. **Decisions.**
   - **(a)** Add `struct_size` (or version) fields to `hearth_options` and `hearth_stats`?
   - **(b)** Adopt the MXCSR invariant?
   - **(c)** Which LFU heat decay is normative, 0.9 or 0.995, and when?
   - **(d)** Full-content mirror hashing, or a qualified INV-DET-1?
2. **Recommendation.**
   - **(a)** Yes. Add the fields in the R3 commit (S0, HM-5a), so that S6a can export `hearth.h`
     exactly and keep the Python toolkit unchanged (07 §13).
   - **(b)** Yes. Set the default MXCSR on entry and restore the caller's value on exit at every
     `hearth.h` and `hx_*` entry, and set and assert it at pool-worker start (ARCHITECTURE §6.3).
   - **(c)** Three options:
     - **DECAY_09** (recommended): supersede ADR-0004 with 0.9 as the default and LRU as the named
       baseline, and record LRU's 1 GiB, no-prefetch win as a niche finding for the Forge (M4).
       **Sign it only after HM-5b has committed `docs/results/policy-default.md` and you have read
       it.** This brief could not see that file. Land it in its own change, merged before the R3
       commit or as a separate commit in the same merge, never in the same change as D0-1.
     - **DEFER**: commit R3 with its heat-decay default set back to 0.995, matching ADR-0004 and the
       code at b5d3f14, and decide at S4 as ROADMAP says. Cheap and reversible. Whether anything
       else in R3 relies on 0.9 is not verifiable here.
     - **DECAY_0995**: keep ADR-0004's 0.995 as normative now; R3's default then also changes back.

     If you want R3 committed before you have read `policy-default.md`, DEFER is the choice.
   - **(d)** Decide now, as ROADMAP says: qualify INV-DET-1 as "mirrors (assuming byte-identical
     mirror files)" in its own ADR that cites INV-DET-1, landed by S4. 07 §9.3 item 6 says "qualify
     now", but no M0 step needs the change earlier [inference]. Add per-slab content hashes in FORMAT
     v2 (07 §11).
3. **Evidence.**
   - **(a)** `hearth.h` has no size field at b5d3f14 [M·d0]. The `read_errors` field made
     `hearth_get_stats` write 8 bytes past the Python buffer on every OS
     (`governance/reviews/2026-10-05-ci-first-runs.md:14` [M·d0]). R3 grows both structs again
     [R11; not verifiable at b5d3f14].
   - **(b)** No MXCSR, `getcsr`, `_controlfp` or `fesetround` reference exists in `engine/`
     [M·d0, grep]. `q_rint` uses the 1.5·2²³ magic constant (`quant.c:46-47` [M·d0]).
     `cvtps_epi32` relies on round-to-nearest-even (`quant_avx2.c:100`, `quant_avx512.c:99`
     [M·d0]). The cost of an MXCSR save and restore per entry is not measured.
   - **(c)** At b5d3f14 the code default is 0.995 (`store.c:884`), matching
     `ADR-0004-lfu-default-eviction.md:22` and `hx_store.h:39` [M·d0]. The 0.9 default exists only
     in R3 [R11; not verifiable at b5d3f14]. DR-015 already records the drift in Mithril; no Hearth
     record does. Measured in the engine:
     - LFU 0.995 was the worst policy at every cache size;
     - LRU won at 1 GiB without prefetch;
     - LFU 0.9 won at 2–4 GiB and whenever prefetch was on.

     This comes from [R02 §10] and Hearth `docs/results/policy-default.md`, which is not in the
     clone. The decay changes speed, never output: INV-DET-1 covers "eviction policy"
     (`INVARIANTS.md:11` [M·d0]). So it needs no corpus re-baseline.
   - **(d)** `check_mirror` compares the size, preamble, metadata and both directories, but slab
     content only on the first page of up to 16 slabs (`store.c:79`, `store.c:747-782` [M·d0]).
     `pick_file` picks the mirror with the fewest outstanding reads and rotates ties, a load- and
     timing-dependent choice (`store.c:295-296` [M·d0]). A full hash at open would read the whole
     container: ≈ 2.4 s per mirror [D: 17.0 GB synthetic Qwen3 container
     (`H03-forward-gen-001.json:124`, conditions [M·d0 read]) ÷ 7.16 GB/s (measured) [R11]].
   - **Breaker.** Landing ADR-0004's supersession together with D0-1's ADR retires 2 of 8 Accepted
     ADRs (25%) and trips the 15% breaker. Landed alone, each retires 1 of 8 (12.5%) and passes. A
     reworded INV-DET-1 passes only with an ADR that cites it [M·d0, Appendix A, cases C, D, E, F].
     Tripping the breaker only requires your `decisions-reviewed` label (Hearth
     `governance/README.md:308-309` [M·d0]); ADR-0008 says it exists because "a single large change
     can quietly overturn many earlier decisions" (`ADR-0008-generational-governance.md:14-15`
     [M·d0]). **Landing D0-1 and D0-5c separately is recommended for review and revert granularity,
     not to avoid the breaker.**
   - **B1.** ROADMAP §7 lists exactly five defects for B1. Four of them depend on D0-5: mirror
     hashing, `struct_size`, MXCSR and the decay drift. The fifth, the `hx_store_heat` race, does
     not.
4. **Needed by.**
   - (a) S0 (the R3 commit); at the latest S6a.
   - (b) S1 (07 §9.3 item 5). This is earlier than ROADMAP's S4/S6a and therefore stricter.
   - (c) S4 (ROADMAP). Before the R3 commit only if R3 is to keep 0.9 (DECAY_09).
   - (d) S4.
   - *Declined:* "B1 defect items shrink" (ROADMAP §11), below five named defects unless a substitute
     is accepted (§7 Q9).
5. **Dependencies.** HM-5a and HM-5b (R3 and the evidence file); D0-1 (land separately); D0-2
   (INV-DET-1 wording if ADR-0010 is declined); D0-6 (device axis later).
6. **Cost.** 1 h to decide; 3–6 h to review four small Hearth changes [inference]. API is part of
   S0 and S1 and is not costed in ROADMAP (§7 Q3).
7. **Provisional, pending D0-5.** Draft the ADR texts and the C diffs in Mithril's `experiments/`,
   not in Hearth. Nothing merges.

```text
D0-5a  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
D0-5b  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
D0-5c  [ ] DECAY_09 (recommended; only after HM-5b)   [ ] DEFER   [ ] DECAY_0995   [ ] AMEND: ________   Tag: d0-sign-__
D0-5d  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
```

### 4.6 D0-2 ADR-0010, specified transcendentals

1. **Decisions.** Will Hearth replace "the platform libm" in NUMERICS.md with named, specified
   functions before the hash corpus is built (D0-2)? Which function for `expf` (D0-2a) and for
   `sinf`/`cosf` (D0-2b)?
2. **Recommendation.** Adopt ADR-0010 before the S0 corpus (DR-014):
   - **D0-2a, `expf`: `canon_v1`.** A Hearth-authored, fixed op-DAG with no FMA, in scalar, AVX2 and
     AVX-512.
   - **D0-2b, `sinf`/`cosf`: `cr`.** Either Hearth-authored, or vendored CORE-MATH if you rule that
     vendored MIT source satisfies INV-DEP (HM-6). Either way it is checked exhaustively over all
     2³² inputs against an independent correctly rounded reference. **If neither builds under MSVC by
     the fallback date in the Value line, D0-2b returns to you for re-signature. Nothing amends
     automatically.**
   - **`sqrtf`:** unchanged. It stays a true `sqrtf`, never `rsqrt`.
   - Extend the canonical-NaN rule to the §4 elementwise outputs (07 §3 item 5).
   - Record the output-change rate under INV-LOSSLESS-DEFAULT.
   - Update the bit-exact references in `test_model.c` and `test_quant.c`. The goldens are not
     re-locked.
   - Propose INV-DET-4, cross-OS hash equality, as a separate invariant ADR.
3. **Evidence.**
   - **Today.** NUMERICS.md says `expf`, `sinf`, `cosf`, `sqrtf` "come from the platform libm"
     (`docs/NUMERICS.md:13-14` [M·d0]). No ADR-0010 exists at b5d3f14: the records are ADR-0001
     to ADR-0009 [M·d0].
   - **The problem.** UCRT's FMA3 and non-FMA3 paths disagree on 1 `expf`, 44,232 `sinf` and
     18,018 `cosf` inputs. UCRT misrounds 23,276 `expf` inputs and ≈ 2.87 M `sinf`/`cosf` inputs
     each. All of this was measured over 2³² inputs on the 9950X [G04 F3].
   - **canon_v1 expf.** The prototype has 0 mismatches across scalar, AVX2 and AVX-512 over 2³²
     inputs. It is 99.19% correctly rounded, with a maximum error of 1 ulp. It runs at 0.204
     ns/element on AVX-512, against 1.12 ns for scalar UCRT (measured) [G04 F5.3].
   - **cr expf.** Scalar `cr` costs about +0.3% of decode time at 4,096 context and +0.9% of a
     2,048-token prefill, or, at a pessimistic 2.4× CORE-MATH ratio, about +1.5% and +4%
     [inference, G04 F7]. No vectorised `cr` expf that builds under MSVC is known [G04 F5.2]. After
     the attention kernel work, a scalar `expf` could reach ≈ 15–20% of long-context attention time
     [inference, G04 F7].
   - **Output change.** Nearly every token's logits change once [inference, G04 F3], and so do
     11–13% of RoPE positions (measured on a Qwen3-shaped table) [G04 F3].
   - **Goldens.** The golden suite pins no absolute logits, so it needs no re-lock [G04 F8;
     `tests/golden/test_golden_invariants.py` M·d0].
   - **Breaker.** ADR-0010 on its own retires no ADR, so the breaker stays quiet [M·d0, Appendix A,
     case A]. NUMERICS.md is a maintainer-only contract (`governance/README.md:291` [M·d0]).
   - **Open.** Whether CORE-MATH builds under MSVC is unverified. Vendoring under INV-DEP is a
     maintainer ruling [G04, open questions 1–2].
4. **Needed by.** The S0 corpus (ROADMAP §11). For S0 to finish inside M0 (07 §4), the team needs
   the signature by ≈ week 3 [inference: about two weeks of C work and review, then two corpus
   runs].
   - *Delayed:* S0 slips and S1 waits (D0-3), or the corpus is built first and re-baselined later.
     A re-baseline is an AUTHORITY operation with ledger invalidation and a second real-model run
     (07 §3).
   - *Declined:* "libm drift risk; `parity::` shim fallback" (ROADMAP §11). INV-DET-1 is reworded to
     name the CRT/libm build and the CPU features. DR-014's trigger
     `hearth.adr(0010).status == rejected` fires.
5. **Dependencies.** HM-5a (R3 comes first in the S0 order); D0-3; D0-9a; HM-6; D0-6
   (`canon_v1::expf` carries over to PTX, DR-022).
6. **Cost.** 1 h to decide; 3–6 h to review the ADR, the C diff and the exhaustive-check report
   [inference]. API ≈ $1–3k [inference]; S0 has no ROADMAP cost line (§7 Q3). The exhaustive
   binary32 check takes ≈ 22 s for 3 functions × 2 CRT paths on 32 threads (measured [G04]).
7. **Provisional, pending D0-2.** Implement the candidates and the exhaustive checker in Mithril's
   `experiments/` only, and measure them. No Hearth branch, local or pushed. Draft the ADR-0010
   text. No Hearth merge and no corpus.

```text
D0-2   Value (required): fallback date for D0-2b = ________
D0-2   [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
D0-2a  expf: [ ] CANON_V1 (recommended)   [ ] CR   [ ] AMEND: ________   Tag: d0-sign-__
D0-2b  sinf/cosf: [ ] CR (recommended)   [ ] CANON_V1   [ ] AMEND: ________   Tag: d0-sign-__
```

### 4.7 D0-1 May Mithril be the core's source?

1. **Decision.** May Hearth's engine core be Mithril-generated C11, checked in and regenerated in
   CI, under a new ADR that supersedes ADR-0001?
2. **Recommendation.** Option A (DR-026, [07 §9.1](architecture/07-hearth-port.md)).
   - `.mith` sources and the generated C11 live side by side. CMake builds from the C alone, and CI
     checks that a pinned `mithc` regenerates it byte for byte.
   - INV-DEP's text stays unchanged. The superseding ADR keeps ADR-0001's pool and OS-isolation
     bullets verbatim and adds option A's conditions as the reading of INV-DEP.
   - Land it **on its own**. The breaker will not fire (Appendix A, case B), so no label is required;
     add `decisions-reviewed` yourself to mark it as constitutional (07 §9.1).
   - Sign the decision by the end of M0, and merge the Hearth ADR before S1 merges.
3. **Evidence.**
   - INV-DEP: "The engine core is C11 + OS APIs only: no third-party libraries, no C++ runtime, no
     OpenMP", enforced by "review" (`INVARIANTS.md:18` [M·d0]).
   - ADR-0001's reasons: build "with nothing but a C compiler", stay easy to audit, ship no runtime
     (`ADR-0001-c11-core-persistent-pool.md:10-17` [M·d0]).
   - At b5d3f14, 8 ADRs are Accepted and ADR-0009 is Proposed [M·d0, `adr.py index --rev HEAD`].
   - Superseding ADR-0001 alone retires 1 of 8 (12.5%) and stays under the 15% limit. Bundled with
     ADR-0004 it is 2 of 8 (25%) and trips [M·d0, Appendix A, cases B, C]. The limit is
     `adr.py:421`, `--max-fraction` default 0.15 [M·d0], and ADR-0008 lines 41-44.
   - So R11's claim that a Mithril core "trips the circuit breaker" does not hold for option A
     (07 §13).
   - Generated files stay LF-only under `.gitattributes` `* text=auto eol=lf` [M·d0], so the
     byte-for-byte check does not flap.
4. **Needed by.** The end of M0 (ROADMAP §11), because ROADMAP §4 has an M0 verdict row for "Owner
   rejects a Mithril-sourced core".
   - **First blocked step:** S0's constitutional-ADR step (≈ weeks 2–3 [inference]), if the
     port-base tag must follow the ADR-0001 supersession. 07 §4 puts "Constitutional ADRs (§9)" at
     S0 step 2, before ADR-0010 and the tag, and ARCHITECTURE §13.1 item 2 asks for D0-1 early
     "because S0 and the M0 verdict depend on" it. 07 §9.1's heading says "before S1 merges". The
     sources disagree (Q12).
   - *Declined:* STOP-L. Mithril is re-scoped to tools over C, with a tombstone triggered by
     "owner ADR changes".
   - *Delayed:* possibly the S0 tag (Q12); in any case the M0 verdict cannot pick a row that
     continues the language.
5. **Dependencies.** D0-5c (land separately); D0-11c; D0-4.
6. **Cost.** 1–2 h to decide and 0.5–1 h to merge the ADR [inference]. Negligible API.
7. **Provisional, pending D0-1.** Draft the superseding ADR in Mithril's `experiments/`. Nothing
   touches Hearth.

```text
D0-1  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
```

### 4.8 D0-11 Spec authority

ROADMAP §11 gives one row: needed by M1, recommendation "Yes to all three". If declined, maintainers
write all specs.

1. **Decisions.**
   - **(a)** Who may seal specs?
   - **(b)** Must the Author and Builder of a sealed artifact come from different model families?
   - **(c)** Does Hearth admit `validated` evidence as an INV-VERIFY evidence class?
2. **Recommendation.**
   - **(a)** Sealing (admission, hash-locking) is an AUTHORITY act that you sign. Agents prepare,
     you seal (03 §4.4, §8.3). X1's suite hash is frozen inside X1's record (D0-12).
   - **(b)** Yes, from M1.
   - **(c)** Yes, by a Hearth ADR. Per 07 §9.3 item 7 it also:
     - admits spec roles;
     - says who may seal;
     - makes handover `kind` mandatory;
     - makes toolchain-generated manifests canonical.
3. **Evidence.**
   - INV-VERIFY: "Golden tests (`tests/golden/`) are authored by maintainers only ... New behaviour
     is covered by contributor tests, which must pass mutation testing" (`INVARIANTS.md:21`
     [M·d0]).
   - Changing that text without an ADR that cites the invariant trips Hearth's breaker [M·d0,
     Appendix A, case E]; with such an ADR it passes (case F). Invariant edits also need a golden
     update and the `golden-reviewed` label (`governance/README.md:292` [M·d0]).
   - A same-family contract record caps spec strength at `tested` (03 §8.4).
   - LLM-written specs are sound and complete only about half the time [R03 (medium-high), citing
     Verina; via 03 §8.4].
   - **X1 does not wait on (b)** [inference]: ROADMAP §3.2 already requires the planted corpus from a
     family other than `mithi`'s author, 05 §13 requires task authors from a different family than
     the card editors, and D0-10c's role assignment carries both out (Q1).
4. **Needed by.**
   - (a) M1.
   - (b) M1 (ROADMAP §11).
   - (c) S1 (07 §9.3).
   - *Declined:* maintainers, which here means you, write all specs (ROADMAP §11).
5. **Dependencies.** D0-10c (b); D0-9 (a); D0-1 and D0-3 (c).
6. **Cost.** 0.5 h now; 1–2 h for the Hearth ADR at S1 [inference].
7. **Provisional.** None needed before M1. X1's role split is D0-10c's.

D0-11b YES assumes Q1 = CONFIRM.

```text
D0-11a  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
D0-11b  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
D0-11c  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
```

### 4.9 D0-3 S0 freeze, `hearth-c-ref` and the hash corpus

1. **Decision.** Will Hearth:
   - freeze a port base (R3 committed, ADR-0010 landed);
   - keep `hearth-c-ref@port-base-1`, built with the release flags, as the permanent differential
     oracle;
   - adopt a cross-binary SHA-256 hash corpus as a maintainer-owned golden tier, extending
     INV-VERIFY?
2. **Recommendation.** Yes, with the corpus reproduced twice on the 9950X (ROADMAP §11). The
   layout follows 07 §2.3:
   - Synthetic, kernel and quantiser hash lists live under `tests/golden/corpus/`, locked by
     `MANIFEST.sha256`.
   - The real-model list is checked by a script you run, because INV-DATA keeps models out of CI.
   - Each entry records the commit, compiler, flags, CRT/libm identity, `_get_FMA3_enable()` state,
     CPU flags and canon version.
   - A re-baseline happens only by ADR, signed by you.
   - `hearth-c-ref` is a lineage of tags (07 §6).
3. **Evidence.**
   - The golden suite checks relational equalities and tolerance against numpy, over 5
     architectures × {F32, Q4} plus `big_q4` (`test_golden_invariants.py:22-42` [M·d0]). It pins no
     absolute logits, so a port with a different but self-consistent float order would pass it
     [R11; 07 §2.2].
   - Oracle hole: `hearth.quant` calls the engine's own quantiser (`governance/README.md:131,
     440-443` [M·d0]).
   - Golden tests are maintainer-authored (`INVARIANTS.md:21`). `tests/golden/` is code-owned by
     @pierce-lonergan (`.github/CODEOWNERS` [M·d0]).
   - Hearth has used logit hashing once: SHA-1 over 512 real-weight steps (measured;
     `policy-default.md`, not verifiable at b5d3f14).
   - Run time: one 512-step decode at 2 GiB takes ≈ 39 s [D: 512 ÷ 13.02 tok/s (measured)
     [R11]], and a 2,048-token prefill ≈ 9 s [D: 2,048 ÷ 226 tok/s (measured) [R11]]. Load time is
     not measured.
   - Hashes need determinism, not a quiet machine [inference], so corpus runs are daytime work.
4. **Needed by.** M1's S1 (ROADMAP §11). S0's own gate is in M0: the corpus reproduces twice,
   ADR-0010 is decided before the lock, and you sign it (07 §4).
   - *Declined:* there is no bit-exact oracle, so there is no port.
   - *Delayed:* S1 and M1's scalar port slip.
5. **Dependencies.** D0-2; D0-5a; HM-5a; D0-9a (signing before M3) and D0-9b (re-baselines on the
   ledger); HM-7 (optional).
6. **Cost.** 0.5 h to decide; 2–4 h to review the corpus specification and sign both runs
   [inference]. API ≈ $0.5–2k for tooling [inference], not costed in ROADMAP. A few daytime
   machine hours [inference].
7. **Provisional, pending D0-3.**
   - The generator and manifest schema are written in Mithril's `experiments/`.
   - They are dry-run on b5d3f14 synthetic containers, and every output is labelled "unlocked,
     provisional".
   - Nothing is written into Hearth's `tests/golden/`, because only maintainers may (INV-VERIFY).

```text
D0-3  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
```

### 4.10 D0-8 Measurement host

1. **Decision.** Is the 9950X desktop the measurement host, with a second box only when D-22
   fires?
2. **Recommendation.** Yes. Also record GEMS and the other co-tenant jobs as facts about "the
   Owner's own use", so that D-22's clause on quiet windows can be evaluated. Choose a box and its
   cost only when D-22 fires.
3. **Evidence.**
   - D-22 has six clauses, including a failed A/A or planted-regression calibration, and quiet
     windows that conflict with the Owner's use (ROADMAP §9; 06 §6.9).
   - A Zen 5 twin doubles throughput for existing niches. A different microarchitecture serves F2
     but cannot confirm Zen 5 niches (06 §6.9).
   - DR-018 reopens when `hw.measurement_hosts >= 2`.
   - Hearth already measures on a shared machine (load 10–86%, measured; H03-forward-gen-001
     [M·d0 read]). GEMS plans night GPU and CPU work on the desktop (§4.2, D0-10d, evidence
     [M·d0 read]).
   - ROADMAP §10 does not cost hardware.
4. **Needed by.** M4 (ROADMAP §11). A failed X4 calibration fires D-22 already in M0.
   - *Declined:* campaigns are bounded by measured throughput.
5. **Dependencies.** D0-10d; D0-7a.
6. **Cost.** 0.25 h now [inference]. A second box is uncosted hardware.
7. **Provisional, pending D0-8.** The desktop serves as the M0 host under D0-10d.

This YES assumes Q7 = YES (GEMS counts as the Owner's own use); if you answer Q7 otherwise, tick
AMEND.

```text
D0-8  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
```

### 4.11 D0-6 GPU scope

1. **Decision.** Three questions, each on its own line:
   - **D0-6a.** Is the RTX 5070 in scope for Hearth and Mithril compute?
   - **D0-6b.** Does `nvcuda.dll` count as an "OS API" under INV-DEP?
   - **D0-6c.** Should the display move to the iGPU?
2. **Recommendation.** DEFER all three to M5, as ROADMAP §11 says. The VRAM tier stays reserved in
   the types either way, and INV-DET-1 gains a device axis only once a GPU tier exists.
   - When you decide, weigh that GEMS is reported to use a GPU queue on this card [M·d0 read of
     GEMS's own files and PLAN §2; see D0-10d's evidence].
   - Also consider tightening task R01's acceptance to "bit-identical for any dynamically placed
     op" (07 §9.2 item 4).
3. **Evidence.**
   - The card, queried 2026-10-11 [G03 F1]: RTX 5070 with 12,227 MiB, compute capability 12.0,
     WDDM. The display uses 1,503 MiB at idle. `nvcuda.dll` and `vulkan-1.dll` are present, and
     there is no CUDA toolkit.
   - The GPU tier gives 3.6–4.8x for in-RAM MoE (simulated) [G03].
   - Canonical GEMV against llama.cpp's MMVQ is unmeasured [G03, open question 2].
   - DR-022 is the gate.
   - R01-cuda accepts "bit-identical to CPU kernels or documented tolerance"
     (`governance/tasks.json:190-201` [M·d0]).
   - ADR-0003: "A GPU backend must reproduce these semantics or document its tolerance"
     (`ADR-0003-canonical-numerics.md:44-45` [M·d0]).
4. **Needed by.** M5. *OUT on D0-6a, or no choice by M5:* CPU-only, and the GPU becomes a tombstone
   (ROADMAP §11).
5. **Dependencies.** D0-1 (the INV-DEP reading); D0-2; D0-8.
6. **Cost.** 0.25 h now [inference].
7. **Provisional.** Nothing runs on the GPU. The tier exists in the types only.

```text
D0-6a  RTX 5070 in scope: [ ] DEFER (recommended)   [ ] IN   [ ] OUT   [ ] AMEND: ________   Tag: d0-sign-__
D0-6b  nvcuda.dll an OS API: [ ] DEFER (recommended)   [ ] OSAPI   [ ] NOTOSAPI   [ ] AMEND: ________   Tag: d0-sign-__
D0-6c  display on the iGPU: [ ] DEFER (recommended)   [ ] IGPU   [ ] KEEP   [ ] AMEND: ________   Tag: d0-sign-__
```

### 4.12 D0-4 Normativity

1. **Decision.** Do NUMERICS.md and the scalar C stay normative through S6, with Mithril meanings
   becoming normative only after S6 (NUMERICS.md then generated and checked)?
2. **Recommendation.** STATUSQUO. The flip is a separate Hearth ADR at S6 (07 §9.3 item 10).
3. **Evidence.**
   - NUMERICS.md is titled "(normative)" (`docs/NUMERICS.md:1`). ADR-0003 says "docs/NUMERICS.md is
     normative" (`ADR-0003-canonical-numerics.md:20` [M·d0]).
   - DR-026 keeps NUMERICS.md and the scalar C normative until S6.
   - Meanings take over "is this the canonical order?", never "is this the model?". They are never
     derived from `reference.py` (07 §8).
4. **Needed by.** S6 (M5). *AMEND (a different rule) or no decision by S6:* dual normativity with a
   drift check (ROADMAP §11).
5. **Dependencies.** D0-1; D0-2 (ADR-0010 edits NUMERICS §4 first); D0-3.
6. **Cost.** 0.25 h now; about 2 h for the flip ADR at S6 [inference].
7. **Provisional.** Nothing. The status quo is the recommendation.

```text
D0-4  [ ] STATUSQUO (recommended)   [ ] AMEND: ________   Tag: d0-sign-__
```

### 4.13 Total owner ask

ROADMAP prices M0 at ~195 owner h, of which D0 is ~10 h [inference, §3.7, §10]. This table counts
everything this brief asks of you, including what lies outside those lines. Inputs are the item-6
figures above and §5's HM column; sums by `hours.py` in this track's scratch directory [D].

| Part | Hours | Formula | Inside ROADMAP's ~195 h? |
|---|---|---|---|
| Decide the D0 lines | 8.25–9.25 | Sum of item 6 "to decide" [D] | D0's ~10 h |
| Decide the HM lines | 1.2–3.0 | 12 lines × 0.1–0.25 h to read and decide [D, inputs G]; the work hours in §5's column are counted in the rows below | D0's ~10 h [inference] |
| Answer §7's questions | 0.75–2.25 | 15 × 0.05–0.15 h [D, inputs G] | D0's ~10 h [inference] |
| Read this brief | 2–3 | [G]; partly overlaps the lines above | D0's ~10 h [inference] |
| **Subtotal: decide** | **12.2–17.5** [D] | | Exceeds D0's ~10 h by 2.2–7.5 h [D] |
| Review and sign pre-registration records | 17–34 | 17 records × 1–2 h [D] | Yes, inside the X lines (PLAN §7.1) [inference] |
| Read COST.md weekly | 1.75–3.25 | 0.25 h × 7–13 weeks [D] | Yes [inference] |
| S0 and Hearth-maintainer review | 11–22 | D0-5 3–6 + D0-2 3–6 + D0-3 2–4 + D0-1 merge 0.5–1 + HM-5a 2–4 + HM-5b 0.25–0.5 + HM-7 0.25–0.5 [D] | No: S0 has no ROADMAP line (Q3) |
| One-off setup | 5.25–13 | D0-9a key 0.25–1 + D0-9b tokens and recovery 2–4 + gate account 1–3 + D0-10c keys 1–3 + D0-10d settings 1–2 [D] | No ROADMAP line [inference] |
| **Total in the M0 period** | **47.2–89.75** [D] | Sum of the four groups | |
| **Beyond ROADMAP's ~195 h** | **18.45–42.5** [D] | (decide − 10) + S0 review + setup | |

**Not owner hours, but yours:** the desktop is unavailable to you during quiet windows, 8 h ×
nights a week: 32 h in the pilot week, then 16–56 h a week at 2–7 nights [D: nights × 8 h].

**Later milestones:** D0-11c's Hearth ADR at S1 (1–2 h), D0-4's flip ADR at S6 (about 2 h), and from
M3 a second-device approval for each high-impact AUTHORITY act (D0-9b, about 0.1–0.25 h per act
[G]; the number of acts is not estimated). HM-9a filing costs about 0.25–0.5 h per issue [G].

---

## 5. Hearth-maintainer decisions without a D0 number

You are also Hearth's maintainer. `.github/CODEOWNERS` gives `governance/decisions/`,
`governance/INVARIANTS.md` and `tests/golden/` to @pierce-lonergan [M·d0]. Hearth's origin is
`https://github.com/pierce-lonergan/hearth.git` [M·d0, `git remote -v`]; its visibility was not
checked. These are Hearth decisions, recorded as Hearth ADRs or commits. HM-1 to HM-4 are
ARCHITECTURE §17's unnumbered rows. HM-5 to HM-9 surfaced in this read.

| ID | Decision | Recommendation | If NO | Needed by | Owner h [G] | Source |
|---|---|---|---|---|---|---|
| HM-1 | Task-DAG ownership by definition path once `.mith` is the source | Adopt for ported modules. Give the generated directory no human owner in `tasks.json` | Ownership stays per file, so generated C keeps human owners [inference, 07 §7] | S1 | 0.25 now; 0.5–1 at S1 | ARCHITECTURE §17; 07 §7, §9.3 item 9 |
| HM-2 | `canon.v1.1` MXFP4 block order (additive; no golden reset) | DEFER. Decide before the first MXFP4 golden (07 §11 item 3 sketches two sub-block terms added in order) | — (AMEND to decide now) | Later | 0 now | ARCHITECTURE §17; 07 §11 |
| HM-3 | `canon.v2` fixed-chunk attention order (major version, the first use of the migration protocol) | DEFER. Decide before any GPU attention, with an Owner ADR and a Hearth ADR recording the golden reset | — (if declined at that point, attention stays on the CPU) | By trigger | 0 now | ARCHITECTURE §17; 03 §12; DR-022 |
| HM-4 | Self-hosting | DEFER until after M7 | — (AMEND to decide now) | After M7 | 0 now | DR-026 |
| HM-5a | Commit R3 and repair the task DAG, adding the R3 tasks to `tasks.json` | Commit R3 with `struct_size` per D0-5a's outcome and the heat-decay default per D0-5c's outcome: 0.9 only if DECAY_09 is signed by then, otherwise 0.995 restored | S0 cannot start: R3 stays uncommitted and strict DAG validation fails [R11] | S0 step 1, before the tag | 2–4 (17 files, 3 handovers) | 07 §4 S0; R11. The R3 tree is not in the clone |
| HM-5b | Commit `docs/results/policy-default.md` | Yes, so the decay evidence is in history before D0-5c is decided | DECAY_09 cannot be signed under this brief's condition; DEFER or DECAY_0995 remain | Before D0-5c = DECAY_09 | 0.25–0.5 | R02 §10; D0-5c |
| HM-6 | Does vendored MIT source (CORE-MATH) satisfy INV-DEP's "no third-party libraries"? | DEFER: rule only if D0-2b's `cr` sinf/cosf would vendor it; a Hearth-authored implementation avoids the question | — | With D0-2 (≈ week 3) | 0 now; 0.5–1 if needed | G04, open question 2 |
| HM-7 | ADR-0009 (golden gate against the base revision) is **Proposed** at b5d3f14, yet its tooling already gates golden changes [M·d0] | Accept it before the corpus relies on it [inference]. Accepting it does not trip the breaker, and ADR-0001's retirement then counts 1 of 9 (11.1%) [M·d0, Appendix A, cases G, H] | The corpus relies on a Proposed ADR's tooling | Before the S0 corpus | 0.25–0.5 | 07 §2.2 |
| HM-8a | Kimi-K3 sequencing: K3 formats in Mithril after S2, kernels after S1 | Adopt | K3 work may land in C during the port and arrive through rebase windows (07 §11 item 6) | Before K3 work lands in C | 0.25 | 07 §11 item 6 |
| HM-8b | Treat reuse of kimi-k3-in-c kernels as a canon decision (task R07-landscape) | Adopt | Reused kernels could import that engine's double-precision, 4-way canon without a canon decision (07 §11 item 7) | Before K3 work lands in C | 0.25 | 07 §11 item 7; `governance/tasks.json:353` [M·d0] |
| HM-9a | Whether and when to file the research's Hearth defect reports, and any X0 flag-defect draft | Yes. Agents draft the issue text in Mithril's `experiments/`; **only you file it**, labelled "from Mithril research". Each fix still goes through Hearth's normal rules | The reports stay in Mithril's documents (07 §10) | Any time; X0 drafts after its verdict | 0.25–0.5 per issue | 07 §10; X0 record §8, amber (b) |
| HM-9b | Channel for memory-safety items (for example the 8-byte write past the Python buffer) | PRIVATE advisory [G] | — | With HM-9a | 0.1 | 07 §10 |

```text
HM-1   [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
HM-2   [ ] DEFER (recommended)   [ ] AMEND: ________   Tag: d0-sign-__
HM-3   [ ] DEFER (recommended)   [ ] AMEND: ________   Tag: d0-sign-__
HM-4   [ ] DEFER (recommended)   [ ] AMEND: ________   Tag: d0-sign-__
HM-5a  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
HM-5b  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
HM-6   [ ] DEFER (recommended)   [ ] VENDOR_OK   [ ] VENDOR_NO   [ ] AMEND: ________   Tag: d0-sign-__
HM-7   [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
HM-8a  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
HM-8b  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
HM-9a  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
HM-9b  [ ] PRIVATE (recommended)   [ ] PUBLIC   [ ] AMEND: ________   Tag: d0-sign-__
```

---

## 6. Tombstones this brief proposes

These are the options this brief recommends against. They use the format of
[DECISIONS §4](DECISIONS.md), and their triggers use the grammar of
[06 §7.2](architecture/06-forge.md). Each is **provisional, pending the D0 item named**: it becomes
a tombstone only if you sign that recommendation. Admitting it to the ledger is itself an
AUTHORITY act (DECISIONS §1). Proposed for DECISIONS.md; not added there by this track. Options
that a DR already rejected are not repeated here (DECISIONS §1); the `cr` expf option for ADR-0010
reopens only through DR-014's own trigger.

```text
tombstone mithc_build_dependency {                  // D0-1, option B; pending D0-1
    verdict: costlier                               // Hearth would need mithc to build; ADR-0001 wants "nothing but a C compiler"
    scope:   { project: hearth, period: port_s0_to_s6b, option: d0_1_b }
    class:   F                                      // under INV-DEP as worded at b5d3f14
    revisit_when: hearth.invariant_hash("INV-DEP") != at_burial.hearth.invariant_hash("INV-DEP")
               || port.stage(S6b).verdict == pass
    evidence: [07 §9.1] [R11] hearth:governance/INVARIANTS.md:18, ADR-0001:10-17
    // survivor: option A, checked-in C11 regenerated byte for byte (DR-026)
}

tombstone textual_owner_signature {                 // pending D0-9a
    verdict: gameable                               // any session that can write the repository can type a name
    scope:   { artifact: owner_authority, phase: m0, repo_writers: owner_and_agents }
    class:   F                                      // under A10: authority is a signature, never a sentence (03 §1)
    revisit_when: owner.decision(a10) == amended
    evidence: [03 §1 A10] [03 §11.3] [ROADMAP §1 rules 1, 3]
    // survivor: a signed d0-sign-<n> tag made with a key agents cannot use (D0-9a = HW or PASS; Appendix B), then mithc ledger sign --authority (M3)
}

tombstone software_key_on_agent_account {           // pending D0-9a (HW or PASS)
    verdict: gameable                               // a key usable from the account agents run under signs for any process in it (inference)
    scope:   { artifact: owner_signing_key, phase: m0, key_store: agent_os_account }
    class:   F                                      // under: agent sessions run in the OS account that holds the key
    revisit_when: owner.decision(agent_os_account) == separate
    evidence: [03 §11.3] [03 §1 A10]
    // survivor: a hardware key that needs a touch, or a passphrase key held outside the agents' account (D0-9a)
}

tombstone sampled_collection_before_signature {     // pending D0-12
    verdict: gameable                               // data seen before signing can shape the record that is then signed
    scope:   { records: m0_prereg, designs: {sampled, sequential}, examples: {x1, x2_fuzz, x3_ab, x4_calibration} }
    class:   F                                      // under: a record can still be amended between collection and signature
    revisit_when: has(rule: gatekeeper_judges_frozen_text_only)
    evidence: [ROADMAP §1 rule 1] [ROADMAP §11 D0-12] [docs/m0/README.md, collection rule]
    // survivor: none under D0-12x = ROADMAP; under D0-12x = X0, the exception for deterministic, exhaustive measurements (X0)
}

tombstone quiet_window_cotenancy {                  // pending D0-10d
    verdict: unpredictable                          // co-tenant GPU and CPU jobs can perturb DRAM-bound timing past a CPU-load gate (inference)
    scope:   { host: mp_9950x, window: quiet, cotenants: {gems_gpu_queue, other_cpu_jobs} }
    class:   H                                      // one shared desktop
    revisit_when: meas.aa_reject_rate(hearth_c_ref, hearth_c_ref, cotenant: gems) <= prereg(forge.aa_alpha)
               || hw.measurement_hosts >= 2
    evidence: [06 §6.7, §6.8] [DR-023] hearth:governance/handovers/H03-forward-gen-001.json:124; GEMS_Challenge:ops/gpu_calendar.md (2752b35)
    // survivor: co-tenants run outside quiet windows; a second box by D-22 (D0-8)
}
```

The triggers use only `!=`, `==`, `<=`, `>=`, `||`, `has(...)`, `at_burial.`, `prereg(...)` and
parameterised facts. A fact nobody yet measures (`meas.aa_reject_rate(..., cotenant: gems)`)
evaluates to `unknown`, which never fires but is reported (06 §7.2). This brief did not run
`mithc revisit --design --check`, which does not exist yet.

---

## 7. Owner questions

Each is a place where this brief thinks ROADMAP is wrong, unclear or incomplete, or where a
recommendation rests on a reading only you can confirm. ROADMAP has not been changed. Every question
has its own answer line, signed by tag like any D0 line.

1. **D0-11b and X1.** This brief reads X1's family split as already required by ROADMAP §3.2
   (planted corpus) and 05 §13 (task authors), and carried out by D0-10c, so D0-11b stays at M1.
   Confirm?
2. **D0-9 is needed before X4.** ROADMAP §1 rules 1 and 3 put the Owner key into every gate
   evaluation, starting with X0. Should ROADMAP add an interim M0 signing method (D0-9a)?
3. **S0 has no slot and no budget.** 07 §4 and ARCHITECTURE §13 put S0 in M0, and D0-3 needs it
   before S1. S0 means the R3 commit, the constitutional ADRs, the `struct_size` change, ADR-0010 in
   C and the corpus run twice (07 §4 steps 1–5). Yet it has no row in ROADMAP §2, §3 or §10. Who
   does S0, when, and from which budget line?
4. **Collection before signature.** [m0/README.md](m0/README.md)'s collection rule allows collection
   under a FROZEN record with your instruction, before you sign. ROADMAP §11's D0-12 says "signs each
   record before collection". Which should change: m0/README (to match ROADMAP) or ROADMAP (to adopt
   the exception)?
5. **"A one-family pilot at X1".** D0-10's wording can be misread as "X1 may run with one frontier
   family". This brief reads it as the *local* model running as a pilot, while X1's kill still
   needs ≥ 2 frontier families (§1 rule 5, §3.2). Confirm?
6. **Unattended runs.** D0-7 says "unattended only inside quiet windows", and 06 §6.8 bars agent
   sessions inside windows. Read literally together, Forge work with LLM proposers can never run
   unattended. LITERAL keeps that reading (F1-sim attended). MEASUREMENT reads "unattended" as
   applying to measurement only, with daytime F1-sim allowed under the normal agent rules (D0-7x =
   DAYSIM).
7. **GEMS.** Does GEMS count as "the Owner's own use" for D-22? If GEMS cannot pause inside quiet
   windows, D-22 fires at once.
8. **Hardware.** The two key tokens (D0-9b) and any second box (D0-8) are not costed in ROADMAP
   §10. Should they be?
9. **B1 has no slack.** ROADMAP §7 names exactly five defects, four of which depend on D0-5. If any
   part of D0-5 is declined, may a substitute live defect (07 §10: the `n_io = 1` prefetch clamp)
   count toward B1? That would be a ROADMAP change.
10. **D0-5 deadlines.** 07 §9.3 puts `struct_size` at S0 (item 3) and MXCSR at S1 (item 5);
    ARCHITECTURE §17 puts `struct_size` with the R3 commit and gives no stage for MXCSR. Both are
    earlier than ROADMAP §11's "S4 / S6a". Should ROADMAP §11 say so?
11. **D0-7's deadline.** ROADMAP §11 sets X4 for all of D0-7. 07 §9.3 item 8 gives the Forge-authority
    decision "first live-engine Forge run (after S4)", and grants first become live at M6 (03 §4.4).
    Should ROADMAP §11 split D0-7's deadline (SPLIT), or keep X4 for every part (KEEP)?
12. **S0's step 2.** 07 §4 puts "Constitutional ADRs (§9)" before ADR-0010 and the port-base tag;
    07 §9.1's heading says "before S1 merges"; ARCHITECTURE §13.1 item 2 says S0 depends on D0-1.
    Does S0's step 2 include the ADR-0001 supersession (INCLUDES_9_1), or only 07 §9.3 items 3–4
    (ONLY_9_3)?
13. **Review queue order.** ARCHITECTURE §16 risk 6 orders the review queue "by evidence grade";
    PLAN §7.2's ordering rule puts signatures and freeze commits that unblock machine time or a second
    family first [G]. Which governs M0?
14. **X1 measurement.** Is X1's agent measurement ($2.0–8.2k [D]) inside X1's $7–15k (INSIDE), or a
    separate part of M0's $16–36k (SEPARATE)? Under SEPARATE the per-experiment ceilings would sum to
    $43.7k [D], above ROADMAP's $36k.
15. **Self-authoring.** Under D0-10c, Family B writes X1's sealed tasks and reference solutions and
    is also an X1 participant. May the family that wrote the sealed tasks also attempt them? If not,
    a third family or a split of authorship is needed.

```text
Q1   [ ] CONFIRM   [ ] OTHER: ________   Tag: d0-sign-__
Q2   [ ] YES   [ ] NO   [ ] OTHER: ________   Tag: d0-sign-__
Q3   [ ] ANSWER: ________   Tag: d0-sign-__
Q4   [ ] ROADMAP   [ ] README   [ ] OTHER: ________   Tag: d0-sign-__
Q5   [ ] CONFIRM   [ ] OTHER: ________   Tag: d0-sign-__
Q6   [ ] LITERAL   [ ] MEASUREMENT   [ ] OTHER: ________   Tag: d0-sign-__
Q7   [ ] YES   [ ] NO   [ ] OTHER: ________   Tag: d0-sign-__
Q8   [ ] YES   [ ] NO   [ ] OTHER: ________   Tag: d0-sign-__
Q9   [ ] YES   [ ] NO   [ ] OTHER: ________   Tag: d0-sign-__
Q10  [ ] YES   [ ] NO   [ ] OTHER: ________   Tag: d0-sign-__
Q11  [ ] SPLIT   [ ] KEEP   [ ] OTHER: ________   Tag: d0-sign-__
Q12  [ ] INCLUDES_9_1   [ ] ONLY_9_3   [ ] OTHER: ________   Tag: d0-sign-__
Q13  [ ] EVIDENCE_GRADE   [ ] UNBLOCK_FIRST   [ ] OTHER: ________   Tag: d0-sign-__
Q14  [ ] INSIDE   [ ] SEPARATE   [ ] OTHER: ________   Tag: d0-sign-__
Q15  [ ] YES   [ ] NO   [ ] OTHER: ________   Tag: d0-sign-__
```

---

## 8. What this brief could not verify

- **The R3 working tree.** It is on the desktop and not in the clone. Every R3 fact is from the
  dossiers: the 0.9 default, the grown structs, `policy-default.md`, and R11's working-tree line
  numbers. For example, `hearth.h` is 164 lines at b5d3f14 [M·d0], against 176 in R11, and
  `read_errors` is at line 115, against R11's 121. Whether anything in R3 besides the default relies
  on 0.9 (D0-5c DEFER) is unknown.
- **Per-decision costs.** The owner hours and dollars for single decisions are this track's
  inference or judgment, including T1's $3k. Only the ROADMAP figures they are checked against
  carry ROADMAP's own labels.
- **Providers and tools.** Not verified: provider spend limits, provider data-use terms, which
  current models each provider offers, git OpenPGP/SSH tag signing and `git verify-tag` on the
  laptop, signing-agent caching behaviour, and whether CORE-MATH builds under MSVC. Appendix B's
  git layer was not run against a signed tag.
- **GEMS.** Read from its own files only (§4.2): its calendar plans night GPU and CPU work. Its CPU
  and memory load, whether it can pause, and the cost of pausing it are unknown. That its GPU is the
  desktop's card is [inference].
- **Hearth's visibility** on GitHub (public or private), which matters for HM-9b.
- **X0 collection so far.** The repository holds X0's flags and scripts but no results [M·d0:
  `ls experiments/x0-census`]. Whether X0 objects were already compiled on the desktop under the
  instruction was not checked; this track did not use the remote desktop. If any were, then under
  D0-12x = ROADMAP they were collected before signature, and the X0 record should say so.
- **Unmeasured costs.** The MXCSR save and restore per entry, and real corpus load times.
- **No independent review.** Both reviews of this brief were same-family (§9). No different-family
  or Owner review has been run.

---

## 9. Review log

| Date | Reviewer | Lens | Family | Findings | Accepted | Rejected |
|---|---|---|---|---|---|---|
| 2026-10-16 | Reviewer 1 | Source fidelity: deadlines, wording and consequences against ROADMAP and the cited sources; evidence tags; tombstone format | Claude (same family as author; independent context) | 18: 5 major, 13 minor | 18 | 0 |
| 2026-10-16 | Reviewer 2 | The Owner's position: whether each line can be signed safely and on its own, whether every option and cost is shown, framing | Claude (same family as author; independent context) | 18: 9 major, 9 minor | 18 | 0 |

The reviser (the d0 track, same family) checked every finding against the sources before acting on
it, and re-ran Appendix A (cases A–H unchanged [M·d0, 2026-10-16, CPython 3.12.10]).

**Rejected findings:** none.

**Accepted with a change to the proposed fix** (one line each):
- R1 #2 and R2 #1 (X0 collection before signature) were merged into D0-12, D0-12x and D0-12i, with
  ROADMAP as the recommended option and both loosenings labelled as such.
- R1 #11 (GEMS uncited): cited GEMS's own files and PLAN §2 instead of the sprint brief, which this
  reviser could not read.
- R1 #12 (tombstones): `cr_expf_in_adr_0010` dropped; `textual_owner_signature` re-anchored on A10;
  `software_key_on_agent_account` added for R2 #3.
- R2 #2 (signing protocol): implemented as "How to sign" plus Appendix B's verifier, tested on 13
  synthetic cases [M·d0, `python -I`, 2026-10-16]; its git layer is untested.
- R2 #4 (tranches): T2 split into card iteration (T2a) and held-out (T2b), because card iteration
  runs before the held-out record is signed; T1's $3k is this track's [G].
- R2 #7 (staged window): Stage 1 is the pilot week only (4 nights, PLAN §6.3 [G]); after it, PLAN
  §6.3's σ_d-based rule sets the rate, up to 7, because a fixed 4 nights would let X3 slip to W7 at
  σ_d = 4% [D, PLAN §6.3]. PLAN §6.3 and PLAN Q1, revised the same day, still follow the earlier
  7-night draft; aligning them is the plan track's call.
- R2 #14 (week-0 list): D0-11b returned to M1; Q1 kept, with an answer line.
- R2 #17 (INV-DET-1 "now"): kept ROADMAP's "decide now", moved the landing to "by S4".

---

## Appendix A: reproducing the breaker checks

The script below loads Hearth's own `governance/tools/adr.py`. It calls `breaker()` on the ADR
records and `INVARIANTS.md` read from git `HEAD` (b5d3f14), then on copies edited in memory. Nothing
in the clone is changed. It was run by the d0 track on 2026-10-16 with `python -I` (CPython
3.12.10), and re-run by the reviser the same day with the same results.

```python
import importlib.util, sys, re
root = sys.argv[1]                                   # path to a Hearth clone at b5d3f14
spec = importlib.util.spec_from_file_location("adr", root + "/governance/tools/adr.py")
adr = importlib.util.module_from_spec(spec); sys.modules["adr"] = adr; spec.loader.exec_module(adr)
base, base_inv = adr.read_rev(root, "HEAD")
def retire(f, name, by):
    t = re.sub(r"^- Status: Accepted$", "- Status: Superseded", f[name], flags=re.M)
    f[name] = re.sub(r"^- Superseded-by: none$", f"- Superseded-by: {by}", t, flags=re.M)
def new(f, num, slug, sup, extra=""):
    f[f"ADR-{num}-{slug}.md"] = (f"# ADR-{num}: {slug}\n\n- Status: Accepted\n- Date: 2026-10-20\n"
        f"- Supersedes: {sup}\n- Superseded-by: none\n\n## Context\n\nx {extra}\n\n## Decision\n\nx\n\n## Consequences\n\nx\n")
def run(label, cur, cur_inv=base_inv, b=base):
    r = adr.breaker(b, cur, base_inv, cur_inv, 0.15)
    print(label, f"{len(r['deprecated'])}/{len(r['active_at_base'])}", bool(r["tripped"]))
n1, n4, n9 = (next(k for k in base if k.startswith(p)) for p in ("ADR-0001", "ADR-0004", "ADR-0009"))
c = dict(base); new(c, "0010", "specified-transcendentals", "none"); run("A", c)
c = dict(base); retire(c, n1, "ADR-0011"); new(c, "0011", "mithril-sourced-core", "ADR-0001"); run("B", c)
c2 = dict(c); retire(c2, n4, "ADR-0012"); new(c2, "0012", "lfu-decay-0-9", "ADR-0004"); run("C", c2)
run("D", c2, b=c)                                     # ADR-0004's supersession after B has merged
inv2 = base_inv.replace("mirrors, pinning", "mirrors (assuming byte-identical mirror files), pinning")
run("E", dict(base), cur_inv=inv2)
c = dict(base); new(c, "0013", "qualify-inv-det-1-mirrors", "none", "INV-DET-1"); run("F", c, cur_inv=inv2)
b9 = dict(base); b9[n9] = re.sub(r"^- Status: Proposed$", "- Status: Accepted", b9[n9], flags=re.M); run("G", b9)
c = dict(b9); retire(c, n1, "ADR-0011"); new(c, "0011", "mithril-sourced-core", "ADR-0001"); run("H", c, b=b9)
```

| Case | Change | Retired / Accepted at base | Tripped [M·d0] |
|---|---|---|---|
| A | ADR-0010 added; retires nothing | 0/8 | no |
| B | ADR-0001 superseded alone | 1/8 = 12.5% | no |
| C | ADR-0001 and ADR-0004 superseded in one change | 2/8 = 25% | **yes** (limit 15%; clears with your `decisions-reviewed` label) |
| D | ADR-0004 superseded after B has merged | 1/8 = 12.5% | no |
| E | INV-DET-1 reworded, no ADR | 0/8 | **yes** (invariant changed without an ADR) |
| F | INV-DET-1 reworded, with an ADR citing INV-DET-1 | 0/8 | no |
| G | ADR-0009 moved from Proposed to Accepted | 0/8 | no |
| H | ADR-0001 superseded with ADR-0009 already Accepted | 1/9 = 11.1% | no |

In case D, the script reuses `base_inv` for the base. That is correct, because B does not touch
`INVARIANTS.md`.

`adr.py`'s working-tree mode refused to read this clone's `governance/decisions/` ("not a plain
file") [M·d0]. `--rev HEAD` mode reads it normally. The likely cause is file attributes in the temp
clone, which was not investigated. It does not affect the results above.

---

## Appendix B: the signing-tag verifier

**Tag message grammar.** The first line is `D0-SIGN 1`. An optional `file: docs/D0_BRIEF.md` line
follows. Then one line per decided item: `<ID>: <CHOICE>[; <field>=<value>]...`, where `<ID>` is a
line ID of this brief (`D0-12x`, `D0-10a`, `HM-5b`, `Q6`), `<CHOICE>` is the token after the ticked
box (`YES`, `NO`, `AMEND`, `ROADMAP`, `DECAY_09`, …), `text=` repeats the AMEND, OTHER or ANSWER
text, and the other fields repeat the Value line's fields by name. The signature block that git
appends ends the list. Example:

```text
D0-SIGN 1
file: docs/D0_BRIEF.md
D0-12: YES
D0-12x: ROADMAP
D0-12i: CONFIRMED
D0-9a: HW; key fingerprint=SHA256:...
D0-10b: YES; H=15 h/week; signing slots=Tue, Fri
```

**What the script checks.** For each `d0-sign-<n>` tag in order: `git verify-tag` succeeds; each named
item has exactly one ticked box with the same token at the tag's commit; AMEND/OTHER/ANSWER text and
Value fields match the message; a required Value is filled; a YES with a Value other than its
`(rec …)` is counted as AMEND. Then, at `HEAD`: a ticked line that no verified tag names is void,
and a line or Value field changed since the tag that decided it is void until re-tagged. It prints
each decided item and each problem, and exits 1 if there is any problem.

**Status.** Provisional, pending D0-9a. Its pure functions were tested by the reviser on 13
synthetic cases (clean YES, untagged tick, unverified tag, change after tag, blank required Value,
filled Value, YES with a non-recommended Value, Value mismatch, matching and mismatching OTHER
text, a later tag re-deciding, a bad header, a `Tag:` field naming another tag); all pass [M·d0,
`python -I`, CPython 3.12.10, 2026-10-16]. Run on this file, it finds every signature line and no
ticked box [M·d0]. Its git layer has not been run against a signed tag. It checks that a signature
verifies, not whose key made it: compare the printed signer with D0-9a's fingerprint.

```python
import re, subprocess, sys
ID = r"(?:D0-\d+[a-z]*|HM-\d+[a-z]*|Q\d+)"
SIG = re.compile(rf"^({ID})\s+(.*\[[ xX]\].*)$")
VAL = re.compile(rf"^({ID})\s+Value(\s*\(required\))?:\s*(.*)$")
BOX = re.compile(r"\[([ xX])\]\s+([A-Z][A-Z0-9_+]*)(:)?")
TAGF = re.compile(r"Tag:\s*(\S*)\s*$")
norm = lambda s: " ".join(s.split()).casefold()
blank = lambda v: "__" in v or not v

def parse_brief(text):
    """Return {id: (boxes, line)}, {id: (required, {field: (value, rec)}, line)} for signature and Value lines."""
    sig, val = {}, {}
    for ln in text.splitlines():
        m = VAL.match(ln)
        if m:
            f = {}
            for seg in m.group(3).split(";"):
                if "=" in seg:
                    k, v = seg.split("=", 1)
                    r = re.search(r"\(rec ([^)]*)\)\s*$", v)
                    f[norm(k)] = (norm(re.sub(r"\(rec [^)]*\)\s*$", "", v)), norm(r.group(1)) if r else None)
            val[m.group(1)] = (bool(m.group(2)), f, ln)
            continue
        m = SIG.match(ln)
        if m:
            boxes = []
            for b in BOX.finditer(ln):
                txt = norm(re.split(r"\s{3,}(?:\[|Tag:)", ln[b.end():])[0]) if b.group(3) else None
                boxes.append((b.group(1) != " ", b.group(2), txt))
            sig[m.group(1)] = (boxes, ln)
    return sig, val

def parse_tag(msg):
    """Tag message: 'D0-SIGN 1', optional 'file:' line, then '<ID>: <CHOICE>[; name=value]...' lines."""
    lines = [l.strip() for l in msg.splitlines()]
    if not lines or lines[0] != "D0-SIGN 1":
        raise ValueError("first line is not 'D0-SIGN 1'")
    items = {}
    for l in lines[1:]:
        if l.startswith("-----BEGIN"):
            break
        if not l or l.startswith("file:"):
            continue
        m = re.match(rf"^({ID}):\s*([A-Z][A-Z0-9_+]*)\s*(?:;(.*))?$", l)
        if not m:
            raise ValueError(f"unparsable line: {l}")
        f = {norm(k): norm(v) for k, v in (s.split("=", 1) for s in (m.group(3) or "").split(";") if "=" in s)}
        items[m.group(1)] = (m.group(2), f)
    return items

def check(tags, head):
    """tags: [(name, verified, message, brief_text_at_tag_commit)] in tag order; head: brief text at HEAD."""
    decided, out = {}, []
    for name, ok, msg, text in tags:
        if not ok:
            out.append(f"{name}: signature does not verify; tag ignored"); continue
        try:
            items = parse_tag(msg)
        except ValueError as e:
            out.append(f"{name}: {e}; tag ignored"); continue
        sig, val = parse_brief(text)
        for iid, (choice, f) in items.items():
            if iid not in sig:
                out.append(f"{name} {iid}: no such signature line"); continue
            boxes, line = sig[iid]
            ticked = [b for b in boxes if b[0]]
            if len(ticked) != 1 or ticked[0][1] != choice:
                out.append(f"{name} {iid}: tag says {choice}, file ticks {[b[1] for b in ticked]}"); continue
            t = TAGF.search(line)
            if t and not blank(t.group(1)) and t.group(1) != name:
                out.append(f"{name} {iid}: line names tag {t.group(1)}"); continue
            txt = ticked[0][2]
            if txt is not None and (blank(txt) or f.get("text") != txt):
                out.append(f"{name} {iid}: {choice} text blank or differs from the tag"); continue
            eff, vline = choice, None
            if iid in val:
                req, vf, vline = val[iid]
                empty = [k for k, (v, r) in vf.items() if blank(v)]
                if req and empty and choice != "NO":
                    out.append(f"{name} {iid}: required Value blank {empty}; not decided"); continue
                diff = [k for k, (v, r) in vf.items() if not blank(v) and f.get(k) != v]
                if diff:
                    out.append(f"{name} {iid}: Value differs between file and tag {diff}"); continue
                if choice == "YES" and any(r is not None and not blank(v) and v != r for v, r in vf.values()):
                    eff = "AMEND"; out.append(f"{name} {iid}: YES with a Value other than its (rec ...); counted as AMEND")
            decided[iid] = (eff, name, line, vline)
    sig, val = parse_brief(head)
    for iid, (boxes, line) in sig.items():
        if any(b[0] for b in boxes) and iid not in decided:
            out.append(f"HEAD {iid}: ticked, but no verified tag names it; void")
    for iid in list(decided):
        eff, name, line, vline = decided[iid]
        if iid not in sig or sig[iid][1] != line or (val[iid][2] if iid in val else None) != vline:
            out.append(f"HEAD {iid}: changed after {name}; void until re-tagged"); del decided[iid]
    return decided, out

def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, encoding="utf-8")

def main(repo, path="docs/D0_BRIEF.md"):
    names = git(repo, "tag", "-l", "d0-sign-*").stdout.split()
    names.sort(key=lambda s: int(s.rsplit("-", 1)[1]) if s.rsplit("-", 1)[1].isdigit() else 10**9)
    tags = []
    for t in names:
        v = git(repo, "verify-tag", t)
        print(f"{t}: verify-tag exit {v.returncode}: {(v.stderr.strip().splitlines() or [''])[0]}")
        raw = git(repo, "cat-file", "tag", t).stdout
        tags.append((t, v.returncode == 0, raw.split("\n\n", 1)[1] if "\n\n" in raw else "",
                     git(repo, "show", f"{t}^{{commit}}:{path}").stdout))
    decided, out = check(tags, git(repo, "show", f"HEAD:{path}").stdout)
    for iid, (eff, name, _, _) in sorted(decided.items()):
        print(f"DECIDED {iid}: {eff} ({name})")
    for o in out:
        print("PROBLEM", o)
    return 1 if out else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
```

---

## Sources

**Mithril.**
- ROADMAP §1–§4, §7–§11.
- ARCHITECTURE §6.3, §7.3, §13, §13.1, §16, §17.
- [03-trust](architecture/03-trust.md) §1, §4.3–4.4, §7.2–7.3, §8, §11.3.
- [05-agent-protocol](architecture/05-agent-protocol.md) §13.
- [06-forge](architecture/06-forge.md) §6.6–6.9, §7.1–7.2, §8.2.
- [07-hearth-port](architecture/07-hearth-port.md) §1–§4, §6–§13.
- DECISIONS §1, §4; DR-014, DR-015, DR-017, DR-018, DR-019, DR-022, DR-023, DR-026.
- [m0/README.md](m0/README.md); [m0/PLAN.md](m0/PLAN.md) §2, §3.7–3.9, §4, §6, §7, §8, §13;
  [m0/COST.md](m0/COST.md) §1–§5; [m0/prereg/X0-census.md](m0/prereg/X0-census.md).
- Research: [R11](research/R11-hearth-port-requirements.md), [G03](research/G03-gpu-tier-and-cross-device-determinism.md),
  [G04](research/G04-transcendental-libm-numeric-spec.md), [R02 §10](research/R02-open-endedness-revisiting.md),
  [R03](research/R03-llm-language-ergonomics.md).

**Hearth**, clone at b5d3f14, read-only, 2026-10-16.
- `governance/INVARIANTS.md`
- `governance/decisions/ADR-0001`, `ADR-0003`, `ADR-0004`, `ADR-0008`, `ADR-0009`; `TEMPLATE.md`
- `governance/tools/adr.py`
- `governance/README.md`
- `governance/tasks.json`
- `governance/handovers/H03-forward-gen-001.json`
- `governance/reviews/2026-10-05-ci-first-runs.md`
- `.github/CODEOWNERS`; `.gitattributes`; `CMakeLists.txt`
- `docs/NUMERICS.md`
- `engine/include/hearth.h`
- `engine/src/store.c`, `hx_store.h`, `hx_model.h`, `model.c`, `quant.c`, `quant_avx2.c`, `quant_avx512.c`
- `python/hearth/server.py`
- `tests/golden/test_golden_invariants.py`

There is no ADR-0010 at b5d3f14.

**GEMS_Challenge** (local repository on the laptop, commit `2752b35`, 2026-10-16), read only for the
co-tenancy facts in D0-10d: `ops/gpu_calendar.md`, `ops/eligibility_E1_plan.md:127`,
`tools/remote/` (file names only).
