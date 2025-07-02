import struct
import sys
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext

# =============================================================================
#  مهم: برای استفاده از تم‌های مدرن، ابتدا باید این کتابخانه را نصب کنید
#  در ترمینال یا Command Prompt خود دستور زیر را اجرا کنید:
#  pip install ttkthemes
# =============================================================================
try:
    from ttkthemes import ThemedTk
except ImportError:
    print("Warning: ttkthemes not found. Falling back to default theme.")
    print("For a better look, run: pip install ttkthemes")
    from tkinter import Tk as ThemedTk


# =============================================================================
#  بخش ۱: هسته اصلی شبیه‌ساز (موتور) - بدون تغییر
# =============================================================================

class Instruction:
    def __init__(self, hex_instr):
        self.hex = hex_instr
        self.opcode = hex_instr & 0x7F
        self.rd = (hex_instr >> 7) & 0x1F
        self.funct3 = (hex_instr >> 12) & 0x7
        self.rs1 = (hex_instr >> 15) & 0x1F
        self.rs2 = (hex_instr >> 20) & 0x1F
        self.funct7 = (hex_instr >> 25) & 0x7F
        self.imm_I = self._sign_extend(hex_instr >> 20, 12)
        self.imm_S = self._sign_extend(((hex_instr >> 25) << 5) | ((hex_instr >> 7) & 0x1F), 12)
        self.imm_B = self._sign_extend(
            ((hex_instr & 0x80000000) >> 19) |
            ((hex_instr & 0x7E000000) >> 20) |
            ((hex_instr & 0xF00) >> 7) |
            ((hex_instr & 0x80) << 4), 13)
        self.imm_U = self._sign_extend(hex_instr & 0xFFFFF000, 32)
        self.imm_J = self._sign_extend(
            ((hex_instr & 0x80000000) >> 11) |
            (hex_instr & 0xFF000) |
            ((hex_instr & 0x100000) >> 9) |
            ((hex_instr & 0x7FE00000) >> 20), 21)

    def _sign_extend(self, value, bits):
        sign_bit = 1 << (bits - 1)
        return (value & (sign_bit - 1)) - (value & sign_bit)

class RISCVSimulator:
    def __init__(self, mem_size=64 * 1024):
        self.mem_size = mem_size
        self.memory = bytearray(mem_size)
        self.registers = [0] * 32
        self.pc = 0x1000
        self.running = False

    def load_program(self, filename):
        self.reset()
        try:
            with open(filename, 'rb') as f:
                program_bytes = f.read()
            self.memory[0x1000:0x1000 + len(program_bytes)] = program_bytes
            return f"Program '{filename}' loaded ({len(program_bytes)} bytes)."
        except FileNotFoundError:
            return f"Error: File '{filename}' not found."

    def reset(self):
        self.memory = bytearray(self.mem_size)
        self.registers = [0] * 32
        self.pc = 0x1000
        self.running = False

    def _get_signed_reg(self, reg_index):
        return struct.unpack('<i', struct.pack('<I', self.registers[reg_index]))[0]

    def run_single_step(self):
        if self.pc >= self.mem_size: return False
        instruction_bytes = self.memory[self.pc:self.pc + 4]
        if len(instruction_bytes) < 4: return False
        instruction_hex = struct.unpack('<I', instruction_bytes)[0]
        if instruction_hex == 0: return False

        instr = Instruction(instruction_hex)
        next_pc = self.pc + 4
        
        opcode = instr.opcode
        if opcode == 0x33:
            rs1_val = self._get_signed_reg(instr.rs1)
            rs2_val = self._get_signed_reg(instr.rs2)
            if instr.funct3 == 0x0:
                if instr.funct7 == 0x00: self.registers[instr.rd] = rs1_val + rs2_val # add
                elif instr.funct7 == 0x20: self.registers[instr.rd] = rs1_val - rs2_val # sub
            elif instr.funct3 == 0x4: self.registers[instr.rd] = rs1_val ^ rs2_val # xor
            elif instr.funct3 == 0x6: self.registers[instr.rd] = rs1_val | rs2_val # or
            elif instr.funct3 == 0x7: self.registers[instr.rd] = rs1_val & rs2_val # and
            elif instr.funct3 == 0x1: self.registers[instr.rd] = rs1_val << (rs2_val & 0x1F) # sll
            elif instr.funct3 == 0x5:
                if instr.funct7 == 0x00: self.registers[instr.rd] = self.registers[instr.rs1] >> (rs2_val & 0x1F) # srl
                elif instr.funct7 == 0x20: self.registers[instr.rd] = rs1_val >> (rs2_val & 0x1F) # sra
            elif instr.funct3 == 0x2: self.registers[instr.rd] = 1 if rs1_val < rs2_val else 0 # slt
            elif instr.funct3 == 0x3: self.registers[instr.rd] = 1 if self.registers[instr.rs1] < self.registers[instr.rs2] else 0 # sltu
            if instr.funct7 == 0x01:
                if instr.funct3 == 0x0: self.registers[instr.rd] = rs1_val * rs2_val # mul
                elif instr.funct3 == 0x1: self.registers[instr.rd] = (rs1_val * rs2_val) >> 32 # mulh
                elif instr.funct3 == 0x4: self.registers[instr.rd] = -1 if rs2_val == 0 else int(rs1_val / rs2_val) # div
                elif instr.funct3 == 0x6: self.registers[instr.rd] = rs1_val if rs2_val == 0 else rs1_val % rs2_val # rem
        elif opcode == 0x13: # addi
            self.registers[instr.rd] = self.registers[instr.rs1] + instr.imm_I
        elif opcode == 0x03:
            address = self.registers[instr.rs1] + instr.imm_I
            if instr.funct3 == 0x2: # lw
                self.registers[instr.rd] = struct.unpack('<i', self.memory[address:address+4])[0]
            elif instr.funct3 == 0x1: # lh
                self.registers[instr.rd] = struct.unpack('<h', self.memory[address:address+2])[0]
        elif opcode == 0x23:
            address = self.registers[instr.rs1] + instr.imm_S
            if instr.funct3 == 0x2: # sw
                self.memory[address:address+4] = struct.pack('<i', self.registers[instr.rs2])
            elif instr.funct3 == 0x1: # sh
                self.memory[address:address+2] = struct.pack('<h', self.registers[instr.rs2] & 0xFFFF)
        elif opcode == 0x63:
            rs1_val, rs2_val = self._get_signed_reg(instr.rs1), self._get_signed_reg(instr.rs2)
            condition_met = False
            if instr.funct3 == 0x0 and rs1_val == rs2_val: condition_met = True  # beq
            elif instr.funct3 == 0x1 and rs1_val != rs2_val: condition_met = True # bne
            elif instr.funct3 == 0x4 and rs1_val < rs2_val: condition_met = True  # blt
            elif instr.funct3 == 0x5 and rs1_val >= rs2_val: condition_met = True # bge
            elif instr.funct3 == 0x6 and self.registers[instr.rs1] < self.registers[instr.rs2]: condition_met = True # bltu
            elif instr.funct3 == 0x7 and self.registers[instr.rs1] >= self.registers[instr.rs2]: condition_met = True # bgeu
            if condition_met: next_pc = self.pc + instr.imm_B
        elif opcode == 0x37: self.registers[instr.rd] = instr.imm_U # lui
        elif opcode == 0x17: self.registers[instr.rd] = self.pc + instr.imm_U # auipc
        elif opcode == 0x6F: # jal
            self.registers[instr.rd] = self.pc + 4
            next_pc = self.pc + instr.imm_J
        elif opcode == 0x67: # jalr
            self.registers[instr.rd] = self.pc + 4
            next_pc = (self.registers[instr.rs1] + instr.imm_I) & ~1
        else: return False

        self.registers[0] = 0
        self.pc = next_pc
        return True

# =============================================================================
#  بخش ۲: رابط کاربری گرافیکی (GUI) - نسخه بهبود یافته
# =============================================================================

class SimulatorGUI:
    def __init__(self, master):
        self.master = master
        self.master.title("RISC-V Graphical Simulator")
        self.master.geometry("1100x800")

        self.sim = RISCVSimulator()
        self.running = False
        self.run_speed = 50 # ms delay
        self.prev_regs = list(self.sim.registers)

        # --- استایل و تم ---
        style = ttk.Style(self.master)
        style.configure('Treeview', rowheight=25, font=('Segoe UI', 10))
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))
        style.configure('TButton', padding=6, relief="flat", font=('Segoe UI', 10))
        style.configure('TLabelframe.Label', font=('Segoe UI', 11, 'bold'))
        
        # --- تعریف رنگ‌ها برای هایلایت ---
        self.reg_tree = None # Placeholder
        self.master.after(100, self._configure_treeview_tags)

        # --- ایجاد فریم‌های اصلی برای چیدمان ---
        main_paned_window = ttk.PanedWindow(master, orient=tk.HORIZONTAL)
        main_paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_paned_window, width=250)
        main_paned_window.add(left_frame, weight=0)

        right_frame = ttk.Frame(main_paned_window)
        main_paned_window.add(right_frame, weight=1)

        # --- بخش کنترل‌ها (سمت چپ) ---
        self._create_controls(left_frame)

        # --- بخش نمایشگرها (سمت راست) ---
        self._create_displays(right_frame)

        self.update_display()

    def _configure_treeview_tags(self):
        """ کانفیگ رنگ برای هایلایت کردن رجیسترهای تغییر کرده """
        if self.reg_tree:
            self.reg_tree.tag_configure('changed', background='#d0f0c0') # رنگ سبز روشن

    def _create_controls(self, parent):
        """ ویجت‌های بخش کنترل را ایجاد می‌کند """
        controls_frame = ttk.LabelFrame(parent, text="Controls", padding="10")
        controls_frame.pack(fill="x", pady=(0, 10))

        self.load_btn = ttk.Button(controls_frame, text="📂 Load Program", command=self.load_file)
        self.load_btn.pack(fill="x", pady=5)
        self.step_btn = ttk.Button(controls_frame, text="➡️ Step", command=self.step)
        self.step_btn.pack(fill="x", pady=5)
        self.run_btn = ttk.Button(controls_frame, text="▶️ Run", command=self.run_toggle)
        self.run_btn.pack(fill="x", pady=5)
        self.reset_btn = ttk.Button(controls_frame, text="🔄 Reset", command=self.reset)
        self.reset_btn.pack(fill="x", pady=5)
        
        pc_frame = ttk.LabelFrame(parent, text="Program Counter", padding="10")
        pc_frame.pack(fill="x")
        self.pc_label = ttk.Label(pc_frame, text="PC: 0x0000", font=("Courier", 14, 'bold'))
        self.pc_label.pack()

    def _create_displays(self, parent):
        """ ویجت‌های نمایش رجیستر و حافظه را ایجاد می‌کند """
        display_paned_window = ttk.PanedWindow(parent, orient=tk.VERTICAL)
        display_paned_window.pack(fill=tk.BOTH, expand=True)

        # --- بخش رجیسترها با Treeview ---
        reg_frame = ttk.LabelFrame(display_paned_window, text="Registers", padding="10")
        display_paned_window.add(reg_frame, weight=1)

        columns = ('reg_name', 'abi', 'hex_val', 'dec_val')
        self.reg_tree = ttk.Treeview(reg_frame, columns=columns, show='headings')
        self.reg_tree.heading('reg_name', text='Register')
        self.reg_tree.heading('abi', text='ABI Name')
        self.reg_tree.heading('hex_val', text='Hex Value')
        self.reg_tree.heading('dec_val', text='Decimal')
        
        self.reg_tree.column('reg_name', width=80, anchor='center')
        self.reg_tree.column('abi', width=100, anchor='center')
        # --- تغییر در این دو خط ---
        self.reg_tree.column('hex_val', width=150, anchor='center') # از 'w' به 'center' تغییر کرد
        self.reg_tree.column('dec_val', width=150, anchor='center') # از 'w' به 'center' تغییر کرد
        
        self.reg_tree.pack(fill="both", expand=True)
        
        # --- بخش حافظه ---
        mem_frame = ttk.LabelFrame(display_paned_window, text="Memory View (from 0x1000)", padding="10")
        display_paned_window.add(mem_frame, weight=1)
        self.mem_text = scrolledtext.ScrolledText(mem_frame, height=10, width=80, font=("Courier", 10))
        self.mem_text.pack(fill="both", expand=True)
        self.mem_text.config(state='disabled')

    def load_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("Binary files", "*.bin"), ("All files", "*.*")])
        if not filepath: return
        message = self.sim.load_program(filepath)
        self.prev_regs = list(self.sim.registers)
        self.update_display()
        print(message)

    def step(self):
        self.prev_regs = list(self.sim.registers)
        if not self.sim.run_single_step():
            self.running = False
            self.run_btn.config(text="▶️ Run")
            print("Simulation halted.")
        self.update_display()

    def run_toggle(self):
        if self.running:
            self.running = False
            self.run_btn.config(text="▶️ Run")
        else:
            self.running = True
            self.run_btn.config(text="⏸️ Pause")
            self.run_loop()
    
    def run_loop(self):
        if self.running:
            self.step()
            self.master.after(self.run_speed, self.run_loop)

    def reset(self):
        self.sim.reset()
        self.running = False
        self.run_btn.config(text="▶️ Run")
        self.prev_regs = list(self.sim.registers)
        self.update_display()
        print("Simulator reset.")

    def update_display(self):
        self.pc_label.config(text=f"PC: {self.sim.pc:#06x}")
        
        # --- به‌روزرسانی جدول رجیسترها ---
        abi_names = ['zero', 'ra', 'sp', 'gp', 'tp', 't0', 't1', 't2', 's0', 's1', 'a0', 'a1', 'a2', 'a3', 'a4', 'a5',
                     'a6', 'a7', 's2', 's3', 's4', 's5', 's6', 's7', 's8', 's9', 's10', 's11', 't3', 't4', 't5', 't6']
        
        self.reg_tree.delete(*self.reg_tree.get_children()) # پاک کردن جدول
        for i in range(32):
            val = self.sim.registers[i]
            signed_val = self._get_signed_val(val, 32)
            
            tags = ()
            if val != self.prev_regs[i]:
                tags = ('changed',) # اعمال تگ برای هایلایت
            
            self.reg_tree.insert('', 'end', iid=i, tags=tags,
                                 values=(f"x{i}", abi_names[i], f"{val:#010x}", str(signed_val)))

        # --- به‌روزرسانی نمایش حافظه ---
        self.mem_text.config(state='normal')
        self.mem_text.delete('1.0', tk.END)
        addr_start = 0x1000
        num_bytes_to_show = 256
        for offset in range(0, num_bytes_to_show, 16):
            addr = addr_start + offset
            data_chunk = self.sim.memory[addr:addr+16]
            hex_repr = ' '.join(f'{b:02x}' for b in data_chunk)
            ascii_repr = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data_chunk)
            self.mem_text.insert(tk.END, f"{addr:#06x}: {hex_repr:<48} |{ascii_repr}|\n")
        self.mem_text.config(state='disabled')

    def _get_signed_val(self, val, bits):
        """ مقدار بدون علامت را به معادل علامت‌دار آن تبدیل می‌کند """
        if (val & (1 << (bits - 1))) != 0:
            val = val - (1 << bits)
        return val

# --- راه‌اندازی برنامه اصلی ---
if __name__ == "__main__":
    # از ThemedTk برای اعمال تم استفاده می‌کنیم
    try:
        root = ThemedTk(theme="arc")
    except tk.TclError:
        print("ttkthemes not found, using default theme.")
        root = tk.Tk()
        
    app = SimulatorGUI(root)
    root.mainloop()

