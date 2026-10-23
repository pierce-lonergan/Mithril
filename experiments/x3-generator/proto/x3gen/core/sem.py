"""Symbolic semantics of isa entries for the global checker (library L; trusted within X3).

Values are byte-slot vectors. A slot is a concrete byte (int) or Sl(obj, k, w): byte k of a w-byte
symbolic value obj. Symbolic values:
  Tab   integer bit pattern that is a function of at most two input bytes (DESIGN 4.3 C3(a), the
        bit-vector layer): a table over the bytes' declared domains. Bit ops, shifts, abs, sign and
        byte moves stay in this layer; every claim about a lane is proved by enumerating its table.
  Poly  exact integer, a polynomial over Z in named atoms (wq, xq, xsum) with a proved interval
        (C3(b), the ring layer). A Tab enters it only through an exhaustively verified fit.
  FT    an IEEE binary32 term, hash-consed (C1).
  Pred  an all-ones/all-zero lane predicate (isnan of an FT, or a comparison).
Anything the rules cannot establish raises Unknown, which the checker treats as rejection.
Leaves are named only by the address they were loaded from (DESIGN 4.3, "leaf naming").
"""

from fractions import Fraction

from . import fp32


class Unknown(Exception):
    """The checker cannot establish a fact: rejection (02 section 1)."""


# ===================================================================== tables (bit-vector layer)

_TBL = []
_TID = {}


def tid_of(t):
    t = tuple(t)
    i = _TID.get(t)
    if i is None:
        i = len(_TBL)
        _TBL.append(t)
        _TID[t] = i
    return i


def table(tid):
    return _TBL[tid]


class Tab:
    """Bit pattern of width w bytes (unsigned value in the table) over leaf bytes deps."""

    __slots__ = ("deps", "tid", "w")
    _intern = {}

    def __new__(cls, deps, tid, w):
        key = (deps, tid, w)
        o = cls._intern.get(key)
        if o is None:
            o = object.__new__(cls)
            o.deps, o.tid, o.w = deps, tid, w
            cls._intern[key] = o
        return o

    def __repr__(self):
        return "Tab(%r, t%d, w%d)" % (self.deps, self.tid, self.w)


ID8 = tid_of(range(256))


_MEMO = {}


class Ctx:
    """Domain knowledge: which leaf bytes exist and their declared value domains, and the atoms a
    leaf byte carries (from the formats, through the address decoder). Memo tables are shared by
    every shape checked against the same formats (they depend on tables and domains only)."""

    def __init__(self, decoder, memo_key=None):
        self.dec = decoder
        m = (
            _MEMO.setdefault(memo_key, {"fit": {}, "op": {}, "red": {}})
            if memo_key
            else {"fit": {}, "op": {}, "red": {}}
        )
        self.fit_memo, self.op_memo, self.red_memo = m["fit"], m["op"], m["red"]

    def domain(self, leaf):
        return self.dec.domain(leaf)


def _s8(b):
    return b - 256 if b >= 128 else b


def opfn(op):
    """Named bit-vector operations (the memo key is the name, never a closure)."""
    k = op[0]
    if k == "join":
        return lambda *b: sum(x << (8 * i) for i, x in enumerate(b))
    if k == "byte":
        return lambda v, s=op[1]: v >> (8 * s)
    if k == "and":
        return lambda x, y: x & y
    if k == "or":
        return lambda x, y: x | y
    if k == "xor":
        return lambda x, y: x ^ y
    if k == "abs8":
        return lambda x: abs(_s8(x)) & 255
    if k == "sign8":
        return lambda x, y: x if _s8(y) > 0 else (0 if _s8(y) == 0 else (-_s8(x)) & 255)
    if k == "mulus":
        return lambda u, s: u * _s8(s)
    if k == "srl16":
        return lambda v, c=op[1]: (v & 0xFFFF) >> c
    if k == "sext8":
        return lambda b: 255 if b >= 128 else 0
    if k == "andc":
        return lambda v, c=op[1]: v & c
    if k == "sra":
        return lambda v, c=op[1], w=op[2]: (v - (1 << (8 * w)) if v >= 1 << (8 * w - 1) else v) >> c
    raise Unknown("unknown bit-vector operation %r" % (op,))


def leaf_byte(leaf):
    return Tab((leaf,), ID8, 1)


def const_tab(v, w):
    return Tab((), tid_of([v & ((1 << (8 * w)) - 1)]), w)


def _index_space(cx, deps):
    """All (index, values) assignments over the declared domains of deps."""
    if not deps:
        return [(0, ())]
    d0 = cx.domain(deps[0])
    if len(deps) == 1:
        return [(b, (b,)) for b in d0]
    d1 = cx.domain(deps[1])
    return [(b0 + 256 * b1, (b0, b1)) for b1 in d1 for b0 in d0]


def tab_eval(t: Tab, assign):
    """Value of t under an assignment {leaf: byte}."""
    tb = table(t.tid)
    if not t.deps:
        return tb[0]
    idx = assign[t.deps[0]]
    if len(t.deps) == 2:
        idx += 256 * assign[t.deps[1]]
    return tb[idx]


def combine(cx, parts, op, w):
    """New Tab of width w: op(values of parts) over the union of the parts' leaves (at most two),
    reduced to the leaves it actually depends on (proved by enumeration over their domains)."""
    deps = []
    for p in parts:
        if isinstance(p, Tab):
            for d in p.deps:
                if d not in deps:
                    deps.append(d)
    if len(deps) > 2:
        raise Unknown("value depends on more than two input bytes")
    deps = tuple(deps)
    key = (
        op,
        w,
        tuple(
            (p.tid, tuple(deps.index(d) for d in p.deps)) if isinstance(p, Tab) else ("c", p)
            for p in parts
        ),
    )
    tid = cx.op_memo.get(key)
    if tid is None:
        fn = opfn(op)
        mask = (1 << (8 * w)) - 1
        size = 256 ** len(deps)
        cols = []
        for p in parts:
            if isinstance(p, Tab):
                pt = table(p.tid)
                pos = [deps.index(d) for d in p.deps]
                if not pos:
                    cols.append([pt[0]] * size)
                elif len(pos) == 1:
                    if pos[0] == 0:
                        cols.append([pt[i % 256] for i in range(size)])
                    else:
                        cols.append([pt[i // 256] for i in range(size)])
                else:
                    if pos == [0, 1]:
                        cols.append(list(pt[:size]))
                    else:
                        cols.append([pt[(i // 256) + 256 * (i % 256)] for i in range(size)])
            else:
                cols.append([p] * size)
        tid = tid_of([fn(*args) & mask for args in zip(*cols)])
        cx.op_memo[key] = tid
    return reduce_deps(cx, Tab(deps, tid, w))


def _dsig(cx, d):
    return len(cx.domain(d)), cx.domain(d)[0], cx.domain(d)[-1]


def reduce_deps(cx, t: Tab):
    """Drop leaves the table does not depend on over their declared domains (proved by enumeration)."""
    if not t.deps:
        return t
    key = (t.tid, t.w, tuple(_dsig(cx, d) for d in t.deps))
    r = cx.red_memo.get(key)
    if r is None:
        r = _reduce(cx, t)
        cx.red_memo[key] = r
    keep, tid = r
    return Tab(tuple(t.deps[i] for i in keep), tid, t.w)


def _reduce(cx, t):
    tb = table(t.tid)
    if len(t.deps) == 1:
        d0 = cx.domain(t.deps[0])
        v = tb[d0[0]]
        if all(tb[b] == v for b in d0):
            return (), tid_of([v])
        return (0,), t.tid
    d0, d1 = cx.domain(t.deps[0]), cx.domain(t.deps[1])
    if all(tb[b0 + 256 * b1] == tb[b0 + 256 * d1[0]] for b1 in d1 for b0 in d0):
        sub = tid_of([tb[b + 256 * d1[0]] for b in range(256)])
        keep, tid = _reduce(cx, Tab((t.deps[0],), sub, t.w))
        return tuple(0 for _ in keep), tid
    if all(tb[b0 + 256 * b1] == tb[d0[0] + 256 * b1] for b1 in d1 for b0 in d0):
        sub = tid_of([tb[d0[0] + 256 * b] for b in range(256)])
        keep, tid = _reduce(cx, Tab((t.deps[1],), sub, t.w))
        return tuple(1 for _ in keep), tid
    return (0, 1), t.tid


def tab_range(cx, t: Tab, signed):
    bits = 8 * t.w
    vals = set(table(t.tid)[i] for i, _ in _index_space(cx, t.deps))
    if signed:
        vals = {v - (1 << bits) if v >= 1 << (bits - 1) else v for v in vals}
    return min(vals), max(vals)


# ===================================================================== ring layer


class Poly:
    """Exact integer: {monomial (sorted tuple of atoms): coefficient} with a proved interval."""

    __slots__ = ("terms", "lo", "hi")

    def __init__(self, terms, lo, hi):
        self.terms = {m: c for m, c in terms.items() if c}
        self.lo, self.hi = lo, hi

    def __repr__(self):
        return "Poly(%d terms, [%d, %d])" % (len(self.terms), self.lo, self.hi)


def pconst(v):
    return Poly({(): v}, v, v)


def padd(a, b, sign=1):
    t = dict(a.terms)
    for m, c in b.terms.items():
        t[m] = t.get(m, 0) + sign * c
    lo = a.lo + (b.lo if sign > 0 else -b.hi)
    hi = a.hi + (b.hi if sign > 0 else -b.lo)
    return Poly(t, lo, hi)


def pscale(a, k):
    lo, hi = sorted((a.lo * k, a.hi * k))
    return Poly({m: c * k for m, c in a.terms.items()}, lo, hi)


def as_poly(cx, v, signed=True, width=None):
    """A lane value as a Poly: ints and Polys directly, a Tab through an exhaustive fit."""
    if isinstance(v, Poly):
        return v
    if isinstance(v, int):
        if signed and width and v >= 1 << (8 * width - 1):
            v -= 1 << (8 * width)
        return pconst(v)
    if isinstance(v, Tab):
        return fit(cx, v, signed)
    if isinstance(v, FLeafI):
        return Poly({(v.atom,): 1}, v.lo, v.hi)
    raise Unknown("integer operand is not integer-valued: %r" % (v,))


def _solve(rows, rhs):
    """Exact Gaussian elimination; rows are lists of Fractions. Returns a solution or None."""
    n = len(rows[0])
    m = [list(r) + [b] for r, b in zip(rows, rhs)]
    piv_cols = []
    r = 0
    for c in range(n):
        p = next((i for i in range(r, len(m)) if m[i][c] != 0), None)
        if p is None:
            continue
        m[r], m[p] = m[p], m[r]
        inv = 1 / m[r][c]
        m[r] = [x * inv for x in m[r]]
        for i in range(len(m)):
            if i != r and m[i][c] != 0:
                f = m[i][c]
                m[i] = [x - f * y for x, y in zip(m[i], m[r])]
        piv_cols.append(c)
        r += 1
    for i in range(r, len(m)):
        if m[i][-1] != 0:
            return None
    sol = [Fraction(0)] * n
    for i, c in enumerate(piv_cols):
        sol[c] = m[i][-1]
    return sol


def fit(cx, t: Tab, signed):
    """Prove t (read as a signed or unsigned integer) equal to a polynomial of degree <= 2 in the
    atoms its leaf bytes carry, by solving on samples and verifying on the whole declared domain."""
    deps = t.deps
    if not deps:
        v = table(t.tid)[0]
        if signed and v >= 1 << (8 * t.w - 1):
            v -= 1 << (8 * t.w)
        return pconst(v)
    atoms = [cx.dec.atoms(d) for d in deps]  # per dep: list of (atom name, fn(byte) -> int)
    kinds = tuple(tuple(name[0] for name, _ in a) for a in atoms)
    key = (
        t.tid,
        t.w,
        signed,
        tuple(cx.dec.atom_shape(d) for d in deps),
        tuple(tuple(cx.domain(d)) == tuple(range(256)) for d in deps),
    )
    sol = cx.fit_memo.get(key)
    if sol is None:
        mons = [()]
        for di, a in enumerate(atoms):
            mons += [((di, ai),) for ai in range(len(a))]
        if len(deps) == 2:
            mons += [((0, i), (1, j)) for i in range(len(atoms[0])) for j in range(len(atoms[1]))]
        pts = _index_space(cx, deps)
        tb = table(t.tid)
        bits = 8 * t.w

        def target(idx):
            v = tb[idx]
            return v - (1 << bits) if signed and v >= 1 << (bits - 1) else v

        def row(vals):
            out = []
            for mon in mons:
                p = 1
                for di, ai in mon:
                    p *= atoms[di][ai][1](vals[di])
                out.append(Fraction(p))
            return out

        step = max(1, len(pts) // 997)
        sample = pts[::step][:4000]
        s = _solve([row(v) for _, v in sample], [Fraction(target(i)) for i, _ in sample])
        if s is None or any(c.denominator != 1 for c in s):
            cx.fit_memo[key] = ("fail",)
            raise Unknown("no polynomial identity for an integer operand")
        coef = [int(c) for c in s]
        for idx, vals in pts:
            acc = 0
            for c, mon in zip(coef, mons):
                if c:
                    p = c
                    for di, ai in mon:
                        p *= atoms[di][ai][1](vals[di])
                    acc += p
            if acc != target(idx):
                cx.fit_memo[key] = ("fail",)
                raise Unknown("integer operand fails its identity at some input (bit-vector layer)")
        rng = [target(i) for i, _ in pts]
        sol = ("ok", tuple(zip(coef, mons)), min(rng), max(rng))
        cx.fit_memo[key] = sol
    if sol[0] == "fail":
        raise Unknown("no polynomial identity for an integer operand")
    _, cm, lo, hi = sol
    terms = {}
    for c, mon in cm:
        if c:
            m = tuple(sorted(atoms[di][ai][0] for di, ai in mon))
            terms[m] = terms.get(m, 0) + c
    del kinds
    return Poly(terms, lo, hi)


# ===================================================================== FP terms (C1)

_FT = {}
_FTL = []


def ft(*node):
    i = _FT.get(node)
    if i is None:
        i = len(_FTL)
        _FTL.append(node)
        _FT[node] = i
    return FT(i)


class FT:
    __slots__ = ("i",)

    def __init__(self, i):
        self.i = i

    def __eq__(self, o):
        return isinstance(o, FT) and o.i == self.i

    def __hash__(self):
        return hash(("FT", self.i))

    def node(self):
        return _FTL[self.i]

    def __repr__(self):
        return "FT%d%r" % (self.i, self.node()[:1])


class Pred:
    __slots__ = ("node",)

    def __init__(self, node):
        self.node = node

    def __eq__(self, o):
        return isinstance(o, Pred) and o.node == self.node

    def __hash__(self):
        return hash(("Pred", self.node))


class FLeafI:
    """An i32 input field read whole (the activation sum): a ring atom with its declared range."""

    __slots__ = ("atom", "lo", "hi")

    def __init__(self, atom, lo, hi):
        self.atom, self.lo, self.hi = atom, lo, hi


class Undef:
    pass


UNDEF = Undef()


class Sl:
    __slots__ = ("obj", "k", "w")

    def __init__(self, obj, k, w):
        self.obj, self.k, self.w = obj, k, w


def put(vals, w):
    """Lane values of width w -> byte slots."""
    out = []
    for v in vals:
        if isinstance(v, int):
            v &= (1 << (8 * w)) - 1
            out.extend((v >> (8 * k)) & 255 for k in range(w))
        elif isinstance(v, Tab) and v.w == w and not v.deps:
            c = table(v.tid)[0]
            out.extend((c >> (8 * k)) & 255 for k in range(w))
        else:
            out.extend(Sl(v, k, w) for k in range(w))
    return out


def byte_of(cx, s):
    """One slot as a byte-level value: int or width-1 Tab."""
    if isinstance(s, int):
        return s
    if isinstance(s, Tab):
        return s
    if isinstance(s, Sl):
        o = s.obj
        if isinstance(o, Tab):
            if o.w == 1:
                return o
            return combine(cx, [o], ("byte", s.k), 1)
    raise Unknown("byte of a non-bit-vector value")


def lanes(cx, slots, w, kind="int"):
    """Byte slots -> lane values of width w. kind 'int' | 'f32' | 'f16' | 'pred'."""
    out = []
    for i in range(0, len(slots), w):
        grp = slots[i : i + w]
        if all(isinstance(s, int) for s in grp):
            out.append(sum(b << (8 * k) for k, b in enumerate(grp)))
            continue
        s0 = grp[0]
        if (
            isinstance(s0, Sl)
            and s0.w == w
            and all(isinstance(s, Sl) and s.obj is s0.obj and s.k == k for k, s in enumerate(grp))
        ):
            out.append(s0.obj)
            continue
        if any(isinstance(s, Sl) and s.obj is UNDEF for s in grp):
            raise Unknown("use of an undefined lane")
        fl = cx.dec.field_run(grp, w, kind)
        if fl is not None:
            out.append(fl)
            continue
        bs = [byte_of(cx, s) for s in grp]
        out.append(combine(cx, bs, ("join",), w))
    return out


def as_ft(cx, v):
    if isinstance(v, FT):
        return v
    if isinstance(v, int):
        return ft("c", v & 0xFFFFFFFF)
    if isinstance(v, Tab) and not v.deps:
        return ft("c", table(v.tid)[0])
    raise Unknown("FP operand is not an FP term: %r" % (v,))
