import os
import textwrap

import anthropic

from simulator import run_simulation, get_tag_stats, NORMAL_PARAMS, visualize_tags


def build_comparison_text(stats_df):
    lines = []
    for tag, params in NORMAL_PARAMS.items():
        if tag not in stats_df.columns:
            continue
        recent_mean = float(stats_df.loc["mean", tag])
        recent_std  = float(stats_df.loc["std",  tag])
        normal_mean = params["mean"]
        normal_std  = params["std"]
        z = (recent_mean - normal_mean) / (normal_std if normal_std else 1.0)
        lines.append(
            f"{tag}:\n"
            f"  recent  mean={recent_mean:.3f}  std={recent_std:.3f}\n"
            f"  normal  mean={normal_mean}      std={normal_std}\n"
            f"  z-score={z:+.2f}"
        )
    return "\n".join(lines)


def run_analysis(df) -> str:
    """Analyze a pump simulation DataFrame and return Claude's RCA as a string.

    Args:
        df: DataFrame produced by run_simulation(), containing time and tag columns.

    Returns:
        Claude's plain-text diagnosis.
    """
    stats = get_tag_stats(df, window=30)
    context_text = build_comparison_text(stats)

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    system_prompt = textwrap.dedent("""\
        You are a senior process engineer specializing in centrifugal pump diagnostics.
        You will be given recent sensor tag statistics (last 30 readings) compared against
        known normal operating ranges expressed as mean ± std. The z-score indicates how
        many standard deviations the recent mean is from normal.

        Use the fault fingerprint table below to identify the fault. Match the observed
        z-score pattern to the expected pattern — pay attention to tags that are NOT
        elevated as much as tags that are, since the absence of a deviation is equally
        diagnostic.

        FAULT FINGERPRINTS (expected z-score directions at fault severity):
        Tag                  | Cavitation | Bearing Wear | Seal Leak | Plugged Discharge
        ---------------------|------------|--------------|-----------|------------------
        PUMP_FLOW            | large -    | neutral      | moderate -| large -
        PUMP_INLET_PRESS     | large -    | neutral      | slight -  | neutral
        PUMP_OUTLET_PRESS    | neutral    | neutral      | moderate -| moderate +
        PUMP_VIBRATION       | large +    | very large + | neutral   | neutral
        PUMP_MOTOR_CURRENT   | slight +   | slight +     | neutral   | neutral
        PUMP_BEARING_TEMP    | neutral    | large +      | neutral   | large +

        Key discriminators:
        - Cavitation vs Bearing Wear: cavitation shows LOW inlet pressure and LOW flow;
          bearing wear shows ELEVATED bearing temp with NORMAL pressure and flow.
        - Cavitation vs Plugged Discharge: cavitation shows LOW inlet pressure;
          plugged discharge shows HIGH outlet pressure with LOW flow.
        - Seal Leak vs others: no vibration spike; outlet pressure drops with flow.

        Based on the data, determine:
        1. Whether a fault is present.
        2. The most likely fault type with your reasoning tied to specific tag z-scores
           and how they match (or don't match) the fingerprint table.
        3. The recommended next action — including immediate mitigations, triage steps,
           and monitoring guidance.

        Be concise and structured. Ground every conclusion in the tag data provided.
    """)

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=800,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": (
                    "Here are the recent tag statistics (last 30 samples) vs normal ranges:\n\n"
                    f"{context_text}\n\n"
                    "Is a fault present? If so, which fault type and why? "
                    "What is the recommended next action?"
                ),
            }
        ],
    )

    return message.content[0].text


def main():
    fault_start = 240
    print("Running simulation with cavitation fault at t=240...")
    df = run_simulation(fault_type="cavitation", fault_start=fault_start)

    visualize_tags(df, fault_start=fault_start, save_path="pump_tags.png", show=False)
    print("Chart saved to pump_tags.png")

    print("\nRunning analysis...")
    result = run_analysis(df)
    print("\n" + "=" * 60)
    print("Claude's diagnosis:")
    print("=" * 60)
    print(result.encode("utf-8", errors="replace").decode("utf-8"))


if __name__ == "__main__":
    main()
