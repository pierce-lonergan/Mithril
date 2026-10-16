"""Read `clang -###` / `clang-cl -###` output on stdin; print the cc1 flags that matter for FP and ISA.

Usage: clang-cl /fp:precise -### -c x.c 2>&1 | python -I cc1flags.py
"""
import re
import sys

KEEP = re.compile(r"^(-O\d|-ffp-contract=.*|-f(no-)?rounding-math|-ffp-exception-behavior=.*|-fmath-errno|"
                  r"-ffast-math|-menable-no-.*|-fapprox-func|-freciprocal-math|-fno-signed-zeros|"
                  r"-ffp-eval-method=.*|-complex-range=.*|-ffunction-sections|-vectorize-.*|-stack-protector)$")
for line in sys.stdin:
    if "-cc1" not in line:
        continue
    toks = re.findall(r'"((?:[^"\\]|\\.)*)"', line)
    out = []
    for i, t in enumerate(toks):
        if t in ("-target-cpu", "-tune-cpu", "-stack-protector") and i + 1 < len(toks):
            out.append("%s=%s" % (t, toks[i + 1]))
        elif t == "-target-feature" and i + 1 < len(toks):
            out.append("+feature:" + toks[i + 1])
        elif KEEP.match(t):
            out.append(t)
    print(" ".join(out))
