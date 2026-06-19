import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import RESULT_DIR


def parse_tokens(token_str: str):
    if not isinstance(token_str, str):
        return []
    return [t for t in token_str.split(".") if t]


def composition_signature(tokens):
    return ".".join(sorted(tokens))


def main():
    design_path = RESULT_DIR / "design_pipeline" / "final_shortlist.csv"
    de_novo_path = RESULT_DIR / "de_novo_generation" / "final_generated_shortlist.csv"
    out_dir = RESULT_DIR / "docking_candidates"
    out_dir.mkdir(parents=True, exist_ok=True)

    design_df = pd.read_csv(design_path)
    design_df["candidate_type"] = "optimized"
    design_df["source_route"] = "design_pipeline"
    if "tokens" not in design_df.columns:
        design_df["tokens"] = design_df["HELM"].astype(str).apply(
            lambda h: ".".join(
                [t.strip("[]") for t in h[h.find("{") + 1 : h.find("}")].split(".") if t.strip()]
            )
        )

    de_novo_df = pd.read_csv(de_novo_path)
    de_novo_df["candidate_type"] = "de_novo"
    de_novo_df["source_route"] = "de_novo_generation"
    de_novo_df["parent_helm"] = de_novo_df.get("parent_helm", pd.Series(["NA"] * len(de_novo_df)))
    de_novo_df["improvement"] = de_novo_df.get("improvement", pd.Series([pd.NA] * len(de_novo_df)))

    common_cols = sorted(set(design_df.columns) | set(de_novo_df.columns))
    merged = pd.concat(
        [design_df.reindex(columns=common_cols), de_novo_df.reindex(columns=common_cols)],
        ignore_index=True,
    )

    merged["tokens_list"] = merged["tokens"].astype(str).apply(parse_tokens)
    merged["composition_signature"] = merged["tokens_list"].apply(composition_signature)
    merged = (
        merged.sort_values(
            ["predicted_positive_prob", "predicted_permeability"],
            ascending=False,
        )
        .drop_duplicates(subset=["composition_signature"])
        .reset_index(drop=True)
    )

    docking_top = merged.head(20).copy()
    docking_top.drop(columns=["tokens_list"], inplace=True, errors="ignore")
    docking_top.to_csv(out_dir / "top20_docking_candidates.csv", index=False)
    merged.drop(columns=["tokens_list"], inplace=True, errors="ignore")
    merged.to_csv(out_dir / "all_docking_candidates.csv", index=False)

    type_summary = (
        docking_top["candidate_type"].value_counts().reset_index()
    )
    type_summary.columns = ["candidate_type", "count"]
    type_summary.to_csv(out_dir / "candidate_type_summary.csv", index=False)

    print("Top docking candidates:")
    print(
        docking_top[
            [
                "candidate_type",
                "HELM",
                "predicted_permeability",
                "predicted_positive_prob",
                "source_route",
                "parent_helm",
                "improvement",
            ]
        ].to_string(index=False)
    )
    print("---")
    print("Candidate type summary:")
    print(type_summary.to_string(index=False))
    print(f"Saved docking set to: {out_dir / 'top20_docking_candidates.csv'}")


if __name__ == "__main__":
    main()
