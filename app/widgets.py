from __future__ import annotations

from pathlib import Path
from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFontMetrics
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .i18n import tr

class DropArea(QFrame):
    paths_dropped = Signal(list)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setMinimumHeight(96)
        self._label = QLabel(tr("drop_hint"))
        self._label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout(self)
        layout.addWidget(self._label)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        paths: List[Path] = []
        for u in urls:
            p = Path(u.toLocalFile())
            if p.exists():
                paths.append(p)
        if paths:
            self.paths_dropped.emit(paths)
        event.acceptProposedAction()


class ElidedLabel(QLabel):
    def __init__(self) -> None:
        super().__init__()
        self._full_text = ""
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(20)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)

    def set_full_text(self, text: str) -> None:
        self._full_text = text
        self.setToolTip(text)
        self._update_elide()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_elide()

    def _update_elide(self) -> None:
        fm = QFontMetrics(self.font())
        elided = fm.elidedText(self._full_text, Qt.ElideMiddle, max(10, self.width() - 8))
        super().setText(elided)


class PathRow(QWidget):
    remove_clicked = Signal()

    def __init__(self, title: str, full_path: str, icon, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(18, 18)
        self._icon_label.setPixmap(icon.pixmap(18, 18))

        self._title = ElidedLabel()
        self._title.set_full_text(title)
        self._title.setToolTip(full_path)

        self._remove = QToolButton()
        self._remove.setText("✕")
        self._remove.setAutoRaise(True)
        self._remove.setCursor(Qt.PointingHandCursor)
        self._remove.clicked.connect(self.remove_clicked.emit)
        self._remove.setFixedSize(22, 22)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)
        layout.addWidget(self._icon_label)
        layout.addWidget(self._title, 1)
        layout.addWidget(self._remove)
