"""Global checks C1-C4 on the lane program (DESIGN 4.3), by symbolic execution (library L; trusted
within X3).

The lane program runs on concrete shapes (n, T, r0, r1, ldy) with symbolic data: every input byte
is a leaf named by its address. Loops run their real trip counts, so every tail width, token tail,
P8 copy and degenerate case in the chosen shape set is executed, not assumed.

  C1  every stored lane equals canon(F_{t,r}(G)) for the (t, r) its own store address names, with
      F(0) = +0.0 and F(g+1) = F(g) + i2f(I(r,g,t)) * (h2f(Wd(r,g)) * Ad(t,g)), structurally
      (hash-consed terms; equality up to commutation only when a P15 application is logged). This
      covers visit order, accumulator sharing, the initial value and canon exactly once at the sink.
  C2  every statement carries the provenance id of a logged primitive application and names a
      known, non-banned isa entry: checked on the whole program text (audit_static), executed or
      not, and again on every executed statement. The provenance test is membership, bound at
      class level only: FP arithmetic under P12/P14/P15, FP compares, selects and stores under
      P13, hints under P11. Every string the printer copies into the C is checked too:
      identifiers, declared and cast types, literals and comment text (no verbatim C).
  C3  each i2f operand is proved equal over Z to sum_i wq(r,g,i) * xq(t,g,i) (bit-vector layer by
      enumeration, ring layer by polynomial normal form, PRE2 for the activation sum), with no
      saturation or wrap anywhere (interval proofs), and |I| < 2^24.
  C4  stores hit exactly {t*ldy + r : t < T, r0 <= r < r1}, once each; loads stay inside W's rows
      [r0, r1) and A's T*G blocks; nothing is loaded or stored for T = 0 or r0 = r1.

From the executed shapes to every block count G (n = 64*G, G >= 1), for the same (T, r0, r1, ldy):
  structure()  the block count G is n / block, declared once; a value that depends on n, G or a
               block index (taint) never reaches a branch, a ?: condition, a comparison, a bit
               operation, a loop bound, a product with another such value or a C type narrower
               than 64 bits; the only loop with a G-dependent bound is the canonical
               "for (g = 0; g < G; g++)", unnested; the only state carried from one block to the
               next is an FP accumulator X = add(X, y), read nowhere else in the loop; no store
               runs inside a block loop.
  Machine      every G-dependent integer carries its affine form c0 + cG*G + cg*g (TInt); a
               G-dependent value used as data is rejected; every input load must be
               row*G*bsW + g*bsW + field (W) or (t*G + g)*bsA + field (A) with the row, token and
               field independent of G and g; store addresses must not depend on G or g.
               Index arithmetic is evaluated with the C types the printer emits (integer
               promotions and the usual arithmetic conversions): a value outside its C type's
               range is a rejection, never a wrap, and for a G-dependent value that must hold for
               every G up to the largest the buffers allow (Gmax), and every block index g < G.
  scopes()     C scoping: the checker's flat environment means what the printed C means.
  Coverage     every statement runs, and every branch and ?: takes both arms, on some shape;
               statements and branch sites are identified by their position in the program, not
               by object identity, so one object placed twice is two sites.
Then control flow does not depend on G, each block runs the same operations on the leaves of
block g, and the check of one shape holds for every G with that shape's (T, r0, r1, ldy).

What it does not do (prototype): T, r0, r1 and ldy stay bounded to the executed shapes (row and
token tails are concrete); DESIGN 4.3 asks for symbolic addresses over every runtime shape.
"""

import ast
import re

from ..isa import TABLE
from ..isa.scalar import HELPERS
from . import fp32
from . import sem as S
from .ir import Init as MInit
from .ir import Store as MStore
from .ir import Update as MUpdate
from .ir import iter_nodes
from .ir import walk as ir_walk
from .lp import IX, Arr, Call, Comment, Do, For, Idx, If, Let, Set, Var, walk

BANNED_CLASSES = {"fma", "approx", "mxcsr", "double"}
P15_ID = "P15.commute#"

# ===================================================================== C types of the printed code
# Integer types as (bits, signed) on x86-64. LP64 (Linux) and LLP64 (Windows) agree on every type
# listed; `long` is absent because they do not. __mmask8/16 are unsigned char/short.
CINT = {
    "int": (32, True),
    "int8_t": (8, True),
    "int16_t": (16, True),
    "int32_t": (32, True),
    "int64_t": (64, True),
    "unsigned": (32, False),
    "uint8_t": (8, False),
    "uint16_t": (16, False),
    "uint32_t": (32, False),
    "uint64_t": (64, False),
    "size_t": (64, False),
    "__mmask8": (8, False),
    "__mmask16": (16, False),
}
INT = CINT["int"]
DATA_TYPES = {"float", "__m128", "__m128i", "__m256", "__m256i", "__m512", "__m512i"}
SIZE_MAX, INT64_MAX = (1 << 64) - 1, (1 << 63) - 1
CMP_OPS = {"<", "<=", "==", "!=", ">=", ">"}
LIT_RE = re.compile(r"\A[0-9]+\Z")
IDENT_RE = re.compile(r"\A[A-Za-z][A-Za-z0-9_]{0,62}\Z")
MACRO_RE = re.compile(r"\A[A-Z0-9_]+\Z")
C_WORDS = set(
    "auto break case char const continue default do double else enum extern float for goto if "
    "inline int long register restrict return short signed sizeof static struct typedef "
    "union unsigned void volatile while bool true false asm typeof alignas alignof noreturn "
    "static_assert thread_local complex imaginary NULL memcpy memset main".split()
)


_RESERVED = {}


def _reserved_names():
    """Identifiers the printed file already uses at file scope: every name in an isa spelling or
    return type, and the helper functions."""
    if len(TABLE) not in _RESERVED:
        out = {key for key, _ in HELPERS}
        for e in TABLE.values():  # names only, not the suffix of a literal such as 0.0f
            code = re.sub(r"/\*.*?\*/", "", e.c)
            out |= set(re.findall(r"(?<![\w.])[A-Za-z_]\w*", code))
            out |= set(re.findall(r"(?<![\w.])[A-Za-z_]\w*", e.ret or ""))
        _RESERVED.clear()
        _RESERVED[len(TABLE)] = out
    return _RESERVED[len(TABLE)]


def ident_ok(name):
    """A C identifier the printer may emit: no keyword, type, macro-style, reserved (leading
    underscore), helper or intrinsic name, so that it can only mean the variable it declares."""
    return (
        isinstance(name, str)
        and IDENT_RE.search(name) is not None
        and name not in C_WORDS
        and not name.endswith("_t")
        and not (MACRO_RE.search(name) and "_" in name)
        and name not in _reserved_names()
    )


def decl_type(ct):
    """The C type of a declaration: (bits, signed) for an integer type, 'ptr' for an allowed
    pointer type, 'd:<type>' for a data type; None if the string is not one the checker models."""
    if not isinstance(ct, str):
        return None
    if ct in PTR_ESZ:
        return "ptr"
    t = ct[len("const ") :] if ct.startswith("const ") else ct
    if t in CINT:
        return CINT[t]
    if t in DATA_TYPES:
        return "d:" + t
    return None


def _promote(t):
    return INT if t[0] < 32 else t


def _common(t1, t2):
    """The usual arithmetic conversions (C11 6.3.1.8) for the integer types above."""
    t1, t2 = _promote(t1), _promote(t2)
    if t1[1] == t2[1]:
        return (max(t1[0], t2[0]), t1[1])
    u, s = (t1, t2) if not t1[1] else (t2, t1)
    return u if u[0] >= s[0] else s


def _range(t):
    b, sg = t
    return (-(1 << (b - 1)), (1 << (b - 1)) - 1) if sg else (0, (1 << b) - 1)


def _lit_type(v):
    """An integer literal in index arithmetic: only values of type int, printed in decimal or hex
    alike, so the literal's C type never depends on how it is spelled."""
    if not -(1 << 31) < v < (1 << 31):
        raise Reject("C2: integer literal %d outside int in index arithmetic" % v)
    return INT


def _is_int_t(t):
    return isinstance(t, tuple)


class Reject(Exception):
    pass


class TInt(int):
    """An integer that depends on the block count: its value, and its affine form
    (c0, cG, cg) = c0 + cG*G + cg*g, with G the block count and g the running block index."""

    def __new__(cls, v, aff):
        o = int.__new__(cls, v)
        o.aff = aff
        return o


def _aff(v):
    if isinstance(v, (TInt, Ptr)):
        return v.aff
    return (int(v), 0, 0)


def _tainted(a):
    return a[1] != 0 or a[2] != 0


def _tform(op, f0, f1):
    """Affine form of f0 op f1, or Reject when the result is not affine in (G, g)."""
    if op == "+":
        return tuple(p + q for p, q in zip(f0, f1))
    if op == "-":
        return tuple(p - q for p, q in zip(f0, f1))
    if op == "*":
        if _tainted(f0) and _tainted(f1):
            raise Reject("C1: product of two block-count values (not affine in G)")
        k, f = (f1[0], f0) if _tainted(f0) else (f0[0], f1)
        return tuple(k * c for c in f)
    if op == "/" and not _tainted(f1) and f1[0] > 0 and all(c % f1[0] == 0 for c in f0):
        return tuple(c // f1[0] for c in f0)
    raise Reject("C1: block-count value in '%s' (only + - * and exact division stay affine)" % op)


def _cdiv(a, b):
    """C division of integers: truncation toward zero, exact for any size."""
    if b == 0:
        raise Reject("C4: division by zero in index arithmetic")
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b > 0) else -q


IXOP = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": _cdiv,
    "<": lambda a, b: int(a < b),
    "<=": lambda a, b: int(a <= b),
    "==": lambda a, b: int(a == b),
    "!=": lambda a, b: int(a != b),
    ">=": lambda a, b: int(a >= b),
    ">": lambda a, b: int(a > b),
    "<<": lambda a, b: _shl(a, b),
    "%": lambda a, b: a - b * _cdiv(a, b),
    "&": lambda a, b: a & b,
}


def _shl(a, b):
    if not 0 <= b < 64:
        raise Reject("C4: shift by %d in index arithmetic" % b)
    return a << b


class Ptr:
    __slots__ = ("buf", "off", "esz", "aff")

    def __init__(self, buf, off, esz, aff=None):
        self.buf, self.off, self.esz = buf, off, esz
        self.aff = aff if aff is not None else (off, 0, 0)


class KM:
    """A k-mask register value: one predicate or concrete bit per lane."""

    __slots__ = ("bits",)

    def __init__(self, bits):
        self.bits = bits


PTR_ESZ = {"const uint8_t *": 1, "float *": 4, "uint8_t *": 1}


class Decoder:
    """Address -> leaf meaning, from the formats and the shape (DESIGN 4.3 leaf naming)."""

    def __init__(self, kernel, n, T, r0, r1, ldy):
        self.F = kernel.params["W"][1]
        self.AF = kernel.params["A"][1]
        self.blk = kernel.params["block"]
        self.G = n // self.blk
        self.rb = self.G * self.F.size
        self.T, self.r0, self.r1, self.ldy = T, r0, r1, ldy
        lo, hi = self.AF.q.value_bounds()
        self.xdom = [b for b in range(256) if lo <= (b - 256 if b >= 128 else b) <= hi]
        self.full = list(range(256))

    def w_loc(self, off):
        r, o = divmod(off, self.rb)
        g, fo = divmod(o, self.F.size)
        return r, g, fo

    def a_loc(self, off):
        blk, fo = divmod(off, self.AF.size)
        t, g = divmod(blk, self.G)
        return t, g, fo

    def domain(self, leaf):
        buf, off = leaf
        if buf == "A":
            fo = self.a_loc(off)[2]
            if self.AF.q.offset <= fo < self.AF.q.offset + self.AF.q.nbytes:
                return self.xdom
        return self.full

    def atoms(self, leaf):
        buf, off = leaf
        if buf == "W":
            r, g, fo = self.w_loc(off)
            q = self.F.q
            if not (q.offset <= fo < q.offset + q.nbytes):
                return []
            j = fo - q.offset
            out = []
            for k in range(8 // q.bits):
                i = j + k * q.hi_at if q.bits < 8 else j
                sh = k * q.bits
                out.append((("w", r, g, i), (lambda b, sh=sh, q=q: q.value_of_byte(b, sh))))
            return out
        t, g, fo = self.a_loc(off)
        q = self.AF.q
        if not (q.offset <= fo < q.offset + q.nbytes):
            return []
        i = fo - q.offset
        return [(("x", t, g, i), lambda b: b - 256 if b >= 128 else b)]

    def atom_shape(self, leaf):
        buf, off = leaf
        if buf == "W":
            fo = self.w_loc(off)[2]
            q = self.F.q
            return ("W", q.offset <= fo < q.offset + q.nbytes)
        fo = self.a_loc(off)[2]
        q = self.AF.q
        return ("A", q.offset <= fo < q.offset + q.nbytes)

    def field_run(self, grp, w, kind):
        offs = []
        buf = None
        for s in grp:
            if not (isinstance(s, S.Tab) and s.tid == S.ID8 and s.w == 1 and len(s.deps) == 1):
                return None
            b, o = s.deps[0]
            if buf is None:
                buf = b
            if b != buf:
                return None
            offs.append(o)
        if offs != list(range(offs[0], offs[0] + w)):
            return None
        o = offs[0]
        if buf == "A":
            t, g, fo = self.a_loc(o)
            if kind == "f32" and w == 4 and fo == self.AF.d.offset:
                return S.ft("ad", t, g)
            if kind == "int" and w == 4 and self.AF.sum is not None and fo == self.AF.sum.offset:
                lo, hi = self.AF.q.value_bounds()
                m = self.AF.q.count * max(abs(lo), abs(hi))
                return S.FLeafI(("s", t, g), -m, m)
        if buf == "W" and kind == "f16" and w == 2:
            r, g, fo = self.w_loc(o)
            if fo == self.F.d.offset:
                return S.ft("h2f", r, g)
        return None


# ===================================================================== integer helpers


def s8(b):
    return b - 256 if b >= 128 else b


def _signed(v, w):
    return v - (1 << (8 * w)) if v >= 1 << (8 * w - 1) else v


def _fits(p, w):
    lo, hi = -(1 << (8 * w - 1)), (1 << (8 * w - 1)) - 1
    return lo <= p.lo and p.hi <= hi


def pmul(a, b):
    t = {}
    for m1, c1 in a.terms.items():
        for m2, c2 in b.terms.items():
            m = tuple(sorted(m1 + m2))
            t[m] = t.get(m, 0) + c1 * c2
    ends = [a.lo * b.lo, a.lo * b.hi, a.hi * b.lo, a.hi * b.hi]
    return S.Poly(t, min(ends), max(ends))


def product_poly(cx, ub, sb):
    """u8(ub) * s8(sb) for one byte pair, proved as a polynomial (bit-vector table, then fit)."""
    if isinstance(ub, int) and isinstance(sb, int):
        return S.pconst(ub * s8(sb))
    t = S.combine(cx, [ub, sb], ("mulus",), 4)
    return S.as_poly(cx, t, signed=True, width=4)


# ===================================================================== the machine


class Machine:
    def __init__(self, kernel, func, shape, log_ids, cov=None):
        n, T, r0, r1, ldy = shape
        self.k, self.f = kernel, func
        self.n, self.T, self.r0, self.r1, self.ldy = n, T, r0, r1, ldy
        self.dec = Decoder(kernel, n, T, r0, r1, ldy)
        self.cx = S.Ctx(
            self.dec, memo_key=(self.dec.F.ctype, self.dec.AF.ctype, tuple(self.dec.xdom))
        )
        self.env = {}
        self.stores = {}
        self.where = {}
        self.loads = 0
        self.log_ids = log_ids
        self.cov = cov
        self.facts = {"i2f_proved": 0, "canon_lifted": 0, "prov_checked": 0}
        self.Aend = T * self.dec.G * self.dec.AF.size
        self.oracle = Oracle(kernel)
        self.Gc = self.dec.G
        self.gvar = self.gval = None
        self.tenv = {}
        # The largest block count the buffers of this shape allow: n = 64*G is an int64_t, and W's
        # first r1 rows and A's T*G blocks are objects, whose sizes are at most SIZE_MAX bytes.
        lim = [INT64_MAX // self.dec.blk]
        if r1 > 0:
            lim.append(SIZE_MAX // (r1 * self.dec.F.size))
        if T > 0:
            lim.append(SIZE_MAX // (T * self.dec.AF.size))
        self.Gmax = max(1, min(lim))

    # ------------------------------------------------------------ block-count forms
    def _form(self, v, a):
        """v with its affine form a, after checking that a describes v at this shape."""
        if a[2] and self.gval is None:
            raise Reject("C1: a block index is used outside its block loop")
        if a[0] + a[1] * self.Gc + a[2] * (self.gval or 0) != v:
            raise Reject("checker: affine form %r does not describe %d" % (a, v))
        return TInt(v, a) if _tainted(a) else int(v)

    def _span(self, a):
        """Least and greatest value of c0 + cG*G + cg*g over 1 <= G <= Gmax, 0 <= g < G (a linear
        form on a triangle: its extremes are at the vertices)."""
        c0, cG, cg = a
        pts = [(1, 0), (self.Gmax, 0)] + ([(self.Gmax, self.Gmax - 1)] if cg else [])
        vals = [c0 + cG * G + cg * g for G, g in pts]
        return min(vals), max(vals)

    def _fits(self, v, t, what):
        """v must be representable in the C integer type t, for every G when v depends on G: C
        would wrap it (unsigned), overflow (signed) or narrow it, and the checker's integers are
        over Z, so that is a rejection."""
        lo, hi = _range(t)
        vlo, vhi = self._span(v.aff) if isinstance(v, TInt) else (v, v)
        if vlo < lo or vhi > hi:
            raise Reject(
                "C4: %s: value %s outside the C type %s%d range [%d, %d]%s"
                % (
                    what,
                    "[%d, %d]" % (vlo, vhi) if vlo != vhi else vlo,
                    "int" if t[1] else "uint",
                    t[0],
                    lo,
                    hi,
                    " for some G <= %d" % self.Gmax if isinstance(v, TInt) else "",
                )
            )

    def _cond(self, site, c):
        if isinstance(c, TInt):
            raise Reject("C1: a branch or loop condition depends on the block count")
        if not isinstance(c, int):
            raise Reject("C1: branch on a data value")
        if self.cov is not None and site is not None:
            self.cov.arm(site, c)

    # ------------------------------------------------------------ static C types
    def sty(self, e):
        """The C type of an index expression, from the declarations (C11 6.3.1, 6.5)."""
        if isinstance(e, bool):
            raise Reject("bool literal")
        if isinstance(e, int):
            return _lit_type(e)
        if isinstance(e, Var):
            if e.name not in self.tenv:
                raise Reject("C4: read of an undeclared variable %s" % e.name)
            return self.tenv[e.name]
        if isinstance(e, Idx):
            if e.arr not in self.tenv:
                raise Reject("C4: %s is not declared" % e.arr)
            return self.tenv[e.arr]
        if isinstance(e, Call):
            return "d:" + str(TABLE[e.entry].ret)
        if not isinstance(e, IX):
            raise Reject("C2: %r in index arithmetic" % (e,))
        op, x = e.op, e.args
        if op == "lit":
            return INT
        if op == "cast":
            return decl_type(x[0])
        if op in CMP_OPS:
            return INT
        if op == "?:":
            t1, t2 = self.sty(x[1]), self.sty(x[2])
            if _is_int_t(t1) and _is_int_t(t2):
                return _common(t1, t2)
            if t1 == t2 == "ptr":
                return "ptr"
            raise Reject("C2: ?: arms of types %s and %s" % (t1, t2))
        t0, t1 = self.sty(x[0]), self.sty(x[1])
        if t0 == "ptr" and op == "+" and _is_int_t(t1):
            return "ptr"
        if not (_is_int_t(t0) and _is_int_t(t1)):
            raise Reject("C2: '%s' on types %s and %s" % (op, t0, t1))
        return _promote(t0) if op == "<<" else _common(t0, t1)

    # ------------------------------------------------------------ expressions
    def ev(self, a, path=()):
        """Value of expression a; path is its position in the program (coverage sites)."""
        if isinstance(a, Var):
            if a.name not in self.env:
                raise Reject("C4: read of an unset variable %s" % a.name)
            return self.env[a.name]
        if isinstance(a, bool):
            raise Reject("bool literal")
        if isinstance(a, int):
            return a
        if isinstance(a, str):
            raise Reject("C2: verbatim text in an argument: %r" % a)
        if isinstance(a, Idx):
            arr, i = self._elem(a, path)
            v = arr[i]
            if v is None:
                raise Reject("C1: read of an uninitialised accumulator element")
            return v
        if isinstance(a, IX):
            return self.ix(a, path)
        if isinstance(a, Call):
            return self.call(a, path)
        raise Reject("cannot evaluate %r" % (a,))

    def _elem(self, a, path=()):
        arr = self.env.get(a.arr)
        if not isinstance(arr, list):
            raise Reject("C4: %s is not an array" % a.arr)
        i = self.ev(a.index, path + ("i",))
        if isinstance(i, TInt):
            raise Reject("C1: an array index depends on the block count")
        if not isinstance(i, int) or not 0 <= i < len(arr):
            raise Reject("C4: index %r outside array %s" % (i, a.arr))
        return arr, i

    def ix(self, a, path=()):
        op, x = a.op, a.args
        if op == "lit":
            s = x[0]
            if not (isinstance(s, str) and LIT_RE.search(s)) or int(s) >= 1 << 31:
                raise Reject("C2: literal %r is not a plain decimal int" % (s,))
            return int(s)
        if op == "cast":
            v = self.ev(x[1], path + (1,))
            t = x[0]
            if t in PTR_ESZ:
                if not isinstance(v, Ptr):
                    raise Reject("C4: integer cast to a pointer")
                return Ptr(v.buf, v.off, PTR_ESZ[t], v.aff)
            if isinstance(v, Ptr):
                raise Reject("C4: pointer cast to an integer")
            if not isinstance(v, int):
                raise Reject("integer cast of a data value")
            if t not in CINT:
                raise Reject("C2: cast to a type the checker does not model: %r" % (t,))
            if t.startswith("__mmask") and isinstance(v, TInt):
                raise Reject("C1: a mask depends on the block count")
            self._fits(v, CINT[t], "(%s) cast" % t)
            return v
        if op == "?:":
            c = self.ev(x[0], path + (0,))
            self._cond(path, c)
            t = self.sty(a)
            j = 1 if c else 2
            v = self.ev(x[j], path + (j,))
            if _is_int_t(t):
                if not isinstance(v, int) or isinstance(v, Ptr):
                    raise Reject("C2: ?: arm is not an integer")
                self._fits(v, t, "?: result")
            return v
        a0, a1 = self.ev(x[0], path + (0,)), self.ev(x[1], path + (1,))
        if isinstance(a0, Ptr):
            if op == "+" and isinstance(a1, int) and _is_int_t(self.sty(x[1])):
                f0, f1 = a0.aff, _aff(a1)
                aff = tuple(p + q * a0.esz for p, q in zip(f0, f1))
                return Ptr(a0.buf, a0.off + a1 * a0.esz, a0.esz, aff)
            raise Reject("C4: unsupported pointer arithmetic")
        if not (isinstance(a0, int) and isinstance(a1, int)):
            raise Reject("C2: data value in index arithmetic")
        if op not in IXOP:
            raise Reject("IX op %s" % op)
        t0, t1 = self.sty(x[0]), self.sty(x[1])
        if not (_is_int_t(t0) and _is_int_t(t1)):
            raise Reject("C2: '%s' on types %s and %s" % (op, t0, t1))
        if op == "<<":
            rt = _promote(t0)
            if isinstance(a0, TInt) or isinstance(a1, TInt):
                raise Reject("C1: a shift of a block-count value")
            if not 0 <= a1 < rt[0] or a0 < 0:
                raise Reject("C4: shift %d << %d is undefined in C" % (a0, a1))
            r = a0 << a1
            self._fits(r, rt, "'<<'")
            return r
        ct = _common(t0, t1)
        if (op in CMP_OPS or op in ("/", "%")) and _promote(t0)[1] != _promote(t1)[1]:
            raise Reject("C4: '%s' between signed and unsigned operands" % op)
        self._fits(a0, ct, "left operand of '%s'" % op)
        self._fits(a1, ct, "right operand of '%s'" % op)
        r = IXOP[op](int(a0), int(a1))
        if not (isinstance(a0, TInt) or isinstance(a1, TInt)):
            if op not in CMP_OPS:
                self._fits(r, ct, "'%s'" % op)
            return r
        v = self._form(r, _tform(op, _aff(a0), _aff(a1)))
        self._fits(v, ct, "'%s'" % op)
        return v

    def _store_int(self, t, v, what):
        """C conversion of a value to a declared type t on initialisation or assignment."""
        if _is_int_t(t):
            if isinstance(v, Ptr) or not isinstance(v, int):
                raise Reject("C2: %s: a non-integer value in an integer variable" % what)
            self._fits(v, t, what)
        elif t == "ptr":
            if not isinstance(v, Ptr):
                raise Reject("C2: %s: a non-pointer value in a pointer variable" % what)
        elif isinstance(v, (int, Ptr)):
            raise Reject("C2: %s: an integer or pointer value in a %s variable" % (what, t[2:]))

    # ------------------------------------------------------------ memory
    def load(self, p, nb):
        if not isinstance(p, Ptr):
            raise Reject("C4: load through a non-pointer")
        self.loads += 1
        if self.T == 0 or self.r0 == self.r1:
            raise Reject("C4: a load executes although T == 0 or r0 == r1")
        if p.buf == "W":
            lo, hi = self.r0 * self.dec.rb, self.r1 * self.dec.rb
        elif p.buf == "A":
            lo, hi = 0, self.Aend
        else:
            raise Reject("C4: load from the output buffer")
        if p.off < lo or p.off + nb > hi:
            raise Reject(
                "C4: load [%d, %d) of %s outside [%d, %d)" % (p.off, p.off + nb, p.buf, lo, hi)
            )
        self._uniform(p, nb)
        return [S.leaf_byte((p.buf, p.off + i)) for i in range(nb)]

    def _uniform(self, p, nb):
        """The leaf a load names must be the same function of g for every G: the address is
        row*G*bs + g*bs + field (W) or (t*G + g)*bs + field (A), with the row (token) and the field
        independent of G and g, the field inside one block, and the load inside a block loop.
        Then the load is in bounds, and reads block g of that row, for every G."""
        c0, cG, cg = p.aff
        if p.buf == "W":
            bs, lo, hi = self.dec.F.size, self.r0, self.r1
        else:
            bs, lo, hi = self.dec.AF.size, 0, self.T
        if self.gvar is None:
            raise Reject("C1: input load outside a block loop")
        if cg != bs or cG % bs or not lo <= cG // bs < hi or c0 < 0 or c0 + nb > bs:
            raise Reject(
                "C1: load address %d + %d*G + %d*g of %s is not row*G*%d + g*%d + field"
                % (c0, cG, cg, p.buf, bs, bs)
            )

    def store_lanes(self, p, v, live):
        if not isinstance(p, Ptr) or p.buf != "Y":
            raise Reject("C4: store outside the output")
        if _tainted(p.aff) or self.gvar is not None:
            raise Reject("C4: a store address or a store depends on the block count")
        vals = S.lanes(self.cx, v, 4, "f32")
        for i, val in enumerate(vals):
            if not live[i]:
                continue
            off = p.off + 4 * i
            if off % 4:
                raise Reject("C4: misaligned store")
            idx = off // 4
            if self.T > 1 and self.ldy > 0:  # unique under the precondition ldy >= r1 - r0
                t, r = divmod(idx - self.r0, self.ldy)
                r += self.r0
            else:
                t, r = 0, idx
            if not (0 <= t < self.T and self.r0 <= r < self.r1) or off < 0:
                raise Reject(
                    "C4: store to Y[%d] (t=%d, r=%d) outside the output range" % (idx, t, r)
                )
            if idx in self.stores:
                raise Reject("C4: Y[%d] written twice" % idx)
            self.stores[idx] = S.as_ft(self.cx, val)
            self.where[idx] = (t, r)

    # ------------------------------------------------------------ calls
    def call(self, c, path=()):
        e = TABLE.get(c.entry)
        if e is None:
            raise Reject("C2: unknown isa entry %s" % c.entry)
        if e.cls in BANNED_CLASSES:
            raise Reject("C2/B2-B7: banned instruction class %s (%s)" % (e.cls, c.entry))
        kinds = arg_kinds(e)
        if len(kinds) != len(c.args):
            raise Reject("C2: %s takes %d arguments, not %d" % (c.entry, len(kinds), len(c.args)))
        for j, (a, k) in enumerate(zip(c.args, kinds)):
            self._arg_ok(a, k, c.entry, j)
        args = [self.ev(a, path + (j,)) for j, a in enumerate(c.args)]
        if any(isinstance(v, TInt) for v in args):
            raise Reject("C1: a block-count value is used as data (%s)" % c.entry)
        try:
            return SEM[e.sem[0]](self, e.sem[1:], args)
        except S.Unknown as u:
            raise Reject("C3/C1 unknown at %s: %s" % (c.entry, u))

    def _arg_ok(self, a, kind, entry, j):
        """The argument's C type is one C passes to that parameter without a conversion the
        checker reads differently (ARG_KINDS)."""
        if type(a) is int:
            ok = kind in ("int", "intd", "i32", "u64", "imm", "mask") and (
                a >= 0 or kind not in ("imm", "u64")
            )
        else:
            t = self.sty(a)
            data_int = isinstance(t, str) and _is_int_t(decl_type(t[2:]) if t[:2] == "d:" else 0)
            if kind == "v":
                ok = isinstance(t, str) and t.startswith("d:__m") and "mask" not in t
            elif kind == "f32":
                ok = t == "d:float"
            elif kind == "i32":
                ok = t in ("d:int32_t", "d:int") or _is_int_t(t)
            elif kind == "u64":
                ok = t == "d:uint64_t"
            elif kind == "int":
                ok = _is_int_t(t)
            elif kind == "intd":
                ok = _is_int_t(t) or (data_int and "mask" not in t)
            elif kind == "mask":
                ok = _is_int_t(t) or t in ("d:__mmask8", "d:__mmask16")
            elif kind == "ptr":
                ok = t == "ptr"
            else:
                ok = False
        if not ok:
            raise Reject(
                "C2: argument %d of %s is a %r where the parameter takes %s (C would convert it)"
                % (j, entry, a if type(a) is int else self.sty(a), ARG_DOC[kind])
            )

    # ------------------------------------------------------------ statements
    def _declared(self, ctype, rhs, what):
        t = decl_type(ctype)
        if t is None:
            raise Reject(
                "C2: %s declared with a type the checker does not model: %r" % (what, ctype)
            )
        if isinstance(rhs, Call):
            ret = TABLE[rhs.entry].ret if rhs.entry in TABLE else None
            if decl_type(ret) != t:
                raise Reject("C2: %s of type %s holds a %s result" % (what, ctype, ret))
            return "d:" + ret if _is_int_t(t) else t
        return t

    def _assign(self, target, v, path, rhs):
        """C assignment to a declared variable or array element (typed as declared)."""
        name = target.arr if isinstance(target, Idx) else target.name
        t = self.tenv.get(name)
        if t is None:
            raise Reject("C4: assignment to an undeclared name %s" % name)
        if isinstance(rhs, Call):
            if t != "d:" + str(TABLE[rhs.entry].ret):
                raise Reject("C2: %s of type %s assigned a %s result" % (name, t, rhs.entry))
        else:
            self._store_int(t, v, "assignment to %s" % name)
        if isinstance(target, Idx):
            arr, i = self._elem(target, path)
            arr[i] = v
        else:
            self.env[name] = v

    def run(self, body, base=()):
        for k, st in enumerate(body):
            if isinstance(st, Comment):
                continue
            pos = base + (k,)
            prov = getattr(st, "prov", "")
            if prov not in self.log_ids:
                raise Reject("C2: statement without a logged provenance id: %r" % (prov,))
            self.facts["prov_checked"] += 1
            if self.cov is not None:
                self.cov.ran.add(pos)
            if isinstance(st, Let):
                v = self.ev(st.rhs, pos + ("rhs",))
                t = self._declared(st.ctype, st.rhs, st.name)
                if not isinstance(st.rhs, Call):
                    self._store_int(t, v, "declaration of %s" % st.name)
                self.tenv[st.name] = t
                self.env[st.name] = v
            elif isinstance(st, Set):
                v = self.ev(st.rhs, pos + ("rhs",))
                self._assign(st.target, v, pos + ("tix",), st.rhs)
            elif isinstance(st, Arr):
                self.tenv[st.name] = self._declared(st.ctype, None, st.name)
                self.env[st.name] = [None] * st.n
            elif isinstance(st, Do):
                self.call(st.call, pos + ("call",))
            elif isinstance(st, For):
                self._for(st, pos)
            elif isinstance(st, If):
                c = self.ev(st.cond, pos + ("cond",))
                self._cond(pos + ("if",), c)
                self.run(st.then if c else st.other, pos + (("then",) if c else ("other",)))
            else:
                raise Reject("unknown statement %r" % (st,))

    def _for(self, st, pos):
        if st.declare:
            t = self._declared(st.ctype, None, st.var)
            if not _is_int_t(t):
                raise Reject("C2: loop variable %s of a non-integer type" % st.var)
            self.tenv[st.var] = t
        t = self.tenv.get(st.var)
        if not _is_int_t(t):
            raise Reject("C1: loop variable %s is not an integer variable" % st.var)
        if is_block_loop(st):
            self._block_loop(st, pos, t)
            return
        if st.init is not None:
            v = self.ev(st.init, pos + ("init",))
            if isinstance(v, TInt) or not isinstance(v, int) or isinstance(v, Ptr):
                raise Reject("C1: loop %s starts at a block-count or data value" % st.var)
            self._store_int(t, v, "loop variable %s" % st.var)
            self.env[st.var] = v
        guard = 0
        while True:
            c = self.ev(st.cond, pos + ("cond",))
            self._cond(None, c)
            if not c:
                break
            self.run(st.body, pos + ("body",))
            step = self.ev(st.step, pos + ("step",)) if not isinstance(st.step, int) else st.step
            cur = self.env.get(st.var)
            if isinstance(step, TInt) or isinstance(cur, TInt) or not isinstance(step, int):
                raise Reject("C1: loop %s steps by a block-count or data value" % st.var)
            ct = _common(t, self.sty(st.step))  # v += step: v = (type of v)(v + step)
            self._fits(cur + step, ct, "step of %s" % st.var)
            self._store_int(t, cur + step, "loop variable %s" % st.var)
            self.env[st.var] = cur + step
            guard += 1
            if guard > 1 << 20:
                raise Reject("loop does not terminate")

    def _block_loop(self, st, pos, t):
        """for (g = 0; g < G; g++): g carries the form (0, 0, 1) and runs 0 .. G-1."""
        if self.gvar is not None:
            raise Reject("C1: block loops nest")
        G = self.env.get("G")
        if not isinstance(G, TInt) or G.aff != (0, 1, 0):
            raise Reject("C1: the block loop is not bounded by the block count n / block")
        if self.sty(Var("G")) != (64, True):
            raise Reject("C1: the block count is not an int64_t")
        self.gvar = st.var
        try:
            for gv in range(int(G)):
                self.gval = gv
                self.env[st.var] = g = TInt(gv, (0, 0, 1))
                self._fits(g, t, "block index %s" % st.var)
                self._fits(TInt(gv + 1, (1, 0, 1)), t, "g++ of %s" % st.var)
                self.run(st.body, pos + ("body",))
        finally:
            self.gvar = self.gval = None
        self.env.pop(st.var, None)

    def execute(self):
        vals = {
            "W": Ptr("W", 0, 1),
            "act": Ptr("A", 0, 1),
            "Y": Ptr("Y", 0, 4),
            "n": TInt(self.n, (0, self.k.params["block"], 0)),
            "T": self.T,
            "ldy": self.ldy,
            "r0": self.r0,
            "r1": self.r1,
        }
        for ct, nm in self.f.params:
            t = "ptr" if ct.endswith("*") else decl_type(ct)
            if t is None:
                raise Reject("C2: parameter %s of an unmodelled type %r" % (nm, ct))
            self.tenv[nm] = t
            if t != "ptr":
                self._store_int(t, vals[nm], "parameter %s" % nm)
            self.env[nm] = vals[nm]
        self.run(self.f.body)


# ===================================================================== semantics table


def _vec(v):
    if isinstance(v, list):
        return v
    raise S.Unknown("expected a vector or scalar data value, got %r" % (type(v).__name__,))


def sem_zero(m, p, a):
    return [0] * p[0]


def sem_bcast(m, p, a):
    ew, nb = p
    v = a[0]
    one = S.put([v], ew) if isinstance(v, int) else _vec(v)[:ew]
    return one * (nb // ew)


def sem_bcast_const(m, p, a):
    ew, nb = p
    return S.put([a[0]] * (nb // ew), ew)


def sem_setr(m, p, a):
    ew, nb = p
    return S.put(a, ew)


def sem_flane(m, p, a):
    op, nb = p
    x = S.lanes(m.cx, _vec(a[0]), 4, "f32")
    y = S.lanes(m.cx, _vec(a[1]), 4, "f32")
    name = {"fadd": "add", "fmul": "mul"}[op]
    return S.put([S.ft(name, S.as_ft(m.cx, u), S.as_ft(m.cx, v)) for u, v in zip(x, y)], 4)


ATOM_TAG = {"wq": "w", "xq": "x"}  # meaning leaf ops -> ring atoms named by the decoder


class Oracle:
    """What the meaning says, derived from its loop tree (never written by hand here): the FP chain
    of one output and the exact integer each i2f must carry."""

    def __init__(self, kernel):
        nodes = list(iter_nodes(kernel.body))
        self.init = [n for n in nodes if isinstance(n, MInit)][0].value
        self.update = [n for n in nodes if isinstance(n, MUpdate)][0].value
        self.store = [n for n in nodes if isinstance(n, MStore)][0].value
        self.isum = [e for e in ir_walk(self.update) if e.op == "isum"][0]
        self.memo = {}

    def _ev(self, e, env, acc):
        op, a = e.op, e.args
        if op == "acc":
            return acc
        if op == "fzero":
            return S.ft("c", 0)
        if op in ("fadd", "fmul"):
            return S.ft(
                {"fadd": "add", "fmul": "mul"}[op],
                self._ev(a[0], env, acc),
                self._ev(a[1], env, acc),
            )
        if op == "canon":
            return S.ft("canon", self._ev(a[0], env, acc))
        if op == "i2f" and a[0].op == "isum":
            return S.ft("i2f", env["r"], env["g"], env["t"])
        if op == "h2f" and a[0].op == "wd":
            return S.ft("h2f", *(env[v] for v in a[0].args))
        if op == "ad":
            return S.ft("ad", *(env[v] for v in a))
        raise Reject("C1: meaning op %s has no term form" % op)

    def chain(self, t, r, G):
        key = (t, r, G)
        if key not in self.memo:
            env = {"t": t, "r": r}
            acc = self._ev(self.init, env, None)
            for g in range(G):
                env["g"] = g
                acc = self._ev(self.update, env, acc)
            self.memo[key] = self._ev(self.store, env, acc)
        return self.memo[key]

    def isum_target(self, r, g, t):
        var, count, body = self.isum.args
        if body.op != "imul":
            raise Reject("C3: meaning sum body is not a product of two leaves")
        env = {"r": r, "g": g, "t": t}
        out = {}
        for i in range(count):
            env[var] = i
            mon = tuple(
                sorted((ATOM_TAG[x.op],) + tuple(env[v] for v in x.args) for x in body.args)
            )
            out[mon] = out.get(mon, 0) + 1
        return out


def normal_form_I(poly, dec, oracle):
    """Apply P2 (the sum field equals the sum of the codes) and require the result to equal the
    meaning's exact sum for the (r, g, t) its own atoms name."""
    t = {}
    for mon, c in poly.terms.items():
        expanded = [()]
        for at in mon:
            if at[0] == "s":
                expanded = [
                    e + (("x", at[1], at[2], i),) for e in expanded for i in range(dec.AF.q.count)
                ]
            else:
                expanded = [e + (at,) for e in expanded]
        for e in expanded:
            key = tuple(sorted(e))
            t[key] = t.get(key, 0) + c
    t = {k: v for k, v in t.items() if v}
    ws = {(at[1], at[2]) for mon in t for at in mon if at[0] == "w"}
    xs = {(at[1], at[2]) for mon in t for at in mon if at[0] == "x"}
    if len(ws) != 1 or len(xs) != 1:
        raise S.Unknown(
            "integer sum mixes blocks or rows: %d weight and %d activation blocks"
            % (len(ws), len(xs))
        )
    (r, g), (tt, g2) = ws.pop(), xs.pop()
    if g != g2:
        raise S.Unknown("integer sum pairs block %d of W with block %d of A" % (g, g2))
    want = oracle.isum_target(r, g, tt)
    if t != want:
        extra = sorted(set(t) - set(want))[:1] + [m for m in want if t.get(m) != want[m]][:1]
        raise S.Unknown("integer sum differs from the meaning's at %r" % (extra,))
    return r, g, tt


def sem_i2f(m, p, a):
    out = []
    for v in S.lanes(m.cx, _vec(a[0]), 4, "int"):
        if isinstance(v, int):
            out.append(S.ft("c", fp32.i2f(_signed(v, 4))))
            continue
        pl = S.as_poly(m.cx, v, True, 4)
        if not (-(1 << 24) < pl.lo and pl.hi < 1 << 24):
            raise S.Unknown("E1: |I| not proved below 2^24")
        r, g, t = normal_form_I(pl, m.dec, m.oracle)
        m.facts["i2f_proved"] += 1
        out.append(S.ft("i2f", r, g, t))
    return S.put(out, 4)


def sem_h2f(m, p, a):
    nb = p[0]
    src = _vec(a[0])[: nb // 2]
    out = []
    for v in S.lanes(m.cx, src, 2, "f16"):
        if isinstance(v, S.FT):
            out.append(v)
        elif isinstance(v, int):
            out.append(S.ft("c", fp32.h2f(v)))
        else:
            raise S.Unknown("h2f of a value that is not one weight scale field")
    return S.put(out, 4)


def sem_h2f_scalar(m, p, a):
    v = _vec(a[0])
    if any(not (isinstance(s, int) and s == 0) for s in v[2:]):
        raise S.Unknown("scalar h2f of a value with high bits set")
    return sem_h2f(m, (4,), [v[:2]])


def sem_cmp_unord(m, p, a):
    x = S.lanes(m.cx, _vec(a[0]), 4, "f32")
    y = S.lanes(m.cx, _vec(a[1]), 4, "f32")
    out = []
    for u, v in zip(x, y):
        u, v = S.as_ft(m.cx, u), S.as_ft(m.cx, v)
        out.append(S.Pred(("isnan", u)) if u == v else S.Pred(("unord", u, v)))
    return S.put(out, 4)


def sem_cmp_unord_k(m, p, a):
    x = S.lanes(m.cx, _vec(a[0]), 4, "f32")
    y = S.lanes(m.cx, _vec(a[1]), 4, "f32")
    bits = []
    for u, v in zip(x, y):
        u, v = S.as_ft(m.cx, u), S.as_ft(m.cx, v)
        bits.append(S.Pred(("isnan", u)) if u == v else S.Pred(("unord", u, v)))
    return KM(bits)


QNAN_FT = None


def _select(m, pred, x, y):
    """Lane = pred ? y : x. Lifted to canon(x) only under P13's rule."""
    qn = S.ft("c", fp32.QNAN)
    if isinstance(pred, S.Pred):
        if pred.node[0] == "isnan" and pred.node[1] == x and y == qn:
            m.facts["canon_lifted"] += 1
            return S.ft("canon", x)
        return S.ft("sel", pred.node, x, y)
    if isinstance(pred, int):
        return y if pred else x
    raise S.Unknown("select on an unknown predicate")


def sem_blendv(m, p, a):
    x = [S.as_ft(m.cx, v) for v in S.lanes(m.cx, _vec(a[0]), 4, "f32")]
    y = [S.as_ft(m.cx, v) for v in S.lanes(m.cx, _vec(a[1]), 4, "f32")]
    k = S.lanes(m.cx, _vec(a[2]), 4, "pred")
    out = []
    for u, v, c in zip(x, y, k):
        if isinstance(c, int):
            c = int(bool(c & 0x80000000))
        out.append(_select(m, c, u, v))
    return S.put(out, 4)


def sem_mask_mov(m, p, a):
    x = [S.as_ft(m.cx, v) for v in S.lanes(m.cx, _vec(a[0]), 4, "f32")]
    km = a[1]
    y = [S.as_ft(m.cx, v) for v in S.lanes(m.cx, _vec(a[2]), 4, "f32")]
    bits = km.bits if isinstance(km, KM) else [(km >> i) & 1 for i in range(len(x))]
    return S.put([_select(m, b, u, v) for u, v, b in zip(x, y, bits)], 4)


def sem_s_isnan(m, p, a):
    v = S.as_ft(m.cx, S.lanes(m.cx, _vec(a[0]), 4, "f32")[0])
    return S.put([S.Pred(("isnan", v))], 4)


def sem_s_select(m, p, a):
    c = S.lanes(m.cx, _vec(a[0]), 4, "pred")[0]
    y = S.as_ft(m.cx, S.lanes(m.cx, _vec(a[1]), 4, "f32")[0])
    x = S.as_ft(m.cx, S.lanes(m.cx, _vec(a[2]), 4, "f32")[0])
    return S.put([_select(m, c, x, y)], 4)


def sem_f32const(m, p, a):
    return S.put([a[0]], 4)


def sem_cast(m, p, a):
    nin, nout = p
    v = _vec(a[0])
    if nout <= nin:
        return v[:nout]
    return v + [S.Sl(S.UNDEF, 0, 1)] * (nout - nin)


def sem_load(m, p, a):
    return m.load(a[0], p[0])


def sem_store(m, p, a):
    v = _vec(a[1])
    m.store_lanes(a[0], v, [True] * (len(v) // 4))


def sem_maskstore32(m, p, a):
    mk = S.lanes(m.cx, _vec(a[1]), 4, "int")
    if not all(isinstance(x, int) for x in mk):
        raise S.Unknown("store mask is not concrete")
    v = _vec(a[2])
    m.store_lanes(a[0], v, [bool(x & 0x80000000) for x in mk])


def sem_kstore32(m, p, a):
    k = a[1]
    if not isinstance(k, int):
        raise S.Unknown("store k-mask is not concrete")
    v = _vec(a[2])
    m.store_lanes(a[0], v, [bool((k >> i) & 1) for i in range(p[0])])


def sem_bitop(m, p, a):
    op = p[0]
    f = S.opfn((op,))
    x, y = _vec(a[0]), _vec(a[1])
    out = []
    for s, t in zip(x, y):
        if isinstance(s, int) and isinstance(t, int):
            out.append(f(s, t))
        else:
            out.append(S.combine(m.cx, [S.byte_of(m.cx, s), S.byte_of(m.cx, t)], (op,), 1))
    return out


def sem_srli16(m, p, a):
    imm = a[1]
    out = []
    for v in S.lanes(m.cx, _vec(a[0]), 2, "int"):
        if isinstance(v, int):
            out.append((v & 0xFFFF) >> imm)
        elif isinstance(v, S.Tab):
            out.append(S.combine(m.cx, [v], ("srl16", imm), 2))
        else:
            raise S.Unknown("shift of a non-bit-vector lane")
    return S.put(out, 2)


def sem_abs8(m, p, a):
    out = []
    for s in _vec(a[0]):
        b = S.byte_of(m.cx, s)
        out.append(abs(s8(b)) & 255 if isinstance(b, int) else S.combine(m.cx, [b], ("abs8",), 1))
    return out


def _sign(x, y):
    sy = s8(y)
    return x if sy > 0 else (0 if sy == 0 else (-s8(x)) & 255)


def sem_sign8(m, p, a):
    out = []
    for s, t in zip(_vec(a[0]), _vec(a[1])):
        bs, bt = S.byte_of(m.cx, s), S.byte_of(m.cx, t)
        if isinstance(bs, int) and isinstance(bt, int):
            out.append(_sign(bs, bt))
        else:
            out.append(S.combine(m.cx, [bs, bt], ("sign8",), 1))
    return out


def sem_maddubs(m, p, a):
    x, y = _vec(a[0]), _vec(a[1])
    out = []
    for k in range(0, len(x), 2):
        terms = [
            product_poly(m.cx, S.byte_of(m.cx, x[k + j]), S.byte_of(m.cx, y[k + j])) for j in (0, 1)
        ]
        s = S.padd(terms[0], terms[1])
        if not s.terms or set(s.terms) == {()}:
            v = s.terms.get((), 0)
            out.append(max(-32768, min(32767, v)) & 0xFFFF)
            continue
        if not _fits(s, 2):
            raise S.Unknown("maddubs may saturate: [%d, %d]" % (s.lo, s.hi))
        out.append(s)
    return S.put(out, 2)


def _poly_or_int(m, v, w):
    return S.as_poly(m.cx, v, True, w)


def _const_val(pl):
    if set(pl.terms) <= {()}:
        return pl.terms.get((), 0)
    return None


def sem_madd16(m, p, a):
    x = S.lanes(m.cx, _vec(a[0]), 2, "int")
    y = S.lanes(m.cx, _vec(a[1]), 2, "int")
    out = []
    for k in range(0, len(x), 2):
        if all(isinstance(v, int) for v in (x[k], x[k + 1], y[k], y[k + 1])):
            r = sum(_signed(x[k + j], 2) * _signed(y[k + j], 2) for j in (0, 1))
            out.append(r & 0xFFFFFFFF)  # hardware: wraps only for (-32768)^2 * 2
            continue
        acc = S.pconst(0)
        for j in (0, 1):
            u, v = _poly_or_int(m, x[k + j], 2), _poly_or_int(m, y[k + j], 2)
            acc = S.padd(acc, pmul(u, v))
        if not _fits(acc, 4):
            raise S.Unknown("madd may wrap")
        cv = _const_val(acc)
        out.append(cv & 0xFFFFFFFF if cv is not None else acc)
    return S.put(out, 4)


def sem_ilane(m, p, a):
    op, ew, nb = p
    x, y = a
    xs = S.lanes(m.cx, _vec(x), ew, "int") if isinstance(x, list) else [x]
    ys = S.lanes(m.cx, _vec(y), ew, "int") if isinstance(y, list) else [y] * len(xs)
    if len(ys) == 1 and len(xs) > 1:
        ys = ys * len(xs)
    out = []
    mask = (1 << (8 * ew)) - 1
    for u, v in zip(xs, ys):
        if isinstance(u, int) and isinstance(v, int):
            su, sv = _signed(u & mask, ew), _signed(v & mask, ew)
            if op == "sra":
                r = su >> min(max(sv, 0), 8 * ew - 1)
            else:
                r = {
                    "add": lambda: su + sv,
                    "sub": lambda: su - sv,
                    "mul": lambda: su * sv,
                    "and": lambda: su & sv,
                }[op]()
            out.append(r & mask)
            continue
        if op in ("and", "sra"):
            if isinstance(u, S.Tab) and isinstance(v, int):
                key = ("andc", v) if op == "and" else ("sra", v, ew)
                out.append(S.combine(m.cx, [u], key, ew))
                continue
            raise S.Unknown("bit operation on a ring value")
        pu, pv = _poly_or_int(m, u, ew), _poly_or_int(m, v, ew)
        r = S.padd(pu, pv) if op == "add" else S.padd(pu, pv, -1) if op == "sub" else pmul(pu, pv)
        if not _fits(r, ew):
            raise S.Unknown("int%d %s may wrap: [%d, %d]" % (8 * ew, op, r.lo, r.hi))
        cv = _const_val(r)
        out.append(cv & mask if cv is not None else r)
    return S.put(out, ew)


def sem_hadd32(m, p, a):
    x = S.lanes(m.cx, _vec(a[0]), 4, "int")
    y = S.lanes(m.cx, _vec(a[1]), 4, "int")
    out = []
    for h in range(len(x) // 4):
        xs, ys = x[4 * h : 4 * h + 4], y[4 * h : 4 * h + 4]
        for src in (xs, ys):
            for j in (0, 2):
                if isinstance(src[j], int) and isinstance(src[j + 1], int):
                    out.append((src[j] + src[j + 1]) & 0xFFFFFFFF)
                    continue
                s = S.padd(_poly_or_int(m, src[j], 4), _poly_or_int(m, src[j + 1], 4))
                if not _fits(s, 4):
                    raise S.Unknown("hadd may wrap")
                cv = _const_val(s)
                out.append(cv & 0xFFFFFFFF if cv is not None else s)
    return S.put(out, 4)


def sem_perm2x128(m, p, a):
    x, y, imm = _vec(a[0]), _vec(a[1]), a[2]
    halves = [x[:16], x[16:], y[:16], y[16:]]
    out = []
    for sh in (0, 4):
        sel = (imm >> sh) & 0xF
        out += [0] * 16 if sel & 8 else halves[sel & 3]
    return out


def sem_cmpgt32(m, p, a):
    x = S.lanes(m.cx, _vec(a[0]), 4, "int")
    y = S.lanes(m.cx, _vec(a[1]), 4, "int")
    if not all(isinstance(v, int) for v in x + y):
        raise S.Unknown("comparison of data values")
    return S.put([0xFFFFFFFF if _signed(u, 4) > _signed(v, 4) else 0 for u, v in zip(x, y)], 4)


def sem_dpbusd(m, p, a):
    acc = S.lanes(m.cx, _vec(a[0]), 4, "int")
    x, y = _vec(a[1]), _vec(a[2])
    out = []
    for k, c in enumerate(acc):
        bs = [S.byte_of(m.cx, x[4 * k + j]) for j in range(4)] + [
            S.byte_of(m.cx, y[4 * k + j]) for j in range(4)
        ]
        if isinstance(c, int) and all(isinstance(b, int) for b in bs):
            r = _signed(c, 4) + sum(bs[j] * s8(bs[4 + j]) for j in range(4))
            out.append(r & 0xFFFFFFFF)  # hardware: wraps (the symbolic path forbids it)
            continue
        s = _poly_or_int(m, c, 4)
        for j in range(4):
            s = S.padd(
                s, product_poly(m.cx, S.byte_of(m.cx, x[4 * k + j]), S.byte_of(m.cx, y[4 * k + j]))
            )
        if not _fits(s, 4):
            raise S.Unknown("dpbusd may wrap")
        cv = _const_val(s)
        out.append(cv & 0xFFFFFFFF if cv is not None else s)
    return S.put(out, 4)


def sem_unpack(m, p, a):
    ew, hi = p
    x, y = _vec(a[0]), _vec(a[1])
    out = []
    for lane in range(len(x) // 16):
        xl, yl = x[16 * lane : 16 * lane + 16], y[16 * lane : 16 * lane + 16]
        n = 16 // ew // 2
        base = n * hi
        for i in range(n):
            j = base + i
            out += xl[ew * j : ew * j + ew] + yl[ew * j : ew * j + ew]
    return out


def sem_pshufd(m, p, a):
    x, imm = _vec(a[0]), a[1]
    out = []
    for lane in range(len(x) // 16):
        xl = x[16 * lane : 16 * lane + 16]
        for i in range(4):
            j = (imm >> (2 * i)) & 3
            out += xl[4 * j : 4 * j + 4]
    return out


def sem_permvar32(m, p, a):
    idx = S.lanes(m.cx, _vec(a[0]), 4, "int")
    x = _vec(a[1])
    if not all(isinstance(i, int) for i in idx):
        raise S.Unknown("permute index is not concrete")
    out = []
    for i in idx:
        j = i & 15
        out += x[4 * j : 4 * j + 4]
    return out


def sem_insert(m, p, a):
    piece, total = p
    dst, src, imm = list(_vec(a[0])), _vec(a[1]), a[2]
    pos = imm & (total // piece - 1)
    dst[piece * pos : piece * pos + piece] = src[:piece]
    return dst


def sem_shuf_i64x2(m, p, a):
    x, y, imm = _vec(a[0]), _vec(a[1]), a[2]
    ch = lambda v, i: v[16 * i : 16 * i + 16]  # noqa: E731
    return ch(x, imm & 3) + ch(x, (imm >> 2) & 3) + ch(y, (imm >> 4) & 3) + ch(y, (imm >> 6) & 3)


def sem_bcast_x4(m, p, a):
    return _vec(a[0])[:16] * 4


def _gpr(v, nb):
    return S.put([v], nb) if isinstance(v, int) else _vec(v)


def sem_set64x2(m, p, a):
    return _gpr(a[1], 8) + _gpr(a[0], 8)


def sem_gpr2vec(m, p, a):
    return _gpr(a[0], 8) + [0] * (p[0] - 8)


def sem_gpr_shl(m, p, a):
    v, s = _gpr(a[0], 8), a[1]
    if not isinstance(s, int) or s % 8:
        raise S.Unknown("GPR shift by a non-byte amount")
    k = s // 8
    return ([0] * k + v)[:8]


def sem_gpr_or(m, p, a):
    x, y = _gpr(a[0], 8), _gpr(a[1], 8)
    out = []
    for s, t in zip(x, y):
        if isinstance(s, int) and s == 0:
            out.append(t)
        elif isinstance(t, int) and t == 0:
            out.append(s)
        elif isinstance(s, int) and isinstance(t, int):
            out.append(s | t)
        else:
            out.append(S.combine(m.cx, [S.byte_of(m.cx, s), S.byte_of(m.cx, t)], ("or",), 1))
    return out


def sem_sload(m, p, a):
    nbytes, outbytes, signed = p
    bs = m.load(a[0], nbytes)
    if outbytes == nbytes:
        return bs
    if signed:
        ext = S.combine(m.cx, [bs[-1]], ("sext8",), 1)
        return bs + [ext] * (outbytes - nbytes)
    return bs + [0] * (outbytes - nbytes)


def sem_hint(m, p, a):
    return None


SEM = {
    "zero": sem_zero,
    "bcast": sem_bcast,
    "bcast_const": sem_bcast_const,
    "setr": sem_setr,
    "flane": sem_flane,
    "i2f": sem_i2f,
    "h2f": sem_h2f,
    "h2f_scalar": sem_h2f_scalar,
    "cmp_unord": sem_cmp_unord,
    "cmp_unord_k": sem_cmp_unord_k,
    "blendv": sem_blendv,
    "mask_mov": sem_mask_mov,
    "s_isnan": sem_s_isnan,
    "s_select": sem_s_select,
    "f32const": sem_f32const,
    "cast": sem_cast,
    "load": sem_load,
    "store": sem_store,
    "maskstore32": sem_maskstore32,
    "kstore32": sem_kstore32,
    "bitop": sem_bitop,
    "srli16": sem_srli16,
    "abs8": sem_abs8,
    "sign8": sem_sign8,
    "maddubs": sem_maddubs,
    "madd16": sem_madd16,
    "ilane": sem_ilane,
    "hadd32": sem_hadd32,
    "perm2x128": sem_perm2x128,
    "cmpgt32": sem_cmpgt32,
    "dpbusd": sem_dpbusd,
    "unpack": sem_unpack,
    "pshufd": sem_pshufd,
    "permvar32": sem_permvar32,
    "insert": sem_insert,
    "shuf_i64x2": sem_shuf_i64x2,
    "bcast_x4": sem_bcast_x4,
    "set64x2": sem_set64x2,
    "gpr2vec": sem_gpr2vec,
    "gpr_shl": sem_gpr_shl,
    "gpr_or": sem_gpr_or,
    "sload": sem_sload,
    "hint": sem_hint,
}


# ===================================================================== C1 / C4 verdict


def _norm(x, memo):
    """Canonical form up to commutation of add and mul (P15), for the secondary comparison."""
    if x.i in memo:
        return memo[x.i]
    nd = x.node()
    if nd[0] in ("add", "mul"):
        a, b = _norm(nd[1], memo), _norm(nd[2], memo)
        a, b = sorted((a, b), key=lambda z: z.i)
        r = S.ft(nd[0], a, b)
    elif nd[0] == "canon":
        r = S.ft("canon", _norm(nd[1], memo))
    else:
        r = x
    memo[x.i] = r
    return r


# ===================================================================== static rules (program text)


def _exprs(st):
    """The expressions a statement evaluates itself (not those of nested statements)."""
    if isinstance(st, Let):
        return [st.rhs]
    if isinstance(st, Set):
        return [st.rhs] + ([st.target.index] if isinstance(st.target, Idx) else [])
    if isinstance(st, Do):
        return [st.call]
    if isinstance(st, For):
        return [x for x in (st.init, st.cond, st.step) if x is not None]
    if isinstance(st, If):
        return [st.cond]
    return []


def _sub(e):
    """Every sub-expression of e, depth first."""
    yield e
    if isinstance(e, (IX, Call)):
        for x in e.args:
            yield from _sub(x)
    elif isinstance(e, Idx):
        yield from _sub(e.index)


def _names(e):
    """The variable and array names an expression reads."""
    out = set()
    for x in _sub(e):
        if isinstance(x, Var):
            out.add(x.name)
        elif isinstance(x, Idx):
            out.add(x.arr)
    return out


def _target(st):
    if isinstance(st, Let):
        return st.name
    return st.target.arr if isinstance(st.target, Idx) else st.target.name


def _target_or_var(st):
    if isinstance(st, Arr):
        return st.name
    return st.var if isinstance(st, For) else _target(st)


WIDE = {"int64_t", "size_t", "uint64_t"}


def _wide(ctype):
    """A 64-bit integer or a pointer type: the affine forms of block-count values are over Z, so
    they must not pass through a C type that could wrap them."""
    t = ctype.replace("const ", "").strip()
    return t in WIDE or t.endswith("*")


def is_block_loop(st):
    """The canonical block loop: for (v = 0; v < G; v++), declaring v."""
    return (
        isinstance(st, For)
        and st.declare
        and type(st.init) is int
        and st.init == 0
        and type(st.step) is int
        and st.step == 1
        and st.cond == IX("<", (Var(st.var), Var("G")))
    )


IX_OPS = {"lit", "cast", "?:", "+", "-", "*", "/", "%", "<<", "&"} | CMP_OPS
COMMENT_RE = re.compile(r"\A[ -~]*\Z")
# C2's provenance binding, at class level (review 2026-10-23, checker lens, finding 5): the entries
# that compute on FP values, select or compare them, write memory or prefetch may be created only
# by the primitive whose licence covers them. Other entries are bound by membership only.
PROV_BIND = {
    "fp": lambda p, e: (p == "P12" and e.ieee in ("fadd", "fmul", "i2f"))
    or (p == "P14" and e.ieee == "h2f")
    or (p == "P15" and e.ieee in ("fadd", "fmul")),
    "fpcmp": lambda p, e: p == "P13",
    "sel": lambda p, e: p == "P13",
    "store": lambda p, e: p == "P13",
    "hint": lambda p, e: p == "P11",
}


# Argument kinds of the isa entries, so that each argument is read the way C passes it (the call-side
# twin of the checker lens' finding 1, found by the reviser: a float parameter given an integer,
# or an integer parameter given a float, is a numeric conversion in C, while the checker would read
# the bits). v: a vector value; f32: a float value; i32: an int32 value, an index integer or a
# literal; u64: a uint64 value or a non-negative literal; int: an index integer or a literal,
# which C converts modulo 2^w as put() reads it; intd: the same or a scalar integer data value;
# imm: a non-negative literal; mask: a k-mask value or an index integer; ptr: a pointer.
ARG_DOC = {
    "v": "a vector",
    "f32": "a float",
    "i32": "a 32-bit integer",
    "u64": "a uint64_t",
    "int": "an integer index value",
    "intd": "an integer",
    "imm": "a non-negative literal",
    "mask": "a mask",
    "ptr": "a pointer",
}
SCALAR_KINDS = {
    "ld.u8": ("ptr",),
    "ld.s8": ("ptr",),
    "ld.u16": ("ptr",),
    "ld.i32": ("ptr",),
    "ld.f32": ("ptr",),
    "i32.add": ("i32", "i32"),
    "i32.sub": ("i32", "i32"),
    "i32.mul": ("i32", "i32"),
    "i32.and": ("i32", "i32"),
    "i32.shr": ("i32", "imm"),
    "i32.zero": (),
    "u64.shl": ("u64", "imm"),
    "u64.or": ("u64", "u64"),
    "f32.add": ("f32", "f32"),
    "f32.mul": ("f32", "f32"),
    "f32.from_i32": ("i32",),
    "f32.zero": (),
    "f32.bits": ("imm",),
    "f32.isnan": ("f32",),
    "f32.select": ("i32", "f32", "f32"),
    "f32.store": ("ptr", "f32"),
    "scalar.h2f_bits": ("u64",),
}
_IMM_ARG = {"srli16": 1, "perm2x128": 2, "insert": 2, "shuf_i64x2": 2, "pshufd": 1}
_MASK_ARG = {"mask_mov": 1, "kstore32": 1}


def arg_kinds(e):
    """The kind of each argument of entry e (ARG_DOC), from its semantics key."""
    if e.key in SCALAR_KINDS:
        return SCALAR_KINDS[e.key]
    n = len(set(re.findall(r"\{(\d+)\}", e.c)))
    kinds = ["v"] * n
    s = e.sem[0]
    if s in ("load", "store", "maskstore32", "kstore32", "hint", "sload") and n:
        kinds[0] = "ptr"
    if s in _IMM_ARG and n > _IMM_ARG[s]:
        kinds[_IMM_ARG[s]] = "imm"
    if s in _MASK_ARG and n > _MASK_ARG[s]:
        kinds[_MASK_ARG[s]] = "mask"
    if s == "bcast":
        kinds = ["f32" if e.ret in DATA_TYPES and not e.ret.endswith("i") else "intd"] * n
    if s in ("bcast_const", "setr"):
        kinds = ["int"] * n
    if s in ("set64x2", "gpr2vec"):
        kinds = ["intd"] * n
    return tuple(kinds)


def _placeholder_glued(spelling):
    """Argument positions whose placeholder touches an identifier character in the isa spelling
    (e.g. "x3_f32bits({0}u)"): the printed argument would merge with it, so only a non-negative
    int literal may stand there."""
    out = set()
    for m in re.finditer(r"\{(\d+)\}", spelling):
        before = spelling[m.start() - 1 : m.start()]
        after = spelling[m.end() : m.end() + 1]
        if re.search(r"\w", before) or re.search(r"\w", after):
            out.add(int(m.group(1)))
    return out


def _audit_expr(e, where):
    """Every string the printer would copy from an expression into the C (B9, no verbatim C)."""
    if isinstance(e, bool) or not isinstance(e, (int, Var, Idx, IX, Call)):
        raise Reject("C2: %r is not an expression the printer models (%s)" % (e, where))
    if isinstance(e, Var):
        if not ident_ok(e.name):
            raise Reject("C2: identifier %r (%s)" % (e.name, where))
    elif isinstance(e, Idx):
        if not ident_ok(e.arr):
            raise Reject("C2: identifier %r (%s)" % (e.arr, where))
        _audit_expr(e.index, where)
    elif isinstance(e, IX):
        if e.op not in IX_OPS:
            raise Reject("C2: index operator %r (%s)" % (e.op, where))
        if e.op == "lit":
            if len(e.args) != 1 or not (isinstance(e.args[0], str) and LIT_RE.search(e.args[0])):
                raise Reject("C2: literal %r is not a plain decimal int (%s)" % (e.args, where))
            return
        if e.op == "cast":
            t = e.args[0] if len(e.args) == 2 else None
            if not (t in PTR_ESZ or t in CINT):
                raise Reject("C2: cast type %r (%s)" % (t, where))
            _audit_expr(e.args[1], where)
            return
        if len(e.args) != (3 if e.op == "?:" else 2):
            raise Reject("C2: '%s' with %d operands (%s)" % (e.op, len(e.args), where))
        for x in e.args:
            _audit_expr(x, where)
    elif isinstance(e, Call):
        ent = TABLE.get(e.entry)
        if ent is None:
            raise Reject("C2: unknown isa entry %s" % e.entry)
        if ent.cls in BANNED_CLASSES:
            raise Reject("C2/B2-B7: banned instruction class %s (%s)" % (ent.cls, e.entry))
        nargs = len(set(re.findall(r"\{(\d+)\}", ent.c)))
        if len(e.args) != nargs:
            raise Reject("C2: %s takes %d arguments, not %d" % (e.entry, nargs, len(e.args)))
        glued = _placeholder_glued(ent.c)
        for j, y in enumerate(e.args):
            if isinstance(y, str):
                raise Reject("C2: verbatim text in an argument of %s" % e.entry)
            if isinstance(y, Call):  # the spellings put no parentheses around arguments
                raise Reject("C2: a call nested in an argument of %s (%s)" % (e.entry, where))
            if j in glued and not (type(y) is int and y >= 0):
                raise Reject("C2: argument %d of %s must be a non-negative literal" % (j, e.entry))
            _audit_expr(y, where)


def audit_static(func, log_ids):
    """C2 on the program text, executed or not (DESIGN 4.3 C2, 4.4): every statement carries a
    logged provenance id (bound to its primitive at class level, PROV_BIND), and every call, in
    every arm and every loop body, names a known isa entry outside the banned classes. Every string
    the printer copies into the C is one the checker models: identifiers, declared and cast types,
    literals and comment text (B9, no verbatim C; review 2026-10-23, checker lens, finding 2)."""
    if not (isinstance(func.name, str) and IDENT_RE.search(func.name)):
        raise Reject("C2: function name %r" % (func.name,))
    for ct, nm in func.params:
        if not ident_ok(nm):
            raise Reject("C2: parameter name %r" % (nm,))
    for st in walk(func.body):
        if isinstance(st, Comment):
            if not (isinstance(st.text, str) and COMMENT_RE.search(st.text)) or (
                "/*" in st.text or "*/" in st.text
            ):
                raise Reject("C2: comment text %r could end the comment" % (st.text,))
            continue
        if not isinstance(st, (Let, Set, Arr, Do, For, If)):
            raise Reject("C2: unknown statement %r" % (st,))
        prov = getattr(st, "prov", "")
        if prov not in log_ids:
            raise Reject("C2: statement without a logged provenance id: %r" % (prov,))
        if isinstance(st, (Let, Arr, For)):
            nm = st.var if isinstance(st, For) else st.name
            if not ident_ok(nm):
                raise Reject("C2: declared identifier %r" % (nm,))
            if decl_type(st.ctype) is None:
                raise Reject("C2: declared type %r of %s" % (st.ctype, nm))
        if isinstance(st, Arr) and not (type(st.n) is int and st.n > 0):
            raise Reject("C2: array %s of size %r" % (st.name, st.n))
        if isinstance(st, Let) and isinstance(st.rhs, Call) and st.rhs.entry in TABLE:
            ret = TABLE[st.rhs.entry].ret
            if decl_type(st.ctype) != decl_type(ret):
                raise Reject("C2: %s declared %s holds a %s result" % (st.name, st.ctype, ret))
        if isinstance(st, Set) and not isinstance(st.target, (Var, Idx)):
            raise Reject("C2: assignment target %r" % (st.target,))
        if isinstance(st, Set):
            _audit_expr(st.target, "target")
        where = "%s %s" % (type(st).__name__, prov)
        for e in _exprs(st):
            _audit_expr(e, where)
            for x in _sub(e):
                if isinstance(x, Call):
                    ent = TABLE[x.entry]
                    bind = PROV_BIND.get(ent.cls)
                    if bind is not None and not bind(prov.split(".")[0], ent):
                        raise Reject(
                            "C2: %s (%s) created under %s, whose licence does not cover it"
                            % (x.entry, ent.cls, prov)
                        )


def scopes(func):
    """C scoping, so that the checker's flat environment means what the printed C means: every
    name read or assigned is declared in an enclosing scope, and no declaration repeats or
    shadows a visible name (with a shadowed name, C would read another value than the checker)."""

    def need(e, vis):
        for nm in _names(e):
            if nm not in vis:
                raise Reject("C1: %s is used outside the scope that declares it" % nm)

    def declare(nm, vis):
        if nm in vis:
            raise Reject("C1: the declaration of %s repeats or shadows a visible name" % nm)

    def rec(body, outer):
        local = set()
        for st in body:
            vis = outer | local
            if isinstance(st, For):
                if st.init is not None:
                    need(st.init, vis)
                if st.declare:
                    declare(st.var, vis)
                    inner = vis | {st.var}
                elif st.var in vis:
                    inner = vis
                else:
                    raise Reject("C1: loop variable %s is not declared" % st.var)
                need(st.cond, inner)
                need(st.step, inner)
                rec(st.body, inner)
            elif isinstance(st, If):
                need(st.cond, vis)
                rec(st.then, vis)
                rec(st.other, vis)
            elif isinstance(st, (Let, Arr)):
                if isinstance(st, Let):
                    need(st.rhs, vis)
                declare(st.name, vis)
                local.add(st.name)
            elif isinstance(st, Set):
                for e in _exprs(st):
                    need(e, vis)
                if _target(st) not in vis:
                    raise Reject("C1: %s is assigned outside its scope" % _target(st))
            elif isinstance(st, Do):
                need(st.call, vis)

    rec(func.body, {p[1] for p in func.params})


def structure(func, kernel):
    """C1 visit order and block-count independence, on the program text (DESIGN 4.3 C1 (i)-(iv)).

    G must be declared once, at the top, as n / block, and n read nowhere else. A name is tainted
    if an integer definition of it reads n, G, a block index or a tainted name (a fixed point over
    the whole text, so copies of G are tainted too). A tainted value may only pass through + - *
    (never the product of two tainted values), casts and division by a constant: never into a
    branch, a ?: condition, a comparison, a bit operation or a loop bound, except the canonical
    block loop, which must not nest. Inside it only FP accumulations carry state (_carried).
    Returns the tainted names."""
    blk = kernel.params["block"]
    top = [st for st in func.body if isinstance(st, Let) and st.name == "G"]
    every = [st for st in walk(func.body) if isinstance(st, Let) and st.name == "G"]
    if len(top) != 1 or len(every) != 1 or top[0].rhs != IX("/", (Var("n"), blk)):
        raise Reject("C1: the block count must be declared once, at the top, as G = n / %d" % blk)
    for st in walk(func.body):
        if isinstance(st, Set) and _target(st) in ("n", "G"):
            raise Reject("C1: the block count or n is assigned")
        if st is not top[0] and any("n" in _names(e) for e in _exprs(st)):
            raise Reject("C1: n is read other than to declare the block count")
    taint = {"n", "G"}
    grew = True
    while grew:
        grew = False
        for st in walk(func.body):
            if isinstance(st, For):
                dst, src = st.var, _exprs(st)
            elif isinstance(st, (Let, Set)):
                dst, src = _target(st), ([] if isinstance(st.rhs, Call) else _exprs(st))
            else:
                continue
            if dst not in taint and any(_names(e) & taint for e in src):
                taint.add(dst)
                grew = True

    for st in walk(func.body):  # C types: a tainted value is never narrowed below 64 bits
        if isinstance(st, Let) and st.name in taint and not isinstance(st.rhs, Call):
            ct = st.ctype
        elif isinstance(st, For) and st.var in taint:
            ct = st.ctype
        elif isinstance(st, Arr) and st.name in taint and _is_int_t(decl_type(st.ctype)):
            ct = st.ctype  # integer array element (review 2026-10-23, checker lens, finding 4)
        else:
            ct = None
        if ct is not None and not _wide(ct):
            raise Reject(
                "C1: block-count value %s held in the narrow type %s" % (_target_or_var(st), ct)
            )

    def exprs_ok(e):
        for x in _sub(e):
            if isinstance(x, IX) and x.op == "cast" and _names(x.args[1]) & taint:
                if not _wide(x.args[0]):
                    raise Reject("C1: block-count value narrowed to %s" % x.args[0])
            if not isinstance(x, IX) or x.op in ("lit", "cast", "+", "-"):
                continue
            hot = [bool(_names(y) & taint) for y in x.args]
            if x.op == "?:":
                bad = hot[0]
            elif x.op == "*":
                bad = hot[0] and hot[1]
            elif x.op == "/":
                bad = hot[1] or (hot[0] and type(x.args[1]) is not int)
            else:
                bad = any(hot)
            if bad:
                raise Reject("C1: a block-count value reaches '%s': %s" % (x.op, repr(x)[:90]))

    def rec(body, loop):
        for st in body:
            if isinstance(st, For):
                if any(_names(e) & taint for e in _exprs(st)):
                    if not is_block_loop(st):
                        raise Reject(
                            "C1: loop %s has a block-count bound but is not the canonical "
                            "for (%s = 0; %s < G; %s++)" % ((st.var,) * 4)
                        )
                    if loop is not None:
                        raise Reject("C1: block loops nest (%s inside %s)" % (st.var, loop.var))
                    _carried(st, taint)
                    rec(st.body, st)
                    continue
                for e in _exprs(st):
                    exprs_ok(e)
                rec(st.body, loop)
            elif isinstance(st, If):
                if _names(st.cond) & taint:
                    raise Reject("C1: a branch tests a block-count value: %s" % repr(st.cond)[:90])
                exprs_ok(st.cond)
                rec(st.then, loop)
                rec(st.other, loop)
            else:
                for e in _exprs(st):
                    exprs_ok(e)

    rec(func.body, None)
    return taint


def _carried(loop, taint):
    """Inside a block loop the only state carried from one block to the next is an FP
    accumulator updated as X = add(X, y) (or add(y, X)) by an entry realising fadd, and X is read
    nowhere else in the loop. A name declared outside the loop and assigned inside it is such
    state. The block index is never assigned, inner loops declare their own index, and no store
    runs inside."""
    local = {loop.var}
    for st in walk(loop.body):
        if isinstance(st, (Let, Arr)):
            local.add(st.name)
        elif isinstance(st, For) and st.declare:
            local.add(st.var)
    upd = []
    for st in walk(loop.body):
        if isinstance(st, Do):
            ent = TABLE.get(st.call.entry)
            if ent is not None and ent.cls == "store":
                raise Reject("C4: a store inside block loop %s" % loop.var)
        if isinstance(st, For) and (st.var == loop.var or not st.declare):
            raise Reject("C1: a loop inside block loop %s advances %s" % (loop.var, st.var))
        if not isinstance(st, Set):
            continue
        if _target(st) == loop.var:
            raise Reject("C1: the block index %s is assigned inside its loop" % loop.var)
        if _target(st) in local:
            continue
        r = st.rhs
        ent = TABLE.get(r.entry) if isinstance(r, Call) else None
        ok = (
            ent is not None
            and ent.ieee == "fadd"
            and len(r.args) == 2
            and (r.args[0] == st.target) != (r.args[1] == st.target)
            and not (isinstance(st.target, Idx) and _names(st.target.index) & taint)
        )
        if not ok:
            raise Reject(
                "C1: %s carries state across blocks other than as an FP accumulation "
                "X = add(X, y) (or add(y, X), which C1 then accepts only under P15)" % _target(st)
            )
        upd.append(st)
    carried = {_target(st) for st in upd}
    for st in walk(loop.body):
        if any(st is u for u in upd):
            y = st.rhs.args[1] if st.rhs.args[0] == st.target else st.rhs.args[0]
            es = [y] + ([st.target.index] if isinstance(st.target, Idx) else [])
        else:
            es = _exprs(st)
        for e in es:
            hit = _names(e) & carried
            if hit:
                raise Reject(
                    "C1: accumulator %s is read inside the block loop other than by its own "
                    "accumulation" % sorted(hit)[0]
                )


def positions(body, base=()):
    """(position, statement) for every statement, with the positions Machine.run uses: the index
    path through statement lists, For bodies ("body") and If arms ("then", "other")."""
    for k, st in enumerate(body):
        pos = base + (k,)
        yield pos, st
        if isinstance(st, For):
            yield from positions(st.body, pos + ("body",))
        elif isinstance(st, If):
            yield from positions(st.then, pos + ("then",))
            yield from positions(st.other, pos + ("other",))


def _expr_roots(st, pos):
    """(path, expression) for the expressions a statement evaluates, as Machine.run names them."""
    if isinstance(st, Let):
        return [(pos + ("rhs",), st.rhs)]
    if isinstance(st, Set):
        out = [(pos + ("rhs",), st.rhs)]
        if isinstance(st.target, Idx):
            out.append((pos + ("tix", "i"), st.target.index))
        return out
    if isinstance(st, Do):
        return [(pos + ("call",), st.call)]
    if isinstance(st, For):
        return [(pos + (f,), getattr(st, f)) for f in ("init", "cond", "step")]
    if isinstance(st, If):
        return [(pos + ("cond",), st.cond)]
    return []


def _ternaries(e, path):
    """Paths of the ?: nodes in e, with the sub-expression paths Machine.ev uses."""
    if isinstance(e, IX):
        if e.op == "?:":
            yield path
        if e.op == "cast":
            yield from _ternaries(e.args[1], path + (1,))
        elif e.op != "lit":
            for j, x in enumerate(e.args):
                yield from _ternaries(x, path + (j,))
    elif isinstance(e, Call):
        for j, x in enumerate(e.args):
            yield from _ternaries(x, path + (j,))
    elif isinstance(e, Idx):
        yield from _ternaries(e.index, path + ("i",))


class Coverage:
    """Statements run and branch arms taken over the whole shape set. Code that never runs, or a
    branch arm never taken, is code the per-shape checks have not seen (C1 generalisation). Sites
    are positions in the program, so a statement object placed at two positions is two sites
    (review 2026-10-23, checker lens, finding 3)."""

    def __init__(self):
        self.ran = set()
        self.arms = {}

    def arm(self, site, c):
        self.arms.setdefault(site, set()).add(bool(c))

    def require(self, func):
        sts = [(p, st) for p, st in positions(func.body) if not isinstance(st, Comment)]
        for p, st in sts:
            if p not in self.ran:
                raise Reject(
                    "C1: a %s statement at %r never runs on the shape set (unchecked code)"
                    % (type(st).__name__, p)
                )
        sites = [(p + ("if",), st.cond) for p, st in sts if isinstance(st, If)]
        for p, st in sts:
            for root, e in _expr_roots(st, p):
                for q in _ternaries(e, root):
                    sites.append((q, None))
        for q, cond in sites:
            if len(self.arms.get(q, ())) < 2:
                raise Reject(
                    "C1: the branch at %r takes one arm only on the shape set (the other arm is "
                    "unchecked)%s" % (q, (": " + repr(cond)[:80]) if cond is not None else "")
                )
        return {"statements": len(sts), "branch_sites": len(sites)}


# ===================================================================== C1 / C4 verdict


# The meaning's REQUIRES strings that are not conditions on the shape, and how the checker carries
# each one. A REQUIRES string that is neither one of these, nor PRE1's range (checked against the
# activation format), nor a shape predicate, is refused: the meaning text and the checked domain
# cannot drift apart (review 2026-10-23, meaning lens, finding 3).
NON_SHAPE = {
    "A.sum == sum(A.q)": "PRE2: applied in C3's normal form (normal_form_I); P5's bias forms",
    "(mxcsr & 0xFFC0) == 0x1F80": "PRE3: the environment; leaves are IEEE operations under it",
    "Y disjoint from W and A": "PRE4: loads read only W and A, stores write only Y (C4); P9",
    "W and A readable, Y writable, over their extents": "PRE4: C4 keeps loads in W rows [r0, r1) "
    "and A's T*G blocks, and stores in the output set",
}
RANGE_RE = re.compile(r"\AA\.q in \[(-?\d+), (-?\d+)\]\Z")
SHAPE_NAMES = {"n", "T", "r0", "r1", "ldy"}
_PRED_NODES = (
    ast.Expression,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.Compare,
    ast.BinOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Mod,
    ast.UnaryOp,
    ast.USub,
    ast.Constant,
    ast.Load,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Eq,
    ast.NotEq,
)
_CMPF = {
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
}
_BINF = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Mod: lambda a, b: a % b,
}


def _shape_pred(src):
    """The parsed form of a REQUIRES string that is a condition on n, T, r0, r1, ldy and rows(W)
    only, built from integer constants, + - * %, comparisons, and, or; else None."""
    try:
        tree = ast.parse(src, mode="eval")
    except SyntaxError:
        return None
    for nd in ast.walk(tree):
        if isinstance(nd, ast.Call):
            a = nd.args
            if not (
                isinstance(nd.func, ast.Name)
                and nd.func.id == "rows"
                and len(a) == 1
                and not nd.keywords
                and isinstance(a[0], ast.Name)
                and a[0].id == "W"
            ):
                return None
        elif isinstance(nd, ast.Name):
            if nd.id not in SHAPE_NAMES | {"rows", "W"}:
                return None
        elif not isinstance(nd, _PRED_NODES):
            return None
        elif isinstance(nd, ast.Constant) and type(nd.value) is not int:
            return None
    return tree


def _pred(nd, env):
    if isinstance(nd, ast.Expression):
        return _pred(nd.body, env)
    if isinstance(nd, ast.BoolOp):
        vals = [_pred(v, env) for v in nd.values]
        return all(vals) if isinstance(nd.op, ast.And) else any(vals)
    if isinstance(nd, ast.Compare):
        left = _pred(nd.left, env)
        for op, c in zip(nd.ops, nd.comparators):
            right = _pred(c, env)
            if not _CMPF[type(op)](left, right):
                return False
            left = right
        return True
    if isinstance(nd, ast.BinOp):
        return _BINF[type(nd.op)](_pred(nd.left, env), _pred(nd.right, env))
    if isinstance(nd, ast.UnaryOp):
        return -_pred(nd.operand, env)
    if isinstance(nd, ast.Constant):
        return nd.value
    if isinstance(nd, ast.Call):
        return env["rows(W)"]
    return env[nd.id]


def preconditions(kernel):
    """The meaning's shape predicates, after checking that every other REQUIRES string is one
    the checker carries (NON_SHAPE) and that PRE1's range is the activation format's."""
    preds = []
    for src in kernel.requires:
        m = RANGE_RE.search(src)
        if m:
            want = kernel.params["A"][1].q.value_bounds()
            if (int(m.group(1)), int(m.group(2))) != tuple(want):
                raise ValueError("%r disagrees with the activation format's range %r" % (src, want))
            continue
        if src in NON_SHAPE:
            continue
        tree = _shape_pred(src)
        if tree is None:
            raise ValueError("the checker does not know the precondition %r" % (src,))
        preds.append((src, tree))
    return preds


def shape_ok(kernel, shape):
    """The meaning's shape preconditions (PRE5, PRE6), evaluated from meaning.REQUIRES itself, with
    rows(W) = r1 (the checker's W holds rows [0, r1)). A shape outside them is a harness error,
    not a verdict on the program."""
    n, T, r0, r1, ldy = shape
    env = {"n": n, "T": T, "r0": r0, "r1": r1, "ldy": ldy, "rows(W)": r1}
    for src, tree in preconditions(kernel):
        if not _pred(tree, env):
            raise ValueError("shape %r is outside the meaning's precondition %r" % (shape, src))
    if n % kernel.params["block"]:
        raise ValueError("shape %r: n is not a multiple of the format's block" % (shape,))


def check_shape(kernel, func, shape, log_ids, cov=None):
    shape_ok(kernel, shape)
    n, T, r0, r1, ldy = shape
    m = Machine(kernel, func, shape, log_ids, cov)
    m.execute()
    G = n // kernel.params["block"]
    want = {t * ldy + r for t in range(T) for r in range(r0, r1)}
    got = set(m.stores)
    if got != want:
        missing = sorted(want - got)[:5]
        raise Reject("C4: output locations not written exactly: missing %r" % missing)
    licensed = any(i.startswith(P15_ID) for i in log_ids)
    commuted = 0
    memo = {}
    for idx, term in m.stores.items():
        t, r = m.where[idx]
        exp = m.oracle.chain(t, r, G)
        if term != exp:
            if _norm(term, memo) == _norm(exp, memo):
                if not licensed:
                    raise Reject(
                        "C1: Y[t=%d, r=%d] equals canon(F_{t,r}(G)) only up to commutation, and "
                        "no P15 application is logged" % (t, r)
                    )
                commuted += 1
                continue
            raise Reject("C1: Y[t=%d, r=%d] is not canon(F_{t,r}(G)) in canonical order" % (t, r))
    return {"stores": len(m.stores), "loads": m.loads, "commuted": commuted, **m.facts}


def default_shapes(lanes, tail_lanes=None):
    """Bounded shape set: every row-tail width of every tile size, every token-tail width (T = 1..9,
    16, 17), G = 1..5 on both the T == 1 and T > 1 paths, offsets r0 > 0, the degenerate T = 0
    and r0 = r1, and three output layouts: the callers' own (r0 = 0, ldy = r1), the tightest the
    precondition allows (ldy = r1 - r0 < r1), and T == 1 with ldy below the row count."""
    shapes = set()
    L = max(lanes, 1)
    tl = tail_lanes or L
    widths = sorted(
        {1, 2, 3, L - 1, L, L + 1} | {L + k for k in range(1, tl + 1)} | {2 * L + tl - 1, 2 * L}
    )
    for rows in widths:
        if rows <= 0:
            continue
        for T in (1, 2):
            shapes.add((64 * (1 + (rows % 2)), T, 0, rows, rows + 1))
    for T in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 16, 17):  # every token-tail width 1..8
        shapes.add((128, T, 1, 1 + L + 2, L + 5))
    for G in (1, 2, 3):
        shapes.add((64 * G, 9, 3, 3 + L + tl - 1, L + tl + 4))
    for G in (3, 4, 5):
        for T in (1, 2):
            shapes.add((64 * G, T, 0, L + 1, L + 3))
    shapes.add((128, 5, 2, 2, 7))
    shapes.add((128, 2, 0, L + 3, L + 3))
    shapes.add((128, 3, L, 2 * L + 1, L + 1))
    shapes.add((64, 1, 2, L + 3, 1))
    return sorted(shapes)


def check_func(kernel, func, log_ids, shapes):
    """The whole check, in order: C2 on the program text; C scoping; the static C1 rules; C1-C4
    on every shape, with block-count forms; then statement and branch coverage. A Reject carries
    .stage, and .shape when a shape exposed it."""
    for stage, fn in (
        ("C2 static audit", lambda: audit_static(func, log_ids)),
        ("C scoping", lambda: scopes(func)),
        ("C1 structure", lambda: structure(func, kernel)),
    ):
        try:
            fn()
        except Reject as e:
            e.stage = stage
            raise
    cov = Coverage()
    out = {"shapes": len(shapes), "stores": 0, "i2f_proved": 0, "canon_lifted": 0, "commuted": 0}
    for sh in shapes:
        try:
            r = check_shape(kernel, func, sh, log_ids, cov)
        except Reject as e:
            e.stage, e.shape = "shape", sh
            raise
        for k in ("stores", "i2f_proved", "canon_lifted", "commuted"):
            out[k] += r[k]
    try:
        out.update(cov.require(func))
    except Reject as e:
        e.stage = "C1 coverage"
        raise
    return out
