#!/usr/bin/env python3
"""hearth_shingles.py HEARTH_CLONE OUT.json -- the fingerprint set of x0_driver.py's shingle guard (x0final revision,
2026-10-17; record §2; redefined by the pre-freeze review of 2026-10-17): for each of the seven pinned Hearth files
(class/B_iform.json inputs.hearth_blobs) it reads the file from the read-only clone's working tree, checks that its
git blob hash (computed here, no git command) equals the pin, and writes the SHA-256 of every window of
x0_driver.SHINGLE_K (2) consecutive normalised non-trivial lines (x0_driver.nontrivial_lines: comments stripped
first). It also writes the allow-list of structural lines (ALLOWED below, recorded in record §2): the dispatch-table
shape that a census mock must share with Hearth so that x0_extract.py finds the struct and the three tables; a window
made only of allow-listed lines is not refused. Only hashes are written for the fingerprints; no Hearth text other
than the allow-listed declarations leaves the clone. Reads Hearth source text only; compiles nothing.
Standard library only; run with python -I."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import x0_driver  # noqa: E402
import x0_extract  # noqa: E402

# The dispatch-table shape of record §4.1 (hx_quant.h:59-63, 71-73; quant.c:429-430; quant_avx2.c:341-342, 347;
# quant_avx512.c:365-366, 371), as normalised lines.
ALLOWED = [
    "typedef struct hx_kernels {",
    "hx_matmul_fn matmul[7];",
    "void (*act_quantize_q8)(const float *x, hx_act_q8 *out, int64_t n);",
    "} hx_kernels;",
    "extern const hx_kernels hx_kernels_scalar;",
    "const hx_kernels *hx_kernels_avx2_table(void);",
    "const hx_kernels *hx_kernels_avx512_table(void);",
    "const hx_kernels hx_kernels_scalar = {",
    "HEARTH_ISA_SCALAR,",
    "static const hx_kernels k_avx2 = {",
    "HEARTH_ISA_AVX2,",
    "static const hx_kernels k_avx512 = {",
    "HEARTH_ISA_AVX512,",
]


def main():
    clone, out = sys.argv[1], sys.argv[2]
    bi = json.load(open(os.path.join(x0_driver.ROOT, "class", "B_iform.json"), encoding="utf-8"))
    commit = bi["inputs"].get("hearth_commit") or "b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220"
    blobs = bi["inputs"]["hearth_blobs"]
    shingles, per_file, lines_all = set(), {}, set()
    for rel, want in sorted(blobs.items()):
        with open(os.path.join(clone, *rel.split("/")), "rb") as f:
            data = f.read()
        have = x0_extract.git_blob_sha1(data)
        if have != want:
            raise SystemExit("blob of %s is %s, pinned %s" % (rel, have, want))
        text = data.decode("utf-8")
        s = x0_driver.shingles(text)
        per_file[rel] = len(s)
        shingles.update(s)
        lines_all.update(x0_driver.nontrivial_lines(text))
    missing = [x for x in ALLOWED if x not in lines_all]
    if missing:
        raise SystemExit("allow-listed lines not found in the pinned files: %s" % missing)
    rec = {"note": "pre-freeze review of 2026-10-17 (x0final revision's guard redefined): SHA-256 of every window of k "
                   "consecutive normalised non-trivial lines (comments stripped) of the pinned Hearth files "
                   "(x0_driver.nontrivial_lines); x0_driver.py refuses a smoke source that shares one, unless every line "
                   "of the window is in allowed_structural_lines (the dispatch-table shape, record §2). Hashes only for "
                   "the fingerprints.",
           "definition": x0_driver.SHINGLE_DEFINITION, "k": x0_driver.SHINGLE_K,
           "hearth_commit": commit, "hearth_blobs": blobs, "windows_per_file": per_file,
           "allowed_structural_lines": ALLOWED, "shingles": sorted(shingles)}
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps({"files": len(per_file), "shingles": len(shingles), "windows_per_file": per_file}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
