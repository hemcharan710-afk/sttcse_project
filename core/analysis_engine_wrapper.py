"""
core/analysis_engine_wrapper.py
Wraps analysis_engine.py so it can be called from the UI without blocking
or popping up matplotlib windows.
"""

import sys
import os
import matplotlib

# Force non-interactive backend to prevent plt.show() from opening windows
matplotlib.use("Agg")

import matplotlib.pyplot as plt

# We must ensure the sttcse_project directory is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import analysis_engine as _engine


def disable_plots(func):
    """Decorator to temporarily disable plt.show and plt.savefig during execution."""
    def wrapper(*args, **kwargs):
        original_show = plt.show
        original_savefig = plt.savefig
        plt.show = lambda *a, **kw: None
        plt.savefig = lambda *a, **kw: None
        
        try:
            return func(*args, **kwargs)
        finally:
            plt.show = original_show
            plt.savefig = original_savefig
            # Close any figures created to prevent memory leaks
            plt.close("all")
            
    return wrapper


@disable_plots
def run_analysis(filepath: str, params: dict):
    """
    Runs the lag metrics computation from analysis_engine.py.
    Overrides module constants with user parameters.
    """
    _engine.FILE = filepath
    _engine.FRAME_RATE_HZ = params.get("frame_rate", 30.0)
    _engine.PIXELS_PER_MICRON = params.get("pixel_scale", 1.0)
    _engine.FRAME_INTERVAL_SEC = 1.0 / _engine.FRAME_RATE_HZ
    
    # Run the lag metrics (this computes MSD, NGP, Van Hove and writes CSVs)
    _engine.calculate_lag_metrics()
    
    # Also run pair correlation just so it creates the CSV if needed
    _engine.calculate_pair_correlation()
