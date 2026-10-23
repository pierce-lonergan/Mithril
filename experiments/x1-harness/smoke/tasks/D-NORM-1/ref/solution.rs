// D-NORM-1 reference (Rust).
use crate::prelude::*;

pub fn rmsnorm(y: &mut [f32], x: &[f32], w: &[f32], eps: f32) {
    let n = x.len();
    let ms = dot16(x, x) / (n as f32);
    let r = 1.0 / (ms + eps).sqrt();
    for i in 0..n {
        y[i] = canon_nan((x[i] * r) * w[i]);
    }
}
