import argparse
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main.evaluate_generation_results import novelty_ratio, pairwise_jaccard_diversity, uniqueness_ratio
from main.generate_de_novo_peptides import (
    build_elite_profiles,
    evaluate_sequences,
    mutate_guided_tokens,
    sample_guided_peptides,
    select_top_diverse,
)
from main.screen_monomer_candidates import build_training_frame
from main.train_enhanced_predictor import build_monomer_lookup
from utils.project_paths import DATASET_DIR, RESULT_DIR


VARIANT_WEIGHTS = {
    "full": {
        "perm_quality": 0.30,
        "predicted_positive_prob": 0.24,
        "motif_score": 0.16,
        "composition_alignment": 0.16,
        "uncertainty_stability": 0.08,
        "novelty_score": 0.06,
    },
    "no_motif": {
        "perm_quality": 0.34,
        "predicted_positive_prob": 0.27,
        "motif_score": 0.00,
        "composition_alignment": 0.19,
        "uncertainty_stability": 0.11,
        "novelty_score": 0.09,
    },
    "no_composition": {
        "perm_quality": 0.34,
        "predicted_positive_prob": 0.27,
        "motif_score": 0.19,
        "composition_alignment": 0.00,
        "uncertainty_stability": 0.11,
        "novelty_score": 0.09,
    },
    "no_uncertainty": {
        "perm_quality": 0.33,
        "predicted_positive_prob": 0.26,
        "motif_score": 0.17,
        "composition_alignment": 0.17,
        "uncertainty_stability": 0.00,
        "novelty_score": 0.07,
    },
    "quality_only": {
        "perm_quality": 0.55,
        "predicted_positive_prob": 0.35,
        "motif_score": 0.00,
        "composition_alignment": 0.00,
        "uncertainty_stability": 0.00,
        "novelty_score": 0.10,
    },
}


def compute_variant_score(df: pd.DataFrame, variant_name: str) -> pd.Series:
    weights = VARIANT_WEIGHTS[variant_name]
    score = np.zeros(len(df), dtype=float)
    for column, weight in weights.items():
        score += weight * df[column].to_numpy(dtype=float)
    return pd.Series(score, index=df.index, name=f"{variant_name}_score")


def summarize_shortlist(name: str, df: pd.DataFrame, train_signatures: set[str]) -> dict:
    token_lists = [tokens.split(".") for tokens in df["tokens"].astype(str)]
    return {
        "variant": name,
        "final_count": int(len(df)),
        "uniqueness": uniqueness_ratio(token_lists),
        "novelty_vs_train": novelty_ratio(token_lists, train_signatures),
        "pairwise_jaccard_diversity": pairwise_jaccard_diversity(token_lists),
        "mean_predicted_permeability": float(df["predicted_permeability"].mean()),
        "mean_predicted_positive_prob": float(df["predicted_positive_prob"].mean()),
        "mean_perm_quality": float(df["perm_quality"].mean()),
        "mean_motif_score": float(df["motif_score"].mean()),
        "mean_composition_alignment": float(df["composition_alignment"].mean()),
        "mean_uncertainty_stability": float(df["uncertainty_stability"].mean()),
        "mean_natural_ratio": float(df["natural_ratio"].mean()),
        "mean_n_methyl_ratio": float(df["n_methyl_ratio"].mean()),
        "mean_d_ratio": float(df["d_ratio"].mean()),
    }


def main():
    parser = argparse.ArgumentParser(description="Ablation study for the multi-objective de novo generator.")
    parser.add_argument("--label-csv", default=str(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv"))
    parser.add_argument("--monomer-csv", default=str(DATASET_DIR / "CycPeptMPDB_Monomer_All.csv"))
    parser.add_argument("--result-dir", default=str(RESULT_DIR / "generator_ablation"))
    parser.add_argument("--global-samples", type=int, default=12000)
    parser.add_argument("--stage1-top-k", type=int, default=240)
    parser.add_argument("--local-offspring-per-seed", type=int, default=28)
    parser.add_argument("--final-top-k", type=int, default=80)
    parser.add_argument("--shortlist-k", type=int, default=24)
    parser.add_argument("--length", type=int, default=6)
    parser.add_argument("--elite-fraction", type=float, default=0.18)
    parser.add_argument("--n-jobs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    out_dir = Path(args.result_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    label_df = pd.read_csv(args.label_csv)
    monomer_df = pd.read_csv(args.monomer_csv, low_memory=False)
    monomer_lookup = build_monomer_lookup(monomer_df)
    train_df = build_training_frame(label_df, monomer_lookup)
    feature_cols = [
        c for c in train_df.columns
        if c not in {"HELM", "Permeability", "Monomer_Length_in_Main_Chain", "Source", "Year", "tokens", "label"}
    ]

    reg = RandomForestRegressor(
        n_estimators=500, max_depth=None, min_samples_leaf=2, random_state=args.seed, n_jobs=args.n_jobs
    )
    cls = RandomForestClassifier(
        n_estimators=500, max_depth=None, min_samples_leaf=2, class_weight="balanced_subsample", random_state=args.seed, n_jobs=args.n_jobs
    )
    x_train = train_df[feature_cols].fillna(0.0).to_numpy()
    reg.fit(x_train, train_df["Permeability"].to_numpy())
    cls.fit(x_train, train_df["label"].to_numpy())

    global_counts = {}
    for tokens in train_df["tokens"]:
        for token in tokens:
            global_counts[token] = global_counts.get(token, 0) + 1
    monomer_pool = [tok for tok, _ in sorted(global_counts.items(), key=lambda kv: kv[1], reverse=True)[:36]]
    _, position_probs, global_probs, elite_stats = build_elite_profiles(
        train_df, monomer_pool, elite_fraction=args.elite_fraction, alpha=1.0
    )
    train_signatures = set(train_df["tokens"].apply(lambda toks: ".".join(toks)).tolist())

    global_sequences = sample_guided_peptides(
        monomer_pool=monomer_pool,
        global_probs=global_probs,
        position_probs=position_probs,
        n_samples=args.global_samples,
        length=args.length,
        explore_rate=0.30,
    )
    stage1_base = evaluate_sequences(
        global_sequences,
        reg,
        cls,
        monomer_lookup,
        feature_cols,
        monomer_pool,
        global_probs,
        position_probs,
        train_signatures,
        elite_stats,
    )
    stage1_base = stage1_base.loc[stage1_base["novelty_score"] > 0].copy()

    summary_rows = []
    shortlist_frames = []

    for idx, variant in enumerate(VARIANT_WEIGHTS):
        variant_seed = args.seed + 1000 * (idx + 1)
        random.seed(variant_seed)
        np.random.seed(variant_seed)

        stage1_df = stage1_base.copy()
        stage1_df["variant_score"] = compute_variant_score(stage1_df, variant)
        stage1_df = stage1_df.sort_values(
            ["variant_score", "robust_score", "predicted_positive_prob", "predicted_permeability"],
            ascending=False,
        ).drop_duplicates(subset=["tokens"]).reset_index(drop=True)
        stage1_top = select_top_diverse(stage1_df, args.stage1_top_k, min_jaccard=0.28).copy()

        local_sequences = []
        parent_tokens = []
        for token_str in stage1_top["tokens"]:
            proposals = mutate_guided_tokens(
                tokens=token_str.split("."),
                monomer_pool=monomer_pool,
                global_probs=global_probs,
                position_probs=position_probs,
                offspring_per_seed=args.local_offspring_per_seed,
                position_top_k=8,
            )
            local_sequences.extend(proposals)
            parent_tokens.extend([token_str] * len(proposals))

        stage2_df = evaluate_sequences(
            local_sequences,
            reg,
            cls,
            monomer_lookup,
            feature_cols,
            monomer_pool,
            global_probs,
            position_probs,
            train_signatures,
            elite_stats,
        )
        stage2_df["parent_tokens"] = parent_tokens
        stage2_df = stage2_df.loc[stage2_df["novelty_score"] > 0].copy()
        stage2_df["variant_score"] = compute_variant_score(stage2_df, variant)
        stage2_df = stage2_df.sort_values(
            ["variant_score", "robust_score", "predicted_positive_prob", "predicted_permeability"],
            ascending=False,
        ).drop_duplicates(subset=["tokens"]).reset_index(drop=True)
        final_pool = select_top_diverse(stage2_df, args.final_top_k, min_jaccard=0.34).copy()
        shortlist = select_top_diverse(final_pool, args.shortlist_k, min_jaccard=0.34).copy()
        shortlist["variant"] = variant
        shortlist["rank"] = np.arange(1, len(shortlist) + 1)

        summary = summarize_shortlist(variant, shortlist, train_signatures)
        summary["stage1_top_count"] = int(len(stage1_top))
        summary["stage2_unique_count"] = int(len(stage2_df))
        summary["final_pool_count"] = int(len(final_pool))
        summary_rows.append(summary)
        shortlist_frames.append(shortlist)

    summary_df = pd.DataFrame(summary_rows).sort_values(
        ["mean_predicted_positive_prob", "pairwise_jaccard_diversity", "mean_predicted_permeability"],
        ascending=[False, False, False],
    )
    shortlist_df = pd.concat(shortlist_frames, ignore_index=True)

    narrative_rows = []
    full_row = summary_df.loc[summary_df["variant"] == "full"].iloc[0]
    for variant in summary_df["variant"]:
        if variant == "full":
            continue
        row = summary_df.loc[summary_df["variant"] == variant].iloc[0]
        narrative_rows.append(
            {
                "comparison": f"full_vs_{variant}",
                "delta_mean_predicted_positive_prob": float(full_row["mean_predicted_positive_prob"] - row["mean_predicted_positive_prob"]),
                "delta_pairwise_jaccard_diversity": float(full_row["pairwise_jaccard_diversity"] - row["pairwise_jaccard_diversity"]),
                "delta_mean_predicted_permeability": float(full_row["mean_predicted_permeability"] - row["mean_predicted_permeability"]),
            }
        )
    narrative_df = pd.DataFrame(narrative_rows)

    summary_df.to_csv(out_dir / "summary.csv", index=False)
    shortlist_df.to_csv(out_dir / "shortlists.csv", index=False)
    narrative_df.to_csv(out_dir / "narrative_summary.csv", index=False)

    print("Generator ablation summary:")
    print(
        summary_df[
            [
                "variant",
                "final_count",
                "uniqueness",
                "novelty_vs_train",
                "pairwise_jaccard_diversity",
                "mean_predicted_permeability",
                "mean_predicted_positive_prob",
                "mean_motif_score",
                "mean_composition_alignment",
                "mean_uncertainty_stability",
            ]
        ].to_string(index=False)
    )
    print(f"Saved ablation summary to: {out_dir / 'summary.csv'}")


if __name__ == "__main__":
    main()
