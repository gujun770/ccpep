import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import RESULT_DIR


def main():
    sns.set_theme(style="whitegrid")
    detail_df = pd.read_csv(RESULT_DIR / "candidate_novelty_depth" / "candidate_nearest_neighbors.csv")
    summary_df = pd.read_csv(RESULT_DIR / "candidate_novelty_depth" / "summary.csv")

    out_dir = RESULT_DIR / "paper_figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(13.5, 8))
    gs = fig.add_gridspec(2, 2, hspace=0.28, wspace=0.24)

    palette = {"optimized_shortlist": "#ef4444", "de_novo_shortlist": "#2563eb"}

    ax0 = fig.add_subplot(gs[0, 0])
    sns.violinplot(
        data=detail_df,
        x="route",
        y="nearest_train_token_jaccard",
        palette=palette,
        inner="box",
        cut=0,
        ax=ax0,
    )
    ax0.set_title("Nearest train token similarity", fontsize=13)
    ax0.set_xlabel("")
    ax0.set_ylabel("Nearest train token Jaccard")
    ax0.set_xticklabels(["Optimized", "De novo"])
    ax0.spines["top"].set_visible(False)
    ax0.spines["right"].set_visible(False)

    ax1 = fig.add_subplot(gs[0, 1])
    sns.violinplot(
        data=detail_df,
        x="route",
        y="nearest_descriptor_distance",
        palette=palette,
        inner="box",
        cut=0,
        ax=ax1,
    )
    ax1.set_title("Nearest train descriptor distance", fontsize=13)
    ax1.set_xlabel("")
    ax1.set_ylabel("Euclidean distance")
    ax1.set_xticklabels(["Optimized", "De novo"])
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    ax2 = fig.add_subplot(gs[1, 0])
    sns.scatterplot(
        data=detail_df,
        x="nearest_train_token_jaccard",
        y="predicted_permeability",
        hue="route",
        palette=palette,
        s=90,
        alpha=0.85,
        ax=ax2,
    )
    ax2.set_title("Novelty vs predicted permeability", fontsize=13)
    ax2.set_xlabel("Nearest train token Jaccard")
    ax2.set_ylabel("Predicted permeability")
    ax2.legend(title="", labels=["Optimized", "De novo"])
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    ax3 = fig.add_subplot(gs[1, 1])
    bar_df = summary_df.melt(
        id_vars="route",
        value_vars=["mean_nearest_train_token_jaccard", "mean_nearest_descriptor_distance"],
        var_name="metric",
        value_name="value",
    )
    bar_df["metric"] = bar_df["metric"].map(
        {
            "mean_nearest_train_token_jaccard": "Mean token similarity",
            "mean_nearest_descriptor_distance": "Mean descriptor distance",
        }
    )
    sns.barplot(
        data=bar_df,
        x="metric",
        y="value",
        hue="route",
        palette=palette,
        ax=ax3,
    )
    ax3.set_title("Route-level novelty summary", fontsize=13)
    ax3.set_xlabel("")
    ax3.set_ylabel("Value")
    ax3.legend(title="", labels=["Optimized", "De novo"])
    ax3.tick_params(axis="x", rotation=10)
    ax3.spines["top"].set_visible(False)
    ax3.spines["right"].set_visible(False)

    fig.suptitle("Figure 12. Deep novelty analysis against training peptides", fontsize=16, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    out_path = out_dir / "figure12_novelty_depth.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved novelty-depth figure to: {out_path}")


if __name__ == "__main__":
    main()
