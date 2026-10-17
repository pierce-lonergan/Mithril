#!/usr/bin/env python3
"""design_time_lines.py DIAG.log OUT.txt -- the design-time ClCompile command lines of a Visual Studio project, from
a diagnostic (-v:diag) MSBuild log of target GetClCommandLines (CLCommandLine task output items "ClCommandLines",
with metadata Files=...; the task builds command lines and runs no compiler). Writes the format of
flags/prefreeze/A-vs.design_time_cl_lines.txt ("cmd: <line>" then "files: <a;b;c>"), which x0_build.py msbuild reads.
x0final, 2026-10-16 (the x0prep capture of Hearth's lines was extracted by hand from the same kind of log).
Standard library only."""
import sys


def main():
    lines = open(sys.argv[1], encoding="utf-8", errors="replace").read().splitlines()
    out = ["# design-time ClCompile command lines (GetClCommandLines; no compiler run), from %s" % sys.argv[1]]
    n = 0
    for i, line in enumerate(lines):
        if line.strip() == "ClCommandLines=" and i + 2 < len(lines):
            cmd = lines[i + 1].strip()
            files = None
            for j in range(i + 2, min(i + 8, len(lines))):
                s = lines[j].strip()
                if s.startswith("Files="):
                    files = s[len("Files="):].split(" (TaskId")[0]
                    break
            if not files:
                continue
            out += ["cmd:   " + cmd, "files: " + files]
            n += 1
    with open(sys.argv[2], "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")
    print("design-time lines: %d" % n)
    return 0 if n else 1


if __name__ == "__main__":
    sys.exit(main())
