// MUTANT group_ties_high: groups compared by value only with a non-strict test, so equal scores go to
// the higher group index (and NaN scores are not ranked last). CANARY: expected FAIL.
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

pub fn group_topk(sel: &[f32], n_group: usize, topk_group: usize, k: usize, ids: &mut [u32]) {
    let e_n = sel.len();
    let mut eff: Vec<f32> = sel.to_vec();
    if n_group > 1 {
        let gs = e_n / n_group;
        let mut gsc = vec![0.0f32; n_group];
        let mut keep = vec![false; n_group];
        for g in 0..n_group {
            let v = &sel[g * gs..(g + 1) * gs];
            let mut i1 = 0usize;
            let mut i2: Option<usize> = None;
            for i in 1..gs {
                if ranks_before(v[i], i, v[i1], i1) {
                    i2 = Some(i1);
                    i1 = i;
                } else if i2.map_or(true, |j| ranks_before(v[i], i, v[j], j)) {
                    i2 = Some(i);
                }
            }
            gsc[g] = match i2 {
                Some(j) => v[i1] + v[j],
                None => v[i1],
            };
        }
        for _r in 0..topk_group {
            let mut best: Option<usize> = None;
            for g in 0..n_group {
                if !keep[g] && best.map_or(true, |b| !(gsc[b] > gsc[g])) {
                    best = Some(g);
                }
            }
            keep[best.unwrap()] = true;
        }
        for e in 0..e_n {
            if !keep[e / gs] {
                eff[e] = 0.0;
            }
        }
    }
    let mut taken = vec![false; e_n];
    for r in 0..k {
        let mut best: Option<usize> = None;
        for e in 0..e_n {
            if !taken[e] && best.map_or(true, |b| ranks_before(eff[e], e, eff[b], b)) {
                best = Some(e);
            }
        }
        let b = best.unwrap();
        ids[r] = b as u32;
        taken[b] = true;
    }
}
