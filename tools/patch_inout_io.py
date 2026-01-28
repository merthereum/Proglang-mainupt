from pathlib import Path
import re

SRC = Path(r"out3\calls_demo_fib_full.asm")
DST = Path(r"out3\calls_demo_fib_io.asm")

text = SRC.read_text(encoding="utf-8")

# ---- yardımcı: fonksiyon bloğunu yakala ----
def find_block(label: str) -> tuple[int,int]:
    # label: satır başında "in:" gibi
    m = re.search(rf"(?m)^{re.escape(label)}\s*\n", text)
    if not m:
        raise SystemExit(f"Cannot find label {label}")
    start = m.start()
    # bir sonraki "^\w+:" etiketine kadar
    m2 = re.search(r"(?m)^[A-Za-z_][A-Za-z0-9_]*:\s*$", text[m.end():])
    end = len(text) if not m2 else m.end() + m2.start()
    return start, end

# ---- in/out içinde kullanılan return/arg slot adreslerini bulmaya çalış ----
def pick_ret_slot(block: str) -> str:
    # çoğu senaryoda codegen return slotunu 0x0204'e movm ile taşır.
    # yoksa default 0x0204
    return "0x0204"

def pick_arg_slot(block: str) -> str:
    # out fonksiyonunda parametre genelde 0x0200 civarına taşınır.
    # blok içinden ilk 0x02xx görünen adresi seçmeye çalışalım.
    m = re.search(r"movm\s+(0x02[0-9a-fA-F]{2})\s+0x", block)
    if m:
        return m.group(1)
    return "0x0200"

# ---- in() patch: out3\calls_demo_fib_full.asm içindeki in_b1'e IO ekle ----
in_start, in_end = find_block("in:")
in_block = text[in_start:in_end]
RET = pick_ret_slot(in_block)

# in_b1 label'ını bul (sen zaten _b1 patch yaptıysan vardır)
if not re.search(r"(?m)^in_b1:\s*$", in_block):
    raise SystemExit("in_b1 label not found inside in(). You must run the _b1 patch first on full asm.")

# in_b1: ... ret kısmını tamamen değiştir
in_block_new = re.sub(
    r"(?ms)^in_b1:\s*.*?^\s*ret\s*$",
    "in_b1:\n"
    "    ; --- IO IMPLEMENTATION (read 1 byte) ---\n"
    "    inm 0x0000\n"
    f"    movm {RET} 0x0000\n"
    "    ret\n",
    in_block
)

# ---- out() patch: out_b1'e IO ekle ----
out_start, out_end = find_block("out:")
out_block = text[out_start:out_end]
ARG = pick_arg_slot(out_block)

if not re.search(r"(?m)^out_b1:\s*$", out_block):
    raise SystemExit("out_b1 label not found inside out(). You must run the _b1 patch first on full asm.")

out_block_new = re.sub(
    r"(?ms)^out_b1:\s*.*?^\s*ret\s*$",
    "out_b1:\n"
    "    ; --- IO IMPLEMENTATION (write 1 byte) ---\n"
    f"    outm {ARG}\n"
    "    ret\n",
    out_block
)

# ---- metni birleştir ----
patched = text[:in_start] + in_block_new + text[in_end:out_start] + out_block_new + text[out_end:]
DST.write_text(patched, encoding="utf-8")
print("OK:", DST)
print("Used RET slot:", RET, "ARG slot:", ARG)
