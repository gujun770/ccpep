import ast
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main.train_enhanced_predictor import parse_helm_monomers
from main.screen_monomer_candidates import build_training_frame
from main.train_enhanced_predictor import build_monomer_lookup
from utils.project_paths import DATASET_DIR, RESULT_DIR


DESCRIPTOR_COLS = [
    "natural_ratio",
    "n_methyl_ratio",
    "d_ratio",
    "aromatic_ratio",
    "MolWt_mean",
    "MolWt_std",
    "TPSA_mean",
    "TPSA_std",
    "MolLogP_mean",
    "MolLogP_std",
    "qed_mean",
    "qed_std",
    "FractionCSP3_mean",
    "FractionCSP3_std",
    "HeavyAtomCount_mean",
    "HeavyAtomCount_std",
    "NumHAcceptors_mean",
    "NumHAcceptors_std",
    "NumHDonors_mean",
    "NumHDonors_std",
    "RingCount_mean",
    "RingCount_std",
]


def parse_token_string(token_str):
    if not isinstance(token_str, str):
        return []
    if token_str.startswith("[") and token_str.endswith("]"):
        try:
            parsed = ast.literal_eval(token_str)
            if isinstance(parsed, list):
                return [str(t) for t in parsed]
        except Exception:
            pass
    return [t for t in token_str.split(".") if t]


def token_jaccard_similarity(tokens_a, tokens_b):
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return len(set_a & set_b) / union


def nearest_token_neighbor(candidate_tokens, train_token_lists):
    best_idx = -1
    best_sim = -1.0
    for idx, train_tokens in enumerate(train_token_lists):
        sim = token_jaccard_similarity(candidate_tokens, train_tokens)
        if sim > best_sim:
            best_sim = sim
            best_idx = idx
    return best_idx, best_sim


def build_route_frame(path: Path, route_name: str):
    df = pd.read_csv(path)
    if "tokens" in df.columns:
        df["tokens_list"] = df["tokens"].astype(str).apply(parse_token_string)
    else:
        raise ValueError(f"Missing tokens column in {path}")
    df["route"] = route_name
    return df


def main():
    out_dir = RESULT_DIR / "candidate_novelty_depth"
    out_dir.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_csv(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv")
    train_df["tokens_list"] = train_df["HELM"].apply(parse_helm_monomers)
    monomer_df = pd.read_csv(DATASET_DIR / "CycPeptMPDB_Monomer_All.csv", low_memory=False)
    monomer_lookup = build_monomer_lookup(monomer_df)
    train_feature_df = build_training_frame(train_df.copy(), monomer_lookup)

    optimized_df = build_route_frame(RESULT_DIR / "design_pipeline" / "final_shortlist.csv", "optimized_shortlist")
    denovo_df = build_route_frame(RESULT_DIR / "de_novo_generation" / "final_generated_shortlist.csv", "de_novo_shortlist")
    candidates = pd.concat([optimized_df, denovo_df], ignore_index=True)

    train_token_lists = train_df["tokens_list"].tolist()
    token_neighbor_idx = []
    token_neighbor_sim = []
    for tokens in candidates["tokens_list"]:
        idx, sim = nearest_token_neighbor(tokens, train_token_lists)
        token_neighbor_idx.append(idx)
        token_neighbor_sim.append(sim)
    candidates["nearest_train_token_idx"] = token_neighbor_idx
    candidates["nearest_train_token_jaccard"] = token_neighbor_sim
    candidates["nearest_train_helm"] = candidates["nearest_train_token_idx"].apply(lambda i: train_df.iloc[i]["HELM"])
    candidates["nearest_train_permeability"] = candidates["nearest_train_token_idx"].apply(lambda i: train_df.iloc[i]["Permeability"])

    common_cols = [c for c in DESCRIPTOR_COLS if c in candidates.columns]
    available_train_cols = [c for c in common_cols if c in train_feature_df.columns]
    train_matrix = train_feature_df[available_train_cols].fillna(0.0).to_numpy(dtype=float)
    cand_matrix = candidates[available_train_cols].fillna(0.0).to_numpy(dtype=float)
    dists = cdist(cand_matrix, train_matrix, metric="euclidean")
    nearest_desc_idx = dists.argmin(axis=1)
    nearest_desc_dist = dists.min(axis=1)
    candidates["nearest_descriptor_idx"] = nearest_desc_idx
    candidates["nearest_descriptor_distance"] = nearest_desc_dist
    candidates["nearest_descriptor_helm"] = train_feature_df.iloc[nearest_desc_idx]["HELM"].to_numpy()
    candidates["nearest_descriptor_permeability"] = train_feature_df.iloc[nearest_desc_idx]["Permeability"].to_numpy()

    detail_cols = [
        "route",
        "HELM",
        "predicted_permeability",
        "predicted_positive_prob",
        "nearest_train_token_jaccard",
        "nearest_train_permeability",
        "nearest_train_helm",
        "nearest_descriptor_distance",
        "nearest_descriptor_permeability",
        "nearest_descriptor_helm",
    ]
    candidates[detail_cols].to_csv(out_dir / "candidate_nearest_neighbors.csv", index=False)

    summary_rows = []
    for route, sub in candidates.groupby("route"):
        summary_rows.append(
            {
                "route": route,
                "count": int(len(sub)),
                "mean_nearest_train_token_jaccard": float(sub["nearest_train_token_jaccard"].mean()),
                "median_nearest_train_token_jaccard": float(sub["nearest_train_token_jaccard"].median()),
                "max_nearest_train_token_jaccard": float(sub["nearest_train_token_jaccard"].max()),
                "mean_nearest_descriptor_distance": float(sub["nearest_descriptor_distance"].mean()),
                "median_nearest_descriptor_distance": float(sub["nearest_descriptor_distance"].median()),
                "min_nearest_descriptor_distance": float(sub["nearest_descriptor_distance"].min()),
            }
        )
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(out_dir / "summary.csv", index=False)

    narrative = pd.DataFrame(
        [
            {
                "finding": "optimized_neighbor_similarity",
                "summary": (
                    f"Optimized candidates have mean nearest-train token Jaccard "
                    f"{summary_df.loc[summary_df['route']=='optimized_shortlist', 'mean_nearest_train_token_jaccard'].iloc[0]:.3f}."
                ),
            },
            {
                "finding": "denovo_neighbor_similarity",
                "summary": (
                    f"De novo candidates have mean nearest-train token Jaccard "
                    f"{summary_df.loc[summary_df['route']=='de_novo_shortlist', 'mean_nearest_train_token_jaccard'].iloc[0]:.3f}, "
                    f"supporting novelty beyond exact duplication."
                ),
            },
            {
                "finding": "descriptor_distance_compare",
                "summary": (
                    f"Mean nearest-descriptor distance is "
                    f"{summary_df.loc[summary_df['route']=='optimized_shortlist', 'mean_nearest_descriptor_distance'].iloc[0]:.3f} "
                    f"for optimized candidates and "
                    f"{summary_df.loc[summary_df['route']=='de_novo_shortlist', 'mean_nearest_descriptor_distance'].iloc[0]:.3f} "
                    f"for de novo candidates."
                ),
            },
        ]
    )
    narrative.to_csv(out_dir / "narrative_summary.csv", index=False)

    print("Candidate novelty depth summary:")
    print(summary_df.to_string(index=False))
    print(f"Saved novelty-depth analysis to: {out_dir}")


if __name__ == "__main__":
    main()
