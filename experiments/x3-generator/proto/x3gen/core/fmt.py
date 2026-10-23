"""Generic block-format descriptions (library L).

A format is a fixed-size C struct holding one scale and a run of integer codes. Nothing here knows
any particular engine: sizes, offsets, code widths and value offsets all come from the meaning file
that instantiates these classes.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass(frozen=True)
class Scalar:
    """One scalar field: kind is 'f16' (stored as u16 bits), 'f32' or 'i32'."""

    kind: str
    offset: int

    @property
    def nbytes(self) -> int:
        return {"f16": 2, "f32": 4, "i32": 4}[self.kind]


@dataclass(frozen=True)
class Codes:
    """count integer codes packed into bytes starting at offset.

    bits == 8: element i is byte i, read as signed (signed=True) or unsigned.
    bits == 4: element i sits in byte (i % hi_at) at bit shift 4 * (i // hi_at).
    The integer value of element i is code(i) - value_offset (codes stored with an offset).
    value_range is a declared precondition on the values (None means the full storage range).
    """

    offset: int
    count: int
    bits: int
    signed: bool = False
    value_offset: int = 0
    hi_at: int = 0
    value_range: Optional[Tuple[int, int]] = None

    @property
    def nbytes(self) -> int:
        return self.count * self.bits // 8

    def locate(self, i: int) -> Tuple[int, int]:
        """(byte index within the code run, bit shift) of element i."""
        if self.bits == 8:
            return i, 0
        return i % self.hi_at, (self.bits * (i // self.hi_at))

    @property
    def mask(self) -> int:
        return (1 << self.bits) - 1

    def storage_range(self) -> Tuple[int, int]:
        if self.bits == 8 and self.signed:
            return -128, 127
        return 0, self.mask

    def value_bounds(self) -> Tuple[int, int]:
        if self.value_range is not None:
            return self.value_range
        lo, hi = self.storage_range()
        return lo - self.value_offset, hi - self.value_offset

    def value_of_byte(self, b: int, shift: int) -> int:
        """Element value from the raw storage byte b (0..255) holding it at bit shift."""
        if self.bits == 8:
            v = b - 256 if (self.signed and b >= 128) else b
            return v - self.value_offset
        return ((b >> shift) & self.mask) - self.value_offset


@dataclass(frozen=True)
class Format:
    """A block format: C struct name, size in bytes, and named fields."""

    ctype: str
    size: int
    d: Scalar
    q: Codes
    sum: Optional[Scalar] = None
    tag: str = ""

    def __post_init__(self):
        end = max(self.d.offset + self.d.nbytes, self.q.offset + self.q.nbytes)
        if self.sum is not None:
            end = max(end, self.sum.offset + self.sum.nbytes)
        if end > self.size:
            raise ValueError("format fields overflow the declared size")

    def field_at(self, off: int):
        """Name of the field covering byte off of a block, and the byte index inside it."""
        for name in ("d", "sum"):
            f = getattr(self, name)
            if f is not None and f.offset <= off < f.offset + f.nbytes:
                return name, off - f.offset
        if self.q.offset <= off < self.q.offset + self.q.nbytes:
            return "q", off - self.q.offset
        return None, None


def fmt_scalar(kind: str, offset: int) -> Scalar:
    return Scalar(kind, offset)


@dataclass
class SlotSig:
    """The C function slot a kernel fills: parameter names and C types, the header that declares
    the types, and the name pattern of the generated functions."""

    typedef: str
    header: str
    params: Tuple[Tuple[str, str], ...]
    name_pattern: str
    simd_guard: str = ""
    extra_includes: Tuple[str, ...] = field(default_factory=tuple)
