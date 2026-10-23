// MUTANT no_offset: the stored nibble is used without subtracting 8. CANARY: expected FAIL.
use crate::prelude::*;

pub fn q4_dequant(w: &[BlockQ4], y: &mut [f32]) {
    for g in 0..w.len() {
        let d = f16_to_f32(w[g].d);
        for j in 0..32 {
            y[g * 64 + j] = canon_nan((w[g].qs[j] & 15) as f32 * d);
            y[g * 64 + j + 32] = canon_nan((w[g].qs[j] >> 4) as f32 * d);
        }
    }
}
