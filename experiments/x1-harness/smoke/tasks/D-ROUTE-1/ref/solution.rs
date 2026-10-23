// D-ROUTE-1 reference (Rust).
use crate::prelude::*;

fn ranks_before(va: f32, ia: usize, vb: f32, ib: usize) -> bool {
    let (na, nb) = (va.is_nan(), vb.is_nan());
    if na || nb {
        return if na == nb { ia < ib } else { nb };
    }
    if va != vb {
        return va > vb;
    }
    ia < ib
}

pub fn topk(sel: &[f32], k: usize, ids: &mut [u32]) {
    let mut taken = vec![false; sel.len()];
    for r in 0..k {
        let mut best: Option<usize> = None;
        for e in 0..sel.len() {
            if taken[e] {
                continue;
            }
            match best {
                None => best = Some(e),
                Some(b) => {
                    if ranks_before(sel[e], e, sel[b], b) {
                        best = Some(e);
                    }
                }
            }
        }
        let b = best.unwrap();
        ids[r] = b as u32;
        taken[b] = true;
    }
}
