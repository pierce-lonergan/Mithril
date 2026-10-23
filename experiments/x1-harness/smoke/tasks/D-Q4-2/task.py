"""D-Q4-2 (T-Q4), DEVELOPMENT item: dequantise a row of Q4 blocks to f32.

Hearth's Q4 layout (FORMAT.md, NUMERICS 3): byte j holds element j (low nibble) and element j+32
(high nibble), stored as element + 8. Not sealed, not held out.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from smokelib import Lcg, mul, f16_to_f32, hex32, lit_array  # noqa: E402

TASK = {
    "id": "D-Q4-2",
    "family": "T-Q4",
    "split": "development",
    "title": "Dequantise Q4 blocks to f32",
    "unit": "q4_dequant",
    "grade": "exact",
}

RANDOM = {"count": 120, "seed0": 42000}


def elem(b, j):
    if j < 32:
        return (b[j] & 15) - 8
    return (b[j - 32] >> 4) - 8


def model(case):
    out = []
    for d_bits, b in case["blocks"]:
        d = f16_to_f32(d_bits)
        for j in range(64):
            out.append(hex32(mul(float(elem(b, j)), d)))
    return ",".join(out) if out else "empty"


def visible_cases():
    ramp = [(j % 16) | (((j + 5) % 16) << 4) for j in range(32)]
    return [
        {"blocks": []},
        {"blocks": [(0x3C00, ramp)]},
        {"blocks": [(0xC000, [0x8F] * 32), (0x3800, [0x07] * 32)]},
        {"blocks": [(0x0001, [0x9A] * 32)]},
    ]


def hidden_literal_cases():
    return [
        {"blocks": [(0x8000, [0x80] * 32)]},             # -0 scale: signs of zero
        {"blocks": [(0x7C00, [0x08 | (0x9 << 4)] * 32)]},  # inf scale: 0 * inf = NaN (canonical)
        {"blocks": [(0xFC00, [0x0F] * 32)]},
        {"blocks": [(0x7E01, [0x88] * 32)]},               # NaN scale
        {"blocks": [(0x7BFF, [0x00] * 32), (0x0400, [0xFF] * 32)]},
        {"blocks": [(0x3555, list(range(32)))]},
    ]


def random_case(seed):
    r = Lcg(seed)
    nb = (r.next() >> 16) % 5
    blocks = []
    for _ in range(nb):
        x = r.next()
        d = (x >> 16) & 0xFFFF
        if (d & 0x7C00) == 0x7C00:      # keep most scales finite; inf/NaN are literal cases
            d &= 0xBFFF
        b = [(r.next() >> 24) & 0xFF for _ in range(32)]
        blocks.append((d, b))
    return {"blocks": blocks}


def describe(case):
    if not case["blocks"]:
        return "w = [] (nb = 0); y = []"
    return "; ".join(f"block {g}: d = f16 bits 0x{d:04x}, bytes = [{', '.join('0x%02x' % v for v in b)}]"
                     for g, (d, b) in enumerate(case["blocks"]))


def rust_lit(case):
    nb = len(case["blocks"])
    ds = ["0x%04x" % d for d, _ in case["blocks"]]
    bs = ["0x%02x" % v for _, b in case["blocks"] for v in b]
    return (f"let d: [u16; {nb}] = {lit_array('u16', ds)}; "
            f"let b: [u8; {32 * nb}] = {lit_array('u8', bs)}; "
            "x1h_run(&d, &b)")


mith_lit = rust_lit

RUST_HELPERS = r"""
fn x1h_run(d: &[u16], b: &[u8]) -> String {
    let mut w: Vec<BlockQ4> = Vec::new();
    for g in 0..d.len() {
        let mut qs = [0u8; 32];
        for j in 0..32 { qs[j] = b[g * 32 + j]; }
        w.push(BlockQ4 { d: d[g], qs: qs });
    }
    let mut y: Vec<f32> = Vec::new();
    for _i in 0..(64 * d.len()) { y.push(f32::from_bits(0x7f80_0001)); }
    q4_dequant(&w, &mut y);
    let mut out = String::new();
    for i in 0..y.len() {
        if i > 0 { out.push_str(","); }
        out.push_str(&format!("{:08x}", y[i].to_bits()));
    }
    if y.len() == 0 { out.push_str("empty"); }
    out
}

fn x1h_rand(seed: u32) -> String {
    let mut s = seed;
    let nb = ((x1h_next(&mut s) >> 16) % 5) as usize;
    let mut d: Vec<u16> = Vec::new();
    let mut b: Vec<u8> = Vec::new();
    for _g in 0..nb {
        let x = x1h_next(&mut s);
        let mut dd: u16 = ((x >> 16) & 0xFFFF) as u16;
        if (dd & 0x7C00) == 0x7C00 { dd = dd & 0xBFFF; }
        d.push(dd);
        for _j in 0..32 { b.push(((x1h_next(&mut s) >> 24) & 0xFF) as u8); }
    }
    x1h_run(&d, &b)
}
"""

MITH_HELPERS = r"""
fn x1h_run(d: &[u16], b: &[u8]) -> String uses { alloc(Global) } {
    let mut w: Vec<BlockQ4> = Vec::new();
    for g in 0..d.len() {
        let mut qs = [0u8; 32];
        for j in 0..32 { qs[j] = b[g * 32 + j]; }
        w.push(BlockQ4 { d: f16::from_bits(d[g]), q: Nib64o8 { b: qs } });
    }
    let mut y: Vec<f32> = Vec::new();
    for _i in 0..(64 * d.len()) { y.push(f32::from_bits(0x7f80_0001)); }
    q4_dequant(&w, &mut y);
    let mut out = String::new();
    for i in 0..y.len() {
        if i > 0 { out.push_str(","); }
        out.push_str(&format!("{:08x}", y[i].to_bits()));
    }
    if y.len() == 0 { out.push_str("empty"); }
    out
}

fn x1h_rand(seed: u32) -> String uses { alloc(Global) } {
    let mut s = seed;
    let nb = ((x1h_next(&mut s) >> 16) % 5) as usize;
    let mut d: Vec<u16> = Vec::new();
    let mut b: Vec<u8> = Vec::new();
    for _g in 0..nb {
        let x = x1h_next(&mut s);
        let mut dd: u16 = ((x >> 16) & 0xFFFF) as u16;
        if (dd & 0x7C00) == 0x7C00 { dd = dd & 0xBFFF; }
        d.push(dd);
        for _j in 0..32 { b.push(((x1h_next(&mut s) >> 24) & 0xFF) as u8); }
    }
    x1h_run(&d, &b)
}
"""
