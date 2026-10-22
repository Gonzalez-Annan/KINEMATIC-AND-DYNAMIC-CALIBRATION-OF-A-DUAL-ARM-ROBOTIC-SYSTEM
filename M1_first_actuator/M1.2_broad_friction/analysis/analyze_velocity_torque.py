#!/usr/bin/env python3

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

try:
    from scipy.optimize import curve_fit
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


# ============================================================
# CONFIG
# ============================================================

DATA_DIR = Path(
    Path(__file__).resolve().parents[1] / "data" / "raw"
)

OUTPUT_DIR = Path(
    Path(__file__).resolve().parents[1] / "data" / "processed"
)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Automatically use newest CSV
csv_files = sorted(
    DATA_DIR.glob("velocity_torque_raw_*.csv"),
    key=lambda p: p.stat().st_mtime,
)

if not csv_files:
    raise FileNotFoundError(
        f"No velocity_torque_raw_*.csv found in {DATA_DIR}"
    )

CSV_PATH = csv_files[-1]

LOW_SPEED_LIMIT = 0.5


# ============================================================
# LOAD
# ============================================================

FIG_DIR = Path(__file__).resolve().parents[1] / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(CSV_PATH)

print()
print("========================================")
print("INPUT FILE")
print("========================================")
print(CSV_PATH)
print()

print("========================================")
print("DATASET OVERVIEW")
print("========================================")
print(f"Rows: {len(df)}")
print(f"Columns: {list(df.columns)}")
print()

print("Missing values:")
print(df.isna().sum())
print()


# ============================================================
# SAMPLING CHECK
# ============================================================

dt = np.diff(df["ros_time_s"].to_numpy())
dt_positive = dt[dt > 0]

print("========================================")
print("SAMPLING")
print("========================================")

if len(dt_positive) > 0:
    print(f"Median dt:       {np.median(dt_positive):.6f} s")
    print(f"Approx rate:     {1.0 / np.median(dt_positive):.2f} Hz")
    print(f"Min dt:          {np.min(dt_positive):.6f} s")
    print(f"Max dt:          {np.max(dt_positive):.6f} s")

print()


# ============================================================
# PER-POINT SUMMARY
# ============================================================

group_cols = [
    "sweep",
    "point",
    "command_velocity_rad_s",
]

summary = (
    df.groupby(group_cols)
    .agg(
        n_samples=("measured_velocity_rad_s", "size"),

        mean_velocity_rad_s=(
            "measured_velocity_rad_s",
            "mean",
        ),

        std_velocity_rad_s=(
            "measured_velocity_rad_s",
            "std",
        ),

        min_velocity_rad_s=(
            "measured_velocity_rad_s",
            "min",
        ),

        max_velocity_rad_s=(
            "measured_velocity_rad_s",
            "max",
        ),

        mean_torque_raw=(
            "torque_raw_per_mille",
            "mean",
        ),

        std_torque_raw=(
            "torque_raw_per_mille",
            "std",
        ),

        mean_torque_Nm=(
            "torque_Nm",
            "mean",
        ),

        std_torque_Nm=(
            "torque_Nm",
            "std",
        ),

        min_torque_Nm=(
            "torque_Nm",
            "min",
        ),

        max_torque_Nm=(
            "torque_Nm",
            "max",
        ),

        start_position_rad=(
            "measured_position_rad",
            "first",
        ),

        end_position_rad=(
            "measured_position_rad",
            "last",
        ),
    )
    .reset_index()
)

summary["velocity_error_rad_s"] = (
    summary["mean_velocity_rad_s"]
    - summary["command_velocity_rad_s"]
)

summary["abs_velocity_error_rad_s"] = (
    np.abs(summary["velocity_error_rad_s"])
)

summary["position_change_rad"] = (
    summary["end_position_rad"]
    - summary["start_position_rad"]
)


# ============================================================
# COMBINED ACROSS SWEEPS
# ============================================================

combined = (
    summary.groupby("command_velocity_rad_s")
    .agg(
        n_blocks=("mean_velocity_rad_s", "size"),

        mean_velocity_rad_s=(
            "mean_velocity_rad_s",
            "mean",
        ),

        std_velocity_between_sweeps=(
            "mean_velocity_rad_s",
            "std",
        ),

        mean_velocity_std_within=(
            "std_velocity_rad_s",
            "mean",
        ),

        mean_torque_Nm=(
            "mean_torque_Nm",
            "mean",
        ),

        std_torque_between_sweeps=(
            "mean_torque_Nm",
            "std",
        ),

        mean_torque_std_within=(
            "std_torque_Nm",
            "mean",
        ),

        mean_torque_raw=(
            "mean_torque_raw",
            "mean",
        ),
    )
    .reset_index()
    .sort_values("command_velocity_rad_s")
)

combined["velocity_error_rad_s"] = (
    combined["mean_velocity_rad_s"]
    - combined["command_velocity_rad_s"]
)


# ============================================================
# LOW-SPEED DATA
# ============================================================

low_speed = combined[
    np.abs(
        combined["command_velocity_rad_s"]
    ) <= LOW_SPEED_LIMIT
].copy()

nonzero = combined[
    np.abs(
        combined["command_velocity_rad_s"]
    ) > 1e-9
].copy()

low_nonzero = low_speed[
    np.abs(
        low_speed["command_velocity_rad_s"]
    ) > 1e-9
].copy()


# ============================================================
# PRINT TABLES
# ============================================================

pd.set_option("display.max_rows", 200)
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 40)

print("========================================")
print("PER-POINT SUMMARY")
print("========================================")

print(
    summary[
        [
            "sweep",
            "point",
            "command_velocity_rad_s",
            "n_samples",
            "mean_velocity_rad_s",
            "std_velocity_rad_s",
            "velocity_error_rad_s",
            "mean_torque_Nm",
            "std_torque_Nm",
            "position_change_rad",
        ]
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.6f}",
    )
)

print()

print("========================================")
print("COMBINED ACROSS SWEEPS")
print("========================================")

print(
    combined.to_string(
        index=False,
        float_format=lambda x: f"{x:.6f}",
    )
)

print()

print("========================================")
print("LOW-SPEED REGION")
print(f"|velocity| <= {LOW_SPEED_LIMIT} rad/s")
print("========================================")

print(
    low_speed.to_string(
        index=False,
        float_format=lambda x: f"{x:.6f}",
    )
)

print()


# ============================================================
# ZERO-SPEED BLOCKS
# ============================================================

zero_summary = summary[
    np.isclose(
        summary["command_velocity_rad_s"],
        0.0,
    )
].copy()

print("========================================")
print("ZERO-SPEED BLOCKS")
print("========================================")

print(
    zero_summary[
        [
            "sweep",
            "point",
            "mean_velocity_rad_s",
            "std_velocity_rad_s",
            "mean_torque_Nm",
            "std_torque_Nm",
        ]
    ].to_string(
        index=False,
        float_format=lambda x: f"{x:.6f}",
    )
)

print()


# ============================================================
# POSITIVE / NEGATIVE SYMMETRY
# ============================================================

print("========================================")
print("POSITIVE / NEGATIVE COMPARISON")
print("========================================")

speeds = sorted(
    set(
        abs(v)
        for v in combined["command_velocity_rad_s"]
        if abs(v) > 1e-9
    )
)

symmetry_rows = []

for speed in speeds:

    pos = combined[
        np.isclose(
            combined["command_velocity_rad_s"],
            speed,
        )
    ]

    neg = combined[
        np.isclose(
            combined["command_velocity_rad_s"],
            -speed,
        )
    ]

    if len(pos) == 1 and len(neg) == 1:

        pos_tau = pos.iloc[0]["mean_torque_Nm"]
        neg_tau = neg.iloc[0]["mean_torque_Nm"]

        pos_vel = pos.iloc[0]["mean_velocity_rad_s"]
        neg_vel = neg.iloc[0]["mean_velocity_rad_s"]

        symmetry_error = pos_tau + neg_tau

        symmetry_rows.append({
            "abs_command_velocity_rad_s": speed,
            "positive_mean_velocity_rad_s": pos_vel,
            "negative_mean_velocity_rad_s": neg_vel,
            "positive_torque_Nm": pos_tau,
            "negative_torque_Nm": neg_tau,
            "torque_symmetry_sum_Nm": symmetry_error,
        })

        print(
            f"|w|={speed:.3f} | "
            f"+tau={pos_tau:+.6f} Nm | "
            f"-tau={neg_tau:+.6f} Nm | "
            f"sum={symmetry_error:+.6f} Nm"
        )

print()

symmetry_df = pd.DataFrame(symmetry_rows)


# ============================================================
# TORQUE QUANTIZATION
# ============================================================

unique_raw = np.sort(
    df["torque_raw_per_mille"].unique()
)

diffs = np.diff(unique_raw)

nonzero_diffs = diffs[
    np.abs(diffs) > 1e-12
]

print("========================================")
print("TORQUE QUANTIZATION")
print("========================================")

print(f"Unique raw torque values: {len(unique_raw)}")

if len(nonzero_diffs) > 0:
    print(
        "Smallest raw torque step: "
        f"{np.min(np.abs(nonzero_diffs))}"
    )

print("Raw torque values:")
print(unique_raw)
print()


# ============================================================
# COULOMB + VISCOUS MODEL
# ============================================================

def coulomb_viscous(w, tau_c, b, offset):
    return (
        tau_c * np.sign(w)
        + b * w
        + offset
    )


cv_data = nonzero.copy()

w_cv = cv_data[
    "mean_velocity_rad_s"
].to_numpy()

tau_cv = cv_data[
    "mean_torque_Nm"
].to_numpy()

X = np.column_stack([
    np.sign(w_cv),
    w_cv,
    np.ones_like(w_cv),
])

params_cv, _, _, _ = np.linalg.lstsq(
    X,
    tau_cv,
    rcond=None,
)

tau_c_cv = params_cv[0]
b_cv = params_cv[1]
offset_cv = params_cv[2]

tau_pred_cv = coulomb_viscous(
    w_cv,
    tau_c_cv,
    b_cv,
    offset_cv,
)

ss_res_cv = np.sum(
    (tau_cv - tau_pred_cv) ** 2
)

ss_tot_cv = np.sum(
    (tau_cv - np.mean(tau_cv)) ** 2
)

r2_cv = (
    1.0 - ss_res_cv / ss_tot_cv
    if ss_tot_cv > 0
    else np.nan
)

print("========================================")
print("COULOMB + VISCOUS MODEL")
print("tau = tau_c*sign(w) + b*w + offset")
print("========================================")

print(f"tau_c:   {tau_c_cv:+.8f} Nm")
print(f"b:       {b_cv:+.8f} Nm/(rad/s)")
print(f"offset:  {offset_cv:+.8f} Nm")
print(f"R^2:     {r2_cv:.8f}")
print()


# ============================================================
# STRIBECK MODEL
# ============================================================

def stribeck_model(
    w,
    tau_c,
    tau_s,
    w_s,
    b,
    offset,
    n,
):
    abs_w = np.abs(w)

    friction_mag = (
        tau_c
        + (tau_s - tau_c)
        * np.exp(
            -np.power(
                abs_w / w_s,
                n,
            )
        )
    )

    return (
        np.sign(w) * friction_mag
        + b * w
        + offset
    )


stribeck_success = False
stribeck_params = None
stribeck_r2 = np.nan

if SCIPY_AVAILABLE and len(low_nonzero) >= 8:

    w_s_data = low_nonzero[
        "mean_velocity_rad_s"
    ].to_numpy()

    tau_s_data = low_nonzero[
        "mean_torque_Nm"
    ].to_numpy()

    try:

        initial_guess = [
            0.020,   # tau_c
            0.030,   # tau_s
            0.05,    # w_s
            0.003,   # b
            0.0,     # offset
            1.0,     # n
        ]

        lower_bounds = [
            0.0,
            0.0,
            0.001,
            0.0,
            -0.05,
            0.2,
        ]

        upper_bounds = [
            0.2,
            0.2,
            1.0,
            0.1,
            0.05,
            5.0,
        ]

        popt, pcov = curve_fit(
            stribeck_model,
            w_s_data,
            tau_s_data,
            p0=initial_guess,
            bounds=(
                lower_bounds,
                upper_bounds,
            ),
            maxfev=50000,
        )

        pred = stribeck_model(
            w_s_data,
            *popt,
        )

        ss_res = np.sum(
            (tau_s_data - pred) ** 2
        )

        ss_tot = np.sum(
            (
                tau_s_data
                - np.mean(tau_s_data)
            ) ** 2
        )

        stribeck_r2 = (
            1.0 - ss_res / ss_tot
            if ss_tot > 0
            else np.nan
        )

        stribeck_params = popt
        stribeck_success = True

    except Exception as exc:

        print(
            "Stribeck fit failed:",
            exc,
        )


print("========================================")
print("STRIBECK MODEL")
print("========================================")

if not SCIPY_AVAILABLE:

    print(
        "SciPy not installed. "
        "Install with:"
    )
    print(
        "sudo apt install python3-scipy"
    )

elif not stribeck_success:

    print("Stribeck fit was not successful.")

else:

    tau_c_s, tau_s_s, w_s_s, b_s, offset_s, n_s = (
        stribeck_params
    )

    print(f"tau_c:    {tau_c_s:+.8f} Nm")
    print(f"tau_s:    {tau_s_s:+.8f} Nm")
    print(f"w_s:      {w_s_s:+.8f} rad/s")
    print(f"b:        {b_s:+.8f} Nm/(rad/s)")
    print(f"offset:   {offset_s:+.8f} Nm")
    print(f"n:        {n_s:+.8f}")
    print(f"R^2:      {stribeck_r2:.8f}")

print()


# ============================================================
# SAVE TABLES
# ============================================================

summary.to_csv(
    OUTPUT_DIR / "per_sweep_summary.csv",
    index=False,
)

combined.to_csv(
    OUTPUT_DIR / "combined_summary.csv",
    index=False,
)

low_speed.to_csv(
    OUTPUT_DIR / "low_speed_summary.csv",
    index=False,
)

zero_summary.to_csv(
    OUTPUT_DIR / "zero_speed_summary.csv",
    index=False,
)

symmetry_df.to_csv(
    OUTPUT_DIR / "positive_negative_symmetry.csv",
    index=False,
)


# ============================================================
# PLOT 1 - FULL VELOCITY VS TIME
# ============================================================

t = (
    df["ros_time_s"]
    - df["ros_time_s"].iloc[0]
)

plt.figure(figsize=(13, 6))

plt.plot(
    t,
    df["measured_velocity_rad_s"],
    linewidth=0.7,
    label="Measured velocity",
)

plt.plot(
    t,
    df["command_velocity_rad_s"],
    linewidth=1.0,
    label="Command",
)

plt.xlabel("Time [s]")
plt.ylabel("Velocity [rad/s]")
plt.title("Velocity Command and Measured Velocity")
plt.grid(True)
plt.legend()
plt.tight_layout()

plt.savefig(
    FIG_DIR / "01_velocity_vs_time.png",
    dpi=200,
)

plt.close()


# ============================================================
# PLOT 2 - TORQUE VS TIME
# ============================================================

plt.figure(figsize=(13, 6))

plt.plot(
    t,
    df["torque_Nm"],
    linewidth=0.6,
)

plt.xlabel("Time [s]")
plt.ylabel("Torque [Nm]")
plt.title("Measured Torque vs Time")
plt.grid(True)
plt.tight_layout()

plt.savefig(
    FIG_DIR / "02_torque_vs_time.png",
    dpi=200,
)

plt.close()


# ============================================================
# PLOT 3 - COMMAND VS MEASURED VELOCITY
# ============================================================

plt.figure(figsize=(8, 8))

plt.errorbar(
    combined["command_velocity_rad_s"],
    combined["mean_velocity_rad_s"],
    yerr=combined[
        "std_velocity_between_sweeps"
    ].fillna(0),
    fmt="o",
    capsize=4,
)

limits = [
    min(
        combined[
            "command_velocity_rad_s"
        ].min(),
        combined[
            "mean_velocity_rad_s"
        ].min(),
    ),
    max(
        combined[
            "command_velocity_rad_s"
        ].max(),
        combined[
            "mean_velocity_rad_s"
        ].max(),
    ),
]

plt.plot(
    limits,
    limits,
    linestyle="--",
    label="Ideal y=x",
)

plt.xlabel("Command velocity [rad/s]")
plt.ylabel("Measured velocity [rad/s]")
plt.title("Velocity Tracking")
plt.grid(True)
plt.legend()
plt.tight_layout()

plt.savefig(
    OUTPUT_DIR
    / "03_command_vs_measured_velocity.png",
    dpi=200,
)

plt.close()


# ============================================================
# PLOT 4 - FULL TORQUE VS VELOCITY
# ============================================================

plt.figure(figsize=(9, 6))

plt.errorbar(
    combined["mean_velocity_rad_s"],
    combined["mean_torque_Nm"],
    yerr=combined[
        "std_torque_between_sweeps"
    ].fillna(0),
    fmt="o",
    capsize=4,
    label="Measured",
)

w_plot = np.linspace(
    combined["mean_velocity_rad_s"].min(),
    combined["mean_velocity_rad_s"].max(),
    1000,
)

plt.plot(
    w_plot,
    coulomb_viscous(
        w_plot,
        tau_c_cv,
        b_cv,
        offset_cv,
    ),
    linestyle="--",
    label="Coulomb + viscous",
)

plt.xlabel("Measured velocity [rad/s]")
plt.ylabel("Mean torque [Nm]")
plt.title("No-Load Torque vs Velocity")
plt.grid(True)
plt.legend()
plt.tight_layout()

plt.savefig(
    FIG_DIR / "04_torque_vs_velocity_full.png",
    dpi=200,
)

plt.close()


# ============================================================
# PLOT 5 - REPEATABILITY
# ============================================================

plt.figure(figsize=(10, 6))

for sweep in sorted(
    summary["sweep"].unique()
):

    temp = summary[
        summary["sweep"] == sweep
    ].sort_values(
        "mean_velocity_rad_s"
    )

    plt.plot(
        temp["mean_velocity_rad_s"],
        temp["mean_torque_Nm"],
        marker="o",
        label=f"Sweep {sweep}",
    )

plt.xlabel("Measured velocity [rad/s]")
plt.ylabel("Mean torque [Nm]")
plt.title("Torque-Velocity Repeatability")
plt.grid(True)
plt.legend()
plt.tight_layout()

plt.savefig(
    FIG_DIR / "05_sweep_repeatability.png",
    dpi=200,
)

plt.close()


# ============================================================
# PLOT 6 - TORQUE DISTRIBUTION
# ============================================================

ordered_commands = sorted(
    df["command_velocity_rad_s"].unique()
)

box_data = [
    df[
        np.isclose(
            df["command_velocity_rad_s"],
            cmd,
        )
    ]["torque_Nm"].to_numpy()
    for cmd in ordered_commands
]

plt.figure(figsize=(16, 7))

plt.boxplot(
    box_data,
    tick_labels=[
        f"{x:g}"
        for x in ordered_commands
    ],
    showfliers=False,
)

plt.xlabel("Command velocity [rad/s]")
plt.ylabel("Torque [Nm]")
plt.title("Torque Distribution by Command Velocity")
plt.xticks(rotation=90)
plt.grid(True)
plt.tight_layout()

plt.savefig(
    FIG_DIR / "06_torque_distribution.png",
    dpi=200,
)

plt.close()


# ============================================================
# PLOT 7 - LOW-SPEED TORQUE VS VELOCITY
# ============================================================

plt.figure(figsize=(10, 7))

plt.errorbar(
    low_speed["mean_velocity_rad_s"],
    low_speed["mean_torque_Nm"],
    yerr=low_speed[
        "std_torque_between_sweeps"
    ].fillna(0),
    fmt="o",
    capsize=4,
    label="Measured",
)

plt.axvline(
    0.0,
    linewidth=0.8,
)

plt.axhline(
    0.0,
    linewidth=0.8,
)

plt.xlabel("Measured velocity [rad/s]")
plt.ylabel("Mean torque [Nm]")
plt.title(
    "Low-Speed Friction Region"
)
plt.grid(True)
plt.legend()
plt.tight_layout()

plt.savefig(
    OUTPUT_DIR
    / "07_low_speed_torque_vs_velocity.png",
    dpi=250,
)

plt.close()


# ============================================================
# PLOT 8 - LOW-SPEED VELOCITY TRACKING
# ============================================================

plt.figure(figsize=(9, 7))

plt.errorbar(
    low_speed["command_velocity_rad_s"],
    low_speed["mean_velocity_rad_s"],
    yerr=low_speed[
        "std_velocity_between_sweeps"
    ].fillna(0),
    fmt="o",
    capsize=4,
)

low_lim = LOW_SPEED_LIMIT * 1.1

plt.plot(
    [-low_lim, low_lim],
    [-low_lim, low_lim],
    linestyle="--",
)

plt.xlim(
    -low_lim,
    low_lim,
)

plt.ylim(
    -low_lim,
    low_lim,
)

plt.xlabel("Command velocity [rad/s]")
plt.ylabel("Measured velocity [rad/s]")
plt.title("Low-Speed Velocity Tracking")
plt.grid(True)
plt.tight_layout()

plt.savefig(
    OUTPUT_DIR
    / "08_low_speed_velocity_tracking.png",
    dpi=250,
)

plt.close()


# ============================================================
# PLOT 9 - STRIBECK FIT
# ============================================================

if stribeck_success:

    plt.figure(figsize=(10, 7))

    plt.scatter(
        low_nonzero["mean_velocity_rad_s"],
        low_nonzero["mean_torque_Nm"],
        label="Measured",
    )

    w_fit = np.linspace(
        -LOW_SPEED_LIMIT,
        LOW_SPEED_LIMIT,
        1000,
    )

    w_fit = w_fit[
        np.abs(w_fit) > 1e-6
    ]

    plt.plot(
        w_fit,
        stribeck_model(
            w_fit,
            *stribeck_params,
        ),
        linewidth=1.5,
        label="Stribeck fit",
    )

    plt.xlabel("Measured velocity [rad/s]")
    plt.ylabel("Mean torque [Nm]")
    plt.title(
        f"Stribeck Friction Fit, R²={stribeck_r2:.5f}"
    )
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        FIG_DIR / "09_stribeck_fit.png",
        dpi=250,
    )

    plt.close()


# ============================================================
# GLOBAL CHECKS
# ============================================================

print("========================================")
print("GLOBAL CHECKS")
print("========================================")

print(
    "Maximum absolute velocity error: "
    f"{summary['abs_velocity_error_rad_s'].max():.8f} rad/s"
)

print(
    "Mean absolute velocity error: "
    f"{summary['abs_velocity_error_rad_s'].mean():.8f} rad/s"
)

print(
    "Maximum velocity std: "
    f"{summary['std_velocity_rad_s'].max():.8f} rad/s"
)

print(
    "Maximum torque std: "
    f"{summary['std_torque_Nm'].max():.8f} Nm"
)

print(
    "Torque range: "
    f"{df['torque_Nm'].min():+.8f} "
    "to "
    f"{df['torque_Nm'].max():+.8f} Nm"
)

print()

print("Analysis files saved to:")
print(OUTPUT_DIR)
print()

for path in sorted(OUTPUT_DIR.iterdir()):
    print(" ", path.name)


# ============================================================
# PLOT 10 - FRICTION COMPONENT DECOMPOSITION
# ============================================================

if stribeck_success:

    tau_c_s, tau_s_s, w_s_s, b_s, offset_s, n_s = stribeck_params

    w_comp = np.linspace(
        -5.0,
        5.0,
        2000,
    )

    # Avoid exactly zero for sign-based components
    w_comp_nozero = w_comp.copy()
    w_comp_nozero[
        np.abs(w_comp_nozero) < 1e-9
    ] = 1e-9

    sign_w = np.sign(w_comp_nozero)
    abs_w = np.abs(w_comp_nozero)

    # Coulomb component
    tau_coulomb = (
        tau_c_s * sign_w
    )

    # Viscous component
    tau_viscous = (
        b_s * w_comp_nozero
    )

    # Stribeck contribution ABOVE the Coulomb level
    tau_stribeck = (
        (tau_s_s - tau_c_s)
        * np.exp(
            -np.power(
                abs_w / w_s_s,
                n_s,
            )
        )
        * sign_w
    )

    # Offset / bias
    tau_offset = np.full_like(
        w_comp_nozero,
        offset_s,
    )

    # Total model
    tau_total = (
        tau_coulomb
        + tau_viscous
        + tau_stribeck
        + tau_offset
    )

    plt.figure(figsize=(11, 7))

    plt.plot(
        w_comp_nozero,
        tau_coulomb,
        linewidth=1.5,
        label="Coulomb friction",
    )

    plt.plot(
        w_comp_nozero,
        tau_viscous,
        linewidth=1.5,
        label="Viscous friction",
    )

    plt.plot(
        w_comp_nozero,
        tau_stribeck,
        linewidth=1.5,
        label="Stribeck contribution",
    )

    plt.plot(
        w_comp_nozero,
        tau_total,
        linewidth=2.0,
        label="Total fitted friction",
    )

    plt.scatter(
        combined["mean_velocity_rad_s"],
        combined["mean_torque_Nm"],
        s=25,
        label="Measured mean torque",
    )

    plt.axhline(
        0.0,
        linewidth=0.8,
    )

    plt.axvline(
        0.0,
        linewidth=0.8,
    )

    plt.xlabel(
        "Velocity [rad/s]"
    )

    plt.ylabel(
        "Torque [Nm]"
    )

    plt.title(
        "Friction Model Decomposition"
    )

    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        / "10_friction_component_decomposition.png",
        dpi=250,
    )

    plt.close()


# ============================================================
# PLOT 11 - LOW-SPEED FRICTION COMPONENT DECOMPOSITION
# ============================================================

if stribeck_success:

    w_low = np.linspace(
        -LOW_SPEED_LIMIT,
        LOW_SPEED_LIMIT,
        2000,
    )

    w_low_nozero = w_low.copy()
    w_low_nozero[
        np.abs(w_low_nozero) < 1e-9
    ] = 1e-9

    sign_w = np.sign(
        w_low_nozero
    )

    abs_w = np.abs(
        w_low_nozero
    )

    tau_coulomb_low = (
        tau_c_s * sign_w
    )

    tau_viscous_low = (
        b_s * w_low_nozero
    )

    tau_stribeck_low = (
        (tau_s_s - tau_c_s)
        * np.exp(
            -np.power(
                abs_w / w_s_s,
                n_s,
            )
        )
        * sign_w
    )

    tau_total_low = (
        tau_coulomb_low
        + tau_viscous_low
        + tau_stribeck_low
        + offset_s
    )

    plt.figure(figsize=(11, 7))

    plt.plot(
        w_low_nozero,
        tau_coulomb_low,
        linewidth=1.5,
        label="Coulomb friction",
    )

    plt.plot(
        w_low_nozero,
        tau_viscous_low,
        linewidth=1.5,
        label="Viscous friction",
    )

    plt.plot(
        w_low_nozero,
        tau_stribeck_low,
        linewidth=1.5,
        label="Stribeck contribution",
    )

    plt.plot(
        w_low_nozero,
        tau_total_low,
        linewidth=2.0,
        label="Total fitted friction",
    )

    plt.scatter(
        low_speed["mean_velocity_rad_s"],
        low_speed["mean_torque_Nm"],
        s=35,
        label="Measured mean torque",
    )

    plt.axhline(
        tau_c_s,
        linestyle="--",
        linewidth=1.0,
        label=f"+ Coulomb level = {tau_c_s:.4f} Nm",
    )

    plt.axhline(
        -tau_c_s,
        linestyle="--",
        linewidth=1.0,
        label=f"- Coulomb level = {-tau_c_s:.4f} Nm",
    )

    plt.axhline(
        tau_s_s,
        linestyle=":",
        linewidth=1.0,
        label=f"+ Static/Stribeck level = {tau_s_s:.4f} Nm",
    )

    plt.axhline(
        -tau_s_s,
        linestyle=":",
        linewidth=1.0,
        label=f"- Static/Stribeck level = {-tau_s_s:.4f} Nm",
    )

    plt.xlabel(
        "Velocity [rad/s]"
    )

    plt.ylabel(
        "Torque [Nm]"
    )

    plt.title(
        "Low-Speed Friction Decomposition"
    )

    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.savefig(
        OUTPUT_DIR
        / "11_low_speed_friction_decomposition.png",
        dpi=250,
    )

    plt.close()


# ============================================================
# SAVE FIT PARAMETERS
# ============================================================

if stribeck_success:

    fit_parameters = pd.DataFrame(
        [
            {
                "parameter":
                    "Coulomb friction tau_c",
                "value":
                    tau_c_s,
                "unit":
                    "Nm",
            },
            {
                "parameter":
                    "Static/Stribeck torque tau_s",
                "value":
                    tau_s_s,
                "unit":
                    "Nm",
            },
            {
                "parameter":
                    "Stribeck characteristic velocity w_s",
                "value":
                    w_s_s,
                "unit":
                    "rad/s",
            },
            {
                "parameter":
                    "Viscous coefficient b",
                "value":
                    b_s,
                "unit":
                    "Nm/(rad/s)",
            },
            {
                "parameter":
                    "Torque offset",
                "value":
                    offset_s,
                "unit":
                    "Nm",
            },
            {
                "parameter":
                    "Stribeck exponent n",
                "value":
                    n_s,
                "unit":
                    "-",
            },
            {
                "parameter":
                    "Stribeck model R2",
                "value":
                    stribeck_r2,
                "unit":
                    "-",
            },
            {
                "parameter":
                    "Coulomb+viscous tau_c",
                "value":
                    tau_c_cv,
                "unit":
                    "Nm",
            },
            {
                "parameter":
                    "Coulomb+viscous b",
                "value":
                    b_cv,
                "unit":
                    "Nm/(rad/s)",
            },
            {
                "parameter":
                    "Coulomb+viscous offset",
                "value":
                    offset_cv,
                "unit":
                    "Nm",
            },
            {
                "parameter":
                    "Coulomb+viscous R2",
                "value":
                    r2_cv,
                "unit":
                    "-",
            },
        ]
    )

    fit_parameters.to_csv(
        OUTPUT_DIR
        / "friction_model_parameters.csv",
        index=False,
    )

    print()
    print("========================================")
    print("FRICTION COMPONENT PARAMETERS")
    print("========================================")

    print(
        f"Coulomb friction:        "
        f"{tau_c_s:.8f} Nm"
    )

    print(
        f"Static/Stribeck torque:  "
        f"{tau_s_s:.8f} Nm"
    )

    print(
        f"Stribeck velocity:        "
        f"{w_s_s:.8f} rad/s"
    )

    print(
        f"Viscous coefficient:      "
        f"{b_s:.8f} Nm/(rad/s)"
    )

    print(
        f"Torque offset:            "
        f"{offset_s:.8f} Nm"
    )

    print(
        f"Stribeck exponent:        "
        f"{n_s:.8f}"
    )

    print(
        f"Stribeck model R²:        "
        f"{stribeck_r2:.8f}"
    )

    print()
