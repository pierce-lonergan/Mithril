"""Loop-nest IR for exact kernel meanings (library L).

The meaning is a tree of loops and statements over typed expressions. Floating-point expressions
form a DAG of IEEE binary32 operations; integer sums are exact (over Z). Schedules transform the
loop tree with the primitives in sched.py and annotate it; lower.py turns the result into a lane
program. Nothing in this file knows a particular engine.
"""

import copy
import itertools
from dataclasses import dataclass, field
from typing import Any, List, Optional

# ---------------------------------------------------------------- expressions


@dataclass(frozen=True)
class E:
    """Expression node. op names:
    wq(r,g,i)  integer weight value       xq(t,g,i)  integer activation code
    wd(r,g)    f16 bits of a weight scale  ad(t,g)    f32 activation scale
    xsum(t,g)  activation code sum field   isum(i,n,body) exact integer sum over i < n
    imul(a,b)  exact integer product       i2f(a) exact int->f32   h2f(a) exact f16->f32
    fmul(a,b)  binary32 multiply, RNE      fadd(a,b) binary32 add, RNE
    fzero()    +0.0f                       canon(a)  NaN -> canonical quiet NaN
    acc(name)  accumulator read
    """

    op: str
    args: tuple = ()

    def __repr__(self):
        if not self.args:
            return self.op + "()"
        return "%s(%s)" % (self.op, ", ".join(repr(a) for a in self.args))


def walk(e):
    yield e
    for a in e.args:
        if isinstance(a, E):
            yield from walk(a)


FP_OPS = {"i2f", "h2f", "fmul", "fadd", "fzero", "canon", "ad", "acc"}
INT_OPS = {"wq", "xq", "isum", "imul", "xsum", "wd"}

# ---------------------------------------------------------------- statements

_ids = itertools.count(1)


@dataclass(eq=False)
class Loop:
    """for var in [lo, hi): kind 'out' (independent outputs) or 'seq' (carries FP state).

    Schedule annotations (set only by primitives in sched.py):
      step    tile size of a split outer loop; inner loop of a split has origin=(outer var, k)
      tail    None | 'guard' | 'dup_last' | 'cut' for the outer loop of a split
      lanes   > 0 when the loop is vectorised: lane k = iteration k
      vec     vector annotation dict (width, layout, store) when lanes > 0
      unroll  0 none, -1 full, u > 0 by u
      only_full True on a 'cut' main loop (runs whole tiles only)
    """

    var: str
    lo: Any
    hi: Any
    kind: str
    body: list
    step: int = 1
    tail: Optional[str] = None
    lanes: int = 0
    vec: dict = field(default_factory=dict)
    unroll: int = 0
    only_full: bool = False
    origin: Optional[tuple] = None
    hoist: tuple = ()
    prov: list = field(default_factory=list)
    uid: int = field(default_factory=lambda: next(_ids))


@dataclass(eq=False)
class Init:
    acc: str
    value: E
    expanded_over: tuple = ()
    prov: list = field(default_factory=list)


@dataclass(eq=False)
class Update:
    acc: str
    value: E
    expanded_over: tuple = ()
    prov: list = field(default_factory=list)


@dataclass(eq=False)
class Store:
    """out[index] = value, with index = sum(coef * var); coef names a runtime scalar or is 1."""

    out: str
    index: tuple
    value: E
    expanded_over: tuple = ()
    prov: list = field(default_factory=list)


@dataclass(eq=False)
class Spec:
    """Specialisation: run `then` when pred holds, else `other` (copies of one subtree)."""

    pred: tuple
    then: list
    other: list
    prov: list = field(default_factory=list)


@dataclass(eq=False)
class Region:
    """A transparent container naming part of the tree (made by a 'cut' split) so that later
    primitives can address the main and remainder copies separately."""

    name: str
    body: list
    prov: list = field(default_factory=list)


@dataclass
class Kernel:
    name: str
    params: dict
    body: list
    requires: tuple
    slot: Any = None
    attrs: dict = field(default_factory=dict)

    def clone(self):
        k = copy.deepcopy(self)
        for n in iter_nodes(k.body):
            if isinstance(n, Loop):
                n.uid = next(_ids)
        return k


def iter_nodes(body):
    for n in body:
        yield n
        if isinstance(n, Loop):
            yield from iter_nodes(n.body)
        elif isinstance(n, Spec):
            yield from iter_nodes(n.then)
            yield from iter_nodes(n.other)
        elif isinstance(n, Region):
            yield from iter_nodes(n.body)


def loops_named(body, var) -> List[Loop]:
    return [n for n in iter_nodes(body) if isinstance(n, Loop) and n.var == var]


def parent_of(body, target):
    """(container list, index) holding target."""
    for i, n in enumerate(body):
        if n is target:
            return body, i
        if isinstance(n, (Loop, Region)):
            r = parent_of(n.body, target)
            if r:
                return r
        elif isinstance(n, Spec):
            r = parent_of(n.then, target) or parent_of(n.other, target)
            if r:
                return r
    return None


def enclosing_loops(body, target, acc=()):
    """Loops enclosing target, outermost first."""
    for n in body:
        if n is target:
            return list(acc)
        if isinstance(n, Loop):
            r = enclosing_loops(n.body, target, acc + (n,))
            if r is not None:
                return r
        elif isinstance(n, Region):
            r = enclosing_loops(n.body, target, acc)
            if r is not None:
                return r
        elif isinstance(n, Spec):
            for part in (n.then, n.other):
                r = enclosing_loops(part, target, acc)
                if r is not None:
                    return r
    return None


def dump(body, ind=0) -> str:
    """Deterministic text form (used for hashing schedules' effect and for debugging)."""
    out = []
    sp = "  " * ind
    for n in body:
        if isinstance(n, Loop):
            ann = []
            for k in ("step", "tail", "lanes", "unroll", "only_full", "origin", "hoist"):
                v = getattr(n, k)
                if v not in (1, None, 0, False, (), {}) or (k == "step" and v != 1):
                    ann.append("%s=%r" % (k, v))
            if n.vec:
                ann.append("vec=%r" % sorted(n.vec.items()))
            out.append(
                "%sfor %s in [%r, %r) %s %s" % (sp, n.var, n.lo, n.hi, n.kind, " ".join(ann))
            )
            out.append(dump(n.body, ind + 1))
        elif isinstance(n, Region):
            out.append("%sregion %s:" % (sp, n.name))
            out.append(dump(n.body, ind + 1))
        elif isinstance(n, Spec):
            out.append("%sif %r:" % (sp, n.pred))
            out.append(dump(n.then, ind + 1))
            out.append("%selse:" % sp)
            out.append(dump(n.other, ind + 1))
        elif isinstance(n, Init):
            out.append("%s%s%s = %r" % (sp, n.acc, list(n.expanded_over) or "", n.value))
        elif isinstance(n, Update):
            out.append("%s%s%s = %r" % (sp, n.acc, list(n.expanded_over) or "", n.value))
        elif isinstance(n, Store):
            out.append("%s%s[%r] = %r" % (sp, n.out, n.index, n.value))
    return "\n".join(x for x in out if x)


# ---------------------------------------------------------------- builders for meaning files


def v(op, *args):
    return E(op, tuple(args))


def fadd(a, b):
    return v("fadd", a, b)


def fmul(a, b):
    return v("fmul", a, b)


def i2f(a):
    return v("i2f", a)


def h2f(a):
    return v("h2f", a)


def canon(a):
    return v("canon", a)


def fzero():
    return v("fzero")


def acc(name):
    return v("acc", name)


def exact_sum(i, n, body):
    return v("isum", i, n, body)


def loop(var, lo, hi, kind, *body):
    return Loop(var, lo, hi, kind, list(body))
