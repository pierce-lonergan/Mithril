# M0 cost tracker

Status: living ledger, opened 2026-10-16, revision 2 the same day after a same-family review
([PLAN §15](PLAN.md#15-review-log)), revision 3 the same day by the owner track to carry the Owner's
chat answers, and revision 4 the same day after one review of revision 3 (Claude, same family,
independent context; logged in [PLAN §15](PLAN.md#15-review-log) and
[OWNER-QUEUE](OWNER-QUEUE.md#review-log)). Revision 5, 2026-10-23, is by the queue track (consistency edits for
Pierce's batches 3 and 4; rows 9–12; a late W0 snapshot), revised the same day after one review of the queue
track's files (Claude, same family, independent context; logged in [PLAN §15](PLAN.md#15-review-log) and
[DELEGATED](DELEGATED.md#review-log-of-the-proposed-rows)). It tracks spend, Owner hours and machine
hours against ROADMAP §10's M0 lines. The plan track maintains the format. Each track appends its own rows. Evidence tags follow
[README](README.md#evidence-tags). [PLAN.md](PLAN.md) holds the schedule that these figures are
compared against.

**Owner answers, 2026-10-16** ([OWNER-ANSWERS.md](OWNER-ANSWERS.md), commit `11210a8`; decided by
Pierce in chat, not yet AUTHORITY facts until a `d0-sign-<n>` tag ratifies them at sitting 1, Sun
2026-10-18; work proceeds on them provisionally): D0-10a "No metered API". Claude work runs on
Pierce's Claude Code plan, and no family gets paid API access; D0-10c names the local Qwen3 via Hearth
as the only family besides Claude, as the ROADMAP pilot ([D0_BRIEF §0](../D0_BRIEF.md)). So **the
metered budget stated by Pierce is $0 (approved once D0-10a is ratified)**. ROADMAP's API lines below
stay as estimates of what M0 would cost at API prices, never as a spend authorisation. The costs that
bind instead are Claude Code plan usage (tokens and the account-wide 5-hour and weekly windows),
daytime desktop hours for Qwen3 and, if Pierce writes X1's templates himself, owner hours (§1.6). His
batch-2 X1 rule ("Claude kills; pass provisional") makes X1's Claude attempts the largest plan-usage
line; his check of the plan's terms and capacity is OWNER-QUEUE A20.

**Revision 5 (2026-10-23).** On 10-23 Pierce ratified these answers in his interim chat signature (OWNER-ANSWERS
batch 4); under A10 the tag at sitting 2 (Sun 10-25) is the AUTHORITY fact. So **the metered budget is $0,
ratified in chat, with the tag still to come**. His batch-3 answer to A20 was "Terms OK; run the smoke run".
X1-amendment-1 is SIGNED (interim) with s = 50% of each weekly window, cap 160, K = 6 and effort `max`. "Extra
usage" stays disabled (its §2.2 and §2.4 P6). Spending money stays outside the written delegation
([DELEGATED.md](DELEGATED.md), Limits).

**Contents**
1. [Budget](#1-budget)
2. [Counting rules](#2-counting-rules)
3. [Ledger](#3-ledger)
4. [Totals against budget](#4-totals-against-budget)
5. [Alerts and stop-loss](#5-alerts-and-stop-loss)
6. [Weekly snapshot](#6-weekly-snapshot)

---

## 1. Budget

*(Revision 5: D0-10a's answer, $0 metered, is ratified in Pierce's interim chat signature of 10-23. It becomes
an AUTHORITY fact with his tag at sitting 2. No other amount is approved.)* None of this is approved. The
amounts become a budget only when D0-10 is signed. Until then they are
ROADMAP's estimates. Under D0-10a's chat answer (pending ratification) no metered amount will be
approved: the dollar figures in §1.1–§1.3 are API-price estimates only. §1.6 gives the plan-token and
desktop-hour figures that replace them.

### 1.1 M0 totals (ROADMAP §3.7, §10)

| Line | Estimate | Tag | Source |
|---|---|---|---|
| API spend, measurement budget included | $16–36k | [inference] | ROADMAP §3.7, §10 |
| Owner hours | ~195 h; peak ~33 h/week; ~13 weeks at 15 h/week | [inference] | ROADMAP §3.7, §10 |
| Quiet-machine hours | ≈ 60–215 h (8–27 nights of 8 h). The reconstruction in §1.4 reaches 333 h at σ_d = 4% if every A/A session runs to N | [inference]; reconstruction [D] | ROADMAP §10; PLAN §6.2 |
| Daytime desktop hours | only the X1 local pilot is budgeted (5–10 machine h, assuming loaded 9950X time; unverified under the 8-thread cap, PLAN Q18); builds, X0 compiles and X2 fuzzing are not costed | [inference] | ROADMAP §3.2, §10 |
| Hardware | not costed | — | ROADMAP §10 |

### 1.2 By experiment (ROADMAP §3)

| Experiment | API | Owner h | Quiet h | Notes |
|---|---|---|---|---|
| X0 census | $0.5–1.5k | ~10 | 0 | |
| X1 writability | $7–15k | ~55 | 0 | Includes the tooling kit ($1–2k, ~10 h) and the checker precondition |
| X2 checker spike | $3–6k | ~40 | 0 | Zen 5 fuzzing runs in daytime |
| X3 generator | $1–3k | ~20 | part of the M0 line | Nights for A/B per release compiler |
| X4 integrity kit | $3–8k | ~40 | most of the M0 line | Calibration nights, plus the noise pilot and `mithc profile measure` |
| CC note | $1–2k | ~20 | 0 | |
| D0 | — | ~10 | 0 | |
| **Sum** | **$15.5–35.5k** [D] | **195** [D] | **≈ 60–215** [inference] | The API sum rounds to ROADMAP's $16–36k |

*Rows [inference, ROADMAP §3.1–§3.7]; the sums are [D] by addition (`scratchpad/plan/check.py`).*

### 1.3 Measurement budget, inside the API lines (ROADMAP §10)

| Measurement | Attempts | API | Machine | Tag |
|---|---|---|---|---|
| X1 held-out: 60 × 5 × 3 primary arms + 60 × 3 × 3 secondary arms, × 2 families | ≈ 2.9k | $1.4–5.8k | — | [inference] |
| X1 card iteration: 20 × 5 × 3 epochs × 2 Mithril arms × 2 families | ≈ 1.2k | $0.6–2.4k | — | [inference] |
| X1 local pilot: 10 × 3 × 2 arms × 1 local model | 60 | $0 | 5–10 desktop h, daytime (unverified under the cap) | [inference] |
| **X1 measurement subtotal (ROADMAP)** | ≈ 4.1k [D] | $2.0–8.2k [D] | 5–10 h | |
| *Not in ROADMAP's lines:* | | | | |
| Held-out growth if the n rule asks for n > 60: 48 attempts per extra item [D: (5 × 3 + 3 × 3) × 2] | 48 × (n − 60) | $0.024–0.096k per extra item [D] | — | [D] |
| — for example n = 120 (the example n_max of PLAN §3.2): 5,760 held-out attempts in all | 5,760 | $2.9–11.5k in all [D] | — | [D] |
| Proposed Rust arm on the card-iteration items (PLAN §3.2, Q16): 20 × 5 × 1 epoch × 2 families; 100 at one kill-carrying family (D0_BRIEF Q16) | 200 (100 at one family) | $0.1–0.4k [D], an API-price estimate, not a budget (D0-10a chat answer); on the plan it costs tokens | — | [D], pending PLAN Q16 and D0_BRIEF Q16. *Revision 5: not in the signed X1-amendment-1's attempt count (§4.4), which uses option (c), a 24-item calibration set (OWNER-QUEUE D01)* |
| **Family B authoring and reviews (metered):** X1 sealed tasks, oracles, reference solutions and the reserve; the `mithi` planted corpus; X4's blind hack batch; the X2 lockstep Prover; the CC Prover and Adversary; R-diff reviews of SIGNED records and verdicts (PLAN §9) | — | **not estimated** [G]; filled in from the first provider export. *Revision 3: no Family B exists under the chat answers; these roles fall to the local Qwen3 (desktop hours, §1.6) or the Owner, pending D0_BRIEF Q16–Q18. Revision 5: Q16 signed 10-23; Q17 and Q18 at sitting 2 (not delegable; recommendations: DELEGATED P3, P2)* | — | — |

The price basis is $0.5–2 per agentic attempt with a frontier model [inference, ROADMAP §10].

**Why the family-B line matters.** In this setup Claude work is subscription usage, which costs $0 in
the API column (§2). The metered dollars therefore come from family B: its attempts, plus all its
authoring and review work. ROADMAP §3.2 says writing the suite and its oracles dominates X1's
$7–15k, but gives no separate figure [inference]. This file does not invent one. Family B's authoring
draws on the same approved amount *before* the held-out runs start, which is why the stop-loss in §5
is written against the remaining budget at the moment of the held-out start. PLAN Q19 asks whether
D0-10a should set a sub-cap for it.

### 1.4 Quiet hours by component (reconstruction)

This reconstruction [D] uses 06 §6.6's formula. Its assumptions are in
[PLAN §6.2](PLAN.md#62-quiet-hour-demand-reconstructed). "Central" means each A/A session lasts one
planned test. "Bound" means each A/A session runs to the amber limit N (2 × planned).

| Component | σ_d = 2%, central | σ_d = 2%, bound | σ_d = 4%, central | σ_d = 4%, bound |
|---|---|---|---|---|
| X4 planted regression (3% and 4%, 100 microbenchmark sessions each, to N) | 26.7 h | 26.7 h | 97.8 h | 97.8 h |
| X4 A/A, 100 microbenchmark sessions | 6.7 h | 13.3 h | 24.4 h | 48.9 h |
| X4 end-to-end A/A, 20 sessions | 24.0 h | 48.0 h | 88.0 h | 176.0 h |
| X3 microbenchmark, 8 tests | 0.5 h | 0.5 h | 2.0 h | 2.0 h |
| X3 decode guard, 2 tests | 2.4 h | 2.4 h | 8.8 h | 8.8 h |
| **Total** | **60.3 h** | **90.9 h** | **221.0 h** | **333.4 h** |

*All cells [D]: `scratchpad/plan/check.py`, revision 2.*

- Under PLAN §3.5's proposed A/A stopping rule (microbenchmark A/A to N; end-to-end A/A to
  non-inferiority e ≥ 20 or N), the total is 66.9–90.9 h at σ_d = 2% and 245.4–333.4 h at σ_d = 4% [D].
- Outside the formula [G, not measured]: the noise pilot (2–3 nights) and `mithc profile measure`
  (2–4 h, one night).
- The reconstruction omits calibration blocks, sentinels, settling, voids and tuning re-runs. The cost
  line remains ROADMAP's ≈ 60–215 h. At σ_d = 4%, the bound case and the proposed rule both exceed
  it. PLAN Q12 (contingency) and Q15 (stopping rule) put that to the Owner.

### 1.5 Night capacity (PLAN §6.3)

| Nights a week from W2 | W2–W6 capacity | After pilot and profile (4 nights [G]) | W3–W6 only (calibration from W3) |
|---|---|---|---|
| 4 | 160 h | 128 h | 128 h |
| 5 | 200 h | 168 h | 160 h |
| 7 (D0_BRIEF D0-10d) | 280 h | 248 h | 224 h |

*[D]: weeks × nights × 8 h (`check.py`). The ask and the rule for setting the rate after the pilot
are in PLAN §6.3, provisional, pending D0-10d. Revision 3: the ask is now D0_BRIEF D0-10d's staged
window (4 pilot-week nights, then the rule's rate, at most 7); the 7-night row is that rule's
maximum, not the ask.*

### 1.6 Plan tokens and desktop hours under the 2026-10-16 owner answers

*Revision 5 (2026-10-23).* The chat answers are ratified (interim), and Q16 is signed with X1-amendment-1.
D0_BRIEF Q17 and Q18 are still open, and neither is delegable: both need Pierce's signed lines. The
recommendations, QWEN3_LOCAL_PROVISIONAL and GEN_QWEN3 (DELEGATED P3 and P2), are not adopted. Until he signs Q17
and a weekly Qwen3 cap, all Qwen3 jobs together stay within R2's 5–10 desktop hours (P13). **The template rows below
use two held-out kill-carrying families (F = 2) and are superseded by the signed X1-amendment-1 §5.3 (F = 1,
≤ 1 held-out item per template, 167–201 templates):**
- GEN_OWNER ≈ 84–302 owner h;
- GEN_QWEN3 ≈ 54–374 daytime desktop h for X1's Qwen3 work in all;
- GEN_CLAUDE ≈ 22–197 M plan tokens, ≈ 0.31–3.39 weekly windows.

At 2–3 held-out items per template and n = 160 (§5.3): GEN_OWNER ≈ 42–171 owner h; GEN_QWEN3 ≈ 33–225 h;
GEN_CLAUDE ≈ 11–112 M plan tokens. These are [inference and D from G]; they were re-derived by
`scratchpad/queue/calc_queue.py` [D]. Two or three items per template are not admissible above the signed cap of
160 (§4.3); at or below it they need the X1 record's §6.3 recompute and a §4.3 change Pierce signs. Effort `max` changes the tokens per
attempt (X1-amendment-1 §2.1), so the per-attempt row below is unmeasured at that level until the §6.2 smoke
run.

All rows are pending ratification of the chat answers and, for X1, D0_BRIEF Q17 and Q18 (Q16 is
answered in chat: option 4b). The X1 record's section "X1 under the 2026-10-16 owner constraints"
derives them (`scratchpad/owner/calc.py`, `calc2.py`). Template-based rows carry two template counts:
**≤ 1 held-out item per template** (the X1 record's §4.3, as designed; ≈ 127–204 templates) and
**2–3 per template** (≈ 71–94 templates; it needs a template-clustered analysis, an F = 1 power
simulation not yet run and a §4.3 change Pierce would sign).

| Item | Claude Code plan tokens | Daytime desktop hours (local Qwen3) | Owner h beyond ROADMAP's X1 line | Tag |
|---|---|---|---|---|
| One Claude attempt (X1) | ≈ 0.26–0.92 M | — | — | [D from G: X1 DESIGN §12.1's formula, 10–20 turns, 10–15k prefix, 5–20k output] |
| X1, one kill-carrying family, n = 96: 2,856 attempts (2,016 held-out + 600 card iteration + 240 calibration) | ≈ 0.73–2.63 B | — | — | [D] |
| X1, one kill-carrying family, n = 160: 3,816 attempts | ≈ 0.97–3.51 B | — | — | [D] |
| X1, one kill-carrying family, **n = 136**, the planned n_final of [X1-amendment-1](prereg/X1-amendment-1.md) §4 [S]: 3,456 attempts (2,616 held-out + 600 card iteration + 240 calibration) | ≈ 0.90–3.18 B ≈ 13–55 full weekly windows at ≈ 58–71 M tokens per window [D, rough; note on rows 7–8] | — | — | [D] |
| X1 option 1 (Claude and Qwen3 both carry the kill; Qwen3 writes whole items). Contradicts D0-10c's option text and the X1 rule; for comparison only | ≈ 0.73–2.63 B | ≈ 288–788 | ≈ 0 | [D from G and inference] |
| X1 option 4b (the X1 rule), Qwen3 templates (D0_BRIEF Q18 = GEN_QWEN3), ≤ 1 held-out item per template | ≈ 0.73–2.63 B, plus 5–20 M for the generator | ≈ 44–378 | ≈ 1–5 | [D from G and inference] |
| — the same, 2–3 per template | as above | ≈ 30–190 | ≈ 1–5 | [D from G and inference] |
| X1 option 4b, Owner-written templates (GEN_OWNER), ≤ 1 per template | as 4b | ≈ 12–30 | ≈ 64–306 | [D from G: 0.5–1.5 h per template] |
| — the same, 2–3 per template | as 4b | ≈ 12–30 | ≈ 36–141 | [D from G] |
| X1 option 4b, Claude-written templates (GEN_CLAUDE; a labelled loosening of 05 §13's author guard, not recommended) | as 4b, plus ≈ 9–200 M for the templates | ≈ 12–30 | ≈ 1–5 | [D from G: 5–10 turns, 15–30k prefix, 20–40k output, × 1–2 drafts per template, over 71–204 templates] |
| X1 local pilot (all options) | — | 5–10 | — | [inference, ROADMAP §3.2]; unverified under 8 threads (PLAN Q18) |
| D0_BRIEF Q17 roles, if Qwen3 holds them (bounded placeholder): R-local reviews of ≤ 23 records and verdicts | — | ≈ 1–12 | — | [D from G: 10–25k tokens in, 2–5k out, 1–3 passes; prefill 100–226 tok/s, of which 226 is measured on a 2,048-token prompt [R11]; decode 13–22 tok/s] |
| — CC Prover and Adversary (the note ≈ 70k tokens [D: 277,935 bytes / 4, G]) | — | ≈ 0.3–4 | — | [D from G: 5–20k out, 1–3 passes; context length not verified, so chunking may add time] |
| — X2 lockstep Prover | — | ≈ 0.04–1 | — | [D from G: 10–30k in, 2–10k out, 1–3 passes] |
| — X4 batch (b) Adversary | — | ≈ 0.6–21 | — | [D from G: 10–30 hacks, 20–50k in and 3–10k out each, 1–2 drafts] |
| — Q17 roles together | — | ≈ 2–38 | — | [D]; or a weekly Qwen3 cap Pierce signs instead (PLAN Q18, OWNER-QUEUE B06) |

*For scale, the agent work of 2026-10-16 so far reported 10,649,295 tokens (ledger rows 4 and 5)
[D: 10,248,932 + 400,363], so X1's Claude attempts alone are ≈ 70–250 times that at n = 96 [D].
How plan tokens convert to the 5-hour and weekly windows is unknown; X1's smoke run (PLAN S70)
measures it. The windows are account-wide (§2), so for about six weeks X1 would take a large, so far
unmeasured share of them, and the agent team and Pierce's other Claude use would slow down
[inference]; whether the plan's terms allow it is Pierce's own check (OWNER-QUEUE A20). If the X1 option chosen cannot fit the windows, a signed amendment comes before
collection (ROADMAP §1 rule 1). The figure that would restore ROADMAP's design, a second frontier
family's attempts alone, is ≈ $1.4–5.7k at n = 96 [D: 2,856 × $0.5–2]; it is listed for comparison
and is contrary to the D0-10a answer.*

---

## 2. Counting rules

**API $ (metered).** This column holds only dollars actually billed by a provider. It is filled from the
provider's usage export or invoice and tagged [M], with the source named.
- The X1 harness logs tokens in and out for every attempt. It computes dollars from a price table
  that the X1 record pins, with a citation and a date.
- Family B's authoring and review sessions are logged the same way, per work item (suite batch,
  reserve, planted corpus, blind batch, Prover or Adversary review, R-diff review). They are kept
  separate from attempts so that the family-B line of §1.3 can be filled in.
- No price is filled in from memory. If no published price is cited, the dollar cell stays empty and
  only the token count is recorded.

**Claude Code sessions are subscription usage, not metered API dollars.** The agent team (orchestrator,
tracks and reviewers) runs in Claude Code on a Max plan [M, `get_usage`, 2026-10-16T18:17Z]. These
sessions cost $0 in the API column. Record what is available, in this order:

1. **Tokens.** Record cumulative token counts when a usage report or transcript export provides them,
   tagged [M]. A *context occupancy* snapshot (the tokens in a session's window at one moment, as
   `get_usage` reports it) is not cumulative consumption. Record it as such, never as tokens spent.
   A workflow or agent report's total is tagged [M, workflow report] and its row says what it counts
   (for example "subagent tokens", which excludes the orchestrating session) and which earlier rows
   it already contains, so that rows are never added twice.
2. **Plan-window usage.** Take snapshots of the 5-hour and weekly percentages at the start and end of
   a work block, and at least 4 per work block when they are used for pacing. Tag them [M], with the
   reset time `get_usage` reports. The window is account-wide, so a delta includes every session that
   ran in parallel. Attributing it to one track is [G].
3. **Wall-clock time** of the session or block, [M] from timestamps.

An *API-equivalent* dollar figure may be added only as [D], with the formula and the cited price at its
date. It never enters the API column.

ROADMAP's API lines assume metered API spend for agent work [inference]. In this setup most authoring
runs on the subscription, so the API column will undercount the economic cost of M0. The subscription's
weekly and 5-hour limits are a throughput constraint instead (PLAN risk R17).

**Owner hours.** These come from Pierce's own log: a weekly total per track is enough (PLAN Q13), tagged
[M, owner log]. An agent's estimate of Owner time is [G], is marked *est.*, and is replaced when
Pierce reports. Freeze and signature commits and R-diff review reading (PLAN §7) are logged under the
track whose record they concern.

**Machine hours.**
- *Desktop daytime*: wall-clock time of Mithril jobs (≤ 8 threads in aggregate), taken from the job
  wrapper's start and end stamps, with the token count, [M]. The wrapper is X4's deliverable, due at
  the start of W1 (PLAN §3.5). Before it exists, daytime hours are not metered.
- *Quiet hours*: taken from the measurement service's session log, [M]. Hours of voided sessions count,
  because they used the window. The void count is recorded beside them. The noise pilot and
  `mithc profile measure` are logged as their own lines.
- *Laptop*: recorded only for jobs over about 1 CPU-minute.

**Ledger rules.**
- The ledger is append-only. A correction is a new row that cites the row it corrects and gives the
  signed difference.
- There is one row per item per day.
- Every row carries a tag. Rows that are estimates are marked **est.**
- No row may present an Owner decision as made. A budget line becomes "approved" only by citing the
  signed D0-10.

---

## 3. Ledger

Columns: API $ is metered dollars only; Tokens / plan usage follows the Claude Code rules of §2; Owner h
and Machine h are as in §2.

| # | Date | Item | Track | API $ (metered) | Tokens / plan usage | Owner h | Machine h | Tag | Source |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-16 | **Sprint setup, est.** The host session "Full-send Mithril: D0 brief + M0 falsification sprint" was created at 17:53Z. It covers reading the repository and the Hearth clone, the `docs/m0/` scaffold, the X0 record draft, the start of the X0 toolchain setup (LLVM, XED) and the X0 scripts, and orchestrating the track agents | all | $0 [G: no metered API keys provisioned, per the sprint brief] | host-session context occupancy 250,894 tokens at 18:17Z (a snapshot, not cumulative) [M]. Plan usage at 18:17Z: 5-hour 3%, weekly all-models 10% [M]. Cumulative tokens unknown | not logged (Pierce to fill) | laptop: light, not metered. Desktop: downloads and clones, not metered | **est.** | `get_usage`, 2026-10-16T18:17Z |
| 2 | 2026-10-16 | Plan track: read ROADMAP, ARCHITECTURE §11–§17, DECISIONS §1/§4, 05 §13, 06 §6–§7, 07 §4 and the X0 record; wrote PLAN.md and COST.md; ran `check.py` (< 1 s) | plan | $0 [G] | Plan usage at 18:29Z: 5-hour 8%, weekly all-models 11% [M]. Delta from row 1: +5 and +1 points, account-wide, while several tracks ran in parallel; the plan track's share is unknown [G] | 0 | laptop: < 1 CPU-minute [G] | M / G | `get_usage`, 2026-10-16T18:29Z |
| 3 | 2026-10-16 | Plan reviser: checked 18 same-family review findings against the sources; wrote PLAN.md revision 2 and COST.md revision 2; ran `check.py` revision 2 | plan | $0 [G] | Plan usage at 18:45Z: 5-hour 16%, weekly all-models 13%, weekly Fable 0% [M]. 5-hour reset `2026-10-16T22:59:59.905Z`; extra usage disabled [M]. Delta from row 2: +8 and +2 points in 16 min, account-wide; the plan track's share is unknown [G] | 0 | laptop: `check.py` 0.14 s wall [M, `time`] | M / G | `get_usage`, 2026-10-16T18:45Z |
| 4 | 2026-10-16 | **Workflow 1** (the week-0 build): 30 agents, the track authors, reviewers and revisers for the D0 brief, PLAN and COST, the X0–X4 records and designs and the core-calculus note. It contains the agents of rows 2 and 3; do not add those rows to it | all | $0 (Claude Code plan; no metered API, D0-10a chat answer) | **10,248,932 subagent tokens** [M, workflow report]; excludes the orchestrating host session (row 1) | not logged (Pierce to fill) | laptop: light, not metered; desktop: not metered (job wrapper not yet live) | M | workflow 1 report, as relayed to the owner track |
| 5 | 2026-10-16 | **Toolchain setup agent** (X0): LLVM 23.1.3 for Windows and Linux, XED v2026.08.23, CMake, the Hearth source on D:, smoke and probe compiles ([TOOLCHAINS.md](../../experiments/x0-census/TOOLCHAINS.md)) | X0 | $0 (Claude Code plan) | **400,363 tokens** [M] | 0 | desktop: downloads, builds and smoke compiles, not metered (TOOLCHAINS.md lists them) | M | agent report, as relayed to the owner track |
| 6 | 2026-10-16 | **Build round** (this round: the owner track's integration of the chat answers, the X1 restructure section and OWNER-QUEUE.md, plus whatever other tracks run in the same round) | all | $0 (Claude Code plan) | *to be filled from the round's report* | 0 | owner track: laptop, `calc.py` and a brief-parsing check, each < 1 s [M] | — | to be filled |
| 7 | 2026-10-16 | **Build round, report** (fills row 6; it does not add to it): 22 agents. Their work most likely landed in commits `1e5ddd6` to `6b14b35`, all made at 19:39 PT [inference: the commit times; the report itself was not seen]: `mithi` v0 and the grammar, CC round 2, the X0 freeze kit, the X2 harness and proofs, X4 service v0 work in progress, and the owner-answer integration. It contains row 6's owner track | all | $0 (Claude Code plan) | **9,871,258 subagent tokens** [M, workflow report, as relayed by the lead engineer]; excludes the orchestrating session. Plan readings, weekly all-models: **22% at 14:40 PT (21:40Z) and 39% at 19:40 PT (02:40Z, 10-17)** [M, lead engineer's usage readings] | not logged (Pierce to fill) | desktop builds and unit tests by the X0, X2 and X4 tracks, not metered (job wrapper not yet live) | M | build-round report, as relayed to the packet track |
| 8 | 2026-10-16 | **Packet round** (this round: the sitting-1 packet and HOW-TO-SIGN, X1-amendment-1 and the F = 1 power blocks, plus whatever other tracks run in the same round) | all | $0 (Claude Code plan) | *to be filled from the round's report* | 0 | packet track, laptop: power simulation, F = 1 blocks 91.8 s and 230.8 s, reproduction re-run of blocks 1, 12 and 13 41.8 s, quick test 2.4 s [M, script output]; arithmetic and doc checks < 1 s each [M]. Packet reviser: the reviewer's simulator re-checks ≈ 20 s and ≈ 31 s, `--recompute --families 1` at 2,000 and 20,000 replicates 17 s and 121 s, the gate simulation in `calc_packet.py` a few seconds [M]. Desktop: none (thread budget 0). **Plan reading by the packet reviser, 2026-10-17T03:27Z (20:27 PT on 10-16): 5-hour 49% (resets 04:00Z), weekly all-models 43% (resets 2026-10-23T12:00Z, Fri 05:00 PT), weekly Fable 0%; extra usage disabled [M, `get_usage`]** | M / — | `get_usage`, 2026-10-17T03:27Z; tokens to be filled |
| 9 | 2026-10-17 | **X0 freeze and census round** (late entry, written 2026-10-23 by the queue track from the commit log): X0 pre-freeze review fixes (`2191ff8`), the desktop re-run and the lead engineer's freeze rulings (`a7ca16a`), the freeze (`152fa33`, 01:16 PT), census run 1 on the desktop, the independent re-derivation and REPORT.md (`506c0bd`), results stored byte-exact (`cb7d869`), and the final sitting-1 packet (`7e187ca`, `a3add8b`) | X0, packet, lead | $0 (Claude Code plan) | *to be filled from the round's report* | 0 | desktop: census run 1, 07:10–07:19 PT [M, as reported in PACKET item 5]; the pre-freeze re-run is not metered (job wrapper not live) | M (commit times) / — | `git log`; PACKET item 5; tokens to be filled |
| 10 | 2026-10-23 | **Owner, batches 3 and 4** (asked about 08:10 PT; answered by about 08:40 PT): three answers (interim signing, the four pilot defaults, plan terms), then the interim chat signature of sitting 1 with effort = `max` and the written delegation ([OWNER-ANSWERS](OWNER-ANSWERS.md)) | D0 | $0 | — | not logged (Pierce to fill) | — | — | OWNER-ANSWERS batches 3 and 4 |
| 11 | 2026-10-23 | **Lead engineer, morning**: X1-amendment-1 frozen (`ac751b8`, 08:03 PT); batch 3 logged (`c88e0ab`); batch 4, SIGNATURES.md, the interim-signature sections of X0 and X1-amendment-1, and DELEGATED.md (`3a66d49`, 08:37 PT) | lead | $0 (Claude Code plan) | *to be filled* | 0 | laptop: commits only [G] | M (commit times) / — | `git log`; tokens to be filled |
| 12 | 2026-10-23 | **Workflow round, W1, round 1** (this round; the tracks running now). Among them: the queue track (OWNER-QUEUE classification; proposed DELEGATED rows; D0_BRIEF, PLAN and COST consistency edits); the X0-A1 tooling fix (untracked `experiments/x0-census/results/tooling_fix_A1/` and `scripts/tests/test_loops_a1.py` [M, `git status`]); X4 pilot-service work (untracked `pilot.rs`, `pilotcfg.rs`, `observe.rs`, `hygiene.rs`, `sensors_win.rs`, `x4plant.c` and others [M, `git status`]); a portable LLVM 23.1.3 download in `C:\Users\Pierce Lonergan\tools\_downloads` (folder time 08:46 PT [M]) | all | $0 (Claude Code plan) | *to be filled from the round's report*. Plan readings *to be filled* (the lead engineer's `get_usage`; the queue track has no usage tool). The weekly window was due to reset at 05:00 PT today [M, reset time read 10-17 (row 8); weekly recurrence is inference] | 0 | queue track: file and `git` reads on the laptop, < 1 CPU-minute [G]; it did not use the desktop, which another workflow was using (round brief) | — | to be filled |

**Note on row 2** [D]: the 5-hour window rose 5 points in 12 minutes (18:17Z to 18:29Z). At that rate
the remaining 92 points would last ≈ 3.7 h, against a reset 4.5 h away (23:00Z). Parallel track agents
can therefore exhaust the 5-hour window before it resets. Extra usage was disabled [M]. This is the
first data point for PLAN risk R17.
*Revision 2 annotation:* the first version did not tag the 23:00Z reset. Row 3's `get_usage`
reading confirms it as `resetsAt` 2026-10-16T22:59:59.905Z [M, plan reviser, 18:45Z]. The projection
is a two-point extrapolation from track start-up, which is likely a burst. It should not be used for
pacing until it has at least 4 readings per work block (§2).

**Note on row 3** [D, `check.py`]: three readings (3%, 8% and 16% at 18:17Z, 18:29Z and 18:45Z) give
0.46 points a minute over 28 minutes. At that rate the remaining 84 points last ≈ 3.0 h, against a
reset ≈ 4.2 h away, so the window would run out ≈ 1.2 h before it resets. All three readings come
from the first hour of track start-up, so this is still a burst figure, not a pacing rate.

**Note on rows 4–6** [D]: the reported totals so far are 10,649,295 tokens [D: 10,248,932 +
400,363], all on the Claude Code plan, with metered API spend $0. The host session's own cumulative
tokens (row 1) are not reported. No plan-window reading from the end of workflow 1 is recorded
here, so the tokens-to-window conversion that X1's sizing needs (§1.6) is still unmeasured.

**Note on rows 7–8** (packet track, 2026-10-16 evening; revised the same night after one review,
Claude, same family, independent context, logged in [X1-amendment-1 §11](prereg/X1-amendment-1.md#11-review-log)).
- **Totals.** The reported totals are now 20,520,553 tokens [D: 10,248,932 + 400,363 + 9,871,258], all
  on the plan, with metered spend $0. Per build-round agent the mean is 448,694 tokens [D: 9,871,258 / 22].
- **A first, rough tokens-to-window conversion**, from the readings recorded in this ledger:
  - From 10% (18:17Z, row 1) to 39% (02:40Z, row 7), 29 points, the reported subagent tokens were
    20,120,190 (rows 4 and 7), or 20,520,553 with row 5, whose timing is not recorded: ≈ 0.69–0.71 M
    tokens per point [D, rough].
  - The build round alone moved it 17 points (22% to 39%) for 9,871,258 tokens: ≈ 0.58 M per point
    [D, rough].
  - So a full weekly window ≈ 58–71 M subagent tokens [D, rough].
  - The first version of this note used "0% to 39% on 10-16" (≈ 0.50 M per point, lead engineer). The
    window did start 10-16 near 0% (it resets Fri 05:00 PT, below), but 10 points were already used by
    18:17Z, before nearly all of the subagent tokens (the 5-hour window then read 3%). That figure
    counted other use as subagent use, and is withdrawn.
- **Why it is rough, and which way it leans.** It assumes:
  - that no other use (the host session, Pierce) moved the window. Other use makes the true tokens per
    point larger, so the figures are pessimistic for X1;
  - that the build round ran between its two readings;
  - that "subagent tokens" count the same things as X1's per-attempt estimate (cumulative processed
    tokens, including cache reads). That is not verified.
- **Use.** X1-amendment-1 §6 applies it, and finds X1's Claude attempts ≈ 13–55 weekly windows at
  n = 136 [D, rough]. The X1 smoke run's gate (PLAN S70; X1-amendment-1 §6.2) measures the deciding
  input.
- **Pacing signal.** The weekly window resets at 12:00Z, Fri 05:00 PT [M, row 8's reading]; with a
  7-day window [inference], 10-16 was its first day. On §5's rule (reading > (days elapsed / 7) × 100
  + 15 points) the signal has fired at every reading since: 22% against a line of 20.8% at 21:40Z, 39%
  against 23.7% at 02:40Z, and 43% against 24.2% at 03:27Z [D]. §5's action: pace the tracks; extra
  usage stays disabled (D23). At 43% with 6.4 days left, 57 points remain for the rest of the week [D].

**Note on rows 9–12** (queue track, 2026-10-23).
- **Late entry.** Row 9 is late: the ledger had no row for 10-17's X0 round. It adds no figure that was not
  already recorded in a commit or in PACKET item 5.
- **Tokens and readings.** Rows 9, 11 and 12 need the rounds' token reports. They also need plan readings
  from W0's end and W1's start; neither is recorded here.
- **The X1 smoke run.** That run (X1-amendment-1 §6.2) needs a quiet account, at a time Pierce agrees
  (batch 3). Its readings will be the first per-attempt plan figures [M] for X1.
- **Desktop daytime hours** remain unmetered until the job wrapper (S13) is live.

---

## 4. Totals against budget

Update this with each weekly snapshot. "Budget" stays ROADMAP's estimate until D0-10 approves an
amount.

| Line | Budget | To date | % of low end | % of high end | Tag |
|---|---|---|---|---|---|
| API $ (metered) | $16–36k [inference] as ROADMAP's estimate; **stated by Pierce: $0**, ratified in his interim chat signature of 2026-10-23; the D0-10a tag follows at sitting 2 | $0 [G] | 0% | 0% | [G] until the first provider export |
| of which family B authoring and reviews | no Family B under the chat answers; PLAN Q19 moot | $0 [G] | — | — | [G] |
| Claude Code plan tokens (reported totals) | not a ROADMAP line; X1's Claude attempts estimated at ≈ 0.73–2.63 B at n = 96, ≈ 0.90–3.18 B at the F = 1 planned n = 136 (§1.6) | 20,520,553 [D: rows 4 + 5 + 7]; rows 8, 9, 11 and 12 to come | — | — | [D] |
| Daytime desktop hours, local Qwen3 | not a ROADMAP line except the pilot; ≈ 12–378 h for X1 depending on D0_BRIEF Q18 and the template count, plus ≈ 2–38 h for the Q17 roles (§1.6). At F = 1 (X1-amendment-1 §5.3): ≈ 12–30 h without Qwen3 templates, ≈ 54–374 h with them | 0 [M: no Qwen3 job run yet; the queue track saw no Qwen3 job on 10-23] | — | — | [M] |
| Owner hours | ~195 h [inference] | not logged | — | — | — |
| Quiet-machine hours | ≈ 60–215 h [inference]; reconstruction 60.3–333.4 h [D] | 0 h [M: no quiet window has run; windows agreed in chat (R5), the X4-noise-pilot record still DRAFT on 10-23] | 0% | 0% | [M] |
| Desktop daytime hours | X1 pilot 5–10 h [inference]; the rest unbudgeted | not metered (job wrapper due W1) | — | — | — |
| Subscription, weekly all-models window | not a ROADMAP line | 13% at 18:45Z on day 0 [M]; 22% at 14:40 PT and 39% at 19:40 PT on 10-16 [M, lead engineer's readings]; 43% at 20:27 PT (03:27Z), resets Fri 10-23 05:00 PT [M, row 8]; COST §5's weekly signal fired [D] | — | — | [M] |

---

## 5. Alerts and stop-loss

These are proposals [G]. The Owner sets the actual levels with D0-10. **Under D0-10a's chat answer
(no metered API; ratified in chat 2026-10-23, the tag at sitting 2) the metered rows are dormant: any metered charge at all
stops the work that caused it and goes to Pierce, because no metered amount is approved.** The
subscription rows become the binding ones, and X1's sizing depends on them (§1.6; PLAN R17, R29).

| Signal | Level | Action |
|---|---|---|
| Metered API spend | 50% of the approved M0 amount | Notify the Owner in the weekly snapshot |
| Metered API spend | 80% of the approved amount | Stop new X1 runs until the Owner re-approves. **Exception:** an X1 held-out batch already under way runs to its fixed n. Truncating it would break the fixed-n rule (05 §13), and the held-out start check below has already reserved its cost |
| X1 held-out start | remaining approved budget < n × 48 × p_high [D]. n comes from the signed X1-heldout fill-in (before the fill-in, plan with n_max). 48 is attempts per held-out item [D, ROADMAP §10]. p_high is the top of the X1 record's pinned price table, or $2 per attempt [inference, ROADMAP §10] until that table exists. At n = 60 that is $5.76k; at n = 120 it is $11.52k [D] | Do not start the held-out runs. Starting and then truncating would break the fixed-n rule (05 §13) |
| Family-B metered spend (authoring and reviews) | 50% and 100% of a sub-cap, if D0-10a sets one (PLAN Q19) | At 50%, notify. At 100%, stop new family-B authoring until the Owner re-approves; held-out attempts are governed by the rows above |
| Owner hours | a week < 70% of PLAN's planned hours | Re-plan at the next checkpoint (PLAN §7.2) |
| Quiet hours | planned hours for the remaining nights > the nights agreed, at the pilot's σ_d and the frozen A/A stopping rule (PLAN §6.3) | Raise the night rate by PLAN §6.3's rule if the Owner agrees; otherwise record the D-22 trigger fact (ROADMAP §9), and X4 "waits" (ROADMAP §3.7) |
| Subscription 5-hour window | projected exhaustion before reset (as in rows 2–3) | Stagger track agents; long jobs wait for the reset |
| Subscription weekly window | % used > (days elapsed / 7) × 100 + 15 points | Pace the tracks; the Owner decides on extra usage |
| Any metered charge (revision 3) | > $0 | Stop the job that caused it; report to Pierce; nothing metered resumes without a new signed decision |
| Local Qwen3 daytime hours (revision 3) | the week's Qwen3 hours would push the 8-thread cap's queue past the share Pierce agreed (PLAN Q18) | Re-plan the Qwen3 jobs at the next checkpoint; never move them into a quiet window |

---

## 6. Weekly snapshot

The plan track appends one block per week, on the Thursday that ends the week.

```text
Week Wn (YYYY-MM-DD..YYYY-MM-DD)
API $ metered:     this week $…, to date $… / approved $…        [M, provider export]
  of which:        family-B attempts $…; family-B authoring and reviews $…                      [M]
Tokens:            metered harness tokens in/out …; Claude Code cumulative … (if available)  [M]
Plan usage:        weekly all-models start …% / end …%; 5-hour peaks …% (readings: …)          [M]
Owner hours:       by track D0 … X0 … X1 … X2 … X3 … X4 … CC …; total … vs PLAN … (A or B)   [M, owner log]
Quiet hours:       used … (voided …) of … agreed; nights …; rate in force …/week; pilot σ_d …   [M, service log]
Daytime desktop:   … h (jobs: …; peak tokens …); of which local Qwen3 … h                     [M, job wrapper log]
Alerts fired:      …
```

**Week W0 (2026-10-16..2026-10-22).** Written late, on 2026-10-23, by the queue track. It is assembled from
ledger rows 1–9 only, with no new measurement. The plan track may replace it.

```text
Week W0 (2026-10-16..2026-10-22)
API $ metered:     this week $0, to date $0 / approved $0 (D0-10a ratified in chat 10-23; tag at sitting 2)  [G: no metered key exists]
  of which:        family-B attempts $0; family-B authoring and reviews $0 (no family B: D0-10c)           [G]
Tokens:            Claude Code reported totals 20,520,553 (rows 4, 5, 7) [D]; rows 8 and 9 to be filled
Plan usage:        weekly all-models 10% at 18:17Z 10-16 (first reading) → 43% at 03:27Z 10-17 (last recorded)
                   [M]; no reading recorded for 10-17 03:27Z..10-22; 5-hour peak recorded 49% (03:27Z 10-17) [M]
Owner hours:       not logged (Pierce to fill)
Quiet hours:       used 0 h; no quiet window has run (the X4-noise-pilot record is DRAFT) [M]
Daytime desktop:   not metered (job wrapper not live); X0 census run 1, 07:10-07:19 PT 10-17 [M, PACKET];
                   local Qwen3 0 h [M]
Alerts fired:      weekly pacing signal (§5) at every recorded reading: 22% vs 20.8%, 39% vs 23.7%,
                   43% vs 24.2% [D, note on rows 7-8]; no metered charge
```
