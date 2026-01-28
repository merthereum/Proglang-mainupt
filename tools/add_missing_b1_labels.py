from __future__ import annotations
from pathlib import Path
import re

ASM_IN  = Path(r"out3/calls_demo_fib_full_merged_fixed.asm")
ASM_OUT = Path(r"out3/calls_demo_fib_full_FINAL.asm")

# function header:  fib:
FUNC_HDR = re.compile(r"^([A-Za-z_]\w*):\s*$")
# any label: fib__b23:
ANY_LBL  = re.compile(r"^([A-Za-z_]\w*):\s*$")
# reference: jmp fib__b1 / call fib__b1 / jzf fib__b1 ...
REF_B1   = re.compile(r"\b([A-Za-z_]\w*)__b1\b")

def main():
    if not ASM_IN.exists():
        raise SystemExit(f"INPUT NOT FOUND: {ASM_IN.resolve()}")

    lines = ASM_IN.read_text(encoding="utf-8", errors="replace").splitlines()

    # 1) Hangi __b1 target'ları referans ediliyor?
    needed = set()
    for ln in lines:
        for m in REF_B1.finditer(ln):
            needed.add(m.group(1))          # e.g. "fib", "main", "readInt"

    if not needed:
        print("No __b1 references found. Nothing to fix.")
        ASM_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print("WROTE:", ASM_OUT.resolve())
        return

    # 2) Hangi __b1 label'ları zaten tanımlı?
    defined_b1 = set()
    for ln in lines:
        s = ln.strip()
        if s.endswith(":") and "__b1:" in s:
            defined_b1.add(s.replace(":", ""))  # "fib__b1"

    missing = []
    for fn in sorted(needed):
        if f"{fn}__b1" not in defined_b1:
            missing.append(fn)

    print("Functions with missing __b1 labels:", missing)

    # 3) Her fonksiyonun sonuna (ret'ten önce) __b1 stub ekleyeceğiz.
    # Mantık: fn: bloğu başlıyor -> bir sonraki fonksiyon başlayana kadar fn'nin gövdesi.
    out = []
    i = 0
    current_fn = None
    fn_buf = []

    def flush_fn(fn_name: str | None, buf: list[str]):
        if fn_name is None:
            out.extend(buf)
            return

        # Eğer bu fonksiyon missing list'te ise __b1 ekle
        if fn_name in missing:
            # Fonksiyon içinde son "ret" satırını bul
            ret_idx = None
            for k in range(len(buf)-1, -1, -1):
                if buf[k].strip().startswith("ret"):
                    ret_idx = k
                    break

            stub = [
                f"{fn_name}__b1:",
                "ret"
            ]

            if ret_idx is None:
                # ret yoksa sonuna koy
                buf.extend(stub)
            else:
                # ret'ten hemen önce koy (ret zaten var ise, stub ret eklemek güvenli olsun diye ret'i kaldırmayacağız)
                # Ama "ret"i iki kez yapmayalım: ret'ten önce label koyup ret'i kullan
                # -> label + (mevcut ret)
                buf.insert(ret_idx, f"{fn_name}__b1:")

        out.extend(buf)

    while i < len(lines):
        ln = lines[i]
        m = FUNC_HDR.match(ln.strip())
        if m:
            # önceki fonksiyonu flush et
            flush_fn(current_fn, fn_buf)
            # yeni fonksiyon başlat
            current_fn = m.group(1)
            fn_buf = [ln]
        else:
            fn_buf.append(ln)
        i += 1

    flush_fn(current_fn, fn_buf)

    ASM_OUT.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    print("WROTE:", ASM_OUT.resolve())

    # 4) hızlı doğrulama: missing __b1 tanımları artık var mı?
    txt = ASM_OUT.read_text(encoding="utf-8", errors="replace")
    still_missing = []
    for fn in missing:
        if f"{fn}__b1:" not in txt:
            still_missing.append(fn)
    if still_missing:
        print("ERROR: still missing:", still_missing)
    else:
        print("OK: all missing __b1 labels were added.")

if __name__ == "__main__":
    main()
