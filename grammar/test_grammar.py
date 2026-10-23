"""Checks for grammar/mithril_v0.lark (X1 DESIGN section 10.1, PLAN S20). Status: v0 DRAFT.

    python grammar/test_grammar.py [--mithi PATH] [--mutants N]

Needs the `lark` package (written and run with lark 1.3.1). What it checks:

1. every canonical snippet of docs/m0/core-calculus/verdicts.json (D-C1 to D-C8; D-C8 is the README
   taste snippet) parses, after its SHA-256 is checked against the recorded hash (hash rule of
   verdicts.json: the fence body lines joined with LF plus one final LF);
2. every derived snippet (D-D01 to D-D27) parses, including the five outside X1, which the grammar
   recognises so that the checker can report E-OUT-OF-SCOPE-<KW>;
3. the gate negative items N-01 to N-06 parse (built as crates/mithi/tests/verdicts.rs builds
   them), with the documentation extension below, since N-01 has a `…` body and N-03 is a
   signature without a body;
4. mithi's own corpus programs (crates/mithi/tests/corpus/*.mith) parse;
5. a list of malformed programs is rejected.

With --mithi PATH (a built mithi executable), the same inputs, and N single-token deletions of the
snippets (--mutants, default 0), are also given to `mithi parse`, and accept/reject is compared.
The comparison is reported; only a disagreement on an unmutated input fails the run. Known
differences are listed in crates/mithi/README.md ("Grammar and parser").

Snippets whose first code line starts with `let` are documentation statements (D-C7, D-D25,
D-D26); they are parsed from the start symbol `loose`.
"""

import hashlib
import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time

from lark import Lark

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAMMAR = os.path.join(REPO, "grammar", "mithril_v0.lark")
VERDICTS = os.path.join(REPO, "docs", "m0", "core-calculus", "verdicts.json")
CORPUS = os.path.join(REPO, "crates", "mithi", "tests", "corpus")

# Documentation shorthand (not part of the X1 surface): `…` as an elided expression or body, and a
# function signature with neither body nor `;`. mithi accepts both under --doc-snippets.
DOC_EXTENSION = r"""
%extend primary: "…"
%extend decl: doc_signature
doc_signature: (FN_KIND _WS)? "fn" _WS NAME (_s generics)? _s params (_s "->" _s type)? (_s fn_clause)*
"""

MALFORMED = [
    ("unclosed parameter list", "fn f( {}\n"),
    ("missing `;` between statements", "fn f() { let x = 1 let y = 2; }\n"),
    ("missing `,` between fields", "struct S { a: u32 b: u32 }\n"),
    ("dangling operator", "fn f() -> u32 { 1 + }\n"),
    ("keyword run into a name", "fnf() {}\n"),
    ("chained comparison", "fn f(a: u32, b: u32, c: u32) -> bool { a < b < c }\n"),
    ("kernel without fn", "kernel f() {}\n"),
    ("missing `,` between match arms", "fn f(x: u32) -> u32 { match x { 0 => 1 1 => 2 } }\n"),
    ("strict keyword as a name", "fn f() { let fn = 1; }\n"),
    ("format argument without value", "format F { q: nibbles<64, offset = > }\n"),
    ("uses without braces", "fn f() uses io {}\n"),
    ("par without for", "fn f() { par i in 0..4 {} }\n"),
    ("schedule without target", "schedule s for f { tile r by 16; }\n"),
    ("claim without grade", "spec s for f { claim refines(a, f) requires; }\n"),
    # review 2026-10-16: char escapes must be Unicode scalar values (Rust rejects both)
    ("unicode escape above 10FFFF", "fn f() -> char { '\\u{110000}' }\n"),
    ("unicode escape of a surrogate", "fn f() -> char { '\\u{D800}' }\n"),
]

# Forms the grammar and mithi parse must both accept (review 2026-10-16: the first four were
# grammar-only rejections; labelled blocks are in the X1 core, note section 12).
ACCEPTED = [
    ("labelled block", "fn f() -> u32 { let r = 'a: { if true { break 'a 5u32; } 6u32 }; r }\n"),
    ("matches! with a struct pattern", "struct P { a: u32 }\nfn f(p: P) -> bool { matches!(p, P { .. }) }\n"),
    ("matches! with a guard", "fn f(x: u32) -> bool { matches!(x, 1 | 2 if x > 0) }\n"),
    ("float literal with a trailing dot", "fn f() -> f32 { 2. }\n"),
    ("nested block comment", "fn f() {} /* a /* b */ c */\n"),
    ("unicode escape at 10FFFF", "fn f() -> char { '\\u{10FFFF}' }\n"),
    # 2026-10-23: the keyword `unsafe` in a row parses, so that J3 can name E-GRANT-UNSAFE (note
    # section 5.2); mithi parses it since its review of 2026-10-23 (finding 12)
    ("unsafe in a row", "fn f() uses { unsafe } {}\n"),
    ("unsafe among other labels", "fn f() uses { io, unsafe, alloc(Global) } {}\n"),
]


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fence_body(path, start, end):
    """Lines start..=end (1-based) of a repository file, joined with LF, plus one final LF."""
    with open(os.path.join(REPO, path), encoding="utf-8", newline="") as f:
        lines = f.read().split("\n")
    return "\n".join(l[:-1] if l.endswith("\r") else l for l in lines[start - 1:end]) + "\n"


def start_symbol(text):
    for line in text.split("\n"):
        s = line.strip()
        if s and not s.startswith("//"):
            return "loose" if s.startswith("let ") else "start"
    return "start"


def uncomment(text, pred):
    out = []
    for l in text.split("\n"):
        if pred(l):
            t = l.lstrip()
            ind = l[: len(l) - len(t)]
            rest = t[3:] if t.startswith("// ") else (t[2:] if t.startswith("//") else t)
            out.append(ind + rest)
        else:
            out.append(l)
    return "\n".join(out)


def load_items():
    with open(VERDICTS, encoding="utf-8") as f:
        v = json.load(f)
    items = []
    for it in v["items"]:
        occ = it["snippet"]["occurrences"][0]
        body = fence_body(occ["file"], occ["start_line"], occ["end_line"])
        items.append((it["id"], occ["file"], it["snippet"]["sha256"], body))
    return items


def gate_negatives(snip):
    """N-01 to N-06, constructed as crates/mithi/tests/verdicts.rs constructs them."""
    d04 = snip["D-D04"].split("\n")
    at = next(i for i, l in enumerate(d04) if l.startswith("// fn live"))
    live = set(d04[at:at + 3])
    return [
        ("N-01", uncomment(snip["D-D01"], lambda l: l.startswith("// fn first_dyn"))),
        ("N-02", uncomment(snip["D-D02"], lambda l: l.startswith("// struct RowCache"))),
        ("N-03", uncomment(snip["D-D02"], lambda l: l.startswith("// fn pick"))),
        ("N-04", uncomment(snip["D-D04"], lambda l: l in live)),
        ("N-05", "\n".join(l for l in snip["D-D05"].split("\n") if "store.release(lease);" not in l)),
        ("N-06", uncomment(snip["D-D06"], lambda l: l.startswith("// fn heat_view"))),
    ]


class Grammar:
    def __init__(self, doc=False):
        with open(GRAMMAR, encoding="utf-8") as f:
            text = f.read()
        if doc:
            text += DOC_EXTENSION
        self.parser = Lark(text, start=["start", "loose"], parser="earley", lexer="dynamic")
        self.memo = {}

    def accepts(self, text):
        if text not in self.memo:
            try:
                self.parser.parse(text, start=start_symbol(text))
                self.memo[text] = (True, "")
            except Exception as e:  # lark raises UnexpectedInput subclasses
                self.memo[text] = (False, str(e).split("\n")[0][:160])
        return self.memo[text]


TOKEN = re.compile(
    r"//[^\n]*|/\*[\s\S]*?\*/|\s+|\"(?:[^\"\\]|\\.)*\"|'(?:[^'\\]|\\.)'|"
    r"[0-9][0-9_]*(?:\.[0-9][0-9_]*)?(?:[eE][+-]?[0-9]+)?[A-Za-z0-9_]*|[A-Za-z_][A-Za-z0-9_]*|"
    r"<<=|>>=|\.\.=|::|->|=>|==|!=|<=|>=|&&|\|\||\+=|-=|\*=|/=|%=|\^=|&=|\|=|<<|>>|\.\.|…|."
)


def mutants(named, n, seed=20261016):
    """n single-token deletions, sampled with a fixed seed from the code tokens of the inputs."""
    sites = []
    for name, text in named:
        for m in TOKEN.finditer(text):
            tok = m.group(0)
            if tok.isspace() or tok.startswith("//") or tok.startswith("/*"):
                continue
            sites.append((name, text, m.start(), m.end(), tok))
    rng = random.Random(seed)
    picked = rng.sample(sites, min(n, len(sites)))
    picked.sort(key=lambda s: (s[0], s[2]))
    return [(f"{name}~del{a}:{tok}", text[:a] + text[b:]) for name, text, a, b, tok in picked]


def mithi_accepts(mithi, named, tmp):
    """Run `mithi parse` once over all inputs; return {name: (accepted, message)}."""
    paths = {}
    for k, (name, text) in enumerate(named):
        p = f"in{k:05}.mith"
        with open(os.path.join(tmp, p), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        paths[p] = name
    out = {}
    files = list(paths)
    for i in range(0, len(files), 100):  # keep command lines short
        chunk = files[i:i + 100]
        r = subprocess.run([os.path.abspath(mithi), "parse", *chunk], capture_output=True, text=True, encoding="utf-8", cwd=tmp)
        for line in r.stdout.splitlines():
            p, _, rest = line.partition(": ")
            if p in paths:
                out[paths[p]] = (rest.startswith("ok"), rest)
    return out


def main(argv):
    mithi = None
    n_mut = 0
    i = 0
    while i < len(argv):
        if argv[i] == "--mithi":
            mithi = argv[i + 1]
            i += 1
        elif argv[i] == "--mutants":
            n_mut = int(argv[i + 1])
            i += 1
        i += 1
    import lark

    with open(GRAMMAR, encoding="utf-8", newline="") as f:
        gtext = f.read()
    print(f"lark {lark.__version__}; grammar/mithril_v0.lark: {len(gtext.encode('utf-8'))} bytes, sha256 {sha256(gtext)}")
    failures = []
    t0 = time.time()
    g = Grammar()
    gd = Grammar(doc=True)

    items = load_items()
    snip = {}
    for iid, path, want_hash, body in items:
        snip[iid] = body
        if sha256(body) != want_hash:
            failures.append(f"{iid}: stale snippet ({path}): hash {sha256(body)[:16]} != recorded {want_hash[:16]}")
    canon = [(iid, b) for iid, path, h, b in items if iid.startswith("D-C")]
    taste = [iid for iid, path, h, b in items if path == "README.md"]
    derived = [(iid, b) for iid, path, h, b in items if iid.startswith("D-D")]
    if taste != ["D-C8"]:
        failures.append(f"expected the README taste snippet to be D-C8, found {taste}")

    def check_all(label, named, gram, want=True):
        ok = 0
        for name, text in named:
            acc, msg = gram.accepts(text)
            if acc == want:
                ok += 1
            else:
                failures.append(f"{label} {name}: {'rejected' if want else 'accepted'} {msg}")
        print(f"{label}: {ok}/{len(named)} {'parse' if want else 'rejected'}")

    check_all("canonical snippets (D-C1..D-C8)", canon, g)
    check_all("derived snippets (D-D01..D-D27)", derived, g)
    negs = gate_negatives(snip)
    check_all("gate negatives N-01..N-06 (documentation extension)", negs, gd)
    corpus = []
    for f in sorted(os.listdir(CORPUS)):
        if f.endswith(".mith"):
            with open(os.path.join(CORPUS, f), encoding="utf-8") as fh:
                corpus.append((f, fh.read()))
    check_all("mithi corpus programs", corpus, g)
    check_all("malformed programs", MALFORMED, g, want=False)
    check_all("accepted forms", ACCEPTED, g)
    print(f"grammar checks: {round(time.time() - t0, 1)} s")

    if mithi:
        base = canon + derived + corpus + MALFORMED + ACCEPTED
        muts = mutants(canon + derived, n_mut) if n_mut else []
        with tempfile.TemporaryDirectory() as tmp:
            got = mithi_accepts(mithi, base + negs + muts, tmp)
        rows = []
        for label, named, gram in (("input", base, g), ("doc input", negs, gd), ("mutant", muts, g)):
            agree = 0
            for name, text in named:
                la, lmsg = gram.accepts(text)
                ma, mmsg = got.get(name, (None, "no output"))
                if la == ma:
                    agree += 1
                else:
                    rows.append((label, name, la, ma, lmsg if not la else mmsg))
            print(f"mithi parse vs grammar, {label}s: {agree}/{len(named)} agree")
        for label, name, la, ma, msg in rows:
            print(f"  DIFFER {label} {name}: grammar {'accepts' if la else 'rejects'}, mithi {'accepts' if ma else 'rejects'}: {msg}")
            if label != "mutant":
                failures.append(f"mithi parse disagrees on {name}")
    if failures:
        print("FAILED:")
        for f in failures:
            print("  " + f)
        return 1
    print("all grammar checks passed")
    return 0


def test_grammar():
    """pytest entry point (no mithi comparison)."""
    assert main([]) == 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
