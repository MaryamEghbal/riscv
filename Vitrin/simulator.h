#ifndef SIMULATOR_H
#define SIMULATOR_H

#include <cstdint>
#include <vector>
#include <QString>

class Simulator
{
public:
    Simulator();

    void reset();
    bool loadProgram(const QString &filePath);
    uint32_t fetch();
    void step();
    const std::vector<uint32_t>& getRegisters() const;
    uint32_t getPC() const;
    const std::vector<uint8_t>& getMemory() const;


private:
    static const int MEM_SIZE = 65536;
    static const int REG_COUNT = 32;
    uint32_t PC;
    std::vector<uint32_t> REG;
    std::vector<uint8_t> MEMORY;

    void execute(uint32_t inst);
};

#endif // SIMULATOR_H
