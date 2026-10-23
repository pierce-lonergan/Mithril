"""Concrete interpreter of a meaning (library L, test oracle).

Walks the meaning's loop tree with Python integers for exact sums and fp32.py for binary32. It
reads inputs from raw bytes using only the format declarations, so it checks the meaning text
itself, not a second hand-written reference.
"""

import struct

from . import fp32
from .ir import E, Init, Loop, Spec, Store, Update


class Inputs:
    def __init__(self, kernel, W: bytes, A: bytes, n: int):
        self.F = kernel.params["W"][1]
        self.AF = kernel.params["A"][1]
        self.blk = kernel.params["block"]
        if n % self.blk:
            raise ValueError("n must be a multiple of the block size")
        self.G = n // self.blk
        self.W, self.A = W, A

    def wblock(self, r, g):
        return (r * self.G + g) * self.F.size

    def ablock(self, t, g):
        return (t * self.G + g) * self.AF.size


def ev(e: E, env, inp: Inputs, accs):
    op, a = e.op, e.args
    if op == "wq":
        r, g, i = env[a[0]], env[a[1]], env[a[2]]
        bi, sh = inp.F.q.locate(i)
        b = inp.W[inp.wblock(r, g) + inp.F.q.offset + bi]
        return inp.F.q.value_of_byte(b, sh)
    if op == "xq":
        t, g, i = env[a[0]], env[a[1]], env[a[2]]
        b = inp.A[inp.ablock(t, g) + inp.AF.q.offset + i]
        return inp.AF.q.value_of_byte(b, 0)
    if op == "wd":
        r, g = env[a[0]], env[a[1]]
        o = inp.wblock(r, g) + inp.F.d.offset
        return struct.unpack_from("<H", inp.W, o)[0]
    if op == "ad":
        t, g = env[a[0]], env[a[1]]
        o = inp.ablock(t, g) + inp.AF.d.offset
        return struct.unpack_from("<I", inp.A, o)[0]
    if op == "isum":
        var, count, body = a
        s = 0
        for i in range(count):
            env[var] = i
            s += ev(body, env, inp, accs)
        del env[var]
        return s
    if op == "imul":
        return ev(a[0], env, inp, accs) * ev(a[1], env, inp, accs)
    if op == "i2f":
        return fp32.i2f(ev(a[0], env, inp, accs))
    if op == "h2f":
        return fp32.h2f(ev(a[0], env, inp, accs))
    if op == "fmul":
        return fp32.fmul(ev(a[0], env, inp, accs), ev(a[1], env, inp, accs))
    if op == "fadd":
        return fp32.fadd(ev(a[0], env, inp, accs), ev(a[1], env, inp, accs))
    if op == "fzero":
        return 0
    if op == "canon":
        return fp32.canon(ev(a[0], env, inp, accs))
    if op == "acc":
        return accs[a[0]]
    raise ValueError("unknown op " + op)


def bound(x, env):
    return env[x] if isinstance(x, str) else x


def run(kernel, W: bytes, A: bytes, n: int, T: int, Y: list, ldy: int, r0: int, r1: int):
    """Execute the meaning; Y is a list of u32 bit patterns, updated in place. Returns the set of
    written indices (each must be written at most once)."""
    inp = Inputs(kernel, W, A, n)
    env = {"T": T, "r0": r0, "r1": r1, "G": inp.G, "ldy": ldy}
    accs = {}
    written = set()

    def exec_body(body):
        for s in body:
            if isinstance(s, Loop):
                for x in range(bound(s.lo, env), bound(s.hi, env)):
                    env[s.var] = x
                    exec_body(s.body)
                env.pop(s.var, None)
            elif isinstance(s, Init) or isinstance(s, Update):
                accs[s.acc] = ev(s.value, env, inp, accs)
            elif isinstance(s, Store):
                idx = sum(env[var] * (1 if c == 1 else env[c]) for var, c in s.index)
                if idx in written:
                    raise AssertionError("location written twice")
                written.add(idx)
                Y[idx] = ev(s.value, env, inp, accs)
            elif isinstance(s, Spec):
                raise ValueError("meaning trees carry no specialisation")

    exec_body(kernel.body)
    return written
