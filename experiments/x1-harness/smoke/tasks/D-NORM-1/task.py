"""D-NORM-1 (T-NORM), DEVELOPMENT item: RMSNorm with the canonical 16-lane sum (S-NORM-0 shape).

NUMERICS 1 and 4 of Hearth. Not sealed, not held out. The NaN canonicalisation of the output is an
addition to S-NORM-0 (the corpus version in crates/mithi/tests/corpus/norm.mith has it).
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from smokelib import Lcg, add, div, f32, from_bits, hex32, lit_array, mul, sqrt  # noqa: E402

TASK = {
    "id": "D-NORM-1",
    "family": "T-NORM",
    "split": "development",
    "title": "RMSNorm with the canonical 16-lane sum (S-NORM-0 shape)",
    "unit": "rmsnorm",
    "grade": "exact",
}

RANDOM = {"count": 120, "seed0": 44000}
EPS_BITS = [0x3727C5AC, 0x358637BD]  # 1e-5, 1e-6 as f32


def b32(v):
    return struct.unpack("<I", struct.pack("<f", v))[0]


def sum16(vals):
    lanes = [0.0] * 16
    for i, v in enumerate(vals):
        lanes[i & 15] = add(lanes[i & 15], v)
    for s in (8, 4, 2, 1):
        for j in range(s):
            lanes[j] = add(lanes[j], lanes[j + s])
    return lanes[0]


def model(case):
    x = [from_bits(b) for b in case["x"]]
    w = [from_bits(b) for b in case["w"]]
    eps = from_bits(case["eps"])
    n = len(x)
    ms = div(sum16([mul(v, v) for v in x]), f32(float(n)))
    r = div(1.0, sqrt(add(ms, eps)))
    return ",".join(hex32(mul(mul(x[i], r), w[i])) for i in range(n))


def case(xs, ws, eps_bits=EPS_BITS[0]):
    return {"x": [b32(f32(v)) for v in xs], "w": [b32(f32(v)) for v in ws], "eps": eps_bits}


def visible_cases():
    return [
        case([3.0], [1.0]),
        case([float(i) - 7.5 for i in range(16)], [1.0] * 16),
        case([0.5 * i for i in range(17)], [1.0 + 0.125 * (i % 4) for i in range(17)]),
        case([0.0] * 5, [2.0, -2.0, 1.0, -1.0, 0.5]),
    ]


def hidden_literal_cases():
    out = [
        case([1.0e20, -2.0, 3.0], [1.0, -1.0, 0.5]),                   # x*x overflows: r = 0, signed zeros
        case([0.0, -0.0, 0.0], [1.0, 1.0, -1.0], 0),                   # eps = 0, x = 0: 0 * inf = NaN
        case([1.0e-30] * 33, [1.0] * 33),                              # tiny squares underflow
        case([float(i % 7) * 1.0e3 + 0.1 for i in range(64)], [1.0 / (i + 1) for i in range(64)], EPS_BITS[1]),
        case([(-1.0) ** i * (2.0 ** (i % 20)) for i in range(40)], [0.75] * 40),
    ]
    # order matters: one huge lane and many tiny values in other lanes
    xs = [1.0e15] + [1.0] * 31
    out.append(case(xs, [1.0] * 32))
    return out


def random_case(seed):
    r = Lcg(seed)
    n = 1 + (r.next() >> 16) % 70
    e = (r.next() >> 16) % 41                    # x scale 2^(e-30)
    xs, ws = [], []
    for _ in range(n):
        m = (r.next() >> 8) - 8388608
        xs.append(b32(f32(m * 2.0 ** (e - 30 - 23))))
        mw = (r.next() >> 8) - 8388608
        ws.append(b32(f32(mw * 2.0 ** -22)))
    eps = EPS_BITS[(r.next() >> 16) % 2]
    return {"x": xs, "w": ws, "eps": eps}


def describe(c):
    return ("x (f32 bits) = [" + ", ".join("0x%08x" % v for v in c["x"]) + "]; w (f32 bits) = ["
            + ", ".join("0x%08x" % v for v in c["w"]) + f"]; eps = f32 bits 0x{c['eps']:08x}")


def rust_lit(c):
    n = len(c["x"])
    return (f"let x: [u32; {n}] = {lit_array('u32', ['0x%08x' % v for v in c['x']], 8)}; "
            f"let w: [u32; {n}] = {lit_array('u32', ['0x%08x' % v for v in c['w']], 8)}; "
            f"x1h_run(&x, &w, 0x{c['eps']:08x}u32)")


mith_lit = rust_lit

RUST_HELPERS = r"""
fn x1h_run(xb: &[u32], wb: &[u32], eb: u32) -> String {
    let mut x: Vec<f32> = Vec::new();
    let mut w: Vec<f32> = Vec::new();
    let mut y: Vec<f32> = Vec::new();
    for i in 0..xb.len() {
        x.push(f32::from_bits(xb[i]));
        w.push(f32::from_bits(wb[i]));
        y.push(f32::from_bits(0x7f80_0001));
    }
    rmsnorm(&mut y, &x, &w, f32::from_bits(eb));
    let mut out = String::new();
    for i in 0..y.len() {
        if i > 0 { out.push_str(","); }
        out.push_str(&format!("{:08x}", y[i].to_bits()));
    }
    out
}

fn x1h_rand(seed: u32) -> String {
    let mut s = seed;
    let n = 1 + ((x1h_next(&mut s) >> 16) % 70) as usize;
    let e = (x1h_next(&mut s) >> 16) % 41;
    let sx = f32::from_bits((127 + e - 30 - 23) << 23);
    let sw = f32::from_bits((127 - 22) << 23);
    let mut xb: Vec<u32> = Vec::new();
    let mut wb: Vec<u32> = Vec::new();
    for _i in 0..n {
        let m = ((x1h_next(&mut s) >> 8) as i32 - 8388608) as f32;
        xb.push((m * sx).to_bits());
        let mw = ((x1h_next(&mut s) >> 8) as i32 - 8388608) as f32;
        wb.push((mw * sw).to_bits());
    }
    let eb: u32 = if (x1h_next(&mut s) >> 16) % 2 == 0 { 0x3727C5AC } else { 0x358637BD };
    x1h_run(&xb, &wb, eb)
}
"""

MITH_HELPERS = r"""
fn x1h_run(xb: &[u32], wb: &[u32], eb: u32) -> String uses { alloc(Global) } {
    let mut x: Vec<f32> = Vec::new();
    let mut w: Vec<f32> = Vec::new();
    let mut y: Vec<f32> = Vec::new();
    for i in 0..xb.len() {
        x.push(f32::from_bits(xb[i]));
        w.push(f32::from_bits(wb[i]));
        y.push(f32::from_bits(0x7f80_0001));
    }
    rmsnorm(&mut y, &x, &w, f32::from_bits(eb));
    let mut out = String::new();
    for i in 0..y.len() {
        if i > 0 { out.push_str(","); }
        out.push_str(&format!("{:08x}", y[i].to_bits()));
    }
    out
}

fn x1h_rand(seed: u32) -> String uses { alloc(Global) } {
    let mut s = seed;
    let n = 1 + ((x1h_next(&mut s) >> 16) % 70) as usize;
    let e = (x1h_next(&mut s) >> 16) % 41;
    let sx = f32::from_bits((127 + e - 30 - 23) << 23);
    let sw = f32::from_bits((127 - 22) << 23);
    let mut xb: Vec<u32> = Vec::new();
    let mut wb: Vec<u32> = Vec::new();
    for _i in 0..n {
        let m = ((x1h_next(&mut s) >> 8) as i32 - 8388608) as f32;
        xb.push((m * sx).to_bits());
        let mw = ((x1h_next(&mut s) >> 8) as i32 - 8388608) as f32;
        wb.push((mw * sw).to_bits());
    }
    let eb: u32 = if (x1h_next(&mut s) >> 16) % 2 == 0 { 0x3727C5AC } else { 0x358637BD };
    x1h_run(&xb, &wb, eb)
}
"""
