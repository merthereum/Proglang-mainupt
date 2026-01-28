# src/task3/emit_asm_2addr.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AsmProgram:
    lines: List[str]

    def add(self, s: str = "") -> None:
        self.lines.append(s)

    def label(self, name: str) -> None:
        self.lines.append(f"{name}:")

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")


def emit_prolog(p: AsmProgram) -> None:
    # ZORUNLU: toolchain VM code bank'ten başlıyor -> section şart
    p.add("[section code, code]")
    p.add("ldsp 0xFFFC      ; stack top (optional)")
    p.add("setbp            ; establish base pointer")
    p.add("call main")
    p.add("hlt")
    p.add("")


def emit_epilog(p: AsmProgram) -> None:
    p.add("")
    p.add("; ---- end ----")
