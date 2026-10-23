// D-Q4-2 reference (Rust).
use crate::prelude::*;

pub fn q4_dequant(w: &[BlockQ4], y: &mut [f32]) {
    for g in 0..w.len() {
        let d = f16_to_f32(w[g].d);
        for i in 0..64 {
            y[g * 64 + i] = canon_nan((w[g].elem(i) as f32) * d);
        }
    }
}
