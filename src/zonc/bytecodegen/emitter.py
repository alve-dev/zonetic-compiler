from zonc.zonast import *
from .opcode import *
from .register_manager import RegisterManager
from .bytecodescope import SymbolTable
from collections import namedtuple

class LabelManger:
    def __init__(self):
        self.labels = {}
        self.counter = 0
        
    def create(self):
        self.labels.update({self.counter:0})
        self.counter += 1
        return self.counter-1
        
    def place_label(self, id, pc):
        self.labels[id] = pc * 4
        
IntsB = namedtuple("IntsB", ["rs1", "rs2", "opc", "f3", "label"])
IntsJ = namedtuple("IntsJ", ["opc", "label", "rd"])

class Emitter:
    def __init__(self):
        self.code = []
        self.reg_manager = RegisterManager()
        self.symbol_table = SymbolTable()
        self.label_manager = LabelManger()
        self.loop_stack = []
        
    def get_pc(self): return len(self.code)
    
    def emit_r_type(self, opcode, funct3, funct7, rd, rs1, rs2):
        rd &= 0x1F
        rs1 &= 0x1F
        rs2 &= 0x1F
        funct3 &= 0x7
        funct7 &= 0x7F
        opcode &= 0x7F
        inst: int = (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode
        self.code.append(inst.to_bytes(4, "little"))
        print(inst.to_bytes(4, "little"))
        
    def emit_i_type(self, opcode, funct3, rd, rs1, imm):
        rd &= 0x1F
        rs1 &= 0x1F
        funct3 &= 0x7
        imm &= 0xFFF
        opcode &= 0x7F
        inst: int = (imm << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode
        self.code.append(inst.to_bytes(4, "little"))
        print(inst.to_bytes(4, "little"))
        
    def emit_b_type(self, opcode, f3, rs1, rs2, label):
        self.code.append(IntsB(rs1=rs1, rs2=rs2, f3=f3, opc=opcode, label=label))
    
    def emit_j_type(self, opcode, rd, label):
        self.code.append(IntsJ(rd=rd, opc=opcode, label=label))
        
    def generate_b_type(self, instruction, offset):
        val = offset
        b12   = (val >> 12) & 0x1
        b11   = (val >> 11) & 0x1
        b10_5 = (val >> 5)  & 0x3F
        b4_1  = (val >> 1)  & 0xF
        
        inst = (b12 << 31) | (b10_5 << 25) | (instruction.rs2 << 20) | (instruction.rs1 << 15) | \
                (instruction.f3 << 12) | (b4_1 << 8) | (b11 << 7) | (instruction.opc & 0x7F)
        
        print(inst.to_bytes(4, "little"))
        return inst.to_bytes(4, "little")
    
    def generate_j_type(self, instruction, offset):
        val = offset
        imm_20    = (val >> 20) & 0x1
        imm_10_1  = (val >> 1)  & 0x3FF
        imm_11    = (val >> 11) & 0x1
        imm_19_12 = (val >> 12) & 0xFF

        inst = (imm_20 << 31) | (imm_10_1 << 21) | (imm_11 << 20) | \
            (imm_19_12 << 12) | (instruction.rd << 7) | (instruction.opc)
        
        print(inst.to_bytes(4, "little"))
        return inst.to_bytes(4, "little")
        
    def emit_ecall(self):
        self.code.append(0x73.to_bytes(4, "little"))
        print(0x73.to_bytes(4, "little"))
        
    def save(self, filename):
        with open(f"{filename}", "wb") as f:
            f.write(0x5A4F4E21.to_bytes(4, "little"))
            for i, inst in enumerate(self.code):
                if isinstance(inst, bytes):
                    f.write(inst)
                
                elif isinstance(inst, IntsB):
                    current_pc = i * 4
                    target_pc = self.label_manager.labels[inst.label]
                    offset = target_pc - current_pc
                    f.write(self.generate_b_type(inst, offset))

                elif isinstance(inst, IntsJ):
                    current_pc = i * 4
                    target_pc = self.label_manager.labels[inst.label]
                    offset = target_pc - current_pc
                    f.write(self.generate_j_type(inst, offset))
        
    def generate_literal_num(self, imm, reg):
        self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, 0x0, imm)
        
    def generate_stmt(self, node):
        match node:
            case DeclarationStmt():
                reg = self.symbol_table.define(node.name)
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, 0x0, 0)
                
            case AssignmentStmt():
                reg = self.symbol_table.resolve(node.name)
                if isinstance(node.value, (IntLiteral, BoolLiteral)):
                    self.generate_literal_num(node.value.value, reg)
                    return
                
                reg_value = self.generate_expr(node.value)
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, reg_value, 0)
                self.reg_manager.free_temp(reg_value)
                
            case InitializationStmt():
                reg_value = 0
                if not isinstance(node.assign_stmt.value, (IntLiteral, BoolLiteral)):
                    reg_value = self.generate_expr(node.assign_stmt.value)
                
                real_reg = 0
                if self.symbol_table.exists_here(node.decl_stmt.name):
                    real_reg = self.symbol_table.resolve(node.decl_stmt.name)
                else:
                    real_reg = self.symbol_table.define(node.decl_stmt.name)
                
                if reg_value != 0:
                    self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, real_reg, reg_value, 0)
                    self.reg_manager.free_temp(reg_value)
                else:
                    self.generate_literal_num(node.assign_stmt.value.value, real_reg)
                    
            case CallFunc():
                if node.name == "print":
                    reg_param = self.generate_expr(node.params[0])
                    self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 10, reg_param, 0)
                    self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, 17, 0x0, 1)
                    self.emit_ecall()
                    self.reg_manager.free_temp(reg_param)
                    
            case BlockExpr():
                self.symbol_table.enter_scope()
                for stmt in node.stmts:
                    self.generate_stmt(stmt)
                self.symbol_table.exit_scope()    
                            
            case IfForm():
                exit = self.label_manager.create()
                end_if = self.label_manager.create()
                self.generate_cond(end_if, node.if_branch.cond)
                self.generate_stmt(node.if_branch.block)
                if node.elif_branches is None and node.else_branch is None:
                    self.label_manager.place_label(end_if, self.get_pc())
                    return
                elif node.elif_branches is None and not node.else_branch is None:
                    self.emit_jump(exit)
                    self.label_manager.place_label(end_if, self.get_pc())
                    
                    
                if not node.elif_branches is None:
                    self.emit_jump(exit)
                    self.label_manager.place_label(end_if, self.get_pc())
                    for i, branch in enumerate(node.elif_branches):
                        end_elif = self.label_manager.create()
                        self.generate_cond(end_elif, branch.cond)
                        self.generate_stmt(branch.block)
                        
                        if (len(node.elif_branches) - 1) == i and node.else_branch is None:
                            self.label_manager.place_label(end_elif, self.get_pc())
                            self.label_manager.place_label(exit, self.get_pc())
                            return
                        
                        self.emit_jump(exit)
                        self.label_manager.place_label(end_elif, self.get_pc())
                        
                if not node.else_branch is None:
                    self.generate_stmt(node.else_branch.block)
                    
                self.label_manager.place_label(exit, self.get_pc())
                
            case WhileForm():
                exit = self.label_manager.create()
                cond = self.label_manager.create()
                self.loop_stack.append((exit, cond))
                self.label_manager.place_label(cond, self.get_pc())
                self.generate_cond(exit, node.condition_field)
                self.generate_stmt(node.block_expr)
                self.emit_jump(cond)
                self.label_manager.place_label(exit, self.get_pc())
                
            case ContinueStmt():
                self.emit_jump(self.loop_stack[-1][1])
                
            case BreakStmt():
                self.emit_jump(self.loop_stack[-1][0])
            
    def emit_jump(self, label):
        self.emit_j_type(OpCode.JAL, 0x0, label)
    
    def generate_expr(self, node):
        if isinstance(node, (IntLiteral, BoolLiteral)):
            reg = self.reg_manager.alloc_temp()
            self.generate_literal_num(node.value, reg)
            return reg
        
        match node:
            case BinaryExpr():
                match node.operator:
                    case Operator.ADD:
                        if isinstance(node.right, IntLiteral):
                            reg_left = self.generate_expr(node.left)
                            reg = self.reg_manager.alloc_temp()
                            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, reg_left, node.right.value)
                            self.reg_manager.free_temp(reg_left)
                            return reg

                        if isinstance(node.left, IntLiteral):
                            reg_right = self.generate_expr(node.right)
                            reg = self.reg_manager.alloc_temp
                            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, reg_right, node.left.value)
                            self.reg_manager.free_temp(reg_right)
                            return reg

                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        reg = self.reg_manager.alloc_temp()
                        self.emit_r_type(OpCode.OP, F3_ALU.ADD_SUB, F7.STANDARD, reg, reg_left, reg_right)
                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)
                        return reg

                    
                    case Operator.SUB:
                        if isinstance(node.right, IntLiteral):
                            reg_left = self.generate_expr(node.left)
                            reg = self.reg_manager.alloc_temp()
                            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, reg_left, -(node.right.value))
                            self.reg_manager.free_temp(reg_left)
                            return reg

                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        reg = self.reg_manager.alloc_temp()
                        self.emit_r_type(OpCode.OP, F3_ALU.ADD_SUB, F7.ALT, reg, reg_left, reg_right)
                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)
                        return reg
                    
                    case Operator.MUL:
                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        reg = self.reg_manager.alloc_temp()
                        self.emit_r_type(OpCode.OP, F3_M_EXT.MUL, F7.M_EXT, reg, reg_left, reg_right)
                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)
                        return reg
                    
                    case Operator.DIV:
                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        reg = self.reg_manager.alloc_temp()
                        self.emit_r_type(OpCode.OP, F3_M_EXT.DIV, F7.M_EXT, reg, reg_left, reg_right)
                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)
                        return reg
                    
                    case Operator.MOD:
                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        reg = self.reg_manager.alloc_temp()
                        self.emit_r_type(OpCode.OP, F3_M_EXT.REM, F7.M_EXT, reg, reg_left, reg_right)
                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)
                        return reg
                    
                    case Operator.LT:
                        return self.generate_lt_expr(node)
                        
                    case Operator.GT:
                        right = node.right
                        node.right = node.left
                        node.left = right
                        return self.generate_lt_expr(node)
                    
                    case Operator.LE:
                        right = node.right
                        node.right = node.left
                        node.left = right
                        reg_lt = self.generate_lt_expr(node)
                        return self.generate_not_expr(reg_val=reg_lt)
                    
                    case Operator.GE:
                        reg_lt = self.generate_lt_expr(node)
                        return self.generate_not_expr(reg_val=reg_lt)
                    
                    case Operator.EQ:
                        return self.generate_eq_expr(node)
                        
                    case Operator.NE:
                        reg_eq = self.generate_eq_expr(node)
                        return self.generate_not_expr(reg_val=reg_eq)
                    
                    case Operator.AND:
                        return self.generate_and_expr(node)
                    
                    case Operator.OR:
                        return self.generate_or_expr(node)
                    
                        
            case UnaryExpr():
                match node.operator:
                    case Operator.NEG:
                        if isinstance(node.value, IntLiteral):
                            reg = self.reg_manager.alloc_temp()
                            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg, 0x0, -(node.value.value))
                            return reg
                        
                        reg_value = self.generate_expr(node.value)
                        reg = self.reg_manager.alloc_temp()
                        self.emit_r_type(OpCode.OP, F3_ALU.ADD_SUB, F7.ALT, reg, 0x0, reg_value)
                        self.reg_manager.free_temp(reg_value)
                        return reg

                    case Operator.NOT:
                        return self.generate_not_expr(node)
                        
            case VariableExpr():
                return self.symbol_table.resolve(node.name)
                

    def generate_eq_expr(self, node):
        if isinstance(node.left, (IntLiteral, BoolLiteral)):
            reg_right = self.generate_expr(node.right)
            reg_xor = self.reg_manager.alloc_temp()
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.XOR_XORI, reg_xor, reg_right, node.left.value)
            self.reg_manager.free_temp(reg_right)
            reg = self.reg_manager.alloc_temp()
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.SLTU_SLTIU, reg, reg_xor, 1)
            self.reg_manager.free_temp(reg_xor)
            return reg
        
        if isinstance(node.right, (IntLiteral, BoolLiteral)):
            reg_left = self.generate_expr(node.left)
            reg_xor = self.reg_manager.alloc_temp()
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.XOR_XORI, reg_xor, reg_left, node.right.value)
            self.reg_manager.free_temp(reg_left)
            reg = self.reg_manager.alloc_temp()
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.SLTU_SLTIU, reg, reg_xor, 1)
            self.reg_manager.free_temp(reg_xor)
            return reg
        
        reg_left = self.generate_expr(node.left)
        reg_right = self.generate_expr(node.right)
        reg_xor = self.reg_manager.alloc_temp()
        self.emit_r_type(OpCode.OP, F3_ALU.XOR_XORI, F7.STANDARD, reg_xor, reg_left, reg_right)
        self.reg_manager.free_temp(reg_left)
        self.reg_manager.free_temp(reg_right)
        reg = self.reg_manager.alloc_temp()
        self.emit_i_type(OpCode.OP_IMM, F3_ALU.SLTU_SLTIU, reg, reg_xor, 1)
        self.reg_manager.free_temp(reg_xor)
        return reg
    
    def generate_not_expr(self, node = None, reg_val = None):
        if not reg_val is None:
            reg = self.reg_manager.alloc_temp()
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.XOR_XORI, reg, reg_val, 1)
            self.reg_manager.free_temp(reg_val)
            return reg
            
        reg_value = self.generate_expr(node.value)
        reg = self.reg_manager.alloc_temp()
        self.emit_i_type(OpCode.OP_IMM, F3_ALU.XOR_XORI, reg, reg_value, 1)
        self.reg_manager.free_temp(reg_value)
        return reg
    
    def generate_lt_expr(self, node):
        if isinstance(node.right, IntLiteral):
            reg_left = self.generate_expr(node.left)
            reg = self.reg_manager.alloc_temp()
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.SLT_SLTI, reg, reg_left, node.right.value)
            self.reg_manager.free_temp(reg_left)
            return reg
        
        reg_left = self.generate_expr(node.left)
        reg_right = self.generate_expr(node.right)
        reg = self.reg_manager.alloc_temp()
        self.emit_r_type(OpCode.OP, F3_ALU.SLT_SLTI, F7.STANDARD, reg, reg_left, reg_right)
        self.reg_manager.free_temp(reg_left)
        self.reg_manager.free_temp(reg_right)
        return reg

    def generate_cond(self, label, node):
        match node:
            case BoolLiteral():
                reg_b = self.reg_manager.alloc_temp()
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg_b, 0x0, node.value)
                self.emit_b_type(OpCode.OP_B, F3_B.BEQ, reg_b, 0x0, label)
                self.reg_manager.free_temp(reg_b)
                
            case BinaryExpr():
                match node.operator:
                    case Operator.NE:
                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        self.emit_b_type(OpCode.OP_B, F3_B.BEQ, reg_left, reg_right, label)
                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)
                        
                    case Operator.EQ:
                        reg_left = self.generate_expr(node.left)
                        reg_right = self.generate_expr(node.right)
                        self.emit_b_type(OpCode.OP_B, F3_B.BNE, reg_left, reg_right, label)
                        self.reg_manager.free_temp(reg_left)
                        self.reg_manager.free_temp(reg_right)
                        
                    case Operator.LT:
                        self.generate_cond_lt(label, node)
                        
                    case Operator.GT:
                        right = node.right
                        node.right = node.left
                        node.left = right
                        self.generate_cond_lt(label, node)
                        
                    case Operator.LE:
                        right = node.right
                        node.right = node.left
                        node.left = right
                        self.generate_cond_ge(label, node)
                        
                    case Operator.GE:
                        self.generate_cond_ge(label, node)
                        
                    case Operator.AND:
                        self.generate_cond_and(node, label)
                        
                    
            case VariableExpr():
                self.emit_b_type(OpCode.OP_B, F3_B.BEQ, self.symbol_table.resolve(node.name), 0x0, label)

    def generate_cond_and(self, node, label=None, reg_x=None):
        reg_left = self.generate_expr(node.left)
        false_l = self.label_manager.create()
        exit = self.label_manager.create()
        if label is None:
            self.emit_b_type(OpCode.OP_B, F3_B.BEQ, reg_left, 0x0, false_l)
        else:
            self.emit_b_type(OpCode.OP_B, F3_B.BEQ, reg_left, 0x0, label)
        
        self.reg_manager.free_temp(reg_left)
        reg_right = self.generate_expr(node.right)
        
        if label is None:
            self.emit_b_type(OpCode.OP_B, F3_B.BEQ, reg_right, 0x0, false_l)
        else:
            self.emit_b_type(OpCode.OP_B, F3_B.BEQ, reg_right, 0x0, label)
        
        self.reg_manager.free_temp(reg_right)
        
        if label is None:
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg_x, 0x0, 1)
            self.emit_jump(exit)
            self.label_manager.place_label(false_l, self.get_pc())
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg_x, 0x0, 0)
            self.label_manager.place_label(exit, self.get_pc())
            
        
    def generate_cond_lt(self, label, node):
        reg_left = self.generate_expr(node.left)
        reg_right = self.generate_expr(node.right)
        self.emit_b_type(OpCode.OP_B, F3_B.BGE, reg_left, reg_right, label)
        self.reg_manager.free_temp(reg_left)
        self.reg_manager.free_temp(reg_right)
        
    def generate_cond_ge(self, label, node):
        reg_left = self.generate_expr(node.left)
        reg_right = self.generate_expr(node.right)
        self.emit_b_type(OpCode.OP_B, F3_B.BLT, reg_left, reg_right, label)
        self.reg_manager.free_temp(reg_left)
        self.reg_manager.free_temp(reg_right)
        
    def generate_and_expr(self, node):
        if isinstance(node.left, (VariableExpr, BoolLiteral)) or isinstance(node.right, (VariableExpr, BoolLiteral)):
            if isinstance(node.left, BoolLiteral):
                reg_right = self.generate_expr(node.right)
                reg = self.reg_manager.alloc_temp()
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.AND_ANDI, reg, reg_right, node.left.value)
                self.reg_manager.free_temp(reg_right)
                return reg
            if isinstance(node.right, BoolLiteral):
                reg_left = self.generate_expr(node.left)
                reg = self.reg_manager.alloc_temp()
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.AND_ANDI, reg, reg_left, node.right.value)
                self.reg_manager.free_temp(reg_left)
                return reg
                
            reg_left = self.generate_expr(node.left)
            reg_right = self.generate_expr(node.right)
            reg = self.reg_manager.alloc_temp()
            self.emit_r_type(OpCode.OP, F3_ALU.AND_ANDI, F7.STANDARD, reg, reg_left, reg_right)
            self.reg_manager.free_temp(reg_left)
            self.reg_manager.free_temp(reg_right)
            return reg
        
        reg = self.reg_manager.alloc_temp()
        self.generate_cond_and(node, reg_x=reg)
        return reg
    
    def generate_or_expr(self, node):
        if isinstance(node.left, (VariableExpr, BoolLiteral)) or isinstance(node.right, (VariableExpr, BoolLiteral)):
            if isinstance(node.left, BoolLiteral):
                reg_right = self.generate_expr(node.right)
                reg = self.reg_manager.alloc_temp()
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.OR_ORI, reg, reg_right, node.left.value)
                self.reg_manager.free_temp(reg_right)
                return reg
            if isinstance(node.right, BoolLiteral):
                reg_left = self.generate_expr(node.left)
                reg = self.reg_manager.alloc_temp()
                self.emit_i_type(OpCode.OP_IMM, F3_ALU.OR_ORI, reg, reg_left, node.right.value)
                self.reg_manager.free_temp(reg_left)
                return reg
                
            reg_left = self.generate_expr(node.left)
            reg_right = self.generate_expr(node.right)
            reg = self.reg_manager.alloc_temp()
            self.emit_r_type(OpCode.OP, F3_ALU.OR_ORI, F7.STANDARD, reg, reg_left, reg_right)
            self.reg_manager.free_temp(reg_left)
            self.reg_manager.free_temp(reg_right)
            return reg
        
        reg = self.reg_manager.alloc_temp()
        self.generate_cond_or(node, reg_x=reg)
        return reg
    
    def generate_cond_or(self, node, label=None, reg_x=None):
        reg_left = self.generate_expr(node.left)
        true_l = self.label_manager.create()
        exit = self.label_manager.create()
        if label is None:
            self.emit_b_type(OpCode.OP_B, F3_B.BNE, reg_left, 0x0, true_l)
        else:
            self.emit_b_type(OpCode.OP_B, F3_B.BNE, reg_left, 0x0, label)
        
        self.reg_manager.free_temp(reg_left)
        reg_right = self.generate_expr(node.right)
        
        if label is None:
            self.emit_b_type(OpCode.OP_B, F3_B.BNE, reg_right, 0x0, true_l)
        else:
            self.emit_b_type(OpCode.OP_B, F3_B.BNE, reg_right, 0x0, label)
        
        self.reg_manager.free_temp(reg_right)
        
        if label is None:
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg_x, 0x0, 0)
            self.emit_jump(exit)
            self.label_manager.place_label(true_l, self.get_pc())
            self.emit_i_type(OpCode.OP_IMM, F3_ALU.ADD_SUB, reg_x, 0x0, 1)
            self.label_manager.place_label(exit, self.get_pc())
            