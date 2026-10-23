"""D-ROUTE-2 (T-ROUTE), DEVELOPMENT item: group-limited top-k (S-ROUTE-0 shape).

The selection step of Hearth's route_select (engine/src/model.c at b5d3f14, NUMERICS 5.3): group
score = the sum of the group's two best values in rank order (the best alone for one-expert groups);
keep the topk_group best groups; experts of dropped groups count as 0.0 and stay eligible; then the
k best experts. Ranking everywhere is Hearth's ranks_before. Not sealed, not held out.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from smokelib import Lcg, add, from_bits, lit_array  # noqa: E402

TASK = {
    "id": "D-ROUTE-2",
    "family": "T-ROUTE",
    "split": "development",
    "title": "Group-limited top-k selection (S-ROUTE-0 shape)",
    "unit": "group_topk",
    "grade": "exact",
}

RANDOM = {"count": 150, "seed0": 46000}

PALETTE = [0xC0000000, 0xBF800000, 0xBF000000, 0x80000000, 0x00000000, 0x3E800000, 0x3F000000,
           0x3F800000, 0x3F800000, 0x40000000, 0x7FC00000, 0x7F800000, 0xFF800000, 0x40400000]
SHAPES = [(1, 4), (2, 1), (2, 3), (4, 2), (4, 4), (8, 2), (8, 4), (2, 8), (16, 2), (4, 16)]


def ranks_before(va, ia, vb, ib):
    na, nb = va != va, vb != vb
    if na or nb:
        return ia < ib if na == nb else nb
    if va != vb:
        return va > vb
    return ia < ib


def model(case):
    sel = [from_bits(b) for b in case["sel"]]
    ng, tg, k = case["n_group"], case["topk_group"], case["k"]
    E = len(sel)
    if ng > 1:
        gs = E // ng
        gsc, keep = [], [False] * ng
        for g in range(ng):
            v = sel[g * gs:(g + 1) * gs]
            i1, i2 = 0, -1
            for i in range(1, gs):
                if ranks_before(v[i], i, v[i1], i1):
                    i2, i1 = i1, i
                elif i2 < 0 or ranks_before(v[i], i, v[i2], i2):
                    i2 = i
            gsc.append(add(v[i1], v[i2]) if i2 >= 0 else v[i1])
        for _ in range(tg):
            best = -1
            for g in range(ng):
                if not keep[g] and (best < 0 or ranks_before(gsc[g], g, gsc[best], best)):
                    best = g
            keep[best] = True
        sel = [sel[e] if keep[e // gs] else 0.0 for e in range(E)]
    taken = [False] * E
    ids = []
    for _ in range(k):
        best = -1
        for e in range(E):
            if not taken[e] and (best < 0 or ranks_before(sel[e], e, sel[best], best)):
                best = e
        ids.append(best)
        taken[best] = True
    return ",".join(str(i) for i in ids) if ids else "empty"


def mk(vals, ng, tg, k):
    import struct
    return {"sel": [struct.unpack("<I", struct.pack("<f", v))[0] if isinstance(v, float) else v for v in vals],
            "n_group": ng, "topk_group": tg, "k": k}


def visible_cases():
    return [
        mk([0.1, 0.9, 0.2, 0.3, 0.8, 0.7, 0.05, 0.6], 4, 2, 3),
        mk([1.0, 1.0, 1.0, 1.0], 2, 1, 4),
        mk([-1.0, -2.0, 0.5, 0.25, -0.5, -0.25], 3, 1, 4),   # dropped experts count as 0.0 and stay eligible
        mk([3.0, 0.0, 2.0, 2.5, 0.0, 0.0], 1, 1, 3),         # one group: no group limit
    ]


def hidden_literal_cases():
    nan, inf, ninf = 0x7FC00000, 0x7F800000, 0xFF800000
    return [
        mk([nan, 1.0, 2.0, nan, 0.5, 0.5], 3, 2, 6),
        mk([inf, ninf, 1.0, 1.0, 0.0, -0.0], 3, 1, 6),       # inf + -inf = NaN group score ranks last
        mk([2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0], 4, 2, 8),
        mk([0.5, 0.5, 0.75, 0.25, 0.6, 0.4, 0.9, 0.1], 4, 3, 5),  # equal group sums: lower group index
        mk([-0.0, 0.0, 0.0, -0.0], 4, 2, 4),
        mk([5.0, -3.0, -1.0, -2.0, -0.5, -0.75], 2, 1, 6),   # group scores: top-2 sums, not top-1
    ]


def random_case(seed):
    r = Lcg(seed)
    ng, gs = SHAPES[(r.next() >> 16) % len(SHAPES)]
    E = ng * gs
    tg = 1 + (r.next() >> 16) % ng
    k = (r.next() >> 16) % (E + 1)
    sel = [PALETTE[(r.next() >> 16) % len(PALETTE)] for _ in range(E)]
    return {"sel": sel, "n_group": ng, "topk_group": tg, "k": k}


def describe(c):
    return ("sel (f32 bits) = [" + ", ".join("0x%08x" % v for v in c["sel"]) + "]; "
            f"n_group = {c['n_group']}; topk_group = {c['topk_group']}; k = {c['k']}")


def rust_lit(c):
    n = len(c["sel"])
    return (f"let s: [u32; {n}] = {lit_array('u32', ['0x%08x' % v for v in c['sel']], 8)}; "
            f"x1h_run(&s, {c['n_group']}, {c['topk_group']}, {c['k']})")


mith_lit = rust_lit

PAL_RS = ", ".join("0x%08X" % v for v in PALETTE)
SH_RS = ", ".join(f"{a}" for a, _ in SHAPES)
SH2_RS = ", ".join(f"{b}" for _, b in SHAPES)

_RUN = r"""
fn x1h_run(sb: &[u32], ng: usize, tg: usize, k: usize) -> String @@USES@@{
    let mut sel: Vec<f32> = Vec::new();
    for i in 0..sb.len() { sel.push(f32::from_bits(sb[i])); }
    let mut ids: Vec<u32> = Vec::new();
    for _i in 0..k { ids.push(999999); }
    group_topk(&sel, ng, tg, k, &mut ids);
    let mut out = String::new();
    for i in 0..k {
        if i > 0 { out.push_str(","); }
        out.push_str(&format!("{}", ids[i]));
    }
    if k == 0 { out.push_str("empty"); }
    out
}

fn x1h_rand(seed: u32) -> String @@USES@@{
    let pal: [u32; 14] = [@@PAL@@];
    let sh_ng: [u32; 10] = [@@SH@@];
    let sh_gs: [u32; 10] = [@@SH2@@];
    let mut s = seed;
    let si = ((x1h_next(&mut s) >> 16) % 10) as usize;
    let ng = sh_ng[si];
    let e = ng * sh_gs[si];
    let tg = 1 + (x1h_next(&mut s) >> 16) % ng;
    let k = (x1h_next(&mut s) >> 16) % (e + 1);
    let mut sb: Vec<u32> = Vec::new();
    for _i in 0..e { sb.push(pal[((x1h_next(&mut s) >> 16) % 14) as usize]); }
    x1h_run(&sb, ng as usize, tg as usize, k as usize)
}
""".replace("@@PAL@@", PAL_RS).replace("@@SH@@", SH_RS).replace("@@SH2@@", SH2_RS)

RUST_HELPERS = _RUN.replace("@@USES@@", "")
MITH_HELPERS = _RUN.replace("@@USES@@", "uses { alloc(Global) } ")
