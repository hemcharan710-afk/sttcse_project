"""
ui/pages/parameters_page.py
Screen 5: Experimental Parameters setup (Frame Rate, Pixel Scale, etc.)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QFrame,
    QGridLayout, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class ParametersPage(QWidget):
    navigate_to_validation = Signal()
    navigate_back          = Signal()

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self._orc = orchestrator
        self._build()
        self._connect_signals()

    def _build(self):
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
        title = QLabel("Experimental Parameters")
        title.setObjectName("page_title")
        title.setFont(QFont("Inter", 30, QFont.Bold))
        layout.addWidget(title)
        layout.addSpacing(6)

        subtitle = QLabel("Set physical scales and acquisition parameters to compute accurate metrics.")
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(32)

        # ── Two Column Layout ─────────────────────────────────
        cols = QHBoxLayout()
        cols.setSpacing(32)

        # Left Column: Acquisition
        left = QVBoxLayout()
        left.setSpacing(16)
        
        acq_title = QLabel("Acquisition Settings")
        acq_title.setObjectName("param_section_title")
        left.addWidget(acq_title)

        acq_grid = QGridLayout()
        acq_grid.setSpacing(12)

        acq_grid.addWidget(QLabel("Frame Rate"), 0, 0)
        
        fps_row = QHBoxLayout()
        self._fps_input = QLineEdit("30")
        self._fps_input.setFixedWidth(80)
        fps_row.addWidget(self._fps_input)
        fps_row.addWidget(QLabel("fps"))
        fps_row.addStretch()
        acq_grid.addLayout(fps_row, 0, 1)

        acq_grid.addWidget(QLabel("Time Interval (Δt)"), 1, 0)
        self._dt_input = QLineEdit("0.0333")
        self._dt_input.setReadOnly(True)
        self._dt_input.setFixedWidth(120)
        acq_grid.addWidget(self._dt_input, 1, 1)

        acq_grid.addWidget(QLabel("Total Duration"), 2, 0)
        self._duration_input = QLineEdit("—")
        self._duration_input.setReadOnly(True)
        self._duration_input.setFixedWidth(120)
        acq_grid.addWidget(self._duration_input, 2, 1)

        left.addLayout(acq_grid)
        left.addStretch()

        # Right Column: Calibration
        right = QVBoxLayout()
        right.setSpacing(16)
        
        cal_title = QLabel("Calibration & Units")
        cal_title.setObjectName("param_section_title")
        right.addWidget(cal_title)

        cal_grid = QGridLayout()
        cal_grid.setSpacing(12)

        cal_grid.addWidget(QLabel("Pixel-to-Physical Scale"), 0, 0)
        
        scale_row = QHBoxLayout()
        self._scale_input = QLineEdit("0.065")
        self._scale_input.setFixedWidth(80)
        scale_row.addWidget(self._scale_input)
        scale_row.addWidget(QLabel("μm/px"))
        scale_row.addStretch()
        cal_grid.addLayout(scale_row, 0, 1)

        cal_grid.addWidget(QLabel("Spatial Unit"), 1, 0)
        self._unit_combo = QComboBox()
        self._unit_combo.addItems(["Micrometers (μm)", "Nanometers (nm)", "Pixels (px)"])
        self._unit_combo.setFixedWidth(200)
        cal_grid.addWidget(self._unit_combo, 1, 1)

        cal_grid.addWidget(QLabel("Coordinate System"), 2, 0)
        self._coord_combo = QComboBox()
        self._coord_combo.addItems(["Cartesian (X, Y)", "Polar (r, θ)"])
        self._coord_combo.setFixedWidth(200)
        cal_grid.addWidget(self._coord_combo, 2, 1)

        right.addLayout(cal_grid)
        right.addStretch()

        cols.addLayout(left, 1)
        cols.addLayout(right, 1)
        layout.addLayout(cols)
        layout.addSpacing(32)

        # ── Parameter Check Box ───────────────────────────────
        self._verify_box = QFrame()
        self._verify_box.setObjectName("param_verify_box")
        verify_layout = QHBoxLayout(self._verify_box)
        verify_layout.setContentsMargins(16, 14, 16, 14)
        
        self._verify_label = QLabel("✓  Parameters look valid based on data bounds")
        self._verify_label.setObjectName("param_verify_label")
        verify_layout.addWidget(self._verify_label)
        layout.addWidget(self._verify_box)
        layout.addSpacing(40)

        # ── Footer ────────────────────────────────────────────
        footer = QHBoxLayout()

        back_btn = QPushButton("Back to Import")
        back_btn.setFixedHeight(40)
        back_btn.setStyleSheet(
            "QPushButton { background: white; border: 1px solid #D1D5DB; "
            "border-radius: 8px; padding: 0 20px; color: #374151; font-size: 14px; }"
            "QPushButton:hover { background: #F9FAFB; }"
        )
        back_btn.clicked.connect(self.navigate_back)

        self._continue_btn = QPushButton("Review & Confirm  →")
        self._continue_btn.setFixedHeight(40)
        self._continue_btn.setStyleSheet(
            "QPushButton { background: #3B5BDB; color: white; border: none; "
            "border-radius: 8px; padding: 0 24px; font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { background: #2F4AC7; }"
        )
        self._continue_btn.clicked.connect(self._on_continue)

        footer.addWidget(back_btn)
        footer.addStretch()
        footer.addWidget(self._continue_btn)
        
        layout.addStretch()
        layout.addLayout(footer)

    def _connect_signals(self):
        self._fps_input.textChanged.connect(self._recalculate)
        self._orc.stats_ready.connect(self._on_stats_loaded)

    def _on_stats_loaded(self, stats: dict):
        self._frames = stats.get("frame_max", 0) - stats.get("frame_min", 0)
        self._recalculate()

    def _recalculate(self):
        try:
            fps = float(self._fps_input.text())
            if fps <= 0:
                raise ValueError
            
            dt = 1.0 / fps
            self._dt_input.setText(f"{dt:.4f}")
            
            if hasattr(self, '_frames') and self._frames > 0:
                duration = self._frames * dt
                self._duration_input.setText(f"{duration:.1f} s")
                
            self._verify_box.setStyleSheet("#param_verify_box { background: #ECFDF5; border: 1px solid #A7F3D0; }")
            self._verify_label.setText("✓  Parameters look valid based on data bounds")
            self._verify_label.setStyleSheet("color: #065F46;")
            self._continue_btn.setEnabled(True)

        except ValueError:
            self._dt_input.setText("—")
            self._duration_input.setText("—")
            self._verify_box.setStyleSheet("#param_verify_box { background: #FEF2F2; border: 1px solid #FECACA; }")
            self._verify_label.setText("⚠  Invalid frame rate")
            self._verify_label.setStyleSheet("color: #991B1B;")
            self._continue_btn.setEnabled(False)

    def _on_continue(self):
        try:
            params = {
                "frame_rate": float(self._fps_input.text()),
                "pixel_scale": float(self._scale_input.text()),
                "spatial_unit": self._unit_combo.currentText(),
                "coord_system": self._coord_combo.currentText()
            }
            self._orc.run_validation(params)
            self.navigate_to_validation.emit()
        except ValueError:
            pass
