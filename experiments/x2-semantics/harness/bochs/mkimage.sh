#!/bin/sh
# mkimage.sh OUTDIR LOOPS -- assemble boot.S with the WSL binutils (as/ld 2.42) into a 1.44 MB floppy image
# whose timing loop runs LOOPS iterations. Run inside WSL from the directory holding boot.S.
set -e
out=$1; loops=${2:-0}
mkdir -p "$out"
as --64 -o "$out/boot.o" boot.S
ld -Ttext=0x7c00 --oformat binary -o "$out/boot.bin" "$out/boot.o"
# patch the 8-byte loop count at the symbol 'loops'
off=$(( $(nm "$out/boot.o" | awk '$3=="loops"{print "0x"$1}') ))
python3 - "$out/boot.bin" "$off" "$loops" <<'PY'
import struct, sys
p, off, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
b = bytearray(open(p, "rb").read())
b[off:off + 8] = struct.pack("<Q", n)
assert len(b) <= 18 * 512, len(b)
b += b"\0" * (1474560 - len(b))
open(p.replace("boot.bin", "boot_%d.img" % n), "wb").write(b)
PY
as --version | head -1
ls -l "$out"
