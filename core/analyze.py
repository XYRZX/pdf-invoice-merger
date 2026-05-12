from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

import re
import fitz

from .config import DEFAULT_KEYWORDS, KeywordConfig, MergeOptions
from .models import PageItem, PageKind, RectTuple


def classify_text(text: str, keywords: KeywordConfig = DEFAULT_KEYWORDS) -> PageKind:
    t = text.lower()
    invoice_score = sum(1 for k in keywords.invoice if k.lower() in t)
    travel_score = sum(1 for k in keywords.travel if k.lower() in t)

    if invoice_score >= max(2, travel_score + 1):
        return "invoice"
    if travel_score >= max(2, invoice_score + 1):
        return "travel"
    if invoice_score > 0 and invoice_score >= travel_score:
        return "invoice"
    if travel_score > 0 and travel_score >= invoice_score:
        return "travel"
    return "other"


def _union_rect(a: Optional[fitz.Rect], b: fitz.Rect) -> fitz.Rect:
    return b if a is None else a | b


def _rect_area(r: fitz.Rect) -> float:
    return max(0.0, r.width) * max(0.0, r.height)


def estimate_content_clip(page: fitz.Page, kind: PageKind, options: MergeOptions) -> fitz.Rect:
    page_rect = page.rect
    if not options.auto_crop:
        return page_rect

    page_area = _rect_area(page_rect)
    page_h = max(1.0, page_rect.height)

    def add_rect_if_meaningful(content: Optional[fitz.Rect], rect: fitz.Rect, *, min_area: float) -> Optional[fitz.Rect]:
        if rect.is_empty:
            return content
        if _rect_area(rect) < min_area:
            return content
        if page_area > 0 and (_rect_area(rect) / page_area) > 0.985:
            return content
        return _union_rect(content, rect)

    content: Optional[fitz.Rect] = None
    text_rect: Optional[fitz.Rect] = None

    words = page.get_text("words")
    if words:
        all_text: Optional[fitz.Rect] = None
        for w in words:
            if len(w) < 4:
                continue
            rect = fitz.Rect(w[0], w[1], w[2], w[3])
            all_text = add_rect_if_meaningful(all_text, rect, min_area=12.0)

        text_candidate = all_text
        if kind == "travel":
            footer_band_top = page_rect.y1 - max(90.0, page_h * 0.15)
            page_no_re = re.compile(r"^(?:\d+|\d+/\d+|第?\s*\d+\s*页(?:/\s*共?\s*\d+\s*页)?|page\s*\d+(?:/\d+)?)$", re.IGNORECASE)
            filtered: Optional[fitz.Rect] = None
            for w in words:
                if len(w) < 5:
                    continue
                rect = fitz.Rect(w[0], w[1], w[2], w[3])
                txt = str(w[4]).strip()
                txt_norm = txt.replace(" ", "")
                in_footer = rect.y0 >= footer_band_top
                is_page_no = bool(page_no_re.match(txt_norm))
                is_footer_marker = is_page_no or txt_norm in ("/",) or ("页码" in txt_norm)
                if in_footer and is_footer_marker:
                    continue
                filtered = add_rect_if_meaningful(filtered, rect, min_area=12.0)

            if all_text is not None and filtered is not None:
                shrink = all_text.y1 - filtered.y1
                min_h = max(120.0, page_h * 0.15)
                if shrink >= 18.0 and filtered.height >= min_h:
                    text_candidate = filtered

        if text_candidate is not None:
            content = text_candidate
            text_rect = fitz.Rect(text_candidate)

    data = page.get_text("dict")
    for block in data.get("blocks", []):
        bbox = block.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        rect = fitz.Rect(bbox)
        btype = int(block.get("type", 0))
        if btype == 1:
            if page_area > 0 and (_rect_area(rect) / page_area) > 0.35:
                continue
            if text_rect is not None:
                expanded = fitz.Rect(
                    max(page_rect.x0, text_rect.x0 - 18.0),
                    max(page_rect.y0, text_rect.y0 - 18.0),
                    min(page_rect.x1, text_rect.x1 + 18.0),
                    min(page_rect.y1, text_rect.y1 + 18.0),
                )
                if not rect.intersects(expanded):
                    continue
            content = add_rect_if_meaningful(content, rect, min_area=80.0)
        else:
            if words:
                continue
            content = add_rect_if_meaningful(content, rect, min_area=80.0)

    if content is None:
        return page_rect

    pad = 16.0 if kind == "invoice" else 10.0
    clip = fitz.Rect(
        content.x0 - pad,
        content.y0 - pad,
        content.x1 + pad,
        content.y1 + pad,
    )
    clip = clip & page_rect
    if clip.is_empty:
        return page_rect
    return clip


def build_page_items(
    pdf_paths: Iterable[Path],
    options: MergeOptions,
    keywords: KeywordConfig = DEFAULT_KEYWORDS,
) -> List[PageItem]:
    items: List[PageItem] = []
    for pdf_path in pdf_paths:
        doc = fitz.open(pdf_path)
        try:
            for i in range(doc.page_count):
                page = doc.load_page(i)
                text = page.get_text("text") or ""
                kind = classify_text(text, keywords)
                stem = pdf_path.stem
                if "电子发票" in stem:
                    kind = "invoice"
                elif "行程单" in stem:
                    kind = "travel"
                elif "替票" in str(pdf_path):
                    kind = "invoice"
                clip = estimate_content_clip(page, kind, options)
                r = page.rect
                items.append(
                    PageItem(
                        pdf_path=pdf_path,
                        page_index=i,
                        kind=kind,
                        clip=(clip.x0, clip.y0, clip.x1, clip.y1),
                        source_size=(r.x0, r.y0, r.x1, r.y1),
                    )
                )
        finally:
            doc.close()
    return items


def normalize_inputs(paths: Iterable[Path]) -> List[Path]:
    out: List[Path] = []
    for p in paths:
        if p.is_dir():
            out.extend(sorted([x for x in p.rglob("*.pdf") if x.is_file()]))
        elif p.is_file() and p.suffix.lower() == ".pdf":
            out.append(p)
    return sorted(dict.fromkeys(out))
