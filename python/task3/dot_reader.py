# src/task3/dot_reader.py
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class DotCFG:
    # node_id (int) -> label (str)
    nodes: Dict[int, str]
    # src_id (int) -> list of (dst_id, edge_label)
    edges: Dict[int, List[Tuple[int, Optional[str]]]]

    def succs(self, nid: int) -> List[Tuple[int, Optional[str]]]:
        return self.edges.get(nid, [])


_NODE_RE = re.compile(r'^\s*n(\d+)\s*\[\s*label\s*=\s*"(.*?)"\s*\]\s*;\s*$')
# Examples:
#   n4 -> n5 [label="True"];
#   n12 -> n13;
_EDGE_RE = re.compile(
    r'^\s*n(\d+)\s*->\s*n(\d+)\s*(?:\[\s*label\s*=\s*"(.*?)"\s*\])?\s*;\s*$'
)


def parse_dot(path: str | Path) -> DotCFG:
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="replace").splitlines()

    nodes: Dict[int, str] = {}
    edges: Dict[int, List[Tuple[int, Optional[str]]]] = {}

    for line in text:
        m = _NODE_RE.match(line)
        if m:
            nid = int(m.group(1))
            label = m.group(2)
            nodes[nid] = label
            continue

        m = _EDGE_RE.match(line)
        if m:
            src = int(m.group(1))
            dst = int(m.group(2))
            lab = m.group(3)
            if src not in edges:
                edges[src] = []
            edges[src].append((dst, lab))
            continue

    return DotCFG(nodes=nodes, edges=edges)


def find_node_by_label(cfg: DotCFG, wanted: str) -> Optional[int]:
    for nid, lab in cfg.nodes.items():
        if lab.strip() == wanted:
            return nid
    return None
