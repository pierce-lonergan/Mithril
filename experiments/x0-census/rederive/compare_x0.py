#!/usr/bin/env python3
"""Compare the frozen re-derivation (figures.json + rederive_detail.json) with census.json (PROCEDURE.md section 4)
and write (1) comparison.json and (2) a copy of census.json with the `rederivation` block filled, for judge.py.

Run after figures.json is frozen; reads census.json only here.  Standard library only (python -I)."""
import argparse, collections, hashlib, json, re

MAIN = ["A", "B-cmake", "C", "D"]


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def hdr_key(h):
    """'<name>#<sec>:0x<off>' (re-derivation) or [sec, off] (census) -> (sec, off)."""
    if isinstance(h, list):
        return (int(h[0]), int(h[1]))
    m = re.match(r".*#(\d+):0x([0-9a-f]+)$", h)
    return (int(m.group(1)), int(m.group(2), 16))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--figures", required=True)
    ap.add_argument("--detail", required=True)
    ap.add_argument("--census", required=True)
    ap.add_argument("--out-comparison", required=True)
    ap.add_argument("--out-census", required=True)
    a = ap.parse_args()
    F = json.load(open(a.figures))
    D = json.load(open(a.detail))
    C = json.load(open(a.census))
    mism = []
    rows = []

    def add(kind, key, census_val, rederive_val, note=""):
        mism.append({"kind": kind, "key": key, "census": census_val, "rederivation": rederive_val, "note": note})

    # ---- census side, per (config, table:slot) ----
    cv = collections.defaultdict(list)
    for v in C["variants"]:
        cv[(v["config"], "%s:%s" % (v["table"], v["slot"]))].append(v)
    ab = C["metrics"]["secondary"].get("ab_compare")
    # A file that failed to compile in both builds has no variant records in census.json; its variants carry the
    # gap compile_failed through the build records (record 5 P1 compile rule).  Normalise that representation:
    # rc != 0 in both builds, the pinned compiler ran with the frozen argv, an error located in the census file.
    failed = {}
    for cfg in MAIN + ["A-ninja"]:
        for fname in ("quant.c", "quant_avx2.c", "quant_avx512.c"):
            bs = [b for b in C["builds"] if b["config"] == cfg and b["file"] == fname]
            if len(bs) == 2 and all(b["rc"] != 0 and b.get("compiler_ran") and b.get("argv_matches_frozen") and
                                    any((e.get("file") or "").replace("\\", "/").endswith(fname)
                                        for e in b.get("errors", [])) for b in bs):
                failed[(cfg, fname)] = True
    tfile = {"hx_kernels_scalar": "quant.c", "k_avx2": "quant_avx2.c", "k_avx512": "quant_avx512.c"}
    for key in F["p1"]:
        cfg, k = key.split("|", 1)
        if (cfg, k) not in cv and failed.get((cfg, tfile[k.split(":")[0]])):
            cv[(cfg, k)] = [{"config": cfg, "build_index": b, "coverage": {"slot_resolved": False,
                             "gaps": [{"cause": "compile_failed"}]}, "p3": {"c": []}, "loops": [], "iforms": {},
                             "fp_sensitive": [], "p2_fma": 0, "_normalised_from_builds": True} for b in (1, 2)]
    census_members = [(c, k) for (c, k) in cv if c in MAIN]
    census_members += [(c, k) for (c, k), vs in cv.items() if c == "A-ninja" and any(v.get("union_member") for v in vs)]
    red_members = [tuple(k.split("|", 1)) for k in F["p1"]]
    if sorted(census_members) != sorted(red_members):
        add("union_members", "variants", sorted("%s|%s" % x for x in census_members),
            sorted("%s|%s" % x for x in red_members))
    # ---- P1 ----
    for (cfg, k) in sorted(set(census_members) | set(red_members)):
        key = "%s|%s" % (cfg, k)
        vs = cv.get((cfg, k), [])
        c_res = all(v["coverage"]["slot_resolved"] for v in vs) if vs else False
        c_g = sorted({g["cause"] for v in vs for g in v["coverage"]["gaps"]})
        r = F["p1"].get(key)
        if r is None:
            add("p1", key, {"slot_resolved": c_res, "gap_causes": c_g}, None, "variant missing on re-derivation side")
            continue
        if c_res != r["slot_resolved"]:
            add("p1.slot_resolved", key, c_res, r["slot_resolved"])
        if c_g != sorted(r["gap_causes"]):
            add("p1.gap_causes", key, c_g, sorted(r["gap_causes"]))
    # ---- P2 ----
    cp2 = C["metrics"]["p2"]
    for cfg in MAIN:
        per_var = sum(v.get("p2_fma", 0) for (c, k), vs in cv.items() if c == cfg for v in vs)
        if (cp2.get(cfg, 0) > 0) != (F["p2"].get(cfg, 0) > 0) or cp2.get(cfg, 0) != F["p2"].get(cfg, 0):
            add("p2", cfg, cp2.get(cfg), F["p2"].get(cfg))
    # ---- P3(b) ----
    c3b = sorted("%s|%s|%s" % (c, k, ic) for (c, k), vs in cv.items() if (c, k) in census_members
                 for v in vs for ic in v["p3"].get("b", []))
    c3b = sorted(set(c3b))
    if c3b != sorted(F["p3b"]):
        add("p3b", "all", c3b, F["p3b"])
    # ---- P3(c) by header address ----
    p3c_rows = []
    for (cfg, k) in sorted(set(census_members) | set(red_members)):
        key = "%s|%s" % (cfg, k)
        vs = cv.get((cfg, k), [])
        c_flag = {}
        c_loops = {}
        for v in vs:
            ids = set(v["p3"].get("c", []))
            for L in v.get("loops", []):
                hk = hdr_key(L["header"])
                c_loops[hk] = L
                if L["id"] in ids:
                    c_flag[hk] = L["id"]
        r_flag, r_loops = {}, {}
        for b in (1, 2):
            dv = D["variants"].get("%s|b%d|%s" % (cfg, b, k))
            if not dv:
                continue
            for L in dv.get("loops", []):
                hk = hdr_key(L["header"])
                r_loops[hk] = L
                if L["flagged"]:
                    r_flag[hk] = L["id"]
        for hk in sorted(set(c_flag) | set(r_flag)):
            cl, rl = c_loops.get(hk), r_loops.get(hk)
            row = {"variant": key, "header": "%d:0x%x" % hk, "census_id": cl["id"] if cl else None,
                   "rederive_id": rl["id"] if rl else None,
                   "census_flagged": hk in c_flag, "rederive_flagged": hk in r_flag,
                   "census_lanes": cl.get("acc_lanes_emitted") if cl else None,
                   "census_bound": cl.get("bound_used") if cl else None,
                   "census_rule": cl.get("bound_rule") if cl else None,
                   "census_source": (cl.get("source_loop") if cl else None),
                   "rederive_lanes": rl.get("acc_lanes_emitted") if rl else None,
                   "rederive_bound": rl.get("bound") if rl else None,
                   "rederive_rule": rl.get("bound_rule") if rl else None,
                   "rederive_source": [rl.get("source_header"), rl.get("source_latch")] if rl else None}
            p3c_rows.append(row)
            if (hk in c_flag) != (hk in r_flag):
                add("p3c", "%s@%s" % (key, row["header"]), hk in c_flag, hk in r_flag,
                    "census lanes %s bound %s; re-derivation lanes %s bound %s" % (
                        row["census_lanes"], row["census_bound"], row["rederive_lanes"], row["rederive_bound"]))
        # loop inventory (descriptive)
        if set(c_loops) != set(r_loops):
            rows.append({"variant": key, "loops_only_census": ["%d:0x%x" % h for h in sorted(set(c_loops) - set(r_loops))],
                         "loops_only_rederivation": ["%d:0x%x" % h for h in sorted(set(r_loops) - set(c_loops))]})
    # ---- P3(d1) ----
    for cfg in MAIN:
        vs = cv.get((cfg, "hx_kernels_scalar:act_quantize_q8"), [])
        cd = "pass" if vs and all(v["p3"].get("d1") == "pass" for v in vs) else "not pass"
        rd = F["p3d1"].get(cfg)
        if (cd == "pass") != (rd == "pass"):
            add("p3d1", cfg, cd, rd)
    # ---- P4, P5, baseline ----
    cmp_num = {"u_all": C["metrics"]["p4_u_all"], "p5_iclass": C["metrics"]["p5_iclass"],
               "p5_opclass": C["metrics"]["secondary"].get("p5_opclass"),
               "b_iform": C["baseline"]["b_iform"], "b_mnem": C["baseline"]["b_mnem"], "t_forms": C["baseline"]["t_forms"]}
    for k, v in cmp_num.items():
        if v != F[k]:
            add(k, k, v, F[k])
    c_iforms = sorted({f for (c, k), vs in cv.items() if (c, k) in census_members for v in vs for f in v["iforms"]})
    if c_iforms != F["iforms"]:
        add("iforms", "set", {"only_census": sorted(set(c_iforms) - set(F["iforms"]))},
            {"only_rederivation": sorted(set(F["iforms"]) - set(c_iforms))})
    c_fps = sorted(C["metrics"]["secondary"].get("fp_sensitive_iclasses") or
                   {ic for (c, k), vs in cv.items() if (c, k) in census_members for v in vs for ic in v["fp_sensitive"]})
    if c_fps != F["fp_sensitive_iclasses"]:
        add("fp_sensitive_iclasses", "set", {"only_census": sorted(set(c_fps) - set(F["fp_sensitive_iclasses"]))},
            {"only_rederivation": sorted(set(F["fp_sensitive_iclasses"]) - set(c_fps))})
    # ---- secondary, descriptive comparisons (not V3 items) ----
    desc = []
    for (cfg, k) in sorted(set(census_members) & set(red_members)):
        vs = cv.get((cfg, k), [])
        for v in vs:
            dv = D["variants"].get("%s|b%d|%s" % (cfg, v["build_index"], k))
            if not dv or v.get("_normalised_from_builds"):
                continue
            ci, ri = v.get("n_instructions"), dv.get("n_instructions")
            cf, rf = set(v.get("iforms", {})), set(dv.get("iform_list", []))
            cc = [c["symbol"] if isinstance(c, dict) else c for c in v.get("closure", [])]
            rc = [c[0] for c in dv.get("closure", [])]
            if ci != ri or cf != rf or sorted(cc) != sorted(rc) or v.get("attribution") != dv.get("attribution"):
                desc.append({"variant": "%s|b%d|%s" % (cfg, v["build_index"], k), "n_instructions": [ci, ri],
                             "iforms_only_census": sorted(cf - rf), "iforms_only_rederivation": sorted(rf - cf),
                             "closure": [sorted(cc), sorted(rc)], "attribution": [v.get("attribution"), dv.get("attribution")]})
    # ---- rederivation block for judge.py (PROCEDURE.md section 4) ----
    figs = {"u_all": F["u_all"], "p5_iclass": F["p5_iclass"]}
    for key, p in F["p1"].items():
        cfg, k = key.split("|", 1)
        flagged = bool(F["p3c"].get(key)) or any(x.startswith(key + "|") for x in F["p3b"]) or \
            (k == "hx_kernels_scalar:act_quantize_q8" and F["p3d1"].get(cfg) != "pass")
        n_fma = 0
        for b in (1, 2):
            dv = D["variants"].get("%s|b%d|%s" % (cfg, b, k))
            if dv:
                n_fma = max(n_fma, dv.get("p2", 0))
        flagged = flagged or n_fma > 0
        figs[key] = {"flagged": flagged, "gap_causes": sorted(p["gap_causes"])}
    block = {"present": True, "matches": not mism, "mismatches": mism, "figures": figs,
             "label": "same family (Claude), independent context",
             "figures_sha256": sha(a.figures), "procedure": "experiments/x0-census/rederive/PROCEDURE.md"}
    C2 = dict(C)
    C2["rederivation"] = block
    with open(a.out_census, "w", newline="\n") as f:
        json.dump(C2, f, indent=1)
    comp = {"matches": not mism, "n_mismatches": len(mism), "mismatches": mism, "p3c_rows": p3c_rows,
            "compile_failed_from_builds": sorted("%s|%s" % x for x in failed),
            "loop_inventory_differences": rows, "variant_differences_descriptive": desc,
            "inputs": {"figures.json": sha(a.figures), "rederive_detail.json": sha(a.detail),
                       "census.json": sha(a.census)}}
    with open(a.out_comparison, "w", newline="\n") as f:
        json.dump(comp, f, indent=1)
    print("mismatches:", len(mism))
    for m in mism:
        print(" ", m["kind"], m["key"], "census=", json.dumps(m["census"])[:200], "rederive=",
              json.dumps(m["rederivation"])[:200], m["note"])
    print("descriptive variant differences:", len(desc), "loop inventory differences:", len(rows))


if __name__ == "__main__":
    main()
