"""Instruction-table entries (instruction library I).

Each entry names exactly one intrinsic or C operator (the only multi-operation entry is the named
exception scalar.h2f_bits, DESIGN 5.1). An entry records:
  c      C spelling, with {0}, {1}, ... for arguments
  ret    C type of the result (None for a statement)
  cls    'fp' (IEEE arithmetic or conversion), 'fpcmp', 'sel', 'int', 'bit', 'move', 'const',
         'load', 'store', 'hint'
  ieee   for P12 (map_fp): the meaning op the entry realises lane-wise, else None
  sem    (name, params...) of the semantic function in core/sem.py used by the checker
  ext    the CPUID feature the entry needs
"""

from dataclasses import dataclass
from typing import Optional

TABLE = {}


@dataclass(frozen=True)
class Entry:
    key: str
    c: str
    ret: Optional[str]
    cls: str
    sem: tuple
    ieee: Optional[str] = None
    ext: str = ""
    validated: str = "pending (DESIGN 5.4, desktop)"


def entry(key, c, ret, cls, sem, ieee=None, ext=""):
    if key in TABLE:
        raise ValueError("duplicate isa entry " + key)
    TABLE[key] = Entry(key, c, ret, cls, sem, ieee, ext)
    return TABLE[key]


def call_c(e: Entry, args) -> str:
    return e.c.format(*args)


PFX = {128: "_mm_", 256: "_mm256_", 512: "_mm512_"}
FT = {128: "__m128", 256: "__m256", 512: "__m512"}
IT = {128: "__m128i", 256: "__m256i", 512: "__m512i"}
SI = {128: "si128", 256: "si256", 512: "si512"}


def name(width: int, stem: str) -> str:
    """Intrinsic name for a width, e.g. name(256, 'add_ps') == '_mm256_add_ps'."""
    return PFX[width] + stem
