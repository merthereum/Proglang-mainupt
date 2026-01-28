from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class CFGBlock:
    id: int
    label: str
    succs: List[Tuple[int, Optional[str]]] = field(default_factory=list)  # (to_id, edge_label)


@dataclass
class CFG:
    name: str
    blocks: Dict[int, CFGBlock] = field(default_factory=dict)
    next_id: int = 0

    entry: int = -1
    exit: int = -1

    errors: List[str] = field(default_factory=list)
    calls: Set[str] = field(default_factory=set)

    def new_block(self, label: str) -> int:
        bid = self.next_id
        self.next_id += 1
        self.blocks[bid] = CFGBlock(id=bid, label=label)
        return bid

    def add_edge(self, src: int, dst: int, label: Optional[str] = None) -> None:
        self.blocks[src].succs.append((dst, label))
