import simpy
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ── Configuration ────────────────────────────────────────────────
RANDOM_SEED = 42
SIM_DURATION = 480       # minutes (one 8-hour shift)
SAMPLE_INTERVAL = 1      # minutes between tag readings
np.random.seed(RANDOM_SEED)

# ── Tag log (shared state) ────────────────────────────────────────
tag_log = []

# ── Normal operating parameters ──────────────────────────────────
NORMAL_PARAMS = {
    "PUMP_FLOW":           {"mean": 606, "std": 12},
    "PUMP_INLET_PRESS":    {"mean": 0.5, "std": 0.05},
    "PUMP_OUTLET_PRESS":   {"mean": 2.7, "std": 0.3},
    "PUMP_MOTOR_CURRENT":  {"mean": 44, "std": 4},
    "PUMP_BEARING_TEMP":   {"mean": 55,  "std": 2},
    "PUMP_VIBRATION":     {"mean": 2.5, "std": 0.3},
}

def apply_fault(tag_values, fault_type, severity=1.0):
    """
    Modifies tag values in-place based on fault type and severity (0.0 to 1.0).
    Severity ramps up over time to simulate gradual degradation.
    """
    if fault_type == "cavitation":
        # Low suction pressure, erratic flow, high vibration, high current
        tag_values["PUMP_INLET_PRESS"]   *= (1 - 0.4 * severity)
        tag_values["PUMP_FLOW"]          *= (1 - 0.3 * severity)
        tag_values["PUMP_VIBRATION"]     *= (1 + 1.5 * severity)
        tag_values["PUMP_MOTOR_CURRENT"] *= (1 + 0.2 * severity)

    elif fault_type == "bearing_wear":
        # Gradually rising vibration and temperature, slight current increase
        tag_values["PUMP_VIBRATION"]     *= (1 + 2.0 * severity)
        tag_values["PUMP_BEARING_TEMP"]  *= (1 + 0.3 * severity)
        tag_values["PUMP_MOTOR_CURRENT"] *= (1 + 0.1 * severity)

    elif fault_type == "seal_leak":
        # Flow drop, outlet pressure drop, slight inlet pressure drop
        tag_values["PUMP_FLOW"]          *= (1 - 0.25 * severity)
        tag_values["PUMP_OUTLET_PRESS"]  *= (1 - 0.2 * severity)
        tag_values["PUMP_INLET_PRESS"]   *= (1 - 0.1 * severity)

    elif fault_type == "plugged_discharge":
        # Flow drop, outlet pressure spike, bearing temp rise
        tag_values["PUMP_FLOW"]          *= (1 - 0.5 * severity)
        tag_values["PUMP_OUTLET_PRESS"]  *= (1 + 0.15 * severity)
        tag_values["PUMP_BEARING_TEMP"]  *= (1 + 0.3 * severity)

    return tag_values



def pump_process(env, fault_type=None, fault_start=None, fault_ramp=60):
    """
    SimPy process: samples pump tags every SAMPLE_INTERVAL minutes.
    Optionally injects a fault starting at fault_start, ramping severity
    over fault_ramp minutes to simulate gradual degradation.
    """
    while True:
        # Sample base tag values with Gaussian noise
        tag_values = {
            tag: np.random.normal(p["mean"], p["std"])
            for tag, p in NORMAL_PARAMS.items()
        }

        # Apply fault if active
        if fault_type and fault_start is not None:
            if env.now >= fault_start:
                elapsed = env.now - fault_start
                severity = min(elapsed / fault_ramp, 1.0)  # ramps 0→1
                tag_values = apply_fault(tag_values, fault_type, severity)

        # Log the reading
        tag_log.append({"time": env.now, **tag_values})

        yield env.timeout(SAMPLE_INTERVAL)


def run_simulation(fault_type=None, fault_start=240):
    """Run the simulation and return a DataFrame of tag history."""
    global tag_log
    tag_log = []

    env = simpy.Environment()
    env.process(pump_process(env, fault_type=fault_type, fault_start=fault_start))
    env.run(until=SIM_DURATION)

    return pd.DataFrame(tag_log)

if __name__ == "__main__":
    # Run normal operation
    df_normal = run_simulation(fault_type=None)
    print("Normal run:")
    print(df_normal.tail())

    # Run with cavitation fault injected at t=240 min
    df_fault = run_simulation(fault_type="cavitation", fault_start=240)
    print("\nCavitation fault run:")
    print(df_fault[235:250])   # inspect the transition window


def get_tag_history(df, tag_name, window=30):
    """Returns the last `window` readings for a given tag."""
    return df[["time", tag_name]].tail(window)

def get_latest_tags(df):
    """Returns the most recent reading for all tags."""
    return df.iloc[-1].to_dict()

def get_tag_stats(df, window=30):
    """Returns mean and std for all tags over the last `window` readings."""
    recent = df.tail(window)
    return recent.describe().loc[["mean", "std"]]


def visualize_tags(df, fault_start=None, save_path=None, dpi=150, show=True):
    """Plot all pump tags over time in separate subplots.

    If `fault_start` is provided (numeric time), draw a vertical red dashed
    line at that timestamp to indicate when the fault began. If `save_path`
    is provided the figure will be saved to that path (PNG recommended).

    Args:
        df: DataFrame containing `time` and tag columns.
        fault_start: optional numeric timestamp to mark fault start.
        save_path: optional path to save the figure (e.g. 'pump_tags.png').
        dpi: resolution for saved figure.
        show: if True, call `plt.show()` to display the figure.
    """
    tags = [
        "PUMP_FLOW",
        "PUMP_INLET_PRESS",
        "PUMP_OUTLET_PRESS",
        "PUMP_VIBRATION",
        "PUMP_MOTOR_CURRENT",
        "PUMP_BEARING_TEMP",
    ]

    fig, axes = plt.subplots(len(tags), 1, figsize=(10, 12), sharex=True)

    time = df["time"]
    for ax, tag in zip(axes, tags):
        if tag not in df.columns:
            continue
        ax.plot(time, df[tag], label=tag)
        ax.set_ylabel(tag)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right")
        if fault_start is not None:
            ax.axvline(fault_start, color="red", linestyle="--", linewidth=1)

    axes[-1].set_xlabel("Time (minutes)")
    fig.tight_layout()

    if save_path:
        try:
            fig.savefig(save_path, dpi=dpi, bbox_inches="tight")
        except Exception:
            # attempt to save as PNG if extension omitted
            if not save_path.lower().endswith(".png"):
                fig.savefig(f"{save_path}.png", dpi=dpi, bbox_inches="tight")
            else:
                raise

    if show:
        plt.show()

    return fig

