from __future__ import annotations
from dataclasses import dataclass

from typing import Optional, Sequence, Tuple, List

from task1.ast import (
    Program, FuncDef,
    Stmt, VarDecl, Break, ExprStmt, If, While, DoLoop,
    Expr, Assign, Binary, Unary, Place, Literal, CallOrIndexer,
)

from .cfg import CFG


@dataclass
class _LoopCtx:
    break_target: int  # break nereye atlayacak


class CFGBuilder:
    def build_for_func(self, f: FuncDef) -> CFG:
        cfg = CFG(name=f.signature.name)

        entry = cfg.new_block("ENTRY")
        exit_ = cfg.new_block("EXIT")
        cfg.entry = entry
        cfg.exit = exit_

        body = getattr(f, "body", None)
        if not body:
            cfg.errors.append(f"[{cfg.name}] function has no body")
            cfg.add_edge(entry, exit_)
            return cfg

        loop_stack: List[_LoopCtx] = []
        start_id, end_id = self._build_stmt_list(cfg, body, loop_stack)

        if start_id is None:
            cfg.add_edge(entry, exit_)
        else:
            cfg.add_edge(entry, start_id)
            if end_id is not None:
                cfg.add_edge(end_id, exit_)

        return cfg

    def _build_stmt_list(
        self,
        cfg: CFG,
        stmts: Sequence[Stmt],
        loop_stack: List[_LoopCtx],
    ) -> Tuple[Optional[int], Optional[int]]:
        first_start: Optional[int] = None
        prev_end: Optional[int] = None

        for st in stmts:
            s, e = self._build_stmt(cfg, st, loop_stack)

            if first_start is None and s is not None:
                first_start = s

            if prev_end is not None and s is not None:
                cfg.add_edge(prev_end, s)

            prev_end = e

        return first_start, prev_end

    def _build_stmt(
        self,
        cfg: CFG,
        st: Stmt,
        loop_stack: List[_LoopCtx],
    ) -> Tuple[Optional[int], Optional[int]]:
        if isinstance(st, VarDecl):
            b = cfg.new_block(self._stmt_to_str(st))
            return b, b

        if isinstance(st, ExprStmt):
            self._collect_calls(cfg, st.expr)
            b = cfg.new_block(self._stmt_to_str(st))
            return b, b

        if isinstance(st, Break):
            b = cfg.new_block("break")
            if not loop_stack:
                cfg.errors.append(f"[{cfg.name}] break outside loop")
                return b, None
            cfg.add_edge(b, loop_stack[-1].break_target, "break")
            return b, None

        if isinstance(st, If):
            self._collect_calls(cfg, st.cond)
            cond_id = cfg.new_block(f"if {self._expr_to_str(st.cond)}")

            then_start, then_end = self._build_stmt_list(cfg, st.then_body or [], loop_stack)

            else_start, else_end = (None, None)
            if st.else_body:
                else_start, else_end = self._build_stmt_list(cfg, st.else_body, loop_stack)

            join_id = cfg.new_block("join")

            if then_start is None:
                cfg.add_edge(cond_id, join_id, "True")
            else:
                cfg.add_edge(cond_id, then_start, "True")
                if then_end is not None:
                    cfg.add_edge(then_end, join_id)

            if else_start is None:
                cfg.add_edge(cond_id, join_id, "False")
            else:
                cfg.add_edge(cond_id, else_start, "False")
                if else_end is not None:
                    cfg.add_edge(else_end, join_id)

            return cond_id, join_id

        if isinstance(st, While):
            self._collect_calls(cfg, st.cond)
            cond_id = cfg.new_block(f"while {self._expr_to_str(st.cond)}")

            after_id = cfg.new_block("after_while")
            loop_stack.append(_LoopCtx(break_target=after_id))

            body_start, body_end = self._build_stmt_list(cfg, st.body or [], loop_stack)
            loop_stack.pop()

            if body_start is None:
                cfg.add_edge(cond_id, cond_id, "True")
            else:
                cfg.add_edge(cond_id, body_start, "True")
                if body_end is not None:
                    cfg.add_edge(body_end, cond_id)

            cfg.add_edge(cond_id, after_id, "False")
            return cond_id, after_id

        if isinstance(st, DoLoop):
            self._collect_calls(cfg, st.cond)

            after_id = cfg.new_block("after_do")
            loop_stack.append(_LoopCtx(break_target=after_id))

            body_start, body_end = self._build_stmt_list(cfg, st.body or [], loop_stack)
            loop_stack.pop()

            cond_id = cfg.new_block(f"do_{st.mode} {self._expr_to_str(st.cond)}")

            if body_start is None:
                cfg.add_edge(cond_id, cond_id)
                cfg.add_edge(cond_id, after_id)
                return cond_id, after_id

            if body_end is not None:
                cfg.add_edge(body_end, cond_id)

            if str(st.mode).lower() == "while":
                cfg.add_edge(cond_id, body_start, "True")
                cfg.add_edge(cond_id, after_id, "False")
            else:
                cfg.add_edge(cond_id, after_id, "True")
                cfg.add_edge(cond_id, body_start, "False")

            return body_start, after_id

        b = cfg.new_block(f"[unhandled stmt] {type(st).__name__}")
        cfg.errors.append(f"[{cfg.name}] unhandled stmt type: {type(st).__name__}")
        return b, b

    def _stmt_to_str(self, st: Stmt) -> str:
        if isinstance(st, VarDecl):
            names = ", ".join(getattr(st, "names", []))
            t = getattr(st, "type_ref", None)
            return f"dim {names} as {self._type_to_str(t)}"
        if isinstance(st, ExprStmt):
            return f"{self._expr_to_str(st.expr)};"
        if isinstance(st, Break):
            return "break"
        return type(st).__name__

    def _type_to_str(self, t) -> str:
        if t is None:
            return "<?>"
        name = getattr(t, "name", None)
        if name is not None:
            return str(name)
        base = getattr(t, "base", None)
        rank = getattr(t, "rank", None)
        if base is not None and rank is not None:
            return f"{self._type_to_str(base)}({rank})"
        return str(t)

    def _expr_to_str(self, e: Expr) -> str:
        if isinstance(e, Place):
            return str(e.name)
        if isinstance(e, Literal):
            v = getattr(e, "value", None)
            if v is None:
                v = getattr(e, "text", None)
            if v is None:
                v = getattr(e, "raw", None)
            if v is None:
                v = str(e)
            return str(v)
        if isinstance(e, Unary):
            return f"({e.op}{self._expr_to_str(e.rhs)})"
        if isinstance(e, Binary):
            return f"({self._expr_to_str(e.lhs)} {e.op} {self._expr_to_str(e.rhs)})"
        if isinstance(e, Assign):
            return f"({self._expr_to_str(e.lhs)} = {self._expr_to_str(e.rhs)})"
        if isinstance(e, CallOrIndexer):
            callee = self._expr_to_str(e.callee)
            args = ", ".join(self._expr_to_str(a) for a in (e.args or []))
            return f"{callee}({args})"
        return type(e).__name__

    def _collect_calls(self, cfg: CFG, e: Optional[Expr]) -> None:
        if e is None:
            return
        if isinstance(e, CallOrIndexer):
            if isinstance(e.callee, Place):
                cfg.calls.add(str(e.callee.name))
            self._collect_calls(cfg, e.callee)
            for a in (e.args or []):
                self._collect_calls(cfg, a)
            return
        if isinstance(e, Unary):
            self._collect_calls(cfg, e.rhs)
            return
        if isinstance(e, Binary):
            self._collect_calls(cfg, e.lhs)
            self._collect_calls(cfg, e.rhs)
            return
        if isinstance(e, Assign):
            self._collect_calls(cfg, e.lhs)
            self._collect_calls(cfg, e.rhs)
            return
