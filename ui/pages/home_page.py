"""
ui/pages/home_page.py
Screen 1: Welcome screen with New Project / Open Project cards and Quick Stats.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from core import metadata_store
from ui.dialogs.new_project_dialog import NewProjectDialog
from ui.dialogs.import_dialog import ImportDialog


class StatCard(QWidget):
    def __init__(self, value: str, label: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        num = QLabel(value)
        num.setObjectName("stat_number")
        num.setFont(QFont("Inter", 16, QFont.Bold))

        lbl = QLabel(label)
        lbl.setObjectName("stat_label")

        layout.addWidget(num)
        layout.addWidget(lbl)
        layout.addSpacing(24)


class HomePage(QWidget):
    navigate_to_mapping = Signal()

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self._orc = orchestrator
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(0)

        # ── Title ─────────────────────────────────────────────
        title = QLabel("Welcome back")
        title.setObjectName("page_title")
        title.setFont(QFont("Inter", 32, QFont.Bold))
        layout.addWidget(title)
        layout.addSpacing(6)

        subtitle = QLabel("Select a project or initialize a new trajectory simulation analysis.")
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(32)

        # ── Cards row ─────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)

        # New Project card
        new_card = QFrame()
        new_card.setObjectName("new_project_card")
        new_card.setCursor(Qt.PointingHandCursor)
        new_card.setMinimumHeight(160)
        new_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        new_layout = QHBoxLayout(new_card)
        new_layout.setContentsMargins(24, 24, 24, 24)

        new_text = QVBoxLayout()
        new_text.setSpacing(6)
        new_title = QLabel("New Project")
        new_title.setObjectName("card_title")
        new_title.setFont(QFont("Inter", 20, QFont.Bold))
        new_title.setStyleSheet("color: white;")
        new_sub = QLabel("Import data and start a new analysis\nfrom scratch")
        new_sub.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 13px;")
        new_text.addWidget(new_title)
        new_text.addWidget(new_sub)
        new_text.addStretch()

        self._btn_new = QPushButton("+")
        self._btn_new.setObjectName("card_icon_btn")
        self._btn_new.setFixedSize(52, 52)
        self._btn_new.setFont(QFont("Inter", 22))
        self._btn_new.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.25); border: none; "
            "border-radius: 10px; color: white; font-size: 22px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.35); }"
        )
        self._btn_new.clicked.connect(self._open_new_project)

        new_layout.addLayout(new_text)
        new_layout.addStretch()
        new_layout.addWidget(self._btn_new, alignment=Qt.AlignVCenter)

        # Open Project card
        open_card = QFrame()
        open_card.setObjectName("open_project_card")
        open_card.setCursor(Qt.PointingHandCursor)
        open_card.setMinimumHeight(160)
        open_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        open_layout = QHBoxLayout(open_card)
        open_layout.setContentsMargins(24, 24, 24, 24)

        open_text = QVBoxLayout()
        open_text.setSpacing(6)
        open_title = QLabel("Open Project")
        open_title.setObjectName("card_title")
        open_title.setFont(QFont("Inter", 20, QFont.Bold))
        open_title.setStyleSheet("color: #1A1D2E;")
        open_sub = QLabel("Browse directories to open existing\ntrajectory simulation analysis")
        open_sub.setStyleSheet("color: #6B7280; font-size: 13px;")
        open_text.addWidget(open_title)
        open_text.addWidget(open_sub)
        open_text.addStretch()

        self._btn_open = QPushButton("📁")
        self._btn_open.setObjectName("card_icon_btn_dark")
        self._btn_open.setFixedSize(52, 52)
        self._btn_open.setStyleSheet(
            "QPushButton { background: #EEF2FF; border: none; "
            "border-radius: 10px; font-size: 22px; }"
            "QPushButton:hover { background: #E0E7FF; }"
        )
        self._btn_open.clicked.connect(self._open_existing)

        open_layout.addLayout(open_text)
        open_layout.addStretch()
        open_layout.addWidget(self._btn_open, alignment=Qt.AlignVCenter)

        cards_row.addWidget(new_card)
        cards_row.addWidget(open_card)
        layout.addLayout(cards_row)
        layout.addSpacing(40)

        # ── Quick Stats ────────────────────────────────────────
        stats_label = QLabel("QUICK STATS")
        stats_label.setObjectName("stats_section_label")
        stats_label.setFont(QFont("Inter", 10, QFont.Bold))
        layout.addWidget(stats_label)
        layout.addSpacing(10)

        self._stats_row = QHBoxLayout()
        self._stats_row.setSpacing(0)
        self._refresh_stats()
        layout.addLayout(self._stats_row)

        layout.addStretch()

    def _refresh_stats(self):
        # Clear
        while self._stats_row.count():
            item = self._stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        count = metadata_store.get_project_count()
        self._stats_row.addWidget(StatCard(str(count), "Active Projects"))
        self._stats_row.addWidget(StatCard("—", "Imported Datasets"))
        self._stats_row.addWidget(StatCard("Today", "Last Simulation Run"))
        self._stats_row.addStretch()

    def _open_new_project(self):
        dlg = NewProjectDialog(self._orc, self)
        if dlg.exec():
            # After project created, open ImportDialog
            imp = ImportDialog(self._orc, self)
            if imp.exec():
                self.navigate_to_mapping.emit()
        self._refresh_stats()

    def _open_existing(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Parquet File", "",
            "Data Files (*.parquet *.csv *.h5)"
        )
        if path:
            self._orc.load_schema(path)
            self.navigate_to_mapping.emit()

    def showEvent(self, event):
        self._refresh_stats()
        super().showEvent(event)
