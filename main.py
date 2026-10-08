import sys
import os
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    # Make sure we can import from core, models, ui, etc.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    app = QApplication(sys.argv)
    
    # Initialize the main window
    window = MainWindow()
    
    # Load stylesheet
    window.load_stylesheet()
    
    # Show window
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
