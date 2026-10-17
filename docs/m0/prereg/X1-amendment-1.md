# X1-amendment-1: Claude alone carries X1's kill; a pass is provisional

Status: **DRAFT.** No data may be collected under it. Drafted 2026-10-16 (evening) by the packet track (a
Claude agent) and revised the same night after one review (Claude, same family, independent context;
§11). The lead engineer may freeze it, and Pierce signs the frozen text at a weekly sitting (sitting 1
is Sun 2026-10-18; if it is not FROZEN in that packet, or he defers it, sitting 2 is Sun 2026-10-25).
No X1 data exist, so nothing here is post-data.

**What it amends.** It changes how ROADMAP §1 rule 5 ("at least two model families") and §3.2
("Participants. At least two frontier families … They carry the kill") apply to **X1 at M0 only**. It
also changes DR-017's family requirement for X1, and the [X1 pre-registration](X1-writability.md),
which is still DRAFT. The X1 track revises §§2–8 of that record to match before X1 freezes (§9 lists the
changes). M1 is not amended: M1's DR-017 kill still needs two families.

ROADMAP anchor: §1 rules 1, 2, 3, 5; §3.2; §4 (the X1 row, STOP-L); §5 (M1); §10; §11 (D0-10). DR-017.
Owner answer: [OWNER-ANSWERS.md](../OWNER-ANSWERS.md), 2026-10-16, batch 2, the "X1 rule" row.
Power simulation: [x1_power_sim.py](../../../experiments/x1-harness/power/x1_power_sim.py), blocks 14–19
(F = 1), seed 20261016. Tables: [x1_power_tables.md](../../../experiments/x1-harness/power/results/x1_power_tables.md)
§14–19.

Evidence tags follow [docs/m0/README.md](../README.md): [M] measured, [D] derived, [S] simulated, [G]
judgment, [inference], [target]. Every [S] number here comes from the simulator under its [G] inputs
(base rates: Rust VP@1 0.50, CABW 0.20; scenarios "low" to "stress"). None is a measurement of any
model. The [D] arithmetic is `scratchpad/packet/calc_packet.py` (revision 2, re-run 2026-10-16 late
evening PT, which also simulates §6.2's gate). Owner choices are marked *provisional, pending …*.

---

## 1. The Owner's rule, verbatim, and what it changes

Pierce answered in chat on 2026-10-16, about 14:30 PT, in batch 2 of [OWNER-ANSWERS.md](../OWNER-ANSWERS.md).

> Answer: "Claude kills; pass provisional (Recommended)"
>
> Option text he saw: "Claude alone can fire the kill (VP@1 gap >15, or CABW >5 worse than Rust). A
> pass is only provisional until a second frontier family confirms it at M1. Claude also edits the card,
> which biases toward passing, so a kill is the more trustworthy signal. Sealed items are generated from
> templates with deterministic oracles, so no model writes them."

This record carries that rule into the design. It is D0_BRIEF Q16 = OPT4_STRICT, which is option 4b of
the X1 record with option 2's generated suite. It replaces the batch-1 option text "X1 cannot pass or
kill and stays amber" (D0-10a), pending ratification.

**Unchanged.** Every threshold stays as it is:

| Item | Value | Source |
|---|---|---|
| K1 | Rust − Mithril VP@1 > 15 points (point estimate, strict `>`) | ROADMAP §3.2 [target]; X1 record §7.4 |
| K2 | CABW(Mithril) − CABW(Rust) > 5 points | ROADMAP §3.2 [target] |
| Held-out items | ≥ 60 | ROADMAP §1 rule 5 [target] |
| R-VP | P(K1) ≤ 0.10 at a true 5-point gap and ≥ 0.90 at 25 | ROADMAP §3.2 [target] |
| R-CABW, R-JOINT | as in the X1 record §6.2 (stricter than ROADMAP) | X1 record [target] |
| Checker calls | 8 per task | ROADMAP §3.2 [target] |
| Oracles | ≥ 95% mutant kill | ROADMAP §3.2 [target] |
| Planted corpus | ≥ 100 items (a dev half and a confirmation half, X1 Q21) | ROADMAP §3.2 [target] |
| Ambers (a), (b), (c) | as in ROADMAP | ROADMAP §3.2 [target] |
| Re-scoring rule; VOID; UNDERPOWERED | as in the X1 record §§8, 10 | ROADMAP §3.2 |

**Changed, for X1 at M0 only.**

1. **One kill-carrying family (F = 1): Claude** (§2). Every estimand and estimator of the X1 record §7
   is computed with F = 1. The per-family terms become the whole estimate. The one-family referral of
   §7.7 does not apply, because there is no second family.
2. **A breach is binding.** If K1 or K2 holds on Claude's estimate, the X1 kill fires. The outcome is
   STOP-L (ROADMAP §4), or STOP-ALL with an X2 kill. The `standalone_surface` tombstone is written with
   `models: {claude@<pinned id>}` (§3).
3. **A pass is provisional** (`pass_one_family`). It is not DR-017's pass. It becomes one only when a
   second frontier family confirms it at M1 (§3).
4. **n is recomputed for F = 1** (§4). The planned n_final rises from 96 to **136** [S].
5. **A generated suite.** Sealed items are instantiated by a deterministic generator from templates
   with deterministic oracles (§5). The template author is a separate decision (D0_BRIEF Q18).
6. **A feasibility gate on plan capacity** before X1 freezes (§6). The amendment runs only if the
   plan's windows can carry it.

**This amendment does not decide:** who writes the templates (D0_BRIEF Q18, §5), the Qwen3 roles
(D0_BRIEF Q17), the Gatekeeper store (OWNER-QUEUE A06), or how the M0 verdict counts
`pass_one_family` (PLAN Q7, OWNER-QUEUE B01).

---

## 2. The kill-carrying family: Claude, through the Claude Code plan

### 2.1 Model identity

- **Family.** Anthropic's Claude. Every Claude model is the same family. Running two Claude models
  (for example an Opus and a Sonnet) never makes F = 2.
- **The model.** One Claude model ID, pinned at X1's freeze in the X1 record §2 and logged on every
  attempt. Candidates, by the exact IDs in the Claude reference bundled with this session (cached
  2026-10-06) [cited, not re-checked]:
  - `claude-opus-5-5` (Claude Opus 5.5). **Suggested default [G]**, *provisional, pending OWNER-QUEUE D07*.
    It is the model this drafting session runs as [M, session metadata, 2026-10-16]. The track commits
    of 2026-10-16 are co-authored by "Claude Opus 5.5" [M, `git log`], so it is very likely the model
    that edits the card and wrote `mithi` [inference]. That makes participant = card editor, which is
    exactly the bias R4 names, so the rule's reasoning applies as stated.
  - `claude-fable-5-1` (Claude Fable 5.1), described in the reference as Anthropic's most capable widely
    released model. Plan readings show a separate "weekly Fable" percentage (COST row 3 [M]). How Fable
    use counts against the plan's windows is not known [not verified].
- **Settings.** On Claude Opus 5.5, sampling parameters (temperature, top_p, top_k) cannot be set: the
  API rejects them, and effort is the only control [cited: bundled reference, "Thinking & Effort",
  re-read 2026-10-16]. The X1 record §2's "sampling parameters" field therefore reads "provider
  defaults, not settable".
- **Effort.** The same reference gives `medium` as Opus 5.5's default effort on the API, and calls
  `xhigh` "the default in Claude Code" in a sentence about other models [cited]. Which effort a
  headless Claude Code session uses on Opus 5.5, and whether the runner can set it, is **not verified**.
  Effort changes the tokens an attempt spends, so it changes §6's window share *w*. Therefore:
  - the effort level is a signed field (§10) and is pinned for the whole X1 run;
  - the smoke run (§6.2) runs at that level, and its *w* holds only for that level and Claude Code
    version;
  - if the runner cannot set effort, the smoke run records the level Claude Code reports using (or
    that it reports none, a deviation recorded before freeze, §7), and the X1 run must use the same
    Claude Code version and setting; a change is a deviation (X1 record §10.6).
- **A version change mid-run** is handled by the X1 record §10.6 (model withdrawal): that family's run
  restarts on the same sealed batch with a successor model the Owner names. The same rule covers a
  Claude Code version change that alters the system prompt or tool protocol (§2.3).

### 2.2 Access

- Claude Code plan only. **No metered API** (R1). "Extra usage" stays disabled (OWNER-QUEUE D23), so no
  paid usage beyond the plan can start silently.
- Whether the plan's terms allow scripted, headless harness attempts at this volume is **Pierce's own
  check** (OWNER-QUEUE A20). Agents do not interpret the terms. The signature block records his answer.
  OWNER-QUEUE puts A20 **before ratifying R4** (D0_BRIEF Q16). This record adds one more order
  constraint, a tightening [G]: **the smoke run (§6.2) does not start before Pierce has answered A20
  "allowed"**, because the smoke run is itself scripted, headless use of the plan.
- Content sent to a Claude participant goes to Anthropic under the plan's data-use setting, which is
  not verified (OWNER-QUEUE D08). Participants see visible bundles only. Hidden bundles never reach any
  Claude session.

### 2.3 How an attempt runs (headless and sandboxed)

This replaces X1 DESIGN §12.1's "native tool calling for API families" for Claude. The runner is a
deterministic script, written in `experiments/x1-harness/`. Per attempt:

1. **A fresh, non-interactive Claude Code session**, started by the runner. Claude Code's print
   (non-interactive) mode, or the Claude Agent SDK, which the reference describes as "Claude Code
   packaged as a library" [cited]. Which of the two runs on the plan's credentials is part of A20
   [not verified].
2. **An isolated configuration.** A per-attempt configuration directory created by the runner. It
   holds no user or project instructions (no CLAUDE.md), no memory, no skills, no hooks, no MCP servers
   except the harness's own, and no project settings. It is deleted after the attempt, once its
   transcript is copied to the private store. This matters for two reasons. First, a participant must
   not read Mithril design files ("cold" agents). Second, Claude Code keeps session transcripts in its
   configuration directory, and visible held-out content must not land where the card-editing sessions
   can read it (X1 DESIGN §4.6). The mechanism (for example a configuration-directory environment
   variable) is **not verified on this machine**: no `claude` CLI is on the laptop's PATH [M, 2026-10-16].
   The smoke run (§6) must show it works before any sealed content is used.
3. **Tools.** Every built-in tool is disabled (file read, write and edit, shell, web, sub-agents). The
   only tools are the harness's task tools (`read_file`, `write_file`, `check`, `submit`, `abandon`;
   DESIGN §7), served by the runner over MCP. The working directory is empty. The tool names and
   behaviour are the same in every arm.
4. **System prompt.** Claude Code's own system prompt, which the harness cannot change, plus the
   harness's common instructions and the arm's card (or helper card) and the shared domain preamble,
   appended the same way in every arm. The Claude Code version and the hash of everything the harness
   adds are recorded per attempt. Claude Code's own prompt is the same in every arm of a given
   version [inference].
5. **Execution.** Agent code runs only inside the X1 per-`check` sandbox (DESIGN §11.2: no network,
   read-only, no capabilities, CPU limits) and the two-stage oracle (§11.3) on the execution host
   (OWNER-QUEUE B12; default: the laptop [G]). The Claude Code process holds no hidden data and no
   shell. Its network use is its own connection to Anthropic.
6. **Budgets** as in DESIGN §12.1: 8 `check` calls [target], 60 turns, 600k non-prefix input tokens,
   60k output tokens, 45 minutes [G]. Token counts come from Claude Code's per-session usage report
   where it gives one [not verified]. Where it does not, the attempt record says so and the token
   budget is enforced by the turn cap only. That is a deviation, logged.
7. **Failures.** A plan rate-limit or window stop that ends an attempt early is an infrastructure
   failure (DESIGN §13.3): re-run as a fresh attempt, never scored.

### 2.4 Plan-usage pacing (provisional, pending OWNER-QUEUE A20 and D23)

The windows are account-wide (COST §2): X1, the agent team and Pierce's own Claude use draw on the same
5-hour and weekly windows.

- **P1, share.** X1 attempts may use at most **s = 50%** [G] of each weekly all-models window. The
  rest stays with the agent team and Pierce. Pierce may set another s at signature.
- **P2, stops.** The runner starts no new attempt while the weekly all-models reading is above
  (days since reset / 7) × 100 + 15 points (COST §5's pacing signal), or the 5-hour reading is above 80%
  [G]. An attempt under way runs to its end. The weekly window's reset is reported as
  2026-10-23T12:00Z, Friday 05:00 PT [M, `get_usage`, 2026-10-17T03:27Z]; that it recurs weekly at that
  time is [inference].
- **P3, readings.** Plan readings are taken before and after every batch of attempts, with at least 4
  readings per work block (COST §2). The readings recorded so far come from `get_usage`, a tool
  available inside Claude sessions in the desktop app (COST rows 1–3 and 8; row 7's are the lead
  engineer's readings). It reports **whole
  percentage points** (for example 49, 43 and 0 [M, 2026-10-17T03:27Z]); whether it rounds or truncates
  is not documented. Whether a script can read the same figures is not verified.
- **P4, order.** Pausing never reorders. The seeded run order (X1 record §6.4) continues where it
  stopped, and every pause is logged. A pause longer than 7 days [G] is reported in REPORT.md as a drift
  risk. It does not change the analysis.
- **P5, quiet windows.** If an X1 attempt or sandbox ever runs on the desktop, it never runs in a quiet
  window (DR-023; 23:00–07:00 PT under R5).
- **P6, no silent overflow.** Extra usage stays disabled (D23). If the windows cannot carry the plan,
  the run stops and Pierce decides; it is never topped up with paid usage.

---

## 3. Kill, provisional pass and confirmation

| X1 outcome at M0 (one family) | Condition (X1 record §8, F = 1) | Action |
|---|---|---|
| **KILL** | K1 or K2 on Claude's estimate, not VOID, not UNDERPOWERED | STOP-L (ROADMAP §4); with an X2 kill, STOP-ALL. Tombstone `standalone_surface` with `verdict` = the rule(s) that fired and `scope.models = {claude@<pinned id>}` |
| **PASS, provisional** (`pass_one_family`) | neither K1 nor K2; realised MDE ≤ 15; not VOID | Not DR-017's pass. In the M0 verdict it is neither pass nor kill: rows that need "X1 = pass" stay undecided (X1 record option 4b; PLAN §3.8, pending PLAN Q7 / B01). M1 work may start |
| Ambers (a), (b), (c) | as ROADMAP §3.2, on Claude's estimates | as ROADMAP; they accompany a provisional pass |
| VOID, UNDERPOWERED, no run | as the X1 record §8 | as the X1 record §8 |

**Confirmation at M1** (Pierce's wording: "until a second frontier family confirms it at M1").

- The binding two-family test runs as soon as a second frontier family exists. It uses a fresh sealed
  batch built as M1's is (ROADMAP §5), drawn from the unspent sealed reserve (record §4.4), with both
  families pooled as the record §7 states (F = 2).
- Its result is X1's DR-017 verdict, and a breach then is the X1 kill. It must be evaluated before
  M1's own DR-017 gate.
- Under R1 and R2 no second frontier family is planned. Adding one needs a new Owner answer
  (OWNER-ANSWERS, "Consequences").

**The standing gap**, written as a tombstone at the M0 verdict if X1 passes provisionally:

```text
tombstone x1_pass_one_family {              // written only on a provisional X1 pass
    verdict: pass_one_family                // copied from the signed X1 report
    scope:   { arms: {mithril_t01, rust}, suite: x1_heldout@sha256:…, models: {claude@<pinned id>} }
    class:   V                              // evaluation (06 §4 classes): not run as DR-017 defines it
    revisit_when: harness.frontier_families >= 2
    evidence: ledger:sha256:…
}
```

The trigger reads a fact the harness writes. The fact `harness.families` in the X1 record §7.6 becomes
1.

**The local Qwen3 pilot stays outside the kill** (R2: "reported but not part of the kill"). It runs as
the X1 record §6.6 says: T-ROUTE, 60 attempts, daytime only. Its results are reported and never enter
K1, K2 or any verdict.

---

## 4. Sample size with one kill-carrying family [S]

Simulator: [x1_power_sim.py](../../../experiments/x1-harness/power/x1_power_sim.py), extended 2026-10-16
with blocks 14–19 (F = 1). With one family, the item × family and three-way terms are no longer
averaged over two families, so the effective item × arm logit SD is 1.118 × the scenario value [D]. Run
on the shared laptop after 19:00 PT on 2026-10-16: blocks 14, 15 and 19b in 91.8 s, blocks 16–19a in
230.8 s [M]. Before the new blocks were added, the modified script re-ran blocks 1, 12 and 13
into a scratch directory. Every block-1 row and block 13's points matched the stored results exactly,
and block 12 matched apart from one new metadata key (`n_fam`) [M]. Monte Carlo SE near 0.10 or 0.90 is
≈ 0.0067 at 2,000 replicates and ≈ 0.0021 at 20,000 [D].

### 4.1 P(kill) by true VP@1 gap (CABW gap 0), one family [S, block 14, 2,000 replicates]

| Scenario | n | P(K1) at true gap 0 / 5 / 10 / 15 / 20 / 25 points | P(K1 or K2) at the same gaps |
|---|---|---|---|
| high | 60 | 0.002 / 0.014 / 0.134 / 0.494 / 0.852 / 0.991 | 0.161 / 0.164 / 0.225 / 0.517 / 0.855 / 0.991 |
| high | 96 | 0.000 / 0.003 / 0.093 / 0.499 / 0.911 / 0.998 | 0.092 / 0.097 / 0.167 / 0.509 / 0.911 / 0.998 |
| high | 128 | 0.000 / 0.000 / 0.065 / 0.511 / 0.945 / 1.000 | 0.074 / 0.070 / 0.125 / 0.519 / 0.945 / 1.000 |
| high | 160 | 0.000 / 0.000 / 0.032 / 0.497 / 0.963 / 1.000 | 0.047 / 0.052 / 0.071 / 0.501 / 0.963 / 1.000 |
| stress | 60 | 0.002 / 0.038 / 0.180 / 0.496 / 0.845 / 0.978 | 0.171 / 0.198 / 0.291 / 0.524 / 0.849 / 0.978 |
| stress | 160 | 0.000 / 0.002 / 0.059 / 0.475 / 0.945 / 1.000 | 0.062 / 0.064 / 0.117 / 0.486 / 0.945 / 1.000 |

At **n = 136**, high scenario, 20,000 replicates [S, block 16]:
- P(K1) at gaps 0 / 5 / 10 / 15 / 25 is 0.0000 / 0.0008 / 0.0500 / 0.4916 / 0.9998.
- P(K1 or K2) at the same gaps is 0.0619 / 0.0683 / 0.1060 / 0.5000 / 0.9998.
- Gap 20 is not on block 16's surface. Block 14 gives P(K1) = 0.945 at n = 128 and 0.963 at n = 160.

The low and mid rows are in the tables, §14.

**ROADMAP's own requirement (R-VP) is met at n = 60 in every scenario** [S, block 14]. Even in the
stress scenario, P(K1) at a 5-point gap is ≤ 0.038 and at 25 points ≥ 0.978, with MC bounds. With one
family, as with two, ROADMAP's VP@1 rule does not constrain n.

### 4.2 The binding requirements (R-CABW, R-JOINT) [S]

| Scenario | Smallest n meeting R-VP, R-CABW and R-JOINT: point estimate, 2,000 reps (block 15) | Same, with MC 95% bounds at 2,000 reps (block 15) | **Step-4 rule: MC bounds at 20,000 reps (block 16)** |
|---|---|---|---|
| low | 96 | 96 | — |
| mid | 112 | 112 | — |
| high (the planning floor) | 128 | 160 | **136** |
| stress | 144 | 176 | **160** |

At n = 136 in the high scenario [S, block 16]:
- The worst case over true VP gaps 0 to 15 is P(K2 | CABW gap 0) = 0.0803 and P(K2 | CABW gap 10) =
  0.9058. Both occur at a VP gap of 15.
- P(K1 or K2) at the joint null (5, 0) is 0.0683, and P(K1) at a 25-point gap is 0.9998.

At n = 128 the worst-case power at a CABW gap of 10 is 0.9013, whose MC lower bound falls below 0.90.
With two families the same rule gave 96 [S, block 13].

*Check by the review (2026-10-16).* Block 16's three points above and block 14's high-scenario n = 128
row were reproduced exactly from the same keys, and with independent seeds at n = 136 P(K2) at
(15, 0) came out 0.0803–0.0861 over four seeds, P(K2) at (15, 10) 0.9073 and P(K1 or K2) at (5, 0)
0.0685, so 136 still meets the step-4 rule; at n = 128 the power at (15, 10) was 0.9001, below 0.90
once the MC lower bound is applied [S; re-runs by the reviewer, repeated by the reviser, ≈ 20 s and
≈ 31 s on the laptop, M].

**Sensitivity [S].**
- *Base rates (block 19a, high scenario, 1,000 replicates).* With a Rust VP@1 of 0.30, the requirements
  are met only at n = 256 on the point estimate, and not with MC bounds at any n simulated. With a Rust
  CABW of 0.35: 160 on the point estimate, 192 with MC bounds.
- *Templates (block 17).* Two or three held-out items per template (template share of item variance
  0.5–0.8) need n = 160–192 in the high scenario and 128–160 in mid. In the high scenario the MC rule
  at 1,000 replicates gives 192 in every case simulated and the point rule 160–192, so the upper end is
  **above the cap of 160** (§4.3).
- *Attempts per cell (block 18, high scenario).*
  - m = 3: 192 on the point estimate, not met with MC bounds at n ≤ 192.
  - m = 5: 160 (both rules at 1,000 replicates).
  - m = 10: 96 on the point estimate, 128 with MC bounds.

  More attempts per cell buy fewer items at the cost of more attempts. That trade is §6's
  plan-token problem.
- *Calibration (block 19b).* The X1 record §6.3 procedure works with one family. 24 calibration items,
  m = 5 and one family make 240 attempts [D]. The selected ladder level is at least the true one in
  0.963–0.972 of runs, and with the floor at "high" in 1.000 (mid, high) and 0.972 (stress).

### 4.3 What this record sets (more precise, never looser)

- **Planned n_final = 136** [S, block 16]. It is the value the X1 record §6.3 step 4 gives with one
  family, the high scenario and the base-case rates. The record's planned value of 96 (two families)
  is replaced.
- **§6.3 runs with one family**: `x1_power_sim.py --recompute --families 1`. Step 3's ladder reference
  and step 4's simulation are both computed with F = 1. Because step 3 never selects a level below
  "high" and step 4 takes the larger result over the two base-rate sets, n_final is never below 136 with
  one family [S]. The floor of 96 stays in the text but no longer binds. Check: that command, with the
  base-case rates, dispersion bounds at the high level's reference values (36.2 and 40.2 points, block
  19b) and 20,000 replicates, selects "high" and returns n_final = 136 [S; run by the reviser into a
  scratch file, 121 s on the laptop, M].
- **The cap stays 160** [target, a budget cap]: *provisional, pending Pierce's choice at signature*.
  Stress-scenario variance at base-case rates needs exactly 160 [S]. A Rust VP@1 near 0.30 needs about
  256 or more [S], beyond the cap, and §6.3 step 5 then applies: collection waits for a new signed
  record, and no threshold moves. Raising the cap to 256 would need about 295 sealed candidates [D:
  256 × 1.15] and, at n = 256, about 5,256 Claude attempts in all [D: 15 × 256 + 576 + 600 + 240]. That
  makes §6's capacity problem worse, so this record does not recommend it [G].
- **≤ 1 held-out item per template** stays (X1 record §4.3). Two or three per template would cut the
  template count by roughly half but raise n to 160–192 [S, block 17] and add 360–840 held-out attempts
  [D: 15 × (160 − 136) to 15 × (192 − 136)]. That is a plan-token cost, against an authoring saving.
  **Above n = 160 it is not admissible under this record:** the cap stays 160, so a template-clustered
  n of 192 triggers the X1 record's §6.3 step 5 (collection waits for a new signed record that raises
  the cap; no threshold moves). In the mid scenario block 17 gives 128–160, within the cap. In the high
  scenario only the point rule reaches 160 (and not at a template share of 0.8); whether the step-4
  rule (MC bounds at 20,000 replicates) is met at 160 was not simulated [S, block 17 at 1,000].
- **m = 5 attempts per primary cell** stays (ROADMAP §10).

### 4.4 Attempts with one family [D]

| | n = 96 | **n = 136 (planned)** | n = 160 (cap) |
|---|---|---|---|
| Held-out: 15n primary + 576 secondary (64 items × 3 attempts × 3 arms) | 2,016 | **2,616** | 2,976 |
| Card iteration: 20 × 5 × 3 epochs × 2 Mithril arms | 600 | 600 | 600 |
| Calibration: 24 × 5 × 2 arms | 240 | 240 | 240 |
| **Claude attempts in all** | 2,856 | **3,456** | 3,816 |

---

## 5. The generated suite and who writes the templates

### 5.1 Generation (X1 record option 2)

- A deterministic generator instantiates each sealed item from a parametric template. Each template
  carries a brief template, stubs, Rust and C11 references, and a bit-exact oracle model with vector
  generators.
- The Gatekeeper seals the seeds and the template-to-split assignment.
- Mutant kill (≥ 95%), reference agreement and the contamination check run mechanically (DESIGN §4.5,
  §6.2).
- Mithril references come from a deterministic Rust-to-X1-subset transliterator, a public tool Claude
  may write. Where it fails, the template is rejected and replaced, never hand-patched by a model
  (§5.2).
- The generator and transliterator cost about 5–20 M plan tokens [inference, X1 record option 2], or
  0.07–0.34 weekly windows [D, §6].
- The planted corpus is a separate role (D0_BRIEF Q17). It never goes to Claude: a Claude-written
  mutation engine would make `mithi`'s author family its author in substance (X1 record option 2).

### 5.2 The firewall (every option)

- **Template authors never see the card.** No template author reads the Tier 0 or Tier 1 card, the
  no-traits or obfuscated cards, or the card-iteration transcripts. Templates are written against the
  public task-family interface (DESIGN §5.1) and the public Hearth source only.
- **Card editors never see templates.** Templates, seeds and instances live only in the Gatekeeper
  store (OWNER-QUEUE A06). Card editors (Claude development sessions) see counts, hashes and verdict
  classes only (DESIGN §4.6).
- Where a template author is a model, its sessions run under the store's account. That is the separate
  desktop account of A06 (a), whose files the Claude development sessions, which reach the desktop over
  SSH as Pierce, cannot read [inference]. Their transcripts stay in that account.

### 5.3 The three options

Template counts with one family [D]:
- **≤ 1 held-out item per template (planned):** 167–201 templates. That is 136 held-out (up to 157
  with the 15% reserve), plus 24 calibration, plus 7–20 iteration.
- **2–3 per template:** 85–114 templates at n = 160, the cap (54–80 held-out templates, plus 24,
  plus 7–10). Block 17 puts the high scenario at n = 160–192 [S]; **only n ≤ 160 is admissible under
  this record**, and n = 192 (85–130 templates) needs a signed record that raises the cap (§4.3).

Unit costs [G, X1 record option 2]: 0.5–1.5 owner hours per template; 20–40k Qwen3 output tokens at
13–22 tok/s, × 1–2 drafts, which is 0.25–1.71 desktop hours; 0.13–0.98 M Claude plan tokens.

Owner hours and plan tokens are [inference]: they rest on these per-template guesses, and none has been
measured. In the table, the second figure of each pair is 2–3 per template **at n = 160**.

| | **GEN_OWNER**: Pierce writes the templates | **GEN_QWEN3**: the local Qwen3 writes them | **GEN_CLAUDE**: Claude writes them |
|---|---|---|---|
| Matches the text Pierce accepted, "no model writes them" (D0_BRIEF Q18) | **yes** | **no**: a model family (Qwen3) authors the templates | **no**: a model family (Claude) authors the templates |
| 05 §13's guard: task authors from a family other than the card editors' | kept | kept (a different family, non-frontier) | **loosened**: the card editor's family authors. A labelled loosening that only Pierce can grant |
| Needs a new Owner answer beyond R1–R6 | no | **yes**: extends R2's pilot-only role (D0_BRIEF Q17/Q18) | **yes**: the loosening |
| Bias direction [inference] | none systematic toward either arm; Pierce's Rust-first habits shape briefs, as any author's would | none systematic toward Claude; a different family's idioms are equally foreign to Claude in both arms | **toward PASS** (the 05 §13 Goodhart concern: card editor, author and participant share priors, so items fit what Claude-in-Mithril does well). The provisional-pass rule already discounts a pass, so a kill stays credible. **One counter-mechanism, toward KILL:** an author family that is also the participant family gives Claude an edge in whichever language the author thinks in natively, usually Rust (X1 record §9, "author family = participant family"). Neither effect is measured; a kill under GEN_CLAUDE is reported with that label |
| Owner hours, ≤ 1 per template / 2–3 per template | **84–302 h / 42–171 h** [inference]: 5.6–20.1 / 2.8–11.4 weeks of all his hours at 15 h a week [D] | 1–5 h of review [G] | 1–5 h of review [G] |
| Plan tokens for templates | 0 | 0 | **22–197 M / 11–112 M** [inference] = 0.31–3.39 / 0.16–1.92 weekly windows [D, §6] |
| Desktop hours (daytime, 8-thread cap) | 12–30 h of other X1 Qwen3 work, if Q17 gives it to Qwen3 [D from G] | **54–374 h / 33–225 h** in all [D from G], against X2's fuzz weeks under the shared cap; Qwen3's tok/s under 8 threads is not measured (PLAN S71) | 12–30 h, as GEN_OWNER |
| Template quality risk | lowest [G] | highest: a non-frontier model writing bit-exact oracle models; more rejected drafts [inference] | low [G] |
| Card editing by Pierce | none; he signs the card hash only (OWNER-QUEUE C38) | allowed | allowed |

A note on readings. If Pierce reads his text as "no model writes an *item*" (items are generated from
templates), GEN_QWEN3 and GEN_CLAUDE also fit it. That reading is his to adopt, not this record's.

**No recommendation** (as D0_BRIEF Q18 and OWNER-QUEUE A04). GEN_OWNER is the only option that matches
the text Pierce accepted. GEN_QWEN3 departs from it and extends R2. GEN_CLAUDE departs from it and loosens
05 §13. Each option's main costs, side by side:
- **GEN_OWNER:** 84–302 owner hours at ≤ 1 item per template [inference], 5.6–20.1 weeks of all his
  hours at 15 h a week [D], which moves X1's verdict by months; the lowest template-quality risk [G].
- **GEN_QWEN3:** 54–374 daytime desktop hours in all [D from G], competing with X2's fuzz weeks under
  the 8-thread cap, at a tok/s not yet measured (PLAN S71); the highest template-quality risk
  [inference]; and a new Owner answer that extends R2 beyond the pilot.
- **GEN_CLAUDE:** 22–197 M plan tokens, 0.31–3.39 weekly windows [D], on top of X1's attempts, which
  §6 finds do not fit the plan at today's estimate; the loosening of 05 §13, with a bias toward PASS
  [inference].

**The choice is Pierce's.** This record does not require any one option. It requires that the template
author be named by a signed D0_BRIEF Q18 line before any sealed template exists.

---

## 6. Plan usage for the whole X1 run, and a feasibility gate

### 6.1 Estimate

Inputs:
- **Per Claude attempt:** ≈ 0.26–0.92 M tokens processed [D from G: X1 DESIGN §12.1's cumulative-input
  formula, 10–20 turns, 10–15k prefix, 5–20k output; X1 record, common facts].
- **Weekly window conversion**, from the readings recorded in COST's ledger [M]:
  - 10% at 18:17Z on 10-16 (row 1), 22% at 14:40 PT (21:40Z) and 39% at 19:40 PT (02:40Z on 10-17)
    (row 7). The weekly window resets at 12:00Z (05:00 PT) [M, `get_usage` reset time, read
    2026-10-17T03:27Z; inference: a 7-day window], so 10-16 was its first day.
  - From 10% to 39%, 29 points, the reported subagent tokens were 20,120,190 (workflow 1, row 4, and
    the build round, row 7), or 20,520,553 with row 5's toolchain agent, whose timing is not recorded.
    That is ≈ 0.69–0.71 M tokens per point [D, rough].
  - The build round alone moved it 17 points (22% to 39%) for 9,871,258 tokens: ≈ 0.58 M per point
    [D, rough].
  - So a full weekly window ≈ **58–71 M** subagent tokens [D, rough].
  - Revision 1 used "0% to 39% on 10-16" (≈ 0.50 M per point). The window did start 10-16 near 0%,
    but 10 points were already used by 18:17Z, before nearly all of the subagent tokens: the 5-hour
    window then read 3% (row 1). That figure counted other use as subagent use, and is withdrawn.

  The rough part, and which way each assumption pushes:
  - It assumes that no other use (the host session, Pierce) moved the window between the readings.
    Other use makes the true tokens per point larger, so **these figures are pessimistic for X1**.
  - It assumes that the build round ran between its two readings.
  - It assumes that the workflow's "subagent tokens" count the same things as the per-attempt estimate
    (cumulative processed tokens, including cache reads). That is **not verified**. If the workflow
    figure counts less, for example no cache reads, this conversion overstates X1's share, possibly by
    several times.

| | Value [D] |
|---|---|
| One attempt | 0.37–1.58% of a weekly window; 63–272 attempts per full window |
| X1 at n = 136, 3,456 attempts | **0.90–3.18 B tokens ≈ 13–55 full weekly windows** (12.7–54.8) |
| X1 at n = 160, 3,816 attempts | 0.99–3.51 B tokens ≈ 14–61 windows |
| X1 at n = 136 with s = 50% of each window (§2.4 P1) | **25–110 weeks** |
| Generator and transliterator (5–20 M) | 0.07–0.34 windows |
| GEN_CLAUDE templates (≤ 1 per template) | 0.31–3.39 windows |
| Smoke run, 5 / 10 / 20 / 25 / 65 attempts, if the estimate holds | 2–8% / 4–16% / 7–32% / 9–40% / 24–103% of one weekly window; §6.2 bounds the gate's own cost |

**Read plainly: at today's per-attempt estimate and this rough conversion, X1 under R4 does not fit
the plan within M0.** The X1 record's option-4b schedule puts card iteration, calibration and the
held-out runs in roughly W6–W11, about 6 weeks [G]. Fitting 3,456 attempts into 6 weeks at s = 50%
needs w ≤ w* = 0.087 window points per attempt, about 50–61k workflow-equivalent tokens [D]. That is
4 to 18 times below the estimate. Either the estimate or the conversion is far off, or R4 cannot run
as planned. Only a measurement can tell which.

**Context: the plan today.** At 2026-10-17T03:27Z (20:27 PT on 10-16) the weekly all-models window read
43%, 0.64 days into a 7-day window, and the 5-hour window read 49% [M, `get_usage`]. COST §5's weekly
pacing line, (days elapsed / 7) × 100 + 15 = 24.2 points, is exceeded [D]. Extra usage is disabled [M].

### 6.2 Feasibility gate (pre-registered here; development data, not collection)

**Definitions.**
- A = the planned Claude attempts (3,456 at n = 136); s = the signed share (§2.4 P1); K = the weeks X1
  has in the schedule (≈ 6 under Plan B [G], or a figure Pierce signs).
- w* = 100 × s × K / A, the weekly-window points per attempt at which X1 just fits. At s = 50%, K = 6
  and A = 3,456: **w* = 0.0868** [D].
- Readings are whole percentage points (§2.4 P3). The difference of two readings is therefore within 1
  point of the true change, whether the tool rounds or truncates [D]. A single attempt's change cannot
  be read at the scale of w*, so the gate works on the **cumulative change over batches**, never on a
  per-attempt median.

**Preconditions.** Pierce has answered A20 "allowed" (§2.2). The model and the effort level are the
ones to be pinned (§2.1). Public smoke items only (PLAN S70; DESIGN §5.2). No signature is needed for
the smoke run itself.

**Procedure.**
1. **The account is quiet.** From the first reading to the last, there is no Claude use on the account
   other than the gate's attempts [G]: the lead engineer pauses the agent team, and Pierce does not use
   Claude. The windows are account-wide (COST §2), so any other use would be counted as X1's. Attempts
   may run concurrently [G]. At the 45-minute attempt budget, stage 1 (5 attempts run together) takes
   at most about 1 h, and each 20-attempt batch, 5 at a time, at most about 3 h, plus the reading wait
   [D from G]. Pierce is told this before the smoke run is scheduled. §2.4 P2's stops apply, so in
   practice the gate runs soon after a weekly reset (Friday 05:00 PT [M, §2.4]), when the reading is
   low and the stop line is not yet reached [inference].
2. **Stage 1.** Read the weekly all-models percentage, r0, just before the first attempt. Run **5
   attempts** [G]. Read r1 at least 10 minutes after the last attempt ends, then again every 10
   minutes until two consecutive readings agree, and use that value [G: how quickly usage registers is
   not known, and a late reading would bias the gate toward RUNNABLE]. The account stays quiet until
   then. The same applies to every later reading. Record the 5-hour readings too, and the tokens per
   attempt as Claude Code reports them [M]. These are supporting data; the gate does not use them.
3. **Decision after every batch k**, with N_k = the attempts so far and Δ_k = r_k − r0:
   - **NOT RUNNABLE** if (Δ_k − 1) / N_k > w*;
   - **RUNNABLE** if (Δ_k + 1) / N_k ≤ w*;
   - otherwise run the next batch of **20** attempts and read again, up to **N = 65** in all (5 + 3 ×
     20) [G];
   - at N = 65 with neither, **UNDETERMINED**.
4. **Outcomes.**
   - **RUNNABLE.** The interval [(Δ − 1)/N, (Δ + 1)/N] and the token reports go into COST.md and the X1
     record §6.3 as [M] facts. X1 may freeze as planned.
   - **NOT RUNNABLE.** X1 under this amendment is not runnable as planned. The lead engineer reports
     it to Pierce with the interval. Before X1 freezes, Pierce gives a new answer: a longer X1, a
     smaller s for the team, fewer attempts by a signed record (never a moved threshold), or a
     different X1 rule. That answer is a second amendment.
   - **UNDETERMINED.** Reported to Pierce with the interval; X1 does not freeze until he answers. His
     options include more batches by a signed answer, or a token-based estimate: Claude Code's
     per-attempt token reports, converted with a tokens-per-point figure measured over a block of at
     least 20 points in which every Claude session reports its tokens on the same basis [G].
5. **If the account cannot stay quiet between batches,** each batch has its own before and after
   readings, Δ_k is the sum of the batch changes, and the ±1 in step 3 becomes ±k after k batches.
6. No X1 threshold depends on the gate.

**Properties** [D: `calc_packet.py` simulates the rule on whole-point readings, under both rounding
rules, for true w from 0 to 1.6 points per attempt, at w* = 0.0868, on a quiet account with usage
fully registered]:
- No wrong decision: RUNNABLE never occurs with w > w*, and NOT RUNNABLE never with w ≤ w*.
- RUNNABLE needs N ≥ 1 / w* ≈ 12, so stage 1 alone can only show NOT RUNNABLE. It does so whenever
  w ≥ 0.4 points per attempt. At the estimate (0.37–1.58), 5 attempts move the reading by 1.8–7.9
  points.
- UNDETERMINED occurs only for a true w between about 0.06 and 0.10.
- **The whole gate costs at most about 10 points of one weekly window, whatever the true w** (9.97 in
  the simulation), because the rule stops as soon as the readings exclude a fit. At other signed
  values the bound moves with w*: about 10 points at w* = 0.079 (n = 160) and about 13 at w* = 0.174
  (K = 12, or s = 100%). Under the step-5 variant, at w* = 0.0868: at most about 13 points, and
  UNDETERMINED is possible for any w up to about 0.15.

**Timing against the signature.** If Pierce signs this record before the smoke run, s and K are fixed
before w is measured, so the gate cannot be tuned to the result. If he signs after it, the readings
stand as recorded, and the gate is evaluated with the s and K he then signs, knowing w. The review log
and REPORT.md say which happened.

---

## 7. Threats added by one family

| Threat | Handling |
|---|---|
| The card is tuned on the participant family (bias toward pass) | Named by R4; a pass is provisional; a kill is binding (§3) |
| Template-author bias | §5.3 per option; a kill under GEN_CLAUDE carries its label |
| No averaging over families: the result describes "Claude in Claude Code" only | Stated in REPORT.md; the M1 confirmation (§3) is the general test |
| A long, paced run (§2.4) meets model or Claude Code version drift | The model ID is pinned; a withdrawal or protocol change follows X1 record §10.6; the Claude Code version is logged per attempt; pauses are logged |
| Headless controls not verified (isolation, tool disabling, effort, token reports) | The smoke run must show each before sealed content is used; a control that cannot be shown is a deviation recorded before freeze |
| Visible held-out content persisting in Claude Code transcripts | Per-attempt configuration directory, copied to the private store and deleted (§2.3) |
| Plan throttling ends attempts | Infrastructure failure, re-run (§2.3 item 7) |
| Plan readings are whole percentage points; other use on the account mixes into them | §6.2 reads cumulative batch changes with a ±1-point bound, on a quiet account, with a stated UNDETERMINED band; the effort level is pinned before the smoke run (§2.1) |
| Reviews are same-family only | Stated in the review log (§11), as everywhere in M0 |

---

## 8. Deviation and re-run policy

The X1 record §10 applies unchanged, with F = 1. Changes to this amendment after freeze are dated
amendments appended below. The planned n_final (136), the cap (160) and s (50%) may change only before
the calibration run (X1 record §6.3). The effort level (§2.1) changes only by a dated amendment, and a
change re-runs the §6.2 gate, because w depends on it.

---

## 9. What the X1 track changes in the X1 record before X1 freezes

- §2: one family row (Claude, the pinned model ID, settings "provider defaults; effort ___", the level
  signed in §10 here); Family B and C rows "none (X1-amendment-1)"; Claude Code version pinned.
- §3: "Participants: one frontier family, Claude (X1-amendment-1); the local pilot outside the kill."
- §4.4: candidates stay 184 (cap 160 × 1.15).
- §6.1: F = 1 attempt counts (§4.4 here); n_final planned 136.
- §6.2: block 13 cited beside block 16.
- §6.3: `--families 1`. Step 6: block 17 (F = 1) replaces block 4b's "about 120 in the high scenario";
  with one family the template-scenario value is 160–192 in the high scenario (192 on the MC rule) [S],
  so at the cap of 160 the upper end leads to step 5: collection waits for a new signed record.
- §6.3 and COST.md: the §6.2 gate's outputs, as [M] facts.
- §7.1–§7.2: F = 1.
- §7.6: `harness.families = 1`.
- §7.7: not applicable.
- §8: the `pass_one_family` row (§3 here).
- DESIGN §2, §4.6 and §12.1: the Claude Code runner (§2.3 here) in place of API sessions.

---

## 10. What Pierce signs

```text
X1-amendment-1      Freeze commit: ______________________
Rule (Q16):         [ ] OPT4_STRICT as written here (Claude kills; pass provisional; confirmation at M1)
Claude model:       [ ] claude-opus-5-5 (suggested default [G])   [ ] claude-fable-5-1   [ ] other: ______
Effort (§2.1):      ____ (no default; the smoke run uses it)   [ ] Claude Code's own level, if not settable
Runner (D07):       [ ] accept: Claude Code plan, headless, isolated configuration, provider-default
                        sampling, effort pinned
Plan check (A20):   [ ] I checked the plan's terms: scripted headless attempts allowed
                    [ ] not yet checked (the smoke run waits, and X1 may not freeze, until I have)
                    [ ] not allowed
Share s (§2.4):     ____ % of each weekly window (suggested default 50% [G])
Cap:                [ ] 160 (suggested default [G])   [ ] other: ____
Feasibility gate:   [ ] as §6.2   (K = ____ weeks; suggested default 6 [G])
Template author:    decided by a signed D0_BRIEF Q18 line, not here
Owner: ______________________   Date: __________   Signed tag: ______________________
```

The signature is a signed tag over the freeze commit ([HOW-TO-SIGN](../sittings/2026-10-18/HOW-TO-SIGN.md)).
The block above is a readable mirror and is not edited after freeze. Pierce's choices go in the tag
message.

---

## 11. Review log

| Date | Reviewer | Family | Context | Scope | Result |
|---|---|---|---|---|---|
| 2026-10-16/17 | review 1: one reviewer agent, adversarial; it read this record with the sitting-1 PACKET and HOW-TO-SIGN, against D0_BRIEF, OWNER-QUEUE, OWNER-ANSWERS, COST, the X1 record and the simulator | Claude, same family | independent context | Lenses: fair presentation against the sources; order of owner decisions against OWNER-QUEUE; statistical soundness of the feasibility gate; the arithmetic of the token-to-window conversion; reproduction of the F = 1 simulation; consistency with the X1 record's §6.3 | **11 findings (5 major, 6 minor) across the three files; all 11 accepted, 0 rejected.** In this record: (1, major) §5.3 brought back a GEN_QWEN3 recommendation that D0_BRIEF Q18 and OWNER-QUEUE A04 had withdrawn, through a "Reading B": replaced by no recommendation, a neutral note on readings and each option's costs side by side; (3, major) A20 precedes R4's ratification: §2.2 says so and adds that the smoke run waits for A20 [G, a tightening]; (5, major) the gate could not resolve its own threshold from whole-point readings with a per-attempt median: §6.2 rewritten as a sequential rule on cumulative batch changes with a ±1-point bound, a quiet account, a cap of 65 attempts and an UNDETERMINED outcome, simulated (no wrong decision; at most ≈ 10 points of one window); effort pinned and added to §10; (6, minor) the conversion rested on an unrecorded "0%": rebased on the recorded 10% → 39%, window ≈ 58–71 M, X1 ≈ 13–55 windows, with the direction of each assumption; (11, minor) 2–3 items per template exceeds the cap at n = 192: §4.2, §4.3, §5.3 and §9 (§6.3 step 6) annotated. The rest concern the packet and HOW-TO-SIGN, and are logged in the packet. The reviser also read the plan's reset time and the 43% reading (§2.4, §6.1) [M]. A second-family review is not possible under R1 and R2 |
| — | — | — | — | — | Still open before freeze: the lead engineer checks that this revision answers review 1; a further same-family review is optional [G] |

---

## Amendments

None.
