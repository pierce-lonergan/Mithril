"""x0_norm.py -- map an llvm-objdump (Intel syntax) instruction text to the set of XED iclasses it may
denote, using the frozen table class/objdump_norm.csv (record §7, cross-decoder check). Library only.

Table rows (kind, objdump, xed_iclasses, note):
  merge  TOKEN       a prefix that llvm-objdump may print as its own line (e.g. 'lock'); merge_lines() joins it
                     with the next line before comparison
  strip  TOKEN       a prefix token printed before the mnemonic that XED folds into the same iclass
  prefix TOKEN SET   a prefix token that changes the iclass; SET uses {X} for the iclass(es) of the rest
  alias  MNEM  SET   exact (lower-case) mnemonic -> '|'-separated iclasses
  regex  RX    SET   re.fullmatch on the lower-case mnemonic; {n} = upper-cased group n
Default when no alias or regex row matches: the mnemonic upper-cased.
The check passes when XED's iclass is in the returned set.
"""
import csv
import re


class Normalizer:
    def __init__(self, path):
        self.strip, self.prefix, self.alias, self.regex, self.merge = set(), {}, {}, [], set()
        with open(path, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                k, od, x = r["kind"], r["objdump"], r["xed_iclasses"]
                if k == "merge":
                    self.merge.add(od)
                elif k == "strip":
                    self.strip.add(od)
                elif k == "prefix":
                    self.prefix[od] = x.split("|")
                elif k == "alias":
                    if od in self.alias:
                        raise ValueError("duplicate alias %s" % od)
                    self.alias[od] = x.split("|")
                elif k == "regex":
                    self.regex.append((re.compile(od), x.split("|")))
                else:
                    raise ValueError("unknown kind %r" % k)

    def _base(self, mnem):
        if mnem in self.alias:
            return set(self.alias[mnem])
        for rx, tmpl in self.regex:
            m = rx.fullmatch(mnem)
            if m:
                out = set()
                for t in tmpl:
                    for i, g in enumerate(m.groups(), 1):
                        t = t.replace("{%d}" % i, (g or "").upper())
                    out.add(t)
                return out
        return {mnem.upper()}

    def iclasses(self, text):
        """Return (set of acceptable XED iclasses, mnemonic) for one instruction's text, or (None, None) for
        '<unknown>' or empty text."""
        toks = text.replace("\t", " ").split()
        prefixes = []
        while toks and (toks[0] in self.strip or toks[0] in self.prefix):
            if toks[0] in self.prefix:
                prefixes.append(toks[0])
            toks = toks[1:]
        if not toks or toks[0].startswith("<unknown"):
            return None, None
        mnem = toks[0].lower()
        acc = self._base(mnem)
        for p in reversed(prefixes):
            acc = {t.replace("{X}", x) for t in self.prefix[p] for x in acc}
        return acc, mnem

    def merge_lines(self, insts):
        """insts: {offset: (length, text)} from llvm-objdump. A line whose text is a single 'merge' prefix
        token is joined with the line that follows it at offset+length (repeatedly), giving
        {offset: (total length, 'prefix ... text')}. Other lines are returned unchanged."""
        out, offs, consumed = {}, sorted(insts), set()
        for o in offs:
            if o in consumed:
                continue
            ln, txt = insts[o]
            cur = o + ln
            while txt.split() and all(t in self.merge for t in txt.split()) and cur in insts:
                nln, ntxt = insts[cur]
                consumed.add(cur)
                txt, ln, cur = txt + " " + ntxt, ln + nln, cur + nln
            out[o] = (ln, txt)
        return out
