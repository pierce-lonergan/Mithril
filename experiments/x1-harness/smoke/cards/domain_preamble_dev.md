SHARED DOMAIN NOTES (every arm gets this text; development version)
- Values are IEEE 754 binary32 (f32) unless a brief says otherwise. "Exact" means bit-identical
  output: each arithmetic operation is one correctly rounded IEEE operation (round to nearest,
  ties to even), in exactly the order the brief writes, with no fusing (no FMA) and no
  reassociation.
- -0.0 and +0.0 compare equal but have different bits; output bits are compared, so signs of zero
  matter. NaN compares unequal to everything, itself included. Where a brief says "canonical NaN",
  the bits are 0x7fc00000.
- Integer arithmetic in a brief is exact; the briefs' inputs never overflow the stated types unless
  the brief says what must happen.
- The hidden tests are many more cases of the same meaning (edge cases included); passing the
  visible tests is necessary, not sufficient.
