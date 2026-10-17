"""flag_analysis.py OLD_SCRIPTS NEW_SCRIPTS -- every P3(c)-flagged loop of the first re-run, analysed with the pinned
x0_loops.py of commit 2191ff8 (before) and with the fixed one (after): acc_lanes_emitted, partial-result cycles, and
the dependency-breaking idioms in the loop body on the cycle's registers. Laptop, on decodes fetched from the desktop
(NON-Hearth). Run from the scratch directory."""
import importlib.util, inspect, json, os, sys, re
def load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(path, "x0_loops.py"))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
OLD, NEW = load(sys.argv[1], "x0_loops_old"), load(sys.argv[2], "x0_loops_new")
CASES = [("R2", "r2/A/decode", "A:hx_kernels_scalar:act_quantize_q8", "L9_90"),
         ("R2", "r2/B-cmake/decode", "B-cmake:hx_kernels_scalar:act_quantize_q8", "L23_761"),
         ("R2", "r2/B-cmake/decode", "B-cmake:k_avx2:matmul[Q8]", "L20_3c8"),
         ("R2", "r2/B-cmake/decode", "B-cmake:k_avx2:matmul[Q4]", "L20_3c8"),
         ("R2", "r2/C/decode", "C:hx_kernels_scalar:act_quantize_q8", "L1_70"),
         ("R2", "r2/C/decode", "C:k_avx2:act_quantize_q8", "L1_1e7"),
         ("R2", "r2/D/decode", "D:hx_kernels_scalar:act_quantize_q8", "L2_f9d"),
         ("R2", "r2/D/decode", "D:k_avx2:matmul[Q8]", "L2_137a"),
         ("R2", "r2/D/decode", "D:k_avx2:matmul[Q4]", "L2_137a"),
         ("R1", "r1/B-cmake/smoke_dispatch.c/decode", "B-cmake:sd_table:matmul[3]", "L9_134"),
         ("R1", "r1/B-cmake/smoke_dispatch.c#scalar/decode", "B-cmake:sd_table:matmul[3]", "L9_126"),
         ("R1", "r1/C/smoke_dispatch.c/decode", "C:sd_table:matmul[3]", "L1_78"),
         ("R1", "r1/C/smoke_dispatch.c#scalar/decode", "C:sd_table:matmul[3]", "L1_68"),
         ("R1", "r1/D/smoke_dispatch.c/decode", "D:sd_table:matmul[3]", "L2_2b1"),
         ("R1", "r1/D/smoke_dispatch.c#scalar/decode", "D:sd_table:matmul[3]", "L2_283"),
         ("R1 earlier flag", "r1/B-cmake/smoke_dispatch.c/decode", "B-cmake:sd_table:matmul[0]", "L19_2a0"),
         ("R1 earlier flag", "r1/B-cmake/smoke_dispatch.c/decode", "B-cmake:sd_table:matmul[0]", "L19_1ca"),
         ("R1 earlier flag", "r1/B-cmake/smoke_dispatch.c/decode", "B-cmake:sd_table:matmul[0]", "L19_123"),
         ("R1 earlier flag", "r1/D/smoke_dispatch.c/decode", "D:sd_table:matmul[0]", "L2_10c0"),
         ("R1 earlier flag", "r1/D/smoke_dispatch.c/decode", "D:sd_table:matmul[0]", "L2_f34"),
         ("R1 earlier flag", "r1/D/smoke_dispatch.c/decode", "D:sd_table:matmul[0]", "L2_e66")]
cache = {}
for run, dec, vid, lid in CASES:
    key = (dec, vid)
    if key not in cache:
        insts = {}
        with open(os.path.join(dec, "instructions.jsonl")) as fh:
            for line in fh:
                r = json.loads(line)
                if r.get("role") == "reachable" and r["variant"] == vid:
                    insts[(r["section"], r["offset"])] = r
        cache[key] = insts
    insts = cache[key]
    succ = {k: [tuple(s) for s in i.get("succ", [])] for k, i in insts.items()}
    roots = [k for k, i in insts.items() if i.get("entry")] + sorted({tuple(i["call"]) for i in insts.values() if i.get("call") and tuple(i["call"]) in insts})
    out = {}
    for tag, X in (("before", OLD), ("after", NEW)):
        X.ABI["current"] = "elf" if vid.split(":")[0] in ("C", "D") else "coff"
        seen = set()
        for root in roots:
            loops, preds = X.natural_loops(root, succ)
            for lp in loops:
                if lp["header"] in seen: continue
                seen.add(lp["header"])
                if "L%d_%x" % lp["header"] != lid: continue
                info = X.analyse_loop(lp, insts, succ, preds)
                out[tag] = (info["acc_lanes_emitted"], [(c["members"], c["lanes"]) for c in info["partial_result_cycles"]])
                if tag == "before":
                    regs = {m for c in info["partial_result_cycles"] for m in c["members"]}
                    idi = []
                    for n in sorted(lp["body"]):
                        i = insts[n]
                        if NEW.dependency_breaking(i) and (NEW.uses_defs(i)[1] & regs):
                            idi.append("%x: %s" % (n[1], i.get("disasm")))
                    out["idioms"] = idi
    print("%-16s %-44s %-8s before %-3s %-40s after %-3s %s" % (run, vid, lid, out["before"][0], json.dumps(out["before"][1]),
                                                              out["after"][0], json.dumps(out["after"][1])))
    print("%-16s   idioms writing the cycle's registers (before): %s" % ("", "; ".join(out["idioms"]) or "none"))
