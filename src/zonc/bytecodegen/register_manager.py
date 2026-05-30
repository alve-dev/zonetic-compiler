from .bytecodescope import ZonVar, RegT
from zonc.zonast import ZonType

class RegisterManager:
    def __init__(self, offset_stack):
        # x31 y f31 son tx6 y tf11 pero se usaran como comodin para
        # la carga de offsets temps
        
        self.temps = [5, 6, 7, 28, 29]
        self.ftemps = [0, 1, 2, 3, 4, 5, 6, 7, 28, 29]
        self.offset_stack = offset_stack
        self.used_temps = [True] * len(self.temps)
        self.used_ftemps = [True] * len(self.ftemps)
        self.free_spill_offsets = []

    def alloc_temp(self):
        for i in range(len(self.temps)):
            if self.used_temps[i]:
                self.used_temps[i] = False
                return ZonVar(self.temps[i], RegT.X, ZonType(0, "UNKNOWN"))
            
        if self.free_spill_offsets:
            recycled_offset = self.free_spill_offsets.pop()
            return ZonVar(None, RegT.X, ZonType(0, "UNKNOWN"), recycled_offset)
        
        current_offset = self.offset_stack[-1][0]
        self.offset_stack[-1][0] -= 8
        return ZonVar(None, RegT.X, ZonType(0, "UNKNOWN"), offset_stack=current_offset)
    
    def alloc_ftemp(self):
        for i in range(len(self.ftemps)):
            if self.used_ftemps[i]:
                self.used_ftemps[i] = False
                return ZonVar(self.ftemps[i], RegT.F, ZonType(0, "UNKNOWN"))
            
        if self.free_spill_offsets:
            recycled_offset = self.free_spill_offsets.pop()
            return ZonVar(None, RegT.F, ZonType(0, "UNKNOWN"), recycled_offset)
        
        current_offset = self.offset_stack[-1][0]
        self.offset_stack[-1][0] -= 8
        return ZonVar(None, RegT.F, ZonType(0, "UNKNOWN"), offset_stack=current_offset)

    def free_temp(self, reg: ZonVar):
        if reg.reg is None:
            self.free_spill_offsets.append(reg.offset_stack)
        
        else:
            if reg.regt == RegT.X:
                for i in range(len(self.temps)):
                    if self.temps[i] == reg.reg:
                        self.used_temps[i] = True
                        break
                    
            elif reg.regt == RegT.F:
                for i in range(len(self.ftemps)):
                    if self.ftemps[i] == reg.reg:
                        self.used_ftemps[i] = True
                        break
    
    def get_active_regs(self):
        current_used_x = []
        
        i = 0
        for is_used in self.used_temps:
            if not is_used:
                i += 1
                
        current_used_x = self.temps[:i]
        
        i = 0
        for is_used in self.used_ftemps:
            if not is_used:
                i += 1
                
        return (current_used_x, self.ftemps[:i])
        