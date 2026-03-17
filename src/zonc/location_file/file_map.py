class FileMap:
    def __init__(self, code: str):
        self.line_starts = [0]
        for offset, char in enumerate(code):
            if char == '\n':
                self.line_starts.append(offset + 1)
        self.line_starts.append(len(code))
            
                
                
    def get_location(self, offset: int) -> tuple[int, int]:
        """line = index 0, column = index 1"""
        
        start = 0
        end = len(self.line_starts) - 1
        line_idx = 0 # Guardará el índice de la línea encontrada
        
        # Búsqueda binaria de "Piso" (Floor search)
        while start <= end:
            half = (start + end) // 2
            
            if self.line_starts[half] <= offset:
                line_idx = half     # Este es un candidato posible, guardamos el índice
                start = half + 1    # Intentamos buscar uno más a la derecha
            else:
                end = half - 1      # Es muy alto, buscamos a la izquierda
        
        # Una vez encontrado el índice de la línea:
        line = line_idx + 1
        column = offset - self.line_starts[line_idx] + 1
        
        return line, column
        
