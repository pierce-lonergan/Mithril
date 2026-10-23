// MUTANT seq_sum: a sequential float sum (FF-SUM) instead of the 16-lane sum. CANARY: expected FAIL.
use crate::prelude::*;

pub fn rmsnorm(y: &mut [f32], x: &[f32], w: &[f32], eps: f32) {
    let n = x.len();
    let ms = x.iter().map(|v| v * v).sum::<f32>() / (n as f32);
    let r = 1.0 / (ms + eps).sqrt();
    for i in 0..n {
        y[i] = canon_nan((x[i] * r) * w[i]);
    }
}
