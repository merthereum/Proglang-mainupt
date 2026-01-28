from __future__ import annotations
from pathlib import Path
import inspect
import re

DOT_DIR = Path("out3/graph")
OUT_ASM = Path("out3/calls_demo_fib_full.asm")

def call_generate_from_dot_dir():
    from task3.codegen_2addr import generate_from_task2_dot_dir
    # En sağlam çağrı: positional (isimler sürüme göre değişebiliyor)
    generate_from_task2_dot_dir(DOT_DIR, OUT_ASM)

def patch_missing_b1_labels(text: str) -> str:
    """
    Assembler hatandaki gibi 'fib_b1' vb. label'lar referanslanıp tanımlı olmayabiliyor.
    Bu patch, her fonksiyon bloğunda 'ret' satırından hemen önce eksik *_b1: etiketini ekler.
    """
    lines = text.splitlines()
    # Fonksiyon başlangıçlarını bul: "<name>:"
    func_starts = []
    for i, ln in enumerate(lines):
        if re.match(r"^[A-Za-z_]\w*:$", ln.strip()):
            func_starts.append((ln.strip()[:-1], i))
    func_starts.append(("_EOF_", len(lines)))

    defined = set()
    for ln in lines:
        m = re.match(r"^([A-Za-z_]\w*):$", ln.strip())
        if m:
            defined.add(m.group(1))

    out = lines[:]
    delta = 0

    for idx in range(len(func_starts) - 1):
        fname, s0 = func_starts[idx]
        _, s1 = func_starts[idx + 1]
        s0 += delta
        s1 += delta
        block = out[s0:s1]

        # Bu fonksiyon içinde *_b1 referansı var mı?
        refs = set(re.findall(r"\b" + re.escape(fname) + r"_b1\b", "\n".join(block)))
        if not refs:
            continue

        b1 = f"{fname}_b1"
        if b1 in defined:
            continue

        # bu fonksiyon bloğunda son 'ret' satırını bul
        ret_pos = None
        for j in range(s1 - 1, s0, -1):
            if out[j].strip() == "ret":
                ret_pos = j
                break

        if ret_pos is None:
            continue

        # ret'ten önce label ekle
        out.insert(ret_pos, f"{b1}:")
        defined.add(b1)
        delta += 1

    return "\n".join(out) + "\n"

def main():
    if not DOT_DIR.exists():
        raise SystemExit(f"DOT dir not found: {DOT_DIR.resolve()}")

    # DOT'lardan ASM üret
    call_generate_from_dot_dir()

    if not OUT_ASM.exists():
        raise SystemExit("Full ASM was not generated (calls_demo_fib_full.asm missing).")

    # *_b1 eksik label patch
    txt = OUT_ASM.read_text(encoding="utf-8", errors="replace")
    patched = patch_missing_b1_labels(txt)
    OUT_ASM.write_text(patched, encoding="utf-8", newline="\n")

    print("OK:", OUT_ASM.resolve())

if __name__ == "__main__":
    main()
