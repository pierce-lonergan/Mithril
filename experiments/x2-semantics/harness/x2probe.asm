; x2probe.asm -- hand-written plumbing probes for the harness self-test. They use the same
; load/store path as the generated stubs but execute only data movement (no table instruction).
OPTION PROLOGUE:NONE
OPTION EPILOGUE:NONE
.data
ALIGN 4
x2p_mxcsr_default DD 00001F80h
.code

; void x2probe_mxcsr(uint32_t *inout): load inout[0] into MXCSR, store MXCSR into inout[1], restore
x2probe_mxcsr PROC
    vldmxcsr dword ptr [rcx]
    vstmxcsr dword ptr [rcx+4]
    vldmxcsr dword ptr [x2p_mxcsr_default]
    ret
x2probe_mxcsr ENDP

; void x2probe_copy_evex(const x2case *c, x2out *o): the stub preamble, then zmm16 <- zmm17, k2 <- k1
x2probe_copy_evex PROC
    vmovdqu64 zmm16, zmmword ptr [rcx+192]
    vmovdqu64 zmm17, zmmword ptr [rcx+64]
    vmovdqu64 zmm18, zmmword ptr [rcx+128]
    kmovq k1, qword ptr [rcx+8]
    kmovq k2, qword ptr [rcx+40]
    mov rax, qword ptr [rcx+32]
    push qword ptr [rcx+24]
    popfq
    vldmxcsr dword ptr [rcx]
    vmovdqa64 zmm16, zmm17
    kmovq k2, k1
    pushfq
    pop r8
    mov qword ptr [rdx+72], r8
    vstmxcsr dword ptr [rdx+64]
    kmovq r9, k2
    mov qword ptr [rdx+80], r9
    mov qword ptr [rdx+88], rax
    vmovdqu64 zmmword ptr [rdx], zmm16
    vldmxcsr dword ptr [x2p_mxcsr_default]
    ret
x2probe_copy_evex ENDP

; void x2probe_copy_vex(const x2case *c, x2out *o): zmm0 <- zmm2 (512-bit move)
x2probe_copy_vex PROC
    vmovdqu64 zmm0, zmmword ptr [rcx+192]
    vmovdqu64 zmm1, zmmword ptr [rcx+64]
    vmovdqu64 zmm2, zmmword ptr [rcx+128]
    vldmxcsr dword ptr [rcx]
    vmovdqa64 zmm0, zmm2
    vstmxcsr dword ptr [rdx+64]
    vmovdqu64 zmmword ptr [rdx], zmm0
    vldmxcsr dword ptr [x2p_mxcsr_default]
    ret
x2probe_copy_vex ENDP

; uint64_t x2probe_load(const void *p)
x2probe_load PROC
    mov rax, qword ptr [rcx]
    ret
x2probe_load ENDP

END
