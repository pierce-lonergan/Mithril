#!/usr/bin/env python3
"""Scratch prototype (NOT committed): recursive-descent parser + Kleene evaluator for the
06-forge §7.2 trigger grammar, run over every trigger in docs/DECISIONS.md.

Usage: python -I trigger_proto.py <path-to-DECISIONS.md>
"""
from __future__ import annotations
import re, sys, json, hashlib

TOK = re.compile(r"""
 (?P<ws>\s+)
|(?P<hash>(?:sha256|h):[0-9a-fA-F…]+)
|(?P<num>\d+(?:\.\d+)?)
|(?P<str>"[^"]*")
|(?P<op>\|\||&&|==|!=|<=|>=|\.\.=|\.\.|[!<>()+\-*,:{}.])
|(?P<name>[A-Za-z_][A-Za-z0-9_]*)
""", re.X)

KEYWORDS = {"in", "not", "has", "exists", "true", "false", "prereg", "at_burial", "scope"}
SUGAR = {"tier_exists": "tier"}


class ParseError(Exception):
    pass


def lex(s):
    out, i = [], 0
    while i < len(s):
        m = TOK.match(s, i)
        if not m:
            raise ParseError(f"bad char {s[i]!r} at {i}")
        i = m.end()
        k = m.lastgroup
        if k == "ws":
            continue
        out.append((k, m.group()))
    out.append(("eof", ""))
    return out


class P:
    def __init__(self, s):
        self.t = lex(s); self.i = 0; self.warn = []; self.facts = set()

    def peek(self, k=0):
        return self.t[self.i + k]

    def eat(self, v=None, kind=None):
        tk = self.t[self.i]
        if v is not None and tk[1] != v:
            raise ParseError(f"expected {v!r} got {tk[1]!r}")
        if kind is not None and tk[0] != kind:
            raise ParseError(f"expected {kind} got {tk}")
        self.i += 1
        return tk

    # pred := or
    def pred(self):
        a = self.and_()
        while self.peek()[1] == "||":
            self.eat("||"); a = ("or", a, self.and_())
        return a

    def and_(self):
        a = self.not_()
        while self.peek()[1] == "&&":
            self.eat("&&"); a = ("and", a, self.not_())
        return a

    def not_(self):
        if self.peek()[1] in ("!", "not"):
            self.i += 1
            return ("not", self.not_())
        return self.primary()

    def primary(self):
        tk = self.peek()
        if tk[1] == "(":
            self.eat("("); p = self.pred(); self.eat(")"); return p
        if tk[1] == "exists":
            self.eat("exists"); self.eat("(")
            var = self.eat(kind="name")[1]
            self.eat("in"); setf = self.fact()
            self.eat(":")
            body = self.pred(); self.eat(")")
            if "exists" in json.dumps(body):
                raise ParseError("nested exists")
            return ("exists", var, setf, body)
        if tk[1] == "has":
            self.eat("has"); self.eat("(")
            kind = None
            if self.peek(1)[1] == ":":
                kind = self.eat(kind="name")[1]; self.eat(":")
            name = self.eat(kind="name")[1]
            args = self.args() if self.peek()[1] == "(" else []
            self.eat(")")
            return ("has", kind, name, args)
        if tk[0] == "name" and tk[1] in SUGAR and self.peek(1)[1] == "(":
            self.i += 1; self.eat("(")
            name = self.eat(kind="name")[1]; self.eat(")")
            return ("has", SUGAR[tk[1]], name, [])
        return self.atom()

    def atom(self):
        left = self.lin()
        op = self.peek()[1]
        if op == "in":
            self.eat("in")
            if self.peek()[1] == "{":
                return ("in_set", left, self.setlit())
            if self.peek()[0] == "num" and self.peek(1)[1] in ("..", "..="):
                lo = float(self.eat(kind="num")[1]); incl = self.eat()[1] == "..="
                hi = float(self.eat(kind="num")[1])
                return ("in_range", left, lo, hi, incl)
            # const in fact
            return ("const_in", left, self.fact())
        if op in ("==", "!=", "<", "<=", ">", ">="):
            self.i += 1
            if self.peek()[1] == "{":
                if op not in ("==", ">=", "<="):
                    raise ParseError(f"set compare with {op}")
                return ("set_cmp", op, left, self.setlit())
            right = self.lin()
            return ("cmp", op, left, right)
        # bare boolean fact
        if left[0] == "lin" and len(left[1]) == 1 and left[1][0][1] == 1 and left[1][0][2][0] in ("fact", "const_name"):
            ref = left[1][0][2]
            if ref[0] == "const_name":
                # a single bare name used as a boolean atom
                self.warn.append(f"bare name {ref[1]!r} used as boolean fact (un-namespaced)")
                ref = ("fact", ref[1], False)
            return ("bool", ref)
        raise ParseError(f"dangling operand before {self.peek()}")

    def setlit(self):
        self.eat("{"); items = []
        if self.peek()[1] != "}":
            items.append(self.const())
            while self.peek()[1] == ",":
                self.eat(","); items.append(self.const())
        self.eat("}")
        return ("set", items)

    def const(self):
        tk = self.eat()
        if tk[0] in ("num", "str", "name", "hash"):
            return tk[1]
        raise ParseError(f"bad const {tk}")

    def lin(self):
        terms = [self.term(1)]
        while self.peek()[1] in ("+", "-"):
            sign = 1 if self.eat()[1] == "+" else -1
            terms.append(self.term(sign))
        return ("lin", terms)

    def term(self, sign):
        tk = self.peek()
        if tk[0] == "num" and self.peek(1)[1] == "*":
            k = float(self.eat()[1]); self.eat("*")
            return ("term", sign * k, self.ref())
        if tk[0] == "num":
            return ("term", sign, ("num", float(self.eat()[1])))
        if tk[0] == "str" or tk[0] == "hash" or tk[1] in ("true", "false"):
            return ("term", sign, ("const", self.eat()[1]))
        return ("term", sign, self.ref())

    def ref(self):
        tk = self.peek()
        if tk[1] == "prereg":
            self.eat("prereg"); self.eat("(")
            key = self.dotted(); self.eat(")")
            return ("prereg", key)
        if tk[1] == "at_burial":
            self.eat("at_burial")
            if self.peek()[1] == "(":
                self.eat("("); f = self.fact(); self.eat(")")
            else:
                self.eat("."); f = self.fact()
            return ("at_burial", f)
        if tk[1] == "scope":
            self.eat("scope"); self.eat("."); return ("scope", self.fact())
        f = self.fact()
        if f[0] == "fact" and "." not in f[1] and "(" not in f[1]:
            return ("const_name", f[1])   # bare single name: enum constant (resolved by type)
        return f

    def dotted(self):
        s = self.eat(kind="name")[1]
        while self.peek()[1] == "." and self.peek(1)[0] == "name":
            self.eat("."); s += "." + self.eat(kind="name")[1]
        return s

    def fact(self):
        parts = []
        seg = self.eat(kind="name")[1]
        if seg in KEYWORDS and seg not in ("scope",):
            raise ParseError(f"keyword {seg} as fact")
        if self.peek()[1] == "(":
            seg += "(" + ",".join(self.args()) + ")"
        parts.append(seg)
        while self.peek()[1] == "." and self.peek(1)[0] == "name":
            self.eat("."); seg = self.eat(kind="name")[1]
            if self.peek()[1] == "(":
                seg += "(" + ",".join(self.args()) + ")"
            parts.append(seg)
        path = ".".join(parts)
        self.facts.add(re.sub(r"\(.*?\)", "(…)", path))
        return ("fact", path, False)

    def args(self):
        self.eat("("); out = [self.arg()]
        while self.peek()[1] == ",":
            self.eat(","); out.append(self.arg())
        self.eat(")")
        return out

    def arg(self):
        name = ""
        if self.peek()[0] == "name" and self.peek(1)[1] == ":":
            name = self.eat()[1] + ":"; self.eat(":")
        tk = self.peek()
        if tk[1] == "prereg":
            self.eat("prereg"); self.eat("("); k = self.dotted(); self.eat(")")
            return name + f"prereg({k})"
        if tk[0] in ("num", "str", "hash"):
            return name + self.eat()[1]
        if tk[0] == "name":
            d = self.dotted()
            if "." in d:
                self.warn.append(f"dotted arg {d!r}: fact or constant key? (grammar ambiguity)")
            return name + d
        raise ParseError(f"bad arg {tk}")


def parse(s):
    p = P(s)
    tree = p.pred()
    if p.peek()[0] != "eof":
        raise ParseError(f"trailing {p.peek()}")
    return tree, p


# ---------------- Kleene evaluation ----------------
T, F, U = True, False, None


def k_and(a, b):
    if a is F or b is F: return F
    if a is U or b is U: return U
    return T


def k_or(a, b):
    if a is T or b is T: return T
    if a is U or b is U: return U
    return F


def k_not(a):
    return U if a is U else (not a)


def lookup(store, path, env):
    head = path.split(".")[0]
    if head in env:
        obj = env[head]
        for seg in path.split(".")[1:]:
            if not isinstance(obj, dict) or seg not in obj:
                return U
            obj = obj[seg]
        return obj
    return store.get(path, U)


def val(store, env, burial, r):
    k = r[0]
    if k == "num": return r[1]
    if k == "const": return r[1].strip('"')
    if k == "const_name": return r[1]
    if k == "fact": return lookup(store, r[1], env)
    if k == "prereg": return store.get("prereg:" + r[1], U)
    if k == "at_burial": return burial.get(r[1][1], U)
    if k == "scope": return store.get("scope." + r[1][1], U)
    raise ValueError(r)


def lin_val(store, env, burial, lin):
    tot = 0.0; sym = None
    for (_, k, ref) in lin[1]:
        v = val(store, env, burial, ref)
        if v is U: return U
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            tot += k * v
        else:
            if len(lin[1]) != 1 or k != 1: return U
            sym = v
    return sym if sym is not None else tot


def ev(tree, store, env=None, burial=None):
    env = env or {}; burial = burial or {}
    k = tree[0]
    if k == "or": return k_or(ev(tree[1], store, env, burial), ev(tree[2], store, env, burial))
    if k == "and": return k_and(ev(tree[1], store, env, burial), ev(tree[2], store, env, burial))
    if k == "not": return k_not(ev(tree[1], store, env, burial))
    if k == "bool":
        v = val(store, env, burial, tree[1]); return U if v is U else bool(v)
    if k == "has":
        cat = store.get(f"catalogue:{tree[1]}", U)
        return U if cat is U else (tree[2] in cat)
    if k == "cmp":
        a = lin_val(store, env, burial, tree[2]); b = lin_val(store, env, burial, tree[3])
        if a is U or b is U: return U
        op = tree[1]
        try:
            return {"==": a == b, "!=": a != b, "<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
        except TypeError:
            return U
    if k == "in_set":
        a = lin_val(store, env, burial, tree[1]); return U if a is U else (a in tree[2][1])
    if k == "in_range":
        a = lin_val(store, env, burial, tree[1])
        if a is U: return U
        return tree[2] <= a <= tree[3] if tree[4] else tree[2] <= a < tree[3]
    if k == "set_cmp":
        a = lin_val(store, env, burial, tree[2])
        if a is U: return U
        s = set(tree[3][1]); a = set(a)
        return {"==": a == s, ">=": a >= s, "<=": a <= s}[tree[1]]
    if k == "exists":
        members = lookup(store, tree[2][1], env)
        if members is U: return U
        acc = F
        for m in members:
            acc = k_or(acc, ev(tree[3], store, {**env, tree[1]: m}, burial))
        return acc
    if k == "const_in":
        c = lin_val(store, env, burial, tree[1]); s = lookup(store, tree[2][1], env)
        return U if (c is U or s is U) else (c in s)
    raise ValueError(k)


def extract(md):
    out = []
    # tombstone blocks
    for m in re.finditer(r"tombstone (\w+) \{(.*?)\n\}", md, re.S):
        name, body = m.group(1), m.group(2)
        tm = re.search(r"revisit_when:(.*?)\n\s*(evidence|//|\Z)", body, re.S)
        trig = re.sub(r"//[^\n]*", "", tm.group(1)) if tm else None
        out.append(("tombstone", name, " ".join(trig.split()) if trig else None,
                    hashlib.sha256(m.group(0).encode()).hexdigest()))
    # DR revisit lines
    cur = None
    for line in md.splitlines():
        h = re.match(r"### (DR-\d+)", line)
        if h: cur = h.group(1)
        r = re.match(r"\*\*Revisit when\*\* `([^`]*)`", line)
        if r and cur:
            out.append(("dr", cur, r.group(1), hashlib.sha256(line.encode()).hexdigest()))
    return out


if __name__ == "__main__":
    md = open(sys.argv[1], encoding="utf-8").read()
    items = extract(md)
    ok = bad = 0
    allfacts = {}
    for kind, name, trig, h in items:
        try:
            tree, p = parse(trig)
            ok += 1
            allfacts[name] = sorted(p.facts)
            w = ("; WARN " + " | ".join(p.warn)) if p.warn else ""
            print(f"OK   {kind:9} {name:36} sha256:{h[:12]}{w}")
        except ParseError as e:
            bad += 1
            print(f"FAIL {kind:9} {name:36} {e} :: {trig}")
    print(f"\nparsed {ok}, failed {bad}, total {len(items)}")
    if len(sys.argv) > 2:
        json.dump(allfacts, open(sys.argv[2], "w"), indent=1)
