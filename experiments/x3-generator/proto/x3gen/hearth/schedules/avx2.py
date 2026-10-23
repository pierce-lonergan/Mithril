"""AVX2 schedule: 8-row tiles, lane i = row r+i, dup_last row tail with masked store, a T == 1
copy, and token blocks of 8 with the weight work hoisted (the shape of quant_avx2.c:231-332).
Schedule text (counted as S)."""

from x3gen.core.sched import Schedule


def schedule(k):
    s = Schedule(k, "avx2")
    s.reorder("t", "r")
    s.split("r", 8, tail="dup_last")
    s.reorder("r_i", "t")
    s.vectorize("r_i", 8, 256, store="mask")
    one, many = s.specialize("t", ("T", "==", 1))
    many.block("t", 8, "r_i")
    many.hoist(("W",), out_of="t_i")
    signed = "sign_transfer" if k.params["W"][1].q.signed else "bias"
    s.lower_isum("maddubs", signed=signed, reduce="hadd")
    s.load_scales("gpr64", "cvtph")
    s.canon_store("blendv")
    return s
