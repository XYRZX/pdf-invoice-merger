from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Tuple


PageKind = Literal["invoice", "travel", "other"]
RectTuple = Tuple[float, float, float, float]


@dataclass(frozen=True)
class PageItem:
    pdf_path: Path
    page_index: int
    kind: PageKind
    clip: RectTuple
    source_size: RectTuple
