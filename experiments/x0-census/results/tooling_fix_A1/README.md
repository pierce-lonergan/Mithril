# X0-A1: evidence for the post-data tooling fix of `x0_loops.py`

Written 2026-10-23 by the x0fix track (Claude). Revised the same day ("r2") after the fix's independent review
(Claude, same family, independent context; two reviewers, 18 findings). This folder holds the evidence for Amendment
X0-A1 to the record `docs/m0/prereg/X0-census.md` (FROZEN at `152fa33`). Whether and when the amendment was appended is
shown by the record itself; this folder is not edited when it is appended. No census was re-run and no census verdict
was computed. Nothing here was committed by the x0fix track.

**This folder contains census run 1 outputs** (loop ids, lane counts, bounds, disassembly of run 1's objects) and
describes `x0_loops.py`. A fresh re-deriver (`rederive/PROCEDURE.md`) must not receive it.

Evidence tags follow `docs/m0/README.md`. Every number below is **[M]**, read from the file named next to it, unless
it is tagged otherwise.

## 1. What X0-A1 changes

Record §4.7 admits only "a register, or a constant-offset, non-escaping stack slot treated as a register (04 §7.2
step 4)". The record does not define "non-escaping". The script frozen at 152fa33 (`x0_loops.py` `8c7ecc9e…`) treated
every `[RSP+d]` and `[RBP+d]` operand as such a slot and never tested the condition. X0-A1 gives the word a post-data
operational definition and implements it (`x0_loops.py` `5519a568…`, comment block above `FrameInfo`):

- **Escaping slot.** A stack address is taken when it is put in a register: by `LEA r,[RSP|RBP+…]`, by `MOV r,RSP|RBP`,
  or by a pointer derived from one of those. The pointer then reaches slots:
  - an access `[p+d]` through it reaches the slots whose bytes it may overlap;
  - any other use reaches every slot of the frame: an indexed access, a string instruction, a store of the pointer,
    the pointer in an argument register at a call or in RAX at a return, any other read. If the pointer points at or
    above the entry RSP, only the slots there.
  - **r2:** a use counts for a loop only when the loop's header is reachable from it in the function's control-flow
    graph (in the loop, before it, or in an enclosing loop). A use that only follows the loop, such as an epilogue
    call, cannot reach a slot while the loop runs.
- **Scope (r2).** X0-A1 treats an escaping slot as plain memory **only for the P3(c) quantity**: `acc_lanes_emitted`,
  `partial_results`, `partial_result_cycles`. Every other loop field keeps the frozen reading, so `accumulators`,
  `acc_updates_per_iter`, `u_acc`, `fp_accumulator_ops`, `carried_registers`, `fp_free`, the tags and the X2
  narrowing vocabulary are unchanged.
- **Unscreened (r2).** A loop is `unscreened` when its P3(c) count or its partial results (escaping slot keys aside)
  differ between the frozen reading and the X0-A1 reading. This covers a partial result held in an escaping slot and
  also one that only passes through such a slot inside an iteration (a register spilled and reloaded). It is never
  silently cleared.
  - Loop fields: `unscreened`, `unscreened_reason`, `escaping_slots`, `escaping_partial_results`,
    `acc_lanes_if_escaping_slots_were_registers` (the frozen count) and `escape_events`.
  - Variant fields: `p3c_unscreened`, and `p3c_frozen_reading`, the P3(c) list of the frozen reading.
- **Census level (r2).** `x0_census.py` copies both variant lists into `census.json`, writes `metrics.x0_a1` (per
  configuration: unscreened loops and the P3(c) flags of both readings) and adds one note per unscreened loop, with
  both counts and its bound.
- **Verdict level (r2).** `judge.py` reports the verdict both ways (record §10). When the census carries
  `p3c_frozen_reading`, `verdict.json` gets `both_ways`: the variants whose two readings differ, every unscreened loop,
  and the whole decision list run a second time with P3(c) under the frozen reading (`outcomes`, `validity`,
  `amber_b`). The top-level `outcomes` use X0-A1. Which reading governs is Pierce's decision.
- **Direction.** The definition over-approximates escape: a stack pointer in any argument register at any call, or
  any unbounded use, makes the whole frame escape. Over-approximating escape removes counted lanes, which is the
  direction favourable to Pass. It is safe only together with the `unscreened` listing and the both-ways verdict.
- **Cause (b), the string store.** It needs no rule of its own. A `REP STOS` into the frame writes through a stack
  pointer in RDI. That is an unbounded use, so every slot it can write already escapes.

**What r2 changed, and in which direction.** The r2 script was written after census run 1 had been read (rev1, 12:16
EDT) and after the review. None of its changes is favourable to Pass:
- unscreened on any change of the count or partial results (more loops listed);
- descriptive fields on the frozen reading (as before X0-A1);
- uses that only follow a loop no longer make its slots escape (more screening, the unfavourable direction);
- the census-level and verdict-level reporting is new and changes no flag.

## 2. Order of work (all times EDT, 2026-10-23; job logs in `joblogs/`)

| When | What | Script |
|---|---|---|
| 11:24:57 | dev `x0_loops.py` written to the desktop | `BB7D131A838656148B163C58AA54D41705D0F34640FFDC4EE5DD0938908A3ABF` (dev, never pinned) |
| 11:35-11:55 | dev run `A1dev` of the NON-Hearth reproduction; its reloop steps failed (rc 1) under the dev build. **Superseded; kept as the record of what was seen** (`joblogs/rev1/A1dev_*`) | dev |
| 11:56:22 | rev1 script final (laptop mtime 08:56:22 PDT) | `7a6393d3…` |
| 12:00:57-12:15:19 | rev1: reproduction `A1final`, its reloop, runbook steps 86 and 88 | `7a6393d3…` |
| 12:16:19 | **first read of census run 1** (rev1 `run1_job`): the pinned re-run in it failed (rc 1, wrong tree). **Superseded; kept** | `7a6393d3…`, `8c7ecc9e…` |
| 12:19:00-12:19:48 | rev1: the pinned script re-run on run 1 from a tree with the pinned class files; byte-identical to run 1's `loops.json` | `8c7ecc9e…` |
| about 12:30-12:45 | independent review of rev1 (two reviewers, 18 findings) [inference, from the reviewers' scratch-file times] | `7a6393d3…` |
| 13:04:35-13:50:45 | r2: run 1 reloop, reproduction reloop, runbook steps 86 and 88, comparisons (`joblogs/r2/`) | `5519a568…` |

Nothing read census run 1 before the rev1 script was final. The r2 revision came after run 1 had been read; section 1
says why none of its changes is favourable to Pass. The rev1 evidence is kept in `superseded_rev1/` with its own
`SHA256SUMS`.

## 3. Files

| Path | What |
|---|---|
| `run1/p1_p5_before_after.tsv`, `run1/p1_p5_before_after.json` | **Record §10's before/after table of every P1 to P5 value** for census run 1 (`tools/a1_pvalues.py`): one row per configuration and build, one row for the union. BEFORE is run 1's `census.json`; AFTER is the same census with only the fields `x0_census.py` copies from `loops.json` taken from the r2 re-run. Columns `*_before`, `*_after`, the AFTER-only X0-A1 counts, and `changed` |
| `run1/p3c_before_after.tsv`, `run1/p3c_summary.tsv` | P3(c) detail for census run 1 (`tools/a1_tables.py`): every loop record whose r2 reading differs from `census.json` or that is listed unscreened, with bound, lanes before/after, flags, the partial results behind the change, the escape events (cause (a)) and the string stores in the loop body (cause (b)); and the per-configuration summary |
| `run1/run1_allfields.json` | `tools/a1_allfields.py`: EVERY variant and loop field of the r2 re-run against run 1's own `loops.json`, counted by field and by unscreened/screened, with four checks that must be 0 |
| `run1/run1_compare_new_vs_census.json` | `tools/a1_compare.py`: flags removed and added, with causes (a) and (b) |
| `run1/run1_otherfields.json` | `tools/a1_otherfields.py`: every per-variant field other than the loop records and the P3(c) lists (attribution, d1 and its sites, d2, sequences, probe) against the pinned re-run, and the frozen-reading list against the pinned `p3.c` |
| `run1/run1_changed_loops.json`, `run1/events/` | The changed loop records' summary fields, and the `FrameInfo` events of the functions holding them, each marked `reaches_header` (`tools/a1_events.py`) |
| `run1/reloop_r2/*.reloop.json` | The r2 re-run of every recorded `loops_*` step of run 1 (`tools/a1_reloop.py`): argv, rc, and the SHA-256 of each new `loops.json` |
| `run1/judge_preview_after_x0a1_NOT_A_VERDICT.json` | `judge.py` (r2) on run 1's census with the r2 loop fields substituted. **Not a verdict:** V3 and V4 fail, so both readings give `tooling_failure`. It shows `both_ways` on real data |
| `repro/` | The NON-Hearth reproduction `scripts/smoke/a1/a1_escape.c` (run `smoke-20261023T160057Z`): the r2 script against the pinned script on the same decodes, with the same tables and tools |
| `regression_replay/` | Runbook steps 86 and 88 with the r2 scripts: run ids, `check_regression_run.py` logs, summaries, verdicts (with `both_ways`), and the comparisons with the 2026-10-17 final runs (`s88_*.compare.json`, `s88_*.allfields.json`; summaries and verdicts against `scripts/smoke/results/prefreeze_rerun/` in `s88_vs_20261017_summaries_verdicts.jsondiff.json`) and with the rev1 replay (`s88_*.vs_rev1.compare.json`) |
| `laptop_precheck/` | `laptop_check_r2.py` and its output (every loop field, pinned against r2, on NON-Hearth decodes kept on the laptop; no compile, no decode); `unit_tests_r2.txt` (the 215 unit tests) |
| `joblogs/rev1/`, `joblogs/r2/` | Every desktop job log of rev1 (`D:\mithril\jobs\x0fixA1\`) and of r2 (`D:\mithril\jobs\x0fixA1\r2\`), copied |
| `tools/` | The evidence tools and the desktop job scripts as run. None of them is a census input. r2 added `a1_allfields.py`, `a1_pvalues.py`, `a1_jsondiff.py`, `desktop_jobs/r2_job.ps1`, `r2_post.ps1`, `reloop_job_r2.ps1`, `run1_loopinfo_r2.py`, and changed `a1_otherfields.py` (ignores the new variant list) and `a1_events.py` (`reaches_header`) |
| `superseded_rev1/` | The rev1 evidence and its `SHA256SUMS`, as reviewed: **superseded by r2, kept as the record of what was seen**. Its `tools/` holds the rev1 tool versions |
| `SHA256SUMS` | SHA-256 of every file in this folder except itself |

## 4. Results (r2)

1. **Unit tests.** 215 pass: 183 earlier, 25 in `tests/test_loops_a1.py` and 7 in `tests/test_a1_census_judge.py`
   [M, laptop, 2026-10-23, `laptop_precheck/unit_tests_r2.txt`]. The guarded test in `test_driver_guard` runs, because
   the pins match.
   - The review's two adversarial streams are now tests. A register accumulator spilled and reloaded through an
     escaping slot inside one iteration gives 0 lanes under X0-A1 and is `unscreened` with the frozen count 4. A
     two-accumulator split with one half so spilled gives 4 lanes and is `unscreened` with the frozen count 8. Under
     rev1 both were cleared silently.
   - The synthetic run-1 shape in `test_loops_a1.py` reuses the offset 0x140 that REPORT.md §10 quotes from run 1's
     re-derivation. No run-1 decode was read to write the tests or `a1_escape.c`.
2. **Pins.** `pin_inputs.py --write` found 5 differences against the rev1 pins (`x0_loops.py`, `x0_census.py`,
   `judge.py`, `tests/test_loops_a1.py`, and the new `tests/test_a1_census_judge.py`), then 0. The desktop's r2 tree
   also gives 0 (100 script files pinned) [M, `joblogs/r2/r2_pin_inputs.log`]. `class/frozen_inputs.json` is now
   `d3ba19a9…`. Against the freeze, 8 script files differ or are new (FREEZE.md, appended section).
3. **Laptop pre-check** on NON-Hearth decodes kept on the laptop (`laptop_precheck/laptop_check_r2_output.txt`). They
   are the R1 regression set and the R2 mock of the x0final revision (2026-10-17, so `smoke_dispatch.c` may still carry
   the three two-line runs of Hearth text that record §2 discloses), and the x0prep reviewer's `rv_tricky` decodes.
   - 2,395 loops; 242 have escaping slots.
   - 30 change, all of them unscreened, and only in `acc_lanes_emitted`, `partial_results` and
     `partial_result_cycles`. Every other loop field is identical.
4. **NON-Hearth reproduction** (`repro/`; shingle guard 0 shared pairs; the r2 script re-run on the decodes of run
   `smoke-20261023T160057Z`).

   | | Pinned script | r2 script |
   |---|---|---|
   | Flagged loops per build | 16 (B-cmake 2, C 6, D 8) | 0 |
   | Flagged variants per build | 8 (B-cmake 1, C 3, D 4) | 0 |
   | Lanes of the flagged loops | 24 to 64 against a bound of 0 | listed `unscreened` (40 loop records, both builds) |

   - The frozen-reading list equals the pinned script's flags in every variant (`repro/A1final_allfields.json`: the 4
     checks are all 0).
   - Only the P3(c) fields change, on the 40 unscreened records. Every other field is identical, including the
     controls (`a1_mm_regs` keeps 16 lanes in registers, `a1_peak` 1 lane).
   - A and A-ninja flag nothing under either script.
5. **Regression replay** (runbook steps 86 and 88 with the r2 tree; `regression_replay/`).
   - Runs: R2 mock `smoke-20261023T172426Z`, R1 regression set `smoke-20261023T174221Z`, both from the r2 tree with
     `pin_inputs.py` at 0 differences.
   - `check_regression_run.py` finds **0 deviations** (60 decode outputs, 420 variants; `regression_replay/R1_check.log`).
   - The decode outputs are byte-identical to the 2026-10-17 final runs (96 units: R1 70, R2 26; `s88_*.compare.json`).
   - **P3(c) flags are unchanged: 0 removed, 0 added.**
   - 30 loop records are unscreened (R1 12, R2 18), all under C, each 8 lanes within its bound under the frozen
     reading. They are the address-taken `L[16]` arrays of `smoke_dispatch.c` and of the mock (as in rev1).
   - Every field (`s88_*.allfields.json`): only the three P3(c) fields change, on those 30 records; every other loop
     and variant field is identical; the 4 checks are 0. Against the rev1 replay, the same 30 records are unscreened,
     and their `acc_updates_per_iter` is back on the frozen reading (`s88_*.vs_rev1.compare.json`).
   - Summaries and verdicts against the 2026-10-17 final runs (`s88_vs_20261017_summaries_verdicts.jsondiff.json`):
     the only differences are the run ids, the evaluation dates, the tree path in 13 `non_gate` details, the new
     `both_ways` block and its note. Every outcome is unchanged. In all four verdicts, `both_ways` gives the same
     outcomes under the frozen reading (`p3c_differs` false), and lists the unscreened loops (R1 12, R2 18).
6. **Census run 1** (read only; `run1/`).
   - **P1 to P5** (`run1/p1_p5_before_after.tsv`): every value is unchanged except P3(c) under C, 4 → 0 flagged loops
     and 2 → 0 flagged variants per build. P4 = |U_all| is 446, P5_iclass 32 and P5_opclass 15, before and after. P1,
     P2, P3(a), P3(b), P3(d1) and P3(d2) are unchanged in every configuration and build.
   - **P3(c), removed flags:** C `k_avx512` Q8 `L1_d98` (quant_avx512.c:316) and `L1_c64` (:352), and Q4 `L1_2e90`
     (:316) and `L1_2d5f` (:352), in both builds. Each was flagged at 32 lanes against a bound of 0. Each is now at 0
     lanes and `unscreened`, with the frozen count 32. That is 8 records removed and 0 added.
   - **Unscreened: 14 records, all under C.** The 8 above, and C scalar F32/F16/BF16 quant.c:362 (6 records; 8 lanes
     against a bound of 8 under the frozen reading, so no flag either way; the address-taken `L[]` array is accessed
     through `rcx`/`rsi`).
   - **Changed from rev1:** A and A-ninja `k_avx2` Q8 quant_avx2.c:240 (`L7_290`, 4 records) is screened again. Under
     rev1, its slot `STK:RBP:128` escaped through one event only: a stack address in RDX at the call after
     `xor rcx,rsp` (7:b47; [inference] the `/GS` check). That call follows the loop and cannot reach its header
     (`run1/events/events_A*_b1_7_290.jsonl`: `reaches_header` false for 7:b47 and the epilogue's restores), so under
     r2 the loop keeps its 8 lanes against a bound of 8, as in run 1.
   - The same event files show FP accumulation through a stack pointer in that function (`vaddps ymm3,ymm2,[rdx]` at
     7:9ae, `vmovups [rdx],ymm3` at 7:9b5). Neither reading counts such an access as a location (see Residual).
     Whether it lies in a loop and carries an FP value across iterations was not determined here.
   - **Every field** (`run1/run1_allfields.json`): only `acc_lanes_emitted`, `partial_results` and
     `partial_result_cycles` change, on the 14 unscreened records, besides the new X0-A1 fields. Every other loop
     field and every other variant field is identical, and the 4 checks are 0. The frozen-reading list equals run 1's
     `p3.c` in all 264 variants.
   - **Both ways** (`run1/judge_preview_after_x0a1_NOT_A_VERDICT.json`). `judge.py` r2 was run on run 1's census with
     the r2 loop fields substituted (that census, SHA-256 `dd9c4acd…`, is not kept; `tools/a1_pvalues.py
     --after-census` rebuilds it). It gives `tooling_failure` under both readings: V3 fails, and V4 because the scripts
     are not the census run's. `both_ways` lists 10 C variant records: the four `k_avx512` records whose P3(c) differs
     (`[]` against two loops each) and the six scalar records with an unscreened loop.
7. **Cause of each removed flag** (`run1/p3c_before_after.tsv`, `run1/events/events_C_*.jsonl`).
   - **Cause (a) applies to all 8.**
     - In `mm_q8_avx512`, `lea rax,[rsp+0x140]` at 1:453 and `lea rsi,[rsp+0x140]` at 1:d29 take the address of the
       accumulator array, whose first element is the first counted slot, `STK:RSP:320`. The address is stored to
       `[rsp+0x120]` at 1:45b and to `[rsp+0x118]` at 1:d37.
     - In `mm_q4_avx512`, `lea rax,[rsp+0x180]` at 1:2535 and 1:2e2f take the address of the array that starts at
       `STK:RSP:384`. It is stored to `[rsp+0x120]` and `[rsp+0x150]`.
     - Each store is an unbounded use from which the loops' headers are reachable, so the frame's slots escape.
   - **Cause (b) is present in all 8.** A `rep stosq` inside each flagged loop's body zeroes the array per chunk (1:dc2
     in Q8, 1:2ebc in Q4). Its RDI is reloaded from the stored address, and its count is set by `and ecx,0x1ffffffe`,
     not by an immediate. So (b) alone could not have removed the flags soundly. The removal rests on (a), that is, on
     X0-A1's definition of "non-escaping".
8. **V3** [D, from `results/rederive/comparison.json` and the tables above]. X0-A1 removes run 1's 4 census-only P3(c)
   mismatches. It does not touch the 25 re-derivation-only mismatches, which the re-deriver attributes to its own v1
   script. V3 therefore still needs the fresh re-derivation of REPORT §20.

## 5. Residual

- The escape rule over-approximates escape: a stack pointer in any argument register at any call, or any unbounded
  use, makes the whole frame escape. Over-approximating escape removes lanes, the direction favourable to Pass. It is
  acceptable only with the `unscreened` listing and the both-ways verdict; `judge.py`'s top-level outcomes alone do not
  show what it removed.
- Direct indexed stack accesses (`[RSP+i*s+d]`) and `[RBP+d]` slots where RBP holds no stack address keep the frozen
  treatment.
- `unscreened` lists only loops whose P3(c) quantity differs between the readings. Accumulation through a pointer
  into a stack array counts 0 lanes under both readings and is not listed. Examples: C `k_avx512` Q8 `L1_e32` and Q4
  `L1_2f27` (quant_avx512.c:320; `vaddps xmm1,xmm1,[rdx-0x10]` at 1:108d and 1:3145, `vmovaps [rdx-0x10],xmm0` at
  1:109f, with RDX loaded from the stored `&acc[0]` at 1:f70) [M, run 1 C/b1 decode, read only, by the reviewer and
  the x0fix track]. These are per-token independent sums, so there is no reassociation [inference], but they are
  unscreened in substance. This is a frozen residual that X0-A1 does not change.
- A pre-existing `(V)MOVSS` stack-reload defect in `lane0_uses` counts a scalar spilled accumulator as 0 lanes, an
  under-count in the unsafe direction (found by rev1 on synthetic streams; its effect on run 1 not measured). X0-A1
  does not change it.
- r2's own changes are not independently reviewed.

## 6. Re-derivation blinding

A fresh re-deriver under `rederive/PROCEDURE.md` §2 item 1 receives the record as `git show
152fa33:docs/m0/prereg/X0-census.md`, never the record at HEAD. The amendment's part X0-A1.2, `FREEZE.md`,
`scripts/README.md`, `scripts/smoke/a1/` and this folder contain census outputs or describe `x0_loops.py`, and none of
them is given to it. The amendment's part X0-A1.1 states the operative rule without census output. Whether the
re-deriver receives it is open (provisional, pending the lead engineer and Pierce). Without it, the re-deriver
implements "non-escaping" from the freeze text alone, and V3 can mismatch on unscreened loops.

## 7. Desktop use (DESKTOP-8RS9J1J, 2026-10-23; EDT = PDT + 3 h)

**rev1 (11:32-12:27 EDT).**
- New on D: `D:\mithril\x0fixA1\` (225,311,377 bytes in 3,815 files at 12:24 EDT) and `D:\mithril\jobs\x0fixA1\`.
- Read only: `D:\mithril\x0census\run1` and `D:\mithril\x0reg\runs` (the 2026-10-17 runs).
- WSL only inside keepalives started by the track:
  - the first (`Start-Process`, 11:32 EDT) ended with its SSH session and left the WSLg trace
    `RdClientAutoTrace-WppAutoTrace-20261023-153224-185.etl` (23,592,960 bytes) under
    `%LOCALAPPDATA%\Temp\DiagOutputDir\RdClientAutoTrace\` on C:;
  - the second (`Win32_Process.Create`, 11:35 EDT, pid 60040) left
    `RdClientAutoTrace-WppAutoTrace-20261023-153508-687.etl`. **Correction:** rev1 reported it as 0 bytes at 12:24
    EDT. Its final size is 104,857,600 bytes, last written 12:27:33 EDT, when that keepalive was stopped [M, directory
    listing, 13:04 EDT].
- Other new C: files in that window (four 0-byte `<GUID>.tmp`, `.ses`, `mat-debug-14780.log`, a Visual Studio
  `dd_BackgroundDownload_*` set) were not attributed with certainty and were left in place [inference: not this
  track's].

**r2 (13:04-13:52 EDT = 10:04-10:52 PDT).**
- New on D: only `D:\mithril\x0fixA1\r2\` (2,824 files, 182,152,437 bytes at 13:52 EDT: the r2 tree, the run 1 and
  reproduction re-runs, `runs88`, the comparisons and five transfer tar files) and `D:\mithril\jobs\x0fixA1\r2\` (73
  files, 117,386 bytes).
- Read only: `D:\mithril\x0census\run1`, `D:\mithril\x0reg\runs`, and rev1's `D:\mithril\x0fixA1\runs\A1final`,
  `cmp\A1final_out\old`, `run1_reloop\old` and `runs88`.
- WSL ran only inside one keepalive started by this track (`Win32_Process.Create`, `wsl.exe -d Ubuntu --exec sleep
  14400`, pid 24364, 13:04:20 EDT; WSL had been stopped before). It was stopped at 13:50:03 EDT, and WSL then
  stopped. It left the WSLg trace `RdClientAutoTrace-WppAutoTrace-20261023-170421-962.etl` on C: (104,857,600 bytes,
  last written 13:50:18 EDT) [M, directory listing, 13:52 EDT].
- Other new files on C: in `%LOCALAPPDATA%\Temp` in that window: `.ses` (53 bytes, 13:05), two 0-byte `<GUID>.tmp`
  (13:48, 13:52), `cv_debug.log` (24,052 bytes, 13:43) and a 0-byte `mat-debug-28176.log` (13:32). They were not
  attributed with certainty [inference: the `.tmp` files may come from this track's SSH PowerShell sessions; the
  others are not its jobs'] and were left in place. Nothing new at the profile's top level.
- D: was saturated during the run (% disk time 582 to 630, queue 5; read-only performance counters, 13:15-13:21 EDT),
  so step 86 took 11 minutes instead of 25 seconds. The busiest process by I/O was a `python` process this track did
  not start [M, `\Process(*)\IO Data Bytes/sec`; its owner was not determined].

**Common to both.** At most one compiler at a time, XED `-j 2`, at most 4 threads, `CUDA_VISIBLE_DEVICES=-1`, no GPU,
`TEMP`/`TMP` on D:. No system setting was changed. No Hearth file was compiled and no Hearth object was decoded; census
run 1's existing decodes and objects were read only. The Hearth working tree, the WSL home and GEMS were not touched.
Nothing was deleted: `D:\mithril\x0fixA1\` (rev1 and `r2\`) and the job folders remain, for Pierce or the lead engineer
to remove.

## 8. Review of rev1 and how r2 handles it

Reviewers: two, Claude, same family, independent context, adversarial brief (2026-10-23). Scope: rev1's
`x0_loops.py` (`7a6393d3…`), its evidence (now `superseded_rev1/`), FREEZE.md and the proposed amendment text. 18
findings: 1 blocker, 7 major, 10 minor. All 18 accepted, 3 of them in part; none rejected outright.

| # | Severity | Finding | Verified | r2 |
|---|---|---|---|---|
| R1-1 | blocker | A register accumulator spilled and reloaded through an escaping slot inside one iteration is cleared silently (the slot is never a partial result) | [M] the reviewer's `adv_a1.py` on rev1: frozen 4, rev1 0, `unscreened` false; split: 8 → 4, false | Fixed: unscreened on any change of count or partial results (escaping keys aside); 2 unit tests |
| R1-2 | major | Descriptive fields (tags, u_acc, `fp_free`, accumulators, `carried_registers`) were recomputed on the escape-aware reading | [M] rev1 run 1: `unrolled-u` dropped on C scalar quant.c:362, `fp_free` false → true | Fixed: every field except the three P3(c) fields keeps the frozen reading; unit test; `a1_allfields.py` shows no other field changes |
| R1-3 | major | Unscreened had no verdict effect and no census-level trace | [M] rev1 `x0_census.py` did not copy `p3c_unscreened` | Fixed in part: `census.json` carries `p3c_unscreened`, `p3c_frozen_reading`, `metrics.x0_a1` and notes; `judge.py` `both_ways`. Not adopted: "the removal counts only after a recorded per-loop disassembly review". An agent's review cannot decide a flag (ROADMAP §1 rule 3); which reading governs is Pierce's decision, and both are computed by `judge.py` |
| R1-4 | major | "applies the frozen condition and adds no new rule" overstates; "non-escaping" is undefined, and FrameInfo is a post-data definition in the favourable direction | [M] record §4.7, 04 §7.2 step 4 | Fixed: the amendment and the code comments call it a post-data operational definition and give the alternative reading [inference] |
| R1-5 | minor | Accumulation through a pointer into the same stack array is unscreened in substance but not listed | [M] run 1 C/b1 decode: `vaddps xmm1,xmm1,[rdx-0x10]` at 1:108d, RDX from `[rsp+0x118]` at 1:f70 | Fixed: stated in Residual (frozen residual) |
| R1-6 | minor | FREEZE.md freeze-time rows and the D12 sentence were edited in place | [M] `git diff` | Fixed: FREEZE.md restored to its freeze-time text byte for byte; one section appended |
| R1-7 | minor | Escape events that cannot reach the loop (an epilogue call) still made slots escape | [M] rev1 run 1 A/A-ninja `L7_290`, call at 7:b47 | Fixed: only events from which the header is reachable count (more screening); 3 unit tests; `L7_290` is screened again |
| R2-1 | major | "Every other loops.json field is identical" was false; the evidence tool compared 8 fields | [M] rev1 `run1_compare_new_vs_pinned.json` tags diffs | Fixed: by R1-2, and `tools/a1_allfields.py` compares every field (run 1, reproduction, replay) |
| R2-2 | major | Record §10 asks for a before/after table of every P1 to P5 value | [M] rev1 had P3(c) tables only | Fixed: `run1/p1_p5_before_after.tsv` |
| R2-3 | major | "Conservative" hid the direction; nothing at verdict level read `unscreened` | as R1-3 | Fixed: "over-approximates escape … favourable to Pass" in the amendment, README and code; `both_ways`; Owner question |
| R2-4 | major | The appended amendment would put census outputs into the record at HEAD | [M] PROCEDURE.md §1 "It may read the record"; §2 item 1 "at the freeze commit" | Fixed: blinding paragraph; the amendment split into X0-A1.1 (data-free rule) and X0-A1.2; Owner question on X0-A1.1 |
| R2-5 | minor | The order of work and the superseded attempts were not evidenced | [M] desktop job logs | Fixed: `joblogs/`, section 2 |
| R2-6 | minor | FREEZE.md's X0-A1 section was inserted mid-file and the D12 sentence reworded | [M] `git diff` | Fixed in part: restored and appended, with its own D12 statement. Not adopted: keeping the regenerated freeze-time rows with annotations (R1-6's fix was taken instead: the freeze-time rows keep their values, and the appended section has before and after) |
| R2-7 | minor | `_provenance.written` did not mention the re-pin | [M] | Fixed in part: a key `_provenance.x0_a1` records it. `pin_inputs.py --write` rewrites `written` with fixed text, so an edit there would be lost at the next re-pin |
| R2-8 | minor | `unscreened_reason` missing from the field lists | [M] | Fixed |
| R2-9 | minor | The test's run-1 offset 0x140 came from REPORT.md, not from "the shape" alone | [M] REPORT.md:421 | Fixed: disclosed in the test docstring (re-pinned anyway), this README and the amendment |
| R2-10 | minor | Status sentences "not appended yet" would go stale and change the cited hashes | [M] | Fixed: FREEZE.md and this README need no edit when the amendment is appended |
| R2-11 | minor | "compiled with the frozen quant_avx512.c lines" could read as compiling Hearth lines | [M] `a1_set.json` | Fixed: "the frozen compile command line of `quant_avx512.c`" |
