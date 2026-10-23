"""Lane program -> C11 with intrinsics (library L; trusted within X3, kept small).

Rules (07 section 7 rules 1-4, DESIGN 5.1 rule 5): one operation per statement; deterministic
output with LF line ends; a provenance header; no hand edits. Rule 5: no C full-expression contains
more than one floating-point operation, so a compiler that contracts within an expression
(clang-cl /fp:precise gives -ffp-contract=on, X0 TOOLCHAINS 4-6) has nothing to fuse. The printer
re-parses its own output and refuses to return text that breaks rule 5.

Defence in depth for B9 (review 2026-10-23, checker lens, finding 2; the checker's audit_static is
the check that counts): the printer copies no string it has not checked against a closed form.
Identifiers are plain C names, declared and cast types come from a fixed list, literals are plain
decimal digits, comment text cannot close the comment, no call is nested in another call's argument
(operator spellings such as "{0} - {1}" put no parentheses around arguments), a placeholder glued to
an identifier character takes only a non-negative literal, and a call result is declared with the
call's own type.
"""

import re

from ..isa import TABLE
from ..isa.scalar import HELPERS
from .lp import IX, Arr, Call, Comment, Do, For, Idx, If, Let, Set, Var

IND = "    "
NAME = re.compile(r"\A[A-Za-z][A-Za-z0-9_]{0,62}\Z")
INT_TYPES = {"int", "int8_t", "int16_t", "int32_t", "int64_t", "unsigned", "uint8_t", "uint16_t"}
INT_TYPES |= {"uint32_t", "uint64_t", "size_t", "__mmask8", "__mmask16"}
PTR_TYPES = {"const uint8_t *", "uint8_t *", "float *"}
DATA_TYPES = {"float", "__m128", "__m128i", "__m256", "__m256i", "__m512", "__m512i"}


class PrintError(Exception):
    pass


def _name(s):
    if not (isinstance(s, str) and NAME.search(s)):
        raise PrintError("identifier %r" % (s,))
    return s


def _base(ct):
    if not isinstance(ct, str):
        raise PrintError("type %r" % (ct,))
    if ct in PTR_TYPES:
        return ct
    t = ct[len("const ") :] if ct.startswith("const ") else ct
    if t not in INT_TYPES | DATA_TYPES:
        raise PrintError("type %r" % (ct,))
    return t


def _call(a):
    e = TABLE[a.entry]
    glued = {
        int(m.group(1))
        for m in re.finditer(r"\{(\d+)\}", e.c)
        if re.search(r"\A\w", e.c[m.end() : m.end() + 1])
        or re.search(r"\A\w", e.c[m.start() - 1 : m.start()] if m.start() else "")
    }
    for j, x in enumerate(a.args):
        if isinstance(x, Call):
            raise PrintError("a call nested in an argument of %s" % a.entry)
        if j in glued and not (type(x) is int and x >= 0):
            raise PrintError("argument %d of %s must be a non-negative literal" % (j, a.entry))
    return e.c.format(*[cx(x) for x in a.args])


def cx(a) -> str:
    if isinstance(a, Var):
        return _name(a.name)
    if isinstance(a, bool):
        raise PrintError("bool literal")
    if isinstance(a, int):
        if a >= 4096:
            return "0x%x" % a
        return str(a)
    if isinstance(a, str):
        raise PrintError("verbatim text %r" % (a,))
    if isinstance(a, Idx):
        return "%s[%s]" % (_name(a.arr), cx(a.index))
    if isinstance(a, Call):
        return _call(a)
    if isinstance(a, IX):
        op, x = a.op, a.args
        if op == "cast":
            if x[0] not in INT_TYPES | PTR_TYPES:
                raise PrintError("cast type %r" % (x[0],))
            return "((%s)%s)" % (x[0], cx(x[1]))
        if op == "lit":
            if not (isinstance(x[0], str) and re.search(r"\A[0-9]+\Z", x[0])):
                raise PrintError("literal %r" % (x[0],))
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
    _base(ctype)
    _name(name)
    if ctype.endswith("*"):
        return "%s%s" % (ctype, name)
    if mut or ctype.startswith("const "):
        return "%s %s" % (ctype, name)
    return "const %s %s" % (ctype, name)


def stmts(body, depth, out):
    pad = IND * depth
    for s in body:
        if isinstance(s, Let):
            if isinstance(s.rhs, Call) and _base(s.ctype) != TABLE[s.rhs.entry].ret:
                raise PrintError(
                    "%s declared %s holds a %s result" % (s.name, s.ctype, s.rhs.entry)
                )
            out.append("%s%s = %s;" % (pad, decl(s.ctype, s.name, s.mut), strip_parens(cx(s.rhs))))
        elif isinstance(s, Set):
            out.append("%s%s = %s;" % (pad, cx(s.target), strip_parens(cx(s.rhs))))
        elif isinstance(s, Arr):
            if type(s.n) is not int or s.n <= 0:
                raise PrintError("array size %r" % (s.n,))
            out.append("%s%s %s[%d];" % (pad, _base(s.ctype), _name(s.name), s.n))
        elif isinstance(s, Do):
            out.append("%s%s;" % (pad, cx(s.call)))
        elif isinstance(s, For):
            init = ""
            _name(s.var)
            if s.init is not None:
                init = (
                    ("%s %s = %s" % (_base(s.ctype), s.var, cx(s.init)))
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
            t = s.text
            if not (isinstance(t, str) and re.search(r"\A[ -~]*\Z", t)) or "*/" in t or "/*" in t:
                raise PrintError("comment text %r" % (t,))
            out.append("%s/* %s */" % (pad, t))
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


def _wrapper(prog):
    """The translation unit's fixed text (emit.py) has closed forms too: comment lines, include
    lines, an `#if defined(MACRO)` guard, and plain names in the function headers."""
    for h in prog.header_lines:
        if not re.search(r"\A/\* [ -~]*? \*/\Z", h) or "*/" in h[:-2]:
            raise PrintError("header line %r" % (h,))
    for inc in prog.includes:
        if not re.search(r'\A(?:"[\w./]+"|<[\w./]+>)\Z', inc):
            raise PrintError("include %r" % (inc,))
    for p in prog.prelude:
        if not re.search(r"\A#include <[\w./]+>\Z", p):
            raise PrintError("prelude line %r" % (p,))
    if prog.guard and not re.search(r"\Adefined\(\w+\)\Z", prog.guard):
        raise PrintError("guard %r" % (prog.guard,))
    for f in prog.funcs:
        for x in (f.name, f.meaning, f.isa):
            _name(x)
        for t, n in f.params:
            _name(n)
            if t not in ("const void *", "float *", "int64_t", "int"):
                raise PrintError("parameter type %r" % (t,))


def print_program(prog) -> str:
    _wrapper(prog)
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
