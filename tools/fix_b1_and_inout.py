from pathlib import Path
import re

SRC = Path(r"out3\calls_demo_fib_full.asm")
DST = Path(r"out3\calls_demo_fib_io.asm")

text = SRC.read_text(encoding="utf-8")
lines = text.splitlines(True)

# Function labels: "name:" but NOT "name_b123:"
func_re = re.compile(r"^([A-Za-z_]\w*):\s*$")
blk_re  = re.compile(r"^([A-Za-z_]\w*)_b(\d+):\s*$")

# Find all top-level function label line indices
func_idxs = []
for i, ln in enumerate(lines):
    m = func_re.match(ln.strip())
    if not m:
        continue
    name = m.group(1)
    # exclude block labels
    if blk_re.match(ln.strip()):
        continue
    func_idxs.append((i, name))

# Add sentinel end
func_idxs.append((len(lines), "__END__"))

def region(start_i, end_i):
    return lines[start_i:end_i]

def has_label(region_lines, label):
    target = label + ":\n"
    target2 = label + ":\r\n"
    for ln in region_lines:
        if ln == target or ln == target2 or ln.strip() == (label + ":"):
            return True
    return False

def find_last_ret_index(region_lines):
    # returns index within region_lines
    for j in range(len(region_lines) - 1, -1, -1):
        if region_lines[j].lstrip().startswith("ret"):
            return j
    return -1

def first_out_arg_slot(region_lines):
    # Try to detect a 0x02xx slot used for argument/locals; pick first "0x02.." appearing as destination in movm
    for ln in region_lines:
        m = re.search(r"\bmovm\s+(0x02[0-9a-fA-F]{2,4})\b", ln)
        if m:
            return m.group(1)
    # fallback commonly used
    return "0x0200"

RET_SLOT = "0x0204"  # common return slot in your traces

out_arg_slot = None

# --- pass 1: ensure *_b1 label exists for each function if referenced ---
new_lines = []
for k in range(len(func_idxs) - 1):
    start_i, fn = func_idxs[k]
    end_i, _ = func_idxs[k + 1]
    reg = region(start_i, end_i)

    reg_text = "".join(reg)

    # detect if code references fn_b1
    ref_b1 = re.search(rf"\b{re.escape(fn)}_b1\b", reg_text) is not None
    def_b1 = has_label(reg, f"{fn}_b1")

    if fn == "__END__":
        continue

    # Determine out arg slot once
    if fn == "out":
        out_arg_slot = first_out_arg_slot(reg)

    if ref_b1 and not def_b1:
        # insert label before last ret, otherwise append at end with ret
        idx_ret = find_last_ret_index(reg)
        if idx_ret >= 0:
            # insert label line just before ret
            patched = reg[:idx_ret] + [f"{fn}_b1:\n"] + reg[idx_ret:]
        else:
            patched = reg + [f"{fn}_b1:\n", "ret\n"]
        new_lines.extend(patched)
    else:
        new_lines.extend(reg)

# Update text after b1 fix
lines = new_lines
text = "".join(lines)

# --- pass 2: patch in_b1 and out_b1 to real IO ---
def patch_block(fn, replacement_lines):
    nonlocal_text = None
    pattern = rf"(?ms)^{re.escape(fn)}_b1:\s*\n.*?^\s*ret\s*$"
    m = re.search(pattern, text)
    if not m:
        # if cannot find a "ret" bounded block, at least replace the label line + following few lines until next label
        # safer: locate fn_b1: line and replace until next label
        m2 = re.search(rf"(?m)^{re.escape(fn)}_b1:\s*$", text)
        if not m2:
            raise SystemExit(f"ERROR: {fn}_b1 label still not found.")
        start = m2.start()
        # find next label after start
        m3 = re.search(r"(?m)^[A-Za-z_]\w*:\s*$", text[m2.end():])
        end = len(text) if not m3 else m2.end() + m3.start()
        return text[:start] + "".join(replacement_lines) + text[end:]
    return re.sub(pattern, "".join(replacement_lines).rstrip("\n"), text)

# Prepare replacements
in_repl = [
    "in_b1:\n",
    "    ; --- IO: read one byte from rin into mem[0x0000] ---\n",
    "    inm 0x0000\n",
    f"    movm {RET_SLOT} 0x0000\n",
    "    ret\n",
]

if out_arg_slot is None:
    out_arg_slot = "0x0200"

out_repl = [
    "out_b1:\n",
    "    ; --- IO: write one byte from arg slot to rout ---\n",
    f"    outm {out_arg_slot}\n",
    "    ret\n",
]

# Apply patches
text = patch_block("in", in_repl)
text = patch_block("out", out_repl)

DST.write_text(text, encoding="utf-8")

print("OK:", DST)
print("Return slot used:", RET_SLOT)
print("out() arg slot used:", out_arg_slot)
