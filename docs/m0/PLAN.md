# M0 sprint plan

Status: living document, first version 2026-10-16, revision 2 the same day after a same-family
review (§15), revision 3 the same day by the owner track to carry the Owner's chat answers of
2026-10-16 and to align with [D0_BRIEF](../D0_BRIEF.md), and revision 4 the same day by the owner
track after one review of revision 3 (Claude, same family, independent context; §14, §15). Revision 5,
2026-10-23, by the queue track, makes consistency edits only: it carries Pierce's batches 3
and 4 (interim chat signature, written delegation). It was revised the same day after one review of the queue
track's files (Claude, same family, independent context; §15). The plan track maintains it. Every other track updates its own rows in the [status table](#12-status-table) in the same change
that lands its work.

**Owner answers received 2026-10-16 (chat; ratify at sitting 1, Sun 2026-10-18).** The verbatim
source, with the option text Pierce saw, is [OWNER-ANSWERS.md](OWNER-ANSWERS.md) (commit `11210a8`).
Batch 1: D0-10a "No metered API"; D0-10c "Local Qwen3 via Hearth" (its option text: the ROADMAP
pilot, "reported but not part of the kill"); D0-12 "Batch weekly review" (collection under any record
waits for the weekly sitting, except X0, already authorised). Batch 2: the X1 rule "Claude kills; pass
provisional" (D0_BRIEF Q16 = OPT4_STRICT, to be drafted as a signed amendment record); D0-10d "4 pilot
nights, then a rule" (23:00–07:00 PT, starting in week 1, then a re-signed rule of 4–7 nights a week;
Pierce keeps GEMS out of those hours); the cadence "Sunday evening" (sitting 1 on Sun 2026-10-18, its
packet due Sat 2026-10-17, night). Status: decided by Pierce in chat; not yet AUTHORITY facts until a
`d0-sign-<n>` tag ratifies them; work proceeds on them provisionally. Everything else in D0 is open,
including D0-9a, D0-10b's hours, D0-7a and D0_BRIEF Q17 and Q18. [D0_BRIEF §0](../D0_BRIEF.md) maps the
answers onto the signature lines. The consolidated, ranked list of open owner questions, with sitting
1's agenda, is [OWNER-QUEUE.md](OWNER-QUEUE.md).

**Owner answers of 2026-10-23 (revision 5).** Sitting 1 did not take place. In batch 3 Pierce answered:
- "Chat now, key on Sunday": interim chat signatures now, an SSH key and signed tags at sitting 2 (Sun 10-25);
- "Accept all four defaults": C01, the thread cap lifts only inside the 23:00–07:00 windows; C02, timing runs
  read the real Qwen3-30B-A3B Q4 file on the NVMe, read-only; C25, X3's parity stays provisional until X4's
  calibration, which runs on `x3_bench`; D0-7a, measurement may run unattended inside windows, with no agents
  running then;
- "Terms OK; run the smoke run" (A20).

In batch 4 he signed sitting 1 in chat with effort = `max`. That ratifies the answers above, SIGNS the X0
record (frozen at `152fa33`, OQs deferred) and SIGNS X1-amendment-1 (frozen at `ac751b8`; `claude-opus-5-5`,
effort `max`, s = 50%, cap 160, K = 6). He also gave a written delegation, logged in
[DELEGATED.md](DELEGATED.md).

Status wording from now on: ratified by his interim chat signature; under A10 the tag at sitting 2 is the
AUTHORITY fact. OWNER-QUEUE classifies every open item and lists what only Pierce can do at sitting 2. Where
this plan below says "sitting 1 (10-18)" or "ratify at sitting 1", read it with this paragraph.

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
- **Signing rhythm** (D0-12's chat answers, pending ratification): one weekly signing sitting, on
  Sunday evenings. Each Friday-to-Thursday week holds one: W0 10-18 (sitting 1), W1 10-25, W2 11-01,
  W3 11-08, W4 11-15, W5 11-22, W6 11-29, W7 12-06, W8 12-13, W9 12-20, W10 12-27, W11 2027-01-03,
  W12 01-10 [D: `scratchpad/owner/calc2.py`]. A "sign" week in §8 means "at that week's sitting". A
  step on a week's Friday or Saturday needs the previous week's sitting. A record ready mid-week waits
  for the next sitting, so each freeze → fill-in → sign chain can carry up to a week of wait
  [inference]. Each sitting's packet is due the Saturday night before it (OWNER-QUEUE).
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
   families and the quiet windows. X1's kill needs at least two frontier families (ROADMAP §1 rule
   5). X1's task authors must come from a different family than the card editors, and its planted Dc
   corpus from a family other than `mithi`'s author (05 §13, ROADMAP §3.2). X4's blind batch needs an
   Adversary from another family. CC and X2's lockstep proof need a Prover from another family. Every
   agent today is a Claude model [M, sprint brief]. **The chat answers of 2026-10-16 settle most of
   D0-10 (pending ratification): no metered API; no family besides Claude except the local Qwen3 via
   Hearth, as the pilot; the quiet windows (D0-10d); and the X1 rule (Claude kills, pass provisional;
   D0_BRIEF Q16). X1 still cannot write a sealed template until Pierce chooses the template author
   (D0_BRIEF Q18, with no default: his rule's text says "no model writes them") and the Gatekeeper
   store, and its rule rests on his check of the Claude Code plan's terms and capacity (OWNER-QUEUE
   A20). Every "other family" role waits on D0_BRIEF Q17 (the local Qwen3, by a new answer, or
   unmet).** Until then the team can build but cannot evaluate any gate except X0's, and X0's only once
   its record is SIGNED. D0-10b's hours are still open.
2. **Owner hours.** About 195 h in total [inference, ROADMAP §3.7], about 33 h/week at peak
   [inference, ROADMAP §10]. ROADMAP §10 says owner time goes to table entries, the X1 suite,
   pre-registrations and D0. Of those, reviewing the X1 suite and the X2 semantics table is the longest
   owner-bound chain [G]. Freeze commits and signatures also queue on Pierce (R26).
3. **Quiet-machine nights on the shared desktop.** ROADMAP §10 gives about 60–215 quiet hours, or
   8–27 nights of 8 h [inference]. The reconstruction in §6.2 gives the following [D]:
   - 60.3 h at σ_d = 2% and 221.0 h at σ_d = 4% when A/A sessions last about one planned test;
   - 90.9 h and 333.4 h when every A/A session runs to the amber limit N.

   The plan therefore asks for nights as D0_BRIEF D0-10d recommends: a **staged window**, which
   Pierce's chat answer chose (pending ratification): 4 pilot nights of 8 h, 23:00–07:00 PT, **from
   W1**, carrying the noise pilot and the profile measurement, once the X4-noise-pilot record is
   SIGNED. After it, the derived rule of §6.3 sets the rate from the measured σ_d, within **4–7**
   nights a week (his option text), and Pierce re-signs it. Revision 2 asked for a fixed 7 nights a week
   from W2; revision 3 follows the brief. The rule's outputs show what the choice costs: at 4 nights a
   week and σ_d = 4%, the planted-regression calibration finishes on the last night of W6 with no
   slack, and X3's verdict, which needs that calibration (§3.4), lands in W7 under Plan A [D, §6.3];
   at that σ_d the rule asks for more than 7 under Plan A and 5 under Plan B.

*Revision 5 (2026-10-23).* Sitting 1's steps that Pierce signed in chat on 10-23 are done: the answers
ratified, the X1 amendment record SIGNED, and the plan check (A20). The rest of sitting 1 moves to sitting 2,
Sun 10-25: D0-9a's key, D0-10b's hours, the signed D0_BRIEF Q17 and Q18 lines (not delegable; recommendations
QWEN3_LOCAL_PROVISIONAL and GEN_QWEN3, DELEGATED P3 and P2), and the X4-noise-pilot record if it is
FROZEN by then. X1's next owner-independent step is the §6.2 smoke-run gate, at a time Pierce agrees, with the
account idle (batch 3).

**Critical path** [G], against Sunday sittings (10-18, 10-25, 11-01, …) and pilot nights from W1.
At Plan B cadence, operative until D0-10b's hours are signed: sitting 1, Sun 10-18 (D0-9a; the chat
answers of both batches ratified; D0_BRIEF Q18 and Q17 answered; the plan check, OWNER-QUEUE A20) →
the X1 amendment record signed (10-18 if it is FROZEN in the packet, otherwise 10-25) → X1's
template authoring (**under GEN_QWEN3 if chosen**: a generator built by Claude, templates by the
local Qwen3, W1–W5, if the template hours fit the shared cap; **under GEN_OWNER**: Pierce's hours,
which move X1's verdict to ≈ W15–W32 at ≤ 1 held-out item per template or ≈ W13–W21 at 2–3 [G]) →
sealing → card iteration and the calibration run → CC's X1-subset rules frozen and the `mithi`
precondition → X1 held-out runs (≈ W10–W11 under GEN_QWEN3) → M0 verdict (≈ W12). The held-out runs
also depend on the Claude Code plan's account-wide token windows (X1 record; R17, R29). At Plan A
cadence the same chain compresses to a W6 verdict only if the sitting falls in W0, which sitting 1
(10-18) does. The night chain runs beside it: X4-noise-pilot SIGNED (10-18, or 10-25 at the latest
for W1 nights) → 4 pilot nights in W1 → the rate rule re-signed → calibration nights. X2 runs in
parallel. Its verdict date depends on Q9: at the end of calendar W6 (Plan A, or Plan B-cal in §7.2),
or in the scheduled verdict week.

**What the team does this week without the Owner** [G]:
- X0 collection (the Owner's instruction of 2026-10-16, confirmed by his chat answer to D0-12 pending
  ratification, authorises it once its record is frozen; see [X0-census](prereg/X0-census.md));
- drafting every pre-registration record, with the rules parts of X1-heldout, X2-gate, X3-parity and
  X4-calibration ready for an early freeze (§8), and sitting 1's packet (due Sat 10-17, night:
  OWNER-QUEUE), with the X1 amendment record and the X4-noise-pilot record frozen if they are ready;
- building X1's grammar, cards, `mithi`, tooling kit and harness, and only the family-agnostic parts
  of the X1 restructure (the generator engine, a Claude Code runner prototype, F = 1 power code); no
  sealed content;
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
| Desktop limits | Mithril jobs capped at 8 threads; < 500 MB of new data on C:; big data on D:, a slow USB HDD; other projects run there; quiet windows are negotiated with Pierce (chat answer 10-16: 23:00–07:00 PT, pending ratification). This plan reads the 8-thread cap as an **aggregate** over all Mithril jobs, not a per-job cap (Q2) | [M, brief]; reading [G] |
| GPU | The RTX 5070 belongs to another project's queue; Mithril never uses it | [M, brief] |
| Measurement host | The desktop, per D0-8's recommendation. **Not decided:** provisional, pending D0-8 | [M, brief]; decision open |
| Hearth | GitHub `main` = `b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220`, committed 2026-10-05T23:15:13−04:00, equal to the desktop's HEAD | [M, plan: `git log` on the read-only clone]; HEAD equality [M, brief] |
| Hearth clone size | 5.9 MB including 1.6 MB of `.git` (the read-only scratch clone) | [M, plan: `du`, 11:41 PT] |
| Hearth working tree | 21 uncommitted R3 entries on the desktop (17 modified, 4 untracked), not on GitHub | [M, brief] |
| Hearth simulator | `hearth.sim` is Python and needs only numpy (Hearth `docs/SIMULATOR.md`), so it runs on the laptop | [M, plan: read] |
| Model families | All agents are Claude models; no second family is provisioned. Owner chat answers of 2026-10-16 (pending ratification): no metered API for any family; the only family besides Claude is the local Qwen3 via Hearth, as the ROADMAP pilot | [M, brief]; answers from [OWNER-ANSWERS.md](OWNER-ANSWERS.md) |
| X0 toolchain (refresh, owner track) | `TOOLCHAINS.md` now exists and lists LLVM 23.1.3 (Windows and Linux), XED v2026.08.23 and CMake as working, on D:; it states that no census data was collected and no Hearth source compiled | [M, owner track: read 2026-10-16 14:38 PT] |
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
- **Waits on.** Collection is authorised by the Owner's instruction of 2026-10-16, as the record states,
  and his chat answer to D0-12 confirms X0 as the one exception (pending ratification). The record
  must be FROZEN first (its Appendix D freeze checklist was empty on 2026-10-16 [M, owner track]).
  The Gatekeeper evaluates the verdict only once the record is SIGNED (D0-12), with the signature form
  of D0-9a. The record's OQ-1 to OQ-7 should be answered before the first compile: an answer that
  loosens a gate after X0 data exist is a post-data amendment (record Appendix A).
- **Now.** Toolchain setup, scripts, freeze, and compiling configurations A–D on the desktop in
  daytime. In W0, X0 is the only Mithril desktop job and may use all 8 threads. From W1 its jobs go
  through the job wrapper (§6.1) and pass `-j` explicitly to fit their token share.

### 3.2 X1: cold-agent writability (ROADMAP §3.2, weeks 0–5)

**The X1 rule is answered; its template author is not (revision 4).** Under the chat answers of
2026-10-16 there is no frontier Family B and no metered spend, so this section's "family B" steps
cannot run as written. The X1 record's section "X1 under the 2026-10-16 owner constraints" gave four
options. Pierce's batch-2 chat answer chose the rule (D0_BRIEF Q16 = OPT4_STRICT, pending
ratification by a signed amendment record): Claude, through the Claude Code plan, is the only
kill-carrying family; a breach is binding and a pass is provisional until a second frontier family
confirms it at M1; sealed items are generated from templates with deterministic oracles. **Still
open:** who writes the templates (D0_BRIEF Q18: GEN_OWNER matches his text "no model writes them";
GEN_QWEN3 departs from it; no default), the local Qwen3's other roles (D0_BRIEF Q17), the Gatekeeper
store (Q5) and the plan check (OWNER-QUEUE A20). In this plan, a bare "Qn" is this plan's own §13
question; the brief's are always written "D0_BRIEF Qn". The run's cost is plan tokens, daytime desktop
hours and, under GEN_OWNER, owner hours, not dollars. Wherever this section says "family B" below,
read "the non-Claude author D0_BRIEF Q17–Q18 name".

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
  - **A Rust arm on the card-iteration items** (proposal, pending this plan's Q16 and D0_BRIEF Q16).
    05 §13 defines σ_ta as the SD of the item-specific *Mithril-minus-Rust* arm effect. ROADMAP §10's
    card-iteration design runs only the 2 Mithril arms, so σ_ta cannot be estimated from it. The Rust
    arm needs no card, so one epoch is enough [G]: 20 items × 5 attempts = 100 Claude attempts at one
    kill-carrying family (200 at two), on the plan's tokens; $0.1–0.4k at two families is an
    API-price estimate, not a budget (D0-10a chat answer) [D at ROADMAP §10's $0.5–2 per attempt]. If the Owner declines it, the X1-heldout rules use a
    pre-registered prior floor for σ_ta instead. The X1 track proposes the value. For scale, the
    power simulation's scenarios imply σ_ta of 0.11, 0.18, 0.24 and 0.30 [S, same file, §1 at n = 60].
    *Revision 3 note:* the X1 record (§6.3, its Owner question 18) proposes a third option, a
    dedicated 24-item calibration set run after the card freeze, and argues that card-iteration items
    cannot serve because the card is tuned on them. The two proposals conflict; OWNER-QUEUE lists them
    as one question, with the X1 record's option as the default because it is the later and more
    detailed design [G]. Under D0-10a's answer the dollar figures here become plan tokens.
  - The Gatekeeper analysis script (the mixed-effects model of 05 §13).
  - The local-model pilot (10 items × 3 attempts × 2 arms = 60 attempts [inference, ROADMAP §10]).
    Its machine hours under the 8-thread cap are unverified; see the local pilot item below.
  - The report.
  - Paths: `experiments/x1-harness/` (created by the X1 track [M, plan]). The first version's
    `x1-writability/` proposal is withdrawn. The sealed suite, the reserve, reference solutions and
    oracles live **outside any repository**, in the Gatekeeper store (Q5).
- **Gate and kill.** ROADMAP §3.2: Rust − Mithril VP@1 ≤ 15 points and CABW no more than 5 points worse
  than Rust's. Either breach is the kill (STOP-L). Amber triggers (a)–(c) as written there.
- **Budget.** $7–15k (an API-price estimate, not a budget: D0-10a chat answer) and ~55 owner h,
  including the kit and the checker precondition [inference, ROADMAP §3.2]. The measurement share is
  ≈ 2.9k held-out attempts ($1.4–5.8k) plus ≈ 1.2k card-iteration attempts ($0.6–2.4k), both API-price
  estimates [inference, ROADMAP §10]. If the n rule asks for more than
  60 items, the held-out share grows by 48 attempts per item [D, ROADMAP §10: (5 × 3 + 3 × 3) × 2];
  see [COST §1.3](COST.md#13-measurement-budget-inside-the-api-lines). *Revision 3:* under D0-10a's
  chat answer there is no metered budget; the X1 record prices each restructure option in Claude Code
  plan tokens (≈ 0.73–2.63 billion for one family's attempts at n = 96 [D]), daytime desktop hours
  for Qwen3 (≈ 44–378 h under GEN_QWEN3 at ≤ 1 held-out item per template, ≈ 30–190 h at 2–3 [D])
  and, under GEN_OWNER, owner hours (≈ 64–306 or ≈ 36–141 [D from G]); COST §1.6 carries the figures.
- **Depends on.**
  - CC: the X1-subset rules must be frozen, and the hand derivations available, before the `mithi`
    precondition.
  - X4: the sandbox, reused for harness isolation [G].
- **Waits on.** *(Revision 5: Q16 is ratified in chat and X1-amendment-1 is SIGNED (10-23). A20 is answered
  ("Terms OK; run the smoke run"). The runner and model are accepted (OWNER-QUEUE D07). Q18 and Q17 wait for
  Pierce's signed lines at sitting 2; neither is delegable, and the recommendations are DELEGATED P2 and P3.
  Until he signs, Qwen3 does only S71, within R2's 5–10 desktop hours (P13). The store (Q5 = OWNER-QUEUE A06)
  is his.)*
  - **D0_BRIEF Q16 ratified** with its amendment record, **D0_BRIEF Q18** (the template author) and
    **D0_BRIEF Q17** (the planted corpus, item reviews, the semantic guard and the kit acceptance
    corpus), all at sitting 1 (10-18); and Pierce's check of the plan's terms and capacity (OWNER-QUEUE
    A20). D0-10c's chat answer settles the families; the Qwen3 checkpoint is still to pick.
  - D0-11b is **not** a week-0 item (revision 3 follows D0_BRIEF Q1: ROADMAP needs it by M1, and X1's
    author roles are D0_BRIEF Q16–Q18's).
  - D0-12: signatures at a weekly sitting on the card-iteration, precondition and held-out records
    before those runs.
  - The location of the sealed store (Q5).
  - Where the Rust and LLVM toolchains for `mithi` and the harness may live (Q4).
  - Under the X1 rule of D0_BRIEF Q16 (answered in chat): Pierce's check of the plan's terms and
    capacity (OWNER-QUEUE A20) and a measured smoke run of the Claude Code runner on the public smoke
    set (tokens and plan-window share per attempt [M]), before the X1 records freeze; and this
    plan's own Q18 (not D0_BRIEF Q18) for Qwen3's daytime share of the 8-thread cap.
- **Now.**
  - Grammar, cards, `mithi` and the kit.
  - The harness, family templates, oracle and mutant infrastructure.
  - Drafting the X1 records, with the X1-heldout rules ready to freeze in W2 (§8).
  - Claude may draft the cards. Task items are authored by a non-Claude author, because 05 §13
    requires task authors from a different family than the card editors. Until D0_BRIEF Q18 and the
    store (Q5) are answered, no sealed content is written; the generator engine and the runner are
    built as family-agnostic tools (provisional, pending D0_BRIEF Q17–Q18).
- **Kit cut-off (made more precise; for the X1-heldout record).** The kit's acceptance tests are frozen
  with the X1-heldout rules (W2 in Plan A). The W4 fill-in names a kit commit before the first held-out
  attempt. The kit counts as "ready" only if those tests pass on that commit. Otherwise the arm is
  dropped from X1 and amber (a) waits for M1 (ROADMAP §3.2).
- **Local pilot under the cap.** ROADMAP's 5–10 h assumes "loaded 9950X time" at about 20 tok/s
  [inference, ROADMAP §3.2]. Under the daytime cap of 8 threads, decode may run on one CCD, and one CCD
  caps at 64 GB/s [R08, via 06 §6.7]. Hearth's thread scaling under an 8-thread cap is not verified
  here. Before X1-local-pilot freezes, the pilot's machine hours are re-estimated from a short
  measured tok/s run under 8 threads, in daytime. If agentic attempts then come close to the harness
  time-outs, Pierce chooses between a daytime cap exception and fewer attempts (Q18). Under the chat
  answers the same tok/s run also sizes every other Qwen3 job (templates, planted corpus, reviews,
  Provers and Adversary), so it moves to W1.

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
  - A frozen X2-fuzz record, then SIGNED at a weekly sitting, before any vector runs on silicon.
    Revision 3: the chat answer to D0-12 (pending ratification) gives an instruction route to X0
    only, so the README's instruction route no longer covers X2-fuzz.
  - D0_BRIEF Q17: the local Qwen3 as the different-family Prover for the lockstep proof (by a new
    answer; under QWEN3_LOCAL_PROVISIONAL a pass that rests on it stays provisional), or the
    requirement stays unmet and the verdict carries the same-family label (X2 record, question 6).
    Daytime desktop use under the 8-thread cap is already allowed [M, brief]; any Qwen3 run shares
    that cap with the fuzzing.
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
  (Q1). Q17 (reference binary). *(Revision 5: D0-7a is answered (batch 3, 10-23), and C25 too: X3's parity
  stays provisional until X4's calibration, which runs on `x3_bench`.)*
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
  - The report. Path: `experiments/x4-integrity/` (created by the X4 track [M, owner track, 2026-10-16]).
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
  - D0-7a: unattended runs inside quiet windows. The noise pilot is the first unattended night (W1
    under D0-10d's chat answer), so D0-7a, or Pierce's consent under Q1, is needed by then: 10-18, or
    10-25 at the latest for a first night from 10-25. *(Revision 5: answered in chat 10-23, "measurement
    may run unattended inside windows, with no agents running then"; ratified. C01 and C02 too: the cap
    lifts only inside windows, and the real Q4 file is read on the NVMe, read-only.)*
  - D0-9: (a) the interim signature form, needed at the first weekly sitting; (b) the long-term
    hardware key is needed by X4 (ROADMAP §11), but per D0_BRIEF's current text no M0 step blocks on
    it if (a)'s signed tags are accepted for the kit hash-freeze and the calibration records.
    (Revision 2 put (b) before the kit freeze, following the brief's earlier draft.)
  - D0-8: the host (provisional).
  - D0-10d: the quiet windows (answered in chat: 4 pilot nights from W1, 23:00–07:00 PT; ratify).
    D0_BRIEF Q17: the local Qwen3 as the blind batch's Adversary (by a new answer; under
    QWEN3_LOCAL_PROVISIONAL a pass that rests on it stays provisional), or batch (b) stays unwritten
    and X4's gate cannot pass at M0. No metered budget exists (D0-10a's chat
    answer); X4 never needed one for Claude work.
  - D0-12, at a weekly sitting, for the noise pilot as for every other record (no instruction route
    under D0-12's chat answer).
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
- **Waits on.** D0_BRIEF Q17 (under D0-10c's chat answer, only the local Qwen3 can be the
  different-family Prover and Adversary; otherwise the gate cannot pass at M0), CC's own Q6 (may the
  X1-subset freeze rest on same-family review), and D0-12 (the Owner's signature at a weekly sitting).
- **Now.** All drafting.

### 3.7 D0: owner decisions (ROADMAP §11, from W0, ~10 owner h)

- **Deliverable.** `docs/D0_BRIEF.md`, with recommendations and signature lines (README). It is not
  this track's file. It has been present since 11:35 PT [M, plan].
- **Order.** ROADMAP's "needed by" column is kept unchanged. A second column gives the earlier date
  that this plan's own schedule creates. Pierce should order his decisions by that second column.

  | ROADMAP "needed by" (§11) | Item | Needed by in this plan | Why |
  |---|---|---|---|
  | W0 | **D0-10, D0-12** | W0. **a, c, d, D0-12 and its cadence answered in chat 2026-10-16; ratify at sitting 1 (Sun 10-18).** b's hours still open; d's first night in W1. *Revision 5: ratified in chat 10-23 (interim); tags at sitting 2 (10-25)* | budget, families, cadence, nights; signatures |
  | — | **D0_BRIEF Q16–Q18** (new) | sitting 1 (10-18). Q16 answered in chat (X1 rule); Q17 and Q18 open. *Revision 5: Q16 SIGNED with X1-amendment-1 (10-23); Q17 and Q18 at sitting 2; not delegable, with recommendations in DELEGATED P3 and P2* | X1 writes no sealed template until Q18 (template author) and the store are answered; Q17 also gates X2's Prover, X4's batch (b) and CC's reviewers |
  | M1 | **D0-11** | (b) M1, as ROADMAP says. Revision 2 put (b) in W0, following the brief's earlier draft; the brief now keeps it at M1 (D0_BRIEF Q1) | 05 §13; D0_BRIEF D0-11b |
  | X4 | **D0-9** | **(a) the first weekly sitting**, needed to ratify anything; (b) X4, with no M0 step blocked if (a)'s tags are accepted for the kit freeze (D0_BRIEF D0-9). *Revision 5: (a) at sitting 2 (10-25); until then Pierce's chat signatures are the interim method (batches 3 and 4)* | D0_BRIEF D0-9a and D0-9b |
  | X4 | **D0-7** | **(a) W1**, before the noise pilot's first unattended night (or Q1 consent). *Revision 5: (a) answered 10-23* | the pilot runs unattended at night |
  | M4 | D0-8 | W1, for the provisional use of the desktop as host | X3 and X4 measure on it from the pilot on |
  | S0 | D0-2 | not on M0's path | S0 only (§3.9) |
  | M1's S1 | D0-3 | not on M0's path; M0 uses a stand-in for `hearth-c-ref` (§3.4, Q17) | S0 tag |
  | End of M0 | **D0-1** | W6 (Plan A) or ≈ W12 (Plan B) | M0 verdict |
  | S4 / S6a | D0-5 | — | — |
  | M5 | D0-6 | — | — |
  | S6 | D0-4 | — | — |

- **D0-8.** Its "needed by" is M4, but X3 and X4 measure on the desktop in M0, so the plan uses the
  desktop provisionally, pending D0-8. Calibration is per host, so a different choice means
  re-calibrating on the new host, not discarding the X3 and X4 code.
- The six chat answers of 2026-10-16 are decided by Pierce in chat and recorded as answers pending
  ratification, not as signatures (not yet AUTHORITY facts); nothing in this plan presents any other
  item as decided.

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

  *Revision 5 (2026-10-23), a proposal only:* X2's record defines no band for a gate missed without a kill. DELEGATED
  P28 proposes the state `gate_missed` for it, and P8 one added line, `if X2 == gate_missed: rows += NARROW (X2:
  failing variants stay tested)`, so that a missed X2 gate cannot drop out of the verdict. Pierce signs both in
  the X2-gate and M0-verdict records.

  *Revision 3, provisional, pending D0_BRIEF Q16 and Q7.* If Pierce chooses the X1 record's option 4b
  (Q16 = OPT4_STRICT), X1 gains a state `pass_one_family`: Claude alone passed and a second frontier
  family has not yet confirmed it. It is neither `pass` nor `kill`. The "X2 alone" clause, which reads
  X1 = pass, stays undecided. Unlike the other pending states, `pass_one_family` does not block the
  verdict: the verdict may be signed with X1 open and its confirmation owed before M1's DR-017 gate.
  An X1 `kill` under option 4b maps to the X1 rows exactly as above. Pierce's batch-2 chat answer
  chose option 4b (pending ratification).

  *Revision 4, provisional, pending D0_BRIEF Q17 and Q7.* If Pierce answers D0_BRIEF Q17 =
  QWEN3_LOCAL_PROVISIONAL, each gate pass whose different-family requirement is met only by the local
  Qwen3 (X4's batch (b), X2's Prover, CC's Prover and Adversary, the X1 precondition's planted corpus)
  takes the state `pass_local_family`. It is handled like `pass_one_family`: neither pass nor kill,
  not blocking the verdict, owed a frontier family's repetition. A kill, or a review that finds a
  flaw, maps as above.
- **Waits on.** D0-1 (needed by the end of M0), D0-12, D0-10 (if declined, there is no M0), Q7, and
  D0_BRIEF Q16 (the X1 state set).

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

*Revisions 3 and 4:* the D0-10 node now reads "sitting 1" (Sun 10-18): D0-9a, the chat answers of
both batches ratified (D0_BRIEF Q16 and D0-10d among them), D0_BRIEF Q17 and Q18 answered, D0-10b's
hours signed. "Non-Claude author" is the template author D0_BRIEF Q18 names (no default: the Owner,
the local Qwen3 by a new answer, or Claude by a labelled loosening). "Different-family reviews" are
the local Qwen3's if D0_BRIEF Q17 = QWEN3_LOCAL_PROVISIONAL or FULL; otherwise they stay open.

```text
sitting 1 ─┬─> X1 restructure (Q16-Q18) ─> non-Claude author: suite, reserve + planted corpus ─> card iteration ─┐
 (D0-9a,   │                                                                                                    ├─> mithi precondition ─> X1 held-out ─> X1 verdict ─┐
  D0-10,   │   CC note ─> X1-subset rules frozen + hand derivations ─────────────────────────────────────────────┘                                                    │
  Q16-18)  ├─> quiet windows (D0-10d) ─> noise pilot ─> profile ─> X3 A/B + X4 calibration (records signed) ─> X3, X4 verdicts ─────────────────────────────────────┤
           └─> different-family reviews via local Qwen3 (Q17): CC, lockstep proof, X4 blind batch, R-diff backlog ─────────────────────────────────────────────────┤
X0 census.json (hash + FP-sensitivity) ─> X2 fuzz iclass set + table scope + loop shapes ─> T1/T2 spike ─> X2 verdict ─> X0 narrowing (joint) ───────────────┤
X4 service + job wrapper ─> X3 A/B    X4-hacks-catalogue frozen ─> dev runs ─> kit hash-freeze ─> gated catalogue run ‖ blind batch ─> blind run          │
clean b5d3f14 reference binary (Q17) ─> X3 A/B, planted regression                                                                                        │
D0-12 (+ D0-9a form) ─> every SIGNED record         D0-1 ─────────────────────────────────────────────────────────────────────────────────────────────────> M0 verdict
```

| Track | Can run with no Owner decision | Blocks on | Provisional work (reversible) |
|---|---|---|---|
| X0 | everything, including collection once its record is FROZEN (Owner instruction of 2026-10-16, confirmed by D0-12's chat answer, pending ratification) | D0-12 (with D0-9a) for the verdict; X0 OQ-1 to OQ-7 before the first compile | none |
| X1 | grammar, cards, `mithi`, kit, harness, generator engine, runner prototype, record drafts | **D0_BRIEF Q16–Q18** (restructure, authors), Q17 (Qwen3 roles), D0-12, Q4, Q5, Q16, Q18; the Claude Code smoke run | none: no sealed content until D0_BRIEF Q16–Q18 |
| X2 | table drafts, Z3 proofs, transliteration, T1/T2 spike, mutant generator | **X0 `census.json` frozen (hash) and FP-sensitivity classification** (or the amendment rule of §3.3); fuzz-record signature at a weekly sitting; D0_BRIEF Q17 (Prover); D0-12; Q9 before the X2-gate rules freeze | B_iform scope until the census lands |
| X3 | generator, codegen, daytime builds and bit-identity tests | D0-10d (nights), D0-7a or Q1, D0-12, Q2, Q17 | the desktop as host, pending D0-8 |
| X4 | service, job wrapper, sandbox, catalogue batch, MIN/OPT, F1-sim, revisit prototype | D0-7a, D0-9a, D0-10d, D0_BRIEF Q17 (Adversary), D0-12; Owner-applied hygiene settings; Q2, Q3, Q15, Q17 | the desktop as host, pending D0-8; signature form pending D0-9a (Q6) |
| CC | all drafting | D0_BRIEF Q17 (reviewers), CC Q6, D0-12 | none |
| M0 verdict | mapping script and record draft | D0-1, D0-10, D0-12; Q7; D0_BRIEF Q16 (X1's state set) | the two "pending Q7" lines of §3.8, and the `pass_one_family` line |

Realistic expectation [G]: if the first weekly sitting slips by k weeks, X1, and with it the M0
verdict, slips by about k weeks. X0, the build halves of X2–X4 and the CC draft do not slip. If X0
slips past W1, X2's fuzz set and table scope slip with it (R27). Under the Owner's X1 rule the plan's
token windows are a second X1 risk that no Owner decision removes once he has accepted their cost
(R17, R29; OWNER-QUEUE A20).

---

## 5. Schedule

### 5.1 Plan A: ~33 owner h/week, verdict in W6

The dates are W0 = 2026-10-16 onward [D]. The phases are [G], aligned with ROADMAP §2's [inference]
timeline. Plan A applies only if Pierce signs about 33 h/week under D0-10b; until then Plan B (§5.2)
is operative.

```text
week (Fri start)  W0 10-16  W1 10-23  W2 10-30  W3 11-06  W4 11-13  W5 11-20  W6 11-27  (W7 12-04)
D0                [sitting 1: D0-9a, ratify, Q16-18; D0-10b,d][D0-7a, D0-8 ...]          [D0-1]
X0                [census ........][verdict]                                   [narrowing w/ X2]
X1                [grammar, cards, mithi, kit, harness, generator engine ...]
                           [suite + reserve + planted corpus (non-Claude author)][iter][pre][held-out ][report]
                                                                                [local pilot, days]
X2                [table, Z3, transliteration ......][T1/T2 spike ..........][final run][verdict] (amber: W7)
                           [Zen 5 fuzz, days, after census hash .]
X3                          [generator ..........][A/B nights][tuning     ][report]
X4                [service + sandbox + wrapper][pilot+profile][calibration nights ............] (may wait)
                  [catalogue dev][freeze][gated cat. ‖ blind batch][blind run][F1-sim, replay, revisit]
CC                [note ......................................][other-family review][signed]
M0 verdict                  [record frozen + signed]                           [dossier, signature]
```

*Revisions 3 and 4:* "Q16-18" are D0_BRIEF's. Sitting 1 is Sun 10-18, in W0. X1's lane is drawn
under GEN_QWEN3 if chosen: the local Qwen3's template authoring (≈ 18–161 daytime hours at 2–3
held-out items per template, ≈ 32–349 at ≤ 1 [D, X1 record]) must then fit W1–W3 inside the 8-thread
cap it shares with X0 and X2, which is unlikely at the top of either range [G]. Under GEN_OWNER the
lane is set by Pierce's hours instead, and Plan A's W6 verdict is out of reach [G]. "Other-family
review" means the local Qwen3's under D0_BRIEF Q17 = QWEN3_LOCAL_PROVISIONAL or FULL.

**Checkpoints** (each gives what must be true by the end of the week):

| # | By (Thu) | What must be true |
|---|---|---|
| C0 | W0, 10-22 | Sitting 1 held on Sun 10-18 (its date is Pierce's chat answer, pending ratification): D0-9a's signature form chosen; the six chat answers ratified (D0-10a, D0-10c, D0-10d, D0-12 with its cadence, D0_BRIEF Q16); D0-10b's hours signed; D0_BRIEF Q17 and Q18 answered; the plan check (OWNER-QUEUE A20) done. Signed if FROZEN in the Sat 10-17 packet: the X1 amendment record, the X4-noise-pilot record (with the X4-calibration rules frozen), the M0-verdict record, X0. (D0-11b is not a W0 item; revision 2 listed it here.) X0 record frozen, with OQ-1 to OQ-7 answered or deferred. Q1–Q6, Q9 and Q17 answered. Harness host and toolchain locations approved. Job-wrapper design agreed |
| C1 | W1, 10-29 | Sitting 2 on Sun 10-25 signs what sitting 1 did not: the X4-noise-pilot record and D0-7a at the latest (so the 4 pilot nights still fall in W1, 10-25 to 10-28); the X1 amendment record. X0 census, re-derivation and review done; `census.json` hash and FP-sensitivity classification handed to X2; X0 record SIGNED; X0 verdict computed. M0-verdict record frozen and SIGNED by 10-25 (otherwise X0's verdict waits for the 11-01 sitting). X2-fuzz record frozen by the Sat 10-24 packet, naming the census hash if it exists by then and otherwise the B_iform scope plus the census amendment rule (§3.3), and SIGNED on 10-25; fuzzing on silicon only after that. If it is not in the 10-24 packet, X2 fuzzing slips to after the 11-01 sitting, and the plan says so at C1. Noise-pilot nights run in W1. Local Qwen3 serving checked on the desktop: tok/s under 8 threads measured (Q18), daytime only. Claude Code runner smoke run on public items done (tokens per attempt [M]). X3 counting rule frozen before the first schedule line; generator emits its first ISA. X4 service skeleton measuring on the desktop (engineering dry runs, outputs discarded). Job wrapper live. F1-sim held-out traces hash-sealed |
| C2 | W2, 11-05 | **Rules frozen** before the data they could be tuned to: X1-heldout (analysis model, n rule, σ_ta estimator and floor, exclusions, reserve order seed, kit acceptance tests) before the first card-iteration attempt; X2-gate (counting rules, Q9 reading) before T1 runs on the real variants; X3-parity and X4-calibration (N and c rules, A/A stopping rule) before the noise pilot. `mithi` covers the X1 subset. Card-iteration items (~20) and the planted corpus delivered by the non-Claude author (D0_BRIEF Q16–Q18); reserve authoring started. X4-hacks-catalogue frozen; catalogue engineering runs done; kit hash-frozen at the end of W2. Noise-pilot and profile nights run. `numerics_v1` pool sealed. X3 generator emits all three ISAs and passes `test_quant` in daytime. Reference binary built and hashed |
| C3 | W3, 11-12 | CC X1-subset rules frozen. `mithi` precondition passed. Card iteration done (≤ 3 epochs), with the Rust arm if approved. Reserve sealed. Claude Code runner attempts per window measured. X3-parity and X4-calibration filled in and SIGNED, nights running. Gated catalogue run on the frozen kit done; blind batch written (by the local Qwen3 if D0_BRIEF Q17 = QWEN3_LOCAL). X2 rule list frozen and mutant kill rates measured. CC draft complete |
| C4 | W4, 11-19 | σ_ta computed by the frozen rule; n filled in; X1-heldout SIGNED; held-out runs under way at the concurrency sized in W3. Blind batch run. X2 lockstep proof under different-family review (the local Qwen3's, under D0_BRIEF Q17). X3 tuning window open if X3 misses parity. Planted regression done if σ_d ≈ 2% (in W3 at 7 nights a week, W4 at 4); at σ_d = 4% it ends in W5 at 7 nights a week [D, §6.3] |
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
    the non-Claude author (D0_BRIEF Q16–Q18) starts the card-iteration items; Claude Code runner smoke
    run on public items.
  - X2: entries for the census union; fuzzing in daytime once the census hash and the X2-fuzz record
    exist; Bochs build; transliteration.
  - X3: counting rule frozen; generator prototype; the Python-versus-Exo choice (owner review).
  - X4: service, load gate, fingerprint, job wrapper live, MIN/OPT oracle; F1-sim held-out traces
    hash-sealed.
  - CC: sections drafted.
- **W2 (10-30..11-05).**
  - Rules freezes: X1-heldout, X2-gate, X3-parity, X4-calibration (§8).
  - X1: `mithi` covers the subset; kit started; card-iteration items delivered; oracle mutant-kill
    checks; reserve authoring starts (non-Claude author).
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
  - X4: A/A microbenchmark nights; gated catalogue run on the frozen kit; blind batch written (the
    local Qwen3, daytime, under D0_BRIEF Q17); tombstone import; revisit prototype; replay tests.
  - CC: draft complete, same-family review.
- **W4 (11-13..11-19).**
  - X1: σ_ta and n by the frozen rule; X1-heldout filled in and SIGNED; held-out runs (≈ 2.9k attempts
    at n = 60 [inference, ROADMAP §10]; 48 more per extra item [D]).
  - X2: lockstep proof for X0's loop shapes, to a different-family Prover (the local Qwen3 under
    D0_BRIEF Q17); table/silicon mismatches fixed.
  - X3: a tuning window if the primary metric misses parity. It lasts at most two weeks: the kill is
    "still < 90% after two weeks of tuning" (ROADMAP §3.4).
  - X4: planted-regression nights; blind batch run; F1-sim held-out traces unsealed under their
    record.
  - CC: different-family Prover and Adversary (the local Qwen3 under D0_BRIEF Q17).
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
D0     [sitting 1: 9a, ratify, Q16-18, 10b, 10d][D0-7a, 8]                    [D0-1]
X0     [census][verdict]                                                 [narrowing]
X1     [grammar, cards, mithi, kit, generator ..][suite + reserve + corpus by the non-Claude author, Owner sample review ...][iter][pre][held-out][report]
X2     [table, Z3, transliteration ..............][T1/T2 spike, rule proofs ..........][final][verdict]
X3           [generator ..............][A/B nights][tuning][report]
X4     [service, sandbox, wrapper, catalogue dev][pilot][calibration nights ..........][blind][report]
CC     [note .............................................................][review][signed]
```

**Plan B checkpoints** [G for content; dates D]:

| # | By (Thu) | What must be true |
|---|---|---|
| B-C0 | W0, 10-22 | As C0 (sitting 1, Sun 10-18) |
| B-C1 | W1, 10-29 | As C1's sitting-2 items (Sun 10-25): X4-noise-pilot and D0-7a signed at the latest, pilot nights in W1. X0 census, re-derivation, review; census hash to X2; X0 SIGNED; X0 verdict. M0-verdict SIGNED by 10-25. X2-fuzz SIGNED on 10-25 (with the census hash, or the B_iform scope plus the amendment rule) and fuzzing; otherwise after 11-01. Local Qwen3 serving checked (tok/s under 8 threads, Q18). Claude Code runner smoke run done. Job wrapper live. F1-sim traces sealed. X3 counting rule frozen |
| B-C2 | W3, 11-12 | Rules freezes done as in C2 (the X1-heldout rules freeze at the latest before the first card-iteration attempt). Kit hash-frozen. Noise-pilot and profile nights run. `numerics_v1` sealed. `mithi` covers the subset. X3 passes `test_quant`. Reference binary built and hashed |
| B-C3 | W5, 11-26 | X3-parity and X4-calibration SIGNED (by W4) and nights running. Gated catalogue run done; blind batch written (local Qwen3, D0_BRIEF Q17). X2 rule list frozen and kill rates measured. Card-iteration items reviewed |
| B-C4 | W7, 12-10 | Planted regression done at σ_d ≤ 4% with ≥ 4 nights a week (W7 at σ_d = 4% and 4 nights a week, central A/A [D, §6.3]). X3 report. Blind batch run. Card iteration done (with the Rust arm if approved). X2 lockstep proof under different-family review (local Qwen3, D0_BRIEF Q17). Suite and reserve review about half done |
| B-C5 | W9, 12-24 | Suite, reserve and planted corpus reviewed and sealed. CC X1-subset rules frozen; `mithi` precondition passed. X2 final run on the frozen checker (if Q9 = the scheduled verdict week) |
| B-C6 | W11, 2027-01-07 | X1-heldout filled in and SIGNED; held-out runs complete. X2 verdict and joint X0 narrowing. CC signed. X4 calibrations complete (at σ_d = 4% and 4 nights a week, end-to-end A/A ends in W10 [D]) |
| B-C7 | W12, 01-14 | Gatekeeper analysis; all verdict files signed; D0-1 decided; M0 verdict signed |

- The X1 suite review runs at about 5 owner h/week from W3 to W9 (§7.2), so held-out runs land around
  W10–W11 [G]. Under the Owner's X1 rule with a generated suite, the Owner's item review becomes a
  seeded sample of templates after the card freeze, and the suite's pace is set instead by the
  template author's hours (Qwen3's daytime hours under GEN_QWEN3, Pierce's under GEN_OWNER, which
  moves the verdict to ≈ W15–W32 or ≈ W13–W21) and the plan's token windows (X1 record) [G].
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
  reading G, Q2]. The sprint brief of 2026-10-16 states the aggregate reading as a rule ("8 threads
  in total across all tracks") [M, sprint brief]; whether the cap lifts inside quiet windows is still
  Q2. *(Revision 5: answered 10-23, C01: "the 8-thread cap lifts only inside 23:00–07:00 windows".)* This covers builds, X0 compiles, X2 fuzzing, X3 builds and correctness tests, Bochs, the
  reference-binary build, the X1 local-model pilot and, under D0-10c's chat answer, every other local
  Qwen3 job (template or item authoring, the planted corpus, reviews, the Prover and Adversary roles
  of D0_BRIEF Q17). Local model runs, fuzzing and builds never overlap a quiet window (DR-023, ROADMAP
  §3.2). Qwen3 jobs need their share of the 8 tokens agreed in advance (Q18), because X2's fuzzing runs
  in the same weeks.
- **Job wrapper.** From W1, every Mithril desktop job goes through the job wrapper (§3.5). The wrapper
  holds the 8-token semaphore, refuses starts inside quiet windows and logs stamps. Ad hoc SSH
  commands that use more than 1 thread are not allowed. In W0, before the wrapper exists, X0 is the
  only multi-threaded Mithril desktop job. Any other track's desktop command uses 1 thread.
- **Desktop quiet windows** are negotiated with Pierce (D0-10d; chat answer 10-16, pending
  ratification: 23:00–07:00 PT, 4 pilot nights from W1, then a re-signed rule of 4–7 nights a week;
  no Mithril agents, builds or WSL activity in a window). Inside one, the supervisor holds a
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
  *Revision 3:* under the chat answers the Claude attempts run as headless Claude Code sessions on the
  plan, still network-bound and still on the laptop; their limit is the plan's 5-hour and weekly
  windows, not a dollar budget (R17). Only Qwen3 work uses the desktop.

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
  [G] in W2 (revision 3), or in W1 under D0-10d's chat answer, which frees W2's nights for calibration
  if its records are signed by the 11-01 sitting.
- **Ask (revision 3: the staged window of [D0_BRIEF](../D0_BRIEF.md) D0-10d; revision 4: Pierce's
  chat answer, pending ratification).** 8-hour windows [inference, ROADMAP §10 uses 8 h nights],
  23:00–07:00 PT (his answer).
  - **Stage 1, the pilot week:** 4 nights, **from W1** (his answer), once the X4-noise-pilot record is
    SIGNED (10-18, or 10-25 at the latest for W1 nights), the X4-calibration rules are FROZEN, D0-7a is
    signed and the measurement service v0 has passed its acceptance check. They carry the noise pilot
    (2–3 nights) and `mithc profile measure` (1 night) [G].
  - **From the next week:** the rate the rule below gives from the pilot's σ_d, **within 4–7 nights a
    week** (his answer's floor and cap), proposed by the team and re-signed by Pierce at a weekly
    sitting. Under the answer, every rate of 2 or 3 in the table below becomes 4.
  - **End:** when X3's and X4's planned quiet hours are met, not at a fixed week.

  Revision 2 asked for a fixed 7 nights a week from W2, following the brief's earlier draft. The
  arithmetic behind that ask still holds [D]: 7 a week is the only rate that covers ROADMAP's 215 h top
  figure by W6 under Plan A (280 h of W2–W6 capacity, or 248 h after the pilot and profile). The staged
  window reaches the same rate when the measured σ_d calls for it, and asks for fewer nights when it
  does not; under Plan B, the operative cadence, the rule asks for 2–5 nights a week up to σ_d = 4%
  in the central case (table below).
- **Rule for setting the rate after the pilot** (proposal for D0-10d; inputs [G], arithmetic [D]):
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

**Plan A calendar if the rule gives the maximum rate, 7 nights a week after the pilot week** [G for
content; finish weeks D from the table above]. Revision 3: under D0-10c's chat answer, the daytime
column also carries the local Qwen3's jobs (X1 templates and planted corpus, item reviews, the X4 blind
batch, the X2 and CC Prover and Adversary roles) inside the same 8 threads, in the weeks D0_BRIEF Q16–Q18
schedule them; they are not drawn here.

| Week | Desktop daytime (wrapper, ≤ 8 threads in aggregate) | Desktop quiet nights | Laptop |
|---|---|---|---|
| W0 | LLVM and XED setup; X0 compiles and decodes (X0 alone may use 8 threads) | none | agent sessions; light until 19:00 PT on 10-16; venv (Z3, numpy) |
| W1 | X0 twin builds and re-runs; X2 fuzz bring-up (vectors only after the census hash and the X2-fuzz record); Bochs build; X4 dry runs (outputs discarded); job wrapper live | revision 4, under D0-10d's chat answer: noise pilot (2–3 nights [G]) and profile measurement (1 night [G]), 23:00–07:00 PT, once X4-noise-pilot is SIGNED (10-18, or 10-25 for the nights of 10-25 to 10-28) | harness, `mithi`, MIN/OPT; F1-sim held-out traces sealed |
| W2 | X2 fuzz; X3 builds and correctness tests; reference-binary build; X4 catalogue engineering runs | revision 3 drew the noise pilot and profile here; under D0-10d's chat answer they move to W1, and W2's nights run only if X3-parity and X4-calibration are signed (11-01 sitting) | harness bring-up; F1-sim |
| W3 | X2 fuzz tail; X3 builds; X4 gated catalogue run on the frozen kit (in a window if a hack's declared stage needs one) | X3 A/B; X4 A/A microbenchmark; planted regression (done in W3 if σ_d ≈ 2%) | card iteration (+ Rust arm); tombstone replay; attempts per hour measured |
| W4 | X3 tuning builds; local-pilot tok/s check under 8 threads | planted regression continues at higher σ_d; X3 decode guard and end-to-end A/A (all done in W4 if σ_d ≈ 2%) | held-out attempts |
| W5 | X1 local pilot (hours per Q18) | planted regression done at σ_d = 4%; X3 decode guard; end-to-end A/A | X1 analysis |
| W6 | — | end-to-end A/A (ends in W6 at σ_d = 4% with central A/A; to W8 in the bound case) | verdict scripts and dossier |

**Plan B night calendar** [G]. Same order. The pilot and profile run in W1 under D0-10d's chat answer
(W2 in revision 3, which the finish-week table above assumes). A W1 pilot moves a finish earlier only
if the X3-parity and X4-calibration fill-ins are also signed a sitting earlier [inference]; the table
is not re-derived here (plan track, `check.py`). Calibration nights run from W4, or from W3 if the
records are signed then. At 4 nights a week calibration ends in W5
(σ_d = 2%) or W10 (σ_d = 4%, central). At 7 nights a week it ends in W7 at σ_d = 4% [D, table above].
The ask is the same staged window: 4 pilot-week nights, then the rule's rate, at most 7. Under Plan B
the rule gives 4 nights a week up to σ_d = 3.5% (central A/A) or 2.5% (bound), and 5 nights at
σ_d = 4% central [D, rate table].

---

## 7. Owner-hour asks

ROADMAP's split by experiment [inference, ROADMAP §3]: D0 10, X0 10, X1 55, X2 40, X3 20, X4 40 and
CC 20, for 195 h in total [D: sum]. Weekly splits are [G]. The arithmetic is checked by
`scratchpad/plan/check.py` [D].

Two loads sit inside these hours rather than on top of them [G]:
- **Freeze and signature commits.** One weekly signing sitting (D0-12's chat answer, "Batch weekly
  review", pending ratification; revision 2 had two slots a week), on Sunday evenings. Signatures are
  batched into it; freeze commits are too, unless Pierce's authorisation of the lead engineer to
  commit and push Mithril work (OWNER-ANSWERS.md) covers freezes between sittings, which is OWNER-QUEUE
  A02's residual (Q6) (R26).
- **R-diff review reading** (§9). There are at most 23 reviews [D: 17 records + 6 verdicts] at about
  0.5 h each [G], so ≈ 11.5 h [D]. The hours come from the owning track's allocation, because
  ROADMAP counts pre-registration work in M0's ~195 h. Under D0_BRIEF Q17 = QWEN3_LOCAL_PROVISIONAL
  or FULL these are the local Qwen3's reviews (R-local, §9).

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
  - Read the D0 brief. At sitting 1 (Sun 10-18): D0-9a; ratify the chat answers (D0-10a, D0-10c,
    D0-10d, D0-12/12x/12i with the Sunday cadence, D0_BRIEF Q16); decide D0-10b's hours and D0_BRIEF
    Q17 and Q18; check the plan's terms and capacity (OWNER-QUEUE A20); then D0-7a and D0-8.
    (Revision 2 listed D0-11b and D0-9b here; the brief now puts them at M1 and X4.)
  - The sitting's slot is answered in chat (Sunday evenings).
  - Answer Q1–Q6, Q9 (needed before the X2-gate rules freeze) and Q17, and X0's OQ-1 to OQ-7 before
    its first compile.
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
  - Sign the X4 noise-pilot record (no instruction route under D0-12's chat answer), and answer
    D0-7a or Q1 for unattended nights.
  - CC: review sections.
- **W2 (33 h).**
  - Commit the rules freezes: X1-heldout, X2-gate, X3-parity, X4-calibration, X4-hacks-catalogue.
  - X1: review the suite (batch 1), the oracles, and the first reserve items (Q16).
  - X2: review table entries.
  - Review the catalogue batch.
  - Commit the kit hash-freeze, signed with D0-9a's key (D0_BRIEF: D0-9b is not needed for it).
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
   first. Under the chat answers, "a second family" means the X1 restructure and the local Qwen3's
   roles (D0_BRIEF Q16–Q18).
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
explicit Owner instruction. The Gatekeeper evaluates nothing until a record is SIGNED. **Revision 3:**
Pierce's chat answer to D0-12 ("Batch weekly review", pending ratification) narrows the instruction
route to X0 alone: collection under every other record waits for its signature at a weekly sitting.
Revision 2 marked X2-fuzz and X4-noise-pilot "an instruction suffices, pending D0-12"; both now need a
signature, and the m0/README rule should be narrowed to match once the answer is ratified (README is
not this track's file; OWNER-QUEUE lists the follow-up). "Sign" weeks below mean that week's sitting,
on its Sunday (§0). **Revision 4:** under D0-10d's chat answer the pilot nights fall in W1, so
X4-noise-pilot is signed at the W0 or W1 sitting and the X4-calibration rules freeze before the first
pilot night.
The record IDs below are proposals; the owning track names the file. "Rules by" is the rules freeze
of §0. Where it is "—", the record is frozen whole.

| Record | Gates this collection | Must be FROZEN before | Rules by (A / B) | SIGNED (or Owner instruction) before | Plan A: freeze / sign | Plan B: freeze / sign | D0 |
|---|---|---|---|---|---|---|---|
| [X0-census](prereg/X0-census.md) | compiling Hearth objects, decoding | the first Hearth object is compiled (TOOLCHAINS.md written first) | — | instruction given 2026-10-16, confirmed by D0-12's chat answer (the only instruction route; ratify); signature before the Gatekeeper verdict | W0 / W1 | W0 / W1 | D0-12, D0-9a; X0 OQ-1 to OQ-7 before the first compile. *Revision 5: FROZEN at `152fa33` (10-17); SIGNED in chat 10-23 with OQ-1 to OQ-7 deferred; the tag follows at sitting 2* |
| M0-verdict | the mapping from experiment verdicts to §4 rows | the first experiment verdict is known; not with §3.8's "pending Q7" lines open unless they stay as written | — | the same | W1 / W1 | W1 / W1 | D0-12, D0-1; Q7 |
| X1-card-iteration | card-iteration attempts (training items only; ≤ 3 epochs; the Rust arm on the same items if approved) | the first iteration attempt | — | the same | W2 / W3 | W5 / W6 | D0_BRIEF Q16–Q18, D0-12; Q16 |
| X1-precondition | `mithi` against hidden references, the planted corpus and CC's derivations; freezes `mithi`'s hash | the precondition run | — | the same | W3 / W3 | W8 / W9 | D0_BRIEF Q17/Q18 (corpus author), D0-12 |
| X1-heldout | the held-out runs (the kill) | rules: the first **card-iteration** attempt. Rules: analysis model (05 §13), exclusions, stopping, kit acceptance tests, the σ_ta estimator with its conservative choice and prior floor, n = max(60, n required by the power rule at that σ_ta) capped at n_max, the reserve's random-order seed, and what happens if a pinned model version is withdrawn mid-batch. Fill-in: σ_ta, n, the item hashes and the kit commit, before the first held-out attempt | W2 / W5 | the first held-out attempt | W2 → fill-in W4 / W4 | W5 → fill-in W10 / W10 | D0_BRIEF Q16 (one or two kill-carrying families; n recomputed for F = 1 under option 4b), D0-12 |
| X1-local-pilot | local-model pilot runs (reported, not part of the kill) | the first pilot attempt; machine hours from a measured tok/s run under 8 threads (Q18) | — | the same | W4 / W5 | W9 / W10 | D0-10c (local model: Qwen3 per chat answer; checkpoint open), D0-10d |
| X2-fuzz | vectors on silicon (Zen 5), Bochs comparison | the first vector. The iclass set is the FP-sensitive iclasses of `census.json@sha256:<hash>`, or the B_iform scope plus the census amendment rule (§3.3). Single-oracle iclasses are listed | — | the same, at a weekly sitting (no instruction route under D0-12's chat answer) | W1 (in the Sat 10-24 packet) / W1 (10-25) | W1 / W1 (10-25; otherwise W2, 11-01) | D0-12 |
| X2-mutants | the kill-rate measurement under G, G+C and T1+T2 | T1's rule list is frozen; the pool is hash-sealed first | — | the same | W3 / W3 | W7 / W7 | D0-12 |
| X2-gate | the verdict run of the frozen T1 on the real variants and the mutants | rules: before T1 runs on the real variants. Rules: what counts as a rule; per-kernel `assumed` axiom; the fixable-table-bug test; the week reading (Q9; Plan B or B-cal) | W2 / W2 | the verdict run | W2 / W5 | W2 / W10 (W6 under B-cal) | D0_BRIEF Q17 (Prover), D0-12; Q9 |
| X3-parity | A/B sessions | the first A/B session. It states N's and c's rules, the arms, the reference binary's hash (§3.4) and the counting rule. The counting rule is frozen before the first schedule line | counting rule W1 / W1; rest W2 / W3 | the first A/B session | W2 → fill-in W3 / W3 | W3 → fill-in W4 / W4 | D0-8 (provisional), D0-10d, D0-12; Q17 |
| X4-noise-pilot | quiet-night noise runs, descriptive only, never pooled into a calibration. States which σ_d estimate feeds §6.3's rate rule | the first quiet night | — | the same, at a weekly sitting (no instruction route under D0-12's chat answer) | W0 / W0 (10-18), or W1 / W1 (10-25) at the latest for W1 nights | same | D0-10d (chat answer: nights from W1), **D0-7a or Q1** (unattended). *Revision 5: D0-7a, C01, C02 and C25 answered 10-23. The record is still DRAFT [M, its status line, 10-23]; a chat signature counts as the interim form (batch 4)* |
| X4-calibration | A/A, planted-regression and end-to-end A/A sessions; `mithc profile measure`. Fixes c's and N's rules, the A/A stopping rule (§3.5) and the reference binary's hash | rules: the first noise-pilot night (W1 under D0-10d's chat answer). Fill-in: N and c from the pilot by the frozen rules | W1 / W1 (revision 3: W2) | the first calibration session | W2 → fill-in W3 / W3 | W2 → fill-in W4 / W4 | D0-7a, D0-8 (provisional), D0-10d, D0-12; Q15, Q17 |
| X4-hacks-catalogue | the gated run of the frozen kit against batch (a); each hack's declared stage. States that a gated miss is HALT-F | the catalogue engineering runs (so the hack list and stages are fixed before kit tuning) | — | the gated catalogue run, after the kit hash-freeze | W2 / W3 | W2 / W4 | D0-12 |
| X4-hacks-blind | running the frozen kit against batch (b) | the blind run; the kit is hash-frozen before the batch is written | — | the same | W3 / W4 | W4 / W6 | D0_BRIEF Q17 (Adversary: the local Qwen3, or batch (b) is never written), D0-12 |
| X4-forge-sim | F1-sim on sealed held-out traces; the MDE | the held-out traces are unsealed; traces hash-sealed in W1, before F1-sim development; MIN/OPT validated first | — | the same | W3 / W4 | W5 / W6 | D0-12 |
| X4-tombstone-replay | the replay acceptance tests (06 §7.6), with the irrelevant perturbations listed in advance | the first replay | — | the same | W3 / W4 | W5 / W7 | D0-12 |
| CC-gate | `mithi`'s acceptance of the canonical snippets; the Tier 0 trace | that acceptance check (aligned with X1-precondition) | — | signed at the gate | W3 / W5 | W8 / W11 | D0_BRIEF Q17 (reviewers), CC Q6, D0-12 |

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
| R-local (revision 3, provisional, pending D0_BRIEF Q17) | the local Qwen3 via Hearth, in a scripted session with the same frozen inputs and checklist; daytime only, inside the 8-thread cap | `different-family (local, non-frontier)` | the letter of ROADMAP's "different family" requirements if Pierce answers D0_BRIEF Q17 = QWEN3_LOCAL_PROVISIONAL or QWEN3_LOCAL_FULL (a new answer: D0-10c's option text named only the pilot). Under PROVISIONAL, a gate pass that rests on an R-local review is `pass_local_family` until a frontier family repeats it (§3.8); under FULL it counts outright. Each such review carries a trigger to repeat it with a frontier family when one exists |

Under D0-10c's chat answer no frontier R-diff will exist in M0. R-local is the only different-family
grade available, and only if Pierce accepts it. R-same reviews continue beside it.

**Where ROADMAP requires a different family** (these items stay open until an R-diff, or under
D0_BRIEF Q17 an R-local, exists; an R-same stand-in is logged as preparation, never as the requirement
met):
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
5. **R-diff backlog.** *Superseded under R1/R2 (the D0-10a and D0-10c chat answers): no family B will
   be provisioned in M0, so this step's metered and provisioning text does not apply; only the
   R-local sentence at its end does.* Once family B is provisioned, each SIGNED gate-bearing record and each computed
   verdict gets an R-diff review in the week after its signature. Records signed before family B
   existed are reviewed in the first two weeks after provisioning. All of them are done before the M0
   verdict is signed [G]. At most 23 reviews [D: 17 records in §8 + 6 verdicts]. The Owner's reading
   is about 0.5 h per review [G], ≈ 11.5 h [D], inside each track's hours (§7). Their metered cost is
   in family B's line ([COST §1.3](COST.md#13-measurement-budget-inside-the-api-lines)). ROADMAP asks
   for different-family review throughout; this plan defers it only because no second family exists
   yet. *Revision 3:* under D0-10c's chat answer this backlog becomes an R-local backlog if Pierce
   answers D0_BRIEF Q17 = QWEN3_LOCAL_PROVISIONAL or FULL. Its cost is daytime desktop hours under
   the 8-thread cap, not metered dollars; it depends on Qwen3's tok/s under 8 threads (Q18), and a
   bounded placeholder is ≈ 1–12 daytime hours [D from G, COST §1.6]. If he answers UNMET, the
   backlog stays open and every review log keeps the same-family label.

**Separation of roles** [G]: a Builder never reviews its own track's records. The Gatekeeper scripts
are written by one agent and re-derived by another. No agent edits a sealed artifact after its hash is
committed.

---

## 10. Risk register

Likelihood (L) and impact (I) are [G]: H, M or L.

| # | Risk | L | I | Early signal | Mitigation |
|---|---|---|---|---|---|
| R1 | D0-10 slips, so there is no budget, no second family and no nights | M | H | C0 missed | D0 brief first; everything that needs no data proceeds; slip X1 one-for-one and say so. *Revisions 3 and 4:* D0-10a, D0-10c and D0-10d are answered in chat (ratify at sitting 1, Sun 10-18); D0-10b's hours remain the slip risk |
| R2 | A second model family cannot be provisioned (access, terms, cost) | **materialised** (revision 3) | H | the chat answers of 2026-10-16: no metered API, no family besides Claude except the local Qwen3 | the X1 restructure (X1 record; D0_BRIEF Q16–Q18); R-local reviews under D0_BRIEF Q17; R-same stand-ins clearly labelled; X1's kill as ROADMAP defines it cannot run (ROADMAP §1 rule 5) |
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
| R16 | API overrun (≈ 4.1k attempts at n = 60, $0.5–2 each [inference, ROADMAP §10], plus family B's metered authoring) | L (revision 3: no metered API under D0-10a's chat answer) | M | any metered charge at all | stop-loss in [COST.md §5](COST.md#5-alerts-and-stop-loss): under the answer, any metered spend stops the work and goes to Pierce; the overrun risk moves to R17 |
| R17 | The Claude Code subscription's 5-hour or weekly limit throttles the agent team, and under the chat answers also X1's Claude participant attempts | H | **H** (revision 3; was M) | Account-wide 5-hour usage rose 3% → 8% → 16% at 18:17Z, 18:29Z and 18:45Z; the weekly window rose 10% → 11% → 13% [M, plan]. Extrapolated, the 5-hour window runs out about 1.2 h before its 23:00Z reset [D, COST row 3]. This is a start-up burst, not a rate. Workflow 1 used 10,248,932 subagent tokens [M, workflow report]; X1's Claude attempts are estimated at ≈ 0.73–2.63 billion tokens at n = 96 [D from inference, X1 record], ≈ 71–256 times that | pace by `get_usage` readings (≥ 4 per work block) logged in COST.md; stagger the tracks; the Owner decides on extra usage (disabled [M, plan]); measure tokens and window share per attempt in the X1 smoke run before any X1 record freezes (R29) |
| R18 | Supply chain: downloaded toolchains (LLVM, XED, Bochs) | L | M | signature or attestation failure | verify signatures or attestations; pin and hash every archive in TOOLCHAINS.md |
| R19 | X3's parity verdict rests on an incomplete planted-regression calibration | M (H at σ_d ≥ 3.5% and < 7 nights/week [D, §6.3]) | M | X3 A/B finishes before the calibration | X3-parity makes its verdict final only after the calibration (§3.4); the §6.3 rate rule, which asks for up to 7 nights a week when σ_d is high (revision 3: staged window); Q8 |
| R20 | Holiday weeks (2026-11-26, 2026-12-25, 2027-01-01) in Plan B | M | L | Owner calendar | Q11; re-plan at the checkpoint |
| R21 | Signature form before D0-9 is challenged later | L | M | — | D0-9a's interim form (D0_BRIEF), re-signed with the D0-9b key once it exists (Q6) |
| R22 | Quiet-profile settings left unapplied (power plan, Defender, indexing) | M | M | void rate in the noise pilot | Pierce applies the settings he chooses before the pilot; the service detects and voids and never changes them (06 §6.7) |
| R23 | Toolchain availability. Bochs may not emulate every census iclass (AVX-512 VNNI and other forms; not verified here), leaving one oracle for those iclasses. clang-cl for X3's Clang arm exists only if X0's portable LLVM install succeeds. Exo and its Python dependencies are unverified. Rust, rust-analyzer and a C compiler on the laptop (none today [M, brief]) are uninstalled | M | M | a census iclass without Bochs support; TOOLCHAINS.md has no clang-cl; Q4 unanswered by C0 | X2-fuzz lists single-oracle iclasses; the laptop Zen 4 cross-check runs as a secondary arm that cannot change a verdict; X3 falls back to the Python generator if Exo fails; Q4 in W0 |
| R24 | (revision 4) Claude Code throughput: the plan's account-wide 5-hour and weekly windows, outages, or a change of the Claude model in Claude Code mid-batch. Revision 3's provider text (API rate limits, a pinned provider version) no longer applies under the D0-10a chat answer. At n = 96, one family's 2,016 held-out attempts × 5–10 min = 168–336 attempt-hours [D; per-attempt time is ROADMAP §3.2's local-model figure, Claude Code latency not measured] | M | H | runner attempts per window, measured in the smoke run (W1) and in card iteration, project held-out completion past W11 (Plan B) | R29's mitigation: measure before freezing, pace attempts over windows; the record pins the model ID per session and states, before data, what happens if the Claude model changes mid-batch |
| R25 | Laptop uptime as harness host: sleep, Windows Update reboots, other benchmarks | M | M | interrupted attempts in card iteration | resumable harness (attempt-level checkpoints); an interrupted attempt is an infrastructure failure, re-run under 05 §13's exclusion rule; power plan and update hours are Pierce's settings |
| R26 | Commit bottleneck: no track agent commits, so every freeze, fill-in and landing waits on Pierce or an authorised session, and that time is not in the owner-hour tables | H | M | a frozen-ready record waits > 3 days for a commit; under the weekly sitting, any record ready just after a sitting waits ≈ 7 days | one weekly signing sitting on Sunday evenings (D0-12's chat answers), with signatures batched into it (§7); the lead engineer is authorised to commit and push Mithril work (OWNER-ANSWERS.md), and OWNER-QUEUE A02 asks whether that covers freeze commits between sittings, so that only signatures wait |
| R27 | X0 slips past W1, so X2's table scope and fuzz set slip | M | M | TOOLCHAINS.md not written by the end of W0 | X2 works on the B_iform scope; X2-fuzz's census amendment rule (§3.3); X2's verdict week does not move (Q9) |
| R28 | Aggregate desktop threads exceed the 8-thread cap, or a desktop job starts inside a quiet window (for example over SSH from the laptop) | M | H | wrapper not live by W1; the wrapper log shows > 8 tokens or a start inside a window | job wrapper (§3.5, §6.1); ad hoc multi-thread SSH jobs not allowed; a job inside a window voids that night's sessions (06 §6.8) |
| R29 | (revision 3) The Claude Code plan cannot carry X1's participant attempts in the weeks planned: unknown token-to-window conversion, plan terms for harness-driven use not verified, an unpinnable sampling setup, and (revision 4) X1 displacing the agent team and Pierce's other Claude use from the account-wide windows for about six weeks [inference] | M | H | the X1 smoke run's tokens or window share per attempt project the held-out run past W11 (Plan B) | Pierce checks the plan's terms and accepts the capacity cost before ratifying the X1 rule (OWNER-QUEUE A20; agents do not interpret the terms); measure before freezing (X1 smoke run, W1); pace attempts over windows; fall back to fewer secondary-arm attempts before touching any kill-carrying cell; if still infeasible, a signed amendment before collection (ROADMAP §1 rule 1), never after |
| R30 | (revision 3) The local Qwen3's daytime jobs (templates, planted corpus, reviews, Prover and Adversary roles, pilot) crowd X2 fuzzing, X3 builds and X0 re-runs under the shared 8-thread cap, or run far slower than the 5–10 min per attempt and 13–22 tok/s planning figures | M | M | Qwen3 tok/s under 8 threads (Q18) below the planning figures; wrapper queue times rising | measure tok/s in W1; agree a token share for Qwen3 with Pierce (Q18); schedule Qwen3 jobs around the X2 fuzz weeks; never in a quiet window (DR-023) |
| R31 | (revision 3) DR-017's binding test never runs: no second frontier family is ever provisioned, so an X1 pass stays provisional (X1 record, option 4b) and M1's DR-017 kill cannot be evaluated either | M | H | no change to D0-10a or D0-10c by M1's start | keep the gap visible: the M0 verdict carries X1 as `pass_one_family`, and a tombstone with trigger `harness.frontier_families >= 2` records it; the X1 record prices the cheapest repair (one frontier family's attempts alone, ≈ $1.4–5.7k at n = 96 [D]) for Pierce to weigh, without recommending it against his answer |

---

## 11. Rejected plan options (tombstones)

These options were considered and rejected while writing this plan. They are written in the
[DECISIONS §4](../DECISIONS.md#4-design-tombstones) format, with triggers in the 06 §7.2 grammar. They
are **proposals** for DECISIONS.md: admitting them is an AUTHORITY operation that needs the Owner
(DECISIONS §1). The first four were buried on 2026-10-16 in the first version, and the last three in
revision 2 the same day. Revision 3 added none and changed two survivor comments
(`m0_same_family_review_as_cross_family`, `m0_fixed_four_night_ask`); no scope, class or trigger
changed. The X1 restructure's tombstones (for example option 4a, and the standing DR-017 gap) belong in
the X1 record once Pierce chooses. Fact names not yet recorded in any ledger evaluate to `unknown` and
never fire (06 §7.2).

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
    // survivor: R-same reviews, labelled as such; the different-family item stays open until a different family reviews (R-local under D0_BRIEF Q17, or a frontier family later)
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
    // survivor (revision 3): the staged window of D0_BRIEF D0-10d: 4 pilot-week nights, then the post-pilot rate rule of §6.3, at most 7 nights/week
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
| S02 | D0-10a–d signed (budget, cadence, families, windows) | Owner | a, c, d and b's signing slots ratified in chat 10-23 (interim); tags at sitting 2 (10-25). b's hours blocked: Owner. c's Value (the Qwen3 checkpoint): proposed operating assumption Qwen3-30B-A3B Q4 (DELEGATED P4) | W0 / W0 | cadence, nights | [D0_BRIEF §0](../D0_BRIEF.md) | 10-23 |
| S03 | D0-11b signed (role split) | Owner | not due: M1 (D0_BRIEF Q1); revision 2 had W0 | M1 / M1 | sealed specs at M1 | — | 10-16 |
| S04 | D0-12 signed | Owner | ratified in chat 10-23 (interim); the tag at sitting 2 | W0 / W0 | every Gatekeeper verdict; every collection except X0's | [D0_BRIEF §0](../D0_BRIEF.md) | 10-23 |
| S05 | D0-9a signature form | Owner | interim form chosen 10-23: chat signatures until the key exists ("Chat now, key on Sunday"); D0-9a (an SSH key) at sitting 2, Sun 10-25 | sitting 2 (10-25) | the tags that turn the chat signatures into AUTHORITY facts | [SIGNATURES](sittings/2026-10-23-chat/SIGNATURES.md) | 10-23 |
| S06 | D0-7a (or Q1 consent) for unattended nights | Owner | done: answered in chat 10-23 ("measurement may run unattended inside windows, with no agents running then"); ratified (interim) | W1 / W1 | noise pilot, X3 A/B, calibration | [OWNER-ANSWERS](OWNER-ANSWERS.md) batch 3 | 10-23 |
| S07 | D0-9b Owner key | Owner | blocked: Owner; per D0_BRIEF no M0 step blocks on it if D0-9a's tags are accepted for the kit freeze | X4 / X4 | ledger AUTHORITY facts (M3) | — | 10-16 |
| S08 | Q1–Q6, Q9, Q17 answered | Owner | Q1's unattended part, Q2's window part, and Q3 answered 10-23; Q4, Q6 and Q17 proposed for delegation (DELEGATED P5, P1, P20); Q5 and Q9 blocked: Owner (§13, revision 5) | W0 / W0 | toolchains, store, windows, X2-gate rules, reference binary | §13 | 10-23 |
| S09 | Weekly signing sitting's slot set (revision 2: two slots) | Owner | done: Sunday evenings (10-16), ratified in chat 10-23. Sitting 1 (10-18) did not take place; sitting 2 is Sun 10-25 | W0 / W0 | every freeze and signature (R26) | [OWNER-ANSWERS.md](OWNER-ANSWERS.md) | 10-23 |
| S10 | Quiet windows agreed (staged: 4 pilot nights, then the rule; times; GEMS paused) | Owner | answered in chat 10-16: 23:00–07:00 PT, 4 pilot nights from W1, then a re-signed rule of 4–7 nights a week, GEMS kept out; ratified in chat 10-23 (interim). The rule's form and its 25% contingency are proposed (DELEGATED P7); the post-pilot rate is Pierce's re-signature | W0 / W0 | all quiet nights | [OWNER-ANSWERS.md](OWNER-ANSWERS.md) | 10-23 |
| S11 | Hygiene settings applied by Pierce | Owner | blocked: Owner (checklist from X4) | W1 / W1 | a valid noise pilot | — | 10-16 |
| S12 | Second family provisioned (keys, pinned versions) | Owner | **will not happen in M0** (chat answers 10-16): no frontier family B; the local Qwen3 is the only other family. Replaced by S69 and S71 | — | — | [D0_BRIEF §0](../D0_BRIEF.md) | 10-16 |
| S13 | Desktop job wrapper (8 tokens, window refusal, stamps) | X4 | todo | W1 / W1 | all multi-thread desktop jobs from W1 | — | 10-16 |
| S14 | X0 record | X0 | frozen@`152fa33` (10-17) [M, record status line, `git log`]; signed@2026-10-23 (interim chat, OQ-1 to OQ-7 deferred; the tag at sitting 2). Census run 1's computed outcome is `tooling_failure` (V3), unsigned, until the X0-A1 fix and re-run, bounded at 11-12 (SIGNATURES; PACKET item 5). The X0 track updates S17 | freeze W0, sign W1 / same | X0 compiles; X0 verdict | [X0-census](prereg/X0-census.md) | 10-23 |
| S15 | X0 toolchains (LLVM, XED) and TOOLCHAINS.md | X0 | doing [M, brief]; TOOLCHAINS.md absent at 11:40 PT [M, plan]; present at 14:38 PT, tools listed as working [M, owner track] | W0 / W0 | X0 compiles | [TOOLCHAINS.md](../../experiments/x0-census/TOOLCHAINS.md) | 10-16 |
| S16 | X0 scripts | X0 | doing: `judge.py` with 56 unit tests, reworked extract and decode, regression on 24 non-Hearth objects with 0 deviations; no Hearth source compiled or decoded; `census.json` assembler not written [commit `6fa2931` message, as reported by x0prep] | W0 / W0 | — | `experiments/x0-census/scripts/` | 10-16 |
| S17 | X0 `census.json`, REPORT.md, re-derivation | X0 | blocked: S14 freeze, S15 | W1 / W1 | X0 verdict | — | 10-16 |
| S18 | Census handoff (hash + FP-sensitivity classification) | X0 → X2 | blocked: S17 | W1 / W1 | X2 fuzz vectors, table scope | — | 10-16 |
| S19 | M0-verdict record and mapping script | verdict | blocked: Q7 (or "pending Q7" lines as written) | W1 / W1 | mapping verdicts to §4 rows | §3.8 | 10-16 |
| S20 | Lark grammar v0 | X1 | draft (commit `dcd4c87`, not frozen): parses every snippet; 150/150 mutants agree with `mithi`'s parse [commit message, as reported by the X1 build track] | W1 / W2 | cards | `experiments/x1-harness/` | 10-16 |
| S21 | Tier 0 and Tier 1 cards | X1 | todo | W1 / W3 | card iteration | — | 10-16 |
| S22 | `mithi` | X1 | draft v0 (commit `dcd4c87`, not frozen; Rust toolchain installed, OWNER-QUEUE A07 to confirm): agrees with the core-calculus note's hand verdicts on 35/35 canonical and derived snippets, 6/6 gate negatives and 33/33 supplementary items, not blind (same family, verdicts visible); 39 tests pass; revised after two reviews (39 findings, 9 blockers) [commit message] | W2 / W5 | precondition | `crates/mithi/` | 10-16 |
| S23 | M0 tooling kit | X1 | blocked: Q4 | W3 / W9 | tooling arm | — | 10-16 |
| S24 | X1 harness (six arms, sandbox, resumable) | X1 | todo | W2 / W5 | all X1 attempts | `experiments/x1-harness/` | 10-16 |
| S25 | X1 power simulation | X1 | draft; F = 1 blocks 14–19 added and run (packet track, 10-16 evening): planned n_final 136 with one kill-carrying family, against 96 with two [S]; blocks 1, 12 and 13 re-run and reproduced [M] | W2 / W5 | X1-heldout n rule | `experiments/x1-harness/power/` | 10-16 |
| S26 | X1-card-iteration record (+ Rust arm if approved) | X1 | todo | W2 → W3 / W5 → W6 | card-iteration attempts | — | 10-16 |
| S27 | X1-heldout rules freeze, then fill-in | X1 | todo | W2 → W4 / W5 → W10 | held-out runs | — | 10-16 |
| S28 | X1-precondition record | X1 | todo | W3 / W9 | precondition run | — | 10-16 |
| S29 | X1-local-pilot record (tok/s under 8 threads first) | X1 | blocked: D0-10c checkpoint (Qwen3 per chat answer), Q18 | W4 → W5 / W9 → W10 | pilot runs | — | 10-16 |
| S30 | Card-iteration items (~20) | X1 | blocked: D0_BRIEF Q16–Q18 (author), Q5 | W2 / W5 | card iteration | — | 10-16 |
| S31 | Held-out ≥ 60 + reserve to n_max, oracles ≥ 95% mutant kill | X1 | blocked: D0_BRIEF Q16–Q18, Q5, Q16 | W3 / W9 | held-out runs | — | 10-16 |
| S32 | Planted Dc corpus ≥ 100 | X1 | blocked: D0_BRIEF Q17/Q18 (corpus author) | W2 / W8 | precondition | — | 10-16 |
| S33 | Card iteration done (≤ 3 epochs); attempts per hour measured | X1 | blocked: S26, S30 | W3 / W7 | σ_ta; held-out concurrency | — | 10-16 |
| S34 | `mithi` precondition passed | X1 | blocked: S28, S32, S61 | W3 / W9 | held-out runs | — | 10-16 |
| S35 | Held-out runs and Gatekeeper analysis | X1 | blocked: S27, S34 | W5 / W11 | X1 verdict | — | 10-16 |
| S36 | Local pilot | X1 | blocked: S29 | W5 / W10 | (reported only) | — | 10-16 |
| S37 | Semantics table | X2 | doing [M, plan: files present] | W5 / W9 | T1 | `experiments/x2-semantics/semantics/` | 10-16 |
| S38 | X2-fuzz record; Zen 5 fuzz and Bochs | X2 | harness built and self-tested (commit `cce9911`): 491 XED-encoded stubs over 88 entries; exact-integer C reference, 10^6 lane cases, 0 divergences against Python; Bochs 3.1 oracle; the dev smoke found one table error (DIVSS-class flags). No pre-registered fuzz budget run [commit message]. Record: blocked: S18 (or amendment rule) | W1 / W1 | vectors on silicon | `experiments/x2-semantics/harness/` | 10-16 |
| S39 | `numerics_v1` ≥ 200 sealed; X2-mutants record | X2 | blocked: Q5 (store) | W2 → W3 / W6 → W7 | kill-rate measurement | — | 10-16 |
| S40 | X2-gate rules freeze; record signed | X2 | blocked: Q9 | W2 → W5 / W2 → W10 | X2 verdict run | — | 10-16 |
| S41 | `mithcheck` T1/T2 spike and rule proofs | X2 | doing: rule proofs started (commit `cce9911`), 23 rule queries proved in both Z3 and cvc5; R02 and R03 not yet proved [commit message]; the T1/T2 spike is todo | W4 / W9 | X2 verdict | `experiments/x2-semantics/proofs/` | 10-16 |
| S42 | Lockstep proof, different-family Prover (R-local under D0_BRIEF Q17) | X2 | blocked: S17; D0_BRIEF Q17 | W4 / W8 | X2 verdict, X0 narrowing | — | 10-16 |
| S43 | X2 report and verdict | X2 | todo | W6 / W11 (W6 under B-cal) | M0 verdict | — | 10-16 |
| S44 | X3-parity: counting rule, rules, fill-in | X3 | todo | W1, W2 → W3 / W1, W3 → W4 | A/B sessions | — | 10-16 |
| S45 | Reference binary (clean `b5d3f14`; MSVC and clang-cl; hashed) | X3 | blocked: Q17 | W2 / W3 | X3 A/B, planted regression | — | 10-16 |
| S46 | Generator and scratch Hearth | X3 | todo (from W1) | W2 / W4 | A/B | — | 10-16 |
| S47 | X3 A/B nights | X3 | blocked: S10, S06, Q2, S44 | W3 / W4 | X3 verdict | — | 10-16 |
| S48 | X3 report (final after planted regression) | X3 | todo | W5 / W7 | M0 verdict | — | 10-16 |
| S49 | Measurement service v0 | X4 | doing, not usable yet (commit `93f67a8`, "inconsistent state"): the C harness and Rust orchestrator were built and unit-tested on the desktop; two reviews found 26 issues, 3 of them blockers; the C side is on protocol v2 and the orchestrator still on v1, so every orchestrated run fails closed [commit message] | W1 / W1 | every quiet-night run; the first pilot night | `experiments/x4-integrity/service/` | 10-16 |
| S50 | Sandbox (Job Object) | X4 | doing (commit `93f67a8`): sandbox and probes in progress, same state as S49 [commit message] | W2 / W3 | hacks; X1 harness isolation | `experiments/x4-integrity/sandbox/` | 10-16 |
| S51 | X4-noise-pilot record; pilot nights; σ_d published | X4 | blocked: S06, S11; the record split out of the X4 DRAFT and frozen (signed 10-18, or 10-25 at the latest for W1 nights). *Revision 5 (owner side only): S06 done; C01, C02 and C25 answered 10-23; the record is DRAFT [M, its status line, 10-23]; S11 still blocked: Owner* | W1 / W1 | N and c; night rate | — | 10-23 |
| S52 | `mithc profile measure` (one quiet night) | X4 | blocked: Q2, Q3, S10 | W2 / W2 | phys/emp bounds | — | 10-16 |
| S53 | X4-calibration rules, fill-in, sessions; time-to-pass, σ_d, throughput published | X4 | blocked: S06, S10, S04, Q15 | W2 → W3, nights W3–W6 / W2 → W4, nights W4–W10 | X3 finality; X4 verdict | — | 10-16 |
| S54 | X4-hacks-catalogue record; dev runs; kit hash-freeze; gated run | X4 | blocked: S05 (the freeze is signed with D0-9a's key; D0_BRIEF no longer needs D0-9b for it) | W2 → W3 / W2 → W4 | blind batch; X4 verdict | — | 10-16 |
| S55 | Blind batch (local Qwen3 under D0_BRIEF Q17) and blind run | X4 | blocked: D0_BRIEF Q17, S54 | W4 / W6 | X4 verdict | — | 10-16 |
| S56 | MIN/OPT oracle and F1-sim; held-out traces sealed | X4 | todo (laptop after 19:00 PT on 10-16) | traces W1; sim W4 / W1; W6 | X4-forge-sim | — | 10-16 |
| S57 | Tombstone import, revisit prototype, replay tests | X4 | todo | W4 / W7 | X4 verdict | — | 10-16 |
| S58 | Prune pilot reproduced | X4 | todo | W4 / W7 | X4 verdict | — | 10-16 |
| S59 | X4 report | X4 | todo | W6 / W11 | M0 verdict (may wait) | — | 10-16 |
| S60 | Core-calculus note | CC | doing: round 2 landed (commit `5e16fbb`); a second same-family Prover and Adversary review found 32 defects (11 blockers), all fixed as F-60..F-88 (provisional); supplementary counterexamples N-11..N-69 [commit message] | W3 / W8 | CC gate | [core-calculus.md](core-calculus.md) | 10-16 |
| S61 | CC X1-subset rules frozen | CC | todo | W3 / W9 | `mithi` precondition | — | 10-16 |
| S62 | CC-gate record; different-family review; signature | CC | blocked: D0_BRIEF Q17; CC Q6 | W5 / W11 | M0 verdict | — | 10-16 |
| S63 | Different-family review backlog (§9 step 5; R-local under D0_BRIEF Q17) | reviewers | blocked: D0_BRIEF Q17 | week after each signature | M0 verdict signature | — | 10-16 |
| S64 | PLAN.md | plan | draft (revision 4, owner track, after one same-family review) | living | — | this file | 10-16 |
| S65 | COST.md | plan | draft (revision 4, owner track, after one same-family review) | living | stop-loss (§5) | [COST.md](COST.md) | 10-16 |
| S66 | S0: R3 commit, ADR-0010, port base, corpus | Hearth / Owner | blocked: R3 commit, D0-2, D0-3 | not an M0 gate | M1's S1 | — | 10-16 |
| S67 | M0 verdict signed | Owner | blocked: S14–S63, S69 | W6 / W12 | M0 outcome | — | 10-16 |
| S68 | Owner queue (`OWNER-QUEUE.md`) | owner | revised 2026-10-23 by the queue track (not reviewed): batches 3 and 4 carried; all 116 entries classified (A 16, B 41, C 59, after one same-family review); sitting-2 list | living | the weekly sittings' agendas | [OWNER-QUEUE.md](OWNER-QUEUE.md) | 10-23 |
| S69 | X1 restructure chosen (D0_BRIEF Q16–Q18) and folded into the X1 record | Owner, then X1 | *Revision 5: X1-amendment-1 frozen@`ac751b8`, signed@2026-10-23 (interim chat: `claude-opus-5-5`, effort `max`, s = 50%, cap 160, K = 6); A20 answered; Q17 and Q18 at sitting 2 (not delegable; recommendations: DELEGATED P3, P2).* Earlier status, 10-16: Q16 answered in chat 10-16; X1-amendment-1 drafted (packet track, 10-16 evening) and revised after one same-family review (11 findings across the packet's files, all accepted): F = 1, planned n 136 [S], a Claude Code runner with a signed effort level, pacing, and a sequential plan-capacity feasibility gate, because the estimate is ≈ 13–55 weekly windows [D, rough]; no recommendation on Q18. Q17, Q18 and OWNER-QUEUE A20 blocked: Owner; A20 comes before Q16's ratification and before the smoke run; the packet leaves Q17 and Q18 until after the smoke run | W0 / W0–W1 | all X1 sealed content and attempts | [X1-amendment-1](prereg/X1-amendment-1.md) | 10-16 |
| S70 | Claude Code runner smoke run on public items (tokens and window share per attempt [M]) | X1 | *Revision 5: A20 answered and effort pinned at `max` (10-23); it waits for the runner and a time Pierce agrees, with the account idle.* todo; development, not collection. Waits for A20 (Owner) and the pinned effort level; runs on a quiet account (agent team paused) as X1-amendment-1 §6.2's sequential gate: 5 attempts, then batches of 20 up to 65, at most ≈ 10 points of one weekly window [D] | W1 / W1 | sizing X1 under the plan (R29) | [X1-amendment-1 §6.2](prereg/X1-amendment-1.md) | 10-16 |
| S71 | Local Qwen3 serving on the desktop: checkpoint located, tok/s under 8 threads measured (daytime), tool-call support checked | X1 / Owner | *Revision 5: Q3 answered (C02, 10-23); checkpoint proposed (DELEGATED P4); until Pierce signs a weekly Qwen3 cap, all Qwen3 jobs stay within R2's 5–10 desktop hours (P13); the desktop is busy with another workflow on 10-23.* Earlier: blocked: D0-10c checkpoint, Q3, Q18 | W1 / W1 | every Qwen3 job; X1-local-pilot | — | 10-16 |
| S72 | Sitting-1 packet (agenda, signing mechanics) | packet | draft (packet track, 10-16 evening), revised after one same-family review: agenda ≈ 105–135 min with the key made before Sunday and two records signed on their summaries, up to ≈ 210 min otherwise [inference]; item 6 optional; item 7's checklist now follows the X4 track's draft X4-noise-pilot §11; three freeze-hash placeholders for the lead engineer to fill by Sat 10-17 night. *Revision 5: marked FINAL 10-17 (`a3add8b`); sitting 1 did not take place, and its items were signed in chat 10-23 or moved to sitting 2* | W0 / W0 | sitting 1 (Sun 10-18) | [PACKET](sittings/2026-10-18/PACKET.md) | 10-23 |
| S73 | Delegation log (`DELEGATED.md`) | lead engineer | scope and limits committed (`3a66d49`); 62 rows drafted by the queue track 10-23 and revised after one same-family review: 59 marked "PROPOSED, pending lead engineer" and 3 (P2, P3, P23) "Not delegable", recommendations only; none adopted | living | the C items of OWNER-QUEUE | [DELEGATED.md](DELEGATED.md) | 10-23 |
| S74 | Sitting-2 packet (Sun 10-25): the key, re-signing by tag, the signed Q17 and Q18 lines, the records FROZEN by then | lead engineer / packet | todo; due Sat 10-24, night (R6). OWNER-QUEUE's sitting-2 list is its input | W1 | every AUTHORITY fact of M0 so far | [OWNER-QUEUE](OWNER-QUEUE.md#sitting-2-sun-2026-10-25-what-only-pierce-can-do-class-b) | 10-23 |

**Checkpoint review.** At each checkpoint (§5.1 or §5.2), the plan track:
- compares the status table with the checkpoint row;
- re-plans the slipped items;
- updates the risk register's signals;
- records the Owner's actual hours from COST.md against §7.

---

## 13. Owner questions

**Revision 5 (2026-10-23): status of each question.** Classes follow
[OWNER-QUEUE](OWNER-QUEUE.md#classification-of-every-open-item-2026-10-23): A answered by Pierce; B only Pierce;
C delegable, with a proposed row in [DELEGATED.md](DELEGATED.md) (none adopted).
- **Answered (A):**
  - Q1: nights (R5) and the unattended part (D0-7a, batch 3);
  - Q2: the window part, "the 8-thread cap lifts only inside 23:00–07:00 windows"; the aggregate reading
    outside windows is the sprint rule;
  - Q3: "the real Qwen3-30B-A3B Q4 file on the NVMe, read-only, never the USB disk";
  - Q8: C25, provisional until X4's calibration, which runs on `x3_bench`;
  - Q10: the Claude model `claude-opus-5-5`, effort `max`, runner accepted (batch 4);
  - Q19, Q21: as noted at each;
  - Q16: option (c), the 24-item calibration set, through the signed X1-amendment-1 (OWNER-QUEUE D01).
- **Delegable (C):**
  - Q4: P5 (Rust confirmed at user level, PATH unchanged [M, 10-23]);
  - Q6: P1 (freeze commits between sittings);
  - Q7: P8, with one added line for X2's `gate_missed` (P28);
  - Q10's checkpoint: P4;
  - Q12: P7;
  - Q13: P15;
  - Q15: P21, for the stopping rule (to N);
  - Q17: P20;
  - Q18: P13, for the interim bound (no cap exception; R2's 5–10 desktop hours until a signed cap);
  - Q20: P26.
- **Pierce only (B):**
  - Q5, the store (OWNER-QUEUE A06);
  - Q9 and Q14 ("end of week 6", OWNER-QUEUE C04);
  - Q11 (D0-10b's hours);
  - Q15's ROADMAP §10 part, and the microbenchmark A/A 2N horizon (+13.3 h / +48.9 h [D, X4 Q9]);
  - Q18's weekly Qwen3 cap;
  - Q16's review role (OWNER-QUEUE C38).

None of these is decided. Each item proposes something and names the decision it rests on.
*Revision 3:* Q10, Q19 and Q21 are answered or made moot by the chat answers of 2026-10-16 (noted at
each, pending ratification). Q2's aggregate reading is stated as a rule in the sprint brief; its
quiet-window half stays open. Every question here, with those from D0_BRIEF, the records and the
designs, is consolidated, deduplicated and ranked by the date it blocks in
[OWNER-QUEUE.md](OWNER-QUEUE.md).

1. **Quiet windows (D0-10d).** Which nights, at what times, and how many per week? The proposal
   matches D0_BRIEF D0-10d's staged window (revision 3; revision 2 asked for 7 nights a week from W2):
   4 nights of 8 h in the pilot week, then the rate the rule in §6.3 gives from the measured σ_d, at
   most 7, re-signed. At 4 nights a week and σ_d = 4%, X3 lands in W7 and X4's calibration in W9
   [D, §6.3], which is why the rule may ask for more. Inside a window, are other projects' jobs and the RTX 5070 queue idle? Are unattended
   Mithril runs allowed in those windows? D0-7a covers this. The noise pilot is the first
   unattended night, and X3's A/B is not the Forge. *Revision 4: answered in chat 2026-10-16, pending
   ratification (OWNER-ANSWERS.md, D0-10d): 23:00–07:00 PT, 4 pilot nights from W1, then a re-signed
   rule of 4–7 nights a week; Pierce keeps GEMS jobs out of those hours. Still open: the unattended
   part (D0-7a) and the rule's contingency (Q12).*
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
   the virtual disk on C:, or must they go to D:? *Revision 4: Rust was installed by rustup on
   2026-10-16; the lead engineer reads Pierce's "ultra code mode" instruction as operational
   permission covering installs (OWNER-ANSWERS.md). Residual: confirm the install, and whether LLVM and
   a C compiler may follow (OWNER-QUEUE A07).*
5. **Gatekeeper store.** Where do the sealed suites, the reserve, reference solutions, oracles and the
   mutant pool live? The proposal is outside every repository, encrypted, with a key the Builder
   sessions do not hold. Who holds the key? Is the Mithril repository public?
6. **Signature form before D0-9.** D0_BRIEF D0-9a recommends a signed git tag over each freeze commit,
   made with Pierce's own key. This plan follows whatever D0-9a says and keeps its first version's
   fallback (Pierce commits the signature block himself, naming the freeze commit) only if D0-9a is
   declined. Who makes freeze commits in this sprint, and in which weekly slots? *Revision 4: the
   slot is answered in chat (Sunday evenings); the lead engineer is authorised to commit and push
   Mithril work (OWNER-ANSWERS.md). Residual: does that cover freeze commits between sittings
   (OWNER-QUEUE A02)?*
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
    Which local model for the pilot? Is there a weekly cap on metered spend? *Answered in chat
    2026-10-16, pending ratification: no metered API; Claude through the Claude Code plan; the local
    model is Qwen3 via Hearth. Still open: the Qwen3 checkpoint, and which Claude model the X1
    runner pins (OWNER-QUEUE).*
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
    - (a) add a Rust arm on the ~20 card-iteration items: 100 Claude attempts at one kill-carrying
      family, 200 at two, on the plan's tokens ($0.1–0.4k at two families is an API-price estimate,
      not a budget) [D];
    - (b) pre-register a conservative prior floor for σ_ta, proposed by the X1 track.

    Also:
    - Approve a sealed reserve up to n_max (example 120 [G]), authored in W2–W3.
    - Pierce either reviews all n_max items up front, which costs hours not in ROADMAP's 55, or
      reviews the first 60 up front and the rest in W4 only if the n rule draws them, which delays
      the held-out start by that review time.

    *ROADMAP observation, no change made:* §10's card-iteration row and 05 §13's recompute rule do
    not fit together.

    *Revision 3:* the X1 record (§6.3, its Owner question 18) adds option (c), a dedicated 24-item
    calibration set run after the card freeze (480 attempts at two families; 240 at one), and argues
    that iteration items cannot serve. OWNER-QUEUE merges (a), (b) and (c) into one question, with
    (c) as the default. Under D0-10a's chat answer the dollar figures become plan tokens.
17. **Reference binary.** May M0 measure a clean checkout of `b5d3f14`, built with Hearth's release
    flags (MSVC, and clang-cl for the proxy arm), as the stand-in for `hearth-c-ref`? Its hash would
    be pinned in X3-parity and X4-calibration. The S0 tag would then not be a prerequisite (§3.4).
    Where should the clean checkout and its build live: D:, or inside the C: budget?
18. **X1 local pilot under the cap.** Either grant a daytime exception to the 8-thread cap for the
    pilot's 5–10 h [inference, ROADMAP §3.2], or accept a re-estimate from a short measured tok/s run
    under 8 threads. The result goes into the X1-local-pilot record before it freezes. *Revision 3:*
    under D0-10c's chat answer the question widens: what share of the 8 threads may all local Qwen3
    jobs (authoring, reviews, Prover and Adversary roles, the pilot) take in the weeks X2 fuzzes?
19. **Family-B metered sub-cap (D0-10a).** Family B's authoring and reviews are metered and draw on
    the same approved amount before the held-out runs ([COST §1.3, §5](COST.md#5-alerts-and-stop-loss)).
    Should D0-10a set a sub-cap for them, inside X1's and the other experiments' caps? *Moot under
    D0-10a's chat answer ("No metered API"), pending ratification.*
20. **Gated catalogue run before or after the kit freeze.** The proposal (§3.5): engineering runs on
    the unfrozen kit, then freeze, then the gated run, where a miss is HALT-F. The alternative is to
    run the gated catalogue before the freeze, which moves the freeze, blind-batch commissioning and
    X4-hacks-blind one week later. Which does Pierce prefer?
21. **Collection by instruction (D0-12).** The README collection rule lets an Owner instruction cover
    a frozen, unsigned record. D0_BRIEF's D0-12 recommendation limits that to deterministic,
    exhaustive runs (X0). Which applies to X2-fuzz and the X4 noise pilot? §8 marks both "pending
    D0-12". *Answered in chat 2026-10-16, pending ratification: only X0 has the instruction route;
    X2-fuzz and the noise pilot wait for their signatures at a weekly sitting (§8, revision 3).*

---

## 14. Change log

| Date | Change | By |
|---|---|---|
| 2026-10-16 | First version: tracks, dependencies, Plan A and Plan B, machine calendar, owner hours, pre-registration schedule, review protocol, risks, plan tombstones, status table, owner questions | plan track (Claude, same-family; not yet reviewed) |
| 2026-10-16 | Revision 2 after one same-family review of 18 findings (§15). Changes: Plan B operative until D0-10b; night ask aligned with D0_BRIEF D0-10d plus a post-pilot rate rule; A/A bound column and stopping-rule proposal; Plan B checkpoints, night calendar and Plan B-cal; σ_ta Rust arm or floor plus the sealed reserve; X0 → X2 census dependency; rules freezes before development data; explicit kit/catalogue order; job wrapper and aggregate thread cap; `mithc profile measure` in the night order; reference-binary stand-in; D0 "needed by in this plan" column; barred-X3 mapping lines; R-diff backlog schedule; R23–R28; three tombstones; rebuilt status table; Q15–Q21; adopted the track-created paths | plan reviser (Claude, same family as author; independent context) |
| 2026-10-16 | Revision 3: carried the Owner's chat answers of 2026-10-16 (D0-10a "No metered API"; D0-10c "Local Qwen3 via Hearth"; D0-12 "Batch weekly review", X0 excepted), pending ratification. Resolved the three disagreements with D0_BRIEF that the week-0 residual risks listed, preferring the brief's latest positions: (1) the night ask is now the staged window (4 pilot-week nights, then the §6.3 rule, at most 7), not a fixed 7 from W2; (2) D0-11b is back at M1, not W0; (3) only X0 is covered by an instruction, and X2-fuzz and X4-noise-pilot need signatures at a weekly sitting. Also aligned with the brief: one weekly sitting instead of two slots; D0-9b not needed for the kit freeze. X1 marked blocked pending the restructure (D0_BRIEF Q16–Q18; X1 record). R-local review grade (D0_BRIEF Q17). `pass_one_family` mapping line (§3.8). Risks R2, R16, R17, R26 updated; R29–R31 added. Status rows S02–S12, S29–S32, S42, S54–S55, S62–S65 updated; S68–S71 added. Q1, Q10, Q16, Q18, Q19, Q21 annotated. Two tombstone survivor comments changed. Setup table refreshed (families; TOOLCHAINS.md present) | owner track (Claude; not reviewed) |
| 2026-10-23 | Revision 5, consistency edits only, by the queue track (Claude, same family; not reviewed). Carried Pierce's batches 3 and 4 from OWNER-ANSWERS at `3a66d49`: the interim chat signature (effort `max`); X0 and X1-amendment-1 SIGNED (interim); D0-7a, C01, C02, C25 and A20 answered; the written delegation. Annotated the header, §1, §3.2, §3.4, §3.5, §3.7, §6.1, §8 and §13. Updated S02, S04–S06, S08–S10, S14, S51 (its owner-side blockers only) and S68–S72, and added S73 (the delegation log) and S74 (the sitting-2 packet). No schedule, threshold or derived figure was re-computed; the finish-week tables and checkpoints C0/B-C0 still show the 10-18 sitting, which did not take place | queue track |
| 2026-10-23 | Revision 5, revised after one review of the queue track's files (Claude, same family, independent context; 13 findings, all accepted; §15). Consistency edits only: the Q17 and Q18 lines are not delegable (recommendations in DELEGATED P3 and P2); S71 and Qwen3 work bound to R2's 5–10 desktop hours until Pierce signs a weekly cap (P13); a proposed `gate_missed` line noted under §3.8 (P8, P28); §13's classes re-split (Q7, Q15, Q18); S68, S69, S71 and S73 updated. No schedule, threshold or derived figure was re-computed | queue track reviser |
| 2026-10-16 | Revision 4 after one review of revision 3 (Claude, same family, independent context; 13 findings across the owner track's five files, all accepted; §15). Batch 2 of the chat answers carried, cited from OWNER-ANSWERS.md: the X1 rule (Q16 answered, template author Q18 open with no default), D0-10d (pilot nights from W1, 23:00–07:00 PT, a 4–7-night rule), Sunday sittings (10-18 first). Critical path, C0, C1, B-C0, B-C1 re-derived against Sunday sittings and W1 nights; §8's X2-fuzz, X4-noise-pilot and X4-calibration rows moved; `pass_local_family` line (§3.8); R-local provisional (§9); §9 step 5 marked superseded; provider-era R24 and C3 rewritten; dollar figures in §3.2 labelled as API-price estimates; R1, R26, R29 updated; S02, S05, S06, S09, S10, S51, S69 updated; Q1, Q4, Q6, Q16 annotated | owner track reviser (Claude, same family) |

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

**Revision 3 (owner track, 2026-10-16)** was reviewed once, together with the owner track's other
files:

| Date | Reviewer | Family | Lens | Scope (input) | Findings by severity | Outcome |
|---|---|---|---|---|---|---|
| 2026-10-16 | Reviewer 1 of the owner-track revision | Claude, same family, independent context | the Owner's position: fidelity to the owner answers log (commit `11210a8`), decision by framing, cost completeness, sitting feasibility, stale text (inferred from the findings) | D0_BRIEF, PLAN revision 3, COST revision 3, the X1 record's restructure section, OWNER-QUEUE | blocker 1, major 6, minor 6 (13 in all, across the five files) | 13 accepted (6 with a modified fix), 0 rejected; revision 4. Full log in [OWNER-QUEUE](OWNER-QUEUE.md#review-log) |

In this plan the review led to the revision 4 changes in §14. Two came from findings about PLAN alone:
the provider-era text (R24, C3, §9 step 5, the dollar figures of §3.2) and the re-derivation of C0,
C1 and the critical path against Sunday sittings and W1 nights. The finish-week table of §6.3 was not
re-derived; the plan track owns `check.py`.

**Revision 5 (queue track, 2026-10-23)** was reviewed once, together with the queue track's other files:

| Date | Reviewer | Family | Lens | Scope (input) | Findings by severity | Outcome |
|---|---|---|---|---|---|---|
| 2026-10-23 | Reviewer 1 of the queue track's revision | Claude, same family, independent context | the delegation's limits against the FROZEN records and the owner log; fair presentation of options; pre-registration of each rule (inferred from the findings) | DELEGATED's proposed rows, OWNER-QUEUE, D0_BRIEF; PLAN and COST as sources | blocker 1, major 6, minor 6 (13 in all; finding 7 also names §3.8's mapping, which DELEGATED P8 adopts) | 13 accepted (3 with a modified fix), 0 rejected. Full log in [DELEGATED](DELEGATED.md#review-log-of-the-proposed-rows) |

In this plan it led to the consistency edits in §14's second revision-5 row.
