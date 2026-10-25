# Sitting 2: Sunday 2026-10-25, evening

Status: **FINAL** (lead engineer, Sat 2026-10-24). Drafted by the sitting2 track (a Claude agent) on Fri 10-23,
reviewed once and revised the same day. On Sat 10-24 the facts marked **[Sat]** were filled from the sources and
`git log` (origin/main `85542cd`), items 6a and 8a were added, the C05 cost was corrected, and item 4's C07 figures
were updated to the X4-calibration record; then an owner-advocate check (Claude, independent context) corrected
eight points in place ([review log](#review-log) at the end). Sources: your verbatim answers
([OWNER-ANSWERS](../../OWNER-ANSWERS.md), batches 1–5), [DELEGATED](../../DELEGATED.md),
[OWNER-QUEUE](../../OWNER-QUEUE.md) (sitting-2 list), [HOW-TO-SIGN](../2026-10-18/HOW-TO-SIGN.md),
[SIGNATURES (interim)](../2026-10-23-chat/SIGNATURES.md), the X0-A1 material, the X2, X4-noise-pilot and
X4-calibration records, SMOKE.md and the X1 isolation README. Agents never create or see a key, never tick a box or
fill a Value, and never write a tag message. The lines below are forms for you to copy and fill.

---

## The sitting on one page

**Before Sunday (optional):** make the signing key and configure git, [HOW-TO-SIGN](../2026-10-18/HOW-TO-SIGN.md)
steps 1–2 (saves 15–60 min at the sitting [D0_BRIEF §4.3 item 6]); and item 7 (the WSL traces), which X0's re-run
waits on now (at the sitting, item 7 then only records what you did). **At the start:** ask the lead engineer to
hold every commit to `main` until your push (HOW-TO-SIGN step 3).

| # | What you decide | Recommendation | Where your answer goes | Min. [inference] |
|---|---|---|---|---|
| 1 | Re-sign everything signed in chat on 10-23 | Re-sign as answered; PASS key | `d0-sign-1` tag; two record tags | 15–20 (+15–60 if the key is made at the sitting) |
| 2 | The 59 rows adopted under your delegation; may batch 4 settle a D0 line? | Accept all (the team's own rows: disclosed); glance at the 11 flagged; the D0-line question is yours, no recommendation | signed commit message | 10–15 |
| 3 | X0-A1: which P3(c) reading governs X0's verdict | **No recommendation** (see why). X0-A1 is **not appended** to the X0 record, so the answer can only be FROZEN, AMENDED-after-append or DEFER | X0 record tag | 5–10 |
| 4 | Q17, C07 (and Q18, optional) | Q17 PROVISIONAL; C07 confirm both; Q18 defer | `d0-sign-1`; commit message | 10–15 (+10–15 for Q18) |
| 5 | X3/X4 priority class | NORMAL in both | commit message | 2–3 |
| 6 | X4 noise pilot: the record (**not FROZEN**), C29, your pre-night settings | Allow a mid-week tag. C29: **no recommendation** (lapse = ALL) | commit message | 5 |
| 6a | X4's quiet hours: 525–746 h at σ_d 4% against ROADMAP §10's ≈ 215 h, so D-22 (a second measurement machine) is likely to fire | Information. **No recommendation** on what to do about it; on a blank the registered course applies | commit message (optional) | 5–8 |
| 7 | WSL trace files on the desktop's C: | (a) `guiApplications=false`, then delete (best done before Sunday) | commit message | 5 |
| 8 | An idle window for the X1 smoke run | a 2 h block this week, outside 23:00–07:00 PT | commit message or chat | 3–5 |
| 8a | Your OK for the X1 isolation layer's brief per-user AppContainer profiles (isolation README gap 3) | OK (disclosure: the team built the layer) | commit message | 2–4 |
| — | Close: commit, tags, verify, push | | | 15–20 |

**Time** [D, sums of the [inference] rows, recomputed 2026-10-24]: with the key made beforehand and Q18
deferred, **87–120 minutes, so about 90–120**, reading this page included (10). Key made at the sitting:
102–180. Q18 decided tonight: +10–15. The X4 noise-pilot record cannot be signed tonight (it is not FROZEN, item
6), so no time is planned for it. To stay near 90–120 minutes, make the key before Sunday and leave Q18 for the
sitting after the smoke-run gate (item 4).

**What waits on you today** (state at origin/main `85542cd`, read Sat 2026-10-24): agents start no WSL until you
decide item 7, so X0's re-run of configurations C and D cannot start, and its week-3 bound is 2026-11-12 [M, X0
`verdict.json`]; the X4-calibration record cannot freeze before C07 (item 4), the X4 noise pilot cannot freeze
before it, and C29 freezes as ALL unless you answer (item 6); the X1 smoke run waits for your idle window (item
8); the X2 record is freeze-ready except for your scope reading O1 (Deferred).

---

## 1. The key, and the re-signature of everything signed in chat (D0-9a; R1–R10; X0; X1-amendment-1; batch 5)

**Summary.** On 10-23 you signed in chat (interim form, HOW-TO-SIGN (b)), and the records say so: your answers
R1–R9, the X0 record frozen at `152fa33`, X1-amendment-1 frozen at `ac751b8` (R10), and on the same day the X1
smoke-run approval (batch 5). Under A10 a chat sentence is not an AUTHORITY fact; an agent wrote every log. Your
key turns them into signed tags. The recommended form: one signed commit of your own with the ticks in
`docs/D0_BRIEF.md`; one signed tag `d0-sign-1` on it; one signed tag per record on its freeze commit. A key with
no passphrase in your Windows account is usable by every agent running there, so it proves no more than a
typed name (tombstone `software_key_on_agent_account`).

**Options (D0-9a).** HW (a FIDO2 token with a touch); PASS (a passphrase key never loaded into ssh-agent);
SOFT (weak); NO (nothing can be signed, and the chat signatures stay interim).

**Recommendation.** **PASS**, as HOW-TO-SIGN step 1b, or HW if a token is at hand. Re-sign each item as you
answered it; correct any reading you disagree with (AMEND or OTHER).

**What to re-sign, and where** (lines in the Appendix B grammar; `<…>` is yours to fill):

| Item | Your words (log) | Goes in | Tag line |
|---|---|---|---|
| R7 (batch 3) | "Chat now, key on Sunday" | `d0-sign-1` | `D0-9a: PASS; key fingerprint=SHA256:<…>` (this ends the interim method, R10 item 4) |
| R3 | "Batch weekly review" | `d0-sign-1` | `D0-12: YES` · `D0-12x: X0` · `D0-12i: CONFIRMED` · `Q4: OTHER; text=<the X0 exception, in your words>` |
| R1 | "No metered API" | `d0-sign-1` | `D0-10a: AMEND; text=<…>; t1 cap=$0; stop-loss=<e.g. no metered key exists>` |
| R6 | "Sunday evening" | `d0-sign-1` | `D0-10b: YES; H=<…> h/week; signing slots=Sun evening`. **H is required** (A15). If you do not want to fix H tonight, leave D0-10b unticked: the slot part stays chat-ratified, and Plan B's 15 h/week stays the planning assumption |
| R2 | "Local Qwen3 via Hearth" | `d0-sign-1` | `D0-10c: AMEND; text=<…>; family b=none; local model=Qwen3-30B-A3B Q4` (the file you chose for timing runs in R8; DELEGATED P4) |
| R5 | "4 pilot nights, then a rule" | `d0-sign-1` | `D0-10d: AMEND; text=<…>; pilot-week nights=4; window=23:00-07:00 PT; first night=<e.g. the first night after the X4-noise-pilot record is SIGNED and its pre-night amendment is committed>; co-tenant jobs paused=yes; rate after the pilot=<e.g. PLAN §6.3 rule, 4-7 nights a week, 25% contingency, re-signed>`. Write PT: the desktop clock runs on US Eastern time [M, X4-noise-pilot §2] |
| R8 (batch 3) | C01, C02, C25, D0-7a: "Accept all four defaults" | `d0-sign-1` for D0-7a; commit message for C01, C02, C25 (they have no D0_BRIEF line) | `D0-7a: YES` |
| R4 | "Claude kills; pass provisional" | `d0-sign-1` and the X1 tag | `Q16: OPT4_STRICT` |
| R9 (batch 3) | A20: "Terms OK; run the smoke run" | X1 tag | `plan check: checked-allowed` |
| R10 (batch 4) | the interim signature of sitting 1 | the two record tags below, with the lines above | — |
| X0 record | frozen at `152fa33cc24225d78806bc028a1985fffbd3148b` | `prereg-sign-x0-census` | message below |
| X1-amendment-1 | frozen at `ac751b86f1b37e6cd7e55759e1b770335b57827c` | `prereg-sign-x1-amendment-1` | message below |
| Batch 5 | the smoke-run approval | the X1 tag (it departs from that record's controls) | line below |

Optional in the same tag: `Q5: CONFIRM` (open; consistent with R2's option text and R4 [G]); and, if you
accept the rows in item 2, the D0 lines they only assumed: `Q13: UNBLOCK_FIRST` (P6), `D0-7x: ROADMAP` with
`Q6: LITERAL` (P27). Then they are your decisions, not operating assumptions. Q14 and Q15 are moot; Q2 is
deferred.

Rules for the ticks (HOW-TO-SIGN step 3): one box per line; **AMEND, not YES, wherever a Value differs from the
printed `(rec …)`**; no `;` inside an AMEND text or a Value; at least three spaces before `Tag:`.

**Record tags** (HOW-TO-SIGN step 5: check each freeze commit first). Messages, in your words:

```text
PREREG-SIGN 1
record: docs/m0/prereg/X0-census.md
freeze: 152fa33cc24225d78806bc028a1985fffbd3148b
sitting: 2 (2026-10-25)
OQ-1..OQ-7: deferred
T_forms: min(|B_iform|, 105) as registered
P3(c) reading for X0's verdict: <FROZEN | X0-A1 once appended unchanged, X0-A1.1 SHA-256 49e0b344c989440200f63b1a39ca650367c93a34f61272af5ed98b63f800c11f; if not appended before the re-run's verdict: <FROZEN | DEFER>>
```

The P3(c) line is item 3's answer: omit it if you defer. X0-A1 is not appended, so no appending commit can be
named tonight; the hash is the [Sat] fact in item 3.

```text
PREREG-SIGN 1
record: docs/m0/prereg/X1-amendment-1.md
freeze: ac751b86f1b37e6cd7e55759e1b770335b57827c
sitting: 2 (2026-10-25)
rule: OPT4_STRICT as written
claude model: claude-opus-5-5; effort: max; runner: accept; plan check: checked-allowed
share s: 50%; cap: 160; feasibility gate: as §6.2, K = 6 weeks
smoke-run deviations approved (batch 5): SMOKE.md §2 (development items only), §1.1 item substitution,
  §4.4 counting rules, run root C:\Users\Pierce Lonergan\x1s\s1; SMOKE.md as at 7be2960
  (SHA-256 bac5ab2e66178334a5b6269809a402d42dea958a3352328f2e4cc0aa2a114db9)
```

The values are the ones you signed in chat (SIGNATURES.md) and approved in batch 5 [M, OWNER-ANSWERS at
`6fe61e6`; SMOKE.md unchanged since `7be2960`, SHA-256 read 2026-10-23]. Change any of them by writing your
value instead.

---

## 2. The 59 rows adopted under your delegation (DELEGATED.md, 10-23)

**Summary.** Batch 4 gave a written delegation. The lead engineer used it on 10-23 to settle 59 open items, each
logged with its options, choice, reason and how to reverse it [M: 59 rows marked "ADOPTED 2026-10-23" in
DELEGATED.md, commit `0ba059e`]. DELEGATED's own rule says every row is reviewed at the next sitting. The test
for adoption: unanswered by you; needed by the work; needs nothing only you can give; loosens nothing (the
registered default or stricter, pre-data, no ROADMAP threshold moved, no FROZEN text changed). Three rows were
**not** adopted because they are yours: P2 (Q18), P3 (Q17), P23 (C07), all in item 4. Two questions about batch 4
are also yours here (OWNER-QUEUE sitting-2 list, item 2): confirm or correct the lead engineer's reading
effort = `max`; and **does batch 4 let the lead engineer settle a D0 line?** ROADMAP §11 says of D0-1 to D0-12:
"No agent may take these decisions." The rows assume not: P4, P7 and P27 adopt operating assumptions only, and
leave those lines for you. Q17, Q18 and C07 stay yours whatever you answer.

**By area** (row numbers in DELEGATED.md; the "Reversible how" column there gives each row's way back):

| Area | Rows | What they settle |
|---|---|---|
| Your D0 lines, as **operating assumptions only** | P4, P7, P27 | Qwen3 checkpoint (D0-10c Value); the post-pilot rate rule's form, 4–7 nights and 25% contingency (D0-10d); no unattended F1-sim (D0-7x). You can tick these lines yourself (item 1) |
| Process and tooling | P1, P5, P6, P13, P15, P18, P19, P20 | freezes between sittings; portable LLVM and C compiler, user-level, on the laptop; queue order (its Q13 line is yours to tick, item 1, optional); Qwen3 work within R2's 5–10 desktop hours until you sign a weekly cap (no D0 line: its line is item 4's optional Qwen3 cap); weekly owner-hour totals; X1 sandboxes on the laptop; job wrapper; the `hearth-c-ref` stand-in from clean `b5d3f14` |
| M0 verdict | P8 | PLAN §3.8 as written, plus one line for a missed X2 gate (P28) |
| X1 | P17, P46–P54 | two planted-corpus halves; hole report; obfuscation scope; `topk`; R-CABW/R-JOINT bind; trigger parameters; SE rule not adopted; 90% two-sided intervals; canary UUID published; T-ROUTE pilot |
| X2 | P9, P10, P14, P28–P34, P62 | MXCSR flags count; second-oracle fallback pre-registered; SDM-only table; gate-miss action; false accepts kill as written; F16/BF16 secondary; mutant and rule counting; a QF_BV proof counts only with an agreeing route; certify under MXCSR = 0x1F80 |
| X3 | P11, P12, P35–P43 | H = 303; x3gen; scalar confirmatory; bands; 1/20 kill level; log(1.03); clang-cl flags; 7-day tuning window; WSL2 Clang bit-identity; α carried; centred clamps |
| X4 | P21, P22, P24–P26, P55 | A/A to N (2N is your option, Deferred); ≤ 2/100 confirmed; e-process across two N-sessions; revision rule; gated run after hash-freeze; quoted IDs |
| Core calculus and `mithi` | P16, P44, P45, P56–P61 | typing-only forms; C-ALLOC; "abandon" renamed; prelude; out-of-scope snippets; counterexamples; policy-trap fallback; `debug_assert!`; certificate obligations |

3 + 8 + 1 + 10 + 11 + 11 + 6 + 9 = 59 [D].

**The eleven rows worth a look** (the adopted option was not the strictest available, no default was
registered, or the row was adopted with data already known):
- **P8** (M0-verdict composition): adopted with X0's census-run-1 previews (ambers (a) and (b)) already known,
  one of two adoptions made with data already present (the other is P11, below, a strict default). Its mapping reads only X0's week-6 narrowing, so the previews
  cannot shape it [inference, DELEGATED P8]. It carries P28's added line (next).
- **P28** (the X2 record has no default here): a missed X2 gate becomes the state `gate_missed`; its variants stay
  `tested`, with no extension; the M0 verdict shows it as a NARROW row (P8's added line). You also sign it in the
  X2-gate and M0-verdict records.
- **P16**: `mithi` type-checks `par for`, `deterministic`, `schedule`, `spec`, `linear` without executing them.
  Keeping `E-X1-NOTYET` makes ROADMAP §3.6's gate unpassable; changing the gate would loosen it (excluded).
- **P30**: F16 and BF16 are secondary for P1 (their mutants still count in P3). Gating them is stricter than
  ROADMAP states.
- **P32**: the loop rules count as 1 rule toward "≤ 30" (registered default); 7 is the strictest reading.
- **P45** (no default registered; the queue's [G] suggestion): the trap-path release is renamed and the 05 §10
  agent verb keeps its name. Naming only.
- **P46**: `mithi`'s hole report reaches all three Mithril arms. It helps those arms, so it leans toward a
  pass; under R4 a pass is provisional anyway.
- **P55** (no default registered; the queue's [G] suggestion): invariant IDs are quoted as strings in the
  trigger grammar, with no grammar change.
- **P56**: a frozen, `mithi`-accepted prelude of declarations may be input to "accepted by `mithi`"; "no" is
  stricter.
- **P57**: the six derived snippets outside X1's scope count as agreement on `E-OUT-OF-SCOPE-<KW>`; having
  `mithi` type them is stricter.
- **P58**: the review's counterexamples N-11 to N-39 stay supplementary, not gate items; "yes" is stricter.

Borderline by the same test, not counted above: **P62** (X2 may certify `b5d3f14` under the stated precondition
MXCSR = 0x1F80 before D0-5b lands; the registered default; "require D0-5b first" is the more restrictive
option, and each certificate claims no more than its precondition) [DELEGATED P62; OWNER-QUEUE D20].

The D0-line rows (P4, P7, P27) are not repeated here: you fill those lines yourself in item 1. P4's checkpoint
had no registered default either; it is the sitting-1 packet's suggested Value, the file you named in R8.

One row cannot be reversed toward looser: **P11** (H = 303). Schedule lines exist since 10-23 09:09 PT [M, file
times], so 369 would now be post-data and favourable.

**Options.** Accept all; accept all except named rows (each named row is reversed and what was built on it
re-examined, DELEGATED "Review"); or narrow the delegation itself for the future. For the D0-line question:
the D0 lines stay yours; or batch 4 also lets the lead engineer settle the D0 lines you name.

**Recommendation.** Accept all 59, and confirm effort = `max`. **Disclosure:** the rows were adopted by the lead
engineer, and this recommendation comes from the same team. The safeguard is each row's four-part test and its
reversal path, not this recommendation. **The D0-line question: no recommendation** (it sets how far the team's
own authority reaches).

**Commit-message lines**, in your words, e.g.: `DELEGATED: the 59 rows adopted on 10-23 (0ba059e) accepted,
except <none | Pnn: reason>. Batch 4 reading confirmed: effort = max.` and one of `D0 lines: stay mine` or
`D0 lines: batch 4 also covers <named lines>`.

---

## 3. X0-A1: which P3(c) reading governs X0's verdict

**Summary.** X0's record (FROZEN `152fa33`, signed) lets a P3(c) accumulator live in "a register, or a
constant-offset, non-escaping stack slot treated as a register". It never defines "non-escaping", and the
script frozen with it counted every constant-offset stack slot without testing escape [M, tooling_fix_A1
README §1]. After census run 1 had been read, the x0fix track wrote **Amendment X0-A1**: an operational
definition (a slot escapes when its address is put in a register and that pointer can reach the loop), applied
to the P3(c) quantity only. On census run 1 it **removes 8 flag records and adds none**: C, `k_avx512` Q8 and
Q4, quant_avx512.c:316 and :352, both builds, each 32 lanes against a bound of 0. It lists 14 records as
`unscreened`, with their frozen counts beside them. Every other P1–P5 value is unchanged [M, README §4.6].
- **Facts on one side:** it removes flags, the direction favourable to Pass; it was defined after census run 1
  and its report, which had already called these flags a probable over-count (REPORT §10); it over-approximates
  escape (a stack pointer in any argument register at any call makes the whole frame escape); rev1 and r2 were
  each reviewed on 10-23 (rev1: two reviewers, 18 findings; r2: one reviewer, 7 findings; all accepted, 3 of
  rev1's in part; the reviewers Claude, same family), but r3, which followed the second review, is not independently reviewed [M,
  AMENDMENT-X0-A1 review log and "Residual"].
- **Facts on the other:** the frozen text itself says "non-escaping", which the frozen script did not test; each
  removed flag sits on an accumulator array whose address is taken and stored to memory (cause (a)) [M, README
  §4.7]; the rev1 script was final before the fix track read run 1's outputs, every r2 change is neutral or moves
  away from Pass, and r3 changes no loop output [M, AMENDMENT-X0-A1 "Order of work"]; and `judge.py` computes the
  whole verdict under both readings
  (`both_ways`), so both are computed (which one it shows first: "Coupled", below).
- **What it changes in the verdict** (preview from census run 1, not a verdict; V3 still fails until the re-run
  and a fresh re-derivation) [D, X0 REPORT §2.3; AMENDMENT-X0-A1 "Verdicts both ways"]: Amber (b) holds under
  either reading, through B-cmake's P3(a1). The reading decides whether C is also listed under Amber (b), and
  whether C's four loops enter the flag-defect report (REPORT §14.3: if real, that would be a compiler report against GCC 13.3, not a Hearth one).
- **Coupled:** what the fresh re-deriver receives (README §6). Under X0-A1 it needs the data-free rule text
  X0-A1.1 to reproduce the governing reading; under FROZEN it gets the freeze text only and reads
  "non-escaping" itself. Either way V3 can disagree on these loops [inference]. The lead engineer sets the brief
  to match your line. Also coupled: the **default display**. Today `judge.py`'s top-level `outcomes` use X0-A1,
  and the frozen reading sits under `both_ways` [M, README §1; its §5: the top-level outcomes "alone do not show
  what it removed"]. Under FROZEN or DEFER, the lead engineer makes the frozen reading the top-level outcome
  (FROZEN) or shows both side by side with neither as the default (DEFER) before the re-run's verdict is
  written; that is a reporting change to `judge.py`, re-pinned and reviewed like any other.
- **Whose call:** DELEGATED's limits exclude a post-data change in the favourable direction, so only you can
  adopt X0-A1 as governing.
- **What can be signed.** X0's tag goes on `152fa33`, which does not contain X0-A1's text. **[Sat, filled
  10-24] X0-A1 is not appended to the X0 record** [M: `docs/m0/prereg/X0-census.md` at `85542cd` does not
  mention X0-A1]. It stands at r3, committed at `bd4f064` ("amendment text ready, not appended" [M, commit
  subject]): the draft text is `experiments/x0-census/results/tooling_fix_A1/AMENDMENT-X0-A1.md` ("Appended by
  the lead engineer on <date>" still blank), with its r2 review logged in its review log, and r3 itself not
  reviewed. Part X0-A1.1, the data-free rule, is the separate file `experiments/x0-census/X0-A1.1-RULE.md`,
  SHA-256 `49e0b344c989440200f63b1a39ca650367c93a34f61272af5ed98b63f800c11f` [M, re-hashed 2026-10-24; the same
  value as quoted in the amendment]. Since no appending commit exists, **item 3 can only be answered FROZEN,
  AMENDED-after-append, or DEFER.** A plain "X0-A1" would still sign a name, not a fixed text; AMENDED-after-append
  binds the rule by its hash instead.

**Options.**
- **FROZEN**: the reading frozen at `152fa33` governs and becomes `judge.py`'s top-level outcome; X0-A1's
  reading is reported beside it.
- **AMENDED-after-append**: you adopt X0-A1's reading now, to govern only once the lead engineer appends the
  amendment to the record with part X0-A1.1 byte-identical to the hash above; the frozen reading is reported
  beside it. If the text changes before it is appended (for example after a review of r3), the hash no longer
  matches and your line does not apply, so the item comes back to you. Your line also says which reading
  applies if the amendment is not appended before the re-run's verdict is written (FROZEN or DEFER).
- **DEFER**: X0's verdict is reported both ways, side by side, and not acted on until you answer. Answering after
  the re-run's verdict is known would mean choosing between two known outcomes.

**Recommendation: none.** The amendment is the team's own post-data change in the favourable direction; a
recommendation from the team is the framing the rules guard against. Answer before the re-run's verdict exists,
so that the choice cannot follow the outcome.

**Line** (X0 tag message, item 1): `P3(c) reading for X0's verdict: FROZEN`, or `…: X0-A1 once appended
unchanged, X0-A1.1 SHA-256 49e0b344c989440200f63b1a39ca650367c93a34f61272af5ed98b63f800c11f; if not appended
before the re-run's verdict: <FROZEN | DEFER>`; omit the line to defer.

---

## 4. The three decisions reserved to you: Q17, C07, Q18

Not delegable: Q18 and Q17 are reserved to you by the FROZEN, signed X1-amendment-1 §5.3 and by the owner log
(a second family "only by a new Owner answer"); C07 amends normative 06 §6.2, which governs every milestone.

### Q17: may the local Qwen3 hold the "different family" roles?

**Summary.** The roles: planted-corpus author (W1–W2), X4's blind batch (b) (W4–W6), X2's Prover (W4–W8), CC's
reviewers (W8–W11). Today they are **UNMET** (the log's default under R2): Qwen3 does only S71 (serving and
tok/s), inside R2's 5–10 daytime desktop hours (P3, P13). Qwen3's tok/s under the 8-thread cap is unmeasured
[DELEGATED P2].

**Options.**
- **QWEN3_LOCAL_PROVISIONAL**: Qwen3 holds the roles. A pass resting only on it stays provisional
  (`pass_local_family`); a kill or a flaw it finds binds. X2's kill clock does not wait for its review; CC's
  X1-subset freeze uses same-family plus local reviews.
- **QWEN3_LOCAL_FULL**: passes count outright. Keeps ROADMAP's letter ("a different family"), weaker in
  substance; only you can choose it.
- **UNMET**: the roles stay open; CC's gate and X4's batch (b) cannot pass at M0.

**Recommendation.** QWEN3_LOCAL_PROVISIONAL [G, D0_BRIEF Q17; P3]. Optional with it: a weekly Qwen3 cap
(B06), and what R2's "daytime only" means (outside a quiet window, or 07:00–23:00 every day). Without a cap,
P13's bound (R2's 5–10 h) stays.

**Lines.** `Q17: QWEN3_LOCAL_PROVISIONAL` (`d0-sign-1`). Commit message, optional: `Qwen3 weekly cap: <…>
h/week; daytime = <outside windows | 07:00-23:00>`.

### C07: 06 §6.2, the gate scorer and the tail check

**Summary.** Two separable points; the numbers are the X4-calibration record's §3a (DRAFT revision 2, `8cd45f6`)
[S, its `c07_branches.py` and the reference's tables; σ_d 2% unless stated]. Its freeze gate requires that you
answer from a packet quoting them (condition 1).
- **(a) The gate scorer.** Under 06 §6.2's literal block clip (L06), a true 20% improvement never reaches e = 20
  within 400 blocks (share 0.000 at σ_d 1%, 2%, 4%), and a 5% improvement needs a median of 155 blocks against 10
  under the run-level **R** scorer. Both scorers keep A/A false alarms far inside ≤ 2/100 (≤ 0.0015 each within
  N = 2n). R spends parity power under outlier runs: the share passing within N at true parity, at outlier-run
  rates 0, 1, 2, 5, 10%, is 0.952, 0.816, 0.658, 0.345, 0.053 under R against 0.950, 0.876, 0.813, 0.576, 0.331
  under L06.
- **(b) The tail check.** The credit a rare-stall candidate earns (15% of runs 30% slow) is 0.127 (R) / 0.144
  (L06) unchecked; 0.078 / 0.096 under 06's literal check (T-06, one-sided 1%); 0.011 / 0.010 under the pooled
  check (T-pooled, one-sided 5%). With 10% of runs 50% slow: T-06 0.221 / 0.213, T-pooled 0.073 / 0.055. Cost at
  parity with no outliers: 0.942–0.980 credited under T-pooled, 0.943–0.968 under T-06, against 0.947–0.980
  uncredited.
- **Direction.** Neither point moves one way only: R makes superiority reachable (a loosening for superiority
  claims) and spends parity power under outliers; L06 keeps superiority nearly unreachable for large true
  effects; T-pooled leaves less rare-stall credit than T-06. No ROADMAP threshold moves in any branch (e ≥ 20;
  ≤ 2/100). The X4-calibration record, and so the first pilot night, waits for this answer.

**Options** (all four combinations are specified in §3a): CONFIRM both = R with T-pooled; confirm (b) only and
keep the literal clip = L06 with T-pooled; keep 06 §6.2 literally = L06 with T-06; or R with T-06. Any branch
other than R with T-pooled needs code before collection (§3a: the Rust L06 scorer's capped-run case, a T-06
counter).

**Recommendation.** CONFIRM both (X4's provisional default; P23).

**Line** (commit message): `C07: (a) gate scorer <R | L06>, (b) tail check <T-pooled one-sided 5% | T-06
one-sided 1%>` (CONFIRM both = R and T-pooled), or your variant.

### Q18: who writes the templates of X1's sealed suite (optional tonight)

**Summary.** Your X1 rule's last sentence ("Sealed items are generated from templates with deterministic
oracles, so no model writes them") can be read as "no model writes an item" or as "no model writes a template".
X1-amendment-1 §5.3 makes the reading and the choice yours. **Nothing can use the answer yet:** a sealed
template needs the smoke-run gate to say RUNNABLE and the Gatekeeper store (A06); a Qwen3 practice set also waits
for RUNNABLE (DELEGATED P2, items 3–4). At the current estimate the gate may say NOT RUNNABLE (item 8), which
would re-plan X1 and change these costs.

**Options** (X1-amendment-1 §5.3, ≤ 1 held-out item per template) [inference and D from G]:
GEN_OWNER, you write them: 84–302 owner h (5.6–20.1 weeks at 15 h/week). GEN_QWEN3: 54–374 daytime desktop h in
all, tok/s unmeasured, extends R2. GEN_CLAUDE: 22–197 M plan tokens, a loosening of 05 §13 only you can grant.
QWEN3_ITEMS, OWNER_ITEMS, OTHER (for example a split author). Your review role C38 belongs to this choice.

**Recommendation.** **Defer** until the smoke-run gate decides; nothing is lost [D, from P2's own conditions].
If you decide tonight, the lead engineer's recommendation is GEN_QWEN3 at ≤ 1 per template with the C38 sample
review. Disclosure: X1-amendment-1's own review withdrew an earlier GEN_QWEN3 recommendation as framing
(DELEGATED, "P2 in full").

**Line** (if decided): `Q18: <choice>` (`d0-sign-1`).

---

## 5. X3/X4 priority class

**Summary.** X3's design runs `x3_bench` at `HIGH_PRIORITY_CLASS` (X3 DESIGN §8.2); X4 measures at
`NORMAL_PRIORITY_CLASS` (MEASUREMENT-SERVICE §7.6 [target]). Under C25 (R8) X4 calibrates on `x3_bench`, so the
two must agree before either record freezes: a calibration covers only the configuration it measured. Both
records are DRAFT, so either answer is pre-data [M, status lines].

**Options.** NORMAL in both (X3 amends its DRAFT §8.2); HIGH in both (a signed change to MEASUREMENT §7.6, the
noise-pilot §3 row and the X4-calibration record before freeze).

**Recommendation.** **NORMAL in both** [G, X4-noise-pilot §3]: X4's integrity checks (the job's priority limit,
the a31 check) are built and tested at NORMAL; HIGH would pre-empt Defender, the indexer and other services on
the run core and hide the interference the load gate is there to see; on a quiet, pinned core with its SMT
sibling idle, HIGH buys little [inference]; σ̂_d is measured at one class, so a later change means a new pilot.

**Why it is on your agenda.** Nothing FROZEN or in the owner log reserves it to you: the only text that does is
the X4-noise-pilot DRAFT §3 ("a recommendation for Pierce, not a decision"), written by an agent. It is here
because the two records register different values, so the delegation's test "the registered default or
stricter" has no single default to apply, and HIGH would need a signed change to MEASUREMENT §7.6 and to the
X4 records before freeze. DELEGATED's scope also lets the lead engineer resolve a contradiction between records:
if he adopts NORMAL as a DELEGATED row before Saturday night, this item moves into item 2's list and leaves the
agenda (saves 2–3 min). **[Sat, filled 10-24] Still here:** DELEGATED.md at `85542cd` has no priority-class
row, and X3 DESIGN §8.2 still says `HIGH_PRIORITY_CLASS` [M]. The X4-calibration record also registers NORMAL
(its §2 and §13, blank = NORMAL), and its freeze-gate condition 6 needs X3 to agree on the run type, priority
class included.

**Line** (commit message): `Priority class: NORMAL in X3 and X4`.

---

## 6. X4 noise pilot: the record, C29, and your pre-night actions

**Summary.** The pilot is four quiet nights that measure the noise every later X4 constant depends on; it judges
no gate. **[Sat, filled 10-24] Not FROZEN** [M]: the record is **DRAFT revision 5** (`185dc3b`, after its third
review round, 13 findings, all accepted; a cross-reference to the new X4-calibration record added at `8cd45f6`);
revision 5 itself is unreviewed. It can freeze only after the **X4-calibration record** is FROZEN. That record now
exists as a DRAFT (revision 2, `8cd45f6`, unreviewed), and its freeze waits on C07 (item 4), on its other owner
fields (C29 below, the priority class of item 5, C05's two parts and the planted horizon, item 6a; each blank
registers the stricter or operative value), on a statistics-reference revision with all four C07 branches (the
reference is still at the revision with one branch, SHA-256 `6ac99140…`), on a logged review, and on agreement
with this record's §3a and §7(b) and with X3 [M, X4-calibration freeze gate and "Where it stands"]. So nothing
can be signed tonight. After signing, the first night still needs your one-time steps (A1–A9 below, in
PRE-NIGHT's order: A1–A5, then the lead engineer's L1, then A6–A9) and the lead engineer's pre-night amendment
(L2: it commits your A7 pins files and A8–A9 outputs, the filled configuration and its hash, K, the goldens,
o_rt), so it falls some days later [M, PRE-NIGHT "Revision 5" and L1–L2].

**C29: what counts toward N** (ROADMAP §1 rule 4's amber limit; the noise-pilot record registers a default for
it). **BLOCKS**: only A/B block time counts, so N holds ≈ 3n blocks. **ALL**: cool-downs and gaps count too (≈ 2n
blocks). X3's gate-level P(Pass) at true parity, σ_d 2%, all 14 configurations together, is 0.995 in the first
N under BLOCKS against 0.535 under ALL, and 1.000 under either after the full inconclusive path [S, X3 DESIGN
§8.8 table "Gate level", §14 Q14: "The choice changes power, not any error rate"]. BLOCKS is the registered
default (X3 DESIGN §14 Q14) and the looser reading, so it cannot register by lapse (OWNER-QUEUE conventions).
BLOCKS also raises X4's calibration hours by ≈ 61 h at σ_d 2% and ≈ 221 h at 4% over ALL [D, X4-calibration
§10.3 item 2; item 6a]. **No recommendation**; answer either, or the records freeze with ALL. Line (commit
message): `C29: <BLOCKS | ALL>`.

**Options for the record.** SIGN tonight is not possible (not FROZEN, above). DEFER to sitting 3 (11-01), which
moves the pilot to W2 or later; or allow yourself a **mid-week signed tag** once it freezes, a one-off exception
to your weekly-batch rule (R3).

**Recommendation.** Allow the mid-week tag [G]; the nights can then start in W1 or early W2. Either way, A1–A5
can be done this week; they need no signature. A6–A9 wait for the lead engineer's L1 (the pinned binaries and the
filled configuration on D:), and A9 runs inside a window (PRE-NIGHT A6–A9).

**Signature** (when you sign): a tag `prereg-sign-x4-noise-pilot` on its freeze commit, with the record's §13
fields in your words (revision 5 lists them all, each with what a blank registers). Among them: the C01
placement (as R8), MITHRIL-MEASURE **active 24/7 or switched nightly**, the **GEMS process image names** the
pilot must treat as excluded, the weeks of the §7(b) rate rule (Plan A, W6, or Plan B, W10; blank = Plan B; see
item 6a), the R1-11 reading (is the pre-START wall ceiling judged or only recorded; registered: judged), a
confirmation that the local Qwen3 server runs as `python`/`pythonw` [inference, PRE-NIGHT §0], and C29 if not
answered above. For the GEMS names: the record already excludes, whatever you write, `claude`, `node`, `python` (outright), the build tools, the local
Qwen3 server, WSL's images and the launchers `OneDrive`, `Overwolf`, `CurseForge`, `EpicGamesLauncher`
[M, X4-noise-pilot §10, "Session hygiene void"]. Seen running on 10-23 [M, PRE-NIGHT B1]: `claude.exe` ×12,
`python` ×16, OneDrive, Overwolf, CurseForge ×7, EpicGamesLauncher, all already on that list. Name only GEMS
images not on it, or write `none beyond the record's list`; agents do not look at GEMS processes.

**Your pre-night actions** (you run these; no agent changes a system or security setting; full text, with what
fails today, in [PRE-NIGHT.md](../../../../experiments/x4-integrity/pilot/PRE-NIGHT.md)):
- **A1, power plan** (elevated PowerShell on the desktop; write down the GUID it prints):
  ```powershell
  powercfg /duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c
  powercfg /changename <NEW-GUID> MITHRIL-MEASURE
  powercfg /setacvalueindex <NEW-GUID> SUB_PROCESSOR CPMINCORES 100
  powercfg /setacvalueindex <NEW-GUID> SUB_PROCESSOR CPMAXCORES 100
  powercfg /qh <NEW-GUID> SUB_PROCESSOR CPMINCORES | Select-String 'Current AC'   # must read 0x00000064
  powercfg /qh <NEW-GUID> SUB_PROCESSOR CPMAXCORES | Select-String 'Current AC'   # must read 0x00000064
  powercfg /qh <NEW-GUID> SUB_SLEEP STANDBYIDLE | Select-String 'Current AC'      # must read 0x00000000
  ```
  Then, by your 24/7-or-nightly choice [PRE-NIGHT A1, B3, Morning]:
  ```powershell
  # 24/7: once
  powercfg /setactive <NEW-GUID>
  # nightly: each pilot night by 22:50 PT
  powercfg /setactive <NEW-GUID>
  # nightly: each morning after 07:00 PT, back to Balanced
  powercfg /setactive 381b4222-f694-41f0-9685-ff5bb260df2e
  ```
- **A2, Windows Update**: Settings > Windows Update > **Pause updates** for the pilot week (recommended: it also
  stops servicing that would discard blocks), or Advanced options > Active hours > Manually, 8:00 PM to 2:00 PM
  desktop (Eastern) time, which blocks only the restart.
- **A3, maintenance**: Control Panel > System and Security > Security and Maintenance > Maintenance > Change
  maintenance settings: e.g. 4:00 PM desktop time, and untick "Allow scheduled maintenance to wake up my
  computer". Today it defaults to 2:00 AM Eastern = 23:00 PT, the window's start [inference, PRE-NIGHT A3].
- **A4, data directory**, and optionally a Defender exclusion (a security trade-off, your call):
  ```powershell
  # not elevated:
  New-Item -ItemType Directory -Force D:\mithril-data\x4\pilot, D:\mithril-data\x4\scratch, D:\mithril-data\x4\pins, D:\mithril-data\x4\bin
  # elevated, optional:
  Add-MpPreference -ExclusionPath 'D:\mithril-data'
  ```
- **A5, C: free space** (advisory): 8.5% free, 158.1 GB [M, 2026-10-23 12:33 PT]; the design asks for about 20%
  [G]. Free some, or accept; say which at signing.
- **A6–A9, once, from your own console session, not elevated, after the lead engineer's L1** (PRE-NIGHT A6–A9).
  **A6, how the driver starts**: in your console session; over SSH it cannot see your input and refuses the night
  [M]. Either by hand, in a PowerShell window at about 22:55 PT (it waits for 23:00 PT; needs no setup), or by a
  scheduled task registered with `-Priority 4`, which no agent has tested and which needs its own once-only
  check through a temporary task (exact commands for both in PRE-NIGHT A6). **A7**, the two pins files, made by
  you in the launch context with the nights' plan active (exact `x4svc fingerprint` commands in PRE-NIGHT A7).
  **A8**, the readability check, once. **A9**, one attended end-to-end run at the pilot placement, once, inside a
  window (23:00–07:00 PT) before the first night, after B1–B2 (not pilot data; a few minutes):
  ```powershell
  # by hand, each pilot night (the canonical hash comes from the lead engineer's L2):
  D:\mithril-data\x4\bin\x4svc.exe pilot-night --config D:\mithril-data\x4\pilot.cfg --pilot --config-sha256 <CANONICAL-HASH>
  # A8, once, before night 1 (not elevated):
  D:\mithril-data\x4\bin\x4svc.exe verify-hygiene --config D:\mithril-data\x4\pilot.cfg --as-pilot > D:\mithril-data\x4\launch-check.txt
  # A9, once, inside a window:
  D:\mithril-data\x4\bin\x4svc.exe dev-run --config D:\mithril-data\x4\pilot.cfg --run-type e2e-decode > D:\mithril-data\x4\e2e-attended.txt
  ```
- **Every pilot night by 22:50 PT** (PRE-NIGHT B): GEMS jobs stopped and the GPU queue paused; launchers closed;
  `wsl --shutdown`; if you chose nightly, `powercfg /setactive <NEW-GUID>` (A1); then leave the machine; **no SSH
  or agent access 23:00–07:00 PT** (a new `sshd`, `sshd-session`, `powershell`, `pwsh` or `cmd` process voids the running
  session).

The open point "does an idle WSL keepalive count as WSL activity?" (OWNER-QUEUE sitting-2 list, item 4) is yours.
The DRAFT record's rule: a WSL process that starts or uses CPU in a window voids the session, and you run
`wsl --shutdown` each night, so no keepalive survives into a window. **You rule on it when you sign the record**
(its rule as written, or your words in the tag). Until then agents apply that stricter rule, and under the lead
engineer's hold of 10-23 they start no WSL at all.

---

## 6a. X4's quiet hours against ROADMAP §10, and D-22 (information; a decision only if you want another course)

**Summary.** The X4-calibration record (DRAFT revision 2, `8cd45f6`, §6.3) re-derives X4's quiet-window hours
with the per-run overhead and the new long-run size [D from G; X4's calibration units only, the noise pilot and
X3 excluded]:

| | σ_d 2% | σ_d 4% |
|---|---|---|
| C29 = ALL (L = 2n) | 154.6 h | 524.8 h |
| C29 = BLOCKS (L = 3n) | 215.6 h | 746.2 h |
| ROADMAP §10's M0 line (X3 and X4 together) | ≈ 60 h | ≈ 215 h |
| Your option: microbenchmark A/A to 2L (C05) | +20.0 h (ALL), +30.0 h (BLOCKS) | +73.3 h (ALL), +110.0 h (BLOCKS) |
| Your option: planted sessions to 2L (X3's carried wealth) | +46.7 h (ALL), +70.0 h (BLOCKS) | +170.0 h (ALL), +256.7 h (BLOCKS) |

X4 alone is 2.4–3.5 times §10's line at σ_d 4% and 2.6–3.6 times at 2% [D]. §10's line is an estimate, not a
threshold: exceeding it loosens nothing, and its revision is yours (C05) [X4-calibration §6.3].

**Why D-22 is likely to fire at σ_d 4%.** D-22 is the second measurement machine; ROADMAP §10: "If a stage's
planned hours exceed its available windows, D-22 fires." The noise pilot's §7(b) turns the pilot's σ̂ into
nights per week, clamped to 4–7; an unclamped value above 7 is recorded as a D-22 trigger fact and X4 "waits"
(amber, ROADMAP §3.7) [M, X4-noise-pilot §7(b)]. A week holds at most 7 nights × 8 usable hours = 56 h (§7(b)'s
caps). At σ_d 4% the calibration alone needs 9.4–13.3 such weeks with no voids, 11.7–16.7 with §7(b)'s 25%
contingency [D]. The first calibration night follows the four pilot nights and the post-pilot amendment (W2 or
W3 [inference]), and the 8–9 weeks from there to the end of W10 (Plan B's horizon) hold at most 448–504 h [D], so
the unclamped rate would exceed 7 under either plan [D]. At σ_d 2% (2.8–3.9 weeks at the cap, 3.5–4.8 with the
contingency) it fits under Plan B, and under Plan A (W6) it comes close to the cap [D]. σ_d is not measured yet:
ROADMAP's 2% and 4% are illustrative, and the pilot measures it. In every case no ROADMAP threshold moves, and
the other M0 verdicts do not wait for X4 (ROADMAP §3.7: "the X4 verdict waits (amber); the other verdicts do not").

**Options** (none needs an answer tonight; a blank keeps the first):
- **Accept a longer X4 timeline** (the registered course): the pilot measures σ_d, §7(b) computes the rate, and
  if it exceeds 7 the D-22 fact is recorded and X4's verdict waits (amber); ROADMAP §10's line stays as written
  (C05 "leave", the X4-calibration record's blank).
- **Plan a second measurement box** (D0-8, OWNER-QUEUE A18; hardware money; ROADMAP's recommendation "The desktop
  first; a second box by D-22", needed by M4). A second machine is a new machine profile, so it would need its
  own noise pilot and calibration before its nights count [inference, X4-calibration §2 pins the desktop's
  profile].
- **Re-scope**: revise ROADMAP §10's M0 line (C05), or change what X4 calibrates at M0. The second is a ROADMAP
  §3.5 amendment; any cut below §3.5's 100 counted sessions per calibration or 20 end-to-end units loosens a
  ROADMAP threshold, which only you can do.

Answers elsewhere that move these hours: C29 (item 6), the two 2L options (Deferred; L registered), and Plan A or
Plan B in the noise pilot's §13 (blank = Plan B).

**Recommendation: none.** The choice is about hardware money and X4's calendar, both yours, and σ_d is unmeasured.

**When.** Tonight, or when you sign the X4 records: the C05 fields and Plan A or B are fixed before any pilot data
[X4-calibration §13; X4-noise-pilot §13]. D0-8 is needed by M4 (ROADMAP §11).

**Line** (commit message, optional): `X4 quiet hours: <registered course | plan a second box (D0-8) | re-scope:
<your words>>; ROADMAP §10 M0 line: <leave | revise: <your words>>`.

---

## 7. WSL trace files on the desktop's C:

**Summary.** Each WSL VM start leaves a trace of 10–105 MB [M, TOOLCHAINS §9 and the sizes below] in
`%LOCALAPPDATA%\Temp\DiagOutputDir\RdClientAutoTrace\` on the desktop's C:, written by WSLg's remote-desktop
client, one per VM start [inference from the file times, TOOLCHAINS §9]. The recorded Mithril traces total
**553,648,128 bytes ≈ 553.6 MB** [D: 320,339,968 on 10-16 (14 files, TOOLCHAINS §9) + 23,592,960 + 104,857,600 +
104,857,600 on 10-23 (tooling_fix_A1 README §7)], over your rule of < 500 MB of new data on C:. At least one more
start (x0prep step 71, 10-16) has no recorded size, so the true total may be higher. None was deleted; the folder
also holds older traces from 10-12, before the Mithril jobs [M, TOOLCHAINS §10]. C: is 91.5% full [M, 10-23]. Since the lead
engineer's hold of 10-23, agents start no WSL at all, so **X0's re-run of configurations C and D (WSL2) waits**,
against the week-3 bound of 2026-11-12, and so does X3's WSL2 Clang bit-identity arm (P41). **[Sat, filled
10-24]** No new trace size is recorded in the repository since 10-23, and no answer of yours on this item is
logged (OWNER-ANSWERS ends at batch 5) [M, `git log` to `85542cd`].

**Options.**
- **(a) Stop the traces at the source** (you, once, on the desktop). Open `notepad "$env:USERPROFILE\.wslconfig"`
  (create it if absent) and add, or extend an existing `[wsl2]` section with:
  ```ini
  [wsl2]
  guiApplications=false
  ```
  Then, at a moment when nothing of yours runs in WSL, `wsl --shutdown`; the next VM start reads the setting.
  `guiApplications` is a documented `.wslconfig` setting that turns WSLg (Linux GUI apps) off [documented,
  Microsoft Learn "Advanced settings configuration in WSL"; not verified on this desktop]. Cost: Linux GUI apps
  stop working in all your distros until you remove the line. Then delete the existing traces (below). The lead
  engineer checks the folder, read-only, after the next permitted WSL start; if a trace still appears, he
  reports it and (c) applies.
- **(b) Move X0's configurations C and D off WSL.** The signed X0 record pins C and D as "WSL2, SysV" on the
  desktop, with hashed compiler binaries (record §2–§3). Every alternative host is costly: a VM on the desktop (a
  system change only you make, and a new host to pin), a rented Linux VM (money; R1 excludes it), or the laptop
  (no WSL there as of 10-16 [M, the lead engineer's machine notes]; enabling it is a system change and moves the
  traces to its C:). Any of them departs
  from a signed record's controls (your signed amendment) and changes V4's pinned inputs, so C and D would no
  longer be a re-run of the same census [inference]. X3's WSL2 arm (P41) would need the same.
- **(c) Accept and delete periodically.** You exempt these traces from the 500 MB rule and delete them yourself,
  for example at each sitting. Agents keep to one VM start per working session (one long keepalive, already the
  practice) and log each new trace's size.

**Recommendation.** **(a)**, then delete the existing traces once. It removes the cause [inference], costs one
edit and one restart of WSL, and leaves the signed X0 hosts unchanged. If you use Linux GUI apps yourself, (c).

**Deleting the traces** (you, on the desktop, normal PowerShell; list first, then delete what you choose):
```powershell
# run after `wsl --shutdown`: a live VM's trace may still be open or being written
$d = "$env:LOCALAPPDATA\Temp\DiagOutputDir\RdClientAutoTrace"
Get-ChildItem $d -Filter 'RdClientAutoTrace-WppAutoTrace-*.etl' | Sort-Object LastWriteTime | Format-Table Name, Length, LastWriteTime
# the Mithril-era ones (from 2026-10-16 on); or all of them, your call:
Get-ChildItem $d -Filter 'RdClientAutoTrace-WppAutoTrace-*.etl' | Where-Object LastWriteTime -ge '2026-10-16' | Remove-Item
```

**Line** (commit message, or tell the lead engineer in chat as soon as it is done, since X0's bound is running):
`WSL traces: <(a) done on <date> | (b) | (c)>; agents may use WSL again in daytime from <date>`.

---

## 8. An idle window for the X1 smoke run

**Summary.** Batch 5 approved the smoke run on the 8 public development items from run root
`C:\Users\Pierce Lonergan\x1s\s1`, and you said you would give an idle window. In it the **whole account stays
quiet**: no Claude use by you, your GEMS session included, and every agent paused. Stage 1 is 5 attempts, up to
about 1 h, then at least 20 min of usage readings [D from G, SMOKE §4.1]. The gate's threshold is w* = 25/288 ≈
0.0868 points of the weekly window per attempt [D, X1-amendment-1 §6.2]. At the current estimate (12.7–54.8
weekly windows for X1's 3,456 attempts, i.e. ≈ 0.37–1.58 points per attempt [D from G, X1-amendment-1 §6.1–§6.2];
effort `max` may move it, which is what the run measures), stage 1 alone would move the reading by about
1.8–7.9 points and end **NOT RUNNABLE** whenever the true cost is ≥ 0.4 points per attempt, i.e. over almost all
of that range; at its low end it may need a second batch [D, X1-amendment-1 §6.2 "Properties"]. A RUNNABLE answer needs at least 25 attempts [D]. A further batch of 20 takes up to about 3 h
plus readings; batches may run in separate idle windows (§6.2 step 5) [SMOKE §4.3]. Constraints [M, SMOKE §4.1]:
no batch may straddle the weekly reset (Fridays 05:00 PT); the plan's pacing rule must allow the start
(weekly ≤ days since reset / 7 × 100 + 15, 5-hour ≤ 80), which the lead engineer reads just before.

**Options.** (i) Sunday right after the sitting, if it ends early enough to finish by about 22:30 PT. (ii) A
weekday block you name, before Fri 10-30 05:00 PT. (iii) Overnight, while you sleep: the run is on the laptop and
never touches the desktop, but R8's text says "with no agents running then" for measurement windows; on a pilot
night that reading is yours.

**Recommendation.** A **2-hour block** for stage 1 this week, outside 23:00–07:00 PT (option (i) or (ii)), so
no reading of R8 is needed. It holds up to about 1 h of attempts, at least 20 min of readings (a 10-min wait,
then readings 10 min apart until two agree, so more if they do not), and the short pre-r0 steps [SMOKE §4.2
step 6, §4.3]: the mandatory probe (its length unmeasured), r0 and the P2 check [inference]. 1.5 h would leave
about 10 min of slack [D from G: 90 − 60 − 20], and an overrun means asking you for the account a second time. If the gate says
CONTINUE, the lead engineer asks you for a 4-hour block per batch (up to about 3 h, plus readings).

**Line** (commit message or chat): `X1 smoke stage 1: <day> <hh:mm>-<hh:mm> PT; account idle, GEMS included`.

---

## 8a. The X1 isolation layer's AppContainer profiles (your OK)

**Summary.** For sealed X1 items the x1iso track built the isolation controls of X1-amendment-1 §2.3 (commit
`7a41873`: the harness tools served over a local MCP server with no shell, a per-`check` sandbox, enforced
budgets), self-tested on the laptop with 58/58 negative tests [M, `experiments/x1-harness/isolation/README.md`].
The smoke run does not use them (development items only, SMOKE.md §3). Each sandbox is an AppContainer, which
launches only with a registered profile (an unregistered SID fails with `ERROR_FILE_NOT_FOUND` [M]). So each
sandbox registers its own profile, a per-user app-package registration in your HKCU hive plus a storage folder
under `%LOCALAPPDATA%\Packages\x1iso.*`, and deletes both inside the call. A killed MCP server cannot delete its
profiles; `winsandbox.stale_profiles()` finds leftovers (prefix `x1iso.`) and `delete_profile()` removes them,
and the runner should run both after each attempt [README gap 3]. The README leaves to you whether you want that
persistence, however brief (gap 3). Laptop only; no installer; the README states that no system or security
setting is changed. **Disclosure:** the 10-23 self-test already registered and deleted such profiles on the
laptop, before your OK: none was left, and the HKCU mapping count was 125 before and after [M, README "Scope and
coexistence"].

**When it is needed.** Before the suite runs again: the README asks for a re-run on any host that will run sealed
items (gap 5), and nothing sealed can run before the smoke-run gate says RUNNABLE and the Gatekeeper store (A06)
exists (item 4, Q18).

**Options.** OK (each sandbox registers and deletes its own profile; the stale-profile sweep runs after every
attempt); OK with a condition you name; NO: the sandbox as built cannot launch [M, gap 3], so sealed items cannot
use this layer until another per-`check` sandbox is designed [inference].

**Recommendation.** OK [G]: the registration is per-user, deleted inside each call and swept after each attempt,
and the sandbox cannot launch without it. Disclosure: the layer and this recommendation come from the same team.

**Line** (commit message): `X1 isolation: per-sandbox AppContainer profiles <OK | OK if <your condition> | NO>`.

---

## Close: one commit, the tags, verify, push (HOW-TO-SIGN steps 3–6)

1. In your own checkout, up to date with `origin/main`: tick `docs/D0_BRIEF.md`; commit it signed with your own
   message file, `git commit -S -F "$HOME\sitting-2-commit.txt"`. That message carries every answer without a
   D0_BRIEF line, for example:
   ```text
   Sitting 2 (2026-10-25). Answers without a D0_BRIEF line:
   R8: C01, C02, C25 as answered on 10-23
   DELEGATED: <item 2 line>
   D0 lines: <stay mine | batch 4 also covers <named lines>>
   C07: <item 4 line>
   C29: <item 6 line>
   Priority class: <item 5 line>
   X4 pilot: settings I apply <A1..A9>; plan <24/7 | nightly>; GEMS images <…>; C: <accept | free>; mid-week tag <yes | no>
   X4 quiet hours: <item 6a line, optional>
   WSL traces: <item 7 line>
   X1 smoke stage 1: <item 8 line>
   X1 isolation: <item 8a line>
   ```
   Before tagging: `git show --stat HEAD` (must list `docs/D0_BRIEF.md` only), then read the full diff
   (`git show HEAD -- docs/D0_BRIEF.md`).
2. `git tag -s d0-sign-1 -F "$HOME\d0-sign-1.txt" HEAD` (first line `D0-SIGN 1`, then `file: docs/D0_BRIEF.md`,
   then one line per item ticked: item 1's table and any optional lines you ticked (Q5, Q13, D0-7x, Q6), plus
   Q17 and Q18 if decided).
3. The record tags on their freeze commits, after the step-5 checks: `prereg-sign-x0-census` on `152fa33…` and
   `prereg-sign-x1-amendment-1` on `ac751b8…`. No other record is FROZEN at `85542cd` (every other file in
   `docs/m0/prereg/` is DRAFT, X2, X4-noise-pilot and X4-calibration included, and no M0-verdict record exists
   [M]), so there is no other record tag tonight.
4. `git verify-tag` on each tag (the authority check: the signer's fingerprint must match your D0-9a Value);
   the Appendix B verifier is advisory.
5. `git push origin main d0-sign-1 prereg-sign-x0-census prereg-sign-x1-amendment-1` (plus any other tag). If
   the push is rejected, merge (`git pull --no-rebase --no-edit`), never rebase.

Afterwards the lead engineer appends a "Signature (tag)" section to each signed record, marks the chat
signatures superseded, records item 2's outcome in DELEGATED.md, and opens the 11-01 list.

---

## Deferred (not tonight)

Each waits safely for a later sitting or has an interim rule [OWNER-QUEUE sitting-2 list; inference].
- **Records** (none is FROZEN at `85542cd` [M, Sat 10-24]): the **X2-fuzz** record (`prereg/X2-checker.md`,
  B02, B03; fuzzing on silicon waits for it) is DRAFT, freeze-ready revision 4 at `cb442e5`; "one thing stands
  between this text and the freeze commit": your **scope reading, its §13 O1** (three readings, ticked in its §14; the
  record proposes the object-level reading but does not adopt it, since it narrows a ROADMAP build line).
  Its other ticks (O4 the carve-out, O9 `gate_missed`) come with its signature. You may answer O1 tonight (not
  timed here) or at sitting 3. The **M0-verdict** record (B01, with P8) does not exist as a file yet; it must be
  SIGNED before X0's re-run verdict, so sitting 3 (11-01) at the latest.
- **With the X4-calibration record:** C05's ROADMAP §10 quiet-hour revision (item 6a) and the microbenchmark A/A
  horizon 2L (P21's "2N"), which adds **+20.0 h at σ_d 2% and +73.3 h at 4% under ALL** (+30.0 h and +110.0 h
  under BLOCKS) [D, X4-calibration §6.3; the earlier +13.3 h / +48.9 h left out the per-run overhead, its §10.3
  item 9]; likewise its planted-horizon option (item 6a). P21 runs A/A to N (the record's L) meanwhile.
- **After the smoke-run gate:** Q18 (if not decided), C38 (your review role), A06 (the Gatekeeper store and a
  desktop account no Claude session can read; nothing can be sealed before it), D08 (the plan's data-use
  setting, before W5).
- **Your hours and the desktop:** A15 (D0-10b's H, if not filled in item 1); A18 (D0-8, and Q7: does GEMS count
  as your own use for D-22; see item 6a for why D-22 may fire).
- **By 11-01 (sitting 3):** C04 ("end of week 6"); C20; C10; C13's line in the X2-gate record.
- **By 11-22 or later:** D02, D11, D13, C30, D06's DECISIONS-wide convention.
- **Later:** D0-9b, D0-7b, D0-7c (D21, D22); Q2 and the other ROADMAP observations (one ROADMAP-amendment
  sitting); tombstone admissions; E01–E09 and F01–F11; filing the two Hearth issue drafts of X0 REPORT §14
  (HM-9); desktop housekeeping (`D:\mithril\x0fixA1\` and other job folders, kept for you or the lead engineer to
  remove).

---

## For the lead engineer (not for the sitting)

**[Sat] facts, filled Sat 10-24** (origin/main `85542cd` [M]): X0-A1 not appended; r3 at `bd4f064`, its r2
review logged, r3 unreviewed; X0-A1.1 SHA-256 `49e0b344…c11f` (item 3, which therefore offers FROZEN,
AMENDED-after-append or DEFER). X4 noise pilot: DRAFT revision 5 at `185dc3b` (cross-reference at `8cd45f6`),
unreviewed, not FROZEN. X4-calibration: DRAFT revision 2 at `8cd45f6`, unreviewed, not FROZEN. X2: DRAFT,
freeze-ready revision 4 at `cb442e5`, waiting on O1 (Deferred). No M0-verdict record exists. Priority class not
adopted as a DELEGATED row (item 5 stays). No new WSL trace size recorded; no answer on item 7 logged.

**Proposed Fri 10-23** (whether it was done is not logged in the repository by `85542cd`): send Pierce item 7
and HOW-TO-SIGN steps 1–2 in chat, so that X0's re-run (bound 2026-11-12) is not held longer and the key is made
before Sunday. At the sitting, item 7 then only records what he did. Before X0's re-run verdict is written, make
`judge.py`'s top-level outcome match his item-3 answer (item 3, "Coupled"); under AMENDED-after-append, append
X0-A1 only with X0-A1.1 byte-identical to the signed hash.

**Inconsistencies found while writing (not this track's files, so not fixed here):**
1. DELEGATED.md's status header (since `e321593`) says the 59 rows are adopted in place, but its adopted-rows
   table is still empty and the paragraph under the header still says "Until then each row is a proposal"; D0_BRIEF
   §0 still says "(none adopted)" [M, at `85542cd`]. Item 2 cites `0ba059e`; OWNER-QUEUE carries a dated status
   pointer.
2. OWNER-ANSWERS dates batch 5 "about 12:30 PT", but the commit that logs it, `6fe61e6`, is dated 11:25:30 PDT
   [M, `git log`]. Check which is right before Pierce re-signs "batch 5 as logged".
3. The X4-noise-pilot record's §3a registers C29's default ("A/B block time only"), which OWNER-QUEUE classes B
   and excludes from default-on-lapse because it loosens; unless Pierce signs C29, the record should freeze with
   the strict alternative (item 6).
4. SMOKE.md's header still asks the lead engineer to log the deviations in DELEGATED.md; batch 5 made them
   Pierce's approval instead, so the log entry should cite batch 5.
5. *(added 10-24)* The microbenchmark A/A 2L cost is still given as +13.3 h / +48.9 h in DELEGATED P21,
   OWNER-QUEUE (sitting-2 list item 4 and the C05 row), PLAN, COST and X4-integrity Q9 [M, `git grep`];
   X4-calibration §6.3 gives +20.0 h / +73.3 h under ALL (+30.0 h / +110.0 h under BLOCKS), and its §10.3 item 9
   asks those records to cite §6.3 before Pierce answers C05. This packet now does.
6. *(added 10-24)* DELEGATED P23 and OWNER-QUEUE's C07 row quote the older C07 figures (0.130 → 0.110 / 0.017);
   X4-calibration §10.3 item 8 and freeze-gate condition 1 ask for §3a's numbers, which item 4 now quotes.

---

## Review log

| Date | Reviewer | Family | Context | Scope | Result |
|---|---|---|---|---|---|
| 2026-10-23 | review 1: one reviewer agent | Claude, same family | independent context | the DRAFT packet against its sources (OWNER-ANSWERS, DELEGATED, OWNER-QUEUE, HOW-TO-SIGN, tooling_fix_A1 README, PRE-NIGHT, SMOKE, X4-noise-pilot) | 11 findings (3 major, 8 minor); all accepted, 3 with a modified fix; details below |
| 2026-10-23 | reviser (sitting2 track) | Claude, same family | independent context from the reviewer | each finding checked against the cited source before the change | packet revised; no record, row or default changed; OWNER-QUEUE status pointer updated |
| 2026-10-24 | finalization (an updater agent for the lead engineer) | Claude, same family | not independently reviewed | [Sat] facts from the sources and `git log` at `85542cd`; items 6a (X4 quiet hours, D-22) and 8a (AppContainer profiles) added; the C05 2L cost corrected; item 4's C07 figures updated to X4-calibration §3a (its freeze-gate condition 1); item 3 restated for a non-appended X0-A1; time recomputed | packet FINAL; no record, row or default changed; no other file edited |
| 2026-10-24 | owner-advocate check (one checker agent) | Claude, same family | independent context | the FINAL packet against its sources (OWNER-ANSWERS, DELEGATED, OWNER-QUEUE, HOW-TO-SIGN, SIGNATURES, tooling_fix_A1 README and AMENDMENT-X0-A1, X0 REPORT, X4-noise-pilot, X4-calibration, PRE-NIGHT, X2, X3 DESIGN, X1-amendment-1, SMOKE, isolation README, TOOLCHAINS, `git log` at `85542cd`); hashes re-computed (X0-A1.1, SMOKE.md) and freeze commits resolved | 8 corrections, made in place: (1) item 6 listed pre-night steps A1–A6; PRE-NIGHT has A1–A9 (A7 pins, A8 readability, A9 an attended run in a window), and A6–A9 come after the lead engineer's L1, so "do A1–A6 this week" became A1–A5; (2) item 6's by-hand launch command lacked `--config-sha256`, A4 lacked the `bin` folder, A1 lacked the standby check; (3) C29's 0.995 / 0.535 were described as one kernel's pass probability; they are X3's gate-level P(Pass) over 14 configurations in the first N, and both readings reach 1.000 after the full path (X3 DESIGN §8.8); (4) item 2 called P8 "the one" post-data adoption; P11 was also adopted with its data present; (5) item 2's X2 row omitted P34; P62 noted as borderline by the flagging test (not counted); (6) item 3's review facts omitted rev1's review; source sections made exact; (7) item 7's per-trace size 23–105 MB became 10–105 MB (TOOLCHAINS §9), and "older traces of your own" lost its unsupported "of your own"; (8) item 8's cost figures now quote X1-amendment-1 (0.37–1.58 points per attempt; 1.8–7.9 points for stage 1). No recommendation, option or time row changed; no other file edited |

**Review 1, finding by finding** (each checked against the source it cites [M]):
1. *(major)* `judge.py`'s top-level `outcomes` use X0-A1 (README §1, §5), so "neither is hidden" overstated
   neutrality. **Accepted:** item 3 now says "both are computed", names the default display as coupled to the
   answer (frozen top-level under FROZEN, side by side under DEFER), and the lead-engineer section carries it.
2. *(major)* The X0 tag would sign the name "X0-A1", not a fixed text (prepared only, at `c069600`). **Accepted:**
   the tag line now names the appending commit and the SHA-256 of X0-A1.1; if not appended with its review
   logged by Sunday, only FROZEN or DEFER can be signed; both values added to the [Sat] list.
3. *(major)* The flagged list was incomplete by its own test. **Accepted, modified:** the count "nine" was
   right if P8 inside the P28 bullet is counted (8 bullets, 9 rows), but P45 and P55 ("no default") and P8's
   adoption with X0's run-1 previews known were missing. Now eleven rows, one bullet each, with a note on the
   D0-line rows (P4 has no registered default either); table row 2 updated.
4. *(minor)* Item 2 recommended accepting the team's own rows without disclosure, and presented "the D0 lines
   stay mine" as a reading although OWNER-QUEUE item 2 asks it open. **Accepted:** disclosure added; the D0-line
   question now has two lines and no recommendation (it sets how far the team's own authority reaches).
5. *(minor)* P13 has no D0 line. **Accepted:** moved to "Process and tooling" (3 + 8; total 59 unchanged [D]).
6. *(minor)* Item 5 did not say why it is Pierce's. **Accepted, modified:** the suggested reason "the class
   becomes part of the hardware fingerprint you sign" is not supported: the fingerprint is pinned mechanically
   in the pre-night amendment, "no new signature" (X4-noise-pilot, Amendments). The packet now states the actual
   reason (only an agent-written DRAFT reserves it; two registered values; HIGH needs a signed change) and the
   alternative (the lead engineer adopts NORMAL as a DELEGATED row and the item leaves the agenda). This track
   adopts no row.
7. *(minor)* Pre-night commands incomplete. **Accepted, modified:** the 24/7 and nightly `powercfg /setactive`
   commands and the nightly step are given exactly; A6 says the task route is untested and needs its own check.
   Not adopted: "by hand is the tested route" (no agent has run the driver in Pierce's console session; over SSH
   it refuses), written as "needs no setup"; and the images seen on 10-23 are all on the record's pinned list
   already, so they are given as context and Pierce names only GEMS images beyond it.
8. *(minor)* C29 and the WSL-keepalive ruling were stated inconsistently. **Accepted:** table row 6, "What waits
   on you" and item 6 now agree (C29 lapses to ALL; the keepalive ruling is made when he signs the record).
9. *(minor)* Item 7 and the key wait for Sunday. **Accepted:** "run after `wsl --shutdown`" added; "Before
   Sunday" names item 7; the lead-engineer section proposes sending item 7 and HOW-TO-SIGN steps 1–2 today.
10. *(minor)* 1.5 h is tight for stage 1. **Accepted:** 2 h, with what it holds; by the same arithmetic the
    per-batch block is now 4 h (was 3.5 h).
11. *(minor)* Close steps 1–2 dropped `git show --stat HEAD` and the optional lines. **Accepted:** both added.

The time estimate was unchanged by review 1 (80–108 min with the key made beforehand) [D, `calc_sitting2.py`
re-run 2026-10-23]. At finalization (10-24) rows 6a (5–8 min) and 8a (2–4 min) were added, and item 6's "+15 to
sign the record" was dropped because the record is not FROZEN: 87–120 min with the key made beforehand, so about
90–120 [D, sum of the rows].
