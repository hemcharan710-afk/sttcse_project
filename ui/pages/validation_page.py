"""
ui/pages/validation_page.py
Screens 6 & 8: Validation Report (Checklist).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ui.widgets.validation_row import ValidationRow
from ui.dialogs.drift_dialog import DriftDialog
from models.validation_report import ValidationReport


class ValidationPage(QWidget):
    navigate_to_viz = Signal()
    navigate_back   = Signal()

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self._orc = orchestrator
        self._report = None
        self._rows = {}
        self._build()
        self._connect_signals()

    def _build(self):
        # Allow scrolling if many checks
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        outer = QWidget()
        scroll.setWidget(outer)

        main = QVBoxLayout(self)
        main.setContentsMargins(0, 0, 0, 0)
        main.addWidget(scroll)

        layout = QVBoxLayout(outer)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(0)

        # ── Title ─────────────────────────────────────────────
        title = QLabel("Validation Report")
        title.setObjectName("page_title")
        title.setFont(QFont("Inter", 30, QFont.Bold))
        layout.addWidget(title)
        layout.addSpacing(6)

        subtitle = QLabel("We've analyzed your data to ensure it's ready for trajectory analysis.")
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(24)

        # ── File info bar ─────────────────────────────────────
        self._info_bar = QFrame()
        self._info_bar.setStyleSheet(
            "QFrame { background: white; border: 1px solid #E5E7EB; border-radius: 8px; padding: 12px 16px; }"
        )
        info_layout = QHBoxLayout(self._info_bar)
        info_layout.setContentsMargins(0, 0, 0, 0)
        self._info_label = QLabel("—")
        self._info_label.setStyleSheet("color: #4B5563; font-size: 13px; font-weight: 500;")
        info_layout.addWidget(self._info_label)
        layout.addWidget(self._info_bar)
        layout.addSpacing(32)

        # ── Checklist Header ──────────────────────────────────
        header = QHBoxLayout()
        chk_lbl = QLabel("VALIDATION CHECKLIST")
        chk_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #6B7280; letter-spacing: 1px;")
        
        self._summary_label = QLabel("—")
        self._summary_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._summary_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #1A1D2E;")
        
        header.addWidget(chk_lbl)
        header.addStretch()
        header.addWidget(self._summary_label)
        layout.addLayout(header)
        layout.addSpacing(12)

        # ── Checklist Container ───────────────────────────────
        self._list_container = QFrame()
        self._list_container.setStyleSheet(
            "QFrame { background: white; border: 1px solid #E5E7EB; border-radius: 8px; }"
        )
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        
        # Initial loading state
        self._loading_label = QLabel("Analyzing data...\nThis may take a moment.")
        self._loading_label.setAlignment(Qt.AlignCenter)
        self._loading_label.setStyleSheet("color: #6B7280; font-size: 14px; padding: 40px;")
        self._list_layout.addWidget(self._loading_label)
        
        layout.addWidget(self._list_container)
        
        layout.addStretch()
        layout.addSpacing(40)

        # ── Footer ────────────────────────────────────────────
        footer = QHBoxLayout()

        back_btn = QPushButton("Back")
        back_btn.setFixedHeight(40)
        back_btn.setStyleSheet(
            "QPushButton { background: white; border: 1px solid #D1D5DB; "
            "border-radius: 8px; padding: 0 20px; color: #374151; font-size: 14px; }"
            "QPushButton:hover { background: #F9FAFB; }"
        )
        back_btn.clicked.connect(self.navigate_back)

        self._continue_btn = QPushButton("Continue to Analysis  →")
        self._continue_btn.setFixedHeight(40)
        self._continue_btn.setEnabled(False)
        self._continue_btn.setStyleSheet(
            "QPushButton { background: #3B5BDB; color: white; border: none; "
            "border-radius: 8px; padding: 0 24px; font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { background: #2F4AC7; }"
            "QPushButton:disabled { background: #BFC7E0; }"
        )
        self._continue_btn.clicked.connect(self.navigate_to_viz.emit)

        footer.addWidget(back_btn)
        footer.addStretch()
        footer.addWidget(self._continue_btn)
        
        layout.addLayout(footer)

    def _connect_signals(self):
        self._orc.validation_done.connect(self._on_validation_done)
        self._orc.drift_preview_ready.connect(self._show_drift_dialog)

    def _on_validation_done(self, report: ValidationReport):
        self._report = report
        
        # Info bar
        f_min, f_max = report.frame_range
        info_text = (
            f"📄 {report.filename}  ·  "
            f"{report.n_particles:,} particles  ·  "
            f"{report.n_observations:,} observations  ·  "
            f"Frames {f_min}–{f_max}"
        )
        self._info_label.setText(info_text)
        
        self._update_summary()

        # Clear list
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._rows.clear()

        # Add rows
        for check in report.checks:
            row = ValidationRow(check)
            row.action_requested.connect(self._handle_row_action)
            self._list_layout.addWidget(row)
            self._rows[check.name] = row
            
            # Add separator line unless it's the last one
            if check != report.checks[-1]:
                line = QFrame()
                line.setFixedHeight(1)
                line.setStyleSheet("background-color: #F3F4F6;")
                self._list_layout.addWidget(line)

        # Enable continue if no fatal errors
        self._continue_btn.setEnabled(report.error_count == 0)

    def _update_summary(self):
        if not self._report:
            return
        p_c = self._report.passed_count
        w_c = self._report.warning_count
        
        # Count "corrected" as passed for the header
        for r in self._rows.values():
            if r._check.status == "corrected":
                p_c += 1
                w_c -= 1

        parts = []
        if p_c > 0:
            parts.append(f"<span style='color: #2F9E44;'>{p_c} passed</span>")
        if w_c > 0:
            parts.append(f"<span style='color: #F59F00;'>{w_c} warnings</span>")
            
        self._summary_label.setText("  ·  ".join(parts))

    def _handle_row_action(self, check_name: str):
        if check_name == "Possible Drift":
            # Need to compute drift preview first
            # The orchestrator will emit drift_preview_ready which opens the dialog
            dlg = DriftDialog(self._orc, self)
            if dlg.exec():
                # Corrected!
                self._rows[check_name].mark_corrected()
                self._update_summary()

    def _show_drift_dialog(self, preview_data: dict):
        pass # Handle if we want to separate preview generation from dialog opening
