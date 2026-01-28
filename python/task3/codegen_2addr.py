# src/task3/codegen_2addr.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
import re
from pathlib import Path

from task3.emit_asm_2addr import AsmProgram, emit_prolog, emit_epilog

WORD = 4

@dataclass
class DotCFGBlock:
    id: int
    label: str
    succs: List[Tuple[int, Optional[str]]]  # (to_id, edge_label)

@dataclass
class DotCFG:
    name: str
    blocks: Dict[int, DotCFGBlock]
    entry: int
    exit: int

# ----------------- helpers -----------------

def imm16(x: int) -> int:
    return x & 0xFFFF

def emit_setm(p: AsmProgram, dst: int, value: int) -> None:
    p.add(f"setm 0x{imm16(dst):04x} 0x{value & 0xFFFFFFFF:08x}")

def emit_movm(p: AsmProgram, dst: int, src: int) -> None:
    p.add(f"movm 0x{imm16(dst):04x} 0x{imm16(src):04x}")

def emit_addm(p: AsmProgram, dst: int, src: int) -> None:
    p.add(f"addm 0x{imm16(dst):04x} 0x{imm16(src):04x}")

def emit_subm(p: AsmProgram, dst: int, src: int) -> None:
    p.add(f"subm 0x{imm16(dst):04x} 0x{imm16(src):04x}")

def emit_mulm(p: AsmProgram, dst: int, src: int) -> None:
    p.add(f"mulm 0x{imm16(dst):04x} 0x{imm16(src):04x}")

def emit_outm(p: AsmProgram, src: int) -> None:
    p.add(f"outm 0x{imm16(src):04x}")

def emit_cmpm(p: AsmProgram, a: int, b: int) -> None:
    p.add(f"cmpm 0x{imm16(a):04x} 0x{imm16(b):04x}")

def emit_jmp(p: AsmProgram, label: str) -> None:
    p.add(f"jmp {label}")

def emit_jzf(p: AsmProgram, label: str) -> None:
    p.add(f"jzf {label}")

def emit_jgf(p: AsmProgram, label: str) -> None:
    p.add(f"jgf {label}")

def emit_jlf(p: AsmProgram, label: str) -> None:
    p.add(f"jlf {label}")

# ----------------- DOT parsing -----------------

_NODE_RE = re.compile(r'^\s*(n(\d+))\s+\[label="(.*)"\];\s*$')
_EDGE_RE = re.compile(r'^\s*n(\d+)\s*->\s*n(\d+)(?:\s*\[label="(.*)"\])?;\s*$')

def _unescape_dot_label(s: str) -> str:
    # DOT label may contain escaped sequences like \n
    return s.replace(r"\n", "\n").replace('\\"', '"')

def parse_dot_cfg(dot_path: Path) -> DotCFG:
    text = dot_path.read_text(encoding="utf-8", errors="replace").splitlines()

    name = dot_path.stem
    blocks: Dict[int, DotCFGBlock] = {}
    edges: List[Tuple[int,int,Optional[str]]] = []

    for line in text:
        m = _NODE_RE.match(line)
        if m:
            nid = int(m.group(2))
            label = _unescape_dot_label(m.group(3))
            blocks[nid] = DotCFGBlock(id=nid, label=label, succs=[])
            continue
        m = _EDGE_RE.match(line)
        if m:
            a = int(m.group(1))
            b = int(m.group(2))
            lab = m.group(3)
            edges.append((a,b,lab))
            continue

    for a,b,lab in edges:
        if a in blocks:
            blocks[a].succs.append((b, lab))

    # detect entry/exit by label
    entry = -1
    exit_ = -1
    for bid, blk in blocks.items():
        if blk.label.strip() == "ENTRY":
            entry = bid
        if blk.label.strip() == "EXIT":
            exit_ = bid

    if entry == -1:
        # fallback: smallest id
        entry = min(blocks.keys()) if blocks else 0
    if exit_ == -1:
        # fallback: last id
        exit_ = max(blocks.keys()) if blocks else entry

    return DotCFG(name=name, blocks=blocks, entry=entry, exit=exit_)

# ----------------- variable discovery -----------------

_IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")

KEYWORDS = {
    "ENTRY","EXIT","dim","as","if","then","else","end","while","wend","do","loop","break","join",
    "true","false","function"
}

def collect_vars_from_cfg(cfg: DotCFG) -> List[str]:
    vars_: set[str] = set()
    for blk in cfg.blocks.values():
        t = blk.label
        # var decl: dim x, y as int
        if t.startswith("dim "):
            mid = t[4:]
            if " as " in mid:
                names = mid.split(" as ")[0]
                for n in names.split(","):
                    n = n.strip()
                    if n:
                        vars_.add(n)
            continue

        # assignments: (x = ...)
        if "=" in t and "==" not in t:
            # rough split
            left = t.split("=", 1)[0]
            left = left.replace("(", "").replace(")", "").replace(";", "").strip()
            if left and left not in KEYWORDS:
                vars_.add(left)

        # other identifiers in expressions
        for tok in _IDENT.findall(t):
            if tok not in KEYWORDS and not tok.isdigit():
                # filter type names like int/uint etc
                if tok in {"bool","byte","int","uint","long","ulong","char","string"}:
                    continue
                vars_.add(tok)

    # stable order
    return sorted(vars_)

def build_addr_map(vars_: List[str], base: int) -> Dict[str,int]:
    m: Dict[str,int] = {}
    cur = base
    for v in vars_:
        m[v] = cur
        cur += WORD
    return m

# ----------------- expression compilation (limited but works for your constructs) -----------------

def strip_stmt(s: str) -> str:
    return s.strip().rstrip(";").strip()

def parse_if_cond(label: str) -> Optional[Tuple[str,str,str]]:
    # supports: if (x > 0)  / while (y > 0)
    m = re.search(r"\((.*)\)", label)
    if not m:
        return None
    expr = m.group(1).strip()
    # operators priority: >= <= == != > <
    for op in [">=", "<=", "==", "!=", ">", "<"]:
        if op in expr:
            a,b = [x.strip() for x in expr.split(op, 1)]
            return (a, op, b)
    return None

def is_int_literal(x: str) -> bool:
    return re.fullmatch(r"-?\d+", x) is not None

def eval_to_tmp(p: AsmProgram, x: str, env: Dict[str,int], tmp: int) -> None:
    x = x.strip()
    if is_int_literal(x):
        emit_setm(p, tmp, int(x))
        return
    # variable
    if x in env:
        emit_movm(p, tmp, env[x])
        return
    # fallback: unknown -> 0
    emit_setm(p, tmp, 0)

def compile_assign_stmt(p: AsmProgram, label: str, env: Dict[str,int], tmp0: int, tmp1: int) -> None:
    s = strip_stmt(label)
    s = s.replace("(", "").replace(")", "")
    if "=" not in s:
        return
    lhs, rhs = [x.strip() for x in s.split("=", 1)]
    if lhs not in env:
        return

    # binary?
    for op in ["+", "-", "*"]:
        if op in rhs:
            a,b = [x.strip() for x in rhs.split(op, 1)]
            eval_to_tmp(p, a, env, tmp0)
            eval_to_tmp(p, b, env, tmp1)
            if op == "+":
                emit_addm(p, tmp0, tmp1)
            elif op == "-":
                emit_subm(p, tmp0, tmp1)
            else:
                emit_mulm(p, tmp0, tmp1)
            emit_movm(p, env[lhs], tmp0)
            return

    # simple var or literal
    eval_to_tmp(p, rhs, env, tmp0)
    emit_movm(p, env[lhs], tmp0)

# ----------------- CFG traversal + codegen -----------------

def block_label_name(func: str, bid: int) -> str:
    return f"{func}_b{bid}"

def dfs_order(cfg: DotCFG) -> List[int]:
    seen = set()
    order: List[int] = []

    def go(u: int):
        if u in seen:
            return
        seen.add(u)
        order.append(u)
        for v,_lab in cfg.blocks[u].succs:
            go(v)

    go(cfg.entry)
    # include any disconnected blocks
    for bid in sorted(cfg.blocks.keys()):
        if bid not in seen:
            go(bid)
    return order

def emit_condition_and_branches(
    p: AsmProgram,
    cond: Tuple[str,str,str],
    succ_true: str,
    succ_false: str,
    env: Dict[str,int],
    tmp0: int,
    tmp1: int,
) -> None:
    a,op,b = cond
    eval_to_tmp(p, a, env, tmp0)
    eval_to_tmp(p, b, env, tmp1)
    emit_cmpm(p, tmp0, tmp1)

    if op == ">":
        emit_jgf(p, succ_true)
        emit_jmp(p, succ_false)
    elif op == "<":
        emit_jlf(p, succ_true)
        emit_jmp(p, succ_false)
    elif op == "==":
        emit_jzf(p, succ_true)
        emit_jmp(p, succ_false)
    elif op == "!=":
        # if equal -> false, else -> true
        emit_jzf(p, succ_false)
        emit_jmp(p, succ_true)
    elif op == ">=":
        emit_jgf(p, succ_true)
        emit_jzf(p, succ_true)
        emit_jmp(p, succ_false)
    elif op == "<=":
        emit_jlf(p, succ_true)
        emit_jzf(p, succ_true)
        emit_jmp(p, succ_false)
    else:
        # unknown -> always false
        emit_jmp(p, succ_false)

def codegen_one_cfg(p: AsmProgram, cfg: DotCFG, func_index: int) -> None:
    func = cfg.name

    # per-function memory base
    base = 0x0000 + func_index * 0x0100
    tmp_base = 0x0800 + func_index * 0x0100
    tmp0 = tmp_base + 0*WORD
    tmp1 = tmp_base + 1*WORD

    vars_ = collect_vars_from_cfg(cfg)
    env = build_addr_map(vars_, base)

    # function label
    p.label(func)

    order = dfs_order(cfg)

    for bid in order:
        blk = cfg.blocks[bid]
        lab = blk.label.strip()

        # give each block a label (except ENTRY/EXIT)
        if lab not in {"ENTRY", "EXIT"}:
            p.label(block_label_name(func, bid))

        # EXIT => ret
        if bid == cfg.exit or lab == "EXIT":
            p.add("ret")
            continue

        # ENTRY => jump to first successor if exists
        if lab == "ENTRY":
            if blk.succs:
                emit_jmp(p, block_label_name(func, blk.succs[0][0]))
            continue

        # VarDecl: nothing (addresses already allocated)
        if lab.startswith("dim "):
            # no code needed for declaration
            pass

        # Assign:
        elif "=" in lab and "==" not in lab and "!=" not in lab:
            compile_assign_stmt(p, lab, env, tmp0, tmp1)

        # If/While/Do condition blocks:
        elif lab.startswith("if ") or lab.startswith("while ") or lab.startswith("do"):
            cond = parse_if_cond(lab)
            if cond and len(blk.succs) >= 2:
                # find true/false edges (labels may be "True"/"False")
                tdst = blk.succs[0][0]
                fdst = blk.succs[1][0]
                for dst, elab in blk.succs:
                    if elab == "True":
                        tdst = dst
                    if elab == "False":
                        fdst = dst
                emit_condition_and_branches(
                    p,
                    cond,
                    succ_true=block_label_name(func, tdst),
                    succ_false=block_label_name(func, fdst),
                    env=env,
                    tmp0=tmp0,
                    tmp1=tmp1
                )
                continue

        # Break block: just jump to its only successor (task2 already built edge)
        elif lab == "break":
            if blk.succs:
                emit_jmp(p, block_label_name(func, blk.succs[0][0]))
                continue

        # Default: if only 1 succ -> jmp
        if len(blk.succs) == 1:
            emit_jmp(p, block_label_name(func, blk.succs[0][0]))

        # if 2 succ but not recognized condition -> just jmp first
        elif len(blk.succs) >= 2:
            emit_jmp(p, block_label_name(func, blk.succs[0][0]))

    # if function falls through (safety)
    p.add("ret")


def generate_from_task2_dot_dir(dot_dir: str, output_path: str) -> None:
    dot_path = Path(dot_dir)
    dots = sorted(dot_path.glob("*.dot"))
    if not dots:
        raise RuntimeError(f"No .dot files found in: {dot_path}")

    cfgs: List[DotCFG] = [parse_dot_cfg(p) for p in dots]

    prog = AsmProgram(lines=[])
    emit_prolog(prog)

    # runtime entry expects main exists
    # We generate each cfg as a subprogram
    for idx, cfg in enumerate(cfgs):
        codegen_one_cfg(prog, cfg, func_index=idx)

    emit_epilog(prog)
    prog.save(output_path)

# ----------------- DEMO (kept) -----------------

def generate_demo_only(output_path: str) -> None:
    """
    Sabit 2+4=6 demo (pipeline testi)
    """
    p = AsmProgram(lines=[])
    emit_prolog(p)

    p.label("main")
    a = 0x0000
    b = 0x0004
    x = 0x0008

    emit_setm(p, a, 2)
    emit_setm(p, b, 4)
    emit_movm(p, x, a)
    emit_addm(p, x, b)
    emit_outm(p, x)
    p.add("ret")

    emit_epilog(p)
    p.save(output_path)
