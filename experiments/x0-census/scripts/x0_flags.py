#!/usr/bin/env python3
"""x0_flags.py -- read exact per-file compile commands from CMake's compile_commands.json.

Subcommands:
  show   LABEL=compile_commands.json [...] [--files quant.c quant_avx2.c quant_avx512.c] [--json OUT]
         Print, per configuration and file, the compiler and the argument list with the
         source, object-output and PDB arguments removed (those are per-file plumbing, not flags).
  replay compile_commands.json --as quant_avx512.c --src OTHER.c --obj OUT.obj [--exec]
         Rebuild the exact command CMake uses for --as, but compiling --src into --obj.
         Prints the argv as JSON; with --exec runs it (from the entry's "directory") and returns
         the compiler's exit status. On Windows run it from a vcvars64 environment.

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
    new += (["/c", "/Fo" + obj, src] if msvc else ["-c", "-o", obj, src])
    print(json.dumps({"directory": e["directory"], "argv": new}))
    if a.exec_:
        os.makedirs(os.path.dirname(obj), exist_ok=True)
        return subprocess.call(new, cwd=e["directory"])
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
    a = ap.parse_args()
    return cmd_show(a) if a.cmd == "show" else cmd_replay(a)


if __name__ == "__main__":
    sys.exit(main() or 0)
