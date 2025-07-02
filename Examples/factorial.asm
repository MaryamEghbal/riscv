# ===============================================
#  factorial.asm
#  Calculates the factorial of N (where N=7)
#  The final result is stored in register a0 (x10).
# ===============================================


.text
.global _start

_start:
    # Load the address of N into a register
    lui   a0, %hi(N)
    lw    t0, %lo(N)(a0)

    # Initial values for factorial result (t1) and counter (t2)
    li    t1, 1          # Set t1 (result) to 1
    mv    t2, t0         # Set t2 (counter) to N

factorial_loop:
    # If the counter (t2) reaches one, the loop is finished
    li    t3, 1
    beq   t2, t3, end_loop # Branch if t2 == 1

    # Multiply the current result by the counter
    mul   t1, t1, t2     # result = result * counter

    # Decrement the counter
    addi  t2, t2, -1     # counter = counter - 1

    # Jump to the beginning of the loop
    jal   x0, factorial_loop

end_loop:
    # Store the final result in memory
    lui   a0, %hi(Result)
    sw    t1, %lo(Result)(a0)

    # Move the result to a0 for output
    mv    a0, t1

halt:
    # Infinite loop to halt the processor
    jal   x0, halt


.data
N:      .word 7   # The number to calculate the factorial of
Result: .word 0   # A memory location to store the final result
