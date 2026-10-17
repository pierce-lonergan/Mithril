"""Compare two directories of exported SMT-LIB 2 queries modulo Z3's let-variable numbering.

Z3's printer names shared subterms `?xNNN` / `$xNNN` after internal AST ids, which depend on every term built
earlier in the same process, so the sha256 of an exported query identifies the FILE, not the query's meaning:
building one more query first renumbers the later ones. This tool renames those variables in order of first
appearance and compares the texts (added 2026-10-16 to check that moving the integer lane formulas into
int_lanes.py left the first run's queries unchanged).

  python -B smt2_equiv.py OLD_DIR NEW_DIR [--out report.json]
"""
import argparse
import glob
import json
import os
import re
import sys


def norm(t):
    m = {}

    def rep(x):
        k = x.group(0)
        if k not in m:
            m[k] = "%s%d" % (k[0], len(m))
        return m[k]
    return re.sub(r"[?$][a-z]\d+", rep, t)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = {}
    for p in sorted(glob.glob(os.path.join(a.new, "*.smt2"))):
        fn = os.path.basename(p)
        q = os.path.join(a.old, fn)
        if not os.path.exists(q):
            res[fn] = "missing in OLD"
            continue
        x, y = open(q).read(), open(p).read()
        res[fn] = "identical" if x == y else ("equal modulo let-variable names" if norm(x) == norm(y) else "DIFFERENT")
    for k, v in res.items():
        print("%-28s %s" % (k, v))
    if a.out:
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)
    return 0 if all(v != "DIFFERENT" and not v.startswith("missing") for v in res.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
