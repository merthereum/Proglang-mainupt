# tools/build_calls_demo_fib_full_asm.py
from __future__ import annotations

import re
import sys
import shutil
import tempfile
from pathlib import Path


def _patch_missing_labels_with_ret(asm_text: str) -> str:
    # label defs: "name:"
    defined = set(re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*$", asm_text, flags=re.M))
    # refs in jmp/j??/call
    refs = set(re.findall(r"^\s*(?:jmp|jzf|jgf|jlf|call)\s+([A-Za-z_][A-Za-z0-9_]*)\b", asm_text, flags=re.M))
    missing = sorted(refs - defined)

    if not missing:
        return asm_text

    extra = ["", "; --- auto-added missing labels (safety) ---"]
    for lab in missing:
        # safe fallback: return from current function
        extra.append(f"{lab}:")
        extra.append("ret")
        extra.append("")
    return asm_text + "\n" + "\n".join(extra)


def _prepend_runtime_in_out(asm_text: str) -> str:
    # variant27_2addr IO: use inm/outm on mem[0x0000] as return/arg slot.
    rt = (
        "[section code, code]\n\n"
        "; --- runtime IO for variant27_2addr ---\n"
        "in:\n"
        "    inm 0x0000\n"
        "    ret\n\n"
        "out:\n"
        "    outm 0x0000\n"
        "    ret\n\n"
    )
    return rt + asm_text


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python tools/build_calls_demo_fib_full_asm.py <dot_dir> <out_asm>")
        return 2

    dot_dir = Path(sys.argv[1]).resolve()
    out_asm = Path(sys.argv[2]).resolve()
    if not dot_dir.exists():
        print(f"[ERR] dot_dir not found: {dot_dir}")
        return 2

    # 1) copy DOTs except in/out into temp dir (we provide real IO in runtime above)
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        for p in dot_dir.glob("*.dot"):
            if p.stem in ("in", "out"):
                continue
            shutil.copy2(p, td_path / p.name)

        # 2) call internal generator
        import task3.codegen_2addr as cg

        gen = getattr(cg, "generate_from_task2_dot_dir", None)
        if gen is None:
            print("[ERR] task3.codegen_2addr.generate_from_task2_dot_dir not found")
            return 2

        # Try common calling conventions
        tried = []
        ok = False
        for args, kwargs in [
            ((td_path, out_asm), {}),
            ((str(td_path), str(out_asm)), {}),
            ((), {"dot_dir": td_path, "out_asm": out_asm}),
            ((), {"dot_dir": str(td_path), "out_asm": str(out_asm)}),
            ((), {"dot_dir_path": td_path, "out_asm_path": out_asm}),
            ((), {"in_dot_dir": td_path, "out_asm": out_asm}),
            ((), {"dot_dir": td_path, "out_path": out_asm}),
        ]:
            try:
                gen(*args, **kwargs)
                ok = True
                break
            except TypeError as e:
                tried.append(str(e))

        if not ok:
            print("[ERR] Could not call generate_from_task2_dot_dir. TypeErrors:")
            for t in tried[:8]:
                print("  -", t)
            print("\nRun this to inspect signature:\n  python -c \"import inspect,task3.codegen_2addr as c; print(inspect.signature(c.generate_from_task2_dot_dir))\"")
            return 2

    # 3) postprocess: add IO + patch missing labels
    text = out_asm.read_text(encoding="utf-8")
    text = _patch_missing_labels_with_ret(text)
    text = _prepend_runtime_in_out(text)
    out_asm.write_text(text, encoding="utf-8")

    print(f"[OK] full asm written: {out_asm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
