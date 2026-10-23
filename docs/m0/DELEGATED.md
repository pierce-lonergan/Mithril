# Decisions taken under the Owner's written delegation

On 2026-10-23 Pierce wrote: "Do whatever YOU need to do to make this project work. you have my full written
permission to ratify any conflicting statements." The message is quoted verbatim in [OWNER-ANSWERS.md](OWNER-ANSWERS.md),
batch 4. This file logs every decision the lead engineer takes under that delegation, so that Pierce can review
each one and reverse any of them at a sitting.

**Scope**
- The lead engineer may use the delegation to resolve contradictions between records.
- He may also use it to settle open owner items the work needs. Where the item has a registered recommended
  default, he adopts that default; otherwise he makes a documented choice.

**Limits**
- No ROADMAP threshold is ever loosened, and nothing is changed post-data in the favourable direction.
- FROZEN records stay append-only.
- The coexistence rules and the safety scope still apply: documented, vendor-supported interfaces only.
- No money is spent, because R1 forbids metered API.
- Pre-registration records are not signed in Pierce's name: they wait for his own chat or key signature.
- Gate verdicts are reported to Pierce before anyone acts on them.

**Review.** Every row is reviewed at the next sitting. A row Pierce rejects is reversed, and anything built on it is
re-examined.

| # | Date | Item (source) | Options | Choice | Why | Reversible how |
|---|---|---|---|---|---|---|

---

## Rows drafted by the queue track (2026-10-23); adoption status per row

**Status (lead engineer, 2026-10-23, 13:00 PT):** each row below now says ADOPTED or Not delegable. The lead engineer adopted the 59 delegable rows in place after the owner-advocate review, rather than copying them into the table above. The queue track (a Claude agent) drafted them on 2026-10-23 from its
classification of every open item ([OWNER-QUEUE](OWNER-QUEUE.md#classification-of-every-open-item-2026-10-23)).
The lead engineer adopts a row by copying it into the table above with a number and the adoption date, or
rejects it. Until then each row is a proposal, and the item it names stays open. Reviewed once (Claude, same
family, independent context; 13 findings, all accepted, 3 with a modified fix;
[review log](#review-log-of-the-proposed-rows)). After that review, **three rows are marked "Not delegable": P2,
P3 and P23.** Each names a decision reserved to Pierce, gives a recommendation for his sitting, and proposes at
most an interim restriction, which is the only part the lead engineer can adopt.

**The test applied to every row.** A row is proposed only if all four hold:
1. Pierce has not answered the item (R1–R10 and I1–I4 in OWNER-QUEUE were checked).
2. The work needs an answer before a DRAFT record freezes or a step starts; "Needed by" is in the Item cell.
3. It needs nothing that only Pierce can give: no signature, key, money, his hours, his accounts or machine
   settings, GEMS or Hearth. It takes no decision that a FROZEN record or the owner log reserves to him (for
   example X1-amendment-1 §5.3, "That reading is his to adopt, not this record's"; OWNER-ANSWERS, a second family
   "only by a new Owner answer"), and it amends no normative architecture section that governs later milestones.
4. It loosens nothing. The choice is the registered recommended default, or stricter. Where nothing is
   registered, it is a documented choice no looser than any registered option. Every row is pre-data for the
   record it touches and fixes its rule in full when it is written: no trigger is left for a track to settle
   later. No ROADMAP threshold moves, and no FROZEN body changes.

**Three cautions for the lead engineer.**
- **ROADMAP §11 says of D0-1 to D0-12: "No agent may take these decisions."** P4, P7 and P27 touch D0 lines:
  D0-10c's local model, D0-10d's rate rule and D0-7x. These rows adopt an **operating assumption** only: what
  the work proceeds on, as PLAN already does with "provisional, pending D0-x". The D0_BRIEF line stays unticked
  for Pierce's signature. P2 (D0_BRIEF Q18, which splits D0-10c's roles) and P3 (Q17) are not delegable at all:
  a FROZEN, signed record and the owner log reserve them to him (see each row). Whether batch 4 lets the lead
  engineer take a D0 line outright is put to Pierce at sitting 2 (OWNER-QUEUE, sitting-2 list, item 2).
- **A row that settles a question inside a DRAFT record settles its text before freeze.** Pierce still signs
  the record ("Pre-registration records are not signed in Pierce's name", Limits above).
- **A row marked "Not delegable"** keeps its number so that cross-references hold. Its item stays open (class B
  in OWNER-QUEUE) until Pierce answers.

| # | Date | Item (source) | Options | Choice | Why | Reversible how |
|---|---|---|---|---|---|---|
| P1 | 2026-10-23 | OWNER-QUEUE A02 (PLAN Q6, R26): may freeze commits of pre-registration records land between sittings? Needed by: every freeze from now on | (b) yes: freezes land between sittings, and only signatures wait for a sitting. (a) no: a record ready just after a sitting waits ≈ 7 days | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** (b) | Registered default (b) [G, OWNER-QUEUE A02]. A freeze fixes a record's text earlier. It decides nothing and loosens nothing, and the signatures stay Pierce's. It is already the practice: X0 (`152fa33`) and X1-amendment-1 (`ac751b8`) were frozen between sittings, and Pierce chat-signed both at those commits (R10) | Pierce answers (a) at a sitting. Later freezes then wait for sittings. Earlier freezes stand, because he signed them |
| P2 | 2026-10-23 | D0_BRIEF Q18 = OWNER-QUEUE A04: who writes the templates of X1's generated suite, and how R4's last sentence is read. Needed by: the first sealed template, which also needs A06's store and X1-amendment-1 §6.2 = RUNNABLE, so nothing needs it before sitting 2 (Sun 10-25) | GEN_OWNER, GEN_QWEN3, GEN_CLAUDE, each at ≤ 1 held-out item per template or at 2–3 within n ≤ 160; also QWEN3_ITEMS, OWNER_ITEMS and OTHER (for example a split author) | **Not delegable.** Q18 and the reading of R4's last sentence are reserved to Pierce by X1-amendment-1 §5.3 (FROZEN, signed): "That reading is his to adopt, not this record's"; "The choice is Pierce's." Recommendation for sitting 2 (proposed for the lead engineer): GEN_QWEN3, ≤ 1 held-out item per template, with the C38 sample review. **Interim restriction (adoptable), until Pierce signs a Q18 line:** only family-agnostic work proceeds: the generator, the transliterator, and S71 within R2's terms (P13). No Qwen3 template authoring, practice templates included | §5.3's own table marks GEN_QWEN3 "Needs a new Owner answer beyond R1–R6: **yes**"; the owner log adds a second family "only by a new Owner answer"; the delegation never overrides a FROZEN record and never invents an Owner statement. Every option's cost, the recommendation's reasons and a disclosure are below ("P2 in full") | Pierce signs any Q18 line, at sitting 2 or later; the interim restriction then lapses. Nothing sealed or practised exists to unwind |
| P3 | 2026-10-23 | D0_BRIEF Q17 = OWNER-QUEUE A05, with X2 Q6 and CC Q6: may the local Qwen3 hold the "different family" roles? Needed by: the planted corpus (W1–W2); X4 batch (b) (W4–W6); X2's Prover (W4–W8); CC's reviewers (W8–W11). S71 has not run, so no Qwen3 role can start before sitting 2 | QWEN3_LOCAL_PROVISIONAL; QWEN3_LOCAL_FULL; UNMET | **Not delegable** (OWNER-ANSWERS, Consequences: a second family "can be added only by a new Owner answer"). Operating status until Pierce signs Q17: **UNMET**, the log's own default under R2. Recommendation for sitting 2: QWEN3_LOCAL_PROVISIONAL, with X2's kill clock not waiting for the Qwen3 review (its verdict carries the review's label) and CC's X1-subset freeze on R-same plus R-local reviews. **Interim restriction (adoptable):** until then Qwen3 does only S71 (serving and tok/s), within R2's pilot terms (P13) | D0_BRIEF §0: any other role for Qwen3 "is a new decision, not a reading of this answer"; ROADMAP §11 keeps D0-10 with Pierce; a delegated row is not an Owner statement. Why the recommendation: ROADMAP §3.3, §3.5 and §3.6 ask for "a different family", and Qwen3 is one. Every pass resting only on Qwen3 stays provisional (`pass_local_family`), while a kill or a flaw found stays binding, stricter than ROADMAP's letter. FULL counts passes from a weaker reviewer outright. UNMET leaves CC's gate and X4's batch (b) unpassable at M0. QWEN3_LOCAL_PROVISIONAL is the brief's and the queue's [G] recommendation (D0_BRIEF Q17; OWNER-QUEUE A05), not a registered default: the log's default under R2 is UNMET | Pierce signs any Q17 line. Under UNMET the roles stay open. Under either QWEN3 option, Qwen3 role work starts then, within the weekly cap he signs (P13) |
| P4 | 2026-10-23 | D0-10c's Value "local model" (sitting-1 PACKET item 2; PLAN Q10; S71). Needed by: S71 (Qwen3 serving and tok/s) and every Qwen3 job | Qwen3-30B-A3B Q4, the existing `.hearth` file; another Qwen3 checkpoint | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Operating assumption: Qwen3-30B-A3B Q4, the file on the desktop's 990 PRO that R8 (C02) names for timing runs, opened read-only. S71 records its path and SHA-256 in daytime. The D0-10c Value line is Pierce's to fill | It is the only Qwen3 with measured Hearth figures [R11], and the sitting-1 packet's suggested Value. Pierce already chose that file for timing runs (R8). Nothing new is installed on his machine | Pierce names another checkpoint in his D0-10c Value. The Qwen3 measurements are then redone on it |
| P5 | 2026-10-23 | OWNER-QUEUE A07 residual (PLAN Q4; S22, S23; R23): may a portable LLVM and a C compiler follow on the laptop? Needed by: X1's sandboxed checks; X3's clang-cl arm | yes: user-level portable installs; no: builds in WSL on the desktop | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Yes: official portable archives only, in `C:\Users\Pierce Lonergan\tools\` or the existing `.rustup-mithril` and `.cargo-mithril`. Each is hash- or signature-verified and recorded, with no installer and no PATH or registry edit | Registered default yes (PLAN Q4). The confirmation part is [M, queue track, 2026-10-23]: rustc 1.99.1 and stable (GNU host) are under `C:\Users\Pierce Lonergan\.rustup-mithril\toolchains`; the user PATH has no cargo, rustup or tools entry; no user RUSTUP_HOME or CARGO_HOME is set. User-directory files change no system setting | Delete the tool directories. Nothing else was changed |
| P6 | 2026-10-23 | D0_BRIEF Q13 = OWNER-QUEUE A16: what orders the review queue? Needed by: every agenda | UNBLOCK_FIRST; EVIDENCE_GRADE | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** UNBLOCK_FIRST orders the review queue and the sitting agendas. The Q13 line stays for Pierce | Registered [G] default; OWNER-QUEUE is already ordered that way. It orders work and sets no threshold | Pierce ticks EVIDENCE_GRADE. Agendas are then re-ordered |
| P7 | 2026-10-23 | OWNER-QUEUE A17 (i) and (ii), the residual of D0-10d (PLAN Q1, Q12, §6.3). Needed by: the X4-noise-pilot freeze, which must come before σ_d is known | (i) PLAN §6.3's rule with R5's floor of 4 and cap of 7, or another rule; (ii) a 25% contingency, or another | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** (i) PLAN §6.3's rule, bounded to 4–7 nights a week; (ii) a 25% contingency. Both go into the X4-noise-pilot draft before freeze. The rate it gives after the pilot is re-signed by Pierce (R5). The first night is not chosen here | Registered default (OWNER-QUEUE A17; PLAN Q12). The rule sets nights only inside the 4–7 band Pierce chose, and the contingency can only add nights. Fixing both before σ_d keeps them pre-data | Pierce signs a different rule or contingency before the pilot's σ_d is known. After that, any change is post-data, and only a stricter one is allowed |
| P8 | 2026-10-23 | OWNER-QUEUE B01 (PLAN Q7, §3.8): how the M0 verdict is composed. Needed by: `prereg/M0-verdict.md`, which must be FROZEN and SIGNED before any experiment's gate verdict, X0's re-run among them | PLAN §3.8 as written; other readings (for example, amber counts as pass) | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** PLAN §3.8 as written: every applicable row is reported; the most severe class governs; an X1 or X3 that is not `pass` cannot satisfy the "X2 alone" clause; pending states block the verdict except X4 "waits", `pass_one_family` and `pass_local_family`. **One added line** (P28): X2's state set gains `gate_missed`, and the mapping adds `if X2 == gate_missed: rows += NARROW (X2: failing variants stay tested)`, so a missed X2 gate always appears in the verdict. Drafted into the record; Pierce signs it | Registered default, plus one line that only adds a row. Not a loosening. Without the line, a missed X2 gate would produce no row: §3.8 reads narrowing only for X0, and a gate miss is neither pending nor a kill (review 1, finding 7). The `pass_one_family` handling is what X1-amendment-1 §3 (FROZEN, signed) already says. X0's census-run-1 previews (ambers (a) and (b)) are known [D, X0 REPORT]. The mapping reads only X0's narrowing, which is judged at week 6, so the previews cannot shape it [inference] | Pierce signs another composition before the record freezes. After the freeze, only by an amendment before any verdict is mapped |
| P9 | 2026-10-23 | OWNER-QUEUE B02 (X2 Q4; TABLE-SCHEMA Q2): do MXCSR flag disagreements count as mismatches? Needed by: the X2-fuzz freeze | yes, per execution; values only | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Yes, per execution | Registered default; the stricter option | Pierce answers "values only" before X2-fuzz freezes |
| P10 | 2026-10-23 | OWNER-QUEUE B03 (X2 Q5; FUZZ-DESIGN §6.2): pre-register the second-oracle fallback? Needed by: the X2-fuzz freeze | sign the fallback with the record; don't (then any switch is a deviation) | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Pre-register it in X2-fuzz: a switch to SoftFloat-direct plus a probed SDE by week 3 | Registered default. It fixes the switch rule before data, instead of leaving it to a post-data deviation. No threshold moves | Removed from the draft before X2-fuzz freezes |
| P11 | 2026-10-23 | OWNER-QUEUE B04 (X3 D§14 Q1): H, the denominator of "schedule ≤ 30% of hand-written lines". Needed by: the X3 track's first schedule line (W1 start, Fri 10-23) | H = 303 (SIMD-only closure); H = 369 (with the scalar closure) | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** H = 303, with shared helpers counted once per file (the closure rule) | Registered strict default. The smaller denominator makes "≤ 30%" harder to meet. Adopting the strict default after schedule lines exist moves nothing in the favourable direction | Schedule lines exist since 2026-10-23 09:09 PT [M, file times of `experiments/x3-generator/proto/x3gen/hearth/schedules/` `avx2.py`, `avx512.py` and `scalar.py`, 59 lines in all]. A change to 369 would now be post-data and favourable, so it is not allowed. H = 303 stands unless Pierce signs a stricter rule |
| P12 | 2026-10-23 | OWNER-QUEUE B05 (X3 D§14 Q13): x3gen or Exo. Needed by: W1 | x3gen; Exo's DAG-preserving subset | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** x3gen | Registered default. Exo has no IEEE-exact mode [R05] | Reversible until T0 |
| P13 | 2026-10-23 | OWNER-QUEUE B06 (PLAN Q18; R30): the local Qwen3's share of the 8 daytime threads, and its hours. Needed by: S71 and the first Qwen3 job | R2's 5–10 desktop hours until a weekly cap Pierce signs; a weekly share set by the lead engineer; all 8 outside X2's fuzz runs; an exception to the cap (Pierce only) | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** No exception to the 8-thread cap. **Until Pierce signs a weekly Qwen3 cap** (PLAN Q18; sitting 2), all Qwen3 jobs together stay within R2's 5–10 desktop hours: daytime only, CPU only, through the job wrapper, never in a window. S71 runs first. From its measured tok/s and the model's measured RAM footprint, the lead engineer proposes a weekly cap for Pierce's signature, lower in X2's fuzz weeks. Each week's Qwen3 hours are logged in COST | Registered default (no exception; re-estimate first). R2 approved "about 5–10 desktop hours, daytime only"; any wider Qwen3 use is a new Owner answer (Q17, Q18), and its size is his to cap (D0_BRIEF Q17: "or you sign a weekly cap on Qwen3 hours instead"; COST §5's alert reads "the share Pierce agreed"). The 8-thread cap bounds threads, not the RAM or memory bandwidth a 30B Q4 model takes over hundreds of hours on the desktop he uses himself [inference]. A cap exception would change a coexistence rule, so it is not proposed | Pierce signs a cap at any sitting; the interim bound then lapses |
| P14 | 2026-10-23 | OWNER-QUEUE B07 (TABLE-SCHEMA Q1): may the X2 table use Intel's intrinsics XML? Needed by: the census-union entries (W1) | SDM-only; XML-assisted | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** SDM-only | Provisional default. It avoids the open licence question (G02, open question 2) | Switch before the census-union entries are written |
| P15 | 2026-10-23 | OWNER-QUEUE B08 (PLAN Q13): is a weekly total per track enough for owner-hour logging? Needed by: the next weekly snapshot | yes; finer | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** A weekly total per track is what COST asks of Pierce | Registered default. It is the lightest request on his time and sets nothing | Pierce asks for finer logging, or logs nothing; COST then marks his hours "not logged" |
| P16 | 2026-10-23 | OWNER-QUEUE B09 (CC Q9; X1 DESIGN §9): should `mithi` accept `par for`, `deterministic`, `schedule`, `spec` and `linear` typing-only? Needed by: `mithi`'s scope (W1–W2); X1-precondition freeze (W8) at the latest | typing-only; keep `E-X1-NOTYET`; change the gate (a ROADMAP §3.6 loosening) | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Typing-only: `mithi` accepts and type-checks these forms without executing them | CC's recommendation. It lets ROADMAP §3.6's "accepted by `mithi`" be met as written. Keeping `E-X1-NOTYET` makes the gate unpassable. Changing the gate is a loosening, so it is excluded | Before the X1-precondition freeze |
| P17 | 2026-10-23 | OWNER-QUEUE B11 (X1 Q21): one planted corpus or two halves? Needed by: planted-corpus authoring | a dev half and a sealed confirmation half, ≥ 100 each; one corpus ≥ 100 | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Two halves, ≥ 100 items each | Registered default; stricter than ROADMAP's minimum, because P-2 cannot be passed by iterating on its own test set | Before planted-corpus authoring |
| P18 | 2026-10-23 | OWNER-QUEUE B12 (X1 Q11 host; PLAN §6.1): where X1's sandboxed `check` and oracle runs execute. Needed by: the smoke run's sandboxed checks | the laptop; desktop WSL2 in daytime; a rented Linux VM (paid, so excluded under R1) | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** The laptop, within the laptop's 8-thread job limit | Registered [G] default. It keeps X1's sandboxes off the desktop's shared cap and out of the quiet windows | Move to desktop WSL2 in daytime under the cap before the X1 freeze |
| P19 | 2026-10-23 | OWNER-QUEUE B13 (PLAN C0; X4 S13): approve the desktop job-wrapper design? Needed by: W1 | approve; change | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Approve: an 8-token aggregate semaphore, refusal inside quiet windows, start and end stamps | Registered default. It enforces the coexistence rules | Redesign at any time, only in the stricter direction |
| P20 | 2026-10-23 | OWNER-QUEUE C03 (PLAN Q17; X3 D§14 Q7): the stand-in for `hearth-c-ref`. Needed by: the reference binary (W2–W3) | a clean `b5d3f14`, built with MSVC and clang-cl on D:, hashes pinned; wait for S0's tag | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** A clean `b5d3f14` stand-in, built on D:. A re-pin happens only by a pre-data amendment that re-measures H | Registered default. S0 has no date. It reads only the public Hearth commit; Pierce's Hearth working tree is not touched | A pre-data amendment |
| P21 | 2026-10-23 | OWNER-QUEUE C05, the stopping-rule part (X4 Q1, Q9; PLAN Q15). Needed by: the X4-calibration rules freeze (before the first pilot night) | end-to-end A/A to N, or to the first non-inferiority pass; microbenchmark A/A to N or to 2N | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** End-to-end and microbenchmark A/A sessions run to N (the registered default). The microbenchmark 2N horizon (+13.3 h at σ_d = 2%, +48.9 h at 4% [D, X4 Q9]) goes to Pierce at sitting 2 as his option, beside C05's ROADMAP §10 revision | Registered default (the X4 record, the later and more detailed source; OWNER-QUEUE C05: "A/A to N, not 2N"). Stopping at the first pass can bias σ̂_d low, which weakens the calibration. 2N would add quiet-window hours on Pierce's desktop nights, with GEMS kept out, against ROADMAP §10's M0 quiet-hour line, which X4 already exceeds and whose revision is his. A 2N whose trigger a track settles later would not be fully pre-registered (row test 4) | Changed before the X4-calibration rules freeze; Pierce may sign 2N then |
| P22 | 2026-10-23 | OWNER-QUEUE C06 (X4 Q3): the ≤ 2/100 A/A rule | confirm ROADMAP's rule; tighten before data | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Confirm | It is ROADMAP's own rule [target] | Tighten before data only |
| P23 | 2026-10-23 | OWNER-QUEUE C07 (X4 Q4; 06 §6.2): the run-level R scorer and a pooled tail check. Needed by: the X4-calibration rules freeze | confirm both; keep 06 §6.2 literally | **Not delegable.** It amends normative 06 §6.2, which governs every milestone, not only M0, and X4's owner question 4 is addressed to the Owner ("Confirm, or amend 06"). Recommendation for sitting 2: confirm both (X4's provisional default). The X4-calibration rules do not freeze on this point until he answers | X4's numbers [S]: under 06's literal block clip a true 20% improvement never reaches e = 20 within 400 blocks; the R scorer cuts the tail credit a rare-stall candidate can earn from 0.130 to 0.017 (literal check: 0.110). No ROADMAP threshold moves (e ≥ 20; ≤ 2/100). The change moves both ways: it makes superiority reachable, a loosening for superiority claims, and tightens tail credit. So it fails row tests 3 and 4 | Pierce answers at sitting 2, before the calibration rules freeze (OWNER-QUEUE sitting-2 list, item 4) |
| P24 | 2026-10-23 | OWNER-QUEUE C08 (X4 Q5): may X4's kill e-process continue across the two N-sessions of an unchanged binary? | yes; another rule | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Yes | Registered default. It makes a confirmed regression reachable (0.992 within 2N against 0.048 within N at σ_d = 2% [S]), so it moves toward a kill, not away from one | Before the calibration rules freeze |
| P25 | 2026-10-23 | OWNER-QUEUE C09 (X4 Q6): if the pilot gives P(NI within N at parity) < 0.8, revise N, the clip rule and the throughput figures? | yes: fix the rule now, act before M4; no | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Yes: the rule is fixed now. Any revision it triggers is a new record that Pierce signs | Registered default. The trigger is fixed pre-data | Before the calibration rules freeze |
| P26 | 2026-10-23 | OWNER-QUEUE C11 (PLAN Q20): gated catalogue run before or after the kit hash-freeze? Needed by: the X4-hacks-catalogue freeze (W2) | after; before | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** After: engineering runs, then the freeze, then the gated run, in which a miss is HALT-F | Registered default. A miss on the frozen kit is binding | Before the catalogue freeze |
| P27 | 2026-10-23 | OWNER-QUEUE C12 = D0-7x with D0_BRIEF Q6 (operating assumption only): may F1-sim run unattended in the daytime? Needed by: any unattended F1-sim (W2) | ROADMAP literal: F1-sim attended; DAYSIM: a loosening only Pierce can grant | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Operating assumption: ROADMAP literal. No unattended F1-sim runs. The D0-7x and Q6 lines stay for Pierce | The recommended option and ROADMAP §11's wording. It needs no new permission. DAYSIM is a loosening, so it is excluded | Pierce ticks DAYSIM. Unattended daytime F1-sim may then start |
| P28 | 2026-10-23 | OWNER-QUEUE C13 (X2 pre-freeze Q1): the written action if no kill holds but the gate is missed at week 6. Needed by: the X2-gate rules freeze (W2) | a `gate_missed` state: the failing variants stay `tested`, no extension, reported as a NARROW row; another written action | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** X2's state **`gate_missed`**: at the end of week 6 (or of the amber week), P1 < 8 or P3 < 100% or P5 > 0, with P2a ≤ 30, while no kill condition holds (X2 record §8). The failing variants stay `tested`, with no extension. A `gate_missed` X2 never satisfies any clause that reads X2 = pass, and the M0-verdict mapping reports it as a NARROW row (P8). Pierce signs both, in the X2-gate and M0-verdict records | No record default: the X2 record flags this band for the Owner (§8; pre-freeze question 1), and ROADMAP §1 rule 2 needs a written action before freeze. This action grants no extra time, and the NARROW row keeps the miss in the verdict. "Narrow" alone would have left no row, because PLAN §3.8 reads narrowing only for X0 and a narrowed X2 is not pending (review 1, finding 7). He sees it as its own line in the X2-gate record (OWNER-QUEUE sitting-2 list, item 12) | Before the X2-gate rules freeze; Pierce may sign another written action in that record |
| P29 | 2026-10-23 | OWNER-QUEUE C14 (X2 Q2): does a false accept from a fixable matcher or lifter bug kill X2? | keep ROADMAP's text (strict); excuse it if a fresh blind pool is fully rejected | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Keep the text | Registered strict default | Before the X2-gate rules freeze |
| P30 | 2026-10-23 | OWNER-QUEUE C15 (X2 Q3; TABLE-SCHEMA Q3): do the F16 and BF16 variants gate P1? | secondary; gate | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Secondary. Their mutants still count in P3 (P31) | ROADMAP names Q4, Q8, F32 and act-q8. Gating more variants would add requirements ROADMAP does not state; keeping them secondary loosens nothing | Before the X2-gate rules freeze |
| P31 | 2026-10-23 | OWNER-QUEUE C16 (X2 Q8; MUTANTS §1, §6): which mutants enter P3's denominator? | (b) every host joins T1; (a) gating hosts only (removes a ROADMAP mutant class, a loosening) | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** (b) | Registered strict default. (a) is excluded | Before the X2-gate rules freeze |
| P32 | 2026-10-23 | OWNER-QUEUE C17 (X2 Q9; RULES RQ-1): how many rules do the loop rules count toward ≤ 30? | 1; 0 (looser); 7 (strictest) | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** 1: LOCKSTEP and its extensions are lemmas of one proof | The record's registered default. ROADMAP does not say how loop rules count, so 1 loosens no ROADMAP threshold. 0 is excluded as looser. 7 is stricter, and the lead engineer may choose it instead | Before the X2-gate rules freeze |
| P33 | 2026-10-23 | OWNER-QUEUE C18 (X2 Q10; RULES RQ-2): do integer identities count as rule rows? | yes, each instance (7 rows); no | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Yes, each instance | Registered strict default | Before the X2-gate rules freeze |
| P34 | 2026-10-23 | OWNER-QUEUE C19 (X2 Q11; RULES RQ-3): does a Z3 QF_BV proof alone satisfy "Z3 FPA or exhaustive binary32" for integer rows? | only with an agreeing exhaustive or second-solver route; alone | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Only with an agreeing route | Registered strict default | Before the X2-gate rules freeze |
| P35 | 2026-10-23 | OWNER-QUEUE C21 (X3 D§14 Q2): are the scalar variants confirmatory? | yes; screening-only | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Yes | ROADMAP §3.4 says "per ISA". The stricter option | Before the X3-parity rules freeze |
| P36 | 2026-10-23 | OWNER-QUEUE C22 (X3 D§14 Q3; D§15): the bands ROADMAP §3.4 leaves undefined | as the X3 design proposes; others | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** As proposed in X3 DESIGN §14 Q3 | ROADMAP §1 rule 2 requires every band to be defined, and §3.4 leaves these undefined. The proposal moves no ROADMAP threshold, and "no admissible variant at window close" counts as < 90% (kill (a)) | Before the X3-parity rules freeze |
| P37 | 2026-10-23 | OWNER-QUEUE C23 (X3 D§14 Q4): the kill confirmation level | 1/20 per configuration; Bonferroni 1/240 (makes kills rarer: a loosening) | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** 1/20 per configuration | Registered. Bonferroni is excluded | Before the X3-parity rules freeze |
| P38 | 2026-10-23 | OWNER-QUEUE C24 (X3 D§14 Q5; D§15): which margin boundary is canonical? Needed by: the X4-calibration rules | log(1.03); ratio < 0.97 | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** log(1.03) | The stricter boundary | Before the calibration rules freeze |
| P39 | 2026-10-23 | OWNER-QUEUE C26 (X3 D§14 Q8): the confirmatory clang-cl arm's flags | X0's config B lines plus a shared `-mavx512vnni`, and `/clang:-ffp-contract=off` only if arm A fails §7 step 4; B-gnu as confirmatory | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** The first | Registered. It is closest to what CMake gives clang-cl, and it changes no threshold | Before the X3-parity rules freeze |
| P40 | 2026-10-23 | OWNER-QUEUE C27 (X3 D§14 Q9): the length of the bounded tuning window | 7 days [target]; other | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** 7 days | Registered. ROADMAP §1 rule 4 says only "bounded". A longer window would favour a pass, so only a shorter one could replace it | Before the X3-parity rules freeze, shorter only |
| P41 | 2026-10-23 | OWNER-QUEUE C28 (X3 D§14 Q12): include bit-identity under WSL2 Linux Clang in the gate? | yes; no | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Yes | A tightening | — |
| P42 | 2026-10-23 | OWNER-QUEUE C31 (X3 D§14 Q17): α across the two attempts of the inconclusive path | carry wealth forward, threshold 20; split α (threshold 40 each) | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Carry wealth forward | Registered. The false-pass bound per configuration stays 1/20. The claim it supports, "at least one evaluated variant is non-inferior", is the one REPORT states | Before the X3-parity rules freeze |
| P43 | 2026-10-23 | OWNER-QUEUE C32 (X3 D§14 Q18): the regression estimand | clamps centred on each boundary; another estimand | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Centred clamps | Registered. It keeps a kill reachable within N | Before the X3-parity rules freeze |
| P44 | 2026-10-23 | OWNER-QUEUE C33 (CC Q3): which allocation rule X1 uses. Needed by: the Tier 0 card freeze | C-ALLOC (`alloc(Global)`); a label-free global heap; arena-only tasks | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** C-ALLOC | Registered provisional default. A label-free heap would let policies allocate unless T0 forbids it | Before the Tier 0 freeze |
| P45 | 2026-10-23 | OWNER-QUEUE C34 (CC Q7): the two meanings of "abandon" | rename the trap-path release; rename the agent verb; keep both | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Rename the trap-path release. The agent verb keeps its 05 §10 name | The note gives no default; this is the queue's [G] suggestion, a documented choice. It is a naming choice that keeps the published protocol verb stable | Before the Tier 0 freeze |
| P46 | 2026-10-23 | OWNER-QUEUE C35 (X1 Q9): does `mithi`'s hole report reach the three Mithril arms? Needed by: card design (W3) | yes; the tooling arm only | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Yes | Registered recommendation, for symmetry with the tooling arm. It moves no threshold. It helps the Mithril arms, so it leans toward a pass. Under R4 a pass is provisional anyway, and a kill observed despite the help stays credible | Before card design |
| P47 | 2026-10-23 | OWNER-QUEUE C36 (X1 Q19): the obfuscation scope | the record's wider scope; keywords and primitive types only (ROADMAP's minimum) | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** The wider scope | Stricter than ROADMAP's minimum | Before the card freeze |
| P48 | 2026-10-23 | OWNER-QUEUE C37 (X1 Q20): `topk` parity | give `topk` to the Rust and C11 helper packs; remove it from `mithi`'s X1 std | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Give it to all packs | Registered. Either option keeps the arms at parity | Before the helper packs are frozen |
| P49 | 2026-10-23 | OWNER-QUEUE D03 (X1 Q7, Q14): should ROADMAP §3.2 state R-CABW and R-JOINT? | the record binds them regardless; amend ROADMAP §3.2 | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** The record binds them. The ROADMAP edit goes to Pierce's ROADMAP-amendment sitting | The stricter requirements bind either way | — |
| P50 | 2026-10-23 | OWNER-QUEUE D04 (X1 Q8): `agent.hole_use_floor` = 0.10 and `agent.dc_rate_bound` = 0.10. Needed by: the X1-heldout rules (W5) | accept [G]; other values | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Accept | Registered [G]. They are trigger parameters for DR-003 to DR-005, not gate thresholds | Before the X1-heldout rules freeze |
| P51 | 2026-10-23 | OWNER-QUEUE D05 (X1 Q15): should SE(Γ̂) > 3.90 points make the result UNDERPOWERED? | not adopted (reported only); adopt | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Keep it not adopted, the registered state | Adopting it would void the run, so no kill and no pass, in 0.05–0.14 of high-variance worlds at n = 96 [S, X1 record Q15], whatever K1 or K2 would have said. That is a path by which a kill could be avoided. Under R4, keeping the kill reachable is the side that loosens nothing | Pierce adopts it before the X1-heldout rules freeze |
| P52 | 2026-10-23 | OWNER-QUEUE D06 (X1 Q16): the interval convention | two-sided 90% with `.ci_level` and `.ci_sides` facts (X1); one-sided 90% (05 §13's M1 CABW test); a DECISIONS-wide convention | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** X1 publishes two-sided 90% intervals with the level facts. A convention for DECISIONS and 06 §7.2 stays with Pierce | Registered for X1. Changing DECISIONS is an AUTHORITY act | — |
| P53 | 2026-10-23 | OWNER-QUEUE D09 (X1 Q13): the canary UUID at freeze | publish (DESIGN §4.4); keep private | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Publish | Registered. It lets corpus builders filter X1 content, and it reveals no sealed content. Whether the repository is public is part of A06 | Before the X1 freeze |
| P54 | 2026-10-23 | OWNER-QUEUE D10 (X1 Q12): the pilot's task family | T-ROUTE; another | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** T-ROUTE | Registered provisional default | Before the X1-local-pilot freeze |
| P55 | 2026-10-23 | OWNER-QUEUE D12 (X4 Q2; TOMBSTONES §4.1): the trigger grammar and hyphenated IDs | quote invariant IDs as strings; add a hyphenated identifier class | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Quoted strings, with no grammar change | The queue's [G] suggestion; X4 gives no default. It changes no meaning | Before the X4-tombstone-replay freeze |
| P56 | 2026-10-23 | OWNER-QUEUE D14 (CC Q5): may a frozen prelude of declarations be input to "accepted by `mithi`"? | yes; no | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Yes, provided the prelude is frozen with the CC-gate record before the check and is itself accepted by `mithi` | The queue's [G] default, with a tightening so that the prelude cannot hide an unchecked declaration | Before the CC-gate freeze |
| P57 | 2026-10-23 | OWNER-QUEUE D15 (CC Q10): the six derived snippets outside X1's scope | agreement on `E-OUT-OF-SCOPE-<KW>` (the note's reading); `mithi` types them; exclude them (a loosening of §3.2) | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** The note's reading | Registered. ROADMAP §3.2 asks for agreement with the note's derivations, which this keeps. Exclusion is excluded | Before the X1-precondition freeze |
| P58 | 2026-10-23 | OWNER-QUEUE D16 (CC Q11): should the review's counterexamples (N-11 to N-39) become gate items? | no, supplementary; yes | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Supplementary, offered to the planted corpus | ROADMAP §3.2's requirements as written | Before the X1-precondition freeze |
| P59 | 2026-10-23 | OWNER-QUEUE D17 (CC Q1): what a policy trap falls back to | the port's declared fallback (the note's reading); another | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** The note's reading | Registered. It is a semantic reading of ROADMAP §3.6's "falls back to the default policy", with no threshold | Before the CC freeze |
| P60 | 2026-10-23 | OWNER-QUEUE D18 (CC Q8): `debug_assert!` | always checked (C-MACROS); release-only | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Always checked | The stricter option | — |
| P61 | 2026-10-23 | OWNER-QUEUE D19 (CC Q2): make F-tot, P-ind, S-tot and A-ind named obligations of the store-core certificate? | yes; no | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Yes | It adds obligations, so it is stricter | — |
| P62 | 2026-10-23 | OWNER-QUEUE D20 (X2 Q12): may X2 certify `b5d3f14` under the declared precondition "MXCSR = 0x1F80 at entry" before D0-5b lands? | yes, with the precondition in every certificate; require D0-5b first | **ADOPTED 2026-10-23 (lead engineer, under the batch-4 delegation; review at sitting 2).** Yes, with the precondition stated in every certificate | Registered. D0-5b is a Hearth decision (Pierce's). The certificate claims no more than its precondition | Before the X2 verdict |

### P2 in full: who writes X1's templates (D0_BRIEF Q18, OWNER-QUEUE A04)

*Revised 2026-10-23 after review 1 (findings 1–3, 10 and 11). The first draft of this row adopted reading (i)
below and GEN_QWEN3 as a working choice. Both are withdrawn: the row now gives Pierce every option with its cost,
then a recommendation, and changes nothing until he signs.*

**What Pierce wrote, verbatim** ([OWNER-ANSWERS.md](OWNER-ANSWERS.md)):
- Batch 2, the X1 rule: "Claude kills; pass provisional (Recommended)". The option text he saw ends: "Claude also
  edits the card, which biases toward passing, so a kill is the more trustworthy signal. Sealed items are
  generated from templates with deterministic oracles, so no model writes them."
- Batch 1, D0-10c: "Local Qwen3 via Hearth". Option text: "The pilot the ROADMAP plans: 60 attempts, about 5–10
  desktop hours, daytime only, reported but not part of the kill. Uses only the desktop CPU, never the GPU."
- Batch 4: "Do whatever YOU need to do to make this project work. you have my full written permission to ratify
  any conflicting statements."

**The question.** The last sentence of the X1 rule can be read two ways.
- **(i) Literal.** "Them" is "sealed items". Items are instantiated by a deterministic generator, so no model
  writes an item, whoever writes the templates. All three GEN options satisfy (i).
- **(ii) Substantive.** This is the caution of D0_BRIEF Q18 and X1-amendment-1 §5.3: the template carries the
  authorship and the item-level variance, so "no model writes them" should also cover the templates. Only
  GEN_OWNER satisfies (ii).

**Why the choice is not delegable.**
- **The FROZEN, signed X1-amendment-1 reserves it.** §5.3: "If Pierce reads his text as 'no model writes an
  *item*' (items are generated from templates), GEN_QWEN3 and GEN_CLAUDE also fit it. That reading is his to
  adopt, not this record's." Then: "**No recommendation**" and "**The choice is Pierce's.**" Its table marks
  GEN_QWEN3 "Needs a new Owner answer beyond R1–R6: **yes**: extends R2's pilot-only role". The delegation never
  overrides a FROZEN record and never invents an Owner statement.
- **The owner log and ROADMAP reserve it.** A second family "can be added only by a new Owner answer"
  (OWNER-ANSWERS, Consequences). Any other role for Qwen3, the template author included, "is a new decision, not a
  reading of this answer" (D0_BRIEF §0, D0-10c). ROADMAP §11: "No agent may take these decisions."
- **It is not a conflict between Pierce's statements**, which is what batch 4 lets the lead engineer ratify.
  Under reading (ii), GEN_OWNER needs 84–302 owner hours (X1-amendment-1 §5.3, [inference]): 1.5–5.5 times
  ROADMAP's whole X1 owner line of ~55 h, and 5.6–20.1 weeks of all his hours at 15 h a week [D,
  `scratchpad/queue/calc_queue.py`]; X1's verdict would move to ≈ W15–W32 [G, X1 record option 3]. But 15 h a
  week is Plan B's planning assumption, not his statement: D0-10b's H is open (OWNER-QUEUE A15). The tension is
  between his words and a plan figure, and only he can resolve it: by his hours, his reading or his choice.
- **Nothing needs Q18 before sitting 2** (Sun 10-25). Sealed authoring also needs A06's store, which is his own
  setup, and §6.2 = RUNNABLE, whose smoke run waits for a time he agrees (OWNER-QUEUE sitting-2 list, items 7
  and 8; PLAN S70). So row test 2 is not met either.

**Test 1: does each option keep the X1 kill credible?** R4's own argument is that the known bias runs toward a
pass, so a kill is the trustworthy signal. A kill stays credible as long as nothing in the items biases them
toward Rust, against Mithril, by a comparable amount. The template author matters here.
- **GEN_CLAUDE: outside the delegation in any case, because it loosens 05 §13** (a labelled loosening only
  Pierce can grant: D0_BRIEF §0 and Q18; X1-amendment-1 §5.3). Its main bias runs **toward PASS**: card editor,
  author and participant share priors, so items fit what Claude-in-Mithril does well; the provisional-pass rule
  already discounts a pass, so a kill stays credible (§5.3). For the kill it carries **one unmeasured
  mechanism toward a kill**: "an author family that is also the participant family gives Claude an edge in
  whichever language the author thinks in natively, usually Rust" (§5.3). Neither effect is measured; a kill
  under GEN_CLAUDE is reported with that label.
- **GEN_QWEN3: no known systematic bias toward either arm; one unmeasured residual toward a kill (brief
  quality).** Qwen3 is not a kill-carrying participant. It is the local pilot's participant (outside the kill)
  and sees the card there: the pilot draws 10 T-ROUTE held-out items and runs Mithril and Rust arms (X1 record
  §6.6). The pilot runs after the frontier held-out run, so every template is sealed before any Qwen3 session
  sees the card. The pilot's items are then author = participant, and REPORT.md says so. Whether that meets
  §5.2's "Template authors never see the card", read per family rather than per session, is part of what Pierce
  weighs. "A different family's idioms are equally foreign to Claude in both arms" (§5.3). The X1 record, option
  4b: "Author bias is removed, because the template author (the Owner or Qwen3) is not a participant." Its
  weakness is quality: a non-frontier model writing bit-exact oracle models. The mechanical gates turn most
  quality failures into rejected drafts rather than biased items:
  - every template's Rust and C11 references must pass its oracle;
  - the oracle must kill ≥ 95% of mutants;
  - the Mithril reference comes from a deterministic transliterator, and a template whose transliteration
    fails is rejected and replaced, never hand-patched by a model (§5.1).

  The residual risk is that a weaker author writes briefs whose ambiguity costs the less familiar Mithril arm
  more than the Rust arm [inference]. Its only listed mitigation, the owner sample review (OWNER-QUEUE C38), is
  class B and unanswered, so **today it is unmitigated**. REPORT.md names the template author on every X1
  verdict.
- **GEN_OWNER: none systematic toward either arm** ("Pierce's Rust-first habits shape briefs, as any author's
  would", §5.3). A human author shares no model priors with the card editor or the participant: the strongest
  independence (X1 record, option 3).

**Test 2: is each option feasible inside M0?**
- **GEN_OWNER.** ≤ 1 held-out item per template: 84–302 owner hours [inference], 5.6–20.1 weeks of all his
  hours at 15 h a week [D]. 2–3 per template at n = 160: 42–171 h [inference, §5.3], 2.8–11.4 weeks [D],
  subject to the §6.3 recompute (item 6 below). Only Pierce can commit these hours.
- **GEN_CLAUDE: poor.** It needs 22–197 M plan tokens, 0.31–3.39 weekly windows (§5.3). That comes on top of X1's
  attempts, which §6.1 estimates at 13–55 windows at n = 136 [D, rough]. Pierce signed effort `max`, and effort
  changes the tokens per attempt (§2.1). The plan is already the binding constraint.
- **GEN_QWEN3: unmeasured; feasible only conditionally.** It needs 54–374 daytime desktop hours for X1's Qwen3
  work in all (§5.3, [D from G]; 33–225 h at 2–3 per template), inside the 8-thread cap and never in a window,
  shared with X2's fuzzing, X0's re-runs and X3's builds. Qwen3's tok/s under 8 threads is not measured (PLAN
  S71). The capacity it would take [D, `calc_queue.py`]:
  - if "daytime" means any time outside a quiet window (PLAN §6.1), W1–W5 has 560–680 h
    [5 × (168 − 8 × 7) to 5 × (168 − 8 × 4)], and Qwen3 would take ≈ 8–67% of them;
  - under R2's literal "daytime only" (16 h a day), W1–W5 has 560 h, and the share is 9.6–66.7%;
  - sealed authoring cannot start in W1 (it needs sitting 2, A06's store and §6.2 RUNNABLE), so over W2–W5
    (448–544 h) the share is up to 83%.

  The low and middle of the range fit; the top end would crowd X2. Which meaning of "daytime" R2 carries is
  Pierce's to confirm.

QWEN3_ITEMS contradicts even the literal reading (a model writes the items). OWNER_ITEMS needs ≈ 230–460 owner
hours (D0_BRIEF Q18, at two families; not re-derived at one).

**What holds whatever he signs.** X1-amendment-1 §5.3 requires "that the template author be named by a signed
D0_BRIEF Q18 line before any sealed template exists". A delegated row is not his signature. So:
1. **Before Pierce signs a Q18 line** (in chat or with his key; sitting 2, Sun 10-25, at the earliest), nothing
   sealed is written and no Qwen3 template is authored, practice templates included.
2. **Allowed meanwhile (family-agnostic, development only):**
   - the generator and the transliterator;
   - Qwen3 serving and its tok/s under 8 threads, measured in daytime (PLAN S71), within R2's 5–10 desktop hours
     (P13).
3. **Only after a signed Q18 = GEN_QWEN3, and after §6.2 has returned RUNNABLE:** a small practice set of
   templates on public material (X1 DESIGN §5.2), to measure Qwen3's hours per accepted template and its
   rejection rate. Its hours count against the weekly Qwen3 cap he signs (P13). Practice templates are never
   sealed and never reused as items.
4. **Sealed authoring starts only when all of these hold:**
   - X1-amendment-1 §6.2's feasibility gate has said RUNNABLE;
   - Pierce's signed Q18 line exists;
   - the Gatekeeper store and the desktop account that no Claude session can read exist (OWNER-QUEUE A06,
     Pierce's own setup).
5. **A feasibility check, proposed for the X1 record before freeze [G], under GEN_QWEN3.** From the practice set,
   project Qwen3's hours for all templates. If the projection exceeds the signed weekly cap, or the daytime
   capacity left after X2's fuzz weeks by X1's sealing date, the lead engineer reports to Pierce. There is no
   fallback to another author without his signature.
6. **Held-out items per template.** At most one, as X1-amendment-1 §4.3 registers. Two or three per template
   are admissible only if the X1 record's §6.3 recompute returns n ≤ 160 (mid scenario: 128–160 [S]; high
   scenario at the step-4 rule: not simulated). Above 160, collection waits for a signed record that raises the
   cap. Choosing 2–3 is a change to the X1 record's §4.3 that Pierce signs.
7. **The label.** Under GEN_QWEN3, REPORT.md, and the `standalone_surface` tombstone if a kill fires, record the
   template author as the local Qwen3 (non-frontier), with the checkpoint of P4.

**For Pierce's signed Q18 line: every option, in X1-amendment-1 §5.3's order, then the recommendation.**
- **GEN_OWNER**: he writes the templates; it matches "no model writes them" on either reading. ≤ 1 per template:
  84–302 owner h, 5.6–20.1 weeks of all his hours at 15 h a week. 2–3 per template at n = 160: 42–171 owner h,
  2.8–11.4 weeks [inference, §5.3; D], subject to item 6. He then takes no part in card editing and signs the
  card hash only (C38).
- **GEN_QWEN3**: the local Qwen3 writes them. A new answer that extends R2 beyond the pilot. 54–374 daytime
  desktop h in all, or 33–225 h at 2–3 per template [D from G]; tok/s unmeasured (S71); the highest
  template-quality risk [inference]; his weekly Qwen3 cap (P13).
- **GEN_CLAUDE**: Claude writes them. A loosening of 05 §13 that only he can grant. 22–197 M plan tokens,
  0.31–3.39 weekly windows (11–112 M, 0.16–1.92 windows at 2–3 per template) [inference; D], on top of X1's
  attempts, which §6.1 finds do not fit the plan at today's estimate. Main bias toward PASS; one unmeasured
  counter-mechanism toward KILL.
- **QWEN3_ITEMS** and **OWNER_ITEMS**, as above.
- **OTHER [G, not simulated]: a split author.** He writes a seeded subset of the held-out templates and Qwen3
  writes the rest, with the author recorded per item, so that an author effect could be estimated. It still
  extends R2, and it needs a power check before he chooses it.
- **His review role (C38) belongs to this decision.** A seeded sample of 24 templates (≈ 4–8 h [G]), all
  held-out items (≈ 13–21 h), or none (required under GEN_OWNER). Under GEN_QWEN3 it is the only listed
  mitigation for brief quality.

**Recommendation (proposed by the queue track; the lead engineer's once adopted):** GEN_QWEN3, ≤ 1 held-out
item per template, with the C38 sample review. For it: the author is neither the kill-carrying participant nor
the card editor, so the binding kill does not rest on an author with a known bias, and its cost falls on desktop
hours under a cap he signs rather than on his own hours or on 05 §13. Against it: a model family writes the
templates, which departs from the text he accepted, and its feasibility and template quality are unmeasured.
**Disclosure:** X1-amendment-1 §11, review 1, finding 1 withdrew an earlier GEN_QWEN3 recommendation as framing;
this recommendation re-opens it under batch 4, and would be the lead engineer's, not a reading of R4. If Pierce prefers
reading (ii), he signs GEN_OWNER, at either template count, and X1's schedule is re-planned around his hours.

---

## Review log of the proposed rows

| Date | Reviewer | Family | Lens | Findings | Accepted | Rejected |
|---|---|---|---|---|---|---|
| 2026-10-23 | Reviewer 1 | Claude, same family, independent context | The delegation's limits against the FROZEN records and the owner log; fair presentation of options to Pierce; pre-registration of each rule (inferred from the findings; the lens name was not relayed) | 13 across DELEGATED, OWNER-QUEUE and D0_BRIEF: 1 blocker, 6 major, 6 minor | 13 (3 with a modified fix) | 0 |

The reviser (the queue track, a Claude agent, same family) checked every finding against the sources before
acting: X1-amendment-1 §4.3, §5.2, §5.3 and §11 (FROZEN at `ac751b8`); OWNER-ANSWERS (Consequences; batch 4); the
X1 record §6.6; the X2 record §8 and its pre-freeze question 1; the X4 record (line 55; owner questions 4 and 9;
review R2-6); PLAN §3.8, §6.1 and S71; COST §5; OWNER-QUEUE C05, C29 and C38; the X3 schedule files' times [M,
`ls --time-style=full-iso`, 2026-10-23]; and the arithmetic (`scratchpad/queue/calc_queue.py`, CPython `-I`,
< 1 s [M]).

**Accepted as proposed:** 1 (blocker: P2 took Q18; now not delegable, a recommendation with a disclosure, every
option listed first), 2 (GEN_CLAUDE's bias: toward PASS with one counter-mechanism; GEN_QWEN3's residual
unmitigated while C38 is open), 4 (P3: not delegable; UNMET until signed), 5 (P13: R2's 5–10 h until a signed
cap; practice set only after a signed GEN_QWEN3 and §6.2 RUNNABLE), 6 (P23: not delegable), 8 (P21: A/A to N;
2N to Pierce), 9 (P11: schedule lines exist), 10 (Qwen3 is the pilot's participant), 12 (Q5 open; OWNER-QUEUE
and D0_BRIEF), 13 (the default-on-lapse convention excludes class-B loosening defaults; OWNER-QUEUE).

**Accepted with a modified fix** (one line each):
- Finding 3 (2–3 per template): accepted; the added OTHER (split author) is labelled [G, not simulated] and also
  marked as extending R2, and the 2–3 option is noted as a change to the X1 record's §4.3 that Pierce signs.
- Finding 7 (X2 gate miss): of the two fixes offered, the second was taken: P28 defines `gate_missed` and P8 adds
  its NARROW line, so C13 stays C. The X2 record's own "the Owner decides" is met because Pierce signs the
  X2-gate record, and the sitting-3 list now names the line.
- Finding 11 (daytime capacity): accepted; the share under R2's literal reading is 9.6–66.7% (373.71 / 560 h,
  unrounded), and the W2–W5 share is up to 83% (373.71 / 448 h) [D].

**Rejected findings:** none.
