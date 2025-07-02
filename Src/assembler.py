# RISC-V Assembler - Final Version with Bug Fix
# This script implements a two-pass assembler for the required RISC-V instruction set.
# It now correctly handles labels on the same line as instructions/directives.
# It also includes a more robust parser for complex instructions and modifiers.

import struct
import sys
import os
import re 

# --- Data Structures and Tables ---

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

# --- Helper Functions  ---

def to_binary(n, bits, signed=True):
    if signed and n < 0:
        return bin((1 << bits) + n)[2:].zfill(bits)
    return f'{n:0{bits}b}'

def clean_line(line):
    return line.split('#')[0].strip()

def parse_immediate(imm_str, symbol_table):
    imm_str = imm_str.strip()
    match = re.match(r'%(hi|lo)\((.+)\)', imm_str)
    if match:
        modifier, label = match.groups()
        if label not in symbol_table:
            raise ValueError(f"Undefined label '{label}' used in %{modifier}() modifier.")
        address = symbol_table[label]
        if modifier == 'hi':
            return (address + 0x800) >> 12
        else: # lo
            lo_part = address & 0xFFF
            return lo_part - 0x1000 if lo_part & 0x800 else lo_part
    else:
        try:
            return int(imm_str, 0)
        except ValueError:
            raise ValueError(f"Invalid immediate value: '{imm_str}'.")

def expand_pseudo_instructions(line, symbol_table):
    parts = [p.strip() for p in re.split(r'[,\s]+', line, 1)]
    if not parts: return []
    op = parts[0]
    
    if op == 'la':
        args = [p.strip() for p in parts[1].split(',')]
        rd, label = args[0], args[1]
        return [f'auipc {rd}, %hi({label})', f'addi {rd}, {rd}, %lo({label})']

    if op == 'nop': return ['addi x0, x0, 0']
    if op == 'mv':
        args = [p.strip() for p in parts[1].split(',')]
        return [f'addi {args[0]}, {args[1]}, 0']
    if op == 'not':
        args = [p.strip() for p in parts[1].split(',')]
        return [f'xori {args[0]}, {args[1]}, -1']
    if op == 'neg':
        args = [p.strip() for p in parts[1].split(',')]
        return [f'sub {args[0]}, x0, {args[1]}']
    if op == 'li':
        args = [p.strip() for p in parts[1].split(',')]
        rd, imm_str = args[0], args[1]
        imm = int(imm_str, 0)
        if -2048 <= imm <= 2047:
            return [f'addi {rd}, x0, {imm}']
        else:
            upper = (imm + 0x800) >> 12 & 0xFFFFF 
            lower = imm & 0xFFF
            return [f'lui {rd}, {upper}', f'addi {rd}, {rd}, {lower}']
    return [line]

# --- Main Assembler Logic  ---

def first_pass(lines):
    symbol_table = {}
    location_counter = 0x1000
    temp_symbol_table = {} 
    
    temp_lc = 0x1000
    for line in lines:
        parts = line.split()
        if not parts: continue
        if parts[0].endswith(':'):
            temp_symbol_table[parts[0][:-1]] = temp_lc
        else:
            op = parts[0]
            if op == 'li' or op == 'la': temp_lc += 8
            elif op.startswith('.'):
                directive_parts = line.split()
                if op == '.word': temp_lc += 4 * (len(directive_parts) - 1)
                elif op == '.half': temp_lc += 2 * (len(directive_parts) - 1)
                elif op == '.byte': temp_lc += 1 * (len(directive_parts) - 1)
            else: temp_lc += 4

    for line in lines:
        parts = line.split()
        if not parts: continue

        if parts[0].endswith(':'):
            label = parts[0][:-1]
            symbol_table[label] = location_counter
            parts = parts[1:]
            if not parts: continue
        
        line_content = " ".join(parts)
        expanded_lines = expand_pseudo_instructions(line_content, temp_symbol_table)
        
        for expanded_line in expanded_lines:
            op = expanded_line.split()[0]
            if op.startswith('.'):
                directive_parts = expanded_line.split()
                if op == '.word': location_counter += 4 * (len(directive_parts) - 1)
                elif op == '.half': location_counter += 2 * (len(directive_parts) - 1)
                elif op == '.byte': location_counter += 1 * (len(directive_parts) - 1)
                elif op == '.align':
                    alignment = 2**int(directive_parts[1])
                    padding = (alignment - (location_counter % alignment)) % alignment
                    location_counter += padding
            else:
                location_counter += 4
    return symbol_table

def second_pass(lines, symbol_table):
    output_bytes = bytearray()
    location_counter = 0x1000
    for line_num, line in enumerate(lines, 1):
        parts = line.split()
        if not parts: continue
        
        line_content = line
        if parts[0].endswith(':'):
            line_content = " ".join(parts[1:])
            if not line_content: continue

        expanded_lines = expand_pseudo_instructions(line_content, symbol_table)

        for expanded_line in expanded_lines:
            tokens = [p.strip() for p in re.split(r'[,\s]+', expanded_line, 1)]
            op = tokens[0]
            
            if op.startswith('.'):
                directive_parts = expanded_line.split()
                if op == '.word':
                    for val_str in directive_parts[1:]: output_bytes.extend(struct.pack('<i', int(val_str, 0)))
                elif op == '.half':
                    for val_str in directive_parts[1:]: output_bytes.extend(struct.pack('<h', int(val_str, 0)))
                elif op == '.byte':
                    for val_str in directive_parts[1:]: output_bytes.extend(struct.pack('<b', int(val_str, 0)))
                elif op == '.align':
                    alignment = 2**int(directive_parts[1])
                    padding = (alignment - (location_counter % alignment)) % alignment
                    output_bytes.extend(b'\x00' * padding)
                continue
            
            if op not in OPCODES: raise ValueError(f"Error on line {line_num}: Unknown instruction '{op}'")
            opcode, funct3, funct7, fmt = OPCODES[op]
            binary_string = ""
            
            operands = [p.strip() for p in tokens[1].split(',')]

            if fmt == 'I':
                rd, rs1, imm_str = REGS[operands[0]], REGS[operands[1]], operands[2]
                imm = parse_immediate(imm_str, symbol_table)
                binary_string = f"{to_binary(imm, 12)}{rs1}{funct3}{rd}{opcode}"
            elif fmt == 'I-load':
                rd = REGS[operands[0]]
                match = re.match(r'(.+)\((.+)\)', operands[1])
                imm_str, rs1_str = match.groups()
                rs1 = REGS[rs1_str]
                imm = parse_immediate(imm_str, symbol_table)
                binary_string = f"{to_binary(imm, 12)}{rs1}{funct3}{rd}{opcode}"
            elif fmt == 'U':
                rd, imm_str = REGS[operands[0]], operands[1]
                imm = parse_immediate(imm_str, symbol_table)
                binary_string = f"{to_binary(imm, 20, signed=False)}{rd}{opcode}"
            elif fmt == 'R':
                rd, rs1, rs2 = REGS[operands[0]], REGS[operands[1]], REGS[operands[2]]
                binary_string = f"{funct7}{rs2}{rs1}{funct3}{rd}{opcode}"
            elif fmt == 'S':
                rs2 = REGS[operands[0]]
                match = re.match(r'(.+)\((.+)\)', operands[1])
                imm_str, rs1_str = match.groups()
                rs1 = REGS[rs1_str]
                imm = parse_immediate(imm_str, symbol_table)
                imm_bin = to_binary(imm, 12)
                binary_string = f"{imm_bin[0:7]}{rs2}{rs1}{funct3}{imm_bin[7:12]}{opcode}"
            elif fmt == 'B':
                rs1, rs2, label = REGS[operands[0]], REGS[operands[1]], operands[2]
                offset = symbol_table[label] - location_counter
                imm_bin = to_binary(offset, 13)
                binary_string = f"{imm_bin[0]}{imm_bin[2:8]}{rs2}{rs1}{funct3}{imm_bin[8:12]}{imm_bin[1]}{opcode}"
            elif fmt == 'J':
                rd, label = REGS[operands[0]], operands[1]
                offset = symbol_table[label] - location_counter
                imm_bin = to_binary(offset, 21)
                binary_string = f"{imm_bin[0]}{imm_bin[10:20]}{imm_bin[9]}{imm_bin[1:9]}{rd}{opcode}"
            
            output_bytes.extend(struct.pack('<I', int(binary_string, 2)))
            location_counter += 4
    return output_bytes

def main(input_file, output_file):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
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
