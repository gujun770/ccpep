import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import RESULT_DIR


COLORS = ["#315C72", "#8FAF6B", "#D9A441", "#B85C47", "#6F6A9F", "#4C8C84"]


def add_value_labels(ax, fmt="{:.3f}"):
    ymin, ymax = ax.get_ylim()
    span = ymax - ymin
    for patch in ax.patches:
        value = patch.get_height()
        if pd.isna(value):
            continue
        y = value + 0.02 * span if value >= 0 else value - 0.08 * span
        ax.text(
            patch.get_x() + patch.get_width() / 2,
            y,
            fmt.format(value),
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=8,
        )


def save_bar(df, x, y, path, title, ylabel, rotation=25, ylim=None):
    plt.figure(figsize=(8.8, 5.2))
    ax = plt.gca()
    ax.bar(df[x], df[y], color=COLORS[: len(df)], edgecolor="#222222", linewidth=0.6)
    plt.title(title)
    plt.ylabel(ylabel)
    if ylim is not None:
        plt.ylim(*ylim)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.18)
    add_value_labels(ax)
    plt.xticks(rotation=rotation, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=300)
    plt.close()


def plot_main_comparison(fig_dir):
    df = pd.read_csv(RESULT_DIR / "paper_tables" / "main_comparison.csv")
    plot_df = df.copy()
    label_map = {
        "Public baseline (TF-IDF)": "TF-IDF\nrandom",
        "Enhanced predictor": "Enhanced\n",
        "Hybrid predictor": "Hybrid\nrandom",
        "Descriptor RF (group CV mean)": "Descriptor RF\ngroup-CV",
    }
    plot_df["label"] = [
        (label_map.get(row["model"], row["model"]) + (row["setting"] if row["model"] == "Enhanced predictor" else ""))
        for _, row in plot_df.iterrows()
    ]
    save_bar(
        plot_df,
        "label",
        "auroc",
        fig_dir / "main_comparison_auroc.png",
        "Predictive Performance Comparison",
        "AUROC",
        rotation=0,
        ylim=(0.5, 0.9),
    )
    save_bar(
        plot_df,
        "label",
        "r2",
        fig_dir / "main_comparison_r2.png",
        "Regression Performance Comparison",
        "R2",
        rotation=0,
    )


def plot_ablation(fig_dir):
    df = pd.read_csv(RESULT_DIR / "paper_tables" / "ablation.csv")
    df["config"] = df["config"].replace(
        {
            "descriptor_only": "Descriptor",
            "text_plus_peptide_descriptors": "Text+Peptide desc.",
            "text_plus_descriptors": "Text+All desc.",
            "text_plus_monomer_stats": "Text+Monomer stats",
            "text_only": "Text only",
        }
    )
    save_bar(
        df,
        "config",
        "cls_auroc_mean",
        fig_dir / "ablation_auroc.png",
        "Group-CV Ablation Study",
        "Mean AUROC",
        ylim=(0.45, 0.75),
    )
    save_bar(
        df,
        "config",
        "reg_r2_mean",
        fig_dir / "ablation_r2.png",
        "Group-CV Regression Ablation",
        "Mean R2",
    )


def plot_descriptor_benchmark(fig_dir):
    df = pd.read_csv(RESULT_DIR / "paper_tables" / "descriptor_benchmark.csv")
    df["model"] = df["model"].replace(
        {
            "random_forest": "Random Forest",
            "ensemble": "Ensemble",
            "hist_gb": "HistGB",
            "extra_trees": "ExtraTrees",
        }
    )
    save_bar(
        df,
        "model",
        "cls_auroc_mean",
        fig_dir / "descriptor_benchmark_auroc.png",
        "Descriptor Model Benchmark",
        "Mean AUROC",
        rotation=0,
        ylim=(0.6, 0.78),
    )


def plot_generation_summary(fig_dir):
    df = pd.read_csv(RESULT_DIR / "generation_evaluation" / "summary.csv")
    df["group"] = df["group"].replace(
        {
            "train_top100": "Training top-100",
            "optimized_shortlist": "Optimized",
            "de_novo_shortlist": "De novo",
        }
    )
    save_bar(
        df,
        "group",
        "novelty_vs_train",
        fig_dir / "generation_novelty.png",
        "Generation Novelty",
        "Novelty vs Training Set",
        rotation=0,
        ylim=(0, 1.1),
    )
    save_bar(
        df,
        "group",
        "pairwise_jaccard_diversity",
        fig_dir / "generation_diversity.png",
        "Generation Diversity",
        "Pairwise Jaccard Distance",
        rotation=0,
        ylim=(0, 0.85),
    )
    filtered = df.loc[df["mean_predicted_permeability"].notna()].copy()
    save_bar(
        filtered,
        "group",
        "mean_predicted_permeability",
        fig_dir / "generation_predicted_permeability.png",
        "Predicted Permeability of Designed Candidates",
        "Mean Predicted Permeability",
        rotation=0,
    )


def plot_candidate_type_summary(fig_dir):
    df = pd.read_csv(RESULT_DIR / "docking_candidates" / "candidate_type_summary.csv")
    df["candidate_type"] = df["candidate_type"].replace({"optimized": "Optimized", "de_novo": "De novo"})
    save_bar(
        df,
        "candidate_type",
        "count",
        fig_dir / "candidate_type_summary.png",
        "Final Validation Candidate Sources",
        "Count",
        rotation=0,
    )


def main():
    fig_dir = RESULT_DIR / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    plot_main_comparison(fig_dir)
    plot_ablation(fig_dir)
    plot_descriptor_benchmark(fig_dir)
    plot_generation_summary(fig_dir)
    plot_candidate_type_summary(fig_dir)

    print(f"Saved figures to: {fig_dir}")
    for path in sorted(fig_dir.glob("*.png")):
        print(path)


if __name__ == "__main__":
    main()
