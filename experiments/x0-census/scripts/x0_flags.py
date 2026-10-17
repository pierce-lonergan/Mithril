#!/usr/bin/env python3
"""x0_flags.py -- read exact per-file compile commands from CMake's compile_commands.json.

Subcommands:
  show   LABEL=compile_commands.json [...] [--files quant.c quant_avx2.c quant_avx512.c] [--json OUT]
         Print, per configuration and file, the compiler and the argument list with the
         source, object-output and PDB arguments removed (those are per-file plumbing, not flags).
  replay compile_commands.json --as quant_avx512.c --src OTHER.c --obj OUT.obj [--exec] [--extra=ARG ...]
         Rebuild the exact command CMake uses for --as, but compiling --src into --obj.
         Prints the argv as JSON; with --exec runs it (from the entry's "directory") and returns
         the compiler's exit status. On Windows run it from a vcvars64 environment. --extra=ARG (repeatable)
         appends one argument (used for `-###`, `/Zs`, or the debug-info twin flag /Z7 or -g).
  proxy  B-cmake.compile_commands.json --dlike D-clang.compile_commands.json --out B-proxy.argv.json
         Record §3 arm B-proxy: every B-cmake entry with /fp:precise and /arch:* removed and /clang:-O3,
         /clang:-std=gnu11, /clang:-ffp-contract=off and D's -m flags for the same file added through /clang:.
         Writes a compile_commands-style JSON (entries with "arguments") that `replay` accepts.
  p3a    --patterns ../class/fp_flag_patterns.txt [--argv-json F] [--cc1 F] [--gccq F]
         Record §5 P3(a): match the frozen flag patterns against a driver argv (JSON list, or a
         compile_commands.json entry), the -cc1 line of `clang -###` output (raw text) and/or the
         output of `gcc <flags> -Q --help=common,optimizers` (raw text). Prints JSON
         {"a1": [ids], "a2": [ids], "hits": [...]}; exit 0 whether or not anything matched.

Windows (NMake/MSVC-style) commands are split with CommandLineToArgvW rules, others with shlex.
Standard library only; Python >= 3.8.
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys


def split_windows(cmd):
    """Split a command line the way CommandLineToArgvW does (enough for CMake output)."""
    args, cur, i, inq, have = [], [], 0, False, False
    while i < len(cmd):
        c = cmd[i]
        if c == "\\":
            j = i
            while j < len(cmd) and cmd[j] == "\\":
                j += 1
            n = j - i
            if j < len(cmd) and cmd[j] == '"':
                cur.append("\\" * (n // 2))
                if n % 2:
                    cur.append('"')
                    i = j + 1
                else:
                    i = j
                have = True
                continue
            cur.append("\\" * n)
            i = j
            have = True
            continue
        if c == '"':
            if inq and i + 1 < len(cmd) and cmd[i + 1] == '"':
                cur.append('"')
                i += 2
                continue
            inq = not inq
            have = True
            i += 1
            continue
        if c in " \t" and not inq:
            if have or cur:
                args.append("".join(cur))
                cur, have = [], False
            i += 1
            continue
        cur.append(c)
        have = True
        i += 1
    if have or cur:
        args.append("".join(cur))
    return args


def entry_argv(e):
    if "arguments" in e:
        return list(e["arguments"])
    cmd = e["command"]
    winish = re.match(r'^\s*"?[A-Za-z]:[\\/]', cmd) is not None  # drive-letter compiler path
    return split_windows(cmd) if winish else shlex.split(cmd)


def is_msvc_driver(path):
    return os.path.basename(path.replace("\\", "/")).lower() in ("cl.exe", "cl", "clang-cl.exe", "clang-cl")


def plumbing(argv, src):
    """Indices of per-file plumbing args: source, -o X, /Fo.., /Fd.., -c, and (GNU-style only)
    the dependency-file flags -MD/-MMD/-MF/-MT/-MQ. For cl/clang-cl, -MD is the runtime-library
    flag and is kept."""
    msvc = is_msvc_driver(argv[0])
    drop, i = set(), 1
    base = os.path.basename(src.replace("\\", "/")).lower()
    while i < len(argv):
        a = argv[i]
        al = a.lower()
        if os.path.basename(a.replace("\\", "/")).lower() == base:
            drop.add(i)
        elif a == "-o" or (not msvc and a in ("-MF", "-MT", "-MQ")):
            drop.update((i, i + 1))
            i += 1
        elif msvc and al[:3] in ("/fo", "-fo", "/fd", "-fd"):
            drop.add(i)
        elif a in ("-c", "/c", "--") or (not msvc and a in ("-MD", "-MMD")):
            drop.add(i)
        i += 1
    return drop


def find(entries, name):
    hits = [e for e in entries if os.path.basename(e["file"]).lower() == name.lower()]
    if not hits:
        raise SystemExit("no compile_commands entry for %s" % name)
    return hits


# ------------------------------------------------------------------ P3(a) flag patterns

def load_patterns(path):
    """Read fp_flag_patterns.txt -> list of (id, class, sources, compiled regex)."""
    pats, seen = [], set()
    with open(path, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 4:
                raise ValueError("%s:%d: expected 4 TAB-separated fields" % (path, ln))
            pid, cls, src, rx = parts
            if cls not in ("a1", "a2") or pid in seen:
                raise ValueError("%s:%d: bad class or duplicate id" % (path, ln))
            srcs = tuple(src.split(","))
            if not set(srcs) <= {"argv", "cc1", "gccq"}:
                raise ValueError("%s:%d: bad source %r" % (path, ln, src))
            seen.add(pid)
            pats.append((pid, cls, srcs, re.compile(rx)))
    return pats


def expand_argv(argv):
    """Driver argv plus the clang pass-through spellings /clang:X and -Xclang X (matched as X too)."""
    out = list(argv)
    for i, t in enumerate(argv):
        if t.lower().startswith("/clang:") or t.startswith("-clang:"):
            out.append(t[len("/clang:"):])
        if t == "-Xclang" and i + 1 < len(argv):
            out.append(argv[i + 1])
    return out


def parse_cc1(text):
    """Tokens of the first -cc1 command printed by `clang -###` (each argument is double-quoted)."""
    for line in text.splitlines():
        if '"-cc1"' in line:
            return [re.sub(r"\\(.)", r"\1", t) for t in re.findall(r'"((?:[^"\\]|\\.)*)"', line)]
    return None


def parse_gccq(text):
    """`gcc -Q --help=...` output -> list of "option<TAB>value" strings (options without a value are kept
    as "option<TAB>")."""
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("-"):
            continue
        parts = s.split(None, 1)
        out.append("%s\t%s" % (parts[0], parts[1].strip() if len(parts) > 1 else ""))
    return out


def match_p3a(patterns, argv=None, cc1=None, gccq=None):
    """Return {"a1": sorted ids, "a2": sorted ids, "hits": [[id, source, token], ...]}."""
    srcs = {"argv": expand_argv(argv) if argv else [], "cc1": cc1 or [], "gccq": gccq or []}
    hits = []
    for pid, cls, where, rx in patterns:
        for src in where:
            for tok in srcs[src]:
                if rx.fullmatch(tok):
                    hits.append([pid, src, tok])
    cls_of = {p[0]: p[1] for p in patterns}
    return {"a1": sorted({h[0] for h in hits if cls_of[h[0]] == "a1"}),
            "a2": sorted({h[0] for h in hits if cls_of[h[0]] == "a2"}), "hits": hits}


def cmd_p3a(a):
    pats = load_patterns(a.patterns)
    argv = cc1 = gccq = None
    if a.argv_json:
        with open(a.argv_json) as f:
            j = json.load(f)
        argv = entry_argv(j) if isinstance(j, dict) else list(j)
    if a.cc1:
        with open(a.cc1, encoding="utf-8", errors="replace") as f:
            cc1 = parse_cc1(f.read())
        if cc1 is None:
            raise SystemExit("no -cc1 line in %s" % a.cc1)
    if a.gccq:
        with open(a.gccq, encoding="utf-8", errors="replace") as f:
            gccq = parse_gccq(f.read())
    print(json.dumps(match_p3a(pats, argv, cc1, gccq), indent=1))
    return 0


def cmd_show(a):
    out = {}
    for spec in a.dbs:
        label, _, path = spec.partition("=")
        with open(path) as f:
            entries = json.load(f)
        out[label] = {}
        for name in a.files:
            for e in find(entries, name):
                argv = entry_argv(e)
                drop = plumbing(argv, e["file"])
                flags = [x for k, x in enumerate(argv[1:], 1) if k not in drop]
                out[label].setdefault(name, []).append({
                    "compiler": argv[0], "flags": flags, "directory": e["directory"], "file": e["file"],
                    "output": e.get("output")})
    if a.json:
        with open(a.json, "w") as f:
            json.dump(out, f, indent=1)
    for label, files in out.items():
        print("## %s" % label)
        for name, lst in files.items():
            for x in lst:
                print("%-16s %s" % (name, x["compiler"]))
                print("%-16s %s" % ("", " ".join(x["flags"])))
        print()


def cmd_replay(a):
    with open(a.db) as f:
        entries = json.load(f)
    e = find(entries, a.as_)[0]
    argv = entry_argv(e)
    msvc = is_msvc_driver(argv[0])
    drop = plumbing(argv, e["file"])
    new = [argv[0]] + [x for k, x in enumerate(argv[1:], 1) if k not in drop]
    src, obj = os.path.abspath(a.src), os.path.abspath(a.obj)
    new += list(a.extra or [])
    new += (["/c", "/Fo" + obj, src] if msvc else ["-c", "-o", obj, src])
    print(json.dumps({"directory": e["directory"], "argv": new}))
    if a.exec_:
        os.makedirs(os.path.dirname(obj), exist_ok=True)
        return subprocess.call(new, cwd=e["directory"])
    return 0


PROXY_DROP = ("/fp:precise", "-fp:precise", "/arch:AVX2", "-arch:AVX2", "/arch:AVX512", "-arch:AVX512")
PROXY_ADD = ["/clang:-O3", "/clang:-std=gnu11", "/clang:-ffp-contract=off"]


def proxy_argv(b_argv, d_argv):
    """B-proxy argv from a B-cmake argv and the D argv for the same file (record §3)."""
    m_flags = [t for t in d_argv[1:] if re.match(r"^-m[a-z0-9]", t)]
    out = [t for t in b_argv if t not in PROXY_DROP]
    add = PROXY_ADD + ["/clang:" + t for t in m_flags]
    cut = next((i for i, t in enumerate(out) if i > 0 and (t in ("-c", "/c", "--") or t[:3].lower() in ("/fo", "-fo"))),
               len(out))
    return out[:cut] + add + out[cut:]


def cmd_proxy(a):
    with open(a.db) as f:
        b_entries = json.load(f)
    with open(a.dlike) as f:
        d_entries = json.load(f)
    out = []
    for e in b_entries:
        name = os.path.basename(e["file"])
        d = [x for x in d_entries if os.path.basename(x["file"]) == name]
        if not d:
            continue
        out.append({"directory": e["directory"], "file": e["file"], "output": e.get("output"),
                    "arguments": proxy_argv(entry_argv(e), entry_argv(d[0]))})
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)
    for e in out:
        if os.path.basename(e["file"]).startswith("quant"):
            print(os.path.basename(e["file"]), " ".join(e["arguments"][1:]))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("show")
    s.add_argument("dbs", nargs="+", help="LABEL=path/to/compile_commands.json")
    s.add_argument("--files", nargs="+", default=["quant.c", "quant_avx2.c", "quant_avx512.c"])
    s.add_argument("--json")
    r = sub.add_parser("replay")
    r.add_argument("db")
    r.add_argument("--as", dest="as_", required=True)
    r.add_argument("--src", required=True)
    r.add_argument("--obj", required=True)
    r.add_argument("--exec", dest="exec_", action="store_true")
    r.add_argument("--extra", action="append", default=[])
    x = sub.add_parser("proxy")
    x.add_argument("db")
    x.add_argument("--dlike", required=True)
    x.add_argument("--out", required=True)
    q = sub.add_parser("p3a")
    q.add_argument("--patterns", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "class",
                                                      "fp_flag_patterns.txt"))
    q.add_argument("--argv-json")
    q.add_argument("--cc1")
    q.add_argument("--gccq")
    a = ap.parse_args()
    return {"show": cmd_show, "replay": cmd_replay, "p3a": cmd_p3a, "proxy": cmd_proxy}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main() or 0)
