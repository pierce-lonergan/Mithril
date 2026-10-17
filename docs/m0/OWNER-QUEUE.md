# M0 owner queue

Status: living document, created 2026-10-16 by the owner track (a Claude agent) and revised the same
day after one review (same family, independent context; [Review log](#review-log)) to carry Pierce's
second batch of chat answers. It collects every open owner question in the M0 records and designs,
merges duplicates, and ranks them by the date the work they block would stop. It decides nothing.
D0 lines and D0_BRIEF questions are answered by signed tag ([D0_BRIEF](../D0_BRIEF.md), "How to
sign"); a record's own questions are answered in that record before it freezes, and Pierce signs the
frozen text. **This file carries the agenda for sitting 1 (Sun 2026-10-18); its packet is due Sat
2026-10-17, night** ([OWNER-ANSWERS.md](OWNER-ANSWERS.md), "Consequences").

**Sources read for this queue (2026-10-16):** [OWNER-ANSWERS.md](OWNER-ANSWERS.md) (commit `11210a8`,
the verbatim log of Pierce's chat answers); [D0_BRIEF](../D0_BRIEF.md) §0–§7; [PLAN](PLAN.md) §3,
§7, §8, §12, §13; [COST](COST.md) §5; the records [X0](prereg/X0-census.md) (Appendix A),
[X1](prereg/X1-writability.md) (Owner questions and the 2026-10-16 restructure section),
[X2](prereg/X2-checker.md) (pre-freeze questions), [X3](prereg/X3-generator.md) (pointing to its
design §14), [X4](prereg/X4-integrity.md) (owner questions); the designs
[x0 TOOLCHAINS §10](../../experiments/x0-census/TOOLCHAINS.md),
[x1 DESIGN](../../experiments/x1-harness/DESIGN.md),
[x2 TABLE-SCHEMA §13, RULES §7, FUZZ-DESIGN §6.2 and §8, MUTANTS](../../experiments/x2-semantics/),
[x3 DESIGN §14–§15](../../experiments/x3-generator/DESIGN.md),
[x4 DESIGN, MEASUREMENT-SERVICE §7, SANDBOX §3, HACK-SUITE, TOMBSTONES](../../experiments/x4-integrity/);
and [core-calculus.md](core-calculus.md) §16.

**Conventions.**
- Weeks follow PLAN §0 and its operative cadence, **Plan B** (15 owner h/week, verdict ≈ W12). W0 =
  10-16..10-22, W1 = 10-23..10-29, W2 = 10-30..11-05, W3 = 11-06..11-12, W4 = 11-13..11-19, W5 =
  11-20..11-26, W6 = 11-27..12-03, W8 = 12-11..12-17, W10 = 12-25..12-31, W12 = 2027-01-08..01-14.
- **Sittings** are Sunday evenings (R6, pending ratification). Each Friday-to-Thursday week holds one
  Sunday: W0 10-18 (sitting 1), W1 10-25, W2 11-01, W3 11-08, W4 11-15, W5 11-22, W6 11-29, W7 12-06,
  W8 12-13, W9 12-20, W10 12-27, W11 2027-01-03, W12 01-10 [D: `owner/calc2.py`]. A step on a week's
  Friday or Saturday therefore needs the previous week's sitting. Each sitting's packet is due the
  Saturday night before it.
- "Needed by" is the earliest step that stops without an answer. "Latest sitting" is the last sitting
  at which an answer still lands before that step. Where a record has a default, the work does not
  stop: the default becomes the registered choice at freeze, and "Latest sitting" is then the last
  sitting at which an answer can still replace it.
- "Post-data?" says whether answering *after* data exist under the named record would be a post-data
  amendment (ROADMAP §1 rule 1; README lifecycle: verdicts reported both ways, thresholds never move).
  "no" means a governance, schedule or cost choice that no record judges data by.
- "Default" is the source's recommendation or provisional default, cited; where the source gives
  none, the owner track's suggestion is marked [G]. Where the owner track judged that a default would
  decide by framing, the entry gives none.
- IDs here (A01, B03, …) are queue IDs. Source IDs are given in "Where". A bare "Qn" in PLAN means
  PLAN's own question; the brief's are written "D0_BRIEF Qn".
- Owner-minute estimates are [inference].

---

## Answers received 2026-10-16 (chat; ratify at sitting 1)

Source: [OWNER-ANSWERS.md](OWNER-ANSWERS.md), commit `11210a8`, the verbatim, append-only log the lead
engineer keeps. The owner track did not see the chat. Every quotation below is copied from that log,
including the option text Pierce saw, because that text limits what each answer means.

**Status, one wording in every owner-track file.** Decided by Pierce in chat on 2026-10-16. Not yet an
AUTHORITY fact: each answer becomes one when a `d0-sign-<n>` tag ratifies it (A10; D0_BRIEF "How to
sign"). Work proceeds on it provisionally. Agents tick no box and fill no Value field.

**Batch 1** (asked about 11:45 PT):

| ID | Item | Answer (verbatim) | Option text he saw (verbatim) | Reading for the signature line [G] | Settles or makes moot |
|---|---|---|---|---|---|
| R1 | D0-10a | "No metered API" | "Claude Code plan only. X1 cannot meet DR-017's requirement of two or more model families, so X1 cannot pass or kill and stays amber until a second family exists." | AMEND: metered budget $0; Claude work on the Claude Code plan only. The option text's "X1 … stays amber" is superseded by R4 (pending ratification; confirm at sitting 1) | PLAN Q19 and D0_BRIEF Q14 (moot); X1 Q2's dollar part; X0 OQ-6's spend cap ($0 metered) |
| R2 | D0-10c | "Local Qwen3 via Hearth" (the only option selected) | "The pilot the ROADMAP plans: 60 attempts, about 5–10 desktop hours, daytime only, reported but not part of the kill. Uses only the desktop CPU, never the GPU." | AMEND: no Family B; local model = Qwen3 via Hearth as the ROADMAP pilot, outside the kill; checkpoint still open. The question asked also covered authoring and reviews, but the option text he saw describes only the pilot. **Any other role for Qwen3 (template author, A04; Prover, Adversary, planted corpus, reviews, A05) is a new decision, not a reading of this answer** | PLAN Q10 (except the checkpoint and the X1 runner's Claude model); X1 Q1 (families); X1 Q3 (no Family B); D0_BRIEF Q15 (moot unless D0_BRIEF Q16 = OPT1) |
| R3 | D0-12, D0-12x, D0-12i | "Batch weekly review" | "You sign all records ready that week in one sitting. Collection under any record waits for that sitting, except X0, which you already authorised." | D0-12 YES (weekly); D0-12x X0; D0-12i CONFIRMED | PLAN Q21; D0_BRIEF Q4 (as OTHER: ROADMAP gains the X0 exception, m0/README narrows to X0); X0 OQ-6's instruction part |

**Batch 2** (asked about 14:30 PT):

| ID | Item | Answer (verbatim) | Option text he saw (verbatim) | Reading for the signature line [G] | Settles or makes moot |
|---|---|---|---|---|---|
| R4 | X1 rule (amends DR-017's family requirement for X1) | "Claude kills; pass provisional (Recommended)" | "Claude alone can fire the kill (VP@1 gap >15, or CABW >5 worse than Rust). A pass is only provisional until a second frontier family confirms it at M1. Claude also edits the card, which biases toward passing, so a kill is the more trustworthy signal. Sealed items are generated from templates with deterministic oracles, so no model writes them." | D0_BRIEF Q16 = OPT4_STRICT, carried by **a signed amendment record** (to be drafted; signed at the first sitting whose packet holds it FROZEN). The amendment should use his wording "confirms it at M1"; the X1 record's option 4b runs the confirmation before M1's DR-017 gate, which agrees. His option text's last sentence bears on who writes the templates (A04) | A03 (answered); X1 Q6 (moot); D0_BRIEF Q5 (the pilot reading stands; the kill part is amended by R4); R1's "stays amber" |
| R5 | D0-10d | "4 pilot nights, then a rule (Recommended)" | "23:00–07:00 PT, starting in week 1. The first 4 nights measure the noise (σ_d). A pre-registered rule then sets 4–7 nights per week, and you re-sign it. You keep GEMS jobs out of those hours." | D0-10d Value: pilot-week nights = 4; window = 23:00–07:00 PT; first night = in week 1 (in PLAN's numbering W1 = 10-23..10-29; the log's "10-18 at the earliest" is the signing constraint, so the exact night is his to fill, A17), and no earlier than the X4-noise-pilot record's signature; co-tenants = GEMS kept out by Pierce; rate after the pilot = a pre-registered rule giving 4–7 nights a week, re-signed. Under this answer PLAN §6.3's rule gains a floor of 4 | A17 (reduced to its residual); PLAN Q1's night part; the ask behind tombstone `m0_fixed_four_night_ask`. **Not settled:** D0-7a (A19), D0-8 and D0_BRIEF Q7 (A18), PLAN Q2 (C01) |
| R6 | D0-12, cadence | "Sunday evening (Recommended)" | "First sitting Sun 2026-10-18. I send the agenda and a signing-ready packet Saturday night." | D0-10b's "signing slots" Value = Sunday evening. D0-10b's H (hours a week) stays open (A15) | A02's slot part; PLAN Q6's "in which weekly slots"; PLAN S09 |

**Earlier instructions in the same log** (not D0 answers):
- I1. "Start the parts that need no owner decision: X0 instruction census..." This is the instruction
  D0-12i asks Pierce to confirm (R3).
- I2. "Authorisation to commit and push Mithril work to origin main, in small path-limited commits"
  (the log's paraphrase). It bears on A02.
- I3. "please do this on ultra code mode and you have permission to do whatever you need to do to
  fulfil this project in its entirety". The lead engineer reads it as operational permission
  (installs, desktop builds, commits, agent orchestration), not as delegating D0 decisions or gate
  signatures (ROADMAP §11). It bears on A07.

**Everything else in D0 is open**, including D0-9a, D0-10b's H, D0-7a, D0-8 and every D0_BRIEF
question except Q16 (answered, R4) and Q4, Q14 and Q15 (answered or moot as above).

---

## Next 3 asks

The three answers that unblock the most work soonest, given R1–R6.

1. **Sitting 1 (Sun 10-18): the signing key (A01), then ratify R1–R6.** Without D0-9a no tag can be
   made: R1–R6 stay unratified, nothing can be SIGNED, and every collection except X0's waits. The X1
   amendment record (R4) is signed at the first sitting whose packet holds it FROZEN.
   ≈ 40–95 min [inference], plus key setup (0.25–1 h [G], D0_BRIEF §4.13).
2. **X1's template author (A04 = D0_BRIEF Q18), with the plan check (A20) and the store account
   (A06); and the Qwen3 roles (A05 = D0_BRIEF Q17).** The X1 rule he chose says "no model writes"
   the sealed items. Items are generated, but someone writes the templates, and the template carries
   the authorship (X1 record, option 2). No sealed template can be written until A04 and A06 are
   answered, and the X1 rule itself rests on the plan check (A20). Q17 also releases the planted
   corpus, X4's batch (b), X2's Prover and CC's reviewers. No default is given for A04 (see its
   entry). ≈ 40–80 min to decide [inference], plus 0.5–1 h for the terms check [G] and 1–3 h of
   account setup [inference, D0_BRIEF D0-9b].
3. **The first pilot nights in W1 (R5): the X4-noise-pilot record SIGNED, with the X4-calibration
   rules FROZEN; D0-7a (A19); the machine settings (B10); the rate rule's form and contingency
   (A17).** The log puts the first pilot night after the X4-noise-pilot record is signed. If that
   record is not in Saturday's packet, the nights cannot start before the 10-25 sitting; signed on
   10-25, the 4 pilot nights still fit in W1 (the nights of 10-25 to 10-28), provided the measurement
   service v0 has passed its acceptance check and the settings are applied. Signed on 11-01, the
   pilot moves to W2. ≈ 20–40 min to decide plus 1–2 h to review the record [inference], plus 1–2 h
   of settings [inference, D0_BRIEF D0-10d].

**Already moving, to confirm:** PLAN Q4 (A07). A Rust toolchain was installed during the build round
by another track: the working tree's `rust-toolchain.toml` records rustc 1.99.1 installed 2026-10-16
by rustup, and `crates/mithi` exists [M, owner track, read 2026-10-16]. The lead engineer reads I3 as
covering installs. The owner track did not check where it was installed or how.

**Time-critical but not blocking:** X0's OQ-1 to OQ-5 and OQ-7 (A08–A13) and the config-C hardening
choice (A14). X0 may collect as soon as its record is FROZEN (R3). The record's strict defaults then
apply; an answer that loosens a gate after X0 data exist is a post-data amendment, and OQ-1 would
also need a ROADMAP amendment.

---

## Sitting 1 (Sun 2026-10-18, evening): agenda

**Ready to sign.** No pre-registration record is FROZEN as of 2026-10-16 15:23 PT [M, owner track:
every record's status line reads DRAFT; X0's Appendix D freeze checklist is empty]. Rows marked
**if FROZEN** are signed only if the record's freeze commit is in Saturday's packet; otherwise they
move to the 10-25 sitting, with the consequence given.

| # | Item | What Pierce does | Est. minutes [inference] |
|---|---|---|---|
| 1 | D0-9a (A01), D0_BRIEF Q2 | Choose HW, PASS or SOFT; create the key if needed; fill in the fingerprint Value. Answer Q2 (should ROADMAP name an interim signing method) | 20–60 |
| 2 | Ratify R1–R6 | Tick D0-12 YES, D0-12x X0, D0-12i CONFIRMED; D0-10a AMEND with its required Value (for example T1 cap = $0); D0-10c AMEND with Family B = none and the Qwen3 checkpoint; D0-10d with its Value line from R5; D0-10b's "signing slots" = Sunday evening (its H is row 6); D0_BRIEF Q16 = OPT4_STRICT; Q4, Q5, Q14 and Q15 as he sees fit. Confirm that R4 supersedes R1's "X1 stays amber" | 20–35 |
| 3a | **If FROZEN:** the X1 amendment record (R4) | Review and sign. If it is not in the packet: sign at 10-25; X1's freeze (≈ W5) is the real deadline, so nothing slips | 30–60 |
| 3b | **If FROZEN:** the X4-noise-pilot record, with the X4-calibration rules frozen | Review and sign. **If it is not in the packet, "nights from week 1" cannot start before the 10-25 sitting** (the nights of 10-25 to 10-28 are still in W1) | 60–120 |
| 3c | **If FROZEN:** the M0-verdict record (B01) | Review and sign. It must be SIGNED before X0's verdict (≈ W1); if it is not signed by 10-25, X0's verdict waits for 11-01 | 60–120 |
| 3d | **If FROZEN:** X0 | Review and sign; the Gatekeeper's X0 verdict needs it | 60–120 [D0_BRIEF: 1–2 h per record] |
| 4 | X1 and the other-family roles: D0_BRIEF Q18 (A04), A20, A06, D0_BRIEF Q17 (A05), D07 | Read the X1 record's section "X1 under the 2026-10-16 owner constraints" (≈ 6 pages); choose the template author, confirm the plan check, the store account and the Qwen3 roles; accept or reject the Claude Code runner | 40–80 |
| 5 | Nights: A17's residual, D0-7a (A19), D0-8 and D0_BRIEF Q7 (A18), D0-7x with D0_BRIEF Q6 (C12), settings (B10), PLAN Q2 (C01), PLAN Q3 (C02) | The rate rule's form and its contingency (PLAN Q12); unattended measurement; GEMS and D-22; daytime F1-sim; which settings he applies; the thread cap inside windows; the model file | 20–40 |
| 6 | D0-10b's H (A15), D0_BRIEF Q13 (A16), A02's residual, A07's residual, PLAN Q4, Q5, Q17, Q13 (B08) | Hours a week and holidays; queue order; freeze commits between sittings; toolchain confirmation; reference binary; hour logging. Plain answers; no tag needed for PLAN questions, but recording them in the tag message keeps one place of record [G] | 15–30 |
| 7 | X0's questions (A08–A14) | Answer OQ-1 to OQ-5, OQ-7 and the config-C choice, or "deferred" (signature block) | 15–30 |
| 8 | If time remains: cheap deferrals | D0-10e DEFER, D0-6a/b/c DEFER, D0-4 STATUSQUO, HM-2/3/4 DEFER (F07–F10) | 5–10 |
| — | Close | One commit with the ticks; one signed tag `d0-sign-1` listing every decided line (Appendix B grammar); run the Appendix B verifier | 10–15 |

**Total (the one sitting-1 estimate; D0_BRIEF §2 cites it):** ≈ 145–300 minutes (≈ 2.4–5.0 h)
without any record signature; each FROZEN record adds 0.5–2 h, so ≈ 5.9–12.0 h with all four [D:
`owner/calc2.py`, sum of the rows; inputs inference]. That is too long for one evening. **Shortest
useful sitting:** rows 1, 2 and 4 and the close, ≈ 90–190 min. Then 3b, if FROZEN, because it decides
whether the pilot nights start on 10-23 or 10-25. Everything else can move to 10-25 without moving a
step this week, except the X0 OQs if X0 freezes before 10-25 (its strict defaults then register).

**The 10-25 sitting (W1)** is already heavy [G]: whatever of 3a–3d slipped, the X2-fuzz record (B02,
B03; frozen by the Sat 10-24 packet, with the census hash or with the B_iform scope plus the census
amendment rule of PLAN §3.3), and the X4-calibration questions (C05–C10, C24, C25, C29), which freeze
with the rules before the first pilot night.

---

## The queue, ranked by the date the work blocks

### Tier A: blocks now, or at sitting 1 (W0–W1)

| ID | Question | Options and consequences | Default | Where | Needed by | Latest sitting | Post-data? |
|---|---|---|---|---|---|---|---|
| A01 | How does Pierce sign in M0, and with which key? | **HW**: hardware key with a touch; strongest; may mean buying a token. **PASS**: passphrase key outside the agents' account or without caching; usable now; re-sign later with HW. **SOFT**: key in the account agents run under; no stronger than a typed name (tombstone `software_key_on_agent_account`). **NO**: nothing can be SIGNED; R1–R6 stay unratified | HW; PASS if no token is at hand (D0_BRIEF §4.3) | D0-9a; D0_BRIEF Q2 (interim method in ROADMAP: YES [G]); PLAN Q6 (form) | sitting 1 | 10-18 | no |
| A02 | May a named session commit freezes between sittings? *The slot is answered (R6: Sunday evenings).* I2 already authorises the lead engineer "to commit and push Mithril work to origin main, in small path-limited commits". Residual: does that extend to **freeze commits of pre-registration records**, or are those reserved for the sitting? | **(b) yes**: freezes land between sittings; only signatures wait for Sunday. **(a) no**: everything waits for the sitting, so a record ready just after one waits ≈ 7 days (R26) | (b) [G] | D0-10b Value ("signing slots", answered by R6); PLAN Q6 (commits); PLAN R26; OWNER-ANSWERS I2 | sitting 1 (X0's freeze is the first) | 10-18 | no |
| A03 | Who carries X1's kill under R1 and R2? | **Answered in chat: R4** ("Claude kills; pass provisional") = D0_BRIEF Q16 OPT4_STRICT, to be ratified by tick and carried by a signed amendment record. Kept here so that the ID still resolves | — | D0_BRIEF Q16 (merges Q5); X1 Q6 (moot) | ratification at sitting 1; the amendment before X1's freeze (≈ W5) | 10-18 (tick); amendment by 11-22 | yes: before freeze; no X1 data exist |
| A04 | Who writes the templates of X1's generated suite (and so, in substance, its sealed items)? Preface for Pierce: *the X1 rule you chose (R4) says no model writes the sealed items. Items are generated, but someone writes the templates, and the template carries the authorship and the item-level variance (X1 record, option 2). Choose the template author.* | **GEN_OWNER**: Pierce writes the templates; the reading that matches "no model writes them". Owner hours ≈ 64–306 at ≤ 1 held-out item per template (the record's §4.3, as designed), or ≈ 36–141 at 2–3 per template [D from G]; at 15 h/week X1's verdict moves to ≈ W15–W32 or ≈ W13–W21 [G]. **GEN_QWEN3**: the local Qwen3 writes the templates. *A model family (Qwen3) authors the templates; this departs from the summary you accepted, and extends R2 beyond the pilot.* Daytime desktop hours ≈ 44–378 or ≈ 30–190 for X1's Qwen3 work in all [D from G]; owner +1–5 h; X1 ≈ W11–W12 if the plan's windows suffice. **QWEN3_ITEMS**: Qwen3 writes whole items; contradicts "no model writes them"; ≈ 50–312 desktop h. **OWNER_ITEMS**: ≈ 228–456 owner h; not feasible at 15 h/week. **GEN_CLAUDE**: Claude writes the templates; ≈ 9–200 M plan tokens [D from G]. *Loosens 05 §13's author guard (the card editor becomes the author: a Goodhart risk toward passing, on top of the card bias R4's option text names). Not recommended; only Pierce can grant it.* The second figure of each pair needs a template-clustered analysis and an F = 1 simulation not yet run, and a change to the record's §4.3 that Pierce would sign | **none** (the owner track gives no default: GEN_QWEN3, its earlier default, departs from the text Pierce chose) | D0_BRIEF Q18 (merges X1 Q3 and X1 Q10's template count) | sitting 1: no sealed template is written until it is answered | 10-18 | yes (before sealing) |
| A05 | May the local Qwen3 count as "another family" for the non-participant roles (X2 Prover, X4 Adversary, CC Prover and Adversary, X1 planted corpus, item reviews, semantic guard, kit acceptance corpus, R-diff reviews)? *R2's option text described only the pilot, so this is a new decision.* | **QWEN3_LOCAL_PROVISIONAL**: Qwen3 holds the roles, logged "different family (local, non-frontier)"; **every gate pass whose different-family requirement is met only by Qwen3** (X4 batch (b), X2 Prover, CC Prover and Adversary, the X1 precondition's planted corpus) **is recorded as provisional** (`pass_local_family`), handled in the M0 verdict like `pass_one_family`, until a frontier family repeats the role; a kill or a failed review stays binding. **QWEN3_LOCAL_FULL**: such passes count outright. It keeps ROADMAP's letter ("a different family"; §3.3, §3.5, §3.6 do not say frontier) but is a weaker test in substance: a weaker Adversary writes hacks that are easier to catch, a weaker Prover misses more [inference]. Not recommended; only Pierce can choose it. **UNMET**: the roles stay open (the log's own default under R2); CC's gate and X4's batch (b) cannot pass at M0; X2's verdict carries the same-family label; X1's planted corpus needs Pierce or A04's author. Qwen3 hours for the Prover, Adversary and R-local review roles ≈ 2–38 daytime h in all [D from G: per role in COST §1.6], or a weekly cap Pierce signs (B06). Also X2 Q6: does X2's kill clock wait for that review? | QWEN3_LOCAL_PROVISIONAL [G]; the clock does not wait, the verdict carries the review's label [G] (waiting could delay a kill) | D0_BRIEF Q17; X2 Q6; CC Q6 (freeze the X1 subset on same-family review: under either QWEN3 option, on R-same plus R-local); X1 Q3 (family C) | sitting 1 (planted corpus W1–W2; X4 batch (b) W4–W6; X2 Prover W4–W8; CC W8–W11) | 10-18 for the planted corpus; 11-15 for batch (b) | X2 Q6's clock: yes (X2-gate rules, W2); otherwise no |
| A06 | Where do sealed items live, who holds the key, and is there a desktop account no Claude session can read? | **(a)** a separate local account on the desktop (D0-9b's gate account), store on D: under it: Qwen3 authoring can run there; Pierce's admin setup 1–3 h [inference]. **(b)** another machine with no Claude sessions: Qwen3 output has to be moved. **(c)** Claude settings deny rules only: weak, because agents reach the desktop over SSH as Pierce [inference]. Also: is the Mithril repository public? | (a) [G, from X1 DESIGN §4.2 and §4.6 and D0_BRIEF D0-9b]; store outside every repository and cloud-synced folder, encrypted, key held by Pierce or the Gatekeeper account (PLAN §3.2) | PLAN Q5; X1 Q11 (firewall part); X1 DESIGN §4.6; D0-9b (gate account); X2 mutant pool | before any sealed content exists: the first template (W1 if A04 is answered at sitting 1); X2's mutant pool W6 | 10-18 | no, but nothing may be sealed before it |
| A07 | Confirm the Rust install already made (where, and with PATH unchanged?), and may a portable LLVM and a C compiler follow on the laptop? | **Yes**: user-level, archives verified, no PATH or system change (rustup can install without editing PATH [not verified here]). **No**: build in WSL on the desktop under `/mnt/d` inside the 8-thread cap; slower, and it competes with X0 and X2. Desktop installs go to D: in either case (sprint rule). *Status:* rustc 1.99.1 was installed by rustup on 2026-10-16 and `crates/mithi` exists [M, `rust-toolchain.toml` read by the owner track]; where and how was not checked here. The lead engineer reads I3 as covering installs, so only the confirmation and the residual are asked | yes (PLAN Q4) | PLAN Q4; OWNER-ANSWERS I3; status S22, S23; R23 | now (confirm) | 10-18 | no |
| A08 | X0 OQ-1: does ROADMAP §3.1's "mnemonic" mean XED iclass or a grouped operation class? | **ICLASS** (record): amber (a) plausible through P5 (expectation E3). **OP_CLASS**: fewer units, so amber fires less; needs a ROADMAP §3.1 amendment before signing | ICLASS (strict) | X0 Appendix A; tombstone `x0_p5_opclass_gate` | before X0's first compile | 10-18 (if X0 freezes later, the sitting before its freeze) | yes |
| A09 | X0 OQ-2: is amber (a)'s "union" every reachable instruction, or a like-for-like SIMD comparison? | **Full union** (record): amber plausible on GPR, memory and hardening forms (E4). **Like-for-like**: looser | full union | X0 Appendix A | before X0's first compile | as A08 | yes |
| A10 | X0 OQ-3: accept that X0 screens for reassociation rather than proving its absence? | **Accept** for M0, with the open item routed to the B1.5 object audit. **Route the clause to B1.5** by a ROADMAP amendment | accept, with OQ-3 carried to B1.5 (record §8, Pass row) | X0 Appendix A | before X0's first compile | as A08 | yes |
| A11 | X0 OQ-4: is amber (b) the right reading of the contraction clause; do non-release configurations (B-cmake, C) count; are clang-cl defects "unsupported"? And config B as configured (no VNNI on `/arch:AVX512`; `-ffp-contract=on`) or patched? | **Strict** (record): amber (b) counts every main-union configuration; B-cmake as configured, so its AVX-512 file is expected not to build (row N2) and B is expected to trip amber (b) (E1, E2). **Release-only**: looser; tombstone `x0_amber_b_release_only` | strict; B as configured | X0 Appendix A; TOOLCHAINS §10 items 1–2 | before X0's first compile | as A08 | yes |
| A12 | X0 OQ-5: if the recomputed \|B_iform\| exceeds 105, may T_forms use it? | **No** (record): T_forms = min(\|B_iform\|, 105). **Yes**: a larger threshold, which is looser | no | X0 Appendix A, signature block | before X0's first compile | as A08 | yes |
| A13 | X0 OQ-7: accept the tooling track's statement that no Hearth object was compiled and examined before freeze? | **Accept**: TOOLCHAINS.md says no census data was collected and no Hearth source compiled [M, read 2026-10-16]; it becomes freeze-checklist item D12. **Ask for more**: the freeze waits | accept | X0 Appendix A, D12 | X0's freeze commit | as A08 | n/a (pre-freeze fact) |
| A14 | Config C (Ubuntu GCC): record the distribution's hidden hardening flags (CET `endbr64`, stack protector) or neutralise them? | **Record as built** with Hearth's own flags; the record already expects the hardening code (E5). **Neutralise** (`-fcf-protection=none` and the like): no longer Hearth's build as shipped | record as built [G, consistent with record E5] | TOOLCHAINS §10 item 3 | X0's freeze | as A08 | yes |
| A15 | How many owner hours a week, and which weeks are off? | 33 → Plan A, verdict W6; 20 → ≈ 10 weeks; **15 → Plan B**, ≈ 13 weeks; 10 → ≈ 20 weeks [D, D0_BRIEF]. Holidays 11-26, 12-25 week, 01-01 stretch Plan B further. GEN_OWNER (A04) adds its hours on top | a figure he can sustain; Plan B operative meanwhile | D0-10b (H); PLAN Q11 | sitting 1 | 10-18 | no |
| A16 | Which governs the review queue: evidence grade or unblock-first? | **UNBLOCK_FIRST** (PLAN §7.2): signatures that unblock nights or another family first. **EVIDENCE_GRADE** (ARCHITECTURE §16 risk 6) | UNBLOCK_FIRST [G]; this queue is ordered that way | D0_BRIEF Q13 | sitting 1 | 10-18 | no |
| A17 | Quiet windows: the residual of D0-10d after R5 | *Answered in chat (R5):* 4 pilot nights, 23:00–07:00 PT, from week 1, GEMS kept out by Pierce, then a pre-registered rule giving 4–7 nights a week, re-signed. **Residual Value fields:** (i) the rule: PLAN §6.3's rule with R5's floor of 4 and cap of 7, or another; (ii) its contingency: **25%** (PLAN Q12) or another; (iii) the exact first night. The rule should be signed before the pilot's σ_d is known | PLAN §6.3's rule with a 4–7 bound, 25% contingency (PLAN Q12) | D0-10d; PLAN Q1, Q12; tombstones `m0_fixed_four_night_ask`, `quiet_window_cotenancy` | before the first pilot night (W1) | 10-18 for a first night on 10-23 or 10-24; 10-25 for one from 10-25 | partly: the rate rule before the pilot's σ_d is known |
| A18 | Is the desktop the measurement host, and does GEMS count as "the Owner's own use" for D-22? | D0-8 **YES**: desktop now, second box by D-22. Q7 **YES**: if GEMS cannot pause inside windows, D-22 fires at once; **NO**: GEMS is a co-tenant to be scheduled around. R5 says Pierce keeps GEMS jobs out of the window hours, which answers the scheduling but not Q7 | YES, YES (D0_BRIEF §4.10, Q7) | D0-8; D0_BRIEF Q7 | before the first pilot night (W1 under R5); ROADMAP: D0-8 by M4 | as A17 | no |
| A19 | May measurement run unattended inside quiet windows? | **YES** (ROADMAP §11's wording). **NO**: attended only; someone present for 60–215 quiet hours, and X4's verdict slips. R5's night window implies unattended runs but does not answer D0-7a | YES | D0-7a; PLAN Q1 (unattended part) | before the first pilot night (W1 under R5) | as A17 | no |
| A20 | **New.** The X1 rule (R4) rests on Claude attempts through the Claude Code plan. Confirm (i) that your plan's terms allow scripted, headless X1 attempts at ≈ 2,856–3,816 attempts (n = 96 to the cap n = 160 [D]), ≈ 0.73–3.51 billion tokens [D from G]; and (ii) that you accept X1 taking a large, so far unmeasured share of the plan's account-wide 5-hour and weekly windows for about six weeks, so that the agent team and your other Claude use slow down [inference; COST §2: the windows are account-wide] | **YES to both**: R4 runs as planned; the X1 smoke run (PLAN S70) then measures the window share per attempt. **NO to either**: R4 cannot run as planned and needs a new answer before X1 freezes | **Pierce checks the terms himself**; agents do not interpret them | X1 record, "Facts common to every option"; PLAN R17, R29; D0_BRIEF §8 | before ratifying R4 | 10-18 | no |

### Tier B: blocks in W1 (by 10-29)

| ID | Question | Options and consequences | Default | Where | Needed by | Latest sitting | Post-data? |
|---|---|---|---|---|---|---|---|
| B01 | How is the M0 verdict composed when several §4 rows apply, and how do amber, barred, waiting, `pass_one_family` and (with A05) `pass_local_family` states count? | **PLAN §3.8's proposal**: report every row, most severe class governs; an X1 or X3 that is not `pass` leaves the "X2 alone" clause undecided; pending states block the verdict except X4 "waits", `pass_one_family` (R4) and `pass_local_family` (A05 = QWEN3_LOCAL_PROVISIONAL). **Other readings**: amber counts as pass, and so on | PLAN §3.8 as written | PLAN Q7; PLAN §3.8 (revision 3 and 4 lines) | M0-verdict record SIGNED before the first experiment verdict (X0's, ≈ W1) | 10-25 (if not, X0's verdict waits for 11-01) | yes |
| B02 | X2: do MXCSR flag disagreements count as table/silicon mismatches, per execution? | **Yes** (stricter). **Values only** | yes, per execution | X2 Q4; TABLE-SCHEMA Q2 | X2-fuzz freeze (W1) | 10-25 (record in the 10-24 packet) | yes |
| B03 | X2: sign the second-oracle fallback (FUZZ-DESIGN §6.2) with the record? | **Sign**: a switch to SoftFloat-direct plus a probed SDE by week 3 is pre-registered. **Don't**: any switch is a deviation (§10) | sign | X2 Q5; FUZZ-DESIGN §6.2 | X2-fuzz signature (W1 sitting) | 10-25 | yes |
| B04 | X3: H's denominator for "schedule ≤ 30% of hand-written lines" | **H = 303** (SIMD-only closure; strict). **H = 369** (with the scalar closure; cap 110). Also confirm that shared helpers count once per file | 303 | X3 D§14 Q1 | before the first schedule line (W1 start, Fri 10-23) | 10-18 | yes |
| B05 | X3: generator x3gen (Python) or Exo's DAG-preserving subset? | **x3gen**: no IEEE-exact gap. **Exo**: no IEEE-exact mode [R05]; reversible until T0 | x3gen | X3 D§14 Q13; PLAN §7.1 W1 | W1 | 10-25 | no |
| B06 | What share of the 8 daytime threads may the local Qwen3's jobs take, and is there any exception for the X1 pilot? | **A weekly token share**, agreed in advance and lower in X2's fuzz weeks [G]. **All 8 outside X2's fuzz runs.** **An exception to the 8-thread rule** for the pilot (only Pierce can grant it; the sprint rule calls the cap a hard limit). The pilot's hours are re-estimated from a measured tok/s run first. A weekly cap also bounds A05's roles | a weekly share; no exception; re-estimate first (PLAN Q18) | PLAN Q18 (widened in revision 3); R30 | W1 (tok/s check; Qwen3 authoring if A04 = GEN_QWEN3) | 10-25 (10-18 if Qwen3 authoring starts at once) | for X1-local-pilot's machine hours: no |
| B07 | X2: may a local tool parse Intel's intrinsics XML to propose integer table entries, or does the table stay SDM-only? | **SDM-only** (provisional). **XML-assisted**: faster; licence question G02 open question 2 | SDM-only | TABLE-SCHEMA Q1 | W1 (entries for the census union) | 10-25 | no |
| B08 | Is a weekly total per track enough for owner-hour logging? | **Yes**. **Finer** (per record or per review) | yes | PLAN Q13 | the first weekly snapshot (Thu 10-22) | 10-18 | no |
| B09 | CC and X1 conflict: should `mithi` accept `par for`, `deterministic`, `schedule`, `spec` and `linear` typing-only, so that every canonical snippet is accepted (ROADMAP §3.6)? | **Typing-only** (CC's recommendation). **Keep `E-X1-NOTYET`** (X1 design draft): the CC gate cannot pass as written. **Change the gate**: a ROADMAP §3.6 loosening | typing-only | CC Q9; X1 DESIGN §9 | `mithi`'s scope now (W1–W2); at the latest X1-precondition freeze (W8) | 10-25; 12-13 at the latest | yes (X1-precondition, CC-gate) |
| B10 | Which quiet-profile machine settings will Pierce apply (06 §6.7)? | Each, **apply** or **not**: measurement power plan and core parking off; Defender and Search-indexer exclusions for the data directory (a security trade-off); maintenance window confirmed; a standard user `MithrilMeasure` and an outbound firewall rule for it (SANDBOX §3.2–3.3); optionally AMD uProf. Not applying means more voided sessions (the void rate feeds D-22) or, for the user and firewall rule, a degraded sandbox | apply all he judges acceptable; agents never change them | MEASUREMENT-SERVICE §7; SANDBOX §3; X3 D§14 Q11; PLAN S11, R22 | before the noise pilot (W1 under R5) | no sitting needed: applied by Pierce before the first pilot night (10-23 at the earliest) | no; a change mid-calibration voids sessions |
| B11 | X1: a dev half and a sealed confirmation half of the planted corpus (≥ 100 each)? | **Yes**: P-2 cannot be passed by iterating on its own test set. **One corpus of ≥ 100** (ROADMAP's minimum) | yes | X1 Q21 | before planted-corpus authoring (W1–W2, once A05 names an author) | 10-25 | yes (X1-precondition) |
| B12 | X1: where do the sandboxed `check` and oracle runs execute? | **Laptop** (PLAN §6.1): off the desktop's 8-thread cap. **Desktop WSL2 in daytime** (X1 DESIGN §11.1): ≈ 16–21 h of 12 cores [D, DESIGN §16] inside the cap. **Rented Linux VM**: paid infrastructure that R1 does not cover; it would need its own decision | laptop [G] | X1 Q11 (host part); PLAN §6.1 | W1 (smoke run); card iteration (W5) | 10-25 | no |
| B13 | Approve the desktop job-wrapper design (8-token semaphore, refusal inside quiet windows, start and end stamps)? | **Approve**. **Change it** | approve | PLAN C0; X4 deliverable S13 | W1 (wrapper live from Fri 10-23) | 10-18 | no |

### Tier C: blocks in W2–W3 (by 11-12): rules freezes for X2, X3 and X4, and the X1 card

**Moved earlier by R5.** The X4-calibration rules freeze before the first noise-pilot night (PLAN
§8). With the pilot nights in W1, every row that feeds those rules (C05–C10, C24, C25, C29), the
profile night (C01, C02) and the A/A design is needed by the first pilot night: latest sitting 10-25.
They stay in Tier C so that their IDs do not change; the "Latest sitting" column carries the earlier
date. If no answer lands in time, the record's default is registered at freeze.

| ID | Question | Options and consequences | Default | Where | Needed by | Latest sitting | Post-data? |
|---|---|---|---|---|---|---|---|
| C01 | May the 8-thread cap lift inside quiet windows for end-to-end decode and all-core STREAM? | **Lift inside windows only**. **Keep it**: end-to-end runs use a declared reduced placement, which changes what X4's end-to-end calibration covers, and all-core STREAM is not measured | lift inside windows only (PLAN Q2); the aggregate reading outside windows is already a sprint rule [M, sprint brief] | PLAN Q2; R6 | the profile night, in the pilot week (W1 under R5); end-to-end runs | 10-25 | yes (X3-parity, X4-calibration run types) |
| C02 | Which model file do timing runs read? | **The existing Qwen3-30B-A3B Q4 file on the desktop's NVMe**, in place and read-only (meaningful logits hashes). **The synthetic container** behind the 21.88 tok/s figure. Never from the USB HDD. Where is the file? | the real Q4 file, read-only | PLAN Q3; X3 D§14 Q10 | the profile's NVMe grid (pilot week, W1 under R5); X3-parity rules (W3) | 10-25 | yes |
| C03 | May M0 measure a clean `b5d3f14` build as the stand-in for `hearth-c-ref`, and must X3 re-pin if S0 tags `port-base-1` first? | **Clean `b5d3f14`**, MSVC and clang-cl, hashes pinned in X3-parity and X4-calibration; built on D:. **Wait for S0's tag**: S0 has no date. On re-pin: a pre-data amendment re-measuring H | clean `b5d3f14` on D:; re-pin only by a pre-data amendment | PLAN Q17; X3 D§14 Q7; D0-3 (provisional) | W3 (Plan B build) | 11-08 | yes |
| C04 | What does "the end of week 6" mean at Plan B cadence: for X2's kill, X3's tuning and inconclusive path, and X4 "waits"? | **Calendar W6 (12-03)**: Plan B-cal front-loads X2's 40 h; M0 verdict ≈ W13–W14 [G]. **The scheduled verdict week**. For X3: report "amber (b) pending" at week 6, or cap T_start at ≈ week 2.5 | none: Pierce's choice; PLAN gives no default | PLAN Q9, Q14; X3 D§14 Q16 | X2-gate rules (W2) | 11-01 | yes |
| C05 | The A/A stopping rule, the A/A horizon and the quiet-hour budget | End-to-end A/A **run to N** (X4 record: σ_d unbiased; ≈ 325–403 h at σ_d 4% for the full X4 plan [D from G]) or **stop at the first non-inferiority pass** (PLAN Q15: saves 13.0 h / 78.1 h [D], σ̂_d can be biased low). Microbenchmark A/A to **N** or **2N** (+13.3 h / +48.9 h [D]). Revise ROADMAP §10's M0 line (X4 alone exceeds it at both σ_d ends) by a signed record before collection? | run to N (X4 record, the later and more detailed source [G]); A/A to N, not 2N; §10 revision: Pierce's call | X4 Q1, Q9; PLAN Q15, Q12; COST §1.4 | X4-calibration rules (before the first pilot night) | 10-25 | yes |
| C06 | Is the ≤ 2/100 A/A rule the right design point? | **Confirm** ROADMAP's rule (exact OC: passes a true 5% rate with ≈ 0.12, 8% with ≈ 0.01). **Tighten before data** | confirm | X4 Q3 | X4-calibration rules | 10-25 | yes |
| C07 | 06 §6.2 (normative): adopt the run-level R scorer as the single gate scorer, and the pooled tail check at a one-sided 5% level? | **Confirm both**: literal block clip becomes descriptive; tail credit for a rare-stall candidate falls 0.130 → 0.017 [S]. **Keep 06 literally**: a 20% true improvement never reaches 20 within 400 blocks [S]; the calibration is re-simulated | confirm (X4 provisional) | X4 Q4; X3 D§15 (clip note) | X4-calibration rules | 10-25 | yes |
| C08 | May X4's kill e-process continue across the two N-sessions of an unchanged binary? | **Yes**: at σ_d 2% a kill needs both sessions (0.992 within 2N vs 0.048 within N [S]). **Another rule**, for example a longer N for kills | yes | X4 Q5 | X4-calibration rules | 10-25 | yes |
| C09 | If the pilot's outlier rate puts P(NI within N at parity) below 0.8, revise N, the clip rule and the throughput figures in a signed record before M4? | **Yes**. **No**: accept lower power | yes; fix the rule now, act before M4 | X4 Q6 | X4-calibration rules | 10-25 | yes |
| C10 | Exclude the untestable extras a22, a23 and a24 from X4's denominator, re-declared at M2 and M4, with both counts reported? | **Confirm**. **Keep them**: the gate is unreachable at X4 | confirm | X4 Q7; HACK-SUITE §4.1 | X4-hacks-catalogue freeze (W2) | 11-01 | yes |
| C11 | Gated catalogue run before or after the kit hash-freeze? | **After** (PLAN §3.5): engineering runs, freeze, then the gated run, where a miss is HALT-F. **Before**: freeze, blind-batch commissioning and X4-hacks-blind move a week later | after | PLAN Q20 | X4-hacks-catalogue freeze (W2) | 11-01 | yes |
| C12 | May X4's F1-sim (simulation, no measurement) run unattended in the daytime? | **ROADMAP / LITERAL**: attended. **DAYSIM / MEASUREMENT**: unattended daytime under the normal agent rules, a loosening only Pierce can grant | ROADMAP (D0_BRIEF §4.4) | D0-7x; D0_BRIEF Q6 | before any unattended F1-sim (W2) | 11-01 | no |
| C13 | X2: what action applies when no kill condition holds but the gate is missed at week 6? | ROADMAP §1 rule 2 needs a written action before freeze. **Narrow** (suggested): the failing variants stay `tested`, no extension. **Another written action** | narrow, no extension [G]; the record gives none | X2 pre-freeze Q1 | X2-gate rules (W2) | 11-01 | yes |
| C14 | X2: does a false accept from a fixable matcher or lifter bug kill X2, as ROADMAP's text says? | **Keep the text** (strict). **Excuse it** only if the fixed T1 then rejects 100% of a fresh blind pool: a signed change before data | keep the text | X2 Q2 | X2-gate rules (W2) | 11-01 | yes |
| C15 | X2: do the F16 and BF16 variants gate P1? | **Secondary** (ROADMAP names Q4, Q8, F32, act-q8). **Gate** | secondary; their mutants still count in P3 under C16's default | X2 Q3; TABLE-SCHEMA Q3 | X2-gate rules (W2) | 11-01 | yes |
| C16 | X2: which mutants enter P3's denominator? | **(b) every host joins T1** with an opaque-call premise; ≈ 2–4 agent-days and ≈ 3 more rules [G]. **(a) gating hosts only**: removes a ROADMAP mutant class (M-ROPE included), a loosening | (b) | X2 Q8; MUTANTS §1, §6 | X2-gate rules (W2) | 11-01 | yes |
| C17 | X2: do loop rules count toward ≤ 30 rules? | **1** (LOCKSTEP and its extensions as lemmas of one proof; strict default). **0** (looser). **7** (strictest) | 1 | X2 Q9; RULES RQ-1 | X2-gate rules (W2) | 11-01 | yes |
| C18 | X2: do integer identities count as rule rows? | **Yes**, each instance (strict; 7 rows). **No**: T2 per-instance obligations | yes | X2 Q10; RULES RQ-2 | X2-gate rules (W2) | 11-01 | yes |
| C19 | X2: does a Z3 QF_BV proof satisfy "Z3 FPA or exhaustive binary32" for integer rows? | **Only with an agreeing exhaustive or second-solver route**. **Alone** | with an agreeing route | X2 Q11; RULES RQ-3 | X2-gate rules (W2) | 11-01 | yes |
| C20 | X2: is a native difference caused by the compiled object a level-divergent finding or a T1 false accept? | **Carve-out**: a finding against the build, reported first. **Count it as a false accept**: a compiler's behaviour, owned by X0 and M2, could fire X2's kill | carve-out | X2 Q13 | X2-gate rules (W2) | 11-01 | yes |
| C21 | X3: are the scalar variants confirmatory? | **Yes** ("per ISA", ROADMAP §3.4). **Screening-only** (ROADMAP §10's S1 row): saves ≈ 0.4–1.5 quiet hours [D] | yes | X3 D§14 Q2 | X3-parity rules (W3) | 11-08 | yes |
| C22 | X3: the bands ROADMAP §3.4 leaves undefined | Proposed: schedule share S > 90 → amber; a confirmed decode-guard regression → amber; a T1 rejection from T1 incompleteness → amber; no admissible variant at window close → counts as < 90% (kill (a)). **Others** | as proposed | X3 D§14 Q3; X3 D§15 (ROADMAP §3.4 note) | X3-parity rules (W3) | 11-08 | yes |
| C23 | X3: the kill confirmation level | **1/20 per configuration**, no multiplicity correction. **Bonferroni 1/240**: kills rarer, a loosening | 1/20 | X3 D§14 Q4 | X3-parity rules (W3) | 11-08 | yes |
| C24 | Which margin boundary is canonical: ROADMAP's "ratio < 0.97" or 06's "E[x] ≥ log(1.03)"? | **log(1.03)** (stricter). **0.97** | log(1.03) | X3 D§14 Q5; X3 D§15 | X4-calibration rules (before the first pilot night) and X3-parity (W3) | 10-25 | yes |
| C25 | Is X3's parity verdict final only after X4's planted-regression calibration passes, and should X4 calibrate on `x3_bench`? | **PASS-PROVISIONAL until calibration** (amber (d)); **X4 adopts `x3_bench`**. **X3-local calibration**: ≈ 36 quiet hours per level per compiler [D] | provisional until calibration; X4 adopts `x3_bench` | PLAN Q8; X3 D§14 Q6; X3 D§15 | X4-calibration rules; X3-parity (W3) | 10-25 | yes |
| C26 | X3: the confirmatory clang-cl arm's flags | **X0's config B lines plus a shared `-mavx512vnni`**; `/clang:-ffp-contract=off` only if arm A fails §7 step 4; B-gnu descriptive. **B-gnu as confirmatory**: closer to SysV, further from CMake | the first | X3 D§14 Q8 | X3-parity rules (W3) | 11-08 | yes |
| C27 | X3: the length of the bounded tuning window on the inconclusive path | **7 days** [target]. **Other** | 7 days | X3 D§14 Q9 | X3-parity rules (W3) | 11-08 | yes |
| C28 | X3: include bit-identity under WSL2 Linux Clang in the gate (a tightening)? | **Yes**. **No** | yes | X3 D§14 Q12 | X3-parity rules (W3) | 11-08 | yes |
| C29 | What counts toward N, ROADMAP §1 rule 4's amber limit? | **A/B block time only** (N holds 3n blocks): P(Pass in the first N at parity, σ_d 2%) 0.995 [S]. **Cool-downs and gaps too** (≈ 2n): 0.535 [S] | block time only | X3 D§14 Q14 | X4-calibration rules; X3-parity (W3) | 10-25 | yes |
| C30 | Revise ROADMAP §10's n-formula for bounded bets, and proceed if the pilot's σ̂ gives P(Pass \| parity) < 0.8? | **No ROADMAP change now**; decide after the pilot's σ̂ and before the first A/B session [G]. **Revise §10** by a signed record. Gate-level power at a true 0.99 and σ_d 4% is 0.751 (0.464 under 2n) [S] | decide after the pilot, before the first A/B [G] | X3 D§14 Q15; X3 D§15 | X3-parity rules (W3), after the pilot | 11-08 | yes |
| C31 | X3: α across the two attempts of the inconclusive path | **Carry wealth forward, threshold 20**: supports "at least one evaluated variant is non-inferior". **Split α (threshold 40 each)**: per-variant claims, ≈ 1.23× the blocks [D] | carry forward | X3 D§14 Q17 | X3-parity rules (W3) | 11-08 | yes |
| C32 | X3: the regression estimand | **Clamps centred on each boundary** (keeps a kill reachable within N). **Another estimand** | centred clamps | X3 D§14 Q18 | X3-parity rules (W3) | 11-08 | yes |
| C33 | CC: which allocation rule does X1 use? | **C-ALLOC** (`alloc(Global)`) [prov]. **A label-free global heap**: policies could allocate unless T0 forbids it. **Arena-only tasks** | C-ALLOC | CC Q3 (OP-1) | before the Tier 0 card freezes (Plan B cards W3) | 11-08 | yes (X1 subset) |
| C34 | CC: rename one of the two meanings of "abandon" before the Tier 0 card freezes? | **Rename the trap-path release** so the agent verb keeps its 05 §10 name [G]. **Rename the verb**. **Keep both** | rename the trap-path release [G]; the note gives no default | CC Q7 | Tier 0 freeze (W3) | 11-08 | no |
| C35 | X1: does `mithi`'s hole report reach the three Mithril arms? | **Yes**: symmetry with the tooling arm. **Only the tooling arm** gets hole context | yes | X1 Q9 | card design (W3); card iteration (W5) | 11-08 | yes |
| C36 | X1: obfuscation scope | **Keywords, primitive types and keyword-like prelude names**, with language names removed (record). **Keywords and primitive types only** (ROADMAP's minimum) | the record's wider scope | X1 Q19 | card freeze (W5) | 11-22 | yes |
| C37 | X1: `topk` parity | **Give `topk` to the Rust and C11 helper packs** (provisional). **Remove it from `mithi`'s X1 std**: every arm hand-writes T-ROUTE selection | give it to all packs | X1 Q20 | helper packs (W2–W5) | 11-01 | yes |
| C38 | X1: Pierce's role in item review | **A seeded sample of 24 after the card freeze** (≈ 6 h; with a generated suite, 24 templates, ≈ 4–8 h [G]). **All held-out items after the freeze** (≈ 13–21 h). **No card editing; sign the card hash only** (required if he authors templates, A04 = GEN_OWNER) | the sample | X1 Q17; PLAN Q16 (review part) | before card iteration (W5) | 11-22 | yes |

### Tier D: blocks in W4–W9 (Plan B's X1 rules freeze ≈ W5, precondition ≈ W8; X2 and CC mid-course)

| ID | Question | Options and consequences | Default | Where | Needed by | Latest sitting | Post-data? |
|---|---|---|---|---|---|---|---|
| D01 | Where does X1's σ_ta come from, and how large is the sealed reserve? | **(c) a dedicated 24-item calibration set** after the card freeze (X1 record; 240 attempts at one family). **(a) a Rust arm on the card-iteration items** (PLAN; the card is tuned on them, which biases n down). **(b) a pre-registered prior floor**. Reserve: 184 candidates and a cap of 160 (record), or 120 | (c), with the record's reserve; the record is the later and more detailed design [G] | PLAN Q16; X1 Q18, Q2 (sample part), Q10 | X1-heldout rules (before the first card-iteration attempt, W5; W2 under Plan A) | 11-22 | yes |
| D02 | X1: the decision statistics | **Identity-link stratified estimator for VP@1 and a stratified ratio estimator for CABW**, GLMMs as reported secondaries (a deviation from 05 §13, not from ROADMAP). **The logistic GLMM** as the decision statistic | the record's | X1 Q5 | X1-heldout rules (W5) | 11-22 | yes |
| D03 | Should ROADMAP §3.2 state X1's CABW and joint false-kill requirements (R-CABW, R-JOINT)? | **Record binds them regardless**; a ROADMAP edit is optional. **Amend ROADMAP §3.2** | the record binds them; ROADMAP edit optional [G] | X1 Q7, Q14 (iv) | X1-heldout rules (W5) | 11-22 | no for ROADMAP; the record's text is pre-data |
| D04 | X1: the named parameters `agent.hole_use_floor` = 0.10 and `agent.dc_rate_bound` = 0.10 | **Accept** [G]. **Other values** | accept | X1 Q8 | X1-heldout rules (W5) | 11-22 | yes |
| D05 | X1: should SE(Γ̂) > 3.90 points make the result UNDERPOWERED? | **Not adopted** (record): reported only. **Adopt**: voids the run in 0.05–0.14 of high-variance and 0.35–0.56 of stress worlds at n = 96 [S] | not adopted, pending his decision | X1 Q15 | X1-heldout rules (W5) | 11-22 | yes |
| D06 | One convention for interval facts (`ci_low`, `ci_high`) across X1 and M1 | **Two-sided 90%, with `.ci_level` and `.ci_sides` facts** (X1). **One-sided 90%** (05 §13's M1 CABW test). A DECISIONS / 06 §7.2 change | two-sided 90% with level facts | X1 Q16 | X1-heldout rules (W5) | 11-22 | yes |
| D07 | The X1 runner under R1 and R4: pin which Claude model; accept unpinned sampling and an isolated Claude Code configuration? | **Accept**, pinning the model ID per session; results describe "Claude in Claude Code" [inference]. **Reject**: no Claude attempts without metered API, so the X1 rule of R4 cannot run | accept | X1 record, restructure section (new); PLAN Q10 (remainder) | X1 freeze (W5); ideally with A20 | 10-18 (with A20) if possible; 11-22 at the latest | yes |
| D08 | X1: the Claude Code plan's data-use setting for content sent to it | **Check it, and opt out of training if the plan offers that** [inference; not verified]. **Accept the default** | check and opt out | X1 Q4 (now about the plan); X1 DESIGN §4.2 | before any sealed visible bundle reaches a Claude participant (card iteration, W5) | 11-22 | no |
| D09 | X1: publish the canary UUID at freeze, or keep it private? | **Publish** (DESIGN §4.4): corpus builders can filter it. **Private** | publish | X1 Q13 | X1 freeze (W5) | 11-22 | no |
| D10 | X1: the pilot's task family | **T-ROUTE** (provisional). **Another** | T-ROUTE | X1 Q12 | X1-local-pilot record (W9) | 12-20 | yes |
| D11 | 03 §6.3 bans MAX/MIN operand commutation; may T1 use the conditional fold rules R02/R03 under their side conditions? | **Allow under the side conditions** (X2 proposal): P1 can reach 8/8. **Keep the ban**: P1 cannot reach 8/8 for act_q8 [inference] | allow under side conditions | X2 Q7; RULES §7 item 1 | before T1 runs on the real variants (≈ W5 under Plan B [G]) | 11-22 | yes |
| D12 | The trigger grammar (06 §7.2) cannot parse hyphenated arguments such as `INV-DET-1` | **Quote invariant IDs as strings** (no grammar change) [G]. **Add a hyphenated identifier class** | quoted strings [G]; X4 gives no default | X4 Q2; TOMBSTONES §4.1 | X4-tombstone-replay freeze (W5) | 11-22 | yes |
| D13 | CC: do protocol atoms of the Tier 0 card trace to 05 and 03 rather than to the note? | **Yes**. **No**: the trace gate cannot pass as written | yes [G]; until answered each also cites a note section | CC Q4 | CC-gate (W8) | 12-13 | yes |
| D14 | CC: is a frozen prelude of declarations an acceptable input to "accepted by `mithi`"? | **Yes**. **No**: canonical snippets reference declarations they do not contain | yes [G] | CC Q5 | CC-gate, X1-precondition (W8) | 12-13 | yes |
| D15 | CC: what does "every derived snippet" mean for the six derived snippets outside X1's scope? | **Agreement with `E-OUT-OF-SCOPE-<KW>`** (note's current reading). **`mithi` types them**: more checker work. **Exclude them**: loosens §3.2 | the note's reading | CC Q10 | X1-precondition (W8) | 12-13 | yes |
| D16 | CC: should any of the review's counterexamples (N-11 to N-39) become gate items? | **No: supplementary**, offered to the planted corpus. **Yes**: adds requirements ROADMAP §3.2 does not state | supplementary | CC Q11 | X1-precondition (W8) | 12-13 | yes |
| D17 | CC: a policy trap "falls back to the default policy": the port's declared fallback, not a profile's default? | **Yes** (note's reading). **No** | yes | CC Q1 | CC freeze (W8) | 12-13 | yes |
| D18 | CC: `debug_assert!` is always checked | **Confirm** (C-MACROS). **Release-only** | confirm | CC Q8 | CC freeze (W8) | 12-13 | yes |
| D19 | CC: make F-tot, P-ind, S-tot and A-ind named obligations of the store-core certificate? | **Yes**: the §8 narrowing verdict depends on them; A-ind has no discharge route yet. **No** | yes [G] | CC Q2 | CC signature (W11); matters at M4 | 2027-01-03 | no |
| D20 | X2: may X2 certify `b5d3f14` under the declared precondition "MXCSR = 0x1F80 at entry" before D0-5b lands? | **Yes**, the precondition stated in every certificate. **Require D0-5b first** | yes (record proceeds so) | X2 Q12 | X2 verdict (W10–W11; W6 under Plan B-cal) | 12-27 (11-29 under B-cal) | yes |
| D21 | Long-term Owner key: two hardware tokens, a recovery path, a separate gate account | **YES**: buy two tokens (price not researched) and set up the account (1–3 h). **NO**: no AUTHORITY facts from M3, so no promotion | YES (D0_BRIEF §4.3); the gate account is also A06's option (a) | D0-9b; D0_BRIEF Q8 (cost hardware?) | ROADMAP: by X4 (≈ W6–W11); first blocked step M3, or earlier via A06 | 11-29 to 01-03, or 10-18 via A06 | no |
| D22 | Forge authority: who signs grants; `timing_only` defaults only by ADR | **YES, YES** (ROADMAP §11). **NO**. And ROADMAP's deadline: **KEEP** X4 for every part, or **SPLIT** (grants M6, defaults after S4) | YES, YES; Q11 open | D0-7b, D0-7c; D0_BRIEF Q11 | ROADMAP: X4; first use M6 / after S4 | 11-29 to 01-03 | no |
| D23 | Claude Code extra usage when the plan's windows bind | **Keep it disabled**, consistent with R1 [inference: extra usage is paid usage]. **Enable it**: paid usage beyond the plan, which R1 rules out unless he re-decides | keep disabled | PLAN R17; COST §5 | when X1's attempts run (W5–W11) | 11-22 | no |
| D24 | X2: run the vector sets on the Zen 4 laptop as a secondary fingerprint? | **Yes**, as a secondary arm that cannot change a verdict. **No** | the X2 track's call; no owner action needed unless it changes the record [G] | FUZZ-DESIGN §8; PLAN §6.1 | X2 fuzz weeks (W1–W3) | none needed | no |
| D25 | Narrow ROADMAP §3.5's "tests exchangeability on this desktop" to "label exchangeability"? | **Yes**: the A/A design tests harness label symmetry only. **No** | yes [X4 suggests] | X4 Q8 | any time before X4's verdict | 2027-01-03 | no |

### Tier E: end of M0 and S0 (W6–W12; S0 has no date)

| ID | Question | Options and consequences | Default | Where | Needed by | Post-data? |
|---|---|---|---|---|---|---|
| E01 | May Hearth's core be Mithril-generated C11 (option A, superseding ADR-0001)? | **YES**, landed alone (the breaker does not fire). **NO**: STOP-L, re-scoped to tools over C | YES | D0-1 | end of M0 (≈ W12), or S0's step 2 if E02 says so | no |
| E02 | Does S0's step 2 include the ADR-0001 supersession? | **INCLUDES_9_1**: D0-1 is needed at S0. **ONLY_9_3**: D0-1 waits for the end of M0 | none (sources disagree) | D0_BRIEF Q12 | S0 step 2 | no |
| E03 | Who does S0, when, and from which budget line? | An answer line; S0 has no ROADMAP §2, §3 or §10 row | none | D0_BRIEF Q3 | before any S0 work (PLAN schedules none until R3 is committed) | no |
| E04 | Commit R3 and repair the task DAG | **YES**, with `struct_size` (D0-5a) and the decay default per E06. **NO**: S0 cannot start | YES | HM-5a; D0-5a | S0 step 1 | no |
| E05 | Add `struct_size` fields in the R3 commit? | **YES**. **NO**: S6a cannot export `hearth.h` exactly; one B1 item lost | YES | D0-5a | the R3 commit | no |
| E06 | Heat-decay default: 0.9 or 0.995, and commit `policy-default.md` first? | **DECAY_09**, signed only after HM-5b commits the evidence file. **DEFER**: R3 commits with 0.995, decide at S4. **DECAY_0995** | DECAY_09 after HM-5b; otherwise DEFER | D0-5c; HM-5b | before the R3 commit only if R3 keeps 0.9; else S4 | no |
| E07 | ADR-0010: specified transcendentals, `canon_v1` expf, `cr` sinf/cosf; vendored CORE-MATH allowed? | **YES / CANON_V1 / CR**, with a fallback date. **NO**: libm drift, `parity::` shim. HM-6: **DEFER** unless `cr` vendors CORE-MATH | YES, CANON_V1, CR; HM-6 DEFER | D0-2, D0-2a, D0-2b; HM-6 | the S0 corpus (≈ week 3 if S0 is to finish in M0) | no |
| E08 | Accept ADR-0009 before the S0 corpus relies on its tooling? | **YES**: no breaker trip. **NO** | YES | HM-7 | before the S0 corpus | no |
| E09 | File the research's Hearth defect reports, and through which channel? | **YES**, filed by Pierce, labelled "from Mithril research"; memory-safety items **PRIVATE**. Hearth's GitHub visibility is unknown | YES; PRIVATE | HM-9a, HM-9b; X0 amber (b) drafts; X3 D§15 (`test_isa_identity` report) | any time; X0's draft after its verdict | no |

### Tier F: M1 and later

| ID | Question | Default | Where | Needed by |
|---|---|---|---|---|
| F01 | S0 freeze, `hearth-c-ref` lineage and the hash corpus as a maintainer golden tier | YES, reproduced twice | D0-3 | M1's S1 |
| F02 | Spec authority: who seals; different families for Author and Builder (only Qwen3 under R2, and only by a new answer, as A05); `validated` as an INV-VERIFY class | YES ×3; (b) decided at M1 against R2 | D0-11a/b/c; D0_BRIEF Q1 | M1 (c: S1) |
| F03 | The MXCSR invariant | YES | D0-5b | S1 |
| F04 | Task-DAG ownership by definition path | YES | HM-1 | S1 |
| F05 | Mirror hashing or a qualified INV-DET-1 | YES: qualify by ADR by S4; per-slab hashes in FORMAT v2 | D0-5d | S4 (decide now per ROADMAP) |
| F06 | B1's slack and D0-5's deadlines in ROADMAP | Pierce's call | D0_BRIEF Q9, Q10 | with D0-5 |
| F07 | GPU scope: RTX 5070, `nvcuda.dll`, display on the iGPU | DEFER ×3 | D0-6a/b/c | M5 |
| F08 | Normativity | STATUSQUO | D0-4 | S6 |
| F09 | B2's margin | DEFER; under R1 B2's cost becomes plan usage and its two-family pooling meets the same gap as X1 | D0-10e | before M6 |
| F10 | MXFP4 order, `canon.v2`, self-hosting | DEFER ×3 | HM-2, HM-3, HM-4 | later |
| F11 | Kimi-K3 sequencing and kernel reuse as a canon decision | YES, YES | HM-8a, HM-8b | before K3 work lands in C |

---

## Standing gaps (no single question closes them)

- **DR-017's binding test.** Under R1, R2 and R4 no second frontier family exists, so an X1 pass stays
  provisional, and M1's DR-017 kill, which also needs ≥ 2 families, cannot be evaluated either (PLAN
  R31). The cheapest repair is one frontier family's attempts alone, ≈ $1.4–5.7k at n = 96 [D, X1
  record], contrary to R1; it is shown so that the price is visible.
- **Different-family review.** Only the local Qwen3, non-frontier, can be the "other family", and
  only by a new answer (A05). Under QWEN3_LOCAL_PROVISIONAL every pass that rests on it stays
  provisional.
- **Plan capacity for X1.** X1's Claude attempts are ≈ 0.73–3.51 billion tokens (n = 96 to 160) [D
  from inference]; how that maps onto the plan's account-wide windows is unknown until the X1 smoke
  run (PLAN R29), and whether the terms allow it is A20.
- **Quiet hours.** X4 alone exceeds ROADMAP §10's M0 line at both σ_d ends (X4 Q1); D-22 is at risk.
- **S0** has no ROADMAP slot or budget (E03).

## Follow-ups once R1–R6 are ratified (actions, not questions)

- **The X1 amendment record (R4)** has to be drafted (lead engineer or X1 track) and put in a packet
  FROZEN; its contents are listed in the X1 record, option 4b, "Pierce signs" (i).
- **The X4-noise-pilot record** has to be split out of the X4 DRAFT (the lead engineer splits it at
  freeze, X4 record header) and frozen, with the X4-calibration rules, before the first pilot night.
- **m0/README's collection rule** should narrow its instruction route to X0 (R3). README is not the
  owner track's file.
- **The X0 record's authorisation line** can cite the ratified D0-12x = X0 and D0-12i, and OQ-6's spend
  cap of $0 metered (R1).
- **The X2, X3, X4 and CC records** say collection needs a signature "or an explicit Owner
  instruction"; under R3 only the signature route applies to them.
- **Stale "D0-10 families" text in other tracks' files** [M, read by the owner track 2026-10-16]. Under
  R1 and R2 no frontier family is scheduled, so each "scheduled for the D0-10 families" becomes
  "pending D0_BRIEF Q17 (the local Qwen3) or a future frontier family":
  [X4 record](prereg/X4-integrity.md) line 160 ("batch (b) scheduled for the D0-10 families");
  [HACK-SUITE](../../experiments/x4-integrity/HACK-SUITE.md) line 8 ("waits for D0-10 to name the
  families"), §3 step 3, line 111 (the same) and line 150 ("needs a different family (D0-10)");
  [core-calculus.md](core-calculus.md) §16, CC Q6 ("Until D0-10 names families", line 3059 of the
  working tree); [x1 DESIGN](../../experiments/x1-harness/DESIGN.md) §2's role table (task authors,
  item reviewers, semantic guard, planted corpus, kit acceptance corpus and scorer canaries as
  "family B or C"; participants as "family A and family B"), lines 110–126, which the X1 record's
  restructure section overrides until the X1 track revises them.
- **The WSL keepalive** (`wsl -d Ubuntu --exec sleep 43200`, a sprint rule) can span 23:00–07:00. R5's
  log entry rules out "WSL activity" in a window. Whether an idle WSL VM counts is for the X4 track's
  load gate to measure and for Pierce to rule on [G].
- **Tombstone admissions** proposed by PLAN §11, D0_BRIEF §6, X0 Appendix B, X1 DESIGN §17, X3
  DESIGN §13 and X4 TOMBSTONES are AUTHORITY acts (DECISIONS §1). None blocks M0; batch them for a
  later sitting.
- **ROADMAP observations** raised without a change (X0 OQ-1 if OP_CLASS; X1 Q7, Q14; X3 D§15; X4 Q1,
  Q8; PLAN Q14, Q15, Q16; D0_BRIEF Q2, Q8, Q9, Q10, Q11): collect them for one ROADMAP amendment
  sitting rather than piecemeal.
- **Desktop housekeeping (optional, Pierce only):** about 320 MB of WSL trace files on C:
  (TOOLCHAINS §10 item 4) can be deleted by him, or avoided with `[wsl2] guiApplications=false` in
  `.wslconfig`, a configuration change agents may not make.

---

## Where every source question went

| Source | Question → queue ID |
|---|---|
| Owner answers log | batch 1 → R1–R3; batch 2 → R4 (X1 rule), R5 (D0-10d), R6 (cadence); earlier instructions → I1 (D0-12i), I2 (A02), I3 (A07) |
| D0_BRIEF lines | D0-12, 12x, 12i → R3; D0-10a → R1; D0-10c → R2; D0-9a → A01; D0-10b → A15 (H), R6 (signing slots), A02; D0-10d → R5, A17; D0-8 → A18; D0-7a → A19; D0-7x → C12; D0-7b, 7c → D22; D0-9b → D21; D0-1 → E01; D0-5a → E05; D0-5c → E06; D0-2, 2a, 2b → E07; D0-3 → F01; D0-11a/b/c → F02; D0-5b → F03; D0-5d → F05; D0-6a/b/c → F07; D0-4 → F08; D0-10e → F09 |
| D0_BRIEF HM | HM-5a → E04; HM-5b → E06; HM-6 → E07; HM-7 → E08; HM-9a, 9b → E09; HM-1 → F04; HM-2, 3, 4 → F10; HM-8a, 8b → F11 |
| D0_BRIEF Q | Q1 → F02; Q2 → A01; Q3 → E03; Q4 → R3; Q5 → R4 (A03); Q6 → C12; Q7 → A18; Q8 → D21; Q9, Q10 → F06; Q11 → D22; Q12 → E02; Q13 → A16; Q14 → R1 (moot); Q15 → R2 (moot unless OPT1); Q16 → R4 (A03); Q17 → A05; Q18 → A04 |
| PLAN Q | Q1 → R5, A17, A19; Q2 → C01; Q3 → C02; Q4 → A07; Q5 → A06; Q6 → A01, A02, R6; Q7 → B01; Q8 → C25; Q9 → C04; Q10 → R2, D07; Q11 → A15; Q12 → A17, C05; Q13 → B08; Q14 → C04; Q15 → C05; Q16 → D01, C38; Q17 → C03; Q18 → B06; Q19 → R1 (moot); Q20 → C11; Q21 → R3. C0 items: harness host and toolchains → A07, B12; signing slots → R6; job wrapper → B13. R29 → A20 |
| X0 | OQ-1 → A08; OQ-2 → A09; OQ-3 → A10; OQ-4 → A11; OQ-5 → A12; OQ-6 → R1, R3; OQ-7 → A13. TOOLCHAINS §10: 1, 2 → A11; 3 → A14; 4 → follow-ups; 5, 6 informational |
| X1 | Q1 → R2, D07; Q2 → R1, D01; Q3 → A04, A05; Q4 → D08; Q5 → D02; Q6 → R4 (moot); Q7 → D03; Q8 → D04; Q9 → C35; Q10 → A04, D01; Q11 → A06, B12; Q12 → D10; Q13 → D09; Q14 → D03, follow-ups; Q15 → D05; Q16 → D06; Q17 → C38; Q18 → D01; Q19 → C36; Q20 → C37; Q21 → B11; runner question → D07; plan terms and capacity (restructure section) → A20 |
| X2 | Q1 → C13; Q2 → C14; Q3 → C15; Q4 → B02; Q5 → B03; Q6 → A05; Q7 → D11; Q8 → C16; Q9 → C17; Q10 → C18; Q11 → C19; Q12 → D20; Q13 → C20. TABLE-SCHEMA Q1 → B07, Q2 → B02, Q3 → C15. RULES §7: 1 → D11, 2 (keep MAXPS/MINPS as observers: no action needed), 3–5 → C17–C19. FUZZ-DESIGN §6.2 → B03, §8 → D24. MUTANTS → C16 |
| X3 (design §14) | Q1 → B04; Q2 → C21; Q3 → C22; Q4 → C23; Q5 → C24; Q6 → C25; Q7 → C03; Q8 → C26; Q9 → C27; Q10 → C02; Q11 → B10; Q12 → C28; Q13 → B05; Q14 → C29; Q15 → C30; Q16 → C04; Q17 → C31; Q18 → C32. §15 proposals → C22, C24, C25, C07, C30, E09, follow-ups |
| X4 | Q1 → C05; Q2 → D12; Q3 → C06; Q4 → C07; Q5 → C08; Q6 → C09; Q7 → C10; Q8 → D25; Q9 → C05. MEASUREMENT-SERVICE §7 and SANDBOX §3 settings → B10 |
| CC | Q1 → D17; Q2 → D19; Q3 → C33; Q4 → D13; Q5 → D14; Q6 → A05; Q7 → C34; Q8 → D18; Q9 → B09; Q10 → D15; Q11 → D16 |
| COST | stop-loss levels → R1 (metered rows dormant); extra usage → D23 |

---

## Review log

| Date | Reviewer | Lens | Family | Findings | Accepted | Rejected |
|---|---|---|---|---|---|---|
| 2026-10-16 | Reviewer 1 | The Owner's position across the five owner-track files: fidelity to the owner answers log, decision by framing, cost completeness, sitting feasibility, stale text (inferred from the findings; the lens name was not relayed) | Claude, same family, independent context | 13: 1 blocker, 6 major, 6 minor | 13 (6 with a modified fix) | 0 |

The reviser (the owner track, a Claude agent, same family) checked every finding against the sources
before acting on it: [OWNER-ANSWERS.md](OWNER-ANSWERS.md) at commit `11210a8`, the five track files,
ROADMAP §3.2, §3.3, §3.5, §3.6 and §11, the X4 record and HACK-SUITE, core-calculus §16, x1 DESIGN §2,
and the arithmetic (`owner/calc2.py`, CPython, < 1 s [M]). The same review applies to
[D0_BRIEF](../D0_BRIEF.md), [PLAN](PLAN.md), [COST](COST.md) and the
[X1 record](prereg/X1-writability.md); each logs it in one row.

**Accepted as proposed:** finding 1 (blocker: batch 2 carried everywhere; R4–R6; status lines;
sitting dates), 2 (no default for the template author; GEN_OWNER listed first), 7 (A20), 8 (one
sitting-1 estimate; §4.13 "five groups"), 10 (provider-era text in PLAN), 11 (A02 and A07 reduced
to their residuals), 12 (one status wording; COST's "approved").

**Accepted with a modified fix** (one line each):
- Finding 3 (option text): accepted; the D0-10c question as asked did also name authoring and
  reviews, so the files now say the option text limits the answer to the pilot and treat every other
  Qwen3 role as a new decision, rather than calling the earlier reading wrong.
- Finding 4 (template counts): accepted with corrected arithmetic. 127 templates give ≈ 32 Qwen3 h,
  not 35 (the earlier script used 140), so option 4b's Qwen3 total at ≤ 1 item per template is
  ≈ 44–378 h, not 47–378; the Owner-template figure at 2–3 per template is ≈ 36–141 h, not 35–142
  (71 × 0.5 and 94 × 1.5) [D, `owner/calc2.py`].
- Finding 5 (sitting-1 agenda): accepted; one precision: an X4-noise-pilot signature on 10-25 still
  leaves the 4 pilot nights inside W1 (10-25 to 10-28), so "cannot start before the 10-25 sitting"
  is used, not "slips past W1". X2-fuzz can still be signed on 10-25 without the census hash, under
  the census amendment rule PLAN §3.3 already provides.
- Finding 6 (QWEN3_LOCAL): accepted as options QWEN3_LOCAL_PROVISIONAL and QWEN3_LOCAL_FULL; FULL is
  labelled "keeps ROADMAP's letter, weaker in substance; only Pierce can choose it", not "a ROADMAP
  loosening", because ROADMAP §3.3, §3.5 and §3.6 ask for "a different family", not a frontier one.
- Finding 9 (follow-ups): accepted; CC Q6 is at line 3059 of the working tree, not 3046, and is cited
  by section.
- Finding 13 (GEN_CLAUDE, Q17 hours): accepted; the X1 record did mention Claude templates ("not
  offered"), so the gap was an unpriced option rather than a silent one. Q17's roles carry a bounded
  [D from G] placeholder (≈ 2–38 h) and the B06 weekly cap.

**Rejected findings:** none.

---

## Change log

| Date | Change | By |
|---|---|---|
| 2026-10-16 | Created: answers received (R1–R3), Next 3 asks, sitting-1 agenda, 115 queue entries in six tiers (A 19, B 13, C 38, D 25, E 9, F 11 [M: counted by script]), standing gaps, follow-ups, source map | owner track (Claude; not reviewed) |
| 2026-10-16 | Revised after one review (Claude, same family, independent context; 13 findings, all accepted). Batch 2 carried (R4–R6) with the option text of every answer, cited from OWNER-ANSWERS.md; earlier instructions I1–I3; A03 marked answered; A02, A07 and A17 reduced to their residuals; A04 without a default, GEN_OWNER first, GEN_CLAUDE added as a labelled loosening, two template-count rows; A05 split into PROVISIONAL and FULL; A20 added (plan terms and capacity); "Latest sitting" column in Tiers A–D against Sunday sittings; sitting-1 agenda with the records to sign if FROZEN and one estimate; follow-ups for stale D0-10 text and the WSL keepalive; review log. 116 queue entries (A 20, B 13, C 38, D 25, E 9, F 11) | owner track reviser (Claude, same family, independent context from the reviewer) |
