"""Schedule primitives P1-P15 of P_X3 (DESIGN 4.2), each with its own precondition check (library L).

A schedule is a script of primitive applications over a clone of the meaning's loop tree. Every
application is logged with a provenance id and the facts its check established. These checks are
the first line of defence; the global checks C1-C4 (check.py) re-validate the final lane program
and carry soundness (DESIGN 4.3: "validate the output, not each rewrite").

Loop roles come from the meaning's variable names: the first letter of a loop variable names the
meaning loop it came from (splits append suffixes), so every piece of a split FP-carried loop stays
FP-carried (DESIGN 4.2, P2).
"""

import copy

from .ir import Init, Loop, Region, Spec, Store, Update, iter_nodes, parent_of, walk

ALLOWED_SPEC = {("T", "==", 1)}  # P8; tail predicates are created by splits themselves
CANON_LOWERINGS = {"blendv", "mask_mov", "branch"}  # P13
STORE_KINDS = {"full", "mask", "kmask"}


class PrimError(Exception):
    """A primitive's precondition failed: the schedule is rejected."""


def role(var):
    return var.split("_")[0]


class Log:
    def __init__(self):
        self.apps = []

    def add(self, prim, args, facts):
        pid = "%s#%d" % (prim, len(self.apps) + 1)
        self.apps.append({"id": pid, "prim": prim, "args": args, "facts": facts})
        return pid

    def ids(self):
        return {a["id"] for a in self.apps}


def _is_child(parent: Loop, node) -> bool:
    return any(x is node for x in parent.body)


class View:
    """A schedule restricted to some subtrees (the whole kernel, or one branch of a Spec)."""

    def __init__(self, sched, roots):
        self.s = sched
        self.roots = roots

    # ------------------------------------------------------------ lookup helpers
    def _nodes(self):
        for root in self.roots:
            yield from iter_nodes(root)

    def _loops(self, var):
        return [n for n in self._nodes() if isinstance(n, Loop) and n.var == var]

    def loop(self, var) -> Loop:
        ls = self._loops(var)
        if len(ls) != 1:
            raise PrimError("loop %r: %d found in this view" % (var, len(ls)))
        return ls[0]

    def _container(self, node):
        r = parent_of(self.s.k.body, node)
        if not r:
            raise PrimError("node not found in the kernel")
        return r

    def _parent_loop(self, node):
        for n in iter_nodes(self.s.k.body):
            if isinstance(n, Loop) and _is_child(n, node):
                return n
        return None

    def fp_carried(self, lp: Loop) -> bool:
        return lp.kind == "seq" and self.s.carried.get(role(lp.var), False)

    # ------------------------------------------------------------ P1 split, P6 tail
    def split(self, var, k, tail="guard"):
        lp = self.loop(var)
        if not isinstance(k, int) or k <= 0:
            raise PrimError("P1: split factor must be a positive constant")
        if tail not in ("guard", "dup_last", "cut"):
            raise PrimError("P6: unknown tail strategy %r" % tail)
        if tail == "dup_last" and lp.kind != "out":
            raise PrimError("P6: dup_last only on an output loop (dead lanes recompute a live row)")
        facts = [
            "P1: %s = %s_o + %s_i is an order-preserving bijection (lexicographic)" % ((var,) * 3)
        ]
        inner = Loop(var + "_i", 0, k, lp.kind, lp.body, origin=(var + "_o", k))
        outer = Loop(
            var + "_o", lp.lo, lp.hi, lp.kind, [inner], step=k, tail=tail, prov=list(lp.prov)
        )
        cont, i = self._container(lp)
        made = [outer, inner]
        if tail == "cut":
            outer.only_full = True
            rem = Loop(
                var + "_t",
                ("cont", var + "_o"),
                lp.hi,
                lp.kind,
                copy.deepcopy(lp.body),
                prov=list(lp.prov),
            )
            facts.append(
                "P6: the main loop runs whole tiles; the remainder starts where it stopped "
                "and ends at the bound, so [lo, hi) is covered once, in increasing order"
            )
            regions = [Region("main", [outer]), Region("rest", [rem])]
            cont[i : i + 1] = regions
            made.append(rem)
        else:
            facts.append("P6: tail %s covers (hi - lo) mod %d exactly once" % (tail, k))
            cont[i] = outer
        pid = self.s.log.add("P1.split", (var, k, tail), facts)
        for n in made:
            n.prov.append(pid)
        if tail == "cut":
            return View(self.s, [regions[0].body]), View(self.s, [regions[1].body])
        return pid

    # ------------------------------------------------------------ P2 reorder
    def _reorder_node(self, a: Loop):
        if len(a.body) != 1 or not isinstance(a.body[0], Loop):
            raise PrimError("P2: %s is not a perfect nest" % a.var)
        b = a.body[0]
        fa, fb = self.fp_carried(a), self.fp_carried(b)
        if fa and fb:
            raise PrimError("P2: interchange of two FP-carried loops (%s, %s)" % (a.var, b.var))
        facts = ["P2: at most one of %s, %s is FP-carried; no loop is reversed" % (a.var, b.var)]
        if fa or fb:
            other = a if fb else b
            if other.lanes:
                raise PrimError("P2: moving a lane loop across an FP-carried loop")
            for n in iter_nodes([b]):
                if isinstance(n, Update) and other.var not in n.expanded_over:
                    raise PrimError("P2: accumulator %s is not private to %s" % (n.acc, other.var))
            facts.append("P2: every accumulator in the body is private to %s" % other.var)
        cont, i = self._container(a)
        a.body, b.body = b.body, [a]
        cont[i] = b
        pid = self.s.log.add("P2.reorder", (a.var, b.var), facts)
        a.prov.append(pid)
        b.prov.append(pid)
        return pid

    def reorder(self, outer_var, inner_var):
        a = self.loop(outer_var)
        if len(a.body) != 1 or not isinstance(a.body[0], Loop) or a.body[0].var != inner_var:
            raise PrimError("P2: %s does not directly enclose %s" % (outer_var, inner_var))
        return self._reorder_node(a)

    # ------------------------------------------------------------ P3 expand
    def _expand_node(self, lp: Loop, accname):
        if self.fp_carried(lp):
            raise PrimError("P3: cannot expand over an FP-carried loop")
        inits = [n for n in iter_nodes(lp.body) if isinstance(n, Init) and n.acc == accname]
        if not inits:
            raise PrimError("P3: %s is not re-initialised inside %s" % (accname, lp.var))
        for n in iter_nodes(lp.body):
            uses = (
                n.acc == accname
                if isinstance(n, (Init, Update))
                else (
                    isinstance(n, Store)
                    and any(e.op == "acc" and e.args[0] == accname for e in walk(n.value))
                )
            )
            if uses:
                n.expanded_over = n.expanded_over + (lp.var,)
        pid = self.s.log.add(
            "P3.expand",
            (accname, lp.var),
            ["P3: %s re-initialised in every iteration of %s" % (accname, lp.var)],
        )
        for n in iter_nodes(lp.body):
            if isinstance(n, (Init, Update, Store)) and lp.var in n.expanded_over:
                n.prov.append(pid)
        return pid

    def expand(self, accname, over):
        return self._expand_node(self.loop(over), accname)

    # ------------------------------------------------------------ P2, distribution form
    def _distribute_node(self, lp: Loop):
        if self.fp_carried(lp):
            raise PrimError("P2: distribution of an FP-carried loop")
        for n in iter_nodes(lp.body):
            if isinstance(n, (Init, Update)) and lp.var not in n.expanded_over:
                raise PrimError("P2: %s not expanded over %s before distribution" % (n.acc, lp.var))
        cont, i = self._container(lp)
        pieces = [
            Loop(lp.var, lp.lo, lp.hi, lp.kind, [st], origin=lp.origin, prov=list(lp.prov))
            for st in lp.body
        ]
        cont[i : i + 1] = pieces
        pid = self.s.log.add(
            "P2.distribute",
            (lp.var,),
            ["P2: state private per iteration; statement order kept per chain"],
        )
        for p in pieces:
            p.prov.append(pid)
        return pieces, pid

    # ------------------------------------------------------------ P4 vectorize
    def vectorize(self, var, lanes, width, layout="rows", store="full"):
        lp = self.loop(var)
        if lp.kind != "out":
            raise PrimError("P4: only loops over independent outputs may be vectorised")
        if lp.origin is None or lp.origin[1] != lanes or lp.lo != 0 or lp.hi != lanes:
            raise PrimError("P4: lane count must equal the split factor of %s" % var)
        if store not in STORE_KINDS:
            raise PrimError("P4: unknown store kind")
        outer = [
            n for n in iter_nodes(self.s.k.body) if isinstance(n, Loop) and n.var == lp.origin[0]
        ]
        tails = {o.tail for o in outer}
        if "dup_last" in tails and store == "full":
            raise PrimError("P6: dup_last tiles must store with a mask (dead lanes never stored)")
        if "guard" in tails:
            raise PrimError("P6: a vector tile needs dup_last or cut, not guard")
        if not any(isinstance(n, Init) for n in iter_nodes(lp.body)):
            raise PrimError("P4: accumulators must be initialised inside the lane loop")
        rv = role(var)
        for n in iter_nodes(lp.body):
            if isinstance(n, (Update, Store, Init)):
                for e in walk(n.value):
                    if rv in e.args and e.op not in ("wq", "wd"):
                        raise PrimError("P4: %s mixes lanes through %s" % (var, e.op))
        lp.lanes, lp.vec = lanes, {"width": width, "layout": layout, "store": store}
        return self.s.log.add(
            "P4.vectorize",
            (var, lanes, width, layout, store),
            [
                "P4: lane k = output %s+k; the lane variable reaches only per-row leaves and the "
                "store index, so no FP op reads two lanes" % rv
            ],
        )

    # ------------------------------------------------------------ P7 unroll
    def unroll(self, var, u=-1):
        lp = self.loop(var)
        if lp.origin is None and not (isinstance(lp.lo, int) and isinstance(lp.hi, int)):
            raise PrimError("P7: unroll needs a constant trip count")
        # lower.py has no unrolling: logging "iterations composed in order" would record a fact
        # with no effect on the program, so P7 refuses every application until lowering does it.
        raise PrimError("P7: unroll is not lowered in this prototype")

    # ------------------------------------------------------------ P8 specialize
    def specialize(self, var, pred):
        if pred not in ALLOWED_SPEC:
            raise PrimError("P8/B12: specialisation on %r is not allowed" % (pred,))
        lp = self.loop(var)
        cont, i = self._container(lp)
        sp = Spec(pred, [copy.deepcopy(lp)], [copy.deepcopy(lp)])
        cont[i] = sp
        pid = self.s.log.add(
            "P8.specialize", (var, pred), ["P8: both copies are the same program on a sub-domain"]
        )
        sp.prov.append(pid)
        return View(self.s, [sp.then]), View(self.s, [sp.other])

    # ------------------------------------------------------------ P9 hoist
    def hoist(self, what, out_of):
        if role(out_of) != "t":
            raise PrimError("P9: this prototype hoists weight work out of token loops only")
        if tuple(what) != ("W",):
            raise PrimError("P9: only loads of the read-only weight input are hoistable")
        if "Y disjoint from W and A" not in self.s.k.requires:
            raise PrimError(
                "P9: needs the read-only/no-alias precondition (DESIGN 3.3 P4, meaning PRE4)"
            )
        cands = []
        for lp in self._loops(out_of):
            par = self._parent_loop(lp)
            if par is not None and role(par.var) == "g":
                cands.append((par, lp))
        if len(cands) != 1:
            raise PrimError("P9: %s must sit directly inside exactly one block loop" % out_of)
        g, lp = cands[0]
        if lp.origin is None:
            raise PrimError("P9: hoist only out of a blocked token loop (trip count >= 1 proven)")
        g.hoist = tuple(what)
        return self.s.log.add(
            "P9.hoist",
            (tuple(what), out_of),
            [
                "P9: W-only subterms (wq, wd of the tile rows) do not mention %s; W is read-only; the "
                "token loop runs >= 1 time whenever its block body runs (guarded split)" % out_of
            ],
        )

    # ------------------------------------------------------------ P10 block
    def block(self, var, b, lanes_var):
        """Register blocking of an output loop around a vectorised row tile:
        split(var, b) ; reorder(var_i, lanes_var) ; expand(acc, var_i) ; distribute(var_i) ;
        reorder(var_i, g). Every step runs its own check."""
        ids = [self.split(var, b, "guard")]
        vi = var + "_i"
        a = self.loop(vi)
        if len(a.body) != 1 or not isinstance(a.body[0], Loop) or a.body[0].var != lanes_var:
            raise PrimError("P10: %s must directly enclose %s" % (vi, lanes_var))
        ids.append(self._reorder_node(a))
        ids.append(self._expand_node(a, "acc"))
        pieces, pid = self._distribute_node(a)
        ids.append(pid)
        gpieces = [p for p in pieces if isinstance(p.body[0], Loop) and role(p.body[0].var) == "g"]
        if len(gpieces) != 1:
            raise PrimError("P10: block loop not found after distribution")
        ids.append(self._reorder_node(gpieces[0]))
        return self.s.log.add(
            "P10.block", (var, b, lanes_var), ["P10: composite of " + ", ".join(ids)]
        )

    # ------------------------------------------------------------ P5, P13, P14, P11, P15
    def _updates(self):
        return [n for n in self._nodes() if isinstance(n, Update)]

    def _stores(self):
        return [n for n in self._nodes() if isinstance(n, Store)]

    def lower_isum(self, using, **opts):
        from . import recipes

        ups = self._updates()
        if not ups:
            raise PrimError("P5: no exact_sum in this view")
        facts = recipes.check_isum(self.s.k, using, opts)
        pid = self.s.log.add("P5.lower_isum", (using, tuple(sorted(opts.items()))), facts)
        for u in ups:
            u.__dict__.setdefault("lower", {})["isum"] = (using, dict(opts), pid)
        return pid

    def load_scales(self, pack="gpr64", convert="cvtph"):
        if (pack, convert) not in (("gpr64", "cvtph"), ("scalar", "h2f_bits")):
            raise PrimError("P14: unknown scale packing")
        pid = self.s.log.add(
            "P14.load_scales",
            (pack, convert),
            ["P14: integer packing of f16 bit patterns, then exact widening"],
        )
        for u in self._updates():
            u.__dict__.setdefault("lower", {})["scales"] = (pack, convert, pid)
        return pid

    def canon_store(self, lowering):
        if lowering not in CANON_LOWERINGS:
            raise PrimError(
                "P13: canon lowering %r not in %s" % (lowering, sorted(CANON_LOWERINGS))
            )
        pid = self.s.log.add(
            "P13.canon_store",
            (lowering,),
            [
                "P13: selector cmp_unord(v, v) on the stored value, replacement the "
                "canonical NaN in every lane (lifting rule, re-checked by C1)"
            ],
        )
        for st in self._stores():
            st.__dict__.setdefault("lower", {})["canon"] = (lowering, pid)
        return pid

    def prefetch(self, buf, ahead):
        if buf != "W" or not isinstance(ahead, int) or ahead <= 0:
            raise PrimError("P11: prefetch of the weight stream only, at a positive distance")
        pid = self.s.log.add("P11.prefetch", (buf, ahead), ["P11: inserts _mm_prefetch only"])
        for lp in self._nodes():
            if isinstance(lp, Loop) and role(lp.var) == "g":
                lp.vec = dict(lp.vec, prefetch=(ahead, pid))
        return pid

    def commute(self, op):
        if op not in ("fadd", "fmul"):
            raise PrimError("P15: commutation of %s" % op)
        stores = self._stores()
        if not stores or any("canon" not in s.__dict__.get("lower", {}) for s in stores):
            # Commutation is IEEE-exact except for the NaN payload, which only canon at the sink
            # erases (DESIGN 4.2, P15; 03 6.3): every store of the view must already carry P13.
            raise PrimError("P15: commutation needs canon (P13) at every store of the view")
        return self.s.log.add(
            "P15.commute",
            (op,),
            [
                "P15: the chain has no NaN-observing consumer before canon; P13 canon is applied "
                "at every store, so the NaN payload is erased at the sink"
            ],
        )


class Schedule(View):
    def __init__(self, kernel, isa):
        self.k = kernel.clone()
        self.isa = isa
        self.log = Log()
        self.carried = {}
        for n in iter_nodes(self.k.body):
            if isinstance(n, Loop) and n.kind == "seq":
                self.carried[role(n.var)] = True
        View.__init__(self, self, [self.k.body])
        self.implicit = self.log.add(
            "P12.map_fp",
            ("table",),
            [
                "P12: each meaning FP op maps to the isa entry whose 'ieee' "
                "field names it, lane-wise, RNE under PRE3"
            ],
        )
