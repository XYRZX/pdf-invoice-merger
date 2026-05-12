from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class KeywordConfig:
    invoice: Sequence[str]
    travel: Sequence[str]


DEFAULT_KEYWORDS = KeywordConfig(
    invoice=(
        "发票",
        "校验码",
        "价税合计",
        "开票日期",
        "购买方",
        "销售方",
        "机器编号",
    ),
    travel=(
        "行程单",
        "电子客票",
        "旅客",
        "航班号",
        "承运人",
        "票号",
        "出发",
        "到达",
    ),
)


@dataclass(frozen=True)
class MergeOptions:
    margin_pt: float = 24.0
    gap_pt: float = 10.0
    prefer_invoice_2up: bool = True
    auto_crop: bool = True
