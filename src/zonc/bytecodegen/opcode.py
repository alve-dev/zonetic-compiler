from enum import IntEnum

class OpCode(IntEnum):
    OP_IMM = 0x13
    OP = 0x33
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
    

class F7(IntEnum):
    STANDARD = 0x00
    M_EXT = 0x01
    ALT = 0x20
    