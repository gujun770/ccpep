import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main.train_enhanced_predictor import MONOMER_FEATURE_COLUMNS, build_monomer_lookup, parse_helm_monomers
from utils.project_paths import DATASET_DIR, RESULT_DIR


def aggregate_monomer_features(tokens, monomer_lookup):
    aromatic_symbols = {"F", "W", "Y", "H", "bHph"}
    natural_symbols = {
        "A", "R", "N", "D", "C", "Q", "E", "G", "H", "I",
        "L", "K", "M", "F", "P", "S", "T", "W", "Y", "V",
    }

    rows = []
    natural_count = 0
    n_methyl_count = 0
    d_count = 0
    aromatic_count = 0

    for token in tokens:
        if token in monomer_lookup.index:
            rows.append(monomer_lookup.loc[token].to_numpy(dtype=float))
        if token in natural_symbols:
            natural_count += 1
        if token.lower().startswith("me") or "_me" in token.lower():
            n_methyl_count += 1
        if token.lower().startswith("d"):
            d_count += 1
        if token in aromatic_symbols or "ph" in token.lower():
            aromatic_count += 1

    base = {
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
            base[f"{col}_mean"] = float(np.nanmean(matrix[:, idx]))
            base[f"{col}_std"] = float(np.nanstd(matrix[:, idx]))
            base[f"{col}_max"] = float(np.nanmax(matrix[:, idx]))
    else:
        for col in MONOMER_FEATURE_COLUMNS:
            base[f"{col}_mean"] = 0.0
            base[f"{col}_std"] = 0.0
            base[f"{col}_max"] = 0.0

    return base


def helm_with_tokens(original_helm: str, new_tokens):
    start = original_helm.find("{")
    end = original_helm.find("}")
    if start == -1 or end == -1:
        return original_helm
    return original_helm[: start + 1] + ".".join(
        [f"[{t}]" if not (len(t) == 1 and t.isalpha() and t.isupper()) else t for t in new_tokens]
    ) + original_helm[end:]


def build_training_frame(label_df, monomer_lookup):
    label_df = label_df.copy()
    label_df["tokens"] = label_df["HELM"].astype(str).apply(parse_helm_monomers)
    feature_rows = [aggregate_monomer_features(tokens, monomer_lookup) for tokens in label_df["tokens"]]
    feat_df = pd.DataFrame(feature_rows)
    merged = pd.concat([label_df.reset_index(drop=True), feat_df], axis=1)
    merged["label"] = (merged["Permeability"] >= -6.0).astype(int).to_numpy()
    return merged


def main():
    parser = argparse.ArgumentParser(description="Screen cyclic peptide candidates via monomer-aggregate RandomForest.")
    parser.add_argument("--label-csv", default=str(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv"))
    parser.add_argument("--monomer-csv", default=str(DATASET_DIR / "CycPeptMPDB_Monomer_All.csv"))
    parser.add_argument("--result-dir", default=str(RESULT_DIR / "candidate_screen"))
    parser.add_argument("--top-seeds", type=int, default=50)
    parser.add_argument("--top-monomers", type=int, default=20)
    args = parser.parse_args()

    result_dir = Path(args.result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    label_df = pd.read_csv(args.label_csv)
    monomer_df = pd.read_csv(args.monomer_csv, low_memory=False)
    monomer_lookup = build_monomer_lookup(monomer_df)

    train_df = build_training_frame(label_df, monomer_lookup)
    feature_cols = [c for c in train_df.columns if c not in {"HELM", "Permeability", "Monomer_Length_in_Main_Chain", "Source", "Year", "tokens", "label"}]

    x = train_df[feature_cols].fillna(0.0).to_numpy()
    y_reg = train_df["Permeability"].to_numpy()
    y_cls = train_df["label"].to_numpy()

    x_tr, x_te, y_cls_tr, y_cls_te = train_test_split(x, y_cls, test_size=0.2, random_state=42, stratify=y_cls)
    clf_probe = RandomForestClassifier(
        n_estimators=400, max_depth=None, min_samples_leaf=2, class_weight="balanced_subsample", random_state=42, n_jobs=-1
    )
    clf_probe.fit(x_tr, y_cls_tr)
    clf_prob = clf_probe.predict_proba(x_te)[:, 1]
    print(f"Probe classifier AUROC: {roc_auc_score(y_cls_te, clf_prob):.4f}")
    print(f"Probe classifier PR-AUC: {average_precision_score(y_cls_te, clf_prob):.4f}")

    reg = RandomForestRegressor(
        n_estimators=500, max_depth=None, min_samples_leaf=2, random_state=42, n_jobs=-1
    )
    cls = RandomForestClassifier(
        n_estimators=500, max_depth=None, min_samples_leaf=2, class_weight="balanced_subsample", random_state=42, n_jobs=-1
    )
    reg.fit(x, y_reg)
    cls.fit(x, y_cls)

    monomer_counter = {}
    for tokens in train_df["tokens"]:
        for token in tokens:
            monomer_counter[token] = monomer_counter.get(token, 0) + 1
    candidate_pool = [m for m, _ in sorted(monomer_counter.items(), key=lambda kv: kv[1], reverse=True)[: args.top_monomers]]

    seed_df = train_df.sort_values("Permeability", ascending=False).head(args.top_seeds).copy()
    existing_helms = set(train_df["HELM"].astype(str).tolist())
    candidate_rows = []

    for _, row in seed_df.iterrows():
        tokens = list(row["tokens"])
        for pos in range(len(tokens)):
            original = tokens[pos]
            for replacement in candidate_pool:
                if replacement == original:
                    continue
                mutated = tokens.copy()
                mutated[pos] = replacement
                helm = helm_with_tokens(row["HELM"], mutated)
                if helm in existing_helms:
                    continue
                features = aggregate_monomer_features(mutated, monomer_lookup)
                candidate_rows.append(
                    {
                        "parent_helm": row["HELM"],
                        "parent_permeability": row["Permeability"],
                        "position": pos,
                        "from_monomer": original,
                        "to_monomer": replacement,
                        "HELM": helm,
                        **features,
                    }
                )

    candidate_df = pd.DataFrame(candidate_rows).drop_duplicates(subset=["HELM"]).reset_index(drop=True)
    candidate_x = candidate_df[feature_cols].fillna(0.0).to_numpy()
    candidate_df["predicted_permeability"] = reg.predict(candidate_x)
    candidate_df["predicted_positive_prob"] = cls.predict_proba(candidate_x)[:, 1]
    candidate_df["score"] = candidate_df["predicted_permeability"] + candidate_df["predicted_positive_prob"]
    candidate_df = candidate_df.sort_values(
        ["predicted_positive_prob", "predicted_permeability"], ascending=False
    ).reset_index(drop=True)

    top_candidates = candidate_df.head(200)
    top_candidates.to_csv(result_dir / "top_candidates.csv", index=False)
    candidate_df.to_csv(result_dir / "all_candidates.csv", index=False)

    print(f"Generated candidates: {len(candidate_df)}")
    print("Top 20 candidates:")
    print(
        top_candidates[
            ["HELM", "parent_permeability", "position", "from_monomer", "to_monomer", "predicted_permeability", "predicted_positive_prob"]
        ].head(20).to_string(index=False)
    )
    print(f"Saved candidates to: {result_dir / 'top_candidates.csv'}")


if __name__ == "__main__":
    main()
