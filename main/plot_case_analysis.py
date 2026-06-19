import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import RESULT_DIR


PALETTE = {
    "ink": "#27313A",
    "blue": "#315C72",
    "green": "#8FAF6B",
    "gold": "#D9A441",
    "rust": "#B85C47",
    "sand": "#F3EFE2",
}


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.18, linewidth=0.8)
    ax.tick_params(labelsize=9)


def short_label(helm, fallback):
    if not isinstance(helm, str) or "{" not in helm:
        return fallback
    inside = helm.split("{", 1)[1].split("}", 1)[0]
    inside = inside.replace("[", "").replace("]", "")
    return inside[:26]


def main():
    case_path = RESULT_DIR / "case_analysis" / "representative_cases.csv"
    shift_path = RESULT_DIR / "case_analysis" / "case_descriptor_shift_long.csv"
    out_dir = RESULT_DIR / "paper_figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    case_df = pd.read_csv(case_path)
    shift_df = pd.read_csv(shift_path)

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.5), gridspec_kw={"width_ratios": [1.05, 1.1]})

    top_cases = (
        case_df.sort_values(["route", "predicted_positive_prob", "predicted_permeability"], ascending=[True, False, False])
        .groupby("route", as_index=False)
        .head(2)
        .copy()
        .reset_index(drop=True)
    )
    top_cases["label"] = [f"{'O' if r == 'optimized' else 'D'}{i+1}" for i, r in enumerate(top_cases["route"])]

    colors = {"optimized": PALETTE["blue"], "de_novo": PALETTE["gold"]}
    ax = axes[0]
    for _, row in top_cases.iterrows():
        ax.scatter(
            row["predicted_permeability"],
            row["predicted_positive_prob"],
            s=170,
            color=colors[row["route"]],
            edgecolor="white",
            linewidth=1.0,
            zorder=3,
        )
        ax.annotate(
            row["label"],
            (row["predicted_permeability"], row["predicted_positive_prob"]),
            xytext=(4, 6),
            textcoords="offset points",
            fontsize=9,
            weight="bold",
            color=PALETTE["ink"],
        )
    ax.set_title("Representative candidate cases")
    ax.set_xlabel("Predicted permeability")
    ax.set_ylabel("Predicted positive probability")
    style_ax(ax)

    descriptor_focus = (
        shift_df.loc[shift_df["descriptor"].isin(["MolLogP_mean", "TPSA_mean", "n_methyl_ratio", "d_ratio"])]
        .copy()
    )
    descriptor_focus = descriptor_focus.merge(
        top_cases[["candidate_helm", "label", "route"]],
        on="candidate_helm",
        how="inner",
        suffixes=("", "_top"),
    )
    if "route_top" in descriptor_focus.columns:
        descriptor_focus["route"] = descriptor_focus["route_top"]
    descriptor_focus = descriptor_focus.loc[descriptor_focus["delta_to_reference"].abs() > 0.015].copy()
    descriptor_focus["plot_label"] = descriptor_focus["label"] + " " + descriptor_focus["descriptor"].str.replace("_mean", "", regex=False)

    ax = axes[1]
    if len(descriptor_focus) > 0:
        descriptor_focus = descriptor_focus.sort_values("delta_to_reference")
        y_pos = range(len(descriptor_focus))
        bar_colors = [colors[r] for r in descriptor_focus["route"]]
        ax.barh(
            list(y_pos),
            descriptor_focus["delta_to_reference"],
            color=bar_colors,
            alpha=0.9,
        )
        ax.axvline(0, color=PALETTE["ink"], lw=1.0)
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(descriptor_focus["plot_label"])
        ax.set_xlabel("Candidate - nearest high-permeability reference")
        ax.set_title("Descriptor shift toward reference motifs")
        style_ax(ax)
    else:
        ax.axis("off")
        ax.text(0.5, 0.5, "No large descriptor shift", ha="center", va="center", fontsize=11, color=PALETTE["ink"])

    axes[0].text(-0.14, 1.05, "A", transform=axes[0].transAxes, fontsize=15, weight="bold")
    axes[1].text(-0.14, 1.05, "B", transform=axes[1].transAxes, fontsize=15, weight="bold")

    fig.tight_layout()
    out_path = out_dir / "figure5_case_analysis.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)

    legend_rows = []
    for _, row in top_cases.iterrows():
        legend_rows.append(
            {
                "label": row["label"],
                "route": row["route"],
                "candidate_short": short_label(row["candidate_helm"], row["label"]),
                "parent_short": short_label(row["parent_helm"], row["label"]),
                "reference_short": short_label(row["reference_helm"], row["label"]),
                "mutation_description": row.get("mutation_description", ""),
            }
        )
    pd.DataFrame(legend_rows).to_csv(RESULT_DIR / "case_analysis" / "case_label_legend.csv", index=False)

    print(f"Saved case analysis figure to: {out_path}")
    print(pd.DataFrame(legend_rows).to_string(index=False))


if __name__ == "__main__":
    main()
