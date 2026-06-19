import json
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
    "gold": "#D9A441",
    "green": "#8FAF6B",
    "rust": "#B85C47",
}


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.18, linewidth=0.8)
    ax.tick_params(labelsize=9)


def main():
    ci_path = RESULT_DIR / "confidence_intervals" / "hybrid_bootstrap_ci.json"
    group_path = RESULT_DIR / "confidence_intervals" / "descriptor_group_cv_summary.csv"

    with open(ci_path, "r", encoding="utf-8") as f:
        ci = json.load(f)
    group_df = pd.read_csv(group_path)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.2), gridspec_kw={"width_ratios": [1.0, 1.05]})

    auroc_data = [
        ("Random", ci["hybrid_random_split"]["classification"]["auroc"]),
        ("Source", ci["hybrid_source_split"]["classification"]["auroc"]),
    ]
    r2_data = [
        ("Random", ci["hybrid_random_split"]["regression"]["r2"]),
        ("Source", ci["hybrid_source_split"]["regression"]["r2"]),
    ]

    ax = axes[0]
    x_pos = [0, 1]
    auroc_means = [d[1]["mean"] for d in auroc_data]
    auroc_err_low = [d[1]["mean"] - d[1]["ci_lower"] for d in auroc_data]
    auroc_err_high = [d[1]["ci_upper"] - d[1]["mean"] for d in auroc_data]
    r2_means = [d[1]["mean"] for d in r2_data]
    r2_err_low = [d[1]["mean"] - d[1]["ci_lower"] for d in r2_data]
    r2_err_high = [d[1]["ci_upper"] - d[1]["mean"] for d in r2_data]

    ax.errorbar(x_pos, auroc_means, yerr=[auroc_err_low, auroc_err_high], fmt="o-", lw=2.2, color=PALETTE["blue"], label="AUROC")
    ax2 = ax.twinx()
    ax2.errorbar(x_pos, r2_means, yerr=[r2_err_low, r2_err_high], fmt="s--", lw=2.0, color=PALETTE["gold"], label="R2")
    ax.set_xticks(x_pos)
    ax.set_xticklabels([d[0] for d in auroc_data])
    ax.set_ylabel("AUROC", color=PALETTE["blue"])
    ax2.set_ylabel("R2", color=PALETTE["gold"])
    ax.set_title("Hybrid predictor confidence intervals")
    style_ax(ax)
    ax2.spines["top"].set_visible(False)
    handles_1, labels_1 = ax.get_legend_handles_labels()
    handles_2, labels_2 = ax2.get_legend_handles_labels()
    ax.legend(handles_1 + handles_2, labels_1 + labels_2, frameon=False, fontsize=8, loc="center right")

    ax = axes[1]
    group_df = group_df.sort_values("cls_auroc_mean", ascending=True)
    ax.barh(group_df["model"], group_df["cls_auroc_mean"], xerr=group_df["cls_auroc_std"], color=PALETTE["green"], alpha=0.9)
    ax.set_xlabel("Mean AUROC ± SD")
    ax.set_title("Descriptor model robustness across group CV")
    style_ax(ax)

    axes[0].text(-0.16, 1.05, "A", transform=axes[0].transAxes, fontsize=15, weight="bold")
    axes[1].text(-0.14, 1.05, "B", transform=axes[1].transAxes, fontsize=15, weight="bold")
    fig.tight_layout()
    out_path = RESULT_DIR / "paper_figures" / "figure7_confidence_intervals.png"
    fig.savefig(out_path, dpi=300)
    plt.close(fig)

    print(f"Saved confidence interval figure to: {out_path}")


if __name__ == "__main__":
    main()
