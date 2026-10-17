"""Binary formats shared by the Python tools and x2fuzz (x2harness.h). Little-endian, fixed records.

vectors.bin = 256-byte header + N x 320-byte records; results/predictions = 256-byte header + N x
160-byte records. A record's case block is the ABI block the MASM stubs read (x2ref.h x2case).
"""
import hashlib
import struct

VEC_MAGIC, RES_MAGIC = b"X2VEC001", b"X2RES001"
HDR, VREC, RREC = 256, 320, 160
CASE_FMT = "<IIQQQQQ16s64s64s64s"          # mxcsr pad k mem_ptr rflags_in gpr_in kdst_in rsv src1 src2 dst_old
OUT_FMT = "<64sIIQQQ32s"                    # dst mxcsr pad rflags kdst gpr rsv
META_FMT = "<IIIIIIIIQQ16s"                 # stub flags set class env lane mf_boundary n_lane_cases index key rsv
assert struct.calcsize(CASE_FMT) == 256 and struct.calcsize(OUT_FMT) == 128 and struct.calcsize(META_FMT) == 64

FLAG_MEMFAULT, FLAG_SINGLE_LANE, FLAG_FILLERS = 1, 2, 4
SETS = {"V1": 1, "V2": 2, "V3": 3, "V4": 4, "BCAST": 5, "F-MEMFAULT": 6, "DEV": 7, "VALID": 8}
ST_OK, ST_EXCEPTION, ST_UNMODELED, ST_BADSTUB = 0, 1, 2, 3


def i2b(v, n=64):
    return (v & ((1 << (8 * n)) - 1)).to_bytes(n, "little")


def b2i(b):
    return int.from_bytes(b, "little")


class Case:
    __slots__ = ("mxcsr", "k", "mem_ptr", "rflags_in", "gpr_in", "kdst_in", "src1", "src2", "dst_old")

    def __init__(self, mxcsr=0x1F80, k=0, rflags_in=0x202, gpr_in=0, kdst_in=0, src1=0, src2=0, dst_old=0):
        self.mxcsr, self.k, self.mem_ptr, self.rflags_in = mxcsr, k, 0, rflags_in
        self.gpr_in, self.kdst_in, self.src1, self.src2, self.dst_old = gpr_in, kdst_in, src1, src2, dst_old

    def pack(self):
        return struct.pack(CASE_FMT, self.mxcsr, 0, self.k, 0, self.rflags_in, self.gpr_in, self.kdst_in, b"\0" * 16,
                           i2b(self.src1), i2b(self.src2), i2b(self.dst_old))

    @staticmethod
    def unpack(b):
        f = struct.unpack(CASE_FMT, b)
        c = Case(mxcsr=f[0], k=f[2], rflags_in=f[4], gpr_in=f[5], kdst_in=f[6], src1=b2i(f[8]), src2=b2i(f[9]),
                 dst_old=b2i(f[10]))
        c.mem_ptr = f[3]
        return c


class Out:
    __slots__ = ("dst", "mxcsr", "rflags", "kdst", "gpr")

    def __init__(self, dst=0, mxcsr=0, rflags=0, kdst=0, gpr=0):
        self.dst, self.mxcsr, self.rflags, self.kdst, self.gpr = dst, mxcsr, rflags, kdst, gpr

    def pack(self):
        return struct.pack(OUT_FMT, i2b(self.dst), self.mxcsr, 0, self.rflags, self.kdst, self.gpr, b"\0" * 32)

    @staticmethod
    def unpack(b):
        f = struct.unpack(OUT_FMT, b)
        return Out(b2i(f[0]), f[1], f[3], f[4], f[5])


def write_vectors(path, records, manifest_sha, generator_sha, bundle, label):
    """records: iterable of (meta dict, Case). Returns (n, sha256 of the file)."""
    h = hashlib.sha256()
    n = 0
    with open(path, "wb") as f:
        f.write(b"\0" * HDR)
        for meta, case in records:
            b = struct.pack(META_FMT, meta["stub"], meta.get("flags", 0), meta.get("set", 0), meta.get("class", 0),
                            meta.get("env", 0), meta.get("lane", 0xFFFFFFFF), meta.get("mf_boundary", 0),
                            meta.get("n_lane_cases", 1), meta.get("index", n), meta.get("key", 0), b"\0" * 16) + case.pack()
            f.write(b)
            n += 1
        hdr = (VEC_MAGIC + struct.pack("<IIQ", 1, VREC, n) + manifest_sha.encode()[:64].ljust(64, b"0")
               + generator_sha.encode()[:64].ljust(64, b"0") + bundle.encode()[:64].ljust(64, b"0")
               + label.encode()[:40].ljust(40, b"\0"))
        assert len(hdr) == HDR
        f.seek(0)
        f.write(hdr)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return n, h.hexdigest()


def read_vectors(path):
    with open(path, "rb") as f:
        hdr = f.read(HDR)
        assert hdr[:8] == VEC_MAGIC, "not a vectors file"
        _, rs, n = struct.unpack("<IIQ", hdr[8:24])
        assert rs == VREC
        info = {"n": n, "manifest": hdr[24:88].decode(), "generator": hdr[88:152].decode(),
                "bundle": hdr[152:216].decode(), "label": hdr[216:256].rstrip(b"\0").decode()}
        recs = []
        while True:
            b = f.read(VREC)
            if not b:
                break
            m = struct.unpack(META_FMT, b[:64])
            meta = {"stub": m[0], "flags": m[1], "set": m[2], "class": m[3], "env": m[4], "lane": m[5],
                    "mf_boundary": m[6], "n_lane_cases": m[7], "index": m[8], "key": m[9]}
            recs.append((meta, Case.unpack(b[64:])))
    return info, recs


def write_results(path, outs, producer, vectors_sha, manifest_sha, producer_sha="0" * 64):
    """outs: iterable of (index, status, Out)."""
    n = 0
    with open(path, "wb") as f:
        f.write(b"\0" * HDR)
        for idx, st, o in outs:
            f.write(o.pack() + struct.pack("<IIQ16s", st, 0, idx, b"\0" * 16))
            n += 1
        hdr = (RES_MAGIC + struct.pack("<IIQ", 1, RREC, n) + vectors_sha.encode()[:64].ljust(64, b"0")
               + manifest_sha.encode()[:64].ljust(64, b"0") + producer.encode()[:32].ljust(32, b"\0")
               + producer_sha.encode()[:64].ljust(64, b"0") + struct.pack("<II", 0xFFFFFFFF, 0))
        assert len(hdr) == HDR
        f.seek(0)
        f.write(hdr)
    return n


def read_results(path):
    with open(path, "rb") as f:
        hdr = f.read(HDR)
        assert hdr[:8] == RES_MAGIC, "not a results file"
        _, rs, n = struct.unpack("<IIQ", hdr[8:24])
        assert rs == RREC
        info = {"n": n, "vectors_sha256": hdr[24:88].decode(), "manifest": hdr[88:152].decode(),
                "producer": hdr[152:184].rstrip(b"\0").decode(), "producer_sha256": hdr[184:248].decode(),
                "cpu": struct.unpack("<I", hdr[248:252])[0]}
        out = []
        while True:
            b = f.read(RREC)
            if not b:
                break
            st, exc, idx = struct.unpack("<IIQ", b[128:144])
            out.append((idx, st, exc, Out.unpack(b[:128])))
    return info, out


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
