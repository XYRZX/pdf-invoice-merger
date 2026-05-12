from __future__ import annotations

from dataclasses import dataclass
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union

import re
import fitz

from .analyze import build_page_items
from .config import MergeOptions
from .models import PageItem


A4_W_PT = 595.0
A4_H_PT = 842.0


@dataclass(frozen=True)
class MergeStats:
    total_files: int
    total_pages: int
    invoice_pages: int
    travel_pages: int
    other_pages: int
    output_pages: int


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

def _pair_key(path: Path) -> Optional[str]:
    name = path.stem
    l = name.find("【")
    r = name.find("】", l + 1) if l != -1 else -1
    if l != -1 and r != -1 and r > l + 1:
        key = name[l + 1 : r].strip()
        key = key.replace("元", "").replace(" ", "")
        key = re.sub(r"-\d+个行程$", "", key)
        return key
    return None

def _ensure_doc_open(docs: Dict[Path, fitz.Document], pdf_path: Path) -> fitz.Document:
    src_doc = docs.get(pdf_path)
    if src_doc is None:
        src_doc = fitz.open(pdf_path)
        docs[pdf_path] = src_doc
    return src_doc

def _place_item_in_rect(
    out_page: fitz.Page,
    docs: Dict[Path, fitz.Document],
    item: PageItem,
    container: fitz.Rect,
    *,
    align_top: bool,
) -> None:
    src_doc = _ensure_doc_open(docs, item.pdf_path)
    clip = fitz.Rect(item.clip)
    src_w = max(1.0, clip.width)
    src_h = max(1.0, clip.height)
    scale = min(container.width / src_w, container.height / src_h)
    block_w = src_w * scale
    block_h = src_h * scale
    x0 = container.x0 + (container.width - block_w) / 2.0
    y0 = container.y0 if align_top else (container.y0 + (container.height - block_h) / 2.0)
    dest = fitz.Rect(x0, y0, x0 + block_w, y0 + block_h)
    out_page.show_pdf_page(dest, src_doc, item.page_index, clip=clip)

@dataclass(frozen=True)
class PairBlock:
    order: int
    invoice: PageItem
    travel: PageItem

@dataclass(frozen=True)
class SingleBlock:
    order: int
    item: PageItem

Block = Union[PairBlock, SingleBlock]


def merge_pdfs_to_a4(
    pdf_paths: Iterable[Path],
    output_pdf: Path,
    options: MergeOptions,
    progress: Optional[callable] = None,
) -> MergeStats:
    pdf_list = list(pdf_paths)
    items = build_page_items(pdf_list, options=options)
    indexed_items = list(enumerate(items))
    path_counts = Counter(x.pdf_path for x in items)

    groups: Dict[str, Dict[str, Tuple[int, PageItem]]] = defaultdict(dict)
    for idx, item in indexed_items:
        if item.kind not in ("invoice", "travel"):
            continue
        if path_counts[item.pdf_path] != 1:
            continue
        key = _pair_key(item.pdf_path)
        if not key:
            continue
        groups[key][item.kind] = (idx, item)

    pairs: List[Tuple[int, PageItem, PageItem]] = []
    paired_paths: set[Path] = set()
    for g in groups.values():
        inv = g.get("invoice")
        trav = g.get("travel")
        if not inv or not trav:
            continue
        order = min(inv[0], trav[0])
        pairs.append((order, inv[1], trav[1]))
        paired_paths.add(inv[1].pdf_path)
        paired_paths.add(trav[1].pdf_path)

    pairs.sort(key=lambda x: x[0])
    blocks: List[Block] = []
    for order, inv, trav in pairs:
        blocks.append(PairBlock(order=order, invoice=inv, travel=trav))
    for idx, item in indexed_items:
        if item.pdf_path in paired_paths:
            continue
        blocks.append(SingleBlock(order=idx, item=item))
    blocks.sort(key=lambda x: x.order)

    docs: Dict[Path, fitz.Document] = {}
    out = fitz.open()
    output_pages = 0
    try:
        margin = float(options.margin_pt)
        gap = float(options.gap_pt)
        avail_w = A4_W_PT - 2 * margin
        avail_h = A4_H_PT - 2 * margin

        out_page = out.new_page(width=A4_W_PT, height=A4_H_PT)
        cursor_y = margin
        done = 0

        def new_container_page() -> fitz.Page:
            nonlocal cursor_y
            cursor_y = margin
            return out.new_page(width=A4_W_PT, height=A4_H_PT)

        for block in blocks:
            if isinstance(block, PairBlock):
                inv, trav = block.invoice, block.travel
                if cursor_y > margin:
                    out_page = new_container_page()
                half_h = (avail_h - gap) / 2.0
                top = fitz.Rect(margin, margin, margin + avail_w, margin + half_h)
                bottom = fitz.Rect(margin, margin + half_h + gap, margin + avail_w, margin + avail_h)
                _place_item_in_rect(out_page, docs, inv, top, align_top=True)
                _place_item_in_rect(out_page, docs, trav, bottom, align_top=True)
                cursor_y = margin + avail_h + gap
                done += 2
            else:
                item = block.item
                clip = fitz.Rect(item.clip)
                src_w = max(1.0, clip.width)
                src_h = max(1.0, clip.height)

                width_scale = avail_w / src_w
                scale = width_scale
                if options.prefer_invoice_2up and item.kind in ("invoice", "travel"):
                    half_h = (avail_h - gap) / 2.0
                    scale = min(width_scale, half_h / src_h)

                block_w = src_w * scale
                block_h = src_h * scale

                remaining_h = (margin + avail_h) - cursor_y
                if block_h > remaining_h and cursor_y > margin:
                    out_page = new_container_page()
                    remaining_h = (margin + avail_h) - cursor_y

                if block_h > remaining_h:
                    scale = min(width_scale, avail_h / src_h)
                    block_w = src_w * scale
                    block_h = src_h * scale
                    if block_h > remaining_h and cursor_y > margin:
                        out_page = new_container_page()
                        remaining_h = (margin + avail_h) - cursor_y

                x0 = margin + (avail_w - block_w) / 2.0
                y0 = cursor_y
                dest = fitz.Rect(x0, y0, x0 + block_w, y0 + block_h)

                src_doc = _ensure_doc_open(docs, item.pdf_path)
                out_page.show_pdf_page(dest, src_doc, item.page_index, clip=clip)
                cursor_y = dest.y1 + gap
                done += 1

            if progress is not None:
                progress(done, len(items))

        _ensure_parent(output_pdf)
        output_pages = out.page_count
        out.save(output_pdf)
    finally:
        for d in docs.values():
            d.close()
        out.close()

    invoice_pages = sum(1 for x in items if x.kind == "invoice")
    travel_pages = sum(1 for x in items if x.kind == "travel")
    other_pages = len(items) - invoice_pages - travel_pages
    return MergeStats(
        total_files=len(pdf_list),
        total_pages=len(items),
        invoice_pages=invoice_pages,
        travel_pages=travel_pages,
        other_pages=other_pages,
        output_pages=output_pages,
    )
