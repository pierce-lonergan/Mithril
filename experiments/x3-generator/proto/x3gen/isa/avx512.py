"""AVX-512 F/BW/VL/VNNI intrinsics (instruction library I). One entry per intrinsic."""

from .base import entry

P = "_mm512_"
entry(P + "setzero_ps", P + "setzero_ps()", "__m512", "const", ("zero", 64))
entry(P + "set1_ps", P + "set1_ps({0})", "__m512", "move", ("bcast", 4, 64))
entry(P + "add_ps", P + "add_ps({0}, {1})", "__m512", "fp", ("flane", "fadd", 64), ieee="fadd")
entry(P + "mul_ps", P + "mul_ps({0}, {1})", "__m512", "fp", ("flane", "fmul", 64), ieee="fmul")
entry(P + "cvtepi32_ps", P + "cvtepi32_ps({0})", "__m512", "fp", ("i2f", 64), ieee="i2f")
entry(P + "cvtph_ps", P + "cvtph_ps({0})", "__m512", "fp", ("h2f", 64), ieee="h2f")
entry(P + "storeu_ps", P + "storeu_ps({0}, {1})", None, "store", ("store", 64))
entry(P + "castsi512_ps", P + "castsi512_ps({0})", "__m512", "move", ("cast", 64, 64))
entry(
    P + "cmp_ps_mask_unord",
    P + "cmp_ps_mask({0}, {1}, _CMP_UNORD_Q)",
    "__mmask16",
    "fpcmp",
    ("cmp_unord_k", 16),
)
entry(P + "mask_mov_ps", P + "mask_mov_ps({0}, {1}, {2})", "__m512", "sel", ("mask_mov", 16))

entry(P + "setzero_si512", P + "setzero_si512()", "__m512i", "const", ("zero", 64))
entry(P + "set1_epi8", P + "set1_epi8((char){0})", "__m512i", "const", ("bcast_const", 1, 64))
entry(P + "set1_epi32", P + "set1_epi32({0})", "__m512i", "move", ("bcast", 4, 64))
SETR16 = P + "setr_epi32(" + ", ".join("{%d}" % i for i in range(16)) + ")"
entry(P + "setr_epi32", SETR16, "__m512i", "const", ("setr", 4, 64))
entry(P + "and_si512", P + "and_si512({0}, {1})", "__m512i", "bit", ("bitop", "and", 64))
entry(P + "xor_si512", P + "xor_si512({0}, {1})", "__m512i", "bit", ("bitop", "xor", 64))
entry(P + "srli_epi16", P + "srli_epi16({0}, {1})", "__m512i", "bit", ("srli16", 64))
entry(P + "castsi256_si512", P + "castsi256_si512({0})", "__m512i", "move", ("cast", 32, 64))
entry(P + "castsi512_si128", P + "castsi512_si128({0})", "__m128i", "move", ("cast", 64, 16))
entry(P + "inserti64x4", P + "inserti64x4({0}, {1}, {2})", "__m512i", "move", ("insert", 32, 64))
entry(P + "shuffle_i64x2", P + "shuffle_i64x2({0}, {1}, {2})", "__m512i", "move", ("shuf_i64x2",))
entry(P + "broadcast_i32x4", P + "broadcast_i32x4({0})", "__m512i", "move", ("bcast_x4",))
entry(
    P + "dpbusd_epi32",
    P + "dpbusd_epi32({0}, {1}, {2})",
    "__m512i",
    "int",
    ("dpbusd", 64),
    ext="avx512vnni",
)
entry(P + "unpacklo_epi32", P + "unpacklo_epi32({0}, {1})", "__m512i", "move", ("unpack", 4, 0))
entry(P + "unpackhi_epi32", P + "unpackhi_epi32({0}, {1})", "__m512i", "move", ("unpack", 4, 1))
entry(P + "unpacklo_epi64", P + "unpacklo_epi64({0}, {1})", "__m512i", "move", ("unpack", 8, 0))
entry(P + "unpackhi_epi64", P + "unpackhi_epi64({0}, {1})", "__m512i", "move", ("unpack", 8, 1))
entry(P + "add_epi32", P + "add_epi32({0}, {1})", "__m512i", "int", ("ilane", "add", 4, 64))
entry(P + "sub_epi32", P + "sub_epi32({0}, {1})", "__m512i", "int", ("ilane", "sub", 4, 64))
entry(
    P + "shuffle_epi32",
    P + "shuffle_epi32({0}, (_MM_PERM_ENUM){1})",
    "__m512i",
    "move",
    ("pshufd",),
)
entry(P + "permutexvar_epi32", P + "permutexvar_epi32({0}, {1})", "__m512i", "move", ("permvar32",))

# 256-bit helpers used to assemble 512-bit vectors (AVX2)
entry("_mm256_castsi128_si256", "_mm256_castsi128_si256({0})", "__m256i", "move", ("cast", 16, 32))
entry(
    "_mm256_inserti128_si256",
    "_mm256_inserti128_si256({0}, {1}, {2})",
    "__m256i",
    "move",
    ("insert", 16, 32),
)

# AVX-512VL 128-bit forms
entry(
    "_mm_cmp_ps_mask_unord",
    "_mm_cmp_ps_mask({0}, {1}, _CMP_UNORD_Q)",
    "__mmask8",
    "fpcmp",
    ("cmp_unord_k", 4),
)
entry("_mm_mask_mov_ps", "_mm_mask_mov_ps({0}, {1}, {2})", "__m128", "sel", ("mask_mov", 4))
entry("_mm_castsi128_ps", "_mm_castsi128_ps({0})", "__m128", "move", ("cast", 16, 16))
entry("_mm_mask_storeu_ps", "_mm_mask_storeu_ps({0}, {1}, {2})", None, "store", ("kstore32", 4))
