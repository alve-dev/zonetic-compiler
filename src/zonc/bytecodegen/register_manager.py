from .bytecodescope import ZonVar, RegT
from zonc.zonast import ZonType

class RegisterManager:
    def __init__(self):
        self.temps = [5, 6, 7, 28, 29, 30, 31]
        self.ftemps = [0, 1, 2, 3, 4, 5, 6, 7]
        self.used_temps = set()
        self.used_ftemps = set()

    def alloc_temp(self):
        for r in self.temps:
            if r not in self.used_temps:
                self.used_temps.add(r)
                return ZonVar(r, RegT.X, ZonType(0, "UNKNOWN"))
            
        raise Exception("Zonny se quedó sin bolsillos temporales (t)!")
    
    def alloc_ftemp(self):
        for r in self.ftemps:
            if r not in self.used_ftemps:
                self.used_ftemps.add(r)
                return ZonVar(r, RegT.F, ZonType(0, "UNKNOWN"))
            
        raise Exception("Zonny se quedó sin bolsillos temporales para floats (ft)!")

    def free_temp(self, reg: ZonVar):
        if reg.regt == RegT.X:
            if reg.reg in self.used_temps:
                self.used_temps.remove(reg.reg)
                
        elif reg.regt == RegT.F:
            if reg.reg in self.used_ftemps:
                self.used_ftemps.remove(reg.reg)
        