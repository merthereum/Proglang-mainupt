from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re


@dataclass
class DotCFGBlock:
    id: int
    label: str
    succs: List[Tuple[int, Optional[str]]] = field(default_factory=list)  # (to_id, edge_label)


@dataclass
class DotCFG:
    name: str
    blocks: Dict[int, DotCFGBlock] = field(default_factory=dict)
    entry: Optional[int] = None


_NODE_RE = re.compile(r'^\s*(n\d+)\s*\[\s*label\s*=\s*"(.+)"\s*\]\s*;\s*$')
_EDGE_RE = re.compile(r'^\s*(n\d+)\s*->\s*(n\d+)\s*(?:\[\s*label\s*=\s*"([^"]+)"\s*\])?\s*;\s*$')
_GRAPH_RE = re.compile(r'^\s*digraph\s+"([^"]+)"\s*\{\s*$')


def _nid_to_int(nid: str) -> int:
    # "n14" -> 14
    return int(nid[1:])


def load_cfg_from_dot(dot_path: Path) -> DotCFG:
    text = dot_path.read_text(encoding="utf-8", errors="replace").splitlines()

    gname = dot_path.stem
    for ln in text:
        m = _GRAPH_RE.match(ln)
        if m:
            gname = m.group(1)
            break

    cfg = DotCFG(name=gname)

    # 1) nodes
    for ln in text:
        m = _NODE_RE.match(ln)
        if not m:
            continue
        nid, raw_label = m.group(1), m.group(2)
        bid = _nid_to_int(nid)
        label = raw_label.replace(r"\n", "\n")
        cfg.blocks[bid] = DotCFGBlock(id=bid, label=label)

    # 2) edges
    for ln in text:
        m = _EDGE_RE.match(ln)
        if not m:
            continue
        src, dst, elab = m.group(1), m.group(2), m.group(3)
        sid = _nid_to_int(src)
        did = _nid_to_int(dst)
        if sid in cfg.blocks:
            cfg.blocks[sid].succs.append((did, elab))

    # 3) entry: label=="ENTRY" varsa onu al, yoksa en küçük id
    for bid, b in cfg.blocks.items():
        if b.label.strip() == "ENTRY":
            cfg.entry = bid
            break
    if cfg.entry is None and cfg.blocks:
        cfg.entry = min(cfg.blocks.keys())

    return cfg
