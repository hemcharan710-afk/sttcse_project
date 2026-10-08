"""
ui/pages/data_mapping_page.py
Screen 4: Data Import & Mapping — schema preview + column mapping dropdowns.
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QFrame, QHeaderView, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class DataMappingPage(QWidget):
    navigate_to_params = Signal()
    navigate_back      = Signal()

    def __init__(self, orchestrator, parent=None):
        super().__init__(parent)
        self._orc      = orchestrator
        self._schema   = {}
        self._stats    = {}
        self._build()
        self._connect()

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
        title = QLabel("Data Import & Mapping")
        title.setObjectName("page_title")
        title.setFont(QFont("Inter", 30, QFont.Bold))
        layout.addWidget(title)
        layout.addSpacing(6)

        subtitle = QLabel("Verify the auto-detected schema and map the columns required.")
        subtitle.setObjectName("page_subtitle")
        layout.addWidget(subtitle)
        layout.addSpacing(20)

        # ── File badge ────────────────────────────────────────
        self._file_badge = QFrame()
        self._file_badge.setObjectName("file_badge")
        self._file_badge.setStyleSheet(
            "#file_badge { background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 8px; padding: 10px 16px; }"
        )
        badge_layout = QHBoxLayout(self._file_badge)
        badge_layout.setContentsMargins(12, 8, 12, 8)

        self._file_name_label = QLabel("—")
        self._file_name_label.setStyleSheet("color: #065F46; font-weight: 600; font-size: 13px;")

        change_btn = QPushButton("Change File")
        change_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; "
            "color: #3B5BDB; font-size: 13px; font-weight: 600; }"
            "QPushButton:hover { text-decoration: underline; }"
        )
        change_btn.clicked.connect(self.navigate_back)

        badge_layout.addWidget(QLabel("✅"))
        badge_layout.addWidget(self._file_name_label)
        badge_layout.addStretch()
        badge_layout.addWidget(change_btn)
        layout.addWidget(self._file_badge)
        layout.addSpacing(24)

        # ── Schema preview + mapping ──────────────────────────
        two_col = QHBoxLayout()
        two_col.setSpacing(24)

        # Left: schema preview table
        left = QVBoxLayout()
        left.setSpacing(10)

        schema_label = QLabel("SCHEMA PREVIEW")
        schema_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #6B7280; letter-spacing: 1px;")
        left.addWidget(schema_label)

        self._table = QTableWidget(0, 4)
        self._table.setObjectName("schema_table")
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False) # Hide the row numbers
        self._table.setShowGrid(False) # Hide grid for cleaner look
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        self._table.setFixedHeight(200)
        left.addWidget(self._table)
        left.addStretch()

        # Right: required fields mapping
        right = QVBoxLayout()
        right.setSpacing(10)

        map_label = QLabel("MAP REQUIRED FIELDS")
        map_label.setStyleSheet("font-size: 11px; font-weight: 700; color: #6B7280; letter-spacing: 1px;")
        right.addWidget(map_label)

        map_box = QFrame()
        map_box.setStyleSheet(
            "QFrame { background: white; border: 1px solid #E5E7EB; border-radius: 10px; padding: 8px; }"
        )
        map_box_layout = QVBoxLayout(map_box)
        map_box_layout.setSpacing(12)

        self._combos = {}
        for field_key, label in [
            ("particle_id", "Particle ID"),
            ("frame",       "Frame ID"),
            ("x",           "X Position"),
            ("y",           "Y Position"),
        ]:
            row = QHBoxLayout()

            # Green indicator bar matching the mockup
            indicator = QFrame()
            indicator.setFixedSize(4, 16)
            indicator.setStyleSheet("background-color: #2F9E44; border-radius: 2px;")
            
            check_box = QHBoxLayout()
            check_box.setContentsMargins(0,0,0,0)
            check_box.addWidget(indicator)
            check_box.setAlignment(Qt.AlignCenter)
            
            indicator_container = QWidget()
            indicator_container.setFixedWidth(24)
            indicator_container.setLayout(check_box)

            lbl = QLabel(label)
            lbl.setFixedWidth(100)
            lbl.setStyleSheet("font-weight: 600; font-size: 13px; color: #374151;")

            arrow = QLabel("→")
            arrow.setFixedWidth(20)
            arrow.setStyleSheet("color: #6B7280;")

            combo = QComboBox()
            combo.setFixedHeight(34)
            combo.currentTextChanged.connect(self._check_mapping_complete)
            self._combos[field_key] = combo

            row.addWidget(indicator_container)
            row.addWidget(lbl)
            row.addWidget(arrow)
            row.addWidget(combo, 1)
            map_box_layout.addLayout(row)

        right.addWidget(map_box)
        right.addStretch()

        two_col.addLayout(left, 3)
        two_col.addLayout(right, 2)
        layout.addLayout(two_col)
        layout.addSpacing(24)

        # ── Dataset stats ──────────────────────────────────────
        self._stats_row = QHBoxLayout()
        self._stats_row.setSpacing(12)
        layout.addLayout(self._stats_row)
        layout.addSpacing(32)

        # ── Footer ─────────────────────────────────────────────
        footer = QHBoxLayout()

        back_btn = QPushButton("Back")
        back_btn.setFixedHeight(40)
        back_btn.setStyleSheet(
            "QPushButton { background: white; border: 1px solid #D1D5DB; "
            "border-radius: 8px; padding: 0 20px; color: #374151; font-size: 14px; }"
            "QPushButton:hover { background: #F9FAFB; }"
        )
        back_btn.clicked.connect(self.navigate_back)

        self._all_mapped_label = QLabel("")
        self._all_mapped_label.setStyleSheet("color: #2F9E44; font-size: 13px;")

        self._continue_btn = QPushButton("Continue to Parameters  →")
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
        footer.addWidget(self._all_mapped_label)
        footer.addSpacing(16)
        footer.addWidget(self._continue_btn)
        layout.addLayout(footer)

    def _connect(self):
        self._orc.schema_ready.connect(self._on_schema_loaded)
        self._orc.stats_ready.connect(self._on_stats_loaded)

    def _on_schema_loaded(self, schema: dict):
        self._schema = schema

        # Update file badge
        filename = schema.get("filename", "")
        size_str = schema.get("file_size_str", "")
        self._file_name_label.setText(f"{filename}    ({size_str})")

        # Populate schema preview table
        columns = schema.get("columns", [])
        sample  = schema.get("sample_rows", [])
        col_names = [c["name"] for c in columns]

        self._table.setColumnCount(min(len(col_names), 4))
        self._table.setHorizontalHeaderLabels(col_names[:4])

        # Type labels in header (sub-header style)
        for i, col in enumerate(columns[:4]):
            self._table.horizontalHeaderItem(i).setToolTip(col["type"])

        self._table.setRowCount(min(len(sample), 4))
        for row_i, row_data in enumerate(sample[:4]):
            for col_i, col in enumerate(col_names[:4]):
                val = str(row_data.get(col, ""))
                self._table.setItem(row_i, col_i, QTableWidgetItem(val))

        # Populate dropdowns
        for combo in self._combos.values():
            combo.clear()
            combo.addItem("")
            for col_name in col_names:
                combo.addItem(col_name)

        # Auto-detect common column names
        auto_map = {
            "particle_id": ["particle", "particle_id", "id", "track_id"],
            "frame":       ["frame", "t", "time", "frame_id"],
            "x":           ["x", "x_pos", "pos_x", "x_coord"],
            "y":           ["y", "y_pos", "pos_y", "y_coord"],
        }
        for field_key, candidates in auto_map.items():
            for candidate in candidates:
                if candidate in col_names:
                    self._combos[field_key].setCurrentText(candidate)
                    break

        self._check_mapping_complete()

    def _on_stats_loaded(self, stats: dict):
        self._stats = stats
        self._refresh_stat_cards(stats)

    def _refresh_stat_cards(self, stats: dict):
        while self._stats_row.count():
            item = self._stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cards = [
            (str(stats.get("n_particles", "—")),    "Particles",     "🎯"),
            (f"{stats.get('n_observations', '—'):,}", "Observations", "📊"),
            (stats.get("frame_range", "—"),          "Frame Range",   "⏱"),
            (str(stats.get("n_columns", "—")),       "Columns\nDetected", "📋"),
        ]
        for val, lbl, icon in cards:
            card = QFrame()
            card.setStyleSheet(
                "QFrame { background: white; border: 1px solid #E5E7EB; "
                "border-radius: 12px; padding: 20px; min-width: 160px; }"
            )
            cl = QVBoxLayout(card)
            cl.setSpacing(6)
            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet("font-size: 24px;")
            num_lbl = QLabel(val)
            num_lbl.setStyleSheet("font-size: 24px; font-weight: 700; color: #1A1D2E;")
            txt_lbl = QLabel(lbl)
            txt_lbl.setStyleSheet("font-size: 13px; color: #6B7280;")
            cl.addWidget(icon_lbl)
            cl.addWidget(num_lbl)
            cl.addWidget(txt_lbl)
            self._stats_row.addWidget(card)

        self._stats_row.addStretch()

    def _check_mapping_complete(self):
        all_mapped = all(
            self._combos[k].currentText() != ""
            for k in self._combos
        )
        self._continue_btn.setEnabled(all_mapped)
        if all_mapped:
            self._all_mapped_label.setText("✓  All required fields mapped")
        else:
            self._all_mapped_label.setText("")

        # Load stats when mapping is complete
        if all_mapped:
            column_map = {k: self._combos[k].currentText() for k in self._combos}
            self._orc.load_stats(column_map)

    def _on_continue(self):
        column_map = {k: self._combos[k].currentText() for k in self._combos}
        self._orc.column_map = column_map
        self.navigate_to_params.emit()

    def showEvent(self, event):
        # If schema already loaded (coming back), refresh
        if self._schema:
            self._on_schema_loaded(self._schema)
        super().showEvent(event)
