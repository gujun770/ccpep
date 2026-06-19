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


KEY_DESCRIPTORS = [
    "MolLogP_mean",
    "TPSA_mean",
    "FractionCSP3_mean",
    "qed_mean",
    "n_methyl_ratio",
    "d_ratio",
    "aromatic_ratio",
]


def summarize_group(name, df, descriptors):
    row = {"group": name, "count": int(len(df))}
    for col in descriptors:
        row[f"{col}_mean"] = float(df[col].mean())
        row[f"{col}_std"] = float(df[col].std()) if len(df) > 1 else 0.0
    return row


def shift_row(descriptor, overall_df, target_df, candidate_df, candidate_name):
    overall_mean = float(overall_df[descriptor].mean())
    overall_std = float(overall_df[descriptor].std()) or 1.0
    target_mean = float(target_df[descriptor].mean())
    candidate_mean = float(candidate_df[descriptor].mean())
    target_gap = abs(candidate_mean - target_mean)
    baseline_gap = abs(overall_mean - target_mean)
    improvement = baseline_gap - target_gap
    return {
        "candidate_group": candidate_name,
        "descriptor": descriptor,
        "overall_train_mean": overall_mean,
        "train_top100_mean": target_mean,
        "candidate_mean": candidate_mean,
        "candidate_z_vs_overall": (candidate_mean - overall_mean) / overall_std,
        "distance_to_train_top100": target_gap,
        "improvement_toward_train_top100": improvement,
    }


def main():
    label_df = pd.read_csv(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv")
    monomer_df = pd.read_csv(DATASET_DIR / "CycPeptMPDB_Monomer_All.csv", low_memory=False)
    monomer_lookup = build_monomer_lookup(monomer_df)

    train_df = build_training_frame(label_df, monomer_lookup)
    train_top100 = train_df.sort_values("Permeability", ascending=False).head(100).copy()
    optimized_df = pd.read_csv(RESULT_DIR / "design_pipeline" / "final_shortlist.csv")
    de_novo_df = pd.read_csv(RESULT_DIR / "de_novo_generation" / "final_generated_shortlist.csv")

    out_dir = RESULT_DIR / "mechanism_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_df = pd.DataFrame(
        [
            summarize_group("overall_train", train_df, KEY_DESCRIPTORS),
            summarize_group("train_top100", train_top100, KEY_DESCRIPTORS),
            summarize_group("optimized_shortlist", optimized_df, KEY_DESCRIPTORS),
            summarize_group("de_novo_shortlist", de_novo_df, KEY_DESCRIPTORS),
        ]
    )
    summary_df.to_csv(out_dir / "descriptor_group_summary.csv", index=False)

    shift_rows = []
    for descriptor in KEY_DESCRIPTORS:
        shift_rows.append(shift_row(descriptor, train_df, train_top100, optimized_df, "optimized_shortlist"))
        shift_rows.append(shift_row(descriptor, train_df, train_top100, de_novo_df, "de_novo_shortlist"))
    shift_df = pd.DataFrame(shift_rows)
    shift_df.to_csv(out_dir / "descriptor_shift_summary.csv", index=False)

    best_shift = (
        shift_df.sort_values(["candidate_group", "improvement_toward_train_top100"], ascending=[True, False])
        .groupby("candidate_group")
        .head(3)
        .reset_index(drop=True)
    )
    best_shift.to_csv(out_dir / "top_descriptor_shifts.csv", index=False)

    narrative_df = pd.DataFrame(
        [
            {
                "finding": "optimized_profile",
                "summary": (
                    f"Optimized shortlist shows mean MolLogP {optimized_df['MolLogP_mean'].mean():.3f}, "
                    f"TPSA {optimized_df['TPSA_mean'].mean():.3f}, and n-methyl ratio {optimized_df['n_methyl_ratio'].mean():.3f}."
                ),
            },
            {
                "finding": "denovo_profile",
                "summary": (
                    f"De novo shortlist shows mean MolLogP {de_novo_df['MolLogP_mean'].mean():.3f}, "
                    f"TPSA {de_novo_df['TPSA_mean'].mean():.3f}, and n-methyl ratio {de_novo_df['n_methyl_ratio'].mean():.3f}."
                ),
            },
            {
                "finding": "top_shifts",
                "summary": (
                    "The strongest descriptor shifts toward the high-permeability reference set are observed in "
                    + ", ".join(
                        f"{row['candidate_group']}:{row['descriptor']}"
                        for _, row in best_shift.head(4).iterrows()
                    )
                    + "."
                ),
            },
        ]
    )
    narrative_df.to_csv(out_dir / "narrative_summary.csv", index=False)

    print("Descriptor mechanism summary:")
    print(summary_df[["group", "count"] + [f"{c}_mean" for c in KEY_DESCRIPTORS]].to_string(index=False))
    print("---")
    print("Top descriptor shifts toward train_top100:")
    print(best_shift.to_string(index=False))
    print(f"Saved mechanism analysis to: {out_dir}")


if __name__ == "__main__":
    main()
