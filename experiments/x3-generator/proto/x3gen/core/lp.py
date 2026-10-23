"""The lane program: a structured SSA program of single-instruction calls (library L).

Every data operation is a Call naming exactly one isa entry. Integer index and pointer arithmetic
uses IX expressions, which carry no data from inputs. Statements carry a provenance id (the
primitive application that created them) and, for FP results and stores, a lane-map hint that the
checker treats as untrusted (DESIGN 4.3, 5.2).
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass(frozen=True)
class Var:
    name: str

    def __repr__(self):
        return self.name


@dataclass(frozen=True)
class IX:
    """Integer/pointer expression: op in + - * < <= == != min ?: (ternary) cast."""

    op: str
    args: tuple

    def __repr__(self):
        return "IX(%s %r)" % (self.op, self.args)


def ix(op, *a):
    return IX(op, tuple(a))


def add(a, b):
    if b == 0:
        return a
    if a == 0:
        return b
    return ix("+", a, b)


def mul(a, b):
    if a == 1:
        return b
    if b == 1:
        return a
    return ix("*", a, b)


@dataclass(frozen=True)
class Call:
    entry: str
    args: tuple

    def __repr__(self):
        return "%s(%s)" % (self.entry, ", ".join(repr(a) for a in self.args))


@dataclass(frozen=True)
class Idx:
    """Array element arr[i]."""

    arr: str
    index: Any


@dataclass
class Let:
    name: str
    ctype: str
    rhs: Any  # Call or IX/Var/int
    mut: bool = False
    prov: str = ""
    lanes: Optional[tuple] = None


@dataclass
class Set:
    target: Any  # Var or Idx
    rhs: Any
    prov: str = ""
    lanes: Optional[tuple] = None


@dataclass
class Arr:
    name: str
    ctype: str
    n: int
    prov: str = ""


@dataclass
class Do:
    call: Call
    prov: str = ""
    lanes: Optional[tuple] = None


@dataclass
class For:
    var: str
    ctype: str
    init: Any
    cond: Any
    step: Any
    body: List[Any]
    prov: str = ""
    declare: bool = True


@dataclass
class If:
    cond: Any
    then: List[Any]
    other: List[Any] = field(default_factory=list)
    prov: str = ""


@dataclass
class Comment:
    text: str


@dataclass
class Func:
    name: str
    params: tuple
    body: List[Any]
    meaning: str
    isa: str


@dataclass
class Program:
    """One generated translation unit."""

    isa: str
    guard: Optional[str]
    includes: tuple
    prelude: List[str]
    funcs: List[Func]
    header_lines: List[str]


def walk(stmts):
    for s in stmts:
        yield s
        if isinstance(s, For):
            yield from walk(s.body)
        elif isinstance(s, If):
            yield from walk(s.then)
            yield from walk(s.other)
