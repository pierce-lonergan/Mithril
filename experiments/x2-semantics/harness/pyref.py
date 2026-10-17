"""The Python oracle: predictions for a vectors file computed with the reference semantics
(semantics/table.py `_sem` and `write_full`), in the results format. FUZZ-DESIGN §1 uses it on a sample
and to validate the C interpreter (validate_interp.py).

  python -I pyref.py --sem-root DIR --manifest stubs_manifest.json VEC OUT
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vecfmt  # noqa: E402

MASK32 = 0xFFFFFFFF


def load(sem_root, manifest_path):
    sys.path.insert(0, sem_root)
    from semantics import fpenv, table  # noqa: F401
    with open(manifest_path, "rb") as f:
        man = json.load(f)
    return table, fpenv, man


def predict(table, fpenv, stub, c):
    """(status, Out) for one case, from the reference semantics."""
    e = table.ENTRIES[stub["entry_index"]]
    opt = stub["opts"]
    b = e["sem"]["builder"]
    k = None if opt["mask"] == "plain" else c.k
    z = opt["mask"] == "zero"
    o = vecfmt.Out()
    if b in ("int2", "int_acc"):
        if b == "int2":
            res = e["_sem"](c.src1, c.src2, k=k, z=z, dst=c.dst_old)
        else:
            res = e["_sem"](c.dst_old, c.src1, c.src2, k=k, z=z)
        o.dst = table.write_full(e, res, c.dst_old)
        o.mxcsr = c.mxcsr
        return vecfmt.ST_OK, o
    try:
        env = fpenv.Env(c.mxcsr, er=opt["er"], sae=opt["sae"])
    except fpenv.UnmodeledEnvironment:
        return vecfmt.ST_UNMODELED, o
    if b == "packed_fp2":
        res, fl = e["_sem"](c.src1, c.src2, env, k=k, z=z, dst=c.dst_old,
                            bcast_src2=(c.src2 & MASK32) if opt["bcast"] else None)
        o.dst = table.write_full(e, res, c.dst_old)
    elif b == "scalar_fp2":
        s1 = c.dst_old if e["encoding"] == "legacy" else c.src1
        res, fl = e["_sem"](s1, c.src2, env, k=k, z=z, dst=c.dst_old)
        o.dst = table.write_full(e, res, c.dst_old)
    elif b == "packed_fp1":
        res, fl = e["_sem"](c.src1, env, k=k, z=z, dst=c.dst_old)
        o.dst = table.write_full(e, res, c.dst_old)
    elif b == "cmp_k":
        o.kdst, fl = e["_sem"](c.src1, c.src2, opt["imm"], env, k=k)
    elif b == "cmp_vec":
        res, fl = e["_sem"](c.src1, c.src2, opt["imm"], env)
        o.dst = table.write_full(e, res, c.dst_old)
    elif b == "comis":
        rf, fl = e["_sem"](c.src1, c.src2, env)
        o.rflags = (rf["ZF"] << 6) | (rf["PF"] << 2) | rf["CF"] | (rf["OF"] << 11) | (rf["SF"] << 7) | (rf["AF"] << 4)
    elif b == "cvt_f2i_gpr":
        o.gpr, fl = e["_sem"](c.src1, env)
    elif b == "cvt_i2f_scalar":
        up = c.dst_old if e["encoding"] == "legacy" else c.src1
        res, fl = e["_sem"](up, c.gpr_in & MASK32, env)
        o.dst = table.write_full(e, res, c.dst_old)
    else:
        raise KeyError(b)
    o.mxcsr = env.mxcsr_after(fl)
    return vecfmt.ST_OK, o


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-root", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("vectors")
    ap.add_argument("out")
    a = ap.parse_args(argv)
    table, fpenv, man = load(a.sem_root, a.manifest)
    info, recs = vecfmt.read_vectors(a.vectors)
    stubs = man["stubs"]
    outs = []
    for meta, c in recs:
        st, o = predict(table, fpenv, stubs[meta["stub"]], c)
        outs.append((meta["index"], st, o))
    n = vecfmt.write_results(a.out, outs, "interp-py", vecfmt.file_sha256(a.vectors), info["manifest"],
                             table.bundle_hash())
    print(json.dumps({"records": n}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
