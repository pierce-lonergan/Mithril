"""Make and check the X3 seam patch (DESIGN 6) against Hearth b5d3f14, in scratch only.

  python -I scripts/seam.py --hearth CLONE --llvm LLVM_DIR --scratch DIR [--write-patch PATH]

1. Builds x3-seam.patch from DESIGN 6's text: the Q8/Q4 entries of the three hx_kernels tables go
   through X3_Q8/X3_Q4 macros, which name the generated functions only under HEARTH_X3_GEN, plus the
   CMake option. Test files are untouched.
2. git apply --check on a pristine copy.
3. Inertness: with HEARTH_X3_GEN undefined, the patched quant.c, quant_avx2.c and quant_avx512.c
   compile (X0 configuration B flags) to objects byte-identical to the pristine ones.
4. Activity: with HEARTH_X3_GEN defined, the AVX2 and AVX-512 tables, linked with the generated
   objects, hold the generated functions (pointer equality, run time); the scalar table's
   initializer relocations name the generated scalar functions (object level, since linking quant.c
   needs the rest of Hearth).
"""

import argparse
import ctypes
import difflib
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import bitid  # noqa: E402

TABLES = {
    "engine/src/quant.c": (
        "scalar",
        "const hx_kernels hx_kernels_scalar = {",
        "mm_q8_scalar, mm_q4_scalar",
    ),
    "engine/src/quant_avx2.c": (
        "avx2",
        "static const hx_kernels k_avx2 = {",
        "mm_q8_avx2, mm_q4_avx2",
    ),
    "engine/src/quant_avx512.c": (
        "avx512",
        "static const hx_kernels k_avx512 = {",
        "mm_q8_avx512, mm_q4_avx512",
    ),
}
CMAKE_BEFORE = """# X3 scratch only (Mithril experiments/x3-generator): dispatch generated Q4/Q8 kernels.
option(HEARTH_X3_GEN "X3 scratch only: dispatch generated Q4/Q8 kernels" OFF)
set(X3_GEN_DIR "" CACHE PATH "x3gen output directory")
if(HEARTH_X3_GEN)
  list(APPEND CORE_SOURCES ${X3_GEN_DIR}/x3_q_scalar.c)
  if(X86)
    list(APPEND CORE_SOURCES ${X3_GEN_DIR}/x3_q_avx2.c ${X3_GEN_DIR}/x3_q_avx512.c)
    if(MSVC)
      set_source_files_properties(${X3_GEN_DIR}/x3_q_avx2.c PROPERTIES COMPILE_OPTIONS "/arch:AVX2")
      set_source_files_properties(${X3_GEN_DIR}/x3_q_avx512.c PROPERTIES COMPILE_OPTIONS "/arch:AVX512")
    else()
      set_source_files_properties(${X3_GEN_DIR}/x3_q_avx2.c PROPERTIES COMPILE_OPTIONS "-mavx2;-mfma;-mf16c")
      set_source_files_properties(${X3_GEN_DIR}/x3_q_avx512.c PROPERTIES COMPILE_OPTIONS
        "-mavx512f;-mavx512bw;-mavx512vl;-mavx512vnni;-mavx2;-mfma;-mf16c")
    endif()
  endif()
endif()
"""
CMAKE_AFTER = """if(HEARTH_X3_GEN)
  target_compile_definitions(hearth_core PRIVATE HEARTH_X3_GEN)
  target_include_directories(hearth_core PRIVATE ${X3_GEN_DIR})
endif()
"""


def seam_block(isa):
    return (
        "#ifdef HEARTH_X3_GEN\n"
        '#  include "x3_gen.h"\n'
        "#  define X3_Q8 hx_x3_mm_q8_%s\n"
        "#  define X3_Q4 hx_x3_mm_q4_%s\n"
        "#else\n"
        "#  define X3_Q8 mm_q8_%s\n"
        "#  define X3_Q4 mm_q4_%s\n"
        "#endif\n"
    ) % (isa, isa, isa, isa)


def patch_text(orig):
    out = {}
    for rel, (isa, head, pair) in TABLES.items():
        s = orig[rel]
        assert s.count(head) == 1 and s.count(pair) == 1, rel
        s = s.replace(head, seam_block(isa) + head).replace(pair, "X3_Q8, X3_Q4")
        out[rel] = s
    c = orig["CMakeLists.txt"]
    anchor = "add_library(hearth_core OBJECT ${CORE_SOURCES})\n"
    inc = "target_include_directories(hearth_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/engine/include ${SRC})\n"
    assert c.count(anchor) == 1 and c.count(inc) == 1
    c = c.replace(anchor, CMAKE_BEFORE + anchor).replace(inc, inc + CMAKE_AFTER)
    out["CMakeLists.txt"] = c
    return out


def unified(orig, new):
    lines = []
    for rel in sorted(new):
        a = orig[rel].splitlines(keepends=True)
        b = new[rel].splitlines(keepends=True)
        d = list(difflib.unified_diff(a, b, "a/" + rel, "b/" + rel, n=3))
        lines.append("diff --git a/%s b/%s\n" % (rel, rel))
        lines.extend(d)
    return "".join(lines)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hearth", required=True)
    ap.add_argument("--llvm", required=True)
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--write-patch", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    hearth, llvm, sdir = pathlib.Path(a.hearth), pathlib.Path(a.llvm), pathlib.Path(a.scratch)
    if sdir.exists():
        shutil.rmtree(sdir)
    sdir.mkdir(parents=True)
    res = {"what": "X3 seam patch check (DESIGN 6), laptop, clang-cl 23.1.3 (X0 config B flags)"}
    head = bitid.run(["git", "-C", str(hearth), "rev-parse", "HEAD"]).strip()
    assert head == bitid.PIN
    files = ["CMakeLists.txt"] + list(TABLES)
    orig = {rel: (hearth / rel).read_bytes().decode() for rel in files}
    new = patch_text(orig)
    patch = unified(orig, new)
    pbytes = patch.encode()
    res["patch_sha256"] = sha(pbytes)
    res["patch_lines"] = patch.count("\n")
    if a.write_patch:
        pathlib.Path(a.write_patch).write_bytes(pbytes)
    # pristine and patched trees (only what compiling needs)
    for tree, content in (("pristine", orig), ("patched", new)):
        root = sdir / tree
        for rel in ["engine/src/hx_quant.h", "engine/src/hx_platform.h", "engine/include/hearth.h"]:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_bytes((hearth / rel).read_bytes())
        for rel, text in content.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_bytes(text.encode())
    (sdir / "x3-seam.patch").write_bytes(pbytes)
    chk = subprocess.run(
        ["git", "apply", "--check", "-v", str(sdir / "x3-seam.patch")],
        cwd=str(sdir / "pristine"),
        capture_output=True,
        text=True,
    )
    res["git_apply_check"] = {"rc": chk.returncode, "log": (chk.stdout + chk.stderr).strip()[:400]}
    # shims (the laptop has no SDK); math functions declared for quant.c's elementwise ops
    shim = sdir / "shim"
    shim.mkdir()
    for p in (ROOT / "bitid" / "shim").glob("*.h"):
        (shim / p.name).write_bytes(p.read_bytes())
    (shim / "math.h").write_bytes(
        b"#ifndef X3_SHIM_MATH_H\n#define X3_SHIM_MATH_H\n"
        b"float fabsf(float); float sqrtf(float); float expf(float);\n"
        b"float sinf(float); float cosf(float);\n#endif\n"
    )
    gen = sdir / "gen"
    bitid.generate(gen)
    drv, base, arch = bitid.CONFIGS["clangcl_B"]
    exe = str(llvm / "bin" / "clang-cl.exe")

    def cc(tree, rel, extra, obj):
        src = sdir / tree / rel
        isa = {
            "engine/src/quant.c": "none",
            "engine/src/quant_avx2.c": "avx2",
            "engine/src/quant_avx512.c": "avx512",
        }.get(rel, "none")
        cmd = (
            [exe]
            + base
            + arch[isa]
            + extra
            + [
                "-I" + str(shim),
                "-I" + str(sdir / tree / "engine/src"),
                "/c",
                str(src),
                "/Fo" + str(obj),
            ]
        )
        log = bitid.run(cmd)
        return [l for l in log.splitlines() if "warning" in l and "c11atomics" not in l]

    odir = sdir / "obj"
    odir.mkdir()
    inert = {}
    for rel in TABLES:
        stem = pathlib.Path(rel).stem
        cc("pristine", rel, [], odir / (stem + ".pristine.obj"))
        cc("patched", rel, [], odir / (stem + ".off.obj"))
        a_, b_ = (odir / (stem + ".pristine.obj")).read_bytes(), (
            odir / (stem + ".off.obj")
        ).read_bytes()
        # COFF file header bytes 4..7 are the TimeDateStamp clang-cl writes without /Brepro
        same = a_[:4] + a_[8:] == b_[:4] + b_[8:]
        inert[rel] = {
            "identical_except_coff_timestamp": same,
            "byte_identical": a_ == b_,
            "pristine_sha256": sha(a_),
            "patched_off_sha256": sha(b_),
        }
    res["inert_when_off"] = inert
    active = {}
    for rel in TABLES:
        stem = pathlib.Path(rel).stem
        w = cc("patched", rel, ["-DHEARTH_X3_GEN", "-I" + str(gen)], odir / (stem + ".on.obj"))
        active[rel] = {"warnings": w}
    reloc = bitid.run([str(llvm / "bin" / "llvm-objdump.exe"), "-r", str(odir / "quant.on.obj")])
    active["engine/src/quant.c"]["table_relocations_name"] = sorted(
        set(re.findall(r"hx_x3_mm_q[48]_scalar", reloc))
    )
    # link the patched SIMD tables with the generated kernels and compare pointers at run time
    test_c = sdir / "seam_test.c"
    test_c.write_bytes(b"""#include "hx_quant.h"
#include "x3_gen.h"
__declspec(dllexport) int x3s_check(void) {
    int ok = 0;
    ok += hx_kernels_avx2_table()->matmul[HEARTH_Q8] == hx_x3_mm_q8_avx2;
    ok += hx_kernels_avx2_table()->matmul[HEARTH_Q4] == hx_x3_mm_q4_avx2;
    ok += hx_kernels_avx512_table()->matmul[HEARTH_Q8] == hx_x3_mm_q8_avx512;
    ok += hx_kernels_avx512_table()->matmul[HEARTH_Q4] == hx_x3_mm_q4_avx512;
    return ok;
}
""")
    objs = [odir / "quant_avx2.on.obj", odir / "quant_avx512.on.obj"]
    for name, isa in (
        ("x3_q_avx2.c", "avx2"),
        ("x3_q_avx512.c", "avx512"),
        ("x3_q_scalar.c", "none"),
    ):
        o = odir / (name + ".obj")
        bitid.run(
            [exe]
            + base
            + arch[isa]
            + [
                "-I" + str(shim),
                "-I" + str(sdir / "patched/engine/src"),
                "-I" + str(gen),
                "/c",
                str(gen / name),
                "/Fo" + str(o),
            ]
        )
        objs.append(o)
    o = odir / "seam_test.obj"
    bitid.run(
        [exe]
        + base
        + [
            "-I" + str(shim),
            "-I" + str(sdir / "patched/engine/src"),
            "-I" + str(gen),
            "/c",
            str(test_c),
            "/Fo" + str(o),
        ]
    )
    objs.append(o)
    o = odir / "rt.obj"
    bitid.run(
        [exe] + base + ["/clang:-fno-builtin", "/c", str(ROOT / "bitid" / "rt.c"), "/Fo" + str(o)]
    )
    objs.append(o)
    dll = odir / "seam.dll"
    bitid.run(
        [
            str(llvm / "bin" / "lld-link.exe"),
            "/nologo",
            "/DLL",
            "/NOENTRY",
            "/NODEFAULTLIB",
            "/OUT:" + str(dll),
        ]
        + [str(x) for x in objs]
    )
    d = ctypes.CDLL(str(dll))
    res["simd_tables_point_at_generated"] = "%d of 4" % d.x3s_check()
    res["active_when_on"] = active
    text = json.dumps(res, indent=1, sort_keys=True) + "\n"
    if a.out:
        pathlib.Path(a.out).write_bytes(text.encode())
    print(text)


if __name__ == "__main__":
    main()
