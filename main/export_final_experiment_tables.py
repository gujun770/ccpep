import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import RESULT_DIR


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main():
    out_dir = RESULT_DIR / "final_experiment_tables"
    out_dir.mkdir(parents=True, exist_ok=True)

    main_comp = pd.read_csv(RESULT_DIR / "paper_tables" / "main_comparison.csv")
    gen_eval = pd.read_csv(RESULT_DIR / "generation_evaluation" / "summary.csv")
    mech_summary = pd.read_csv(RESULT_DIR / "mechanism_analysis" / "descriptor_shift_summary.csv")
    proxy_summary = pd.read_csv(RESULT_DIR / "conformation_proxy_analysis" / "proxy_neighbor_summary.csv")
    qd_summary = pd.read_csv(RESULT_DIR / "quality_diversity_analysis" / "summary.csv")
    gen_ablation = pd.read_csv(RESULT_DIR / "generator_ablation" / "summary.csv")
    source_heterogeneity = pd.read_csv(RESULT_DIR / "source_heterogeneity" / "heterogeneity_summary.csv")
    source_corr = pd.read_csv(RESULT_DIR / "source_heterogeneity" / "correlation_summary.csv")
    novelty_depth = pd.read_csv(RESULT_DIR / "candidate_novelty_depth" / "summary.csv")
    ci_json = load_json(RESULT_DIR / "confidence_intervals" / "hybrid_bootstrap_ci.json")

    main_table = main_comp.copy()
    main_table.to_csv(out_dir / "table1_prediction_and_baselines.csv", index=False)

    generation_table = gen_eval.copy()
    generation_table.to_csv(out_dir / "table2_generation_summary.csv", index=False)

    qd_table = qd_summary.copy()
    qd_table.to_csv(out_dir / "table3_quality_diversity.csv", index=False)

    gen_ablation_table = gen_ablation.copy()
    gen_ablation_table.to_csv(out_dir / "table4_generator_ablation.csv", index=False)

    mechanism_table = mech_summary.copy()
    mechanism_table.to_csv(out_dir / "table5_descriptor_shift_summary.csv", index=False)

    proxy_table = proxy_summary.copy()
    proxy_table.to_csv(out_dir / "table6_conformation_proxy_neighbors.csv", index=False)

    source_heterogeneity.to_csv(out_dir / "table6b_source_heterogeneity.csv", index=False)
    source_corr.to_csv(out_dir / "table6c_source_correlations.csv", index=False)
    novelty_depth.to_csv(out_dir / "table6d_novelty_depth.csv", index=False)

    ci_table = pd.DataFrame(
        [
            {
                "setting": "hybrid_random",
                "metric": "auroc",
                "mean": ci_json["hybrid_random_split"]["classification"]["auroc"]["mean"],
                "ci_low": ci_json["hybrid_random_split"]["classification"]["auroc"]["ci_lower"],
                "ci_high": ci_json["hybrid_random_split"]["classification"]["auroc"]["ci_upper"],
            },
            {
                "setting": "hybrid_random",
                "metric": "r2",
                "mean": ci_json["hybrid_random_split"]["regression"]["r2"]["mean"],
                "ci_low": ci_json["hybrid_random_split"]["regression"]["r2"]["ci_lower"],
                "ci_high": ci_json["hybrid_random_split"]["regression"]["r2"]["ci_upper"],
            },
            {
                "setting": "hybrid_source",
                "metric": "auroc",
                "mean": ci_json["hybrid_source_split"]["classification"]["auroc"]["mean"],
                "ci_low": ci_json["hybrid_source_split"]["classification"]["auroc"]["ci_lower"],
                "ci_high": ci_json["hybrid_source_split"]["classification"]["auroc"]["ci_upper"],
            },
            {
                "setting": "hybrid_source",
                "metric": "r2",
                "mean": ci_json["hybrid_source_split"]["regression"]["r2"]["mean"],
                "ci_low": ci_json["hybrid_source_split"]["regression"]["r2"]["ci_lower"],
                "ci_high": ci_json["hybrid_source_split"]["regression"]["r2"]["ci_upper"],
            },
        ]
    )
    ci_table.to_csv(out_dir / "table7_confidence_intervals.csv", index=False)

    highlights = pd.DataFrame(
        [
            {
                "section": "prediction",
                "finding": "Hybrid predictor reaches the strongest random-split classification AUROC and retains measurable source-aware performance under harder generalization.",
            },
            {
                "section": "generation",
                "finding": "Both optimized and de novo shortlists are fully novel relative to training peptides, while the de novo route reaches diversity close to the top training reference set.",
            },
            {
                "section": "generator_ablation",
                "finding": "Multi-objective generator ablations reveal clear quality-diversity-composition tradeoffs rather than a trivial one-metric optimum.",
            },
            {
                "section": "mechanism",
                "finding": "Optimized and de novo routes shift descriptor profiles differently, with both moving toward permeability-favorable physicochemical regions.",
            },
            {
                "section": "proxy_validation",
                "finding": "Candidates map to neighborhoods of high-permeability peptides under public 3D polarity proxy descriptors, supporting physical plausibility without requiring private MD trajectories.",
            },
            {
                "section": "source_heterogeneity",
                "finding": "Leave-one-source-out analysis reveals substantial source-level heterogeneity, and this variability is only weakly related to source sample size.",
            },
            {
                "section": "novelty_depth",
                "finding": "Deep novelty analysis shows that optimized candidates remain close to known high-permeability templates, whereas de novo candidates move farther in token and descriptor space while staying within permeability-favorable neighborhoods.",
            },
        ]
    )
    highlights.to_csv(out_dir / "table8_study_highlights.csv", index=False)

    print(f"Saved final experiment tables to: {out_dir}")
    for path in sorted(out_dir.glob("*.csv")):
        print(path)


if __name__ == "__main__":
    main()
