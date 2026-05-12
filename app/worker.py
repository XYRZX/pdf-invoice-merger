from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QObject, QThread, Signal, Slot

from core.analyze import normalize_inputs
from core.config import MergeOptions
from core.merge import MergeStats, merge_pdfs_to_a4

from .i18n import tr

@dataclass(frozen=True)
class MergeRequest:
    inputs: List[Path]
    output_pdf: Path
    options: MergeOptions


class MergeWorker(QObject):
    progress = Signal(int, int)
    finished = Signal(MergeStats)
    failed = Signal(str)

    def __init__(self, request: MergeRequest):
        super().__init__()
        self._request = request

    @Slot()
    def run(self) -> None:
        try:
            pdfs = normalize_inputs(self._request.inputs)
            if not pdfs:
                raise RuntimeError(tr("no_pdf_found"))

            def cb(done: int, total: int) -> None:
                if QThread.currentThread().isInterruptionRequested():
                    raise RuntimeError(tr("cancelled"))
                self.progress.emit(done, total)

            stats = merge_pdfs_to_a4(
                pdf_paths=pdfs,
                output_pdf=self._request.output_pdf,
                options=self._request.options,
                progress=cb,
            )
            self.finished.emit(stats)
        except Exception as e:
            self.failed.emit(str(e))
