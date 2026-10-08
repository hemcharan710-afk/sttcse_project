"""
ui/dialogs/import_dialog.py
Screen 3: Import Data modal — drag & drop or browse.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent


class DropZone(QFrame):
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("drop_zone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(200)
        self.setStyleSheet(
            "#drop_zone { background: #EEF2FF; border: 2px dashed #3B5BDB; "
            "border-radius: 12px; }"
        )
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        icon = QLabel("⬆")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 36px; color: #3B5BDB;")
        layout.addWidget(icon)

        label = QLabel("Drag and Drop file")
        label.setObjectName("drop_zone_label")
        label.setAlignment(Qt.AlignCenter)
        label.setFont(QFont("Inter", 14, QFont.Medium))
        layout.addWidget(label)

        or_label = QLabel("or")
        or_label.setAlignment(Qt.AlignCenter)
        or_label.setStyleSheet("color: #6B7280; font-size: 13px;")
        layout.addWidget(or_label)

        self._browse_btn = QPushButton("Browse Files")
        self._browse_btn.setFixedHeight(40)
        self._browse_btn.setFixedWidth(160)
        self._browse_btn.setStyleSheet(
            "QPushButton { background: #3B5BDB; color: white; border: none; "
            "border-radius: 8px; font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { background: #2F4AC7; }"
        )
        self._browse_btn.clicked.connect(self._browse)
        layout.addWidget(self._browse_btn, alignment=Qt.AlignCenter)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Data File", "",
            "Data Files (*.parquet *.csv *.h5);;All Files (*)"
        )
        if path:
            self.file_dropped.emit(path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(
                "#drop_zone { background: #DBEAFE; border: 2px dashed #1D4ED8; "
                "border-radius: 12px; }"
            )

    def dragLeaveEvent(self, event):
        self.setStyleSheet(
            "#drop_zone { background: #EEF2FF; border: 2px dashed #3B5BDB; "
            "border-radius: 12px; }"
        )

    def dropEvent(self, event: QDropEvent):
        self.setStyleSheet(
            "#drop_zone { background: #EEF2FF; border: 2px dashed #3B5BDB; "
            "border-radius: 12px; }"
        )
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.file_dropped.emit(path)


class ImportDialog(QDialog):

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self._orc = orchestrator
        self._selected_file = ""
        self.setModal(True)
        self.setFixedSize(540, 460)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("modal_container")
        card.setStyleSheet(
            "#modal_container { background: white; border-radius: 12px; "
            "border: 1px solid #E5E7EB; }"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 28, 32, 28)
        card_layout.setSpacing(20)

        # ── Header ────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("Import Data")
        title.setFont(QFont("Inter", 20, QFont.Bold))

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(
            "QPushButton { background: white; border: 1px solid #D1D5DB; "
            "border-radius: 16px; color: #6B7280; font-size: 13px; }"
            "QPushButton:hover { background: #F3F4F6; }"
        )
        close_btn.clicked.connect(self.reject)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_btn)
        card_layout.addLayout(header)

        # ── Drop zone ─────────────────────────────────────────
        self._drop_zone = DropZone()
        self._drop_zone.file_dropped.connect(self._on_file_selected)
        card_layout.addWidget(self._drop_zone)

        # ── Selected file label ───────────────────────────────
        self._file_label = QLabel("")
        self._file_label.setStyleSheet("color: #2F9E44; font-size: 12px;")
        self._file_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self._file_label)

        card_layout.addStretch()

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #E5E7EB;")
        card_layout.addWidget(line)

        # ── Footer ────────────────────────────────────────────
        footer = QHBoxLayout()

        back_btn = QPushButton("Back")
        back_btn.setFixedHeight(40)
        back_btn.setStyleSheet(
            "QPushButton { background: white; border: 1px solid #D1D5DB; "
            "border-radius: 8px; padding: 0 20px; color: #374151; font-size: 14px; }"
            "QPushButton:hover { background: #F9FAFB; }"
        )
        back_btn.clicked.connect(self.reject)

        self._continue_btn = QPushButton("Continue  →")
        self._continue_btn.setFixedHeight(40)
        self._continue_btn.setEnabled(False)
        self._continue_btn.setStyleSheet(
            "QPushButton { background: #3B5BDB; color: white; border: none; "
            "border-radius: 8px; padding: 0 24px; font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { background: #2F4AC7; }"
            "QPushButton:disabled { background: #BFC7E0; }"
        )
        self._continue_btn.clicked.connect(self._on_continue)

        footer.addWidget(back_btn)
        footer.addStretch()
        footer.addWidget(self._continue_btn)
        card_layout.addLayout(footer)

        outer.addWidget(card)

    def _on_file_selected(self, path: str):
        self._selected_file = path
        filename = os.path.basename(path)
        self._file_label.setText(f"✓  {filename}")
        self._continue_btn.setEnabled(True)

    def _on_continue(self):
        if self._selected_file:
            self._orc.load_schema(self._selected_file)
            self.accept()
