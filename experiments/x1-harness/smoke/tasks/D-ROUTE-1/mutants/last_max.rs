// MUTANT last_max: repeated max_by with partial_cmp keeps the last maximum (FF-TIES), NaN as equal.
// CANARY: expected FAIL.
use crate::prelude::*;

pub fn topk(sel: &[f32], k: usize, ids: &mut [u32]) {
    let mut taken = vec![false; sel.len()];
    for r in 0..k {
        let b = (0..sel.len())
            .filter(|&e| !taken[e])
            .max_by(|&a, &b| {
                let (va, vb) = (sel[a], sel[b]);
                if va.is_nan() && !vb.is_nan() {
                    std::cmp::Ordering::Less
                } else if vb.is_nan() && !va.is_nan() {
                    std::cmp::Ordering::Greater
                } else {
                    va.partial_cmp(&vb).unwrap_or(std::cmp::Ordering::Equal)
                }
            })
            .unwrap();
        ids[r] = b as u32;
        taken[b] = true;
    }
}
