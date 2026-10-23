"""SSE/AVX/AVX2/F16C intrinsics (instruction library I). One entry per intrinsic."""

from .base import entry

for w, p in ((128, "_mm_"), (256, "_mm256_")):
    nb = w // 8
    ft, it = "__m%d" % w, "__m%di" % w
    si = "si%d" % w
    entry(p + "setzero_ps", p + "setzero_ps()", ft, "const", ("zero", nb))
    entry(p + "set1_ps", p + "set1_ps({0})", ft, "move", ("bcast", 4, nb))
    entry(p + "add_ps", p + "add_ps({0}, {1})", ft, "fp", ("flane", "fadd", nb), ieee="fadd")
    entry(p + "mul_ps", p + "mul_ps({0}, {1})", ft, "fp", ("flane", "fmul", nb), ieee="fmul")
    entry(p + "cvtepi32_ps", p + "cvtepi32_ps({0})", ft, "fp", ("i2f", nb), ieee="i2f")
    entry(p + "set1_epi32", p + "set1_epi32({0})", it, "move", ("bcast", 4, nb))
    entry(p + "sub_epi32", p + "sub_epi32({0}, {1})", it, "int", ("ilane", "sub", 4, nb))
    entry(p + "add_epi32", p + "add_epi32({0}, {1})", it, "int", ("ilane", "add", 4, nb))
    entry(p + "loadu_" + si, p + "loadu_%s((const %s *)({0}))" % (si, it), it, "load", ("load", nb))
    entry(p + "storeu_ps", p + "storeu_ps({0}, {1})", None, "store", ("store", nb))

entry("_mm_cvtph_ps", "_mm_cvtph_ps({0})", "__m128", "fp", ("h2f", 16), ieee="h2f", ext="f16c")
entry(
    "_mm256_cvtph_ps", "_mm256_cvtph_ps({0})", "__m256", "fp", ("h2f", 32), ieee="h2f", ext="f16c"
)
entry(
    "_mm_set_epi64x",
    "_mm_set_epi64x((long long){0}, (long long){1})",
    "__m128i",
    "move",
    ("set64x2",),
)
entry("_mm_cvtsi64_si128", "_mm_cvtsi64_si128((long long){0})", "__m128i", "move", ("gpr2vec", 16))

# AVX2 integer, 256-bit
entry("_mm256_set1_epi8", "_mm256_set1_epi8((char){0})", "__m256i", "const", ("bcast_const", 1, 32))
entry("_mm256_set1_epi16", "_mm256_set1_epi16({0})", "__m256i", "const", ("bcast_const", 2, 32))
SETR8 = "_mm256_setr_epi32(" + ", ".join("{%d}" % i for i in range(8)) + ")"
entry("_mm256_setr_epi32", SETR8, "__m256i", "const", ("setr", 4, 32))
entry("_mm256_and_si256", "_mm256_and_si256({0}, {1})", "__m256i", "bit", ("bitop", "and", 32))
entry("_mm256_srli_epi16", "_mm256_srli_epi16({0}, {1})", "__m256i", "bit", ("srli16", 32))
entry("_mm256_abs_epi8", "_mm256_abs_epi8({0})", "__m256i", "bit", ("abs8", 32))
entry("_mm256_sign_epi8", "_mm256_sign_epi8({0}, {1})", "__m256i", "bit", ("sign8", 32))
entry("_mm256_maddubs_epi16", "_mm256_maddubs_epi16({0}, {1})", "__m256i", "int", ("maddubs", 32))
entry("_mm256_madd_epi16", "_mm256_madd_epi16({0}, {1})", "__m256i", "int", ("madd16", 32))
entry("_mm256_add_epi16", "_mm256_add_epi16({0}, {1})", "__m256i", "int", ("ilane", "add", 2, 32))
entry("_mm256_hadd_epi32", "_mm256_hadd_epi32({0}, {1})", "__m256i", "int", ("hadd32", 32))
entry(
    "_mm256_permute2x128_si256",
    "_mm256_permute2x128_si256({0}, {1}, {2})",
    "__m256i",
    "move",
    ("perm2x128",),
)
entry("_mm256_cmpgt_epi32", "_mm256_cmpgt_epi32({0}, {1})", "__m256i", "int", ("cmpgt32", 32))

# AVX FP compare, select, cast, masked store
entry(
    "_mm256_cmp_ps_unord",
    "_mm256_cmp_ps({0}, {1}, _CMP_UNORD_Q)",
    "__m256",
    "fpcmp",
    ("cmp_unord", 32),
)
entry("_mm256_blendv_ps", "_mm256_blendv_ps({0}, {1}, {2})", "__m256", "sel", ("blendv", 32))
entry("_mm256_castsi256_ps", "_mm256_castsi256_ps({0})", "__m256", "move", ("cast", 32, 32))
entry(
    "_mm256_maskstore_ps", "_mm256_maskstore_ps({0}, {1}, {2})", None, "store", ("maskstore32", 32)
)
entry("_mm_prefetch_t0", "_mm_prefetch((const char *)({0}), _MM_HINT_T0)", None, "hint", ("hint",))
