"""x0obj.py -- minimal, dependency-free reader for x86-64 ELF64 and COFF (incl. bigobj) objects.

Used by x0_extract.py. Returns plain dicts so results serialise straight to JSON.
Only what the X0 census needs: sections, symbols, relocations, raw bytes.
"""
import struct

# ---------------------------------------------------------------- ELF

SHT_PROGBITS, SHT_SYMTAB, SHT_RELA, SHT_REL, SHT_GROUP, SHT_SYMTAB_SHNDX = 1, 2, 4, 9, 17, 18
SHF_EXECINSTR, SHF_GROUP = 0x4, 0x200
STT_NAMES = {0: "notype", 1: "object", 2: "func", 3: "section", 4: "file", 6: "tls", 10: "gnu_ifunc"}
STB_NAMES = {0: "local", 1: "global", 2: "weak", 10: "gnu_unique"}
SHN_UNDEF, SHN_LORESERVE, SHN_ABS, SHN_COMMON, SHN_XINDEX = 0, 0xFF00, 0xFFF1, 0xFFF2, 0xFFFF

R_X86_64_NAMES = {
    0: "NONE", 1: "64", 2: "PC32", 3: "GOT32", 4: "PLT32", 9: "GOTPCREL", 10: "32", 11: "32S",
    24: "PC64", 41: "GOTPCRELX", 42: "REX_GOTPCRELX",
}


def _cstr(blob, off):
    end = blob.index(b"\0", off)
    return blob[off:end].decode("utf-8", "replace")


def parse_elf(data):
    if data[:4] != b"\x7fELF":
        raise ValueError("not ELF")
    if data[4] != 2 or data[5] != 1:
        raise ValueError("only ELF64 little-endian is supported")
    (e_type, e_machine, _ver, _entry, _phoff, e_shoff, _flags, _ehsize, _phentsize, _phnum,
     e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    if e_machine != 62:
        raise ValueError("ELF machine %d is not x86-64" % e_machine)
    raw = []
    if e_shnum == 0 and e_shoff:
        e_shnum = struct.unpack_from("<Q", data, e_shoff + 32)[0]  # sh_size of section 0
    if e_shstrndx == SHN_XINDEX:
        e_shstrndx = struct.unpack_from("<I", data, e_shoff + 40)[0]  # sh_link of section 0
    for i in range(e_shnum):
        raw.append(struct.unpack_from("<IIQQQQIIQQ", data, e_shoff + i * e_shentsize))
    shstr_off, shstr_size = raw[e_shstrndx][4], raw[e_shstrndx][5]
    shstr = data[shstr_off:shstr_off + shstr_size]
    sections = []
    for i, (nm, typ, flg, addr, off, size, link, info, align, entsize) in enumerate(raw):
        sections.append({
            "index": i, "name": _cstr(shstr, nm), "type": typ, "flags": flg, "addr": addr,
            "offset": off, "size": size, "link": link, "info": info, "align": align,
            "entsize": entsize, "is_code": bool(flg & SHF_EXECINSTR) and typ == SHT_PROGBITS,
            "in_group": bool(flg & SHF_GROUP), "comdat": None,
        })
    # COMDAT groups
    for s in sections:
        if s["type"] == SHT_GROUP:
            words = struct.unpack_from("<%dI" % (s["size"] // 4), data, s["offset"])
            for m in words[1:]:
                if m < len(sections):
                    sections[m]["comdat"] = {"group_section": s["index"], "flags": words[0]}
    # symbols
    symbols = []
    xindex = {}
    for s in sections:
        if s["type"] == SHT_SYMTAB_SHNDX:
            xindex[s["link"]] = struct.unpack_from("<%dI" % (s["size"] // 4), data, s["offset"])
    for s in sections:
        if s["type"] != SHT_SYMTAB:
            continue
        strs = sections[s["link"]]
        strtab = data[strs["offset"]:strs["offset"] + strs["size"]]
        n = s["size"] // 24
        for j in range(n):
            st_name, st_info, st_other, st_shndx, st_value, st_size = struct.unpack_from(
                "<IBBHQQ", data, s["offset"] + j * 24)
            if st_shndx == SHN_XINDEX:
                st_shndx = xindex.get(s["index"], [0] * n)[j]
            typ, bind = st_info & 0xF, st_info >> 4
            name = _cstr(strtab, st_name)
            if typ == 3 and not name and 0 < st_shndx < len(sections):
                name = sections[st_shndx]["name"]
            symbols.append({
                "index": j, "name": name, "value": st_value, "size": st_size,
                "type": STT_NAMES.get(typ, str(typ)), "bind": STB_NAMES.get(bind, str(bind)),
                "visibility": st_other & 3, "section": st_shndx,
                "defined": st_shndx != SHN_UNDEF and st_shndx < SHN_LORESERVE,
            })
    # relocations, keyed by target section
    relocs = {}
    for s in sections:
        if s["type"] not in (SHT_RELA, SHT_REL):
            continue
        ent = 24 if s["type"] == SHT_RELA else 16
        lst = relocs.setdefault(s["info"], [])
        for j in range(s["size"] // ent):
            if s["type"] == SHT_RELA:
                r_off, r_info, r_add = struct.unpack_from("<QQq", data, s["offset"] + j * ent)
            else:
                (r_off, r_info), r_add = struct.unpack_from("<QQ", data, s["offset"] + j * ent), 0
            rtype, rsym = r_info & 0xFFFFFFFF, r_info >> 32
            lst.append({"offset": r_off, "type": R_X86_64_NAMES.get(rtype, str(rtype)),
                        "type_id": rtype, "sym": rsym, "addend": r_add,
                        "width": 8 if rtype in (1, 24) else 4})
    kind = {1: "rel", 2: "exec", 3: "dyn"}.get(e_type, str(e_type))
    return {"format": "elf64", "kind": kind, "sections": sections, "symbols": symbols, "relocs": relocs}


# ---------------------------------------------------------------- COFF

IMAGE_SCN_CNT_CODE, IMAGE_SCN_LNK_COMDAT = 0x20, 0x1000
IMAGE_SCN_LNK_NRELOC_OVFL, IMAGE_SCN_MEM_EXECUTE = 0x01000000, 0x20000000
COFF_CLASS = {2: "external", 3: "static", 6: "label", 101: "function", 103: "file", 105: "weak_external"}
COFF_COMDAT_SEL = {1: "nodup", 2: "any", 3: "same_size", 4: "exact_match", 5: "associative", 6: "largest"}
IMAGE_REL_AMD64 = {0: "ABSOLUTE", 1: "ADDR64", 2: "ADDR32", 3: "ADDR32NB", 4: "REL32", 5: "REL32_1",
                   6: "REL32_2", 7: "REL32_3", 8: "REL32_4", 9: "REL32_5", 10: "SECTION", 11: "SECREL",
                   12: "SECREL7", 13: "TOKEN", 14: "SREL32"}


def parse_coff(data):
    sig1, sig2 = struct.unpack_from("<HH", data, 0)
    if sig1 == 0 and sig2 == 0xFFFF:  # bigobj
        (_v, machine, _ts) = struct.unpack_from("<HHI", data, 4)
        nsec, symptr, nsym = struct.unpack_from("<III", data, 44)
        hdr_size, sym_size, opt_size = 56, 20, 0
        bigobj = True
    else:
        machine, nsec, _ts, symptr, nsym, opt_size, _ch = struct.unpack_from("<HHIIIHH", data, 0)
        hdr_size, sym_size, bigobj = 20, 18, False
    if machine != 0x8664:
        raise ValueError("COFF machine 0x%x is not AMD64" % machine)
    strtab_off = symptr + nsym * sym_size
    strtab = data[strtab_off:] if symptr else b""

    def longname(raw8):
        if raw8[:4] == b"\0\0\0\0":
            return _cstr(strtab, struct.unpack_from("<I", raw8, 4)[0])
        return raw8.rstrip(b"\0").decode("utf-8", "replace")

    sections = [None]  # COFF section numbers are 1-based
    sec_base = hdr_size + opt_size
    for i in range(nsec):
        o = sec_base + i * 40
        raw_name = data[o:o + 8]
        (vsize, vaddr, rsize, rptr, relptr, _lnptr, nrel, _nln, chars) = struct.unpack_from("<IIIIIIHHI", data, o + 8)
        name = raw_name.rstrip(b"\0").decode("utf-8", "replace")
        if name.startswith("/") and name[1:].isdigit():
            name = _cstr(strtab, int(name[1:]))
        relocs = []
        if relptr and nrel:
            first = 0
            if (chars & IMAGE_SCN_LNK_NRELOC_OVFL) and nrel == 0xFFFF:
                nrel = struct.unpack_from("<I", data, relptr)[0]
                first = 1
            for j in range(first, nrel):
                r_va, r_sym, r_type = struct.unpack_from("<IIH", data, relptr + j * 10)
                relocs.append({"offset": r_va, "sym": r_sym, "type": IMAGE_REL_AMD64.get(r_type, str(r_type)),
                               "type_id": r_type, "addend": None, "width": 8 if r_type == 1 else (2 if r_type == 10 else 4)})
        sections.append({
            "index": i + 1, "name": name, "flags": chars, "offset": rptr, "size": rsize, "addr": 0,
            "align": 1 << (((chars >> 20) & 0xF) - 1) if (chars >> 20) & 0xF else 0,
            "is_code": bool(chars & (IMAGE_SCN_CNT_CODE | IMAGE_SCN_MEM_EXECUTE)),
            "comdat": None, "relocs": relocs,
        })
    symbols = []
    j = 0
    while j < nsym:
        o = symptr + j * sym_size
        raw_name = data[o:o + 8]
        if bigobj:
            value, secnum, typ, sclass, naux = struct.unpack_from("<IiHBB", data, o + 8)
        else:
            value, secnum, typ, sclass, naux = struct.unpack_from("<IhHBB", data, o + 8)
        name = longname(raw_name)
        sym = {"index": j, "name": name, "value": value, "section": secnum, "coff_type": typ,
               "storage_class": COFF_CLASS.get(sclass, str(sclass)), "storage_class_id": sclass,
               "naux": naux, "is_function": (typ & 0xF0) == 0x20,
               "defined": secnum > 0, "size": None}
        if sclass == 3 and naux >= 1 and value == 0 and 0 < secnum < len(sections) and name == sections[secnum]["name"]:
            a = symptr + (j + 1) * sym_size  # section definition aux record
            length, nrel, _nln, checksum, num_lo, sel = struct.unpack_from("<IHHIHB", data, a)
            num_hi = struct.unpack_from("<H", data, a + 16)[0] if bigobj else 0
            if sections[secnum]["flags"] & IMAGE_SCN_LNK_COMDAT:
                sections[secnum]["comdat"] = {"selection": COFF_COMDAT_SEL.get(sel, str(sel)),
                                              "associated_section": num_lo | (num_hi << 16), "checksum": checksum}
            sym["is_section_symbol"] = True
        symbols.append(sym)
        j += 1 + naux
    relocs = {s["index"]: s.pop("relocs") for s in sections[1:]}
    return {"format": "coff-bigobj" if bigobj else "coff", "kind": "rel", "sections": sections,
            "symbols": symbols, "relocs": relocs}


def parse_object(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] == b"\x7fELF":
        obj = parse_elf(data)
    elif data[:2] == b"\x64\x86" or data[:4] == b"\0\0\xff\xff":
        obj = parse_coff(data)
    elif data[:2] == b"MZ":
        raise ValueError("PE images are not supported; feed object files (.obj/.o)")
    elif data[:8] == b"!<arch>\n":
        raise ValueError("archives are not supported; extract members first")
    else:
        raise ValueError("unknown object format")
    obj["data"] = data
    return obj
