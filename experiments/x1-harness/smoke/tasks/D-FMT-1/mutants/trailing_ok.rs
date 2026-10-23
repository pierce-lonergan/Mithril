// MUTANT trailing_ok: a trailing partial record is ignored instead of rejected. CANARY: expected FAIL.
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
    if rec == 0 {
        return Err(TraceError::Truncated);
    }
    let body = buf.len() - 24;
    let n_tok = body / rec;
    for t in 0..n_tok * rec / 2 {
        let o = 24 + 2 * t;
        let id = u16::from_le_bytes([buf[o], buf[o + 1]]);
        if id as u32 >= n_experts {
            return Err(TraceError::BadId);
        }
        ids.push(id);
    }
    Ok(TraceHeader { n_layers, n_experts, top_k, n_moe_layers: n_moe, n_tokens: n_tok as u64 })
}
