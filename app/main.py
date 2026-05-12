from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


_STYLE = """
QWidget { font-size: 13px; }
QMainWindow { background: #F8FAFD; }
QFrame { background: #FFFFFF; border: 1px solid #E0E3E7; border-radius: 12px; }
QGroupBox { border: 1px solid #E0E3E7; border-radius: 12px; margin-top: 10px; padding: 10px; background: #FFFFFF; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #1F1F1F; }
QLabel { color: #1F1F1F; }
QPushButton { background: #1A73E8; color: #FFFFFF; border: none; border-radius: 10px; padding: 8px 14px; }
QPushButton:hover { background: #1668D8; }
QPushButton:pressed { background: #155CC0; }
QPushButton:disabled { background: #B0C7F0; color: #F3F6FC; }
QListWidget { background: #FFFFFF; border: 1px solid #E0E3E7; border-radius: 12px; padding: 6px; }
QProgressBar { border: 1px solid #E0E3E7; border-radius: 8px; background: #FFFFFF; text-align: center; height: 18px; }
QProgressBar::chunk { background: #1A73E8; border-radius: 8px; }
QDoubleSpinBox { background: #FFFFFF; border: 1px solid #E0E3E7; border-radius: 8px; padding: 4px 8px; }
QCheckBox { spacing: 8px; }
#OutputPath { color: #5F6368; font-size: 12px; }
QToolButton { border: none; color: #5F6368; }
QToolButton:hover { color: #1F1F1F; }
"""


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(_STYLE)
    w = MainWindow()
    w.resize(900, 720)
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
