import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    matthews_corrcoef,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import RESULT_DIR


def metric_bundle_reg(y_true, y_pred):
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def metric_bundle_cls(y_true, y_prob, threshold):
    y_pred = (y_prob >= threshold).astype(int)
    out = {
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "mcc": float(matthews_corrcoef(y_true, y_pred)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
    }
    if len(np.unique(y_true)) > 1:
        out["auroc"] = float(roc_auc_score(y_true, y_prob))
    return out


def bootstrap_ci(values, alpha=0.05):
    values = np.asarray(values, dtype=float)
    return {
        "mean": float(np.nanmean(values)),
        "ci_lower": float(np.nanpercentile(values, 100 * alpha / 2)),
        "ci_upper": float(np.nanpercentile(values, 100 * (1 - alpha / 2))),
    }


def bootstrap_prediction_metrics(df, reg_col, prob_col, label_col="label", target_col="Permeability", threshold_col="decision_threshold", n_boot=1000, seed=42):
    rng = np.random.default_rng(seed)
    reg_records = []
    cls_records = []

    y_true_reg = df[target_col].to_numpy()
    y_pred_reg = df[reg_col].to_numpy()
    y_true_cls = df[label_col].to_numpy()
    y_prob = df[prob_col].to_numpy()
    threshold = float(df[threshold_col].iloc[0]) if threshold_col in df.columns else 0.5

    n = len(df)
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        reg_metrics = metric_bundle_reg(y_true_reg[idx], y_pred_reg[idx])
        cls_metrics = metric_bundle_cls(y_true_cls[idx], y_prob[idx], threshold)
        reg_records.append(reg_metrics)
        cls_records.append(cls_metrics)

    reg_summary = {k: bootstrap_ci([r[k] for r in reg_records]) for k in reg_records[0].keys()}
    cls_summary = {k: bootstrap_ci([r[k] for r in cls_records]) for k in cls_records[0].keys()}
    return {"regression": reg_summary, "classification": cls_summary}


def summarize_group_cv(summary_json):
    with open(summary_json, "r", encoding="utf-8") as f:
        summary = json.load(f)

    records = []
    for model_name, metrics in summary["models"].items():
        records.append(
            {
                "model": model_name,
                "reg_r2_mean": metrics["regression"]["r2"]["mean"],
                "reg_r2_std": metrics["regression"]["r2"]["std"],
                "cls_auroc_mean": metrics["classification"]["auroc"]["mean"],
                "cls_auroc_std": metrics["classification"]["auroc"]["std"],
                "cls_mcc_mean": metrics["classification"]["mcc"]["mean"],
                "cls_mcc_std": metrics["classification"]["mcc"]["std"],
            }
        )
    return pd.DataFrame(records)


def main():
    out_dir = RESULT_DIR / "confidence_intervals"
    out_dir.mkdir(parents=True, exist_ok=True)

    random_pred = pd.read_csv(RESULT_DIR / "hybrid_predictor" / "random_split_predictions.csv")
    source_pred = pd.read_csv(RESULT_DIR / "hybrid_predictor" / "source_split_predictions.csv")

    random_ci = bootstrap_prediction_metrics(random_pred, "hybrid_reg_pred", "hybrid_cls_prob", n_boot=1000, seed=42)
    source_ci = bootstrap_prediction_metrics(source_pred, "hybrid_reg_pred", "hybrid_cls_prob", n_boot=1000, seed=43)

    ci_summary = {
        "hybrid_random_split": random_ci,
        "hybrid_source_split": source_ci,
    }
    with open(out_dir / "hybrid_bootstrap_ci.json", "w", encoding="utf-8") as f:
        json.dump(ci_summary, f, indent=2, ensure_ascii=False)

    group_cv_df = summarize_group_cv(RESULT_DIR / "descriptor_benchmark" / "summary.json")
    group_cv_df.to_csv(out_dir / "descriptor_group_cv_summary.csv", index=False)

    narrative_df = pd.DataFrame(
        [
            {
                "finding": "hybrid_random_auroc",
                "summary": (
                    f"Hybrid random-split AUROC mean is {random_ci['classification']['auroc']['mean']:.3f} "
                    f"with bootstrap 95% CI [{random_ci['classification']['auroc']['ci_lower']:.3f}, "
                    f"{random_ci['classification']['auroc']['ci_upper']:.3f}]."
                ),
            },
            {
                "finding": "hybrid_source_auroc",
                "summary": (
                    f"Hybrid source-split AUROC mean is {source_ci['classification']['auroc']['mean']:.3f} "
                    f"with bootstrap 95% CI [{source_ci['classification']['auroc']['ci_lower']:.3f}, "
                    f"{source_ci['classification']['auroc']['ci_upper']:.3f}]."
                ),
            },
            {
                "finding": "hybrid_random_r2",
                "summary": (
                    f"Hybrid random-split R2 mean is {random_ci['regression']['r2']['mean']:.3f} "
                    f"with bootstrap 95% CI [{random_ci['regression']['r2']['ci_lower']:.3f}, "
                    f"{random_ci['regression']['r2']['ci_upper']:.3f}]."
                ),
            },
        ]
    )
    narrative_df.to_csv(out_dir / "narrative_summary.csv", index=False)

    print("Hybrid bootstrap CI summary:")
    print(json.dumps(ci_summary, indent=2, ensure_ascii=False))
    print("---")
    print("Descriptor group CV summary:")
    print(group_cv_df.to_string(index=False))
    print(f"Saved confidence interval outputs to: {out_dir}")


if __name__ == "__main__":
    main()
