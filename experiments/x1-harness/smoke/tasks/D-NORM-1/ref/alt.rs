// D-NORM-1 correct-but-non-reference (Rust): explicit squares and sum16. CANARY: expected PASS.
use crate::prelude::*;

pub fn rmsnorm(y: &mut [f32], x: &[f32], w: &[f32], eps: f32) {
    let sq: Vec<f32> = x.iter().map(|v| v * v).collect();
    let ms = sum16(&sq) / x.len() as f32;
    let r = 1.0f32 / (ms + eps).sqrt();
    for ((yi, xi), wi) in y.iter_mut().zip(x).zip(w) {
        let v = (xi * r) * wi;
        *yi = if v.is_nan() { f32::from_bits(0x7fc0_0000) } else { v };
    }
}
