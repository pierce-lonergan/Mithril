"""code_compare.py OLD_RUN NEW_RUN -- compare the decoded code (per variant: function, section, offset, bytes, role of
every decoded instruction record) of two step-88 runs, unit by unit and build by build. NON-Hearth smoke runs only."""
import collections
import json
import os
import sys

old_run, new_run = sys.argv[1:3]
tot = collections.Counter()
for cfg in sorted(os.listdir(new_run)):
    for b in ("b1", "b2"):
        bdir = os.path.join(new_run, cfg, b)
        if not os.path.isdir(bdir):
            continue
        for unit in sorted(os.listdir(bdir)):
            def load(run):
                p = os.path.join(run, cfg, b, unit, "decode", "instructions.jsonl")
                if not os.path.exists(p):
                    return None
                d = collections.defaultdict(list)
                with open(p, encoding="utf-8") as fh:
                    for line in fh:
                        r = json.loads(line)
                        d[r["variant"]].append((r.get("function") or "", r["section"], r["offset"], r["hex"], r.get("role") or ""))
                return {k: sorted(v) for k, v in d.items()}
            o, n = load(old_run), load(new_run)
            if o is None or n is None:
                print("%-10s %s %-26s missing (old %s, new %s)" % (cfg, b, unit, o is not None, n is not None))
                tot["missing"] += 1
                continue
            same = o == n
            diff = sorted(k for k in set(o) | set(n) if o.get(k) != n.get(k))
            tot["identical" if same else "different"] += 1
            print("%-10s %s %-26s %s variants=%d records=%d%s" % (cfg, b, unit, "identical" if same else "DIFFERENT", len(n),
                                                             sum(len(v) for v in n.values()),
                                                             "" if same else " differing: %s" % diff[:6]))
print(dict(tot))
