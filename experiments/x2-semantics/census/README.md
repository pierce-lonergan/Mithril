# X2 census absorption and the frozen budget (2026-10-23, x2freeze track)

X0 census run 1 absorbed into the X2 semantics table (TABLE-SCHEMA §9.1; the X2 record §2, §4 item 9, §6).
Nothing here was run on silicon. Tags as in [docs/m0/README.md](../../../docs/m0/README.md).

| File | What | sha256 |
|---|---|---|
| `coverage_run1_ABCD.json` | `census_absorb.py` over the dispatched closures (build 1) of A, B-cmake, C, D: buckets, operand variants, **every form's disposition with its reason** (`scope`, `scope_reasons`), the cross-check against X0's `x2_scope.json` (iform and FP sets equal), the input hashes, and the budget of the whole table | `d3926ac8…8620` |
| `coverage_run1_AD.json` | the same over the release configurations A and D (the scope if X0's amber (a) holds at signing) | `b8638c14…bbdf` |
| `budget.v1.json` | the vector budget: 610 rows, per-iclass totals, the generator's hash, the rule for entries added after freeze. Becomes `budget.v1` unchanged at the X2 record's freeze commit | `7b905f54…5258` |
| `table_index.json` | every table entry's content hash at this revision (semantics bundle `0c2a041c…ff2d`) | `35825c1e…ed73` |

**Revision 4 (2026-10-23, after the review of the X2 record's revision 3)** [M]: the legacy CMPPS/CMPSS entries
declare imm8 ∈ [0, 7] in their `sem` spec, which changed the semantics bundle and therefore every content hash. The
coverage files were re-generated with the command below: they differ from revision 3's only in entries' content
hashes; `budget.v1.json` has the same 610 rows, summary and per-iclass totals, and differs only in the bundle hash
of its `generator` field.

Inputs (not copied here; on the desktop under `D:\mithril\x0census\run1\<config>\b1\all\decode\`):
`census.json` sha256 `3d54f0d5…6f06` and the build-1 `instructions.jsonl` of A, B-cmake, C and D, whose hashes
`census_absorb.py` records in `inputs` and which equal X0's `results/run1_files.sha256`.

Reproduce (laptop or desktop, Python 3.12+, no network):

```text
python -B -m semantics.census_absorb --census ../x0-census/results/census.json \
       --insts A.b1.instructions.jsonl B-cmake.b1.instructions.jsonl C.b1.instructions.jsonl D.b1.instructions.jsonl \
       --configs A,B-cmake,C,D --x2-scope ../x0-census/results/x2_scope.json --budget --strict \
       -o census/coverage_run1_ABCD.json
```

`--strict` fails if any FP-sensitive form of the union lacks a table entry. Census run 1's verdict is not final; if
X0's re-run changes the union, this is re-run under the record's re-scope rule (§2).
