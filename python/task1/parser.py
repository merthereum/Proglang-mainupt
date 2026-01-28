from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
from lark import Lark, Transformer, exceptions

from .ast import *


@dataclass
class ParseResult:
    program: Optional[Program]
    errors: List[ParseError]


class AstBuilder(Transformer):
    def start(self, items):
        # start: _seps source _seps  => bazen items içinde sadece Program gelir,
        # bazen _seps nedeniyle ekstra elemanlar olabilir. Program olanı seçelim.
        for it in items:
            if isinstance(it, Program):
                return it
        # fallback
        return items[0] if items else Program(items=[])

    def source(self, items):
        # source: (source_item _seps)*  => source_item'lar FuncDef'e dönüşmeli
        return Program(items=items)

    def source_item(self, items):
        # source_item: func_def
        return items[0]

    # --- types ---
    def type_builtin(self, items):
        return BuiltinType(str(items[0]))

    def type_custom(self, items):
        return CustomType(str(items[0]))

    def array_suffix(self, items):
        # items can be [] (no commas) or [comma_list]
        if not items:
            return 1
        commas = str(items[0])
        return commas.count(",") + 1

    def base_type(self, items):
        return items[0]

    def type_ref(self, items):
        base = items[0]
        suffixes = items[1:]
        t = base
        for rank in suffixes:
            t = ArrayType(base=t, rank=int(rank))
        return t

    # --- function ---
    def arg_def(self, items):
        name = str(items[0])
        t = items[1] if len(items) > 1 else None
        return ArgDef(name=name, type_ref=t)

    def arg_list(self, items):
        return items

    def func_signature(self, items):
        name = str(items[0])
        args = items[1] if len(items) > 1 and isinstance(items[1], list) else []
        ret = None
        for it in items[1:]:
            if isinstance(it, TypeRef):
                ret = it
        return FuncSignature(name=name, args=args, return_type=ret)

    def func_def(self, items):
        sig = items[0]
        body = items[1:] if len(items) > 1 else None
        if body is not None:
            body = [x for x in body if isinstance(x, Stmt)]
        return FuncDef(signature=sig, body=body)

    # --- statements ---
    def ident_list(self, items):
        return [str(x) for x in items]

    def var_stmt(self, items):
        names = items[0]
        t = items[1]
        return VarDecl(names=names, type_ref=t)

    def break_stmt(self, items):
        return Break()

    def expr_stmt(self, items):
        return ExprStmt(expr=items[0])

    def if_stmt(self, items):
        cond = items[0]
        stmts = [x for x in items[1:] if isinstance(x, Stmt)]
        return If(cond=cond, then_body=stmts, else_body=None)

    def while_stmt(self, items):
        cond = items[0]
        body = [x for x in items[1:] if isinstance(x, Stmt)]
        return While(cond=cond, body=body)

    def do_stmt(self, items):
        """
        do_stmt: "do" _seps statement* "loop" ("while"|"until") expr _seps

        Eski yaklaşım: mode=items[-2], cond=items[-1] idi.
        Ama _seps / token sıralaması yüzünden bazen son iki eleman bunlar olmayabiliyor.
        Bu yüzden:
          - cond'u: items içindeki SON Expr instance olarak buluyoruz
          - mode'u: items içinde 'while' veya 'until' string/token olarak buluyoruz
          - body'yi: Stmt instance'larından topluyoruz
        """
        # 1) condition: son Expr'yi bul
        cond = None
        for it in reversed(items):
            if isinstance(it, Expr):
                cond = it
                break
        if cond is None:
            # çok uç durumda fallback
            cond = items[-1] if items else None

        # 2) mode: 'while' / 'until' bul
        mode = None
        for it in items:
            s = str(it).lower()
            if s in ("while", "until"):
                mode = s
                break
        if mode is None:
            mode = "while"  # default

        # 3) body: Stmt olanlar
        body = [x for x in items if isinstance(x, Stmt)]

        return DoLoop(body=body, mode=mode, cond=cond)

    # --- expressions ---
    def place(self, items):
        return Place(name=str(items[0]))

    def lit_bool(self, items): return Literal("bool", str(items[0]))
    def lit_str(self, items):  return Literal("str", str(items[0]))
    def lit_char(self, items): return Literal("char", str(items[0]))
    def lit_hex(self, items):  return Literal("hex", str(items[0]))
    def lit_bits(self, items): return Literal("bits", str(items[0]))
    def lit_dec(self, items):  return Literal("dec", str(items[0]))

    def braces(self, items):
        return items[0]

    def unary(self, items):
        op = str(items[0])
        rhs = items[1]
        return Unary(op=op, rhs=rhs)

    def bin(self, items):
        # items: lhs, OP, rhs, OP, rhs ... (left-assoc)
        expr = items[0]
        i = 1
        while i + 1 < len(items):
            op = str(items[i])
            rhs = items[i + 1]
            expr = Binary(op=op, lhs=expr, rhs=rhs)
            i += 2
        return expr

    def assign(self, items):
        # grammar: logic_or (ASSIGN_OP assign)?
        if len(items) == 1:
            return items[0]
        # items = [lhs, Token('='), rhs]
        return Assign(lhs=items[0], rhs=items[-1])

    def call_args(self, items):
        return items

    def call_or_indexer(self, items):
        base = items[0]
        rest = items[1:]
        expr = base
        for arglist in rest:
            args = arglist if isinstance(arglist, list) else []
            expr = CallOrIndexer(callee=expr, args=args)
        return expr


def make_parser() -> Lark:
    with open(__file__.replace("parser.py", "grammar_v3.lark"), "r", encoding="utf-8") as f:
        grammar = f.read()
    return Lark(grammar, start="start", parser="lalr", propagate_positions=True)


_PARSER: Optional[Lark] = None


def parse_text(text: str) -> ParseResult:
    global _PARSER
    if _PARSER is None:
        _PARSER = make_parser()
    try:
        tree = _PARSER.parse(text)
        program = AstBuilder().transform(tree)
        return ParseResult(program=program, errors=[])
    except exceptions.UnexpectedInput as e:
        return ParseResult(
            program=None,
            errors=[ParseError(message=str(e), line=e.line, column=e.column)]
        )
