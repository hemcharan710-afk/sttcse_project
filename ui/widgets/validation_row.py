"""
ui/widgets/validation_row.py
Single row widget for the validation checklist.
Expandable for warnings.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from models.validation_report import ValidationCheck


class ValidationRow(QFrame):
    action_requested = Signal(str)  # emitted when "Apply corrections" is clicked

    def __init__(self, check: ValidationCheck, parent=None):
        super().__init__(parent)
        self._check = check
        self.setObjectName("validation_row")
        self._is_expanded = False
        self._build()

    def _build(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 12, 16, 12)
        self._layout.setSpacing(12)

        # ── Main Header Row ───────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(12)

        # Icon
        self._icon = QLabel()
        self._icon.setFixedSize(20, 20)
        self._icon.setAlignment(Qt.AlignCenter)
        
        # Name
        name_label = QLabel(self._check.name)
        name_label.setStyleSheet("font-size: 14px; font-weight: 500; color: #1A1D2E;")
        
        # Status
        self._status = QLabel()
        self._status.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        header.addWidget(self._icon)
        header.addWidget(name_label)
        header.addStretch()
        header.addWidget(self._status)
        
        self._layout.addLayout(header)

        # ── Expanded Details Area ─────────────────────────────
        self._details_widget = QWidget()
        details_layout = QVBoxLayout(self._details_widget)
        details_layout.setContentsMargins(32, 0, 0, 0)
        details_layout.setSpacing(12)

        detail_text = QLabel(self._check.detail)
        detail_text.setStyleSheet("color: #4B5563; font-size: 13px;")
        detail_text.setWordWrap(True)
        details_layout.addWidget(detail_text)

        if self._check.correctable:
            btn_row = QHBoxLayout()
            
            ignore_btn = QPushButton("Ignore")
            ignore_btn.setStyleSheet(
                "QPushButton { background: transparent; border: 1px solid #D1D5DB; "
                "border-radius: 6px; padding: 6px 12px; color: #4B5563; font-size: 12px; }"
                "QPushButton:hover { background: #F3F4F6; }"
            )
            ignore_btn.clicked.connect(self._toggle_expand)
            
            apply_btn = QPushButton("Apply corrections")
            apply_btn.setStyleSheet(
                "QPushButton { background: white; border: 1px solid #D1D5DB; "
                "border-radius: 6px; padding: 6px 12px; color: #1A1D2E; font-size: 12px; font-weight: 600; }"
                "QPushButton:hover { background: #F9FAFB; }"
            )
            apply_btn.clicked.connect(lambda: self.action_requested.emit(self._check.name))
            
            btn_row.addWidget(ignore_btn)
            btn_row.addWidget(apply_btn)
            btn_row.addStretch()
            details_layout.addLayout(btn_row)

        self._layout.addWidget(self._details_widget)
        self._details_widget.hide()

        self._update_style()

    def _update_style(self):
        if self._check.status == "passed":
            self._icon.setText("✓")
            self._icon.setStyleSheet("color: #2F9E44; font-weight: bold; font-size: 16px;")
            self._status.setText("Passed")
            self._status.setObjectName("status_passed")
            self.setCursor(Qt.ArrowCursor)
        elif self._check.status == "warning":
            self._icon.setText("⚠")
            self._icon.setStyleSheet("color: #F59F00; font-weight: bold; font-size: 16px;")
            arrow = "▾" if self._is_expanded else "▸"
            self._status.setText(f"Warning {arrow}")
            self._status.setObjectName("status_warning")
            self.setCursor(Qt.PointingHandCursor)
        elif self._check.status == "corrected":
            self._icon.setText("✓")
            self._icon.setStyleSheet("color: #2F9E44; font-weight: bold; font-size: 16px;")
            self._status.setText("Drift Corrected")
            self._status.setObjectName("status_corrected")
            self.setCursor(Qt.ArrowCursor)

        self.style().unpolish(self._status)
        self.style().polish(self._status)

    def mousePressEvent(self, event):
        if self._check.status == "warning":
            self._toggle_expand()
        super().mousePressEvent(event)

    def _toggle_expand(self):
        self._is_expanded = not self._is_expanded
        self._details_widget.setVisible(self._is_expanded)
        self.setObjectName("validation_row_expanded" if self._is_expanded else "validation_row")
        self._update_style()
        self.style().unpolish(self)
        self.style().polish(self)
        
    def mark_corrected(self):
        """Called by parent when drift is successfully corrected."""
        self._check.status = "corrected"
        self._is_expanded = False
        self._details_widget.hide()
        self.setObjectName("validation_row")
        self._update_style()
        self.style().unpolish(self)
        self.style().polish(self)
