# X1: cold-agent writability with all arms

Status: DRAFT; **X1 rule answered in chat 2026-10-16** (Claude kills, pass provisional; ratify at
sitting 1 via a signed amendment record; [OWNER-ANSWERS.md](../OWNER-ANSWERS.md), batch 2);
**template author ([D0_BRIEF](../../D0_BRIEF.md) Q18) still open**, with the Qwen3 roles (Q17) and the
plan check (OWNER-QUEUE A20). As designed, X1 needs ≥ 2 frontier families, a non-Claude family to
author sealed items and metered spend; the Owner's chat answers of 2026-10-16 provide none of them,
and the section "X1 under the 2026-10-16 owner constraints" (below) sets out the rule he chose and
what remains open. Track x1, 2026-10-16; revised the same day after two independent same-family
reviews (§12), again by the owner track the same day (restructure section), and once more after one
review of that section (same family, independent context; §12). No data may be collected under this
record.
ROADMAP anchor: [§3.2](../../ROADMAP.md#32-x1-cold-agent-writability-with-all-arms-weeks-05); §1 rules 1–5;
§4 (kill outcomes); §10 (measurement budget); §11 (D0-9, D0-10, D0-11, D0-12). DR-002, DR-003, DR-004,
DR-005, DR-013, DR-017.
Harness design: [experiments/x1-harness/DESIGN.md](../../../experiments/x1-harness/DESIGN.md).
Power analysis: [experiments/x1-harness/power/](../../../experiments/x1-harness/power/) (script,
seed 20261016, results).
Owner authorisation: **none.** Collection, including the calibration run of §6.3, needs this record
FROZEN and either SIGNED or covered by an explicit Owner instruction
([docs/m0/README.md](../README.md#pre-registration-lifecycle-roadmap-1-rule-1-d0-12)). Under the
Owner's chat answer to D0-12 of 2026-10-16 ("Batch weekly review"; pending ratification), only X0 has
an instruction; this record is signed at a weekly sitting (Sunday evenings, sitting 1 on 2026-10-18,
per his batch-2 answer) before any collection.

Every number carries an evidence tag: [M] measured, [D] derived, [S] simulated, [G] judgment,
[inference], [target]. Thresholds copied from ROADMAP §3.2 keep its [target] label. Where this record
makes a ROADMAP rule more precise, it says so; it never loosens one. Every choice that belongs to the
Owner is marked *provisional, pending D0-x*. "[S]" numbers come from
[x1_power_sim.py](../../../experiments/x1-harness/power/x1_power_sim.py) (blocks named per
[x1_power_tables.md](../../../experiments/x1-harness/power/results/x1_power_tables.md)), run on
2026-10-16 by this track on the shared laptop; all simulation inputs are [G].

---

## X1 under the 2026-10-16 owner constraints

*Added 2026-10-16 by the owner track (a Claude agent) and revised the same day after one review
(Claude, same family, independent context; §12). The X1 rule is answered in chat (D0_BRIEF Q16 =
option 4b, below), pending ratification by a signed amendment record; D0_BRIEF Q17 and Q18 are open.
Where this section conflicts with §§2–13 or with [DESIGN](../../../experiments/x1-harness/DESIGN.md),
this section governs until the Owner's answers are ratified and Q18 is answered; the X1 track then
revises §§2–13 to the chosen option. Arithmetic: `scratchpad/owner/calc.py` and `calc2.py` [D].*

### Why X1 cannot run as designed

As designed, X1 rests on three things:
1. **At least two frontier families carry the kill** (ROADMAP §1 rule 5, §3.2; DR-017).
2. **Non-Claude authors.** Task authors come from a family other than the card editors' (05 §13), and
   the planted corpus from a family other than `mithi`'s author (ROADMAP §3.2). Claude edits the card
   and builds `mithi` (DESIGN §2).
3. **Metered spend**: ≈ 5.7k frontier attempts at n = 96 across the two families [D: 4,032 held-out
   + 1,200 card iteration + 480 calibration, §6.1], plus Family B's authoring and reviews; $5.6–18.9k
   in all [D, DESIGN §16].

The Owner's chat answers of 2026-10-16 are logged verbatim, with the option text he saw, in
[OWNER-ANSWERS.md](../OWNER-ANSWERS.md) (commit `11210a8`; [D0_BRIEF §0](../../D0_BRIEF.md)). Status:
decided by Pierce in chat; not yet AUTHORITY facts until a `d0-sign-<n>` tag ratifies them; work
proceeds on them provisionally. Batch 1: no metered API; Claude, through the Claude Code plan, is the
only frontier family; the local Qwen3 served by Hearth runs the ROADMAP pilot ("reported but not part
of the kill", in the option text he saw). So items 1 and 3 cannot be met, and item 2 only by the
Owner, by a generator whose templates someone writes, or by Qwen3 if a new answer gives it that role.
ROADMAP §11's "if declined" mechanism for D0-10 therefore applies to X1: **no X1 kill can be evaluated
as ROADMAP defines it.**

**The Owner's X1 rule (batch 2).** Asked which rule to draft for his signature, Pierce answered
"Claude kills; pass provisional (Recommended)". The option text he saw: "Claude alone can fire the
kill (VP@1 gap >15, or CABW >5 worse than Rust). A pass is only provisional until a second frontier
family confirms it at M1. Claude also edits the card, which biases toward passing, so a kill is the
more trustworthy signal. Sealed items are generated from templates with deterministic oracles, so no
model writes them." That is option 4b with option 2's generated suite below. It supersedes the
batch-1 option text's "X1 cannot pass or kill and stays amber", pending ratification. It is to be
drafted as a signed amendment record. It leaves open who writes the templates (D0_BRIEF Q18, with the
caveat in option 2 below) and whether his plan's terms and capacity carry it (OWNER-QUEUE A20).

Every option below is an amendment the Owner signs. None changes a ROADMAP threshold: 15 points on
VP@1, 5 points on CABW, ≥ 60 held-out items, kill operating characteristics ≤ 10% at a 5-point gap
and ≥ 90% at 25, 8 checker calls per task, ≥ 95% mutant kill and ≥ 100 planted items all stay, as do
this record's stricter R-CABW and R-JOINT (§6.2).

### Facts common to every option

- **Claude as participant runs through the Claude Code plan, not the API.** The runner (DESIGN §12.1)
  would drive headless Claude Code sessions restricted to the harness tools (`read_file`,
  `write_file`, `check`, `submit`, …), from an empty working directory, with an isolated
  configuration so that no Mithril design file, memory or project instruction reaches a "cold"
  attempt. How far a Claude Code session's system prompt, tool set and configuration can be fixed is
  not verified [not verified]. Sampling parameters cannot be pinned the way §2 asks [inference]; the
  model ID can be pinned per session [inference]. Results then describe "Claude in Claude Code", which
  is also the agent setting Mithril targets [inference].
- **Plan usage per Claude attempt** ≈ 0.26–0.92M tokens processed [D: DESIGN §12.1's cumulative
  input ≈ prefix·t + 1.5k·t², inputs G: t = 10–20 turns, prefix 10–15k, plus 5–20k output]. One
  family's full share is 2,856 attempts at n = 96 [D: 2,016 held-out + 600 card iteration + 240
  calibration] and 3,816 at the cap n = 160 [D]. That is ≈ 0.73–2.63 billion tokens at n = 96 and
  ≈ 0.97–3.51 billion at n = 160 [D]. For scale, workflow 1 of 2026-10-16 (30 agents) used 10,248,932
  subagent tokens [M, workflow report]; X1's Claude share is ≈ 71–256 such workflows at n = 96 [D].
  How the plan's 5-hour and weekly windows convert to tokens is not known [unknown]. **This is the
  largest feasibility risk of every option.** A measured smoke run, 20–40 attempts on the public
  smoke set (DESIGN §5.2; not collection), should precede any freeze and give tokens per attempt and
  window percentage per attempt [M] in place of these estimates.
- **The plan's terms and its other users.** Whether the Claude Code plan's terms allow scripted,
  headless harness attempts at this volume is not verified; Pierce checks that himself, and agents do
  not interpret the terms (OWNER-QUEUE A20). The plan's windows are account-wide ([COST §2](../COST.md)),
  so for about six weeks X1 would take a large, so far unmeasured share of them, and the M0 agent team
  and Pierce's other Claude use would slow down [inference]. If either is unacceptable, the X1 rule
  cannot run as planned and needs a new answer before freeze.
- **The local Qwen3** runs in daytime only, never in a quiet window (DR-023, ROADMAP §3.2), and counts
  against the 8-thread total Mithril desktop cap that X0, X2 and X3 share. Its tok/s under 8 threads is
  not measured (PLAN Q18). ROADMAP's planning figure is 5–10 minutes per agentic attempt [inference,
  ROADMAP §3.2]. That may be several times too low if Hearth's server re-prefills the whole context
  every turn [inference]: Hearth's measured prefill is 226 tok/s on a 2,048-token prompt [R11], and a
  20-turn attempt reads several hundred thousand tokens in all [D, formula above]. Hearth's tool-call
  support and usable context length are not verified (DESIGN §15). Text-only roles (authoring,
  review) need no tool calls. **Any Qwen3 role beyond the pilot is a new decision** (D0_BRIEF Q17,
  Q18): the D0-10c option text Pierce chose described only the 60-attempt pilot outside the kill.
- **Contamination.** Whatever a Claude participant reads (visible bundles only) goes to Anthropic under
  the plan's data-use setting, which is not verified [not verified]; Owner question 4 now concerns
  that setting. Qwen3 output never leaves the desktop. Under every option hidden bundles never reach
  a Claude session, and the family-A firewall (DESIGN §4.6) applies to the desktop, where Claude
  sessions also run over SSH, so any authoring there needs a separate account that no Claude session
  can read (D0-9b's gate account would serve); Claude settings deny rules alone are weak there,
  because agents reach the desktop over SSH as Pierce [inference] (OWNER-QUEUE A06).
- **One kill-carrying family needs a larger n.** With F = 1, the per-family standard deviations at
  n = 96 are 3.2–3.8 points for VP@1 and 3.6–4.5 for CABW, against 2.5–3.2 pooled [S, block 11]. The
  power simulation must be extended to F = 1 and re-run before freeze; this round did not run it.
  n_final is expected to rise [inference]. If no n ≤ 160 meets R-VP, R-CABW and R-JOINT, §6.3 step 5
  applies: collection waits for a new signed record, and no threshold moves.
- **Roles that 05 §13 and DESIGN §2 give to "family B or C"** (item reviewers, the semantic guard, the
  kit acceptance corpus, half the scorer canaries, defect-claim confirmers) fall to the Owner, or to
  Qwen3 by a new answer (D0_BRIEF Q17), under every option.

### Option 1: two families, one of them local

*Shown for completeness. It contradicts the D0-10c option text Pierce chose (the pilot is "not part of
the kill") and his batch-2 X1 rule.*

- **Design.** Claude (card editor and participant) and Qwen3 via Hearth (author of every sealed
  item, the planted corpus and the item reviews; participant) both carry the kill. The pooled
  estimand and statistics of §7 stay as written (F = 2).
- **DR-017's kill.** Binding in form. ROADMAP §3.2 says "at least two frontier families", and Qwen3
  is not frontier [inference], so §3.2 is amended. Whether that loosens the kill is unknown: floor
  effects (a weak model near zero in both arms) pull Qwen3's gap and the pooled Δ toward 0, while a
  weaker model may also suffer more from unfamiliar syntax, which widens it [inference; neither is
  measured]. A pre-registered eligibility floor (Qwen3 carries the kill only if its Rust VP@1 on the
  calibration set reaches a level the X1 track proposes before freeze) keeps the reading honest; if
  Qwen3 misses the floor, X1 falls to option 4's rules, decided by the frozen text, not after data.
  Qwen3 both writes and attempts the items, so D0_BRIEF Q15 must be YES and the author × arm
  interaction of §9 cannot be removed.
- **Cost.** Claude ≈ 0.73–2.63 billion tokens [D]. Qwen3: participant attempts ≈ 238–476 h [D:
  2,856 × 5–10 min]; whole-item authoring, planted corpus and reviews ≈ 50–312 h [D from G: 228 items ×
  15–30k output tokens at 13–22 tok/s [measured decode rates: 13.02 tok/s at a 2 GiB cache, R11;
  19–22 tok/s cached, noisy, ROADMAP §7; thread count not verified], × 1–2 for rejected drafts, plus
  200 planted items and 228 reviews]; ≈ 288–788 daytime desktop hours in all [D]. Owner hours as in DESIGN §16 (≈ 45 h).
- **Schedule.** 288–788 h is ≈ 3–8 weeks of the whole 8-thread daytime cap at 14 usable hours a day
  [D; 14 h/day is G], during which X2 fuzzing, X3 builds and X0 re-runs cannot use the desktop. X1's
  verdict moves from ≈ W11–W12 (PLAN Plan B) to roughly W14–W20 [G].
- **Contamination.** Lowest for authoring (local). Claude participants as in the common facts.
- **Pierce signs.** An amendment of ROADMAP §3.2's "frontier" for M0, with the eligibility floor;
  D0-10c's roles (Qwen3 as author and participant); D0_BRIEF Q15 = YES; a daytime-capacity allocation between
  Qwen3 and X0, X2 and X3 (PLAN Q18).

### Option 2: a generated suite (an authoring method; pairs with option 1 or 4)

- **Design.** A deterministic generator instantiates sealed items from parametric templates. 05 §13
  already describes items as "parametric variants within a family (formats, tie rules, sizes, failure
  modes)". Each template carries a brief template, stubs, Rust and C11 references and a bit-exact
  oracle model with vector generators. The Gatekeeper seals the seeds and the template-to-split
  assignment. Mutant kill (≥ 95%), reference agreement and the contamination check run mechanically, as
  now (DESIGN §4.5, §6.2). Mithril references come from a deterministic Rust-to-X1-subset
  transliteration tool where it succeeds (a public tool Claude may write), and from the template
  author otherwise. No model family writes a held-out *instance*.
- **What it does not settle.** Who carries the kill: pair it with option 1 or 4 (the Owner's X1 rule
  pairs it with 4b). **Who writes the templates.** The template carries the authorship and the
  item-level variance, so 05 §13's guard applies to it. The Owner's X1 rule says "no model writes"
  the sealed items; the template author is still a separate choice (D0_BRIEF Q18), and no default is
  given:
  - **the Owner** (GEN_OWNER): the reading that matches "no model writes them" (option 3's costs);
  - **Qwen3** (GEN_QWEN3): meets 05 §13's guard, but a model family then authors the templates, which
    departs from the summary he accepted and extends the D0-10c pilot answer;
  - **Claude** (GEN_CLAUDE): would need 05 §13's guard amended, because the card editor would become
    the author, a Goodhart risk toward passing on top of the card bias his X1 rule names. A labelled
    loosening only Pierce can grant; not recommended. ≈ 9–200 million plan tokens [D from G: a
    Claude Code authoring session of 5–10 turns, 15–30k prefix, 20–40k output, × 1–2 drafts, ≈ 0.13–
    0.98 M tokens per template, over 71–204 templates], about 1–20 times workflow 1.

  The planted corpus stays with a non-Claude author too: a Claude-written mutation engine would make
  `mithi`'s author family its author in substance.
- **Sample-size consequence.** Items from one template are correlated, so generation does not cut the
  template count. Two counts, which every cost below carries:
  - **≤ 1 held-out item per template (§4.3, as designed):** ≈ 127–204 templates [D: n_final 96–160
    + 24 calibration + 7–20 iteration templates].
  - **2–3 held-out items per template:** the high scenario needs n ≈ 120 with a template-clustered
    analysis [S, block 4b, F = 2], that is ≈ 71–94 templates [D: 40–60 held-out + 24 calibration +
    7–10 iteration]. This count rests on an F = 1 simulation that has not been run and on a change
    to §4.3 that Pierce would sign (Owner question 10).
- **Cost.** Generator and transliterator by Claude ≈ 5–20 million tokens [inference: about 0.5–2
  workflow-1 equivalents]. Templates by Qwen3: ≈ 32–349 daytime desktop hours at ≤ 1 item per
  template, or ≈ 18–161 h at 2–3 [D from G: 20–40k output tokens per template at 13–22 tok/s, × 1–2].
  Templates by the Owner: ≈ 64–306 h at ≤ 1 item per template, or ≈ 36–141 h at 2–3 [D from G:
  0.5–1.5 h each].
- **Contamination.** Lowest of all: instances do not exist until they are sealed. Templates that
  follow Hearth's public code paths (T-Q4, T-ACTQ) are caught by the existing `public_near` check.
- **Pierce signs.** The generation method and the template author (D0_BRIEF Q18), in this record before freeze.

### Option 3: Owner-authored items (an authoring method; pairs with option 1 or 4)

- **Design.** Pierce writes the held-out and calibration templates or items, with Rust and C11
  references; the mechanical gates stay; Mithril references by transliteration or by Pierce; the
  planted corpus by Pierce, or by Qwen3 if a new answer allows it.
- **Independence.** The strongest of all options: a human author shares no model priors with the
  card editors. It holds only if Pierce drafts without a Claude session's help, and he then cannot
  review card edits before the card freeze (§9, "the Owner as a channel"; Owner question 17 becomes
  "sign the card hash only").
- **Cost.** Whole items: ≈ 228–456 owner hours [D from G: 228 items × 1–2 h], not feasible at 15 h a
  week. As templates for option 2: ≈ 64–306 h at ≤ 1 held-out item per template, or ≈ 36–141 h at
  2–3 [D from G], on top of DESIGN §16's ≈ 45 h.
- **Schedule.** At 15 h a week, +64–306 h is ≈ 4–20 more weeks and +36–141 h ≈ 2–9 [D], so X1's
  verdict moves to roughly W15–W32 or W13–W21 [G].
- **Contamination.** Lowest.
- **Pierce signs.** His authoring role and hours, a cost change rather than a threshold change; Owner
  question 17's new form.

### Option 4: one frontier family at M0; DR-017's binding two-family test when a second family exists

Two forms. Both use option 2's generated suite with the template author of D0_BRIEF Q18 (the Owner,
or Qwen3 by a new answer), the planted-corpus author of D0_BRIEF Q17 (the Owner or Qwen3), and Qwen3
for the ROADMAP pilot (60 attempts, reported, 5–10 daytime hours [inference, ROADMAP §3.2]).

- **4a, referral form (as first framed).** Claude carries X1 alone. A breach (K1 or K2) becomes an
  Owner referral instead of STOP-L, and DR-017's binding test moves to M1 once a second family exists.
  **This loosens ROADMAP §4's X1 row**: an X1 breach would no longer stop the standalone surface, the
  cheap early stop that M0 exists for. Not recommended.
- **4b, strict form (the Owner's chat answer of 2026-10-16, "Claude kills; pass provisional";
  pending ratification by a signed amendment record).**
  - Claude is the only kill-carrying family at M0 (F = 1). The estimand of §7.1 becomes Claude's, and
    n is recomputed for F = 1 as above.
  - **A breach stays binding:** K1 or K2 on Claude's estimate is the X1 kill, STOP-L (ROADMAP §4), with
    the `standalone_surface` tombstone, whose `models` field then names one family. The one-family
    design's main known bias runs in Mithril's favour: the card is tuned on Claude, the family that
    then attempts the items [inference]. A breach despite that bias is therefore conservative
    evidence. Author bias is removed, because the template author (the Owner or Qwen3) is not a
    participant.
  - **A pass is provisional** (`pass_one_family`). It is not DR-017's pass. The binding two-family
    test runs as soon as a second frontier family exists, on a fresh sealed batch built as M1's is
    (ROADMAP §5) and drawn from the unspent reserve, with both families, pooled as §7 says; its result
    is X1's DR-017 verdict, and a breach then is the kill. It must run before M1's DR-017 gate is
    evaluated, which agrees with the Owner's wording "until a second frontier family confirms it at
    M1"; the amendment record uses his wording [G].
  - **The M0 verdict** treats `pass_one_family` as neither pass nor kill. Rows that need X1 = pass (the
    "X2 kill alone" clause) stay undecided, and the M0 verdict may be signed with X1 open (PLAN §3.8,
    pending PLAN Q7). M1 work may start.
  - **Standing gap.** Under the 2026-10-16 answers no second frontier family is planned. If none ever
    exists, the pass never becomes binding, and M1's own DR-017 kill, which also needs ≥ 2 families,
    cannot be evaluated either. A tombstone records this, with a trigger on the number of frontier
    families in the harness (`harness.frontier_families >= 2`, a fact the harness would write), so
    `mithc revisit` reopens it.
  - **Cost.** Claude ≈ 0.73–2.63 billion tokens at n = 96, ≈ 0.97–3.51 billion at n = 160 [D], plus
    5–20 million for the generator [inference], on a plan whose windows are account-wide (the common
    facts: for about six weeks the agent team and Pierce's other Claude use slow down [inference];
    OWNER-QUEUE A20). Qwen3, besides any templates: ≈ 1–4 h for 200 planted items, ≈ 6–15 h for item
    reviews and 5–10 h for the pilot, ≈ 12–30 h [D from G and inference]. With Qwen3 templates
    (GEN_QWEN3), ≈ 44–378 daytime hours in all at ≤ 1 held-out item per template (§4.3, as
    designed), or ≈ 30–190 h at 2–3 per template [D]. With Owner templates (GEN_OWNER), Qwen3 ≈ 12–30
    h and Owner +64–306 h or +36–141 h. Owner hours otherwise as in DESIGN §16 (≈ 45 h), with the
    post-freeze sample review covering 24 templates instead of 24 items (≈ 4–8 h instead of
    ≈ 3.2 h [G]).
  - **Schedule.** With Qwen3 templates: authoring in daytime W1–W5 alongside X2 fuzzing under the
    shared cap; sealing ≈ W5–W6; card iteration and calibration ≈ W6–W9; held-out runs ≈ W10–W11.
    That keeps PLAN Plan B's X1 verdict at ≈ W11–W12 [G], **if** the plan's token windows carry
    0.7–3.5 billion tokens over about six weeks, which is not known, and if the template count is at
    the low end: at ≤ 1 item per template, up to ≈ 349 template hours do not fit W1–W5 under the
    shared cap [inference], and the verdict date is not re-derived here. With Owner templates, X1's
    verdict moves to ≈ W15–W32 or ≈ W13–W21 (option 3) [G].
  - **Contamination.** As option 2.
  - **Pierce signs.** (i) The amendment for M0: F = 1, breach binding, pass provisional, the
    confirmation rule and its trigger, so that ROADMAP §1 rule 5 and §3.2 apply at confirmation (D0_BRIEF Q16).
    (ii) The generated suite and its template author (D0_BRIEF Q18), and the planted-corpus and
    review roles (D0_BRIEF Q17). (iii) The M0-verdict state `pass_one_family` (PLAN Q7). (iv) The
    Claude Code runner: unpinned sampling and an isolated configuration (a new Owner question for
    this record; OWNER-QUEUE D07). (v) His check of the plan's data-use setting (Owner question 4) and
    of its terms and capacity (OWNER-QUEUE A20).

### Comparison

| | Option 1 | Option 4a (+ 2) | **Option 4b (+ 2), Qwen3 templates** | **Option 4b (+ 2), Owner templates** |
|---|---|---|---|---|
| Status | contradicts D0-10c's option text and the X1 rule | not recommended (a loosening) | 4b is the Owner's chat answer; Qwen3 templates are one answer to D0_BRIEF Q18, open | 4b is the Owner's chat answer; Owner templates are one answer to D0_BRIEF Q18, open |
| Kill-carrying families at M0 | Claude + Qwen3 | Claude | Claude | Claude |
| An X1 breach at M0 | STOP-L (pooled, "frontier" amended) | Owner referral (a loosening) | STOP-L | STOP-L |
| An X1 pass at M0 | DR-017 pass | provisional | provisional until a second frontier family confirms | provisional |
| Sealed items written by | Qwen3 (whole items) | generator, templates per Q18 | generator, Qwen3 templates | generator, Owner templates |
| Matches "no model writes them" (the X1 rule's text)? | no | as 4b, by template author | no: a model writes the templates | yes |
| Claude plan tokens, n = 96 [D] | 0.73–2.63 B | 0.73–2.63 B | 0.73–2.63 B (more if F = 1 raises n) | same |
| Qwen3 daytime desktop hours, ≤ 1 held-out item per template (§4.3, as designed) [D] | ≈ 288–788 | as 4b, by template author | ≈ 44–378 | ≈ 12–30 (no templates) |
| Qwen3 hours, 2–3 per template (needs an F = 1 simulation not yet run and a §4.3 change Pierce signs) [D] | — | as 4b, by template author | ≈ 30–190 | ≈ 12–30 |
| Extra owner hours, ≤ 1 per template [D from G] | ≈ 0 | as 4b, by template author | ≈ 1–5 | ≈ 64–306 |
| Extra owner hours, 2–3 per template [D from G] | — | as 4b, by template author | ≈ 1–5 | ≈ 36–141 |
| X1 verdict under Plan B [G] | ≈ W14–W20 | as 4b, by template author | ≈ W11–W12, if the token windows suffice and the template hours fit W1–W5 | ≈ W15–W32 (≤ 1 per template) or ≈ W13–W21 (2–3) |
| Contamination of held-out content | local authoring; low | lowest | lowest | lowest |
| ROADMAP text amended (signed) | §3.2 "frontier" | §4's X1 row and §1 rule 5 at M0 | §1 rule 5 and §3.2 at M0, pass side only | as 4b |

The Qwen3 hours for "Owner templates" are the pilot, the planted corpus and the reviews only [D].
Every option also carries the plan-capacity cost of the common facts (OWNER-QUEUE A20).

### The Owner's choice (chat) and what remains open

**Chosen in chat, 2026-10-16 (batch 2), pending ratification:** option 4b's rule, "Claude kills; pass
provisional" (D0_BRIEF Q16 = OPT4_STRICT), with option 2's generated suite. It keeps every ROADMAP
threshold and keeps an X1 breach binding, so the cheap early stop that M0 exists for still works. It
gives up a two-family pass at M0: DR-017's pass waits for a second frontier family, possibly
indefinitely under the current answers, and that gap stays visible in the M0 verdict and in a
tombstone.

**Still open before X1 can write a sealed template or freeze:**
1. **The template author** (D0_BRIEF Q18; OWNER-QUEUE A04): no default, because the Owner's text says
   "no model writes them" and the earlier default, Qwen3, is a model. GEN_OWNER matches the text and
   costs owner hours and weeks; GEN_QWEN3 keeps the schedule and departs from the text; GEN_CLAUDE is
   a labelled loosening.
2. **The Qwen3 roles** (D0_BRIEF Q17; OWNER-QUEUE A05), including whether passes resting on Qwen3 stay
   provisional.
3. **The plan's terms and capacity** (OWNER-QUEUE A20), the Gatekeeper store (A06) and the Claude
   Code runner (D07).
4. **The template count**: ≤ 1 held-out item per template as §4.3 says, or 2–3 with a
   template-clustered analysis (Owner question 10), after the F = 1 simulation is run.
5. **The amendment record** itself, drafted and frozen, then signed at a sitting.

**What would restore ROADMAP's design**, for completeness only and against the D0-10a and D0-10c
answers: a second frontier family's participant attempts alone, ≈ 2,856 attempts at n = 96, about
$1.4–5.7k at ROADMAP §10's $0.5–2 per attempt [D]; ≈ 2,040 attempts and $1.0–4.1k at ROADMAP's own
60-item size [D]. Its authoring would still go to the Owner, a generator or Qwen3. This is not
recommended over the Owner's answer; it is listed so that the price of the gap is visible.

**Until those are answered.** The X1 track builds only family-agnostic parts: grammar, cards, `mithi`,
kit, runner, scoring, the generator engine and the power code, including F = 1 support. It writes no
sealed content and runs no attempt on any sealed or Hearth-derived item. The smoke run above is
development on public items, not collection, and needs no signature.

---

## 1. Assumption under test, and what follows if it is false

**Assumption** (ROADMAP §3): "Cold agents write Mithril nearly as well as Rust."

Operationally: on sealed, Hearth-shaped tasks, frontier agents from at least two model families,
given paper Mithril with the Tier 0 and Tier 1 cards and `mithi` as checker, reach a verified pass@1
no more than 15 points below what they reach in Rust, and their checker-accepted-but-wrong rate is no
more than 5 points worse than in Rust.

**If it is false** (ROADMAP §3.2, §4): the X1 kill fires (DR-017). "The standalone surface then stops,
and Mithril ships as checker, ledger and tooling over Rust/C." The outcome class is **STOP-L**; with an
X2 kill as well it is **STOP-ALL** (ROADMAP §4). The kill writes the `standalone_surface` tombstone of
ROADMAP §4, with `verdict` copied from this record's outcome (`vp1_gap`, `cabw_gap` or both).

**Caveat** (ROADMAP §3.2): "Mithril has no full diagnostics yet, so this gap is pessimistic."

---

## 2. Inputs pinned

Everything below is recorded **at freeze** unless a different point is named. Placeholders are marked
`‹at …›`.

| Input | Value |
|---|---|
| Hearth source (task domain and part of the public corpus) | `b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220`, GitHub `main` as of 2026-10-16 [M, read by this track] |
| Mithril repository | the commit that freezes this record |
| Model family A (participant; card editor) | ‹at freeze›: provider, model ID, version or snapshot date, reasoning setting, sampling parameters (provisional, pending D0-10) |
| Model family B (participant; task, planted-corpus and item-review author) | ‹at freeze› (provisional, pending D0-10, D0-11) |
| Optional family C (author or reviewer only) | ‹at freeze, if the Owner provides one› |
| Local pilot model | ‹at freeze›: model, container hash, Hearth commit, context length (provisional, pending D0-10) |
| Sandbox image | `x1-toolchains@sha256:‹at freeze›`, containing rustc/cargo ‹version›, Clang ‹version›, `mithi`, the kit, helper packs, drivers, static gate |
| `mithi` | source commit ‹at the checker precondition›; binary SHA-256 ‹idem›; re-recorded after every permitted change (DESIGN §9.6) (ROADMAP §3.2: "`mithi`'s hash is frozen in the pre-registration") |
| M0 tooling kit (`x1-holes`, `x1-fflint`) | commit and hash ‹at freeze›, or "not ready" (§3) |
| Grammar `mithril-x1.lark` | SHA-256 ‹at freeze› |
| Cards and shared texts | Tier 0, Tier 1, no-traits and obfuscated cards; the Rust, C11 and kit **helper cards**; the **shared domain preamble** (all arms): SHA-256 each ‹at card freeze› (DESIGN §7.1, §10.2) |
| Token map `obf-v1` | SHA-256 ‹at freeze› |
| Core-calculus note, X1 subset rules | commit ‹at the checker precondition› |
| Suite | `COMMITMENTS.json` SHA-256, suite root R, canary UUID, committed **in its own commit at sealing**, before card iteration (DESIGN §4.1) ‹at sealing›; later dated re-commitments listed here |
| Calibration set | 24 sealed items, positions in `COMMITMENTS.json` (split `calibration`) ‹at sealing› |
| Planted corpus | dev half and confirmation half (≥ 100 items each [target]): SHA-256 of each sealed half ‹at the checker precondition› |
| Contamination corpus | Hearth `b5d3f14…`; Mithril HEAD ‹at sealing›; llama.cpp/ggml commit ‹at sealing›; MultiPL-E commit ‹at sealing› (DESIGN §4.5); re-run against the freeze commit |
| Keys | fingerprints of the Runner key and the per-split Gatekeeper keys ‹at sealing› (DESIGN §4.2) |
| Seeds | sealing order, run order, subset draws, sample review, bootstrap: ‹at freeze› |
| Analysis scripts | `experiments/x1-harness/analysis/` (`score.py`, `calibrate.py`, `analyze.py`, `verdict.py`) commit ‹at freeze› |
| Power analysis | `experiments/x1-harness/power/x1_power_sim.py` at the freeze commit, seed 20261016 |
| Price table | provider list prices with date and source URL ‹at freeze› |
| Execution host | ‹at freeze› (provisional, pending D0-10: desktop WSL2 in daytime under the family-A firewall of DESIGN §4.6, or a rented Linux VM) |
| Pilot host | the desktop (Ryzen 9 9950X), daytime only, never in a quiet window (DR-023) |

---

## 3. Arms / configurations

The six arms, verbatim from ROADMAP §3.2. All six run from day one; the tooling arm runs only if its
kit is ready.

| Arm | What the agent gets (ROADMAP §3.2) | Items × attempts per cell | Role |
|---|---|---|---|
| Mithril | Paper Mithril, Tier 0+1, `mithi` as checker, static-dispatch traits (DR-005) | n_final × 5 | kill (both co-primaries) |
| Mithril without traits | Traits rejected by a Dc diagnostic, so the cost of their absence is measured (DR-005) | 64 × 3 | amber (b); DR-005 |
| Rust | rustc/cargo, same oracles and checker-call budget | n_final × 5 | kill comparator (DR-017) |
| C11 | Clang, same oracles | 64 × 3 | descriptive |
| Rust + Mithril tooling | Rust plus the M0 tooling kit (above): the false-friend lint pass over Rust, `todo!()` hole context through rust-analyzer, the same check loop. `mithc lift` and full diagnostics join at M1, so at X1 this arm is a floor for the cheapest competitor | n_final × 5 | amber (a) |
| Obfuscated Mithril | Same semantics with renamed keywords. Separates comprehension from guessability [P1 §7.11] | 64 × 3 | descriptive (familiarity gap FG) |

- **Primary arms** (Mithril, Rust, Rust + tooling) run 5 attempts per cell; **secondary arms** run 3,
  as in ROADMAP §10's measurement table. Secondary arms use a 64-item subset: the first 8 items per
  task family of the decision set (§4.4) in the seeded sealing order, which is itself a seeded random
  order. 64 rather than §10's 60 keeps the strata balanced.
- **Kit not ready.** ROADMAP §3.2: "If the kit is not ready when the held-out runs start, the arm is
  dropped from X1 and starts at M1, and amber (a) waits for M1." Readiness is DESIGN §8.3's criterion.
- **Equal across arms** (05 §13): the item brief; the **shared domain preamble** (every domain-rule
  atom found during card iteration, DESIGN §10.2); the oracles; the visible tests' content; the
  **checker-call budget of 8 per task** [target, ROADMAP §3.2, P5]; the turn, token and wall-time
  budgets of DESIGN §3.2 [G], with tokens counted **excluding each arm's fixed system-prompt prefix**
  (§4.12); the tool set; the sandbox limits; the build flags and sanitizers, identical in `check` and
  in the oracle; the static gate (§4.17); and the model settings within a family.
- **Helper parity** (05 §13, "equal-information brief"). Every std or prelude item reachable by the
  Mithril arms at X1 exists in the Rust and C11 helper packs with the same name and semantics, tested
  to agree (DESIGN §5.1a). This includes `topk(k, Ties::LowerIndex, Nan::Last)` and an accessor for
  every prelude `format` (provisional; the alternative is in Owner question 20). Whole-task canon
  helpers (`canon::act_q8`, `matvec_q`, `rmsnorm`, `softmax`, `silu`, `sigmoid`, `rope`,
  `combine_rank`) are in no arm's X1 library; `mithi` rejects them with `E-X1-NOTYET`.
- **Cards.** Mithril arms: Tier 0 + Tier 1 (no-traits and obfuscated variants, DESIGN §10.3–10.4).
  Rust, C11 and Rust + tooling: a **helper card** with the helper-pack signatures and one usage snippet
  per helper, the Rust or C equivalent of every Mithril-card snippet for a construct a task needs
  (05 §13), and, in the kit arm, the false-friend rows as lint rules. Sizes are logged per arm (05 §13);
  they are not padded to equal length.
- **Hole reports.** The three Mithril arms receive `mithi`'s hole report in every `check` response,
  as the Rust + tooling arm receives the kit's (DESIGN §7). This is provisional and is an Owner
  question (9).
- **Participants** (ROADMAP §3.2): "At least two frontier families, with 8 checker calls per task [P5].
  They carry the kill." One Hearth-hosted local model runs the pilot (§6.6), which is reported and is
  not part of the kill.

---

## 4. Units and counting rules (defined before data)

1. **Point.** One percentage point: 0.01 on the probability scale. Every comparison with a threshold
   uses the unrounded value, computed in exact rational arithmetic, and `>` is strict.
2. **Task family.** One of the eight ROADMAP families (T-Q4, T-ACTQ, T-NORM, T-ROUTE, T-EVICT,
   T-STORE, T-FMT, T-CTRL). Families are **fixed strata**: the estimand is defined over these eight,
   weighted equally.
3. **Template.** A task shape within a family, recorded as `template_id` in the sealed manifest.
   (a) At most one held-out item comes from each template (DESIGN §17, tombstone
   `x1_multi_variant_templates_heldout`). (b) **Iteration, calibration and held-out templates are
   disjoint**; the Gatekeeper asserts at sealing that the count of shared `template_id`s between any two
   splits is 0. (c) **Near-duplicates.** At sealing, no two held-out candidates of the same family may
   have reference solutions with 5-gram containment > 0.5 or alpha-renamed AST similarity > 0.6
   [G, proposed here] (DESIGN §4.5 metrics); the later one in sealing order is re-templated or replaced
   before sealing. The within-family distribution of pairwise similarities is reported. (d) As a
   sensitivity analysis, held-out pairs above the atom-isolation thresholds (containment > 0.2 or AST
   similarity > 0.3) are merged into one cluster, whatever their declared `template_id`, and the
   analysis is reported with those clusters. If (a) cannot be met, §6.3 step 6 applies.
4. **Held-out decision set.** Family B authors and seals **23 held-out candidates per family (184)**
   [D: the cap of 160 plus 15%, 160 × 1.15 = 184] in a seeded sealing order. The decision set is the
   first n_final / 8 candidates per family, in that order, that are unflagged (contamination flag `none`
   at sealing and at the freeze re-run, DESIGN §4.5) and not dropped by review (§10.9). Items flagged
   `public_near` or `leaked` never enter a decision; at the Owner's discretion they also run in the
   primary arms and are reported separately (05 §13). Unused candidates stay sealed; they may serve as
   M1 anchors or fresh-batch candidates, subject to M1's batch rules (ROADMAP §5).
5. **Cell.** One (item, arm, model family). It holds m scored attempts: 5 in primary arms, 3 in
   secondary arms.
6. **Attempt.** One fresh agent session with the fixed budgets, ending in `submit`, `abandon`, a
   budget limit (checker calls, turns, tokens, wall time), or an infrastructure failure. **Scored
   attempt**: any attempt that is not an infrastructure failure. The ending is recorded as
   `end_reason` (DESIGN §12.2).
7. **Infrastructure failure.** Only the closed list of DESIGN §13.3. Re-run as a fresh attempt and
   never scored. Not covered: refusals, context overflows, agent-caused timeouts or crashes, and
   wrong checker verdicts (ROADMAP §3.2).
8. **Verified pass (VP).** The attempt **ended in `submit()`** and the final artifact, rehashed by the
   harness, passes the hidden oracle (05 §13: "the share of attempts whose final submission passes
   the hidden oracle"). Attempts ending by `abandon` or a budget limit are fails; `abandon` on a
   solvable item counts as a fail (05 §13). The oracle still runs on such an attempt's last workspace,
   for the descriptive "unsubmitted oracle-pass" share (§5) only. Every held-out item is solvable by
   construction: its references pass its oracle in all languages, including the no-traits Mithril
   reference (DESIGN §3.1).
9. **Accepted.** The agent called `submit()` **and** the final artifact passes the arm's own acceptance
   check, which the harness runs itself after submission: the arm's checker (rustc with
   `-F unsafe_code`; Clang with no errors; `mithi check`; in the kit arm also zero `deny`-level lint
   findings), the static gate (§4.17), **zero remaining holes** (`todo!`/`unimplemented!` in Rust and
   Mithril, the stub marker `X1_TODO()` in C) in writable files, and the visible tests, whose outcomes
   are read from the harness's nonce-terminated result record, never from an exit status (DESIGN §6.1).
   Because every visible-test case is also a hidden-oracle case (DESIGN §6.1), "submitted, not
   accepted, oracle passes" can occur only through a kit `deny` finding or a remaining hole on an
   unreached path; its share is reported per arm (§5).
10. **CABW** (05 §13). Among accepted attempts, the share the hidden oracle rejects. The unconditional
    rate (accepted-and-wrong over all scored attempts) is reported too.
11. **Checker call.** One invocation of the `check` tool, whatever it runs (DESIGN §7). The harness's
    post-submission acceptance check and the oracle are not checker calls.
12. **Tokens, turns, dollars.** Tokens as the provider reports them per call (input, output, cache
    read, cache write, reasoning where reported). Turns are assistant messages. Dollars are tokens ×
    the pinned price table (§2). **Budget accounting:** the input-token budget counts, per call, all
    input tokens (uncached, cache read and cache write alike) **minus the token count of that arm's
    fixed system-prompt prefix** (common instructions, card or helper card, shared domain preamble),
    so a larger card does not shorten an attempt (DESIGN §12.1). Cost metering counts every token.
13. **First compile.** The first `check` call of an attempt reports no checker errors (tests ignored).
    An attempt with no `check` call has no first compile and leaves the denominator.
14. **Subset rejection** (05 §16; amber (c)). A Rust-arm held-out final artifact that passed the oracle
    is *rejected by the subset* if `mithi lift-check` reports ≥ 1 Dc diagnostic. Missing `uses` rows or
    grade annotations do not count (they are D-construct requirements an auto-fix inserts). Std gaps
    are reported separately and do not count.
15. **Hole use** (DR-003). A Mithril-arm attempt *uses a hole* iff some `check` call's workspace contains
    a `todo!(…)` at an anchor **not present in the stub** (matched by enclosing definition and anchor
    text), that is, the attempt record's `holes_written` ≥ 1. The stub-hole rate (any `todo!(` in any
    checked workspace) is reported separately as descriptive.
16. **Dc citation** (DR-004, DR-005 triggers; 05 §16). A failed Mithril-arm (traits-on) held-out
    attempt *cites row c* if its final artifact's `mithi check` output carries ≥ 1 diagnostic of row c.
17. **Static gate** (DESIGN §11.4). A per-language check of writable files that rejects routes to the
    filesystem, environment, processes, network, compile-time file inclusion and early process exit
    (Rust: `include_bytes!`, `include_str!`, `include!`, `#[path]`, `env!`, `option_env!`, `std::fs`,
    `std::env`, `std::process`, `std::net`, `std::os`, resolved through grouped `use` trees; C: object
    symbols `fopen`, `open`, `openat`, `exec*`, `system`, `popen`, `dlopen`, `syscall`, `exit`, `_Exit`,
    `quick_exit`, `abort`, `atexit`, `signal`, `longjmp`, inline `asm`, and `#include` with an absolute
    or `..` path; Mithril: `mithi` rejects the same macros and has no I/O effect at X1; the complete
    lists are DESIGN §11.4's). A hit is a checker error in `check` and an oracle fail. Legitimate
    solutions to X1 tasks need none of these.
18. **Calibration item.** A sealed item of split `calibration` (§6.3): run once, after the card
    freezes, in the Rust and Mithril arms; never shown to card editors; never held out.

---

## 5. Metrics

**Co-primary** (ROADMAP §1 rule 5: "VP@1 … and CABW … are co-primary, and each can trigger a kill on
its own"):
- **Δ** = VP@1(Rust) − VP@1(Mithril), in points.
- **Γ** = CABW(Mithril) − CABW(Rust), in points.

**Secondary, with pre-registered rules** (review triggers, never kills):
- **Δ_a** = VP@1(Rust + tooling) − VP@1(Mithril) (amber (a)).
- **Δ_b** = VP@1(Mithril) − VP@1(Mithril without traits), on the 64 common items (amber (b); DR-005).
- **R_sub** = subset rejection rate of passing Rust solutions (amber (c); DR-002).

**Secondary, reported** (ROADMAP §3.2 metrics list): tokens, turns and dollars per verified pass
(TPV, turns/VP, $/VP) per arm and family; first-compile rate; the subset rejection rate by Dc rule;
false-friend incidence per construct; FG = VP@1(Mithril) − VP@1(obfuscated) on common items, with the
de-obfuscation probe beside it (DESIGN §10.4); VP@1(C11) − VP@1(Rust); VP@1(Rust + tooling) −
VP@1(Rust); unconditional CABW; item-standardised CABW (§7.2); hole-use rate; Dc citation rates; the
realised CABW operating characteristic (§6.5); per-family estimates of everything above.

**Descriptive:** infrastructure-failure rate per arm; `end_reason` shares per arm and family (submit,
abandon, each budget); the "unsubmitted oracle-pass" share and the "submitted, not accepted, oracle
passes" share per arm; per-(arm, family) accepted counts; brief, card and preamble sizes per arm
(05 §13); stub-hole rate; sandbox CPU time and queue time per attempt; host load at each timeout; the
executor differential and audit-oracle disagreements (DESIGN §13.5); the local pilot results (§6.6);
the calibration run's variance estimates.

---

## 6. Sample and power

### 6.1 Planned sample (provisional, pending D0-10 budget approval)

| Quantity | Value | Basis |
|---|---|---|
| Held-out decision set | **n_final**, planned **96** (12 per task family), ≤ 1 per template; recomputed per §6.3 within [96, 160] | §6.2 [S, block 13]; ROADMAP minimum 60 |
| Held-out candidates authored and sealed | **184** (23 per family) | [D: cap 160 × 1.15]; §4.4 |
| Iteration items | 20 | ROADMAP §3.2 ("about 20 for card iteration") |
| Calibration items | **24** (3 per family) | §6.3; 3 per family gives 16 within-family df [D: 24 − 8] |
| Authored in total | **228** items [D: 184 + 20 + 24] | replaces the earlier ≈ 134 |
| Attempts per cell | 5 (primary arms), 3 (secondary arms) | ROADMAP §10 |
| Model families carrying the kill | 2 | ROADMAP §1 rule 5 |
| Held-out attempts | **4,032** at n = 96 [D: 96·5·3·2 + 64·3·3·2]; **5,952** at the cap n = 160 [D: 160·5·3·2 + 64·3·3·2] | ROADMAP §10 planned ≈ 2.9k for 60 items |
| Card iteration | ≈ 1.2k attempts (20 × 5 × 3 epochs × 2 Mithril arms × 2) | ROADMAP §10 |
| Calibration run | **480** attempts [D: 24 items × 5 × (Rust, Mithril) × 2 families] | added, §6.3 |
| Local pilot | 60 attempts (10 items × 3 × 2 arms × 1 local model) | ROADMAP §3.2, §10 |

The kill decisions use a fixed n with **no interim looks**: ROADMAP §3.2 says "the held-out set runs
once, after the card freezes".

### 6.2 Operating characteristics (power analysis, [S])

Simulator: [x1_power_sim.py](../../../experiments/x1-harness/power/x1_power_sim.py), seed 20261016;
2,000 replicates per configuration in blocks 1, 2 and 9 (Monte Carlo SE ≈ 0.0067 near 0.10 or 0.90
[D: √(0.09/2000)]), 20,000 in block 13 (≈ 0.0021 [D]); all inputs [G]; full tables in
[x1_power_tables.md](../../../experiments/x1-harness/power/results/x1_power_tables.md). The model:
attempts nested in cells; item difficulty, item × arm, item × model family and three-way random
effects on two logits (acceptance; wrong-given-accepted); task families as fixed strata; base rates
Rust VP@1 0.50 and CABW 0.20 [G]. Scenarios: item × arm logit SD 0.35 / 0.70 / 1.05 / 1.40 [G]
("low", "mid", "high", "stress"). They imply probability-scale σ_ta ≈ 0.10–0.14 / 0.18 / 0.24 /
0.29–0.30 [S]; 05 §13 assumed 0.10–0.20. The decision statistics are exactly those of §7.

**Requirements** (binding; each is ROADMAP §3.2 or 05 §13 made more precise, never looser):

| ID | Requirement [target] | Source |
|---|---|---|
| R-VP | P(K1) ≤ 0.10 at a true VP@1 gap of 5 points (CABW gap 0) and ≥ 0.90 at 25 | ROADMAP §3.2, verbatim |
| R-CABW | **for every true VP@1 gap g ∈ {0, 5, 10, 15}** (the gate's pass region): P(K2) ≤ 0.10 at a true CABW gap of 0 and ≥ 0.90 at 10 | 05 §13's proposed analogue, made binding here (Owner question 7) and extended from the single point g = 10 |
| R-JOINT | P(K1 ∨ K2) ≤ 0.10 at a true VP@1 gap of 5 and a CABW gap of 0 | ROADMAP §3.2's "the kill's operating characteristics … ≤ 10% at a true 5-point gap", read for DR-017's disjunctive kill |

**VP@1 kill (R-VP)** [S, block 1]:

| Scenario | n = 60: P(K1) at 5 / 25 | n = 96: P(K1) at 5 / 25 | SD of Δ̂ at n = 96 |
|---|---|---|---|
| low | 0.000 / 1.000 | 0.000 / 1.000 | 2.2–2.3 points |
| mid | 0.001 / 0.998 | 0.000 / 1.000 | 2.6–2.7 |
| high | 0.006 / 0.997 | 0.001 / 1.000 | 3.0–3.1 |
| stress | 0.012 / 0.991 | 0.003 / 1.000 | 3.3–3.5 |

60 items meet R-VP in every scenario [S]. A point-estimate rule meets it whenever SD(Δ̂) ≤ 7.8 points
[D: 10 / z_0.90 = 10 / 1.2816], which agrees with 05 §13.

**CABW kill and the joint requirement (R-CABW, R-JOINT)** [S, block 9]. Worst case over
g ∈ {0, 5, 10, 15}: max P(K2 | CABW gap 0) / min P(K2 | CABW gap 10); then P(K1 ∨ K2) at (5, 0).

| Scenario | n = 64 | n = 80 | n = 88 | n = 96 | n = 104 | n = 120 | n = 128 | n = 160 |
|---|---|---|---|---|---|---|---|---|
| low | 0.062 / 0.919; 0.043 | 0.039 / 0.953; 0.039 | — | 0.029 / 0.967; 0.015 | — | — | — | — |
| mid | 0.095 / **0.892**; 0.074 | 0.074 / 0.928; 0.048 | 0.054 / 0.936; 0.048 | 0.054 / 0.940; 0.042 | 0.049 / 0.953; 0.036 | 0.035 / 0.961; 0.020 | 0.029 / 0.967; 0.017 | 0.015 / 0.979; 0.013 |
| high | **0.126 / 0.871; 0.112** | 0.080 / **0.887**; 0.079 | 0.081 / 0.915; 0.079 | 0.075 / 0.906; 0.059 | 0.077 / 0.922; 0.058 | 0.059 / 0.932; 0.045 | 0.051 / 0.940; 0.039 | 0.032 / 0.967; 0.018 |
| stress | **0.142 / 0.829; 0.140** | **0.113 / 0.849**; 0.100 | **0.110 / 0.883**; 0.094 | **0.104 / 0.878**; 0.096 | 0.091 / **0.895**; 0.084 | 0.083 / **0.895**; 0.072 | 0.060 / 0.926; 0.058 | 0.053 / 0.944; 0.036 |

(**Bold** misses a requirement on the point estimate.) The binding cases are almost always g = 15,
where Mithril has the fewest accepted attempts. Smallest multiple of 8 meeting every requirement on
the point estimate at 2,000 replicates: low 64, mid 72, high 88, stress 128 [S]. The single-point
requirement of the earlier draft (g = 10 only) gave 96 for high and 100 for stress (0.085 / 0.903,
block 2); the stress scenario passes at 100 and 120 under that older requirement and needs 128 under
R-CABW.

**Why n = 96.** 96 is the record's **floor**, not the high scenario's minimum: n never falls below 96
(§6.3 step 4), because 24 calibration items cannot justify shrinking and because the minimum moves by
one grid step between Monte Carlo runs at 2,000 replicates (at 96 the high scenario's worst-case power
is 0.906, whose MC 95% lower bound is below 0.90). At 20,000 replicates (block 13, the step-4 rule
itself) the high scenario meets every requirement at 96 with MC bounds: worst-case P(K2 | 0) 0.0728,
worst-case P(K2 | 10) 0.9148 (both at g = 15), P(K1 ∨ K2 | 5, 0) 0.0640, P(K1 | 25) 0.9997 [S].

**Joint false-kill rate.** P(K1 ∨ K2) at (VP gap 5, CABW gap 0), n = 96: 0.015 / 0.042 / 0.059 / 0.096
(low → stress) [S, block 9]; block 1 gives 0.021 / 0.041 / 0.071 / 0.090 at the same point with other
streams [S]. At a VP gap of 10 (still inside the gate) it is 0.030 / 0.064 / 0.097 / 0.150 [S, block 9]
and 0.0948 in the high scenario at 20,000 replicates [S, block 13]. At n = 60 the joint rate reaches
0.141 (stress) [S, block 1], so 60 items fail R-JOINT under high variance.

**Base rates matter most** [S, blocks 4 and 10]. With a Rust VP@1 of 0.30, R-CABW fails at 128 items in
the mid and high scenarios (worst-case power 0.896 and 0.881) and is met at 160 only on the point
estimate (mid 0.077 / 0.925; high 0.081 / 0.902; 1,000 replicates), so such a base rate drives n_final
to the cap or past it (step 5). A Rust CABW of 0.35 is met at 96 (high 0.092 / 0.908). A high VP@1 with a
low CABW (0.75, 0.10) meets the old requirement easily at 64 (block 4).

**Other sensitivity [S]** (blocks 4, 4b): templates shared by 2–3 held-out items move the high
scenario's CABW requirement to about 120 items (block 4b), hence §4.3; item-difficulty SD 0.75 or 2.5
instead of 1.5, doubled model-family effects, or a correlation of −0.5 between the two logits move the
decisive probabilities by at most about 0.03 at 64 or 120 items (block 4). Naive SEs that treat
attempts as independent cover a 90% interval only 0.68–0.92 of the time; the stratified cluster-robust
SE covers 0.88–0.92 (block 1); with template clusters and df = clusters − 8 it covers 0.88–0.92 for
VP@1 and 0.87–0.92 for CABW (block 4b).

**One-family referral** (§7.7) [S, block 11, n = 96]: with no model-family × arm interaction,
P(no pooled kill, but a per-family breach) is 0.11–0.18 at a pooled VP gap of 5–10; with a fixed
interaction of ±0.5 on the comparison arm's acceptance logit it is 0.17–0.19 at 5 and 0.53–0.57 at 10;
at ±1.0, 0.56–0.67 and 0.88–0.91. The pooled kill rates stay at 0.033–0.103. Per-family SDs are 3.2–3.8
points (VP@1) and 3.6–4.5 points (CABW), against 2.5–3.2 pooled.

**Amber operating characteristics [S]**, reported so the review triggers' noise is visible:
- (a), P(Δ̂_a > 10) at n = 96: ≤ 0.002 at a true gap of 0; 0.008–0.076 at 5; ≥ 0.938 at 15;
  ≥ 0.998 at 20 (block 1).
- (b), P(Δ̂_b > 5) with 64 common items and 5 vs 3 attempts: 0.074 (mid) and 0.101 (high) at a true
  cost of 0; ≥ 0.92 at 10 (block 6).

### 6.3 Recomputation before collection (05 §13: "recomputed with a conservative σ_ta from the card-iteration items")

Made more precise here. The card-iteration items cannot serve: the card is tuned on them for up to
three epochs, which biases Mithril's VP@1 upward and the Rust-minus-Mithril item × arm variance
downward, the direction that stops n from growing; templates may repeat among them; and they hold only
Mithril arms. 05 §13's intent (a conservative σ_ta from pre-held-out data) is met with a **dedicated
calibration set** instead (Owner question 18).

**Order.** This record is FROZEN (and SIGNED, or covered by an Owner instruction) **before** the
calibration run, with `n_final` as the only open field; the only other value that may change is the
token cap, by the mechanical rule of step 7. The frozen script `analysis/calibrate.py` fills both. The
result is appended as a dated amendment before any held-out attempt runs. Nothing in the record may be
chosen after the calibration data are seen.

**Calibration run.** The 24 calibration items (3 per family, distinct templates disjoint from every
other split; §4.18) run in the Rust and Mithril arms with the frozen card, 5 attempts per cell, both
families: 480 attempts [D]. `calibrate.py` outputs **only** the quantities below. It never outputs
Δ̂, Γ̂, VP@1(Mithril), CABW(Mithril) or any per-item result.

1. **Base rates.** VP@1(Rust) and CABW(Rust), computed as in §7.2 on the calibration items.
2. **Dispersion bounds** (observed scale, m = 5, both families, so they match the simulation directly):
   - `d_i = (1/F) Σ_f (p̂_{i,f,Rust} − p̂_{i,f,Mithril})`, p̂ = VP count / 5;
   - `e_i = (1/F) Σ_f [ (W_{i,f,M}/m − R̂_{f,M} A_{i,f,M}/m) / D̄_{f,M} − (W_{i,f,R}/m − R̂_{f,R} A_{i,f,R}/m) / D̄_{f,R} ]`,
     the linearised CABW residuals, with `D̄_{f,a} = (1/8) Σ_T (1/n_T) Σ_{i∈T} A_{i,f,a}/m` and R̂ as in §7.2;
   - `s_d`, `s_e` = the pooled within-family SDs, `s² = Σ_T Σ_{i∈T} (x_i − x̄_T)² / df` with
     **df = 24 − 8 = 16** (one item per template, so df counts items);
   - upper 80% bounds `s_up = s · √(df / χ²_df(0.20))` = s × 1.198 [D: χ²_16(0.20) = 11.152, computed by
     the script's `chi2_ppf`].
   - Also reported, not used for n: `σ̂_ta,within = √max(0, s_d² − mean_i v_i)` with
     `v_i = (1/F²) Σ_f [p̂_R(1 − p̂_R) + p̂_M(1 − p̂_M)] / (m − 1)` (unbiased binomial variance), as fact
     `harness.x1.sigma_ta_within_calibration`.
3. **Scenario.** For each base-rate set B ∈ {the step-1 rates, the base case 0.50 / 0.20}: the smallest
   level of the simulator's ladder (low, mid, high, stress, then item × arm logit SD 1.75, 2.10, 2.45
   [G]) **not below "high"** whose simulated within-family SDs of d_i and e_i (`ladder_reference`, at B,
   evaluated with 480 items at a VP gap of 10 and a CABW gap of 0 [G]) are at least s_d,up and s_e,up.
   If no ladder level reaches both bounds, n_final is declared > 160 and step 5 applies.
4. **n_final** = the largest, over the two base-rate sets, of the smallest n ∈ {96, 104, …, 160}
   meeting R-VP, R-CABW and R-JOINT, each point simulated with **20,000 replicates**, where a
   requirement is met when the **Monte Carlo 95% upper bound** of P(kill | null) ≤ 0.10 and the **MC 95%
   lower bound** of P(kill | alternative) ≥ 0.90 (`x1_power_sim.py --recompute`). **n never falls below
   96.** At the base case and the high scenario this rule gives 96 [S, block 13].
5. If no n ≤ 160 [target, a budget cap] meets them, collection waits for a new Owner-signed record,
   which ROADMAP §1 rule 1 requires when a margin becomes unaffordable. The thresholds do not move.
6. If the authors cannot supply n_final unflagged items with ≤ 1 per template, n_final rises to the
   template-scenario value of the simulation's block 4b (about 120 in the high scenario for 2–3 items
   per template [S]), and the analysis clusters on templates.
7. **Token cap.** `calibrate.py` also outputs the share of attempts ending `budget_tokens` per arm. If
   it exceeds 5% [target] in either arm, the script doubles the non-prefix input-token cap once
   [target]. This mechanical rule is the only other parameter the script may change.

Simulation check of steps 2–3 [S, block 12]: with 24 calibration items, the upper-80% bound of s_d
reaches the population value in 0.78–0.80 of runs (nominal 0.80) and that of s_e in 0.69–0.71 (the
residuals are skewed); because a level is chosen only when both bounds are reached, the selected level
is at least the true one in 0.98 of runs, and with the floor at "high", in 1.000 (mid, high) and 0.981
(stress). The card-tuning bias of iteration items is not modelled; the dedicated set exists to avoid it.

### 6.4 Run order

Within each family, held-out attempts across arms and items run in one seeded random order,
interleaved, so time-varying provider behaviour hits all arms alike. Model versions are pinned; a
version change mid-run triggers §10.6. Admission control (DESIGN §11.2) keeps sandbox contention equal
across arms.

### 6.5 Realised MDE and realised CABW power (DR-017 revisit trigger)

`harness.x1.mde_points` = 2.563 × SE(Δ̂) [D: (z_0.90 + z_0.90) × SE, matching ROADMAP's 10%/90%
language], using the §7.3 standard error. The planned value from §6.3 is recorded before collection;
the realised value after. P(realised MDE > 15) ≤ 0.002 in every simulated scenario at n ≥ 60 [S].

DR-017's trigger reads only `mde_points`, which is built from SE(Δ̂). The CABW co-primary, which can
kill on its own, gets its own realised check, **reported and not gating**:
`harness.x1.cabw_se_points` = SE(Γ̂), and the realised operating characteristic
P(K2 | Γ = 0) = Φ(−5 / SE(Γ̂)) and P(K2 | Γ = 10) = Φ(5 / SE(Γ̂)) [D: normal approximation], which
meet 10% / 90% exactly when SE(Γ̂) ≤ 3.90 points [D: 5 / 1.2816]. Whether SE(Γ̂) > 3.90 should make the
result UNDERPOWERED for K2 is Owner question 15; it is not adopted silently, because it would block
kills. P(SE(Γ̂) > 3.90) at n = 96 is ≤ 0.001 (mid), 0.05–0.14 (high) and 0.35–0.56 (stress) [S, block 2].

### 6.6 Local pilot (reported, not part of the kill)

Provisional, pending D0-10: family **T-ROUTE**; 10 items drawn by a seeded draw at sealing from the
first 12 T-ROUTE held-out candidates in sealing order (always in the decision set unless dropped);
Mithril and Rust arms; 3 attempts per cell; one Hearth-hosted model; daytime only, never in a quiet
window, never co-scheduled with X3 or X4 measurement (DR-023). It runs after the frontier held-out run,
under the family-A firewall (DESIGN §4.6). Its gap estimate has an SD of about 10–12 points [S], so it
is a feasibility and plumbing check, not evidence about any gap smaller than about 25–30 points [D].
Its CABW gap is undefined in 0.21–0.23 of replicates at a true gap of 20 [S, block 7], so the pilot
reports VP@1 and only reports CABW where it is defined.

---

## 7. Analysis procedure

Deterministic scripts in `experiments/x1-harness/analysis/` (`score.py`, `calibrate.py`,
`analyze.py`, `verdict.py`), frozen by commit hash at freeze (§2). Agents may run them; they never
judge (ROADMAP §1 rule 3).

### 7.1 Estimands

For arms a and b, with the eight task families T and the two model families f weighted equally:
`VP@1(a) = mean_f mean_T E[pass | a, f, item in T]`, over the population of held-out items in each
family. `Δ`, `Δ_a`, `Δ_b` are differences of these. `CABW(a) = mean_f [ Σ_T E(accepted-and-wrong) /
Σ_T E(accepted) ]` with equal T weights; `Γ` is its difference.

### 7.2 Estimators (the decision statistics)

With `p̂_ifa` = VP count / scored attempts in cell (i, f, a), `n_T` items in family T, and F = 2:

```text
Δ̂  = (1/F) Σ_f (1/8) Σ_T (1/n_T) Σ_{i∈T} ( p̂_{i,f,Rust} − p̂_{i,f,Mithril} )
R̂_{f,a} = [ Σ_T (1/n_T) Σ_{i∈T} W_{ifa}/m_{ifa} ] / [ Σ_T (1/n_T) Σ_{i∈T} A_{ifa}/m_{ifa} ]     (A accepted, W accepted-and-wrong)
Γ̂  = (1/F) Σ_f ( R̂_{f,Mithril} − R̂_{f,Rust} )
```

**Undefined ratio.** If an arm has no accepted attempt in a model family (the denominator of R̂_{f,a}
is 0), R̂_{f,a} is undefined; that family's term is not computed, Γ̂ is the other family's term alone,
and the case is an Owner referral (§8). If neither family's term is defined, Γ̂ is undefined, K2
cannot be evaluated, and the verdict rests on K1 with an Owner referral. Per-(arm, family) accepted
counts are always reported. (The earlier simulation set an undefined ratio to 0, which biased Γ̂
against a kill in the pilot rows; the simulator now follows this rule.)

Δ̂_a and Δ̂_b are computed like Δ̂, Δ̂_b on the 64 common items. Item-standardised CABW (secondary)
reweights each arm's accepted attempts to Rust's per-item acceptance counts, which separates a
real CABW difference from a change in which items get accepted.

### 7.3 Model formulas

**Primary model, VP@1.** A linear (identity-link) mixed-effects model of the cell pass proportions,
with the task (item) as a random effect, as ROADMAP §3.2 requires ("Mixed-effects, with task as a
random effect"):

```r
lmer(p_hat ~ 0 + arm:model_family:task_family
           + (1 | item) + (1 | item:arm) + (1 | item:model_family),
     weights = n_scored_attempts)
```

The estimand is the equally weighted contrast of §7.1. With balanced cells (infrastructure failures
re-run, §4.7), the fixed-effect contrast equals Δ̂ of §7.2 [D: Zyskind's condition holds because,
with every cell complete within each item, Z Z′ X stays in the column space of X, so generalised and
ordinary least squares give the same cell means; checked numerically by an independent reviewer and
re-run by this track on 2026-10-16: max |GLS − OLS| ≈ 1e-15 for a balanced design, for unequal items
per task family, and for arm-specific weights 5 vs 3]. **The decision statistic is the closed form of
§7.2 by definition**, so the Gatekeeper needs no iterative fit. Where cells within an item are unequal
(for example the without-reversal sensitivity analysis of §10.2, which removes Mithril-arm attempts
only), GLS and OLS no longer coincide (max |GLS − OLS| = 0.085 in a numerical example with 3–5
Mithril attempts per cell [D, this track, 2026-10-16]); the closed form with per-cell p̂ is still the
statistic, and the LMM is reported beside it. Its standard error is the **stratified cluster-robust**
one: within each task family, the variance of the item mean is estimated from cluster totals with the
small-sample factor G/(G − 1), where the clusters are items (templates, and near-duplicate clusters in
the §4.3(d) sensitivity analysis). Degrees of freedom = clusters − 8. Simulated coverage of the
resulting 90% intervals: 0.88–0.92 [S].

**Primary statistic, CABW.** Γ̂ is a **design-based stratified ratio estimator with an item-cluster
linearised (delta-method) SE**, the same stratified construction applied to the residuals e_i of
§6.3. **It is not a mixed model.** DR-017 asks for a "task-clustered mixed-effects analysis"; for CABW
this record meets "task-clustered" through the SE only, which is a deviation for the Owner to accept or
reject (Owner question 5). Reported beside it, not deciding: a logistic GLMM fitted on accepted
attempts,

```r
glmer(wrong ~ 0 + arm:model_family:task_family + (1 | item) + (1 | item:arm),
      family = binomial, nAGQ = 1, control = glmerControl(optimizer = "bobyqa"))
```

with the marginal CABW gap standardised as §7.1.

**Secondary model, VP@1** (05 §13, reported; replaces the earlier draft's formula, which was not
identifiable with two arms per fit: `(1 | task_family/item)` adds an item intercept whose variance is
confounded with the 2 × 2 covariance of `(0 + arm | item)`):

```r
glmer(success ~ 0 + arm:model_family:task_family
              + (1 | item) + (1 | item:arm) + (1 | item:model_family),
      family = binomial, nAGQ = 1, control = glmerControl(optimizer = "bobyqa"))     # lme4, Laplace
```

It is fitted per contrast on the two arms involved, on attempt-level data. The marginal gap is the mean
over sampled items of the predicted probabilities (with the BLUPs), task families and model families
weighted equally, as in §7.1. **Fallback trigger:** non-convergence **or** `isSingular(fit, tol = 1e-4)`;
then `(1 | item:model_family)` is dropped, and if the trigger still holds, `(1 | item:arm)` too; every
change is reported. Its kill verdict (K1 on its marginal gap) is reported. If the pre-registered form
fits without fallback and its verdict differs from the primary's, the record flags a
**model-sensitive verdict** to the Owner; the Gatekeeper's verdict follows the primary statistic.
**Tertiary:** 05 §13's form `success ~ arm * family + (1 | task_family/item) + (0 + arm | item)`,
verbatim, with its `isSingular` flag, for traceability only.

**Why the primary statistic is not the logistic GLMM** (05 §13 names the GLMM as "the model"; this is a
deviation from 05, not from ROADMAP, and an Owner question):
1. DR-017's thresholds are in points on the probability scale. The GLMM's coefficients are
   conditional log-odds and need marginal standardisation, a second modelling step.
2. Random arm slopes over ~96 items may be singular [inference]. A verdict must not depend on optimiser
   behaviour.
3. The Gatekeeper must be deterministic and simple; the closed form is.
4. Its operating characteristics are the ones simulated in §6.2. The GLMM's were not simulated (no
   GLMM fitter in the simulation's budget).

**Robustness check** (05 §13: "A cluster bootstrap over items checks robustness"): a stratified item
(or template) cluster bootstrap of Δ̂ and Γ̂, B = 10,000, percentile intervals, reported beside the
analytic intervals. Simulation check: the analytic SE (3.16 points) sits between the bootstrap SE
(2.96) and the empirical SD (3.26) in the mid scenario at n = 64 [S, block 8]; the bootstrap is
slightly narrow with 8 items per stratum [D: factor √(7/8)].

### 7.4 Decision rules (thresholds copied exactly from ROADMAP §3.2)

| Rule | ROADMAP §3.2 text | Operationalisation (more precise, not looser) |
|---|---|---|
| **Gate** | "Rust − Mithril VP@1 ≤ 15 points, and CABW is no more than 5 points worse than Rust's." | Δ̂ ≤ 15 **and** Γ̂ ≤ 5 |
| **Kill K1** (DR-017) | "VP@1 gap > 15 points" | Δ̂ > 15 |
| **Kill K2** (DR-017) | "**or** CABW worse than Rust's by > 5 points" | Γ̂ > 5 (Γ̂ per §7.2, including its undefined-ratio rule) |
| Consequence | "The standalone surface then stops, and Mithril ships as checker, ledger and tooling over Rust/C." | STOP-L (ROADMAP §4) |
| **Amber (a)** | "Rust + tooling beats Mithril by > 10 points [target]: the Owner reviews, before M1, whether the surface earns its cost." | Δ̂_a > 10; only if the kit ran |
| **Amber (b)** | "The traits ablation costs > 5 points: DR-005 is confirmed." | Δ̂_b > 5 |
| **Amber (c)** | "The subset rejects > 30% of passing Rust solutions [target]: the Dc list is revised before M1." | R_sub > 0.30 |
| **Power** | "it fires with probability ≤ 10% at a true 5-point gap and ≥ 90% at 25 points [target]. If 60 items cannot meet that, the item count grows; the threshold does not move." | R-VP, R-CABW and R-JOINT of §6.2; n set by §6.3 |

K1 and K2 are **point-estimate rules**, as 05 §13 operationalises DR-017 for X1. "Gap > 15 points"
is read literally as the estimate exceeding 15. Their error rates are governed by the pre-registered
operating characteristics in §6.2, not by an α level. A rule that kills only when a confidence bound
exceeds 15 would loosen DR-017 and is rejected (DESIGN §17, tombstone `x1_ci_bound_kill_rule`).

### 7.5 Co-primary handling, one-sided tests, interval levels and multiplicity

- **Co-primary handling.** Both statistics are always computed. KILL if K1 **or** K2 holds; the
  verdict names which (`vp1_gap`, `cabw_gap` or both) for the ROADMAP §4 tombstone. Neither can veto
  the other: DR-017 rejected P1's conjunction precisely because a much worse Mithril could survive by
  halving CABW.
- **Interval levels.** Every interval fact carries its level: `.ci_level = 0.90` and `.ci_sides = 2`
  (§7.6). Each bound of a two-sided 90% interval is a one-sided 95% bound. 05 §13 defines M1's CABW
  test with a one-sided 90% bound, so the same fact name could carry different levels at X1 and M1;
  Owner question 16 asks that DECISIONS / 06 §7.2 fix one convention. Nothing in DECISIONS changes here.
- **One-sided tests.** None of the kills is a hypothesis test. One-sided inference appears only in
  these places:
  1. the ledger's `ci_low`/`ci_high` facts (two-sided 90%, so one-sided 95% per bound);
  2. DR-005's trigger, `harness.x1.vp1_delta(traits_on, traits_off).ci_high < 0`, is then a one-sided
     test at α = 0.05 that traits hurt;
  3. the report states, descriptively, the one-sided p-values for H0: Δ ≤ 15 and H0: Γ ≤ 5, which
     say how close the result is to the boundary. They change nothing.
- **Multiplicity.** No α-splitting between K1 and K2. A correction would raise each kill's effective
  threshold, which loosens DR-017. Instead the family-wise false-kill probability of the disjunction is
  a pre-registered requirement (R-JOINT) and is published as a surface: P(K1 ∨ K2) ≤ 0.10 at the joint
  null (VP gap 5, CABW gap 0) at n = 96 in the low, mid and high scenarios (0.015–0.059 [S, block 9])
  and 0.096 in stress; at a VP gap of 10 it rises to 0.03–0.10 in low to high and 0.15 in stress [S];
  the stress scenario meets every requirement at n = 128 [S]. The ambers are review triggers with
  published operating characteristics; they cannot kill. All other contrasts (C11, FG, the tooling
  effect, per-family estimates, TPV) are labelled exploratory and are not corrected.

### 7.6 Ledger facts this record writes (and the facts its tombstones read)

Units are points (fractions × 100) unless stated. `vp1_delta(a, b)` means VP@1(a) − VP@1(b). Every
interval fact has `.ci_level` (0.90) and `.ci_sides` (2).

| Fact | Definition | Producer | Read by |
|---|---|---|---|
| `m0.x1.verdict` | `pass` \| `kill` \| `void` \| `underpowered` | `verdict.py` | DR-001; ROADMAP §4 |
| `harness.x1.vp1_delta(rust, mithril).{est, ci_low, ci_high, ci_level, ci_sides}` | Δ̂ and its 90% interval | `analyze.py` | DR-017; ROADMAP §4 tombstone |
| `harness.x1.cabw_delta(mithril, rust).{est, ci_low, ci_high, ci_level, ci_sides}` | Γ̂ and its 90% interval | `analyze.py` | DR-017 |
| `harness.x1.vp1_delta(rust_kit, mithril).{…}` | Δ̂_a | `analyze.py` | amber (a) |
| `harness.x1.vp1_delta(traits_on, traits_off).{…}` | Δ̂_b | `analyze.py` | DR-005 trigger |
| `harness.x1.mde_points`, `harness.x1.mde_points_planned` | §6.5 | `analyze.py`, `calibrate.py` | DR-017 trigger |
| `harness.x1.cabw_se_points`, `harness.x1.cabw_oc_realised.{p_kill_at_0, p_kill_at_10}` (fractions) | §6.5 | `analyze.py` | Owner question 15; report |
| `harness.x1.voided.{vp1_delta, cabw_delta}(…).est`, with `status = voided` | the estimates of a batch that is VOID or UNDERPOWERED, always written | `analyze.py` | report; audit trail (§8) |
| `harness.x1.accepted_count(arm, family)` (count) | §7.2 | `score.py` | §7.2 undefined-ratio rule |
| `harness.x1.end_reason_share(arm, reason)` (fraction) | §5 | `score.py` | §6.3 step 7; report |
| `harness.rust_rejection_rate` | R_sub (a fraction) | `analyze.py` | DR-002 trigger |
| `prereg(agent.subset_rejection_bound)` | 0.30 [target, ROADMAP amber (c); 05 §16] | this record | DR-002 |
| `harness.hole_use_rate(spelling: todo)` | share (a fraction) of scored held-out Mithril-arm attempts with `holes_written ≥ 1` (§4.15) | `score.py` | DR-003 |
| `harness.x1.stub_hole_rate` (fraction) | §4.15, descriptive | `score.py` | report |
| `prereg(agent.hole_use_floor)` | **0.10** [target, proposed here; G; an Owner question] | this record | DR-003 |
| `harness.dc_rate(construct: c)` | share (a fraction) of failed held-out Mithril-arm attempts citing row c (§4.16); `c` ∈ {`float_sum`, `ties`, `exp`, `powi`, `f16`, `stored_ref`, `local`, `dyn`, `async`, `cell`, `unsafe`, `clock`} ↔ FF-SUM … FF-CLOCK | `score.py` | DR-004, DR-005 |
| `prereg(agent.dc_rate_bound)` | **0.10** [target; the 10% of ROADMAP D-01 and 05 §16] | this record | DR-004, DR-005 |
| `harness.families` | number of model families carrying the kill (2) | `analyze.py` | DECISIONS §4 triggers |
| `harness.x1.sigma_ta_within.{est, ci_high}` (fraction) | on held-out data: est = √max(0, s_d² − mean v_i) with s_d the pooled within-family SD of d_i (df = clusters − 8) and v_i as §6.3; ci_high = √max(0, s_d² · df / χ²_df(0.05) − mean v_i) (upper 95%) | `analyze.py` | DESIGN §17 tombstones |
| `harness.x1.sigma_ta_within_calibration.{est, ci_high}` (fraction) | the same on the 24 calibration items (df = 16) | `calibrate.py` | report |
| `harness.template_pairs.sigma_ta_share.ci_high` (fraction) | share of σ²_ta at the template level, upper 95% bound | **not X1**: a separately pre-registered template-pair study (pairs of items from one template run in Rust and Mithril), earliest M1. X1 writes no value; the fact reads `unknown` until then | DESIGN §17 tombstone `x1_multi_variant_templates_heldout` |
| `harness.x1.glmm_converged` (bool), `harness.x1.glmm_primary_abs_diff_points` | the pre-registered secondary VP@1 GLMM of §7.3 fitted without fallback and not singular; \|its marginal gap − Δ̂\| | `analyze.py` | DESIGN §17 tombstone |
| `owner.decision(dr017_test_form)` | enum {`point_estimate`, `lower_bound`}: the test form of DR-017's X1 kill as signed | the Owner's signature of this record writes `point_estimate`; a later Owner-signed record may change it | DESIGN §17 tombstone `x1_ci_bound_kill_rule` |
| `owner.decision(x1_calibration_source)` | enum {`dedicated_set`, `iteration_items`}: the Owner's answer to Owner question 18 | the Owner's signature of this record | DESIGN §17 tombstone `x1_calibration_on_iteration_items` |
| `harness.x1.arms_with_ambient_authority` (count) | arms whose language, as run by the harness and before the static gate, can read files, read the environment or exit the process from agent code; 3 at X1 [D: Rust, C11, Rust + tooling] | the harness configuration at freeze | DESIGN §17 tombstone `x1_agent_code_beside_hidden_data` |
| `harness.eval_awareness_shift(canary_brief, plain_brief).{est, ci_high}` | points: VP@1 under a canary-bearing brief minus under a plain brief, from paired shadow runs | **not X1**: the 03 row 34 shadow-run comparison, when a later record pre-registers it. X1 writes no value; the fact reads `unknown` | DESIGN §17 tombstone `x1_canary_in_agent_visible_brief` |
| `harness.x1.post_data_discoveries` (count), `harness.x1.verdict_without_post_data` | §10.2 | `verdict.py` | §8 Owner referral |
| `harness.x1.deobfuscation_probe` (fraction) | share of probe sessions that name Rust as the obfuscated card's base language (DESIGN §10.4) | `score.py` | report beside FG |

Per-family copies of the first five facts are written with a `family` parameter.

### 7.7 Breach in one family only

05 §13: "A breach in one family only goes to the Owner." Read here as: the Gatekeeper's verdict is
computed on the pooled estimand. If the pooled verdict is **not** KILL but K1 or K2 holds on one
family's own estimate, the record goes to the Owner for review, and the verdict is unchanged. If the
pooled verdict is KILL, it stands even when only one family breaches individually. The other reading,
that a pooled kill driven by one family is softened to a referral, would loosen ROADMAP §3.2's kill,
so it is not adopted (Owner question 6). Expected referral rates: 0.11–0.18 with no model-family × arm
interaction, rising to 0.53–0.57 at a pooled VP gap of 10 with a ±0.5-logit interaction [S, block 11]
(§6.2). A referral is therefore common, and is not by itself evidence of an interaction.

---

## 8. Outcomes and actions

| Outcome | Condition | Action |
|---|---|---|
| **No run** | checker precondition fails (P-1, P-2 confirmation half, P-2t or P-3; DESIGN §9.5), or an item misses the mutant requirement and cannot be fixed or replaced from the reserve, or §6.3 step 5 | fix and re-check; no held-out attempt runs until all pass |
| **PASS** | ¬K1 ∧ ¬K2, realised MDE ≤ 15, not VOID | X1 contributes PASS to the M0 verdict (ROADMAP §3.7) |
| **PASS + AMBER (a)** | PASS and Δ̂_a > 10 | "the Owner reviews, before M1, whether the surface earns its cost" |
| **PASS + AMBER (b)** | PASS and Δ̂_b > 5 | "DR-005 is confirmed" (recorded) |
| **PASS + AMBER (c)** | PASS and R_sub > 0.30 | "the Dc list is revised before M1" |
| **KILL** | K1 ∨ K2 (and not VOID, not UNDERPOWERED) | STOP-L; tombstone `standalone_surface` (ROADMAP §4) with the verdict field and scope from this record; with an X2 kill, STOP-ALL |
| **VOID** | the re-scoring rule's reversed-attempt share exceeds 5% in any Mithril arm (§10.2) | "the run repeats on a fresh sealed batch, built as M1's is (§5)". The voided batch's Δ̂ and Γ̂ are still written to the ledger with status `voided` (§7.6), so a VOID after a kill-level estimate stays visible |
| **UNDERPOWERED** | realised `harness.x1.mde_points` > 15 (DR-017's trigger: "An underpowered study must be resized before it can kill or pass") | neither KILL nor PASS; the batch is retired (it may supply M1 anchors); its estimates are written with status `voided`; a fresh sealed batch sized from the realised variance runs under an amended, re-signed record |
| **Owner referral** | one-family-only breach (§7.7); model-sensitive verdict (§7.3); with/without-reversal disagreement (§10.2); verdict differs with and without post-data discoveries (§10.2); Γ̂ on one model family only or undefined (§7.2) | the Owner reviews; the Gatekeeper verdict stands |
| **Kit not ready** | DESIGN §8.3 | the tooling arm is dropped from X1, starts at M1; amber (a) waits for M1 |

The ambers are independent of each other and may co-occur with PASS. They do not apply to KILL,
because the surface stops.

---

## 9. Threats to validity and how each is handled

| Threat | Handling |
|---|---|
| Card overfit to the tasks | atoms isolated from every hidden reference (5-gram containment ≤ 0.2, AST similarity ≤ 0.3 [target, 05 §13]), checked **blind** (editors see only a count of rejected atoms per epoch; the per-atom list goes to the Owner); iteration, calibration and held-out templates disjoint (§4.3); a **semantic guard** before card freeze, by a family B or C reviewer who reads the card against the held-out template list and flags template-specific atoms (moved to the shared domain preamble or removed) (DESIGN §10.2); variant knobs only in the private authoring brief; held-out run once after the card freezes |
| Unequal information between arms | helper parity, `topk` and format accessors included (§3, DESIGN §5.1a); whole-task canon helpers excluded everywhere; helper cards for the Rust, C11 and kit arms; every domain-rule atom in the shared preamble for all arms; sizes logged per arm |
| Task authors favouring one arm | authors from a family other than the card editors (05 §13); one brief and one domain preamble for all arms; helper packs in every language, tested to agree |
| Author family = participant family | an authorship advantage in one arm (for example family B's own Rust idioms) is a **model-family × arm interaction**: it enters the pooled Δ with weight 1/2, does not cancel, and shows in the per-family estimates; block 11 gives its effect on referrals [S]; a third authoring family (Owner question 3) removes it |
| The Owner as a channel from held-out items into the card | the Owner reviews held-out items only after the card hash is frozen (a seeded sample, §10.9); before that, held-out items are reviewed by independent family-B (or C) sessions (provisional; Owner question 17) |
| Leakage of held-out content into family-A (Claude) contexts | the family-A firewall of DESIGN §4.6: scripted authoring and runs, keys and decrypted material only where no family-A session can read them, contamination checks on anything derived from hidden material before a family-A session sees it, content-free logs |
| Training contamination of items | private sealed store; canary in hidden files; contamination check against a pinned public corpus that includes llama.cpp/ggml and MultiPL-E, re-run at freeze (DESIGN §4.5); kill on unflagged items only; API training opt-out (Owner question 4) |
| Agents reading hidden content at scoring time | two separately encrypted bundles per item (visible, hidden); a two-stage oracle in which agent code runs only in a container that holds no hidden data and whose outputs are compared outside it; the static gate; scorer canaries per route (DESIGN §3.3, §11.3, §11.4) |
| Process-level gaming (early `exit(0)`, deleting `#![forbid(unsafe_code)]`) | outcomes only from nonce-terminated result records; `-F unsafe_code` set by the harness; exit-family symbols in the static gate; an `exit(0)` canary per arm |
| Leakage of hidden content to agents | sandbox holds only visible files with no VCS history; oracle out of process; scorer rehashes the final artifact (03 rows 30–31) |
| Evaluation awareness (03 row 34) | no harness markers in agent-visible text; the canary only in hidden files. Shadow-run paired comparisons (row 34) are **not** run at X1 and the gap is reported |
| `mithi` errors | the checker precondition (DESIGN §9.5) with a **sealed confirmation half** of the planted corpus run once after the last `mithi` change; change control after the precondition (DESIGN §9.6); the reference agreement check against two compilers; the **executor differential test** on real Rust-arm artifacts (DESIGN §13.5); the re-scoring rule (§10.2) |
| Oracle weak spots that only one arm's errors hit | cross-arm false-friend mutants (idiomatic Rust and C forms) killed at ≥ 95% as their own subset; a sealed **audit oracle** with ≥ 10× the vectors run on every oracle-passing artifact in every arm (DESIGN §6.2, §13.5) |
| Defect hunting only after a bad result | a pre-declared, equal-effort defect audit over every item and arm, run before unblinding; claims confirmed by an independent family B or C reviewer and the Owner, with the claimant's knowledge of results logged; verdict reported with and without post-data discoveries (§10.2) |
| Token budget binding unequally | budget counts input tokens excluding the fixed prefix (§4.12); the §6.3 step-7 cap rule; `end_reason` reported by arm |
| A kit that is not a fair floor | kit acceptance corpus written by family B or C or the Owner, never the kit builder; parity test against `mithi`'s hole report; `deny` set limited to 01 §2.5's Dc rows in their contexts; every `deny` fix names a function in that arm's helper pack (DESIGN §8) |
| An obfuscated arm that names its base language | no language name in the obfuscated card, brief or diagnostics (CI check); prelude names that act as keywords mapped too; de-obfuscation probe reported (DESIGN §10.4) |
| Infrastructure contention falling on agents | admission control, CPU-time limits, host-load logging, preemption on any DR-023 host as infrastructure failure (DESIGN §11.2, §13.3) |
| Check and oracle disagreeing about flags | `check` uses exactly the oracle's build flags and sanitizers; `mithi vectors` runs the full check first (DESIGN §7, §13.1) |
| CABW composition (it is conditional on acceptance) | item-standardised CABW reported (§7.2) |
| Template correlation | at most one held-out item per template; disjoint templates across splits; near-duplicate rule (§4.3); otherwise template-clustered analysis and n per §6.3 step 6 |
| Variance assumptions behind n | dedicated calibration set and recomputation (§6.3); n only grows; scenario floor "high" |
| Drift in provider behaviour during the run | pinned versions; interleaved seeded run order (§6.4); §10.6 |
| Infrastructure failures differing by arm | closed list; re-runs; per-arm rates reported; a rate above 5% in any arm [G] is investigated and reported before analysis |
| The tooling arm sees grade information (`exact.toml`) | intended (it is "the Mithril arm's tooling applied to Rust"); reported as part of the kit |
| Obfuscation covers keywords, primitive types and keyword-like prelude names only | ROADMAP's definition ("renamed keywords") is the minimum; FG is a lower bound on familiarity, reported with the de-obfuscation probe |
| Basic diagnostics only at X1 | ROADMAP caveat: the gap is pessimistic; M1 re-tests with full diagnostics |
| Two families only; one model generation | the ROADMAP §4 tombstone's `revisit_when` covers model generations and context-window growth |
| Boundary behaviour | a point-estimate rule fires about 50% of the time at a true gap of exactly 15 (0.48–0.52 [S]); inherent, and reported |

---

## 10. Deviation and re-run policy

1. **Lifecycle** ([docs/m0/README.md](../README.md)): DRAFT → FROZEN (commit hash) → SIGNED (D0-12).
   After freeze, changes are dated amendments appended below, stating the reason and whether any data
   had been seen. **Thresholds never move once data have been seen** (ROADMAP §1 rule 1).
2. **The `mithi` re-scoring rule** (ROADMAP §3.2, verbatim): "if a `mithi` bug is found after
   collection, the fixed `mithi` re-scores every final verdict. Attempts in which a reversed verdict
   occurred mid-loop are reported, and the analysis is run with and without them. If they exceed 5% of
   a Mithril arm's attempts [target], the held-out result is void and the run repeats on a fresh sealed
   batch, built as M1's is (§5). "Infrastructure failures are re-run" does not cover a wrong checker
   verdict."
   Precision added (DESIGN §13.4):
   - "reversed" means a verdict bit flipped on replay of a stored `check` input (accept/reject, test
     pass/fail, crash/timeout vs normal); the share is per Mithril arm, over all scored held-out
     attempts of that arm in both families, cumulative across bugs, with > 5.0% strict; the primary
     analysis uses all attempts with the re-scored final verdicts, and a with/without disagreement is
     an Owner referral.
   - A "bug" is a verdict contradicting the frozen note, grammar or pinned Rust meaning, shown by a
     minimal witness and **confirmed by an independent reviewer from family B or C** (a same-family,
     independent-context reviewer if none is available, logged as such) **and by the Owner**. The
     claimant's knowledge of arm-level results at the time of the claim is logged.
   - **Pre-declared defect audit, before unblinding.** Collection ends; scoring writes per-artifact
     verdicts that nobody aggregates by arm yet; then an audit of equal effort over every item and
     every arm runs: the pre-declared `mithi` differential-fuzzing budget, the executor differential
     test, the audit oracle (DESIGN §13.5) and a review of every visible test by a family B or C
     reviewer. Confirmed defects are applied; then results are unblinded.
   - Anything found after unblinding by any other search is a **post-data discovery**. ROADMAP's rule
     still applies it (re-scoring is mandatory), and the verdict is reported both with and without
     post-data discoveries; a difference is an Owner referral (§8).
3. **Infrastructure failures** (§4.7): re-run, never scored; the cell keeps m scored attempts.
4. **Oracle defects**: fix the oracle, re-score every final artifact in every arm. Agents never saw the
   oracle, so no trajectory is re-run. A pass/fail disagreement between the scoring oracle and the
   audit oracle on any artifact is an oracle defect. **Visible-test defects**: the item is voided in
   every arm (it shaped trajectories), and voids are reported. A visible-test claim is filed and
   confirmed **before** per-item arm results are revealed to the claimant, item by item. A voided item
   leaves every arm, and the realised-MDE rule (§6.5, §8) decides whether the remaining sample can
   still kill or pass.
5. **Analysis-script bugs** found after data: both versions are reported. The fixed version governs
   only when the frozen one fails to implement this record's formula, and an independent reviewer
   confirms that; otherwise the frozen version governs.
6. **Model withdrawal mid-run.** If a pinned model version becomes unavailable before its family's
   held-out run completes, that family's run restarts on the same sealed batch with the successor
   version named by the Owner, all of that family's attempts are taken from the restarted run, and the
   change is an amendment. No data from the withdrawn version enter the decision.
7. **No interim looks, no top-ups.** The held-out run happens once. Items are never added after held-out
   data are seen, except through the VOID or UNDERPOWERED routes, which use a **fresh** sealed batch.
8. **Collection preconditions.** For the calibration run: this record FROZEN and SIGNED (or an
   explicit Owner instruction); the checker precondition passed; the card frozen. For the held-out run,
   additionally: the kit's readiness decided; the §6.3 amendment appended; the Owner's post-freeze
   sample review done (§10.9).
9. **Item replacement and re-commitment.** A held-out candidate that is flagged, fails review or misses
   the mutant requirement is replaced by the **next candidate of the same family in sealed order**,
   never a chosen one. Any change to `COMMITMENTS.json` after its sealing commit is a dated
   re-commitment listing the changed positions and the reason (DESIGN §4.1). The Owner's post-freeze
   review covers a seeded sample of 3 items per family [G] from the first 12 per family (24 items).
10. **`mithi` change control.** After the checker precondition, `mithi` may change only to fix a bug
    as defined in item 2, with a witness. Every change re-runs P-1, the P-2 confirmation half, P-2t and
    P-3 in full and re-records the hash; no change may widen the X1 subset (DESIGN §9.6).

---

## 11. Deliverables and where they land

| Deliverable | Where |
|---|---|
| Harness, sandbox image recipe, runner, drivers, static gate, scorer, analysis scripts | `experiments/x1-harness/` (public) |
| Power analysis and its recomputation | `experiments/x1-harness/power/` |
| `mithi` crate; kit (`x1-holes`, `x1-fflint`); grammar; cards; helper cards; shared domain preamble | `experiments/x1-harness/` until M1 moves them (public, after card freeze) |
| `COMMITMENTS.json` (suite commitments, root, canary hash) | its own commit at sealing; dated re-commitments after |
| Sealed suite (visible and hidden bundles), audit vectors, planted corpus (both halves), P-1 reproductions, transcripts, raw attempt records | Gatekeeper private store only, until the verdict (DESIGN §4.6) |
| Result manifest: per-cell table keyed by opaque item IDs; estimates; verdict JSON; facts of §7.6 | `experiments/x1-harness/results/` |
| REPORT.md (ROADMAP §3.2 metrics, ambers, pilot, threats, deviations) | `experiments/x1-harness/results/REPORT.md` |
| Tombstone proposals (DESIGN §17; on a kill, ROADMAP §4's `standalone_surface`) | REPORT.md, for the Owner to admit |

---

## 12. Review log

| Date | Reviewer | Family | Context | Scope | Result |
|---|---|---|---|---|---|
| 2026-10-16 | Reviewer 1, statistics and design lens | Claude (same family as author; independent context) | separate agent context, adversarial brief | this record §§4–10, DESIGN §§13–17, the power simulation (re-ran it with new keys) | 12 findings: 0 blocker, 5 major, 7 minor. All 12 accepted; 2 with a modified fix (below) |
| 2026-10-16 | Reviewer 2, integrity, leakage and fairness lens | Claude (same family as author; independent context) | separate agent context, adversarial brief | DESIGN end to end, this record §§3–10 | 20 findings: 1 blocker, 12 major, 7 minor. All 20 accepted; 5 with a modified fix (below) |

Both reviews are **same-family, independent-context**, which is weaker than ROADMAP's
different-family requirement ([docs/m0/README.md](../README.md)); a family B or C review is still
required before FREEZE once D0-10 names the families. Under the Owner's chat answer to D0-10c, that
review can only be the local Qwen3's, and only by a new answer (D0_BRIEF Q17).

The section "X1 under the 2026-10-16 owner constraints" was added on 2026-10-16 by the owner track (a
Claude agent). It changes no threshold. Elsewhere the owner track added only status notes: the status
and authorisation lines, the note under "Owner questions", the note under "Budget per ROADMAP §10"
and this paragraph. That section, with the owner track's other files, then had one review:

| Date | Reviewer | Family | Context | Scope | Result |
|---|---|---|---|---|---|
| 2026-10-16 | Reviewer 1 of the owner-track revision, the Owner's position lens (fidelity to the owner answers log, decision by framing, cost completeness, sitting feasibility; inferred from the findings) | Claude, same family, independent context | separate agent context | the section "X1 under the 2026-10-16 owner constraints", with D0_BRIEF, PLAN, COST and OWNER-QUEUE | 13 findings across the five files: 1 blocker, 6 major, 6 minor; all 13 accepted, 6 with a modified fix; 0 rejected. Full log in [OWNER-QUEUE](../OWNER-QUEUE.md#review-log) |

In this record the review led to: the Owner's batch-2 X1 rule recorded as answered (status line;
"The Owner's choice (chat) and what remains open" replaces "Recommendation"); option 4b no longer
fixed to Qwen3 templates, the template author left open with GEN_OWNER first and GEN_CLAUDE priced as
a labelled loosening; both template counts carried through options 2, 3 and 4b and the comparison
(Qwen3 templates ≈ 32–349 h at ≤ 1 held-out item per template, not the earlier "35–349", which used
140 templates for the lower end; Owner templates ≈ 36–141 h at 2–3 per template, not "35–142") [D,
`owner/calc2.py`]; option 1 marked as contradicting D0-10c's option text and the X1 rule; the plan's
terms and account-wide capacity added to the common facts and to 4b's cost; Qwen3 roles beyond the
pilot marked as new decisions.

**Totals:** 32 findings (1 blocker, 17 major, 14 minor); 32 accepted, 0 rejected. Revised by track x1
on 2026-10-16: this record, DESIGN.md, and the power simulation (blocks 9–13 added; blocks 1–8 re-run
and reproduced exactly except the two intended changes, block 4b's degrees of freedom and the pilot's
undefined-CABW rule).

**Rejected findings:** none.

**Sub-proposals not adopted** (the finding itself was accepted; one line each, with the reason):
- R1, calibration (finding 1): a 16-item calibration set and df = templates − 1 → 24 items and
  df = items − 8, because n is driven by the *within-family* dispersion, and 2 items per family would
  leave 8 within-family df (upper-80% SD bound factor √(8/χ²_8(0.20)) = 1.32 vs 1.20 at 16 df [D]).
  Matching against the simulation's noise-subtracted `sigma_ta_within` → matching the observed-scale
  within-family SDs of d_i and e_i at the same m = 5, because the subtraction can truncate at 0 with 24
  items and the observed scale needs no binomial correction; σ̂_ta,within (with the reviewer's v_i) is
  still computed and reported.
- R1, templates (finding 10): clustering any pair above the atom thresholds (0.2 / 0.3) → an authoring
  rule at 0.5 / 0.6 [G] plus the 0.2 / 0.3 clustering as a sensitivity analysis, because same-family
  references share loop structure by design, so the atom thresholds could merge most of a family into
  one cluster [inference]; the within-family similarity distribution is reported so the Owner can
  lower the thresholds before freeze.
- R2, oracle isolation (finding 1): seccomp filtering of `open`/`openat` by path → no hidden data in
  any container that runs agent code, because seccomp-bpf cannot inspect path arguments
  [inference]; the static gate and canaries are kept as defence in depth.
- R2, equal information (finding 2): a byte-matched language card for Rust and C11 → a helper card
  with equivalent snippets and logged sizes, because 05 §13 keeps language content arm-specific and
  logs brief sizes rather than padding them.
- R2, token budget (finding 7): re-set the budget if Rust and Mithril `budget_tokens` shares differ by
  > 2 points → prefix-excluded accounting plus a mechanical cap doubling if either arm exceeds 5%,
  because with 240 calibration attempts per arm the SE of that difference is ≈ 2.7 points [D], so a
  2-point rule would fire on noise; the reviewer's turn arithmetic also overstates the effect (11–24%
  fewer turns for a 7–17k-token card [D], not 25–30%).
- R2, kit (finding 12): a `deny` set "exactly" equal to the Dc rows → a subset of them, because FF-REF,
  FF-LOCAL, FF-DYN, FF-ASYNC and FF-CELL are legitimate Rust with Rust meaning, and denying them would
  make the kit arm reject correct Rust.
- R2, canaries (finding 19): correct-but-non-reference canaries per arm → per reference language (Rust,
  C11, Mithril), mechanically carried to the derived arms, because the no-traits and obfuscated arms
  share Mithril's executor and the kit arm shares Rust's.

**Evidence discrepancies noted, not affecting the findings:** Reviewer 1 quoted P(K1 ∨ K2) = 0.136
(stress, n = 96, VP gap 10); the published table gives 0.137. Reviewer 2's 25–30% fewer turns is
11–24% [D] by the same formula.

---

## 13. Signature block

```text
Owner:            ______________________     Date: ____________
Freeze commit:    ______________________     (this record with Status: FROZEN; before the calibration run)
Suite root R:     ______________________     COMMITMENTS.json sha256: ______________ (sealing commit ______)
mithi sha256:     ______________________     Card hashes (T0/T1/no-traits/obf; helper cards; preamble): ______
Kit:              ready (hash ________) | not ready
Model IDs:        A ________  B ________   Local ________
n_final:          ____ (§6.3 amendment dated ________; filled by calibrate.py)
DR-017 test form: point_estimate (writes owner.decision(dr017_test_form))
```

---

## Owner questions

D0 numbers are ROADMAP §11's. Sub-items in brackets point to the split in
[docs/D0_BRIEF.md](../../D0_BRIEF.md), a separate draft, so that each answer can be signed where it
belongs.

*Status after the Owner's chat answers of 2026-10-16 (both batches, [OWNER-ANSWERS.md](../OWNER-ANSWERS.md);
pending ratification; owner track):* question 1 is answered for families (Claude through the plan;
the local Qwen3 as the ROADMAP pilot only); which Qwen3 checkpoint, and the settings, remain open.
Question 2's dollar figures are moot, because there is no metered spend; its sample-size choices
remain and are now priced in plan tokens (section "X1 under the 2026-10-16 owner constraints").
Question 3 becomes D0_BRIEF Q18 and Q17. Question 4 now concerns the Claude Code plan's data-use
setting. Question 6 is moot under the Owner's X1 rule (option 4b, one kill-carrying family).
Question 10 now decides which template count the generated suite uses. Two new questions: accept the
Claude Code runner with unpinned sampling and an isolated configuration (OWNER-QUEUE D07), and do
the plan's terms and capacity carry X1's Claude attempts (OWNER-QUEUE A20)? All open questions are
consolidated, deduplicated and ranked in [OWNER-QUEUE.md](../OWNER-QUEUE.md).

1. **D0-10 [D0-10c], model families.** Which two frontier families carry the kill (family A presumably
   Claude), which exact model versions, and with what reasoning and sampling settings? Which local model
   runs the pilot? Who provides API keys and at what rate limits (about 16 concurrent sessions per
   family are assumed [G])?
2. **D0-10 [D0-10a], budget.** At n = 96, X1 is estimated at $5.6–18.9k [D, DESIGN §16] against
   ROADMAP's $7–15k; at the cap n = 160, $6.6–22.7k [D]. The increase comes from 96 rather than 60 items,
   authoring up to the cap (228 items), the calibration set, the doubled planted corpus and family-B
   review sessions. Options: approve; or keep the iteration items for calibration (Question 18) and
   author only to n = 120 (cap 120 instead of 160), accepting that a Rust VP@1 near 0.30 then ends in
   §6.3 step 5 [S, block 10]; or accept R-CABW only in the low and mid scenarios (n = 96 regardless),
   knowing it fails under high variance at 64–80 items [S].
3. **D0-11 [D0-11b], authorship.** Is family B (a non-Claude family) the author of the held-out,
   calibration and iteration items, the planted corpus and the item reviews? Is a third family
   available for authoring, review, the semantic guard and the kit acceptance corpus?
4. **API data handling.** Are the API accounts configured so that inputs are not used for training? The
   sealed items are reused as M1 anchors, so this matters beyond X1.
5. **Decision statistics.** Do you accept the identity-link stratified estimator (§7.3) for VP@1, and the
   stratified ratio estimator with an item-cluster linearised SE for Γ̂, which is **not** a mixed model,
   as the decision statistics, with logistic GLMMs (VP@1 and CABW) as reported secondaries? This
   deviates from 05 §13 and, for CABW, reads DR-017's "task-clustered mixed-effects analysis" as
   "task-clustered SE".
6. **One-family breaches.** Do you agree with §7.7's reading of 05 §13 ("a breach in one family only
   goes to the Owner"), which never softens a pooled kill? Expect referrals in 0.11–0.18 of runs even
   with no interaction [S].
7. **CABW and joint power requirements.** ROADMAP gives operating characteristics only for the VP@1 kill.
   This record makes 05 §13's CABW analogue binding, extended to every VP gap in the pass region
   (R-CABW), and adds R-JOINT. Should ROADMAP §3.2 state them?
8. **Named parameters.** `agent.hole_use_floor` = 0.10 and `agent.dc_rate_bound` = 0.10 are proposed
   [G]; they feed DR-003, DR-004 and DR-005's triggers.
9. **Holes in the Mithril arms.** Should `mithi`'s hole report reach the Mithril arms at X1
   (recommended, for symmetry with the tooling arm), or should only the tooling arm get hole context?
10. **Templates.** Accept the authoring cost of ≤ 1 held-out item per template (up to 184 distinct
    held-out templates plus 44 for iteration and calibration), or take n = 120 with ≤ 2 per template?
11. **Execution host and firewall.** The desktop's WSL2 in daytime (≈ 16–21 h of 12 cores [D], competing
    with X2's daytime fuzzing, and requiring the Claude settings deny rules of DESIGN §4.6 while
    held-out material is on the machine) or a rented Linux VM (no family-A sessions on it)?
12. **Pilot family.** T-ROUTE is proposed. Is another family preferred?
13. **Canary.** Publish the canary UUID at freeze (lets corpus builders filter it), or keep it private?
14. **ROADMAP observations (no change made).** (i) ROADMAP's VP@1 requirement is met by any n ≥ 60 under
    every simulated scenario [S], so it does not constrain the design; the CABW co-primary does.
    (ii) Amber (b)'s 5-point threshold sits near the noise floor of the secondary arms:
    P(fire | true cost 0) ≈ 0.07–0.10 at 64 items [S]. (iii) ROADMAP §10's X1 attempt line assumes 60
    items, which is too few for the CABW co-primary and for R-JOINT under high between-item variance
    [S]. (iv) ROADMAP's "the kill's operating characteristics" can be read for K1 alone or for the
    disjunctive kill; this record adopts the stricter joint reading (R-JOINT).
15. **Realised CABW power.** DR-017's UNDERPOWERED trigger reads only SE(Δ̂). Should SE(Γ̂) > 3.90 points
    also make the result UNDERPOWERED (for K2 or for the whole verdict)? It would void the run in
    0.05–0.14 of high-variance worlds and 0.35–0.56 of stress worlds at n = 96 [S, block 2]. Not adopted
    without your decision.
16. **Interval convention.** X1 publishes two-sided 90% intervals (one-sided 95% per bound); 05 §13's M1
    CABW test uses a one-sided 90% bound. Should DECISIONS / 06 §7.2 fix one convention for
    `harness.*.ci_low` / `ci_high`? This record adds `.ci_level` and `.ci_sides` facts meanwhile.
17. **Your role in item review.** Provisional: you review iteration items before the card freeze and a
    seeded sample of 24 held-out items after it (≈ 6 h [D from G]); independent family-B sessions review
    all held-out items before sealing. Alternatives: you review all held-out items after the card
    freeze (≈ 13–21 h [D from G]), or you take no part in card editing and only sign the card hash.
18. **Calibration set.** A dedicated 24-item calibration set (recommended; 480 attempts, $0.2–1.0k [D])
    or the 20 iteration items (cheaper; biased toward under-sizing n, so the scenario floor "high" and
    the conservative base rates of §6.3 would be the only protection)?
19. **Obfuscation scope.** ROADMAP says "renamed keywords". This record also maps primitive types and the
    keyword-like prelude names (`todo!`, `Some`, `None`, `Ok`, `Err`, `Option`, `Result`, `Vec`) and
    removes every language name from the obfuscated arm's texts (DESIGN §10.4). Accept, or keep keywords
    and primitive types only?
20. **`topk` parity.** Give `topk(k, Ties::LowerIndex, Nan::Last)` to the Rust and C11 helper packs
    (provisional), or remove it from `mithi`'s X1 std so that every arm writes T-ROUTE selection by hand
    (then FF-TIES's X1 fix text points to explicit comparisons, unlike 01 §2.5)?
21. **Planted corpus.** A dev half and a sealed confirmation half of ≥ 100 items each (≥ 200 in total) so
    that P-2 cannot be passed by iterating on its own test set. Approve the extra authoring?

---

## Budget per ROADMAP §10

| Line | ROADMAP §10 [inference] | This record |
|---|---|---|
| X1 held-out | 60 × 5 × 3 primary arms + 60 × 3 × 3 secondary arms, × 2: ≈ 2.9k attempts, $1.4–5.8k | 4,032 attempts at n = 96, $2.0–8.1k [D]; 5,952 at n = 160, $3.0–11.9k [D] |
| X1 card iteration | 20 × 5 × 3 epochs × 2 Mithril arms × 2: ≈ 1.2k, $0.6–2.4k | unchanged |
| X1 local pilot | 10 × 3 × 2 arms × 1 local: 60, $0; 5–10 machine h | unchanged |
| Calibration run | — | 480 attempts [D], $0.2–1.0k [D] |
| Authoring and review | (inside X1's total) | $1.8–5.4k [D from G, DESIGN §16] |
| X1 total (ROADMAP §3.2) | $7–15k, ~55 h, including the tooling kit and the checker precondition | ≈ $5.6–18.9k at n = 96, $6.6–22.7k at n = 160 [D, DESIGN §16]; ≈ 45 owner hours [D from G, DESIGN §16] |

The per-attempt price ($0.5–2 per agentic attempt with a frontier model) is ROADMAP §10's
[inference]. The pinned price table (§2) replaces it at freeze. Under the Owner's chat answer to
D0-10a ("No metered API", pending ratification) no line of this table is a spend authorisation; the
costs become Claude Code plan tokens and desktop hours, priced per option in the section "X1 under the
2026-10-16 owner constraints".

---

## Amendments

None. (The §6.3 recomputation will be appended here, dated, before any held-out attempt runs.)
