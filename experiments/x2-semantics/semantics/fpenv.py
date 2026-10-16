"""The explicit x86 FP-environment layer (TABLE-SCHEMA.md §4).

MXCSR layout (SDM Vol 1 §10.2.3):
  bit 0 IE  invalid           bit 6  DAZ  denormals-are-zeros
  bit 1 DE  denormal operand  bits 7-12  IM DM ZM OM UM PM (exception masks)
  bit 2 ZE  divide-by-zero    bits 13-14 RC (00 nearest-even, 01 down, 10 up, 11 toward zero)
  bit 3 OE  overflow          bit 15 FTZ  flush-to-zero
  bit 4 UE  underflow
  bit 5 PE  precision (inexact)
Power-on / default value 0x1F80: all exceptions masked, RC = nearest-even, DAZ = FTZ = 0, flags clear.

Scope of the model: all six exceptions masked (the masked responses). An unmasked exception raises
#XM, which this model does not represent: constructing an Env from an MXCSR with any mask bit clear
raises UnmodeledEnvironment. Mithril's runtime sets the default MXCSR on entry (ARCHITECTURE §6.3).
Hearth at b5d3f14 neither sets nor checks it (no MXCSR access in engine/src, checked 2026-10-16), so
X2 certifies its kernels under the declared precondition "MXCSR = 0x1F80 at entry" (RULES.md §4.0
DOM-ENV), provisional pending D0-5b. Non-default values exist here for fuzzing and for the `fp_env`
rows of the table.
"""

IE, DE, ZE, OE, UE, PE = 0x01, 0x02, 0x04, 0x08, 0x10, 0x20
FLAG_NAMES = [(IE, "IE"), (DE, "DE"), (ZE, "ZE"), (OE, "OE"), (UE, "UE"), (PE, "PE")]

RC_RNE, RC_RD, RC_RU, RC_RZ = 0, 1, 2, 3
RC_NAMES = {RC_RNE: "RNE", RC_RD: "RD", RC_RU: "RU", RC_RZ: "RZ"}

MXCSR_DEFAULT = 0x1F80
_MASKS_ALL = 0x1F80
_DAZ = 1 << 6
_FTZ = 1 << 15


class UnmodeledEnvironment(Exception):
    pass


def flags_str(f):
    return "|".join(n for b, n in FLAG_NAMES if f & b) or "-"


class Env:
    """Effective FP environment for one instruction execution.

    rc   rounding control actually used (MXCSR.RC, or the EVEX embedded {er} value)
    daz  MXCSR.DAZ;  ftz  MXCSR.FTZ   ({er} does not override these; SDM Vol 2 §2.7 [reading])
    sae  suppress-all-exceptions: flags are not recorded ({sae}, implied by {er})
    """

    __slots__ = ("rc", "daz", "ftz", "sae", "er", "mxcsr")

    def __init__(self, mxcsr=MXCSR_DEFAULT, er=None, sae=False):
        if (mxcsr & _MASKS_ALL) != _MASKS_ALL:
            raise UnmodeledEnvironment("unmasked SIMD FP exceptions are outside the model (#XM)")
        if mxcsr & ~0xFFFF:
            raise UnmodeledEnvironment("reserved MXCSR bits set (#GP on LDMXCSR)")
        self.mxcsr = mxcsr
        self.daz = bool(mxcsr & _DAZ)
        self.ftz = bool(mxcsr & _FTZ)
        if er is not None:
            assert er in RC_NAMES
            self.rc, self.er, self.sae = er, True, True     # {er} implies {sae}
        else:
            self.rc, self.er, self.sae = (mxcsr >> 13) & 3, False, bool(sae)

    @staticmethod
    def make(rc=RC_RNE, daz=False, ftz=False, er=None, sae=False):
        m = _MASKS_ALL | (rc << 13) | (_DAZ if daz else 0) | (_FTZ if ftz else 0)
        return Env(m, er=er, sae=sae)

    def describe(self):
        s = "RC=%s DAZ=%d FTZ=%d" % (RC_NAMES[self.rc], self.daz, self.ftz)
        if self.er:
            s += " {er}"
        elif self.sae:
            s += " {sae}"
        return s

    def mxcsr_after(self, flags):
        """MXCSR value after an instruction raised `flags` (sticky OR; nothing if {sae})."""
        return self.mxcsr if self.sae else (self.mxcsr | (flags & 0x3F))


DEFAULT = Env()
