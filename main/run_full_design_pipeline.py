import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


STEPS = [
    "prepare_cycpeptmpdb.py",
    "train_public_baseline.py",
    "train_enhanced_predictor.py",
    "train_hybrid_predictor.py",
    "run_group_cv_ablation.py",
    "run_descriptor_model_benchmark.py",
    "run_loso_random_forest.py",
    "export_paper_tables.py",
    "optimize_cyclic_peptides.py",
    "analyze_design_results.py",
    "rerank_candidates_with_uncertainty.py",
    "build_final_shortlist.py",
    "generate_de_novo_peptides.py",
    "postprocess_de_novo_candidates.py",
    "build_docking_candidate_set.py",
    "evaluate_generation_results.py",
    "run_mechanism_analysis.py",
    "build_case_analysis.py",
    "plot_case_analysis.py",
    "run_conformation_proxy_analysis.py",
    "compute_metric_confidence_intervals.py",
    "plot_confidence_intervals.py",
    "analyze_quality_diversity.py",
    "run_generator_ablation.py",
    "plot_generator_ablation.py",
    "compute_design_statistics.py",
    "plot_final_summary_figure.py",
    "analyze_source_heterogeneity.py",
    "plot_source_heterogeneity.py",
    "analyze_candidate_novelty_depth.py",
    "plot_candidate_novelty_depth.py",
    "plot_paper_figures.py",
    "export_project_summary.py",
    "export_final_experiment_tables.py",
]


def run_step(script_name: str):
    script_path = PROJECT_ROOT / "main" / script_name
    print(f"\n=== Running {script_name} ===")
    result = subprocess.run(
        [PYTHON, str(script_path)],
        cwd=str(PROJECT_ROOT),
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"Step failed: {script_name} (exit code {result.returncode})")


def main():
    for step in STEPS:
        run_step(step)
    print("\nPipeline completed successfully.")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Final shortlist: {PROJECT_ROOT / 'Result' / 'design_pipeline' / 'final_shortlist.csv'}")


if __name__ == "__main__":
    main()
