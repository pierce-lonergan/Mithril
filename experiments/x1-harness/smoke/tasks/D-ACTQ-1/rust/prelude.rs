//! D-ACTQ-1 prelude (read-only; the crate's `prelude` module). Hearth's Q8 activation block, with
//! the same layout and meaning as the Mithril arm's prelude.
#![allow(dead_code)]

#[derive(Clone, Copy)]
pub struct ActQ8 {
    pub d: f32,
    pub sum: i32,
    pub q: [i8; 64],
}

/// The canonical quiet NaN (bits 0x7fc00000) for any NaN input; other values unchanged.
pub fn canon_nan(x: f32) -> f32 {
    if x.is_nan() { f32::from_bits(0x7fc0_0000) } else { x }
}
