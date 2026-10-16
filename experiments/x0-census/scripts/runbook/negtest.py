"""negtest.py IN_MANIFEST OUT_MANIFEST -- corrupt a manifest on purpose (negative test for x0_decode.py).

Shifts the first function's decode start by one byte (mid-instruction start) and appends an empty
code range to the second function. x0_decode.py must report errors and exit 1 on the result.
"""
import json
import sys

m = json.load(open(sys.argv[1]))
for man in m:
    man["label"] = (man.get("label") or "") + "-NEGTEST"
    r = man["functions"][0]["code_ranges"][0]
    r["start"] += 1
    r["file_offset"] += 1
    g = man["functions"][1]["code_ranges"]
    g.append({"start": g[-1]["end"], "end": g[-1]["end"], "file_offset": 0})
json.dump(m, open(sys.argv[2], "w"))
