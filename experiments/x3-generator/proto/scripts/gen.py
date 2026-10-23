"""Generate the six X3 prototype variants: python -I scripts/gen.py OUT_DIR (run from proto/)."""

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from x3gen.core import emit  # noqa: E402
from x3gen.hearth import meaning  # noqa: E402
from x3gen.hearth.schedules import avx2, avx512, scalar  # noqa: E402

SCHED = {"scalar": scalar.schedule, "avx2": avx2.schedule, "avx512": avx512.schedule}
FILES = {k: ROOT / "x3gen" / "hearth" / "schedules" / (k + ".py") for k in SCHED}


def main(out_dir):
    out, report = emit.build(
        meaning.MEANINGS, SCHED, ROOT / "x3gen" / "hearth" / "meaning.py", FILES
    )
    emit.write(out, report, out_dir)
    for name, h in sorted(report["files"].items()):
        print(name, h)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "generated"))
