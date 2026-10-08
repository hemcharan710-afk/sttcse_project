"""
ui/dialogs/new_project_dialog.py
Screen 2: New Project modal — name, description, save location.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QPushButton, QFileDialog,
    QFrame, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class NewProjectDialog(QDialog):

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self._orc = orchestrator
        self.setModal(True)
        self.setFixedSize(540, 480)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # White card
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
        title = QLabel("New Project")
        title.setObjectName("modal_title")
        title.setFont(QFont("Inter", 20, QFont.Bold))

        close_btn = QPushButton("✕")
        close_btn.setObjectName("close_btn")
        close_btn.setFixedSize(32, 32)
        close_btn.clicked.connect(self.reject)
        close_btn.setStyleSheet(
            "QPushButton { background: white; border: 1px solid #D1D5DB; "
            "border-radius: 16px; color: #6B7280; font-size: 13px; }"
            "QPushButton:hover { background: #F3F4F6; }"
        )

        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_btn)
        card_layout.addLayout(header)

        # ── Project Name ──────────────────────────────────────
        card_layout.addWidget(QLabel("Project Name"))
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("e.g. Nanoparticle Diffusion Study")
        self._name_input.setFixedHeight(42)
        self._name_input.textChanged.connect(self._validate_form)
        card_layout.addWidget(self._name_input)

        # ── Description ───────────────────────────────────────
        card_layout.addWidget(QLabel("Description (optional)"))
        self._desc_input = QTextEdit()
        self._desc_input.setPlaceholderText("Brief description of your analysis...")
        self._desc_input.setFixedHeight(90)
        card_layout.addWidget(self._desc_input)

        # ── Save Location ─────────────────────────────────────
        card_layout.addWidget(QLabel("Save Location"))
        loc_row = QHBoxLayout()
        loc_row.setSpacing(8)

        self._loc_input = QLineEdit()
        default_loc = os.path.expanduser("~/Documents/TrajectoryAnalysis/Projects")
        self._loc_input.setText(default_loc)
        self._loc_input.setFixedHeight(42)

        browse_btn = QPushButton("📁")
        browse_btn.setFixedSize(42, 42)
        browse_btn.setStyleSheet(
            "QPushButton { background: #EEF2FF; border: 1px solid #D1D5DB; "
            "border-radius: 8px; font-size: 18px; }"
            "QPushButton:hover { background: #E0E7FF; }"
        )
        browse_btn.clicked.connect(self._browse_location)

        loc_row.addWidget(self._loc_input)
        loc_row.addWidget(browse_btn)
        card_layout.addLayout(loc_row)

        card_layout.addStretch()

        # ── Divider ───────────────────────────────────────────
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #E5E7EB;")
        card_layout.addWidget(line)

        # ── Footer ────────────────────────────────────────────
        footer = QHBoxLayout()
        footer.addStretch()

        self._continue_btn = QPushButton("Continue  →")
        self._continue_btn.setObjectName("btn_primary")
        self._continue_btn.setFixedHeight(42)
        self._continue_btn.setEnabled(False)
        self._continue_btn.clicked.connect(self._on_continue)
        self._continue_btn.setStyleSheet(
            "QPushButton { background: #3B5BDB; color: white; border: none; "
            "border-radius: 8px; padding: 0 24px; font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { background: #2F4AC7; }"
            "QPushButton:disabled { background: #BFC7E0; }"
        )

        footer.addWidget(self._continue_btn)
        card_layout.addLayout(footer)

        outer.addWidget(card)

    def _validate_form(self):
        self._continue_btn.setEnabled(bool(self._name_input.text().strip()))

    def _browse_location(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose Save Location")
        if folder:
            self._loc_input.setText(folder)

    def _on_continue(self):
        name     = self._name_input.text().strip()
        desc     = self._desc_input.toPlainText().strip()
        location = self._loc_input.text().strip()
        self._orc.create_project(name, desc, location)
        self.accept()
