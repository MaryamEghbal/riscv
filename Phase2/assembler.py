import struct
import sys

# --- Data Structures and Tables ---

# A dictionary to map register names to their 5-bit binary representation
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

# Add floating-point registers (f0-f31)
REGS.update({f'f{i}': f'{i:05b}' for i in range(32)})

# Complete instruction definitions [opcode, funct3, funct7, format]
OPCODES = {
    # R-type (RV32I)
    'add':  ['0110011', '000', '0000000', 'R'],
    'sub':  ['0110011', '000', '0100000', 'R'],
    'xor':  ['0110011', '100', '0000000', 'R'],
    'or':   ['0110011', '110', '0000000', 'R'],
    'and':  ['0110011', '111', '0000000', 'R'],
    'sll':  ['0110011', '001', '0000000', 'R'],
    'srl':  ['0110011', '101', '0000000', 'R'],
    'sra':  ['0110011', '101', '0100000', 'R'],
    'slt':  ['0110011', '010', '0000000', 'R'],
    'sltu': ['0110011', '011', '0000000', 'R'],
    # R-type (RV32M)
    'mul':  ['0110011', '000', '0000001', 'R'],
    'mulh': ['0110011', '001', '0000001', 'R'],
    'div':  ['0110011', '100', '0000001', 'R'],
    'rem':  ['0110011', '110', '0000001', 'R'],
    # I-type
    'addi': ['0010011', '000', None, 'I'],
    'xori': ['0010011', '100', None, 'I'], # For 'not' pseudo-instruction
    'lw':   ['0000011', '010', None, 'I-load'],
    'lh':   ['0000011', '001', None, 'I-load'],
    'jalr': ['1100111', '000', None, 'I'],
    # S-type
    'sw':   ['0100011', '010', None, 'S'],
    'sh':   ['0100011', '001', None, 'S'],
    # B-type
    'beq':  ['1100011', '000', None, 'B'],
    'bne':  ['1100011', '001', None, 'B'],
    'blt':  ['1100011', '100', None, 'B'],
    'bge':  ['1100011', '101', None, 'B'],
    'bltu': ['1100011', '110', None, 'B'],
    'bgeu': ['1100011', '111', None, 'B'],
    # U-type
    'lui':   ['0110111', None, None, 'U'],
    'auipc': ['0010111', None, None, 'U'],
    # J-type
    'jal':  ['1101111', None, None, 'J'],

    # --- Floating-Point Instructions (RV32F) ---
    # F-type Load/Store
    'flw':   ['0000111', '010', None, 'I-fload'],  # Opcode 0x07, funct3 0x2
    'fsw':   ['0100111', '010', None, 'S-fstore'], # Opcode 0x27, funct3 0x2

    # F-type R-format Arithmetic Operations (Opcode 0x53, funct3 0x0)
    # funct7 determines the specific operation
    'fadd.s': ['1010011', '000', '0000000', 'R-float'], # Single-precision Add
    'fsub.s': ['1010011', '000', '0000100', 'R-float'], # Single-precision Subtract
    'fmul.s': ['1010011', '000', '0001000', 'R-float'], # Single-precision Multiply
    'fdiv.s': ['1010011', '000', '0001100', 'R-float'], # Single-precision Divide

    # F-type R-format Unary Operations (Opcode 0x53, funct3 0x0)
    'fsqrt.s': ['1010011', '000', '0101100', 'R-float-unary'], # Single-precision Square Root

    # F-type R-format Conversion Operations (Opcode 0x53, funct3 0x0)
    'fcvt.w.s': ['1010011', '000', '1100000', 'R-float-conv'], # Convert Single-float to Word (integer)
    'fcvt.s.w': ['1010011', '000', '1101000', 'R-float-conv'], # Convert Word (integer) to Single-float
}

# --- Helper Functions ---

def to_binary(n, bits, signed=True):
    """Converts an integer to a two's complement binary string."""
    if signed and n < 0:
        return bin((1 << bits) + n)[2:]
    return f'{n:0{bits}b}'

def clean_line(line):
    """Removes comments and whitespace."""
    return line.split('#')[0].strip()

def expand_pseudo_instructions(line):
    """Expands a single pseudo-instruction into one or more real instructions."""
    parts = [p.strip() for p in line.replace(',', ' ').split()]
    op = parts[0]

    if op == 'nop':
        return ['addi x0, x0, 0']
    if op == 'mv':
        rd, rs = parts[1], parts[2]
        return [f'addi {rd}, {rs}, 0']
    if op == 'not':
        rd, rs = parts[1], parts[2]
        return [f'xori {rd}, {rs}, -1']
    if op == 'neg':
        rd, rs = parts[1], parts[2]
        return [f'sub {rd}, x0, {rs}'] # Corrected: sub rd, x0, rs
    if op == 'li':
        rd, imm_str = parts[1], parts[2]
        imm = int(imm_str, 0)
        if -2048 <= imm <= 2047: # Fits in 12-bit immediate
            return [f'addi {rd}, x0, {imm}']
        else:
            # Split into LUI and ADDI
            upper = (imm >> 12) & 0xFFFFF
            lower = imm & 0xFFF
            # Handle rounding up if the lower part is negative
            if lower & 0x800:
                upper += 1
            
            lui_instr = f'lui {rd}, {upper}'
            addi_instr = f'addi {rd}, {rd}, {lower}'
            return [lui_instr, addi_instr]
            
    return [line] # Not a pseudo-instruction, return as is

# --- Main Assembler Logic ---

def first_pass(lines):
    """Pass 1: Build the symbol table."""
    symbol_table = {}
    location_counter = 0x1000

    for line in lines:
        line = clean_line(line)
        if not line:
            continue

        # Handle labels
        if line.endswith(':'):
            label = line[:-1]
            symbol_table[label] = location_counter
            continue
        
        # Expand pseudo-instructions to correctly calculate size
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
            else: # Real instruction
                location_counter += 4
                
    return symbol_table

def second_pass(lines, symbol_table):
    """Pass 2: Translate to machine code."""
    output_bytes = bytearray()
    location_counter = 0x1000

    for line_num, line in enumerate(lines, 1):
        line = clean_line(line)
        if not line or line.endswith(':'):
            continue

        expanded_lines = expand_pseudo_instructions(line)

        for expanded_line in expanded_lines:
            parts = [p.strip() for p in expanded_line.replace(',', ' ').split()]
            op = parts[0]
            
            # --- Handle Directives ---
            if op.startswith('.'):
                if op == '.word':
                    for val_str in parts[1:]:
                        val = int(val_str, 0)
                        output_bytes.extend(struct.pack('<i', val))
                        location_counter += 4
                elif op == '.half':
                    for val_str in parts[1:]:
                        val = int(val_str, 0)
                        output_bytes.extend(struct.pack('<h', val))
                        location_counter += 2
                elif op == '.byte':
                    for val_str in parts[1:]:
                        val = int(val_str, 0)
                        output_bytes.extend(struct.pack('<b', val))
                        location_counter += 1
                elif op == '.align':
                    alignment = 2**int(parts[1])
                    padding = (alignment - (location_counter % alignment)) % alignment
                    output_bytes.extend(b'\x00' * padding)
                    location_counter += padding
                continue

            # --- Handle Real Instructions ---
            if op not in OPCODES:
                raise ValueError(f"Error on line {line_num}: Unknown instruction '{op}'")

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
                imm_bin = to_binary(imm, 20, signed=False)
                binary_string = f"{imm_bin}{rd}{opcode}"
            elif fmt == 'J':
                rd, label = REGS[parts[1]], parts[2]
                offset = symbol_table[label] - location_counter
                imm_bin = to_binary(offset, 21)
                binary_string = f"{imm_bin[0]}{imm_bin[10:20]}{imm_bin[9]}{imm_bin[1:9]}{rd}{opcode}"
            
            # --- Floating-Point Specific Formats ---
            elif fmt == 'R-float': # For fadd.s, fsub.s, fmul.s, fdiv.s
                # All three registers are floating-point registers (f-type)
                frd, frs1, frs2 = REGS[parts[1]], REGS[parts[2]], REGS[parts[3]]
                binary_string = f"{funct7}{frs2}{frs1}{funct3}{frd}{opcode}"

            elif fmt == 'R-float-unary': # For fsqrt.s
                # frd and frs1 are floating-point registers. rs2 is 00000.
                frd, frs1 = REGS[parts[1]], REGS[parts[2]]
                binary_string = f"{funct7}{REGS['x0']}{frs1}{funct3}{frd}{opcode}"

            elif fmt == 'R-float-conv': # For fcvt.w.s, fcvt.s.w
                # The first register is the destination, second is the source.
                # Could be a mix of integer (x) and floating-point (f) registers.
                dest_reg = REGS[parts[1]]
                src_reg = REGS[parts[2]]
                # rs2 is typically 00000 for standard rounding mode (RNE)
                binary_string = f"{funct7}{REGS['x0']}{src_reg}{funct3}{dest_reg}{opcode}"

            elif fmt == 'I-fload': # For flw (Floating-Point Load Word)
                # frd is a floating-point register, rs1 is an integer register
                frd = REGS[parts[1]]
                offset_part, rs1_part = parts[2].replace(')','').split('(')
                rs1, imm = REGS[rs1_part], int(offset_part, 0)
                binary_string = f"{to_binary(imm, 12)}{rs1}{funct3}{frd}{opcode}"

            elif fmt == 'S-fstore': # For fsw (Floating-Point Store Word)
                # frs2 is a floating-point register, rs1 is an integer register
                frs2 = REGS[parts[1]]
                offset_part, rs1_part = parts[2].replace(')','').split('(')
                rs1, imm = REGS[rs1_part], int(offset_part, 0)
                imm_bin = to_binary(imm, 12)
                binary_string = f"{imm_bin[0:7]}{frs2}{rs1}{funct3}{imm_bin[7:12]}{opcode}"
            
            # Append the assembled instruction to the byte array
            output_bytes.extend(struct.pack('<I', int(binary_string, 2)))
            location_counter += 4

    return output_bytes

def main(input_file, output_file):
    """Main function to run the assembler."""
    try:
        with open(input_file, 'r') as f:
            lines = [clean_line(line) for line in f.readlines() if clean_line(line)]

        symbol_table = first_pass(lines)
        print("--- Symbol Table ---")
        for label, address in symbol_table.items():
            print(f"{label}: {hex(address)}")
        print("-" * 20)

        output_bytes = second_pass(lines, symbol_table)
        
        with open(output_file, 'wb') as f:
            f.write(output_bytes)
        
        print(f"Successfully assembled '{input_file}' to '{output_file}' ({len(output_bytes)} bytes written).")

    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.")
    except (ValueError, KeyError) as e:
        print(f"Assembly Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# --- Main execution block ---
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python assembler.py <input_file.asm> <output_file.bin>")
        sys.exit(1)
    
    main(sys.argv[1], sys.argv[2])
