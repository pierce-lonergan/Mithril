#!/usr/bin/env python3
"""summarize_x0final.py RUN OUT.json -- compact record of an x0final driver run on NON-Hearth inputs (runbook step 88):
per configuration the steps that returned non-zero, the build records (rc, argv check, compiler pins against
class/frozen_inputs.json), the §6 repro and A versus A-ninja comparisons, attribution, d1, d2, P3(c), loop tags and
gap causes; the metrics; and the outcomes of every verdict file in RUN. Standard library only."""
import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def main():
    run, out = sys.argv[1], sys.argv[2]
    c = json.load(open(os.path.join(run, "census.json"), encoding="utf-8"))
    pins = json.load(open(os.path.join(ROOT, "class", "frozen_inputs.json"), encoding="utf-8")).get("compilers", {})
    res = {"note": "x0final runbook step 88: NON-Hearth inputs only; %s" % c["record"].get("id"),
           "run_id": (json.load(open(os.path.join(run, "run.json"))) or {}).get("run_id"),
           "record": {k: c["record"].get(k) for k in ("id", "profile", "mock")}, "configs": {}}
    for cfg, x in sorted(c["configs"].items()):
        cj = json.load(open(os.path.join(run, cfg, "config.json"), encoding="utf-8"))
        vs = [v for v in c["variants"] if v["config"] == cfg]
        bs = [b for b in c["builds"] if b["config"] == cfg]
        base = cfg.split(".")[-1]
        res["configs"][cfg] = {
            "nonzero_steps": [s["step"] for s in cj.get("steps", []) if "argv" in s and s.get("rc") != 0],
            "builds": [{"file": b["file"], "build_index": b["build_index"], "rc": b["rc"],
                        "argv_matches_frozen": b.get("argv_matches_frozen"),
                        "compiler_pin_match": b.get("compiler_sha256") == pins.get(base) if base in pins else None,
                        "errors": [[os.path.basename(str(e.get("file")).replace(chr(92), "/")), e.get("line"), e.get("text")[:120]]
                                   for e in b.get("errors") or []][:3],
                        "includes": len(b.get("includes") or []), "ice": b.get("ice")} for b in bs],
            "twin_builds_rc": sorted({t.get("rc") for t in c.get("twin_builds", []) if t.get("config") == cfg}),
            "p3a": {f: r for f, r in (x.get("p3a") or {}).items()},
            "repro_identical": {f: r.get("identical") for f, r in (x.get("repro") or {}).items()},
            "ab_compare_files": {f: r.get("identical") for f, r in (x.get("ab_compare_files") or {}).items()},
            "variants": collections.Counter("b%d" % v["build_index"] for v in vs),
            "ab_compare": collections.Counter(v.get("ab_compare") for v in vs if "ab_compare" in v),
            "attribution": collections.Counter(v.get("attribution") for v in vs),
            "loop_attribution": collections.Counter(lp.get("attribution") for v in vs for lp in v.get("loops") or []),
            "loops_attributed_through_inline_frame": sum(1 for v in vs for lp in v.get("loops") or []
                                                         if (lp.get("attributed_through_frame") or 0) > 0),
            "d1": collections.Counter(v["p3"].get("d1") for v in vs if "d1" in v["p3"]),
            "d2": collections.Counter(s.get("result") for v in vs for s in v["p3"].get("d2") or []),
            "p3c_flagged": [[v["table"], v["slot"], v["build_index"], v["p3"]["c"]] for v in vs if v["p3"].get("c")],
            "p3b": sorted({i for v in vs for i in v["p3"].get("b") or []}),
            "tags": collections.Counter(t for v in vs for lp in v.get("loops") or [] for t in lp.get("tags") or []),
            "not_computed_tags": collections.Counter(t for v in vs for lp in v.get("loops") or []
                                                     for t in lp.get("not_computed_tags") or []),
            "gaps": collections.Counter(g.get("cause") for v in vs for g in (v.get("coverage") or {}).get("gaps") or []),
            "u_iforms": len({f for v in vs for f in v.get("iforms") or {}}),
            "probe": {"%s|b%d" % (v["slot"], v["build_index"]): (v.get("probe") or {}).get("pairing")
                      for v in vs if "probe" in v}}
    m = c.get("metrics") or {}
    res["metrics"] = {k: m.get(k) for k in ("p2", "p3", "p4_u_all", "p5_iclass")}
    sec = m.get("secondary") or {}
    res["metrics"]["secondary"] = {k: sec.get(k) for k in ("u_all_S", "u_all_simd", "u_all_simd_S", "u_release",
                                                           "p5_opclass", "fp_environment_iclasses_in_counted_sets",
                                                           "proxy_fidelity")}
    res["crossdecoder"] = collections.Counter((d.get("config"), d.get("xed_iclass"), bool(d.get("fp_sensitive")))
                                              for d in c["crossdecoder"]["disagreements"])
    res["crossdecoder"] = {"%s|%s|fp=%s" % k: n for k, n in res["crossdecoder"].items()}
    res["schema_violations"] = (c.get("schema_check") or {}).get("violations")
    res["verdicts"] = {}
    for p in sorted(glob.glob(os.path.join(run, "verdict*.json"))):
        v = json.load(open(p, encoding="utf-8"))
        vd = v.get("validity_detail") or {}
        res["verdicts"][os.path.basename(p)] = {
            "outcomes": v.get("outcomes"), "validity": v.get("validity"),
            "v1_tooling_gaps": len(vd.get("v1_tooling_gaps") or []), "v1_config_gaps": len(vd.get("v1_config_gaps") or []),
            "v4": vd.get("v4"), "amber_a": {k: (v.get("amber_a") or {}).get(k) for k in ("u_all", "two_t_forms", "p5_iclass", "holds")},
            "amber_b": [{"config": x["config"], "p2": x["p2"], "p3a": sorted(x["p3"].get("a", {}))} for x in v.get("amber_b") or []],
            "amber_c": len(v.get("amber_c") or []),
            "non_gate": sorted({"%s %s" % (x.get("row"), x.get("config")) for x in v.get("non_gate") or []}),
            "notes": (v.get("notes") or [])[:3]}
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(res, f, indent=1, sort_keys=True)
    print(json.dumps({"configs": sorted(res["configs"]), "verdicts": {k: v["outcomes"] for k, v in res["verdicts"].items()}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
