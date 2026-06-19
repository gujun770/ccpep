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
    out_dir = RESULT_DIR / "paper_figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    route_stats = pd.read_csv(RESULT_DIR / "design_statistics" / "route_comparison_stats.csv")
    ablation_stats = pd.read_csv(RESULT_DIR / "design_statistics" / "generator_ablation_stats.csv")
    qd_summary = pd.read_csv(RESULT_DIR / "quality_diversity_analysis" / "summary.csv")

    fig = plt.figure(figsize=(14, 9))
    gs = fig.add_gridspec(2, 2, hspace=0.30, wspace=0.22)

    ax0 = fig.add_subplot(gs[0, 0])
    route_plot = route_stats.copy()
    route_plot["metric_label"] = route_plot["metric"].map(
        {
            "quality_score": "Quality",
            "local_diversity": "Diversity",
            "predicted_permeability": "Permeability",
            "predicted_positive_prob": "Pos prob",
            "n_methyl_ratio": "N-methyl",
            "natural_ratio": "Natural",
            "d_ratio": "D-ratio",
        }
    ).fillna(route_plot["metric"])
    ax0.axvline(0, color="#64748b", linewidth=1.0, linestyle="--")
    ax0.errorbar(
        route_plot["mean_diff"],
        route_plot["metric_label"],
        xerr=[
            route_plot["mean_diff"] - route_plot["ci_lower"],
            route_plot["ci_upper"] - route_plot["mean_diff"],
        ],
        fmt="o",
        color="#0f766e",
        ecolor="#99f6e4",
        elinewidth=3,
        capsize=4,
    )
    ax0.set_title("Optimized vs de novo route comparison", fontsize=13)
    ax0.set_xlabel("Mean difference (optimized - de novo)")
    ax0.set_ylabel("")
    ax0.spines["top"].set_visible(False)
    ax0.spines["right"].set_visible(False)

    ax1 = fig.add_subplot(gs[0, 1])
    qd_plot = qd_summary.loc[qd_summary["route"].isin(["optimized_shortlist", "de_novo_shortlist"])].copy()
    qd_plot["label"] = qd_plot["route"].map(
        {
            "optimized_shortlist": "Optimized",
            "de_novo_shortlist": "De novo",
        }
    )
    ax1.scatter(
        qd_plot["diversity_mean"],
        qd_plot["quality_mean"],
        s=500,
        c=["#ef4444", "#3b82f6"],
        alpha=0.88,
        edgecolor="white",
        linewidth=1.2,
    )
    for _, row in qd_plot.iterrows():
        ax1.text(row["diversity_mean"] + 0.004, row["quality_mean"] + 0.004, row["label"], fontsize=10)
    ax1.set_title("Route-level quality-diversity summary", fontsize=13)
    ax1.set_xlabel("Mean diversity")
    ax1.set_ylabel("Mean quality")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    ax2 = fig.add_subplot(gs[1, 0])
    ablation_focus = ablation_stats.loc[
        ablation_stats["metric"].isin(["predicted_positive_prob", "composition_alignment", "uncertainty_stability"])
    ].copy()
    ablation_focus["comparison"] = ablation_focus["group_b"].map(
        {
            "no_motif": "vs No motif",
            "no_composition": "vs No comp",
            "no_uncertainty": "vs No uncert",
            "quality_only": "vs Quality only",
        }
    )
    ablation_focus["metric_label"] = ablation_focus["metric"].map(
        {
            "predicted_positive_prob": "Pos prob",
            "composition_alignment": "Comp align",
            "uncertainty_stability": "Stability",
        }
    )
    sns.barplot(
        data=ablation_focus,
        x="comparison",
        y="mean_diff",
        hue="metric_label",
        palette=["#0f766e", "#f59e0b", "#7c3aed"],
        ax=ax2,
    )
    ax2.axhline(0, color="#64748b", linewidth=1.0)
    ax2.set_title("Full generator vs ablations", fontsize=13)
    ax2.set_xlabel("")
    ax2.set_ylabel("Mean difference (full - ablation)")
    ax2.legend(title="")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    ax3 = fig.add_subplot(gs[1, 1])
    pval_plot = route_stats.copy()
    pval_plot["metric_label"] = pval_plot["metric"].map(
        {
            "quality_score": "Quality",
            "local_diversity": "Diversity",
            "predicted_permeability": "Permeability",
            "predicted_positive_prob": "Pos prob",
            "n_methyl_ratio": "N-methyl",
            "natural_ratio": "Natural",
            "d_ratio": "D-ratio",
        }
    ).fillna(pval_plot["metric"])
    pval_plot["neglog10p"] = -pval_plot["permutation_pvalue"].clip(lower=1e-6).map(lambda x: __import__("math").log10(x))
    sns.barplot(
        data=pval_plot,
        x="metric_label",
        y="neglog10p",
        color="#1d4ed8",
        ax=ax3,
    )
    ax3.axhline(-__import__("math").log10(0.05), color="#ef4444", linestyle="--", linewidth=1.2)
    ax3.set_title("Route comparison significance", fontsize=13)
    ax3.set_xlabel("")
    ax3.set_ylabel("-log10(p)")
    ax3.tick_params(axis="x", rotation=25)
    ax3.spines["top"].set_visible(False)
    ax3.spines["right"].set_visible(False)

    fig.suptitle("Figure 10. Statistical summary of design routes and generator ablations", fontsize=16, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    out_path = out_dir / "figure10_statistical_summary.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved final statistical summary figure to: {out_path}")


if __name__ == "__main__":
    main()
