from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULT_DIR = PROJECT_ROOT / "Result"
OUT = RESULT_DIR / "paper_figures" / "figure8_quality_diversity.png"


def main():
    pts = pd.read_csv(RESULT_DIR / "quality_diversity_analysis" / "shortlist_qd_points.csv")
    pts = pts.loc[pts["route"].isin(["optimized_shortlist", "de_novo_shortlist"])].copy()
    pts["local_diversity"] = pd.to_numeric(pts["local_diversity"], errors="coerce")
    pts["quality_score"] = pd.to_numeric(pts["quality_score"], errors="coerce")

    fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=350)
    colors = {"optimized_shortlist": "#1f77b4", "de_novo_shortlist": "#f28e2b"}
    labels = {"optimized_shortlist": "Optimized shortlist", "de_novo_shortlist": "De novo shortlist"}

    for route, group in pts.groupby("route"):
        ax.scatter(
            group["local_diversity"],
            group["quality_score"],
            s=52,
            alpha=0.85,
            color=colors[route],
            edgecolor="white",
            linewidth=0.7,
            label=labels[route],
        )
        ax.scatter(
            [group["local_diversity"].mean()],
            [group["quality_score"].mean()],
            s=180,
            marker="*",
            color=colors[route],
            edgecolor="#222222",
            linewidth=0.7,
        )

    ax.set_xlabel("Local diversity")
    ax.set_ylabel("Quality score")
    ax.set_xlim(0.48, 1.03)
    ax.set_ylim(0.60, 1.02)
    ax.set_title("Focused quality-diversity view")
    ax.grid(alpha=0.25)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
