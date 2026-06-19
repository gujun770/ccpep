import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import RESULT_DIR


def bootstrap_diff(a, b, n_boot=4000, seed=42):
    rng = np.random.default_rng(seed)
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    diffs = []
    for _ in range(n_boot):
        sa = rng.choice(a, size=len(a), replace=True)
        sb = rng.choice(b, size=len(b), replace=True)
        diffs.append(sa.mean() - sb.mean())
    diffs = np.asarray(diffs)
    return {
        "mean_diff": float(a.mean() - b.mean()),
        "ci_lower": float(np.quantile(diffs, 0.025)),
        "ci_upper": float(np.quantile(diffs, 0.975)),
    }


def permutation_pvalue(a, b, n_perm=6000, seed=42):
    rng = np.random.default_rng(seed)
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    observed = abs(a.mean() - b.mean())
    combined = np.concatenate([a, b])
    count = 0
    for _ in range(n_perm):
        rng.shuffle(combined)
        perm_a = combined[: len(a)]
        perm_b = combined[len(a):]
        if abs(perm_a.mean() - perm_b.mean()) >= observed:
            count += 1
    return float((count + 1) / (n_perm + 1))


def compare_groups(df, group_a, group_b, metrics, label_col, seed_base=42):
    rows = []
    a_df = df.loc[df[label_col] == group_a].copy()
    b_df = df.loc[df[label_col] == group_b].copy()
    for idx, metric in enumerate(metrics):
        a = a_df[metric].dropna().to_numpy()
        b = b_df[metric].dropna().to_numpy()
        if len(a) == 0 or len(b) == 0:
            continue
        stats = bootstrap_diff(a, b, seed=seed_base + idx)
        rows.append(
            {
                "group_a": group_a,
                "group_b": group_b,
                "metric": metric,
                "group_a_mean": float(a.mean()),
                "group_b_mean": float(b.mean()),
                "mean_diff": stats["mean_diff"],
                "ci_lower": stats["ci_lower"],
                "ci_upper": stats["ci_upper"],
                "permutation_pvalue": permutation_pvalue(a, b, seed=seed_base + 100 + idx),
            }
        )
    return pd.DataFrame(rows)


def main():
    out_dir = RESULT_DIR / "design_statistics"
    out_dir.mkdir(parents=True, exist_ok=True)

    qd_points = pd.read_csv(RESULT_DIR / "quality_diversity_analysis" / "shortlist_qd_points.csv")
    qd_points = qd_points.rename(columns={"route": "group"})
    route_metrics = [
        "quality_score",
        "local_diversity",
        "predicted_permeability",
        "predicted_positive_prob",
        "n_methyl_ratio",
        "natural_ratio",
        "d_ratio",
    ]
    route_stats = compare_groups(
        qd_points,
        "optimized_shortlist",
        "de_novo_shortlist",
        route_metrics,
        label_col="group",
        seed_base=42,
    )
    route_stats.to_csv(out_dir / "route_comparison_stats.csv", index=False)

    ablation_shortlists = pd.read_csv(RESULT_DIR / "generator_ablation" / "shortlists.csv")
    ablation_metrics = [
        "predicted_positive_prob",
        "predicted_permeability",
        "motif_score",
        "composition_alignment",
        "uncertainty_stability",
    ]
    ablation_frames = []
    for variant in ["no_motif", "no_composition", "no_uncertainty", "quality_only"]:
        frame = compare_groups(
            ablation_shortlists,
            "full",
            variant,
            ablation_metrics,
            label_col="variant",
            seed_base=1000 + len(ablation_frames) * 200,
        )
        ablation_frames.append(frame)
    ablation_stats = pd.concat(ablation_frames, ignore_index=True)
    ablation_stats.to_csv(out_dir / "generator_ablation_stats.csv", index=False)

    narrative_rows = []
    for _, row in route_stats.iterrows():
        direction = "higher" if row["mean_diff"] > 0 else "lower"
        narrative_rows.append(
            {
                "comparison": f"{row['group_a']}_vs_{row['group_b']}",
                "metric": row["metric"],
                "summary": (
                    f"{row['group_a']} is {direction} than {row['group_b']} on {row['metric']} "
                    f"(delta={row['mean_diff']:.3f}, 95% CI [{row['ci_lower']:.3f}, {row['ci_upper']:.3f}], "
                    f"p={row['permutation_pvalue']:.4f})."
                ),
            }
        )
    narrative_df = pd.DataFrame(narrative_rows)
    narrative_df.to_csv(out_dir / "narrative_summary.csv", index=False)

    print("Route comparison stats:")
    print(route_stats.to_string(index=False))
    print("---")
    print("Generator ablation stats:")
    print(ablation_stats.to_string(index=False))
    print(f"Saved statistics to: {out_dir}")


if __name__ == "__main__":
    main()
