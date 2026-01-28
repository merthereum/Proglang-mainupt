# src/task2/dot_blockify.py
from __future__ import annotations
import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

NODE_RE = re.compile(r'^\s*n(\d+)\s*\[label="(.*)"\];\s*$')
EDGE_RE = re.compile(r'^\s*n(\d+)\s*->\s*n(\d+)(?:\s*\[label="(True|False)"\])?;\s*$')

@dataclass
class DotCFG:
    nodes: Dict[int, str]
    edges: List[Tuple[int, int, Optional[str]]]

def parse_dot(path: Path) -> DotCFG:
    nodes: Dict[int, str] = {}
    edges: List[Tuple[int, int, Optional[str]]] = []

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = NODE_RE.match(line)
        if m:
            nid = int(m.group(1))
            lab = m.group(2)
            nodes[nid] = lab
            continue
        m = EDGE_RE.match(line)
        if m:
            a = int(m.group(1)); b = int(m.group(2))
            el = m.group(3) if m.group(3) else None
            edges.append((a, b, el))
    return DotCFG(nodes=nodes, edges=edges)

def build_maps(cfg: DotCFG):
    out_map: Dict[int, List[Tuple[int, Optional[str]]]] = {k: [] for k in cfg.nodes}
    in_deg: Dict[int, int] = {k: 0 for k in cfg.nodes}
    for a, b, el in cfg.edges:
        out_map[a].append((b, el))
        in_deg[b] = in_deg.get(b, 0) + 1
    return out_map, in_deg

def find_entry(cfg: DotCFG) -> int:
    for nid, lab in cfg.nodes.items():
        if lab.strip() == "ENTRY":
            return nid
    # fallback: smallest id
    return min(cfg.nodes.keys())

def is_barrier(label: str) -> bool:
    s = label.strip()
    return s in {"ENTRY", "EXIT", "join", "after_while", "after_do", "break"} or s.startswith("if ") or s.startswith("while ") or s.startswith("do_while ")

def blockify(cfg: DotCFG):
    out_map, in_deg = build_maps(cfg)
    entry = find_entry(cfg)

    block_id_of: Dict[int, int] = {}
    blocks: List[List[int]] = []

    def start_new_block(start: int) -> int:
        bid = len(blocks)
        blocks.append([start])
        block_id_of[start] = bid
        return bid

    # simple forward walk from entry over all nodes (deterministic)
    visited = set()

    def walk(n: int):
        if n in visited:
            return
        visited.add(n)

        # decide block start
        if n not in block_id_of:
            start_new_block(n)

        bid = block_id_of[n]

        # if we can merge forward linearly: outdegree==1, indegree(next)==1, no condition edge, and not barrier
        while True:
            outs = out_map.get(blocks[bid][-1], [])
            if len(outs) != 1:
                break
            nxt, el = outs[0]
            if el is not None:
                break
            if in_deg.get(nxt, 0) != 1:
                break
            if is_barrier(cfg.nodes.get(blocks[bid][-1], "")) or is_barrier(cfg.nodes.get(nxt, "")):
                break
            if nxt in block_id_of:
                break
            blocks[bid].append(nxt)
            block_id_of[nxt] = bid

        # recurse to successors of last node in block
        last = blocks[bid][-1]
        for nxt, _ in out_map.get(last, []):
            if nxt not in block_id_of:
                start_new_block(nxt)
            walk(nxt)

    walk(entry)

    # build block edges (from last node)
    bedges: List[Tuple[int, int, Optional[str]]] = []
    for bid, nodes in enumerate(blocks):
        last = nodes[-1]
        for nxt, el in out_map.get(last, []):
            bedges.append((bid, block_id_of[nxt], el))

    return blocks, bedges

def emit_block_dot(cfg: DotCFG, blocks, bedges, out_path: Path):
    lines: List[str] = []
    lines.append('digraph CFG {')
    lines.append('  node [shape=box];')

    # node labels
    for bid, ns in enumerate(blocks):
        body = []
        for n in ns:
            body.append(cfg.nodes.get(n, f"n{n}").replace('"', r'\"'))
        label = "\\l".join(body) + "\\l"
        lines.append(f'  b{bid} [label="#{bid}\\l{label}"];')

    # edges with "default" and "on condition"
    for a, b, el in bedges:
        if el is None:
            lines.append(f'  b{a} -> b{b} [label="default"];')
        else:
            lines.append(f'  b{a} -> b{b} [label="on {el}"];')

    lines.append('}')
    out_path.write_text("\n".join(lines), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("in_dot", help="input DOT (e.g. out2/graph/main.dot)")
    ap.add_argument("out_dot", help="output DOT (e.g. out2/graph/main_bb.dot)")
    ap.add_argument("--png", action="store_true", help="also render PNG using graphviz dot")
    args = ap.parse_args()

    in_dot = Path(args.in_dot)
    out_dot = Path(args.out_dot)
    cfg = parse_dot(in_dot)
    blocks, bedges = blockify(cfg)
    emit_block_dot(cfg, blocks, bedges, out_dot)

    if args.png:
        # requires graphviz 'dot' in PATH
        png = out_dot.with_suffix(".png")
        import subprocess
        subprocess.check_call(["dot", "-Tpng", str(out_dot), "-o", str(png)])
        print("PNG:", png.resolve())

    print("OK:", out_dot.resolve())
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
