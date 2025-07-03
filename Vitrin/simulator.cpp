#include "simulator.h"
#include <QFile>
#include <QDataStream>
#include <QDebug>

Simulator::Simulator()
{
    REG.resize(REG_COUNT, 0);
    MEMORY.resize(MEM_SIZE, 0);
    reset();
}

void Simulator::reset()
{
    PC = 0x1000;
    std::fill(REG.begin(), REG.end(), 0);
    std::fill(MEMORY.begin(), MEMORY.end(), 0);
}

bool Simulator::loadProgram(const QString &filePath)
{
    QFile file(filePath);
    if (!file.open(QIODevice::ReadOnly))
        return false;

    QByteArray data = file.readAll();
    for (int i = 0; i < data.size() && (0x1000 + i) < MEM_SIZE; ++i)
        MEMORY[0x1000 + i] = static_cast<uint8_t>(data[i]);

    file.close();
    return true;
}

uint32_t Simulator::fetch()
{
    return MEMORY[PC] | (MEMORY[PC+1]<<8) | (MEMORY[PC+2]<<16) | (MEMORY[PC+3]<<24);
}

void Simulator::step()
{
    uint32_t inst = fetch();
    execute(inst);
}

void Simulator::execute(uint32_t inst)
{
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
            if (funct7 == 0x00)
                REG[rd] = REG[rs1] + REG[rs2];
            else if (funct7 == 0x20)
                REG[rd] = REG[rs1] - REG[rs2];
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
        qDebug() << "Unsupported instruction:" << QString::number(inst, 16);
        break;
    }
    PC += 4;
}

const std::vector<uint32_t>& Simulator::getRegisters() const
{
    return REG;
}

uint32_t Simulator::getPC() const
{
    return PC;
}

const std::vector<uint8_t>& Simulator::getMemory() const
{
    return MEMORY;
}
