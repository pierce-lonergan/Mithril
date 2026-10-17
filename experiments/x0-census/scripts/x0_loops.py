#!/usr/bin/env python3
"""x0_loops.py -- X0 record §4.7 (loops, accumulators, unroll factors, tags), P3(c) and the canaries P3(d1) and
P3(d2), over the counted sets written by x0_decode.py. Standard library only; Python >= 3.8. Run with python -I.

Usage:
  python -I x0_loops.py DECODE_OUTDIR --manifest MANIFEST.json -o LOOPS.json
         [--loop-table ../class/loop_table.csv] [--fp-class ../class/fp_class.csv]
         [--variant-map hearth|NAME=LOOPVARIANT,...] [--canary-variant TABLE:SLOT[,TABLE:SLOT]]
         [--attribution ATTR.json]

Definitions (record §4.7), per dispatched variant:
  * CFG: the variant's reachable instructions and the intra-procedural edges x0_decode.py recorded (fall-through,
    direct jumps, jump-table targets, tail calls). Every closure function entry (the slot entry and every
    internal or interposable call target) is a root; dominators are computed from each root
    (Cooper-Harvey-Kennedy). A natural loop is a back edge t->h with h dominating t; loops sharing a header merge.
  * Registers: XMMn/YMMn/ZMMn are one register Vn; GPR sub-registers map to the 64-bit name; flags are ignored.
    A memory operand [RSP+d] or [RBP+d] with no index register is a stack slot treated as a register.
  * Loop-carried FP accumulator: a register live into the header along the loop (liveness restricted to the
    loop body) that the body redefines with an FP-sensitive instruction of op_class ADD, SUB, MUL, MAX or MIN
    (FMA-class counts as ADD) reading a loop-carried value.
  * acc_lanes_emitted (the unit of P3(c)): the number of independent FP partial results carried across the back
    edge = the sum over DISTINCT accumulator registers of the widest lane count of their defining instructions
    (scalar 1; f32 in xmm/ymm/zmm 4/8/16; f64 half that; masked forms full width). This is the same unit as the
    loop table's source_lanes ("independent FP partial results carried across iterations").
    acc_updates_per_iter: the sum over defining INSTRUCTIONS of their lane counts (an unrolled serial chain
    updates the same register several times per iteration); it gives u_acc.
  * u_acc = acc_updates_per_iter / source_lanes (attributed loop); u_ind = the largest constant per-iteration
    increment of a GPR induction variable / the source loop's bytes_per_iter (when a single number).
  * Tags computed: lockstep, unrolled-u (u > 1), rotated (latch ends in a conditional branch to the header and a
    pre-header conditional branch guards the loop), software-pipelined (a loop-carried value defined in the body
    by a load), auto-vectorised (packed FP arithmetic in a loop of a scalar-table variant), spilled (vector stores
    and reloads of stack slots inside the body). NOT computed mechanically: peeled, interchanged; when a loop has
    no FP accumulator and no computed tag it is tagged lockstep with fp_free = true.
  * Attribution: from ATTR.json (address -> source file:line, produced from the debug-info twin when its code
    sections and relocations are identical, record §4.6). Without it every loop is unattributed and P3(c) uses
    the variant-wide bound: the largest source_lanes among the variant's loops in loop_table.csv.
  * P3(c): a loop is flagged if acc_lanes_emitted exceeds the bound.
  * P3(d1): in the closure of each canary variant, an FP ADD with a constant operand whose every 32-bit lane is
    M = 0x4B400000, followed by an FP SUB of M (or ADD of -M = 0xCB400000) that reads the ADD's result through
    register moves only. Constants come from relocated memory operands (bytes read from the object) or from
    GPR immediates moved into vector registers. Missing pair -> "fail" (the variant is flagged). A canary variant
    without decoded instructions keeps d1 = "not_evaluated", which judge.py also flags (anything but "pass"); a
    --canary-variant key that matches no variant makes this script exit 1.
  * P3(d2): tree16 sites are checked by the lane-provenance tracker (track_tree16) only when the attribution is
    exact; otherwise the site is "unchecked" (reported, not flagged; record §9).
"""
import argparse
import collections
import csv
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
M_BITS, NEG_M_BITS = 0x4B400000, 0xCB400000
ACC_OPS = {"ADD", "SUB", "MUL", "MAX", "MIN"}
FMA_RE = re.compile(r"^V?F(N)?M(ADD|SUB)(SUB|ADD)?(132|213|231)?(PS|PD|SS|SD)$")
MOVE_RE = re.compile(r"^V?MOV(APS|UPS|APD|UPD|SS|SD_XMM|DQA|DQU|DQA32|DQA64|DQU8|DQU16|DQU32|DQU64)$")
GPR64 = {}
for base, names in {"RAX": "EAX AX AL AH", "RBX": "EBX BX BL BH", "RCX": "ECX CX CL CH", "RDX": "EDX DX DL DH",
                    "RSI": "ESI SI SIL", "RDI": "EDI DI DIL", "RBP": "EBP BP BPL", "RSP": "ESP SP SPL"}.items():
    GPR64[base] = base
    for n in names.split():
        GPR64[n] = base
for i in range(8, 16):
    for suf in ("", "D", "W", "B"):
        GPR64["R%d%s" % (i, suf)] = "R%d" % i
VARIANT_HEARTH = {"hx_kernels_scalar": "scalar", "k_avx2": "avx2", "k_avx512": "avx512"}
SLOT_HEARTH = {"matmul[F32]": "F32", "matmul[F16]": "F16", "matmul[BF16]": "BF16", "matmul[Q8]": "Q8",
               "matmul[Q4]": "Q4", "act_quantize_q8": "act"}


def norm_reg(r):
    if not r or r in ("INVALID", "RIP", "RFLAGS", "EFLAGS", "FLAGS", "MXCSR", "STACKPUSH", "STACKPOP"):
        return None
    m = re.match(r"^[XYZ]MM(\d+)$", r)
    if m:
        return "V" + m.group(1)
    return GPR64.get(r, r)


def disp_value(v):
    if v is None:
        return 0
    try:
        x = int(str(v), 16) if str(v).lower().startswith(("0x", "-0x")) else int(str(v), 0)
    except ValueError:
        x = int(str(v), 16)
    return x - (1 << 64) if x >= (1 << 63) else x


def parse_mem(txt):
    """XED's MEM0/AGEN field text, e.g. 'ptr [RSP+0xc8]' or 'ptr [RCX+RAX*4-0x10]' -> (base, index, disp)."""
    m = re.search(r"\[(.*?)\]", txt or "")
    base = index = None
    disp = 0
    if m:
        for sign, term in re.findall(r"([+-]?)([^+-]+)", m.group(1)):
            t = term.strip()
            if re.match(r"^(0x[0-9a-fA-F]+|\d+)$", t):
                disp += (-1 if sign == "-" else 1) * int(t, 0)
            elif "*" in t:
                index = t.split("*")[0]
            elif base is None:
                base = t
            else:
                index = t
    return base, index, disp


def operands(ins):
    """[(kind, name, action)] with kind reg|mem; name is the normalised register or the stack-slot key."""
    f, out = ins.get("fields", {}), []
    for op in ins.get("operands", []):
        p = op.split("/")
        nm, act = p[0], (p[1] if len(p) > 1 else "")
        if nm.startswith("REG"):
            r = norm_reg(f.get(nm))
            if r:
                out.append(("reg", r, act))
        elif nm.startswith(("MEM", "AGEN")):
            base, idx, disp = parse_mem(f.get(nm) or f.get("AGEN") or "")
            nb, ni = norm_reg(base), norm_reg(idx)
            if nm.startswith("MEM"):
                if nb in ("RSP", "RBP") and not ni:
                    out.append(("mem", "STK:%s:%d" % (nb, disp), act))
                else:
                    out.append(("mem", None, act))
            for r in (nb, ni):
                if r:
                    out.append(("reg", r, "R"))
    return out


def uses_defs(ins):
    """Register (and stack-slot) uses and defs. Conditional writes (CW, RCW: merge masking) also use the old
    value, so they count as uses."""
    u, d = set(), set()
    for kind, name, act in operands(ins):
        if name is None:
            continue
        if "R" in act or act == "CW":
            u.add(name)
        if "W" in act:
            d.add(name)
    return u, d


def dest_register(ins):
    f = ins.get("fields", {})
    for p in ins.get("operands", []):
        q = p.split("/")
        if q[0].startswith("REG") and len(q) > 1 and "W" in q[1]:
            r = f.get(q[0]) or ""
            if re.match(r"^[XYZ]MM\d+$", r):
                return r
    return ""


def op_class_of(ic):
    b = ic[1:] if ic.startswith("V") else ic
    m = re.match(r"^(ADD|SUB|MUL|DIV|SQRT|MIN|MAX)(PS|SS|PD|SD)$", b)
    if m:
        return m.group(1), m.group(2)
    if FMA_RE.match(ic):
        return "ADD", ic[-2:]
    return None, None


def lanes_of(ins):
    op, sfx = op_class_of(ins.get("iclass", ""))
    if op is None:
        return 0
    if sfx in ("SS", "SD"):
        return 1
    dst = dest_register(ins)
    width = 16 if dst.startswith("ZMM") else 8 if dst.startswith("YMM") else 4
    return width if sfx == "PS" else width // 2


SCALAR_UNARY_RE = re.compile(r"^V?(CVTSI2S[SD]|CVTUSI2S[SD]|CVTSS2SD|CVTSD2SS|CVTSH2S[SD]|CVTS[SD]2SH|SQRTS[SD]|RCPSS|"
                             r"RSQRTSS|RCP14S[SD]|RSQRT14S[SD]|ROUNDS[SD]|RNDSCALES[SD]|GETEXPS[SD]|GETMANTS[SD]|"
                             r"MOVSS|MOVSD_XMM)$")


def lane0_uses(ins):
    """Locations whose value can reach the result's lane 0 (for packed ops: all uses). For scalar unary and
    insert-style ops (VCVTSI2SS xmm_d, xmm_pass, r32; legacy CVTSI2SS xmm_d, r32; MOVSS reg, reg ...), the
    pass-through register only supplies the upper lanes, so only the LAST source counts."""
    ic = ins.get("iclass", "")
    if SCALAR_UNARY_RE.match(ic):
        srcs = [(k, n) for k, n, a in operands(ins) if n is not None and "R" in a and not (k == "reg" and n.startswith("K"))]
        explicit = [x for x in srcs]
        return {explicit[-1][1]} if explicit else set()
    return uses_defs(ins)[0]


def full_kills(ins):
    """Locations whose old value is entirely replaced (W or RW; merge-masked RCW/CW writes keep old lanes)."""
    return {n for k, n, a in operands(ins) if n is not None and a in ("W", "RW")}


def is_move(ins):
    """A pure register/stack copy (no arithmetic): the move iclasses of the d2 whitelist and plain MOV."""
    return bool(MOVE_RE.match(ins.get("iclass", ""))) or ins.get("iclass") in ("MOV", "VMOVQ", "MOVQ")


# ------------------------------------------------------------------------------------------------ CFG
def dominators(root, succ):
    order, seen, stack = [], set(), [(root, iter(succ.get(root, [])))]
    seen.add(root)
    while stack:
        n, it = stack[-1]
        for s in it:
            if s not in seen:
                seen.add(s)
                stack.append((s, iter(succ.get(s, []))))
                break
        else:
            order.append(n)
            stack.pop()
    rpo = list(reversed(order))
    idx = {n: i for i, n in enumerate(rpo)}
    preds = collections.defaultdict(list)
    for n in rpo:
        for s in succ.get(n, []):
            if s in idx:
                preds[s].append(n)
    idom = {root: root}
    changed = True
    while changed:
        changed = False
        for n in rpo[1:]:
            ps = [p for p in preds[n] if p in idom]
            if not ps:
                continue
            new = ps[0]
            for p in ps[1:]:
                a, b = p, new
                while a != b:
                    while idx[a] > idx[b]:
                        a = idom[a]
                    while idx[b] > idx[a]:
                        b = idom[b]
                new = a
            if idom.get(n) != new:
                idom[n] = new
                changed = True
    return idom, rpo, preds


def dominates(idom, h, t):
    while True:
        if t == h:
            return True
        if idom.get(t, t) == t:
            return False
        t = idom[t]


def natural_loops(root, succ):
    idom, rpo, preds = dominators(root, succ)
    loops = collections.OrderedDict()
    for t in rpo:
        for h in succ.get(t, []):
            if h in idom and dominates(idom, h, t):
                body = loops.setdefault(h, {"header": h, "latches": [], "body": {h}})
                body["latches"].append(t)
                stack = [t]
                while stack:
                    n = stack.pop()
                    if n not in body["body"]:
                        body["body"].add(n)
                        stack.extend(preds[n])
    return list(loops.values()), preds


# ------------------------------------------------------------------------------------------------ analysis
def analyse_loop(lp, insts, succ, preds):
    body = lp["body"]
    ud = {n: uses_defs(insts[n]) for n in body}
    live_in = {n: set() for n in body}
    changed = True
    while changed:
        changed = False
        for n in body:
            out = set()
            for s in succ.get(n, []):
                if s in body:
                    out |= live_in[s]
            new = ud[n][0] | (out - ud[n][1])
            if new != live_in[n]:
                live_in[n], changed = new, True
    defs_in = set().union(*[ud[n][1] for n in body]) if body else set()
    hdr = lp["header"]
    carried = live_in[hdr] & defs_in
    # Flow-sensitive within one iteration (back edges into the header cut):
    #   UE[n] = locations that may still hold a value carried in from the previous iteration at n's entry
    #   AV[n] = locations that may hold a value an accumulation op computed earlier in this iteration
    # Moves copy both properties; other writes kill them, except merge-masked (RCW/CW) writes.
    order = sorted(body, key=lambda n: (n != hdr, n))
    ue_in = {n: set() for n in body}
    av_in = {n: set() for n in body}
    ue_out, av_out = {}, {}
    acc_value = {}
    for _ in range(len(body) + 2):
        changed = False
        for n in order:
            if n == hdr:
                ue, av = set(carried), set()
            else:
                ue, av = set(), set()
                for p in preds.get(n, []):
                    if p in body:
                        ue |= ue_out.get(p, set())
                        av |= av_out.get(p, set())
            ue_in[n], av_in[n] = ue, av
            ins = insts[n]
            u0 = lane0_uses(ins)
            kills = full_kills(ins)
            d = ud[n][1]
            op, _ = op_class_of(ins.get("iclass", ""))
            if is_move(ins) and (u0 & ue):
                nue = (ue - d) | d
            else:
                nue = ue - kills
            if op in ACC_OPS and (u0 & (ue | av)):
                nav = (av - kills) | d
                for r in d:
                    acc_value[r] = max(acc_value.get(r, 0), lanes_of(ins))
            elif is_move(ins) and (u0 & av):
                nav = (av - d) | d
            else:
                nav = av - kills
            if ue_out.get(n) != nue or av_out.get(n) != nav:
                ue_out[n], av_out[n], changed = nue, nav, True
        if not changed:
            break
    acc_regs, updates, fp_ops = {}, 0, []
    for n in sorted(body):
        ins = insts[n]
        ic = ins.get("iclass", "")
        op, _ = op_class_of(ic)
        u0, d = lane0_uses(ins), ud[n][1]
        if op in ACC_OPS and (u0 & (ue_in[n] | av_in[n])):
            ln = lanes_of(ins)
            for r in d & carried:
                acc_regs[r] = max(acc_regs.get(r, 0), ln)
            updates += ln
            fp_ops.append(ic)
        elif is_move(ins) and d & carried and (u0 & av_in[n]):
            # a carried location written by a pure copy of an accumulated value (spilled accumulator)
            for r in d & carried:
                acc_regs[r] = max(acc_regs.get(r, 0), max([acc_value.get(x, 0) for x in u0] or [0]))
    if not acc_regs:
        updates, fp_ops = 0, []
    lanes = sum(acc_regs.values())
    # inductions: GPR redefined by ADD/SUB/LEA/INC with a constant
    inc = {}
    for n in body:
        ins = insts[n]
        ic, f = ins.get("iclass", ""), ins.get("fields", {})
        u, d = ud[n]
        gd = [r for r in d if r.startswith("R")]
        if ic in ("ADD", "SUB", "INC", "DEC", "LEA") and len(gd) == 1 and gd[0] in carried:
            k = disp_value(f.get("UIMM0") or f.get("SIMM0") or f.get("IMM0") or f.get("DISP") or 0)
            if ic == "INC":
                k = 1
            if ic in ("SUB", "DEC"):
                k = -k if ic == "SUB" else -1
            inc[gd[0]] = inc.get(gd[0], 0) + k
    # tags
    tags = []
    pipelined = [r for r in carried if any(r in ud[n][1] and insts[n].get("iclass", "").startswith(("MOV", "VMOV"))
                                           and any(k == "mem" and "R" in a for k, _, a in operands(insts[n]))
                                           for n in body)]
    if pipelined:
        tags.append("software-pipelined")
    vstk = [n for n in body if any(k == "mem" and nm and nm.startswith("STK") for k, nm, a in operands(insts[n]))
            and any(r.startswith("V") for r in (ud[n][0] | ud[n][1]))]
    if any(any(k == "mem" and nm and "W" in a for k, nm, a in operands(insts[n])) for n in vstk) and \
            any(any(k == "mem" and nm and "R" in a for k, nm, a in operands(insts[n])) for n in vstk):
        tags.append("spilled")
    hdr = lp["header"]
    latch_cond = all(insts[t].get("iclass", "").startswith("J") and insts[t].get("iclass") != "JMP" and
                     hdr in succ.get(t, []) for t in lp["latches"])
    guard = any(insts[p].get("iclass", "").startswith("J") and insts[p].get("iclass") != "JMP"
                for p in preds.get(hdr, []) if p not in body) or \
        any(insts[q].get("iclass", "").startswith("J") and insts[q].get("iclass") != "JMP"
            for p in preds.get(hdr, []) if p not in body for q in preds.get(p, []) if q not in body)
    if latch_cond and guard:
        tags.append("rotated")
    packed = any(lanes_of(insts[n]) > 1 for n in body)
    return {"header": list(hdr), "n_instructions": len(body), "latches": [list(t) for t in lp["latches"]],
            "carried_registers": sorted(carried), "accumulators": dict(sorted(acc_regs.items())),
            "acc_lanes_emitted": lanes, "acc_updates_per_iter": updates, "fp_accumulator_ops": sorted(set(fp_ops)),
            "inductions": dict(sorted(inc.items())), "tags": tags, "packed_fp": packed,
            "spills": sum(1 for n in vstk if any(k == "mem" and "W" in a for k, nm, a in operands(insts[n]))),
            "reloads": sum(1 for n in vstk if any(k == "mem" and "R" in a for k, nm, a in operands(insts[n])))}


# ------------------------------------------------------------------------------------------------ canary d1
class ConstReader:
    def __init__(self, man_obj):
        self.o = man_obj
        self.data = open(man_obj["object"], "rb").read()
        self.secs = {s["index"]: s for s in man_obj["sections"]}
        self.rel = {int(k): {r["offset"]: r for r in v} for k, v in man_obj["relocs"].items()}

    def mem_words(self, sec, off, ins, nbytes):
        """32-bit words of the constant a RIP-relative memory operand of instruction (sec, off) reads."""
        end = off + ins["len"]
        for p in range(off, end - 3):
            r = self.rel.get(sec, {}).get(p)
            if r and r.get("defined"):
                s = self.secs[r["target_section"]]
                if s["is_code"]:
                    return None
                is_coff = self.o["format"].startswith("coff")
                tgt = r["sym_value"] + r["addend"] + (0 if is_coff else (end - p))
                if is_coff and r["type"].startswith("REL32"):
                    k = int(r["type"][6:]) if r["type"] != "REL32" else 0
                    tgt = r["sym_value"] + r["addend"] + (end - p - 4 - k)
                raw = self.data[s["file_offset"] + tgt: s["file_offset"] + tgt + nbytes]
                if len(raw) < 4:
                    return None
                return list(struct.unpack("<%dI" % (len(raw) // 4), raw[:len(raw) // 4 * 4]))
        return None


def canary_d1(insts_sorted, cr):
    """Return 'pass' if the (v + M) - M pair is present in the closure (record P3(d1)), else 'fail'."""
    tag = {}        # register -> ("const", value_set) | ("plusM", id)
    found = []
    for (sec, off), ins in insts_sorted:
        ic = ins.get("iclass", "")
        f = ins.get("fields", {})
        regs = [(f.get(p.split("/")[0]), p.split("/")[1] if len(p.split("/")) > 1 else "")
                for p in ins.get("operands", []) if p.startswith("REG")]
        regs = [(r, a) for r, a in regs if r and not r.startswith("K") and norm_reg(r)]
        dst = [norm_reg(r) for r, a in regs if "W" in a]
        if ic.startswith("V"):
            # VEX/EVEX: the destination is not a source (a merge-masked RCW destination is skipped too)
            srcs = [norm_reg(r) for r, a in regs if "R" in a and "W" not in a]
        else:
            srcs = [norm_reg(r) for r, a in regs if "R" in a]          # legacy SSE: dest is the first source
        memw = None
        if any(p.startswith("MEM") for p in ins.get("operands", [])):
            d0 = dest_register(ins)
            nb = 4 if (ic.endswith(("SS", "D")) or "BCAST" in f) else 64 if d0.startswith("ZMM") else \
                32 if d0.startswith("YMM") else 16
            memw = cr.mem_words(sec, off, ins, nb)
        if ic == "MOV" and dst and ("UIMM0" in f or "IMM0" in f):
            tag[dst[0]] = ("const", {disp_value(f.get("UIMM0") or f.get("IMM0")) & 0xFFFFFFFF})
            continue
        if ic in ("MOVD", "VMOVD", "VPBROADCASTD", "VBROADCASTSS") and dst:
            src = [s for s in srcs if s != dst[0]]
            if memw:
                tag[dst[0]] = ("const", set(memw[:1]))
            elif src and tag.get(src[0], ("",))[0] == "const":
                tag[dst[0]] = tag[src[0]]
            else:
                tag.pop(dst[0], None)
            continue
        if MOVE_RE.match(ic) and dst:
            src = [s for s in srcs if s != dst[0]]
            if memw:
                tag[dst[0]] = ("const", set(memw))
            elif src and src[0] in tag:
                tag[dst[0]] = tag[src[0]]
            else:
                tag.pop(dst[0], None)
            continue
        op, sfx = op_class_of(ic)
        if op in ("ADD", "SUB") and sfx in ("SS", "PS") and dst:
            vals = []
            for s in srcs:
                vals.append(tag.get(s))
            if memw:
                vals.append(("const", set(memw)))
            consts = [v for v in vals if v and v[0] == "const"]
            plus = [v for v in vals if v and v[0] == "plusM"]
            if op == "ADD" and plus and any(c[1] == {NEG_M_BITS} for c in consts):
                found.append([sec, off])
            if op == "SUB" and plus and any(c[1] == {M_BITS} for c in consts):
                # the plusM value must be the minuend: first source operand (VEX REG1, legacy dest/src REG0)
                first = tag.get(srcs[0]) if srcs else None
                if first and first[0] == "plusM":
                    found.append([sec, off])
            if op == "ADD" and any(c[1] == {M_BITS} for c in consts):
                for r in dst:
                    tag[r] = ("plusM", (sec, off))
                continue
        for r in dst:
            tag.pop(r, None)
    return ("pass" if found else "fail"), found


# ------------------------------------------------------------------------------------------------ canary d2
def _canon(e):
    if isinstance(e, tuple) and e and e[0] == "add":
        a, b = sorted([_canon(e[1]), _canon(e[2])])
        return "(%s+%s)" % (a, b)
    return str(e)


def expected_tree16():
    L = ["L%d" % k for k in range(16)]
    for s in (8, 4, 2, 1):
        for j in range(s):
            L[j] = ("add", L[j], L[j + s])
    return _canon(L[0])


def track_tree16(seq, acc_regs):
    """Lane-provenance tracker (record P3(d2)). seq: list of (iclass, dst, srcs, imm) with registers already
    normalised to V<n>/STK keys; acc_regs: [reg] (one 16-lane register, or two 8-lane registers lo, hi).
    Returns 'match', 'mismatch' or 'unchecked' (an instruction outside the whitelist)."""
    st = {}
    if len(acc_regs) == 1:
        st[acc_regs[0]] = ["L%d" % k for k in range(16)]
    else:
        st[acc_regs[0]] = ["L%d" % k for k in range(8)]
        st[acc_regs[1]] = ["L%d" % k for k in range(8, 16)]
    last = None
    for ic, dst, srcs, imm in seq:
        g = [st.get(s) for s in srcs]
        if any(x is None for x in g):
            return "unchecked"
        if ic in ("VADDPS", "ADDPS"):
            a, b = (g[0], g[1]) if len(g) > 1 else (st.get(dst), g[0])
            n = min(len(a), len(b))
            st[dst] = [("add", a[i], b[i]) for i in range(n)]
        elif ic in ("VADDSS", "ADDSS"):
            a, b = (g[0], g[1]) if len(g) > 1 else (st.get(dst), g[0])
            st[dst] = [("add", a[0], b[0])] + list(a[1:4])
        elif ic in ("VEXTRACTF128", "VEXTRACTF32X4"):
            st[dst] = g[0][4 * imm: 4 * imm + 4]
        elif ic in ("VEXTRACTF64X4", "VEXTRACTF32X8"):
            st[dst] = g[0][8 * imm: 8 * imm + 8]
        elif ic in ("VMOVHLPS", "MOVHLPS"):
            a, b = (g[0], g[1]) if len(g) > 1 else (st.get(dst), g[0])
            st[dst] = [b[2], b[3], a[2], a[3]]
        elif ic in ("VMOVSHDUP", "MOVSHDUP"):
            v = g[0]
            st[dst] = [x for k in range(0, len(v), 2) for x in (v[k + 1], v[k + 1])]
        elif ic in ("VSHUFPS", "SHUFPS"):
            a, b = (g[0], g[1]) if len(g) > 1 else (st.get(dst), g[0])
            out = []
            for base in range(0, len(a), 4):
                out += [a[base + (imm & 3)], a[base + ((imm >> 2) & 3)], b[base + ((imm >> 4) & 3)], b[base + ((imm >> 6) & 3)]]
            st[dst] = out
        elif ic == "VPERMILPS":
            v = g[0]
            st[dst] = [v[base + ((imm >> (2 * i)) & 3)] for base in range(0, len(v), 4) for i in range(4)]
        elif ic in ("VUNPCKHPD", "UNPCKHPD"):
            a, b = (g[0], g[1]) if len(g) > 1 else (st.get(dst), g[0])
            st[dst] = [a[2], a[3], b[2], b[3]]
        elif ic in ("VPERMQ", "VPERMPD"):
            v = g[0]
            st[dst] = [v[2 * ((imm >> (2 * i)) & 3) + k] for i in range(4) for k in range(2)]
        elif ic in ("VSHUFF32X4", "VSHUFF64X2"):
            a, b = g[0], g[1]
            n = len(a) // 4
            sel = [(a, imm & 3), (a, (imm >> 2) & 3), (b, (imm >> 4) & 3), (b, (imm >> 6) & 3)][: max(2, len(a) // 4)]
            st[dst] = [x for v, q in sel for x in v[4 * q: 4 * q + 4]]
        elif MOVE_RE.match(ic) or ic in ("SPILL", "RELOAD", "COPY"):
            st[dst] = list(g[0])
        else:
            return "unchecked"
        last = dst
    if last is None:
        return "unchecked"
    return "match" if _canon(st[last][0]) == expected_tree16() else "mismatch"


# ------------------------------------------------------------------------------------------------ main
def load_loop_table(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    by_var = collections.defaultdict(list)
    for r in rows:
        for v in r["variants"].split("|"):
            by_var[v].append(r)
    return rows, by_var


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("decode_dir")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--loop-table", default=os.path.join(HERE, "..", "class", "loop_table.csv"))
    ap.add_argument("--variant-map", default="hearth",
                    help="'hearth', or TABLE:SLOT=LOOPVARIANT pairs separated by commas")
    ap.add_argument("--canary-variant", default="hx_kernels_scalar:act_quantize_q8")
    ap.add_argument("--attribution")
    a = ap.parse_args()
    man = json.load(open(a.manifest))
    variants = json.load(open(os.path.join(a.decode_dir, "variants.json")))
    rows, by_var = load_loop_table(a.loop_table)
    vmap = {}
    if a.variant_map != "hearth":
        for kv in a.variant_map.split(","):
            k, _, v = kv.partition("=")
            vmap[k] = v
    attribution = json.load(open(a.attribution)) if a.attribution else {}
    insts_by_var = collections.defaultdict(dict)
    with open(os.path.join(a.decode_dir, "instructions.jsonl")) as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("role") == "reachable":
                insts_by_var[r["variant"]][(r["section"], r["offset"])] = r
    canaries = set(a.canary_variant.split(","))
    out = []
    for v in variants:
        vid = "%s:%s:%s" % (v["config"], v["table"], v["slot"])
        key = "%s:%s" % (v["table"], v["slot"])
        lvar = vmap.get(key) or ("%s.%s" % (VARIANT_HEARTH.get(v["table"], v["table"]), SLOT_HEARTH.get(v["slot"], v["slot"])))
        insts = insts_by_var.get(vid, {})
        rec = {"config": v["config"], "table": v["table"], "slot": v["slot"], "loop_variant": lvar, "loops": [],
               "p3": {"c": [], "d1": None, "d2": []}, "key_is_canary": key in canaries}
        if key in canaries:
            rec["p3"]["d1"] = "not_evaluated"      # replaced below; anything but "pass" flags the variant (judge.py)
        if not insts:
            out.append(rec)
            continue
        succ = {k: [tuple(s) for s in i.get("succ", [])] for k, i in insts.items()}
        roots = [k for k, i in insts.items() if i.get("entry")] + \
                sorted({tuple(i["call"]) for i in insts.values() if i.get("call") and tuple(i["call"]) in insts})
        bound = max([int(r["source_lanes"]) for r in by_var.get(lvar, [])] or [0])
        seen_headers = set()
        for root in roots:
            loops, preds = natural_loops(root, succ)
            for lp in loops:
                if lp["header"] in seen_headers:
                    continue
                seen_headers.add(lp["header"])
                info = analyse_loop(lp, insts, succ, preds)
                hdr = tuple(info["header"])
                src = attribution.get("%d:%d" % hdr)
                info["id"] = "L%d_%x" % hdr
                info["attribution"] = src["kind"] if src else "none"
                info["source_loop"] = src.get("loop_id") if src else None
                srow = next((r for r in rows if r["loop_id"] == info["source_loop"]), None)
                info["acc_lanes_source"] = int(srow["source_lanes"]) if srow else None
                limit = info["acc_lanes_source"] if (srow and info["attribution"] == "exact") else bound
                info["bound_used"] = limit
                info["unattributed"] = not (srow and info["attribution"] == "exact")
                srcl = int(srow["source_lanes"]) if srow else 0
                info["u_acc"] = (info["acc_updates_per_iter"] / srcl) if srcl else None
                bpi = srow["bytes_per_iter"] if srow else ""
                step = max([abs(x) for x in info["inductions"].values()] or [0])
                info["u_ind"] = (step / int(bpi)) if (bpi.isdigit() and int(bpi) and step) else None
                u = info["u_acc"] or info["u_ind"]
                if u and u > 1:
                    info["tags"].append("unrolled-u")
                if info["packed_fp"] and v["table"] == "hx_kernels_scalar":
                    info["tags"].append("auto-vectorised")
                if not info["tags"]:
                    info["tags"].append("lockstep")
                info["fp_free"] = not info["accumulators"]
                info["not_computed_tags"] = ["peeled", "interchanged"]
                if info["acc_lanes_emitted"] > limit:
                    rec["p3"]["c"].append(info["id"])
                rec["loops"].append(info)
        if key in canaries:
            oi = next(x["object_index"] for x in man["variants"] if x["table"] == v["table"] and x["slot"] == v["slot"])
            cr = ConstReader(man["objects"][oi])
            res, where = canary_d1(sorted(insts.items()), cr)
            rec["p3"]["d1"] = res
            rec["p3"]["d1_sites"] = where
        rec["p3"]["d2"] = [{"site": "tree16", "result": "unchecked",
                            "reason": "no exact twin attribution for the site (record §4.6)"}] \
            if v["table"] in ("k_avx2", "k_avx512") and v["slot"] in ("matmul[F32]", "matmul[F16]", "matmul[BF16]") else []
        out.append(rec)
    json.dump(out, open(a.out, "w"), indent=1)
    flagged = [(r["config"], r["table"], r["slot"], r["p3"]["c"]) for r in out if r["p3"]["c"]]
    keys = {"%s:%s" % (r["table"], r["slot"]) for r in out}
    missing_canaries = sorted(canaries - keys)
    print(json.dumps({"variants": len(out), "loops": sum(len(r["loops"]) for r in out),
                      "p3c_flagged": flagged,
                      "d1": {"%s:%s" % (r["table"], r["slot"]): r["p3"]["d1"] for r in out if r["key_is_canary"]},
                      "canary_keys_matching_no_variant": missing_canaries,
                      "tags": collections.Counter(t for r in out for lp in r["loops"] for t in lp["tags"])}, indent=1))
    if missing_canaries:
        print("ERROR: --canary-variant key(s) %s match no variant; P3(d1) was not evaluated" % missing_canaries,
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
