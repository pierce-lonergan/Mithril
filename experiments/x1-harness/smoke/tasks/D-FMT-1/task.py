"""D-FMT-1 (T-FMT), DEVELOPMENT item: routing-trace parser (S-FMT-0 shape; Hearth FORMAT.md 9).

The check order is part of the brief (FORMAT.md does not fix it). Not sealed, not held out. The
oracle is exact parity with the Python model on literal and generated buffers (no ASan, no fuzzing:
a development item).
"""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from smokelib import Lcg, lit_array  # noqa: E402

TASK = {
    "id": "D-FMT-1",
    "family": "T-FMT",
    "split": "development",
    "title": "Routing-trace parser (S-FMT-0 shape)",
    "unit": "parse_trace",
    "grade": "default",
}

RANDOM = {"count": 250, "seed0": 48000}
MAGIC = 0x52545248


def u32_at(b, off):
    return struct.unpack_from("<I", bytes(b), off)[0]


def model(case):
    buf = case["buf"]
    ne_m, tk_m, nm_m = case["dims"]
    if len(buf) < 24:
        return "E:Truncated"
    if u32_at(buf, 0) != MAGIC:
        return "E:BadMagic"
    if u32_at(buf, 4) != 1:
        return "E:BadVersion"
    nl, ne, tk, nm = (u32_at(buf, o) for o in (8, 12, 16, 20))
    if ne != ne_m or tk != tk_m or nm != nm_m:
        return "E:Mismatch"
    if nl < nm:
        return "E:Mismatch"
    rec = nm * tk * 2
    body = len(buf) - 24
    if rec == 0 or body % rec != 0:
        return "E:Truncated"
    ids = [struct.unpack_from("<H", bytes(buf), o)[0] for o in range(24, len(buf), 2)]
    if any(i >= ne for i in ids):
        return "E:BadId"
    return f"H:{nl},{ne},{tk},{nm},{body // rec};" + ",".join(str(i) for i in ids)


def header(magic, ver, nl, ne, tk, nm):
    return list(struct.pack("<6I", magic, ver, nl, ne, tk, nm))


def trace(dims, nl, ids, magic=MAGIC, ver=1, hdr=None):
    ne, tk, nm = dims
    h = header(magic, ver, nl, *(hdr or (ne, tk, nm)))
    return h + [b for i in ids for b in struct.pack("<H", i)]


def visible_cases():
    d = (8, 2, 1)
    return [
        {"dims": d, "buf": trace(d, 4, [1, 7, 0, 3])},
        {"dims": d, "buf": trace(d, 4, [1, 7, 0, 3])[:20]},
        {"dims": d, "buf": trace(d, 4, [1, 8])},
        {"dims": d, "buf": trace(d, 4, [], magic=0x52545249)},
        {"dims": d, "buf": trace(d, 4, [1, 2, 3])},       # 6 body bytes, record 4: a trailing partial record
    ]


def hidden_literal_cases():
    d = (16, 4, 2)
    big = 0xFFFFFFFF
    return [
        {"dims": d, "buf": trace(d, 2, [])},                                   # zero tokens: valid
        {"dims": d, "buf": trace(d, 1, [0] * 8)},                              # n_layers < n_moe_layers
        {"dims": d, "buf": trace(d, 3, [0] * 8, ver=2)},
        {"dims": d, "buf": trace(d, 3, [0] * 8, hdr=(16, big, big))},          # huge counts: Mismatch first
        {"dims": d, "buf": trace(d, 3, [0] * 8, hdr=(17, 4, 2))},
        {"dims": (16, 0, 2), "buf": trace((16, 0, 2), 3, [])},                 # record size 0: Truncated
        {"dims": d, "buf": trace(d, 3, [15] * 8 + [16])[:-1]},                 # odd trailing byte
        {"dims": d, "buf": trace(d, 3, [15] * 16)},
        {"dims": d, "buf": trace(d, 3, [15] * 15 + [65535])},
        {"dims": d, "buf": [0x48, 0x52, 0x54, 0x52]},                          # magic only
        {"dims": d, "buf": []},
        {"dims": d, "buf": trace(d, 3, [1] * 8, magic=0x48525452)},            # big-endian magic
        {"dims": (65535, 1, 1), "buf": trace((65535, 1, 1), 1, [65534, 0, 65535])},
    ]


DIMS = [(4, 1, 1), (8, 2, 1), (16, 4, 2), (64, 2, 3), (128, 4, 3), (8, 8, 2)]


def random_case(seed):
    r = Lcg(seed)
    dims = DIMS[(r.next() >> 16) % len(DIMS)]
    ne, tk, nm = dims
    nl = nm + (r.next() >> 16) % 4
    ntok = (r.next() >> 16) % 5
    ids = [(r.next() >> 16) % ne for _ in range(ntok * tk * nm)]
    buf = trace(dims, nl, ids)
    kind = (r.next() >> 16) % 11
    x = r.next() >> 16
    if kind == 4:
        buf = buf[:x % len(buf)]                                  # truncation anywhere
    elif kind == 5:
        buf[x % 4] ^= 1 << ((x >> 4) % 8)                         # magic bit flip
    elif kind == 6:
        buf[4] = 2                                                # version
    elif kind == 7:
        buf[12 + 4 * (x % 3)] ^= 1                                # a dimension field
    elif kind == 8 and len(buf) > 24:
        o = 24 + 2 * (x % ((len(buf) - 24) // 2))
        buf[o:o + 2] = list(struct.pack("<H", ne + (x >> 4) % 3))   # an out-of-range id
    elif kind == 9:
        buf = buf + [(x >> 8) & 0xFF] * (1 + x % 3)               # trailing bytes
    elif kind == 10:
        buf[8:12] = list(struct.pack("<I", (r.next() >> 16) % (nm + 1)))   # n_layers may drop below
    return {"dims": dims, "buf": buf}


def describe(c):
    ne, tk, nm = c["dims"]
    return (f"model dims: n_experts = {ne}, top_k = {tk}, n_moe_layers = {nm}; buf ({len(c['buf'])} bytes) = ["
            + ", ".join("0x%02x" % b for b in c["buf"]) + "]")


def rust_lit(c):
    ne, tk, nm = c["dims"]
    n = len(c["buf"])
    return (f"let b: [u8; {n}] = {lit_array('u8', ['0x%02x' % v for v in c['buf']])}; "
            f"x1h_run(&b, {ne}u32, {tk}u32, {nm}u32)")


mith_lit = rust_lit

DIMS_NE = ", ".join(str(d[0]) for d in DIMS)
DIMS_TK = ", ".join(str(d[1]) for d in DIMS)
DIMS_NM = ", ".join(str(d[2]) for d in DIMS)

_COMMON = r"""
fn x1h_put32(v: &mut Vec<u8>, x: u32) @@USES@@{
    let b = x.to_le_bytes();
    for i in 0..4 { v.push(b[i]); }
}

fn x1h_rand(seed: u32) -> String @@USES@@{
    let d_ne: [u32; 6] = [@@NE@@];
    let d_tk: [u32; 6] = [@@TK@@];
    let d_nm: [u32; 6] = [@@NM@@];
    let mut s = seed;
    let di = ((x1h_next(&mut s) >> 16) % 6) as usize;
    let ne = d_ne[di];
    let tk = d_tk[di];
    let nm = d_nm[di];
    let nl = nm + (x1h_next(&mut s) >> 16) % 4;
    let ntok = (x1h_next(&mut s) >> 16) % 5;
    let mut buf: Vec<u8> = Vec::new();
    x1h_put32(&mut buf, 0x52545248);
    x1h_put32(&mut buf, 1);
    x1h_put32(&mut buf, nl);
    x1h_put32(&mut buf, ne);
    x1h_put32(&mut buf, tk);
    x1h_put32(&mut buf, nm);
    for _i in 0..(ntok * tk * nm) {
        let id = ((x1h_next(&mut s) >> 16) % ne) as u16;
        let b = id.to_le_bytes();
        buf.push(b[0]);
        buf.push(b[1]);
    }
    let kind = (x1h_next(&mut s) >> 16) % 11;
    let x = x1h_next(&mut s) >> 16;
    let len = buf.len();
    let mut out: Vec<u8> = Vec::new();
    if kind == 4 {
        let keep = (x as usize) % len;
        for i in 0..keep { out.push(buf[i]); }
    } else {
        for i in 0..len { out.push(buf[i]); }
        if kind == 5 {
            let o = (x % 4) as usize;
            out[o] = out[o] ^ ((1u32 << ((x >> 4) % 8)) as u8);
        } else if kind == 6 {
            out[4] = 2;
        } else if kind == 7 {
            let o = (12 + 4 * (x % 3)) as usize;
            out[o] = out[o] ^ 1;
        } else if kind == 8 && len > 24 {
            let o = 24 + 2 * ((x as usize) % ((len - 24) / 2));
            let b = ((ne + (x >> 4) % 3) as u16).to_le_bytes();
            out[o] = b[0];
            out[o + 1] = b[1];
        } else if kind == 9 {
            for _i in 0..(1 + x % 3) { out.push(((x >> 8) & 0xFF) as u8); }
        } else if kind == 10 {
            let b = ((x1h_next(&mut s) >> 16) % (nm + 1)).to_le_bytes();
            for i in 0..4 { out[8 + i] = b[i]; }
        }
    }
    x1h_run(&out, ne, tk, nm)
}
""".replace("@@NE@@", DIMS_NE).replace("@@TK@@", DIMS_TK).replace("@@NM@@", DIMS_NM)

RUST_HELPERS = r"""
fn x1h_err(e: TraceError) -> &'static str {
    match e {
        TraceError::Truncated => "Truncated",
        TraceError::BadMagic => "BadMagic",
        TraceError::BadVersion => "BadVersion",
        TraceError::Mismatch => "Mismatch",
        TraceError::BadId => "BadId",
    }
}

fn x1h_run(b: &[u8], ne: u32, tk: u32, nm: u32) -> String {
    let m = ModelDims { n_experts: ne, top_k: tk, n_moe_layers: nm };
    let mut ids: Vec<u16> = Vec::new();
    match parse_trace(b, &m, &mut ids) {
        Ok(h) => {
            let mut s = format!("H:{},{},{},{},{};", h.n_layers, h.n_experts, h.top_k, h.n_moe_layers, h.n_tokens);
            for i in 0..ids.len() {
                if i > 0 { s.push_str(","); }
                s.push_str(&format!("{}", ids[i]));
            }
            s
        }
        Err(e) => format!("E:{}", x1h_err(e)),
    }
}
""" + _COMMON.replace("@@USES@@", "")

MITH_HELPERS = r"""
fn x1h_run(b: &[u8], ne: u32, tk: u32, nm: u32) -> String uses { alloc(Global) } {
    let m = ModelDims { n_experts: ne, top_k: tk, n_moe_layers: nm };
    let mut ids: Vec<u16> = Vec::new();
    match parse_trace(b, &m, &mut ids) {
        Ok(h) => {
            let mut s = format!("H:{},{},{},{},{};", h.n_layers, h.n_experts, h.top_k, h.n_moe_layers, h.n_tokens);
            for i in 0..ids.len() {
                if i > 0 { s.push_str(","); }
                s.push_str(&format!("{}", ids[i]));
            }
            s
        }
        Err(TraceError::Truncated) => "E:Truncated".to_string(),
        Err(TraceError::BadMagic) => "E:BadMagic".to_string(),
        Err(TraceError::BadVersion) => "E:BadVersion".to_string(),
        Err(TraceError::Mismatch) => "E:Mismatch".to_string(),
        Err(TraceError::BadId) => "E:BadId".to_string(),
    }
}
""" + _COMMON.replace("@@USES@@", "uses { alloc(Global) } ")
