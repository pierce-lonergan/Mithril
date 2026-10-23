"""D-ROUTE-1 (T-ROUTE), DEVELOPMENT item: exact top-k selection, ties to the lower index, NaN last.

S-ROUTE-0 of X1 DESIGN 5.2 simplified to plain top-k (as in crates/mithi/tests/corpus/route.mith),
with the ordering rule of Hearth's ranks_before (engine/src/model.c at b5d3f14). Not sealed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from smokelib import Lcg, from_bits, lit_array  # noqa: E402

TASK = {
    "id": "D-ROUTE-1",
    "family": "T-ROUTE",
    "split": "development",
    "title": "Exact top-k: descending, ties to the lower index, NaN last",
    "unit": "topk",
    "grade": "exact",
}

RANDOM = {"count": 150, "seed0": 45000}

# palette of f32 bit patterns: ties, signed zeros, infinities and NaNs with different payloads
PALETTE = [0xC0000000, 0xBF800000, 0x80000000, 0x00000000, 0x3F000000, 0x3F800000, 0x3F800000,
           0x40000000, 0x7FC00000, 0x7F800000, 0xFF800000, 0x40400000, 0xFFC00001, 0x3F800000]


def ranks_before(va, ia, vb, ib):
    na, nb = va != va, vb != vb
    if na or nb:
        return ia < ib if na == nb else nb
    if va != vb:
        return va > vb
    return ia < ib


def select(vals, k):
    taken = [False] * len(vals)
    ids = []
    for _ in range(k):
        best = -1
        for e in range(len(vals)):
            if not taken[e] and (best < 0 or ranks_before(vals[e], e, vals[best], best)):
                best = e
        ids.append(best)
        taken[best] = True
    return ids


def model(case):
    vals = [from_bits(b) for b in case["sel"]]
    ids = select(vals, case["k"])
    return ",".join(str(i) for i in ids) if ids else "empty"


def visible_cases():
    f = {"0.5": 0x3F000000, "2": 0x40000000, "nan": 0x7FC00000, "-1": 0xBF800000, "1": 0x3F800000,
         "-0": 0x80000000, "0": 0x00000000}
    return [
        {"sel": [f["0.5"], f["2"], f["nan"], f["2"], f["-1"]], "k": 4},
        {"sel": [f["1"], f["1"], f["1"]], "k": 3},
        {"sel": [f["-0"], f["0"], f["-1"]], "k": 2},
        {"sel": [f["nan"], f["1"]], "k": 0},
    ]


def hidden_literal_cases():
    nan, inf, ninf = 0x7FC00000, 0x7F800000, 0xFF800000
    return [
        {"sel": [nan, nan, 0x3F800000, nan], "k": 4},                 # NaNs last, lower index first
        {"sel": [ninf, 0xC0000000, inf, 0x80000000, 0x00000000], "k": 5},
        {"sel": [0xFFC00001, 0x7FC00000, 0xFF800000], "k": 3},          # a negative-sign NaN is still last
        {"sel": [0x00000000, 0x80000000] * 8, "k": 16},                 # -0 == +0: index order
        {"sel": [0x3F800000] * 40, "k": 40},
        {"sel": [0x40000000 + i for i in range(64)], "k": 64},
    ]


def random_case(seed):
    r = Lcg(seed)
    n = 1 + (r.next() >> 16) % 48
    k = (r.next() >> 16) % (n + 1)
    sel = [PALETTE[(r.next() >> 16) % len(PALETTE)] for _ in range(n)]
    return {"sel": sel, "k": k}


def describe(c):
    return "sel (f32 bits) = [" + ", ".join("0x%08x" % v for v in c["sel"]) + f"]; k = {c['k']}"


def rust_lit(c):
    n = len(c["sel"])
    return (f"let s: [u32; {n}] = {lit_array('u32', ['0x%08x' % v for v in c['sel']], 8)}; "
            f"x1h_run(&s, {c['k']})")


mith_lit = rust_lit

PAL_RS = ", ".join("0x%08X" % v for v in PALETTE)

RUST_HELPERS = r"""
fn x1h_run(sb: &[u32], k: usize) -> String {
    let mut sel: Vec<f32> = Vec::new();
    for i in 0..sb.len() { sel.push(f32::from_bits(sb[i])); }
    let mut ids: Vec<u32> = Vec::new();
    for _i in 0..k { ids.push(999999); }
    topk(&sel, k, &mut ids);
    let mut out = String::new();
    for i in 0..k {
        if i > 0 { out.push_str(","); }
        out.push_str(&format!("{}", ids[i]));
    }
    if k == 0 { out.push_str("empty"); }
    out
}

fn x1h_rand(seed: u32) -> String {
    let pal: [u32; 14] = [@@PAL@@];
    let mut s = seed;
    let n = 1 + ((x1h_next(&mut s) >> 16) % 48) as usize;
    let k = ((x1h_next(&mut s) >> 16) % ((n + 1) as u32)) as usize;
    let mut sb: Vec<u32> = Vec::new();
    for _i in 0..n { sb.push(pal[((x1h_next(&mut s) >> 16) % 14) as usize]); }
    x1h_run(&sb, k)
}
""".replace("@@PAL@@", PAL_RS)

MITH_HELPERS = r"""
fn x1h_run(sb: &[u32], k: usize) -> String uses { alloc(Global) } {
    let mut sel: Vec<f32> = Vec::new();
    for i in 0..sb.len() { sel.push(f32::from_bits(sb[i])); }
    let mut ids: Vec<u32> = Vec::new();
    for _i in 0..k { ids.push(999999); }
    topk(&sel, k, &mut ids);
    let mut out = String::new();
    for i in 0..k {
        if i > 0 { out.push_str(","); }
        out.push_str(&format!("{}", ids[i]));
    }
    if k == 0 { out.push_str("empty"); }
    out
}

fn x1h_rand(seed: u32) -> String uses { alloc(Global) } {
    let pal: [u32; 14] = [@@PAL@@];
    let mut s = seed;
    let n = 1 + ((x1h_next(&mut s) >> 16) % 48) as usize;
    let k = ((x1h_next(&mut s) >> 16) % ((n + 1) as u32)) as usize;
    let mut sb: Vec<u32> = Vec::new();
    for _i in 0..n { sb.push(pal[((x1h_next(&mut s) >> 16) % 14) as usize]); }
    x1h_run(&sb, k)
}
""".replace("@@PAL@@", PAL_RS)
