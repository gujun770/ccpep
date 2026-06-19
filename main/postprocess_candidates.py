import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import RESULT_DIR


def parse_tokens(helm: str):
    start = helm.find("{")
    end = helm.find("}")
    if start == -1 or end == -1:
        return []
    return [token.strip().strip("[]") for token in helm[start + 1:end].split(".") if token.strip()]


def canonical_signature(helm: str) -> str:
    return ".".join(parse_tokens(helm))


def main():
    in_path = RESULT_DIR / "candidate_screen" / "all_candidates.csv"
    out_dir = RESULT_DIR / "candidate_screen"
    df = pd.read_csv(in_path)

    df["signature"] = df["HELM"].astype(str).apply(canonical_signature)
    df["improvement"] = df["predicted_permeability"] - df["parent_permeability"]

    dedup_df = (
        df.sort_values(
            ["predicted_positive_prob", "predicted_permeability", "improvement"],
            ascending=False,
        )
        .drop_duplicates(subset=["signature"])
        .reset_index(drop=True)
    )

    top_unique = dedup_df.head(100).copy()
    top_unique.to_csv(out_dir / "top_candidates_unique.csv", index=False)

    substitution_summary = (
        dedup_df.groupby(["from_monomer", "to_monomer"])
        .agg(
            count=("HELM", "size"),
            mean_predicted_permeability=("predicted_permeability", "mean"),
            mean_positive_prob=("predicted_positive_prob", "mean"),
            mean_improvement=("improvement", "mean"),
        )
        .reset_index()
        .sort_values(
            ["mean_positive_prob", "mean_predicted_permeability", "count"],
            ascending=False,
        )
    )
    substitution_summary.to_csv(out_dir / "substitution_summary.csv", index=False)

    position_summary = (
        dedup_df.groupby("position")
        .agg(
            count=("HELM", "size"),
            mean_predicted_permeability=("predicted_permeability", "mean"),
            mean_positive_prob=("predicted_positive_prob", "mean"),
            mean_improvement=("improvement", "mean"),
        )
        .reset_index()
        .sort_values("mean_positive_prob", ascending=False)
    )
    position_summary.to_csv(out_dir / "position_summary.csv", index=False)

    print(f"Unique candidates: {len(dedup_df)}")
    print("Top 15 unique candidates:")
    print(
        top_unique[
            [
                "HELM",
                "parent_permeability",
                "position",
                "from_monomer",
                "to_monomer",
                "predicted_permeability",
                "predicted_positive_prob",
                "improvement",
            ]
        ]
        .head(15)
        .to_string(index=False)
    )
    print("---")
    print("Top 15 substitutions:")
    print(substitution_summary.head(15).to_string(index=False))
    print(f"Saved unique candidates to: {out_dir / 'top_candidates_unique.csv'}")


if __name__ == "__main__":
    main()
