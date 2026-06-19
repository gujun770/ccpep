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
    "green": "#8FAF6B",
    "gold": "#D9A441",
    "rust": "#B85C47",
    "violet": "#6F6A9F",
    "teal": "#4C8C84",
    "sand": "#F3EFE2",
}


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.18, linewidth=0.8)
    ax.tick_params(labelsize=9)


def fig1_workflow(out_dir):
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.axis("off")
    steps = [
        ("CycPeptMPDB", "public cyclic peptide data"),
        ("Descriptor Scorer", "source-aware RF predictor"),
        ("Two-Route Design", "optimization + de novo"),
        ("Candidate Filtering", "novelty, diversity, uncertainty"),
        ("Final Set", "19 validation candidates"),
    ]
    xs = np.linspace(0.08, 0.92, len(steps))
    y = 0.55
    for i, ((title, subtitle), x) in enumerate(zip(steps, xs)):
        rect = plt.Rectangle((x - 0.085, y - 0.18), 0.17, 0.36, facecolor=PALETTE["sand"], edgecolor=PALETTE["ink"], lw=1.2)
        ax.add_patch(rect)
        ax.text(x, y + 0.055, title, ha="center", va="center", fontsize=10, weight="bold", color=PALETTE["ink"])
        ax.text(x, y - 0.065, subtitle, ha="center", va="center", fontsize=8.5, color=PALETTE["ink"])
        if i < len(xs) - 1:
            ax.annotate("", xy=(xs[i + 1] - 0.095, y), xytext=(x + 0.095, y), arrowprops=dict(arrowstyle="->", lw=1.6, color=PALETTE["blue"]))
    ax.text(0.02, 0.92, "A", fontsize=16, weight="bold")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(out_dir / "figure1_workflow.png", dpi=300)
    plt.close(fig)


def fig2_prediction_panel(out_dir):
    main = pd.read_csv(RESULT_DIR / "paper_tables" / "main_comparison.csv")
    bench = pd.read_csv(RESULT_DIR / "paper_tables" / "descriptor_benchmark.csv")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))

    labels = ["TF-IDF\nrandom", "Enhanced\nrandom", "Enhanced\nsource", "Hybrid\nrandom", "RF\ngroup-CV"]
    vals = main["auroc"].to_numpy()
    axes[0].plot(labels, vals, marker="o", lw=2.2, color=PALETTE["blue"])
    axes[0].fill_between(range(len(vals)), vals, 0.5, color=PALETTE["blue"], alpha=0.12)
    axes[0].set_ylim(0.5, 0.9)
    axes[0].set_ylabel("AUROC")
    axes[0].set_title("Predictive performance")
    for idx, val in enumerate(vals):
        axes[0].text(idx, val + 0.012, f"{val:.3f}", ha="center", fontsize=8)
    style_ax(axes[0])

    bench = bench.sort_values("cls_auroc_mean", ascending=True)
    axes[1].barh(bench["model"], bench["cls_auroc_mean"], color=[PALETTE["violet"], PALETTE["gold"], PALETTE["green"], PALETTE["rust"]])
    axes[1].set_xlim(0.6, 0.76)
    axes[1].set_xlabel("Mean AUROC")
    axes[1].set_title("Descriptor model benchmark")
    for y, val in enumerate(bench["cls_auroc_mean"]):
        axes[1].text(val + 0.003, y, f"{val:.3f}", va="center", fontsize=8)
    style_ax(axes[1])

    axes[0].text(-0.14, 1.05, "A", transform=axes[0].transAxes, fontsize=15, weight="bold")
    axes[1].text(-0.18, 1.05, "B", transform=axes[1].transAxes, fontsize=15, weight="bold")
    fig.tight_layout()
    fig.savefig(out_dir / "figure2_prediction.png", dpi=300)
    plt.close(fig)


def fig3_generation_panel(out_dir):
    summary = pd.read_csv(RESULT_DIR / "generation_evaluation" / "summary.csv")
    freq = pd.read_csv(RESULT_DIR / "generation_evaluation" / "monomer_frequency.csv")
    candidates = pd.read_csv(RESULT_DIR / "docking_candidates" / "candidate_type_summary.csv")

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.3), gridspec_kw={"width_ratios": [1.25, 1, 0.95]})

    display_map = {
        "train_top100": "Train top-100",
        "optimized_shortlist": "Optimized",
        "de_novo_shortlist": "De novo",
    }
    metrics = [
        "novelty_vs_train",
        "pairwise_jaccard_diversity",
        "mean_natural_ratio",
        "mean_n_methyl_ratio",
        "mean_predicted_positive_prob",
    ]
    metric_labels = ["Novelty", "Diversity", "Natural", "N-methyl", "Positive prob."]
    heat = (
        summary.set_index("group")
        .loc[["train_top100", "optimized_shortlist", "de_novo_shortlist"], metrics]
        .fillna(0.0)
        .to_numpy()
    )
    im = axes[0].imshow(heat, cmap="YlGnBu", vmin=0, vmax=1, aspect="auto")
    axes[0].set_xticks(np.arange(len(metric_labels)))
    axes[0].set_xticklabels(metric_labels, rotation=18, ha="right")
    axes[0].set_yticks(np.arange(3))
    axes[0].set_yticklabels([display_map[k] for k in ["train_top100", "optimized_shortlist", "de_novo_shortlist"]])
    axes[0].set_title("Generation profile map")
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            axes[0].text(j, i, f"{heat[i, j]:.2f}", ha="center", va="center", fontsize=7.5, color="white" if heat[i, j] > 0.58 else PALETTE["ink"])
    axes[0].spines["top"].set_visible(False)
    axes[0].spines["right"].set_visible(False)
    plt.colorbar(im, ax=axes[0], fraction=0.045, pad=0.03)

    de_freq = freq.loc[freq["group"] == "de_novo_shortlist"].head(8).sort_values("count", ascending=True)
    axes[1].barh(de_freq["monomer"], de_freq["count"], color=PALETTE["rust"], alpha=0.92)
    axes[1].set_title("De novo monomer motif")
    axes[1].set_xlabel("Count")
    for y, val in enumerate(de_freq["count"]):
        axes[1].text(val + 0.15, y, str(val), va="center", fontsize=8)
    style_ax(axes[1])

    axes[2].pie(
        candidates["count"],
        labels=candidates["candidate_type"].replace({"optimized": "Optimized", "de_novo": "De novo"}),
        autopct="%1.0f%%",
        colors=[PALETTE["blue"], PALETTE["gold"]],
        startangle=90,
        wedgeprops={"edgecolor": "white", "linewidth": 1},
    )
    axes[2].set_title("Validation candidate routes")

    for ax, letter in zip(axes, ["A", "B", "C"]):
        ax.text(-0.12, 1.08, letter, transform=ax.transAxes, fontsize=15, weight="bold")
    fig.tight_layout()
    fig.savefig(out_dir / "figure3_generation.png", dpi=300)
    plt.close(fig)


def fig4_candidate_landscape(out_dir):
    optimized = pd.read_csv(RESULT_DIR / "design_pipeline" / "final_shortlist.csv")
    de_novo = pd.read_csv(RESULT_DIR / "de_novo_generation" / "final_generated_shortlist.csv")
    optimized["route"] = "Optimized"
    de_novo["route"] = "De novo"
    df = pd.concat([optimized, de_novo], ignore_index=True)

    colors = {"Optimized": PALETTE["blue"], "De novo": PALETTE["gold"]}

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), gridspec_kw={"width_ratios": [1.45, 0.9]})

    ax = axes[0]
    bubble_sizes = 330 / (df["permeability_std"].fillna(df["permeability_std"].median()) + 0.06)
    for route, sub in df.groupby("route"):
        sub_sizes = 330 / (sub["permeability_std"].fillna(df["permeability_std"].median()) + 0.06)
        ax.scatter(
            sub["predicted_permeability"],
            sub["predicted_positive_prob"],
            s=sub_sizes,
            alpha=0.82,
            edgecolor="white",
            linewidth=1.0,
            label=route,
            color=colors[route],
        )
    ax.axvline(df["predicted_permeability"].median(), color=PALETTE["ink"], lw=1.0, ls="--", alpha=0.45)
    ax.axhline(df["predicted_positive_prob"].median(), color=PALETTE["ink"], lw=1.0, ls="--", alpha=0.45)
    label_df = (
        df.sort_values(["route", "robust_score"])
        .groupby("route", as_index=False)
        .head(2)
        .copy()
    )
    route_counts = {"Optimized": 0, "De novo": 0}
    offset_map = {
        ("Optimized", 1): (5, 8),
        ("Optimized", 2): (5, -12),
        ("De novo", 1): (5, 8),
        ("De novo", 2): (5, -12),
    }
    for _, row in label_df.iterrows():
        route_counts[row["route"]] += 1
        tag = "O" if row["route"] == "Optimized" else "D"
        short_label = f"{tag}{route_counts[row['route']]}"
        dx, dy = offset_map[(row["route"], route_counts[row["route"]])]
        ax.annotate(
            short_label,
            (row["predicted_permeability"], row["predicted_positive_prob"]),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=8,
            weight="bold",
            color=PALETTE["ink"],
        )
    ax.set_xlabel("Predicted permeability")
    ax.set_ylabel("Predicted positive probability")
    ax.set_title("Candidate confidence landscape")
    ax.legend(frameon=False, loc="lower right")
    style_ax(ax)

    route_order = ["Optimized", "De novo"]
    x_pos = np.arange(len(route_order))
    for idx, route in enumerate(route_order):
        sub = df.loc[df["route"] == route].copy()
        jitter = np.linspace(-0.08, 0.08, len(sub)) if len(sub) > 1 else np.array([0.0])
        axes[1].scatter(
            np.full(len(sub), x_pos[idx]) + jitter,
            sub["robust_score"],
            s=60,
            color=colors[route],
            alpha=0.85,
            edgecolor="white",
            linewidth=0.8,
        )
        axes[1].plot(
            [x_pos[idx] - 0.18, x_pos[idx] + 0.18],
            [sub["robust_score"].median(), sub["robust_score"].median()],
            color=PALETTE["ink"],
            lw=1.4,
        )
    axes[1].set_xticks(x_pos)
    axes[1].set_xticklabels(route_order)
    axes[1].set_ylabel("Robust score")
    axes[1].set_title("Route-wise shortlist spread")
    style_ax(axes[1])

    axes[0].text(-0.12, 1.05, "A", transform=axes[0].transAxes, fontsize=15, weight="bold")
    axes[1].text(-0.16, 1.05, "B", transform=axes[1].transAxes, fontsize=15, weight="bold")
    fig.tight_layout()
    fig.savefig(out_dir / "figure4_candidate_landscape.png", dpi=300)
    plt.close(fig)


def main():
    out_dir = RESULT_DIR / "paper_figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig1_workflow(out_dir)
    fig2_prediction_panel(out_dir)
    fig3_generation_panel(out_dir)
    fig4_candidate_landscape(out_dir)
    print(f"Saved paper-style figures to: {out_dir}")
    for path in sorted(out_dir.glob("*.png")):
        print(path)


if __name__ == "__main__":
    main()
