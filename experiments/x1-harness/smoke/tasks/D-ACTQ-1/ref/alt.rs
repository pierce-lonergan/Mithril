// D-ACTQ-1 correct-but-non-reference (Rust): chunks, fold for amax, iterator sum over integers.
// CANARY: expected PASS.
use crate::prelude::*;

pub fn act_quantize_q8(x: &[f32], out: &mut [ActQ8]) {
    for (blk, o) in x.chunks(64).zip(out.iter_mut()) {
        let amax = blk.iter().fold(0.0f32, |m, v| if v.abs() > m { v.abs() } else { m });
        let d = amax / 127.0;
        let id = if d != 0.0 { 1.0 / d } else { 0.0 };
        for (i, v) in blk.iter().enumerate() {
            o.q[i] = (v * id).round_ties_even() as i8;
        }
        o.sum = o.q.iter().map(|&q| q as i32).sum();
        o.d = d;
    }
}
