"""The QF_BV lane formulas of the integer rule queries, in ONE place (added 2026-10-16 after review finding
R2-5). z3_rules.py and z3_int.py build their queries from these functions, and int_differential.py evaluates
the very same functions on concrete inputs against semantics/int_ops.py, so a query can only use a lane
formula that the differential has checked. The expressions are the ones of the first run, unchanged: the
first run's integer queries re-exported through this module are identical modulo Z3's let-variable numbering
(smt2_equiv.py; the sha256 of an export also depends on that numbering, so it identifies the file only).

  sext, zext            sign / zero extension to n bits (default 32)
  sat16(t)              signed saturation of an int32 term to [-32768, 32767] (as int32)
  word(u0, u1, s0, s1)  one (V)PMADDUBSW word as int32: sat16(zext(u1)*sext(s1) + zext(u0)*sext(s0))
  pabs(b), psign(x, w)  one byte of (V)PABSB / (V)PSIGNB (8-bit terms)
  dpbusd_lane(acc, us, xs)  one VPDPBUSD dword: acc + sum zext(u)*sext(x), wrapping (int32)
  packs(q)              VPACKSSDW then VPACKSSWB on one int32 lane, as an int32 holding the int8 result
"""


def make(z3):
    BV = lambda v, n=32: z3.BitVecVal(v, n)

    class F:
        pass

    F.sext = staticmethod(lambda x, n=32: z3.SignExt(n - x.size(), x))
    F.zext = staticmethod(lambda x, n=32: z3.ZeroExt(n - x.size(), x))
    F.sat16 = staticmethod(lambda t: z3.If(t > BV(32767), BV(32767),
                                           z3.If(t < BV(-32768 & 0xFFFFFFFF), BV(-32768 & 0xFFFFFFFF), t)))
    F.word = staticmethod(lambda u0, u1, s0, s1: F.sat16(F.zext(u1) * F.sext(s1) + F.zext(u0) * F.sext(s0)))
    F.pabs = staticmethod(lambda t: z3.If(t < 0, -t, t))
    F.psign = staticmethod(lambda x_, w_: z3.If(w_ < 0, -x_, z3.If(w_ == 0, z3.BitVecVal(0, 8), x_)))
    F.dpbusd_lane = staticmethod(lambda acc, us, xs: acc + sum((F.zext(u) * F.sext(x) for u, x in zip(us, xs)), BV(0)))

    def packs(q):
        s16 = z3.If(q > 32767, BV(32767), z3.If(q < -32768, BV(-32768 & 0xFFFFFFFF), q))
        return z3.If(s16 > 127, BV(127), z3.If(s16 < -128, BV(-128 & 0xFFFFFFFF), s16))
    F.packs = staticmethod(packs)
    return F
