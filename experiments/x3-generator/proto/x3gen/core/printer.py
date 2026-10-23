"""Lane program -> C11 with intrinsics (library L; trusted within X3, kept small).

Rules (07 section 7 rules 1-4, DESIGN 5.1 rule 5): one operation per statement; deterministic
output with LF line ends; a provenance header; no hand edits. Rule 5: no C full-expression contains
more than one floating-point operation, so a compiler that contracts within an expression
(clang-cl /fp:precise gives -ffp-contract=on, X0 TOOLCHAINS 4-6) has nothing to fuse. The printer
re-parses its own output and refuses to return text that breaks rule 5.
"""

import re

from ..isa import TABLE
from ..isa.scalar import HELPERS
from .lp import IX, Arr, Call, Comment, Do, For, Idx, If, Let, Set, Var

IND = "    "


class PrintError(Exception):
    pass


def cx(a) -> str:
    if isinstance(a, Var):
        return a.name
    if isinstance(a, bool):
        raise PrintError("bool literal")
    if isinstance(a, int):
        if a >= 4096:
            return "0x%x" % a
        return str(a)
    if isinstance(a, str):
        return a
    if isinstance(a, Idx):
        return "%s[%s]" % (a.arr, cx(a.index))
    if isinstance(a, Call):
        e = TABLE[a.entry]
        return e.c.format(*[cx(x) for x in a.args])
    if isinstance(a, IX):
        op, x = a.op, a.args
        if op == "cast":
            return "((%s)%s)" % (x[0], cx(x[1]))
        if op == "lit":
            return x[0]
        if op == "?:":
            return "(%s ? %s : %s)" % (cx(x[0]), cx(x[1]), cx(x[2]))
        if op in ("+", "-", "*", "/", "<", "<=", "==", "!=", "<<", ">=", "%", "&"):
            return "(%s %s %s)" % (cx(x[0]), op, cx(x[1]))
        raise PrintError("IX op " + op)
    if a is None:
        return ""
    raise PrintError("cannot print %r" % (a,))


def strip_parens(s):
    return s[1:-1] if s.startswith("(") and s.endswith(")") and _balanced(s[1:-1]) else s


def _balanced(s):
    d = 0
    for ch in s:
        d += ch == "("
        d -= ch == ")"
        if d < 0:
            return False
    return d == 0


def decl(ctype, name, mut):
    if ctype.endswith("*"):
        return "%s%s" % (ctype, name)
    if mut or ctype.startswith("const "):
        return "%s %s" % (ctype, name)
    return "const %s %s" % (ctype, name)


def stmts(body, depth, out):
    pad = IND * depth
    for s in body:
        if isinstance(s, Let):
            out.append("%s%s = %s;" % (pad, decl(s.ctype, s.name, s.mut), strip_parens(cx(s.rhs))))
        elif isinstance(s, Set):
            out.append("%s%s = %s;" % (pad, cx(s.target), strip_parens(cx(s.rhs))))
        elif isinstance(s, Arr):
            out.append("%s%s %s[%d];" % (pad, s.ctype, s.name, s.n))
        elif isinstance(s, Do):
            out.append("%s%s;" % (pad, cx(s.call)))
        elif isinstance(s, For):
            init = ""
            if s.init is not None:
                init = (
                    ("%s %s = %s" % (s.ctype, s.var, cx(s.init)))
                    if s.declare
                    else ("%s = %s" % (s.var, cx(s.init)))
                )
            step = "%s++" % s.var if s.step == 1 else "%s += %s" % (s.var, cx(s.step))
            out.append("%sfor (%s; %s; %s) {" % (pad, init, strip_parens(cx(s.cond)), step))
            stmts(s.body, depth + 1, out)
            out.append(pad + "}")
        elif isinstance(s, If):
            out.append("%sif (%s) {" % (pad, strip_parens(cx(s.cond))))
            stmts(s.then, depth + 1, out)
            if s.other:
                out.append(pad + "} else {")
                stmts(s.other, depth + 1, out)
            out.append(pad + "}")
        elif isinstance(s, Comment):
            out.append("%s/* %s */" % (pad, s.text))
        else:
            raise PrintError("statement %r" % (s,))


def used_entries(body, acc):
    from .lp import walk

    def visit(a):
        if isinstance(a, Call):
            acc.add(a.entry)
            for x in a.args:
                visit(x)
        elif isinstance(a, IX):
            for x in a.args:
                visit(x)

    for s in walk(body):
        for attr in ("rhs", "call", "cond", "init"):
            if hasattr(s, attr):
                visit(getattr(s, attr))
    return acc


def print_program(prog) -> str:
    out = []
    out.extend(prog.header_lines)
    for inc in prog.includes:
        out.append("#include %s" % inc)
    if prog.guard:
        out.append("")
        out.append("#if %s" % prog.guard)
    for inc in prog.prelude:
        out.append(inc)
    used = set()
    for f in prog.funcs:
        used_entries(f.body, used)
    helpers = [h for key, h in HELPERS if any(re.search(r"\b%s\(" % key, TABLE[u].c) for u in used)]
    if helpers:
        out.append("")
        out.extend(helpers)
    for f in prog.funcs:
        out.append("")
        params = ", ".join("%s%s%s" % (t, "" if t.endswith("*") else " ", n) for t, n in f.params)
        out.append("/* meaning %s, target %s */" % (f.meaning, f.isa))
        out.append("void %s(%s) {" % (f.name, params))
        stmts(f.body, 1, out)
        out.append("}")
    if prog.guard:
        out.append("")
        out.append("#endif /* %s */" % prog.guard)
    text = "\n".join(out) + "\n"
    rule5(text)
    return text


# ------------------------------------------------------------------ rule 5 self-check

TOK = re.compile(
    r"0[xX][0-9a-fA-F]+[uUlL]*|\d+\.\d*(?:[eE][+-]?\d+)?[fF]?|\d+(?:[eE][+-]?\d+)?[fFuUlL]*"
    r"|[A-Za-z_]\w*|->|\+\+|--|<<|>>|<=|>=|==|!=|&&|\|\||[-+*/%&|^~!<>=?:;,.()\[\]{}]"
)
FP_CLASSES = {"fp", "fpcmp", "sel"}


def _fp_intrinsics():
    names = set()
    for e in TABLE.values():
        if e.cls in FP_CLASSES:
            m = re.search(r"^\s*(\w+)\(", e.c)
            if m:
                names.add(m.group(1))
    return names


def rule5(text):
    """Every full-expression holds at most one FP operation: one FP intrinsic or helper call, or one
    binary arithmetic operator in a statement that defines or assigns a float scalar. Returns the
    number of statements checked."""
    fpcalls = _fp_intrinsics() | {"x3_h2f"}
    code = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    code = "\n".join(l for l in code.split("\n") if not l.lstrip().startswith("#"))
    floats = set(re.findall(r"\bfloat\s+(\w+)\s*(?:=|;)", code))
    n = 0
    for st in re.split(r"[;{}]", code):
        toks = TOK.findall(st)
        if not toks:
            continue
        n += 1
        n_calls = sum(
            1
            for i, t in enumerate(toks)
            if t in fpcalls and i + 1 < len(toks) and toks[i + 1] == "("
        )
        n_ops = 0
        if "=" in toks:
            eq = toks.index("=")
            lhs, rhs = toks[:eq], toks[eq + 1 :]
            float_lhs = ("float" in lhs and "*" not in lhs) or (len(lhs) == 1 and lhs[0] in floats)
            if float_lhs:
                for i, t in enumerate(rhs):
                    if (
                        t in ("+", "-", "*", "/")
                        and i > 0
                        and (rhs[i - 1] not in ("(", ",", "?", ":", "+", "-", "*", "/"))
                    ):
                        n_ops += 1
        if n_calls + n_ops > 1:
            raise PrintError("rule 5: more than one FP operation in: %s" % st.strip())
    return n
