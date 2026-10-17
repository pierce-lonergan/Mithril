"""R02/R03 (MAX-FOLD) by two further routes, after the default Z3 strategy timed out on the concrete
64-input pattern (z3_rules.py, 1,200 s):

  (1) the same concrete-pattern claim (identical encoding, built by z3_rules.build) solved with an explicit
      bit-blasting tactic: simplify -> fpa2bv -> simplify -> bit-blast -> sat;
  (2) the lemmas of the written proof (RULES.md R02 "written proof from the lemmas"), each a 2- or 3-input
      query on the table encoding:
        L1 meaning step  : for sign-0 v and sign-0 non-NaN m: (fp.gt(v, m) ? v : m) == umaxN(v, m)
        L2 chain step    : for sign-0 v and sign-0 non-NaN m: MAXPS(v, m)            == umaxN(v, m)
        L3 tree step     : for sign-0 non-NaN a, b:           MAXPS(a, b)            == umax(a, b)
        L4 closure       : umaxN(v, m) is sign-0 and non-NaN whenever m is
      where umaxN(v, m) = (v is not NaN and v >u m) ? v : m and umax is unsigned max. With L1-L4 the
      meaning and the realization both reduce, step by step, to the unsigned maximum over the non-NaN
      elements (starting from +0), which is independent of order because unsigned max is associative and
      commutative.

  python -B z3_fold.py --sem-root DIR --out fold.json [--timeout 1500] [--skip-concrete] [--smt2-dir DIR]

Revised 2026-10-16 after review (finding R2-7): every lemma query is exported as SMT-LIB 2 with --smt2-dir
(file fold_<name>.smt2) and its sha256 is recorded, so the lemmas can be replayed by hash with
second_solver.py. The composition of L1-L6 into the R02/R03 claim is written out in R02-R03-proof.md.
"""
import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=float, default=1500)
    ap.add_argument("--skip-concrete", action="store_true")
    ap.add_argument("--smt2-dir")
    a = ap.parse_args(argv)
    if a.smt2_dir:
        os.makedirs(a.smt2_dir, exist_ok=True)

    def export(name, s):
        blob = s.to_smt2()
        if a.smt2_dir:
            fn = "fold_" + name.split(" ")[0] + ".smt2"
            with open(os.path.join(a.smt2_dir, fn), "w", newline="\n") as f:
                f.write(blob)
        return hashlib.sha256(blob.encode()).hexdigest()
    sys.path.insert(0, HERE)
    import z3_rules
    z3, Q = z3_rules.build(a.sem_root)
    from semantics import smt_encoding as se
    import smt_table as st
    fp, is_nan, maxmin = se.fp, se.is_nan, se.maxmin
    res = {"z3_version": z3.get_version_string(), "timeout_s": a.timeout, "results": []}

    def record(name, verdict, dt, extra=None):
        r = {"name": name, "verdict": verdict, "seconds": round(dt, 3)}
        if extra:
            r.update(extra)
        res["results"].append(r)
        print("%-34s %-18s %9.3f s %s" % (name, verdict, dt, extra or ""), flush=True)
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)

    v, m, b = z3.BitVecs("v m b", 32)
    sign0 = lambda t: z3.Extract(31, 31, t) == 0
    umaxN = lambda x, y: z3.If(z3.And(z3.Not(is_nan(x)), z3.UGT(x, y)), x, y)
    lemmas = {
        "L1 meaning step": z3.Implies(z3.And(sign0(v), sign0(m), z3.Not(is_nan(m))),
                                      z3.If(z3.fpGT(fp(v), fp(m)), v, m) == umaxN(v, m)),
        "L2 chain step": z3.Implies(z3.And(sign0(v), sign0(m), z3.Not(is_nan(m))), maxmin(True, v, m) == umaxN(v, m)),
        "L3 tree step": z3.Implies(z3.And(sign0(v), sign0(b), z3.Not(is_nan(v)), z3.Not(is_nan(b))),
                                   maxmin(True, v, b) == z3.If(z3.UGT(v, b), v, b)),
        "L4 closure": z3.Implies(z3.And(sign0(v), sign0(m), z3.Not(is_nan(m))),
                                 z3.And(sign0(umaxN(v, m)), z3.Not(is_nan(umaxN(v, m))))),
        "L5 start value +0 is sign-0, non-NaN": z3.And(sign0(z3.BitVecVal(0, 32)), z3.Not(is_nan(z3.BitVecVal(0, 32)))),
        "L6 abs is sign-0": sign0(v & z3.BitVecVal(0x7FFFFFFF, 32)),
        # L1 with the meaning's C `a > amax` as the TABLE's relation (fp_ops.relation, as hearth_kernels._c_gt
        # evaluates it; smt_table.relation, DAZ = 0) instead of SMT-LIB fp.gt (added 2026-10-16, cf. finding R2-2)
        "L1t meaning step, table relation": z3.Implies(z3.And(sign0(v), sign0(m), z3.Not(is_nan(m))),
                                                       z3.If(st.relation(v, m, z3.BoolVal(False)) == z3.BitVecVal(4, 4), v, m)
                                                       == umaxN(v, m)),
    }
    for name, claim in lemmas.items():
        s = z3.Solver()
        s.set("timeout", int(a.timeout * 1000))
        s.add(z3.Not(claim))
        sha = export(name, s)
        t = time.perf_counter()
        r = s.check()
        record(name, {"unsat": "PROVED", "sat": "COUNTEREXAMPLE", "unknown": "UNKNOWN"}[str(r)], time.perf_counter() - t,
               {"query_sha256": sha, "smt2": ("fold_" + name.split(" ")[0] + ".smt2") if a.smt2_dir else None})
    if not a.skip_concrete:
        tac = z3.Then("simplify", "fpa2bv", "simplify", "bit-blast", "sat")
        for name in ("R02", "R03"):
            what, claim = Q[name]
            s = tac.solver()
            s.set("timeout", int(a.timeout * 1000))
            s.add(z3.Not(claim))
            t = time.perf_counter()
            r = s.check()
            record(name + " concrete pattern, bit-blast+sat tactic",
                   {"unsat": "PROVED", "sat": "COUNTEREXAMPLE", "unknown": "UNKNOWN(timeout)"}[str(r)],
                   time.perf_counter() - t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
