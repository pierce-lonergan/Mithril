"""One-off generator for experiments/x0-census/class/objdump_norm.csv (the CSV, not this script, is frozen).

Usage: python -I gen_norm_csv.py OUT.csv   (writes LF line endings)
"""
import csv, sys

rows = []
def add(kind, od, xed, note=""):
    rows.append([kind, od, xed, note])

for t in ["notrack", "bnd", "data16", "data32", "addr32", "rex64", "rex", "cs", "ds", "es", "ss", "fs", "gs",
          "{vex}", "{vex2}", "{vex3}", "{evex}", "{disp8}", "{disp32}", "{load}", "{store}", "{nf}",
          "xacquire", "xrelease"]:
    add("strip", t, "", "prefix token printed before the mnemonic; XED folds it into the same iclass")
for t in ["lock", "rep", "repe", "repz", "repne", "repnz", "data16", "data32", "addr32", "rex64", "rex", "cs", "ds",
          "es", "ss", "fs", "gs", "notrack", "bnd", "xacquire", "xrelease"]:
    add("merge", t, "", "llvm-objdump may print this prefix as its own 1-byte line; it is merged with the next line")
add("prefix", "lock", "{X}_LOCK|{X}", "XED names locked RMW forms <X>_LOCK; XCHG and others keep <X>")
add("prefix", "rep", "REP_{X}|REPE_{X}|{X}", "string ops: REP_/REPE_; on other instructions the prefix is ignored (e.g. 'rep ret')")
add("prefix", "repe", "REPE_{X}|{X}", "")
add("prefix", "repz", "REPE_{X}|{X}", "")
add("prefix", "repne", "REPNE_{X}|{X}", "")
add("prefix", "repnz", "REPNE_{X}|{X}", "")

# condition-code aliases: LLVM prints the e/ne/a/ae/... spellings, XED uses Z/NZ/NBE/NB/...
cc = {"e": "Z", "z": "Z", "ne": "NZ", "nz": "NZ", "a": "NBE", "nbe": "NBE", "ae": "NB", "nb": "NB", "nc": "NB",
      "b": "B", "c": "B", "nae": "B", "be": "BE", "na": "BE", "l": "L", "nge": "L", "ge": "NL", "nl": "NL",
      "le": "LE", "ng": "LE", "g": "NLE", "nle": "NLE", "s": "S", "ns": "NS", "p": "P", "pe": "P", "np": "NP",
      "po": "NP", "o": "O", "no": "NO"}
for pfx, X in (("j", "J"), ("cmov", "CMOV"), ("set", "SET")):
    for k, v in cc.items():
        add("alias", pfx + k, X + v, "condition-code spelling")
for od, x in [("ret", "RET_NEAR"), ("retq", "RET_NEAR"), ("call", "CALL_NEAR"), ("callq", "CALL_NEAR"),
              ("lret", "RET_FAR"), ("ljmp", "JMP_FAR"), ("lcall", "CALL_FAR"), ("movabs", "MOV"),
              ("sal", "SHL"), ("wait", "FWAIT"), ("xlatb", "XLAT"), ("int1", "INT1"),
              ("nop", "NOP|NOP2|NOP3|NOP4|NOP5|NOP6|NOP7|NOP8|NOP9"),
              ("xchg", "XCHG|NOP"),
              ("movsd", "MOVSD_XMM|MOVSD"), ("cmpsd", "CMPSD_XMM|CMPSD"),
              ("pushfq", "PUSHFQ"), ("popfq", "POPFQ"), ("icebp", "INT1"),
              ("movsxd", "MOVSXD"), ("cwde", "CWDE"), ("cdqe", "CDQE"),
              ("fstsw", "FNSTSW"), ("fstcw", "FNSTCW"), ("fclex", "FNCLEX"), ("finit", "FNINIT"),
              ("fsave", "FNSAVE"), ("fstenv", "FNSTENV"), ("fcompi", "FCOMIP"), ("fucompi", "FUCOMIP"),
              ("pextrw", "PEXTRW|PEXTRW_SSE4")]:
    add("alias", od, x, "")
# FP compare predicates (record: CMP* are FP-sensitive; the predicate is an immediate in XED)
pred = ("eq|lt|le|unord|neq|nlt|nle|ord|eq_uq|nge|ngt|false|neq_oq|ge|gt|true|eq_os|lt_oq|le_oq|unord_s|"
        "neq_us|nlt_uq|nle_uq|ord_s|eq_us|nge_uq|ngt_uq|false_os|neq_os|ge_oq|gt_oq|true_us")
add("regex", r"cmp(%s)(ps|pd|ss)" % pred, "CMP{2}", "legacy SSE compare, predicate spelled in the mnemonic")
add("regex", r"cmp(%s)sd" % pred, "CMPSD_XMM", "legacy SSE2 scalar double compare (XED CMPSD_XMM)")
add("regex", r"vcmp(%s)(ps|pd|ss|sd|ph|sh|bf16)" % pred, "VCMP{2}", "VEX/EVEX compare, predicate in the mnemonic")
add("regex", r"vpcmp(eq|lt|le|false|neq|nlt|nle|true)(b|w|d|q)", "VPCMP{2}|VPCMPEQ{2}",
    "signed integer compare; 'eq' also spells the VPCMPEQ* opcode")
add("regex", r"vpcmp(eq|lt|le|false|neq|nlt|nle|true)u(b|w|d|q)", "VPCMPU{2}", "unsigned integer compare")
add("regex", r"vpcmpgt(b|w|d|q)", "VPCMPGT{1}|VPCMP{1}", "")
add("regex", r"vpcom(lt|le|gt|ge|eq|neq|false|true)(b|w|d|q)", "VPCOM{2}", "AMD XOP compare")
add("regex", r"vpcom(lt|le|gt|ge|eq|neq|false|true)u(b|w|d|q)", "VPCOMU{2}", "AMD XOP compare")
add("regex", r"(v?)pclmul(lq|hq)(lq|hq)dq", "{1}PCLMULQDQ", "carry-less multiply selector spelled in the mnemonic")
add("regex", r"(v?)cmp(eq|lt|le|unord|neq|nlt|nle|ord)(ps|pd|ss|sd)", "", "covered above; placeholder never used")
rows = [r for r in rows if r[3] != "covered above; placeholder never used"]

w = csv.writer(open(sys.argv[1], "w", newline="", encoding="utf-8"), lineterminator="\n")
w.writerow(["kind", "objdump", "xed_iclasses", "note"])
w.writerows(rows)
