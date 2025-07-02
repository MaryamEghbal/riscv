# RISC-V Assembler - Final Version with Bug Fix
# This script implements a two-pass assembler for the required RISC-V instruction set.
# It now automatically creates the output directory if it doesn't exist.

import struct
import sys
import os 

# --- Data Structures and Tables  ---

REGS = {f'x{i}': f'{i:05b}' for i in range(32)}
REGS.update({
    'zero': REGS['x0'], 'ra': REGS['x1'], 'sp': REGS['x2'], 'gp': REGS['x3'],
    'tp': REGS['x4'], 't0': REGS['x5'], 't1': REGS['x6'], 't2': REGS['x7'],
    's0': REGS['x8'], 'fp': REGS['x8'], 's1': REGS['x9'], 'a0': REGS['x10'],
    'a1': REGS['x11'], 'a2': REGS['x12'], 'a3': REGS['x13'], 'a4': REGS['x14'],
    'a5': REGS['x15'], 'a6': REGS['x16'], 'a7': REGS['x17'], 's2': REGS['x18'],
    's3': REGS['x19'], 's4': REGS['x20'], 's5': REGS['x21'], 's6': REGS['x22'],
    's7': REGS['x23'], 's8': REGS['x24'], 's9': REGS['x25'], 's10': REGS['x26'],
    's11': REGS['x27'], 't3': REGS['x28'], 't4': REGS['x29'], 't5': REGS['x30'],
    't6': REGS['x31']
})

OPCODES = {
    'add':  ['0110011', '000', '0000000', 'R'], 'sub':  ['0110011', '000', '0100000', 'R'],
    'xor':  ['0110011', '100', '0000000', 'R'], 'or':   ['0110011', '110', '0000000', 'R'],
    'and':  ['0110011', '111', '0000000', 'R'], 'sll':  ['0110011', '001', '0000000', 'R'],
    'srl':  ['0110011', '101', '0000000', 'R'], 'sra':  ['0110011', '101', '0100000', 'R'],
    'slt':  ['0110011', '010', '0000000', 'R'], 'sltu': ['0110011', '011', '0000000', 'R'],
    'mul':  ['0110011', '000', '0000001', 'R'], 'mulh': ['0110011', '001', '0000001', 'R'],
    'div':  ['0110011', '100', '0000001', 'R'], 'rem':  ['0110011', '110', '0000001', 'R'],
    'addi': ['0010011', '000', None, 'I'],    'xori': ['0010011', '100', None, 'I'],
    'lw':   ['0000011', '010', None, 'I-load'],'lh':   ['0000011', '001', None, 'I-load'],
    'jalr': ['1100111', '000', None, 'I'],    'sw':   ['0100011', '010', None, 'S'],
    'sh':   ['0100011', '001', None, 'S'],    'beq':  ['1100011', '000', None, 'B'],
    'bne':  ['1100011', '001', None, 'B'],    'blt':  ['1100011', '100', None, 'B'],
    'bge':  ['1100011', '101', None, 'B'],    'bltu': ['1100011', '110', None, 'B'],
    'bgeu': ['1100011', '111', None, 'B'],    'lui':  ['0110111', None, None, 'U'],
    'auipc':['0010111', None, None, 'U'],    'jal':  ['1101111', None, None, 'J'],
}

# --- Helper Functions ---

def to_binary(n, bits, signed=True):
    if signed and n < 0:
        return bin((1 << bits) + n)[2:].zfill(bits)
    return f'{n:0{bits}b}'

def clean_line(line):
    return line.split('#')[0].strip()

def expand_pseudo_instructions(line):
    parts = [p.strip() for p in line.replace(',', ' ').split()]
    op = parts[0]
    if op == 'nop': return ['addi x0, x0, 0']
    if op == 'mv': return [f'addi {parts[1]}, {parts[2]}, 0']
    if op == 'not': return [f'xori {parts[1]}, {parts[2]}, -1']
    if op == 'neg': return [f'sub {parts[1]}, x0, {parts[2]}']
    if op == 'li':
        rd, imm_str = parts[1], parts[2]
        imm = int(imm_str, 0)
        if -2048 <= imm <= 2047:
            return [f'addi {rd}, x0, {imm}']
        else:
            upper = (imm + 0x800) >> 12 & 0xFFFFF 
            lower = imm & 0xFFF
            return [f'lui {rd}, {upper}', f'addi {rd}, {rd}, {lower}']
    return [line]

# --- Main Assembler Logic 

def first_pass(lines):
    symbol_table = {}
    location_counter = 0x1000
    for line in lines:
        if line.endswith(':'):
            symbol_table[line[:-1]] = location_counter
            continue
        expanded_lines = expand_pseudo_instructions(line)
        for expanded_line in expanded_lines:
            parts = expanded_line.split()
            op = parts[0]
            if op.startswith('.'):
                if op == '.word': location_counter += 4 * (len(parts) - 1)
                elif op == '.half': location_counter += 2 * (len(parts) - 1)
                elif op == '.byte': location_counter += 1 * (len(parts) - 1)
                elif op == '.align':
                    alignment = 2**int(parts[1])
                    padding = (alignment - (location_counter % alignment)) % alignment
                    location_counter += padding
            else:
                location_counter += 4
    return symbol_table

def second_pass(lines, symbol_table):
    output_bytes = bytearray()
    location_counter = 0x1000
    for line_num, line in enumerate(lines, 1):
        if line.endswith(':'): continue
        expanded_lines = expand_pseudo_instructions(line)
        for expanded_line in expanded_lines:
            parts = [p.strip() for p in expanded_line.replace(',', ' ').split()]
            op = parts[0]
            if op.startswith('.'):
                if op == '.word':
                    for val_str in parts[1:]:
                        output_bytes.extend(struct.pack('<i', int(val_str, 0)))
                        location_counter += 4
                elif op == '.half':
                    for val_str in parts[1:]:
                        output_bytes.extend(struct.pack('<h', int(val_str, 0)))
                        location_counter += 2
                elif op == '.byte':
                    for val_str in parts[1:]:
                        output_bytes.extend(struct.pack('<b', int(val_str, 0)))
                        location_counter += 1
                elif op == '.align':
                    alignment = 2**int(parts[1])
                    padding = (alignment - (location_counter % alignment)) % alignment
                    output_bytes.extend(b'\x00' * padding)
                    location_counter += padding
                continue
            
            if op not in OPCODES: raise ValueError(f"Error on line {line_num}: Unknown instruction '{op}'")
            opcode, funct3, funct7, fmt = OPCODES[op]
            binary_string = ""
            if fmt == 'R':
                rd, rs1, rs2 = REGS[parts[1]], REGS[parts[2]], REGS[parts[3]]
                binary_string = f"{funct7}{rs2}{rs1}{funct3}{rd}{opcode}"
            elif fmt == 'I':
                rd, rs1, imm = REGS[parts[1]], REGS[parts[2]], int(parts[3], 0)
                binary_string = f"{to_binary(imm, 12)}{rs1}{funct3}{rd}{opcode}"
            elif fmt == 'I-load':
                rd = REGS[parts[1]]
                offset_part, rs1_part = parts[2].replace(')','').split('(')
                rs1, imm = REGS[rs1_part], int(offset_part, 0)
                binary_string = f"{to_binary(imm, 12)}{rs1}{funct3}{rd}{opcode}"
            elif fmt == 'S':
                rs2 = REGS[parts[1]]
                offset_part, rs1_part = parts[2].replace(')','').split('(')
                rs1, imm = REGS[rs1_part], int(offset_part, 0)
                imm_bin = to_binary(imm, 12)
                binary_string = f"{imm_bin[0:7]}{rs2}{rs1}{funct3}{imm_bin[7:12]}{opcode}"
            elif fmt == 'B':
                rs1, rs2, label = REGS[parts[1]], REGS[parts[2]], parts[3]
                offset = symbol_table[label] - location_counter
                imm_bin = to_binary(offset, 13)
                binary_string = f"{imm_bin[0]}{imm_bin[2:8]}{rs2}{rs1}{funct3}{imm_bin[8:12]}{imm_bin[1]}{opcode}"
            elif fmt == 'U':
                rd, imm = REGS[parts[1]], int(parts[2], 0)
                binary_string = f"{to_binary(imm, 20, signed=False)}{rd}{opcode}"
            elif fmt == 'J':
                rd, label = REGS[parts[1]], parts[2]
                offset = symbol_table[label] - location_counter
                imm_bin = to_binary(offset, 21)
                binary_string = f"{imm_bin[0]}{imm_bin[10:20]}{imm_bin[9]}{imm_bin[1:9]}{rd}{opcode}"
            
            output_bytes.extend(struct.pack('<I', int(binary_string, 2)))
            location_counter += 4
    return output_bytes

def main(input_file, output_file):
    """Main function to run the assembler."""
    try:
        with open(input_file, 'r') as f:
            lines = [clean_line(line) for line in f.readlines() if clean_line(line)]
    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
        return 

    try:
        symbol_table = first_pass(lines)
        print("--- Symbol Table ---")
        for label, address in symbol_table.items():
            print(f"{label}: {hex(address)}")
        print("-" * 20)

        output_bytes = second_pass(lines, symbol_table)
        

        output_dir = os.path.dirname(output_file)
        
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: '{output_dir}'")
        
        with open(output_file, 'wb') as f:
            f.write(output_bytes)
        
        print(f"Successfully assembled '{input_file}' to '{output_file}' ({len(output_bytes)} bytes written).")

    except (ValueError, KeyError) as e:
        print(f"Assembly Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# --- Main execution block  ---
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python assembler.py <input_file.asm> <output_file.bin>")
        sys.exit(1)
    
    main(sys.argv[1], sys.argv[2])
