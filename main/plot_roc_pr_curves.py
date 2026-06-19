from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import auc, precision_recall_curve, roc_curve


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULT_DIR = PROJECT_ROOT / "Result"
OUT = RESULT_DIR / "paper_figures" / "figure2b_roc_pr_curves.png"


def load(split):
    df = pd.read_csv(RESULT_DIR / "hybrid_predictor" / f"{split}_split_predictions.csv")
    return df["label"].to_numpy(), df["hybrid_cls_prob"].to_numpy()


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    splits = {
        "Random split": load("random"),
        "Source split": load("source"),
    }

    fig, axes = plt.subplots(1, 2, figsize=(10, 4), dpi=350)
    colors = {"Random split": "#1f77b4", "Source split": "#d62728"}

    for label, (y, prob) in splits.items():
        fpr, tpr, _ = roc_curve(y, prob)
        roc_auc = auc(fpr, tpr)
        precision, recall, _ = precision_recall_curve(y, prob)
        pr_auc = auc(recall, precision)
        axes[0].plot(fpr, tpr, lw=2.2, color=colors[label], label=f"{label} (AUROC={roc_auc:.3f})")
        axes[1].plot(recall, precision, lw=2.2, color=colors[label], label=f"{label} (PR-AUC={pr_auc:.3f})")

    axes[0].plot([0, 1], [0, 1], color="#777777", lw=1, linestyle="--")
    axes[0].set_xlabel("False positive rate")
    axes[0].set_ylabel("True positive rate")
    axes[0].set_title("ROC curves")
    axes[0].legend(frameon=False, loc="lower right")

    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].set_title("Precision-recall curves")
    axes[1].legend(frameon=False, loc="lower left")

    for ax in axes:
        ax.grid(alpha=0.25)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1.02)

    fig.suptitle("Hybrid classifier discrimination under random and source-aware splits", y=1.03)
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight")
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
