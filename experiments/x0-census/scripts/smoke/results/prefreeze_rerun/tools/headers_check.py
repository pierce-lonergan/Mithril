"""headers_check.py SCRIPTS_DIR CENSUS.json [...] -- every configuration's recorded header environment
(census.json configs.<cfg>.headers, written by x0_driver.py) against class/frozen_inputs.json "headers" of its base
configuration (P.<CFG> -> <CFG>; B-proxy -> B-cmake's Windows SDK/UCRT/toolset and clang-cl resource dir), with
judge.headers_mismatch. Also lists the compiler pin check of every build record."""
import json
import os
import sys

scripts = sys.argv[1]
sys.path.insert(0, scripts)
import judge  # noqa: E402

pins = json.load(open(os.path.join(os.path.dirname(scripts), "class", "frozen_inputs.json"), encoding="utf-8"))
hp, cp = pins["headers"], pins["compilers"]
bad_total = 0
for path in sys.argv[2:]:
    c = json.load(open(path, encoding="utf-8"))
    print("==", path, c["record"].get("id"), c["record"].get("profile"))
    for cfg, x in sorted(c["configs"].items()):
        base = cfg.split(".")[-1]
        base = "B-cmake" if base == "B-proxy" else base
        h = x.get("headers") or {}
        bad = judge.headers_mismatch(h, hp.get(base))
        rd = h.get("resource_dir_sha256")
        bs = [b for b in c["builds"] if b.get("config") == cfg]
        cbad = [(b["file"], b["build_index"]) for b in bs if b.get("compiler_sha256") != cp.get(cfg.split(".")[-1], cp.get(base))]
        bad_total += len(bad)
        print("  %-10s pin=%-8s headers_mismatch=%s sdk=%s ucrt=%s vctools=%s libc_dev=%s resource_dir=%s builds=%d compiler_pin_mismatch=%s"
              % (cfg, base, bad or "none", h.get("sdk"), h.get("ucrt"), h.get("vctools"), h.get("libc_dev"),
                 ("%s files %s" % (rd.get("files"), rd.get("sha256")[:12])) if isinstance(rd, dict) else rd, len(bs), cbad or "none"))
print("TOTAL_HEADER_MISMATCHES", bad_total)
