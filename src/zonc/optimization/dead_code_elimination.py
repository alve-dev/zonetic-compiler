"""Dead code elimination optimization pass.

Runs after constant folding, which means immutable variables are already
inlined as literals. This pass exploits that to remove code that can
never execute:

  - `inmut x = 5` — the declaration+assignment collapses to nothing
    because constant folding already embedded the value everywhere x is used.
  - `if true { ... }` — the if form is replaced by its body directly.
  - `if false { ... }` — the entire branch is removed.
  - `while false { ... }` — the whole loop is removed.
"""

from zonc.zonast import *
from zonc.enviroment import Environment, Symbol
from zonc.zonc_errors import DiagnosticEngine


class DeadCodeElimination:
    def __init__(self, diag: DiagnosticEngine) -> None:
        self._diag = diag

    # ------------------------------------------------------------------
    # Program / block entry point
    # ------------------------------------------------------------------

    def eliminate_in_program(self, node: Program | BlockExpr) -> None:
        """Eliminate dead statements from a program or block in-place."""
        scope: Environment = node.scope
        scope.clear()

        # We iterate over a snapshot of the list and track how many items
        # we have removed so far to adjust indices on pop().
        removed = 0

        for i, stmt in enumerate(node.stmts[:]):
            real_i = i + removed

            if isinstance(stmt, DeclarationStmt):
                scope.define(stmt.name, Symbol(stmt.mut, stmt.type, True, i))

            elif isinstance(stmt, AssignmentStmt):
                removed += self._handle_assignment(node, stmt, scope, real_i)

            elif isinstance(stmt, InitializationStmt):
                removed += self._handle_initialization(node, stmt, scope, real_i)

            elif isinstance(stmt, BlockExpr):
                self.eliminate_in_program(stmt)

            elif isinstance(stmt, IfForm):
                node.stmts[real_i] = self.eliminate_in_if(stmt)

            elif isinstance(stmt, WhileForm):
                # while false { } will never run — drop it entirely
                if isinstance(stmt.condition_field, BoolLiteral) and stmt.condition_field.value == 0:
                    node.stmts.pop(real_i)
                    removed -= 1

            elif isinstance(stmt, FuncForm):
                self.eliminate_in_program(stmt.block_expr)

    # ------------------------------------------------------------------
    # Assignment and initialization handlers
    # ------------------------------------------------------------------

    def _handle_assignment(
        self,
        node: Program | BlockExpr,
        stmt: AssignmentStmt,
        scope: Environment,
        real_i: int,
    ) -> int:
        """Process an assignment to an immutable variable.
        Returns the change in removed count (0 or -1).
        """
        is_array = isinstance(stmt.target, IndexExpr)
        name = stmt.target.name if is_array else stmt.target
        symbol = scope.get(name)

        if symbol.mutability:
            return 0

        
        if symbol is None or symbol.mutability:
            return 0

        if isinstance(stmt.value, LiteralNode):
            if symbol.is_empty:
                symbol.is_empty = False
            else:
                # second assignment to an inmut — already inlined, drop it
                node.stmts.pop(real_i)
                return -1

        elif isinstance(stmt.value, BlockExpr):
            self.eliminate_in_program(stmt.value)

        elif isinstance(stmt.value, IfForm):
            stmt.value = self.eliminate_in_if(stmt.value)

        return 0

    def _handle_initialization(
        self,
        node: Program | BlockExpr,
        stmt: InitializationStmt,
        scope: Environment,
        real_i: int,
    ) -> int:
        """Process an initialization statement.
        Returns the change in removed count (0 or -1).
        """
        if not stmt.decl_stmt.mut:
            # inmut + literal value: constant folding already inlined it everywhere,
            # so the statement itself is dead and can be removed
            if isinstance(stmt.assign_stmt.value, LiteralNode):
                node.stmts.pop(real_i)
                return -1

            elif isinstance(stmt.assign_stmt.value, BlockExpr):
                self.eliminate_in_program(stmt.assign_stmt.value)

            elif isinstance(stmt.assign_stmt.value, IfForm):
                stmt.assign_stmt.value = self.eliminate_in_if(stmt.assign_stmt.value)

        else:
            # mutable variable: keep it, but register it in scope
            scope.define(
                stmt.decl_stmt.name,
                Symbol(stmt.decl_stmt.mut, stmt.decl_stmt.type, False, stmt.decl_stmt.span),
            )

        return 0

    # ------------------------------------------------------------------
    # If form simplification
    # ------------------------------------------------------------------

    def eliminate_in_if(self, if_form: IfForm) -> BlockExpr | IfForm:
        """Simplify an if form whose branches have constant conditions.

        Returns either the surviving block (when a branch is always taken)
        or the pruned IfForm (when at least one branch remains dynamic).
        """
        # if true { ... } — replace the whole if with just the body
        if isinstance(if_form.if_branch.cond, BoolLiteral) and if_form.if_branch.cond.value == 1:
            self.eliminate_in_program(if_form.if_branch.block)
            return if_form.if_branch.block

        # if false { ... } — drop the if branch entirely
        if isinstance(if_form.if_branch.cond, BoolLiteral) and if_form.if_branch.cond.value == 0:
            if_form.if_branch = None

        # prune elif branches with constant conditions
        if if_form.elif_branches:
            surviving = []
            for branch in if_form.elif_branches:
                if isinstance(branch.cond, BoolLiteral):
                    if branch.cond.value == 1:
                        # this elif is always taken — promote or collapse
                        if if_form.if_branch is None:
                            self.eliminate_in_program(branch.block)
                            return branch.block
                        else:
                            if_form.else_branch    = branch
                            if_form.elif_branches  = surviving
                            return if_form
                    else:
                        continue  # elif false — skip it
                surviving.append(branch)
            if_form.elif_branches = surviving or None

        # else { ... } and nothing else survived — collapse to the else body
        if if_form.else_branch:
            if if_form.if_branch is None and not if_form.elif_branches:
                self.eliminate_in_program(if_form.else_branch.block)
                return if_form.else_branch.block

        # promote first surviving elif to the if position if the original if was dropped
        if if_form.if_branch is None and if_form.elif_branches:
            if_form.if_branch = if_form.elif_branches.pop(0)

        return if_form