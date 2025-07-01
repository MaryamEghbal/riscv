# ===============================================
#  memory_and_branch.asm
#  Tests memory access and conditional branching.
# ===============================================

.data
# Define a variable in memory
my_variable:
    .word 25  # Store the value 25 at this address

.text
.global _start

_start:
    # Load the address of my_variable into a register
    # We will use auipc and addi to load the address.
    # This is a common pattern for position-independent code.
    auipc x5, 0
    addi  x5, x5, my_variable@pcrel_lo(_start) # This syntax might need assembler support
                                              # A simpler way for this project is to hardcode the address
                                              # Let's assume the address is 0x1020 for now.
    lui   x5, 0x1       # lui x5, 0x10000 -> not quite right
    addi  x5, x0, 0x1020 # Hardcoded address for simplicity in this example
    
    # Load the value from memory into x6
    lw   x6, 0(x5)        # x6 = Mem[x5] -> x6 should become 25

    # Simple loop to decrement the value and store it back
    addi x7, x0, 5         # Loop counter: x7 = 5

loop:
    # Decrement the value in x6
    addi x6, x6, -1      # x6 = x6 - 1

    # Store the new value back to memory
    sw   x6, 0(x5)        # Mem[x5] = x6

    # Decrement loop counter
    addi x7, x7, -1      # x7 = x7 - 1

    # If counter is not zero, jump back to loop
    bne  x7, x0, loop     # Branch to 'loop' if x7 != 0

    # After the loop, the value in my_variable should be 20.

halt:
    beq x0, x0, halt

# The data section will be placed after the code by the linker/assembler
# For our simple assembler, let's just assume an address.
# We will manually place data after the halt instruction.
.word 0 # Padding
my_variable_placeholder:
    .word 25
