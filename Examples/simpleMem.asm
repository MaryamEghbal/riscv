# ===============================================
#  simple_memory.asm
#  A simple test for lw and sw instructions.
# ===============================================

.text
_start:
    # We will use register x2 (sp) as a pointer to our data.
    # Let's assume our data is at address 0x2000.
    lui  x2, 0x2          # x2 = 0x2000

    # Store the value 42 at address 0x2000
    addi x5, x0, 42      # x5 = 42
    sw   x5, 0(x2)       # Mem[0x2000] = 42

    # Now, load the value back from memory into a different register
    lw   x6, 0(x2)       # x6 should now be 42

    # Add 10 to the value
    addi x6, x6, 10      # x6 = 42 + 10 = 52

    # Store the new value back to the same memory address
    sw   x6, 0(x2)       # Mem[0x2000] should now be 52

halt:
    # Infinite loop to stop the processor
    beq x0, x0, halt
