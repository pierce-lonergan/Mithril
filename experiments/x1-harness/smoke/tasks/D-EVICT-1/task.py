"""D-EVICT-1 (T-EVICT), DEVELOPMENT item: LRU victim choice as a timing_only policy (S-EVICT-0).

Not sealed, not held out. The oracle here is the exact-victim part of S-EVICT-0's oracle only (no
replay simulator and no clock scan: a development item).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from smokelib import Lcg  # noqa: E402

TASK = {
    "id": "D-EVICT-1",
    "family": "T-EVICT",
    "split": "development",
    "title": "LRU victim choice as a timing_only policy (S-EVICT-0 shape)",
    "unit": "pick_victim",
    "grade": "timing_only",
}

RANDOM = {"count": 200, "seed0": 47000}


def model(case):
    now = case["now"]
    best = None
    for (sid, pinned, refs, loading, last) in case["slots"]:
        if pinned or refs != 0 or loading:
            continue
        age = now - last
        if best is None or age > best[0] or (age == best[0] and sid < best[1]):
            best = (age, sid)
    return "none" if best is None else str(best[1])


def visible_cases():
    return [
        {"now": 10, "slots": [(4, False, 0, False, 10)]},                          # age 0 is a candidate
        {"now": 8, "slots": [(9, False, 0, False, 3), (2, False, 0, False, 3), (5, True, 0, False, 0)]},
        {"now": 5, "slots": [(1, True, 0, False, 0), (2, False, 3, False, 0)]},     # no candidate
        {"now": 7, "slots": []},
    ]


def hidden_literal_cases():
    return [
        {"now": 100, "slots": [(7, False, 0, True, 0), (8, False, 0, False, 99)]},    # loading is not a candidate
        {"now": 0, "slots": [(3, False, 0, False, 0), (1, False, 0, False, 0)]},
        {"now": 2 ** 40, "slots": [(11, False, 0, False, 0), (12, False, 0, False, 2 ** 40)]},
        {"now": 50, "slots": [(4000000000, False, 0, False, 10), (3, False, 0, False, 10)]},
        {"now": 9, "slots": [(1, True, 0, True, 0), (2, True, 5, False, 0), (3, False, 1, True, 1)]},
    ]


def random_case(seed):
    r = Lcg(seed)
    n = (r.next() >> 16) % 13
    now = 1000 + (r.next() >> 16) % 1000
    off = (r.next() >> 16) % 101
    slots = []
    for i in range(n):
        sid = (i * 37 + off) % 101
        pinned = (r.next() >> 16) % 5 == 0
        x = r.next() >> 16
        refs = 1 + (x >> 4) % 3 if x % 4 == 0 else 0
        loading = (r.next() >> 16) % 6 == 0
        age = (r.next() >> 16) % 5
        slots.append((sid, pinned, refs, loading, now - age))
    return {"now": now, "slots": slots}


def describe(c):
    if not c["slots"]:
        return f"now = {c['now']}; slots = []"
    return f"now = {c['now']}; slots = [" + "; ".join(
        f"{{id: {s[0]}, pinned: {str(s[1]).lower()}, refs: {s[2]}, loading: {str(s[3]).lower()}, last_use: {s[4]}}}"
        for s in c["slots"]) + "]"


def rust_lit(c):
    calls = " ".join(f"x1h_push(&mut v, {s[0]}u32, {str(s[1]).lower()}, {s[2]}u32, {str(s[3]).lower()}, {s[4]}u64);"
                     for s in c["slots"])
    return f"let mut v = x1h_new(); {calls} x1h_run(&v, {c['now']}u64)"


mith_lit = rust_lit

RUST_HELPERS = r"""
fn x1h_new() -> Vec<SlotView> { Vec::new() }

fn x1h_push(v: &mut Vec<SlotView>, id: u32, pinned: bool, refs: u32, loading: bool, last: u64) {
    v.push(SlotView { id: id, pinned: pinned, refs: refs, loading: loading, last_use: last });
}

fn x1h_run(v: &Vec<SlotView>, now: u64) -> String {
    match pick_victim(v, now) {
        Some(id) => format!("{}", id),
        None => "none".to_string(),
    }
}

fn x1h_rand(seed: u32) -> String {
    let mut s = seed;
    let n = (x1h_next(&mut s) >> 16) % 13;
    let now = 1000 + ((x1h_next(&mut s) >> 16) % 1000) as u64;
    let off = (x1h_next(&mut s) >> 16) % 101;
    let mut v = x1h_new();
    for i in 0..n {
        let id = (i * 37 + off) % 101;
        let pinned = (x1h_next(&mut s) >> 16) % 5 == 0;
        let x = x1h_next(&mut s) >> 16;
        let refs = if x % 4 == 0 { 1 + (x >> 4) % 3 } else { 0 };
        let loading = (x1h_next(&mut s) >> 16) % 6 == 0;
        let age = ((x1h_next(&mut s) >> 16) % 5) as u64;
        x1h_push(&mut v, id, pinned, refs, loading, now - age);
    }
    x1h_run(&v, now)
}
"""

MITH_HELPERS = r"""
fn x1h_new() -> Vec<SlotView> { Vec::new() }

fn x1h_push(v: &mut Vec<SlotView>, id: u32, pinned: bool, refs: u32, loading: bool, last: u64) uses { alloc(Global) } {
    v.push(SlotView { id: SlotId(id), pinned: pinned, refs: refs, loading: loading, last_use: Tick(last) });
}

fn x1h_run(v: &Vec<SlotView>, now: u64) -> String uses { alloc(Global) } {
    let h = pick_victim(v, Tick(now));
    match h.get() {
        Some(id) => format!("{}", id.0),
        None => "none".to_string(),
    }
}

fn x1h_rand(seed: u32) -> String uses { alloc(Global) } {
    let mut s = seed;
    let n = (x1h_next(&mut s) >> 16) % 13;
    let now = 1000 + ((x1h_next(&mut s) >> 16) % 1000) as u64;
    let off = (x1h_next(&mut s) >> 16) % 101;
    let mut v = x1h_new();
    for i in 0..n {
        let id = (i * 37 + off) % 101;
        let pinned = (x1h_next(&mut s) >> 16) % 5 == 0;
        let x = x1h_next(&mut s) >> 16;
        let refs = if x % 4 == 0 { 1 + (x >> 4) % 3 } else { 0 };
        let loading = (x1h_next(&mut s) >> 16) % 6 == 0;
        let age = ((x1h_next(&mut s) >> 16) % 5) as u64;
        x1h_push(&mut v, id, pinned, refs, loading, now - age);
    }
    x1h_run(&v, now)
}
"""
