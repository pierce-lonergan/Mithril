"""X3 line counts for the prototype (DESIGN 9.1-9.3; prereg 4.7).

  python -I scripts/count_lines.py HEARTH_CLONE BLACK_DIR [--json OUT]

H: X3-LOC-C over the closure of the dispatched Q4/Q8 table entries in quant_avx2.c and
   quant_avx512.c (the logic of DESIGN Appendix A, unchanged; scalar closure reported for reference).
S: X3-LOC-PY over every file under x3gen/hearth/ except meaning.py and tests/, plus every line of
   core/ or isa/ that the specificity lint flags (counted until an independent reviewer signs it
   off), plus tuned-parameter entries (there are none).
Also M, L, I, tokens, generated C LOC, and the ratios the record reports.
"""

import argparse
import ast
import hashlib
import io
import json
import pathlib
import re
import sys
import tokenize

ROOT = pathlib.Path(__file__).resolve().parents[1]

# ------------------------------------------------------------------ X3-LOC-C (DESIGN Appendix A)
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
TOKEN = re.compile(
    r"[A-Za-z_][A-Za-z0-9_]*|0[xX][0-9a-fA-F]+[uUlL]*|\d+\.?\d*(?:[eE][+-]?\d+)?[fFuUlL]*"
    r"|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|<<=|>>=|->|\+\+|--|<<|>>|<=|>=|==|!=|&&|\|\|"
    r"|[-+*/%&|^~!<>=?:;,.()\[\]{}#]"
)


def strip_comments(src):
    out, i, n, mode = [], 0, len(src), None
    while i < n:
        c = src[i]
        if mode is None:
            if src.startswith("/*", i):
                mode, i = "block", i + 2
                continue
            if src.startswith("//", i):
                mode, i = "line", i + 2
                continue
            if c in "\"'":
                mode = c
            out.append(c)
        elif mode == "block":
            if src.startswith("*/", i):
                mode, i = None, i + 2
                continue
            if c == "\n":
                out.append("\n")
        elif mode == "line":
            if c == "\n":
                mode = None
                out.append("\n")
        else:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(src[i + 1])
                i += 2
                continue
            if c == mode:
                mode = None
        i += 1
    return "".join(out)


def items(text):
    lines, res, i = text.split("\n"), {}, 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r"#define\s+([A-Za-z_]\w*)", ln)
        if m:
            res[m.group(1)] = ("macro", [ln])
            i += 1
            continue
        if ln and (ln[0].isalpha() or ln[0] == "_") and not ln.startswith(("typedef", "#")):
            j, depth, opened = i, 0, False
            while j < len(lines):
                depth += lines[j].count("{") - lines[j].count("}")
                opened = opened or "{" in lines[j]
                if (opened and depth == 0) or (not opened and lines[j].rstrip().endswith(";")):
                    break
                j += 1
            block = lines[i : j + 1]
            head = " ".join(block).split("{", 1)[0]
            if "(" in head and "=" not in head:
                res[IDENT.findall(head.split("(", 1)[0])[-1]] = ("func", block)
            i = j + 1
            continue
        i += 1
    return res


def closure(defs, roots):
    seen, todo = set(), list(roots)
    while todo:
        n = todo.pop()
        if n in seen or n not in defs:
            continue
        seen.add(n)
        todo += [x for x in IDENT.findall("\n".join(defs[n][1])) if x in defs and x not in seen]
    return sorted(seen)


def count_c_closure(path, roots):
    raw = pathlib.Path(path).read_bytes()
    defs = items(strip_comments(raw.decode("utf-8")))
    mem = closure(defs, roots)
    return {
        "file": pathlib.Path(path).name,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "members": mem,
        "loc": sum(1 for n in mem for l in defs[n][1] if l.strip()),
        "tokens": sum(len(TOKEN.findall("\n".join(defs[n][1]))) for n in mem),
    }


def loc_c_file(path):
    text = strip_comments(pathlib.Path(path).read_bytes().decode("utf-8"))
    return {
        "loc": sum(1 for l in text.split("\n") if l.strip()),
        "tokens": len(TOKEN.findall(text)),
    }


# ------------------------------------------------------------------ X3-LOC-PY

SKIP_TOK = {
    tokenize.COMMENT,
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.ENCODING,
    tokenize.ENDMARKER,
}


def docstring_lines(text):
    out = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            b = node.body
            if (
                b
                and isinstance(b[0], ast.Expr)
                and isinstance(b[0].value, ast.Constant)
                and isinstance(b[0].value.value, str)
            ):
                out |= set(range(b[0].lineno, b[0].end_lineno + 1))
    return out


def loc_py(text, black):
    fmt = black.format_str(text, mode=black.Mode(line_length=100))
    doc = docstring_lines(fmt)
    loc = 0
    for i, line in enumerate(fmt.split("\n"), 1):
        s = line.strip()
        if s and not s.startswith("#") and i not in doc:
            loc += 1
    toks = 0
    for t in tokenize.generate_tokens(io.StringIO(fmt).readline):
        if t.type in SKIP_TOK or (t.type == tokenize.STRING and t.start[0] in doc):
            continue
        toks += 1
    return {"loc": loc, "tokens": toks, "black_unchanged": fmt == text}


# ------------------------------------------------------------------ specificity lint (DESIGN 9.1)
LINT_ID = re.compile(r"q4|q8|qk|nib|hx_|hearth|act_?q8|block_?q|tch|qtile|bias_?8|bias_?128", re.I)
LINT_NUM = {34, 66, 72}
NIBBLE = {"0x0f", "0xf0"}


def lint_file(path):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    flagged = {}
    for t in tokenize.generate_tokens(io.StringIO(text).readline):
        hit = None
        if t.type in (tokenize.NAME, tokenize.STRING) and LINT_ID.search(t.string):
            hit = LINT_ID.search(t.string).group(0)
        elif t.type == tokenize.NUMBER:
            try:
                v = int(t.string, 0)
            except ValueError:
                v = None
            if v in LINT_NUM or t.string.lower() in NIBBLE:
                hit = t.string
        if hit:
            for ln in range(t.start[0], t.end[0] + 1):
                flagged.setdefault(ln, set()).add(hit)
    lines = text.split("\n")
    return {
        ln: {"hits": sorted(h), "text": lines[ln - 1].strip()} for ln, h in sorted(flagged.items())
    }


def isa_single_op():
    sys.path.insert(0, str(ROOT))
    from x3gen.isa import TABLE

    bad = []
    for key, e in TABLE.items():
        calls = [c for c in re.findall(r"\b([A-Za-z_]\w*)\s*\(", e.c)]
        if len(calls) > 1:
            bad.append((key, calls))
    return {
        "entries": len(TABLE),
        "multi_call_entries": bad,
        "named_exception": "scalar.h2f_bits (x3_h2f routine)",
    }


# ------------------------------------------------------------------ main


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hearth")
    ap.add_argument("black_dir")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    sys.path.insert(0, a.black_dir)
    import black

    src = pathlib.Path(a.hearth) / "engine" / "src"
    plan = [
        ("quant.c", ["mm_q8_scalar", "mm_q4_scalar"]),
        ("quant_avx2.c", ["mm_q8_avx2", "mm_q4_avx2"]),
        ("quant_avx512.c", ["mm_q8_avx512", "mm_q4_avx512"]),
    ]
    hand = [count_c_closure(src / f, r) for f, r in plan]
    H, H_tok = hand[1]["loc"] + hand[2]["loc"], hand[1]["tokens"] + hand[2]["tokens"]

    x3 = ROOT / "x3gen"
    sched_files = sorted(
        p
        for p in (x3 / "hearth").rglob("*.py")
        if p.name != "meaning.py" and "tests" not in p.parts
    )
    S_files = {
        p.relative_to(ROOT).as_posix(): loc_py(p.read_text(encoding="utf-8"), black)
        for p in sched_files
    }
    lint = {}
    for d in ("core", "isa"):
        for p in sorted((x3 / d).glob("*.py")):
            f = lint_file(p)
            if f:
                lint[p.relative_to(ROOT).as_posix()] = {str(k): v for k, v in f.items()}
    lint_lines = sum(len(v) for v in lint.values())
    S_sched = sum(v["loc"] for v in S_files.values())
    S_tok = sum(v["tokens"] for v in S_files.values())
    S = S_sched + lint_lines
    M = loc_py((x3 / "hearth" / "meaning.py").read_text(encoding="utf-8"), black)
    L = {
        p.name: loc_py(p.read_text(encoding="utf-8"), black)
        for p in sorted((x3 / "core").glob("*.py"))
    }
    I = {
        p.name: loc_py(p.read_text(encoding="utf-8"), black)
        for p in sorted((x3 / "isa").glob("*.py"))
    }
    gen = {p.name: loc_c_file(p) for p in sorted((ROOT / "generated").glob("x3_*"))}
    S_max = (30 * H) // 100
    res = {
        "black": black.__version__,
        "python": sys.version.split()[0],
        "H_closure": hand,
        "H_loc": H,
        "H_tok": H_tok,
        "S_max_loc": S_max,
        "S_schedule_files": S_files,
        "S_schedule_loc": S_sched,
        "S_schedule_tok": S_tok,
        "lint_flagged": lint,
        "lint_flagged_lines": lint_lines,
        "S_loc_conservative": S,
        "S_over_H": round(S / H, 4),
        "S_sched_over_H": round(S_sched / H, 4),
        "S_tok_over_H_tok": round(S_tok / H_tok, 4),
        "M_loc": M["loc"],
        "L_loc": sum(v["loc"] for v in L.values()),
        "I_loc": sum(v["loc"] for v in I.values()),
        "M_plus_S_over_H": round((M["loc"] + S) / H, 4),
        "L_files": L,
        "I_files": I,
        "generated_c": gen,
        "isa_lint": isa_single_op(),
    }
    text = json.dumps(res, indent=1, sort_keys=True, default=list) + "\n"
    if a.json:
        pathlib.Path(a.json).write_bytes(text.encode())
    print("H = %d (tokens %d); S_max = %d" % (H, H_tok, S_max))
    print(
        "S schedule files = %d LOC (%d tokens); lint-flagged library lines = %d; S = %d"
        % (S_sched, S_tok, lint_lines, S)
    )
    print("S/H = %.4f (S_sched/H = %.4f); S_tok/H_tok = %.4f" % (S / H, S_sched / H, S_tok / H_tok))
    print(
        "M = %d, L = %d, I = %d, (M+S)/H = %.4f"
        % (M["loc"], res["L_loc"], res["I_loc"], res["M_plus_S_over_H"])
    )
    for f, info in lint.items():
        for ln, v in info.items():
            print("  lint %s:%s %s | %s" % (f, ln, v["hits"], v["text"][:90]))


if __name__ == "__main__":
    main()
