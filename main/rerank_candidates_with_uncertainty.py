import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main.screen_monomer_candidates import aggregate_monomer_features, build_training_frame
from main.train_enhanced_predictor import build_monomer_lookup, parse_helm_monomers
from utils.project_paths import DATASET_DIR, RESULT_DIR


def tree_prediction_std(rf_model, x):
    preds = np.vstack([est.predict(x) for est in rf_model.estimators_])
    return preds.std(axis=0)


def tree_positive_prob_std(rf_model, x):
    probs = []
    for est in rf_model.estimators_:
        p = est.predict_proba(x)
        if p.shape[1] == 1:
            cls = est.classes_[0]
            probs.append(np.ones(x.shape[0]) if cls == 1 else np.zeros(x.shape[0]))
        else:
            pos_idx = list(est.classes_).index(1)
            probs.append(p[:, pos_idx])
    probs = np.vstack(probs)
    return probs.std(axis=0)


def main():
    design_dir = RESULT_DIR / "design_pipeline"
    filtered_path = design_dir / "filtered_candidates.csv"
    out_path = design_dir / "diverse_top_candidates_uncertainty.csv"

    label_df = pd.read_csv(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv")
    monomer_df = pd.read_csv(DATASET_DIR / "CycPeptMPDB_Monomer_All.csv", low_memory=False)
    monomer_lookup = build_monomer_lookup(monomer_df)
    train_df = build_training_frame(label_df, monomer_lookup)
    feature_cols = [
        c for c in train_df.columns
        if c not in {"HELM", "Permeability", "Monomer_Length_in_Main_Chain", "Source", "Year", "tokens", "label"}
    ]

    reg = RandomForestRegressor(
        n_estimators=500,
        max_depth=None,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    cls = RandomForestClassifier(
        n_estimators=500,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )

    x_train = train_df[feature_cols].fillna(0.0).to_numpy()
    reg.fit(x_train, train_df["Permeability"].to_numpy())
    cls.fit(x_train, train_df["label"].to_numpy())

    candidate_df = pd.read_csv(filtered_path)
    candidate_df["tokens"] = candidate_df["tokens"].astype(str).apply(lambda s: s.split("."))
    feat_df = pd.DataFrame([aggregate_monomer_features(tokens, monomer_lookup) for tokens in candidate_df["tokens"]])
    x_cand = feat_df[feature_cols].fillna(0.0).to_numpy()

    candidate_df["predicted_permeability"] = reg.predict(x_cand)
    candidate_df["predicted_positive_prob"] = cls.predict_proba(x_cand)[:, 1]
    candidate_df["permeability_std"] = tree_prediction_std(reg, x_cand)
    candidate_df["positive_prob_std"] = tree_positive_prob_std(cls, x_cand)

    candidate_df["robust_score"] = (
        candidate_df["predicted_permeability"]
        - 0.5 * candidate_df["permeability_std"]
        + candidate_df["predicted_positive_prob"]
        - 0.25 * candidate_df["positive_prob_std"]
    )

    ranked = candidate_df.sort_values(
        ["robust_score", "predicted_positive_prob", "predicted_permeability"],
        ascending=False,
    ).reset_index(drop=True)
    ranked.head(100).to_csv(out_path, index=False)

    print("Top 20 uncertainty-aware candidates:")
    print(
        ranked[
            [
                "HELM",
                "parent_helm",
                "predicted_permeability",
                "predicted_positive_prob",
                "permeability_std",
                "positive_prob_std",
                "improvement",
                "robust_score",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )
    print(f"Saved uncertainty-aware ranking to: {out_path}")


if __name__ == "__main__":
    main()
