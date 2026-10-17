"""negtest_dispatch.py IN_MANIFEST OUT_MANIFEST -- corrupt an x0_extract.py manifest on purpose.

Moves every resolved slot entry one byte forward (a mid-instruction entry) and drops the relocations of the
first code section that has any, so x0_decode.py must report gaps (cause `other` / `unresolved_indirect` /
decode mismatches) and exit 1. Used by runbook step 72 to show that the checks are not vacuous.
"""
import json
import sys

m = json.load(open(sys.argv[1]))
m["label"] = (m.get("label") or "") + "-NEGTEST"
for v in m["variants"]:
    if v["resolved"] and v["resolved"].get("function"):
        v["resolved"]["offset"] += 1
for o in m["objects"]:
    for s in o["sections"]:
        if s["is_code"] and o["relocs"].get(str(s["index"])):
            o["relocs"][str(s["index"])] = []
            break
json.dump(m, open(sys.argv[2], "w"))
