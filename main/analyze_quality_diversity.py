import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import RESULT_DIR


PALETTE = {
    "ink": "#27313A",
    "blue": "#315C72",
    "gold": "#D9A441",
    "green": "#8FAF6B",
    "rust": "#B85C47",
}


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.18, linewidth=0.8)
    ax.tick_params(labelsize=9)


def jaccard_distance(sig_a, sig_b):
    a = set(str(sig_a).split("."))
    b = set(str(sig_b).split("."))
    union = len(a | b)
    if union == 0:
        return 0.0
    return 1.0 - len(a & b) / union


def local_diversity_scores(signatures):
    signatures = list(signatures)
    scores = []
    for i, sig in enumerate(signatures):
        dists = []
        for j, other in enumerate(signatures):
            if i == j:
                continue
            dists.append(jaccard_distance(sig, other))
        scores.append(float(np.mean(dists)) if dists else 0.0)
    return scores


def attach_quality_diversity(df, signature_col, score_col, route_name):
    out = df.copy()
    out["route"] = route_name
    out["local_diversity"] = local_diversity_scores(out[signature_col].astype(str).tolist())
    out["quality_score"] = out[score_col]
    return out


def summarize_front(df, route_name):
    return {
        "route": route_name,
        "count": int(len(df)),
        "quality_mean": float(df["quality_score"].mean()),
        "quality_top10_mean": float(df["quality_score"].nlargest(min(10, len(df))).mean()),
        "diversity_mean": float(df["local_diversity"].mean()),
        "diversity_top10_mean": float(df.sort_values("quality_score", ascending=False).head(min(10, len(df)))["local_diversity"].mean()),
    }


def main():
    design_pool = pd.read_csv(RESULT_DIR / "design_pipeline" / "filtered_candidates.csv")
    design_short = pd.read_csv(RESULT_DIR / "design_pipeline" / "final_shortlist.csv")
    denovo_pool = pd.read_csv(RESULT_DIR / "de_novo_generation" / "final_generated_candidates.csv")
    denovo_short = pd.read_csv(RESULT_DIR / "de_novo_generation" / "final_generated_shortlist.csv")

    design_pool_qd = attach_quality_diversity(design_pool, "tokens", "predicted_positive_prob", "optimized_pool")
    design_short_qd = attach_quality_diversity(design_short, "tokens", "predicted_positive_prob", "optimized_shortlist")
    denovo_pool_qd = attach_quality_diversity(denovo_pool, "tokens", "multiobjective_score", "de_novo_pool")
    denovo_short_qd = attach_quality_diversity(denovo_short, "tokens", "multiobjective_score", "de_novo_shortlist")

    summary_df = pd.DataFrame(
        [
            summarize_front(design_pool_qd, "optimized_pool"),
            summarize_front(design_short_qd, "optimized_shortlist"),
            summarize_front(denovo_pool_qd, "de_novo_pool"),
            summarize_front(denovo_short_qd, "de_novo_shortlist"),
        ]
    )

    out_dir = RESULT_DIR / "quality_diversity_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(out_dir / "summary.csv", index=False)
    pd.concat([design_short_qd, denovo_short_qd], ignore_index=True).to_csv(out_dir / "shortlist_qd_points.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.2, 0.95]})

    ax = axes[0]
    ax.scatter(
        design_pool_qd["local_diversity"], design_pool_qd["quality_score"],
        s=16, alpha=0.14, color=PALETTE["blue"], label="Optimized pool"
    )
    ax.scatter(
        denovo_pool_qd["local_diversity"], denovo_pool_qd["quality_score"],
        s=16, alpha=0.14, color=PALETTE["gold"], label="De novo pool"
    )
    ax.scatter(
        design_short_qd["local_diversity"], design_short_qd["quality_score"],
        s=58, alpha=0.9, color=PALETTE["blue"], edgecolor="white", linewidth=0.8, label="Optimized shortlist"
    )
    ax.scatter(
        denovo_short_qd["local_diversity"], denovo_short_qd["quality_score"],
        s=58, alpha=0.9, color=PALETTE["gold"], edgecolor="white", linewidth=0.8, label="De novo shortlist"
    )
    ax.set_xlabel("Local Jaccard diversity")
    ax.set_ylabel("Quality score")
    ax.set_title("Quality-diversity landscape")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="lower left")
    style_ax(ax)

    ax = axes[1]
    plot_df = summary_df.copy()
    colors = [PALETTE["blue"], PALETTE["blue"], PALETTE["gold"], PALETTE["gold"]]
    y = np.arange(len(plot_df))
    ax.barh(y, plot_df["diversity_mean"], color=colors, alpha=0.82)
    for idx, row in plot_df.iterrows():
        ax.text(row["diversity_mean"] + 0.01, idx, f"Q={row['quality_mean']:.3f}", va="center", fontsize=8)
    ax.set_yticks(y)
    ax.set_yticklabels(plot_df["route"])
    ax.set_xlabel("Mean local diversity")
    ax.set_title("Route-level quality-diversity summary")
    style_ax(ax)

    axes[0].text(-0.14, 1.05, "A", transform=axes[0].transAxes, fontsize=15, weight="bold")
    axes[1].text(-0.14, 1.05, "B", transform=axes[1].transAxes, fontsize=15, weight="bold")
    fig.tight_layout()
    fig.savefig(RESULT_DIR / "paper_figures" / "figure8_quality_diversity.png", dpi=300)
    plt.close(fig)

    narrative_df = pd.DataFrame(
        [
            {
                "finding": "optimized_tradeoff",
                "summary": (
                    f"Optimized shortlist keeps mean quality {design_short_qd['quality_score'].mean():.3f} "
                    f"with mean local diversity {design_short_qd['local_diversity'].mean():.3f}."
                ),
            },
            {
                "finding": "denovo_tradeoff",
                "summary": (
                    f"De novo shortlist keeps mean quality {denovo_short_qd['quality_score'].mean():.3f} "
                    f"with mean local diversity {denovo_short_qd['local_diversity'].mean():.3f}."
                ),
            },
            {
                "finding": "tradeoff_contrast",
                "summary": (
                    "The optimized route concentrates more strongly on high-confidence local improvements, "
                    "whereas the de novo route expands into a broader diversity region while maintaining competitive quality."
                ),
            },
        ]
    )
    narrative_df.to_csv(out_dir / "narrative_summary.csv", index=False)

    print("Quality-diversity summary:")
    print(summary_df.to_string(index=False))
    print(f"Saved quality-diversity analysis to: {out_dir}")


if __name__ == "__main__":
    main()
