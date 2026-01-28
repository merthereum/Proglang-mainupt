# src/task3/dot_to_asm_2addr.py
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .dot_reader import DotCFG, parse_dot, find_node_by_label
from .emit_asm_2addr import AsmProgram, emit_prolog, emit_epilog

WORD = 4


# -------------------------
# Simple memory layout
# -------------------------
@dataclass
class MemLayout:
    addr: Dict[str, int]
    tmp0: int
    tmp1: int
    tmp2: int
    x_out: int  # which var we print at EXIT


def _alloc_layout(var_names: List[str]) -> MemLayout:
    # deterministic order
    uniq: List[str] = []
    for v in var_names:
        if v not in uniq:
            uniq.append(v)

    base = 0x0000
    addr: Dict[str, int] = {}
    cur = base

    for v in uniq:
        addr[v] = cur
        cur += WORD

    # temps after vars
    tmp0 = cur
    cur += WORD
    tmp1 = cur
    cur += WORD
    tmp2 = cur
    cur += WORD

    # choose x if exists else first var
    x_out = addr.get("x", addr[uniq[0]] if uniq else 0x0000)
    return MemLayout(addr=addr, tmp0=tmp0, tmp1=tmp1, tmp2=tmp2, x_out=x_out)


# -------------------------
# Parsing small expressions
# -------------------------
_IDENT_RE = re.compile(r"[A-Za-z_]\w*")
_INT_RE = re.compile(r"^-?\d+$")


def _strip_parens(s: str) -> str:
    s = s.strip()
    while s.startswith("(") and s.endswith(")"):
        inner = s[1:-1].strip()
        if inner.count("(") == inner.count(")"):
            s = inner
        else:
            break
    return s


def _extract_idents(s: str) -> List[str]:
    kws = {
        "if", "then", "else", "end", "while", "wend", "do", "loop", "until",
        "join", "ENTRY", "EXIT", "after_while", "after_do", "break",
        "as", "int", "uint", "long", "ulong", "byte", "bool", "char", "string",
        "dim", "function", "return",
        "True", "False",
    }
    out: List[str] = []
    for m in _IDENT_RE.finditer(s):
        t = m.group(0)
        if t in kws:
            continue
        out.append(t)
    return out


def _parse_dim_label(label: str) -> List[str]:
    # example: "dim x, y as int"
    label = label.strip()
    if not label.startswith("dim "):
        return []
    body = label[4:]
    if " as " in body:
        body = body.split(" as ", 1)[0]
    parts = [p.strip() for p in body.split(",")]
    return [p for p in parts if p]


def _parse_assign_label(label: str) -> Optional[Tuple[str, str]]:
    # examples:
    # "(x = (a + b));"
    # "(y = (y - 1));"
    s = label.strip()
    if not s.startswith("("):
        return None
    s = s.strip(";")
    s = _strip_parens(s)
    if "=" not in s:
        return None
    left, right = s.split("=", 1)
    left = _strip_parens(left).strip()
    right = _strip_parens(right).strip()
    return left, right


def _parse_cond_label(label: str) -> Optional[Tuple[str, str, str]]:
    # "if (x > 0)"
    # "while (y > 0)"
    # "do_while (x > 10)"
    s = label.strip()
    if s.startswith("if "):
        inside = s[len("if "):].strip()
    elif s.startswith("while "):
        inside = s[len("while "):].strip()
    elif s.startswith("do_while "):
        inside = s[len("do_while "):].strip()
    else:
        return None

    inside = _strip_parens(inside)

    for op in ["==", "!=", ">=", "<=", ">", "<"]:
        if op in inside:
            a, b = inside.split(op, 1)
            return a.strip(), op, b.strip()
    return None


# -------------------------
# 2-addr asm emitters
# -------------------------
def _imm16(x: int) -> int:
    return x & 0xFFFF


def emit_setm(p: AsmProgram, dst: int, value: int) -> None:
    p.add(f"setm 0x{_imm16(dst):04x} 0x{value & 0xFFFFFFFF:08x}")


def emit_movm(p: AsmProgram, dst: int, src: int) -> None:
    p.add(f"movm 0x{_imm16(dst):04x} 0x{_imm16(src):04x}")


def emit_addm(p: AsmProgram, dst: int, src: int) -> None:
    p.add(f"addm 0x{_imm16(dst):04x} 0x{_imm16(src):04x}")


def emit_subm(p: AsmProgram, dst: int, src: int) -> None:
    p.add(f"subm 0x{_imm16(dst):04x} 0x{_imm16(src):04x}")


def emit_mulm(p: AsmProgram, dst: int, src: int) -> None:
    p.add(f"mulm 0x{_imm16(dst):04x} 0x{_imm16(src):04x}")


def emit_outm(p: AsmProgram, src: int) -> None:
    p.add(f"outm 0x{_imm16(src):04x}")


def emit_inm(p: AsmProgram, dst: int) -> None:
    # read one byte from stdin into memory[dst]
    p.add(f"inm 0x{_imm16(dst):04x}")


def emit_cmpm(p: AsmProgram, a: int, b: int) -> None:
    p.add(f"cmpm 0x{_imm16(a):04x} 0x{_imm16(b):04x}")


def emit_jmp(p: AsmProgram, lab: str) -> None:
    p.add(f"jmp {lab}")


def emit_jzf(p: AsmProgram, lab: str) -> None:
    p.add(f"jzf {lab}")


def emit_jgf(p: AsmProgram, lab: str) -> None:
    p.add(f"jgf {lab}")


def emit_jlf(p: AsmProgram, lab: str) -> None:
    p.add(f"jlf {lab}")


# -------------------------
# Linearization helpers
# -------------------------
def _label(nid: int) -> str:
    return f"L_n{nid}"


def _reachable(cfg: DotCFG, entry: int) -> List[int]:
    seen: Set[int] = set()
    order: List[int] = []

    def dfs(u: int) -> None:
        if u in seen:
            return
        seen.add(u)
        order.append(u)
        for v, _ in cfg.succs(u):
            dfs(v)

    dfs(entry)
    return order


def _choose_vars_from_cfg(cfg: DotCFG) -> List[str]:
    vars_: Set[str] = set()

    for lab in cfg.nodes.values():
        for v in _parse_dim_label(lab):
            vars_.add(v)

    for lab in cfg.nodes.values():
        for t in _extract_idents(lab):
            vars_.add(t)

    for bad in ["ENTRY", "EXIT", "after_while", "after_do", "join"]:
        vars_.discard(bad)

    preferred: List[str] = []
    for v in ["a", "b", "x", "y", "yv", "i"]:
        if v in vars_:
            preferred.append(v)
            vars_.remove(v)

    rest = sorted(vars_)
    return preferred + rest


def _is_int(s: str) -> bool:
    return bool(_INT_RE.match(s.strip()))


def _val_to_addr(p: AsmProgram, mem: MemLayout, token: str, scratch: int) -> int:
    token = token.strip()
    if _is_int(token):
        emit_setm(p, scratch, int(token))
        return scratch

    if token not in mem.addr:
        # allocate on the fly
        mem.addr[token] = scratch
        emit_setm(p, scratch, 0)
    return mem.addr[token]


def _emit_expr_to_dst(p: AsmProgram, mem: MemLayout, dst_var: str, expr: str) -> None:
    dst = mem.addr[dst_var]
    expr = _strip_parens(expr)

    for op in ["+", "-", "*"]:
        if op in expr:
            a, b = expr.split(op, 1)
            a = a.strip()
            b = b.strip()

            if _is_int(a):
                emit_setm(p, dst, int(a))
            else:
                emit_movm(p, dst, mem.addr[a])

            src_addr = _val_to_addr(p, mem, b, mem.tmp0)
            if op == "+":
                emit_addm(p, dst, src_addr)
            elif op == "-":
                emit_subm(p, dst, src_addr)
            else:
                emit_mulm(p, dst, src_addr)
            return

    if _is_int(expr):
        emit_setm(p, dst, int(expr))
    else:
        emit_movm(p, dst, mem.addr[expr])


def _emit_cond_branch(
    p: AsmProgram,
    mem: MemLayout,
    a: str,
    op: str,
    b: str,
    true_lab: str,
    false_lab: str,
) -> None:
    a_addr = _val_to_addr(p, mem, a, mem.tmp1)
    b_addr = _val_to_addr(p, mem, b, mem.tmp2)
    emit_cmpm(p, a_addr, b_addr)

    if op == ">":
        emit_jgf(p, true_lab)
        emit_jmp(p, false_lab)
    elif op == "<":
        emit_jlf(p, true_lab)
        emit_jmp(p, false_lab)
    elif op == "==":
        emit_jzf(p, true_lab)
        emit_jmp(p, false_lab)
    elif op == "!=":
        emit_jzf(p, false_lab)
        emit_jmp(p, true_lab)
    elif op == ">=":
        emit_jgf(p, true_lab)
        emit_jzf(p, true_lab)
        emit_jmp(p, false_lab)
    elif op == "<=":
        emit_jlf(p, true_lab)
        emit_jzf(p, true_lab)
        emit_jmp(p, false_lab)
    else:
        emit_jmp(p, false_lab)


# -------------------------
# Main entry: DOT -> ASM
# -------------------------
def generate_from_dot(dot_path: str | Path, asm_path: str | Path) -> None:
    cfg = parse_dot(dot_path)

    entry = find_node_by_label(cfg, "ENTRY")
    exitn = find_node_by_label(cfg, "EXIT")
    if entry is None or exitn is None:
        raise RuntimeError("DOT must contain ENTRY and EXIT nodes")

    vars_ = _choose_vars_from_cfg(cfg)
    mem = _alloc_layout(vars_ if vars_ else ["x"])

    reachable = _reachable(cfg, entry)

    p = AsmProgram(lines=[])
    emit_prolog(p)
    p.label("main")

    # ---- IMPORTANT: read inputs FIRST (calculator behavior) ----
    # If program has variables a and b, read 2 bytes into them.
    if "a" in mem.addr:
        emit_inm(p, mem.addr["a"])
    if "b" in mem.addr:
        emit_inm(p, mem.addr["b"])

    # ---- init variables to 0, BUT do NOT overwrite a/b if we read them ----
    for v, a_addr in mem.addr.items():
        if v in ("a", "b"):
            continue
        emit_setm(p, a_addr, 0)

    for nid in reachable:
        lab = cfg.nodes.get(nid, "")
        p.label(_label(nid))

        # EXIT block
        if nid == exitn:
            emit_outm(p, mem.x_out)
            p.add("ret")
            continue

        # ENTRY block
        if lab.strip() == "ENTRY":
            succs = cfg.succs(nid)
            if succs:
                emit_jmp(p, _label(succs[0][0]))
            continue

        # break block
        if lab.strip() == "break":
            succs = cfg.succs(nid)
            if succs:
                emit_jmp(p, _label(succs[0][0]))
            continue

        # join / after_* : jump to next
        if lab.strip() in {"join", "after_while", "after_do"}:
            succs = cfg.succs(nid)
            if succs:
                emit_jmp(p, _label(succs[0][0]))
            continue

        # condition node?
        cond = _parse_cond_label(lab)
        if cond is not None:
            a, op, b = cond
            succs = cfg.succs(nid)

            t_dst = None
            f_dst = None
            for dst, elab in succs:
                if elab == "True":
                    t_dst = dst
                elif elab == "False":
                    f_dst = dst

            if t_dst is None and len(succs) >= 1:
                t_dst = succs[0][0]
            if f_dst is None and len(succs) >= 2:
                f_dst = succs[1][0]

            if t_dst is None or f_dst is None:
                if succs:
                    emit_jmp(p, _label(succs[0][0]))
                continue

            # heuristic for "if" weird CFG (keep yours)
            if lab.strip().startswith("if "):
                join_dst = f_dst
                then_dst = t_dst
                then_succs = cfg.succs(then_dst)
                if len(then_succs) == 1:
                    mid = then_succs[0][0]
                    mid_succs = cfg.succs(mid)
                    if any(s == join_dst for s, _ in mid_succs):
                        _emit_cond_branch(p, mem, a, op, b, _label(then_dst), _label(mid))
                        continue

            _emit_cond_branch(p, mem, a, op, b, _label(t_dst), _label(f_dst))
            continue

        # assignment node?
        ass = _parse_assign_label(lab)
        if ass is not None:
            left, right = ass
            if left not in mem.addr:
                mem.addr[left] = mem.tmp0
                emit_setm(p, mem.addr[left], 0)

            _emit_expr_to_dst(p, mem, left, right)

            succs = cfg.succs(nid)
            if succs:
                emit_jmp(p, _label(succs[0][0]))
            continue

        # default: just jump to next succ
        succs = cfg.succs(nid)
        if succs:
            emit_jmp(p, _label(succs[0][0]))

    emit_epilog(p)
    Path(asm_path).parent.mkdir(parents=True, exist_ok=True)
    p.save(str(asm_path))
