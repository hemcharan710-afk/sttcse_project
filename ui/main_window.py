"""
ui/main_window.py
QMainWindow: sidebar + stacked content area.
Handles page navigation and global state.
"""

import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QStackedWidget, QApplication
)
from PySide6.QtCore import Qt

from ui.widgets.sidebar import Sidebar
from ui.pages.home_page import HomePage
from ui.pages.data_mapping_page import DataMappingPage
from ui.pages.parameters_page import ParametersPage
from ui.pages.validation_page import ValidationPage
from ui.pages.visualization_page import VisualizationPage

from orchestrator import Orchestrator
from core import metadata_store


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Particle Trajectory Analysis Toolkit")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 780)

        # Init DB
        metadata_store.init_db()

        # Orchestrator (shared across all pages)
        self.orchestrator = Orchestrator(self)

        self._build_ui()
        self._connect_signals()
        self._refresh_sidebar()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        root.addWidget(self.sidebar)

        # Stacked pages
        self.stack = QStackedWidget()
        self.stack.setObjectName("content_area")
        root.addWidget(self.stack, 1)

        # Create pages
        self.home_page       = HomePage(self.orchestrator)
        self.mapping_page    = DataMappingPage(self.orchestrator)
        self.params_page     = ParametersPage(self.orchestrator)
        self.validation_page = ValidationPage(self.orchestrator)
        self.viz_page        = VisualizationPage(self.orchestrator)

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.mapping_page)
        self.stack.addWidget(self.params_page)
        self.stack.addWidget(self.validation_page)
        self.stack.addWidget(self.viz_page)

    def _connect_signals(self):
        # Navigation signals from pages
        self.home_page.navigate_to_mapping.connect(lambda: self.go_to("mapping"))
        self.mapping_page.navigate_to_params.connect(lambda: self.go_to("params"))
        self.params_page.navigate_to_validation.connect(lambda: self.go_to("validation"))
        self.validation_page.navigate_to_viz.connect(lambda: self.go_to("viz"))
        self.viz_page.navigate_home.connect(lambda: self.go_to("home"))

        # Back navigation
        self.mapping_page.navigate_back.connect(lambda: self.go_to("home"))
        self.params_page.navigate_back.connect(lambda: self.go_to("mapping"))
        self.validation_page.navigate_back.connect(lambda: self.go_to("params"))

        # Sidebar project click → jump to visualization
        self.sidebar.project_selected.connect(self._on_project_selected)

        # Global error handling
        self.orchestrator.error_occurred.connect(self._show_error)

    def _show_error(self, err_msg: str):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(self, "Error", f"An error occurred in the background:\n\n{err_msg}")

    def go_to(self, page: str):
        pages = {
            "home":       self.home_page,
            "mapping":    self.mapping_page,
            "params":     self.params_page,
            "validation": self.validation_page,
            "viz":        self.viz_page,
        }
        if page in pages:
            self.stack.setCurrentWidget(pages[page])

    def _on_project_selected(self, project: dict):
        """Clicking a sidebar project jumps to visualization with that project's data."""
        dataset_path = project.get("dataset_path", "")
        if dataset_path and os.path.exists(dataset_path):
            self.orchestrator.current_filepath = dataset_path
            self.go_to("viz")
        else:
            self.go_to("home")

    def _refresh_sidebar(self):
        projects = metadata_store.get_recent_projects()
        self.sidebar.populate_projects(projects)

    def load_stylesheet(self):
        qss_path = os.path.join(
            os.path.dirname(__file__), "style", "theme.qss"
        )
        if os.path.exists(qss_path):
            with open(qss_path, "r") as f:
                QApplication.instance().setStyleSheet(f.read())
