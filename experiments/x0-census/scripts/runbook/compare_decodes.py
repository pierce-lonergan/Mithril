"""compare_decodes.py DIR_A DIR_B -- check two x0_decode.py output directories decode identically.

Compares functions.json tuples and every instruction record (ignoring object paths and labels).
Exit 0 when identical.
"""
import json
import os
import sys

KEYS = ("function", "kind", "offset", "len", "hex", "iclass", "iform", "extension", "isa_set", "category",
        "attributes", "fields", "padding", "undecodable")


def load(d):
    funcs = json.load(open(os.path.join(d, "functions.json")))
    f = [(x["function"], x["start"], x["end"], json.dumps(x["tuples"], sort_keys=True)) for x in funcs]
    ins = []
    with open(os.path.join(d, "instructions.jsonl")) as fh:
        for line in fh:
            r = json.loads(line)
            ins.append(tuple(json.dumps(r.get(k), sort_keys=True) for k in KEYS))
    return f, ins


fa, ia = load(sys.argv[1])
fb, ib = load(sys.argv[2])
same_f, same_i = fa == fb, ia == ib
print("%s vs %s: functions identical=%s (%d), instructions identical=%s (%d/%d)" % (
    sys.argv[1], sys.argv[2], same_f, len(fa), same_i, len(ia), len(ib)))
sys.exit(0 if same_f and same_i else 1)
