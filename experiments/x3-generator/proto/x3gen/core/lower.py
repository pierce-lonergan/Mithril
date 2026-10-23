"""Lowering of a scheduled loop tree to a lane program (library L, untrusted).

The walker follows the tree the primitives built. Meaning FP ops are mapped one to one onto isa
entries whose 'ieee' field names them (P12); integer leaves, scale leaves, canon and stores go
through the recipes the schedule chose (P5, P14, P13). Nothing here is trusted: C1-C4 re-check the
lane program it produces.
"""

from contextlib import contextmanager

from ..isa import TABLE
from . import recipes
from .ir import E, Init, Loop, Region, Spec, Store, Update, iter_nodes, walk
from .lp import IX, Arr, Call, Do, For, Func, Idx, If, Let, Set, Var, add, ix, mul
from .sched import PrimError, role

WIDTH_PFX = {128: "_mm_", 256: "_mm256_", 512: "_mm512_"}
VEC_F = {128: "__m128", 256: "__m256", 512: "__m512"}


class Emitter:
    def __init__(self):
        self.prologue = []
        self.body = []
        self.cur = self.body
        self.counts = {}
        self.consts = {}

    def fresh(self, base):
        n = self.counts.get(base, 0)
        self.counts[base] = n + 1
        return base if n == 0 else "%s%d" % (base, n)

    def emit(self, st):
        self.cur.append(st)

    def call(self, key, *args, base="v", prov="", mut=False, lanes=None):
        e = TABLE[key]
        name = self.fresh(base)
        self.emit(Let(name, e.ret, Call(key, tuple(args)), mut=mut, prov=prov, lanes=lanes))
        return Var(name)

    def const(self, key, *args, base="k", prov=""):
        """A loop-invariant constant, emitted once in the function prologue."""
        sig = (key, args)
        if sig not in self.consts:
            e = TABLE[key]
            name = self.fresh(base)
            self.prologue.append(Let(name, e.ret, Call(key, tuple(args)), prov=prov))
            self.consts[sig] = Var(name)
        return self.consts[sig]

    def let(self, base, ctype, rhs, prov="", mut=False):
        name = self.fresh(base)
        self.emit(Let(name, ctype, rhs, mut=mut, prov=prov))
        return Var(name)

    def set(self, target, rhs, prov="", lanes=None):
        self.emit(Set(target, rhs, prov=prov, lanes=lanes))

    def do(self, key, *args, prov="", lanes=None):
        self.emit(Do(Call(key, tuple(args)), prov=prov, lanes=lanes))

    @contextmanager
    def into(self, lst):
        old = self.cur
        self.cur = lst
        try:
            yield lst
        finally:
            self.cur = old

    @contextmanager
    def loop(self, var, lo, hi, step=1, ctype="int", prov="", declare=True):
        body = []
        cond = ix("<", Var(var), hi)
        self.emit(For(var, ctype, lo, cond, step, body, prov=prov, declare=declare))
        with self.into(body):
            yield Var(var)


class Tile:
    def __init__(self, lanes, width, layout, store, rows, nr=None, smask=None, kmask=None):
        self.lanes, self.width, self.layout, self.store = lanes, width, layout, store
        self.rows, self.nr, self.smask, self.kmask = rows, nr, smask, kmask


class Ctx:
    def __init__(self, sched):
        self.s = sched
        k = sched.k
        self.F = k.params["W"][1]
        self.AF = k.params["A"][1]
        self.em = Emitter()
        self.width = None
        self.tile = None
        self.rowptr = None
        self.t = None
        self.tconst = None
        self.ti = None
        self.tblock = None
        self.tn = None
        self.g = None
        self.go = None
        self.hoisted = {}
        self.cache = {}


def _vf(width):
    return VEC_F[width]


def lower(sched, fname):
    cx = Ctx(sched)
    k = sched.k
    em = cx.em
    p0 = sched.implicit
    em.let("Wb", "const uint8_t *", ix("cast", "const uint8_t *", Var("W")), prov=p0)
    em.let("Ab", "const uint8_t *", ix("cast", "const uint8_t *", Var("act")), prov=p0)
    em.let("G", "const int64_t", ix("/", Var("n"), k.params["block"]), prov=p0)
    em.let("rb", "const size_t", ix("*", ix("cast", "size_t", Var("G")), cx.F.size), prov=p0)
    if any(isinstance(n, Loop) and role(n.var) == "r" for n in iter_nodes(k.body)):
        em.let("r", "int64_t", Var("r0"), prov=p0, mut=True)
    _body(k.body, cx)
    body = em.prologue + em.body
    return Func(fname, k.slot.params, body, k.name, sched.isa)


def _body(nodes, cx):
    for n in nodes:
        _node(n, cx)


def _node(n, cx):
    if isinstance(n, Spec):
        if n.pred != ("T", "==", 1):
            raise PrimError("lowering: unsupported specialisation")
        then, other = [], []
        saved = cx.tconst
        with cx.em.into(then):
            cx.tconst = 1
            _body(n.then, cx)
        cx.tconst = saved
        with cx.em.into(other):
            _body(n.other, cx)
        cx.em.emit(If(ix("==", Var("T"), 1), then, other, prov=n.prov[-1]))
    elif isinstance(n, Region):
        _body(n.body, cx)
    elif isinstance(n, Loop):
        {"r": _row_loop, "t": _tok_loop, "g": _g_loop}[role(n.var)](n, cx)
    elif isinstance(n, Init):
        _init(n, cx)
    elif isinstance(n, Update):
        _update(n, cx)
    elif isinstance(n, Store):
        _store(n, cx)
    else:
        raise PrimError("lowering: unknown node %r" % (n,))


# ------------------------------------------------------------------ row loops


def _lane_loop(n):
    for x in iter_nodes(n.body):
        if isinstance(x, Loop) and x.lanes and x.origin and x.origin[0] == n.var:
            return x
    return None


def _row_loop(n, cx):
    em = cx.em
    prov = n.prov[-1] if n.prov else cx.s.implicit
    if n.lanes:  # the lane loop itself: rows were bound by its tile loop
        saved = (cx.width, cx.tile)
        cx.width = n.vec["width"]
        cx.tile = cx.pending_tile
        _vector_scope(n, cx)
        cx.width, cx.tile = saved
        return
    if n.step == 1:  # a scalar row loop
        with em.loop("r", None, Var("r1"), 1, ctype="int64_t", prov=prov, declare=False):
            cx.rowptr = em.let(
                "wr",
                "const uint8_t *",
                add(Var("Wb"), mul(ix("cast", "size_t", Var("r")), Var("rb"))),
                prov=prov,
            )
            _body(n.body, cx)
        return
    lv = _lane_loop(n)
    if lv is None:
        raise PrimError("lowering: split row loop without a vectorised lane loop")
    L = n.step
    cond = ix("<=", add(Var("r"), L), Var("r1")) if n.only_full else ix("<", Var("r"), Var("r1"))
    body = []
    em.emit(For("r", "int64_t", None, cond, L, body, prov=prov, declare=False))
    with em.into(body):
        rows, nr = [], None
        if n.tail == "dup_last":
            nr = em.let(
                "nr",
                "const int",
                ix(
                    "?:",
                    ix("<", ix("-", Var("r1"), Var("r")), L),
                    ix("cast", "int", ix("-", Var("r1"), Var("r"))),
                    L,
                ),
                prov=prov,
            )
        for kk in range(L):
            if n.tail == "dup_last" and kk:
                ridx = add(Var("r"), ix("?:", ix("<", kk, nr), kk, ix("-", nr, 1)))
            else:
                ridx = add(Var("r"), kk)
            rows.append(
                em.let(
                    "w",
                    "const uint8_t *",
                    add(Var("Wb"), mul(ix("cast", "size_t", ridx), Var("rb"))),
                    prov=prov,
                )
            )
        smask = kmask = None
        store = lv.vec["store"]
        if store == "mask":
            pv = lv.prov[-1]
            nv = em.call("_mm256_set1_epi32", nr, base="nrv", prov=pv)
            iv = em.const("_mm256_setr_epi32", *range(8), base="lane", prov=pv)
            smask = em.call("_mm256_cmpgt_epi32", nv, iv, base="smask", prov=pv)
        elif store == "kmask":
            kmask = em.let(
                "sm",
                "const __mmask8",
                ix("cast", "__mmask8", ix("-", ix("<<", ix("lit", "1u"), nr), ix("lit", "1u"))),
                prov=lv.prov[-1],
            )
        cx.pending_tile = Tile(L, lv.vec["width"], lv.vec["layout"], store, rows, nr, smask, kmask)
        _body(n.body, cx)


def _vector_scope(n, cx):
    """Body of a lane loop: declare accumulator arrays expanded over a token block."""
    em = cx.em
    for x in iter_nodes(n.body):
        if isinstance(x, Init) and x.expanded_over:
            if cx.tblock is None:
                raise PrimError("lowering: expanded accumulator outside a token block")
            name = x.acc
            if ("arr", name) not in cx.cache:
                em.emit(Arr(name, _vf(cx.width), cx.tblock, prov=x.prov[-1] if x.prov else ""))
                cx.cache[("arr", name)] = True
    _body(n.body, cx)
    cx.cache = {k: v for k, v in cx.cache.items() if k[0] != "arr"}


# ------------------------------------------------------------------ token loops


def _tok_loop(n, cx):
    em = cx.em
    prov = n.prov[-1] if n.prov else cx.s.implicit
    if n.origin is not None:  # inner piece of a blocked token loop
        with em.loop("ti", 0, cx.tn, 1, prov=prov) as ti:
            cx.t, cx.ti = add(Var("t0"), ti), ti
            _body(n.body, cx)
        cx.t, cx.ti = None, None
        return
    if n.step > 1:
        B = n.step
        body = []
        em.emit(For("t0", "int", 0, ix("<", Var("t0"), Var("T")), B, body, prov=prov))
        with em.into(body):
            tn = em.let(
                "tn",
                "const int",
                ix("?:", ix("<", ix("-", Var("T"), Var("t0")), B), ix("-", Var("T"), Var("t0")), B),
                prov=prov,
            )
            saved = (cx.tblock, cx.tn)
            cx.tblock, cx.tn = B, tn
            _body(n.body, cx)
            cx.tblock, cx.tn = saved
        return
    if cx.tconst == 1:  # the T == 1 copy: one token, no loop
        cx.t = 0
        _body(n.body, cx)
        cx.t = None
        return
    with em.loop("t", 0, Var("T"), 1, prov=prov) as t:
        cx.t = t
        _body(n.body, cx)
    cx.t = None


# ------------------------------------------------------------------ block loop


def _rows(cx):
    return cx.tile.rows if cx.tile is not None else [cx.rowptr]


def _g_loop(n, cx):
    em = cx.em
    prov = n.prov[-1] if n.prov else cx.s.implicit
    with em.loop("g", 0, Var("G"), 1, ctype="int64_t", prov=prov) as g:
        cx.g = g
        cx.go = em.let("go", "const size_t", mul(ix("cast", "size_t", g), cx.F.size), prov=prov)
        pf = n.vec.get("prefetch")
        if pf:
            ahead, pid = pf
            for r in _rows(cx):
                em.do(
                    "_mm_prefetch_t0",
                    add(r, mul(ix("cast", "size_t", add(g, ahead)), cx.F.size)),
                    prov=pid,
                )
        cx.hoisted = {}
        if n.hoist == ("W",):
            for u in iter_nodes(n.body):
                if isinstance(u, Update):
                    _hoist_w(u, cx)
        _body(n.body, cx)
        cx.hoisted = {}
    cx.g = cx.go = None


def _recipe(u, cx):
    using, opts, pid = u.lower["isum"]
    key = ("recipe", id(u), cx.width)
    if key not in cx.cache:
        cx.cache[key] = (recipes.ISUM[using](cx, opts, pid), pid)
    return cx.cache[key]


def _hoist_w(u, cx):
    rec, pid = _recipe(u, cx)
    cx.hoisted["dec"] = rec.decode(_rows(cx), cx.go)
    pack, conv, spid = u.lower["scales"]
    cx.hoisted["dw"] = recipes.scales(cx, _rows(cx), cx.go, pack, spid)


# ------------------------------------------------------------------ statements


def _acc_ref(name, n, cx):
    if n.expanded_over:
        return Idx(name, cx.ti)
    return Var(name)


def _key(cx, stem, scalar):
    if cx.width is None:
        return scalar
    return WIDTH_PFX[cx.width] + stem


def _init(n, cx):
    em = cx.em
    if n.value.op != "fzero":
        raise PrimError("lowering: accumulators start at +0.0")
    key = _key(cx, "setzero_ps", "f32.zero")
    pid = cx.s.implicit
    if n.expanded_over:
        em.set(_acc_ref(n.acc, n, cx), Call(key, ()), prov=pid)
    else:
        em.emit(Let(n.acc, TABLE[key].ret, Call(key, ()), mut=True, prov=pid))


def _aptr(cx):
    blk = add(mul(ix("cast", "size_t", cx.t), Var("G")), cx.g)
    return add(Var("Ab"), mul(blk, cx.AF.size))


def _fp(e: E, n, cx):
    em = cx.em
    pid = cx.s.implicit
    if e.op == "acc":
        return _acc_ref(e.args[0], n, cx)
    if e.op in ("fadd", "fmul"):
        a = _fp(e.args[0], n, cx)
        b = _fp(e.args[1], n, cx)
        key = _key(
            cx,
            {"fadd": "add_ps", "fmul": "mul_ps"}[e.op],
            {"fadd": "f32.add", "fmul": "f32.mul"}[e.op],
        )
        if TABLE[key].ieee != e.op:
            raise PrimError("P12: %s does not realise %s" % (key, e.op))
        return em.call(key, a, b, base="f", prov=pid, lanes=("rows", cx.width))
    if e.op == "i2f":
        if e.args[0].op != "isum":
            raise PrimError("lowering: i2f of a non-sum")
        rec, rpid = _recipe(n, cx)
        aptr = em.let("ap", "const uint8_t *", _aptr(cx), prov=rpid)
        dec = cx.hoisted.get("dec")
        if dec is None:
            if hasattr(rec, "decode_row") and cx.tile is not None:
                isum = rec.dot(None, aptr, rows=_rows(cx), go=cx.go)
            else:
                isum = rec.dot(rec.decode(_rows(cx), cx.go), aptr)
        else:
            isum = rec.dot(dec, aptr)
        cx.cache["aptr"] = aptr
        key = _key(cx, "cvtepi32_ps", "f32.from_i32")
        if TABLE[key].ieee != "i2f":
            raise PrimError("P12: %s does not realise i2f" % key)
        return em.call(key, isum, base="fi", prov=pid, lanes=("rows", cx.width))
    if e.op == "h2f":
        if e.args[0].op != "wd":
            raise PrimError("lowering: h2f of a non-scale")
        if "dw" in cx.hoisted:
            return cx.hoisted["dw"]
        pack, conv, spid = n.lower["scales"]
        return recipes.scales(cx, _rows(cx), cx.go, pack, spid)
    if e.op == "ad":
        aptr = cx.cache.get("aptr")
        if aptr is None:
            aptr = em.let("ap", "const uint8_t *", _aptr(cx), prov=pid)
            cx.cache["aptr"] = aptr
        d = em.call("ld.f32", add(aptr, cx.AF.d.offset), base="ad", prov=pid)
        if cx.width is None:
            return d
        return em.call(WIDTH_PFX[cx.width] + "set1_ps", d, base="adv", prov=pid)
    raise PrimError("lowering: unexpected FP op %s" % e.op)


def _update(n, cx):
    em = cx.em
    v = n.value
    if v.op != "fadd" or v.args[0].op != "acc":
        raise PrimError("lowering: update must be acc = fadd(acc, term)")
    cx.cache.pop("aptr", None)
    term = _fp(v.args[1], n, cx)
    key = _key(cx, "add_ps", "f32.add")
    em.set(
        _acc_ref(n.acc, n, cx),
        Call(key, (_acc_ref(n.acc, n, cx), term)),
        prov=cx.s.implicit,
        lanes=("rows", cx.width),
    )
    cx.cache.pop("aptr", None)


def _store(n, cx):
    em = cx.em
    v = n.value
    if v.op != "canon" or v.args[0].op != "acc":
        raise PrimError("lowering: store must be canon(acc)")
    lowering, pid = n.lower["canon"]
    accv = _acc_ref(v.args[0].args[0], n, cx)
    c = recipes.canon(cx, lowering, accv, pid)
    r = Var("r")
    yidx = add(mul(ix("cast", "size_t", cx.t), Var("ldy")), r)
    yptr = em.let("yp", "float *", add(Var("Y"), yidx), prov=pid)
    recipes.store(cx, yptr, c, pid)
