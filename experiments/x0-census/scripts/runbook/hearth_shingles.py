#!/usr/bin/env python3
"""hearth_shingles.py HEARTH_CLONE OUT.json -- the fingerprint set of x0_driver.py's shingle guard (x0final revision,
2026-10-17; record §2): for each of the seven pinned Hearth files (class/B_iform.json inputs.hearth_blobs) it reads
the blob at the pinned commit with `git show <commit>:<path>` from a read-only clone, checks the blob hash, and writes
the SHA-256 of every window of three consecutive normalised non-trivial lines (x0_driver.nontrivial_lines). Only
hashes are written; no Hearth text leaves the clone. Reads Hearth source text only; compiles nothing.
Standard library only; run with python -I."""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import x0_driver  # noqa: E402
import x0_extract  # noqa: E402


def main():
    clone, out = sys.argv[1], sys.argv[2]
    bi = json.load(open(os.path.join(x0_driver.ROOT, "class", "B_iform.json"), encoding="utf-8"))
    commit = bi["inputs"].get("hearth_commit") or "b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220"
    blobs = bi["inputs"]["hearth_blobs"]
    shingles, per_file = set(), {}
    for rel, want in sorted(blobs.items()):
        data = subprocess.run(["git", "-C", clone, "show", "%s:%s" % (commit, rel)], capture_output=True, check=True).stdout
        have = x0_extract.git_blob_sha1(data)
        if have != want:
            raise SystemExit("blob of %s is %s, pinned %s" % (rel, have, want))
        s = x0_driver.shingles(data.decode("utf-8", errors="replace"))
        per_file[rel] = len(s)
        shingles.update(s)
    rec = {"note": "x0final revision (2026-10-17): SHA-256 of every window of 3 consecutive normalised non-trivial lines "
                   "of the pinned Hearth files (x0_driver.nontrivial_lines); x0_driver.py refuses a smoke source that "
                   "shares one. Hashes only.",
           "hearth_commit": commit, "hearth_blobs": blobs, "windows_per_file": per_file,
           "shingles": sorted(shingles)}
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps({"files": len(per_file), "shingles": len(shingles), "windows_per_file": per_file}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
