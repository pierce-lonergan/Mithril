"""Meaning M: Hearth's Q8/Q4 matmul slot in canonical IEEE order (counted as M, not schedule text).

Sources, all at Hearth b5d3f14 (blob ids in DESIGN.md section 6):
  formats              engine/src/hx_quant.h:20-28
  slot contract        engine/src/hx_quant.h:49-57 (rows [r0, r1), T tokens, Y[t*ldy + r])
  canonical matvec     docs/NUMERICS.md:38-48; Q4 wq = nibble - 8 (:45); acc order (:46)
  Q4 bias identity     docs/NUMERICS.md:50 (licenses lower_isum's bias form, with PRE2)
  canonical NaN        docs/NUMERICS.md:56-58; engine/src/quant.c:53-65 (HX_CANON_NAN, q_canon)
  batched == single    docs/NUMERICS.md:60-62
  scalar definition    engine/src/quant.c:388-405 (mm_q8_scalar), :407-427 (mm_q4_scalar)
  f16 -> f32           engine/src/quant.c:16-35 (q_f16), exact (E2)
  activation range/sum engine/src/quant.c:339-346 (PRE1, PRE2); precondition quant_avx2.c:11

Preconditions are named PRE1-PRE6 (REQUIRES), not P1-P6, so that they cannot be confused with the
schedule primitives P1-P15 (review 2026-10-23, meaning lens, finding 6). The checker evaluates the
shape conditions (PRE5, PRE6) from this text and refuses a REQUIRES string it does not know.
"""

from x3gen.core.fmt import Codes, Format, Scalar, SlotSig
from x3gen.core.ir import Init, Kernel, Store, Update, acc, canon, exact_sum, fadd, fmul, fzero
from x3gen.core.ir import h2f, i2f, loop, v

QK = 64  # hx_quant.h:20 HX_QK

BlockQ8 = Format("hx_block_q8", 66, d=Scalar("f16", 0), q=Codes(2, QK, 8, signed=True), tag="q8")
BlockQ4 = Format(
    "hx_block_q4", 34, d=Scalar("f16", 0), q=Codes(2, QK, 4, value_offset=8, hi_at=32), tag="q4"
)
ActQ8 = Format(
    "hx_act_q8",
    72,
    d=Scalar("f32", 0),
    sum=Scalar("i32", 4),
    q=Codes(8, QK, 8, signed=True, value_range=(-127, 127)),
)

SLOT = SlotSig(
    typedef="hx_matmul_fn",
    header="hx_quant.h",
    params=(
        ("const void *", "W"),
        ("int64_t", "n"),
        ("const void *", "act"),
        ("int", "T"),
        ("float *", "Y"),
        ("int64_t", "ldy"),
        ("int64_t", "r0"),
        ("int64_t", "r1"),
    ),
    name_pattern="hx_x3_mm_{fmt}_{isa}",
    simd_guard="defined(HX_ARCH_X86_64)",  # as quant_avx2.c:15, quant_avx512.c:14
)

REQUIRES = (
    # PRE1: quant_avx2.c:11; guaranteed by act_q8_* (quant.c:339-340). Carried by ActQ8.q.value_range.
    "A.q in [-127, 127]",
    # PRE2: quant.c:343-346; NUMERICS.md:35. Licenses the bias forms of lower_isum.
    "A.sum == sum(A.q)",
    # PRE3: rounding to nearest even, FTZ = DAZ = 0, all six exceptions masked (bits 6-15 of MXCSR);
    # the status flags (bits 0-5) are unconstrained: the precision flag is set during normal runs.
    "(mxcsr & 0xFFC0) == 0x1F80",
    # PRE4: [G] implicit in hx_quant.h:49-57, which has no aliasing clause (line 45 is about
    # hx_act_prepare). Hearth's callers pass separate buffers: mm_set (model.c:341-352) gets the
    # weights, a prepared activation buffer (m->xact or m->act, act_of :370-382) and a scratch Y.
    "Y disjoint from W and A",
    "W and A readable, Y writable, over their extents",
    # PRE5: the shape. n: hx_row_bytes (quant.c:86-87); rows [r0, r1) of W and T activations:
    # hx_quant.h:50-53. rows(W) is the number of rows the W buffer holds.
    "n >= 0 and n % 64 == 0",
    "T >= 0",
    "0 <= r0 <= r1 <= rows(W)",
    # PRE6: the output map (t, r) -> t*ldy + r is injective, so "written exactly once" is defined.
    # [G] implicit in hx_quant.h:49-57; the callers pass ldy = the matrix's row count (e.g.
    # model.c:448-452, 881, 888) and split rows inside [0, rows) (model.c:298-300), so
    # ldy >= r1 >= r1 - r0. Without it Hearth's own scalar and AVX2 kernels disagree (their store
    # orders differ).
    "T <= 1 or ldy >= r1 - r0",
)


def q_matmul(F):
    term = fmul(
        i2f(exact_sum("i", QK, v("imul", v("wq", "r", "g", "i"), v("xq", "t", "g", "i")))),
        fmul(h2f(v("wd", "r", "g")), v("ad", "t", "g")),
    )
    body = [
        loop(
            "t",
            0,
            "T",
            "out",
            loop(
                "r",
                "r0",
                "r1",
                "out",
                Init("acc", fzero()),
                loop("g", 0, "G", "seq", Update("acc", fadd(acc("acc"), term))),
                Store("Y", (("t", "ldy"), ("r", 1)), canon(acc("acc"))),
            ),
        )
    ]
    params = {"W": ("W", F), "A": ("act", ActQ8), "Y": "Y", "n": "n", "block": QK}
    return Kernel("q_matmul_" + F.tag, params, body, REQUIRES, SLOT, {"fmt": F.tag})


MEANINGS = {"q8": q_matmul(BlockQ8), "q4": q_matmul(BlockQ4)}
