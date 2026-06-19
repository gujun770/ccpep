import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    matthews_corrcoef,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler
import warnings

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main.train_enhanced_predictor import build_feature_table
from utils.project_paths import DATASET_DIR, RESULT_DIR


def compute_sample_weights(df):
    source_counts = df["Source"].value_counts()
    class_counts = df["label"].value_counts()
    source_weights = df["Source"].map(lambda x: 1.0 / source_counts[x]).to_numpy(dtype=float)
    class_weights = df["label"].map(lambda x: 1.0 / class_counts[x]).to_numpy(dtype=float)
    weights = source_weights * class_weights
    return weights / np.mean(weights)


def evaluate_regression(y_true, y_pred):
    return {
        "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def evaluate_classification(y_true, y_prob, threshold=0.5):
    y_pred = (y_prob >= threshold).astype(int)
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "mcc": float(matthews_corrcoef(y_true, y_pred)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
    }
    if len(np.unique(y_true)) > 1:
        metrics["auroc"] = float(roc_auc_score(y_true, y_prob))
    else:
        metrics["auroc"] = float("nan")
    return metrics


def summarize(metric_dicts):
    keys = metric_dicts[0].keys()
    output = {}
    for key in keys:
        vals = np.array([m[key] for m in metric_dicts], dtype=float)
        output[key] = {
            "mean": float(np.nanmean(vals)),
            "std": float(np.nanstd(vals)),
        }
    return output


def summarize_weighted(metric_dicts, weights):
    keys = metric_dicts[0].keys()
    weights = np.array(weights, dtype=float)
    weights = weights / weights.sum()
    output = {}
    for key in keys:
        vals = np.array([m[key] for m in metric_dicts], dtype=float)
        output[key] = {
            "weighted_mean": float(np.nansum(vals * weights)),
            "mean": float(np.nanmean(vals)),
            "std": float(np.nanstd(vals)),
        }
    return output


def get_numeric_cols(df):
    excluded = {"HELM", "Permeability", "Monomer_Length_in_Main_Chain", "Source", "Year", "tokens", "text", "label"}
    return [c for c in df.columns if c not in excluded and pd.api.types.is_numeric_dtype(df[c])]


def train_models(train_x, train_y_reg, train_y_cls, sample_weights):
    reg = RandomForestRegressor(
        n_estimators=400,
        max_depth=None,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    reg.fit(train_x, train_y_reg, sample_weight=sample_weights)

    cls = RandomForestClassifier(
        n_estimators=400,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    cls.fit(train_x, train_y_cls, sample_weight=sample_weights)
    return reg, cls


def main():
    parser = argparse.ArgumentParser(description="Leave-one-source-out evaluation for RandomForest descriptor model.")
    parser.add_argument("--label-csv", default=str(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv"))
    parser.add_argument("--peptide-csv", default=str(DATASET_DIR / "CycPeptMPDB_Peptide_All.csv"))
    parser.add_argument("--monomer-csv", default=str(DATASET_DIR / "CycPeptMPDB_Monomer_All.csv"))
    parser.add_argument("--result-dir", default=str(RESULT_DIR / "loso_random_forest"))
    parser.add_argument("--threshold", type=float, default=-6.0)
    parser.add_argument("--min-test-size", type=int, default=10)
    args = parser.parse_args()

    result_dir = Path(args.result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    label_df = pd.read_csv(args.label_csv)
    peptide_df = pd.read_csv(args.peptide_csv, low_memory=False)
    monomer_df = pd.read_csv(args.monomer_csv, low_memory=False)

    full_df, _ = build_feature_table(label_df, peptide_df, monomer_df)
    full_df["label"] = (full_df["Permeability"] >= args.threshold).astype(int)
    numeric_cols = get_numeric_cols(full_df)

    per_source_results = []
    regression_metrics = []
    classification_metrics = []
    valid_regression_metrics = []
    valid_classification_metrics = []
    valid_weights = []
    all_weights = []
    feature_importance_sum = np.zeros(len(numeric_cols), dtype=float)
    feature_importance_count = 0

    eligible_sources = [s for s, c in full_df["Source"].value_counts().items() if c >= args.min_test_size]

    for source in eligible_sources:
        test_df = full_df.loc[full_df["Source"] == source].copy()
        train_df = full_df.loc[full_df["Source"] != source].copy()

        scaler = StandardScaler()
        train_x = scaler.fit_transform(train_df[numeric_cols])
        test_x = scaler.transform(test_df[numeric_cols])
        sample_weights = compute_sample_weights(train_df)

        reg, cls = train_models(
            train_x=train_x,
            train_y_reg=train_df["Permeability"].to_numpy(),
            train_y_cls=train_df["label"].to_numpy(),
            sample_weights=sample_weights,
        )

        reg_pred = reg.predict(test_x)
        cls_prob = cls.predict_proba(test_x)[:, 1]

        reg_metrics = evaluate_regression(test_df["Permeability"], reg_pred)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cls_metrics = evaluate_classification(test_df["label"], cls_prob)
        regression_metrics.append(reg_metrics)
        classification_metrics.append(cls_metrics)
        all_weights.append(len(test_df))

        has_regression_variance = float(test_df["Permeability"].std(ddof=0)) > 1e-8
        has_both_classes = test_df["label"].nunique() > 1
        if has_regression_variance and has_both_classes:
            valid_regression_metrics.append(reg_metrics)
            valid_classification_metrics.append(cls_metrics)
            valid_weights.append(len(test_df))

        per_source_results.append({
            "source": source,
            "test_samples": int(len(test_df)),
            "num_classes": int(test_df["label"].nunique()),
            "permeability_std": float(test_df["Permeability"].std(ddof=0)),
            "is_valid_for_strict_summary": bool(has_regression_variance and has_both_classes),
            "regression": reg_metrics,
            "classification": cls_metrics,
        })

        feature_importance_sum += reg.feature_importances_
        feature_importance_count += 1

    summary = {
        "num_samples": int(len(full_df)),
        "num_numeric_features": int(len(numeric_cols)),
        "num_sources_evaluated": int(len(per_source_results)),
        "num_sources_valid_for_strict_summary": int(len(valid_regression_metrics)),
        "threshold": float(args.threshold),
        "min_test_size": int(args.min_test_size),
        "all_sources": {
            "regression": summarize_weighted(regression_metrics, all_weights),
            "classification": summarize_weighted(classification_metrics, all_weights),
        },
        "strict_sources_only": {
            "regression": summarize_weighted(valid_regression_metrics, valid_weights) if valid_regression_metrics else {},
            "classification": summarize_weighted(valid_classification_metrics, valid_weights) if valid_classification_metrics else {},
        },
    }

    feature_importance = pd.DataFrame(
        {
            "feature": numeric_cols,
            "importance": feature_importance_sum / max(feature_importance_count, 1),
        }
    ).sort_values("importance", ascending=False)

    with open(result_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with open(result_dir / "per_source_results.json", "w", encoding="utf-8") as f:
        json.dump(per_source_results, f, indent=2, ensure_ascii=False)
    feature_importance.to_csv(result_dir / "feature_importance.csv", index=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print("Top 15 features:")
    print(feature_importance.head(15).to_string(index=False))
    print(f"Saved summary to: {result_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
