# Sitting 2: Sunday 2026-10-25, evening

Status: **DRAFT packet** (sitting2 track, a Claude agent, Fri 2026-10-23 PT; reviewed once and revised the same
day, [review log](#review-log) at the end). The lead engineer fills the facts marked **[Sat]** and marks the packet
FINAL on Sat 10-24, night (R6). Sources: your verbatim answers ([OWNER-ANSWERS](../../OWNER-ANSWERS.md),
batches 1–5), [DELEGATED](../../DELEGATED.md), [OWNER-QUEUE](../../OWNER-QUEUE.md) (sitting-2 list),
[HOW-TO-SIGN](../2026-10-18/HOW-TO-SIGN.md),
[SIGNATURES (interim)](../2026-10-23-chat/SIGNATURES.md). Agents never create or see a key, never tick a box or
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
| 3 | X0-A1: which P3(c) reading governs X0's verdict | **No recommendation** (see why); X0-A1 is signable only as appended, by commit and hash | X0 record tag | 5–10 |
| 4 | Q17, C07 (and Q18, optional) | Q17 PROVISIONAL; C07 confirm both; Q18 defer | `d0-sign-1`; commit message | 10–15 (+10–15 for Q18) |
| 5 | X3/X4 priority class | NORMAL in both | commit message | 2–3 |
| 6 | X4 noise pilot: record (if FROZEN), C29, your pre-night settings | Sign if FROZEN, else allow a mid-week tag. C29: **no recommendation** (lapse = ALL) | X4 tag or commit message | 5 (+15 to sign the record) |
| 7 | WSL trace files on the desktop's C: | (a) `guiApplications=false`, then delete (best done before Sunday) | commit message | 5 |
| 8 | An idle window for the X1 smoke run | a 2 h block this week, outside 23:00–07:00 PT | commit message or chat | 3–5 |
| — | Close: commit, tags, verify, push | | | 15–20 |

**Time** [D, sums of the [inference] rows, `scratchpad/sitting2/calc_sitting2.py`]: with the key made
beforehand, Q18 deferred and the X4 record not yet FROZEN, **80–108 minutes**, reading this page included
(10). Key made at the sitting: 95–168. Q18 decided tonight: +10–15. X4 record signed tonight: +15. To stay
near 90 minutes, make the key before Sunday and leave Q18 for the sitting after the smoke-run gate (item 4).

**What waits on you today** (state at origin/main `94adcf3`, 2026-10-23): agents start no WSL until you decide
item 7, so X0's re-run of configurations C and D cannot start, and its week-3 bound is 2026-11-12 [M, X0
`verdict.json`]; the X4 noise pilot cannot freeze before C07 (item 4), and C29 freezes as ALL unless you answer
(item 6); the X1 smoke run waits for your idle window (item 8).

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
P3(c) reading for X0's verdict: <FROZEN | X0-A1 as appended at <commit>, X0-A1.1 SHA-256 <…>>
```

The P3(c) line is item 3's answer: omit it if you defer; the commit and hash come from the [Sat] facts in item 3.

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
| X2 | P9, P10, P14, P28–P34, P62 | MXCSR flags count; second-oracle fallback pre-registered; SDM-only table; gate-miss action; false accepts kill as written; F16/BF16 secondary; mutant and rule counting; certify under MXCSR = 0x1F80 |
| X3 | P11, P12, P35–P43 | H = 303; x3gen; scalar confirmatory; bands; 1/20 kill level; log(1.03); clang-cl flags; 7-day tuning window; WSL2 Clang bit-identity; α carried; centred clamps |
| X4 | P21, P22, P24–P26, P55 | A/A to N (2N is your option, Deferred); ≤ 2/100 confirmed; e-process across two N-sessions; revision rule; gated run after hash-freeze; quoted IDs |
| Core calculus and `mithi` | P16, P44, P45, P56–P61 | typing-only forms; C-ALLOC; "abandon" renamed; prelude; out-of-scope snippets; counterexamples; policy-trap fallback; `debug_assert!`; certificate obligations |

3 + 8 + 1 + 10 + 11 + 11 + 6 + 9 = 59 [D].

**The eleven rows worth a look** (the adopted option was not the strictest available, no default was
registered, or the row was adopted with data already known):
- **P8** (M0-verdict composition): adopted with X0's census-run-1 previews (ambers (a) and (b)) already known,
  the one adoption made in a post-data context. Its mapping reads only X0's week-6 narrowing, so the previews
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
  escape (a stack pointer in any argument register at any call makes the whole frame escape); its r2 revision
  is not yet independently reviewed (a review runs this round) [M, README §1, §5].
- **Facts on the other:** the frozen text itself says "non-escaping", which the frozen script did not test; each
  removed flag sits on an accumulator array whose address is taken and stored to memory (cause (a)) [M, README
  §4.7]; the rev1 script was final before the fix track read run 1's outputs, and every later (r2) change moves
  away from Pass [M, README §1–§2]; and `judge.py` computes the whole verdict under both readings
  (`both_ways`), so both are computed (which one it shows first: "Coupled", below).
- **What it changes in the verdict** (preview from census run 1, not a verdict; V3 still fails until the re-run
  and a fresh re-derivation) [D, X0 REPORT §2]: Amber (b) holds under either reading, through B-cmake's
  P3(a1). The reading decides whether C is also listed under Amber (b), and whether C's four loops enter the
  flag-defect report (REPORT §14: if real, that would be a compiler report against GCC 13.3, not a Hearth one).
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
- **What can be signed.** X0's tag goes on `152fa33`, which does not contain X0-A1's text. X0-A1 is "prepared
  (not yet appended)" at `c069600` [M, its commit subject], the review of its r2 runs this round and is not yet
  logged, and its scripts are still changing [M, uncommitted changes to `judge.py`, `x0_census.py` and
  `compare_x0.py` in the worktree, 10-23 afternoon]. So signing "X0-A1" would sign a name, not a
  fixed text: the line names the commit that appends it and the SHA-256 of part X0-A1.1 (the data-free rule).
  **If X0-A1 is not appended, with its review logged, by Sunday, only FROZEN or DEFER can be signed tonight.**
  [Sat: X0-A1 appended to the record at commit ____ with its r2 review logged, X0-A1.1 SHA-256 ____; or still
  prepared at `c069600`.]

**Options.**
- **FROZEN**: the reading frozen at `152fa33` governs and becomes `judge.py`'s top-level outcome; X0-A1's
  reading is reported beside it.
- **X0-A1** (only as appended, by commit and hash): the amended reading governs; the frozen reading is reported
  beside it.
- **DEFER**: X0's verdict is reported both ways, side by side, and not acted on until you answer. Answering after
  the re-run's verdict is known would mean choosing between two known outcomes.

**Recommendation: none.** The amendment is the team's own post-data change in the favourable direction; a
recommendation from the team is the framing the rules guard against. Answer before the re-run's verdict exists,
so that the choice cannot follow the outcome.

**Line** (X0 tag message, item 1): `P3(c) reading for X0's verdict: FROZEN`, or `…: X0-A1 as appended at
<commit>, X0-A1.1 SHA-256 <…>` (the [Sat] values above); omit the line to defer.

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

**Summary.** Two points, from X4's simulations [S]. (a) Under 06 §6.2's literal block clip, a true 20%
improvement never reaches e = 20 within 400 blocks; X4 proposes the run-level **R** scorer as the single gate
scorer. (b) The mandatory tail check, as written, barely bites: the credit a rare-stall candidate can earn falls
only from 0.130 to 0.110; pooled with screening runs at a one-sided 5% level (stricter than 06's 1%) it falls to
0.017, at a parity cost of ≤ 0.007. (a) makes superiority reachable, a loosening for superiority claims; (b)
tightens. No ROADMAP threshold moves (e ≥ 20; ≤ 2/100). The X4-calibration rules, and so the first pilot night,
wait for this answer.

**Options.** CONFIRM both; confirm (b) only and keep the literal clip; keep 06 §6.2 literally (the calibration
is then re-simulated).

**Recommendation.** CONFIRM both (X4's provisional default; P23).

**Line** (commit message): `C07: confirm both (06 §6.2: run-level R scorer as the single gate scorer; pooled tail
check at one-sided 5%)`, or your variant.

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
agenda (saves 2–3 min). [Sat: adopted as row ____, or still here.]

**Line** (commit message): `Priority class: NORMAL in X3 and X4`.

---

## 6. X4 noise pilot: the record, C29, and your pre-night actions

**Summary.** The pilot is four quiet nights that measure the noise every later X4 constant depends on; it judges
no gate. State on 10-23 [M]: the record is **DRAFT** (revision 4, unreviewed; a review runs this round). It can
freeze only after the **X4-calibration record** is FROZEN, and that record does not yet exist as a file; its
owner inputs are C07 (item 4) and C29 (below). So the record is unlikely to be FROZEN by Sunday [inference].
[Sat: FROZEN at commit ____ with its review logged, or not.] After signing, the first night still needs your
one-time settings (A1–A6 below) and the lead engineer's pre-night amendment (pins made after your A1, K, the
goldens, o_rt), so it falls some days later.

**C29: what counts toward N** (ROADMAP §1 rule 4's amber limit; the noise-pilot record registers a default for
it). **BLOCKS**: only A/B block time counts, so N holds ≈ 3n blocks; P(a truly equal kernel passes within N, σ_d
2%) = 0.995 [S]. **ALL**: cool-downs and gaps count too (≈ 2n blocks): 0.535 [S]. BLOCKS is the registered
default (X3 DESIGN §14 Q14) and the looser reading, so it cannot register by lapse (OWNER-QUEUE conventions).
**No recommendation**; answer either, or the records freeze with ALL. Line (commit message, or the X4 tag):
`C29: <BLOCKS | ALL>`.

**Options for the record.** SIGN tonight (only if FROZEN with a logged review; summary level, +15 min); DEFER to
sitting 3 (11-01), which moves the pilot to W2 or later; or allow yourself a **mid-week signed tag** once it
freezes, a one-off exception to your weekly-batch rule (R3).

**Recommendation.** If FROZEN: SIGN. If not: allow the mid-week tag [G]; the nights can then start in W1 or early
W2. Either way, do A1–A6 this week; they need no signature.

**Signature** (when you sign): a tag `prereg-sign-x4-noise-pilot` on its freeze commit, with the record's §13
fields in your words: the C01 placement (as R8), MITHRIL-MEASURE **active 24/7 or switched nightly**, the **GEMS
process image names** the pilot must treat as excluded, and C29 if not answered above. For the GEMS names: the
record already excludes, whatever you write, `claude`, `node`, `python` (outright), the build tools, the local
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
  New-Item -ItemType Directory -Force D:\mithril-data\x4\pilot, D:\mithril-data\x4\scratch, D:\mithril-data\x4\pins
  # elevated, optional:
  Add-MpPreference -ExclusionPath 'D:\mithril-data'
  ```
- **A5, C: free space** (advisory): 8.5% free, 158.1 GB [M, 2026-10-23 12:33 PT]; the design asks for about 20%
  [G]. Free some, or accept; say which at signing.
- **A6, how the driver starts**: in your console session; over SSH it cannot see your input and refuses the night
  [M]. Either by hand, in a PowerShell window at about 22:55 PT (it waits for 23:00 PT; needs no setup), or by a
  scheduled task registered with `-Priority 4`, which no agent has tested and which needs its own once-only
  check through a temporary task (exact commands for both in PRE-NIGHT A6). **Once before night 1**, the
  readability check from a normal (not elevated) PowerShell in your console session, after the lead engineer has
  placed the pinned binaries and the configuration:
  ```powershell
  # by hand, each pilot night:
  D:\mithril-data\x4\bin\x4svc.exe pilot-night --config D:\mithril-data\x4\pilot.cfg --pilot
  # once, before night 1 (not elevated):
  D:\mithril-data\x4\bin\x4svc.exe verify-hygiene --config D:\mithril-data\x4\pilot.cfg --as-pilot > D:\mithril-data\x4\launch-check.txt
  ```
- **Every pilot night by 22:50 PT** (PRE-NIGHT B): GEMS jobs stopped and the GPU queue paused; launchers closed;
  `wsl --shutdown`; if you chose nightly, `powercfg /setactive <NEW-GUID>` (A1); then leave the machine; **no SSH
  or agent access 23:00–07:00 PT** (a new `sshd`, `powershell`, `pwsh` or `cmd` process voids the running
  session).

The open point "does an idle WSL keepalive count as WSL activity?" (OWNER-QUEUE sitting-2 list, item 4) is yours.
The DRAFT record's rule: a WSL process that starts or uses CPU in a window voids the session, and you run
`wsl --shutdown` each night, so no keepalive survives into a window. **You rule on it when you sign the record**
(its rule as written, or your words in the tag). Until then agents apply that stricter rule, and under the lead
engineer's hold of 10-23 they start no WSL at all.

---

## 7. WSL trace files on the desktop's C:

**Summary.** Each WSL VM start leaves a trace of 23–105 MB [M, sizes below] in
`%LOCALAPPDATA%\Temp\DiagOutputDir\RdClientAutoTrace\` on the desktop's C:, written by WSLg's remote-desktop
client, one per VM start [inference from the file times, TOOLCHAINS §9]. The recorded Mithril traces total
**553,648,128 bytes ≈ 553.6 MB** [D: 320,339,968 on 10-16 (14 files, TOOLCHAINS §9) + 23,592,960 + 104,857,600 +
104,857,600 on 10-23 (tooling_fix_A1 README §7)], over your rule of < 500 MB of new data on C:. At least one more
start (x0prep step 71, 10-16) has no recorded size, so the true total may be higher. None was deleted; the folder
also holds older traces of your own from 10-12 [M, TOOLCHAINS §10]. C: is 91.5% full [M, 10-23]. Since the lead
engineer's hold of 10-23, agents start no WSL at all, so **X0's re-run of configurations C and D (WSL2) waits**,
against the week-3 bound of 2026-11-12, and so does X3's WSL2 Clang bit-identity arm (P41).

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
0.0868 points of the weekly window per attempt [D, X1-amendment-1 §6.2]. At the current estimate (13–55 weekly
windows for X1's 3,456 attempts, i.e. ≈ 0.38–1.59 points per attempt [D from G]; effort `max` may move it, which
is what the run measures), stage 1 alone would read about 2–8 points and end **NOT RUNNABLE** in the middle and
upper part of that range; at its low end it may need a second batch [D]. A RUNNABLE answer needs at least 25 attempts [D]. A further batch of 20 takes up to about 3 h
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
   X4 pilot: settings I apply <A1..A6>; plan <24/7 | nightly>; GEMS images <…>; C: <accept | free>; mid-week tag <yes | no>
   WSL traces: <item 7 line>
   X1 smoke stage 1: <item 8 line>
   ```
   Before tagging: `git show --stat HEAD` (must list `docs/D0_BRIEF.md` only), then read the full diff
   (`git show HEAD -- docs/D0_BRIEF.md`).
2. `git tag -s d0-sign-1 -F "$HOME\d0-sign-1.txt" HEAD` (first line `D0-SIGN 1`, then `file: docs/D0_BRIEF.md`,
   then one line per item ticked: item 1's table and any optional lines you ticked (Q5, Q13, D0-7x, Q6), plus
   Q17 and Q18 if decided).
3. The record tags on their freeze commits, after the step-5 checks: `prereg-sign-x0-census` on `152fa33…`,
   `prereg-sign-x1-amendment-1` on `ac751b8…`, and `prereg-sign-x4-noise-pilot` if signed.
4. `git verify-tag` on each tag (the authority check: the signer's fingerprint must match your D0-9a Value);
   the Appendix B verifier is advisory.
5. `git push origin main d0-sign-1 prereg-sign-x0-census prereg-sign-x1-amendment-1` (plus any other tag). If
   the push is rejected, merge (`git pull --no-rebase --no-edit`), never rebase.

Afterwards the lead engineer appends a "Signature (tag)" section to each signed record, marks the chat
signatures superseded, records item 2's outcome in DELEGATED.md, and opens the 11-01 list.

---

## Deferred (not tonight)

Each waits safely for a later sitting or has an interim rule [OWNER-QUEUE sitting-2 list; inference].
- **Records, if FROZEN by Sunday** (optional, +15 min each at summary level): the **X2-fuzz** record
  (`prereg/X2-checker.md`; fuzzing on silicon waits for it, B02, B03); the **M0-verdict** record (B01, with P8): it must be SIGNED before X0's re-run
  verdict, so sitting 3 (11-01) at the latest.
- **With the X4-calibration record:** C05's ROADMAP §10 quiet-hour revision and the microbenchmark 2N horizon
  (+13.3 h at σ_d = 2%, +48.9 h at 4% [D, X4 Q9]); P21 runs A/A to N meanwhile.
- **After the smoke-run gate:** Q18 (if not decided), C38 (your review role), A06 (the Gatekeeper store and a
  desktop account no Claude session can read; nothing can be sealed before it), D08 (the plan's data-use
  setting, before W5).
- **Your hours and the desktop:** A15 (D0-10b's H, if not filled in item 1); A18 (D0-8, and Q7: does GEMS count
  as your own use for D-22).
- **By 11-01 (sitting 3):** C04 ("end of week 6"); C20; C10; C13's line in the X2-gate record.
- **By 11-22 or later:** D02, D11, D13, C30, D06's DECISIONS-wide convention.
- **Later:** D0-9b, D0-7b, D0-7c (D21, D22); Q2 and the other ROADMAP observations (one ROADMAP-amendment
  sitting); tombstone admissions; E01–E09 and F01–F11; filing the two Hearth issue drafts of X0 REPORT §14
  (HM-9); desktop housekeeping (`D:\mithril\x0fixA1\` and other job folders, kept for you or the lead engineer to
  remove).

---

## For the lead engineer (not for the sitting)

**Fill on Sat 10-24 [Sat]:** X0-A1's state (appended at which commit, with its r2 review logged, and the SHA-256
of part X0-A1.1 as appended; if not appended, item 3's line offers FROZEN or DEFER only); the X4-noise-pilot and
X4-calibration state; whether X2-checker or M0-verdict is FROZEN (then add their tags to the close); whether the
priority class (item 5) was adopted as a DELEGATED row (then move it into item 2's list and drop item 5); any new
WSL trace sizes; whether Pierce has already done item 7.

**Today (Fri 10-23), if you agree:** send Pierce item 7 and HOW-TO-SIGN steps 1–2 in chat, so that X0's re-run
(bound 2026-11-12) is not held two more days and the key is made before Sunday (the sitting is then about 80–108
min instead of 95–168). At the sitting, item 7 then only records what he did. Before X0's re-run verdict is
written, make `judge.py`'s top-level outcome match his item-3 answer (item 3, "Coupled").

**Inconsistencies found while writing (not this track's files, so not fixed here):**
1. DELEGATED.md still says "**None of the rows below is adopted**" above a table whose 59 rows read "ADOPTED
   2026-10-23", and its adopted-rows table is empty; D0_BRIEF §0 ("none adopted") says the same [M]. Item 2
   cites `0ba059e`; OWNER-QUEUE now carries a dated status pointer.
2. OWNER-ANSWERS dates batch 5 "about 12:30 PT", but the commit that logs it, `6fe61e6`, is dated 11:25:30 PDT
   [M, `git log`]. Check which is right before Pierce re-signs "batch 5 as logged".
3. The X4-noise-pilot record's §3a registers C29's default ("A/B block time only"), which OWNER-QUEUE classes B
   and excludes from default-on-lapse because it loosens; unless Pierce signs C29, the record should freeze with
   the strict alternative (item 6).
4. SMOKE.md's header still asks the lead engineer to log the deviations in DELEGATED.md; batch 5 made them
   Pierce's approval instead, so the log entry should cite batch 5.

---

## Review log

| Date | Reviewer | Family | Context | Scope | Result |
|---|---|---|---|---|---|
| 2026-10-23 | review 1: one reviewer agent | Claude, same family | independent context | the DRAFT packet against its sources (OWNER-ANSWERS, DELEGATED, OWNER-QUEUE, HOW-TO-SIGN, tooling_fix_A1 README, PRE-NIGHT, SMOKE, X4-noise-pilot) | 11 findings (3 major, 8 minor); all accepted, 3 with a modified fix; details below |
| 2026-10-23 | reviser (sitting2 track) | Claude, same family | independent context from the reviewer | each finding checked against the cited source before the change | packet revised; no record, row or default changed; OWNER-QUEUE status pointer updated |

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

The time estimate is unchanged (80–108 min with the key made beforehand) [D, `calc_sitting2.py` re-run
2026-10-23]: no item's minutes changed.
