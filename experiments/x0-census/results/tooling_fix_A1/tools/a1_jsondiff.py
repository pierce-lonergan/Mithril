#!/usr/bin/env python3
"""a1_jsondiff.py OLD.json NEW.json [OLD2.json NEW2.json ...] -o RESULT.json -- Amendment X0-A1 evidence tool (x0fix track,
revision after the review of 2026-10-23; not a census input). For each pair, lists every JSON path whose value differs
(added, removed or changed), with both values cut to 300 characters. Used to compare the step-88 summaries and verdicts
of the r2 replay with the 2026-10-17 final runs (scripts/smoke/results/prefreeze_rerun/). Standard library only."""
import json
import sys


def walk(a, b, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            p = "%s.%s" % (path, k) if path else str(k)
            if k not in a:
                out.append({"path": p, "change": "added", "new": json.dumps(b[k], sort_keys=True)[:300]})
            elif k not in b:
                out.append({"path": p, "change": "removed", "old": json.dumps(a[k], sort_keys=True)[:300]})
            else:
                walk(a[k], b[k], p, out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            walk(x, y, "%s[%d]" % (path, i), out)
    elif a != b:
        out.append({"path": path, "change": "changed", "old": json.dumps(a, sort_keys=True)[:300],
                    "new": json.dumps(b, sort_keys=True)[:300]})


def main():
    args = sys.argv[1:]
    out_path = args[args.index("-o") + 1]
    files = [x for i, x in enumerate(args) if x != "-o" and (i == 0 or args[i - 1] != "-o")]
    res = []
    for old, new in zip(files[0::2], files[1::2]):
        with open(old, encoding="utf-8") as f:
            a = json.load(f)
        with open(new, encoding="utf-8") as f:
            b = json.load(f)
        diffs = []
        walk(a, b, "", diffs)
        res.append({"old": old.replace("\\", "/").split("/x0-census/")[-1], "new": new.replace("\\", "/").split("/x0-census/")[-1],
                    "n_differences": len(diffs), "differences": diffs})
        print("%s -> %s: %d differences" % (old, new, len(diffs)))
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
