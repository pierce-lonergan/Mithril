"""Run the global checks C1-C4 on the six generated lane programs over the bounded shape set.

python -I scripts/check_all.py [--json OUT]
"""

import argparse
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from x3gen.core import check, lower  # noqa: E402
from x3gen.hearth import meaning  # noqa: E402
from x3gen.hearth.schedules import avx2, avx512, scalar  # noqa: E402

VARIANTS = [
    ("scalar", scalar.schedule, 1, 1),
    ("avx2", avx2.schedule, 8, 8),
    ("avx512", avx512.schedule, 16, 4),
]


def run():
    res = {}
    for isa, fn, lanes, tl in VARIANTS:
        for fmt in ("q8", "q4"):
            k = meaning.MEANINGS[fmt]
            s = fn(k)
            f = lower.lower(s, "x3_%s_%s" % (fmt, isa))
            shapes = check.default_shapes(lanes, tl)
            t0 = time.time()
            try:
                r = check.check_func(k, f, s.log.ids(), shapes)
                r["verdict"] = "accept"
            except check.Reject as e:
                r = {"verdict": "reject", "reason": str(e)}
            r["seconds"] = round(time.time() - t0, 1)
            r["shape_list"] = shapes
            res["%s/%s" % (isa, fmt)] = r
            print(
                isa,
                fmt,
                r["verdict"],
                {k2: v for k2, v in r.items() if k2 != "shape_list"},
                flush=True,
            )
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    out = run()
    if a.json:
        pathlib.Path(a.json).write_bytes((json.dumps(out, indent=1) + "\n").encode())
