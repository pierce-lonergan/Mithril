// D-FMT-1 reference (Rust).
use crate::prelude::*;

fn u32_at(buf: &[u8], off: usize) -> u32 {
    u32::from_le_bytes([buf[off], buf[off + 1], buf[off + 2], buf[off + 3]])
}

pub fn parse_trace(buf: &[u8], m: &ModelDims, ids: &mut Vec<u16>) -> Result<TraceHeader, TraceError> {
    if buf.len() < 24 {
        return Err(TraceError::Truncated);
    }
    if u32_at(buf, 0) != 0x5254_5248 {
        return Err(TraceError::BadMagic);
    }
    if u32_at(buf, 4) != 1 {
        return Err(TraceError::BadVersion);
    }
    let n_layers = u32_at(buf, 8);
    let n_experts = u32_at(buf, 12);
    let top_k = u32_at(buf, 16);
    let n_moe = u32_at(buf, 20);
    if n_experts != m.n_experts || top_k != m.top_k || n_moe != m.n_moe_layers {
        return Err(TraceError::Mismatch);
    }
    if n_layers < n_moe {
        return Err(TraceError::Mismatch);
    }
    let rec = (n_moe as usize) * (top_k as usize) * 2;
    let body = buf.len() - 24;
    if rec == 0 || body % rec != 0 {
        return Err(TraceError::Truncated);
    }
    for c in buf[24..].chunks(2) {
        let id = u16::from_le_bytes([c[0], c[1]]);
        if id as u32 >= n_experts {
            return Err(TraceError::BadId);
        }
        ids.push(id);
    }
    Ok(TraceHeader { n_layers, n_experts, top_k, n_moe_layers: n_moe, n_tokens: (body / rec) as u64 })
}
