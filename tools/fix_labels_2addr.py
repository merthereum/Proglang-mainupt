from __future__ import annotations
from pathlib import Path
import re

# X_b123  ->  X__b123  (assembler ile kavga etmeyen güvenli isim)
LBL_DEF = re.compile(r'^([A-Za-z_]\w*)_b(\d+):\s*$')
LBL_REF = re.compile(r'\b([A-Za-z_]\w*)_b(\d+)\b')

def fix_text(s: str) -> str:
    out_lines = []
    for line in s.splitlines():
        m = LBL_DEF.match(line.strip())
        if m:
            name, num = m.group(1), m.group(2)
            out_lines.append(f"{name}__b{num}:")
            continue
        # references (jmp/call/jxx operands) and any other occurrences
        out_lines.append(LBL_REF.sub(r"\1__b\2", line))
    return "\n".join(out_lines) + "\n"

def main():
    inp = Path(r"out3/calls_demo_fib_full_merged.asm")
    out = Path(r"out3/calls_demo_fib_full_merged_fixed.asm")

    if not inp.exists():
        raise SystemExit(f"INPUT NOT FOUND: {inp.resolve()}")

    s = inp.read_text(encoding="utf-8", errors="replace")
    fixed = fix_text(s)
    out.write_text(fixed, encoding="utf-8", newline="\n")

    # hızlı kontrol: hala _b geçen var mı?
    if re.search(r'\b[A-Za-z_]\w*_b\d+\b', fixed):
        print("WARN: still has _bN patterns (check manually).")
    else:
        print("OK: all _bN normalized -> __bN")

    print("WROTE:", out.resolve())

if __name__ == "__main__":
    main()
