# X0-A1: evidence for the post-data tooling fix of `x0_loops.py`

Written 2026-10-23 by the x0fix track (Claude). This folder holds evidence for a **proposed** amendment, X0-A1 (post-data,
tooling only; no unit, threshold or configuration change). The amendment text is not yet appended to the record
(`docs/m0/prereg/X0-census.md`, FROZEN at `152fa33`). No census was re-run and no verdict was computed. Nothing here
was committed.

Evidence tags follow `docs/m0/README.md`. Every number below is **[M]**, read from the file named next to it, unless it
is tagged otherwise.

## What changed

Record §4.7 admits only "a register, or a constant-offset, non-escaping stack slot treated as a register (04 §7.2
step 4)". The script frozen at 152fa33 (`x0_loops.py` `8c7ecc9e…`) treated every `[RSP+d]` and `[RBP+d]` operand as such
a slot. It never tested "non-escaping".

The fixed script (`7a6393d3…`) adds `FrameInfo`, which marks a slot as escaping when its address is taken. A stack
address is taken when it is put in a register: by `LEA r,[RSP|RBP+…]`, by `MOV r,RSP|RBP`, or by a pointer derived
from one of those. That pointer must also be able to reach the slot:
- **Exact accesses.** An access `[p+d]` through the pointer makes escaping only the slots whose bytes it may overlap.
- **Unbounded uses.** These are an indexed access, a string instruction, a store of the pointer, the pointer in an
  argument register at a call or in RAX at a return, or any other read of it. An unbounded use makes every slot of the
  frame escape. If the pointer points at or above the entry RSP, it makes only the slots there escape.

An escaping slot is plain memory. The rule only removes locations, so it can only lower `acc_lanes_emitted`. If the
frozen reading counted a partial result in an escaping slot, the loop is reported `unscreened`, never silently
cleared. The new loop fields are `unscreened`, `escaping_slots`, `escaping_partial_results`,
`acc_lanes_if_escaping_slots_were_registers` and `escape_events`. Each variant also gets `p3c_unscreened` in
`loops.json`. All of these pass into `census.json` `variants[].loops[]` through the unchanged assembler.

The rule as implemented is documented in the comment block above `FrameInfo` in `scripts/x0_loops.py`.

**Cause (b).** Cause (b) is the string store that zeroes the array per chunk without the frozen script treating it as a
kill. It needs no rule of its own. A `REP STOS` into the frame writes through a stack pointer in RDI, which is an
unbounded use, so every slot it can write is escaping already. A kill rule for string stores would therefore never
apply to a tracked slot, and none was added.

## Files

| Path | What |
|---|---|
| `run1/p3c_before_after.tsv` | **Census run 1, the before/after table.** Every loop record whose X0-A1 reading differs from `census.json`, in both directions. Columns: configuration, build, variant, loop, source loop, bound, lanes before/after, flag before/after, unscreened, escaping partial results, cause (a) escape events, cause (b) string stores in the loop body |
| `run1/p3c_summary.tsv` | Census run 1 per configuration and build: variants, loops, P3(c)-flagged loops and variants before and after, unscreened loops after |
| `run1/run1_compare_new_vs_census.json` | `tools/a1_compare.py` output: the fixed script on run 1's decodes against run 1's own `loops.json` |
| `run1/run1_compare_pinned_vs_census.json`, `run1/reloop_pinned/*.reloop.json` | The pinned script re-run on the same inputs: byte-identical to run 1's `loops.json` in all 26 units (`identical: true`) |
| `run1/run1_compare_new_vs_pinned.json`, `run1/reloop_fixed/*.reloop.json` | The fixed script's run, with the sha256 of every new `loops.json` |
| `run1/run1_otherfields.json` | Every per-variant field other than the loop records and P3(c) (attribution, d1 and its sites, d2, sequences, probe): 0 differences in 26 files |
| `run1/run1_changed_loops.json` | Source loop, bound and escape events of the 18 changed loop records |
| `run1/events_C_*.jsonl`, `run1/events_A*_b1_7_290.jsonl`, `run1/disasm_A_b1_7_b00.txt` | `FrameInfo` events of the functions that hold the changed loops (`tools/a1_events.py`) |
| `repro/` | The NON-Hearth reproduction `scripts/smoke/a1/a1_escape.c` (run `smoke-20261023T160057Z`): pinned against fixed script on the same decodes, with the same tables |
| `regression_replay/` | Runbook steps 86 and 88 with the fixed, re-pinned scripts. R2 is `smoke-20261023T160256Z` and R1 is `smoke-20261023T160737Z`, both with `scripts_match_pins` true. Also: `check_regression_run.py`, summaries, verdicts, and the comparison with the 2026-10-17 final runs (`s88_*.compare.json`, `tools/a1_runcompare.py`) |
| `laptop_precheck/` | Before any desktop run: pinned against fixed `analyse_loop` on earlier NON-Hearth decodes kept on the laptop (no compile, no decode) |
| `tools/` | The evidence tools (`a1_reloop.py` re-runs recorded `x0_loops.py` steps read-only; `a1_compare.py`, `a1_runcompare.py`, `a1_otherfields.py`, `a1_events.py`, `a1_tables.py`) and the desktop job scripts as run. None of them is a census input |

## Results

1. **Unit tests.** 203 pass: 183 earlier and 20 in `tests/test_loops_a1.py` [M, laptop, 2026-10-23]. The guarded
   test in `test_driver_guard` runs again after the re-pin.
2. **Pins.** `pin_inputs.py --write` found 5 differences: `scripts/x0_loops.py`, plus 4 new files
   (`scripts/tests/test_loops_a1.py` and `scripts/smoke/a1/a1_escape.c`, `a1_loop_table.csv`, `a1_set.json`). After
   writing it found 0 differences, on the laptop and on the desktop's sync copy (99 script files pinned).
   `class/frozen_inputs.json` is now `5342a236…`.
3. **NON-Hearth reproduction** (`repro/`; shingle guard: 0 shared pairs). The source loops are `a1_escape.c`'s chunk
   and row loops.

   | | Pinned script | Fixed script |
   |---|---|---|
   | Flagged loops per build | 16 (B-cmake 2, C 6, D 8) | 0 |
   | Flagged variants | 8 | 0 |
   | Lanes of the flagged loops | 24 to 64 against a bound of 0 | listed `unscreened` (40 loop records) |

   - The fix removes 32 flag records (both builds) and adds none.
   - A and A-ninja flag nothing under either script.
   - The controls are unchanged: `a1_mm_regs` keeps 16 lanes in registers and `a1_peak` keeps 1 lane.
   - Every other `loops.json` field is unchanged.
   - Under C, the pinned script's false flags have census run 1's shape. The array's address is taken, and a
     `rep stosq` with a variable count zeroes it inside the chunk loop.
4. **Regression replay (runbook step 88, with step 86).**
   - `check_regression_run.py` finds **0 deviations** (60 decode outputs, 420 variants).
   - The decode outputs are byte-identical to the 2026-10-17 final runs.
   - **P3(c) flags are unchanged: 0 removed, 0 added.** So there is no changed flag to explain.
   - `summary.json` is identical except for the run id. `verdict.json` is identical except for dates and paths.
   - 30 loop records changed (R1 12, R2 18), all under C. Each went from 8 counted lanes (within its bound) to
     `unscreened`.
   - The cause is GCC's address-taken scalar `L[16]` arrays in `smoke_dispatch.c` (`smoke_dispatch.c:75`) and in the
     mock (`quant.c:66`, `:76`, `:78`). They are zeroed or read through `lea rcx,[rsp+0x10]` and its derived pointers,
     or passed in an argument register.
5. **Census run 1** (read only; `run1/`).
   - **P3(c) before → after:** C `k_avx512` Q8 loops `L1_d98` (quant_avx512.c:316) and `L1_c64` (:352), and Q4 loops
     `L1_2e90` (:316) and `L1_2d5f` (:352). Each was flagged at 32 lanes against a bound of 0 in both builds. Each is
     now not flagged, at 0 lanes, and `unscreened`. That is 8 flags removed and 0 added.
   - Every other configuration (A, A-ninja, B-cmake, D, B-proxy, P.*) has 0 flags before and after.
   - 10 more loop records become `unscreened` without a flag change:
     - C scalar F32/F16/BF16 quant.c:362 (6 records). Each was 8 lanes against a bound of 8. The address-taken `L[]`
       array is accessed through `rcx`/`rsi`.
     - A and A-ninja `k_avx2` Q8 quant_avx2.c:240 (4 records). Each was 8 lanes in `STK:RBP:128` against a bound
       of 8. RDX holds a stack address (`lea rdx,[rbp+0x280]`) at the call after `xor rcx,rsp`. [inference] That call
       is the `/GS` check `__security_check_cookie`, which reads only RCX. The rule does not know a callee's
       arguments, so it treats every argument register as passed. This is the one place where the conservative
       reading costs screening in a release configuration.
6. **Cause of each removed flag** (`run1/p3c_before_after.tsv`, `run1/events_C_*.jsonl`).
   - **Cause (a) applies to all 8.**
     - In `mm_q8_avx512`, `lea rax,[rsp+0x140]` at 1:453 and `lea rsi,[rsp+0x140]` at 1:d29 take the address of the
       accumulator array. Its first element is the first counted slot, `STK:RSP:320`. The address is stored to
       `[rsp+0x120]` at 1:45b and to `[rsp+0x118]` at 1:d37.
     - In `mm_q4_avx512`, `lea rax,[rsp+0x180]` at 1:2535 and 1:2e2f take the address of the array that starts at
       `STK:RSP:384`. It is stored to `[rsp+0x120]` and `[rsp+0x150]`.
     - Each store is an unbounded use, so the frame's slots escape.
   - **Cause (b) is present in all 8**, as the reviewer reported.
     - A `rep stosq` inside each flagged loop's body zeroes the array per chunk: 1:dc2 in Q8, 1:2ebc in Q4.
     - Its RDI is reloaded from the stored address (`mov rdi,[rsp+0x118]` and `mov rdi,[rsp+0x150]`).
     - Its count is set by `and ecx,0x1ffffffe`, which is not an immediate.
     - So (b) alone could not have removed the flags soundly: a variable-count string store through a pointer
       reloaded from memory is no must-kill. The removal mechanism is (a), the frozen condition.
7. **V3** [D, from `results/rederive/comparison.json` and this table].
   - X0-A1 removes the 4 census-only P3(c) mismatches of run 1.
   - It does not touch the 25 re-derivation-only mismatches, which the re-deriver attributes to its own v1 script.
   - V3 therefore still needs the fresh re-derivation planned in REPORT §20.

## Desktop use (DESKTOP-8RS9J1J, 2026-10-23, 11:32-12:27 EDT = 08:32-09:27 PDT)

- New on D: only `D:\mithril\x0fixA1\` (225,311,377 bytes in 3,815 files at 12:24 EDT) and `D:\mithril\jobs\x0fixA1\`
  (147,656 bytes in 120 files).
- Read-only: `D:\mithril\x0census\run1` (decodes, manifests, attribution files and objects; nothing written) and
  `D:\mithril\x0reg\runs` (the 2026-10-17 runs).
- At most one compiler at a time, XED `-j 2`, no GPU, and `CUDA_VISIBLE_DEVICES=-1`. `TEMP`/`TMP` pointed to D:.
- WSL ran only inside keepalives started by this track:
  - The first (`Start-Process`, 11:32 EDT) ended with the SSH session that started it. It left the WSLg trace
    `RdClientAutoTrace-WppAutoTrace-20261023-153224-185.etl` (23,592,960 bytes) under
    `%LOCALAPPDATA%\Temp\DiagOutputDir\RdClientAutoTrace\` on C:.
  - The second (`Win32_Process.Create`, 11:35 EDT, pid 60040) left `RdClientAutoTrace-WppAutoTrace-20261023-153508-687.etl`
    (0 bytes at 12:24 EDT). It was stopped at 12:27 EDT.
- Other files on C: written in that time were not written by this track's jobs [inference]: four 0-byte `<GUID>.tmp`
  files, `.ses`, `mat-debug-14780.log` and a Visual Studio `dd_BackgroundDownload_*` set.
- No system setting was changed. No Hearth file was compiled or decoded. The Hearth working tree, the WSL home and GEMS
  were not touched.
- At 11:36-11:48 EDT, D: was saturated (% disk time 193, queue 6; read-only performance counters), which slowed one
  B-cmake compile of the reproduction to 12 minutes. A GEMS grading job started at 11:36 EDT was running then
  [inference: the cause of the saturation was not measured].
