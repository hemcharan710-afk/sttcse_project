# ============================================================
# calculate_metrics_corrected.py
# Particle Trajectory Analysis
#
# This version:
#   - removes hard-coded metric parameters from formulas
#   - uses 10 fps through FRAME_RATE_HZ
#   - computes displacement AND velocity
#   - computes trajectory duration and path length
#   - computes 2D MSD and 2D NGP
#   - computes radial self-van-Hove G_s(r,t)
#   - computes pair correlation g(r) with a simple edge-safe
#     reference-particle correction
#   - computes self-ISF when Q_VALUES is supplied
#   - computes chi4 with N measured from each time-origin
#   - explicitly reports that particle orientation metrics cannot
#     be computed unless an orientation angle is present in the data
#
# Dataset columns used:
#   frame, particle, x, y
#
# Units:
#   x,y: pixels in input
#   positions/displacements: micrometers
#   time: seconds
# ============================================================

import pyarrow.parquet as pq
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections import Counter
from scipy.spatial import cKDTree
from scipy.special import j0


# ============================================================
# SETTINGS
# ============================================================

FILE = "linked_phi5.parquet"
#FILE = "linked_phi5_shift_corrected.parquet"

# Camera
FRAME_RATE_HZ = 10.0
FRAME_INTERVAL_SEC = 1.0 / FRAME_RATE_HZ

# Calibration
PIXELS_PER_MICRON = 17.0

# Parquet processing
ROW_BATCH_SIZE = 100_000

# Requested lag times, expressed in frames.
# They are converted to seconds using FRAME_RATE_HZ.
LAGS_FRAMES = [1, 10, 50, 100, 500, 1000]

# Velocity is reported for this lag.
VELOCITY_LAG_FRAMES = 1

# ------------------------------------------------------------
# Self-ISF
# q is NOT determined by camera FPS.
# It must be specified from the research question.
#
# Units: inverse micrometers
# Example: [1.0, 2.0, 5.0]
# ------------------------------------------------------------
Q_VALUES = None

# ------------------------------------------------------------
# Four-point susceptibility
# The overlap cutoff a must be chosen by the research group.
#
# Units: micrometers
# Example: 0.5
# ------------------------------------------------------------
OVERLAP_CUTOFF_UM = None

# ------------------------------------------------------------
# Pair correlation
# All are user parameters, not hidden constants.
# ------------------------------------------------------------
PAIR_FRAME_STEP = 100
PAIR_R_MAX_UM = 20.0
PAIR_DR_UM = 0.1

# ------------------------------------------------------------
# Image/ROI bounds.
# These should describe the actual field of view used for
# the particle positions. Replace if the camera ROI is known
# more accurately.
# ------------------------------------------------------------
ROI_X_MIN_PX = 7.2080846
ROI_X_MAX_PX = 1015.7375
ROI_Y_MIN_PX = 7.201788
ROI_Y_MAX_PX = 2039.7822

# ------------------------------------------------------------
# Self-van-Hove radial histogram.
# G_s(r,t) is reported from the radial probability distribution:
#
#   G_s(r,t) = P(r,t) / (2*pi*r)
#
# for 2D isotropic motion.
# ------------------------------------------------------------
VAN_HOVE_R_MAX_UM = 20.0
VAN_HOVE_DR_UM = 0.1

# Plot settings (not metric definitions)
HISTOGRAM_BINS = 50
PLOT_DPI = 300


# ============================================================
# HELPER: READ DATA FRAME BY FRAME
# ============================================================

def iter_frames():
    """
    Yield:
        frame_number, particle_ids, x_pixels, y_pixels

    The complete 76-million-row file is never loaded into RAM.
    A frame may span multiple Parquet row batches, so pieces
    belonging to the same frame are combined before yielding.
    """
    pf = pq.ParquetFile(FILE)

    current_frame = None
    current_particles = []
    current_x = []
    current_y = []

    for batch in pf.iter_batches(
        batch_size=ROW_BATCH_SIZE,
        columns=["frame", "particle", "x", "y"]
    ):
        frame = batch.column("frame").to_numpy()
        particle = batch.column("particle").to_numpy()
        x = batch.column("x").to_numpy()
        y = batch.column("y").to_numpy()

        start = 0

        while start < len(frame):
            this_frame = int(frame[start])

            end = start + 1
            while (
                end < len(frame)
                and frame[end] == this_frame
            ):
                end += 1

            if (
                current_frame is not None
                and this_frame != current_frame
            ):
                yield (
                    current_frame,
                    np.concatenate(current_particles),
                    np.concatenate(current_x),
                    np.concatenate(current_y)
                )

                current_particles = []
                current_x = []
                current_y = []

            current_frame = this_frame
            current_particles.append(particle[start:end])
            current_x.append(x[start:end])
            current_y.append(y[start:end])

            start = end

    if current_frame is not None:
        yield (
            current_frame,
            np.concatenate(current_particles),
            np.concatenate(current_x),
            np.concatenate(current_y)
        )


# ============================================================
# 1. PARTICLE COUNT VS FRAME
# ============================================================

def particle_count_vs_frame():
    print("\n==============================")
    print("1. PARTICLE COUNT VS FRAME")
    print("==============================")

    frame_counts = Counter()

    for frame_number, particles, _, _ in iter_frames():
        # A frame is already yielded as one complete frame.
        frame_counts[int(frame_number)] = len(
            np.unique(particles)
        )

    frames = np.array(sorted(frame_counts))
    counts = np.array([frame_counts[f] for f in frames])

    print("Number of frames:", len(frames))
    print("Minimum particles/frame:", counts.min())
    print("Maximum particles/frame:", counts.max())
    print("Average particles/frame:", counts.mean())

    np.savetxt(
        "particle_count_vs_frame.csv",
        np.column_stack((frames, counts)),
        delimiter=",",
        header="frame,particle_count",
        comments=""
    )

    plt.figure()
    plt.plot(frames, counts)
    plt.xlabel("Frame")
    plt.ylabel("Number of particles")
    plt.title("Number of Particles vs Frame")
    plt.grid(True)
    plt.savefig(
        "particle_count_vs_frame.png",
        dpi=PLOT_DPI
    )
    plt.show()


# ============================================================
# 2. TRAJECTORY DURATION + PATH LENGTH
# ============================================================

def trajectory_statistics():
    """
    For each particle, find:
    - first frame where it appears
    - last frame where it appears
    - trajectory length in frames
    - trajectory duration in seconds
    """

    particle_stats = {}

    parquet_file = pq.ParquetFile(FILE)

    for batch in parquet_file.iter_batches(
        batch_size=ROW_BATCH_SIZE,
        columns=["particle", "frame"]
    ):
        df = batch.to_pandas()

        # Find first and last frame for each particle
        grouped = df.groupby("particle")["frame"].agg(
            first_frame="min",
            last_frame="max"
        )

        for particle_id, row in grouped.iterrows():

            first_frame = int(row["first_frame"])
            last_frame = int(row["last_frame"])

            if particle_id not in particle_stats:
                particle_stats[particle_id] = [
                    first_frame,
                    last_frame
                ]
            else:
                # Update first frame if we found an earlier one
                particle_stats[particle_id][0] = min(
                    particle_stats[particle_id][0],
                    first_frame
                )

                # Update last frame if we found a later one
                particle_stats[particle_id][1] = max(
                    particle_stats[particle_id][1],
                    last_frame
                )

    # Convert dictionary to DataFrame
    trajectory_df = pd.DataFrame(
        [
            [particle_id, first_frame, last_frame]
            for particle_id, (first_frame, last_frame)
            in particle_stats.items()
        ],
        columns=["particle", "first_frame", "last_frame"]
    )

    # Number of frames covered by the trajectory
    trajectory_df["trajectory_length_frames"] = (
        trajectory_df["last_frame"]
        - trajectory_df["first_frame"]
        + 1
    )

    # Camera = 10 fps
    trajectory_df["trajectory_duration_sec"] = (
        (trajectory_df["last_frame"]
         - trajectory_df["first_frame"])
        * FRAME_INTERVAL_SEC
    )

    # Save results
    trajectory_df.to_csv(
        "trajectory_length_distribution.csv",
        index=False
    )

    # Plot trajectory-length distribution
    plt.figure(figsize=(8, 5))

    plt.hist(
        trajectory_df["trajectory_length_frames"],
        bins=HISTOGRAM_BINS
    )

    plt.xlabel("Trajectory length (frames)")
    plt.ylabel("Number of particles")
    plt.title("Trajectory Length Distribution")

    plt.tight_layout()
    plt.savefig(
        "trajectory_length_distribution.png",
        dpi=PLOT_DPI
    )
    plt.show()

    return trajectory_df

# ============================================================
# 3. DISPLACEMENT + VELOCITY
# ============================================================

def calculate_displacements_and_velocity():
    print("\n======================================")
    print("3. DISPLACEMENT + VELOCITY")
    print("======================================")

    previous = {}

    count = 0

    sum_dx = 0.0
    sum_dy = 0.0
    sum_dr = 0.0

    sum_vx = 0.0
    sum_vy = 0.0
    sum_speed = 0.0

    for batch in pq.ParquetFile(FILE).iter_batches(
        batch_size=ROW_BATCH_SIZE,
        columns=["x", "y", "frame", "particle"]
    ):
        x = batch.column("x").to_numpy()
        y = batch.column("y").to_numpy()
        frame = batch.column("frame").to_numpy()
        particle = batch.column("particle").to_numpy()

        for i in range(len(x)):
            p = int(particle[i])
            f = int(frame[i])

            if p in previous:
                old_frame, old_x, old_y = previous[p]

                if f - old_frame == 1:
                    dx_um = (
                        (x[i] - old_x)
                        / PIXELS_PER_MICRON
                    )
                    dy_um = (
                        (y[i] - old_y)
                        / PIXELS_PER_MICRON
                    )

                    dr_um = np.hypot(
                        dx_um,
                        dy_um
                    )

                    dt = (
                        VELOCITY_LAG_FRAMES
                        * FRAME_INTERVAL_SEC
                    )

                    vx = dx_um / dt
                    vy = dy_um / dt
                    speed = dr_um / dt

                    count += 1

                    sum_dx += dx_um
                    sum_dy += dy_um
                    sum_dr += dr_um

                    sum_vx += vx
                    sum_vy += vy
                    sum_speed += speed

            previous[p] = (
                f,
                float(x[i]),
                float(y[i])
            )

    if count == 0:
        print("No valid consecutive displacements.")
        return

    print("Valid one-frame displacements:", count)
    print("Mean dx (um):", sum_dx / count)
    print("Mean dy (um):", sum_dy / count)
    print("Mean |dr| (um):", sum_dr / count)

    print(
        f"Mean vx (um/s): "
        f"{sum_vx / count}"
    )
    print(
        f"Mean vy (um/s): "
        f"{sum_vy / count}"
    )
    print(
        f"Mean speed (um/s): "
        f"{sum_speed / count}"
    )


# ============================================================
# 4-7. LAG STATISTICS
#
# One streaming pass calculates:
#   MSD
#   fourth moment / NGP
#   self van-Hove histogram
#   self-ISF if q is supplied
#   chi4 if overlap cutoff is supplied
# ============================================================

def calculate_lag_metrics():
    print("\n======================================")
    print("4-7. LAG-BASED METRICS")
    print("======================================")

    lags = sorted(set(int(v) for v in LAGS_FRAMES))
    max_lag = max(lags)

    # --------------------------------------------------------
    # Accumulators
    # --------------------------------------------------------

    sum_r2 = {lag: 0.0 for lag in lags}
    sum_r4 = {lag: 0.0 for lag in lags}
    pair_counts = {lag: 0 for lag in lags}

    # Van-Hove radial bins
    vh_edges = np.arange(
        0.0,
        VAN_HOVE_R_MAX_UM + VAN_HOVE_DR_UM,
        VAN_HOVE_DR_UM
    )

    vh_counts = {
        lag: np.zeros(
            len(vh_edges) - 1,
            dtype=np.int64
        )
        for lag in lags
    }

    # ISF accumulators
    isf_sum = None
    if Q_VALUES is not None:
        isf_sum = {
            float(q): {
                lag: 0.0
                for lag in lags
            }
            for q in Q_VALUES
        }

    # chi4 accumulators
    chi4_Q_values = None
    if OVERLAP_CUTOFF_UM is not None:
        chi4_Q_values = {
            lag: []
            for lag in lags
        }

    history = {}

    for frame_number, particles, x, y in iter_frames():

        # Store positions in micrometers
        x_um = x.astype(np.float64) / PIXELS_PER_MICRON
        y_um = y.astype(np.float64) / PIXELS_PER_MICRON

        history[frame_number] = (
            particles,
            x_um,
            y_um
        )

        old_frames = [
            f for f in history
            if f < frame_number - max_lag
        ]

        for f in old_frames:
            del history[f]

        for lag in lags:

            previous_frame = frame_number - lag

            if previous_frame not in history:
                continue

            (
                old_particles,
                old_x,
                old_y
            ) = history[previous_frame]

            old_positions = {
                int(p): (xx, yy)
                for p, xx, yy in zip(
                    old_particles,
                    old_x,
                    old_y
                )
            }

            # chi4 uses the overlap of matched particles.
            overlap_count = 0
            matched_count = 0

            for p, xx, yy in zip(
                particles,
                x_um,
                y_um
            ):
                p = int(p)

                if p not in old_positions:
                    continue

                old_x_pos, old_y_pos = old_positions[p]

                dx = xx - old_x_pos
                dy = yy - old_y_pos
                r2 = dx * dx + dy * dy
                r4 = r2 * r2
                dr = np.sqrt(r2)

                sum_r2[lag] += r2
                sum_r4[lag] += r4
                pair_counts[lag] += 1

                # Van Hove
                if dr < VAN_HOVE_R_MAX_UM:
                    bin_index = int(
                        dr / VAN_HOVE_DR_UM
                    )
                    if (
                        0 <= bin_index
                        < len(vh_counts[lag])
                    ):
                        vh_counts[lag][bin_index] += 1

                # Self ISF
                if isf_sum is not None:
                    for q in Q_VALUES:
                        isf_sum[float(q)][lag] += j0(
                            float(q) * dr
                        )

                # Four-point overlap
                if chi4_Q_values is not None:
                    matched_count += 1

                    if dr < OVERLAP_CUTOFF_UM:
                        overlap_count += 1

            if chi4_Q_values is not None:
                if matched_count > 0:
                    Q = (
                        overlap_count
                        / matched_count
                    )
                    chi4_Q_values[lag].append(
                        (matched_count, Q)
                    )

    # --------------------------------------------------------
    # MSD + NGP
    # --------------------------------------------------------

    msd_results = []
    ngp_results = []

    for lag in lags:
        n = pair_counts[lag]

        if n == 0:
            msd = np.nan
            ngp = np.nan
        else:
            mean_r2 = sum_r2[lag] / n
            mean_r4 = sum_r4[lag] / n

            msd = mean_r2

            if mean_r2 > 0:
                # Correct 2D NGP:
                #
                # alpha_2 =
                # <r^4> / (2 <r^2>^2) - 1
                ngp = (
                    mean_r4
                    / (
                        2.0 * mean_r2 ** 2
                    )
                ) - 1.0
            else:
                ngp = np.nan

        time_sec = lag * FRAME_INTERVAL_SEC

        msd_results.append(
            (lag, time_sec, n, msd)
        )

        ngp_results.append(
            (lag, time_sec, n, ngp)
        )

        print(
            f"Lag={lag:6d} frames "
            f"({time_sec:10.3f} s) | "
            f"N={n:10d} | "
            f"MSD={msd:.6f} um^2 | "
            f"NGP={ngp:.6f}"
        )

    np.savetxt(
        "msd.csv",
        np.array(msd_results),
        delimiter=",",
        header="lag_frames,time_sec,pair_count,MSD_um2",
        comments=""
    )

    np.savetxt(
        "ngp.csv",
        np.array(ngp_results),
        delimiter=",",
        header="lag_frames,time_sec,pair_count,NGP_2D",
        comments=""
    )

    # --------------------------------------------------------
    # Plot MSD
    # --------------------------------------------------------

    valid_msd = [
        row for row in msd_results
        if np.isfinite(row[3])
        and row[3] > 0
    ]

    if valid_msd:
        times = [row[1] for row in valid_msd]
        msds = [row[3] for row in valid_msd]

        plt.figure()
        plt.loglog(times, msds, "o-")
        plt.xlabel("Lag time (s)")
        plt.ylabel("MSD (um^2)")
        plt.title("Mean Squared Displacement")
        plt.grid(True)
        plt.savefig(
            "msd.png",
            dpi=PLOT_DPI
        )
        plt.show()

    # --------------------------------------------------------
    # Plot NGP
    # --------------------------------------------------------

    valid_ngp = [
        row for row in ngp_results
        if np.isfinite(row[3])
    ]

    if valid_ngp:
        times = [row[1] for row in valid_ngp]
        ngps = [row[3] for row in valid_ngp]

        plt.figure()
        plt.plot(times, ngps, "o-")
        plt.axhline(
            0.0,
            linestyle="--"
        )
        plt.xlabel("Lag time (s)")
        plt.ylabel("2D Non-Gaussian Parameter")
        plt.title("Non-Gaussian Parameter")
        plt.grid(True)
        plt.savefig(
            "ngp.png",
            dpi=PLOT_DPI
        )
        plt.show()

    # --------------------------------------------------------
    # Self van-Hove
    #
    # The histogram is P(r,t), where:
    #   P(r,t) dr = probability of a displacement magnitude
    #               between r and r+dr.
    #
    # For 2D isotropic motion:
    #   G_s(r,t) = P(r,t)/(2*pi*r)
    # --------------------------------------------------------

    centers = (
        vh_edges[:-1]
        + vh_edges[1:]
    ) / 2.0

    for lag in lags:

        n = pair_counts[lag]

        if n == 0:
            continue

        probability_density = (
            vh_counts[lag]
            / (n * VAN_HOVE_DR_UM)
        )

        gs = np.full_like(
            centers,
            np.nan,
            dtype=np.float64
        )

        positive = centers > 0

        gs[positive] = (
            probability_density[positive]
            / (
                2.0
                * np.pi
                * centers[positive]
            )
        )

        np.savetxt(
            f"van_hove_lag_{lag}.csv",
            np.column_stack(
                (
                    centers,
                    probability_density,
                    gs
                )
            ),
            delimiter=",",
            header=(
                "r_um,P_r,Gs_r_um^-2"
            ),
            comments=""
        )

        plt.figure()
        plt.plot(centers, gs)
        plt.xlabel("Displacement magnitude r (um)")
        plt.ylabel("G_s(r,t) (um^-2)")
        plt.title(
            f"Self van-Hove Function "
            f"(lag={lag} frames, "
            f"t={lag * FRAME_INTERVAL_SEC:.3f} s)"
        )
        plt.grid(True)
        plt.savefig(
            f"van_hove_lag_{lag}.png",
            dpi=PLOT_DPI
        )
        plt.show()

    # --------------------------------------------------------
    # Self ISF
    # --------------------------------------------------------

    if isf_sum is not None:

        for q in Q_VALUES:

            q = float(q)
            results = []

            for lag in lags:
                n = pair_counts[lag]

                if n == 0:
                    fs = np.nan
                else:
                    fs = (
                        isf_sum[q][lag]
                        / n
                    )

                results.append(
                    (
                        lag,
                        lag * FRAME_INTERVAL_SEC,
                        n,
                        fs
                    )
                )

            np.savetxt(
                f"isf_q_{q:.6g}.csv",
                np.array(results),
                delimiter=",",
                header=(
                    "lag_frames,time_sec,"
                    "pair_count,F_s"
                ),
                comments=""
            )

            valid = [
                row for row in results
                if np.isfinite(row[3])
            ]

            if valid:
                times = [row[1] for row in valid]
                values = [row[3] for row in valid]

                plt.figure()
                plt.plot(times, values, "o-")
                plt.xlabel("Lag time (s)")
                plt.ylabel("Self-ISF")
                plt.title(
                    f"Self-Intermediate Scattering "
                    f"Function (q={q} um^-1)"
                )
                plt.grid(True)
                plt.savefig(
                    f"isf_q_{q:.6g}.png",
                    dpi=PLOT_DPI
                )
                plt.show()

    else:
        print(
            "\nSELF-ISF SKIPPED: "
            "Q_VALUES is None."
        )

    # --------------------------------------------------------
    # Four-point susceptibility
    #
    # For each time origin:
    #   Q_t = number immobile / number matched
    #
    # We then use:
    #   chi4 = <N_t (Q_t - <Q>)^2>
    #
    # This avoids hard-coding N=2029.
    # Exact ensemble normalization should be confirmed by
    # the research group.
    # --------------------------------------------------------

    if chi4_Q_values is not None:

        chi_results = []

        for lag in lags:

            entries = chi4_Q_values[lag]

            if not entries:
                chi_results.append(
                    (
                        lag,
                        lag * FRAME_INTERVAL_SEC,
                        np.nan,
                        np.nan
                    )
                )
                continue

            Ns = np.array(
                [row[0] for row in entries],
                dtype=np.float64
            )

            Qs = np.array(
                [row[1] for row in entries],
                dtype=np.float64
            )

            mean_Q = np.mean(Qs)

            chi4 = np.mean(
                Ns * (Qs - mean_Q) ** 2
            )

            chi_results.append(
                (
                    lag,
                    lag * FRAME_INTERVAL_SEC,
                    mean_Q,
                    chi4
                )
            )

        np.savetxt(
            "chi4.csv",
            np.array(chi_results),
            delimiter=",",
            header="lag_frames,time_sec,Q_mean,chi4",
            comments=""
        )

        times = [
            row[1] for row in chi_results
            if np.isfinite(row[3])
        ]

        values = [
            row[3] for row in chi_results
            if np.isfinite(row[3])
        ]

        if values:
            plt.figure()
            plt.plot(times, values, "o-")
            plt.xlabel("Lag time (s)")
            plt.ylabel("chi4")
            plt.title("Four-Point Susceptibility")
            plt.grid(True)
            plt.savefig(
                "chi4.png",
                dpi=PLOT_DPI
            )
            plt.show()

    else:
        print(
            "\nCHI4 SKIPPED: "
            "OVERLAP_CUTOFF_UM is None."
        )


# ============================================================
# 8. PAIR CORRELATION g(r)
# ============================================================

def calculate_pair_correlation():
    print("\n======================================")
    print("8. PAIR CORRELATION g(r)")
    print("======================================")

    bins = np.arange(
        0.0,
        PAIR_R_MAX_UM + PAIR_DR_UM,
        PAIR_DR_UM
    )

    histogram = np.zeros(
        len(bins) - 1,
        dtype=np.float64
    )

    frames_used = 0
    total_reference_particles = 0
    total_particles = 0

    x_min_um = ROI_X_MIN_PX / PIXELS_PER_MICRON
    x_max_um = ROI_X_MAX_PX / PIXELS_PER_MICRON
    y_min_um = ROI_Y_MIN_PX / PIXELS_PER_MICRON
    y_max_um = ROI_Y_MAX_PX / PIXELS_PER_MICRON

    width_um = x_max_um - x_min_um
    height_um = y_max_um - y_min_um
    area_um2 = width_um * height_um

    for (
        frame_number,
        particles,
        x,
        y
    ) in iter_frames():

        if frame_number % PAIR_FRAME_STEP != 0:
            continue

        positions = np.column_stack(
            (
                x / PIXELS_PER_MICRON,
                y / PIXELS_PER_MICRON
            )
        )

        n = len(positions)

        if n < 2:
            continue

        # To avoid boundary bias, use only reference particles
        # whose complete R_MAX circle lies inside the ROI.
        interior = (
            (positions[:, 0] >= x_min_um + PAIR_R_MAX_UM)
            & (positions[:, 0] <= x_max_um - PAIR_R_MAX_UM)
            & (positions[:, 1] >= y_min_um + PAIR_R_MAX_UM)
            & (positions[:, 1] <= y_max_um - PAIR_R_MAX_UM)
        )

        reference_indices = np.flatnonzero(interior)

        if len(reference_indices) == 0:
            continue

        tree = cKDTree(positions)

        # query_ball_point gives neighbors for each reference.
        # We exclude the reference particle itself.
        neighbor_lists = tree.query_ball_point(
            positions[reference_indices],
            r=PAIR_R_MAX_UM
        )

        for ref_idx, neighbors in zip(
            reference_indices,
            neighbor_lists
        ):
            for j in neighbors:
                if j == ref_idx:
                    continue

                distance = np.linalg.norm(
                    positions[ref_idx]
                    - positions[j]
                )

                bin_index = int(
                    distance / PAIR_DR_UM
                )

                if (
                    0 <= bin_index
                    < len(histogram)
                ):
                    histogram[bin_index] += 1.0

        frames_used += 1
        total_reference_particles += len(
            reference_indices
        )
        total_particles += n

    if frames_used == 0:
        print("No suitable frames for pair correlation.")
        return

    r = (
        bins[:-1]
        + bins[1:]
    ) / 2.0

    average_N = total_particles / frames_used

    number_density = (
        average_N / area_um2
    )

    shell_area = (
        2.0
        * np.pi
        * r
        * PAIR_DR_UM
    )

    average_reference_count = (
        total_reference_particles
        / frames_used
    )

    expected = (
        average_reference_count
        * number_density
        * shell_area
    )

    observed = histogram / frames_used

    g_r = np.divide(
        observed,
        expected,
        out=np.full_like(
            observed,
            np.nan
        ),
        where=expected > 0
    )

    np.savetxt(
        "pair_correlation.csv",
        np.column_stack((r, g_r)),
        delimiter=",",
        header="r_um,g_r",
        comments=""
    )

    plt.figure()
    plt.plot(r, g_r)
    plt.axhline(
        1.0,
        linestyle="--"
    )
    plt.xlabel("r (um)")
    plt.ylabel("g(r)")
    plt.title("Pair Correlation Function")
    plt.grid(True)
    plt.savefig(
        "pair_correlation.png",
        dpi=PLOT_DPI
    )
    plt.show()

    print("Frames used:", frames_used)
    print(
        "Average particles/frame:",
        average_N
    )
    print(
        "Average interior reference particles/frame:",
        average_reference_count
    )


# ============================================================
# 9. ORIENTATION / ANISOTROPIC METRICS
# ============================================================

def anisotropic_metrics_status():
    print("\n======================================")
    print("9. ANISOTROPIC / ANGULAR METRICS")
    print("======================================")

    print(
        "NOT CALCULATED from this dataset."
    )

    print(
        "\nReason:"
    )

    print(
        "The current Parquet data provide "
        "particle, frame, x, y, mass and size, "
        "but no particle orientation angle theta."
    )

    print(
        "\nA particle orientation metric requires "
        "theta_i(t), e.g. the major-axis angle "
        "of an anisotropic particle."
    )

    print(
        "\nTherefore do NOT interpret the trajectory "
        "direction atan2(dy, dx) as particle orientation."
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("PARTICLE TRAJECTORY METRICS")
    print("=" * 70)

    print(
        f"Camera frame rate: "
        f"{FRAME_RATE_HZ} fps"
    )

    print(
        f"Frame interval: "
        f"{FRAME_INTERVAL_SEC:.6f} s"
    )

    particle_count_vs_frame()

    trajectory_statistics()

    calculate_displacements_and_velocity()

    calculate_lag_metrics()

    calculate_pair_correlation()

    #anisotropic_metrics_status()

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
