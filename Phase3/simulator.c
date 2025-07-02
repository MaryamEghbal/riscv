#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h> // Required for memcpy
#include <math.h>   // Required for sqrtf

#define MEM_SIZE 65536
#define REG_COUNT 32

uint32_t PC = 0x1000;
uint32_t REG[REG_COUNT] = {0};       // Integer registers (x0-x31)
float FREG[REG_COUNT] = {0.0f};      // Floating-point registers (f0-f31)
uint8_t MEMORY[MEM_SIZE] = {0};

void load_program(const char *filename) {
    FILE *f = fopen(filename, "rb");
    if (!f) {
        perror("Cannot open file");
        exit(1);
    }
    fread(&MEMORY[0x1000], 1, MEM_SIZE - 0x1000, f);
    fclose(f);
}

uint32_t fetch() {
    uint32_t inst = MEMORY[PC] | (MEMORY[PC+1]<<8) | (MEMORY[PC+2]<<16) | (MEMORY[PC+3]<<24);
    return inst;
}

void execute(uint32_t inst) {
    uint32_t opcode = inst & 0x7F;
    uint32_t rd = (inst >> 7) & 0x1F;
    uint32_t funct3 = (inst >> 12) & 0x7;
    uint32_t rs1 = (inst >> 15) & 0x1F;
    uint32_t rs2 = (inst >> 20) & 0x1F;
    uint32_t funct7 = (inst >> 25) & 0x7F;
    int32_t imm; // Used for I-type and S-type immediates, and B-type offsets

    switch (opcode) {
        case 0x33: // R-type (Integer Arithmetic)
            if (funct3 == 0x0) {
                if (funct7 == 0x00) { // ADD
                    REG[rd] = REG[rs1] + REG[rs2];
                } else if (funct7 == 0x20) { // SUB
                    REG[rd] = REG[rs1] - REG[rs2];
                }
            }
            // Add other R-type integer ops if necessary (xor, or, and, sll, srl, sra, slt, sltu)
            // Add RV32M extensions (mul, div, rem)
            break;

        case 0x03: // I-type Load (Integer Load Word)
            if (funct3 == 0x2) { // LW
                imm = (int32_t)inst >> 20; // Sign-extended immediate
                uint32_t addr = REG[rs1] + imm;
                REG[rd] = MEMORY[addr] | (MEMORY[addr+1]<<8) | (MEMORY[addr+2]<<16) | (MEMORY[addr+3]<<24);
            }
            // Add other I-type loads if necessary (lh)
            break;

        case 0x23: // S-type Store (Integer Store Word)
            if (funct3 == 0x2) { // SW
                // S-type immediate calculation
                imm = ((inst >> 7) & 0x1F) | (((int32_t)inst >> 25) << 5);
                uint32_t addr = REG[rs1] + imm;
                MEMORY[addr] = REG[rs2] & 0xFF;
                MEMORY[addr+1] = (REG[rs2] >> 8) & 0xFF;
                MEMORY[addr+2] = (REG[rs2] >> 16) & 0xFF;
                MEMORY[addr+3] = (REG[rs2] >> 24) & 0xFF;
            }
            // Add other S-type stores if necessary (sh)
            break;

        case 0x63: // B-type Branch (BEQ)
            if (funct3 == 0x0) { // BEQ
                // B-type immediate calculation
                int32_t offset = ((inst >> 7) & 0x1E) | ((inst >> 20) & 0x7E0) |
                                 ((inst << 4) & 0x800) | ((inst >> 19) & 0x1000);
                offset = (offset << 19) >> 19; // Sign-extend to 32 bits
                if (REG[rs1] == REG[rs2]) {
                    PC += offset;
                    return; // Do not increment PC by 4 after jump
                }
            }
            // Add other B-type branches if necessary (bne, blt, bge, bltu, bgeu)
            break;

        case 0x07: // FLW (Floating-Point Load Word) opcode: 0000111
            if (funct3 == 0x2) { // funct3 for FLW is 010 (binary)
                imm = (int32_t)inst >> 20; // Immediate for I-type (offset)
                uint32_t addr = REG[rs1] + imm; // Calculate effective address using integer register rs1

                uint32_t loaded_word = MEMORY[addr] | (MEMORY[addr+1]<<8) | (MEMORY[addr+2]<<16) | (MEMORY[addr+3]<<24);

                // Reinterpret the uint32_t as a float and store in the floating-point register FREG[rd]
                memcpy(&FREG[rd], &loaded_word, sizeof(float));
            }
            break;

        case 0x27: // FSW (Floating-Point Store Word) opcode: 0100111
            if (funct3 == 0x2) { // funct3 for FSW is 010 (binary)
                // S-type immediate calculation
                imm = ((inst >> 7) & 0x1F) | (((int32_t)inst >> 25) << 5);
                uint32_t addr = REG[rs1] + imm; // Calculate effective address using integer register rs1

                // Reinterpret the float from FREG[rs2] as a uint32_t
                uint32_t stored_word;
                memcpy(&stored_word, &FREG[rs2], sizeof(uint32_t));

                // Write the 4 bytes of the uint32_t to memory
                MEMORY[addr] = stored_word & 0xFF;
                MEMORY[addr+1] = (stored_word >> 8) & 0xFF;
                MEMORY[addr+2] = (stored_word >> 16) & 0xFF;
                MEMORY[addr+3] = (stored_word >> 24) & 0xFF;
            }
            break;

        case 0x53: // Common opcode for R-type Floating-Point operations (1010011)
            // Here, rd, rs1, rs2 from instruction decoding refer to indices for FREG
            // funct3 for single-precision operations is typically 0x0 (000)
            if (funct3 == 0x0) {
                if (funct7 == 0x00) { // FADD.S (funct7: 0000000)
                    FREG[rd] = FREG[rs1] + FREG[rs2];
                } else if (funct7 == 0x04) { // FSUB.S (funct7: 0000100)
                    FREG[rd] = FREG[rs1] - FREG[rs2];
                } else if (funct7 == 0x08) { // FMUL.S (funct7: 0001000)
                    FREG[rd] = FREG[rs1] * FREG[rs2];
                } else if (funct7 == 0x0C) { // FDIV.S (funct7: 0001100)
                    FREG[rd] = FREG[rs1] / FREG[rs2];
                } else if (funct7 == 0x2C) { // FSQRT.S (funct7: 0101100)
                    FREG[rd] = sqrtf(FREG[rs1]);
                } else if (funct7 == 0x60) { // FCVT.W.S (funct7: 1100000) - Convert Float to Integer Word
                    // Result goes to an integer register (REG[rd]), source is float (FREG[rs1])
                    REG[rd] = (int32_t)FREG[rs1];
                } else if (funct7 == 0x68) { // FCVT.S.W (funct7: 1101000) - Convert Integer Word to Float
                    // Result goes to a float register (FREG[rd]), source is integer (REG[rs1])
                    FREG[rd] = (float)REG[rs1];
                }
            }
            break;

        default:
            printf("Unsupported instruction: 0x%08X at PC 0x%08X\n", inst, PC);
            break;
    }
    PC += 4; // Increment PC for next instruction (unless a branch or jump occurred)
}

void print_state() {
    printf("PC = 0x%08X\n", PC);
    printf("Integer Registers:\n");
    for (int i = 0; i < REG_COUNT; i++) {
        printf("x%-2d = 0x%08X ", i, REG[i]);
        if (i % 4 == 3) printf("\n");
    }
    printf("\nFloating-Point Registers:\n");
    for (int i = 0; i < REG_COUNT; i++) {
        printf("f%-2d = %-10f ", i, FREG[i]); // Print floating-point values
        if (i % 4 == 3) printf("\n");
    }
    printf("\n");
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s program.bin\n", argv[0]);
        return 1;
    }

    load_program(argv[1]);

    printf("Simulator Starting at PC = 0x%08X\n", PC);
    while (1) {
        uint32_t inst = fetch();
        printf("Instruction: 0x%08X\n", inst);
        execute(inst);
        print_state();

        printf("Press ENTER to continue, q to quit > ");
        char c = getchar(); // Read single character
        while (c != '\n' && c != EOF) { // Consume remaining characters in buffer
            if (c == 'q') break;
            c = getchar();
        }
        if (c == 'q') break;
    }

    return 0;
}
