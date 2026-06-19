import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
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
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main.train_enhanced_predictor import (
    PEPTIDE_FEATURE_COLUMNS,
    build_feature_table,
)
from utils.project_paths import DATASET_DIR, RESULT_DIR


def evaluate_regression(y_true, y_pred):
    return {
        "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def evaluate_classification(y_true, y_pred, y_prob):
    metrics = {
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
    return metrics


def compute_sample_weights(df):
    source_counts = df["Source"].value_counts()
    class_counts = df["label"].value_counts()
    source_weights = df["Source"].map(lambda x: 1.0 / source_counts[x]).to_numpy(dtype=float)
    class_weights = df["label"].map(lambda x: 1.0 / class_counts[x]).to_numpy(dtype=float)
    weights = source_weights * class_weights
    weights = weights / np.mean(weights)
    return weights


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


def build_text_matrices(train_df, test_df):
    word_vectorizer = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2)
    char_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2)
    x_train_word = word_vectorizer.fit_transform(train_df["text"])
    x_test_word = word_vectorizer.transform(test_df["text"])
    x_train_char = char_vectorizer.fit_transform(train_df["text"])
    x_test_char = char_vectorizer.transform(test_df["text"])
    x_train_text = hstack([x_train_word, x_train_char], format="csr")
    x_test_text = hstack([x_test_word, x_test_char], format="csr")
    return x_train_text, x_test_text


def build_numeric_matrices(train_df, test_df, numeric_cols):
    scaler = StandardScaler()
    x_train_num = scaler.fit_transform(train_df[numeric_cols])
    x_test_num = scaler.transform(test_df[numeric_cols])
    return x_train_num, x_test_num


def run_single_split(train_df, test_df, numeric_cols):
    x_train_text, x_test_text = build_text_matrices(train_df, test_df)
    x_train_num, x_test_num = build_numeric_matrices(train_df, test_df, numeric_cols)
    sample_weights = compute_sample_weights(train_df)

    text_reg = Ridge(alpha=1.0)
    text_reg.fit(x_train_text, train_df["Permeability"], sample_weight=sample_weights)
    text_reg_pred = text_reg.predict(x_test_text)

    num_reg = HistGradientBoostingRegressor(
        learning_rate=0.05,
        max_depth=6,
        max_iter=300,
        random_state=42,
    )
    num_reg.fit(x_train_num, train_df["Permeability"], sample_weight=sample_weights)
    num_reg_pred = num_reg.predict(x_test_num)

    hybrid_reg_pred = 0.5 * text_reg_pred + 0.5 * num_reg_pred

    text_cls = LogisticRegression(max_iter=3000, class_weight="balanced")
    text_cls.fit(x_train_text, train_df["label"], sample_weight=sample_weights)
    text_cls_prob = text_cls.predict_proba(x_test_text)[:, 1]

    num_cls = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_depth=6,
        max_iter=300,
        random_state=42,
    )
    num_cls.fit(x_train_num, train_df["label"], sample_weight=sample_weights)
    num_cls_prob = num_cls.predict_proba(x_test_num)[:, 1]

    if train_df["Source"].nunique() > 1:
        inner_splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=7)
        inner_train_idx, inner_val_idx = next(inner_splitter.split(train_df, groups=train_df["Source"]))
        inner_train = train_df.iloc[inner_train_idx].copy()
        inner_val = train_df.iloc[inner_val_idx].copy()
    else:
        inner_train, inner_val = train_test_split(
            train_df,
            test_size=0.2,
            random_state=7,
            stratify=train_df["label"],
        )

    x_inner_train_text, x_inner_val_text = build_text_matrices(inner_train, inner_val)
    x_inner_train_num, x_inner_val_num = build_numeric_matrices(inner_train, inner_val, numeric_cols)
    inner_weights = compute_sample_weights(inner_train)

    inner_text_cls = LogisticRegression(max_iter=3000, class_weight="balanced")
    inner_text_cls.fit(x_inner_train_text, inner_train["label"], sample_weight=inner_weights)
    inner_text_prob = inner_text_cls.predict_proba(x_inner_val_text)[:, 1]

    inner_num_cls = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_depth=6,
        max_iter=300,
        random_state=42,
    )
    inner_num_cls.fit(x_inner_train_num, inner_train["label"], sample_weight=inner_weights)
    inner_num_prob = inner_num_cls.predict_proba(x_inner_val_num)[:, 1]

    inner_hybrid_prob = 0.5 * inner_text_prob + 0.5 * inner_num_prob
    best_threshold, best_val_mcc = find_best_threshold(inner_val["label"].to_numpy(), inner_hybrid_prob)

    hybrid_cls_prob = 0.5 * text_cls_prob + 0.5 * num_cls_prob
    hybrid_cls_pred = (hybrid_cls_prob >= best_threshold).astype(int)

    predictions = test_df[["HELM", "Source", "Year", "Permeability", "label"]].copy()
    predictions["text_reg_pred"] = text_reg_pred
    predictions["numeric_reg_pred"] = num_reg_pred
    predictions["hybrid_reg_pred"] = hybrid_reg_pred
    predictions["text_cls_prob"] = text_cls_prob
    predictions["numeric_cls_prob"] = num_cls_prob
    predictions["hybrid_cls_prob"] = hybrid_cls_prob
    predictions["hybrid_cls_pred"] = hybrid_cls_pred
    predictions["decision_threshold"] = best_threshold

    return {
        "regression": {
            "text": evaluate_regression(test_df["Permeability"], text_reg_pred),
            "numeric": evaluate_regression(test_df["Permeability"], num_reg_pred),
            "hybrid": evaluate_regression(test_df["Permeability"], hybrid_reg_pred),
        },
        "classification": {
            "text": evaluate_classification(test_df["label"], (text_cls_prob >= 0.5).astype(int), text_cls_prob),
            "numeric": evaluate_classification(test_df["label"], (num_cls_prob >= 0.5).astype(int), num_cls_prob),
            "hybrid": evaluate_classification(test_df["label"], hybrid_cls_pred, hybrid_cls_prob),
        },
        "calibration": {
            "best_threshold": best_threshold,
            "validation_mcc": best_val_mcc,
        },
        "predictions": predictions,
    }


def main():
    parser = argparse.ArgumentParser(description="Train a hybrid text+descriptor predictor for cyclic peptide permeability.")
    parser.add_argument("--label-csv", default=str(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv"))
    parser.add_argument("--peptide-csv", default=str(DATASET_DIR / "CycPeptMPDB_Peptide_All.csv"))
    parser.add_argument("--monomer-csv", default=str(DATASET_DIR / "CycPeptMPDB_Monomer_All.csv"))
    parser.add_argument("--result-dir", default=str(RESULT_DIR / "hybrid_predictor"))
    parser.add_argument("--threshold", type=float, default=-6.0)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    result_dir = Path(args.result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    label_df = pd.read_csv(args.label_csv)
    peptide_df = pd.read_csv(args.peptide_csv, low_memory=False)
    monomer_df = pd.read_csv(args.monomer_csv, low_memory=False)

    full_df, numeric_cols = build_feature_table(label_df, peptide_df, monomer_df)
    full_df["label"] = (full_df["Permeability"] >= args.threshold).astype(int)

    random_train, random_test = train_test_split(
        full_df,
        test_size=args.test_size,
        random_state=args.seed,
        stratify=full_df["label"],
    )
    random_result = run_single_split(random_train, random_test, numeric_cols)

    gss = GroupShuffleSplit(n_splits=1, test_size=args.test_size, random_state=args.seed)
    train_idx, test_idx = next(gss.split(full_df, groups=full_df["Source"]))
    source_train = full_df.iloc[train_idx].copy()
    source_test = full_df.iloc[test_idx].copy()
    source_result = run_single_split(source_train, source_test, numeric_cols)

    metrics = {
        "num_samples": int(len(full_df)),
        "num_numeric_features": int(len(numeric_cols)),
        "num_peptide_descriptor_features": int(len([c for c in numeric_cols if c in PEPTIDE_FEATURE_COLUMNS])),
        "threshold": float(args.threshold),
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
    }

    with open(result_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    random_result["predictions"].to_csv(result_dir / "random_split_predictions.csv", index=False)
    source_result["predictions"].to_csv(result_dir / "source_split_predictions.csv", index=False)

    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    print(f"Saved metrics to: {result_dir / 'metrics.json'}")


if __name__ == "__main__":
    main()
