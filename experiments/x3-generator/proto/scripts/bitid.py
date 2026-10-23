"""Build and run the X3 prototype's bit-identity test on this machine (development data, not gate
data: DESIGN 10, prereg 4.9). Windows x64, LLVM for Windows, no MSVC/SDK needed.

  python -I scripts/bitid.py --hearth CLONE --llvm LLVM_DIR --scratch DIR [--quick] [--configs a,b]
                             [--seeds K] [--mode-every M]

Steps: pin check of the Hearth clone; stage Hearth sources into scratch (the scalar reference
kernels are extracted from quant.c by line range; nothing from Hearth enters the repository);
generate the six variants; compile and link a CRT-free DLL per flag configuration; scan the
objects for FMA, approximation and MXCSR instructions; run the corpus with every buffer between
no-access guard pages, and every M-th case also under seven non-default MXCSR modes, each x3
kernel against the same-ISA Hearth kernel; run the meaning differential (x3gen's interpreter
against the kernels); show, on one shape outside the output-map precondition (PRE6), that the
result then depends on the kernel's store order.
"""

import argparse
import ctypes
import hashlib
import json
import pathlib
import platform
import random
import re
import shutil
import struct
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from x3gen.core import emit, interp  # noqa: E402
from x3gen.core.ir import Store, iter_nodes  # noqa: E402
from x3gen.hearth import meaning  # noqa: E402
from x3gen.hearth.schedules import avx2, avx512, scalar  # noqa: E402

PIN = "b5d3f14a801d43bcb3b3c4ccf4efeca9d328e220"
BLOBS = {  # DESIGN 6 / prereg 2, [M, x3 track, 2026-10-16]; prefixes as recorded there
    "engine/src/quant.c": "e95496945c25",
    "engine/src/quant_avx2.c": "a2004d22fd50",
    "engine/src/quant_avx512.c": "9c7586b16e58",
    "engine/src/hx_quant.h": "df7e75e3e14f",
    "docs/NUMERICS.md": "7c558db51dd2",
}
# quant.c line ranges copied verbatim (b5d3f14): q_f16, q_rint, HX_CANON_NAN + q_canon,
# act_q8_scalar, mm_q8_scalar + mm_q4_scalar. Each range's first code line is checked.
EXTRACT = [
    (16, 35, "HX_INLINE float q_f16("),
    (44, 49, "HX_INLINE float q_rint("),
    (53, 65, "#define HX_CANON_NAN"),
    (323, 348, "static void act_q8_scalar("),
    (388, 427, "static void mm_q8_scalar("),
]
SCHED = {"scalar": scalar.schedule, "avx2": avx2.schedule, "avx512": avx512.schedule}
Q8, Q4 = 3, 4
NK = 6
PAGE = 4096


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode:
        raise SystemExit(
            "command failed (%d): %s\n%s\n%s"
            % (r.returncode, " ".join(map(str, cmd)), r.stdout, r.stderr)
        )
    return r.stdout + r.stderr


# ------------------------------------------------------------------ staging


def stage(hearth, sdir):
    head = run(["git", "-C", str(hearth), "rev-parse", "HEAD"]).strip()
    if head != PIN:
        raise SystemExit("Hearth clone is at %s, not %s" % (head, PIN))
    status = run(["git", "-C", str(hearth), "status", "--porcelain"]).strip()
    blobs = {}
    for path, pre in BLOBS.items():
        b = run(["git", "-C", str(hearth), "rev-parse", "%s:%s" % (PIN, path)]).strip()
        if not b.startswith(pre):
            raise SystemExit("blob mismatch for %s: %s" % (path, b))
        blobs[path] = b
    src = sdir / "hearth" / "engine" / "src"
    inc = sdir / "hearth" / "engine" / "include"
    src.mkdir(parents=True, exist_ok=True)
    inc.mkdir(parents=True, exist_ok=True)
    copied = {}
    for rel in (
        "engine/src/hx_quant.h",
        "engine/src/hx_platform.h",
        "engine/src/quant_avx2.c",
        "engine/src/quant_avx512.c",
        "engine/include/hearth.h",
    ):
        b = (hearth / rel).read_bytes()
        (sdir / "hearth" / rel).write_bytes(b)
        copied[rel] = sha(b)
    lines = (hearth / "engine/src/quant.c").read_bytes().decode().split("\n")
    out = [
        "/* Extracted verbatim from Hearth engine/src/quant.c at %s by x3 scripts/bitid.py. */"
        % PIN,
        "/* Scratch only: never committed to the Mithril repository. */",
        '#include "hx_quant.h"',
        "",
        "#include <math.h>",
        "#include <string.h>",
        "",
    ]
    for a, b, head_txt in EXTRACT:
        chunk = lines[a - 1 : b]
        if not any(l.startswith(head_txt) for l in chunk):
            raise SystemExit("quant.c:%d-%d does not contain %r" % (a, b, head_txt))
        out.append("/* quant.c:%d-%d */" % (a, b))
        out.extend(chunk)
        out.append("")
    sig = "const void *W, int64_t n, const void *act, int T, float *Y, int64_t ldy, int64_t r0, int64_t r1"
    out += [
        "void x3ref_mm_q8_scalar(%s) { mm_q8_scalar(W, n, act, T, Y, ldy, r0, r1); }" % sig,
        "void x3ref_mm_q4_scalar(%s) { mm_q4_scalar(W, n, act, T, Y, ldy, r0, r1); }" % sig,
        "void x3ref_act_q8_scalar(const float *x, hx_act_q8 *out, int64_t n) "
        "{ act_q8_scalar(x, out, n); }",
        "float x3ref_q_f16(uint16_t h) { return q_f16(h); }",
        "float x3ref_q_canon(float v) { return q_canon(v); }",
        "",
    ]
    ref = "\n".join(out).encode()
    (src / "hearth_scalar_ref.c").write_bytes(ref)
    copied["hearth_scalar_ref.c (extracted)"] = sha(ref)
    return {"head": head, "clean": status == "", "blobs": blobs, "staged_sha256": copied}


def generate(gdir):
    files = {k: ROOT / "x3gen" / "hearth" / "schedules" / (k + ".py") for k in SCHED}
    out, report = emit.build(
        meaning.MEANINGS, SCHED, ROOT / "x3gen" / "hearth" / "meaning.py", files
    )
    emit.write(out, report, gdir)
    committed = ROOT / "generated"
    same = {
        n: (committed / n).exists() and (committed / n).read_bytes() == t.encode()
        for n, t in out.items()
    }
    return report, same


# ------------------------------------------------------------------ build

BASE_CLCL = [
    "/nologo",
    "-DHEARTH_BUILD_DLL",
    "-D_CRT_SECURE_NO_WARNINGS",
    "/DWIN32",
    "/D_WINDOWS",
    "/O2",
    "/Ob2",
    "/DNDEBUG",
    "/std:c11",
    "-MD",
    "/experimental:c11atomics",
    "/fp:precise",
    "/utf-8",
    "/W3",
    "/X",
]
ARCH_CLCL = {"none": [], "avx2": ["/arch:AVX2"], "avx512": ["/arch:AVX512", "-mavx512vnni"]}
BASE_GNU = [
    "--target=x86_64-pc-windows-msvc",
    "-DHEARTH_BUILD_DLL",
    "-O3",
    "-DNDEBUG",
    "-std=gnu11",
    "-ffp-contract=off",
    "-Wall",
    "-Wextra",
    "-Wno-unused-parameter",
    "-nostdlibinc",
]
ARCH_GNU = {
    "none": [],
    "avx2": ["-mavx2", "-mfma", "-mf16c"],
    "avx512": [
        "-mavx512f",
        "-mavx512bw",
        "-mavx512vl",
        "-mavx512vnni",
        "-mavx2",
        "-mfma",
        "-mf16c",
    ],
}
CONFIGS = {
    # X0 configuration B's flags (TOOLCHAINS.md), plus the shared -mavx512vnni (DESIGN 6, Q8)
    "clangcl_B": ("clang-cl", BASE_CLCL, ARCH_CLCL),
    # the same with contraction off (the conditional shared deviation of DESIGN 6 / B-gnu bracket)
    "clangcl_B_nocontract": ("clang-cl", BASE_CLCL + ["/clang:-ffp-contract=off"], ARCH_CLCL),
    # X0 configuration D's flags (Linux clang), compiled for the Windows target on this laptop
    "clang_D_flags": ("clang", BASE_GNU, ARCH_GNU),
}
TUS = [
    ("hearth/engine/src/quant_avx2.c", "avx2"),
    ("hearth/engine/src/quant_avx512.c", "avx512"),
    ("hearth/engine/src/hearth_scalar_ref.c", "none"),
    ("gen/x3_q_scalar.c", "none"),
    ("gen/x3_q_avx2.c", "avx2"),
    ("gen/x3_q_avx512.c", "avx512"),
    ("bitid/x3_bitid.c", "none"),
    ("bitid/rt.c", "none"),
]


def build(llvm, sdir, name, tus=None, dllname="x3bitid.dll"):
    drv, base, arch = CONFIGS[name]
    exe = str(llvm / "bin" / (drv + ".exe"))
    odir = sdir / "build" / name
    odir.mkdir(parents=True, exist_ok=True)
    incs = [sdir / "bitid" / "shim", sdir / "hearth" / "engine" / "src", sdir / "gen"]
    objs, cmds, warns = [], {}, {}
    for tu, a in tus or TUS:
        src = sdir / tu
        obj = odir / (src.stem + ".obj")
        cmd = [exe] + base + arch[a] + ["-I" + str(i) for i in incs]
        if src.name == "rt.c":
            cmd += ["/clang:-fno-builtin"] if drv == "clang-cl" else ["-fno-builtin"]
        cmd += (
            ["/c", str(src), "/Fo" + str(obj)]
            if drv == "clang-cl"
            else ["-c", str(src), "-o", str(obj)]
        )
        log = run(cmd)
        warns[tu] = [l for l in log.splitlines() if "warning" in l]
        cmds[tu] = cmd
        objs.append(obj)
    dll = odir / dllname
    run(
        [
            str(llvm / "bin" / "lld-link.exe"),
            "/nologo",
            "/DLL",
            "/NOENTRY",
            "/NODEFAULTLIB",
            "/OUT:" + str(dll),
        ]
        + [str(o) for o in objs]
    )
    return dll, {
        "commands": {k: " ".join(v) for k, v in cmds.items()},
        "warnings": warns,
        "dll_sha256": sha(dll.read_bytes()),
    }


FMA = re.compile(r"\bv?f(n)?m(add|sub)\w*|\bvfmaddsub\w*|\bvfmsubadd\w*")
APPROX = re.compile(r"\bv?rcp\w*|\bv?rsqrt\w*")
MXCSR = re.compile(r"\b(v?ldmxcsr|fxrstor\w*|xrstor\w*)\b")


def objscan(llvm, sdir, name):
    res = {}
    for tu, _ in TUS:
        if "rt.c" in tu or "x3_bitid" in tu:
            continue
        obj = sdir / "build" / name / (pathlib.Path(tu).stem + ".obj")
        dis = run([str(llvm / "bin" / "llvm-objdump.exe"), "-d", "--no-show-raw-insn", str(obj)])
        mn = [
            l.split("\t")[1].split()[0]
            for l in dis.splitlines()
            if l.count("\t") >= 1
            and re.match(r"\s+[0-9a-f]+:", l)
            and len(l.split("\t")) > 1
            and l.split("\t")[1].strip()
        ]
        res[tu] = {
            "instructions": len(mn),
            "fma": sorted({m for m in mn if FMA.fullmatch(m)}),
            "approx": sorted({m for m in mn if APPROX.fullmatch(m)}),
            "mxcsr": sorted({m for m in mn if MXCSR.fullmatch(m)}),
            "fma_count": sum(1 for m in mn if FMA.fullmatch(m)),
        }
    return res


# ------------------------------------------------------------------ guarded buffers


class Guarded:
    """One read-write region between two PAGE_NOACCESS pages."""

    k32 = None

    def __init__(self, nbytes):
        if Guarded.k32 is None:
            k = ctypes.WinDLL("kernel32", use_last_error=True)
            k.VirtualAlloc.restype = ctypes.c_void_p
            k.VirtualAlloc.argtypes = [
                ctypes.c_void_p,
                ctypes.c_size_t,
                ctypes.c_uint32,
                ctypes.c_uint32,
            ]
            k.VirtualProtect.argtypes = [
                ctypes.c_void_p,
                ctypes.c_size_t,
                ctypes.c_uint32,
                ctypes.POINTER(ctypes.c_uint32),
            ]
            Guarded.k32 = k
        k = Guarded.k32
        self.pages = (nbytes + PAGE - 1) // PAGE
        total = (self.pages + 2) * PAGE
        self.base = k.VirtualAlloc(None, total, 0x3000, 0x04)
        if not self.base:
            raise MemoryError("VirtualAlloc failed")
        old = ctypes.c_uint32()
        for off in (0, (self.pages + 1) * PAGE):
            if not k.VirtualProtect(self.base + off, PAGE, 0x01, ctypes.byref(old)):
                raise OSError("VirtualProtect failed")
        self.lo = self.base + PAGE
        self.hi = self.base + (self.pages + 1) * PAGE

    def at_end(self, nbytes):
        return self.hi - nbytes

    def at_start(self, nbytes):
        return self.lo


# ------------------------------------------------------------------ corpus


def load(dll):
    d = ctypes.CDLL(str(dll))
    P, I64, I32, U64 = ctypes.c_void_p, ctypes.c_int64, ctypes.c_int, ctypes.c_uint64
    d.x3t_fill_weights.argtypes = [P, I64, I32, U64, I32, I32, I32, P]
    d.x3t_fill_act.argtypes = [P, I64, U64, I32, I32, I32, P]
    d.x3t_case.argtypes = [I32, I64, I64, I32, I64, P, P, P, P, U64, P, P, P]
    d.x3t_matmul.argtypes = [I32, I32, P, I64, P, I32, P, I64, I64, I64]
    d.x3t_act_quant.argtypes = [P, P, I64]
    d.x3t_kernel_name.restype = ctypes.c_char_p
    d.x3t_case_modes.argtypes = [I32, I64, I64, I32, I64] + [P] * 7 + [I32, P, P, P]
    return d


MODES = [  # MXCSR control words (flags clear): rounding RD/RU/RZ, FTZ (bit 15), DAZ (bit 6)
    ("RD", 0x3F80),
    ("RU", 0x5F80),
    ("RZ", 0x7F80),
    ("FTZ", 0x9F80),
    ("DAZ", 0x1FC0),
    ("FTZ_DAZ", 0x9FC0),
    ("RZ_FTZ_DAZ", 0xFFC0),
]
BASE_NS = [64, 128, 192, 320, 4096]
BASE_TS = list(range(1, 10)) + [16]
EXT_NS = BASE_NS + [384, 448, 8192]  # G = 6, 7 and 128 (review 2026-10-23)
EXT_TS = [17, 23, 24, 25, 33, 40]  # second and third token blocks and their tails (same review)
ROWS_SUB = [1, 2, 3, 4, 5, 7, 8, 9, 15, 16, 17, 20, 31, 33, 47, 63, 64, 65, 67]
ROWS_QUICK = [1, 2, 3, 4, 5, 7, 8, 9, 15, 16, 17, 20, 31, 33, 67]
TS_QUICK = [1, 2, 8, 9, 17, 25]


def grid(quick):
    """(n, rows, T) in corpus order. The base grid (n in BASE_NS, rows 1-67, T in BASE_TS) is the
    pre-review corpus; the review added n in {384, 448, 8192} and T in EXT_TS, on ROWS_SUB.
    --quick: n in BASE_NS, rows ROWS_QUICK, T in TS_QUICK."""
    out = []
    for n in BASE_NS if quick else EXT_NS:
        rows_set = ROWS_QUICK if quick else list(range(1, 68))
        for rows in rows_set:
            for T in TS_QUICK if quick else BASE_TS + EXT_TS:
                if not quick and (n not in BASE_NS or T not in BASE_TS) and rows not in ROWS_SUB:
                    continue
                out.append((n, rows, T))
    return out


def corpus(d, quick, seed0, nseeds=1, mode_every=1):
    """Run x3t_case on every shape of the grid, for both dtypes and nseeds seeds. ldy runs over
    rows .. rows + 5 (case mod 6), so the tight layout ldy = rows is included. Every mode_every-th
    case (0: none) also runs x3t_case_modes, the seven non-default MXCSR modes."""
    shapes = grid(quick)
    maxw = 67 * 128 * 66
    maxa = 40 * 128 * 72
    maxy = 40 * (67 + 8) * 4
    W, A = Guarded(maxw), Guarded(maxa)
    Yr, Yk, Yd, Ys = Guarded(maxy), Guarded(maxy), Guarded(maxy), Guarded(maxy)
    bad = (ctypes.c_int32 * 30)()
    oc = (ctypes.c_int32 * 5)()
    wcls = (ctypes.c_int32 * 6)()
    acls = (ctypes.c_int32 * 6)()
    nm = len(MODES)
    csr = (ctypes.c_uint * nm)(*[v for _, v in MODES])
    pair = (ctypes.c_int32 * (3 * nm))()
    cross = (ctypes.c_int32 * (6 * nm))()
    live = (ctypes.c_int32 * nm)()
    h = ctypes.c_uint64(0xCBF29CE484222325)
    cases = mcases = mwords = 0
    faults = []
    t0 = time.time()
    for dt, sd in [(dt, sd) for sd in range(nseeds) for dt in (Q8, Q4)]:
        for n, rows, T in shapes:
            c = cases
            cases += 1
            G = n // 64
            bs = 66 if dt == Q8 else 34
            wb, ab = rows * G * bs, T * G * 72
            ldy = rows + c % 6
            wp = W.at_end(wb) if c % 2 == 0 else W.at_start(wb)
            ap = A.at_end(ab) if (c // 2) % 2 == 0 else A.at_start(ab)
            yb = T * ldy * 4
            seed = (seed0 + sd) * 1000003 + c
            # input mode (c % 4): 0 clean; 1 W-scale specials; 2 A-scale specials;
            # 3 both, with extreme code bytes. NaN/inf density ~ 1/(4G) per block.
            mode = c % 4
            nanpm = max(4, 250 // G)
            d.x3t_fill_weights(
                wp,
                rows * G,
                dt,
                seed,
                0 if mode in (1, 3) else 1,
                1 if mode == 3 else 0,
                nanpm,
                wcls,
            )
            d.x3t_fill_act(ap, T * G, seed, (c // 4) % 2, 1 if mode in (2, 3) else 0, nanpm, acls)
            try:
                d.x3t_case(
                    dt,
                    n,
                    rows,
                    T,
                    ldy,
                    wp,
                    ap,
                    Yr.at_end(yb),
                    Yk.at_end(yb),
                    seed,
                    bad,
                    ctypes.byref(h),
                    oc,
                )
                if mode_every and c % mode_every == 0:
                    d.x3t_case_modes(
                        dt,
                        n,
                        rows,
                        T,
                        ldy,
                        wp,
                        ap,
                        Yd.at_end(yb),
                        Ys.at_end(yb),
                        Yr.at_end(yb),
                        Yk.at_end(yb),
                        csr,
                        nm,
                        pair,
                        cross,
                        live,
                    )
                    mcases += 1
                    mwords += T * ldy
            except OSError as e:
                faults.append(
                    {
                        "case": c,
                        "dtype": dt,
                        "n": n,
                        "rows": rows,
                        "T": T,
                        "error": str(e),
                        "kernels": probe(d, dt, n, rows, T, ldy, wp, ap, Yk.at_end(yb)),
                    }
                )
    secs = time.time() - t0
    names = [d.x3t_kernel_name(k).decode() for k in range(NK)]
    tests = [
        "whole_vs_hearth_scalar",
        "batched_vs_single",
        "row_splits",
        "no_write_T0_or_empty",
        "subrange_footprint",
    ]
    per = {names[k]: {tests[j]: bad[6 * j + k] for j in range(5)} for k in range(NK)}
    modes = {
        "modes": {m: "0x%04x" % v for m, v in MODES},
        "cases": mcases,
        "words_per_mode": mwords,
        "pair_mismatch_words": {
            m: {"%s~%s" % (names[k + 3], names[k]): pair[3 * i + k] for k in range(3)}
            for i, (m, _) in enumerate(MODES)
        },
        "vs_hearth_scalar_same_mode": {
            m: {names[j]: cross[6 * i + j] for j in range(NK)} for i, (m, _) in enumerate(MODES)
        },
        "words_changed_by_mode": {m: live[i] for i, (m, _) in enumerate(MODES)},
    }
    return {
        "cases": cases,
        "grid": {
            "n": BASE_NS if quick else EXT_NS,
            "T": TS_QUICK if quick else BASE_TS + EXT_TS,
            "rows": (
                "quick subset %r" % ROWS_QUICK
                if quick
                else "1-67 on the base grid; %r where n is 384, 448 or 8192, or T > 16" % ROWS_SUB
            ),
            "ldy": "rows + (case mod 6)",
            "shapes_per_dtype_and_seed": len(shapes),
        },
        "seeds": [seed0 + i for i in range(nseeds)],
        "seconds": round(secs, 1),
        "mismatches": per,
        "total_mismatches": sum(bad[i] for i in range(30)),
        "faults": faults,
        "ref_output_hash_fnv1a64": "%016x" % h.value,
        "ref_output_classes": dict(zip(["nan", "inf", "zero", "subnormal", "normal"], oc)),
        "w_scale_classes": dict(zip(["normal", "subnormal", "zero", "inf", "nan", "edge"], wcls)),
        "a_scale_classes": dict(zip(["normal", "subnormal", "zero", "inf", "nan", "huge"], acls)),
        "mxcsr_modes": modes,
    }


def probe(d, dt, n, rows, T, ldy, wp, ap, yp):
    out = {}
    for k in range(NK):
        try:
            d.x3t_matmul(k, dt, wp, n, ap, T, yp, ldy, 0, rows)
            out[k] = "ok"
        except OSError as e:
            out[k] = str(e)
    return out


# ------------------------------------------------------------------ meaning differential


def f16_rand(rng):
    c = rng.random()
    s = rng.getrandbits(1) << 15
    if c < 0.6:
        return s | (rng.randint(1, 30) << 10) | rng.getrandbits(10)
    if c < 0.7:
        return s | rng.randint(1, 1023)
    if c < 0.76:
        return s
    if c < 0.82:
        return s | 0x7C00
    if c < 0.9:
        return s | 0x7C00 | rng.randint(1, 1023)
    return s | rng.choice([0x7BFF, 0x0400, 0x0001, 0x03FF])


def meaning_without_canon(k):
    """Control for the meaning differential (review 2026-10-23, meaning lens, finding 4): the
    meaning with canon removed at the store. The differential must tell it apart from Hearth."""
    k2 = k.clone()
    for nd in iter_nodes(k2.body):
        if isinstance(nd, Store) and nd.value.op == "canon":
            nd.value = nd.value.args[0]
    return k2


def meaning_diff(d, cases, seed):
    rng = random.Random(seed)
    bad = {k: 0 for k in range(NK)}
    names = [d.x3t_kernel_name(k).decode() for k in range(NK)]
    href = names.index("hearth_scalar")
    ctl = {f: meaning_without_canon(meaning.MEANINGS[f]) for f in ("q8", "q4")}
    ctl_bad = 0
    outputs = 0
    W, A, Y = Guarded(9 * 5 * 66), Guarded(3 * 5 * 72), Guarded(3 * 12 * 4)
    for c in range(cases):
        dt = Q8 if c % 2 == 0 else Q4
        k = meaning.MEANINGS["q8" if dt == Q8 else "q4"]
        G = rng.randint(1, 5)
        n = 64 * G
        rows, T = rng.randint(1, 9), rng.randint(1, 3)
        ldy = rows + rng.randint(0, 2)
        bs = 66 if dt == Q8 else 34
        wb = bytearray(rng.getrandbits(8) for _ in range(rows * G * bs))
        for b in range(rows * G):
            struct.pack_into("<H", wb, b * bs, f16_rand(rng))
        xs = []
        for _ in range(T * n):
            xs.append(rng.uniform(-3, 3) if rng.random() < 0.9 else rng.choice([0.0, 1e30, -1e-30]))
        xf = (ctypes.c_float * len(xs))(*xs)
        ab = ctypes.create_string_buffer(T * G * 72)
        for t in range(T):
            d.x3t_act_quant(ctypes.addressof(xf) + t * n * 4, ctypes.addressof(ab) + t * G * 72, n)
        abb = bytearray(ab.raw)
        for blk in range(T * G):
            if rng.random() < 0.3:
                struct.pack_into(
                    "<I",
                    abb,
                    blk * 72,
                    rng.choice(
                        [
                            0x7FC00000,
                            0xFFC00001,
                            0x7F800000,
                            0xFF800000,
                            0,
                            0x80000000,
                            1,
                            0x807FFFFF,
                            0x7F7FFFFF,
                            0x00800000,
                            rng.getrandbits(32),
                        ]
                    ),
                )
        ctypes.memmove(W.lo, bytes(wb), len(wb))
        ctypes.memmove(A.lo, bytes(abb), len(abb))
        sent = 0x7FC0DEAD
        want = [sent] * (T * ldy)
        interp.run(k, bytes(wb), bytes(abb), n, T, want, ldy, 0, rows)
        nocanon = [sent] * (T * ldy)
        interp.run(
            ctl["q8" if dt == Q8 else "q4"], bytes(wb), bytes(abb), n, T, nocanon, ldy, 0, rows
        )
        outputs += T * rows
        for kk in range(NK):
            ctypes.memmove(
                Y.lo, struct.pack("<%dI" % (T * ldy), *([sent] * (T * ldy))), T * ldy * 4
            )
            d.x3t_matmul(kk, dt, W.lo, n, A.lo, T, Y.lo, ldy, 0, rows)
            got = list(struct.unpack("<%dI" % (T * ldy), ctypes.string_at(Y.lo, T * ldy * 4)))
            bad[kk] += sum(1 for a, b in zip(got, want) if a != b)
            if kk == href:
                ctl_bad += sum(1 for a, b in zip(got, nocanon) if a != b)
    return {
        "cases": cases,
        "outputs": outputs,
        "seed": seed,
        "mismatches_vs_interpreter": {names[k]: v for k, v in bad.items()},
        "control_meaning_without_canon_vs_hearth_scalar": ctl_bad,
    }


def alias_demo(d):
    """Review 2026-10-23, finding 4: with T > 1 and ldy < r1 - r0 two outputs share one word of Y,
    "written exactly once" is undefined, and the word holds whichever value the kernel stores
    last. One shape: Q4, n = 128, rows [0, 12), T = 3, ldy = 4, realistic scales."""
    n, rows, T, ldy = 128, 12, 3, 4
    G = n // 64
    W, A = Guarded(rows * G * 34), Guarded(T * G * 72)
    cls = (ctypes.c_int32 * 6)()
    d.x3t_fill_weights(W.lo, rows * G, Q4, 20261023, 1, 0, 0, cls)
    d.x3t_fill_act(A.lo, T * G, 20261023, 1, 0, 0, cls)
    m = (T - 1) * ldy + rows
    Y = Guarded(m * 4)
    out = {}
    for k in range(NK):
        ctypes.memmove(Y.lo, struct.pack("<%dI" % m, *([0x7FC0DEAD] * m)), m * 4)
        d.x3t_matmul(k, Q4, W.lo, n, A.lo, T, Y.lo, ldy, 0, rows)
        out[d.x3t_kernel_name(k).decode()] = struct.unpack(
            "<%dI" % m, ctypes.string_at(Y.lo, m * 4)
        )

    def words(a, b):
        return sum(x != y for x, y in zip(out[a], out[b]))

    return {
        "shape": {"dtype": "q4", "n": n, "r0": 0, "r1": rows, "T": T, "ldy": ldy},
        "violates": "T <= 1 or ldy >= r1 - r0",
        "words_differing": {
            "hearth_avx2 vs hearth_scalar": words("hearth_avx2", "hearth_scalar"),
            "hearth_avx512 vs hearth_scalar": words("hearth_avx512", "hearth_scalar"),
            "x3_scalar vs hearth_scalar": words("x3_scalar", "hearth_scalar"),
            "x3_avx2 vs hearth_avx2": words("x3_avx2", "hearth_avx2"),
            "x3_avx512 vs hearth_avx512": words("x3_avx512", "hearth_avx512"),
        },
    }


# ------------------------------------------------------------------ main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hearth", required=True)
    ap.add_argument("--llvm", required=True)
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--configs", default=",".join(CONFIGS))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seed", type=int, default=20261023)
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--meaning-cases", type=int, default=240)
    ap.add_argument("--mode-every", type=int, default=1)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    hearth, llvm, sdir = pathlib.Path(a.hearth), pathlib.Path(a.llvm), pathlib.Path(a.scratch)
    if sdir.exists():
        shutil.rmtree(sdir)
    (sdir / "bitid" / "shim").mkdir(parents=True)
    for p in (ROOT / "bitid").rglob("*"):
        if p.is_file():
            (sdir / "bitid" / p.relative_to(ROOT / "bitid")).write_bytes(p.read_bytes())
    res = {
        "what": "X3 prototype bit-identity, development data (not gate data)",
        "machine": "laptop (Ryzen 9 7940HS, Zen 4, Windows 11)",
        "date": time.strftime("%Y-%m-%d"),
        "python": sys.version.split()[0],
        "cpu": platform.processor(),
    }
    res["hearth"] = stage(hearth, sdir)
    res["x3gen"], res["generated_equals_committed"] = generate(sdir / "gen")
    res["x3gen"].pop("variants")
    ver = run([str(llvm / "bin" / "clang.exe"), "--version"]).splitlines()[0]
    res["toolchain"] = {
        "clang": ver,
        "clang_exe_sha256": sha((llvm / "bin" / "clang.exe").read_bytes()),
    }
    res["configs"] = {}
    for name in a.configs.split(","):
        dll, info = build(llvm, sdir, name)
        info["objscan"] = objscan(llvm, sdir, name)
        d = load(dll)
        info["mxcsr_during_run"] = "0x%04x" % d.x3t_mxcsr()
        info["corpus"] = corpus(d, a.quick, a.seed, a.seeds, a.mode_every)
        if name == a.configs.split(",")[0]:
            res["meaning_differential"] = meaning_diff(d, a.meaning_cases, a.seed)
            res["output_map_precondition_demo"] = alias_demo(d)
        res["configs"][name] = info
        print(
            name,
            json.dumps(info["corpus"]["mismatches"]),
            info["corpus"]["seconds"],
            "s",
            "faults",
            len(info["corpus"]["faults"]),
            flush=True,
        )
    text = json.dumps(res, indent=1, sort_keys=True) + "\n"
    (sdir / "bitid_result.json").write_bytes(text.encode())
    if a.out:
        pathlib.Path(a.out).write_bytes(text.encode())
    print("meaning differential", json.dumps(res.get("meaning_differential")))


if __name__ == "__main__":
    main()
