#!/usr/bin/env python3
"""check_regression_run.py RUN EXPECT.json -- the step-72 expectations (tricky_expect.json) applied to a driver run.

RUN is an x0_driver.py replay-mode run of smoke/regression_set.json (NON-Hearth inputs only). Its configurations map
to the expectation names of step 72: A and A-ninja -> A, B-cmake -> B, C -> C, D -> D; a '#scalar' census file
-> '<name>-scalar'. For every configuration, build (1 and 2) and census file, every variant of
RUN/<cfg>/b<k>/<file>/decode/variants.json is checked with check_smoke.check_variant; the two builds' variants.json
must be identical (record §6 on the decode outputs); smoke_dispatch's d1 canaries must be "pass" in loops.json.
Prints one line per deviation; exit 1 if there is any. Standard library only.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_smoke  # noqa: E402

CFG_MAP = {"A": "A", "A-ninja": "A", "B-cmake": "B", "C": "C", "D": "D"}


def main():
    run, exp = sys.argv[1], json.load(open(sys.argv[2]))
    devs, nvar, units = [], 0, 0
    for cfg in sorted(CFG_MAP):
        cdir = os.path.join(run, cfg)
        if not os.path.isdir(cdir):
            devs.append("%s: configuration missing from the run" % cfg)
            continue
        for unit in sorted(os.listdir(os.path.join(cdir, "b1"))) if os.path.isdir(os.path.join(cdir, "b1")) else []:
            fid = unit
            scalar = fid.endswith("#scalar")
            name = re.sub(r"\.c(#scalar)?$", "", fid)
            ecfg = CFG_MAP[cfg] + ("-scalar" if scalar else "")
            spec = exp["decodes"].get(name)
            if spec is None:
                devs.append("%s %s: no expectation for decode %s" % (cfg, fid, name))
                continue
            texts = {}
            for bi in (1, 2):
                vp = os.path.join(cdir, "b%d" % bi, unit, "decode", "variants.json")
                try:
                    texts[bi] = open(vp, "rb").read()
                except OSError as e:
                    devs.append("%s %s b%d: missing %s" % (cfg, fid, bi, e))
                    continue
                units += 1
                vs = json.loads(texts[bi])
                if len(vs) != spec["variants"]:
                    devs.append("%s %s b%d: %d variants, expected %d" % (cfg, fid, bi, len(vs), spec["variants"]))
                for v in vs:
                    nvar += 1
                    key = v.get("source_function") if name != "smoke_dispatch" else "smoke_dispatch:*"
                    rules = exp["expect"].get(key)
                    if rules is None:
                        devs.append("%s %s: no expectation for %s" % (cfg, fid, key))
                        continue
                    for b in check_smoke.check_variant(v, check_smoke.merged_rules(rules, ecfg, exp["defaults"])):
                        devs.append("%s %s b%d %s:%s (%s): %s" % (cfg, fid, bi, v.get("table"), v.get("slot"),
                                                                   v.get("source_function"), b))
                if name == "smoke_dispatch":
                    lp = os.path.join(cdir, "b%d" % bi, unit, "loops.json")
                    loops = json.load(open(lp)) if os.path.exists(lp) else []
                    d1 = {"%s:%s" % (r["table"], r["slot"]): r["p3"].get("d1") for r in loops}
                    for k in ("sd_table:act_quantize", "sd_table_global:act_quantize"):
                        if d1.get(k) != "pass":
                            devs.append("%s %s b%d: d1 canary %s = %r" % (cfg, fid, bi, k, d1.get(k)))
            if len(texts) == 2 and texts[1] != texts[2]:
                devs.append("%s %s: build 1 and build 2 decode outputs differ" % (cfg, fid))
    for d in devs:
        print("DEVIATION:", d)
    print("check_regression_run: %d decode outputs, %d variants checked, %d deviations" % (units, nvar, len(devs)))
    return 1 if devs else 0


if __name__ == "__main__":
    sys.exit(main())
