"""
ui/widgets/sidebar.py
Left sidebar: logo, search bar, recent projects list.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QPixmap, QPainter, QColor, QPainterPath


class ProjectItemWidget(QWidget):
    clicked = Signal(dict)

    def __init__(self, project: dict, parent=None):
        super().__init__(parent)
        self._project = project
        self.setObjectName("project_item")
        self.setCursor(Qt.PointingHandCursor)
        self._build(project)

    def _build(self, project: dict):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(10)

        # Icon thumbnail (colored square)
        icon = QLabel()
        icon.setFixedSize(36, 36)
        icon.setStyleSheet(
            "background-color: #2A3A6E; border-radius: 6px;"
        )
        icon.setAlignment(Qt.AlignCenter)
        icon.setText("📊")

        # Name + meta
        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        name = project.get("name", "Untitled")
        name_label = QLabel(name[:22] + "…" if len(name) > 22 else name)
        name_label.setObjectName("project_name_label")
        name_label.setFont(QFont("Inter", 12, QFont.Medium))

        created = project.get("created_at", "")[:10]
        meta_label = QLabel(created)
        meta_label.setObjectName("project_meta_label")

        text_col.addWidget(name_label)
        text_col.addWidget(meta_label)

        layout.addWidget(icon)
        layout.addLayout(text_col)
        layout.addStretch()

    def mousePressEvent(self, event):
        self.clicked.emit(self._project)
        super().mousePressEvent(event)


class Sidebar(QWidget):
    project_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(200)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(0)

        # ── Logo ──────────────────────────────────────────────
        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)

        logo_icon = QLabel("⬛")
        logo_icon.setFixedSize(36, 36)
        logo_icon.setAlignment(Qt.AlignCenter)
        logo_icon.setStyleSheet(
            "background-color: #2F9E44; border-radius: 8px; color: white; font-size: 16px;"
        )

        app_name = QLabel("App Name")
        app_name.setObjectName("app_name_label")
        app_name.setFont(QFont("Inter", 17, QFont.Bold))

        logo_row.addWidget(logo_icon)
        logo_row.addWidget(app_name)
        logo_row.addStretch()

        layout.addLayout(logo_row)
        layout.addSpacing(24)

        # ── Search ────────────────────────────────────────────
        self._search = QLineEdit()
        self._search.setObjectName("search_bar")
        self._search.setPlaceholderText("🔍  Search projects...")
        self._search.setFixedHeight(36)
        layout.addWidget(self._search)
        layout.addSpacing(20)

        # ── Recent Projects label ─────────────────────────────
        section = QLabel("RECENT PROJECTS")
        section.setObjectName("section_label")
        section.setFont(QFont("Inter", 10, QFont.Bold))
        layout.addWidget(section)
        layout.addSpacing(8)

        # ── Scrollable project list ───────────────────────────
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(self._list_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background: transparent;")

        layout.addWidget(scroll, 1)

    def populate_projects(self, projects: list):
        """Populate the sidebar with recent projects."""
        # Clear existing items (except stretch)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for project in projects:
            item = ProjectItemWidget(project)
            item.clicked.connect(self.project_selected)
            self._list_layout.insertWidget(self._list_layout.count() - 1, item)
