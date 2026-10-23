//! D-Q4-1 prelude (read-only; the crate's `prelude` module). Hearth's Q4 weight block and Q8
//! activation, with the same layout and meaning as the Mithril arm's prelude.
#![allow(dead_code)]

/// 64 elements in 34 bytes. `d`: block scale as IEEE binary16 bits. Byte j of `qs`: low nibble =
/// element j, high nibble = element j+32; each nibble stores element + 8.
#[derive(Clone, Copy)]
pub struct BlockQ4 {
    pub d: u16,
    pub qs: [u8; 32],
}

impl BlockQ4 {
    /// Element i (i < 64), in -8..=7.
    pub fn elem(&self, i: usize) -> i32 {
        let byte = self.qs[i % 32];
        let nib = if i < 32 { byte & 15 } else { byte >> 4 };
        nib as i32 - 8
    }
}

#[derive(Clone, Copy)]
pub struct ActQ8 {
    pub d: f32,
    pub sum: i32,
    pub q: [i8; 64],
}

/// Exact binary16 -> f32 widening (subnormals, infinities and NaN included).
pub fn f16_to_f32(h: u16) -> f32 {
    let sign = ((h as u32) & 0x8000) << 16;
    let exp = ((h >> 10) & 0x1f) as u32;
    let man = (h & 0x3ff) as u32;
    let bits = if exp == 0 {
        if man == 0 {
            sign
        } else {
            let mut e: u32 = 127 - 15 + 1;
            let mut m = man;
            while m & 0x400 == 0 {
                m <<= 1;
                e -= 1;
            }
            sign | (e << 23) | ((m & 0x3ff) << 13)
        }
    } else if exp == 0x1f {
        sign | 0x7f80_0000 | (man << 13)
    } else {
        sign | ((exp + 127 - 15) << 23) | (man << 13)
    };
    f32::from_bits(bits)
}

/// The canonical quiet NaN (bits 0x7fc00000) for any NaN input; other values unchanged.
pub fn canon_nan(x: f32) -> f32 {
    if x.is_nan() { f32::from_bits(0x7fc0_0000) } else { x }
}
