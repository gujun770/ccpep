import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main.screen_monomer_candidates import build_training_frame
from main.train_enhanced_predictor import build_monomer_lookup
from utils.project_paths import DATASET_DIR, RESULT_DIR


CASE_DESCRIPTORS = [
    "MolLogP_mean",
    "TPSA_mean",
    "FractionCSP3_mean",
    "qed_mean",
    "n_methyl_ratio",
    "d_ratio",
]


def nearest_reference(candidate_row, train_top_df):
    diffs = (
        (train_top_df["MolLogP_mean"] - candidate_row["MolLogP_mean"]).abs()
        + (train_top_df["TPSA_mean"] - candidate_row["TPSA_mean"]).abs() / 10.0
        + (train_top_df["n_methyl_ratio"] - candidate_row["n_methyl_ratio"]).abs()
        + (train_top_df["d_ratio"] - candidate_row["d_ratio"]).abs()
    )
    idx = diffs.idxmin()
    return train_top_df.loc[idx]


def build_optimized_cases(df, train_top_df, top_k=4):
    ranked = df.sort_values(["improvement", "predicted_positive_prob"], ascending=False).head(top_k).copy()
    rows = []
    for _, row in ranked.iterrows():
        ref = nearest_reference(row, train_top_df)
        out = {
            "route": "optimized",
            "candidate_helm": row["HELM"],
            "parent_helm": row["parent_helm"],
            "reference_helm": ref["HELM"],
            "predicted_permeability": row["predicted_permeability"],
            "predicted_positive_prob": row["predicted_positive_prob"],
            "improvement": row["improvement"],
            "mutation_description": row["mutation_description"],
        }
        for col in CASE_DESCRIPTORS:
            out[f"candidate_{col}"] = row[col]
            out[f"reference_{col}"] = ref[col]
            out[f"delta_to_reference_{col}"] = row[col] - ref[col]
        rows.append(out)
    return pd.DataFrame(rows)


def build_denovo_cases(df, train_top_df, top_k=4):
    ranked = df.sort_values(["multiobjective_score", "predicted_positive_prob"], ascending=False).head(top_k).copy()
    rows = []
    for _, row in ranked.iterrows():
        ref = nearest_reference(row, train_top_df)
        out = {
            "route": "de_novo",
            "candidate_helm": row["HELM"],
            "parent_helm": row.get("parent_tokens", ""),
            "reference_helm": ref["HELM"],
            "predicted_permeability": row["predicted_permeability"],
            "predicted_positive_prob": row["predicted_positive_prob"],
            "improvement": np.nan,
            "mutation_description": row.get("parent_tokens", ""),
            "multiobjective_score": row.get("multiobjective_score", np.nan),
            "motif_score": row.get("motif_score", np.nan),
        }
        for col in CASE_DESCRIPTORS:
            out[f"candidate_{col}"] = row[col]
            out[f"reference_{col}"] = ref[col]
            out[f"delta_to_reference_{col}"] = row[col] - ref[col]
        rows.append(out)
    return pd.DataFrame(rows)


def main():
    label_df = pd.read_csv(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv")
    monomer_df = pd.read_csv(DATASET_DIR / "CycPeptMPDB_Monomer_All.csv", low_memory=False)
    monomer_lookup = build_monomer_lookup(monomer_df)
    train_df = build_training_frame(label_df, monomer_lookup)
    train_top_df = train_df.sort_values("Permeability", ascending=False).head(100).copy()

    optimized_df = pd.read_csv(RESULT_DIR / "design_pipeline" / "final_shortlist.csv")
    de_novo_df = pd.read_csv(RESULT_DIR / "de_novo_generation" / "final_generated_shortlist.csv")

    out_dir = RESULT_DIR / "case_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    opt_cases = build_optimized_cases(optimized_df, train_top_df, top_k=4)
    denovo_cases = build_denovo_cases(de_novo_df, train_top_df, top_k=4)
    case_df = pd.concat([opt_cases, denovo_cases], ignore_index=True)
    case_df.to_csv(out_dir / "representative_cases.csv", index=False)

    compact_cols = [
        "route",
        "candidate_helm",
        "parent_helm",
        "reference_helm",
        "predicted_permeability",
        "predicted_positive_prob",
        "improvement",
        "mutation_description",
    ] + [f"delta_to_reference_{c}" for c in CASE_DESCRIPTORS]
    case_df[compact_cols].to_csv(out_dir / "representative_cases_compact.csv", index=False)

    descriptor_shift = []
    for _, row in case_df.iterrows():
        for col in CASE_DESCRIPTORS:
            descriptor_shift.append(
                {
                    "route": row["route"],
                    "candidate_helm": row["candidate_helm"],
                    "descriptor": col,
                    "candidate_value": row[f"candidate_{col}"],
                    "reference_value": row[f"reference_{col}"],
                    "delta_to_reference": row[f"delta_to_reference_{col}"],
                }
            )
    shift_df = pd.DataFrame(descriptor_shift)
    shift_df.to_csv(out_dir / "case_descriptor_shift_long.csv", index=False)

    print("Representative cases:")
    print(case_df[compact_cols].to_string(index=False))
    print(f"Saved case analysis to: {out_dir}")


if __name__ == "__main__":
    main()
