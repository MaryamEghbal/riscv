# ===============================================
#  simple_math.asm
#  A simple program to test basic arithmetic.
# ===============================================

# Start of the code segment
.text
.global _start

_start:
    # Load immediate values into registers
    addi x5, x0, 100      # x5 = 100
    addi x6, x0, 50       # x6 = 50

    # Perform arithmetic operations
    add  x7, x5, x6       # x7 = x5 + x6  (100 + 50 = 150)
    sub  x8, x5, x6       # x8 = x5 - x6  (100 - 50 = 50)
    
    # Perform logical operations
    and  x9, x7, x8       # x9 = 150 & 50 (binary: 10010110 & 00110010 = 00010010 = 18)
    or   x10, x7, x8      # x10 = 150 | 50 (binary: 10010110 | 00110010 = 10110110 = 182)

    # End of program (infinite loop to halt execution in a simulator)
halt:
    beq x0, x0, halt
