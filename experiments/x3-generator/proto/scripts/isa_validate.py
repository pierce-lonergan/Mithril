"""Validate isa entries against the compiled intrinsics on this machine (DESIGN 5.4; development
data on the laptop, not the desktop validation the design schedules).

  python -I scripts/isa_validate.py --hearth CLONE --llvm LLVM_DIR --scratch DIR [--n 2000]

1. Every vector entry the six generated programs use is wrapped in an exported C function spelled
   with the entry's own C template, and compared with the checker's semantics (check.SEM) on
   random and structured-edge inputs (integer, bit and data-movement entries), or with the fp32
   emulation (FP entries; NaN results compared as NaN).
2. scalar.h2f_bits (the printed x3_h2f routine) against Hearth's q_f16 and against F16C
   _mm_cvtph_ps over all 65,536 inputs, bit for bit, NaN payloads included.
3. The three canon lowerings, spelled with their entries' templates, against Hearth's q_canon over
   all 2^32 binary32 bit patterns.
"""

import argparse
import ctypes
import json
import pathlib
import random
import shutil
import struct
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import bitid  # noqa: E402
from x3gen.core import check, fp32  # noqa: E402
from x3gen.core import sem as S  # noqa: E402
from x3gen.isa import TABLE  # noqa: E402
from x3gen.isa.scalar import HELPERS  # noqa: E402

# entry -> (result kind, [arg kinds]); imm arguments take the values the generated code uses.
V = {
    "i128": 16,
    "i256": 32,
    "i512": 64,
    "f128": 16,
    "f256": 32,
    "f512": 64,
    "s32": 4,
    "f32": 4,
    "u64": 8,
    "k8": 1,
    "k16": 2,
}
CT = {
    "i128": "__m128i",
    "i256": "__m256i",
    "i512": "__m512i",
    "f128": "__m128",
    "f256": "__m256",
    "f512": "__m512",
    "s32": "int",
    "f32": "float",
    "u64": "uint64_t",
    "k8": "__mmask8",
    "k16": "__mmask16",
}
SPECS = {
    "_mm256_abs_epi8": ("i256", ["i256"]),
    "_mm256_add_epi16": ("i256", ["i256", "i256"]),
    "_mm256_add_epi32": ("i256", ["i256", "i256"]),
    "_mm256_and_si256": ("i256", ["i256", "i256"]),
    "_mm256_sign_epi8": ("i256", ["i256", "i256"]),
    "_mm256_maddubs_epi16": ("i256", ["i256", "i256"]),
    "_mm256_madd_epi16": ("i256", ["i256", "i256"]),
    "_mm256_hadd_epi32": ("i256", ["i256", "i256"]),
    "_mm256_sub_epi32": ("i256", ["i256", "i256"]),
    "_mm256_cmpgt_epi32": ("i256", ["i256", "i256"]),
    "_mm256_srli_epi16": ("i256", ["i256", 4]),
    "_mm256_permute2x128_si256": ("i256", ["i256", "i256", (0x20, 0x31)]),
    "_mm256_inserti128_si256": ("i256", ["i256", "i128", 1]),
    "_mm256_set1_epi32": ("i256", ["s32"]),
    "_mm256_set1_ps": ("f256", ["f32"]),
    "_mm256_add_ps": ("f256", ["f256", "f256"]),
    "_mm256_mul_ps": ("f256", ["f256", "f256"]),
    "_mm256_cvtepi32_ps": ("f256", ["i256"]),
    "_mm256_cvtph_ps": ("f256", ["i128"]),
    "_mm256_cmp_ps_unord": ("f256", ["f256", "f256"]),
    "_mm256_blendv_ps": ("f256", ["f256", "f256", "f256"]),
    "_mm512_add_epi32": ("i512", ["i512", "i512"]),
    "_mm512_sub_epi32": ("i512", ["i512", "i512"]),
    "_mm512_and_si512": ("i512", ["i512", "i512"]),
    "_mm512_xor_si512": ("i512", ["i512", "i512"]),
    "_mm512_unpacklo_epi32": ("i512", ["i512", "i512"]),
    "_mm512_unpackhi_epi32": ("i512", ["i512", "i512"]),
    "_mm512_unpacklo_epi64": ("i512", ["i512", "i512"]),
    "_mm512_unpackhi_epi64": ("i512", ["i512", "i512"]),
    "_mm512_srli_epi16": ("i512", ["i512", 4]),
    "_mm512_broadcast_i32x4": ("i512", ["i128"]),
    "_mm512_dpbusd_epi32": ("i512", ["i512", "i512", "i512"]),
    "_mm512_inserti64x4": ("i512", ["i512", "i256", 1]),
    "_mm512_shuffle_i64x2": ("i512", ["i512", "i512", (0x88, 0xDD)]),
    "_mm512_shuffle_epi32": ("i512", ["i512", (0x4E, 0xB1)]),
    "_mm512_permutexvar_epi32": ("i512", ["i512", "i512"]),
    "_mm512_set1_epi32": ("i512", ["s32"]),
    "_mm512_set1_ps": ("f512", ["f32"]),
    "_mm512_add_ps": ("f512", ["f512", "f512"]),
    "_mm512_mul_ps": ("f512", ["f512", "f512"]),
    "_mm512_cvtepi32_ps": ("f512", ["i512"]),
    "_mm512_cvtph_ps": ("f512", ["i256"]),
    "_mm512_cmp_ps_mask_unord": ("k16", ["f512", "f512"]),
    "_mm512_mask_mov_ps": ("f512", ["f512", "k16", "f512"]),
    "_mm_add_ps": ("f128", ["f128", "f128"]),
    "_mm_mul_ps": ("f128", ["f128", "f128"]),
    "_mm_cvtepi32_ps": ("f128", ["i128"]),
    "_mm_cvtph_ps": ("f128", ["i128"]),
    "_mm_cmp_ps_mask_unord": ("k8", ["f128", "f128"]),
    "_mm_mask_mov_ps": ("f128", ["f128", "k8", "f128"]),
    "_mm_set_epi64x": ("i128", ["u64", "u64"]),
    "_mm_cvtsi64_si128": ("i128", ["u64"]),
    "_mm_sub_epi32": ("i128", ["i128", "i128"]),
    "_mm_set1_epi32": ("i128", ["s32"]),
    "_mm_set1_ps": ("f128", ["f32"]),
}


def variants():
    """(entry, immediates tuple) pairs to wrap."""
    out = []
    for key, (rk, args) in SPECS.items():
        imm_lists = [a if isinstance(a, tuple) else (a,) for a in args if not isinstance(a, str)]
        combos = [()]
        for il in imm_lists:
            combos = [c + (v,) for c in combos for v in il]
        for c in combos:
            out.append((key, c))
    return out


def wrapper_c(i, key, imms):
    rk, args = SPECS[key]
    lines = ["__declspec(dllexport) void x3v_%d(const uint8_t *in, uint8_t *out) {" % i]
    names, it = [], iter(imms)
    for j, a in enumerate(args):
        if isinstance(a, str):
            lines.append("    %s a%d;" % (CT[a], j))
            lines.append("    memcpy(&a%d, in + %d, %d);" % (j, 64 * j, V[a]))
            names.append("a%d" % j)
        else:
            names.append(str(next(it)))
    lines.append("    %s r = %s;" % (CT[rk], TABLE[key].c.format(*names)))
    lines.append("    memcpy(out, &r, %d);" % V[rk])
    lines.append("}")
    return "\n".join(lines)


def canon_c():
    """The three canon lowerings, spelled exactly with their isa entries, over all 2^32 patterns."""
    t = TABLE
    nan = 0x7FC00000
    s_isn = t["f32.isnan"].c.format("v")
    s_q = t["f32.bits"].c.format("0x%x" % nan)
    s_sel = t["f32.select"].c.format("isn", "q", "v")
    a_m = t["_mm256_cmp_ps_unord"].c.format("v", "v")
    a_n = t["_mm256_castsi256_ps"].c.format(t["_mm256_set1_epi32"].c.format("0x%x" % nan))
    a_s = t["_mm256_blendv_ps"].c.format("v", "qn", "m")
    z_m = t["_mm512_cmp_ps_mask_unord"].c.format("v", "v")
    z_n = t["_mm512_castsi512_ps"].c.format(t["_mm512_set1_epi32"].c.format("0x%x" % nan))
    z_s = t["_mm512_mask_mov_ps"].c.format("v", "k", "qn")
    x_m = t["_mm_cmp_ps_mask_unord"].c.format("v", "v")
    x_n = t["_mm_castsi128_ps"].c.format(t["_mm_set1_epi32"].c.format("0x%x" % nan))
    x_s = t["_mm_mask_mov_ps"].c.format("v", "k", "qn")
    return f"""
float x3ref_q_canon(float v);
float x3ref_q_f16(uint16_t h);

__declspec(dllexport) uint64_t x3v_canon_scalar(void) {{
    uint64_t bad = 0;
    uint32_t b = 0;
    do {{
        float v, want, got;
        uint32_t gb, wb;
        memcpy(&v, &b, 4);
        want = x3ref_q_canon(v);
        {{
            const int isn = {s_isn};
            const float q = {s_q};
            got = {s_sel};
        }}
        memcpy(&gb, &got, 4);
        memcpy(&wb, &want, 4);
        bad += gb != wb;
    }} while (++b != 0);
    return bad;
}}

__declspec(dllexport) uint64_t x3v_canon_avx2(void) {{
    uint64_t bad = 0;
    const __m256 qn = {a_n};
    uint64_t b = 0;
    for (; b < (1ull << 32); b += 8) {{
        uint32_t in[8], out[8];
        for (int i = 0; i < 8; i++) in[i] = (uint32_t)(b + i);
        __m256 v;
        memcpy(&v, in, 32);
        const __m256 m = {a_m};
        const __m256 c = {a_s};
        memcpy(out, &c, 32);
        for (int i = 0; i < 8; i++) {{
            float f, w;
            uint32_t wb;
            memcpy(&f, &in[i], 4);
            w = x3ref_q_canon(f);
            memcpy(&wb, &w, 4);
            bad += out[i] != wb;
        }}
    }}
    return bad;
}}

__declspec(dllexport) uint64_t x3v_canon_avx512(void) {{
    uint64_t bad = 0;
    const __m512 qn = {z_n};
    uint64_t b = 0;
    for (; b < (1ull << 32); b += 16) {{
        uint32_t in[16], out[16];
        for (int i = 0; i < 16; i++) in[i] = (uint32_t)(b + i);
        __m512 v;
        memcpy(&v, in, 64);
        const __mmask16 k = {z_m};
        const __m512 c = {z_s};
        memcpy(out, &c, 64);
        for (int i = 0; i < 16; i++) {{
            float f, w;
            uint32_t wb;
            memcpy(&f, &in[i], 4);
            w = x3ref_q_canon(f);
            memcpy(&wb, &w, 4);
            bad += out[i] != wb;
        }}
    }}
    return bad;
}}

__declspec(dllexport) uint64_t x3v_canon_avx512vl(void) {{
    uint64_t bad = 0;
    const __m128 qn = {x_n};
    uint64_t b = 0;
    for (; b < (1ull << 32); b += 4) {{
        uint32_t in[4], out[4];
        for (int i = 0; i < 4; i++) in[i] = (uint32_t)(b + i);
        __m128 v;
        memcpy(&v, in, 16);
        const __mmask8 k = {x_m};
        const __m128 c = {x_s};
        memcpy(out, &c, 16);
        for (int i = 0; i < 4; i++) {{
            float f, w;
            uint32_t wb;
            memcpy(&f, &in[i], 4);
            w = x3ref_q_canon(f);
            memcpy(&wb, &w, 4);
            bad += out[i] != wb;
        }}
    }}
    return bad;
}}

__declspec(dllexport) void x3v_h2f_all(uint32_t *bad) {{
    bad[0] = bad[1] = 0;
    for (uint32_t h = 0; h < 65536; h++) {{
        const float a = x3_h2f(h);
        const float b = x3ref_q_f16((uint16_t)h);
        const float c = _mm_cvtss_f32(_mm_cvtph_ps(_mm_cvtsi32_si128((int)h)));
        uint32_t ab, bb, cb;
        memcpy(&ab, &a, 4);
        memcpy(&bb, &b, 4);
        memcpy(&cb, &c, 4);
        bad[0] += ab != bb;
        bad[1] += ab != cb;
    }}
}}
"""


def gen_source(vs):
    parts = [
        "/* Generated by scripts/isa_validate.py: one wrapper per (isa entry, immediates). */",
        "#include <stdint.h>",
        "#include <string.h>",
        "#include <immintrin.h>",
        "",
    ]
    parts += [h for k, h in HELPERS if k in ("x3_h2f", "x3_f32bits")]
    parts += [wrapper_c(i, k, imm) for i, (k, imm) in enumerate(vs)]
    parts.append(canon_c())
    return "\n".join(parts) + "\n"


# ------------------------------------------------------------------ models


class _M:
    def __init__(self):
        self.cx = S.Ctx(None)


def rand_input(rng, kind, key):
    n = V[kind]
    if kind.startswith("f"):
        pool = [
            0,
            0x80000000,
            0x7F800000,
            0xFF800000,
            0x7FC00000,
            0xFFC00001,
            0x7FA00000,
            1,
            0x807FFFFF,
            0x7F7FFFFF,
            0x00800000,
            0x3F800000,
            0xBF800000,
        ]
        words = [
            rng.choice(pool) if rng.random() < 0.3 else rng.getrandbits(32) for _ in range(n // 4)
        ]
        return b"".join(struct.pack("<I", w) for w in words)
    if kind in ("k8", "k16"):
        return bytes(rng.getrandbits(8) for _ in range(n))
    if "maddubs" in key or "sign" in key or "abs" in key or "dpbusd" in key:
        pool = [0, 1, 0x7F, 0x80, 0x81, 0xFF, 0x0F, 0xF0]
        return bytes(
            rng.choice(pool) if rng.random() < 0.3 else rng.getrandbits(8) for _ in range(n)
        )
    if "permutexvar" in key:
        return bytes(rng.getrandbits(8) for _ in range(n))
    return bytes(rng.getrandbits(8) for _ in range(n))


def model(key, imms, ins):
    """Expected output bytes, or None when the checker's model declines (refuses the case)."""
    rk, args = SPECS[key]
    e = TABLE[key]
    k = e.sem[0]
    m = _M()
    if k in ("flane", "i2f", "h2f", "cmp_unord", "cmp_unord_k", "blendv", "mask_mov") or (
        k == "bcast" and args[0] == "f32"
    ):
        return fp_model(key, imms, ins)
    vals, it = [], iter(imms)
    for j, a in enumerate(args):
        if isinstance(a, str):
            b = ins[j]
            if a == "s32":
                vals.append(struct.unpack("<I", b)[0])
            elif a == "u64":
                vals.append(struct.unpack("<Q", b)[0])
            else:
                vals.append(list(b))
        else:
            vals.append(next(it))
    try:
        r = check.SEM[k](m, e.sem[1:], vals)
    except S.Unknown:
        return None
    return bytes(r)


def fp_model(key, imms, ins):
    rk, args = SPECS[key]
    k = TABLE[key].sem[0]

    def words(b):
        return list(struct.unpack("<%dI" % (len(b) // 4), b))

    if k == "bcast":
        return ins[0] * (V[rk] // 4)
    if k == "flane":
        op = fp32.fadd if TABLE[key].ieee == "fadd" else fp32.fmul
        return [op(x, y) for x, y in zip(words(ins[0]), words(ins[1]))]

    def pack(ws):
        return struct.pack("<%dI" % len(ws), *ws)

    if k == "i2f":
        return pack(
            [
                fp32.rne_f32(float(struct.unpack("<i", struct.pack("<I", w))[0]))
                for w in words(ins[0])
            ]
        )
    if k == "h2f":
        n = V[rk] // 4
        hs = struct.unpack("<%dH" % n, ins[0][: 2 * n])
        return pack([fp32.h2f(h) for h in hs])
    if k == "cmp_unord":
        return pack(
            [
                0xFFFFFFFF if fp32.is_nan(x) or fp32.is_nan(y) else 0
                for x, y in zip(words(ins[0]), words(ins[1]))
            ]
        )
    if k == "cmp_unord_k":
        bits = [int(fp32.is_nan(x) or fp32.is_nan(y)) for x, y in zip(words(ins[0]), words(ins[1]))]
        v = sum(b << i for i, b in enumerate(bits))
        return v.to_bytes(V[rk], "little")
    if k == "blendv":
        return pack(
            [
                y if m & 0x80000000 else x
                for x, y, m in zip(words(ins[0]), words(ins[1]), words(ins[2]))
            ]
        )
    if k == "mask_mov":
        kb = int.from_bytes(ins[1], "little")
        return pack(
            [
                y if (kb >> i) & 1 else x
                for i, (x, y) in enumerate(zip(words(ins[0]), words(ins[2])))
            ]
        )
    raise AssertionError(key)


def compare(key, got, want):
    if want is None:
        return "declined"
    if isinstance(want, (bytes, bytearray)):
        return "ok" if bytes(got) == bytes(want) else "MISMATCH"
    gw = struct.unpack("<%dI" % len(want), got[: 4 * len(want)])
    for g, w in zip(gw, want):
        if fp32.is_nan(w):
            if not fp32.is_nan(g):
                return "MISMATCH"
        elif g != w:
            return "MISMATCH"
    return "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hearth", required=True)
    ap.add_argument("--llvm", required=True)
    ap.add_argument("--scratch", required=True)
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20261023)
    ap.add_argument("--skip-exhaustive-canon", action="store_true")
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
        "what": "isa entry validation against compiled intrinsics (development data, laptop)",
        "date": time.strftime("%Y-%m-%d"),
        "machine": "laptop (Ryzen 9 7940HS, Zen 4)",
    }
    res["hearth"] = bitid.stage(hearth, sdir)
    vs = variants()
    (sdir / "bitid" / "x3_isaval.c").write_bytes(gen_source(vs).encode())
    tus = [
        ("bitid/x3_isaval.c", "avx512"),
        ("hearth/engine/src/hearth_scalar_ref.c", "none"),
        ("bitid/rt.c", "none"),
    ]
    dll, info = bitid.build(llvm, sdir, "clangcl_B", tus, "x3isaval.dll")
    res["build"] = {"dll_sha256": info["dll_sha256"], "config": "clangcl_B"}
    d = ctypes.CDLL(str(dll))
    rng = random.Random(a.seed)
    inbuf = ctypes.create_string_buffer(64 * 4)
    outbuf = ctypes.create_string_buffer(64)
    entries = {}
    for i, (key, imms) in enumerate(vs):
        fn = getattr(d, "x3v_%d" % i)
        fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        rk, args = SPECS[key]
        tally = {"ok": 0, "MISMATCH": 0, "declined": 0}
        first_bad = None
        for _ in range(a.n):
            ins = [rand_input(rng, x, key) if isinstance(x, str) else None for x in args]
            raw = b"".join((x or b"").ljust(64, b"\0") for x in ins)
            ctypes.memmove(inbuf, raw, len(raw))
            fn(inbuf, outbuf)
            got = outbuf.raw[: V[rk]]
            verdict = compare(key, got, model(key, imms, [x for x in ins]))
            tally[verdict] += 1
            if verdict == "MISMATCH" and first_bad is None:
                first_bad = {"inputs": [x.hex() if x else None for x in ins], "got": got.hex()}
        entries["%s%s" % (key, list(imms) if imms else "")] = dict(tally, first_bad=first_bad)
    res["entries"] = entries
    res["entries_mismatching"] = sorted(k for k, v in entries.items() if v["MISMATCH"])
    bad = (ctypes.c_uint32 * 2)()
    d.x3v_h2f_all(bad)
    res["scalar_h2f_bits_all_65536"] = {"vs_hearth_q_f16": bad[0], "vs_f16c_cvtph": bad[1]}
    if not a.skip_exhaustive_canon:
        canon = {}
        for name in ("scalar", "avx2", "avx512", "avx512vl"):
            f = getattr(d, "x3v_canon_" + name)
            f.restype = ctypes.c_uint64
            t0 = time.time()
            canon[name] = {"mismatches_over_2^32": f(), "seconds": round(time.time() - t0, 1)}
        res["canon_lowerings_exhaustive"] = canon
    text = json.dumps(res, indent=1, sort_keys=True) + "\n"
    (sdir / "isa_validate.json").write_bytes(text.encode())
    if a.out:
        pathlib.Path(a.out).write_bytes(text.encode())
    print(json.dumps({k: res[k] for k in res if k not in ("entries", "hearth")}, indent=1))
    print({k: (v["ok"], v["MISMATCH"], v["declined"]) for k, v in entries.items()})


if __name__ == "__main__":
    main()
