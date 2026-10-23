// D-Q4-2 correct-but-non-reference (Rust): chunked output, raw nibbles. CANARY: expected PASS.
use crate::prelude::*;

pub fn q4_dequant(w: &[BlockQ4], y: &mut [f32]) {
    for (blk, out) in w.iter().zip(y.chunks_mut(64)) {
        let d = f16_to_f32(blk.d);
        for j in 0..32 {
            let lo = ((blk.qs[j] & 0x0f) as i32 - 8) as f32 * d;
            let hi = ((blk.qs[j] >> 4) as i32 - 8) as f32 * d;
            out[j] = if lo.is_nan() { f32::from_bits(0x7fc00000) } else { lo };
            out[j + 32] = if hi.is_nan() { f32::from_bits(0x7fc00000) } else { hi };
        }
    }
}
