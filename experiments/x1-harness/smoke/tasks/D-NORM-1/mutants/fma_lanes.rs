// MUTANT fma_lanes: squares accumulated with mul_add (one rounding per step). CANARY: expected FAIL.
use crate::prelude::*;

pub fn rmsnorm(y: &mut [f32], x: &[f32], w: &[f32], eps: f32) {
    let n = x.len();
    let mut l = [0.0f32; 16];
    for i in 0..n {
        l[i & 15] = x[i].mul_add(x[i], l[i & 15]);
    }
    for s in [8usize, 4, 2, 1] {
        for j in 0..s {
            l[j] += l[j + s];
        }
    }
    let ms = l[0] / (n as f32);
    let r = 1.0 / (ms + eps).sqrt();
    for i in 0..n {
        y[i] = canon_nan((x[i] * r) * w[i]);
    }
}
