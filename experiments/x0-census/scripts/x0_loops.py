#!/usr/bin/env python3
"""x0_loops.py -- X0 record §4.7 (loops, accumulators, unroll factors, tags), P3(c) and the canaries P3(d1) and
P3(d2), over the counted sets written by x0_decode.py. Standard library only; Python >= 3.8. Run with python -I.

Usage:
  python -I x0_loops.py DECODE_OUTDIR --manifest MANIFEST.json -o LOOPS.json
         [--loop-table ../class/loop_table.csv] [--variant-map hearth|TABLE:SLOT=LOOPVARIANT,...]
         [--canary-variant TABLE:SLOT[,TABLE:SLOT]|none] [--attribution ATTR.json ...]
         [--d2-helper tree16] [--d2-variants TABLE:SLOT,...|none] [--helpers NAME,...] [--probe-pairing]

Definitions (record §4.7), per dispatched variant:
  * CFG: the variant's reachable instructions and the intra-procedural edges x0_decode.py recorded (fall-through,
    direct jumps, jump-table targets, tail calls). Every closure function entry (the slot entry and every
    internal or interposable call target) is a root; dominators are computed from each root
    (Cooper-Harvey-Kennedy). A natural loop is a back edge t->h with h dominating t; loops sharing a header merge.
  * Registers: XMMn/YMMn/ZMMn are one register Vn; GPR sub-registers map to the 64-bit name; flags are ignored.
    A memory operand [RSP+d] or [RBP+d] with no index register is a stack slot treated as a register. A call
    defines (clobbers) the caller-saved registers of the object's ABI (SysV for ELF, Win64 for COFF; x0final).
  * Accumulation instruction: an FP-sensitive instruction of op_class ADD, SUB, MUL, MAX or MIN (FMA-class counts
    as ADD) that reads, through its data operands, a loop-carried value (live into the header, through moves and
    stack reloads; the address registers of a load are not data) or a value an accumulation produced in this
    iteration; and (x0final revision) a blend or merge-masked FP move that reads a mask written by a (V)CMPP*/CMPS*
    and one of the carried or tainted locations that compare read (compare-select, op MAX/MIN).
  * Taint (x0final revision, record §4.7 (a)): a location written by ANY instruction that reads a tainted value stays
    tainted, with provenance the union of the accumulation instructions behind it; only a write reading no tainted
    value, or a call clobber, removes it; merge-masked writes keep it.
  * acc_lanes_emitted (the unit of P3(c); x0final revision, §4.7 (b), (c)): over the strongly connected components of
    the carried-location graph (s -> r when the header value of s may reach the back-edge value of r; opmask
    registers excluded) that contain a cycle and a tainted location: the component's partial results (tainted
    locations grouped by equal back-edge provenance at every latch, plus each untainted member) times the widest lane
    count of the accumulation instructions behind them (scalar 1; f32 in xmm/ymm/zmm 4/8/16; f64 half that; masked
    forms full width), summed. The same unit as the loop table's source_lanes ("independent FP partial results
    carried across iterations"); partial_results and partial_result_cycles list them.
    acc_updates_per_iter: the sum of the lane counts of the accumulation INSTRUCTIONS behind the counted partial
    results (an unrolled serial chain updates the same register several times per iteration); it gives u_acc.
  * u_acc = acc_updates_per_iter / source_lanes (attributed loop); u_ind = the largest constant per-iteration
    increment of a GPR induction variable / the source loop's bytes_per_iter (when a single number).
  * Tags: lockstep, unrolled-u (u > 1), rotated (latch ends in a conditional branch to the header and a
    pre-header conditional branch guards the loop), software-pipelined (a loop-carried value defined in the body
    by a load), auto-vectorised (packed FP arithmetic in a loop of a scalar-table variant), spilled (vector stores
    and reloads of stack slots inside the body), and (x0final) peeled: every FP arithmetic op class of the body
    (op_class.type) occurs in one straight-line region right before the header or right after an exit (set
    inclusion, which over-tags rather than under-tags); interchanged: an emitted nest whose exactly attributed
    source loops are nested the other way round. `not_computed_tags` lists "interchanged" for a loop of an emitted
    nest without exact source-loop attribution of both loops, and is empty otherwise. When a loop has no FP
    accumulator and no tag it is tagged lockstep with fp_free = true.
  * Attribution (record §4.6, x0_twin.py; one --attribution per census object, checked against the manifest's
    object SHA-256): a variant is EXACT when every executable section of its closure is identical in the twin,
    APPROXIMATE when some differ, NONE without a usable twin line table. A loop's header line is the line of the
    header instruction, or of the first instruction of the header's block that has one (Clang gives some headers
    line 0). Its source loop is the innermost source loop containing that line, walking the inline stack outwards
    when the line lies in an inlined function outside every loop (a load helper, an intrinsic). The same is done
    for the back edge's own instruction (the latch; its line is the loop control). When the two loops nest, the outer
    one is taken only if the inner one shows signs of flattening (constant or outer-bounded trip count and no loop
    attributed to it through header and back edge) or the emitted loop encloses an emitted loop of the inner one;
    otherwise the loop's bound is the smaller of the two (x0final revision); when they are unrelated, the latch's
    (choose_source_loop). bound_header, bound_latch and bound_rule are recorded. A variant is also EXACT when a
    differing section keeps its size and relocation offsets and every closure function's own range is identical
    (x0_twin.py function_identity). Only exact
    attribution to a loop_table.csv row gives the loop its own bound; otherwise P3(c) uses the variant-wide bound,
    the largest source_lanes among the variant's loops in loop_table.csv, and the loop is listed as unattributed.
  * P3(c): a loop is flagged if acc_lanes_emitted exceeds the bound.
  * P3(d1): in the closure of each canary variant, an FP ADD with a constant operand whose every 32-bit lane is
    M = 0x4B400000, followed by an FP SUB of M (or ADD of -M = 0xCB400000) that reads the ADD's result through
    register moves only. Constants come from relocated memory operands (bytes read from the object) or from
    GPR immediates moved into vector registers. Missing pair -> "fail" (the variant is flagged). A canary variant
    without decoded instructions keeps d1 = "not_evaluated", which judge.py also flags (anything but "pass"); a
    --canary-variant key that matches no variant makes this script exit 1.
  * P3(d2) (x0final): with exact attribution, the instructions whose innermost frame in a census source file lies
    in tree16's body (helpers inlined into tree16, such as canon4, keep their own frame; GCC/Clang intrinsic header
    frames are skipped) are grouped into sites: runs along fall-through edges with at most 16 interleaved
    instructions of other lines, which must not write a register the site reads later. A site's sequence ends at
    its last FP ADD (the scalar result). Its live-in vector registers must be one 16-lane or two 8-lane accumulators.
    track_tree16 then gives match / mismatch / unchecked. Without exact attribution every expected site
    (--d2-variants) is "unchecked" (reported, not flagged; record §9).
  * Descriptive (record §5): the iclass sequence of every horizontal-helper site (--helpers), and with
    --probe-pairing (arm P) each probe wrapper's iclass sequence and, for _mm512_reduce_add_ps, its lane pairing
    against the XML's halving tree.
"""
import argparse
import bisect
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
                if nb in ("RSP", "RBP") and not ni and nb not in MOVING_BASES["now"]:
                    out.append(("mem", "STK:%s:%d" % (nb, disp), act))
                else:
                    out.append(("mem", None, act))
            for r in (nb, ni):
                if r:
                    out.append(("reg", r, "R"))
    return out


# Registers a call clobbers (x0final): the caller-saved registers of the object's ABI, as in x0_decode.py. XED's
# operand list of a CALL names none of them, so without this a value returned in xmm0, or a caller-saved register
# reused after a call, looked loop-carried (measured on the census mock under C: a false P3(c) flag).
CALL_CLOBBERS = {"elf": {"RAX", "RCX", "RDX", "RSI", "RDI", "R8", "R9", "R10", "R11"} | {"V%d" % i for i in range(32)},
                 "coff": {"RAX", "RCX", "RDX", "R8", "R9", "R10", "R11"} | {"V%d" % i for i in list(range(6)) + list(range(16, 32))}}
ABI = {"current": "elf"}


def call_clobbers(ins):
    return CALL_CLOBBERS[ABI["current"]] if ins.get("iclass", "").startswith("CALL") else set()


def uses_defs(ins):
    """Register (and stack-slot) uses and defs. Conditional writes (CW, RCW: merge masking) also use the old
    value, so they count as uses. A call defines the caller-saved registers of the ABI."""
    u, d = set(), set()
    for kind, name, act in operands(ins):
        if name is None:
            continue
        if "R" in act or act == "CW":
            u.add(name)
        if "W" in act:
            d.add(name)
    return u, d | call_clobbers(ins)


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
    """Locations whose old value is entirely replaced (W or RW; merge-masked RCW/CW writes keep old lanes; a call
    replaces the caller-saved registers)."""
    return {n for k, n, a in operands(ins) if n is not None and a in ("W", "RW")} | call_clobbers(ins)


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
# Stack-slot bases that move inside the current loop (x0final): GCC at -O3 uses RBP as an ordinary register, so
# [RBP+d] is a stack slot only while RBP is loop-invariant; RSP counts as moving only if an instruction other than
# PUSH/POP/CALL/RET (which leave it balanced) writes it. Measured on the regression set under C: [RBP] stepping
# through Y[r] looked like a carried 1-lane accumulator (a false P3(c) flag).
MOVING_BASES = {"now": set()}
STACK_OPS = ("PUSH", "POP", "CALL", "RET")


def moving_bases(body, insts):
    out = set()
    for n in body:
        ins = insts[n]
        f = ins.get("fields", {})
        for op in ins.get("operands", []):
            p = op.split("/")
            if p[0].startswith("REG") and len(p) > 1 and "W" in p[1]:
                r = norm_reg(f.get(p[0]))
                if r == "RBP" or (r == "RSP" and not ins.get("iclass", "").startswith(STACK_OPS)):
                    out.add(r)
    return out


CMP_RE = re.compile(r"^V?CMP(PS|PD|SS|SD)$")
SELECT_RE = re.compile(r"^V?(BLENDV(PS|PD)|BLENDM(PS|PD))$")
MASKED_MOVE_RE = re.compile(r"^V?MOV(APS|UPS|APD|UPD|SS|SD_XMM)$")


def address_regs(ins):
    """Registers used only to form a memory address (base and index of MEM operands)."""
    f, out = ins.get("fields", {}), set()
    for op in ins.get("operands", []):
        nm = op.split("/")[0]
        if nm.startswith("MEM"):
            base, idx, _ = parse_mem(f.get(nm) or "")
            out |= {r for r in (norm_reg(base), norm_reg(idx)) if r}
    return out


def explicit_regs(ins, act_has):
    f, out = ins.get("fields", {}), set()
    for op in ins.get("operands", []):
        p = op.split("/")
        if p[0].startswith("REG") and len(p) > 1 and act_has in p[1]:
            r = norm_reg(f.get(p[0]))
            if r:
                out.add(r)
    return out


def explicit_defs(ins):
    return explicit_regs(ins, "W")


def data_uses(ins):
    """lane0_uses without the registers that only address memory (x0final revision: the data dependences of
    record §4.7's partial-result count); LEA's address is its data."""
    u = lane0_uses(ins)
    if ins.get("iclass") == "LEA":
        return u
    return u - (address_regs(ins) - explicit_regs(ins, "R"))


def masked_move(ins):
    """A merge-masked FP move (dest RCW/CW, a k-mask read): dst = k ? src : dst."""
    if not MASKED_MOVE_RE.match(ins.get("iclass", "")):
        return False
    f = ins.get("fields", {})
    merge = any(len(op.split("/")) > 1 and op.split("/")[1] in ("RCW", "CW") for op in ins.get("operands", []))
    kreg = any(re.match(r"^K[1-7]$", f.get(op.split("/")[0]) or "") for op in ins.get("operands", []))
    return merge and kreg


def select_lanes(ins):
    """Lane count of a compare-select write (blend or merge-masked move), from its destination and element type."""
    ic = ins.get("iclass", "")
    if ic.endswith(("SS", "SD_XMM")):
        return 1
    dst = dest_register(ins)
    width = 16 if dst.startswith("ZMM") else 8 if dst.startswith("YMM") else 4
    return width if ("PS" in ic) else width // 2


def sccs(nodes, edges):
    """Strongly connected components (Tarjan, iterative), each a sorted list; deterministic order."""
    index, low, on, stack, out, k = {}, {}, set(), [], [], [0]
    for root in nodes:
        if root in index:
            continue
        work = [(root, iter(sorted(edges.get(root, ()))))]
        index[root] = low[root] = k[0]
        k[0] += 1
        stack.append(root)
        on.add(root)
        while work:
            v, it = work[-1]
            nxt = next(it, None)
            if nxt is not None:
                if nxt not in index:
                    index[nxt] = low[nxt] = k[0]
                    k[0] += 1
                    stack.append(nxt)
                    on.add(nxt)
                    work.append((nxt, iter(sorted(edges.get(nxt, ())))))
                elif nxt in on:
                    low[v] = min(low[v], index[nxt])
                continue
            work.pop()
            if work:
                low[work[-1][0]] = min(low[work[-1][0]], low[v])
            if low[v] == index[v]:
                comp = []
                while True:
                    w = stack.pop()
                    on.discard(w)
                    comp.append(w)
                    if w == v:
                        break
                out.append(sorted(comp))
    return sorted(out)


def analyse_loop(lp, insts, succ, preds):
    MOVING_BASES["now"] = moving_bases(lp["body"], insts)
    try:
        return _analyse_loop(lp, insts, succ, preds)
    finally:
        MOVING_BASES["now"] = set()


def _analyse_loop(lp, insts, succ, preds):
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
    # Flow-sensitive within one iteration (back edges into the header cut). x0final revision after the independent
    # review of 2026-10-16/17 (record §4.7):
    #   UE[n]  locations that may still hold a value carried in from the previous iteration (moves copy it);
    #   AV[n]  location -> provenance: the accumulation instructions whose results this iteration may have reached
    #          the location. (a) Taint propagates through ANY instruction that reads a tainted value (a permute,
    #          blend, mask or insert keeps a partial sum a partial sum); only a write that reads no tainted value,
    #          or a call clobber, removes it. Merge-masked writes keep the old value's taint.
    #   CM[n]  mask location -> the carried or tainted locations a (V)CMPP*/CMPS* read when it wrote the mask; (d) a
    #          blend or merge-masked move that reads such a mask and one of those locations is an accumulation of
    #          op MAX/MIN (compare-select).
    #   DEP[n] location -> the carried locations whose header values may have reached it (data operands only; the
    #          address registers of a load are not data).
    order = sorted(body, key=lambda n: (n != hdr, n))
    ue_in, av_in, cm_in = {}, {}, {}
    ue_out, av_out, cm_out, dep_out = {}, {}, {}, {}
    acc_info = {}                                    # n -> lanes, for accumulation (and compare-select) instructions

    def join(maps):
        out = {}
        for m in maps:
            for k, v in m.items():
                out[k] = out.get(k, frozenset()) | v
        return out
    for _ in range(4 * len(body) + 10):
        changed = False
        for n in order:
            ps = [p for p in preds.get(n, []) if p in body and p in ue_out]
            if n == hdr:
                ue, av, cm, dep = set(carried), {}, {}, {s: frozenset([s]) for s in carried}
            else:
                ue = set().union(*[ue_out[p] for p in ps]) if ps else set()
                av = join(av_out[p] for p in ps)
                cm = join(cm_out[p] for p in ps)
                dep = join(dep_out[p] for p in ps)
            ue_in[n], av_in[n], cm_in[n] = ue, av, cm
            ins = insts[n]
            ic = ins.get("iclass", "")
            u0 = lane0_uses(ins)
            du = data_uses(ins)
            d = ud[n][1]
            kills = full_kills(ins)
            clob = call_clobbers(ins)
            op, _ = op_class_of(ic)
            live = ue | set(av)
            is_acc = op in ACC_OPS and bool(du & live)
            is_sel = bool(SELECT_RE.match(ic) or masked_move(ins)) and \
                any(cm[m] & du & live for m in du if m in cm)
            if is_acc or is_sel:
                acc_info[n] = lanes_of(ins) if is_acc else select_lanes(ins)
            nue = ((ue - d) | d) if (is_move(ins) and (du & ue)) else (ue - kills)
            src_prov = frozenset().union(*[av[x] for x in du if x in av])
            nav = {r: p for r, p in av.items() if r not in kills}
            prov = (frozenset([n]) | src_prov) if (is_acc or is_sel) else src_prov
            if prov:
                for r in d - clob:
                    nav[r] = nav.get(r, frozenset()) | prov
            ncm = {m: s for m, s in cm.items() if m not in d}
            if CMP_RE.match(ic):
                srcs = frozenset(x for x in du if x in live)
                if srcs:
                    for m in d - clob:
                        ncm[m] = srcs
            src_dep = frozenset().union(*[dep.get(x, frozenset()) for x in du])
            ndep = dict(dep)
            for r in d:
                if r in clob and r not in explicit_defs(ins):
                    ndep.pop(r, None)
                elif r in kills:
                    ndep[r] = src_dep
                else:
                    ndep[r] = dep.get(r, frozenset()) | src_dep
            if (ue_out.get(n), av_out.get(n), cm_out.get(n), dep_out.get(n)) != (nue, nav, ncm, ndep):
                ue_out[n], av_out[n], cm_out[n], dep_out[n], changed = nue, nav, ncm, ndep, True
        if not changed:
            break
    # (c) independent partial results: the strongly connected components of the carried-location graph (an edge
    # s -> r when the header value of s may reach the back-edge value of r at some latch) that contain a cycle and a
    # location whose back-edge value an accumulation produced. Within one component, (b) locations whose back-edge
    # provenance is equal at every latch (a register and its spill copy) are one partial result; a location the
    # component carries without accumulating (a rotated register: t = acc0 + x; acc0 = acc1; acc1 = t) is one more,
    # since it holds the partial result of another iteration. acc_lanes_emitted = the sum over components of
    # (partial results x the widest lane count of the accumulation instructions behind them).
    latches = sorted(tuple(t) for t in lp["latches"])
    nodes = sorted(r for r in carried if not re.match(r"^K[0-7]$", r))
    edges = {s: set() for s in nodes}
    for tl in latches:
        for r in nodes:
            for s in (dep_out.get(tl) or {}).get(r, frozenset()):
                if s in edges:
                    edges[s].add(r)
    comps = sccs(nodes, edges)
    acc_regs, partial, cycles, counted_prov = {}, [], [], set()
    for comp in comps:
        cyclic = len(comp) > 1 or comp[0] in edges[comp[0]]
        provs = {r: tuple((av_out.get(tl) or {}).get(r, frozenset()) for tl in latches) for r in comp}
        tainted = [r for r in comp if any(provs[r])]
        if not cyclic or not tainted:
            continue
        behind = frozenset().union(*[p for r in comp for p in provs[r]])
        lanes_c = max([acc_info.get(x, 0) for x in behind] or [0])
        if lanes_c <= 0:
            continue
        classes = {}
        for r in comp:
            key = ("acc", provs[r]) if any(provs[r]) else \
                ("copy", tuple((dep_out.get(tl) or {}).get(r, frozenset()) for tl in latches), r)
            classes.setdefault(key, []).append(r)
        groups = sorted(sorted(g) for g in classes.values())
        partial += groups
        cycles.append({"members": sorted(comp), "partial_results": len(groups), "lanes": lanes_c,
                       "emitted": len(groups) * lanes_c})
        for r in comp:
            acc_regs[r] = lanes_c
        counted_prov |= behind
    acc_written = set().union(*[ud[n][1] for n in acc_info]) if acc_info else set()
    dropped = sorted((acc_written & carried) - set(acc_regs))
    updates = sum(acc_info[n] for n in counted_prov if n in acc_info)
    fp_ops = [insts[n].get("iclass", "") for n in counted_prov if n in acc_info]
    lanes = sum(c["emitted"] for c in cycles)
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
            "partial_results": partial, "partial_result_cycles": cycles,
            "carried_overwritten_before_back_edge": dropped,
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
        elif ic in ("VSHUFPD", "SHUFPD"):
            # per 128-bit lane: dst.q0 = a.q[imm bit 2k], dst.q1 = b.q[imm bit 2k+1] (f32 lanes in pairs)
            a, b = (g[0], g[1]) if len(g) > 1 else (st.get(dst), g[0])
            out = []
            for k, base in enumerate(range(0, len(a), 4)):
                q0, q1 = (imm >> (2 * k)) & 1, (imm >> (2 * k + 1)) & 1
                out += [a[base + 2 * q0], a[base + 2 * q0 + 1], b[base + 2 * q1], b[base + 2 * q1 + 1]]
            st[dst] = out
        elif ic == "VPERMILPD":
            v = g[0]
            out = []
            for k, base in enumerate(range(0, len(v), 4)):
                q0, q1 = (imm >> (2 * k)) & 1, (imm >> (2 * k + 1)) & 1
                out += [v[base + 2 * q0], v[base + 2 * q0 + 1], v[base + 2 * q1], v[base + 2 * q1 + 1]]
            st[dst] = out
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


# ------------------------------------------------------------------------------------------------ attribution
class Attribution:
    """Debug-info twin attribution (record §4.6) from x0_twin.py outputs, one per census object."""

    def __init__(self, paths, man):
        self.by_obj, self.errors = {}, []
        shas = {os.path.basename(o["object"]): o["sha256"] for o in man["objects"]}
        for p in paths or []:
            a = json.load(open(p))
            key = os.path.basename(a["census_object"])
            if shas.get(key) != a.get("census_sha256"):
                self.errors.append("%s: attribution is for another object (sha256 differs from the manifest)" % p)
                continue
            starts, stk = {}, {}
            for sec, lst in a.get("lines", {}).items():
                starts[int(sec)] = ([r[0] for r in lst], lst)
            for sec, lst in (a.get("stacks") or {}).items():
                stk[int(sec)] = ([r[0] for r in lst], lst)
            a["_starts"], a["_stacks"] = starts, stk
            self.by_obj[key] = a

    def status(self, v):
        """exact | approximate | none for a variant (record §4.6: exact iff every executable section of the
        closure has identical bytes and relocations in the twin)."""
        a = self.by_obj.get(v.get("object"))
        if a is None:
            return "none", "no twin attribution for %s" % v.get("object"), None
        if not a.get("line_table", {}).get("ok"):
            return "none", "twin line table unusable: %s" % "; ".join(a.get("line_table", {}).get("errors", [])[:3]), a
        ident = {s["census_index"]: s for s in a["identity"]["sections"]}
        bad, by_fn = [], []
        for c in v.get("closure") or []:
            s = ident.get(c["section_index"], {})
            if s.get("identical"):
                continue
            # x0final revision: a section that differs only inside other functions (same size, same relocation
            # offsets) still gives this closure function exact attribution if its own range is identical
            fn = next((f for f in s.get("functions") or [] if f["start"] == c.get("start") and f["end"] == c.get("end")), None)
            if fn and fn["identical"]:
                by_fn.append(c.get("symbol"))
                continue
            bad.append("%s@%s" % (c.get("symbol"), c["section_index"]))
        if bad:
            return "approximate", "closure functions %s differ in the twin (bytes or relocations)" % sorted(set(bad)), a
        if by_fn:
            return "exact", "exact per function (%s): their section differs in the twin only outside them" % sorted(set(by_fn)), a
        return "exact", None, a

    @staticmethod
    def line_at(a, sec, off):
        """(file, line, depth) of the innermost frame at (sec, off), or None."""
        if a is None or sec not in a["_starts"]:
            return None
        st, lst = a["_starts"][sec]
        k = bisect.bisect_right(st, off) - 1
        if k >= 0 and lst[k][0] <= off < lst[k][1] and lst[k][3]:
            return lst[k][2], lst[k][3], lst[k][4]
        return None

    @staticmethod
    def stack_at(a, sec, off):
        """Inline frames at (sec, off), innermost first: [(file, line)]; the innermost line alone if no stack."""
        if a is None:
            return None
        if sec in a.get("_stacks", {}):
            st, lst = a["_stacks"][sec]
            k = bisect.bisect_right(st, off) - 1
            if k >= 0 and lst[k][0] <= off < lst[k][1]:
                return [tuple(f) for f in lst[k][2] if f[1]]
        w = Attribution.line_at(a, sec, off)
        return [(w[0], w[1])] if w else None

    @staticmethod
    def source_frame(a, sec, off):
        """The innermost inline frame at (sec, off) that lies in a source file of the census (the census file or a
        header in its source directories): GCC's and Clang's intrinsics are inline functions in the compiler's
        headers, so their frames are skipped; helper code inlined into a helper (canon4 in tree16) keeps its own
        frame and so does not belong to the outer helper's site."""
        for f in Attribution.stack_at(a, sec, off) or []:
            if f[0] in (a or {}).get("sources", {}):
                return f
        return None

    @staticmethod
    def source_loop_of_stack(a, frames):
        """Record §4.7 'source loop' through the inline stack (x0final precision): the innermost source loop that
        contains the header instruction's line, or, when that line lies in an inlined function outside every loop,
        the innermost source loop containing the inlined call site (the next outer frame), and so on."""
        for k, (fname, line) in enumerate(frames or []):
            sl = Attribution.source_loop(a, fname, line)
            if sl:
                return sl + (k,)
        return None

    @staticmethod
    def source_loop(a, fname, line):
        """Innermost source loop of file `fname` whose line range contains `line`: (loop_id, kind, start, end)."""
        src = (a or {}).get("sources", {}).get(fname)
        if not src:
            return None
        best = None
        for kind, hdr, s, e in src["loops"]:
            if s <= line <= e and (best is None or (s, -e) > (best[2], -best[3])):
                best = ("%s:%d" % (fname, hdr), kind, s, e)
        return best


def _norm_operand_regs(ins):
    """(dst, srcs, imm) for the d2 tracker: registers as V<n>, stack slots as STK keys; mask registers dropped.
    The destination is the first written operand; a read-write destination (legacy SSE) is not listed as a source
    (track_tree16 then takes it as the first operand)."""
    f = ins.get("fields", {})
    dst, srcs = None, []
    for op in ins.get("operands", []):
        p = op.split("/")
        nm, act = p[0], (p[1] if len(p) > 1 else "")
        if nm.startswith("REG"):
            r = f.get(nm) or ""
            if r.startswith("K"):
                continue
            nr = norm_reg(r)
            if not nr:
                continue
            if "W" in act and dst is None:
                dst = nr
            elif act == "R":
                srcs.append(nr)
        elif nm.startswith("MEM"):
            base, idx, disp = parse_mem(f.get(nm) or "")
            nb, ni = norm_reg(base), norm_reg(idx)
            key = "STK:%s:%d" % (nb, disp) if nb in ("RSP", "RBP") and not ni else "MEM"
            if "W" in act and dst is None:
                dst = key
            elif "R" in act:
                srcs.append(key)
    imm = f.get("IMM0")
    try:
        imm = int(str(imm), 16) if imm is not None and str(imm).lower().startswith("0x") else (int(imm) if imm is not None else None)
    except ValueError:
        imm = None
    return dst, srcs, imm


def _width_of(ins, reg):
    """f32 lanes of `reg` as the instruction READS it (0 if it does not read it)."""
    f = ins.get("fields", {})
    for op in ins.get("operands", []):
        p = op.split("/")
        nm, act = p[0], (p[1] if len(p) > 1 else "")
        r = f.get(nm) or ""
        if nm.startswith("REG") and "R" in act and norm_reg(r) == reg:
            return 16 if r.startswith("ZMM") else 8 if r.startswith("YMM") else 4 if r.startswith("XMM") else 0
    return 0


def helper_runs(order, insts, in_helper, max_gap=16):
    """Group helper-attributed instructions into sites: runs in address order along fall-through edges (every
    instruction of the run has exactly one successor, the next instruction in address order), allowing at most
    max_gap interleaved instructions of other lines. Returns [(site_instructions, interleaved_instructions)]."""
    runs, cur, gapbuf = [], None, []
    for k, n in enumerate(order):
        ins = insts[n]
        if in_helper(n):
            if cur is None:
                cur, gapbuf = {"site": [n], "inter": []}, []
            else:
                cur["inter"] += gapbuf
                cur["site"].append(n)
                gapbuf = []
        elif cur is not None:
            gapbuf.append(n)
            if len(gapbuf) > max_gap:
                runs.append((cur["site"], cur["inter"]))
                cur, gapbuf = None, []
                continue
        if cur is not None:
            nxt = order[k + 1] if k + 1 < len(order) else None
            succ = [tuple(s) for s in ins.get("succ", [])]
            if nxt is None or succ != [nxt]:
                runs.append((cur["site"], cur["inter"]))
                cur, gapbuf = None, []
    if cur is not None:
        runs.append((cur["site"], cur["inter"]))
    return runs


def check_d2_site(site, inter, insts):
    """Run the lane-provenance tracker on one tree16 site. Returns (result, reason, seq). The accumulator lanes
    are the site's live-in vector registers: one read as ZMM (16 lanes) or two read as YMM (lanes 0-7, 8-15)."""
    adds = [k for k, n in enumerate(site) if insts[n].get("iclass") in ("VADDSS", "ADDSS", "VADDPS", "ADDPS")]
    if adds:
        # the sequence ends at the tree's last FP ADD, the scalar result (record §5 P3(d2): "from the 16
        # accumulator lanes to the scalar result"); later instructions of the run (Clang's inlined NaN
        # canonicalisation when its frames are lost) are not part of the tree
        site = site[: adds[-1] + 1]
        inter = [m for m in inter if m < site[-1]]
    seq, reads_before_write, written = [], [], set()
    for n in site:
        ins = insts[n]
        dst, srcs, imm = _norm_operand_regs(ins)
        seq.append((ins.get("iclass", ""), dst, srcs, imm))
        for s in srcs:
            if s not in written and s not in reads_before_write:
                reads_before_write.append(s)
        if dst:
            written.add(dst)
    # interleaved instructions of other lines must not write a register the site reads after them
    allpos = sorted(site + inter)
    pos = {n: i for i, n in enumerate(allpos)}
    for m in inter:
        wr = uses_defs(insts[m])[1]
        for n in site:
            if pos[n] > pos[m]:
                _, srcs, _ = _norm_operand_regs(insts[n])
                if wr & set(srcs):
                    return "unchecked", "an interleaved instruction at %#x writes %s, which the site reads later" % (
                        m[1], sorted(wr & set(srcs))), seq
    live = [r for r in reads_before_write if r.startswith("V")]
    widths = []
    for r in live:
        w = 0
        for n in site:
            d_, s_, _ = _norm_operand_regs(insts[n])
            if r in s_:
                w = max(w, _width_of(insts[n], r))
            if d_ == r:
                break
        widths.append(w)
    if not ((len(live) == 1 and widths == [16]) or (len(live) == 2 and widths == [8, 8])):
        return "unchecked", "live-in vector registers %s (widths %s): not one 16-lane or two 8-lane accumulators" % (
            live, widths), seq
    try:
        res = track_tree16(seq, live)
    except (TypeError, IndexError, KeyError) as e:
        return "unchecked", "the tracker could not evaluate the sequence (%s)" % e, seq
    return res, (None if res != "unchecked" else "an instruction outside the whitelist, or a source of unknown lanes"), seq


def probe_pairing(insts, name):
    """Record §3 arm P / §5 secondary 'reduce probe': the emitted iclass sequence of one probe wrapper and, for the
    _mm512_reduce_add_ps wrappers, the lane pairing checked against the XML's halving tree (lanes j and j+8, then
    +4, +2, +1: the same s = 8, 4, 2, 1 tree as track_tree16). The 16 lanes are the vector loaded first from
    memory into a ZMM register (Win64 passes __m512 by reference; the _mem wrappers load), else zmm0 (SysV)."""
    order = sorted(insts)
    skip = {"RET_NEAR", "VZEROUPPER", "ENDBR64", "INT3"}
    body = [n for n in order if insts[n].get("iclass") not in skip and not insts[n].get("iclass", "").startswith("NOP")]
    out = {"iclass_seq": [insts[n].get("iclass") for n in order]}
    if "reduce_add_ps" not in name:
        out.update(pairing="not_tracked", reason="the tracker follows FP ADD trees only")
        return out
    acc, seq = ["V0"], []
    for k, n in enumerate(body):
        ins = insts[n]
        dst, srcs, imm = _norm_operand_regs(ins)
        if k == 0 and MOVE_RE.match(ins.get("iclass", "")) and "MEM" in "".join(srcs) and dest_register(ins).startswith("ZMM"):
            acc = [dst]
            continue
        if not (dst and dst.startswith(("V", "STK"))) and not any(s.startswith(("V", "STK")) for s in srcs):
            continue                               # GPR-only bookkeeping (frame, pointer arithmetic)
        seq.append((ins.get("iclass", ""), dst, srcs, imm))
    try:
        res = track_tree16(seq, acc)
    except (TypeError, IndexError, KeyError) as e:
        res = "unchecked"
        out["reason"] = "the tracker could not evaluate the sequence (%s)" % e
    out.update(pairing=res, accumulator=acc, sequence=[list(s) for s in seq])
    if res == "unchecked" and "reason" not in out:
        out["reason"] = "an instruction outside the whitelist, or a source of unknown lanes"
    return out


FP_LABEL_SFX = {"PS": "f32", "SS": "f32", "PD": "f64", "SD": "f64"}


def fp_label(ins):
    op, sfx = op_class_of(ins.get("iclass", ""))
    if op is None:
        return None
    return "%s.%s" % (op, FP_LABEL_SFX.get(sfx, sfx))


def straight_regions(lp, insts, succ, gpreds, limit=256):
    """Straight-line code right before the loop header (from each out-of-loop predecessor backwards) and right
    after each exit edge (forwards): chains of single-predecessor, single-successor instructions."""
    body = lp["body"]
    regs = []
    for p in sorted(gpreds.get(lp["header"], [])):
        if p in body:
            continue
        chain, cur = [], p
        while cur is not None and cur not in body and len(chain) < limit:
            chain.append(cur)
            ps = gpreds.get(cur, [])
            if len(ps) != 1 or len(succ.get(ps[0], [])) != 1:
                break
            cur = ps[0]
        regs.append(("before", list(reversed(chain))))
    for n in sorted(body):
        for s in succ.get(n, []):
            if s in body or s not in insts:
                continue
            chain, cur = [], s
            while cur is not None and cur not in body and len(chain) < limit and cur in insts:
                chain.append(cur)
                ss = succ.get(cur, [])
                if len(ss) != 1 or len(gpreds.get(ss[0], [])) != 1:
                    break
                cur = ss[0]
            regs.append(("after", chain))
    return regs


def peeled_check(lp, insts, succ, gpreds):
    """Record §4.7 'peeled', mechanised (x0final): every FP arithmetic op class of the loop body (op_class.type,
    e.g. ADD.f32, MUL.f32) occurs in one straight-line region right before the header or right after an exit.
    Set inclusion over-tags rather than under-tags, the strict direction for the narrowing."""
    labs = {fp_label(insts[n]) for n in lp["body"]} - {None}
    if not labs:
        return False, []
    hits = []
    for where, chain in straight_regions(lp, insts, succ, gpreds):
        rl = {fp_label(insts[n]) for n in chain} - {None}
        if chain and labs <= rl:
            hits.append({"where": where, "start": list(chain[0]), "n_instructions": len(chain)})
    return bool(hits), hits


def _trip_ok(inner, outer, rows, ad):
    """record §4.7 (x0final revision): the inner source loop can have been flattened into straight-line code: its
    loop_table.csv trip_count is a compile-time constant, or is the outer loop's induction variable (the variable of
    the outer `for`'s init clause, from x0_twin.py's source scan)."""
    r = rows.get(inner[0])
    if not r:
        return False, "no loop_table.csv row for %s" % inner[0]
    tc = (r.get("trip_count") or "").strip()
    if re.match(r"^\d+\b", tc):
        return True, "trip count %s is a constant" % tc
    fname, _, line = outer[0].rpartition(":")
    var = (((ad or {}).get("sources", {}).get(fname) or {}).get("loop_vars") or {}).get(line)
    if var and tc == var:
        return True, "trip count %s is the induction variable of %s" % (tc, outer[0])
    return False, "trip count %r is neither a constant nor the induction variable of %s (%r)" % (tc, outer[0], var)


def choose_source_loop(sl_h, sl_l, own=None, rows=None, ad=None, encloses=None):
    """Record §4.7 source loop: the loops found from the header instruction and from the back edge's own instruction.
    Returns (source loop, how, rule); rule is 'same', 'header', 'latch', 'outer' or 'min'.
    x0final: when one contains the other, the outer one (an emitted loop whose inner source loop was flattened into
    straight-line code, a vectorised j-loop of an s = 8, 4, 2, 1 tree measured on the regression set under GCC and
    Clang, has its header in the inner loop and its back edge in the outer loop).
    x0final revision (independent review of 2026-10-16/17): the outer loop is taken only if the inner one shows the
    signs of flattening: (i) no loop of the variant is attributed to the inner source loop through both its header
    and its back edge, and (ii) the inner loop's trip count is a compile-time constant or the outer loop's induction
    variable (_trip_ok). Otherwise the loop's bound is the smaller of the two loops' bounds (rule 'min', stricter; the
    caller records both bounds), so a split in a real inner loop whose back-edge line lands on the outer loop is not
    hidden behind the outer loop's lanes. The outer loop is also taken when the emitted loop's body encloses another
    emitted loop attributed to the inner source loop through header and back edge (`encloses`): then this loop is not
    the inner loop (measured on the regression set under C: GCC keeps j-loops of the s = 8, 4, 2, 1 tree inside the
    emitted s-loop, whose header line is a j line; without this the s-loop's 8 lanes were checked against 0).
    When the two loops are unrelated, the back edge's loop."""
    own, rows = own or set(), rows or {}
    if sl_h and sl_l:
        (hs, he), (ls, le) = (sl_h[2], sl_h[3]), (sl_l[2], sl_l[3])
        same_file = sl_h[0].split(":")[0] == sl_l[0].split(":")[0]
        if sl_h[0] == sl_l[0]:
            return sl_h, "header=latch", "same"
        nest = None
        if ls <= hs and he <= le and same_file:
            nest = (sl_h, sl_l, "latch (encloses the header's loop)")
        elif hs <= ls and le <= he and same_file:
            nest = (sl_l, sl_h, "header (encloses the latch's loop)")
        if nest:
            inner, outer, how = nest
            if encloses and encloses(inner[0]):
                return outer, "%s; it encloses an emitted loop of %s" % (how, inner[0]), "outer"
            ok, why = _trip_ok(inner, outer, rows, ad)
            if inner[0] not in own and ok:
                return outer, "%s; inner %s flattened: %s" % (how, inner[0], why), "outer"
            why2 = "a loop of the variant is attributed to %s through header and back edge" % inner[0] \
                if inner[0] in own else why
            return inner, "nested header %s and latch %s, inner not shown flattened (%s): the smaller bound" % (
                sl_h[0], sl_l[0], why2), "min"
        return sl_l, "latch (unrelated to the header's loop)", "latch"
    if sl_l:
        return sl_l, "latch", "latch"
    if sl_h:
        return sl_h, "header", "header"
    return None, None, None


def interchange_tags(lps):
    """Record §4.7 'interchanged', mechanised (x0final): an emitted nest (one loop body strictly inside another)
    whose exactly attributed source loops are nested the other way round (the inner emitted loop's source loop
    strictly contains the outer emitted loop's). Sets not_computed_tags = ["interchanged"] for a loop of an emitted
    nest whose own or partner's source-loop attribution is not exact; [] otherwise. lps: analyse_loop() results
    with "_body", "attribution", "source_loop_lines" and "tags"."""
    for lp in lps:
        nc, inter = [], False
        for q in lps:
            if q is lp or not (q["_body"] < lp["_body"] or lp["_body"] < q["_body"]):
                continue
            outer, inner = (lp, q) if q["_body"] < lp["_body"] else (q, lp)
            if not (outer["source_loop_lines"] and inner["source_loop_lines"] and outer["attribution"] == "exact"
                    and inner["attribution"] == "exact"):
                nc = ["interchanged"]
                continue
            (os_, oe), (is_, ie) = outer["source_loop_lines"], inner["source_loop_lines"]
            if is_ <= os_ and oe <= ie and (is_, ie) != (os_, oe):
                inter = True
        if inter:
            lp["tags"].append("interchanged")
            nc = []
        lp["not_computed_tags"] = nc


# ------------------------------------------------------------------------------------------------ main
def load_loop_table(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    by_var = collections.defaultdict(list)
    for r in rows:
        for v in r["variants"].split("|"):
            by_var[v].append(r)
    return rows, by_var


HEARTH_HELPERS = ("tree16", "hmax16", "hsum_i32", "red_quads", "red_quad1", "canon16", "canon4", "hmax8", "hsum8_i32",
                  "red8", "canon8", "finish16")
HEARTH_D2 = ",".join("%s:%s" % (t, s) for t in ("k_avx2", "k_avx512") for s in ("matmul[F32]", "matmul[F16]", "matmul[BF16]"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("decode_dir")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--loop-table", default=os.path.join(HERE, "..", "class", "loop_table.csv"))
    ap.add_argument("--variant-map", default="hearth",
                    help="'hearth', or TABLE:SLOT=LOOPVARIANT pairs separated by commas")
    ap.add_argument("--canary-variant", default="hx_kernels_scalar:act_quantize_q8")
    ap.add_argument("--attribution", action="append", default=[],
                    help="x0_twin.py output for one census object (repeat for every object of the manifest)")
    ap.add_argument("--d2-helper", default="tree16")
    ap.add_argument("--d2-variants", default=HEARTH_D2,
                    help="TABLE:SLOT keys whose closure must hold a d2 site (default: Hearth's F32/F16/BF16 SIMD slots)")
    ap.add_argument("--helpers", default=",".join(HEARTH_HELPERS), help="horizontal helpers for the descriptive sequences")
    ap.add_argument("--probe-pairing", action="store_true", help="arm P: iclass sequence and lane pairing per probe wrapper")
    a = ap.parse_args()
    man = json.load(open(a.manifest))
    variants = json.load(open(os.path.join(a.decode_dir, "variants.json")))
    rows, by_var = load_loop_table(a.loop_table)
    row_by_id = {r["loop_id"]: r for r in rows}
    vmap = {}
    if a.variant_map != "hearth":
        for kv in a.variant_map.split(","):
            k, _, v = kv.partition("=")
            vmap[k] = v
    attr = Attribution(a.attribution, man)
    for e in attr.errors:
        print("ERROR:", e, file=sys.stderr)
    d2_keys = set(x for x in a.d2_variants.split(",") if x)
    helpers = [h for h in a.helpers.split(",") if h]
    if a.d2_helper not in helpers:
        helpers.append(a.d2_helper)
    insts_by_var = collections.defaultdict(dict)
    with open(os.path.join(a.decode_dir, "instructions.jsonl")) as fh:
        for line in fh:
            r = json.loads(line)
            if r.get("role") == "reachable":
                insts_by_var[r["variant"]][(r["section"], r["offset"])] = r
    canaries = set(x for x in a.canary_variant.split(",") if x and x != "none")
    src_of_obj = {os.path.basename(o["object"]): os.path.basename(o["source"]) for o in man["objects"]}
    fmt_of_obj = {os.path.basename(o["object"]): o.get("format", "elf") for o in man["objects"]}
    out = []
    for v in variants:
        vid = "%s:%s:%s" % (v["config"], v["table"], v["slot"])
        key = "%s:%s" % (v["table"], v["slot"])
        lvar = vmap.get(key) or ("%s.%s" % (VARIANT_HEARTH.get(v["table"], v["table"]), SLOT_HEARTH.get(v["slot"], v["slot"])))
        insts = insts_by_var.get(vid, {})
        ABI["current"] = "coff" if fmt_of_obj.get(v.get("object"), "elf").startswith("coff") else "elf"
        status, why, ad = attr.status(v)
        rec = {"config": v["config"], "table": v["table"], "slot": v["slot"], "loop_variant": lvar, "loops": [],
               "attribution": status, "attribution_detail": why,
               "p3": {"c": [], "d1": None, "d2": []}, "key_is_canary": key in canaries, "sequences": []}
        if key in canaries:
            rec["p3"]["d1"] = "not_evaluated"      # replaced below; anything but "pass" flags the variant (judge.py)
        if not insts:
            if key in d2_keys:
                rec["p3"]["d2"] = [{"site": a.d2_helper, "result": "unchecked", "reason": "no decoded instructions"}]
            out.append(rec)
            continue
        succ = {k: [tuple(s) for s in i.get("succ", [])] for k, i in insts.items()}
        gpreds = collections.defaultdict(list)
        for n, ss in succ.items():
            for s2 in ss:
                if s2 in insts:
                    gpreds[s2].append(n)
        roots = [k for k, i in insts.items() if i.get("entry")] + \
                sorted({tuple(i["call"]) for i in insts.values() if i.get("call") and tuple(i["call"]) in insts})
        bound = max([int(r["source_lanes"]) for r in by_var.get(lvar, [])] or [0])
        seen_headers = set()
        lps, pending = [], []
        for root in roots:
            loops, preds = natural_loops(root, succ)
            for lp in loops:
                if lp["header"] in seen_headers:
                    continue
                seen_headers.add(lp["header"])
                info = analyse_loop(lp, insts, succ, preds)
                hdr = tuple(info["header"])
                info["id"] = "L%d_%x" % hdr
                where = frames = None
                taken = hdr
                if status != "none":
                    cur, seen_n = hdr, 0
                    while cur is not None and seen_n < 64:
                        w0 = Attribution.line_at(ad, cur[0], cur[1])
                        if w0:                     # the innermost (line-table) line is known here
                            frames = Attribution.stack_at(ad, cur[0], cur[1])
                            where, taken = w0, cur
                            break
                        nx = succ.get(cur, [])
                        cur = nx[0] if len(nx) == 1 and nx[0] in lp["body"] and nx[0] != hdr else None
                        seen_n += 1
                if not where:
                    frames = None
                info["header_line_from"] = list(taken) if frames else None
                sl_h = Attribution.source_loop_of_stack(ad, frames) if frames else None
                info["header_source_line"] = ("%s:%d" % (where[0], where[1])) if where else None
                info["header_inline_stack"] = ["%s:%d" % f for f in frames] if frames else None
                # the back edge's own instruction (x0final): its line is the loop control of the source loop the
                # back edge implements; it settles which loop a header line inside a flattened inner loop belongs to
                sl_l, lstack = None, None
                if status != "none":
                    for lt in sorted(tuple(x) for x in lp["latches"]):
                        cur, seen_n = lt, 0
                        while cur is not None and seen_n < 8 and sl_l is None:
                            if Attribution.line_at(ad, cur[0], cur[1]):
                                lstack = Attribution.stack_at(ad, cur[0], cur[1])
                                sl_l = Attribution.source_loop_of_stack(ad, lstack)
                                break
                            ps = [q for q in gpreds.get(cur, []) if q in lp["body"]]
                            cur = ps[0] if len(ps) == 1 else None
                            seen_n += 1
                        if sl_l:
                            break
                info["latch_inline_stack"] = ["%s:%d" % f for f in lstack] if lstack else None
                pending.append((lp, info, sl_h, sl_l))
        # x0final revision (record §4.7): a source loop counts as emitted on its own when some loop of the variant
        # has its header and its back edge attributed to it
        own = {h[0] for _, _, h, l2 in pending if h and l2 and h[0] == l2[0]}
        for lp, info, sl_h, sl_l in pending:
            def encloses(inner_id, lp=lp):
                return any(q is not lp and qh and ql and qh[0] == ql[0] == inner_id and q["header"] in lp["body"]
                           for q, _, qh, ql in pending)
            sl, via, rule = choose_source_loop(sl_h, sl_l, own, row_by_id, ad, encloses)

            def bound_of(x):
                r = row_by_id.get(x[0]) if x else None
                return int(r["source_lanes"]) if (r and status == "exact") else bound
            info["attributed_via"] = via
            info["attributed_through_frame"] = sl[4] if sl else None
            info["attribution"] = status if sl else "none"
            info["source_loop"] = sl[0] if sl else None
            info["source_loop_kind"] = sl[1] if sl else None
            info["source_loop_lines"] = [sl[2], sl[3]] if sl else None
            srow = row_by_id.get(info["source_loop"]) if sl else None
            info["acc_lanes_source"] = int(srow["source_lanes"]) if srow else None
            exact = bool(srow) and info["attribution"] == "exact"
            limit = info["acc_lanes_source"] if exact else bound
            info["bound_header"] = bound_of(sl_h) if sl_h else None
            info["bound_latch"] = bound_of(sl_l) if sl_l else None
            info["bound_rule"] = rule
            if rule == "min":
                limit = min(bound_of(sl_h), bound_of(sl_l))
            info["bound_used"] = limit
            info["unattributed"] = not exact
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
            pe, pregs = peeled_check(lp, insts, succ, gpreds)
            info["peeled_regions"] = pregs
            if pe:
                info["tags"].append("peeled")
            info["fp_free"] = not info["accumulators"]
            info["_body"] = lp["body"]
            if info["acc_lanes_emitted"] > limit:
                rec["p3"]["c"].append(info["id"])
            lps.append(info)
        interchange_tags(lps)
        for lp in lps:
            if not lp["tags"]:
                lp["tags"].append("lockstep")
            lp["tags"] = sorted(set(lp["tags"]), key=lp["tags"].index)
            del lp["_body"]
            rec["loops"].append(lp)
        if key in canaries:
            oi = next(x["object_index"] for x in man["variants"] if x["table"] == v["table"] and x["slot"] == v["slot"])
            cr = ConstReader(man["objects"][oi])
            res, where = canary_d1(sorted(insts.items()), cr)
            rec["p3"]["d1"] = res
            rec["p3"]["d1_sites"] = where
        if a.probe_pairing and v["table"] == "probe":
            rec["probe"] = probe_pairing(insts, v["slot"])
        # d2 sites and the descriptive helper sequences: exact attribution only (record §4.6, §5 P3(d2))
        order = sorted(insts)
        fname = src_of_obj.get(v.get("object"), "")
        funcs = ((ad or {}).get("sources", {}).get(fname) or {}).get("functions", {})
        if status == "exact":
            for h in helpers:
                rng = funcs.get(h)
                if not rng:
                    continue

                def in_h(n, rng=rng):
                    w = Attribution.source_frame(ad, n[0], n[1])
                    return bool(w) and w[0] == fname and rng[0] <= w[1] <= rng[1]
                for site, inter in helper_runs(order, insts, in_h):
                    sid = "%s@%d:%x" % (h, site[0][0], site[0][1])
                    rec["sequences"].append({"helper": h, "site": sid,
                                             "iclass_seq": [insts[n].get("iclass") for n in site], "interleaved": len(inter)})
                    if h == a.d2_helper:
                        res, reason, seq = check_d2_site(site, inter, insts)
                        rec["p3"]["d2"].append({"site": sid, "result": res, "reason": reason,
                                                "sequence": [list(s) for s in seq]})
            if key in d2_keys and not rec["p3"]["d2"]:
                rec["p3"]["d2"] = [{"site": a.d2_helper, "result": "unchecked",
                                    "reason": "no instruction of the closure is attributed to %s" % a.d2_helper}]
        elif key in d2_keys:
            rec["p3"]["d2"] = [{"site": a.d2_helper, "result": "unchecked",
                                "reason": "attribution %s (%s): sites need exact twin attribution (record §4.6)" % (status, why)}]
        out.append(rec)
    json.dump(out, open(a.out, "w"), indent=1)
    flagged = [(r["config"], r["table"], r["slot"], r["p3"]["c"]) for r in out if r["p3"]["c"]]
    keys = {"%s:%s" % (r["table"], r["slot"]) for r in out}
    missing_canaries = sorted(canaries - keys)
    print(json.dumps({"variants": len(out), "loops": sum(len(r["loops"]) for r in out),
                      "attribution": collections.Counter(r["attribution"] for r in out),
                      "p3c_flagged": flagged,
                      "d1": {"%s:%s" % (r["table"], r["slot"]): r["p3"]["d1"] for r in out if r["key_is_canary"]},
                      "d2": collections.Counter(s["result"] for r in out for s in r["p3"]["d2"]),
                      "canary_keys_matching_no_variant": missing_canaries,
                      "tags": collections.Counter(t for r in out for lp in r["loops"] for t in lp["tags"]),
                      "not_computed": collections.Counter(t for r in out for lp in r["loops"] for t in lp["not_computed_tags"])},
                     indent=1))
    if missing_canaries:
        print("ERROR: --canary-variant key(s) %s match no variant; P3(d1) was not evaluated" % missing_canaries,
              file=sys.stderr)
        return 1
    if attr.errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
