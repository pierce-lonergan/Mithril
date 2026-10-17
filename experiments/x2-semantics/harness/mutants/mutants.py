"""Seeded TABLE mutants: the calibration arm of FUZZ-DESIGN.md §6.4 (does the budget find table bugs?).

Each mutant is one textual edit of a copy of `semantics/` (the reference table), applied by exact string
replacement with an anchor that must occur exactly the stated number of times, so a mutant can never be
applied to a table it was not written for. The runner (run_mutants.py) predicts a vector set with the
mutated table (pyref.py) and compares the predictions with UNCHANGED silicon results (compare.py); a mutant
is detected when the comparison differs from the unmutated baseline. Silicon is never re-run.

Adopted 2026-10-16 from the prototype of the x2build review (same family, independent context; finding
R1-10): M01-M10 are the ten §6.4 mutants, M11-M24 the harness-path mutants (zeroing, upper bits, broadcast,
k-destination upper bits, GPR extension, scalar upper lanes, flag-only) and further readings. Stored as
(file, anchor, replacement, count) rather than unified diffs because no `patch` tool is pinned on the
desktop; the effect is the same and the anchor check is stricter.

SEAL: the mutant list is sealed by the sha256 of this file (LF-normalised), printed by `--seal` and written
into every runner report. The X2 record must name that hash before the first native run of the budget
(FUZZ-DESIGN §6.4: "written and sealed before the first native run").

  python -I -B mutants.py --list                    names
  python -I -B mutants.py --seal                    sha256 of this file and of each mutant's edit
  python -I -B mutants.py SRC_SEMANTICS DEST NAME   copy SRC_SEMANTICS to DEST/semantics and apply NAME
"""
import hashlib
import json
import os
import shutil
import sys

MUTANTS = {
    # ---- FUZZ-DESIGN §6.4 calibration list
    "M01_tiny_before_rounding": ("rounding.py", "    if e < -126:", "    if mag < _pow2(-126):", 1),
    "M02_max_returns_src1_on_nan": ("fp_ops.py", "        return b, IE\n", "        return a, IE\n", 1),
    "M03_nan_not_quieted": ("fp_ops.py", "(f32_quiet(a) if f32_is_nan(a) else f32_quiet(b))", "(a if f32_is_nan(a) else b)", 1),
    "M04_cmp_pred_shift": ("fp_ops.py", "CMP_PREDICATES[imm & 31]", "CMP_PREDICATES[(imm + 1) & 31]", 1),
    "M05_indefinite_7fffffff": ("bits.py", "I32_INDEFINITE = 0x80000000", "I32_INDEFINITE = 0x7FFFFFFF", 1),
    "M06_ftz_no_flush_exact": ("rounding.py", "        if ftz:\n", "        if ftz and (mag * (1 << 149)).denominator != 1:\n", 1),
    "M07_daz_applies_to_h2f": ("fp_ops.py", "    v = f16_value(h)\n",
                               "    if env.daz and (h & 0x7C00) == 0:\n        return f32_signed_zero(sign), 0\n    v = f16_value(h)\n", 1),
    "M08_masked_lanes_raise_flags": ("vec.py", "        return (0 if z else dlanes[i]), 0\n",
                                     "        return (0 if z else dlanes[i]), compute()[1]\n", 1),
    "M09_pmaddubsw_swapped": ("int_ops.py", "def pmaddubsw(a, b, vl):", "def pmaddubsw(b, a, vl):", 1),
    "M10_er_disables_daz": ("fpenv.py", "            self.rc, self.er, self.sae = er, True, True     # {er} implies {sae}\n",
                            "            self.rc, self.er, self.sae = er, True, True\n            self.daz = False\n", 1),
    # ---- harness-path mutants: masks, zeroing, upper bits, broadcast, flags, GPR, k destination
    "M11_zeroing_as_merge": ("vec.py", "        return (0 if z else dlanes[i]), 0\n", "        return dlanes[i], 0\n", 1),
    "M12_vex_evex_upper_preserved": ("vec.py", "    assert encoding in (\"vex\", \"evex\")\n    return result & low_mask\n",
                                     "    return (old512 & ~low_mask & ((1 << 512) - 1)) | (result & low_mask)\n", 1),
    "M13_bcast_ignored": ("vec.py", "    B = [bcast_b] * n if bcast_b is not None else lanes32(b, vl)\n    D = lanes32(dst, vl)\n",
                          "    B = lanes32(b, vl)\n    D = lanes32(dst, vl)\n", 1),
    "M14_comis_sets_of": ("table.py", "\"OF\": 0, \"SF\": 0", "\"OF\": 1, \"SF\": 0", 1),
    "M15_cvt2si_sign_extends": ("table.py",
                                "            return r & MASK32, fl                       # 32-bit GPR write zero-extends to 64 bits\n",
                                "            return (r & MASK32) | (0xFFFFFFFF00000000 if r & 0x80000000 else 0), fl\n", 1),
    "M16_kdest_upper_not_zeroed": ("vec.py", "    return res, (0 if env.sae else fl)\n", "    return res | (1 << 31), (0 if env.sae else fl)\n", 1),
    "M17_add_never_pe": ("fp_ops.py", "    r, f = _finish(s < 0, s, env)\n    return r, fl | f\n",
                         "    r, f = _finish(s < 0, s, env)\n    return r, fl | (f & ~PE)\n", 1),
    "M18_legacy_upper_zeroed": ("vec.py", "        return (old512 & ~low_mask & ((1 << 512) - 1)) | (result & low_mask)\n",
                                "        return result & low_mask\n", 1),
    "M19_er_without_sae": ("fpenv.py", "            self.rc, self.er, self.sae = er, True, True     # {er} implies {sae}\n",
                           "            self.rc, self.er, self.sae = er, True, False\n", 1),
    "M20_rd_ru_swapped": ("fpenv.py", "            self.rc, self.er, self.sae = (mxcsr >> 13) & 3, False, bool(sae)\n",
                          "            self.rc, self.er, self.sae = [0, 2, 1, 3][(mxcsr >> 13) & 3], False, bool(sae)\n", 1),
    "M21_i2f_always_rne": ("fp_ops.py", "    return round_f32(v < 0, Fraction(abs(v)), env.rc, False)\n",
                           "    return round_f32(v < 0, Fraction(abs(v)), 0, False)\n", 1),
    "M22_scalar_upper_from_src2": ("vec.py", "    return pack([r] + S1[1:], 32), (0 if env.sae else f)\n",
                                   "    return pack([r] + lanes32(src2_low, 128)[1:], 32), (0 if env.sae else f)\n", 1),
    "M23_vpdpbusd_saturates": ("table.py", "int_ops.masked(f(acc, src1, src2, vl, saturate=sat), acc, k, z, vl, eb)",
                               "int_ops.masked(f(acc, src1, src2, vl, saturate=True), acc, k, z, vl, eb)", 1),
    "M24_daz_raises_de": ("fp_ops.py", "            return b & F32_SIGN, 0\n", "            return b & F32_SIGN, DE\n", 1),
}

# Which mutants FUZZ-DESIGN §6.4 names (the calibration target is 100% of these on the frozen budget's
# silicon results); the others are additional harness-path checks reported with them.
DESIGN_LIST = [n for n in MUTANTS if n[:3] in ("M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08", "M09", "M10")]


def seal():
    with open(os.path.abspath(__file__), "rb") as f:
        spec_sha = hashlib.sha256(f.read().replace(b"\r\n", b"\n")).hexdigest()
    per = {n: hashlib.sha256(json.dumps(MUTANTS[n], sort_keys=True).encode()).hexdigest() for n in MUTANTS}
    return {"spec_sha256": spec_sha, "n_mutants": len(MUTANTS), "design_list": DESIGN_LIST, "mutant_sha256": per}


def apply(src, dest, name):
    """Copy the semantics directory SRC to DEST/semantics and apply mutant NAME. Raises on an anchor miss."""
    f, old, new, cnt = MUTANTS[name]
    d = os.path.join(dest, "semantics")
    if os.path.exists(d):
        shutil.rmtree(d)
    shutil.copytree(src, d, ignore=shutil.ignore_patterns("__pycache__"))
    p = os.path.join(d, f)
    with open(p, encoding="utf-8", newline="") as fh:
        t = fh.read()
    crlf = "\r\n" in t
    if crlf:
        t = t.replace("\r\n", "\n")
    got = t.count(old)
    if got != cnt:
        raise SystemExit("ANCHOR %s: found %d occurrences in %s, want %d" % (name, got, f, cnt))
    t = t.replace(old, new)
    if crlf:
        t = t.replace("\n", "\r\n")
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write(t)
    return f


def main(argv):
    if argv[:1] == ["--list"]:
        print(" ".join(MUTANTS))
        return 0
    if argv[:1] == ["--seal"]:
        print(json.dumps(seal(), indent=1))
        return 0
    src, dest, name = argv[:3]
    f = apply(src, dest, name)
    print("MUTANT %s applied to %s" % (name, f))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
