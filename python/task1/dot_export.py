from __future__ import annotations
from dataclasses import is_dataclass, fields
from typing import Any, Dict, List, Tuple

def to_dot(root: Any) -> str:
    lines: List[str] = ["digraph AST {", '  node [shape=box];']
    ids: Dict[int, str] = {}
    counter = 0

    def nid(obj: Any) -> str:
        nonlocal counter
        key = id(obj)
        if key not in ids:
            ids[key] = f"n{counter}"
            counter += 1
        return ids[key]

    def label(obj: Any) -> str:
        t = type(obj).__name__
        if hasattr(obj, "name") and isinstance(getattr(obj, "name"), str):
            return f"{t}\\nname={getattr(obj,'name')}"
        if hasattr(obj, "op") and isinstance(getattr(obj, "op"), str):
            return f"{t}\\nop={getattr(obj,'op')}"
        if hasattr(obj, "kind"):
            return f"{t}\\nkind={getattr(obj,'kind')}"
        return t

    def walk(obj: Any):
        if obj is None:
            return
        this = nid(obj)
        lines.append(f'  {this} [label="{label(obj)}"];')

        # dataclass fields
        if is_dataclass(obj):
            for f in fields(obj):
                val = getattr(obj, f.name)
                if isinstance(val, list):
                    for i, item in enumerate(val):
                        if is_dataclass(item):
                            child = nid(item)
                            lines.append(f"  {this} -> {child} [label=\"{f.name}[{i}]\"];")
                            walk(item)
                else:
                    if is_dataclass(val):
                        child = nid(val)
                        lines.append(f"  {this} -> {child} [label=\"{f.name}\"];")
                        walk(val)

    walk(root)
    lines.append("}")
    return "\n".join(lines)
