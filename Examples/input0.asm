
# A simple RISC-V assembly program

start:
    addi x5, x0, 10      # Load 10 into x5 (x5 = 10)
    addi x6, x0, 20      # Load 20 into x6 (x6 = 20)
    
loop:
    add  x7, x5, x6      # x7 = 10 + 20 = 30
    sub  x5, x5, x0      # This doesn't change x5 as we subtract zero
    bne  x5, x0, loop    # Branch back to loop if x5 is not zero (infinite loop for demo)
    
# This part is unreachable in this demo
end:
    addi x10, x0, 0      # End of program
