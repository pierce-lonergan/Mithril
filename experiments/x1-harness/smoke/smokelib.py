"""Shared helpers for the X1 smoke-run kit (development items only).

Stdlib only. Bit-exact IEEE binary32 arithmetic is modelled with Python floats (binary64): for
+, -, *, / and sqrt of binary32 operands, computing in binary64 and rounding once to binary32 gives
the correctly rounded binary32 result, because 53 >= 2 * 24 + 2 (double rounding is innocuous for
these five operations). Every task model uses only those operations, comparisons, and exact
integer arithmetic.
"""

from __future__ import annotations

import importlib.util
import math
import struct
from pathlib import Path

SMOKE_DIR = Path(__file__).resolve().parent
TASKS_DIR = SMOKE_DIR / "tasks"
CARDS_DIR = SMOKE_DIR / "cards"
HARNESS_DIR = SMOKE_DIR / "harness"

CANON_NAN_BITS = 0x7FC00000
INF = float("inf")

# The development task set, in a fixed order (task ids are stable; never reuse an id).
TASK_IDS = [
    "D-Q4-1",
    "D-Q4-2",
    "D-ACTQ-1",
    "D-NORM-1",
    "D-ROUTE-1",
    "D-ROUTE-2",
    "D-EVICT-1",
    "D-FMT-1",
]
ARMS = ["mithril", "rust"]
EXT = {"mithril": "mith", "rust": "rs"}


# ----------------------------------------------------------------------------- binary32 helpers

def f32(x: float) -> float:
    """Round a binary64 value to the nearest binary32 value (ties to even), with overflow to inf."""
    if x != x or x in (INF, -INF):
        return x
    try:
        return struct.unpack("<f", struct.pack("<f", x))[0]
    except OverflowError:
        # CPython packs with a C cast (round to nearest); it raises only when the rounded value is
        # infinite while x is finite, so the correctly rounded binary32 value is +-inf.
        return math.copysign(INF, x)


def bits(x: float) -> int:
    """binary32 bit pattern of x (x must already be a binary32 value). NaN -> canonical NaN bits."""
    if x != x:
        return CANON_NAN_BITS
    return struct.unpack("<I", struct.pack("<f", x))[0]


def from_bits(b: int) -> float:
    return struct.unpack("<f", struct.pack("<I", b & 0xFFFFFFFF))[0]


def f16_to_f32(h: int) -> float:
    """Exact widening of binary16 bits (NaN payloads are not preserved; models canonicalise NaN)."""
    return struct.unpack("<e", struct.pack("<H", h & 0xFFFF))[0]


def add(a: float, b: float) -> float:
    return f32(a + b)


def sub(a: float, b: float) -> float:
    return f32(a - b)


def mul(a: float, b: float) -> float:
    return f32(a * b)


def div(a: float, b: float) -> float:
    """IEEE division (no Python exceptions on a zero divisor)."""
    if b == 0.0:
        if a != a or a == 0.0:
            return float("nan")
        neg = (math.copysign(1.0, a) < 0) != (math.copysign(1.0, b) < 0)
        return -INF if neg else INF
    return f32(a / b)


def sqrt(a: float) -> float:
    if a != a or a < 0.0:
        return float("nan")
    if a == INF:
        return INF
    return f32(math.sqrt(a))  # sqrt(-0.0) == -0.0 in Python, as in IEEE


def canon_nan(x: float) -> float:
    return float("nan") if x != x else x


def hex32(x: float) -> str:
    """Driver output format for one binary32 value: 8 lowercase hex digits of its bits."""
    return "%08x" % bits(x)


def round_ties_even(x: float) -> float:
    """binary32 round-half-to-even of a binary32 value (Python's round() on floats is half-even)."""
    if x != x or x in (INF, -INF):
        return x
    r = float(round(x))
    if r == 0.0:
        return math.copysign(0.0, x)
    return r


def f32_to_i8_sat(x: float) -> int:
    """Rust's `as i8` from f32: NaN -> 0, saturating, truncating toward zero."""
    if x != x:
        return 0
    if x >= 127.0:
        return 127
    if x <= -128.0:
        return -128
    return int(x)  # truncation toward zero


# ----------------------------------------------------------------------------- the shared LCG

class Lcg:
    """The drivers' generator: s = s * 1664525 + 1013904223 (mod 2^32), returning the new state.

    The Rust and Mithril drivers implement the same function (x1h_next); the self-test checks that
    reference solutions agree with the Python models on every random case, which also checks that
    the three generators agree.
    """

    def __init__(self, seed: int):
        self.s = seed & 0xFFFFFFFF

    def next(self) -> int:
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return self.s


RUST_LCG = """fn x1h_next(s: &mut u32) -> u32 {
    *s = s.wrapping_mul(1664525).wrapping_add(1013904223);
    *s
}
"""

MITH_LCG = """fn x1h_next(s: &mut u32) -> u32 {
    *s = s.wrapping_mul(1664525).wrapping_add(1013904223);
    *s
}
"""


# ----------------------------------------------------------------------------- literal rendering

def lit_array(ty: str, values, per_line: int = 16) -> str:
    """`[v0, v1, ...]` with an explicit element type suffix on every element (works in both arms)."""
    vals = list(values)
    if not vals:
        return "[]"
    parts = [f"{v}{ty}" if not str(v).startswith("-") else f"({v}{ty})" for v in vals]
    # negative literals are parenthesised so `-1i8` never parses as a binary minus
    lines = []
    for i in range(0, len(parts), per_line):
        lines.append(", ".join(parts[i:i + per_line]))
    return "[" + ",\n        ".join(lines) + "]"


def typed_let(name: str, ty: str, values) -> str:
    vals = list(values)
    return f"let {name}: [{ty}; {len(vals)}] = {lit_array(ty, vals)};"


# ----------------------------------------------------------------------------- task loading

def load_task(task_id: str):
    """Import tasks/<id>/task.py as a module (each task directory is self-contained)."""
    path = TASKS_DIR / task_id / "task.py"
    spec = importlib.util.spec_from_file_location("x1smoke_task_" + task_id.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.TASK_DIR = path.parent
    return mod


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def task_file(task_id: str, rel: str) -> Path:
    return TASKS_DIR / task_id / rel


# ----------------------------------------------------------------------------- drivers

NONCE_PLACEHOLDER = "@@NONCE@@"


def rust_driver(task, cases, mode: str) -> str:
    """Rust crate root (main.rs) for `cases` (literal case dicts).

    mode "visible": `driver <k>` prints case k then the nonce line; `driver all` prints every case.
    mode "hidden": additionally runs the task's random cases (task.RANDOM) after the literals.
    Output: one line per case, then `N:<nonce>`. The nonce is substituted per run.
    """
    lines = [
        "// generated by the X1 smoke kit; harness-owned, never shown to the subject as editable",
        "#![allow(unused_imports, dead_code, unused_mut, unused_variables)]",
        "mod prelude;",
        "mod solution;",
        "use prelude::*;",
        "use solution::*;",
        "",
        RUST_LCG,
        task.RUST_HELPERS,
        "",
        "fn x1h_case(k: usize) -> String {",
        "    match k {",
    ]
    for k, c in enumerate(cases):
        lines.append(f"        {k} => {{ {task.rust_lit(c)} }}")
    lines += [
        "        _ => panic!(\"no such case\"),",
        "    }",
        "}",
        "",
        "fn main() {",
        "    let args: Vec<String> = std::env::args().collect();",
        f"    let n_lit: usize = {len(cases)};",
        "    if args.len() > 1 && args[1] != \"all\" {",
        "        let k: usize = args[1].parse().unwrap();",
        "        println!(\"{}\", x1h_case(k));",
        "    } else {",
        "        for k in 0..n_lit {",
        "            println!(\"{}\", x1h_case(k));",
        "        }",
    ]
    if mode == "hidden":
        n, seed0 = task.RANDOM["count"], task.RANDOM["seed0"]
        lines += [
            f"        for k in 0..{n}u32 {{",
            f"            println!(\"{{}}\", x1h_rand({seed0}u32 + k));",
            "        }",
        ]
    lines += [
        "    }",
        f"    println!(\"N:{NONCE_PLACEHOLDER}\");",
        "}",
        "",
    ]
    return "\n".join(lines)


def mith_driver(task, cases, mode: str) -> str:
    """Mithril driver file (a second user file next to the solution).

    mode "visible": entry `x1h_one_<k>` returns case k's output, then `|N:<nonce>`.
    mode "hidden": entry `x1h_all` returns every literal case, then the random cases, joined by
    `|`, then `|N:<nonce>`. `mithi run` prints the returned String (Debug-quoted).
    """
    out = [
        "// generated by the X1 smoke kit; harness-owned driver (not the subject's file)",
        MITH_LCG,
        task.MITH_HELPERS,
        "",
    ]
    for k, c in enumerate(cases):
        out += [
            f"fn x1h_case_{k}() -> String uses {{ alloc(Global) }} {{",
            f"    {task.mith_lit(c)}",
            "}",
            "",
        ]
    if mode == "visible":
        for k in range(len(cases)):
            out += [
                f"fn x1h_one_{k}() -> String uses {{ alloc(Global) }} {{",
                f"    let mut out = x1h_case_{k}();",
                f"    out.push_str(\"|N:{NONCE_PLACEHOLDER}\");",
                "    out",
                "}",
                "",
            ]
    else:
        out.append("fn x1h_all() -> String uses { alloc(Global) } {")
        out.append("    let mut out = String::new();")
        for k in range(len(cases)):
            out.append(f"    out.push_str(&x1h_case_{k}());")
            out.append("    out.push_str(\"|\");")
        n, seed0 = task.RANDOM["count"], task.RANDOM["seed0"]
        out += [
            f"    for k in 0..{n}u32 {{",
            f"        out.push_str(&x1h_rand({seed0}u32 + k));",
            "        out.push_str(\"|\");",
            "    }",
            f"    out.push_str(\"N:{NONCE_PLACEHOLDER}\");",
            "    out",
            "}",
            "",
        ]
    return "\n".join(out)


def hidden_cases(task):
    """Literal hidden cases: every visible case first (visible tests are a subset of the oracle,
    DESIGN 5.1), then the task's literal edge cases."""
    return list(task.visible_cases()) + list(task.hidden_literal_cases())


def expected_hidden(task):
    exp = [task.model(c) for c in hidden_cases(task)]
    n, seed0 = task.RANDOM["count"], task.RANDOM["seed0"]
    for k in range(n):
        exp.append(task.model(task.random_case(seed0 + k)))
    return exp
