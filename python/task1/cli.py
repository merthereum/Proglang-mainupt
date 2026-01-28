from __future__ import annotations
import argparse
import sys
from functools import partial

from .parser import parse_text
from .dot_export import to_dot

def read_text_blocked(path: str, buf_size: int) -> str:
    # blok blok okuma (byte byte değil), sonsuz döngü yok
    chunks = []
    with open(path, "r", encoding="utf-8") as f:
        for part in iter(partial(f.read, buf_size), ""):
            chunks.append(part)
    return "".join(chunks)

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Input source file")
    ap.add_argument("output", help="Output .dot file")
    ap.add_argument("--buf", type=int, default=64 * 1024, help="Read buffer size")
    args = ap.parse_args(argv)

    text = read_text_blocked(args.input, args.buf)
    res = parse_text(text)

    if res.errors:
        for e in res.errors:
            print(f"[parse error] line={e.line} col={e.column}: {e.message}", file=sys.stderr)
        return 2

    dot = to_dot(res.program)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(dot)

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
