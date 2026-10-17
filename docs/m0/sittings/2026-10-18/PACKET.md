# Sitting 1: Sunday 2026-10-18, evening

Status: **DRAFT packet**, prepared Fri 2026-10-16 by the packet track (a Claude agent) and revised the
same night after one review (Claude, same family, independent context; [Review log](#review-log)).
The lead engineer finalises it by Sat 2026-10-17, night. He fills the three `<<FILL: …>>` freeze
hashes and drops any record that is not FROZEN by then.

**Time** [inference; sums D]. The core items (0–3, 7 and 8) take about **75–105 minutes if your
signing key exists before Sunday**, and 90–165 minutes if you create it at the sitting. Each record you
sign on its summary adds 15 minutes; reading a record in full adds 1–2 h [D0_BRIEF §4.13]. With the
key made beforehand and items 4 and 5 signed on their summaries: **≈ 105–135 minutes**. To stay near
2 hours:
- make the key before Sunday (HOW-TO-SIGN steps 1–2, 15–60 min, any time Saturday or Sunday);
- sign records on their summaries and the logged reviews;
- leave item 6 for 10-25 first (nothing slips), then item 5 (only X0's verdict waits).

The **shortest useful sitting** is items 0–3 and 8: about 70–100 minutes with the key made beforehand.

**What you decide here, in one line.** Choose how you sign. Ratify your six chat answers. Sign up to
three frozen records (item 6 is optional tonight). Decide which pre-night settings you will apply
yourself.

Source of truth for every item:
- your verbatim answers, [OWNER-ANSWERS.md](../../OWNER-ANSWERS.md);
- the lines you tick, [D0_BRIEF](../../../D0_BRIEF.md);
- the ranked queue, [OWNER-QUEUE](../../OWNER-QUEUE.md).

Every signature line below is copied verbatim from D0_BRIEF. You tick it there. The tag-message form
beside it uses the Appendix B grammar; [HOW-TO-SIGN](HOW-TO-SIGN.md) has the mechanics. Agents never
tick, fill or write tag messages.

**Two facts that are new since OWNER-QUEUE's agenda.**
1. **X1 may not fit your plan.**
   - At the current estimate, X1's Claude attempts under your rule need about **13–55 full weekly
     windows** of plan usage [D, rough; X1-amendment-1 §6.1]. If anything else used the window while
     the conversion was measured, X1 fits better than that.
   - A smoke run measures it (X1-amendment-1 §6.2). It starts with 5 attempts, about 2–8% of one weekly
     window at the estimate [D], and continues in batches of 20, up to 65 attempts, only while the
     readings cannot decide. The rule stops as soon as the readings exclude a fit, so the whole run costs
     at most about 10 points of one weekly window at the default s and K [D].
   - It needs two things from you: your check of the plan's terms first (A20, item 2), and **the whole
     account quiet while it runs**. The agent team is paused and you do not use Claude: up to about 1 h
     for the first 5 attempts, and up to about 3 h for each further batch of 20 [D from G].
   - Your plan today: the weekly all-models window read **43% at 20:27 PT on 10-16**, its first day,
     and resets Fri 10-23 at 05:00 PT [M]. That is above COST §5's pacing line of about 24% [D].
   - This packet therefore leaves the template-author choice (Q18) until that measurement exists.
2. **The measurement service is not ready.** Its v0 was committed on 10-16 as "not usable yet" [M,
   commit `93f67a8`]. So the first pilot night waits for the service's acceptance check as well as for
   your signature. Signing the noise-pilot record tonight keeps 10-23 and 10-24 open. Signing on 10-25
   still fits the four nights in week 1 (10-25 to 10-28).

---

## Agenda

"Summary level" means signing on this packet's summary and the record's logged same-family review.

| # | Item | Minutes [inference] |
|---|---|---|
| — | **Before Sunday, optional:** HOW-TO-SIGN steps 1–2 (key and git configuration) | 15–60 [D0_BRIEF §4.3 item 6: 0.25–1 h of key setup] |
| 0 | Read this packet (before or at the start) | 15 |
| 1 | Signing mechanics: D0-9a (with Q2) | 15 if the key exists; 30–75 if you create it now [D0_BRIEF §4.3 item 6] |
| 2 | Ratify the six chat answers (R1–R6). Optional: your plan-terms check (A20) | 20–35 [OWNER-QUEUE row 2]; A20 adds 30–60 [D0_BRIEF §4.13] |
| 3 | The other lines whose latest sitting is tonight: D0-7a, D0-8 with Q7, Q13; five answers in the commit message | 10–20 |
| 4 | X4-noise-pilot record, if FROZEN | 15 at summary level; 1–2 h to read in full [D0_BRIEF §4.13] |
| 5 | X0 record (FROZEN by the lead engineer) | 15 at summary level; 1–2 h in full |
| 6 | X1-amendment-1, if FROZEN. **Optional tonight** | 15 at summary level; 1–2 h in full |
| 7 | Quiet-night PRE-NIGHT checklist: which settings you will apply | 5 |
| 8 | Close: commit, signed tags, verifier, push | 10–15 |
| | **Total** | see [Time check](#time-check) |

---

## 1. Signing mechanics (D0-9a, with Q2), 15–75 min

**Summary.** Under A10, authority is a signature, never a sentence. Nothing can be SIGNED and none of
your chat answers can be ratified until you choose a signing method and key. Git on the laptop has no
signing key configured yet [M, HOW-TO-SIGN "Facts checked"]. The recommended method works like this:
- one commit of your own with the ticks in D0_BRIEF;
- one signed, annotated tag `d0-sign-1` on that commit, whose message lists every decided line;
- one signed tag per FROZEN record, on its freeze commit.

Agents run under your Windows account. So a key with no passphrase and no hardware touch is no stronger
than a typed name.

Creating the key takes 15–60 minutes the first time [D0_BRIEF §4.3 item 6]. Doing HOW-TO-SIGN steps 1–2
before Sunday leaves only the decision for the sitting.

**Full record:** [HOW-TO-SIGN](HOW-TO-SIGN.md); [D0_BRIEF §4.3](../../../D0_BRIEF.md#43-d0-9-owner-key-management)
and Appendix B.

**Options.** D0-9a:
- **HW**: a hardware key that needs a touch;
- **PASS**: a passphrase key, never loaded into ssh-agent;
- **SOFT**: a plain key; weak;
- **NO**: nothing can be signed;
- or the interim chat form (b) in HOW-TO-SIGN, which leaves every item pending re-signature.

Q2 asks whether ROADMAP should name an interim M0 signing method.

**Recommendation.** **PASS** with an SSH key, as in HOW-TO-SIGN (a), or **HW** if a FIDO2 token is at
hand. Q2: **YES** [G, OWNER-QUEUE A01].

**Signature lines**, verbatim:

```text
D0-9a  Value (required): key fingerprint = ________
D0-9a  [ ] HW (recommended)   [ ] PASS   [ ] SOFT   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
Q2   [ ] YES   [ ] NO   [ ] OTHER: ________   Tag: d0-sign-__
```

Tag lines: `D0-9a: <HW|PASS|SOFT|NO>; key fingerprint=SHA256:<…>` and `Q2: <YES|NO>`.

---

## 2. Ratify the six chat answers (R1–R6), 20–35 min

**Summary.** On 10-16 you answered six questions in chat. They are logged verbatim, with the option
text you saw, in [OWNER-ANSWERS.md](../../OWNER-ANSWERS.md). Work proceeds on them provisionally. They
become AUTHORITY facts only when `d0-sign-1` names them. The reading of each, which is yours to confirm
or correct, is [D0_BRIEF §0](../../../D0_BRIEF.md#0-decisions-received-chat-2026-10-16-to-be-ratified).

| Answer | Your words | Line(s) to tick | Note |
|---|---|---|---|
| R3 | "Batch weekly review" | D0-12 YES; D0-12x **X0**; D0-12i CONFIRMED | D0-12x = X0 is a loosening of ROADMAP §11 that only you can grant; the brief's own recommendation was ROADMAP |
| R1 | "No metered API" | D0-10a **AMEND** with its required Value, for example `T1 cap = $0; stop-loss = no metered key exists` | A plain NO would read as ROADMAP's "No M0". Confirm that R4 supersedes this answer's "X1 … stays amber" |
| R6 | "Sunday evening" | D0-10b, Value `H = __ h/week; signing slots = Sun evening` | **H is required** (OWNER-QUEUE A15). The plan assumes 15 h a week (Plan B) until you sign |
| R2 | "Local Qwen3 via Hearth" | D0-10c **AMEND**, Value `Family B = none; local model = <the Qwen3 checkpoint>` | As the pilot only. Any other Qwen3 role is Q17, deferred ([below](#not-on-tonights-agenda)). Picking and locating the exact file takes 0.5–1 h [D0_BRIEF §2]: if you do not know it, write the model name only, for example `Qwen3-30B-A3B Q4` (the file OWNER-QUEUE C02 names), and leave the file to C02 |
| R5 | "4 pilot nights, then a rule" | D0-10d **AMEND** (your Values differ from the printed rec) | Suggested Value [OWNER-QUEUE A17 default]: `pilot-week nights = 4; window = 23:00-07:00 PT; first night = the first W1 night after the X4-noise-pilot record is SIGNED and the service passes its acceptance check; co-tenant jobs paused = yes (GEMS kept out by me); rate after the pilot = PLAN §6.3 rule with 4-7 nights a week and 25% contingency, re-signed` |
| R4 | "Claude kills; pass provisional" | Q16 **OPT4_STRICT** | The design is item 6. **OWNER-QUEUE A20 asks for your check of the plan's terms before you ratify R4.** If you have not checked them, you may leave Q16 unticked: R4 stays a provisional chat answer, and nothing slips before X1's freeze (≈ W5). Or tick it knowing that A20 or the smoke-run gate may force a new answer |

Optional, cheap: Q4 (OTHER: X0 exception), Q5 (CONFIRM, with Q16), Q14 (moot), Q15 (moot) [D0_BRIEF §7].

**Optional tonight: A20, your check of the plan's terms** (30–60 min [D0_BRIEF §4.13]). Do the Claude
Code plan's terms allow scripted, headless X1 attempts, about 2,900–3,800 of them (OWNER-QUEUE A20)?
It is needed before Q16 is ratified and before the smoke run, which is itself scripted, headless use
(X1-amendment-1 §2.2). Agents do not read the terms for you. A20 has no D0_BRIEF line: write your
answer in the signed commit message, or in item 6's tag if you sign it.

**Options.** For each line: tick what you answered, or correct it (AMEND or OTHER), or leave it
unticked, which keeps it provisional.

**Recommendation.** Tick each line as you answered it, with the Values filled; Q16 as the R4 row says.
- Tick **AMEND, not YES, wherever a Value differs from the printed `(rec …)`**. Otherwise the verifier
  flags the line.
- No `;` inside a Value or an AMEND text.

**Signature lines**, verbatim:

```text
D0-12   [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
D0-12x  [ ] ROADMAP (recommended)   [ ] X0   [ ] X0+PILOT   [ ] AMEND: ________   Tag: d0-sign-__
D0-12i  [ ] CONFIRMED   [ ] WITHDRAWN   Tag: d0-sign-__
D0-10a  Value (required): T1 cap = ____ (rec $3k); stop-loss = ____ (rec COST.md §5 plus ceilings)
D0-10a  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
D0-10b  Value (required): H = ____ h/week; signing slots = ________
D0-10b  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
D0-10c  Value (required): Family B = ________; local model = ________
D0-10c  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
D0-10d  Value (required): pilot-week nights = __ (rec 4); window = __:__-__:__ local; first night = ______; co-tenant jobs paused = ___ (rec yes); rate after the pilot = ______ (rec PLAN §6.3 rule, re-signed)
D0-10d  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
Q16  [ ] OPT4_STRICT (recommended; your chat answer)   [ ] OPT4_REFERRAL   [ ] OPT1   [ ] OTHER: ________   Tag: d0-sign-__
```

Tag lines, in this form:
- `D0-12: YES`
- `D0-12x: X0`
- `D0-12i: CONFIRMED`
- `D0-10a: AMEND; text=<…>; t1 cap=<…>; stop-loss=<…>`
- `D0-10b: YES; h=<…> h/week; signing slots=Sun evening`
- `D0-10c: AMEND; text=<…>; family b=none; local model=<…>`
- `D0-10d: AMEND; text=<…>; pilot-week nights=4; window=<…>; first night=<…>; co-tenant jobs paused=<…>; rate after the pilot=<…>`
- `Q16: OPT4_STRICT` (if you tick it tonight)

---

## 3. The other lines whose latest sitting is tonight, 10–20 min

**Summary.** OWNER-QUEUE gives each of these 10-18 as its latest sitting. Unanswered, each either
blocks its step or registers its default, so each is here rather than under "not on tonight's
agenda".
- **D0-7a** (unattended measurement, only inside quiet windows) is needed before the first unattended
  pilot night (OWNER-QUEUE A19).
- **D0-8** (the desktop is the measurement host; a second box only when D-22 fires), with **Q7** (does
  GEMS count as "the Owner's own use" for D-22?), is needed before the first pilot night too
  (OWNER-QUEUE A18). D0-8 is ROADMAP's M4 item, but it bears on the pilot nights.
- **Q13** (OWNER-QUEUE A16): does evidence grade or unblock-first order the review queue? The queue is
  ordered unblock-first already.
- Five items have no D0_BRIEF line. They cannot go in the `d0-sign-1` tag, because the verifier would
  reject the whole tag. Put them in your **signed commit message** instead:
  - **A02**: may the lead engineer commit *freeze* commits between sittings? If the X0 freeze (item 5)
    was committed before tonight, it relied on this answer. If you answer (a) "no": signing item 5
    tonight confirms that freeze. If you also defer item 5, any X0 data collected since the freeze are
    logged as collected under a freeze you have not confirmed; only X0's verdict waits.
  - **B13**: approve the desktop job-wrapper design (8-thread semaphore, refusal inside quiet windows,
    start and end stamps).
  - **B08**: is a weekly total per track enough for owner-hour logging?
  - **B04**: X3's denominator H for "schedule ≤ 30% of hand-written lines": 303 (the strict default) or
    369. Tonight is the last sitting before the first schedule line on Fri 10-23. An answer after X3
    data exist is post-data (OWNER-QUEUE B04).
  - **A07**: confirm the Rust install already made (rustc 1.99.1 by rustup on 10-16 [M, OWNER-QUEUE A07])
    and say whether a portable LLVM and a C compiler may follow on the laptop.

**Full record:** [D0_BRIEF §4.4](../../../D0_BRIEF.md#44-d0-7-forge-authority),
[§4.10](../../../D0_BRIEF.md#410-d0-8-measurement-host) and §7 Q7, Q13; [OWNER-QUEUE](../../OWNER-QUEUE.md)
A02, A07, A16, A18, A19, B04, B08, B13.

**Options.**
- D0-7a: YES (ROADMAP §11's wording), NO (attended only: someone present for 60–215 quiet hours
  [inference, ROADMAP §10]), or AMEND.
- D0-8: YES, NO or AMEND.
- Q7: YES (if GEMS cannot pause inside windows, D-22 fires at once), NO (GEMS is a co-tenant to
  schedule around), or OTHER. Your R5 answer already keeps GEMS out of the window hours.
- Q13: EVIDENCE_GRADE, UNBLOCK_FIRST or OTHER.
- A02: (b) yes, or (a) no (a record ready just after a sitting waits up to 7 days).
- B13: approve or change.
- B08: yes or finer.
- B04: 303 or 369 (and confirm that shared helpers count once per file).
- A07: yes, or no (builds then run in WSL on the desktop under the 8-thread cap).

**Recommendation.** D0-7a **YES**. D0-8 **YES**. Q7 **YES** (D0_BRIEF's recommendations). Q13
**UNBLOCK_FIRST** [G, OWNER-QUEUE A16]. A02 **(b) yes** [G]. B13 **approve**. B08 **yes**. B04 **303**,
the strict default (OWNER-QUEUE B04). A07 **yes** (PLAN Q4).

**Signature lines**, verbatim:

```text
D0-7a  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
D0-8  [ ] YES as recommended   [ ] NO   [ ] AMEND: ________   Tag: d0-sign-__
Q7   [ ] YES   [ ] NO   [ ] OTHER: ________   Tag: d0-sign-__
Q13  [ ] EVIDENCE_GRADE   [ ] UNBLOCK_FIRST   [ ] OTHER: ________   Tag: d0-sign-__
```

Tag lines: `D0-7a: <YES|NO|AMEND>`, `D0-8: <YES|NO|AMEND>`, `Q7: <YES|NO|OTHER>`,
`Q13: <EVIDENCE_GRADE|UNBLOCK_FIRST|OTHER>`. Commit-message lines, in your words, for example
`A02: yes, freeze commits may land between sittings` or `B04: H = 303`.

---

## 4. X4-noise-pilot record (if FROZEN), 15 min at summary level

**Freeze commit: not FROZEN: item dropped to sitting 2 (Sun 10-25). The record needs your answers to C01, C02, C25 and D0-7a first, and the service still lacks observe mode, hygiene sensors and the session driver (X4 track, 2026-10-17)**

**Summary.**
- **What it is.** The first quiet-night measurement and the one your R5 answer schedules. It runs 20
  microbenchmark A/A sessions × 24 blocks and 3 end-to-end A/A sessions × 12 blocks [target] on 4
  nights, 23:00–07:00 PT.
- **What it fixes.** Frozen rules turn its data into every data-dependent constant of X4's later
  calibration: σ̂_d, n and N, the clip c, the load-gate threshold. The values enter X4 by a pre-data
  fill-in amendment.
- **What it is not.** It is **excluded from every gate tally**, so it decides no pass or kill.
- **Preconditions for collection.** This record SIGNED, with the X4-calibration rules FROZEN with it;
  D0-7a (item 3; the X4 track's draft lets the nights run attended until D0-7a is signed); the
  measurement service v0 passing its acceptance check (not yet: commit `93f67a8` says "not usable
  yet" [M]); the pilot's two binaries built and hashed (its §2); and the settings you choose (item 7).

**Full record:** [X4-noise-pilot.md](../../prereg/X4-noise-pilot.md), split out of the
[X4 DRAFT](../../prereg/X4-integrity.md) by the X4 track (DRAFT when this packet was revised; its review
log was still pending). Design:
[MEASUREMENT-SERVICE §5.4](../../../../experiments/x4-integrity/MEASUREMENT-SERVICE.md).

**Options.**
- **SIGN** now: the nights can start as soon as the service is ready, 10-23 at the earliest.
- **DEFER** to 10-25: the 4 nights still fit in W1, 10-25 to 10-28.
- **Ask for changes.**

**Recommendation.** **SIGN**, if it is FROZEN with a logged review and a summary-level signature is
enough for you. It costs nothing if the service is late, and it keeps the earliest nights open. If you
want to read the record in full (1–2 h), DEFER to 10-25: the nights still fit in W1.

**Signature.** A signed tag on the freeze commit, `prereg-sign-x4-noise-pilot`. The message (yours):

```text
PREREG-SIGN 1
record: docs/m0/prereg/X4-noise-pilot.md
freeze: <full hash>
sitting: 1 (2026-10-18)
<any condition in your words>
```

---

## 5. X0 record (FROZEN by the lead engineer), 15 min at summary level

**Freeze commit: `152fa33cc24225d78806bc028a1985fffbd3148b` (FROZEN 2026-10-17 01:25 PT; census scheduled from 07:07 PT Sat 10-17)**

**Summary.**
- **What it tests.** X0 compiles Hearth's three quant files with every configuration and XED-decodes
  them. The test: do we know which instructions real compilers emit (ROADMAP §3.1)?
- **No kill.** X0 has a pass, three ambers and a narrowing; ROADMAP gives it no kill.
- **Evaluation order.** A validity check V comes first: complete coverage records, decoder agreement,
  an exact independent re-derivation, and frozen input hashes. If V fails, the tooling is fixed and the
  census re-runs, bounded at M0 week 3.
- **The outcomes after V** (record §8):
  - **Amber (c)**: a coverage gap under a release compiler.
  - **Amber (b)**: a flag defect in any main-union configuration, built with Hearth's own flags:
    contraction found (P2 > 0) or a P3 screen flagged. A flag-defect report is mandatory.
  - **Amber (a)**: the union of forms exceeds 2 × T_forms = **204** (|B_iform| = 102 [M, x0prep]), or
    more than 20 FP-sensitive XED iclasses. The table then covers MSVC and Clang only.
  - **Pass**: none of these.
  - The **narrowing** is judged with X2 at week 6.
- **Expected before data, by its own registration** [inference, record §8 E1–E4]:
  - Amber (b) under config B-cmake (already seen on the flags);
  - Amber (a) is plausible on the FP-iclass count and on the union size.

  These follow from the **strict readings** in Appendix A (OQ-1 to OQ-5).
- **Your exception R3 applies.** Collection may start as soon as X0 is FROZEN, so by Sunday X0 data
  may exist. Any answer that loosens a reading is then a **post-data amendment**, with the verdict
  reported both ways. OQ-1 = OP_CLASS also needs a ROADMAP amendment first.
- **Only the verdict waits for your signature**, not collection.

**Full record:** [X0-census.md](../../prereg/X0-census.md), §8 (outcomes), Appendix A (OQ-1 to OQ-7),
§13 (signature block).

**Options.**
- **SIGN** with OQ-1 to OQ-7 "deferred". The strict defaults stand, and T_forms is as registered.
- **SIGN with answers.** A loosening after data is post-data.
- **DEFER** to 10-25. Only X0's verdict waits, by at most a week.

**Recommendation.** **SIGN with OQs "deferred" and T_forms "as registered"**, if a summary-level
review plus the logged same-family reviews are enough for you. If you want to read the record in full
(1–2 h [D0_BRIEF §4.1]), **DEFER** to 10-25: nothing but the verdict waits.

**Signature.** A signed tag on the freeze commit, `prereg-sign-x0-census`. The message mirrors the
record's §13 block:

```text
PREREG-SIGN 1
record: docs/m0/prereg/X0-census.md
freeze: <full hash>
sitting: 1 (2026-10-18)
OQ-1..OQ-7: <deferred | your answers>
T_forms: <min(|B_iform|, 105) as registered | accept recomputed |B_iform| = __>
```

---

## 6. X1-amendment-1 (if FROZEN), optional tonight, 15 min at summary level

**Freeze commit: `<<FILL: X1-amendment-1 freeze commit, or "not FROZEN: item dropped">>`**

**Summary.** The amendment carries your rule R4 into X1's design.
- **Kill and pass.** Claude is the only kill-carrying family at M0. K1 (VP@1 gap > 15) or K2 (CABW
  > 5 worse than Rust) on Claude's estimate is binding: STOP-L. A pass is provisional
  (`pass_one_family`) until a second frontier family confirms it at M1. The local Qwen3 pilot stays
  outside the kill. No threshold moves.
- **What a binding kill costs when Mithril is acceptable.** At n = 136 the kill still fires in about
  7% of worlds where Mithril is truly 5 points behind on VP@1 with equal CABW (P(K1 or K2) = 0.068),
  and in about 11% at a true 10-point VP@1 gap (0.106). When CABW is truly equal, the CABW rule alone
  fires in 6–8% across VP@1 gaps of 0 to 15 [S, block 16]. The record's limits are 10% at the points
  they name (R-JOINT at the 5-point gap; R-CABW at every VP@1 gap up to 15); the 10-point gap is
  inside the pass region but not one of those points. At a true gap of exactly 15, K1 fires about
  half the time, by construction [S].
- **Sample size.**
  - ROADMAP's own VP@1 requirement is met at n = 60 even with one family [S].
  - The record's binding CABW and joint requirements raise the planned held-out n from 96 to **136**
    [S, 20,000 replicates; reproduced by the review]. The cap stays 160.
- **The runner.** Headless Claude Code sessions with an isolated configuration and only the harness
  tools, paced to at most a share s of each weekly window (default 50% [G]). The effort level is a
  field you sign; the reference gives `medium` as Opus 5.5's API default, and what headless Claude
  Code uses is not verified.
- **The plan problem.** At the current per-attempt estimate (0.26–0.92 M tokens [D from G]), the run's
  3,456 Claude attempts need about **13–55 full weekly windows** [D, rough: 1 window ≈ 58–71 M tokens
  from the recorded 10-16 readings]. So the amendment adds a **feasibility gate** (§6.2):
  - a smoke run on public items, 5 attempts and then batches of 20 up to 65, on a quiet account,
    measures the window share per attempt; whole-point readings are handled by a ±1-point bound on
    the cumulative change;
  - it ends RUNNABLE, NOT RUNNABLE or UNDETERMINED; the last two go to you, and X1 does not freeze
    until you answer.

**Full record:** [X1-amendment-1.md](../../prereg/X1-amendment-1.md), §1 (your words), §4 (n), §5
(template options, decided by Q18 later), §6 (plan usage and the gate), §10 (what you sign).

**Options.**
- **SIGN** as frozen, filling §10's fields: model, effort, runner, plan check, share s, cap, the gate's
  K.
- **SIGN** with "plan terms not yet checked". The smoke run then waits, and X1 may not freeze, until
  you have checked. OWNER-QUEUE puts A20 before R4's ratification, so you may prefer to sign after A20.
- **DEFER** to 10-25 or later. Nothing slips: X1 freezes about W5.
- **Ask for changes.**

**No recommendation on timing; either is reasonable, and it is your call.**
- **SIGN now:** the gate's K and s are fixed before the smoke run measures w, so they cannot be tuned
  to the result.
- **DEFER:** you sign after reading a reviewed record and, if the smoke run has happened by then, with
  a measured w. The gate is then evaluated with the s and K you sign knowing w, and the record says so.
- **Defaults if you sign** [G]: model `claude-opus-5-5`, s = 50%, cap 160, K = 6 weeks. Effort has no
  default (X1-amendment-1 §2.1).
- Either way, say in the commit message whether the **smoke run** may use your plan in W1: 5 attempts
  first (about 2–8% of one weekly window at the estimate), at most about 10 points in all at the
  default s and K, with the account quiet while it runs. It is development, not collection, and
  needs no signature, but it needs your A20 check first.
- Leave Q18 (template author) and Q17 (Qwen3 roles) until after the smoke run.

**Signature.** A signed tag on the freeze commit, `prereg-sign-x1-amendment-1`. The message holds the
§10 fields in your words:

```text
PREREG-SIGN 1
record: docs/m0/prereg/X1-amendment-1.md
freeze: <full hash>
sitting: 1 (2026-10-18)
rule: OPT4_STRICT as written
claude model: <…>; effort: <…>; runner: <accept | …>; plan check: <checked-allowed | not yet | not allowed>
share s: <…>%; cap: <…>; feasibility gate: as §6.2, K = <…> weeks
```

---

## 7. Quiet-night PRE-NIGHT checklist, 5 min to decide (B10)

**Summary.**
- The commands below are **for you to run yourself**. Agents never change system or security
  settings. The measurement service only reads each setting, and refuses or voids a session on a
  mismatch.
- Decide tonight which ones you will apply. Run them any time **before the first pilot night**, about
  20–40 minutes [inference], outside this sitting.
- Not applying one means more voided sessions. The void rate feeds D-22.
- None of these commands has been run or tested by any agent.
- **The authority is the X4 track's record**, [X4-noise-pilot §11](../../prereg/X4-noise-pilot.md),
  which appeared after this packet was first drafted. This item follows it. If the frozen record's §11
  differs, the frozen record wins.

**Full record:** [X4-noise-pilot §11](../../prereg/X4-noise-pilot.md);
[MEASUREMENT-SERVICE §7](../../../../experiments/x4-integrity/MEASUREMENT-SERVICE.md).

**Once, before the first pilot night** (elevated PowerShell on the desktop):

```powershell
# 1. Power plan and core parking: powercfg prints the new scheme's GUID; record it (it is pinned in the
#    record's pre-night fill-in amendment)
powercfg /duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
powercfg /changename <NEW-GUID> MITHRIL-MEASURE
powercfg /setacvalueindex <NEW-GUID> SUB_PROCESSOR CPMINCORES 100
powercfg /setacvalueindex <NEW-GUID> SUB_PROCESSOR CPMAXCORES 100
powercfg /setactive <NEW-GUID>

# 2. Defender exclusion for the data directory (advisory; a security trade-off, your call)
Add-MpPreference -ExclusionPath 'D:\mithril-data'
#    Search indexer: remove the data directory in Control Panel > Indexing Options (no stable CLI)

# 3. No change: check that scheduled maintenance and Windows Update avoid 23:00-07:00 PT
Get-ScheduledTask -TaskPath '\Microsoft\Windows\TaskScheduler\' | Where-Object State -ne 'Disabled'
```

Then the service's own read-only check, `x4svc verify-profile --collection`, must report the required
items met (X4-noise-pilot §11 item 5).

**Not needed for the pilot nights.** The first draft of this item also listed a separate measurement
user (`MithrilMeasure`) and an outbound firewall rule (SANDBOX §3.2–3.3). The X4 record says the pilot
runs trusted C only, in the sandbox's degraded mode, so those are **not** pre-night requirements for it
(X4-noise-pilot §3). They come back before later untrusted workloads (X3 kernels, Forge candidates),
in a later packet.

`D:\mithril-data` is the X4 track's path; Mithril's desktop area is `D:\mithril\`, so confirm the path
with the lead engineer first. Keep at least about 20% free space on the NVMe [G, MEASUREMENT-SERVICE
§7.4].

**Every pilot night, before 23:00 PT:**
- GEMS jobs stopped and none scheduled until 07:00 (your R5 answer);
- no Mithril agents, builds, local-model or WSL jobs on the desktop (OWNER-ANSWERS, "Consequences";
  X4-noise-pilot §11 item 4);
- `powercfg /getactivescheme` shows MITHRIL-MEASURE;
- no interactive use of the desktop until 07:00 (it voids the running session).

Open point: does an idle WSL keepalive count as "WSL activity"? It is your call (OWNER-QUEUE,
follow-ups).

**Options.** For each setting: apply, or don't.

**Recommendation.** Apply 1 and 3. Apply 2 if you accept the security trade-off: the service still
runs without it, but discards more blocks.

**Signature.** None (B10 needs no tag). Name the settings you will apply in the commit message.

---

## 8. Close, 10–15 min

At the start of the sitting, ask the lead engineer to hold commits to `main` until your push, so that
the push does not fail. Then follow [HOW-TO-SIGN](HOW-TO-SIGN.md) steps 3–6:
1. One signed commit with your ticks, and the non-D0 answers in its message.
2. `git tag -s d0-sign-1` with your message.
3. One `prereg-sign-…` tag per record you signed.
4. `git verify-tag` (the authority check), then the verifier (advisory).
5. Push.

The lead engineer then updates PLAN's status table and opens the 10-25 packet.

---

## Not on tonight's agenda

Each item has a default or waits safely for at least a week [OWNER-QUEUE "Latest sitting"; inference].
The 10-25 sitting is already heavy (OWNER-QUEUE).

**X1 and the other-family roles**, waiting for the smoke-run gate (X1-amendment-1 §6):
- **Q18 / A04**: the template author. No recommendation (D0_BRIEF Q18); GEN_OWNER matches your text.
  Consequence of waiting: no sealed template before 10-25.
- **Q17 / A05**: the Qwen3 roles. Consequence: planted-corpus authoring starts a week later.
- **A06**: the Gatekeeper store and a desktop account no Claude session can read. Consequence: nothing
  may be sealed before it, so no sealed template before 10-25 either.
- **D07**: the runner. Inside the amendment's signature if you sign it.
- **D08**: the plan's data-use setting.
- B11 (two planted-corpus halves), B12 (where X1's sandboxes run), B09 (`mithi` typing-only).

(A20 moved to item 2.)

**Nights.**
- **C01** (thread cap inside windows) and **C02** (which model file timing runs read). Both needed by
  the profile night.
- **The X4-calibration questions** C05–C10, C24, C25, C29. The record's defaults register at freeze
  if they are not answered.
- **C12 / D0-7x**: unattended daytime F1-sim.

**Records for 10-25:**
- the **M0-verdict record (B01)**, which must be SIGNED before X0's verdict, or that verdict waits to
  11-01;
- the **X2-fuzz record** (B02, B03);
- whatever of items 4–6 slips.

**Their defaults register if you say nothing by their latest sitting:**
- **B05**: x3gen, not Exo.
- **B06**: the Qwen3 thread share.
- **B07**: the X2 table stays SDM-only.
- **A08–A14**: X0's OQs, if not answered in item 5.

(B04, A07 and A16 moved to item 3: tonight is their latest sitting.)

**Cheap deferrals, any sitting:**
- D0-10e, D0-6a/b/c, D0-4 and HM-2/3/4 (all DEFER or STATUSQUO);
- **D21** (D0-9b, hardware tokens) and **D22** (D0-7b, D0-7c);
- **D23**: keep "extra usage" disabled (consistent with R1).

**Later tiers:** S0 and Hearth-maintainer items (E01–E09); M1 and later (F01–F11); tombstone
admissions; ROADMAP observations.

---

## Time check

| Part | Minutes [inference; sums D] |
|---|---|
| Before Sunday, optional: key and git configuration | 15–60 |
| Core items 0–3, 7, 8, with the key made beforehand | 75–105 |
| Core items, with the key made at the sitting | 90–165 |
| Each of items 4, 5, 6 at summary level (only if FROZEN) | +15 |
| Each record read in full instead | +1–2 h |
| A20 tonight (optional) | +30–60 |
| **Key beforehand, items 4 and 5 at summary level** | **≈ 105–135** |
| Key beforehand, items 4–6 at summary level | ≈ 120–150 |
| Key at the sitting, items 4–6 at summary level | ≈ 135–210 |

The estimates are [inference]; `scratchpad/packet/calc_packet.py` sums them [D]. To stay near 2 hours,
make the key before Sunday, then drop item 6 first (nothing slips: X1 freezes ≈ W5), then item 5 (only
X0's verdict waits, by a week). None of the three records blocks work this week except the noise
pilot's 10-23 and 10-24 nights.

---

## Review log

| Date | Reviewer | Family | Context | Scope | Result |
|---|---|---|---|---|---|
| 2026-10-16/17 | review 1: one reviewer agent, adversarial | Claude, same family | independent context | This packet, HOW-TO-SIGN and X1-amendment-1, against D0_BRIEF, OWNER-QUEUE, OWNER-ANSWERS, COST, the X1 record and the simulator. Lenses: fair presentation against the sources; time realism against the project's own unit costs; order of owner decisions against OWNER-QUEUE; signing safety; the gate's statistics; the conversion arithmetic; reproduction of the F = 1 simulation | **11 findings (5 major, 6 minor); all 11 accepted, 0 rejected.** For this packet: (1, major) "the amendment recommends GEN_QWEN3" contradicted D0_BRIEF Q18 and OWNER-QUEUE A04: now no recommendation; (2, major) "at most 2 h" rested on estimates below D0_BRIEF's and OWNER-QUEUE's: items 1, 2 and 8 re-estimated from them, a before-Sunday key step added, summary-level signing named, and the time check rewritten (≈ 105–135 min with the key made beforehand and two records); (3, major) Q16 was asked before A20, which OWNER-QUEUE puts first: the R4 row now says so, and A20 moved into item 2 as optional; (4, major) the item-6 "SIGN" recommendation is now a neutral trade with defaults if you sign, and item 6 is optional; (5, major) the smoke run needs a quiet account and A20 first: now in "Two facts"; (6, minor) the plan figures now use the recorded readings (13–55 windows); (7, minor) the false-kill rates under a binding kill are now in item 6's summary, with the 10-point gap (0.106) added because no requirement limits it; (8, minor) B04, A07 and A16 (latest sitting tonight) moved into item 3, A16 as the Q13 tag line it has in D0_BRIEF; (9, minor) A02 now states what answer (a) means for an X0 freeze made before tonight. HOW-TO-SIGN's items (10, minor) are logged there. The X1-amendment-1 items are logged in its §11. The reviser re-ran the reviewer's simulator checks [M] and read the plan readings (43%, reset Fri 05:00 PT) [M]. Not from the review: the X4 track's draft X4-noise-pilot.md appeared at 20:24 PT on 10-16 [M, file time]; item 4 now links it, and item 7 now follows its §11 (GUID-based `powercfg` commands; the measurement user and the firewall rule dropped as not needed for the pilot, its §3) |
