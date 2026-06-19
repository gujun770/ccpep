import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
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
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

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
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "mcc": float(matthews_corrcoef(y_true, y_pred)),
        "pr_auc": float(average_precision_score(y_true, y_prob)),
        "auroc": float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else float("nan"),
    }


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


def get_numeric_cols(df):
    excluded = {"HELM", "Permeability", "Monomer_Length_in_Main_Chain", "Source", "Year", "tokens", "text", "label"}
    return [c for c in df.columns if c not in excluded and pd.api.types.is_numeric_dtype(df[c])]


def build_models():
    return {
        "hist_gb": {
            "reg": HistGradientBoostingRegressor(
                learning_rate=0.05,
                max_depth=6,
                max_iter=300,
                random_state=42,
            ),
            "cls": HistGradientBoostingClassifier(
                learning_rate=0.05,
                max_depth=6,
                max_iter=300,
                random_state=42,
            ),
        },
        "random_forest": {
            "reg": RandomForestRegressor(
                n_estimators=400,
                max_depth=None,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            ),
            "cls": RandomForestClassifier(
                n_estimators=400,
                max_depth=None,
                min_samples_leaf=2,
                class_weight="balanced_subsample",
                random_state=42,
                n_jobs=-1,
            ),
        },
        "extra_trees": {
            "reg": ExtraTreesRegressor(
                n_estimators=500,
                max_depth=None,
                min_samples_leaf=1,
                random_state=42,
                n_jobs=-1,
            ),
            "cls": ExtraTreesClassifier(
                n_estimators=500,
                max_depth=None,
                min_samples_leaf=1,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            ),
        },
    }


def run_models(train_x, test_x, train_y_reg, test_y_reg, train_y_cls, test_y_cls, sample_weights):
    base_models = build_models()
    results = {}
    reg_predictions = {}
    cls_probabilities = {}

    for name, model_pair in base_models.items():
        reg_model = model_pair["reg"]
        cls_model = model_pair["cls"]

        reg_model.fit(train_x, train_y_reg, sample_weight=sample_weights)
        reg_pred = reg_model.predict(test_x)
        reg_predictions[name] = reg_pred

        cls_model.fit(train_x, train_y_cls, sample_weight=sample_weights)
        cls_prob = cls_model.predict_proba(test_x)[:, 1]
        cls_probabilities[name] = cls_prob

        results[name] = {
            "regression": evaluate_regression(test_y_reg, reg_pred),
            "classification": evaluate_classification(test_y_cls, cls_prob),
        }

    ensemble_reg = np.mean(np.vstack(list(reg_predictions.values())), axis=0)
    ensemble_cls = np.mean(np.vstack(list(cls_probabilities.values())), axis=0)
    results["ensemble"] = {
        "regression": evaluate_regression(test_y_reg, ensemble_reg),
        "classification": evaluate_classification(test_y_cls, ensemble_cls),
    }
    return results


def main():
    parser = argparse.ArgumentParser(description="Benchmark descriptor-only models with repeated group CV.")
    parser.add_argument("--label-csv", default=str(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv"))
    parser.add_argument("--peptide-csv", default=str(DATASET_DIR / "CycPeptMPDB_Peptide_All.csv"))
    parser.add_argument("--monomer-csv", default=str(DATASET_DIR / "CycPeptMPDB_Monomer_All.csv"))
    parser.add_argument("--result-dir", default=str(RESULT_DIR / "descriptor_benchmark"))
    parser.add_argument("--threshold", type=float, default=-6.0)
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument("--test-size", type=float, default=0.2)
    args = parser.parse_args()

    result_dir = Path(args.result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    label_df = pd.read_csv(args.label_csv)
    peptide_df = pd.read_csv(args.peptide_csv, low_memory=False)
    monomer_df = pd.read_csv(args.monomer_csv, low_memory=False)

    full_df, _ = build_feature_table(label_df, peptide_df, monomer_df)
    full_df["label"] = (full_df["Permeability"] >= args.threshold).astype(int)
    numeric_cols = get_numeric_cols(full_df)

    aggregated = {}
    split_results = []

    for split_id, random_state in enumerate(range(42, 42 + args.n_splits), start=1):
        splitter = GroupShuffleSplit(n_splits=1, test_size=args.test_size, random_state=random_state)
        train_idx, test_idx = next(splitter.split(full_df, groups=full_df["Source"]))
        train_df = full_df.iloc[train_idx].copy()
        test_df = full_df.iloc[test_idx].copy()

        scaler = StandardScaler()
        train_x = scaler.fit_transform(train_df[numeric_cols])
        test_x = scaler.transform(test_df[numeric_cols])
        sample_weights = compute_sample_weights(train_df)

        split_model_results = run_models(
            train_x=train_x,
            test_x=test_x,
            train_y_reg=train_df["Permeability"].to_numpy(),
            test_y_reg=test_df["Permeability"].to_numpy(),
            train_y_cls=train_df["label"].to_numpy(),
            test_y_cls=test_df["label"].to_numpy(),
            sample_weights=sample_weights,
        )

        split_results.append({
            "split_id": split_id,
            "train_samples": int(len(train_df)),
            "test_samples": int(len(test_df)),
            "train_sources": int(train_df["Source"].nunique()),
            "test_sources": int(test_df["Source"].nunique()),
            "results": split_model_results,
        })

        for model_name, metrics in split_model_results.items():
            if model_name not in aggregated:
                aggregated[model_name] = {"regression": [], "classification": []}
            aggregated[model_name]["regression"].append(metrics["regression"])
            aggregated[model_name]["classification"].append(metrics["classification"])

    summary = {
        "num_samples": int(len(full_df)),
        "num_numeric_features": int(len(numeric_cols)),
        "threshold": float(args.threshold),
        "n_splits": args.n_splits,
        "models": {},
    }
    for model_name, metric_lists in aggregated.items():
        summary["models"][model_name] = {
            "regression": summarize(metric_lists["regression"]),
            "classification": summarize(metric_lists["classification"]),
        }

    with open(result_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with open(result_dir / "split_results.json", "w", encoding="utf-8") as f:
        json.dump(split_results, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Saved summary to: {result_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
