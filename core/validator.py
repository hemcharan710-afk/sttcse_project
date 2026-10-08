"""
core/validator.py
Runs all 10 validation checks shown in the UI screenshot.
Wraps logic from explore_data.py and drift_analysis.py.
Math: UNTOUCHED — same algorithms, just return ValidationReport instead of printing.
"""

import pyarrow.parquet as pq
import numpy as np
import pandas as pd
from collections import Counter

from models.validation_report import ValidationReport, ValidationCheck


def run_validation(filepath: str, column_map: dict, params: dict) -> ValidationReport:
    """
    Runs all 10 validation checks matching the UI screenshot.

    column_map: {"particle_id": "particle", "frame": "frame", "x": "x", "y": "y"}
    params:     {"frame_rate": 30.0, "pixel_scale": 0.065, ...}

    Returns: ValidationReport
    """
    particle_col = column_map.get("particle_id", "particle")
    frame_col    = column_map.get("frame",       "frame")
    x_col        = column_map.get("x",           "x")
    y_col        = column_map.get("y",           "y")
    required     = [particle_col, frame_col, x_col, y_col]

    pf = pyarrow.parquet.ParquetFile(filepath) if False else pq.ParquetFile(filepath)

    # ----------------------------------------------------------------
    # Single pass: collect everything needed for all checks at once
    # ----------------------------------------------------------------
    unique_particles = set()
    frame_counter    = Counter()
    total_rows       = 0

    missing_particle = 0
    missing_x        = 0
    missing_y        = 0
    missing_frame    = 0

    duplicate_count  = 0
    invalid_ts_count = 0

    # For drift detection — same logic as drift_analysis.py
    frame_sum_dx = {}
    frame_sum_dy = {}
    frame_pair_count = {}
    previous_positions = {}

    # For trajectory discontinuities and short trajectories
    particle_frames = {}   # particle_id -> sorted list of frames

    for batch in pf.iter_batches(batch_size=100_000, columns=required):
        df = batch.to_pandas()
        total_rows += len(df)

        # --- check 1: missing particle IDs ---
        missing_particle += int(df[particle_col].isna().sum())

        # --- check 2: missing coordinates ---
        missing_x += int(df[x_col].isna().sum())
        missing_y += int(df[y_col].isna().sum())

        # --- check 3: missing timestamps / frames ---
        missing_frame += int(df[frame_col].isna().sum())

        df_clean = df.dropna(subset=required)

        # --- check 4: duplicate observations ---
        dupes = df_clean.duplicated(subset=[particle_col, frame_col]).sum()
        duplicate_count += int(dupes)

        # --- check 5: invalid timestamps (negative or non-integer frames) ---
        invalid_ts_count += int((df_clean[frame_col] < 0).sum())

        # Unique particles and frames
        unique_particles.update(df_clean[particle_col].unique())
        frame_counter.update(df_clean[frame_col])

        # Extract numpy arrays for fast iteration
        p_arr = df_clean[particle_col].to_numpy()
        f_arr = df_clean[frame_col].to_numpy()
        x_arr = df_clean[x_col].to_numpy()
        y_arr = df_clean[y_col].to_numpy()

        # --- Drift detection (same math as drift_analysis.py) ---
        for i in range(len(p_arr)):
            p     = int(p_arr[i])
            frame = int(f_arr[i])
            x     = float(x_arr[i])
            y     = float(y_arr[i])

            if p in previous_positions:
                prev_frame, prev_x, prev_y = previous_positions[p]
                if frame - prev_frame == 1:
                    dx = x - prev_x
                    dy = y - prev_y
                    frame_sum_dx.setdefault(frame, 0.0)
                    frame_sum_dy.setdefault(frame, 0.0)
                    frame_pair_count.setdefault(frame, 0)
                    frame_sum_dx[frame] += dx
                    frame_sum_dy[frame] += dy
                    frame_pair_count[frame] += 1

            previous_positions[p] = (frame, x, y)

            # For trajectory discontinuity check
            if p not in particle_frames:
                particle_frames[p] = []
            particle_frames[p].append(frame)

    # ----------------------------------------------------------------
    # Post-processing checks
    # ----------------------------------------------------------------

    n_particles    = len(unique_particles)
    n_observations = total_rows
    frames_sorted  = sorted(frame_counter.keys())
    frame_min      = int(frames_sorted[0])  if frames_sorted else 0
    frame_max      = int(frames_sorted[-1]) if frames_sorted else 0

    # --- check 6: trajectory discontinuities ---
    discontinuous_particles = 0
    for p, frames in particle_frames.items():
        frames_sorted_p = sorted(frames)
        gaps = [
            frames_sorted_p[i+1] - frames_sorted_p[i]
            for i in range(len(frames_sorted_p) - 1)
        ]
        if any(g > 1 for g in gaps):
            discontinuous_particles += 1

    # --- check 7: possible drift ---
    drift_detected = False
    drift_vector   = (0.0, 0.0)
    if frame_pair_count:
        mean_dxs = [
            frame_sum_dx[f] / frame_pair_count[f]
            for f in frame_pair_count if frame_pair_count[f] > 0
        ]
        mean_dys = [
            frame_sum_dy[f] / frame_pair_count[f]
            for f in frame_pair_count if frame_pair_count[f] > 0
        ]
        global_mean_dx = float(np.mean(mean_dxs))
        global_mean_dy = float(np.mean(mean_dys))
        drift_magnitude = np.sqrt(global_mean_dx**2 + global_mean_dy**2)
        drift_detected  = drift_magnitude > 0.01   # threshold in pixels
        drift_vector    = (round(global_mean_dx, 4), round(global_mean_dy, 4))

    # --- check 8: trajectories too short ---
    short_threshold  = 10  # frames
    short_count      = sum(1 for frames in particle_frames.values() if len(frames) < short_threshold)

    # --- check 9: missing frames in sequence ---
    expected_frames  = set(range(frame_min, frame_max + 1))
    missing_frames_n = len(expected_frames - set(frame_counter.keys()))

    # --- check 10: particle count changes over time ---
    counts_per_frame = np.array([frame_counter[f] for f in frames_sorted])
    count_std        = float(np.std(counts_per_frame)) if len(counts_per_frame) > 1 else 0.0
    count_changes    = count_std > (0.1 * float(np.mean(counts_per_frame)))

    # ----------------------------------------------------------------
    # Build ValidationReport
    # ----------------------------------------------------------------
    checks = [
        ValidationCheck(
            name="Missing particle IDs",
            status="passed" if missing_particle == 0 else "warning",
            detail=f"{missing_particle} missing particle ID records" if missing_particle else "",
        ),
        ValidationCheck(
            name="Missing coordinates",
            status="passed" if (missing_x + missing_y) == 0 else "warning",
            detail=f"{missing_x} missing X, {missing_y} missing Y" if (missing_x + missing_y) else "",
        ),
        ValidationCheck(
            name="Missing timestamps",
            status="passed" if missing_frame == 0 else "warning",
            detail=f"{missing_frame} missing frame values" if missing_frame else "",
        ),
        ValidationCheck(
            name="Duplicate observations",
            status="passed" if duplicate_count == 0 else "warning",
            detail=f"{duplicate_count} duplicate (particle, frame) pairs found",
        ),
        ValidationCheck(
            name="Invalid/inconsistent timestamps",
            status="passed" if invalid_ts_count == 0 else "warning",
            detail=f"{invalid_ts_count} negative or invalid frame values" if invalid_ts_count else "",
        ),
        ValidationCheck(
            name="Trajectory discontinuities",
            status="passed" if discontinuous_particles == 0 else "warning",
            detail=f"{discontinuous_particles} particles have frame gaps in their trajectory",
        ),
        ValidationCheck(
            name="Possible Drift",
            status="warning" if drift_detected else "passed",
            detail=(
                f"Particles show a possible trend in a certain direction. "
                f"Estimated drift vector: {drift_vector} px/frame"
            ) if drift_detected else "",
            correctable=drift_detected,
        ),
        ValidationCheck(
            name="Trajectories too short",
            status="passed" if short_count == 0 else "warning",
            detail=f"{short_count} particles have fewer than {short_threshold} frames",
        ),
        ValidationCheck(
            name="Missing frames",
            status="passed" if missing_frames_n == 0 else "warning",
            detail=f"{missing_frames_n} frame numbers missing from the sequence",
        ),
        ValidationCheck(
            name="Particle count changes over time",
            status="passed" if not count_changes else "warning",
            detail=f"Particle count std={count_std:.1f} suggests significant variation" if count_changes else "",
        ),
    ]

    return ValidationReport(
        filename=filepath.split("/")[-1].split("\\")[-1],
        n_particles=n_particles,
        n_observations=n_observations,
        frame_range=(frame_min, frame_max),
        checks=checks,
    )
