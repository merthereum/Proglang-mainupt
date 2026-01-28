# tools/remove_inout_defs.py
import re
import sys
from pathlib import Path

def main():
    if len(sys.argv) != 3:
        print("Usage: python tools/remove_inout_defs.py <in.asm> <out.asm>")
        sys.exit(2)

    inp = Path(sys.argv[1])
    outp = Path(sys.argv[2])

    lines = inp.read_text(encoding="utf-8").splitlines(True)

    def is_top_label(line: str):
        # top-level labels like "fib:" or "main:" or "readInt:"
        return re.match(r"^[A-Za-z_]\w*:\s*$", line.strip()) is not None

    def label_name(line: str):
        m = re.match(r"^([A-Za-z_]\w*):\s*$", line.strip())
        return m.group(1) if m else None

    out = []
    i = 0
    while i < len(lines):
        if is_top_label(lines[i]):
            name = label_name(lines[i])
            if name in ("in", "out"):
                # skip everything until next top-level label that is not a basic block label
                i += 1
                while i < len(lines):
                    if is_top_label(lines[i]):
                        # next function label found
                        break
                    i += 1
                continue
        out.append(lines[i])
        i += 1

    outp.write_text("".join(out), encoding="utf-8")
    print(f"OK: removed in/out defs; wrote {outp}")

if __name__ == "__main__":
    main()
