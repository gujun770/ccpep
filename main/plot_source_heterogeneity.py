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
    per_source = pd.read_csv(RESULT_DIR / "source_heterogeneity" / "per_source_metrics.csv")
    out_dir = RESULT_DIR / "paper_figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(14, 8.5))
    gs = fig.add_gridspec(2, 2, hspace=0.30, wspace=0.24)

    ax0 = fig.add_subplot(gs[0, 0])
    plot_df = per_source.sort_values("cls_auroc", ascending=False).copy()
    sns.barplot(data=plot_df, x="cls_auroc", y="source", color="#2563eb", ax=ax0)
    ax0.set_title("LOSO AUROC by source", fontsize=13)
    ax0.set_xlabel("AUROC")
    ax0.set_ylabel("")
    ax0.set_xlim(0.0, 1.02)
    ax0.spines["top"].set_visible(False)
    ax0.spines["right"].set_visible(False)

    ax1 = fig.add_subplot(gs[0, 1])
    scatter = ax1.scatter(
        per_source["test_samples"],
        per_source["cls_auroc"],
        s=40 + per_source["permeability_std"] * 120,
        c=per_source["cls_mcc"],
        cmap="viridis",
        alpha=0.9,
        edgecolor="white",
        linewidth=0.8,
    )
    ax1.set_xscale("log")
    ax1.set_title("Source size vs AUROC", fontsize=13)
    ax1.set_xlabel("Test samples (log scale)")
    ax1.set_ylabel("AUROC")
    cbar = fig.colorbar(scatter, ax=ax1, fraction=0.046, pad=0.04)
    cbar.set_label("MCC")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    ax2 = fig.add_subplot(gs[1, 0])
    sns.scatterplot(
        data=per_source,
        x="permeability_std",
        y="cls_auroc",
        size="test_samples",
        sizes=(60, 400),
        hue="reg_r2",
        palette="coolwarm",
        ax=ax2,
        legend=False,
    )
    ax2.set_title("Source variability vs AUROC", fontsize=13)
    ax2.set_xlabel("Permeability std within source")
    ax2.set_ylabel("AUROC")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    ax3 = fig.add_subplot(gs[1, 1])
    box_df = per_source.melt(
        value_vars=["reg_r2", "cls_auroc", "cls_mcc"],
        var_name="metric",
        value_name="value",
    )
    box_df["metric"] = box_df["metric"].map(
        {"reg_r2": "R²", "cls_auroc": "AUROC", "cls_mcc": "MCC"}
    )
    sns.boxplot(data=box_df, x="metric", y="value", palette=["#f59e0b", "#2563eb", "#10b981"], ax=ax3)
    sns.stripplot(data=box_df, x="metric", y="value", color="#0f172a", size=4, alpha=0.6, ax=ax3)
    ax3.set_title("Distribution of LOSO source metrics", fontsize=13)
    ax3.set_xlabel("")
    ax3.set_ylabel("Value")
    ax3.spines["top"].set_visible(False)
    ax3.spines["right"].set_visible(False)

    fig.suptitle("Figure 11. Source heterogeneity under leave-one-source-out evaluation", fontsize=16, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    out_path = out_dir / "figure11_source_heterogeneity.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved source heterogeneity figure to: {out_path}")


if __name__ == "__main__":
    main()
