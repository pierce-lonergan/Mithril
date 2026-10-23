"""The planted suite (DESIGN 4.5): DAG-changing or footprint-violating lane programs that the
global checks must reject, built as mutations of the generated lane programs. Items 1-28 are
DESIGN 4.5's list. Items 29-41 were added after the 2026-10-23 review (DESIGN 4.5: "more may be
added, none removed"): 29-36 are the reviewer's probes, programs that change the FP DAG or the
footprint only on shapes outside the bounded shape set (G >= 6, T >= 18, r1 - r0 >= 64,
n >= 4096); 37-41 are the reviser's, holes of the same kind found while fixing them (a copy of G,
an address polynomial in G, loop-carried counters, a G-dependent data constant, and a C scope
that the checker's flat environment did not model). Same model family as x3gen (logged as such).
Each mutant is judged by check.check_func, the same pipeline as the generated variants. The
accept half here is the six generated variants; the transliterations of Hearth's six hand
kernels that DESIGN 4.5 also asks for are not written yet.

  python -I tests/planted.py [--json OUT]
"""

import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from x3gen.core import check, lower  # noqa: E402
from x3gen.core import sem as S  # noqa: E402
from x3gen.core.fmt import Codes, Format  # noqa: E402
from x3gen.core.lp import IX, Arr, Call, Do, For, Idx, If, Let, Set, Var, ix  # noqa: E402
from x3gen.core.sched import PrimError  # noqa: E402
from x3gen.hearth import meaning  # noqa: E402
from x3gen.hearth.schedules import avx2, avx512, scalar  # noqa: E402
from x3gen.isa.base import entry, TABLE  # noqa: E402

# ------------------------------------------------------------------ test-only entries
# Real intrinsics a broken generator might emit; never part of the production tables.
if "_mm256_fmadd_ps" not in TABLE:
    entry("_mm256_fmadd_ps", "_mm256_fmadd_ps({0}, {1}, {2})", "__m256", "fma", ("fma3", 32))
    entry("_x3_mul_ps_via_pd", "/* (float)((double)a * b) */", "__m256", "double", ("none",))
    entry("_x3_add_ps_via_pd", "/* (float)((double)a + b) */", "__m256", "double", ("none",))
    entry("_mm256_xor_si256", "_mm256_xor_si256({0}, {1})", "__m256i", "bit", ("bitop", "xor", 32))
    entry(
        "_mm256_set1_epi8_t",
        "_mm256_set1_epi8((char){0})",
        "__m256i",
        "const",
        ("bcast_const", 1, 32),
    )
    entry("_mm256_hadd_ps", "_mm256_hadd_ps({0}, {1})", "__m256", "fp", ("fhadd", 32))
    entry(
        "_mm256_storeu_si256",
        "_mm256_storeu_si256((__m256i *)({0}), {1})",
        None,
        "store",
        ("store", 32),
    )
    entry(
        "_mm256_permutevar8x32_ps",
        "_mm256_permutevar8x32_ps({0}, {1})",
        "__m256",
        "move",
        ("permvar32r",),
    )


def _fhadd(m, p, a):
    x = S.lanes(m.cx, a[0], 4, "f32")
    y = S.lanes(m.cx, a[1], 4, "f32")
    out = []
    for h in range(len(x) // 4):
        for src in (x[4 * h : 4 * h + 4], y[4 * h : 4 * h + 4]):
            for j in (0, 2):
                out.append(S.ft("add", S.as_ft(m.cx, src[j]), S.as_ft(m.cx, src[j + 1])))
    return S.put(out, 4)


def _permvar32r(m, p, a):
    x, idx = a[0], S.lanes(m.cx, a[1], 4, "int")
    out = []
    for i in idx:
        j = i & (len(x) // 4 - 1)
        out += x[4 * j : 4 * j + 4]
    return out


check.SEM.setdefault("fhadd", _fhadd)
check.SEM.setdefault("permvar32r", _permvar32r)
check.SEM.setdefault("fma3", lambda m, p, a: (_ for _ in ()).throw(S.Unknown("fma")))
check.SEM.setdefault("none", lambda m, p, a: (_ for _ in ()).throw(S.Unknown("no semantics")))

SCHED = {
    "scalar": (scalar.schedule, 1, 1),
    "avx2": (avx2.schedule, 8, 8),
    "avx512": (avx512.schedule, 16, 4),
}


def variant(isa, fmt):
    k = meaning.MEANINGS[fmt]
    s = SCHED[isa][0](k)
    return k, s, lower.lower(s, "x3_%s_%s" % (fmt, isa))


# ------------------------------------------------------------------ LP navigation


def stmts(body):
    """(container, index, statement) for every statement, depth first."""
    out = []

    def rec(lst):
        for i, s in enumerate(lst):
            out.append((lst, i, s))
            if isinstance(s, For):
                rec(s.body)
            elif isinstance(s, If):
                rec(s.then)
                rec(s.other)

    rec(body)
    return out


def spec_branches(f):
    for lst, i, s in stmts(f.body):
        if isinstance(s, If) and isinstance(s.cond, IX) and s.cond.args[0] == Var("T"):
            return s.then, s.other
    raise AssertionError("no T == 1 branch")


def calls(body, entry_suffix):
    return [
        (lst, i, s)
        for lst, i, s in stmts(body)
        if isinstance(s, (Let, Set))
        and isinstance(s.rhs, Call)
        and s.rhs.entry.endswith(entry_suffix)
    ]


def acc_updates(body):
    return [
        (lst, i, s)
        for lst, i, s in stmts(body)
        if isinstance(s, Set)
        and isinstance(s.rhs, Call)
        and s.rhs.entry.endswith("add_ps")
        and s.rhs.args[0] == s.target
    ]


def g_loop(body):
    return [(lst, i, s) for lst, i, s in stmts(body) if isinstance(s, For) and s.var == "g"][0]


def let_named(body, name):
    return [(lst, i, s) for lst, i, s in stmts(body) if isinstance(s, Let) and s.name == name][0]


def prologue_let(f, name, ctype, rhs, prov):
    f.body.insert(0, Let(name, ctype, rhs, prov=prov))


def ptr_offset(ix_expr, delta):
    return ix("+", ix_expr, delta)


# ------------------------------------------------------------------ the 28 mutants


def m01_split_acc(f, s):
    then, _ = spec_branches(f)
    lst, i, acc0 = let_named(then, "acc")
    p = acc0.prov
    lst.insert(i + 1, Let("acc2", "__m256", Call("_mm256_setzero_ps", ()), mut=True, prov=p))
    ul, ui, u = acc_updates(then)[0]
    f1 = u.rhs.args[1]
    ul[ui] = If(
        ix("==", ix("%", Var("g"), 2), 0),
        [u],
        [Set(Var("acc2"), Call("_mm256_add_ps", (Var("acc2"), f1)), prov=p)],
        prov=p,
    )
    gl, gi, _ = g_loop(then)
    gl.insert(gi + 1, Set(Var("acc"), Call("_mm256_add_ps", (Var("acc"), Var("acc2"))), prov=p))


def m02_fma(f, s):
    then, _ = spec_branches(f)
    ul, ui, u = acc_updates(then)[0]
    f1 = u.rhs.args[1]
    ml, mi, mlet = let_named(then, f1.name)
    fi, ff = mlet.rhs.args
    ul[ui] = Set(u.target, Call("_mm256_fmadd_ps", (fi, ff, u.target)), prov=u.prov)


def m03_distribute(f, s):
    then, _ = spec_branches(f)
    ul, ui, u = acc_updates(then)[0]
    f1 = u.rhs.args[1]
    ml, mi, m1 = let_named(then, f1.name)
    fi, fname = m1.rhs.args
    _, _, m0 = let_named(then, fname.name)
    dw, adv = m0.rhs.args
    m0.rhs = Call(m0.rhs.entry, (fi, dw))
    m1.rhs = Call(m1.rhs.entry, (fname, adv))


def m04_no_zero_init(f, s):
    then, _ = spec_branches(f)
    ul, ui, u = acc_updates(then)[0]
    ul[ui] = If(
        ix("==", Var("g"), 0), [Set(u.target, u.rhs.args[1], prov=u.prov)], [u], prov=u.prov
    )


def m05_tree(f, s):
    then, _ = spec_branches(f)
    ul, ui, u = acc_updates(then)[0]
    p = u.prov
    gl, gi, g = g_loop(then)
    gl.insert(gi, Arr("qs", "__m256", 64, prov=p))
    ul[ui] = Set(Idx("qs", Var("g")), u.rhs.args[1], prov=p)
    lv, j = Var("lv"), Var("j")
    stride = ix("<<", 1, lv)
    inner = For(
        "j",
        "int64_t",
        0,
        ix("<", ix("+", j, stride), Var("G")),
        ix("<<", 2, lv),
        [
            Set(
                Idx("qs", j),
                Call("_mm256_add_ps", (Idx("qs", j), Idx("qs", ix("+", j, stride)))),
                prov=p,
            )
        ],
        prov=p,
    )
    tree = For("lv", "int", 0, ix("<", stride, Var("G")), 1, [inner], prov=p)
    gi2 = gl.index(g)
    gl[gi2 + 1 : gi2 + 1] = [
        tree,
        Set(Var("acc"), Call("_mm256_add_ps", (Var("acc"), Idx("qs", 0))), prov=p),
    ]


def m06_double_mul(f, s):
    then, _ = spec_branches(f)
    ul, ui, u = acc_updates(then)[0]
    _, _, m1 = let_named(then, u.rhs.args[1].name)
    _, _, m0 = let_named(then, m1.rhs.args[1].name)
    m0.rhs = Call("_x3_mul_ps_via_pd", m0.rhs.args)


def m07_double_acc(f, s):
    then, _ = spec_branches(f)
    ul, ui, u = acc_updates(then)[0]
    u.rhs = Call("_x3_add_ps_via_pd", u.rhs.args)


def m08_biased_maddubs(f, s):
    then, _ = spec_branches(f)
    p = s.implicit
    prologue_let(f, "csign", "__m256i", Call("_mm256_set1_epi8_t", (128,)), p)
    for lst, i, st in calls(then, "_abs_epi8"):
        st.rhs = Call("_mm256_xor_si256", (st.rhs.args[0], Var("csign")))
    for lst, i, st in calls(then, "_sign_epi8"):
        lst[i] = Let(st.name, st.ctype, st.rhs.args[0], prov=st.prov)


def m09_bias7(f, s):
    then, _ = spec_branches(f)
    for lst, i, st in calls(then, "i32.mul"):
        st.rhs = Call("i32.mul", (st.rhs.args[0], 7))


def m10_hadd_ps(f, s):
    then, _ = spec_branches(f)
    ul, ui, u = acc_updates(then)[0]
    f1 = u.rhs.args[1]
    ul.insert(ui, Let("f1h", "__m256", Call("_mm256_hadd_ps", (f1, f1)), prov=u.prov))
    u.rhs = Call(u.rhs.entry, (u.target, Var("f1h")))


def m11_no_canon(f, s):
    then, _ = spec_branches(f)
    for lst, i, st in calls(then, "_blendv_ps"):
        lst[i] = Let(st.name, st.ctype, st.rhs.args[0], prov=st.prov)


def m12_pair_unroll(f, s):
    then, _ = spec_branches(f)
    ul, ui, u = acc_updates(then)[0]
    p = u.prov
    f1 = u.rhs.args[1]
    gl, gi, g = g_loop(then)
    gl.insert(gi, Let("prev", "__m256", Call("_mm256_setzero_ps", ()), mut=True, prov=p))
    even = [
        Set(Var("prev"), f1, prov=p),
        If(
            ix("==", Var("g"), ix("-", Var("G"), 1)),
            [Set(Var("acc"), Call("_mm256_add_ps", (Var("acc"), Var("prev"))), prov=p)],
            [],
            prov=p,
        ),
    ]
    odd = [
        Let("pair", "__m256", Call("_mm256_add_ps", (Var("prev"), f1)), prov=p),
        Set(Var("acc"), Call("_mm256_add_ps", (Var("acc"), Var("pair"))), prov=p),
    ]
    ul[ui] = If(ix("==", ix("&", Var("g"), 1), 0), even, odd, prov=p)


def m13_prefetch_as_store(f, s):
    then, _ = spec_branches(f)
    gl, gi, g = g_loop(then)
    p = g.prov
    g.body.insert(
        1, Let("pf", "__m256i", Call("_mm256_loadu_si256", (ix("+", Var("w"), Var("go")),)), prov=p)
    )
    g.body.insert(
        2, Do(Call("_mm256_storeu_si256", (ix("+", Var("w"), Var("go")), Var("pf"))), prov=p)
    )


def m14_llama_order(f, s):
    then, _ = spec_branches(f)
    loads = [
        (lst, i, st)
        for lst, i, st in calls(then, "_loadu_si256")
        if isinstance(st.rhs.args[0], IX) and st.rhs.args[0].args[0] == Var("ap")
    ]
    lst, i, st = loads[1]
    st.rhs = Call(st.rhs.entry, (ix("+", Var("ap"), 8 + 16),))


def m15_store_dead_lane(f, s):
    then, _ = spec_branches(f)
    for lst, i, st in stmts(then):
        if isinstance(st, If) and st.cond.args[0] == Var("nr"):
            lst[i] = If(1, st.then, [], prov=st.prov)
            break


def _replace_g(f, branch, builder):
    gl, gi, g = g_loop(branch)
    gl[gi : gi + 1] = builder(g)


def m16_interchange_split_g(f, s):
    then, _ = spec_branches(f)
    _replace_g(
        f,
        then,
        lambda g: [
            For("g", g.ctype, 0, g.cond, 2, g.body, prov=g.prov),
            For("g", g.ctype, 1, g.cond, 2, copy.deepcopy(g.body), prov=g.prov),
        ],
    )


def m17_reverse_g(f, s):
    then, _ = spec_branches(f)
    _replace_g(
        f,
        then,
        lambda g: [
            For("g", g.ctype, ix("-", Var("G"), 1), ix(">=", Var("g"), 0), -1, g.body, prov=g.prov)
        ],
    )


def m18_remainder_first(f, s):
    then, _ = spec_branches(f)
    cut = ix("-", Var("G"), ix("%", Var("G"), 2))
    _replace_g(
        f,
        then,
        lambda g: [
            For("g", g.ctype, cut, g.cond, 1, g.body, prov=g.prov),
            For("g", g.ctype, 0, ix("<", Var("g"), cut), 1, copy.deepcopy(g.body), prov=g.prov),
        ],
    )


def m19_acc_mod4(f, s):
    _, other = spec_branches(f)

    def fix(a):
        if isinstance(a, Idx) and a.arr == "acc":
            return Idx("acc", ix("&", a.index, 3))
        if isinstance(a, Call):
            return Call(a.entry, tuple(fix(x) for x in a.args))
        return a

    for lst, i, st in stmts(other):
        if isinstance(st, (Let, Set)):
            st.rhs = fix(st.rhs)
            if isinstance(st, Set):
                st.target = fix(st.target)


def m20_srli_no_mask(f, s):
    then, _ = spec_branches(f)
    shifted = {st.name for _, _, st in calls(then, "_srli_epi16")}
    for lst, i, st in calls(then, "_and_si256"):
        if st.rhs.args[0].name in shifted:
            lst[i] = Let(st.name, st.ctype, st.rhs.args[0], prov=st.prov)


def m21_sign_swapped(f, s):
    then, _ = spec_branches(f)
    for lst, i, st in calls(then, "_sign_epi8"):
        a, b = st.rhs.args
        st.rhs = Call(st.rhs.entry, (b, a))


def m23_canon_t1_only(f, s):
    _, other = spec_branches(f)
    for lst, i, st in calls(other, "_blendv_ps"):
        lst[i] = Let(st.name, st.ctype, st.rhs.args[0], prov=st.prov)


def m24_canon_inside(f, s):
    then, _ = spec_branches(f)
    ul, ui, u = acc_updates(then)[0]
    p = u.prov
    ul[ui:ui] = [
        Let("isn0", "__m256", Call("_mm256_cmp_ps_unord", (Var("acc"), Var("acc"))), prov=p),
        Set(Var("acc"), Call("_mm256_blendv_ps", (Var("acc"), Var("qnan"), Var("isn0"))), prov=p),
    ]


def m25_negzero(f, s):
    then, _ = spec_branches(f)
    p = s.implicit
    prologue_let(f, "negz", "__m256", Call("_mm256_castsi256_ps", (Var("negzi"),)), p)
    prologue_let(f, "negzi", "__m256i", Call("_mm256_set1_epi32", (0x80000000,)), p)
    _, _, a = let_named(then, "acc")
    a.rhs = Var("negz")


def m26_reverse_lanes(f, s):
    then, _ = spec_branches(f)
    p = s.implicit
    prologue_let(f, "rev", "__m256i", Call("_mm256_setr_epi32", (7, 6, 5, 4, 3, 2, 1, 0)), p)
    lst, i, cv = calls(then, "_blendv_ps")[0]
    lst.insert(
        i + 1,
        Let(
            "cvr",
            "__m256",
            Call("_mm256_permutevar8x32_ps", (Var(cv.name), Var("rev"))),
            prov=cv.prov,
        ),
    )
    for l2, j, st in stmts(then):
        if isinstance(st, Do) and st.call.entry.startswith("_mm256_") and "store" in st.call.entry:
            args = list(st.call.args)
            args[-1] = Var("cvr")
            st.call = Call(st.call.entry, tuple(args))


def m27_quad_order(f, s):
    then, _ = spec_branches(f)
    ups = calls(then, "_unpacklo_epi32") + calls(then, "_unpackhi_epi32")
    for lst, i, st in ups[:2]:
        a, b = st.rhs.args
        st.rhs = Call(st.rhs.entry, (b, a))


def m28_hoisted_load_T0(f, s):
    _, other = spec_branches(f)
    other.insert(
        0,
        Let(
            "junk", "__m256i", Call("_mm256_loadu_si256", (ix("+", Var("Ab"), 8),)), prov=s.implicit
        ),
    )


PLANTED = [
    (1, "split accumulator over g (two partial accumulators)", "avx2", "q4", m01_split_acc),
    (2, "FMA on acc + q", "avx2", "q4", m02_fma),
    (3, "(i2f(I) * dw) * dx", "avx2", "q4", m03_distribute),
    (4, "acc = q_0, no +0.0 initial value", "avx2", "q4", m04_no_zero_init),
    (5, "pairwise tree over g", "avx2", "q4", m05_tree),
    (6, "dw * dx in double, then rounded", "avx2", "q4", m06_double_mul),
    (7, "accumulation in double", "avx2", "q4", m07_double_acc),
    (8, "Q8 maddubs on biased u = q + 128", "avx2", "q8", m08_biased_maddubs),
    (9, "Q4 bias -7*sum instead of -8*sum", "avx2", "q4", m09_bias7),
    (10, "horizontal FP sum across row lanes", "avx2", "q4", m10_hadd_ps),
    (11, "canon omitted", "avx2", "q4", m11_no_canon),
    (12, "g unrolled by 2 with acc + (q0 + q1)", "avx2", "q4", m12_pair_unroll),
    (13, "prefetch replaced by a load and store", "avx2", "q4", m13_prefetch_as_store),
    (14, "llama.cpp Q4_0 nibble order (high nibble at j+16)", "avx2", "q4", m14_llama_order),
    (15, "tail stores a dead lane past r1", "avx2", "q4", m15_store_dead_lane),
    (
        16,
        "g split by 2, pieces interchanged, one accumulator",
        "avx2",
        "q4",
        m16_interchange_split_g,
    ),
    (17, "g reversed", "avx2", "q4", m17_reverse_g),
    (18, "remainder of a split g run before the main part", "avx2", "q4", m18_remainder_first),
    (19, "acc[t mod 4] with token blocks of 8", "avx2", "q4", m19_acc_mod4),
    (20, "Q4 srli_epi16(v, 4) without the following & mask", "avx2", "q4", m20_srli_no_mask),
    (21, "Q8 sign_epi8 operands swapped", "avx2", "q8", m21_sign_swapped),
    (22, "x = -128 admitted in the declared activation range", "avx2", "q8", None),
    (23, "canon on the T == 1 path only", "avx2", "q4", m23_canon_t1_only),
    (24, "canon applied before the final add", "avx2", "q4", m24_canon_inside),
    (25, "acc_0 = -0.0", "avx2", "q4", m25_negzero),
    (26, "lane k stored to row r + lanes - 1 - k", "avx2", "q4", m26_reverse_lanes),
    (27, "AVX-512 quad lanes mis-assigned in the reduction", "avx512", "q4", m27_quad_order),
    (28, "hoisted activation load executes when T = 0", "avx2", "q4", m28_hoisted_load_T0),
]


# ------------------------------------------------------------------ 29-41 (after review)


def _after_r(body):
    names = [getattr(x, "name", None) for x in body]
    return names.index("r") + 1


def _guarded(cond, mutate):
    """The whole function body after the row-pointer setup becomes
    if (cond) { mutated body } else { original body }: a mutant only for shapes where cond holds."""

    def fn(f, s):
        orig = copy.deepcopy(f.body)
        mutate(f, s)
        i, io = _after_r(f.body), _after_r(orig)
        f.body[:] = f.body[:i] + [If(cond, f.body[i:], orig[io:], prov=s.implicit)]

    return fn


GE6 = ix(">=", Var("G"), 6)


def _a_loads(then):
    return [
        (lst, i, st)
        for lst, i, st in calls(then, "_loadu_si256")
        if isinstance(st.rhs.args[0], IX) and st.rhs.args[0].args[0] == Var("ap")
    ]


def m30_fma_inside_g(f, s):
    then, _ = spec_branches(f)
    ul, ui, u = acc_updates(then)[0]
    _, _, mlet = let_named(then, u.rhs.args[1].name)
    fi, ff = mlet.rhs.args
    fma = Set(u.target, Call("_mm256_fmadd_ps", (fi, ff, u.target)), prov=u.prov)
    ul[ui] = If(GE6, [fma], [u], prov=u.prov)


def m32_distribute_many(f, s):
    """(i2f(I) * dw) * dx on the T > 1 path. The reviewer's probe distributed on the T == 1 copy,
    which never runs when T >= 18, so it was not DAG-changing on any shape."""
    _, other = spec_branches(f)
    ul, ui, u = acc_updates(other)[0]
    _, _, m1 = let_named(other, u.rhs.args[1].name)
    fi, fname = m1.rhs.args
    _, _, m0 = let_named(other, fname.name)
    dw, adv = m0.rhs.args
    m0.rhs = Call(m0.rhs.entry, (fi, dw))
    m1.rhs = Call(m1.rhs.entry, (fname, adv))


def m36_ternary_address(f, s):
    then, _ = spec_branches(f)
    lst, i, st = _a_loads(then)[1]
    st.rhs = Call(st.rhs.entry, (ix("+", Var("ap"), ix("?:", ix(">=", Var("g"), 6), 24, 40)),))


def m37_copy_of_G(f, s):
    orig = copy.deepcopy(f.body)
    m17_reverse_g(f, s)
    i, io = _after_r(f.body), _after_r(orig)
    f.body[:] = (
        f.body[:i]
        + [Let("G2", "const int64_t", Var("G"), prov=s.implicit)]
        + [If(ix(">=", Var("G2"), 6), f.body[i:], orig[io:], prov=s.implicit)]
    )


def m38_poly_address(f, s):
    then, _ = spec_branches(f)
    lst, i, st = _a_loads(then)[0]
    poly = ix("-", Var("G"), 1)
    for c in (2, 3, 4, 5):
        poly = ix("*", poly, ix("-", Var("G"), c))
    st.rhs = Call(st.rhs.entry, (ix("+", st.rhs.args[0], ix("*", poly, 72)),))


def m39_carried_counters(f, s):
    then, _ = spec_branches(f)
    gl, gi, g = g_loop(then)
    p = g.prov
    gl[gi:gi] = [Let("kc%d" % k, "int64_t", 1 if k == 0 else 0, mut=True, prov=p) for k in range(6)]
    # kc_k = C(g, k) at the start of block g (Pascal's rule, k = 5 down to 1)
    g.body.extend(
        Set(Var("kc%d" % k), ix("+", Var("kc%d" % k), Var("kc%d" % (k - 1))), prov=p)
        for k in range(5, 0, -1)
    )
    lst, i, st = _a_loads(then)[1]
    base, off = st.rhs.args[0].args
    st.rhs = Call(st.rhs.entry, (ix("+", base, ix("-", off, ix("*", Var("kc5"), 16))),))


def m40_g_constant_select(f, s):
    then, _ = spec_branches(f)
    p = s.implicit
    gl, gi, g = g_loop(then)
    gl[gi:gi] = [
        Let("gv", "__m256i", Call("_mm256_set1_epi32", (Var("G"),)), prov=p),
        Let("five", "__m256i", Call("_mm256_set1_epi32", (5,)), prov=p),
        Let("bigi", "__m256i", Call("_mm256_cmpgt_epi32", (Var("gv"), Var("five"))), prov=p),
        Let("big", "__m256", Call("_mm256_castsi256_ps", (Var("bigi"),)), prov=p),
    ]
    ul, ui, u = acc_updates(then)[0]
    f1 = u.rhs.args[1]
    _, _, m1 = let_named(then, f1.name)
    fi, fname = m1.rhs.args
    _, _, m0 = let_named(then, fname.name)
    dw, adv = m0.rhs.args
    ul[ui:ui] = [
        Let("fa", "__m256", Call("_mm256_mul_ps", (fi, dw)), prov=p),
        Let("fb", "__m256", Call("_mm256_mul_ps", (Var("fa"), adv)), prov=p),
        Let("fs", "__m256", Call("_mm256_blendv_ps", (f1, Var("fb"), Var("big"))), prov=p),
    ]
    u.rhs = Call(u.rhs.entry, (u.target, Var("fs")))


def m41_shadowed_canon(f, s):
    then, _ = spec_branches(f)
    lst, i, cv = calls(then, "_blendv_ps")[0]
    inner = Let(cv.name, cv.ctype, cv.rhs, prov=cv.prov)
    lst[i : i + 1] = [
        Let(cv.name, cv.ctype, cv.rhs.args[0], prov=cv.prov),
        If(ix("==", Var("nr"), 8), [inner], [copy.deepcopy(inner)], prov=cv.prov),
    ]


PLANTED += [
    (29, "FMA on acc + q, only when G >= 6", "avx2", "q4", _guarded(GE6, m02_fma)),
    (30, "inside the g loop: if (G >= 6) FMA else add", "avx2", "q4", m30_fma_inside_g),
    (31, "g reversed, only when G >= 6", "avx2", "q4", _guarded(GE6, m17_reverse_g)),
    (
        32,
        "(i2f(I) * dw) * dx on the T > 1 path, only when T >= 18",
        "avx2",
        "q4",
        _guarded(ix(">=", Var("T"), 18), m32_distribute_many),
    ),
    (
        33,
        "accumulation in double, only when r1 - r0 >= 64",
        "avx2",
        "q4",
        _guarded(ix(">=", ix("-", Var("r1"), Var("r0")), 64), m07_double_acc),
    ),
    (
        34,
        "canon omitted, only when n >= 4096",
        "avx2",
        "q4",
        _guarded(ix(">=", Var("n"), 4096), m11_no_canon),
    ),
    (
        35,
        "AVX-512 quad lanes swapped, only when G >= 6",
        "avx512",
        "q4",
        _guarded(GE6, m27_quad_order),
    ),
    (
        36,
        "activation address ap + (g >= 6 ? 24 : 40) (llama order late)",
        "avx2",
        "q4",
        m36_ternary_address,
    ),
    (37, "a copy G2 = G decides: g reversed when G2 >= 6", "avx2", "q4", m37_copy_of_G),
    (38, "activation address + (G-1)(G-2)(G-3)(G-4)(G-5)*72", "avx2", "q4", m38_poly_address),
    (
        39,
        "loop-carried counters C(g, 5) shift the high half from block 5",
        "avx2",
        "q4",
        m39_carried_counters,
    ),
    (
        40,
        "G-dependent constant selects (i2f*dw)*dx when G >= 6",
        "avx2",
        "q4",
        m40_g_constant_select,
    ),
    (
        41,
        "canon into shadowing declarations; C stores the outer value",
        "avx2",
        "q4",
        m41_shadowed_canon,
    ),
]


def kernel_x_minus128(k):
    AF = k.params["A"][1]
    q = AF.q
    AF2 = Format(
        AF.ctype,
        AF.size,
        d=AF.d,
        sum=AF.sum,
        q=Codes(q.offset, q.count, q.bits, q.signed, q.value_offset, q.hi_at, (-128, 127)),
    )
    k2 = k.clone()
    k2.params = dict(k2.params, A=(k2.params["A"][0], AF2))
    return k2


def mutant(pid, isa, fmt, fn):
    """(kernel, schedule, lane program) of planted item pid."""
    k, s, f = variant(isa, fmt)
    extra = {}
    if pid == 22:
        k2 = kernel_x_minus128(k)
        try:
            SCHED[isa][0](k2)
            extra["P5_at_primitive_time"] = "accepted (unexpected)"
        except PrimError as e:
            extra["P5_at_primitive_time"] = "rejected: " + str(e)
        return k2, s, f, extra
    mf = copy.deepcopy(f)
    fn(mf, s)
    return k, s, mf, extra


def run_one(pid, desc, isa, fmt, fn):
    """Judge one planted program with check.check_func, the pipeline the variants pass."""
    kk, s, mf, extra = mutant(pid, isa, fmt, fn)
    shapes = check.default_shapes(SCHED[isa][1], SCHED[isa][2])
    row = {"id": pid, "what": desc, "variant": "%s/%s" % (isa, fmt)}
    try:
        check.check_func(kk, mf, s.log.ids(), shapes)
        row["verdict"] = "ACCEPTED"
    except check.Reject as e:
        row["verdict"] = "rejected"
        row["stage"] = getattr(e, "stage", "?")
        if getattr(e, "shape", None) is not None:
            row["shape"] = e.shape
        row["reason"] = str(e)[:200]
    row.update(extra)
    return row


def run_per_shape_only(pid, desc, isa, fmt, fn):
    """The same program judged by the per-shape execution alone (check_shape on every shape, with
    its block-count forms), without the text audit, scoping, structure or coverage rules."""
    kk, s, mf, _ = mutant(pid, isa, fmt, fn)
    for sh in check.default_shapes(SCHED[isa][1], SCHED[isa][2]):
        try:
            check.check_shape(kk, mf, sh, s.log.ids())
        except check.Reject:
            return "rejected"
    return "accepted"


def run_all():
    res = [run_one(*row) for row in PLANTED]
    for r, row in zip(res, PLANTED):
        r["per_shape_execution_alone"] = run_per_shape_only(*row)
    stages = {}
    for r in res:
        if r["verdict"] == "rejected":
            stages[r["stage"]] = stages.get(r["stage"], 0) + 1
    return {
        "planted": res,
        "rejected": sum(r["verdict"] == "rejected" for r in res),
        "total": len(res),
        "rejected_by_stage": stages,
        "per_shape_execution_alone_rejects": sum(
            r["per_shape_execution_alone"] == "rejected" for r in res
        ),
    }


if __name__ == "__main__":
    out = run_all()
    for r in out["planted"]:
        print(
            "%2d %-55s %s %-16s %s"
            % (
                r["id"],
                r["what"][:55],
                r["verdict"],
                r.get("stage", ""),
                r.get("reason", "")[:100],
            )
        )
    print(
        "rejected %d of %d; by stage %r" % (out["rejected"], out["total"], out["rejected_by_stage"])
    )
    if len(sys.argv) > 2 and sys.argv[1] == "--json":
        pathlib.Path(sys.argv[2]).write_bytes((json.dumps(out, indent=1) + "\n").encode())
