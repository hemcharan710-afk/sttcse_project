"""
ui/dialogs/drift_dialog.py
Screen 7: Drift Correction Modal.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class DriftDialog(QDialog):
    
    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self._orc = orchestrator
        self.setModal(True)
        self.setFixedSize(800, 600)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._build()
        self._connect_signals()
        
        # Start correction process when opened (we calculate the plots on the fly for now)
        self._set_loading(True)
        out_path = self._orc.current_filepath.replace(".parquet", "_corrected.parquet")
        self._orc.apply_drift_correction(out_path, frames_per_window=500)

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
        
        icon = QLabel("⚠")
        icon.setStyleSheet("color: #F59F00; font-size: 24px; font-weight: bold;")
        header.addWidget(icon)
        
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        
        sup = QLabel("POSSIBLE DRIFT")
        sup.setStyleSheet("color: #F59F00; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        title = QLabel("Correct directional drift")
        title.setObjectName("modal_title")
        
        title_col.addWidget(sup)
        title_col.addWidget(title)
        
        header.addLayout(title_col)
        header.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(
            "QPushButton { background: white; border: 1px solid #D1D5DB; "
            "border-radius: 16px; color: #6B7280; font-size: 13px; }"
            "QPushButton:hover { background: #F3F4F6; }"
        )
        close_btn.clicked.connect(self.reject)
        header.addWidget(close_btn)
        
        card_layout.addLayout(header)
        
        desc = QLabel(
            "A directional bias was detected that may indicate stage drift or fluid flow. "
            "Applying correction will subtract the local mean displacement from all trajectories."
        )
        desc.setStyleSheet("color: #4B5563; font-size: 13px;")
        desc.setWordWrap(True)
        card_layout.addWidget(desc)
        card_layout.addSpacing(12)

        # ── Loading State ─────────────────────────────────────
        self._loading_lbl = QLabel("Calculating drift windows... Please wait.")
        self._loading_lbl.setAlignment(Qt.AlignCenter)
        self._loading_lbl.setStyleSheet("color: #6B7280; font-size: 14px;")
        card_layout.addWidget(self._loading_lbl)

        # ── Plot Area ─────────────────────────────────────────
        self._plot_area = QWidget()
        plot_layout = QHBoxLayout(self._plot_area)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.setSpacing(16)
        
        # We will populate these canvases once drift_done is emitted
        self._canvas_before = None
        self._canvas_after = None
        
        card_layout.addWidget(self._plot_area, 1)

        # ── Info Row ──────────────────────────────────────────
        self._info_row = QFrame()
        self._info_row.setStyleSheet(
            "QFrame { background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 8px; }"
        )
        info_layout = QHBoxLayout(self._info_row)
        info_layout.setContentsMargins(16, 12, 16, 12)
        
        self._estimator_lbl = QLabel("Estimator: <b>Local Window (500 frames)</b>")
        self._vector_lbl = QLabel("Drift Vector: <b>—</b>")
        self._applied_lbl = QLabel("Applied To: <b>—</b>")
        
        for lbl in (self._estimator_lbl, self._vector_lbl, self._applied_lbl):
            lbl.setStyleSheet("color: #374151; font-size: 12px;")
            info_layout.addWidget(lbl)
            
        card_layout.addWidget(self._info_row)
        
        # ── Blue Note ─────────────────────────────────────────
        note = QLabel("ℹ  Raw data will be preserved. A new dataset will be generated for the analysis.")
        note.setStyleSheet("color: #1D4ED8; background: #DBEAFE; border-radius: 6px; padding: 10px; font-size: 12px;")
        card_layout.addWidget(note)
        
        card_layout.addStretch()

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #E5E7EB;")
        card_layout.addWidget(line)

        # ── Footer ────────────────────────────────────────────
        footer = QHBoxLayout()

        self._btn_ignore = QPushButton("Continue with original data")
        self._btn_ignore.setFixedHeight(40)
        self._btn_ignore.setStyleSheet(
            "QPushButton { background: white; border: 1px solid #D1D5DB; "
            "border-radius: 8px; padding: 0 20px; color: #374151; font-size: 14px; }"
            "QPushButton:hover { background: #F9FAFB; }"
        )
        self._btn_ignore.clicked.connect(self.reject)

        self._btn_apply = QPushButton("Calculate & subtract drift  →")
        self._btn_apply.setFixedHeight(40)
        self._btn_apply.setEnabled(False)
        self._btn_apply.setStyleSheet(
            "QPushButton { background: #2F9E44; color: white; border: none; "
            "border-radius: 8px; padding: 0 24px; font-size: 14px; font-weight: 600; }"
            "QPushButton:hover { background: #268A3A; }"
            "QPushButton:disabled { background: #8CE99A; }"
        )
        self._btn_apply.clicked.connect(self.accept)

        footer.addStretch()
        footer.addWidget(self._btn_ignore)
        footer.addWidget(self._btn_apply)
        card_layout.addLayout(footer)

        outer.addWidget(card)

    def _set_loading(self, is_loading: bool):
        self._loading_lbl.setVisible(is_loading)
        self._plot_area.setVisible(not is_loading)
        self._info_row.setVisible(not is_loading)
        
    def _connect_signals(self):
        self._orc.drift_done.connect(self._on_drift_done)
        self._orc.progress_update.connect(self._on_progress)
        
    def _on_progress(self, pct: int, msg: str):
        self._loading_lbl.setText(f"{msg} ({pct}%)")

    def _on_drift_done(self, result: dict):
        self._set_loading(False)
        
        fig_before = result.get("before_figure")
        fig_after = result.get("after_figure")
        
        if fig_before and fig_after:
            self._canvas_before = FigureCanvasQTAgg(fig_before)
            self._canvas_after = FigureCanvasQTAgg(fig_after)
            
            self._plot_area.layout().addWidget(self._canvas_before)
            self._plot_area.layout().addWidget(self._canvas_after)
            
        vector = result.get("drift_vector", (0.0, 0.0))
        n_obs = result.get("n_observations", 0)
        
        self._vector_lbl.setText(f"Drift Vector: <b>({vector[0]}, {vector[1]}) px/frame</b>")
        self._applied_lbl.setText(f"Applied To: <b>{n_obs:,} observations</b>")
        
        self._btn_apply.setText("Use corrected data  →")
        self._btn_apply.setEnabled(True)
