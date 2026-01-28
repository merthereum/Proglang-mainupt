from __future__ import annotations
from pathlib import Path
import argparse

from task1.parser import parse_text
from task1.ast import FuncDef

from .builder import CFGBuilder
from .render import cfg_to_dot, call_graph_to_dot, run_dot


def main() -> int:
    ap = argparse.ArgumentParser(
        prog="task2",
        description="Task2: build CFG for each function + call graph (Variant 3)"
    )
    ap.add_argument("rest", nargs="+", help="file1 [file2 ...] out_dir")
    ap.add_argument("--svg", action="store_true", help="also render SVG")
    ap.add_argument("--png", action="store_true", help="also render PNG")
    args = ap.parse_args()

    if len(args.rest) < 2:
        ap.error("Need at least one input file and output directory")

    *files, out_dir = args.rest
    out_dir = Path(out_dir)

    out_tree = out_dir / "tree"
    out_graph = out_dir / "graph"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_tree.mkdir(parents=True, exist_ok=True)
    out_graph.mkdir(parents=True, exist_ok=True)

    builder = CFGBuilder()

    all_errors = []
    func_map: dict[str, FuncDef] = {}
    defined = set()
    no_body = set()
    with_errors = set()
    call_edges = set()

    # 1) parse all files, collect all functions
    for fpath in files:
        p = Path(fpath)
        if not p.exists():
            all_errors.append(f"[io error] file not found: {p}")
            continue

        text = p.read_text(encoding="utf-8")
        res = parse_text(text)

        if res.errors:
            for e in res.errors:
                all_errors.append(f"[parse error] {p.name}: line={e.line} col={e.column}: {e.message}")
            continue

        prog = res.program
        if prog is None:
            all_errors.append(f"[parse error] {p.name}: program is None")
            continue

        (out_tree / f"{p.stem}.ok.txt").write_text("parsed OK\n", encoding="utf-8")

        for item in getattr(prog, "items", []):
            if isinstance(item, FuncDef):
                name = item.signature.name
                if name in func_map:
                    all_errors.append(f"[semantic] duplicate function name: {name} (file {p.name})")
                func_map[name] = item
                defined.add(name)
                if not getattr(item, "body", None):
                    no_body.add(name)

    # 2) build CFG for each function and render
    for name, func in func_map.items():
        cfg = builder.build_for_func(func)
        if cfg.errors:
            with_errors.add(name)
            all_errors.extend(cfg.errors)

        dot_text = cfg_to_dot(cfg)
        dot_path = out_graph / f"{name}.dot"
        dot_path.write_text(dot_text, encoding="utf-8")

        if args.png:
            run_dot(dot_path, out_graph / f"{name}.png")
        if args.svg:
            run_dot(dot_path, out_graph / f"{name}.svg")

        for callee in cfg.calls:
            call_edges.add((name, callee))

    # 3) build + render call graph
    cg_dot = call_graph_to_dot(
        edges=call_edges,
        defined=defined,
        no_body=no_body,
        with_errors=with_errors,
    )
    cg_dot_path = out_dir / "call_graph.dot"
    cg_dot_path.write_text(cg_dot, encoding="utf-8")

    if args.png:
        run_dot(cg_dot_path, out_dir / "call_graph.png")
    if args.svg:
        run_dot(cg_dot_path, out_dir / "call_graph.svg")

    # 4) write errors
    (out_dir / "call_graph.errors.txt").write_text("\n".join(all_errors) + ("\n" if all_errors else ""), encoding="utf-8")

    print(f"OK. out_dir={out_dir.resolve()}")
    print(f"Functions: {len(func_map)}; edges: {len(call_edges)}; errors: {len(all_errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
