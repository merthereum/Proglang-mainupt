from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Union

@dataclass
class SrcPos:
    line: int
    column: int

@dataclass
class ParseError:
    message: str
    line: int
    column: int

# ---- Types ----
@dataclass
class TypeRef: pass

@dataclass
class BuiltinType(TypeRef):
    name: str

@dataclass
class CustomType(TypeRef):
    name: str

@dataclass
class ArrayType(TypeRef):
    base: TypeRef
    rank: int  # 1 for (), 2 for (,), etc.

# ---- Program ----
@dataclass
class Program:
    items: List["FuncDef"]

@dataclass
class ArgDef:
    name: str
    type_ref: Optional[TypeRef]

@dataclass
class FuncSignature:
    name: str
    args: List[ArgDef]
    return_type: Optional[TypeRef]

@dataclass
class FuncDef:
    signature: FuncSignature
    body: Optional[List["Stmt"]]  # None = only declaration

# ---- Statements ----
class Stmt: pass

@dataclass
class VarDecl(Stmt):
    names: List[str]
    type_ref: TypeRef

@dataclass
class Break(Stmt): pass

@dataclass
class If(Stmt):
    cond: "Expr"
    then_body: List[Stmt]
    else_body: Optional[List[Stmt]]

@dataclass
class While(Stmt):
    cond: "Expr"
    body: List[Stmt]

@dataclass
class DoLoop(Stmt):
    body: List[Stmt]
    mode: str  # "while"|"until"
    cond: "Expr"

@dataclass
class ExprStmt(Stmt):
    expr: "Expr"

# ---- Expressions ----
class Expr: pass

@dataclass
class Place(Expr):
    name: str

@dataclass
class Literal(Expr):
    kind: str
    value: str

@dataclass
class Unary(Expr):
    op: str
    rhs: Expr

@dataclass
class Binary(Expr):
    op: str
    lhs: Expr
    rhs: Expr

@dataclass
class Assign(Expr):
    lhs: Expr
    rhs: Expr

@dataclass
class CallOrIndexer(Expr):
    callee: Expr
    args: List[Expr]
