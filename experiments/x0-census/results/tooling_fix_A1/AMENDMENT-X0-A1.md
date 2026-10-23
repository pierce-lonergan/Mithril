## Amendment X0-A1 (post-data; a definition of §4.7's "non-escaping"; no threshold, bound or configuration change)

Date: 2026-10-23. Prepared by the x0fix track (Claude): a first version ("rev1"), its independent review (Claude, same
family, independent context), and the revision after that review ("r2"); revised again by the x0r2 reviser (Claude)
after the independent review of r2 ("r3"), all on 2026-10-23. Appended by the lead engineer on <date>. **Owner
decision: provisional, pending Pierce.** The amendment is post-data: census run 1 (`census-20261017T141025Z`) had been
seen. It removes P3(c) flags, which is the direction favourable to Pass, and DELEGATED.md's limits exclude such a change
from the delegation. Record §10 therefore applies in full: the fix is logged with a before/after table of every P1 to P5
value, and verdicts are reported under both the original and the amended rule. The record text above is unchanged.

The amendment has two parts. **X0-A1.1** states the operative rule. It contains no census output, no run id and no
description of the census scripts, and it is also the separate file `experiments/x0-census/X0-A1.1-RULE.md`, SHA-256
`49e0b344c989440200f63b1a39ca650367c93a34f61272af5ed98b63f800c11f`, so that it can be handed over on its own. **X0-A1.2** gives the implementation, the reporting, the reason
and the evidence; it describes the scripts and contains census run 1 outputs.

### X0-A1.1 Operative rule (contains no census output)

The text below is items 1 to 3 of `experiments/x0-census/X0-A1.1-RULE.md` (SHA-256
`49e0b344c989440200f63b1a39ca650367c93a34f61272af5ed98b63f800c11f`), unchanged.

1. **Definition.** Record §4.7 admits as an accumulator location "a register, or a constant-offset, non-escaping stack
   slot treated as a register (04 §7.2 step 4)". The record does not define "non-escaping". This rule defines it,
   after data had been seen. A constant-offset stack slot (`[RSP+d]` or `[RBP+d]` without an index, under §4.7's
   conditions on a moving base) is **escaping** when a pointer into the function's stack frame may reach it.
   - A *stack pointer* is a register into which a stack address was put (`LEA r,[RSP|RBP+…]`, `MOV r,RSP|RBP`,
     `ADD r,RSP`), or a value derived from a stack pointer by `MOV`, `LEA`, or `ADD`/`SUB`/`AND` with an immediate or
     a register. `XOR` with a stack address, and the difference of two stack addresses, give no pointer. A call
     clobbers the caller-saved registers of the object's ABI. A multi-byte `NOP` or a prefetch accesses nothing.
   - RSP itself is not a stack pointer in this sense: it is the base of the slot model. Apart from the copies above,
     a read of RSP itself, a store of it included (`MOV [m],RSP`, `PUSH RSP`), is not a use. RBP is a stack pointer
     only while it holds a stack address put there in the function (`MOV RBP,RSP`, `LEA RBP,[RSP+d]`); otherwise an
     `[RBP+d]` slot keeps §4.7's treatment.
   - An access `[p+d]` through a stack pointer `p` reaches the slots whose bytes it may overlap. The access covers
     the width of its memory operand (64 bytes when the width is unknown).
   - Any other use of a stack pointer reaches every slot of the frame: an indexed access, a string instruction, a
     store of the pointer, the pointer in an argument register at any call or in RAX at a return, or any other
     read. A pointer at or above the function's entry RSP reaches only the slots there.
   - A use counts for a loop only when the loop's header is reachable from it in the function's control-flow graph
     (in the loop, before it, or in an enclosing loop). A use that only follows the loop does not count.
   - A slot's address is the value of its base (RSP or RBP) at the loop header plus `d`. A `PUSH` or `POP` inside
     the loop, which §4.7 allows without treating RSP as moving, is not followed when the address is placed.
2. **Scope.** An escaping slot is plain memory, not an accumulator location, **for the P3(c) quantity only**:
   `acc_lanes_emitted` and the partial results it counts (§4.7 (b) and (c)). Every other quantity of §4.7 and §5
   keeps the reading frozen at `152fa33`, in which every constant-offset stack slot is a register-like location:
   the accumulators, `acc_updates_per_iter`, u_acc and the loop tags (X2's narrowing vocabulary). P1, P2, P3(a),
   P3(b), P3(d1), P3(d2), P4 and P5 are unchanged, and so is every threshold, bound and configuration.
3. **Direction.** The definition over-approximates escape: a stack pointer in any argument register at any call, or
   any unbounded use, makes the whole frame escape. Over-approximating escape removes counted lanes, the direction
   favourable to Pass. The two narrower points of item 1 (RSP itself; the address placed at the header) keep the
   frozen reading where they apply, the direction unfavourable to Pass. The rule is acceptable only because the
   amendment reports, for every loop whose P3(c) quantity differs between the frozen reading and this rule, both
   counts, and reports the verdict under both readings. Which reading governs is Pierce's decision.
### X0-A1.2 Implementation, reporting, reason and evidence (describes the scripts; contains census run 1 outputs)

**Re-derivation blinding.** A fresh re-deriver under `rederive/PROCEDURE.md` §2 item 1 receives the record as
`git show 152fa33:docs/m0/prereg/X0-census.md`, the text at the freeze commit, never the record at HEAD. This part
X0-A1.2, `experiments/x0-census/FREEZE.md`, `scripts/README.md`, `scripts/smoke/a1/` and `results/tooling_fix_A1/`
contain census outputs or describe the census scripts, and are not given to it. Whether it also receives
`X0-A1.1-RULE.md` is an open question for the lead engineer and Pierce (below).

**Implementation** (`scripts/x0_loops.py`, `x0_census.py`, `judge.py`; `rederive/compare_x0.py`).
1. *Unscreened.* A loop is `unscreened` when its P3(c) count, or its partial results with the escaping slot keys
   removed, differ between the frozen reading and X0-A1.1's reading.
   - Its record carries `unscreened_reason`, `escaping_slots`, `escaping_partial_results`, `escape_events` and
     `acc_lanes_if_escaping_slots_were_registers` (the frozen count).
   - Each variant lists its unscreened loops (`p3c_unscreened`) and the loops the frozen reading flags
     (`p3c_frozen_reading`).
   - `census.json` carries both lists, `metrics.x0_a1` (per configuration: unscreened loops, the P3(c) flags of each
     reading, and the flags of one reading only) and one note per unscreened loop with both counts and its bound.
   - The schema check of `judge.py`, which `x0_census.py` also runs, requires the two lists together, the two P3(c)
     lists to differ only in unscreened loops, `p3c_unscreened` to equal the loops marked unscreened (each with its
     frozen count), and each loop with a bound to be in each list exactly when its count for that reading exceeds the
     bound. A violation is `tooling_failure`.
2. *Both ways.* `judge.py` evaluates the decision list twice: once with P3(c) under X0-A1.1 (the top-level outcomes)
   and once under the frozen reading (`verdict.json` `both_ways`, with its outcomes, validity, validity detail, Amber
   (b) rows and notes). V3 is computed for each reading: `rederive/compare_x0.py` compares the re-derivation with the
   X0-A1 lists (`rederivation`) and with the frozen-reading lists (`rederivation_frozen_reading`), and the frozen
   reading uses its own comparison. Without that block, the frozen reading's V3 is `not_computed` (its outcome
   `tooling_failure`) unless the two lists are equal in every variant or no re-derivation exists.
   `rederive/compare_x0.py` is pinned in V4. Which reading governs the verdict is Pierce's decision. Until he decides,
   both are reported and neither is acted on.

**Reason.**
- Census run 1 failed V3. Four of its P3(c) flags were census-only: configuration C, `k_avx512` Q8 and Q4, loops at
  quant_avx512.c:316 and :352, 32 lanes against a bound of 0, in both builds.
- The script frozen at 152fa33 treated every `[RSP+d]` and `[RBP+d]` operand as a register-like slot and never tested
  "non-escaping".
- The four flags counted the eight elements of a stack array of `__m128` accumulators. The function takes the array's
  address (`lea rax/rsi,[rsp+0x140]` for Q8, `lea rax,[rsp+0x180]` for Q4) and stores it to the stack. Inside the
  flagged loops a `rep stosq` with a variable count zeroes the array through that stored address.

**The choice, and the alternative reading.** X0-A1.1 is one operational reading of an undefined word, made after the
data was seen. Its choices are address-taken escape, flow-insensitivity within the loop's reach, whole-frame escape on
unbounded uses, and conservative call arguments. Each choice removes locations from the screen, the favourable
direction. Its two narrower points (a store of RSP itself is not a use; a slot's address is placed from its base at
the loop header) keep the frozen reading where they apply; r3 stated them rather than widening the escape rule after
the data. Under the alternative reading through 04 §7.2 step 4 (stack slots as cells, a spill followed by a reload an
identity unless an aliasing store intervenes, and the variable-count `rep stosq` only a may-store), the eight run-1 flag
records would remain [inference]. That is why the verdict is reported both ways and the choice is Pierce's.

**Files changed since the freeze point under class/, scripts/ or flags/, and the pinned comparison script** (SHA-256
after X0-A1 r3; at the freeze in brackets):
- `experiments/x0-census/scripts/x0_loops.py`:
  `5519a568568ba80db3c5f12080820b4d0e049a99099e5de5fd59382021282812`
  (`8c7ecc9e6a29b4ec8398661ffca9c225a2fccf7f1e1af3f9d24cd04e78df3799`)
- `experiments/x0-census/scripts/x0_census.py`:
  `f62bd2004c856e8cc60a168e766e194b9cb41982e2dcac3b4430cce369a5dae4`
  (`37bb743918899a5a752d47184e905423e75a40b073d860976c91fe8aa1992176`)
- `experiments/x0-census/scripts/judge.py`:
  `9561c46ec1ea60d35059831260bccb381175d01cb2eb2b1591511b705edbe96a`
  (`d8c8da25d8f65b76e6910b415a17c716c1863786c68ad4d4da49c15913567cc5`)
- `experiments/x0-census/scripts/runbook/pin_inputs.py`:
  `3b46ebdf3eebb2c7f03dcc2154eccfe5339c4f5819f47709e0bf24dfce1742e5`
  (`4c87f3bb7b50e2dc94c07d221d9949fc6cd9bf35a40930cd1c424edc7cedd953`)
- `experiments/x0-census/scripts/tests/test_loops_a1.py`:
  `20a3ab76e8aae684081f2c63af2eb7ff8d618c558a031099dbac438eb9c66e52` (new; 27 tests)
- `experiments/x0-census/scripts/tests/test_a1_census_judge.py`:
  `26a2a31d37564008934cc9cacbaf1357452dc65623f97be47a38dfe6c84e691c` (new; 24 tests)
- `experiments/x0-census/scripts/smoke/a1/a1_escape.c`:
  `9e2e93add5e590bbf00989f5a631c231202fc349e06d5c7ad345fce3415c24a5` (new; NON-Hearth reproduction)
- `experiments/x0-census/scripts/smoke/a1/a1_loop_table.csv`:
  `f23a90c652a00077d05b059c1df32672006abbce8d32803a0fef6abfc23632aa` (new)
- `experiments/x0-census/scripts/smoke/a1/a1_set.json`:
  `e326915d6e15009fc047a3e2350a989451acba3d3a68fb02d877112fd5530bb5` (new)
- `experiments/x0-census/scripts/README.md`:
  `4ac5f4768180a6d8afdc6d7ae503df6966a64ef6afd41d5b3deda65fadf40694` (documentation, not pinned;
  `5e1995ef37164ff4b221f3d2d14a298475f2f874abbe382acb6704ae8f18ba56`)
- `experiments/x0-census/class/frozen_inputs.json`:
  `44fcb6332bb593a573fcf9cfeb6c7744486520e48717270b9fbbaf96c25bd600`
  (`5b4d7c08b3837a7094d5bf87d1a6f89c137966e7b9aa3dac3b7d3496d0737219`; re-pinned by
  `scripts/runbook/pin_inputs.py --write`, then 0 differences, 101 files; `_provenance.x0_a1` and `_provenance.x0_a1_r3`
  record the re-pins)
- `experiments/x0-census/rederive/compare_x0.py`, pinned in V4 from r3:
  `2037923344a110049b7c732ae70e1c4bf546d969c86687db7e207d1eeb40d1cb`
  (not present at the freeze; `376c1f75b2a2dbe6e62e06358ba52a17b2338834511d16ec3a11509c1e4b888d` as committed with
  census run 1's results in `506c0bd`)

Also changed or added, outside those directories:
- `experiments/x0-census/X0-A1.1-RULE.md`: `49e0b344c989440200f63b1a39ca650367c93a34f61272af5ed98b63f800c11f` (new; X0-A1.1);
- `experiments/x0-census/FREEZE.md`: `068138820a6920b748041f37b319896a86f69a367e76578e89d871e72462e0c6` (the freeze-time text is unchanged; the X0-A1 section and its r3
  subsection are appended);
- the evidence folder `experiments/x0-census/results/tooling_fix_A1/`: `SHA256SUMS` `235dad7a81717f6c5b2377e4745a35c8d20b01a200e87cbe5f8a5c052cbc8de8` (every file of
  the folder except itself and this draft, `AMENDMENT-X0-A1.md`).

**Evidence, NON-Hearth first** [M, 2026-10-23].
1. *Unit tests.* 234 pass on the laptop, none skipped: 183 earlier, 27 in `test_loops_a1` and 24 in
   `test_a1_census_judge`. The synthetic run-1 shape in `test_loops_a1.py` reuses the offset 0x140 that REPORT.md §10
   quotes from run 1's re-derivation. No run-1 decode was read to write the tests or `a1_escape.c`.
2. *Laptop pre-check* (r2) on earlier NON-Hearth decodes (2,395 loops). Only the P3(c) fields change, on 30 loops, all
   unscreened. No other loop field changes. `x0_loops.py` is unchanged since.
3. *Reproduction* `a1_escape.c` (r2): a stack array of vector accumulators with a run-time live count, zeroed per chunk,
   its address taken. It shares 0 line pairs with Hearth under the shingle guard.
   - It was compiled in `x0_driver.py` replay mode with the frozen compile command line of `quant_avx512.c`
     (`scripts/smoke/a1/a1_set.json`; A and A-ninja use the A-ninja capture) under A, A-ninja, B-cmake, C and D (run
     `smoke-20261023T160057Z`). The r2 script was re-run on its decodes.
   - The frozen script flags 16 loops per build (B-cmake 2, C 6, D 8), at 24 to 64 lanes against a bound of 0. Under
     C these flags have run 1's shape.
   - The X0-A1 script flags none and lists all 40 loop records `unscreened`, with the frozen count. The frozen-reading
     list equals the frozen script's flags in every variant.
   - Apart from `p3.c` and the three P3(c) fields of the 40 records, every field of `loops.json` is unchanged.
4. *Regression replay*, runbook steps 86 and 88 with the re-pinned r2 scripts (R2 `smoke-20261023T172426Z`, R1
   `smoke-20261023T174221Z`):
   - `check_regression_run.py` finds **0 deviations** (60 decode outputs, 420 variants);
   - the decodes are byte-identical to the 2026-10-17 final runs;
   - P3(c) flags are unchanged (0 removed, 0 added);
   - 30 loop records under C (R1 12, R2 18; the address-taken `L[16]` arrays of `smoke_dispatch.c` and of the mock)
     are `unscreened`, none flagged under either reading, and only their three P3(c) fields change;
   - summaries and verdicts differ from the 2026-10-17 ones only in run ids, dates, tree paths and the new `both_ways`
     block and its note. Every outcome is unchanged, and `both_ways` gives the same outcomes under the frozen reading.
   - r3 (no replay: C and D need WSL, which the sprint's current rule forbids): the replay's two `census.json` files,
     re-judged with the r3 `judge.py` and `judge_regression.py` as step 88 runs them, on a copy whose
     `record.scripts_sha256` is r3's pins. The schema check finds 0 violations. Every outcome equals r2's under both
     readings; the only differences are three new keys of `both_ways.frozen_reading`
     (`results/tooling_fix_A1/regression_replay/r3_replay_check.json`).

**Before/after on census run 1** (post-data; the existing objects and decodes, read only; no new census;
`results/tooling_fix_A1/run1/`).
- The frozen script, re-run, reproduces run 1's `loops.json` byte for byte in all 26 units (rev1's check).
- **P1 to P5** (`run1/p1_p5_before_after.tsv`, one row per configuration and build, and one for the union; reproduced
  byte for byte with the r3 scripts). Every value is unchanged except P3(c) under C:

  | Configuration | P3(c) flagged loops per build | P3(c) flagged variants per build |
  |---|---|---|
  | C | 4 → 0 | 2 → 0 |
  | A, A-ninja, B-cmake, D, B-proxy, P.* | 0 → 0 | 0 → 0 |

  P1, P2, P3(a), P3(b), P3(d1) and P3(d2) are unchanged in every row. P4 = |U_all| is 446, P5_iclass 32 and
  P5_opclass 15, before and after.
- No flag is added. The removed flags are `k_avx512` Q8 L1_d98 (:316) and L1_c64 (:352), and Q4 L1_2e90 (:316) and
  L1_2d5f (:352), in both builds. They are exactly the 4 census-only V3 mismatches. The 25 re-derivation-only
  mismatches are untouched.
- **Unscreened: 14 loop records, all under C.** They are the 8 removed flag records (32 lanes under the frozen reading
  against a bound of 0) and C scalar F32/F16/BF16 quant.c:362 (6 records; 8 lanes against a bound of 8, so no flag
  either way). The frozen-reading P3(c) list equals census run 1's own `p3.c` in all 264 variants.
- **Every field** (`run1/run1_allfields.json`): apart from `p3.c` (4 variant records), only `acc_lanes_emitted`,
  `partial_results` and `partial_result_cycles` change, on the 14 unscreened records, besides the new X0-A1 fields.
  Every other loop field (tags, u_acc, `fp_free` and `carried_registers` among them) and every other variant field is
  identical.
- **Cause (a)** applies to all 8 removed flag records: the array's address is stored. **Cause (b)** is present in all
  8, but alone it would not be a sound kill: a `rep stosq` in the loop body, with a variable count
  (`and ecx,0x1ffffffe`), whose destination is reloaded from the stored address.
- **V3 both ways** (r3; `run1/r3/comparison_after_x0a1_both_ways_r3.json`, with the frozen re-derivation v1 of
  2026-10-17): 25 mismatches against the X0-A1 lists, 29 against the frozen-reading lists (run 1's own 29). The 4 that
  only the frozen reading has are the 4 removed flags. r3's schema check finds 0 violations in this census.

**Verdicts both ways** [D from `run1/p1_p5_before_after.tsv`; previews, not verdicts].
- Under the frozen reading, C's P3(c) flags add C to the Amber (b) preview.
- Under X0-A1, Amber (b) rests on B-cmake's P3(a1) alone.
- `judge.py` (r3), run on census run 1 with the X0-A1 loop fields substituted, gives `tooling_failure` under both
  readings: without a re-derivation, and with the v1 re-derivation compared both ways (V3 fails under each reading, with
  25 and 29 mismatches; V4 fails because the scripts are not the census run's). Its `both_ways` lists the 10 C variant
  records concerned (`run1/r3/*_NOT_A_VERDICT.json`; not verdicts). r2's preview
  (`run1/judge_preview_after_x0a1_NOT_A_VERDICT.json`) took the frozen reading's V3 from the amended comparison; r3
  corrects that.
- In both readings the outcome stays `tooling_failure` (V3) until the census is re-run from the amended commit and a
  fresh, independent re-derivation is done, before 2026-11-12.

**Order of work** (job logs in `results/tooling_fix_A1/joblogs/`). The rev1 `x0_loops.py` (`7a6393d3…`) was final at
11:56 EDT, before any census run 1 decode or object was read (first read 12:16 EDT). The r2 script (`5519a568…`) was
written after run 1 had been read and after the review. Each of its changes is neutral or in the unfavourable
direction: more loops listed unscreened, the descriptive fields back on the frozen reading, more screening (uses that
only follow a loop no longer count), and reporting both ways. r3 (after the review of r2) changes no loop output: it
computes V3 for each reading, adds the schema consistency checks, renames one counter and adds another, pins
`compare_x0.py`, and states two narrower points of the rule instead of widening it.

**Residual.**
- The escape rule over-approximates escape (X0-A1.1 item 3). Whatever it removes is listed as unscreened and counted
  under the frozen reading in `both_ways`.
- Its two narrower points (X0-A1.1 item 1: a store of RSP itself; the slot address placed at the loop header) keep
  the frozen reading where they apply.
- Direct indexed stack accesses (`[RSP+i*s+d]`) and `[RBP+d]` slots where RBP holds no stack address keep the frozen
  treatment.
- Accumulation through a pointer into a stack array counts 0 lanes under both readings and is not listed. Example: C
  `k_avx512` Q8 L1_e32 and Q4 L1_2f27 (quant_avx512.c:320, `vaddps xmm1,xmm1,[rdx-0x10]` with RDX loaded from the
  stored array address). These are per-token independent sums, so no reassociation [inference], but they are
  unscreened in substance. This is a frozen residual, not changed by X0-A1.
- A pre-existing `(V)MOVSS` stack-reload defect in `lane0_uses` counts a scalar spilled accumulator as 0 lanes. X0-A1
  does not change it.
- One re-derivation checks one reading: where the readings differ, a re-deriver that implements X0-A1.1 can match only
  the X0-A1 lists, and one that works from the freeze text alone only its own reading, unless PROCEDURE.md is extended.
- r3's own changes are not independently reviewed.

**Open questions** (provisional, pending Pierce):
1. Which reading governs P3(c) for X0's verdict: X0-A1's (the top-level outcomes) or the frozen one (`both_ways`)?
2. Does a fresh re-deriver receive `X0-A1.1-RULE.md` (data-free) with the freeze-commit record? Without it, the
   re-deriver implements "non-escaping" from the freeze text alone, and V3 can mismatch on unscreened loops.
3. Should PROCEDURE.md ask the re-deriver for P3(c) under both readings, so that V3 can hold under each? Without it,
   V3 can hold under at most one reading wherever the readings differ.

**Review log.**

| Date | Reviewer | Family | Scope | Findings | Outcome |
|---|---|---|---|---|---|
| 2026-10-23 | 2 reviewers, adversarial | Claude, same family, independent context | X0-A1 rev1 (`x0_loops.py` `7a6393d3…`), its evidence and its amendment text | 18: 1 blocker, 7 major, 10 minor | All 18 accepted, 3 of them in part; none rejected outright. Fixed in r2: an in-iteration spill through an escaping slot is now unscreened; the descriptive fields keep the frozen reading; the census and `judge.py` carry the unscreened loops and the both-ways verdict; uses that only follow a loop are ignored; the P1 to P5 table, the all-fields comparison, the job logs and the timeline were added; the wording was corrected (operational definition, over-approximation, blinding); FREEZE.md was restored and appended to. Not adopted: a disassembly review deciding a flag (Pierce decides which reading governs instead); the regenerated freeze-time hash rows (they keep the freeze values, with the after values appended); an edit of `_provenance.written` (a separate key instead). Details: `results/tooling_fix_A1/README.md` §8 |
| 2026-10-23 | 1 reviewer, adversarial | Claude, same family, independent context | X0-A1 r2 (`c069600`: `x0_loops.py` `5519a568…`, `x0_census.py`, `judge.py`, tests, evidence, FREEZE.md, draft amendment) | 7: 1 blocker, 2 major, 4 minor | All 7 accepted, none rejected; each verified first. Fixed in r3: V3 of the frozen reading from its own comparison (`compare_x0.py` both ways, pinned in V4), never inherited; schema consistency of the two P3(c) lists, the unscreened list and the loop records; this text in the repository and X0-A1.1 as a separate data-free file; the two narrower points of the escape rule stated in X0-A1.1 (the reviewer's alternative fix; the code is unchanged, and widening escape after the data would be favourable to Pass); `both_ways.frozen_reading` with validity detail and notes; the `metrics.x0_a1` counters. For the lead engineer: the three WSLg traces the x0fix track's keepalives left on C: (23,592,960, 104,857,600 and 104,857,600 bytes) await Pierce's decision. Details: `results/tooling_fix_A1/README.md` §9. r3's own changes are not independently reviewed |
