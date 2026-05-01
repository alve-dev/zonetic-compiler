from zonc.zonast import *
from zonc.enviroment import *

class DeadCodeElimination:
    def eliminate_in_program(self, node: Program | BlockExpr):
        scope: Enviroment  = node.scope
        scope.values.clear()
        eliminate = 0
        for i, stmt in enumerate(node.stmts[:]):
            if isinstance(stmt, DeclarationStmt):
                symbol = Symbol(stmt.mut, stmt.type, True, i)
                scope.define(stmt.name, symbol)
                
            elif isinstance(stmt, AssignmentStmt):
                symbol = scope.get_symbol(stmt.name)
                if symbol.mutability == False:
                    if isinstance(stmt.value, LiteralNode):
                        if symbol.is_empty:
                            symbol.is_empty = False
                        else:
                            node.stmts.pop(i + eliminate)
                            eliminate -= 1
                    
                    elif isinstance(stmt.value, BlockExpr):
                        self.eliminate_in_program(stmt.value)
                    
                    elif isinstance(stmt.value, IfForm):
                        new_if = self.eliminate_in_if(stmt.value)
                        stmt.value = new_if
                
            elif isinstance(stmt, InitializationStmt):
                if stmt.decl_stmt.mut == False:
                    if isinstance(stmt.assign_stmt.value, LiteralNode):
                        node.stmts.pop(i + eliminate)
                        eliminate -= 1
                    
                    elif isinstance(stmt.assign_stmt.value, BlockExpr):
                        self.eliminate_in_program(stmt.assign_stmt.value)
                    
                    elif isinstance(stmt.assign_stmt.value, IfForm):
                        new_if = self.eliminate_in_if(stmt.assign_stmt.value)
                        stmt.assign_stmt.value = new_if
                
                else:
                    scope.define(
                        stmt.decl_stmt.name,
                        Symbol(stmt.decl_stmt.mut, stmt.decl_stmt.type, False, stmt.decl_stmt.span)
                    )
                    
            elif isinstance(stmt, BlockExpr):
                self.eliminate_in_program(stmt)
                
            elif isinstance(stmt, IfForm):
                new_if = self.eliminate_in_if(stmt)
                node.stmts[i + eliminate] = new_if
                
            elif isinstance(stmt, WhileForm):
                if isinstance(stmt.condition_field, BoolLiteral) and stmt.condition_field.value == 0:
                    node.stmts.pop(i + eliminate)
                    eliminate += 1    
            
                
    def eliminate_in_if(self, if_form: IfForm):
        if isinstance(if_form.if_branch.cond, BoolLiteral) and if_form.if_branch.cond.value == 1:
            self.eliminate_in_program(if_form.if_branch.block)
            return if_form.if_branch.block
        if isinstance(if_form.if_branch.cond, BoolLiteral) and if_form.if_branch.cond.value == 0:
            if_form.if_branch = None

        if if_form.elif_branches:
            new_elifs = []
            for branch in if_form.elif_branches:
                if isinstance(branch.cond, BoolLiteral):
                    if branch.cond.value == 1:
                        if if_form.if_branch is None:
                            self.eliminate_in_program(branch.block)
                            return branch.block
                        else:
                            if_form.else_branch = branch
                            if_form.elif_branches = new_elifs
                            return if_form
                    else:
                        continue
                new_elifs.append(branch)
            if_form.elif_branches = new_elifs if new_elifs else None

        if if_form.else_branch:
            if if_form.if_branch is None and not if_form.elif_branches:
                self.eliminate_in_program(if_form.else_branch.block)
                return if_form.else_branch.block
        
        if if_form.if_branch is None and if_form.elif_branches:
            first_elif = if_form.elif_branches.pop(0)
            if_form.if_branch = first_elif
            return if_form

        return if_form

            
                    
            
                