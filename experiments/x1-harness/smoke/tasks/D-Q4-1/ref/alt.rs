// D-Q4-1 correct-but-non-reference (Rust): explicit nibble decoding, element pairs per byte.
// CANARY: expected PASS.
use crate::prelude::*;

pub fn q4_row_dot(w: &[BlockQ4], a: &[ActQ8]) -> f32 {
    let mut acc = 0.0f32;
    for (wb, ab) in w.iter().zip(a.iter()) {
        let mut isum = 0i32;
        for j in 0..32 {
            let lo = (wb.qs[j] & 0x0f) as i32 - 8;
            let hi = (wb.qs[j] >> 4) as i32 - 8;
            isum += lo * ab.q[j] as i32 + hi * ab.q[j + 32] as i32;
        }
        let scale = f16_to_f32(wb.d) * ab.d;
        acc += isum as f32 * scale;
    }
    if acc.is_nan() { f32::from_bits(0x7fc00000) } else { acc }
}
