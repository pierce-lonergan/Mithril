/* boot.S -- minimal bare-metal guest for the Bochs feasibility probe (FUZZ-DESIGN.md sec. 6.1).
 * Boot sector: real mode -> protected mode -> long mode (identity-mapped 2 MB page), CR4.OSFXSR,
 * OSXMMEXCPT, OSXSAVE, XCR0 = x87|SSE|AVX|opmask|ZMM_Hi256|Hi16_ZMM. Stage 2 (sectors 2-18) runs a few
 * in-scope instructions on hand vectors of semantics/selftest.py and prints, through the Bochs debug
 * port 0xE9, one line per test: "T<n> <lane-0 or k result> <MXCSR after>". Then an optional timing loop
 * of LOOPS x VADDPS zmm, then "DONE" and the Bochs shutdown sequence on port 0x8900. A minimal IDT prints
 * "EXC <vector>" for any exception or interrupt (NMI and vectors >= 32 return; faults end the run).
 * Assemble (WSL binutils 2.42): as --64 -o boot.o boot.S && ld -Ttext=0x7c00 --oformat binary -o boot.bin boot.o
 */
    .intel_syntax noprefix
    .text
    .code16
    .globl _start
_start:
    cli
    cld
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov sp, 0x7c00
    mov [boot_drive], dl
    mov ax, 0x0211                 /* read 17 sectors */
    mov cx, 0x0002                 /* cylinder 0, sector 2 */
    xor dh, dh
    mov dl, [boot_drive]
    mov bx, 0x7e00
    int 0x13
    jc  disk_fail
    in  al, 0x92                   /* fast A20 */
    or  al, 2
    out 0x92, al
    lgdt [gdt_desc]
    mov eax, cr0
    or  eax, 1
    mov cr0, eax
    .byte 0x66, 0xea               /* jmp far 0x08:pm32 (32-bit offset) */
    .long pm32
    .word 0x08
disk_fail:
    mov al, 'E'
    out 0xe9, al
    hlt

    .code32
pm32:
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov esp, 0x90000
    mov edi, 0x1000                /* zero PML4, PDPT, PD */
    xor eax, eax
    mov ecx, 3072
    rep stosd
    mov dword ptr [0x1000], 0x2003
    mov dword ptr [0x2000], 0x3003
    mov dword ptr [0x3000], 0x83   /* 2 MB page at 0, present, writable */
    mov eax, 0x1000
    mov cr3, eax
    mov eax, cr4
    or  eax, (1 << 5) | (1 << 9) | (1 << 10) | (1 << 18)   /* PAE, OSFXSR, OSXMMEXCPT, OSXSAVE */
    mov cr4, eax
    mov ecx, 0xc0000080            /* EFER.LME */
    rdmsr
    or  eax, 1 << 8
    wrmsr
    mov eax, cr0
    and eax, ~(1 << 2)             /* EM = 0 */
    or  eax, (1 << 1) | (1 << 31)  /* MP, PG */
    mov cr0, eax
    .byte 0xea                     /* jmp far 0x18:lm64 */
    .long lm64
    .word 0x18

    .code64
lm64:
    mov ax, 0x10
    mov ds, ax
    mov es, ax
    mov ss, ax
    mov rsp, 0x90000
    xor ecx, ecx
    mov eax, 0xe7
    xor edx, edx
    xsetbv
    jmp stage2

    .balign 8
gdt:
    .quad 0
    .quad 0x00cf9a000000ffff       /* 0x08 code32 */
    .quad 0x00cf92000000ffff       /* 0x10 data */
    .quad 0x00af9a000000ffff       /* 0x18 code64 */
gdt_desc:
    .word gdt_desc - gdt - 1
    .long gdt
boot_drive:
    .byte 0
    .org 510
    .word 0xaa55

/* ---------------------------------------------------------------- stage 2 at 0x7e00 */
stage2:
    cli                            /* the BIOS may return from INT 13h with IF = 1 */
    mov al, 0xff                   /* mask every 8259 line: IRQ0 would arrive as vector 8 */
    out 0x21, al
    out 0xa1, al
    /* minimal IDT: every vector goes to a 10-byte stub (push imm32 vector; jmp isr_common) */
    mov edi, 0x10000               /* IDT at 64 KB, outside the image (identity-mapped) */
    lea rbx, [rip + isr_table]
    xor ecx, ecx
8:  mov rax, rbx
    mov word ptr [rdi], ax
    mov word ptr [rdi + 2], 0x18
    mov word ptr [rdi + 4], 0x8e00
    shr rax, 16
    mov word ptr [rdi + 6], ax
    shr rax, 16
    mov dword ptr [rdi + 8], eax
    mov dword ptr [rdi + 12], 0
    add rdi, 16
    add rbx, 10
    inc ecx
    cmp ecx, 256
    jne 8b
    lidt [rip + idt_desc]
    lea rsi, [rip + banner]
    call puts
    /* T1 VADDPS zmm: A1 1 + 2^-24 RNE -> 0x3F800000, PE */
    vmovdqu64 zmm1, [rip + v_one]
    vmovdqu64 zmm2, [rip + v_2m24]
    ldmxcsr [rip + mx_default]
    vaddps zmm0, zmm1, zmm2
    mov eax, 1
    call report
    /* T2 VMULPS zmm: A13 0x00800001 * 0x3F7FFFFE -> 0x00800000, PE (F-TINY) */
    vmovdqu64 zmm1, [rip + v_a13a]
    vmovdqu64 zmm2, [rip + v_a13b]
    ldmxcsr [rip + mx_default]
    vmulps zmm0, zmm1, zmm2
    mov eax, 2
    call report
    /* T3 VDIVSS: B6 den / +0 -> +inf; table DE|ZE, 9950X dev smoke ZE */
    vmovdqu64 zmm1, [rip + v_den1]
    vpxord zmm2, zmm2, zmm2
    ldmxcsr [rip + mx_default]
    vdivss xmm0, xmm1, xmm2
    mov eax, 3
    call report
    /* T4 VMAXPS zmm: B1 max(+0, -0) -> -0 (src2) */
    vpxord zmm1, zmm1, zmm1
    vmovdqu64 zmm2, [rip + v_m0]
    ldmxcsr [rip + mx_default]
    vmaxps zmm0, zmm1, zmm2
    mov eax, 4
    call report
    /* T5 VCVTPS2DQ zmm: D2 2^31 -> 0x80000000, IE */
    vmovdqu64 zmm1, [rip + v_2p31]
    ldmxcsr [rip + mx_default]
    vcvtps2dq zmm0, zmm1
    mov eax, 5
    call report
    /* T6 VCVTPH2PS zmm under DAZ: D4 f16 0x0001 -> 0x33800000, no flags (F-H2F) */
    vmovdqu64 zmm1, [rip + v_h0001]
    ldmxcsr [rip + mx_daz]
    vcvtph2ps zmm0, ymm1
    mov eax, 6
    call report
    /* T7 VPDPBUSD zmm: acc 0, bytes 2 x 3 -> lane 0 = 24 */
    vpxord zmm0, zmm0, zmm0
    vmovdqu64 zmm1, [rip + v_b2]
    vmovdqu64 zmm2, [rip + v_b3]
    ldmxcsr [rip + mx_default]
    vpdpbusd zmm0, zmm1, zmm2
    mov eax, 7
    call report
    /* T8 VPMADDUBSW zmm: F1 (255,255) x (127,127) -> 32767 (saturated) */
    vmovdqu64 zmm1, [rip + v_b255]
    vmovdqu64 zmm2, [rip + v_b127]
    ldmxcsr [rip + mx_default]
    vpmaddubsw zmm0, zmm1, zmm2
    mov eax, 8
    call report
    /* T9 VCMPPS k, UNORD_Q on [1.0, QNaN, ...] -> k = 0x0002 */
    vmovdqu64 zmm1, [rip + v_cmp]
    ldmxcsr [rip + mx_default]
    vcmpps k2, zmm1, zmm1, 3
    kmovw eax, k2
    vmovd xmm0, eax
    mov eax, 9
    call report
    /* T10 VMULPS zmm under FTZ: A12 2^-126 * 0.5 -> +0, UE|PE (F-FTZ-EXACT) */
    vmovdqu64 zmm1, [rip + v_minn]
    vmovdqu64 zmm2, [rip + v_half]
    ldmxcsr [rip + mx_ftz]
    vmulps zmm0, zmm1, zmm2
    mov eax, 10
    call report
    /* T11 VMAXPS zmm under DAZ: B4 max(+0, -den) -> -0 (F-DAZ-SEL) */
    vpxord zmm1, zmm1, zmm1
    vmovdqu64 zmm2, [rip + v_mden1]
    ldmxcsr [rip + mx_daz]
    vmaxps zmm0, zmm1, zmm2
    mov eax, 11
    call report
    /* T12 VADDPS zmm{k1}: E1 masked-off SNaN raises nothing (k1 = 0xFFFE, lane 0 SNaN) */
    vmovdqu64 zmm1, [rip + v_snan_l0]
    vmovdqu64 zmm2, [rip + v_two]
    mov eax, 0xfffe
    kmovw k1, eax
    vpxord zmm0, zmm0, zmm0
    ldmxcsr [rip + mx_default]
    vaddps zmm0{k1}, zmm1, zmm2
    vextractf32x4 xmm3, zmm0, 0
    vpshufd xmm0, xmm3, 0x55       /* report lane 1 = 1 + 2 = 3.0 */
    mov eax, 12
    call report
    /* timing loop: LOOPS x (VADDPS zmm + DEC + JNZ) */
    lea rsi, [rip + s_loop]
    call puts
    mov rcx, [rip + loops]
    vmovdqu64 zmm1, [rip + v_one]
    vmovdqu64 zmm2, [rip + v_2m24]
    test rcx, rcx
    jz 2f
1:  vaddps zmm0, zmm1, zmm2
    dec rcx
    jnz 1b
2:  lea rsi, [rip + s_done]
    call puts
    mov dx, 0x8900                 /* Bochs shutdown port */
    lea rsi, [rip + s_shutdown]
3:  lodsb
    test al, al
    jz 4f
    out dx, al
    jmp 3b
4:  cli
    hlt
    jmp 4b

/* isr_common: print "EXC <vector>"; NMI (2) and external vectors (>= 32) return, faults stop the run */
isr_common:
    push rax
    push rcx
    push rdx
    push rsi
    push r8
    lea rsi, [rip + s_exc]
    call puts
    mov eax, [rsp + 40]
    call puthex8
    mov al, 10
    out 0xe9, al
    mov eax, [rsp + 40]
    cmp eax, 2
    je 9f
    cmp eax, 32
    jae 9f
    lea rsi, [rip + s_done]
    call puts
    mov dx, 0x8900
    lea rsi, [rip + s_shutdown]
10: lodsb
    test al, al
    jz 11f
    out dx, al
    jmp 10b
11: cli
    hlt
    jmp 11b
9:  pop r8
    pop rsi
    pop rdx
    pop rcx
    pop rax
    add rsp, 8
    iretq

    .set vec, 0
isr_table:
    .rept 256
    .byte 0x68
    .long vec
    .byte 0xe9
    .long isr_common - (. + 4)
    .set vec, vec + 1
    .endr

/* report: "T<eax> <xmm0 lane 0 hex> <MXCSR hex>\n" */
report:
    push rax
    stmxcsr [rip + mx_out]
    vmovd edx, xmm0
    mov [rip + lane0], edx
    mov al, 'T'
    out 0xe9, al
    pop rax
    call puthex8
    mov al, ' '
    out 0xe9, al
    mov eax, [rip + lane0]
    call puthex8
    mov al, ' '
    out 0xe9, al
    mov eax, [rip + mx_out]
    call puthex8
    mov al, 10
    out 0xe9, al
    ret

puthex8:                           /* eax -> 8 hex digits */
    mov ecx, 8
5:  rol eax, 4
    mov edx, eax
    and edx, 0xf
    lea r8, [rip + hexdig]
    mov dl, [r8 + rdx]
    push rax
    mov al, dl
    out 0xe9, al
    pop rax
    dec ecx
    jnz 5b
    ret

puts:
6:  lodsb
    test al, al
    jz 7f
    out 0xe9, al
    jmp 6b
7:  ret

hexdig:     .ascii "0123456789ABCDEF"
banner:     .asciz "X2 BOCHS PROBE\n"
s_loop:     .asciz "LOOP\n"
s_done:     .asciz "DONE\n"
s_shutdown: .asciz "Shutdown"
s_exc:      .asciz "EXC "
    .balign 8
loops:      .quad 0                /* patched by the build script for the timing run */
mx_default: .long 0x1f80
mx_daz:     .long 0x1fc0
mx_ftz:     .long 0x9f80
mx_out:     .long 0
lane0:      .long 0
    .balign 16
idt_desc:   .word 256 * 16 - 1
            .quad 0x10000
    .balign 64
v_one:     .fill 16, 4, 0x3f800000
v_two:     .fill 16, 4, 0x40000000
v_2m24:    .fill 16, 4, 0x33800000
v_a13a:    .fill 16, 4, 0x00800001
v_a13b:    .fill 16, 4, 0x3f7ffffe
v_den1:    .fill 16, 4, 0x00000001
v_mden1:   .fill 16, 4, 0x80000001
v_m0:      .fill 16, 4, 0x80000000
v_2p31:    .fill 16, 4, 0x4f000000
v_h0001:   .fill 16, 4, 0x00010001
v_b2:      .fill 16, 4, 0x02020202
v_b3:      .fill 16, 4, 0x03030303
v_b255:    .fill 16, 4, 0xffffffff
v_b127:    .fill 16, 4, 0x7f7f7f7f
v_minn:    .fill 16, 4, 0x00800000
v_half:    .fill 16, 4, 0x3f000000
v_cmp:     .long 0x3f800000, 0x7fc00000
           .fill 14, 4, 0x3f800000
v_snan_l0: .long 0x7f800001
           .fill 15, 4, 0x3f800000
    .balign 512
