"""
core/preprocessor.py
Wraps shift_correction.py into a callable function.
Math: UNTOUCHED — same two-pass drift correction algorithm.
Only changes: parameters passed in, plt.show() removed, figures returned.
"""

import os
import pyarrow.parquet as pq
import pyarrow as pa
import numpy as np
import matplotlib
matplotlib.use("Agg")   # non-interactive backend — no pop-up windows
import matplotlib.pyplot as plt


def apply_drift_correction(
    filepath: str,
    output_filepath: str,
    column_map: dict,
    frames_per_window: int = 500,
    progress_callback=None,
) -> dict:
    """
    Runs the exact same shift correction algorithm from shift_correction.py.
    Math is untouched — only wrapped into a callable function.

    Args:
        filepath:          path to input parquet
        output_filepath:   path to write corrected parquet
        column_map:        {"particle_id": "particle", "frame": "frame", "x": "x", "y": "y"}
        frames_per_window: drift window size (default 500, same as original script)
        progress_callback: optional fn(percent: int, message: str)

    Returns: {
        "mean_dx": float,
        "mean_dy": float,
        "output_file": str,
        "before_figure": matplotlib.figure.Figure,
        "after_figure":  matplotlib.figure.Figure,
        "drift_vector":  (float, float),
        "n_observations": int,
    }
    """
    particle_col = column_map.get("particle_id", "particle")
    frame_col    = column_map.get("frame",       "frame")
    x_col        = column_map.get("x",           "x")
    y_col        = column_map.get("y",           "y")

    row_batch_size = 100_000

    pf = pq.ParquetFile(filepath)
    total_rows = pf.metadata.num_rows

    # ----------------------------------------------------------------
    # Determine max_frame for array allocation
    # ----------------------------------------------------------------
    max_frame = 0
    for batch in pf.iter_batches(batch_size=row_batch_size, columns=[frame_col]):
        batch_max = int(batch.column(frame_col).to_numpy().max())
        if batch_max > max_frame:
            max_frame = batch_max

    if progress_callback:
        progress_callback(5, "Calculated frame range...")

    # ----------------------------------------------------------------
    # PASS 1 — same algorithm as shift_correction.py
    # Calculate frame-to-frame drift
    # ----------------------------------------------------------------
    sum_dx    = np.zeros(max_frame + 1, dtype=np.float64)
    sum_dy    = np.zeros(max_frame + 1, dtype=np.float64)
    count_arr = np.zeros(max_frame + 1, dtype=np.int64)
    previous  = {}

    pf = pq.ParquetFile(filepath)
    for batch_num, batch in enumerate(
        pf.iter_batches(batch_size=row_batch_size, columns=[particle_col, frame_col, x_col, y_col]),
        start=1
    ):
        data      = batch.to_pydict()
        particles = data[particle_col]
        frames    = data[frame_col]
        xs        = data[x_col]
        ys        = data[y_col]

        for particle, frame, x, y in zip(particles, frames, xs, ys):
            particle = int(particle)
            frame    = int(frame)
            x        = float(x)
            y        = float(y)

            if particle in previous:
                prev_frame, prev_x, prev_y = previous[particle]
                if frame - prev_frame == 1:
                    dx = x - prev_x
                    dy = y - prev_y
                    sum_dx[frame]    += dx
                    sum_dy[frame]    += dy
                    count_arr[frame] += 1

            previous[particle] = (frame, x, y)

        if progress_callback:
            pct = 5 + int(35 * batch_num / max(1, total_rows // row_batch_size))
            progress_callback(pct, f"Pass 1: batch {batch_num}...")

    valid       = count_arr > 0
    mean_dx     = np.where(valid, sum_dx / np.maximum(count_arr, 1), 0.0)
    mean_dy     = np.where(valid, sum_dy / np.maximum(count_arr, 1), 0.0)
    global_mean_dx = float(np.mean(mean_dx[valid]))
    global_mean_dy = float(np.mean(mean_dy[valid]))

    if progress_callback:
        progress_callback(40, "Pass 1 complete. Computing local drift windows...")

    # ----------------------------------------------------------------
    # Local drift window estimation — same as shift_correction.py
    # ----------------------------------------------------------------
    frame_ids    = np.arange(max_frame + 1)
    n_windows    = max(1, (max_frame + 1) // frames_per_window)
    local_cum_dx = np.zeros(max_frame + 1, dtype=np.float64)
    local_cum_dy = np.zeros(max_frame + 1, dtype=np.float64)

    for w in range(n_windows):
        f_start = w * frames_per_window
        f_end   = min((w + 1) * frames_per_window, max_frame + 1)
        mask    = valid[f_start:f_end]
        if mask.any():
            win_dx = float(np.mean(mean_dx[f_start:f_end][mask]))
            win_dy = float(np.mean(mean_dy[f_start:f_end][mask]))
        else:
            win_dx = 0.0
            win_dy = 0.0

        for f in range(f_start, f_end):
            local_cum_dx[f] = local_cum_dx[f_start] + win_dx * (f - f_start)
            local_cum_dy[f] = local_cum_dy[f_start] + win_dy * (f - f_start)

    if progress_callback:
        progress_callback(50, "Drift windows computed. Applying correction...")

    # ----------------------------------------------------------------
    # PASS 2 — apply correction, write output parquet
    # ----------------------------------------------------------------
    pf         = pq.ParquetFile(filepath)
    schema     = pf.schema_arrow
    writer     = None
    rows_written = 0

    for batch_num, batch in enumerate(
        pf.iter_batches(batch_size=row_batch_size),
        start=1
    ):
        df = batch.to_pandas()

        frames_arr = df[frame_col].to_numpy(dtype=np.int64)
        cum_dx_arr = local_cum_dx[frames_arr]
        cum_dy_arr = local_cum_dy[frames_arr]

        df[x_col] = df[x_col] - cum_dx_arr
        df[y_col] = df[y_col] - cum_dy_arr

        corrected_batch = pa.RecordBatch.from_pandas(df, schema=schema)

        if writer is None:
            writer = pq.ParquetWriter(output_filepath, schema)
        writer.write_batch(corrected_batch)

        rows_written += len(df)

        if progress_callback:
            pct = 50 + int(45 * rows_written / max(1, total_rows))
            progress_callback(pct, f"Pass 2: writing corrected data...")

    if writer:
        writer.close()

    if progress_callback:
        progress_callback(95, "Generating comparison plots...")

    # ----------------------------------------------------------------
    # Generate before/after figures for the Drift Dialog
    # (same plots as shift_correction.py, returned as Figure objects)
    # ----------------------------------------------------------------
    fig_before, ax_before = plt.subplots(figsize=(4, 3))
    frames_with_data = frame_ids[valid]
    if len(frames_with_data) > 0:
        sample_frames = frames_with_data[:min(500, len(frames_with_data))]
        cum_original  = np.cumsum(mean_dx[sample_frames])
        ax_before.plot(sample_frames, cum_original, color="#888888", linewidth=0.8)
        ax_before.axhline(0, color="gray", linestyle="--", linewidth=0.5)
    ax_before.set_title("Before correction", fontsize=9)
    ax_before.set_xlabel("Frame", fontsize=8)
    ax_before.set_ylabel("Cumulative drift (px)", fontsize=8)
    ax_before.tick_params(labelsize=7)
    fig_before.tight_layout()

    fig_after, ax_after = plt.subplots(figsize=(4, 3))
    ax_after.axhline(0, color="#2F9E44", linewidth=1.5, label="Corrected")
    ax_after.set_title("After correction", fontsize=9)
    ax_after.set_xlabel("Frame", fontsize=8)
    ax_after.set_ylabel("Cumulative drift (px)", fontsize=8)
    ax_after.tick_params(labelsize=7)
    fig_after.tight_layout()

    if progress_callback:
        progress_callback(100, "Done.")

    return {
        "mean_dx":       global_mean_dx,
        "mean_dy":       global_mean_dy,
        "drift_vector":  (round(global_mean_dx, 4), round(global_mean_dy, 4)),
        "output_file":   output_filepath,
        "n_observations": rows_written,
        "before_figure": fig_before,
        "after_figure":  fig_after,
    }
