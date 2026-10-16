# X0 census scripts

Standard-library Python (3.8 or later), no third-party packages. Each script runs unchanged on the
desktop in WSL (`python3`, Linux XED and LLVM tools) and natively on Windows (`C:\Python313\python.exe`,
Windows XED and LLVM tools). Both platforms gave identical decodes on the smoke objects (step 62).
Run with `python -I` because they read untrusted object files.

| Script | Does |
|---|---|
| `x0obj.py` | Minimal ELF64 / COFF (and bigobj) reader: sections, symbols, relocations, COMDAT info. Library only. |
| `x0_extract.py` | Finds every function's byte range in `.o`/`.obj` files and writes a manifest (JSON). |
| `x0_decode.py` | Decodes each function with the `xed` command-line tool and writes per-instruction and per-function results plus anomalies. |
| `x0_flags.py` | Reads CMake's `compile_commands.json`: `show` prints per-file flags; `replay` compiles another source with a file's exact command. |
| `smoke/smoke.c` | The smoke test file. It is not Hearth code. |
| `smoke/results/<cfg>/` | Smoke results per configuration: manifest, `functions.json`, `anomalies.json`, `summary.json`. |
| `runbook/` | The desktop job scripts used for setup and validation, numbered in run order (see `../TOOLCHAINS.md`). |

## Pipeline

```sh
# WSL on the desktop. Tool paths as installed for X0.
L=/mnt/d/mithril/tools/llvm-linux-23.1.3/bin
X=/mnt/d/mithril/tools/xed-v2026.08.23/bin/xed
S=/mnt/d/mithril/x0/scripts            # copy of this directory

# 1. Function boundaries. COFF objects from Windows builds are read the same way, through /mnt/d.
python3 -I $S/x0_extract.py --readobj $L/llvm-readobj --label A-msvc -o OUT/manifest.json OBJ [OBJ ...]
# 2. Decode.
python3 -I $S/x0_decode.py OUT/manifest.json -o OUT/decode --xed $X --objdump $L/llvm-objdump -j 8 \
        --attr-cache OUT/xed_attr_cache.json
```

On Windows, use the same arguments with `D:\mithril\tools\xed-v2026.08.23-win\bin\xed.exe` and
`D:\mithril\tools\llvm-win-23.1.3\bin\llvm-{readobj,objdump}.exe`.

Both scripts exit 1 when they find something that needs a look, such as a cross-check mismatch,
an undecodable byte or a boundary problem. Read `anomalies.json` before you use any counts.

### x0_extract.py: function boundaries

- **ELF:** each `STT_FUNC` or `STT_GNU_IFUNC` symbol covers `[st_value, st_value+st_size)`. Aliases
  at the same address are merged. A function with `st_size` 0 runs to the next symbol.
  GCC's split cold parts (`foo.cold` in `.text.unlikely`) appear as separate functions.
- **COFF:** functions are symbols with `Type == 0x20` in a section flagged `IMAGE_SCN_CNT_CODE`. COFF
  stores no symbol size, so a function runs to the next function symbol in its section, or to
  the section end. In the smoke objects, both cl and clang-cl put every function in its own
  COMDAT section: MSVC names it `.text$mn` and clang-cl names it `.text`. Sections are tracked by
  index, never by name. Trailing `0xCC` (int3) fill is trimmed and reported.
- **Data in code:** a run of two or more relocations spaced exactly by their width (4 or 8 bytes)
  is treated as a table. MSVC x64 places switch jump tables inside `.text$mn`, after the code.
  The table and the int3 fill before it are left out of decoding and reported as
  `data_in_code_excluded`.
- **Gaps:** code-section bytes that no function covers, such as alignment padding between ELF
  functions, are decoded too. They must contain only NOP or INT3, otherwise the gap is reported
  as `gap_with_code`.
- With `--readobj`, every function symbol (name, section, value, and the size for ELF) is
  compared against `llvm-readobj --symbols`.

### x0_decode.py: XED passes

1. **Sweep:** `xed -64 -cet -ir <range.bin> -b <start> -v 4 -isa-set`, a linear sweep over each code
   range. It gives offset, length, bytes, ICLASS, IFORM, CATEGORY, EXTENSION, ISA_SET, the EVEX
   operand fields (`MASK`, `ZEROING`, `ROUNDC`, `SAE`, `BCAST`, `VL`) and decode errors.
2. **Attributes:** `xed -64 -cet -d <hex>`, run once per distinct encoding and cached. In `-ir` mode XED
   does not print the `ATTRIBUTES:` line, so this pass supplies it. ICLASS, IFORM, ISA_SET,
   EXTENSION and CATEGORY from the two passes must agree.

Checks:
- Bytes decoded plus bytes undecodable must equal the range length.
- XED's `# Errors:` count must match the errors parsed.
- Every relocation field must lie strictly inside one instruction. This catches a sweep that
  went out of sync, and data the table rule missed.
- With `--objdump`, every instruction start and length must match `llvm-objdump -d`, and that
  output must contain no `<unknown>`.
- NOP or INT3 after a function's last terminator is flagged `padding: true` and left out of the
  per-function tuples. This applies only when the size was inferred, not taken from an ELF symbol.

`-cet` is on by default (`--no-cet` turns it off). Without it XED decodes `endbr64`, which Ubuntu's
GCC emits by default, as `NOP_GPRv_GPRv_0F1E`.

Outputs:
- `instructions.jsonl`: one record per instruction, with fields `function`, `section`, `offset`,
  `len`, `hex`, `iclass`, `iform`, `category`, `extension`, `isa_set`, `attributes`, `fields` (EVEX),
  `disasm` and `padding`. Undecodable spans have their own records.
- `functions.json`: for each function, the distinct tuples
  `(iclass, iform, extension, isa_set, attributes)` with counts, excluding padding.
- `anomalies.json`: entries graded `error`, `warning` or `info`.
- `summary.json`: totals, XED version and mode.

Notes for the census:
- `MXCSR` marks instructions whose result depends on or updates MXCSR (FP arithmetic, conversions,
  `VROUNDPS`). In XED v2026.08.23, `MXCSR_RD` occurs only on `STMXCSR` and `VSTMXCSR`. It does not
  mean "uses the MXCSR rounding mode". Embedded rounding shows up as `fields.ROUNDC` / `fields.SAE`.
- NOPs inside a function's symbol range, such as loop alignment, are real bytes of the function.
  They keep `iclass` NOP and the `NOP` attribute, so filter them by iclass if needed.

### x0_flags.py: exact compile commands

```sh
python3 -I x0_flags.py show A-msvc=../flags/A-msvc.compile_commands.json B-clangcl=... --json ../flags/quant_flags.json
python3 -I x0_flags.py replay CFG/compile_commands.json --as quant_avx512.c --src smoke/smoke.c --obj OUT.o --exec
```

`show` removes only per-file plumbing: the source, `-o`, `/Fo`, `/Fd`, `-c`, and the GNU depfile
flags. For cl and clang-cl, `-MD` is the runtime-library flag and is kept. `replay` must run inside
a `vcvars64` environment for A and B.

## Running the census on Hearth objects (not done here)

After step 50 or 51 has configured a build tree, build only the object library, then point
`x0_extract.py` at the objects:

```bat
rem Windows, inside vcvars64. NMake builds serially.
"C:\Program Files\CMake\bin\cmake.exe" --build D:\mithril\x0\cfg\A-msvc --target hearth_core
rem objects: D:\mithril\x0\cfg\A-msvc\CMakeFiles\hearth_core.dir\engine\src\*.c.obj
```

```sh
# WSL
/mnt/d/mithril/tools/cmake-4.4.3-linux/bin/cmake --build /mnt/d/mithril/x0/cfg/C-gcc --target hearth_core -j 8
# objects: /mnt/d/mithril/x0/cfg/C-gcc/CMakeFiles/hearth_core.dir/engine/src/*.c.o
```

The `output` field of each `compile_commands.json` entry names the object, relative to `directory`.
Configuration B is expected to fail on `quant_avx512.c`: a probe calling `_mm512_dpbusd_epi32`,
which `quant_avx512.c` uses, does not compile with B's exact flags because `/arch:AVX512` lacks
AVX512-VNNI under clang-cl. See `../TOOLCHAINS.md`.
