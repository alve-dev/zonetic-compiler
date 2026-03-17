from .token import Token

class ListTokens:
    def __init__(self):
        self._list = []
        self._lenght = 0
                
    
    def _add(self, token: Token):
        self._list.append(token)
        self._lenght += 1
        
        
    def _replace(self, idx: int, token: Token):
        self._list[idx] = token
        
        
    def _del(self, idx: int):
        self._list.pop(idx)
        self._lenght -= 1
        
    def _len(self) -> int:
        return self._lenght
    
    
    def _peek(self, idx: int) -> Token:
        if idx <= self._len():
            return self._list[idx]
    
    
    def __str__(self):
        return str(self.list)