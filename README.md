# Particle Trajectory Analysis Toolkit

A professional, high-performance desktop application for analyzing and visualizing particle trajectory simulations. Built with Python and PySide6 (Qt), this toolkit allows researchers and scientists to ingest massive trajectory datasets, validate coordinates, and compute physical metrics such as Mean Squared Displacement (MSD), Non-Gaussian Parameter (NGP), Self-van-Hove Histograms, and Pair Correlation Functions.

## Features

- **Large File Support**: Safely parses metadata from massive datasets (like 1GB+ Parquet files) without freezing the UI.
- **Automated Data Validation**: Scans for duplicate observations, missing particle IDs, and anomalous frame jumps.
- **Background Processing**: Heavy mathematical computations (like lag-time analysis) are offloaded to background threads.
- **Dynamic Visualizations**: View your results interactively with auto-scaling log-log and linear plots.
- **Export Capabilities**: Save generated plots as PNG or SVG, and export raw calculated arrays as CSV files for publication.

## Prerequisites

- macOS (or Windows/Linux)
- Python 3.9 or higher

## Installation & Setup

1. **Open your Terminal** and navigate to the project directory:
   ```bash
   cd path/to/sttcse_ui/sttcse_project
   ```

2. **Install the required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: It is highly recommended to do this inside a virtual environment!)*

## Running the Application

To launch the desktop application, simply run the main script from the root of the project:

```bash
python3 main.py
```

## How to use

1. **Welcome Screen**: Click **Open Project** and select a `.parquet` trajectory dataset (e.g., from your `data_samples` folder).
2. **Data Mapping**: Verify that the application correctly auto-detected your columns for Particle ID, Frame ID, X Position, and Y Position. 
3. **Parameters**: Define your experimental constraints, such as Frames Per Second (fps) and pixel-to-micrometer calibration.
4. **Validation**: The engine will parse the dataset and alert you to any trajectory discontinuities or severe drift.
5. **Visualization**: Select a metric (e.g., MSD) from the dropdown. The application will compute the metric across the frames and display the results interactively.

## Code Structure

- **`main.py`**: The entry point of the application.
- **`ui/`**: Contains the front-end layout, PySide6 widgets, styling (`theme.qss`), and screen definitions.
- **`orchestrator.py`**: The bridge that handles communication between the UI and the heavy background math operations.
- **`analysis_engine.py`**: The core data science backend that processes PyArrow/Pandas DataFrames and computes physics metrics.
