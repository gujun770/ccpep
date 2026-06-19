import argparse
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    f1_score,
    matthews_corrcoef,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from xgboost import XGBClassifier, XGBRegressor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main.train_enhanced_predictor import build_feature_table
from utils.project_paths import DATASET_DIR, RESULT_DIR


EXCLUDED_COLUMNS = {
    "HELM",
    "Permeability",
    "Monomer_Length_in_Main_Chain",
    "Source",
    "Year",
    "tokens",
    "text",
    "label",
}


def get_numeric_cols(df):
    return [c for c in df.columns if c not in EXCLUDED_COLUMNS and pd.api.types.is_numeric_dtype(df[c])]


def clean_numeric_frame(df, cols):
    x = df[cols].copy()
    x = x.replace([np.inf, -np.inf], np.nan)
    return x


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


def evaluate_classification(y_true, y_prob, threshold):
    y_pred = (y_prob >= threshold).astype(int)
    metrics = {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "mcc": float(matthews_corrcoef(y_true, y_pred)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
    }
    if len(np.unique(y_true)) > 1:
        metrics["auroc"] = float(roc_auc_score(y_true, y_prob))
    else:
        metrics["auroc"] = float("nan")
    return metrics


def find_best_threshold(y_true, y_prob):
    thresholds = np.linspace(0.2, 0.8, 61)
    best_threshold = 0.5
    best_score = -np.inf
    for threshold in thresholds:
        y_pred = (y_prob >= threshold).astype(int)
        score = matthews_corrcoef(y_true, y_pred)
        if score > best_score:
            best_score = score
            best_threshold = float(threshold)
    return best_threshold, float(best_score)


def make_models(seed, n_jobs):
    reg = XGBRegressor(
        n_estimators=700,
        max_depth=3,
        learning_rate=0.03,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=2.0,
        objective="reg:squarederror",
        eval_metric="rmse",
        random_state=seed,
        n_jobs=n_jobs,
        tree_method="hist",
    )
    cls = XGBClassifier(
        n_estimators=700,
        max_depth=3,
        learning_rate=0.03,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_lambda=2.0,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=seed,
        n_jobs=n_jobs,
        tree_method="hist",
    )
    return reg, cls


def train_predict(train_df, test_df, numeric_cols, seed, n_jobs, tune_threshold=True):
    train_x = clean_numeric_frame(train_df, numeric_cols)
    test_x = clean_numeric_frame(test_df, numeric_cols)
    weights = compute_sample_weights(train_df)

    reg, cls = make_models(seed=seed, n_jobs=n_jobs)
    reg.fit(train_x, train_df["Permeability"], sample_weight=weights, verbose=False)
    cls.fit(train_x, train_df["label"], sample_weight=weights, verbose=False)

    reg_pred = reg.predict(test_x)
    cls_prob = cls.predict_proba(test_x)[:, 1]

    threshold = 0.5
    threshold_note = "default"
    validation_mcc = None
    if tune_threshold and train_df["label"].nunique() > 1:
        if train_df["Source"].nunique() > 1:
            splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed + 7)
            inner_train_idx, inner_val_idx = next(splitter.split(train_df, groups=train_df["Source"]))
            inner_train = train_df.iloc[inner_train_idx].copy()
            inner_val = train_df.iloc[inner_val_idx].copy()
        else:
            inner_train, inner_val = train_test_split(
                train_df,
                test_size=0.2,
                random_state=seed + 7,
                stratify=train_df["label"],
            )
        inner_reg, inner_cls = make_models(seed=seed, n_jobs=n_jobs)
        inner_weights = compute_sample_weights(inner_train)
        inner_cls.fit(
            clean_numeric_frame(inner_train, numeric_cols),
            inner_train["label"],
            sample_weight=inner_weights,
            verbose=False,
        )
        val_prob = inner_cls.predict_proba(clean_numeric_frame(inner_val, numeric_cols))[:, 1]
        threshold, validation_mcc = find_best_threshold(inner_val["label"].to_numpy(), val_prob)
        threshold_note = "inner_validation_mcc"

    predictions = test_df[["HELM", "Source", "Year", "Permeability", "label"]].copy()
    predictions["xgb_reg_pred"] = reg_pred
    predictions["xgb_cls_prob"] = cls_prob
    predictions["xgb_cls_pred"] = (cls_prob >= threshold).astype(int)
    predictions["decision_threshold"] = threshold

    return {
        "regression": evaluate_regression(test_df["Permeability"], reg_pred),
        "classification": evaluate_classification(test_df["label"], cls_prob, threshold),
        "calibration": {
            "threshold_note": threshold_note,
            "validation_mcc": validation_mcc,
        },
        "predictions": predictions,
        "feature_importance": reg.feature_importances_,
    }


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


def main():
    parser = argparse.ArgumentParser(description="XGBoost descriptor baseline under identical random, source, and LOSO splits.")
    parser.add_argument("--label-csv", default=str(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv"))
    parser.add_argument("--peptide-csv", default=str(DATASET_DIR / "CycPeptMPDB_Peptide_All.csv"))
    parser.add_argument("--monomer-csv", default=str(DATASET_DIR / "CycPeptMPDB_Monomer_All.csv"))
    parser.add_argument("--result-dir", default=str(RESULT_DIR / "xgboost_baseline"))
    parser.add_argument("--threshold", type=float, default=-6.0)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-jobs", type=int, default=-1)
    parser.add_argument("--min-loso-test-size", type=int, default=10)
    args = parser.parse_args()

    result_dir = Path(args.result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    label_df = pd.read_csv(args.label_csv)
    peptide_df = pd.read_csv(args.peptide_csv, low_memory=False)
    monomer_df = pd.read_csv(args.monomer_csv, low_memory=False)

    full_df, _ = build_feature_table(label_df, peptide_df, monomer_df)
    full_df["label"] = (full_df["Permeability"] >= args.threshold).astype(int)
    numeric_cols = get_numeric_cols(full_df)

    random_train, random_test = train_test_split(
        full_df,
        test_size=args.test_size,
        random_state=args.seed,
        stratify=full_df["label"],
    )
    random_result = train_predict(random_train, random_test, numeric_cols, args.seed, args.n_jobs)

    gss = GroupShuffleSplit(n_splits=1, test_size=args.test_size, random_state=args.seed)
    train_idx, test_idx = next(gss.split(full_df, groups=full_df["Source"]))
    source_train = full_df.iloc[train_idx].copy()
    source_test = full_df.iloc[test_idx].copy()
    source_result = train_predict(source_train, source_test, numeric_cols, args.seed, args.n_jobs)

    random_result["predictions"].to_csv(result_dir / "random_split_predictions.csv", index=False)
    source_result["predictions"].to_csv(result_dir / "source_split_predictions.csv", index=False)

    per_source_results = []
    loso_regression = []
    loso_classification = []
    loso_valid_regression = []
    loso_valid_classification = []
    loso_weights = []
    loso_valid_weights = []
    feature_importance_sum = np.zeros(len(numeric_cols), dtype=float)
    feature_importance_count = 0
    eligible_sources = [s for s, c in full_df["Source"].value_counts().items() if c >= args.min_loso_test_size]

    for source in eligible_sources:
        test_df = full_df.loc[full_df["Source"] == source].copy()
        train_df = full_df.loc[full_df["Source"] != source].copy()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = train_predict(train_df, test_df, numeric_cols, args.seed, args.n_jobs)
        reg_metrics = result["regression"]
        cls_metrics = result["classification"]
        loso_regression.append(reg_metrics)
        loso_classification.append(cls_metrics)
        loso_weights.append(len(test_df))
        has_regression_variance = float(test_df["Permeability"].std(ddof=0)) > 1e-8
        has_both_classes = test_df["label"].nunique() > 1
        if has_regression_variance and has_both_classes:
            loso_valid_regression.append(reg_metrics)
            loso_valid_classification.append(cls_metrics)
            loso_valid_weights.append(len(test_df))
        per_source_results.append(
            {
                "source": source,
                "test_samples": int(len(test_df)),
                "num_classes": int(test_df["label"].nunique()),
                "permeability_std": float(test_df["Permeability"].std(ddof=0)),
                "is_valid_for_strict_summary": bool(has_regression_variance and has_both_classes),
                "regression": reg_metrics,
                "classification": cls_metrics,
                "threshold": result["classification"]["threshold"],
            }
        )
        feature_importance_sum += result["feature_importance"]
        feature_importance_count += 1

    feature_importance = pd.DataFrame(
        {
            "feature": numeric_cols,
            "importance": feature_importance_sum / max(feature_importance_count, 1),
        }
    ).sort_values("importance", ascending=False)

    metrics = {
        "num_samples": int(len(full_df)),
        "num_numeric_features": int(len(numeric_cols)),
        "threshold": float(args.threshold),
        "model": "XGBoost descriptor baseline",
        "random_split": {
            "train_samples": int(len(random_train)),
            "test_samples": int(len(random_test)),
            "regression": random_result["regression"],
            "classification": random_result["classification"],
            "calibration": random_result["calibration"],
        },
        "source_split": {
            "train_samples": int(len(source_train)),
            "test_samples": int(len(source_test)),
            "num_train_sources": int(source_train["Source"].nunique()),
            "num_test_sources": int(source_test["Source"].nunique()),
            "regression": source_result["regression"],
            "classification": source_result["classification"],
            "calibration": source_result["calibration"],
        },
        "loso": {
            "num_sources_evaluated": int(len(per_source_results)),
            "num_sources_valid_for_strict_summary": int(len(loso_valid_regression)),
            "all_sources": {
                "regression": summarize_weighted(loso_regression, loso_weights),
                "classification": summarize_weighted(loso_classification, loso_weights),
            },
            "strict_sources_only": {
                "regression": summarize_weighted(loso_valid_regression, loso_valid_weights) if loso_valid_regression else {},
                "classification": summarize_weighted(loso_valid_classification, loso_valid_weights) if loso_valid_classification else {},
            },
        },
    }

    with open(result_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    with open(result_dir / "per_source_results.json", "w", encoding="utf-8") as f:
        json.dump(per_source_results, f, indent=2, ensure_ascii=False)
    feature_importance.to_csv(result_dir / "feature_importance.csv", index=False)

    compact = {
        "random": {
            "rmse": metrics["random_split"]["regression"]["rmse"],
            "r2": metrics["random_split"]["regression"]["r2"],
            "auroc": metrics["random_split"]["classification"]["auroc"],
            "mcc": metrics["random_split"]["classification"]["mcc"],
        },
        "source": {
            "rmse": metrics["source_split"]["regression"]["rmse"],
            "r2": metrics["source_split"]["regression"]["r2"],
            "auroc": metrics["source_split"]["classification"]["auroc"],
            "mcc": metrics["source_split"]["classification"]["mcc"],
        },
        "loso_strict_weighted": {
            "r2": metrics["loso"]["strict_sources_only"]["regression"].get("r2", {}).get("weighted_mean"),
            "auroc": metrics["loso"]["strict_sources_only"]["classification"].get("auroc", {}).get("weighted_mean"),
            "mcc": metrics["loso"]["strict_sources_only"]["classification"].get("mcc", {}).get("weighted_mean"),
        },
    }
    print(json.dumps(compact, indent=2, ensure_ascii=False))
    print(f"Saved XGBoost baseline to: {result_dir}")


if __name__ == "__main__":
    main()
