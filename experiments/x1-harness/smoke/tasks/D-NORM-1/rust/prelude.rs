//! D-NORM-1 prelude (read-only; the crate's `prelude` module): the helper pack's canonical sums,
//! bit-identical to the Mithril std's canon::sum16 and canon::dot16.
#![allow(dead_code)]

/// The canonical 16-lane sum: lane i & 15 accumulates value i in index order (lanes start at
/// +0.0), then the 8, 4, 2, 1 tree; the result is lane 0.
pub fn sum16(a: &[f32]) -> f32 {
    let mut l = [0.0f32; 16];
    for (i, x) in a.iter().enumerate() {
        l[i & 15] += *x;
    }
    for s in [8usize, 4, 2, 1] {
        for j in 0..s {
            l[j] += l[j + s];
        }
    }
    l[0]
}

/// sum16 of the rounded products w[i] * x[i]. Precondition: w.len() == x.len().
pub fn dot16(w: &[f32], x: &[f32]) -> f32 {
    assert_eq!(w.len(), x.len());
    let p: Vec<f32> = w.iter().zip(x.iter()).map(|(a, b)| a * b).collect();
    sum16(&p)
}

/// The canonical quiet NaN (bits 0x7fc00000) for any NaN input; other values unchanged.
pub fn canon_nan(x: f32) -> f32 {
    if x.is_nan() { f32::from_bits(0x7fc0_0000) } else { x }
}
