import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
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
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import DATASET_DIR, RESULT_DIR


NATURAL_SYMBOLS = {
    "A", "R", "N", "D", "C", "Q", "E", "G", "H", "I",
    "L", "K", "M", "F", "P", "S", "T", "W", "Y", "V",
}
MONOMER_FEATURE_COLUMNS = [
    "MolWt", "TPSA", "MolLogP", "qed", "FractionCSP3",
    "HeavyAtomCount", "NumHAcceptors", "NumHDonors", "RingCount",
]
PEPTIDE_FEATURE_COLUMNS = [
    "MolWt", "TPSA", "MolLogP", "qed", "FractionCSP3",
    "HeavyAtomCount", "NumHAcceptors", "NumHDonors", "RingCount",
    "PC1", "PC2", "CHCl3_3DPSA", "H2O_3DPSA",
]


def parse_helm_monomers(helm_notation: str):
    start_index = helm_notation.find("{")
    end_index = helm_notation.find("}")
    if start_index == -1 or end_index == -1:
        return []
    sequence = helm_notation[start_index + 1:end_index]
    return [token.strip().strip("[]") for token in sequence.split(".") if token.strip()]


def normalize_text(tokens):
    return " ".join(tokens)


def build_monomer_lookup(monomer_df: pd.DataFrame):
    monomer_df = monomer_df.copy()
    monomer_df["Symbol"] = monomer_df["Symbol"].astype(str).str.strip()
    for col in MONOMER_FEATURE_COLUMNS:
        monomer_df[col] = pd.to_numeric(monomer_df[col], errors="coerce")
    return monomer_df.set_index("Symbol")[MONOMER_FEATURE_COLUMNS]


def aggregate_monomer_features(tokens, monomer_lookup):
    rows = []
    natural_count = 0
    n_methyl_count = 0
    d_count = 0
    aromatic_count = 0

    aromatic_symbols = {"F", "W", "Y", "H", "bHph"}

    for token in tokens:
        normalized = token.strip().strip("[]")
        if normalized in monomer_lookup.index:
            rows.append(monomer_lookup.loc[normalized].to_numpy(dtype=float))
        if normalized in NATURAL_SYMBOLS:
            natural_count += 1
        if normalized.lower().startswith("me") or "_me" in normalized.lower():
            n_methyl_count += 1
        if normalized.lower().startswith("d"):
            d_count += 1
        if normalized in aromatic_symbols or "ph" in normalized.lower():
            aromatic_count += 1

    base_features = {
        "seq_len": len(tokens),
        "unique_ratio": len(set(tokens)) / max(len(tokens), 1),
        "natural_ratio": natural_count / max(len(tokens), 1),
        "n_methyl_ratio": n_methyl_count / max(len(tokens), 1),
        "d_ratio": d_count / max(len(tokens), 1),
        "aromatic_ratio": aromatic_count / max(len(tokens), 1),
    }

    if rows:
        matrix = np.vstack(rows)
        for idx, col in enumerate(MONOMER_FEATURE_COLUMNS):
            base_features[f"{col}_mean"] = float(np.nanmean(matrix[:, idx]))
            base_features[f"{col}_std"] = float(np.nanstd(matrix[:, idx]))
            base_features[f"{col}_max"] = float(np.nanmax(matrix[:, idx]))
    else:
        for col in MONOMER_FEATURE_COLUMNS:
            base_features[f"{col}_mean"] = 0.0
            base_features[f"{col}_std"] = 0.0
            base_features[f"{col}_max"] = 0.0

    return base_features


def build_feature_table(label_df, peptide_df, monomer_df):
    peptide_features = peptide_df[["HELM", *PEPTIDE_FEATURE_COLUMNS]].copy()
    for col in PEPTIDE_FEATURE_COLUMNS:
        peptide_features[col] = pd.to_numeric(peptide_features[col], errors="coerce")

    merged = label_df.merge(peptide_features, on="HELM", how="left")
    monomer_lookup = build_monomer_lookup(monomer_df)

    merged["tokens"] = merged["HELM"].astype(str).apply(parse_helm_monomers)
    merged["text"] = merged["tokens"].apply(normalize_text)

    stat_df = pd.DataFrame(
        [aggregate_monomer_features(tokens, monomer_lookup) for tokens in merged["tokens"]]
    )

    full_df = pd.concat([merged.reset_index(drop=True), stat_df], axis=1)
    numeric_cols = [c for c in full_df.columns if c in PEPTIDE_FEATURE_COLUMNS or c in stat_df.columns]
    full_df[numeric_cols] = full_df[numeric_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    return full_df, numeric_cols


def evaluate_regression(y_true, y_pred):
    return {
        "rmse": float(mean_squared_error(y_true, y_pred) ** 0.5),
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


def build_matrices(train_df, test_df, numeric_cols):
    word_vectorizer = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2)
    char_vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2)

    x_train_word = word_vectorizer.fit_transform(train_df["text"])
    x_test_word = word_vectorizer.transform(test_df["text"])

    x_train_char = char_vectorizer.fit_transform(train_df["text"])
    x_test_char = char_vectorizer.transform(test_df["text"])

    scaler = StandardScaler()
    x_train_num = scaler.fit_transform(train_df[numeric_cols])
    x_test_num = scaler.transform(test_df[numeric_cols])

    x_train = hstack([x_train_word, x_train_char, csr_matrix(x_train_num)], format="csr")
    x_test = hstack([x_test_word, x_test_char, csr_matrix(x_test_num)], format="csr")
    return x_train, x_test


def run_single_split(train_df, test_df, numeric_cols, threshold):
    x_train, x_test = build_matrices(train_df, test_df, numeric_cols)

    reg_model = Ridge(alpha=1.0)
    reg_model.fit(x_train, train_df["Permeability"])
    reg_pred = reg_model.predict(x_test)

    cls_model = LogisticRegression(max_iter=3000, class_weight="balanced")
    cls_model.fit(x_train, train_df["label"])
    cls_pred = cls_model.predict(x_test)
    cls_prob = cls_model.predict_proba(x_test)[:, 1]

    return {
        "regression": evaluate_regression(test_df["Permeability"], reg_pred),
        "classification": evaluate_classification(test_df["label"], cls_pred, cls_prob),
        "predictions": pd.DataFrame(
            {
                "HELM": test_df["HELM"].to_numpy(),
                "Source": test_df["Source"].to_numpy(),
                "Year": test_df["Year"].to_numpy(),
                "Permeability": test_df["Permeability"].to_numpy(),
                "label": test_df["label"].to_numpy(),
                "regression_pred": reg_pred,
                "binary_pred": cls_pred,
                "binary_prob": cls_prob,
            }
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Train an enhanced public predictor for cyclic peptide permeability.")
    parser.add_argument("--label-csv", default=str(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv"))
    parser.add_argument("--peptide-csv", default=str(DATASET_DIR / "CycPeptMPDB_Peptide_All.csv"))
    parser.add_argument("--monomer-csv", default=str(DATASET_DIR / "CycPeptMPDB_Monomer_All.csv"))
    parser.add_argument("--result-dir", default=str(RESULT_DIR / "enhanced_predictor"))
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
    random_result = run_single_split(random_train, random_test, numeric_cols, args.threshold)

    gss = GroupShuffleSplit(n_splits=1, test_size=args.test_size, random_state=args.seed)
    train_idx, test_idx = next(gss.split(full_df, groups=full_df["Source"]))
    source_train = full_df.iloc[train_idx].copy()
    source_test = full_df.iloc[test_idx].copy()
    source_result = run_single_split(source_train, source_test, numeric_cols, args.threshold)

    metrics = {
        "num_samples": int(len(full_df)),
        "num_numeric_features": int(len(numeric_cols)),
        "threshold": float(args.threshold),
        "random_split": {
            "train_samples": int(len(random_train)),
            "test_samples": int(len(random_test)),
            "regression": random_result["regression"],
            "classification": random_result["classification"],
        },
        "source_split": {
            "train_samples": int(len(source_train)),
            "test_samples": int(len(source_test)),
            "num_train_sources": int(source_train["Source"].nunique()),
            "num_test_sources": int(source_test["Source"].nunique()),
            "regression": source_result["regression"],
            "classification": source_result["classification"],
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
