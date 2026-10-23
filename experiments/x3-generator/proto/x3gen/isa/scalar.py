"""Scalar C operations as single-operation entries (instruction library I).

Scalars are one-lane values: an i32 or f32 is 4 bytes, a u64 is 8. Loads go through tiny
memcpy helpers printed once per file (x3_ld*), so no access depends on alignment or aliasing.
scalar.h2f_bits is the one named multi-operation entry (DESIGN 5.1, 9.1): a printed static
routine, validated by exhaustive comparison over all 65,536 inputs.
"""

# Provenance of scalar.h2f_bits: transcribed from Hearth's q_f16 (engine/src/quant.c:16-35 at
# b5d3f14), as DESIGN 5.1 specifies, with one FP operation per statement (printer rule 5).

from .base import entry

# loads: pointer -> value
entry("ld.u8", "(int32_t)*(const uint8_t *)({0})", "int32_t", "load", ("sload", 1, 4, False))
entry("ld.s8", "(int32_t)*(const int8_t *)({0})", "int32_t", "load", ("sload", 1, 4, True))
entry("ld.u16", "x3_ld16({0})", "uint64_t", "load", ("sload", 2, 8, False))
entry("ld.i32", "x3_ldi({0})", "int32_t", "load", ("sload", 4, 4, True))
entry("ld.f32", "x3_ldf({0})", "float", "load", ("sload", 4, 4, None))

# 32-bit integer arithmetic on int32_t (exact; wrap excluded by the checker's interval proof)
entry("i32.add", "{0} + {1}", "int32_t", "int", ("ilane", "add", 4, 4))
entry("i32.sub", "{0} - {1}", "int32_t", "int", ("ilane", "sub", 4, 4))
entry("i32.mul", "{0} * {1}", "int32_t", "int", ("ilane", "mul", 4, 4))
entry("i32.and", "{0} & {1}", "int32_t", "bit", ("ilane", "and", 4, 4))
entry("i32.shr", "{0} >> {1}", "int32_t", "bit", ("ilane", "sra", 4, 4))
entry("i32.zero", "0", "int32_t", "const", ("zero", 4))

# 64-bit packing of f16 bit patterns in a general-purpose register (P14)
entry("u64.shl", "{0} << {1}", "uint64_t", "bit", ("gpr_shl", 8))
entry("u64.or", "{0} | {1}", "uint64_t", "bit", ("gpr_or", 8))

# binary32
entry("f32.add", "{0} + {1}", "float", "fp", ("flane", "fadd", 4), ieee="fadd")
entry("f32.mul", "{0} * {1}", "float", "fp", ("flane", "fmul", 4), ieee="fmul")
entry("f32.from_i32", "(float){0}", "float", "fp", ("i2f", 4), ieee="i2f")
entry("f32.zero", "0.0f", "float", "const", ("zero", 4))
entry("f32.bits", "x3_f32bits({0}u)", "float", "const", ("f32const",))
entry("f32.isnan", "{0} != {0}", "int", "fpcmp", ("s_isnan",))
entry("f32.select", "{0} ? {1} : {2}", "float", "sel", ("s_select",))
entry("f32.store", "*({0}) = {1}", None, "store", ("store", 4))

# the named multi-operation exception (DESIGN 5.1, 9.1)
entry("scalar.h2f_bits", "x3_h2f({0})", "float", "fp", ("h2f_scalar",), ieee="h2f")

# Printed once per generated file when used. Each loader is one memory access spelled with memcpy
# (no alignment or aliasing assumption); x3_h2f is the scalar.h2f_bits routine (see above).
HELPERS = [
    (
        "x3_ld16",
        "static inline uint64_t x3_ld16(const uint8_t *p) {\n"
        "    uint16_t v;\n    memcpy(&v, p, 2);\n    return v;\n}",
    ),
    (
        "x3_ldi",
        "static inline int32_t x3_ldi(const uint8_t *p) {\n"
        "    int32_t v;\n    memcpy(&v, p, 4);\n    return v;\n}",
    ),
    (
        "x3_ldf",
        "static inline float x3_ldf(const uint8_t *p) {\n"
        "    float v;\n    memcpy(&v, p, 4);\n    return v;\n}",
    ),
    (
        "x3_f32bits",
        "static inline float x3_f32bits(uint32_t b) {\n"
        "    float v;\n    memcpy(&v, &b, 4);\n    return v;\n}",
    ),
    (
        "x3_h2f",
        "static inline float x3_h2f(uint64_t hv) {\n"
        "    const uint32_t h = (uint32_t)hv;\n"
        "    const uint32_t sign = (h & 0x8000u) << 16;\n"
        "    const uint32_t e = (h >> 10) & 0x1fu;\n"
        "    const uint32_t m = h & 0x3ffu;\n"
        "    uint32_t bits;\n"
        "    float r;\n"
        "    if (e == 0x1fu) {\n"
        "        bits = sign | 0x7f800000u | (m << 13) | (m ? 0x00400000u : 0u);\n"
        "    } else if (e != 0) {\n"
        "        bits = sign | ((e + 112u) << 23) | (m << 13);\n"
        "    } else if (m == 0) {\n"
        "        bits = sign;\n"
        "    } else {\n"
        "        const float fm = (float)m;\n"
        "        const float f = fm * 5.9604644775390625e-8f;\n"
        "        uint32_t fb;\n"
        "        memcpy(&fb, &f, 4);\n"
        "        bits = sign | fb;\n"
        "    }\n"
        "    memcpy(&r, &bits, 4);\n"
        "    return r;\n}",
    ),
]
