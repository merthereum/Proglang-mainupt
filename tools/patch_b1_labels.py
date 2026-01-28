# tools/patch_b1_labels.py
import re
import sys
from pathlib import Path

def main():
    if len(sys.argv) != 3:
        print("Usage: python tools/patch_b1_labels.py <in.asm> <out.asm>")
        sys.exit(2)

    inp = Path(sys.argv[1])
    outp = Path(sys.argv[2])

    text = inp.read_text(encoding="utf-8")
    lines = text.splitlines(True)

    # Find all *_b1 references
    refs = set(re.findall(r"\b([A-Za-z_]\w*)_b1\b", text))
    # Find already defined labels
    defined = set(re.findall(r"^([A-Za-z_]\w*):\s*$", text, flags=re.M))

    missing = sorted(fn for fn in refs if f"{fn}_b1" not in defined and fn in defined)
    if not missing:
        outp.write_text(text, encoding="utf-8")
        print(f"OK: no missing _b1 labels; wrote {outp}")
        return

    def is_func_header(s: str) -> str | None:
        m = re.match(r"^([A-Za-z_]\w*):\s*$", s)
        if not m:
            return None
        name = m.group(1)
        # Function headers are plain names we referenced (fib/main/readInt/...) not basic blocks like fib_b2
        if name in refs:
            return name
        return None

    i = 0
    while i < len(lines):
        fn = is_func_header(lines[i].strip())
        if not fn or f"{fn}_b1" in defined or fn not in missing:
            i += 1
            continue

        # Find function block end: next function header (another referenced function) or EOF
        j = i + 1
        while j < len(lines):
            hdr = is_func_header(lines[j].strip())
            if hdr and hdr != fn:
                break
            j += 1

        # Find last 'ret' inside [i, j)
        ret_idx = None
        for k in range(j - 1, i, -1):
            if re.match(r"^\s*ret\s*$", lines[k]):
                ret_idx = k
                break

        insert_at = ret_idx if ret_idx is not None else j
        ins = f"{fn}_b1:\n"
        lines.insert(insert_at, ins)
        defined.add(f"{fn}_b1")
        # adjust indices after insert
        i = j + 1

    outp.write_text("".join(lines), encoding="utf-8")
    print(f"OK: patched _b1 labels; wrote {outp}")

if __name__ == "__main__":
    main()
