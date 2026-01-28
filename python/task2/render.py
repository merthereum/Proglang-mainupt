from __future__ import annotations
from pathlib import Path
from typing import Iterable, Optional, Set, Tuple
import subprocess

from .cfg import CFG


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def cfg_to_dot(cfg: CFG) -> str:
    lines = []
    lines.append(f'digraph "{_esc(cfg.name)}" {{')
    lines.append("  node [shape=box];")

    for bid, b in cfg.blocks.items():
        lines.append(f'  n{bid} [label="{_esc(b.label)}"];')

    for bid, b in cfg.blocks.items():
        for (to, lab) in b.succs:
            if lab is None:
                lines.append(f"  n{bid} -> n{to};")
            else:
                lines.append(f'  n{bid} -> n{to} [label="{_esc(str(lab))}"];')

    lines.append("}")
    return "\n".join(lines)


def call_graph_to_dot(
    edges: Iterable[Tuple[str, str]],
    defined: Set[str],
    no_body: Set[str],
    with_errors: Set[str],
) -> str:
    lines = []
    lines.append('digraph "call_graph" {')
    lines.append("  rankdir=LR;")
    lines.append("  node [shape=box];")

    all_nodes: Set[str] = set()
    for a, b in edges:
        all_nodes.add(a); all_nodes.add(b)
# defined fonksiyonları da düğüm olarak ekle (edge olmasa bile görünsün)
        all_nodes |= set(defined)

    for n in sorted(all_nodes):
        extra = []
        if n not in defined:
            extra.append("UNDEF")
        if n in no_body:
            extra.append("NO_BODY")
        if n in with_errors:
            extra.append("ERROR")

        label = n if not extra else f"{n}\\n({', '.join(extra)})"
        lines.append(f'  "{_esc(n)}" [label="{_esc(label)}"];')

    for a, b in edges:
        lines.append(f'  "{_esc(a)}" -> "{_esc(b)}";')

    lines.append("}")
    return "\n".join(lines)


def run_dot(dot_path: Path, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fmt = out_path.suffix.lstrip(".")
    subprocess.run(["dot", f"-T{fmt}", str(dot_path), "-o", str(out_path)], check=True)
