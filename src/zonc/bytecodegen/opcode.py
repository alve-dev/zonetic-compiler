from enum import IntEnum

class OpCode(IntEnum):
    L = 0x03
    FL = 0x07
    OP_IMM = 0x13
    AUIPC = 0x17
    OP_IMM_32 = 0x1B
    OP = 0x33
    OP_32 = 0x3B
    LUI = 0x37
    OP_F = 0x53
    OP_B = 0x63
    JAL = 0x6F
    ECALL = 0x73

class F3_ALU(IntEnum):
    ADD_SUB = 0x00
    SLT_SLTI = 0x02
    SLTU_SLTIU = 0x03
    XOR_XORI = 0x04
    OR_ORI = 0x06
    AND_ANDI = 0x07

class F3_M_EXT(IntEnum):
    MUL = 0x00
    DIV = 0x04
    REM = 0x06
    
class F3_B(IntEnum):
    BEQ = 0x00
    BNE = 0x01
    BLT = 0x04
    BGE = 0x05
    BLTU = 0x06
    BGEU = 0x07
    
class F3_FL(IntEnum):
    FLD = 0x3
    
class F3_L(IntEnum):
    LD = 0x3

class F7(IntEnum):
    STANDARD = 0x00
    M_EXT_OR_FADD_D = 0x01
    FSUB_S = 0x04
    FSUB_D = 0x05
    FMUL_S = 0x08
    FMUL_D = 0x09
    FDIV_S = 0x0C
    FDIV_D = 0x0D
    FSGNJ_S = 0x10
    ALT = 0x20
    FCOMP_S = 0x50
    FCOMP_D = 0x51
    FCVT_D_L = 0x61
    FCVT_S_W = 0x68
    FMV_D_X = 0x71
    FMV_W_X = 0x78
    
    