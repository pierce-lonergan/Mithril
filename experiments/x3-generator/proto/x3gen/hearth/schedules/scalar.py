"""Scalar schedule: rows outside tokens, as quant.c:388-427 does. Schedule text (counted as S)."""

from x3gen.core.sched import Schedule


def schedule(k):
    s = Schedule(k, "scalar")
    s.reorder("t", "r")
    s.lower_isum("scalar_loop")
    s.load_scales("scalar", "h2f_bits")
    s.canon_store("branch")
    return s
