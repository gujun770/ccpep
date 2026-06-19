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


def jaccard_distance(tokens_a, tokens_b):
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return 1.0 - (len(set_a & set_b) / union)


def build_shortlist(df, top_k=12, max_per_parent=2, min_jaccard_distance=0.34):
    selected = []
    selected_tokens = []
    parent_counter = {}
    seen_compositions = set()

    for _, row in df.iterrows():
        parent = row["parent_helm"]
        if parent_counter.get(parent, 0) >= max_per_parent:
            continue
        tokens = row["tokens_list"]
        comp = row["composition_signature"]
        if comp in seen_compositions:
            continue

        keep = True
        for existing in selected_tokens:
            if jaccard_distance(tokens, existing) < min_jaccard_distance:
                keep = False
                break
        if not keep:
            continue

        selected.append(row)
        selected_tokens.append(tokens)
        seen_compositions.add(comp)
        parent_counter[parent] = parent_counter.get(parent, 0) + 1
        if len(selected) >= top_k:
            break

    return pd.DataFrame(selected)


def main():
    in_path = RESULT_DIR / "design_pipeline" / "diverse_top_candidates_uncertainty.csv"
    out_path = RESULT_DIR / "design_pipeline" / "final_shortlist.csv"

    df = pd.read_csv(in_path)
    df["tokens_list"] = df["tokens"].astype(str).apply(parse_tokens)
    df["composition_signature"] = df["tokens_list"].apply(composition_signature)

    ranked = df.sort_values(
        ["robust_score", "improvement", "predicted_positive_prob"],
        ascending=False,
    ).reset_index(drop=True)

    shortlist = build_shortlist(ranked, top_k=12, max_per_parent=2, min_jaccard_distance=0.34)
    shortlist = shortlist.copy()
    shortlist.drop(columns=["tokens_list"], inplace=True, errors="ignore")
    shortlist.to_csv(out_path, index=False)

    print("Final shortlist:")
    print(
        shortlist[
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
        ].to_string(index=False)
    )
    print(f"Saved final shortlist to: {out_path}")


if __name__ == "__main__":
    main()
