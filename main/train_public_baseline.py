import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import DATASET_DIR, RESULT_DIR


def parse_helm_monomers(helm_notation: str):
    start_index = helm_notation.find("{")
    end_index = helm_notation.find("}")
    if start_index == -1 or end_index == -1:
        return []
    sequence = helm_notation[start_index + 1:end_index]
    return [token.strip() for token in sequence.split(".") if token.strip()]


def normalize_helm_text(helm_series: pd.Series) -> pd.Series:
    return helm_series.fillna("").astype(str).apply(lambda x: " ".join(parse_helm_monomers(x)))


def evaluate_regression(y_true, y_pred):
    rmse = mean_squared_error(y_true, y_pred) ** 0.5
    return {
        "rmse": float(rmse),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "r2": float(r2_score(y_true, y_pred)),
    }


def evaluate_classification(y_true, y_pred, y_prob):
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }
    if len(np.unique(y_true)) > 1:
        metrics["auroc"] = float(roc_auc_score(y_true, y_prob))
    return metrics


def build_regression_pipeline():
    return Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(analyzer="word", ngram_range=(1, 2))),
            ("model", Ridge(alpha=1.0)),
        ]
    )


def build_classification_pipeline():
    return Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(analyzer="word", ngram_range=(1, 2))),
            ("model", LogisticRegression(max_iter=2000, class_weight="balanced")),
        ]
    )


def main():
    parser = argparse.ArgumentParser(description="Train a public-data baseline for cyclic peptide permeability.")
    parser.add_argument(
        "--input",
        default=str(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv"),
        help="Path to the labeled CSV file.",
    )
    parser.add_argument(
        "--result-dir",
        default=str(RESULT_DIR / "public_baseline"),
        help="Directory for metrics and predictions.",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Test split ratio.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=-6.0,
        help="Permeability threshold for binary classification.",
    )
    args = parser.parse_args()

    result_dir = Path(args.result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(args.input)
    df = df.loc[df["HELM"].notna() & df["Permeability"].notna()].copy()
    df["text"] = normalize_helm_text(df["HELM"])
    df["label"] = (df["Permeability"] >= args.threshold).astype(int)

    train_df, test_df = train_test_split(
        df,
        test_size=args.test_size,
        random_state=args.seed,
        stratify=df["label"],
    )

    regression_pipeline = build_regression_pipeline()
    regression_pipeline.fit(train_df["text"], train_df["Permeability"])
    reg_pred = regression_pipeline.predict(test_df["text"])
    regression_metrics = evaluate_regression(test_df["Permeability"], reg_pred)

    classification_pipeline = build_classification_pipeline()
    classification_pipeline.fit(train_df["text"], train_df["label"])
    cls_pred = classification_pipeline.predict(test_df["text"])
    cls_prob = classification_pipeline.predict_proba(test_df["text"])[:, 1]
    classification_metrics = evaluate_classification(test_df["label"], cls_pred, cls_prob)

    metrics = {
        "num_samples": int(len(df)),
        "train_samples": int(len(train_df)),
        "test_samples": int(len(test_df)),
        "threshold": float(args.threshold),
        "regression": regression_metrics,
        "classification": classification_metrics,
    }

    metrics_path = result_dir / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    prediction_df = test_df[["HELM", "Permeability", "Source", "Year"]].copy()
    prediction_df["regression_pred"] = reg_pred
    prediction_df["binary_label"] = test_df["label"].to_numpy()
    prediction_df["binary_pred"] = cls_pred
    prediction_df["binary_prob"] = cls_prob
    prediction_path = result_dir / "test_predictions.csv"
    prediction_df.to_csv(prediction_path, index=False)

    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    print(f"Saved metrics to: {metrics_path}")
    print(f"Saved predictions to: {prediction_path}")


if __name__ == "__main__":
    main()
