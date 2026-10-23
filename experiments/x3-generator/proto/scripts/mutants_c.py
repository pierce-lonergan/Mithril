"""Mutation adequacy of the C bit-identity harness: print each planted lane program (tests/planted.py)
as C in place of its generated variant, run the quick corpus, and record whether outputs or guard
pages expose it. This measures the harness, not the generator.

  python -I scripts/mutants_c.py --hearth CLONE --llvm LLVM_DIR --scratch DIR [--out JSON]
"""

import argparse
import copy
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import bitid  # noqa: E402
import planted  # noqa: E402
from x3gen.core import emit, lower  # noqa: E402
from x3gen.core.lp import Program  # noqa: E402
from x3gen.core.printer import PrintError, print_program  # noqa: E402
from x3gen.hearth import meaning  # noqa: E402

KIDX = {"scalar": 3, "avx2": 4, "avx512": 5}


def program_with(isa, fmt, mutant):
    """The generated translation unit for isa, with fmt's function replaced by the mutant."""
    sched = bitid.SCHED[isa]
    funcs = []
    for f2 in ("q8", "q4"):
        k = meaning.MEANINGS[f2]
        name = k.slot.name_pattern.format(fmt=f2, isa=isa)
        if f2 == fmt:
            m = copy.deepcopy(mutant)
            m.name = name
            funcs.append(m)
        else:
            funcs.append(lower.lower(sched(k), name))
    slot = meaning.MEANINGS["q8"].slot
    prog = Program(
        isa,
        slot.simd_guard if isa != "scalar" else None,
        ('"%s"' % slot.header, "<string.h>"),
        ["#include <immintrin.h>"] if isa != "scalar" else [],
        funcs,
        ["/* planted mutant: not a generated variant */"],
    )
    return print_program(prog)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hearth", required=True)
    ap.add_argument("--llvm", required=True)
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    hearth, llvm, sdir = pathlib.Path(a.hearth), pathlib.Path(a.llvm), pathlib.Path(a.scratch)
    if sdir.exists():
        shutil.rmtree(sdir)
    (sdir / "bitid" / "shim").mkdir(parents=True)
    for p in (ROOT / "bitid").rglob("*"):
        if p.is_file():
            (sdir / "bitid" / p.relative_to(ROOT / "bitid")).write_bytes(p.read_bytes())
    bitid.stage(hearth, sdir)
    rows = []
    for pid, desc, isa, fmt, fn in planted.PLANTED:
        row = {"id": pid, "what": desc, "variant": "%s/%s" % (isa, fmt)}
        if fn is None:
            row["c_harness"] = "n/a (a precondition change, not a program change)"
            rows.append(row)
            continue
        k, s, f = planted.variant(isa, fmt)
        mf = copy.deepcopy(f)
        fn(mf, s)
        try:
            text = program_with(isa, fmt, mf)
        except (PrintError, KeyError, IndexError) as e:
            row["c_harness"] = "not printable: %s" % str(e)[:120]
            rows.append(row)
            continue
        if "/* (float)((double)" in text:
            row["c_harness"] = "not printable (test-only entry has no single-intrinsic spelling)"
            rows.append(row)
            continue
        if (sdir / "gen").exists():
            shutil.rmtree(sdir / "gen")
        bitid.generate(sdir / "gen")
        (sdir / "gen" / ("x3_q_%s.c" % isa)).write_bytes(text.encode())
        try:
            dll, _ = bitid.build(llvm, sdir, "clangcl_B", dllname="m%02d.dll" % pid)
        except SystemExit as e:
            row["c_harness"] = "does not compile: %s" % str(e)[-160:]
            rows.append(row)
            continue
        d = bitid.load(dll)
        c = bitid.corpus(d, True, 7)
        kname = d.x3t_kernel_name(KIDX[isa]).decode()
        bad = sum(c["mismatches"][kname].values())
        row["c_harness"] = "detected" if bad or c["faults"] else "NOT detected"
        row["mismatching_words"] = bad
        row["faults"] = len(c["faults"])
        rows.append(row)
        print(pid, desc[:50], row["c_harness"], bad, len(c["faults"]), flush=True)
    out = {
        "what": "C harness mutation adequacy (quick corpus, clangcl_B)",
        "rows": rows,
        "detected": sum(r.get("c_harness") == "detected" for r in rows),
        "not_detected": [r["id"] for r in rows if r.get("c_harness") == "NOT detected"],
    }
    text = json.dumps(out, indent=1) + "\n"
    if a.out:
        pathlib.Path(a.out).write_bytes(text.encode())
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}))


if __name__ == "__main__":
    main()
