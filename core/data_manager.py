"""
core/data_manager.py
Wraps schema inspection logic from explore_data.py.
Math: UNTOUCHED — same PyArrow batch-reading logic.
Only change: returns dicts instead of printing.
"""

import os
import pyarrow.parquet as pq
import numpy as np
from collections import Counter


def inspect_schema(filepath: str) -> dict:
    """
    Inspect the schema of a Parquet file without loading all data.

    Returns:
        {
            "columns": [{"name": str, "type": str}, ...],
            "n_rows": int,
            "n_row_groups": int,
            "file_size_gb": float,
            "sample_rows": list[dict]   # first 5 rows for preview
        }
    """
    pf = pq.ParquetFile(filepath)

    columns = [
        {"name": field.name, "type": str(field.type)}
        for field in pf.schema_arrow
    ]

    n_rows = pf.metadata.num_rows
    n_row_groups = pf.num_row_groups
    file_size_gb = os.path.getsize(filepath) / (1024 ** 3)

    # Read first small batch for preview table
    sample_rows = []
    for batch in pf.iter_batches(batch_size=5):
        df = batch.to_pandas()
        sample_rows = df.head(5).to_dict(orient="records")
        break

    return {
        "columns": columns,
        "n_rows": n_rows,
        "n_row_groups": n_row_groups,
        "file_size_gb": file_size_gb,
        "file_size_str": f"{file_size_gb:.2f} GB",
        "sample_rows": sample_rows,
        "filepath": filepath,
        "filename": os.path.basename(filepath),
    }


def get_dataset_stats(filepath: str, column_map: dict) -> dict:
    """
    Compute basic stats using the user-defined column mapping.
    Same batch-reading approach as explore_data.py — math untouched.

    column_map: {
        "particle_id": "particle",
        "frame":       "frame",
        "x":           "x",
        "y":           "y"
    }

    Returns:
        {
            "n_particles": int,
            "n_observations": int,
            "frame_min": int,
            "frame_max": int,
            "n_columns": int,
            "missing": {"particle_id": int, "frame": int, "x": int, "y": int}
        }
    """
    particle_col = column_map.get("particle_id", "particle")
    frame_col    = column_map.get("frame",       "frame")
    x_col        = column_map.get("x",           "x")
    y_col        = column_map.get("y",           "y")

    required_cols = [particle_col, frame_col, x_col, y_col]

    pf = pq.ParquetFile(filepath)

    # --- same logic as explore_data.py ---
    unique_particles = set()
    frame_counts     = Counter()
    total_rows       = 0
    missing          = {c: 0 for c in required_cols}

    for batch in pf.iter_batches(batch_size=100_000, columns=required_cols):
        df = batch.to_pandas()
        total_rows += len(df)

        unique_particles.update(df[particle_col].dropna().unique())
        frame_counts.update(df[frame_col].dropna())

        for col in required_cols:
            if col in df.columns:
                missing[col] += int(df[col].isna().sum())

    frame_min = int(min(frame_counts.keys())) if frame_counts else 0
    frame_max = int(max(frame_counts.keys())) if frame_counts else 0

    return {
        "n_particles":    len(unique_particles),
        "n_observations": total_rows,
        "frame_min":      frame_min,
        "frame_max":      frame_max,
        "frame_range":    f"{frame_min} – {frame_max}",
        "n_columns":      pf.metadata.num_columns,
        "missing":        {
            "particle_id": missing[particle_col],
            "frame":       missing[frame_col],
            "x":           missing[x_col],
            "y":           missing[y_col],
        },
    }
