import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import RESULT_DIR


def normalize_columns(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        min_v = out[col].min()
        max_v = out[col].max()
        if max_v - min_v < 1e-12:
            out[col] = 0.5
        else:
            out[col] = (out[col] - min_v) / (max_v - min_v)
    return out


def main():
    sns.set_theme(style="whitegrid")
    in_path = RESULT_DIR / "generator_ablation" / "summary.csv"
    out_dir = RESULT_DIR / "paper_figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(in_path)
    display_map = {
        "full": "Full",
        "no_motif": "No motif",
        "no_composition": "No comp",
        "no_uncertainty": "No uncert",
        "quality_only": "Quality only",
    }
    df["variant_label"] = df["variant"].map(display_map).fillna(df["variant"])

    metric_cols = [
        "pairwise_jaccard_diversity",
        "mean_predicted_positive_prob",
        "mean_predicted_permeability",
        "mean_motif_score",
        "mean_composition_alignment",
        "mean_uncertainty_stability",
    ]
    heatmap_df = normalize_columns(df[["variant_label"] + metric_cols], metric_cols).set_index("variant_label")
    heatmap_df.columns = ["Diversity", "Prob", "Perm", "Motif", "Comp", "Stable"]

    fig = plt.figure(figsize=(13, 5.5))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.2, 1.0], wspace=0.22)

    ax0 = fig.add_subplot(gs[0, 0])
    sns.heatmap(
        heatmap_df,
        cmap="YlGnBu",
        linewidths=1.0,
        linecolor="white",
        cbar_kws={"label": "Normalized score"},
        annot=True,
        fmt=".2f",
        ax=ax0,
    )
    ax0.set_title("Generator Component Ablation", fontsize=13, pad=10)
    ax0.set_xlabel("")
    ax0.set_ylabel("")

    ax1 = fig.add_subplot(gs[0, 1])
    plot_df = df.copy()
    colors = {
        "Full": "#0f766e",
        "No motif": "#3b82f6",
        "No comp": "#f59e0b",
        "No uncert": "#ef4444",
        "Quality only": "#7c3aed",
    }
    for _, row in plot_df.iterrows():
        label = row["variant_label"]
        ax1.scatter(
            row["pairwise_jaccard_diversity"],
            row["mean_predicted_positive_prob"],
            s=120 + 900 * max(row["mean_composition_alignment"], 0.0),
            color=colors.get(label, "#334155"),
            edgecolor="white",
            linewidth=1.0,
            alpha=0.92,
        )
        ax1.text(
            row["pairwise_jaccard_diversity"] + 0.001,
            row["mean_predicted_positive_prob"] + 0.0005,
            label,
            fontsize=9,
        )
    ax1.set_title("Quality-Diversity Tradeoff Across Ablations", fontsize=13, pad=10)
    ax1.set_xlabel("Pairwise Jaccard diversity")
    ax1.set_ylabel("Mean predicted positive probability")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.grid(alpha=0.25, linestyle="--")

    fig.suptitle("Figure 9. Multi-objective generator ablation", fontsize=15, y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out_path = out_dir / "figure9_generator_ablation.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved generator ablation figure to: {out_path}")


if __name__ == "__main__":
    main()
