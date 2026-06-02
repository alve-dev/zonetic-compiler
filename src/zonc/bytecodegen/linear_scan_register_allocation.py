from zonc.zonast import *

class LinearScanRegisterAllocation:
    def __init__(self, num_available_regs=5, num_available_fregs=10):
        self.NUM_REGS = num_available_regs
        self.NUM_FREGS = num_available_fregs
        
        self.current_regs = 0
        self.current_fregs = 0
        
        self.max_regs_needed = 0
        self.max_fregs_needed = 0
        
        self.seen_ints = set()
        self.seen_floats = set()
        self.has_call = False
        
        self.extra = 0
        
        self.saved_x = [9, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]
        self.saved_f = [8, 9, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]  

    def analyze_function(self, stmts: list, params: list = None) -> tuple:
        self.current_regs = 0
        self.current_fregs = 0
        self.max_regs_needed = 0
        self.max_fregs_needed = 0
        self.seen_ints.clear()
        self.seen_floats.clear()
        self.has_call = False
        self.extra = 0

        if params is not None:
            for param in params:
                if param.zontype.num in [1, 3, 6]:
                    self.seen_ints.add(param.name)
                elif param.zontype.num in [2, 7]:
                    self.seen_floats.add(param.name)

        self._scan_list(stmts)

        extra_ints = max(0, len(self.seen_ints) - 11) 
        extra_floats = max(0, len(self.seen_floats) - 12)

        temps_overflow = max(0, self.max_regs_needed - self.NUM_REGS)
        ftemps_overflow = max(0, self.max_fregs_needed - self.NUM_FREGS)

        total_slots = extra_ints + extra_floats + temps_overflow + ftemps_overflow
        
        bytes_needed = (total_slots * 8) + 16 + self.extra
        
        if bytes_needed % 16 != 0:
            bytes_needed += (16 - (bytes_needed % 16))
            
        used_save_x = len(self.seen_ints)
        if used_save_x > len(self.saved_x): used_save_x = len(self.saved_x)
        used_save_x = self.saved_x[:used_save_x]
        
        used_save_f = len(self.seen_floats)
        if used_save_f > len(self.saved_f): used_save_f = len(self.saved_f)
        used_save_f = self.saved_f[:used_save_f]

        return bytes_needed, self.has_call, (used_save_x, used_save_f)

    def _alloc_t(self):
        self.current_regs += 1
        if self.current_regs > self.max_regs_needed:
            self.max_regs_needed = self.current_regs

    def _free_t(self):
        self.current_regs = max(0, self.current_regs - 1)

    def _alloc_ft(self):
        self.current_fregs += 1
        if self.current_fregs > self.max_fregs_needed:
            self.max_fregs_needed = self.current_fregs

    def _free_ft(self):
        self.current_fregs = max(0, self.current_fregs - 1)

    def _scan_list(self, nodes):
        if not nodes: return
        for node in nodes:
            self._scan_node(node)

    def _scan_node(self, node):
        if node is None: return

        match node:
            case FuncForm():
                if node.params is not None:
                    for param in node.params:
                        if param.zontype.num in [1, 3, 6]:
                            self.seen_ints.add(param.name)
                          
                        elif param.zontype.num in [2, 7]:
                            self.seen_floats.add(param.name)  
                            
            case InitializationStmt():
                self._scan_node(node.assign_stmt.value)
                if node.decl_stmt.name in self.seen_floats or node.decl_stmt.name in self.seen_ints:
                    return
                
                if node.decl_stmt.type.num in [1, 3, 6]:
                    self.seen_ints.add(node.decl_stmt.name)
                elif node.decl_stmt.type.num in [2, 7]:
                    self.seen_floats.add(node.decl_stmt.name)

            case DeclarationStmt():
                if node.decl_stmt.name in self.seen_floats or node.decl_stmt.name in self.seen_ints:
                    return
                
                if node.type.num in [1, 3, 6]:
                    self.seen_ints.add(node.name)
                elif node.type.num in [2, 7]:
                    self.seen_floats.add(node.name)

            case AssignmentStmt():
                self._scan_node(node.value)
                
            case CastExpr():
                self._scan_node(node.value)
                if node.zontype.num in [2,7]:
                    self._free_ft()
                    self._alloc_ft()
                else:
                    self._free_t()
                    self._alloc_t()
                
            case StringLiteral():
                self._alloc_t()
                self._free_t()

            case BinaryExpr():
                if node.operator in (Operator.CONCAT, Operator.EQ_STR, Operator.NE_STR,
                         Operator.BNAND, Operator.BNOR, Operator.BXNOR):
                    self._scan_node(node.left)
                    self._scan_node(node.right)
                    self._free_t()
                    self._free_t()
                    self._alloc_t()
                    return
                
                if node.operator in [Operator.ADD, Operator.SUB]:
                    if isinstance(node.right, IntLiteral) and (-2048 <= node.right.value <= 2047):
                        self._scan_node(node.left)
                        self._alloc_t() 
                        return
                    if isinstance(node.left, IntLiteral) and (-2048 <= node.left.value <= 2047):
                        self._scan_node(node.right)
                        self._alloc_t() 
                        return

                self._scan_node(node.left)
                self._scan_node(node.right)
                
                if node.operator in [Operator.LT, Operator.GT, Operator.LE, Operator.GE, Operator.EQ, Operator.NE]:
                    if isinstance(node.left, FloatLiteral) or isinstance(node.right, FloatLiteral):
                        self._free_ft()
                        self._free_ft()
                    else:
                        self._free_t()
                        self._free_t()
                    self._alloc_t()
                else:
                    if isinstance(node.left, FloatLiteral) or isinstance(node.right, FloatLiteral):
                        self._free_ft()
                        self._free_ft()
                        self._alloc_ft()
                    else:
                        self._free_t()
                        self._free_t()
                        self._alloc_t()

            case UnaryExpr():
                self._scan_node(node.value)
                if node.operator == Operator.NEG and isinstance(node.value, FloatLiteral):
                    self._free_ft()
                    self._alloc_ft()
                else:
                    self._free_t()
                    self._alloc_t()

            case CallFunc():
                if node.name in ["print"]:
                    if isinstance(node.params[0], CallFunc): self.has_call = True
                    return
                
                self.has_call = True
                if node.params is not None:
                    for param in node.params:
                        self._scan_node(param)
                
                    for param in node.params:
                        if isinstance(param, FloatLiteral):
                            self._free_ft()
                        else:
                            self._free_t()
    
                self._alloc_t()
                self._alloc_ft()
                self.extra += self.current_regs * 8 + self.current_fregs * 8 
                

            case IfForm():
                if node.if_branch:
                    self._scan_node(node.if_branch.cond)
                    self._scan_node(node.if_branch.block)
                if node.elif_branches:
                    for branch in node.elif_branches:
                        self._scan_node(branch.cond)
                        self._scan_node(branch.block)
                if node.else_branch:
                    self._scan_node(node.else_branch.block)

            case BlockExpr():
                self._scan_list(node.stmts)

            case WhileForm():
                self._scan_node(node.condition_field)
                self._scan_node(node.block_expr)

            case GiveStmt() | ReturnStmt():
                self._scan_node(node.value)
                if isinstance(node.value, FloatLiteral):
                    self._free_ft()
                else:
                    self._free_t()

            case IntLiteral() | BoolLiteral():
                self._alloc_t()
                self._alloc_t()
                self._free_t()

            case FloatLiteral():
                self._alloc_ft()
                self._alloc_t()
                self._free_t()
                
            case StringLiteral():
                self._alloc_t()
                self._free_t()