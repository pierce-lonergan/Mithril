"""code_detail.py OLD_UNIT_DECODE NEW_UNIT_DECODE VARIANT -- which closure functions of one variant differ between two
decodes, with the per-function instruction counts and iclass multisets. NON-Hearth smoke decodes only."""
import collections
import difflib
import json
import sys


def load(p, vid):
    d = collections.defaultdict(list)
    with open(p + "/instructions.jsonl", encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["variant"] == vid:
                d[r.get("function") or ""].append((r["offset"], r["hex"], r.get("iclass"), r.get("disasm")))
    return {k: sorted(v) for k, v in d.items()}


o, n = load(sys.argv[1], sys.argv[3]), load(sys.argv[2], sys.argv[3])
for f in sorted(set(o) | set(n)):
    a, b = o.get(f, []), n.get(f, [])
    if a == b:
        print("same      %-24s %d instructions" % (f, len(b)))
        continue
    ca, cb = collections.Counter(x[2] for x in a), collections.Counter(x[2] for x in b)
    print("DIFFERENT %-24s %d -> %d instructions; iclass multiset %s" % (f, len(a), len(b), "equal" if ca == cb else
          "differs: -%s +%s" % (dict(ca - cb), dict(cb - ca))))
    sa = ["%s" % x[3] for x in a]
    sb = ["%s" % x[3] for x in b]
    for line in list(difflib.unified_diff(sa, sb, lineterm="", n=1))[:40]:
        print("    " + line)
