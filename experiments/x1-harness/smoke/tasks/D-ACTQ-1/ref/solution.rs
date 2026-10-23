// D-ACTQ-1 reference (Rust).
use crate::prelude::*;

pub fn act_quantize_q8(x: &[f32], out: &mut [ActQ8]) {
    for b in 0..out.len() {
        let v = &x[b * 64..b * 64 + 64];
        let mut amax: f32 = 0.0;
        for i in 0..64 {
            let a = v[i].abs();
            if a > amax {
                amax = a;
            }
        }
        let d = amax / 127.0;
        let id = if d != 0.0 { 1.0 / d } else { 0.0 };
        let mut q = [0i8; 64];
        let mut sum: i32 = 0;
        for i in 0..64 {
            q[i] = (v[i] * id).round_ties_even() as i8;
            sum += q[i] as i32;
        }
        out[b] = ActQ8 { d, sum, q };
    }
}
