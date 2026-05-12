from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from core.config import MergeOptions
from core.merge import MergeStats

from .i18n import tr
from .settings import load_options, load_output_dir, save_options, save_output_dir
from .widgets import DropArea, ElidedLabel, PathRow
from .worker import MergeRequest, MergeWorker


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(tr("app_title"))

        self._thread: Optional[QThread] = None
        self._worker: Optional[MergeWorker] = None

        self._drop = DropArea()
        self._drop.paths_dropped.connect(self._add_inputs)

        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.ExtendedSelection)
        self._list.setSpacing(6)

        self._btn_add_files = QPushButton(tr("add_pdf"))
        self._btn_add_folder = QPushButton(tr("add_folder"))
        self._btn_remove = QPushButton(tr("remove_selected"))
        self._btn_clear = QPushButton(tr("clear"))

        self._btn_add_files.clicked.connect(self._pick_files)
        self._btn_add_folder.clicked.connect(self._pick_folder)
        self._btn_remove.clicked.connect(self._remove_selected)
        self._btn_clear.clicked.connect(self._list.clear)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._btn_add_files)
        btn_row.addWidget(self._btn_add_folder)
        btn_row.addStretch(1)
        btn_row.addWidget(self._btn_remove)
        btn_row.addWidget(self._btn_clear)

        self._output_dir = load_output_dir()
        self._output_dir_label = ElidedLabel()
        self._output_dir_label.setObjectName("OutputPath")
        self._output_dir_label.setMaximumHeight(20)
        self._btn_pick_output_dir = QPushButton(tr("change"))
        self._btn_save_as = QPushButton(tr("save_as"))
        self._btn_pick_output_dir.clicked.connect(self._pick_output_dir)
        self._btn_save_as.clicked.connect(self._save_as)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel(tr("output")))
        out_row.addWidget(self._output_dir_label, 1)
        out_row.addWidget(self._btn_pick_output_dir)
        out_row.addWidget(self._btn_save_as)

        self._opt = load_options()
        self._spin_margin = QDoubleSpinBox()
        self._spin_margin.setRange(0.0, 120.0)
        self._spin_margin.setDecimals(1)
        self._spin_margin.setSingleStep(2.0)
        self._spin_margin.setValue(self._opt.margin_pt)

        self._spin_gap = QDoubleSpinBox()
        self._spin_gap.setRange(0.0, 60.0)
        self._spin_gap.setDecimals(1)
        self._spin_gap.setSingleStep(1.0)
        self._spin_gap.setValue(self._opt.gap_pt)

        self._chk_invoice_2up = QCheckBox(tr("two_up"))
        self._chk_invoice_2up.setChecked(self._opt.prefer_invoice_2up)
        self._chk_auto_crop = QCheckBox(tr("auto_crop"))
        self._chk_auto_crop.setChecked(self._opt.auto_crop)

        self._btn_apply_settings = QPushButton(tr("save_settings"))
        self._btn_apply_settings.clicked.connect(self._persist_settings)

        settings_box = QGroupBox(tr("advanced"))
        settings_box.setCheckable(True)
        settings_box.setChecked(False)
        settings_inner = QWidget()
        settings_inner.setVisible(False)
        settings_box.toggled.connect(settings_inner.setVisible)

        s_layout = QVBoxLayout(settings_inner)
        s_row1 = QHBoxLayout()
        s_row1.addWidget(QLabel(tr("margin")))
        s_row1.addWidget(self._spin_margin)
        s_row1.addSpacing(16)
        s_row1.addWidget(QLabel(tr("gap")))
        s_row1.addWidget(self._spin_gap)
        s_row1.addStretch(1)
        s_layout.addLayout(s_row1)
        s_layout.addWidget(self._chk_invoice_2up)
        s_layout.addWidget(self._chk_auto_crop)
        s_layout.addWidget(self._btn_apply_settings, alignment=Qt.AlignRight)

        settings_outer = QVBoxLayout(settings_box)
        settings_outer.addWidget(settings_inner)

        self._btn_start = QPushButton(tr("start"))
        self._btn_cancel = QPushButton(tr("cancel"))
        self._btn_cancel.setEnabled(False)
        self._btn_start.clicked.connect(self._start_merge_default)
        self._btn_cancel.clicked.connect(self._cancel_merge)

        run_row = QHBoxLayout()
        run_row.addStretch(1)
        run_row.addWidget(self._btn_start)
        run_row.addWidget(self._btn_cancel)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress_label = QLabel("")

        center = QWidget()
        layout = QVBoxLayout(center)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        layout.addWidget(self._drop)
        layout.addLayout(btn_row)
        layout.addWidget(self._list, 1)
        layout.addLayout(out_row)
        layout.addWidget(settings_box)
        layout.addLayout(run_row)
        layout.addWidget(self._progress)
        layout.addWidget(self._progress_label)
        self.setCentralWidget(center)

        self._sync_output_dir_ui()

    def _sync_output_dir_ui(self) -> None:
        self._output_dir_label.set_full_text(str(self._output_dir) if self._output_dir else "")

    def _pick_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, tr("select_pdfs"), "", tr("pdf_filter"))
        self._add_inputs([Path(x) for x in files])

    def _pick_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, tr("select_folder"))
        if folder:
            self._add_inputs([Path(folder)])

    def _pick_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, tr("select_output_dir"))
        if folder:
            self._output_dir = Path(folder)
            save_output_dir(self._output_dir)
            self._sync_output_dir_ui()

    def _save_as(self) -> None:
        path = self._choose_output_path()
        if path is None:
            return
        self._start_merge(path)

    def _start_merge_default(self) -> None:
        if self._thread is not None:
            return
        if self._output_dir is None:
            self._pick_output_dir()
        out_dir = self._output_dir
        if out_dir is None:
            return
        name = f"merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        self._start_merge(out_dir / name)

    def _choose_output_path(self) -> Optional[Path]:
        default_dir = str(self._output_dir) if self._output_dir else ""
        default_name = f"merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("save_file"),
            str(Path(default_dir) / default_name),
            tr("pdf_filter"),
        )
        return Path(path) if path else None

    def _gather_inputs(self) -> List[Path]:
        paths: List[Path] = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            p = Path(item.data(Qt.UserRole))
            paths.append(p)
        return paths

    def _add_inputs(self, paths: List[Path]) -> None:
        existing = {self._list.item(i).data(Qt.UserRole) for i in range(self._list.count())}
        for p in paths:
            s = str(p)
            if s in existing:
                continue
            title = p.name if p.name else s
            it = QListWidgetItem("")
            it.setData(Qt.UserRole, s)
            it.setToolTip(s)
            self._list.addItem(it)
            icon = self.style().standardIcon(QStyle.SP_DirIcon if p.is_dir() else QStyle.SP_FileIcon)
            row = PathRow(title=title, full_path=s, icon=icon)
            row.remove_clicked.connect(lambda _=False, item=it: self._remove_item(item))
            it.setSizeHint(row.sizeHint())
            self._list.setItemWidget(it, row)
            existing.add(s)

    def _remove_item(self, item: QListWidgetItem) -> None:
        row = self._list.row(item)
        if row >= 0:
            self._list.takeItem(row)

    def _remove_selected(self) -> None:
        for it in self._list.selectedItems():
            row = self._list.row(it)
            self._list.takeItem(row)

    def _persist_settings(self) -> None:
        opt = MergeOptions(
            margin_pt=float(self._spin_margin.value()),
            gap_pt=float(self._spin_gap.value()),
            prefer_invoice_2up=bool(self._chk_invoice_2up.isChecked()),
            auto_crop=bool(self._chk_auto_crop.isChecked()),
        )
        save_options(opt)
        self._opt = opt
        QMessageBox.information(self, tr("saved"), tr("settings_saved"))

    def _start_merge(self, output_pdf: Path) -> None:
        inputs = self._gather_inputs()
        if not inputs:
            QMessageBox.warning(self, tr("tip"), tr("no_input"))
            return

        self._btn_start.setEnabled(False)
        self._btn_cancel.setEnabled(True)
        self._progress.setValue(0)
        self._progress_label.setText(tr("ready"))

        req = MergeRequest(inputs=inputs, output_pdf=output_pdf, options=self._opt)
        worker = MergeWorker(req)
        thread = QThread(self)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.progress.connect(self._on_progress)
        worker.finished.connect(self._on_finished)
        worker.failed.connect(self._on_failed)

        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_thread_finished)

        self._worker = worker
        self._thread = thread
        thread.start()

    def _cancel_merge(self) -> None:
        if self._thread is not None:
            self._progress_label.setText(tr("cancelling"))
            self._thread.requestInterruption()

    def _on_progress(self, done: int, total: int) -> None:
        if total <= 0:
            return
        pct = int(done * 100 / total)
        self._progress.setValue(max(0, min(100, pct)))
        self._progress_label.setText(tr("processing", done=done, total=total))

    def _on_finished(self, stats: MergeStats) -> None:
        self._progress.setValue(100)
        self._progress_label.setText(
            tr(
                "done_label",
                files=stats.total_files,
                pages=stats.total_pages,
                out_pages=stats.output_pages,
            )
        )
        QMessageBox.information(
            self,
            tr("done_title"),
            tr("done_body", pages=stats.total_pages, out_pages=stats.output_pages),
        )

    def _on_failed(self, msg: str) -> None:
        self._progress_label.setText(tr("failed"))
        QMessageBox.critical(self, tr("failed"), msg)

    def _on_thread_finished(self) -> None:
        self._btn_start.setEnabled(True)
        self._btn_cancel.setEnabled(False)
        self._thread = None
        self._worker = None
