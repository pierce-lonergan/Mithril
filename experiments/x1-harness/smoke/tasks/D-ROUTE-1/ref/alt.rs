// D-ROUTE-1 correct-but-non-reference (Rust): a stable sort of indices with a total key.
// CANARY: expected PASS.
use crate::prelude::*;

pub fn topk(sel: &[f32], k: usize, ids: &mut [u32]) {
    let mut idx: Vec<usize> = (0..sel.len()).collect();
    idx.sort_by(|&a, &b| {
        let (va, vb) = (sel[a], sel[b]);
        match (va.is_nan(), vb.is_nan()) {
            (true, true) => a.cmp(&b),
            (true, false) => std::cmp::Ordering::Greater,
            (false, true) => std::cmp::Ordering::Less,
            (false, false) => vb.partial_cmp(&va).unwrap().then(a.cmp(&b)),
        }
    });
    for r in 0..k {
        ids[r] = idx[r] as u32;
    }
}
