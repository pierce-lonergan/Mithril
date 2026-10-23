// MUTANT j_plus_16: high nibble of byte j taken as element j+16 (llama.cpp Q4_0 prior, FF-Q4).
// CANARY: expected FAIL.
use crate::prelude::*;

pub fn q4_dequant(w: &[BlockQ4], y: &mut [f32]) {
    for g in 0..w.len() {
        let d = f16_to_f32(w[g].d);
        for j in 0..16 {
            let b0 = w[g].qs[j];
            let b1 = w[g].qs[j + 16];
            y[g * 64 + j] = canon_nan(((b0 & 15) as i32 - 8) as f32 * d);
            y[g * 64 + j + 16] = canon_nan(((b0 >> 4) as i32 - 8) as f32 * d);
            y[g * 64 + j + 32] = canon_nan(((b1 & 15) as i32 - 8) as f32 * d);
            y[g * 64 + j + 48] = canon_nan(((b1 >> 4) as i32 - 8) as f32 * d);
        }
    }
}
