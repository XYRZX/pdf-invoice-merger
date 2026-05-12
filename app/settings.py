from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSettings

from core.config import MergeOptions


ORG_NAME = "InvoiceMerge"
APP_NAME = "InvoiceMerge"


def _settings() -> QSettings:
    return QSettings(ORG_NAME, APP_NAME)


def load_output_dir() -> Optional[Path]:
    s = _settings()
    val = s.value("output_dir", "", type=str)
    p = Path(val) if val else None
    if p and p.exists() and p.is_dir():
        return p
    return None


def save_output_dir(path: Path) -> None:
    s = _settings()
    s.setValue("output_dir", str(path))


def load_options() -> MergeOptions:
    s = _settings()
    margin = float(s.value("margin_pt", 24.0))
    gap = float(s.value("gap_pt", 10.0))
    prefer_invoice_2up = bool(s.value("prefer_invoice_2up", True, type=bool))
    auto_crop = bool(s.value("auto_crop", True, type=bool))
    return MergeOptions(
        margin_pt=margin,
        gap_pt=gap,
        prefer_invoice_2up=prefer_invoice_2up,
        auto_crop=auto_crop,
    )


def save_options(options: MergeOptions) -> None:
    s = _settings()
    s.setValue("margin_pt", float(options.margin_pt))
    s.setValue("gap_pt", float(options.gap_pt))
    s.setValue("prefer_invoice_2up", bool(options.prefer_invoice_2up))
    s.setValue("auto_crop", bool(options.auto_crop))
