#!/usr/bin/env python3
"""pin_inputs.py [--write] [--markdown] -- recompute the V4 pins of class/frozen_inputs.json from the files on disk
(x0final, 2026-10-16).

  * the class files judge.py checks (judge.FROZEN: fp_class.csv, loop_table.csv, B_iform.json, hand_map.csv,
    fp_flag_patterns.txt, objdump_norm.csv, xed_tables.tsv);
  * "scripts": EVERY file under experiments/x0-census/scripts/ except run outputs (runbook/logs/, smoke/results/,
    __pycache__) and documentation (*.md) -- census scripts, tests, smoke and mock inputs, probes and runbook files
    alike. This is a superset
    of the x0prep map (FREEZE.md D5, D6, D8, D10, D11), so V4 also catches a change to any runbook or regression file;
  * "compilers", "headers" (pre-freeze review of 2026-10-17) and "x86-intel.xml" are kept as they are (Table 2.1
    pins; the XML is not stored in the repository).
Without --write it only prints the differences from the current frozen_inputs.json (exit 1 if there are any).
--markdown prints the FREEZE.md hash tables (SHA-256 of the bytes on disk; LF line endings except *.cmd, which
.gitattributes keeps CRLF on every checkout). Standard library only.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))           # experiments/x0-census
sys.path.insert(0, os.path.dirname(HERE))
import judge  # noqa: E402

EXCLUDE_DIRS = {os.path.join("scripts", "runbook", "logs"), os.path.join("scripts", "smoke", "results"), "__pycache__"}


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def script_files():
    out = []
    base = os.path.join(ROOT, "scripts")
    for d, dirs, files in os.walk(base):
        rel_d = os.path.relpath(d, ROOT)
        dirs[:] = sorted(x for x in dirs if x != "__pycache__" and os.path.join(rel_d, x) not in EXCLUDE_DIRS)
        for f in sorted(files):
            if f.endswith((".pyc", ".md")):          # documentation is not a census input
                continue
            out.append(os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, "/"))
    return sorted(out)


def main():
    path = os.path.join(ROOT, "class", "frozen_inputs.json")
    pins = json.load(open(path, encoding="utf-8"))
    new = dict(pins)
    for name in judge.FROZEN:
        new[name] = sha(os.path.join(ROOT, "class", name))
    new["scripts"] = {rel: sha(os.path.join(ROOT, *rel.split("/"))) for rel in script_files()}
    prov = dict(new.get("_provenance", {}))
    prov["scripts"] = ("SHA-256 of every file under experiments/x0-census/scripts/ except run outputs (runbook/logs/, "
                       "smoke/results/, __pycache__) and documentation (*.md), by path under experiments/x0-census; "
                       "recomputed by "
                       "scripts/runbook/pin_inputs.py; judge.py V4 compares the files on disk and census.json "
                       "record.scripts_sha256 with this map")
    prov["written"] = ("2026-10-16 by x0prep; scripts map widened to every script file and recomputed by x0final "
                       "(2026-10-16) with scripts/runbook/pin_inputs.py; recompute and compare with FREEZE.md before "
                       "freezing")
    new["_provenance"] = prov
    diffs = []
    for k in sorted(set(pins) | set(new)):
        if k in ("scripts", "_provenance"):
            continue
        if pins.get(k) != new.get(k):
            diffs.append("%s: %s -> %s" % (k, pins.get(k), new.get(k)))
    old_s, new_s = pins.get("scripts") or {}, new["scripts"]
    for k in sorted(set(old_s) | set(new_s)):
        if old_s.get(k) != new_s.get(k):
            diffs.append("scripts/%s: %s -> %s" % (k, (old_s.get(k) or "-")[:12], (new_s.get(k) or "-")[:12]))
    if "--markdown" in sys.argv:
        print("| File | SHA-256 |\n|---|---|")
        for name in sorted(judge.FROZEN):
            print("| `experiments/x0-census/class/%s` | `%s` |" % (name, new[name]))
        for rel, h in sorted(new_s.items()):
            print("| `experiments/x0-census/%s` | `%s` |" % (rel, h))
        return 0
    for d in diffs:
        print(d)
    print("%d differences; %d script files pinned" % (len(diffs), len(new_s)))
    if "--write" in sys.argv:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(new, f, indent=1, sort_keys=True)
            f.write("\n")
        print("written", path)
        return 0
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
