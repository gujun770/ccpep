import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
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

from main.train_enhanced_predictor import PEPTIDE_FEATURE_COLUMNS, build_feature_table
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


def build_text_features(train_text, test_text):
    word_vectorizer = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2)
    char_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2)
    x_train_word = word_vectorizer.fit_transform(train_text)
    x_test_word = word_vectorizer.transform(test_text)
    x_train_char = char_vectorizer.fit_transform(train_text)
    x_test_char = char_vectorizer.transform(test_text)
    return hstack([x_train_word, x_train_char]), hstack([x_test_word, x_test_char])


def build_numeric_features(train_df, test_df, numeric_cols):
    scaler = StandardScaler()
    x_train = scaler.fit_transform(train_df[numeric_cols])
    x_test = scaler.transform(test_df[numeric_cols])
    return x_train, x_test


def run_text_model(train_df, test_df):
    x_train, x_test = build_text_features(train_df["text"], test_df["text"])
    weights = compute_sample_weights(train_df)

    reg = Ridge(alpha=1.0)
    reg.fit(x_train, train_df["Permeability"], sample_weight=weights)
    reg_pred = reg.predict(x_test)

    cls = LogisticRegression(max_iter=3000, class_weight="balanced")
    cls.fit(x_train, train_df["label"], sample_weight=weights)
    cls_prob = cls.predict_proba(x_test)[:, 1]

    return reg_pred, cls_prob


def run_numeric_model(train_df, test_df, numeric_cols):
    x_train, x_test = build_numeric_features(train_df, test_df, numeric_cols)
    weights = compute_sample_weights(train_df)

    reg = HistGradientBoostingRegressor(
        learning_rate=0.05,
        max_depth=6,
        max_iter=300,
        random_state=42,
    )
    reg.fit(x_train, train_df["Permeability"], sample_weight=weights)
    reg_pred = reg.predict(x_test)

    cls = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_depth=6,
        max_iter=300,
        random_state=42,
    )
    cls.fit(x_train, train_df["label"], sample_weight=weights)
    cls_prob = cls.predict_proba(x_test)[:, 1]

    return reg_pred, cls_prob


def get_ablation_numeric_cols(full_df):
    all_numeric = [
        c for c in full_df.columns
        if c not in {"HELM", "Permeability", "Monomer_Length_in_Main_Chain", "Source", "Year", "tokens", "text", "label"}
        and pd.api.types.is_numeric_dtype(full_df[c])
    ]
    peptide_cols = [c for c in all_numeric if c in PEPTIDE_FEATURE_COLUMNS]
    stat_cols = [c for c in all_numeric if c not in peptide_cols]
    return all_numeric, peptide_cols, stat_cols


def run_config(train_df, test_df, config_name, numeric_cols):
    if config_name == "text_only":
        reg_pred, cls_prob = run_text_model(train_df, test_df)
    elif config_name == "descriptor_only":
        reg_pred, cls_prob = run_numeric_model(train_df, test_df, numeric_cols)
    elif config_name == "text_plus_descriptors":
        text_reg, text_prob = run_text_model(train_df, test_df)
        num_reg, num_prob = run_numeric_model(train_df, test_df, numeric_cols)
        reg_pred = 0.5 * text_reg + 0.5 * num_reg
        cls_prob = 0.5 * text_prob + 0.5 * num_prob
    else:
        raise ValueError(f"Unknown config: {config_name}")

    return {
        "regression": evaluate_regression(test_df["Permeability"], reg_pred),
        "classification": evaluate_classification(test_df["label"], cls_prob),
    }


def summarize_metric_dicts(metric_dicts):
    summary = {}
    metric_names = metric_dicts[0].keys()
    for metric_name in metric_names:
        values = np.array([m[metric_name] for m in metric_dicts], dtype=float)
        summary[metric_name] = {
            "mean": float(np.nanmean(values)),
            "std": float(np.nanstd(values)),
        }
    return summary


def main():
    parser = argparse.ArgumentParser(description="Repeated group CV ablation for cyclic peptide permeability prediction.")
    parser.add_argument("--label-csv", default=str(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv"))
    parser.add_argument("--peptide-csv", default=str(DATASET_DIR / "CycPeptMPDB_Peptide_All.csv"))
    parser.add_argument("--monomer-csv", default=str(DATASET_DIR / "CycPeptMPDB_Monomer_All.csv"))
    parser.add_argument("--result-dir", default=str(RESULT_DIR / "group_cv_ablation"))
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

    all_numeric, peptide_cols, stat_cols = get_ablation_numeric_cols(full_df)
    configs = {
        "text_only": [],
        "descriptor_only": all_numeric,
        "text_plus_descriptors": all_numeric,
        "text_plus_peptide_descriptors": peptide_cols,
        "text_plus_monomer_stats": stat_cols,
    }

    split_results = []
    aggregated = {
        config_name: {"regression": [], "classification": []}
        for config_name in configs
    }

    for split_id, random_state in enumerate(range(42, 42 + args.n_splits), start=1):
        splitter = GroupShuffleSplit(n_splits=1, test_size=args.test_size, random_state=random_state)
        train_idx, test_idx = next(splitter.split(full_df, groups=full_df["Source"]))
        train_df = full_df.iloc[train_idx].copy()
        test_df = full_df.iloc[test_idx].copy()

        split_record = {
            "split_id": split_id,
            "train_samples": int(len(train_df)),
            "test_samples": int(len(test_df)),
            "train_sources": int(train_df["Source"].nunique()),
            "test_sources": int(test_df["Source"].nunique()),
            "results": {},
        }

        for config_name, numeric_cols in configs.items():
            result = run_config(train_df, test_df, "text_only" if config_name == "text_only" else ("descriptor_only" if config_name == "descriptor_only" else "text_plus_descriptors"), numeric_cols)
            split_record["results"][config_name] = result
            aggregated[config_name]["regression"].append(result["regression"])
            aggregated[config_name]["classification"].append(result["classification"])

        split_results.append(split_record)

    summary = {
        "num_samples": int(len(full_df)),
        "threshold": float(args.threshold),
        "n_splits": args.n_splits,
        "configs": {},
    }

    for config_name in configs:
        summary["configs"][config_name] = {
            "regression": summarize_metric_dicts(aggregated[config_name]["regression"]),
            "classification": summarize_metric_dicts(aggregated[config_name]["classification"]),
        }

    with open(result_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    with open(result_dir / "split_results.json", "w", encoding="utf-8") as f:
        json.dump(split_results, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Saved summary to: {result_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
