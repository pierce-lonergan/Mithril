// MUTANT no_canon: NaN results are returned raw. CANARY: expected FAIL.
use crate::prelude::*;

pub fn q4_row_dot(w: &[BlockQ4], a: &[ActQ8]) -> f32 {
    let mut acc: f32 = 0.0;
    for g in 0..w.len() {
        let mut isum: i32 = 0;
        for j in 0..64 {
            isum += w[g].elem(j) * (a[g].q[j] as i32);
        }
        acc = acc + (isum as f32) * (f16_to_f32(w[g].d) * a[g].d);
    }
    acc
}
