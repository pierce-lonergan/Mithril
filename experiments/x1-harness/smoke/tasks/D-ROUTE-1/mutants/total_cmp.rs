// MUTANT total_cmp: sorts by f32::total_cmp (orders -0.0 below +0.0, sign-dependent NaN placement).
// CANARY: expected FAIL.
use crate::prelude::*;

pub fn topk(sel: &[f32], k: usize, ids: &mut [u32]) {
    let mut idx: Vec<usize> = (0..sel.len()).collect();
    idx.sort_by(|&a, &b| sel[b].total_cmp(&sel[a]).then(a.cmp(&b)));
    for r in 0..k {
        ids[r] = idx[r] as u32;
    }
}
