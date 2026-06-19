import ast
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main.train_enhanced_predictor import parse_helm_monomers
from utils.project_paths import DATASET_DIR, RESULT_DIR


NATURAL_SYMBOLS = {
    "A", "R", "N", "D", "C", "Q", "E", "G", "H", "I",
    "L", "K", "M", "F", "P", "S", "T", "W", "Y", "V",
}


def parse_token_string(token_str):
    if isinstance(token_str, list):
        return token_str
    if not isinstance(token_str, str):
        return []
    if token_str.startswith("[") and token_str.endswith("]"):
        try:
            parsed = ast.literal_eval(token_str)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except Exception:
            pass
    return [t for t in token_str.split(".") if t]


def natural_ratio(tokens):
    return sum(t in NATURAL_SYMBOLS for t in tokens) / max(len(tokens), 1)


def n_methyl_ratio(tokens):
    return sum(t.lower().startswith("me") or "_me" in t.lower() for t in tokens) / max(len(tokens), 1)


def d_ratio(tokens):
    return sum(t.lower().startswith("d") for t in tokens) / max(len(tokens), 1)


def jaccard_distance(tokens_a, tokens_b):
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return 1.0 - (len(set_a & set_b) / union)


def pairwise_diversity(token_lists):
    if len(token_lists) < 2:
        return 0.0
    distances = []
    for i in range(len(token_lists)):
        for j in range(i + 1, len(token_lists)):
            distances.append(jaccard_distance(token_lists[i], token_lists[j]))
    return float(np.mean(distances)) if distances else 0.0


def main():
    design_dir = RESULT_DIR / "design_pipeline"
    candidates_path = design_dir / "diverse_top_candidates.csv"
    summary_path = design_dir / "design_analysis_summary.csv"
    substitution_path = design_dir / "design_substitution_summary.csv"
    case_path = design_dir / "design_case_table.csv"

    candidate_df = pd.read_csv(candidates_path)
    label_df = pd.read_csv(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv")

    candidate_df["tokens"] = candidate_df["tokens"].apply(parse_token_string)
    if "from_monomer" not in candidate_df.columns:
        candidate_df["from_monomer"] = "NA"
    if "to_monomer" not in candidate_df.columns:
        candidate_df["to_monomer"] = "NA"
    if "mutation_description" not in candidate_df.columns:
        candidate_df["mutation_description"] = candidate_df.get("mutation_sites", "NA")
    candidate_df["natural_ratio_calc"] = candidate_df["tokens"].apply(natural_ratio)
    candidate_df["n_methyl_ratio"] = candidate_df["tokens"].apply(n_methyl_ratio)
    candidate_df["d_ratio"] = candidate_df["tokens"].apply(d_ratio)

    seed_df = label_df.loc[label_df["HELM"].isin(candidate_df["parent_helm"])].copy()
    seed_df["tokens"] = seed_df["HELM"].apply(parse_helm_monomers)
    seed_df["natural_ratio_calc"] = seed_df["tokens"].apply(natural_ratio)
    seed_df["n_methyl_ratio"] = seed_df["tokens"].apply(n_methyl_ratio)
    seed_df["d_ratio"] = seed_df["tokens"].apply(d_ratio)

    summary = pd.DataFrame(
        [
            {
                "num_unique_parents": int(candidate_df["parent_helm"].nunique()),
                "num_optimized_candidates": int(len(candidate_df)),
                "mean_parent_permeability": float(candidate_df["parent_permeability"].mean()),
                "mean_predicted_permeability": float(candidate_df["predicted_permeability"].mean()),
                "mean_improvement": float(candidate_df["improvement"].mean()),
                "mean_positive_prob": float(candidate_df["predicted_positive_prob"].mean()),
                "mean_seed_natural_ratio": float(seed_df["natural_ratio_calc"].mean()),
                "mean_candidate_natural_ratio": float(candidate_df["natural_ratio_calc"].mean()),
                "mean_seed_n_methyl_ratio": float(seed_df["n_methyl_ratio"].mean()),
                "mean_candidate_n_methyl_ratio": float(candidate_df["n_methyl_ratio"].mean()),
                "mean_seed_d_ratio": float(seed_df["d_ratio"].mean()),
                "mean_candidate_d_ratio": float(candidate_df["d_ratio"].mean()),
                "candidate_pairwise_jaccard_distance": pairwise_diversity(candidate_df["tokens"].tolist()),
            }
        ]
    )
    summary.to_csv(summary_path, index=False)

    substitution_summary = (
        candidate_df.groupby(["from_monomer", "to_monomer"])
        .agg(
            count=("HELM", "size"),
            mean_predicted_permeability=("predicted_permeability", "mean"),
            mean_improvement=("improvement", "mean"),
            mean_positive_prob=("predicted_positive_prob", "mean"),
        )
        .reset_index()
        .sort_values(["count", "mean_improvement"], ascending=[False, False])
    )
    substitution_summary.to_csv(substitution_path, index=False)

    case_table = candidate_df[
        [
            "HELM",
            "parent_helm",
            "parent_permeability",
            "predicted_permeability",
            "predicted_positive_prob",
            "improvement",
            "mutation_sites",
            "mutation_count",
            "from_monomer",
            "to_monomer",
            "natural_ratio_calc",
            "n_methyl_ratio",
            "d_ratio",
        ]
    ].sort_values(
        ["predicted_positive_prob", "predicted_permeability", "improvement"],
        ascending=False,
    )
    case_table.to_csv(case_path, index=False)

    print("Design summary:")
    print(summary.to_string(index=False))
    print("---")
    print("Top substitutions:")
    print(substitution_summary.head(15).to_string(index=False))
    print("---")
    print("Top design cases:")
    print(case_table.head(15).to_string(index=False))
    print(f"Saved summary to: {summary_path}")


if __name__ == "__main__":
    main()
