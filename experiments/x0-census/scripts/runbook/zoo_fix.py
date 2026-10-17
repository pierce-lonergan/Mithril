"""Read clang error logs from the zoo compile; append the intrinsics named in failing wrappers to exclude.txt."""
import re, sys, os
z = sys.argv[1]
ex = os.path.join(z, "exclude.txt")
names = set(l.strip() for l in open(ex)) if os.path.exists(ex) else set()
src = {}
for f in ("zoo_avx.c", "zoo_sse.c"):
    src[f] = open(os.path.join(z, f)).read().split("\n")
new = set()
for log, f in (("zoo_avx.log", "zoo_avx.c"), ("zoo_sse.log", "zoo_sse.c")):
    p = os.path.join(z, log)
    if not os.path.exists(p):
        continue
    for line in open(p, errors="replace"):
        m = re.match(r"^%s\((\d+),\d+\): error" % re.escape(f), line)
        if m:
            ln = int(m.group(1))
            mm = re.search(r"return (_mm\w+|_\w+)\(|\{ (_mm\w+|_\w+)\(", src[f][ln - 1])
            if mm:
                new.add(mm.group(1) or mm.group(2))
names |= new
open(ex, "w").write("\n".join(sorted(names)) + "\n")
print("new exclusions:", len(new), sorted(new)[:20])
