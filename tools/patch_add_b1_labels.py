# tools/patch_add_b1_labels.py
from pathlib import Path

def main():
    # Girdi/çıktı dosyaları
    src = Path(r"out3\calls_demo_fib_final.asm")
    dst = Path(r"out3\calls_demo_fib_final_fixed.asm")

    if not src.exists():
        raise SystemExit(f"ERROR: input not found: {src}")

    lines = src.read_text(encoding="utf-8").splitlines(True)

    # Bu fonksiyonlar için *_b1 label'ı eklemeye çalışacağız
    funcs = ["fib", "main", "readInt", "writeInt", "in", "out"]

    # Fonksiyon başlangıç satırlarını bul
    starts = {}
    for i, ln in enumerate(lines):
        s = ln.strip()
        for fn in funcs:
            if s == f"{fn}:":
                starts[fn] = i

    if not starts:
        raise SystemExit("ERROR: no function labels like 'fib:' found in asm.")

    ordered = sorted(starts.items(), key=lambda x: x[1])
    ranges = []
    for idx, (fn, s) in enumerate(ordered):
        e = ordered[idx + 1][1] if idx + 1 < len(ordered) else len(lines)
        ranges.append((fn, s, e))

    out = list(lines)
    shift = 0

    for fn, s, e in ranges:
        s2, e2 = s + shift, e + shift
        seg = out[s2:e2]

        # Bu fonksiyonda fn_b1'e jump var mı?
        if not any(f"jmp {fn}_b1" in l for l in seg):
            continue

        # Zaten label varsa geç
        if any(l.strip() == f"{fn}_b1:" for l in seg):
            continue

        # En sondaki 'ret' satırını bul (ret'in hemen üstüne label ekleyeceğiz)
        ret_idx = None
        for j in range(len(seg) - 1, -1, -1):
            if seg[j].strip() == "ret":
                ret_idx = j
                break

        if ret_idx is None:
            # ret yoksa fonksiyon sonuna güvenli çıkış ekle
            insert_at = e2
            out.insert(insert_at, f"{fn}_b1:\n")
            out.insert(insert_at + 1, "ret\n")
            shift += 2
        else:
            insert_at = s2 + ret_idx
            out.insert(insert_at, f"{fn}_b1:\n")
            shift += 1

    dst.write_text("".join(out), encoding="utf-8")
    print(f"OK: wrote {dst}")

if __name__ == "__main__":
    main()
