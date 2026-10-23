"""AVX-512 schedule: whole 16-row tiles in quads (vpdpbusd), then 4-row tails one row per 128-bit
lane with a masked store; T == 1 copy on whole tiles; token blocks of 8 with the weight work
hoisted (the shape of quant_avx512.c:250-356). Schedule text (counted as S)."""

from x3gen.core.sched import Schedule


def schedule(k):
    s = Schedule(k, "avx512")
    s.reorder("t", "r")
    main, rest = s.split("r", 16, tail="cut")
    main.reorder("r_i", "t")
    main.vectorize("r_i", 16, 512, layout="quads")
    one, many = main.specialize("t", ("T", "==", 1))
    many.block("t", 8, "r_i")
    many.hoist(("W",), out_of="t_i")
    rest.split("r_t", 4, tail="dup_last")
    rest.reorder("r_t_i", "t")
    rest.vectorize("r_t_i", 4, 128, layout="quad", store="kmask")
    rest.block("t", 8, "r_t_i")
    rest.hoist(("W",), out_of="t_i")
    main.lower_isum("dpbusd", signed="bias", reduce="unpack")
    rest.lower_isum("dpbusd", signed="bias", reduce="permute")
    s.load_scales("gpr64", "cvtph")
    s.canon_store("mask_mov")
    return s
