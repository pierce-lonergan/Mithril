"""init_one.py DRIVER RUN RECORD STUB|REAL SOURCE -- run `x0_driver.py init --kind census` of the x0_driver.py at
DRIVER (inside a THROWAWAY git repository). With STUB the two Hearth source checks (source_blob_check,
source_commit) are replaced by stubs that report the pinned blobs and commit, so the freeze-point git logic
(freeze_checkout) runs without any Hearth tree; with REAL the source tree SOURCE is checked as the census would.
Nothing is compiled or decoded; init only reads files and git metadata and writes RUN/run.json."""
import importlib.util
import os
import sys

drv, run, record, mode, source = sys.argv[1:6]
spec = importlib.util.spec_from_file_location("x0_driver", drv)
m = importlib.util.module_from_spec(spec)
sys.modules["x0_driver"] = m
spec.loader.exec_module(m)
if mode == "STUB":
    want = (m.jload(os.path.join(m.ROOT, "class", "B_iform.json"), {}).get("inputs") or {}).get("hearth_commit")
    m.source_blob_check = lambda s: ({"STUB": {"pinned": "stub", "found": "stub", "ok": True}}, True)
    m.source_commit = lambda s: want
sys.argv = [drv, "init", "--run", run, "--kind", "census", "--source", source, "--record", record]
sys.exit(m.main())
