"""Second-solver route (RULES.md sec. 1): replay each SMT-LIB 2 query written by z3_rules.py --smt2-dir
through cvc5 (PyPI wheel, version printed). Each query asserts the negation of a rule, so unsat = the rule
holds. Queries that use Z3's non-standard fp.to_ieee_bv are not replayed (reported as such).

  python -B second_solver.py --smt2-dir DIR --out cvc5.json [--timeout 1200]
"""
import argparse
import glob
import json
import os
import sys
import time


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--smt2-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=float, default=1200)
    ap.add_argument("--names", help="comma list of query names to replay (default: all)")
    ap.add_argument("--long", default="", help="comma list of names that get --long-timeout")
    ap.add_argument("--long-timeout", type=float, default=1200)
    a = ap.parse_args(argv)
    want = set(a.names.split(",")) if a.names else None
    long_ = set(a.long.split(",")) if a.long else set()
    import cvc5
    res = {"cvc5_version": None, "timeout_s": a.timeout, "rules": []}
    for path in sorted(glob.glob(os.path.join(a.smt2_dir, "*.smt2"))):
        name = os.path.basename(path)[:-5]
        if want is not None and name not in want:
            continue
        tmo = a.long_timeout if name in long_ else a.timeout
        with open(path) as f:
            text = f.read()
        if "fp.to_ieee_bv" in text:
            res["rules"].append({"rule": name, "cvc5": "NOT RUN (query uses Z3's fp.to_ieee_bv)"})
            print("%-22s NOT RUN (fp.to_ieee_bv)" % name, flush=True)
            continue
        tm = cvc5.TermManager()
        s = cvc5.Solver(tm)
        v = s.getVersion()
        res["cvc5_version"] = v.decode() if isinstance(v, bytes) else str(v)
        s.setOption("tlimit-per", str(int(tmo * 1000)))
        s.setOption("fp-exp", "true")
        p = cvc5.InputParser(s)
        p.setStringInput(cvc5.InputLanguage.SMT_LIB_2_6, text, name)
        sm = p.getSymbolManager()
        out, t0, err = [], time.perf_counter(), None
        try:
            while True:
                cmd = p.nextCommand()
                if cmd.isNull():
                    break
                r = cmd.invoke(s, sm)
                if r:
                    out.append(r.strip())
        except Exception as e:          # noqa: BLE001 - record parser/solver errors as results
            err = str(e)[:300]
        dt = time.perf_counter() - t0
        verdict = "ERROR" if err else {"unsat": "PROVED", "sat": "COUNTEREXAMPLE"}.get(out[-1] if out else "", "UNKNOWN(" + (out[-1] if out else "") + ")")
        res["rules"].append({"rule": name, "cvc5": verdict, "seconds": round(dt, 3), "timeout_s": tmo, "output": out[-3:],
                             "error": err})
        print("%-22s %-18s %9.3f s %s" % (name, verdict, dt, err or ""), flush=True)
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
