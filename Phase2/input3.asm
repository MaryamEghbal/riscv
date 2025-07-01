# ===============================================
#  directives_and_pseudo.asm
#  Tests assembler directives and pseudo-instructions.
# ===============================================

.text
.global _start

_start:
    # --- Testing Pseudo-instructions ---

    nop                     # Should be assembled as: addi x0, x0, 0

    li   x5, 123            # Test 'li' with a small immediate. Assembled as: addi x5, x0, 123
    
    li   x6, 4096           # Test 'li' with a large immediate. Should be expanded to:
                            # lui x6, 1
                            # addi x6, x6, 0
    
    mv   x7, x5             # Test 'mv'. Assembled as: addi x7, x5, 0

    not  x8, x5             # Test 'not'. Assembled as: xori x8, x5, -1

    neg  x9, x5             # Test 'neg'. Assembled as: sub x9, x0, x5

halt:
    beq  x0, x0, halt


# --- Testing Directives ---
# This section will be placed after the code.

.data
# Align the next data to a 16-byte boundary (2^4)
.align 4

data_block:
    .word 0xDEADBEEF, 0x12345678 # Store two 32-bit words
    .half 0xABCD, 0xEF01          # Store two 16-bit half-words
    .byte 0x1A, 0x2B, 0x3C, 0x4D   # Store four 8-bit bytes
