"""D-Q4-1 (T-Q4), DEVELOPMENT item: one Q4 weight row times one Q8 activation.

The public smoke example S-Q4-0 of X1 DESIGN 5.2 (Hearth NUMERICS 3). Not sealed, not held out.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from smokelib import Lcg, add, mul, f16_to_f32, from_bits, hex32, lit_array  # noqa: E402

TASK = {
    "id": "D-Q4-1",
    "family": "T-Q4",
    "split": "development",
    "title": "Q4 weight row times Q8 activation (S-Q4-0 shape)",
    "unit": "q4_row_dot",
    "grade": "exact",
}

RANDOM = {"count": 160, "seed0": 41000}


def block(d_bits, bytes32, ad_bits, q64):
    return {"d": d_bits, "b": list(bytes32), "ad": ad_bits, "q": list(q64)}


def elem(b, j):
    """element j of a block: byte j's low nibble (j < 32) or byte j-32's high nibble, minus 8."""
    if j < 32:
        return (b[j] & 15) - 8
    return (b[j - 32] >> 4) - 8


def model(case):
    acc = 0.0
    for blk in case["blocks"]:
        isum = sum(elem(blk["b"], j) * blk["q"][j] for j in range(64))
        d = f16_to_f32(blk["d"])
        ad = from_bits(blk["ad"])
        prod = mul(d, ad)
        acc = add(acc, mul(float(isum), prod))
    return hex32(acc)  # hex32 canonicalises NaN to 0x7fc00000


def visible_cases():
    one = [0x88] * 32
    one[0] = 0xF8  # element 0 = 0, element 32 = 7
    q = [0] * 64
    q[32] = 1
    q16 = [0] * 64
    q16[16] = 1
    return [
        {"blocks": []},
        {"blocks": [block(0x3C00, one, 0x3F800000, q)]},           # 7.0: high nibble is element j+32
        {"blocks": [block(0x3C00, one, 0x3F800000, q16)]},         # 0.0: not llama.cpp's j+16
        {"blocks": [block(0x3800, [0x9A] * 32, 0x40000000, [3] * 64),
                    block(0xC000, [0x17] * 32, 0x3E800000, [-5] * 64)]},
        {"blocks": [block(0x0001, [0x98] * 32, 0x3F800000, [1] * 64)]},   # subnormal f16 scale
    ]


def hidden_literal_cases():
    z = [0x88] * 32  # all elements 0
    cases = []
    # a.d = -0.0 with isum != 0: the product is -0.0; acc must start at +0.0 (+0 + -0 = +0)
    cases.append({"blocks": [block(0x3C00, [0x99] * 32, 0x80000000, [1] * 64)]})
    # scale +-0, inf and NaN; inf * 0 isum -> NaN -> canonical NaN
    cases.append({"blocks": [block(0x8000, [0x9F] * 32, 0x3F800000, [7] * 64)]})
    cases.append({"blocks": [block(0x7C00, z, 0x3F800000, [5] * 64)]})
    cases.append({"blocks": [block(0x7C00, [0x99] * 32, 0x3F800000, [1] * 64)]})
    cases.append({"blocks": [block(0x7E00, [0x99] * 32, 0x3F800000, [1] * 64)]})
    cases.append({"blocks": [block(0x3C00, [0x99] * 32, 0x7FC00001, [1] * 64)]})
    # extreme |isum|: all elements -8 against 127 and 7 against -127
    cases.append({"blocks": [block(0x3C00, [0x00] * 32, 0x3F800000, [127] * 64)]})
    cases.append({"blocks": [block(0x3C00, [0xFF] * 32, 0x3F800000, [-127] * 64)]})
    # overflow to inf, then cancellation inf + -inf -> NaN
    cases.append({"blocks": [block(0x7BFF, [0xFF] * 32, 0x7F000000, [127] * 64),
                             block(0x7BFF, [0x00] * 32, 0x7F000000, [127] * 64)]})
    # cancellation: two blocks that sum to exactly zero, then a tiny third
    cases.append({"blocks": [block(0x3C00, [0x99] * 32, 0x3F800000, [1] * 64),
                             block(0xBC00, [0x99] * 32, 0x3F800000, [1] * 64),
                             block(0x0400, [0x89] * 32, 0x3F800000, [1] * 64)]})
    # rounding order matters: large then small terms
    cases.append({"blocks": [block(0x6400, [0xF8] * 32, 0x4B000000, [1] * 64),
                             block(0x3C00, [0x98] * 32, 0x3F800001, [1] * 64)]})
    return cases


def random_case(seed):
    r = Lcg(seed)
    nb = (r.next() >> 16) % 9
    blocks = []
    for _ in range(nb):
        x = r.next()
        d = 0x2C00 + ((x >> 16) % 0x2000)          # f16 in [2^-4, 2^4)
        if x & 1:
            d |= 0x8000
        b = [(r.next() >> 24) & 0xFF for _ in range(32)]
        y = r.next()
        exp = 120 + ((y >> 8) % 15)                # f32 exponent field 120..134
        ad = ((y >> 9) & 0x7FFFFF) | (exp << 23) | ((y & 1) << 31)
        q = [((r.next() >> 16) % 255) - 127 for _ in range(64)]
        blocks.append(block(d, b, ad, q))
    return {"blocks": blocks}


def describe(case):
    if not case["blocks"]:
        return "w = [], a = [] (nb = 0)"
    parts = []
    for g, blk in enumerate(case["blocks"]):
        parts.append(
            f"block {g}: w.d = f16 bits 0x{blk['d']:04x}; w bytes = [{', '.join('0x%02x' % v for v in blk['b'])}]; "
            f"a.d = f32 bits 0x{blk['ad']:08x}; a.q = [{', '.join(str(v) for v in blk['q'])}]")
    return "; ".join(parts)


def _flat(case, key):
    out = []
    for blk in case["blocks"]:
        v = blk[key]
        out.extend(v if isinstance(v, list) else [v])
    return out


def _hexes(vals, width):
    return ["0x%0*x" % (width, v) for v in vals]


def rust_lit(case):
    nb = len(case["blocks"])
    return (f"let d: [u16; {nb}] = {lit_array('u16', _hexes(_flat(case, 'd'), 4))}; "
            f"let b: [u8; {32 * nb}] = {lit_array('u8', _hexes(_flat(case, 'b'), 2))}; "
            f"let ad: [u32; {nb}] = {lit_array('u32', _hexes(_flat(case, 'ad'), 8))}; "
            f"let q: [i8; {64 * nb}] = {lit_array('i8', _flat(case, 'q'))}; "
            "x1h_run(&d, &b, &ad, &q)")


mith_lit = rust_lit  # the same statements are valid in both arms

RUST_HELPERS = r"""
fn x1h_run(d: &[u16], b: &[u8], ad: &[u32], q: &[i8]) -> String {
    let mut w: Vec<BlockQ4> = Vec::new();
    let mut a: Vec<ActQ8> = Vec::new();
    for g in 0..d.len() {
        let mut qs = [0u8; 32];
        for j in 0..32 { qs[j] = b[g * 32 + j]; }
        let mut qq = [0i8; 64];
        let mut s: i32 = 0;
        for j in 0..64 { qq[j] = q[g * 64 + j]; s += qq[j] as i32; }
        w.push(BlockQ4 { d: d[g], qs: qs });
        a.push(ActQ8 { d: f32::from_bits(ad[g]), sum: s, q: qq });
    }
    let y = q4_row_dot(&w, &a);
    format!("{:08x}", y.to_bits())
}

fn x1h_rand(seed: u32) -> String {
    let mut s = seed;
    let nb = ((x1h_next(&mut s) >> 16) % 9) as usize;
    let mut d: Vec<u16> = Vec::new();
    let mut b: Vec<u8> = Vec::new();
    let mut ad: Vec<u32> = Vec::new();
    let mut q: Vec<i8> = Vec::new();
    for _g in 0..nb {
        let x = x1h_next(&mut s);
        let mut dd: u16 = (0x2C00 + ((x >> 16) % 0x2000)) as u16;
        if x & 1 == 1 { dd = dd | 0x8000; }
        d.push(dd);
        for _j in 0..32 { b.push(((x1h_next(&mut s) >> 24) & 0xFF) as u8); }
        let y = x1h_next(&mut s);
        let e: u32 = 120 + ((y >> 8) % 15);
        ad.push(((y >> 9) & 0x7FFFFF) | (e << 23) | ((y & 1) << 31));
        for _j in 0..64 { q.push((((x1h_next(&mut s) >> 16) % 255) as i32 - 127) as i8); }
    }
    x1h_run(&d, &b, &ad, &q)
}
"""

MITH_HELPERS = r"""
fn x1h_run(d: &[u16], b: &[u8], ad: &[u32], q: &[i8]) -> String uses { alloc(Global) } {
    let mut w: Vec<BlockQ4> = Vec::new();
    let mut a: Vec<ActQ8> = Vec::new();
    for g in 0..d.len() {
        let mut qs = [0u8; 32];
        for j in 0..32 { qs[j] = b[g * 32 + j]; }
        let mut qq = [0i8; 64];
        let mut s: i32 = 0;
        for j in 0..64 { qq[j] = q[g * 64 + j]; s += qq[j] as i32; }
        w.push(BlockQ4 { d: f16::from_bits(d[g]), q: Nib64o8 { b: qs } });
        a.push(ActQ8 { d: f32::from_bits(ad[g]), sum: s, q: qq });
    }
    let y = q4_row_dot(&w, &a);
    format!("{:08x}", y.to_bits())
}

fn x1h_rand(seed: u32) -> String uses { alloc(Global) } {
    let mut s = seed;
    let nb = ((x1h_next(&mut s) >> 16) % 9) as usize;
    let mut d: Vec<u16> = Vec::new();
    let mut b: Vec<u8> = Vec::new();
    let mut ad: Vec<u32> = Vec::new();
    let mut q: Vec<i8> = Vec::new();
    for _g in 0..nb {
        let x = x1h_next(&mut s);
        let mut dd: u16 = (0x2C00 + ((x >> 16) % 0x2000)) as u16;
        if x & 1 == 1 { dd = dd | 0x8000; }
        d.push(dd);
        for _j in 0..32 { b.push(((x1h_next(&mut s) >> 24) & 0xFF) as u8); }
        let y = x1h_next(&mut s);
        let e: u32 = 120 + ((y >> 8) % 15);
        ad.push(((y >> 9) & 0x7FFFFF) | (e << 23) | ((y & 1) << 31));
        for _j in 0..64 { q.push((((x1h_next(&mut s) >> 16) % 255) as i32 - 127) as i8); }
    }
    x1h_run(&d, &b, &ad, &q)
}
"""
