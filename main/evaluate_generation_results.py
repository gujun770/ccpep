import sys
from pathlib import Path
import ast

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


def natural_ratio(tokens):
    return sum(t in NATURAL_SYMBOLS for t in tokens) / max(len(tokens), 1)


def n_methyl_ratio(tokens):
    return sum(t.lower().startswith("me") or "_me" in t.lower() for t in tokens) / max(len(tokens), 1)


def d_ratio(tokens):
    return sum(t.lower().startswith("d") for t in tokens) / max(len(tokens), 1)


def uniqueness_ratio(token_lists):
    signatures = [".".join(tokens) for tokens in token_lists]
    return len(set(signatures)) / max(len(signatures), 1)


def novelty_ratio(token_lists, train_signatures):
    signatures = [".".join(tokens) for tokens in token_lists]
    return sum(sig not in train_signatures for sig in signatures) / max(len(signatures), 1)


def pairwise_jaccard_diversity(token_lists):
    if len(token_lists) < 2:
        return 0.0
    distances = []
    for i in range(len(token_lists)):
        set_i = set(token_lists[i])
        for j in range(i + 1, len(token_lists)):
            set_j = set(token_lists[j])
            union = len(set_i | set_j)
            if union == 0:
                distances.append(0.0)
            else:
                distances.append(1.0 - len(set_i & set_j) / union)
    return float(np.mean(distances)) if distances else 0.0


def summarize_group(name, df, train_signatures):
    token_lists = df["tokens_list"].tolist()
    out = {
        "group": name,
        "count": int(len(df)),
        "uniqueness": uniqueness_ratio(token_lists),
        "novelty_vs_train": novelty_ratio(token_lists, train_signatures),
        "pairwise_jaccard_diversity": pairwise_jaccard_diversity(token_lists),
        "mean_natural_ratio": float(df["natural_ratio_calc"].mean()),
        "mean_n_methyl_ratio": float(df["n_methyl_ratio"].mean()),
        "mean_d_ratio": float(df["d_ratio"].mean()),
    }
    if "predicted_permeability" in df.columns:
        out["mean_predicted_permeability"] = float(df["predicted_permeability"].mean())
    if "predicted_positive_prob" in df.columns:
        out["mean_predicted_positive_prob"] = float(df["predicted_positive_prob"].mean())
    if "improvement" in df.columns and df["improvement"].notna().any():
        out["mean_improvement"] = float(df["improvement"].dropna().mean())
    return out


def monomer_frequency(df, group_name):
    tokens = df["tokens_list"].explode()
    freq = tokens.value_counts().reset_index()
    freq.columns = ["monomer", "count"]
    freq["group"] = group_name
    return freq


def main():
    label_df = pd.read_csv(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv")
    optimized_df = pd.read_csv(RESULT_DIR / "design_pipeline" / "final_shortlist.csv")
    de_novo_df = pd.read_csv(RESULT_DIR / "de_novo_generation" / "final_generated_shortlist.csv")

    label_df["tokens_list"] = label_df["HELM"].apply(parse_helm_monomers)
    label_df["natural_ratio_calc"] = label_df["tokens_list"].apply(natural_ratio)
    label_df["n_methyl_ratio"] = label_df["tokens_list"].apply(n_methyl_ratio)
    label_df["d_ratio"] = label_df["tokens_list"].apply(d_ratio)
    train_signatures = set(label_df["tokens_list"].apply(lambda x: ".".join(x)).tolist())

    high_train_df = label_df.sort_values("Permeability", ascending=False).head(100).copy()

    optimized_df["tokens_list"] = optimized_df["tokens"].astype(str).apply(parse_token_string)
    optimized_df["natural_ratio_calc"] = optimized_df["tokens_list"].apply(natural_ratio)
    optimized_df["n_methyl_ratio"] = optimized_df["tokens_list"].apply(n_methyl_ratio)
    optimized_df["d_ratio"] = optimized_df["tokens_list"].apply(d_ratio)

    de_novo_df["tokens_list"] = de_novo_df["tokens"].astype(str).apply(parse_token_string)
    de_novo_df["natural_ratio_calc"] = de_novo_df["tokens_list"].apply(natural_ratio)
    de_novo_df["n_methyl_ratio"] = de_novo_df["tokens_list"].apply(n_methyl_ratio)
    de_novo_df["d_ratio"] = de_novo_df["tokens_list"].apply(d_ratio)

    summary_rows = [
        summarize_group("train_top100", high_train_df, train_signatures),
        summarize_group("optimized_shortlist", optimized_df, train_signatures),
        summarize_group("de_novo_shortlist", de_novo_df, train_signatures),
    ]
    summary_df = pd.DataFrame(summary_rows)

    freq_df = pd.concat(
        [
            monomer_frequency(high_train_df, "train_top100"),
            monomer_frequency(optimized_df, "optimized_shortlist"),
            monomer_frequency(de_novo_df, "de_novo_shortlist"),
        ],
        ignore_index=True,
    )

    out_dir = RESULT_DIR / "generation_evaluation"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(out_dir / "summary.csv", index=False)
    freq_df.to_csv(out_dir / "monomer_frequency.csv", index=False)

    narrative = pd.DataFrame(
        [
            {
                "finding": "optimized_vs_train",
                "summary": (
                    f"Optimized shortlist keeps novelty {summary_df.loc[summary_df['group']=='optimized_shortlist', 'novelty_vs_train'].iloc[0]:.2f} "
                    f"with mean predicted permeability {summary_df.loc[summary_df['group']=='optimized_shortlist', 'mean_predicted_permeability'].iloc[0]:.3f}."
                ),
            },
            {
                "finding": "denovo_vs_train",
                "summary": (
                    f"De novo shortlist keeps novelty {summary_df.loc[summary_df['group']=='de_novo_shortlist', 'novelty_vs_train'].iloc[0]:.2f} "
                    f"with mean predicted permeability {summary_df.loc[summary_df['group']=='de_novo_shortlist', 'mean_predicted_permeability'].iloc[0]:.3f}."
                ),
            },
            {
                "finding": "diversity_compare",
                "summary": (
                    f"Pairwise Jaccard diversity is "
                    f"{summary_df.loc[summary_df['group']=='optimized_shortlist', 'pairwise_jaccard_diversity'].iloc[0]:.3f} for optimized candidates and "
                    f"{summary_df.loc[summary_df['group']=='de_novo_shortlist', 'pairwise_jaccard_diversity'].iloc[0]:.3f} for de novo candidates."
                ),
            },
        ]
    )
    narrative.to_csv(out_dir / "narrative_summary.csv", index=False)

    print("Generation evaluation summary:")
    print(summary_df.to_string(index=False))
    print("---")
    print("Top monomer frequencies:")
    print(freq_df.groupby("group").head(10).to_string(index=False))
    print(f"Saved summary to: {out_dir / 'summary.csv'}")


if __name__ == "__main__":
    main()
