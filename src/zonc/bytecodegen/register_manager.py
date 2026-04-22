class RegisterManager:
    def __init__(self):
        self.temps = [5, 6, 7, 28, 29, 30, 31]
        
        self.used_temps = set()

    def alloc_temp(self):
        for r in self.temps:
            if r not in self.used_temps:
                self.used_temps.add(r)
                return r
        raise Exception("Zonny se quedó sin bolsillos temporales (t)!")

    def free_temp(self, reg):
        if reg in self.used_temps:
            self.used_temps.remove(reg)