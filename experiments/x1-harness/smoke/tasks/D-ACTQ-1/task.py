"""D-ACTQ-1 (T-ACTQ), DEVELOPMENT item: Q8 activation quantisation (S-ACTQ-0 shape, NUMERICS 2).

Not sealed, not held out. Deviation from S-ACTQ-0 and from the canonical prelude: ActQ8 carries no
`invariant` here, because mithi's T2 cannot discharge the iterator-sum invariant inside a kernel
(crates/mithi/README.md, finding 1); the brief states the sum rule instead.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from smokelib import (Lcg, div, f32, f32_to_i8_sat, from_bits, hex32, lit_array, mul,  # noqa: E402
                      round_ties_even)

TASK = {
    "id": "D-ACTQ-1",
    "family": "T-ACTQ",
    "split": "development",
    "title": "Q8 activation quantisation (S-ACTQ-0 shape)",
    "unit": "act_quantize_q8",
    "grade": "exact",
}

RANDOM = {"count": 100, "seed0": 43000}


def model(case):
    xs = [from_bits(b) for b in case["x"]]
    out = []
    for b0 in range(0, len(xs), 64):
        blk = xs[b0:b0 + 64]
        amax = 0.0
        for v in blk:
            a = abs(v)
            if a > amax:
                amax = a
        d = div(amax, 127.0)
        idv = div(1.0, d) if d != 0.0 else 0.0
        q = [f32_to_i8_sat(round_ties_even(mul(v, idv))) for v in blk]
        out.append(f"{hex32(d)}:{sum(q)}:" + ",".join(str(v) for v in q))
    return ";".join(out) if out else "empty"


def b32(v):
    import struct
    return struct.unpack("<I", struct.pack("<f", v))[0]


def visible_cases():
    ramp = [b32(f32((i - 32) * 0.25)) for i in range(64)]
    ones = [b32(1.0)] * 64
    mixed = [b32(f32(v)) for v in ([3.0, -6.0, 0.5, -0.25] * 16)]
    return [
        {"x": []},
        {"x": ramp},
        {"x": ones + mixed},
        {"x": [0] * 64},
    ]


def near_half_block(amax, alt):
    """A block whose values sit next to (k + 0.5) * d, chosen so that the reference rule
    round(x * (1/d)) differs from `alt` (x / d, or x * (127/amax)) for 63 of them."""
    d = div(amax, 127.0)
    idv = div(1.0, d)
    vals = [amax]
    for k in range(-127, 127):
        base = b32(mul(f32(k + 0.5), d))
        for db in range(-3, 4):
            x = from_bits(base + db)
            if abs(x) > amax or len(vals) >= 64:
                continue
            ref = f32_to_i8_sat(round_ties_even(mul(x, idv)))
            other = f32_to_i8_sat(round_ties_even(div(x, d) if alt == "div" else mul(x, div(127.0, amax))))
            if ref != other:
                vals.append(x)
    vals = (vals + [0.0] * 64)[:64]
    return [b32(v) for v in vals]


def hidden_literal_cases():
    ties = [b32(127.0)] + [b32(v) for v in ([2.5, -3.5, 0.5, -0.5, 1.5, -2.5, 126.5] * 9)]
    ties = ties[:64]
    outlier = [b32(1.0e30)] + [b32(f32(1.0e20 * (i + 1))) for i in range(63)]
    negz = [0x80000000] * 63 + [b32(-1.0)]
    subn = [0x00000001] + [0] * 62 + [0x80000001]
    small = [0x00800000 + i for i in range(64)]
    big = [b32(f32(3.0e38))] + [b32(f32(-1.5e38))] * 63
    near_div = near_half_block(f32(0.37), "div")
    near_rec = near_half_block(f32(5.55), "recip")
    return [{"x": ties}, {"x": outlier}, {"x": negz}, {"x": subn}, {"x": small}, {"x": big},
            {"x": near_div}, {"x": near_rec}, {"x": near_div + near_rec}]


def random_case(seed):
    r = Lcg(seed)
    nblk = 1 + (r.next() >> 16) % 3
    xs = []
    for _ in range(nblk):
        e = (r.next() >> 16) % 51        # scale 2^(e-40), e in 0..50
        for _ in range(64):
            m = (r.next() >> 8) - 8388608
            xs.append(b32(f32(m * 2.0 ** (e - 40))))
    return {"x": xs}


def describe(case):
    if not case["x"]:
        return "x = [] (no blocks); out = []"
    return "x (f32 bits) = [" + ", ".join("0x%08x" % v for v in case["x"]) + "]"


def rust_lit(case):
    n = len(case["x"])
    return f"let x: [u32; {n}] = {lit_array('u32', ['0x%08x' % v for v in case['x']], 8)}; x1h_run(&x)"


mith_lit = rust_lit

RUST_HELPERS = r"""
fn x1h_run(xb: &[u32]) -> String {
    let mut x: Vec<f32> = Vec::new();
    for i in 0..xb.len() { x.push(f32::from_bits(xb[i])); }
    let nb = xb.len() / 64;
    let mut out: Vec<ActQ8> = Vec::new();
    for _b in 0..nb { out.push(ActQ8 { d: f32::from_bits(0x7f80_0001), sum: 12345, q: [99i8; 64] }); }
    act_quantize_q8(&x, &mut out);
    let mut s = String::new();
    for b in 0..nb {
        if b > 0 { s.push_str(";"); }
        s.push_str(&format!("{:08x}:{}:", out[b].d.to_bits(), out[b].sum));
        for i in 0..64 {
            if i > 0 { s.push_str(","); }
            s.push_str(&format!("{}", out[b].q[i]));
        }
    }
    if nb == 0 { s.push_str("empty"); }
    s
}

fn x1h_rand(seed: u32) -> String {
    let mut s = seed;
    let nblk = 1 + ((x1h_next(&mut s) >> 16) % 3) as usize;
    let mut xb: Vec<u32> = Vec::new();
    for _b in 0..nblk {
        let e = (x1h_next(&mut s) >> 16) % 51;
        let scale = f32::from_bits((127 + e - 40) << 23);
        for _i in 0..64 {
            let m = ((x1h_next(&mut s) >> 8) as i32 - 8388608) as f32;
            xb.push((m * scale).to_bits());
        }
    }
    x1h_run(&xb)
}
"""

MITH_HELPERS = r"""
fn x1h_run(xb: &[u32]) -> String uses { alloc(Global) } {
    let mut x: Vec<f32> = Vec::new();
    for i in 0..xb.len() { x.push(f32::from_bits(xb[i])); }
    let nb = xb.len() / 64;
    let mut out: Vec<ActQ8> = Vec::new();
    for _b in 0..nb { out.push(ActQ8 { d: f32::from_bits(0x7f80_0001), sum: 12345, q: [99i8; 64] }); }
    act_quantize_q8(&x, &mut out);
    let mut s = String::new();
    for b in 0..nb {
        if b > 0 { s.push_str(";"); }
        s.push_str(&format!("{:08x}:{}:", out[b].d.to_bits(), out[b].sum));
        for i in 0..64 {
            if i > 0 { s.push_str(","); }
            s.push_str(&format!("{}", out[b].q[i]));
        }
    }
    if nb == 0 { s.push_str("empty"); }
    s
}

fn x1h_rand(seed: u32) -> String uses { alloc(Global) } {
    let mut s = seed;
    let nblk = 1 + ((x1h_next(&mut s) >> 16) % 3) as usize;
    let mut xb: Vec<u32> = Vec::new();
    for _b in 0..nblk {
        let e = (x1h_next(&mut s) >> 16) % 51;
        let scale = f32::from_bits((127 + e - 40) << 23);
        for _i in 0..64 {
            let m = ((x1h_next(&mut s) >> 8) as i32 - 8388608) as f32;
            xb.push((m * scale).to_bits());
        }
    }
    x1h_run(&xb)
}
"""
