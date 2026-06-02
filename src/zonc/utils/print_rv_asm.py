# disassembler.py
import struct
import sys
    
def reg_name(reg_num, is_float=False):
    if is_float:
        fregs = ["ft0", "ft1", "ft2", "ft3", "ft4", "ft5", "ft6", "ft7",
                 "fs0", "fs1", "fa0", "fa1", "fa2", "fa3", "fa4", "fa5",
                 "fa6", "fa7", "fs2", "fs3", "fs4", "fs5", "fs6", "fs7",
                 "fs8", "fs9", "fs10", "fs11", "ft8", "ft9", "ft10", "ft11"]
        return fregs[reg_num] if 0 <= reg_num < 32 else f"f{reg_num}"
    else:
        regs = ["x0", "ra", "sp", "gp", "tp", "t0", "t1", "t2",
                "s0/fp", "s1", "a0", "a1", "a2", "a3", "a4", "a5",
                "a6", "a7", "s2", "s3", "s4", "s5", "s6", "s7",
                "s8", "s9", "s10", "s11", "t3", "t4", "t5", "t6"]
        return regs[reg_num] if 0 <= reg_num < 32 else f"x{reg_num}"

def decode_instruction(binary: int, pc: int) -> str:
    opcode = binary & 0x7F
    
    if opcode == 0b1110011:
        funct3 = (binary >> 12) & 0x7
        if funct3 == 0:
            if (binary >> 20) & 0xFFF == 0:
                return "ecall"
            elif (binary >> 20) & 0xFFF == 1:
                return "ebreak"
        return f".word 0x{binary:08x}"
    
    if opcode == 0b0001011:
        funct3 = (binary >> 12) & 0x7
        funct7 = (binary >> 25) & 0x7F
        rd = (binary >> 7) & 0x1F
        rs1 = (binary >> 15) & 0x1F
        rs2 = (binary >> 20) & 0x1F
        
        if funct7 == 0x00:
            if funct3 == 0x00:
                return f"str.concat {reg_name(rd)}, {reg_name(rs1)}, {reg_name(rs2)}"
            
            elif funct3 == 0x01:
                return f"str.eq {reg_name(rd)}, {reg_name(rs1)}, {reg_name(rs2)}"
    
    if opcode == 0b0110111:
        rd = (binary >> 7) & 0x1F
        imm = (binary >> 12) & 0xFFFFF
        return f"lui {reg_name(rd)}, 0x{imm:x}"
    
    if opcode == 0b0010111:
        rd = (binary >> 7) & 0x1F
        imm = (binary >> 12) & 0xFFFFF
        return f"auipc {reg_name(rd)}, 0x{imm:x}"
    
    if opcode == 0b1101111:
        rd = (binary >> 7) & 0x1F
        
        i31 = (binary >> 31) & 0x1
        i30_21 = (binary >> 21) & 0x3FF
        i20 = (binary >> 20) & 0x1
        i19_12 = (binary >> 12) & 0xFF
        
        imm = (i31 << 20) | (i19_12 << 12) | (i20 << 11) | (i30_21 << 1)
        
        if imm & 0x100000:
            imm -= 0x200000
            
        return f"jal {reg_name(rd)}, {imm:+d}  # target = 0x{pc+imm:04x}"
    
    if opcode == 0b1100111:
        rd = (binary >> 7) & 0x1F
        rs1 = (binary >> 15) & 0x1F
        imm = (binary >> 20) & 0xFFF
        if imm & 0x800: imm -= 0x1000
        return f"jalr {reg_name(rd)}, {imm}({reg_name(rs1)})"
    
    if opcode == 0b1100011:
        funct3 = (binary >> 12) & 0x7
        rs1 = (binary >> 15) & 0x1F
        rs2 = (binary >> 20) & 0x1F
        
        i31 = (binary >> 31) & 0x1
        i30_25 = (binary >> 25) & 0x3F
        i11_8 = (binary >> 8) & 0xF
        i7 = (binary >> 7) & 0x1
        
        imm = (i31 << 12) | (i7 << 11) | (i30_25 << 5) | (i11_8 << 1)
        
        if imm & 0x1000:
            imm -= 0x2000
        
        cond = ["beq", "bne", "blt", "bge", "bltu", "bgeu"][funct3 % 6]
        return f"{cond} {reg_name(rs1)}, {reg_name(rs2)}, {imm:+d}  # target = 0x{pc+imm:04x}"
    
    if opcode == 0b0000011:
        funct3 = (binary >> 12) & 0x7
        rd = (binary >> 7) & 0x1F
        rs1 = (binary >> 15) & 0x1F
        imm = (binary >> 20) & 0xFFF
        if imm & 0x800: imm -= 0x1000
        
        loads = ["lb", "lh", "lw", "ld", "lbu", "lhu", "lwu"]
        return f"{loads[funct3]} {reg_name(rd)}, {imm}({reg_name(rs1)})"
    
    if opcode == 0b0100011:
        funct3 = (binary >> 12) & 0x7
        rs1 = (binary >> 15) & 0x1F
        rs2 = (binary >> 20) & 0x1F
        imm = ((binary >> 7) & 0x1F) | ((binary >> 25) & 0x7F) << 5
        if imm & 0x800: imm -= 0x1000
        
        stores = ["sb", "sh", "sw", "sd"]
        return f"{stores[funct3]} {reg_name(rs2)}, {imm}({reg_name(rs1)})"
    
    if opcode in (0b0010011, 0b0011011):
        funct3 = (binary >> 12) & 0x7
        rd = (binary >> 7) & 0x1F
        rs1 = (binary >> 15) & 0x1F
        imm = (binary >> 20) & 0xFFF
        if imm & 0x800: imm -= 0x1000
        
        alu_ops = ["addi", "slli", "slti", "sltiu", "xori", "srli/srai", "ori", "andi"]
        op_name = alu_ops[funct3]
        
        if funct3 == 0b001:
            shamt = imm & 0x3F
            return f"{op_name} {reg_name(rd)}, {reg_name(rs1)}, {shamt}"
        if funct3 == 0b101:
            shamt = imm & 0x3F
            if imm & 0x400: 
                return f"srai {reg_name(rd)}, {reg_name(rs1)}, {shamt}"
            return f"srli {reg_name(rd)}, {reg_name(rs1)}, {shamt}"
        
        suffix = "w" if opcode == 0b0011011 else ""
        return f"{op_name}{suffix} {reg_name(rd)}, {reg_name(rs1)}, {imm}"
    
    if opcode in (0b0110011, 0b0111011):
        funct3 = (binary >> 12) & 0x7
        funct7 = (binary >> 25) & 0x7F
        rd = (binary >> 7) & 0x1F
        rs1 = (binary >> 15) & 0x1F
        rs2 = (binary >> 20) & 0x1F
        
        if funct7 == 0b0000001:
            mul_ops = ["mul", "mulh", "mulhsu", "mulhu", "div", "divu", "rem", "remu"]
            if funct3 < 8:
                return f"{mul_ops[funct3]}{'w' if opcode==0b0111011 else ''} {reg_name(rd)}, {reg_name(rs1)}, {reg_name(rs2)}"
        
        alu_ops = ["add", "sll", "slt", "sltu", "xor", "srl/sra", "or", "and"]
        op_name = alu_ops[funct3]
        
        if funct3 == 0b001 or funct3 == 0b101:
            if funct7 == 0b0100000:
                op_name = "sra"
            else:
                op_name = "srl"
        elif funct7 == 0b0100000:
            op_name = "sub"
        
        suffix = "w" if opcode == 0b0111011 else ""
        return f"{op_name}{suffix} {reg_name(rd)}, {reg_name(rs1)}, {reg_name(rs2)}"
    
    if opcode == 0b0000111:
        funct3 = (binary >> 12) & 0x7
        rd = (binary >> 7) & 0x1F
        rs1 = (binary >> 15) & 0x1F
        imm = (binary >> 20) & 0xFFF
        if imm & 0x800: imm -= 0x1000
        
        if funct3 == 0b011:
            return f"fld {reg_name(rd, is_float=True)}, {imm}({reg_name(rs1)})"
        return f"flw {reg_name(rd, is_float=True)}, {imm}({reg_name(rs1)})"
    
    if opcode == 0b0100111:
        funct3 = (binary >> 12) & 0x7
        rs1 = (binary >> 15) & 0x1F
        rs2 = (binary >> 20) & 0x1F
        imm = ((binary >> 7) & 0x1F) | ((binary >> 25) & 0x7F) << 5
        if imm & 0x800: imm -= 0x1000
        
        if funct3 == 0b011:
            return f"fsd {reg_name(rs2, is_float=True)}, {imm}({reg_name(rs1)})"
        return f"fsw {reg_name(rs2, is_float=True)}, {imm}({reg_name(rs1)})"
    
    return f".word 0x{binary:08x}"

def disassemble_file(filename: str):
    with open(filename, "rb") as f:
        magic = f.read(6)
        if magic != b"!NOZo\x00":
            print("Not a valid Zon VM bytecode file")
            return
        
        version = f.read(1)[0]
        flags = f.read(1)[0]
        entry_point = struct.unpack("<I", f.read(4))[0]
        text_size = struct.unpack("<I", f.read(4))[0]
        data_size = struct.unpack("<I", f.read(4))[0]
        
        pool_size = struct.unpack("<I", f.read(4))[0]
        
        print(f"=== Zon VM Disassembly ===")
        print(f"Version: {version}")
        print(f"Entry point: 0x{entry_point:x}")
        print(f".text size: {text_size} bytes ({text_size//4} instructions)")
        print(f".data size: {data_size} bytes")
        print(f".rodata size: {pool_size} bytes")
        print(f"\n--- .text section ---")
        
        f.read(40) # padding
        
        pc = 0
        for i in range(text_size // 4):
            inst_bytes = f.read(4)
            inst = struct.unpack("<I", inst_bytes)[0]
            asm = decode_instruction(inst, pc)
            print(f"0x{pc:04x}  {inst:08x}  {asm}")
            pc += 4
            
        if pool_size > 0:
            print(f"\n--- .rodata section (size: {pool_size} bytes) ---")
            print(f"{'Offset':<12}{'Raw Hex':<20}{'As Int64':<22}{'As Double':<22}{'Dump (ASCII)'}")
            
            pool_pc = 0
            for _ in range((pool_size // 8)):
                bytes_8 = f.read(8)
                if len(bytes_8) < 8:
                    break
                
                raw_hex_clean = f"{struct.unpack('<Q', bytes_8)[0]:016x}"
            
                val_int = struct.unpack("<q", bytes_8)[0]
                val_float = struct.unpack("<d", bytes_8)[0]
                
                float_str = f"{val_float:.10g}" if not (val_float != val_float) else "nan"
                
                ascii_chars = []
                for b in bytes_8:
                    if 32 <= b <= 126:
                        ascii_chars.append(chr(b))
                    else:
                        ascii_chars.append(".")
                ascii_string = "".join(ascii_chars)
                
                print(f"0x{pool_pc:04x}      {raw_hex_clean}    {val_int:<20}  {float_str:<20}  {ascii_string}")
                pool_pc += 8
        
        if data_size > 0:
            print(f"\n--- .data ---")
            print(f"Size: {data_size} bytes ({data_size // 8} unified 8-byte slots")
            print(f"Status: Initialized dynamically to 0 by the VM in C++ [OK]")