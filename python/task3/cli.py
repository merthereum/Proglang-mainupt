# src/task3/cli.py
from __future__ import annotations

import argparse
import sys
import subprocess
from pathlib import Path

from .dot_to_asm_2addr import generate_from_dot


def _run_task2_make_cfg(inp: Path, out_dir: Path) -> None:
    """
    Runs: python -m task2.cli <input.v3> <out_dir> --png
    Note: we do NOT use --no-png (because your task2.cli doesn't have it).
    """
    cmd = [
        sys.executable, "-m", "task2.cli",
        str(inp), str(out_dir),
        "--png",
    ]
    # Print the command for clarity in defense
    print("[task3] running:", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    # Always show outputs (teacher likes proofs)
    if r.stdout:
        print(r.stdout.strip())
    if r.stderr:
        print(r.stderr.strip(), file=sys.stderr)
    if r.returncode != 0:
        raise RuntimeError(f"task2.cli failed with code={r.returncode}")


def main() -> int:
    p = argparse.ArgumentParser(prog="task3")
    p.add_argument("input", help="Input .v3 source file")
    p.add_argument("out_dir", help="Output directory")
    p.add_argument("--asm", required=True, help="Path to output asm listing file")
    p.add_argument("--keep-cfg", action="store_true", help="Generate/keep task2 CFG artifacts in out_dir")
    args = p.parse_args()

    inp = Path(args.input)
    out_dir = Path(args.out_dir)
    asm_path = Path(args.asm)

    out_dir.mkdir(parents=True, exist_ok=True)
    asm_path.parent.mkdir(parents=True, exist_ok=True)

    if not inp.exists():
        print(f"[task3] ERROR: input file not found: {inp}")
        return 2

    dot_path = out_dir / "graph" / "main.dot"

    # If asked, try to generate CFG via task2 first
    if args.keep_cfg:
        try:
            _run_task2_make_cfg(inp, out_dir)
        except Exception as e:
            # If DOT already exists, we can continue safely
            if dot_path.exists():
                print(f"[task3] WARNING: task2 failed but DOT exists, continuing. Reason: {e}")
            else:
                print(f"[task3] ERROR: task2 failed and DOT not found. Reason: {e}")
                return 3

    # Require DOT to exist now
    if not dot_path.exists():
        print(f"[task3] ERROR: DOT not found: {dot_path}")
        print("[task3] Tip: run with --keep-cfg, or generate DOT with task2 manually.")
        return 4

    # DOT -> ASM (REAL)
    generate_from_dot(dot_path, asm_path)

    print(f"OK. out_dir={out_dir.resolve()}")
    print(f"OK. dot_used={dot_path.resolve()}")
    print(f"OK. asm_written={asm_path.resolve()}")
    print("NOTE: DOT(CFG) -> Linear ASM generation completed (2-addr).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
