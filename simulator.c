#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define MEM_SIZE 65536  
#define REG_COUNT 32

uint32_t PC = 0x1000;
uint32_t REG[REG_COUNT] = {0};
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
    int32_t imm;

    switch (opcode) {
        case 0x33:  
            if (funct3 == 0x0) {
                if (funct7 == 0x00) {
                    
                    REG[rd] = REG[rs1] + REG[rs2];
                } else if (funct7 == 0x20) {
                    
                    REG[rd] = REG[rs1] - REG[rs2];
                }
            }
            break;

        case 0x03:  
            if (funct3 == 0x2) {
                imm = (int32_t)inst >> 20;
                uint32_t addr = REG[rs1] + imm;
                REG[rd] = MEMORY[addr] | (MEMORY[addr+1]<<8) | (MEMORY[addr+2]<<16) | (MEMORY[addr+3]<<24);
            }
            break;

        case 0x23:  
            if (funct3 == 0x2) {
                imm = ((inst >> 7) & 0x1F) | (((int32_t)inst >> 25) << 5);
                uint32_t addr = REG[rs1] + imm;
                MEMORY[addr] = REG[rs2] & 0xFF;
                MEMORY[addr+1] = (REG[rs2] >> 8) & 0xFF;
                MEMORY[addr+2] = (REG[rs2] >> 16) & 0xFF;
                MEMORY[addr+3] = (REG[rs2] >> 24) & 0xFF;
            }
            break;

        case 0x63:  
            if (funct3 == 0x0) {
                int32_t offset = ((inst >> 7) & 0x1E) | ((inst >> 20) & 0x7E0) |
                                ((inst << 4) & 0x800) | ((inst >> 19) & 0x1000);
                offset = (offset << 19) >> 19;  
                if (REG[rs1] == REG[rs2]) {
                    PC += offset;
                    return; 
                }
            }
            break;

        default:
            printf("Unsupported instruction: 0x%08X\n", inst);
            break;
    }
    PC += 4; 
}


void print_state() {
    printf("PC = 0x%08X\n", PC);
    for (int i = 0; i < REG_COUNT; i++) {
        printf("x%-2d = 0x%08X ", i, REG[i]);
        if (i % 4 == 3) printf("\n");
    }
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        printf("Usage: %s program.bin\n", argv[0]);
        return 1;
    }

    load_program(argv[1]);

    while (1) {
        uint32_t inst = fetch();
        printf("Instruction: 0x%08X\n", inst);
        execute(inst);
        print_state();

        printf("Press ENTER to continue, q to quit > ");
        char c = getchar();
        if (c == 'q') break;
    }

    return 0;
}
