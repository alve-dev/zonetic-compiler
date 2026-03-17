from .file_map import FileMap

class Span:
    def __init__(self, start_offset: int, end_offset: int, file_map: FileMap):
        self.start = start_offset
        self.end = end_offset
        self.line_start, self.column_start = file_map.get_location(self.start)
        
        if self.end > self.start:
            self.line_end, self.column_end = file_map.get_location(self.end - 1)
            self.column_end += 1
        else:
            self.line_end, self.column_end = self.line_start, self.column_start
        
        
    