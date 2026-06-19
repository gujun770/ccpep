import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import RESULT_DIR


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def fisher_z_mean(values, weights):
    vals = np.clip(np.asarray(values, dtype=float), -0.999999, 0.999999)
    w = np.asarray(weights, dtype=float)
    z = np.arctanh(vals)
    return float(np.tanh(np.average(z, weights=w)))


def main():
    out_dir = RESULT_DIR / "source_heterogeneity"
    out_dir.mkdir(parents=True, exist_ok=True)

    per_source = pd.DataFrame(load_json(RESULT_DIR / "loso_random_forest" / "per_source_results.json"))
    per_source["reg_rmse"] = per_source["regression"].apply(lambda x: x["rmse"])
    per_source["reg_r2"] = per_source["regression"].apply(lambda x: x["r2"])
    per_source["cls_auroc"] = per_source["classification"].apply(lambda x: x.get("auroc"))
    per_source["cls_pr_auc"] = per_source["classification"].apply(lambda x: x.get("pr_auc"))
    per_source["cls_mcc"] = per_source["classification"].apply(lambda x: x.get("mcc"))
    per_source["cls_bal_acc"] = per_source["classification"].apply(lambda x: x.get("balanced_accuracy"))
    per_source["log_test_samples"] = np.log10(per_source["test_samples"])

    strict = per_source.loc[per_source["is_valid_for_strict_summary"]].copy()
    strict.to_csv(out_dir / "per_source_metrics.csv", index=False)

    heterogeneity_rows = []
    for metric in ["reg_r2", "cls_auroc", "cls_pr_auc", "cls_mcc", "cls_bal_acc"]:
        vals = strict[metric].dropna().to_numpy(dtype=float)
        weights = strict.loc[strict[metric].notna(), "test_samples"].to_numpy(dtype=float)
        weighted_mean = float(np.average(vals, weights=weights))
        weighted_std = float(np.sqrt(np.average((vals - weighted_mean) ** 2, weights=weights)))
        q1 = float(np.quantile(vals, 0.25))
        q3 = float(np.quantile(vals, 0.75))
        if metric == "cls_auroc":
            weighted_mean = fisher_z_mean(vals, weights)
        heterogeneity_rows.append(
            {
                "metric": metric,
                "weighted_mean": weighted_mean,
                "weighted_std": weighted_std,
                "min": float(vals.min()),
                "q1": q1,
                "median": float(np.median(vals)),
                "q3": q3,
                "max": float(vals.max()),
                "num_sources": int(len(vals)),
            }
        )
    heterogeneity_df = pd.DataFrame(heterogeneity_rows)
    heterogeneity_df.to_csv(out_dir / "heterogeneity_summary.csv", index=False)

    corr_rows = []
    for metric in ["reg_r2", "cls_auroc", "cls_pr_auc", "cls_mcc", "cls_bal_acc"]:
        sub = strict.loc[strict[metric].notna(), ["log_test_samples", "test_samples", metric, "permeability_std"]].copy()
        if len(sub) < 3:
            continue
        corr_rows.append(
            {
                "metric": metric,
                "corr_with_log_test_samples": float(sub["log_test_samples"].corr(sub[metric], method="spearman")),
                "corr_with_permeability_std": float(sub["permeability_std"].corr(sub[metric], method="spearman")),
            }
        )
    corr_df = pd.DataFrame(corr_rows)
    corr_df.to_csv(out_dir / "correlation_summary.csv", index=False)

    best_sources = strict.sort_values("cls_auroc", ascending=False).head(5)[
        ["source", "test_samples", "reg_r2", "cls_auroc", "cls_mcc", "permeability_std"]
    ]
    worst_sources = strict.sort_values("cls_auroc", ascending=True).head(5)[
        ["source", "test_samples", "reg_r2", "cls_auroc", "cls_mcc", "permeability_std"]
    ]
    best_sources.to_csv(out_dir / "top5_sources_by_auroc.csv", index=False)
    worst_sources.to_csv(out_dir / "bottom5_sources_by_auroc.csv", index=False)

    narrative = pd.DataFrame(
        [
            {
                "finding": "source_heterogeneity",
                "summary": (
                    f"Strict LOSO source-level AUROC spans from {strict['cls_auroc'].min():.3f} to {strict['cls_auroc'].max():.3f}, "
                    f"with weighted mean {heterogeneity_df.loc[heterogeneity_df['metric']=='cls_auroc', 'weighted_mean'].iloc[0]:.3f}, "
                    f"indicating substantial source heterogeneity."
                ),
            },
            {
                "finding": "sample_size_relation",
                "summary": (
                    f"Spearman correlation between log source size and AUROC is "
                    f"{corr_df.loc[corr_df['metric']=='cls_auroc', 'corr_with_log_test_samples'].iloc[0]:.3f}, "
                    f"suggesting that source difficulty is not explained by sample size alone."
                ),
            },
            {
                "finding": "variance_relation",
                "summary": (
                    f"Spearman correlation between source permeability variance and AUROC is "
                    f"{corr_df.loc[corr_df['metric']=='cls_auroc', 'corr_with_permeability_std'].iloc[0]:.3f}."
                ),
            },
        ]
    )
    narrative.to_csv(out_dir / "narrative_summary.csv", index=False)

    print("Source heterogeneity summary:")
    print(heterogeneity_df.to_string(index=False))
    print("---")
    print("Correlation summary:")
    print(corr_df.to_string(index=False))
    print(f"Saved source heterogeneity analysis to: {out_dir}")


if __name__ == "__main__":
    main()
