import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import RESULT_DIR


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_main_comparison():
    public_metrics = load_json(RESULT_DIR / "public_baseline" / "metrics.json")
    enhanced_metrics = load_json(RESULT_DIR / "enhanced_predictor" / "metrics.json")
    hybrid_metrics = load_json(RESULT_DIR / "hybrid_predictor" / "metrics.json")
    descriptor_metrics = load_json(RESULT_DIR / "descriptor_benchmark" / "summary.json")

    rows = [
        {
            "model": "Public baseline (TF-IDF)",
            "setting": "random",
            "rmse": public_metrics["regression"]["rmse"],
            "mae": public_metrics["regression"]["mae"],
            "r2": public_metrics["regression"]["r2"],
            "accuracy": public_metrics["classification"]["accuracy"],
            "f1": public_metrics["classification"]["f1"],
            "auroc": public_metrics["classification"]["auroc"],
        },
        {
            "model": "Enhanced predictor",
            "setting": "random",
            "rmse": enhanced_metrics["random_split"]["regression"]["rmse"],
            "mae": enhanced_metrics["random_split"]["regression"]["mae"],
            "r2": enhanced_metrics["random_split"]["regression"]["r2"],
            "accuracy": enhanced_metrics["random_split"]["classification"]["accuracy"],
            "f1": enhanced_metrics["random_split"]["classification"]["f1"],
            "auroc": enhanced_metrics["random_split"]["classification"]["auroc"],
        },
        {
            "model": "Enhanced predictor",
            "setting": "source",
            "rmse": enhanced_metrics["source_split"]["regression"]["rmse"],
            "mae": enhanced_metrics["source_split"]["regression"]["mae"],
            "r2": enhanced_metrics["source_split"]["regression"]["r2"],
            "accuracy": enhanced_metrics["source_split"]["classification"]["accuracy"],
            "f1": enhanced_metrics["source_split"]["classification"]["f1"],
            "auroc": enhanced_metrics["source_split"]["classification"]["auroc"],
        },
        {
            "model": "Hybrid predictor",
            "setting": "random",
            "rmse": hybrid_metrics["random_split"]["regression"]["hybrid"]["rmse"],
            "mae": hybrid_metrics["random_split"]["regression"]["hybrid"]["mae"],
            "r2": hybrid_metrics["random_split"]["regression"]["hybrid"]["r2"],
            "accuracy": hybrid_metrics["random_split"]["classification"]["hybrid"]["accuracy"],
            "f1": hybrid_metrics["random_split"]["classification"]["hybrid"]["f1"],
            "auroc": hybrid_metrics["random_split"]["classification"]["hybrid"]["auroc"],
        },
        {
            "model": "Descriptor RF (group CV mean)",
            "setting": "group_cv",
            "rmse": descriptor_metrics["models"]["random_forest"]["regression"]["rmse"]["mean"],
            "mae": descriptor_metrics["models"]["random_forest"]["regression"]["mae"]["mean"],
            "r2": descriptor_metrics["models"]["random_forest"]["regression"]["r2"]["mean"],
            "accuracy": descriptor_metrics["models"]["random_forest"]["classification"]["accuracy"]["mean"],
            "f1": descriptor_metrics["models"]["random_forest"]["classification"]["f1"]["mean"],
            "auroc": descriptor_metrics["models"]["random_forest"]["classification"]["auroc"]["mean"],
        },
    ]
    return pd.DataFrame(rows)


def build_ablation_table():
    ablation = load_json(RESULT_DIR / "group_cv_ablation" / "summary.json")
    rows = []
    for config, metrics in ablation["configs"].items():
        rows.append(
            {
                "config": config,
                "reg_rmse_mean": metrics["regression"]["rmse"]["mean"],
                "reg_r2_mean": metrics["regression"]["r2"]["mean"],
                "cls_acc_mean": metrics["classification"]["accuracy"]["mean"],
                "cls_f1_mean": metrics["classification"]["f1"]["mean"],
                "cls_mcc_mean": metrics["classification"]["mcc"]["mean"],
                "cls_auroc_mean": metrics["classification"]["auroc"]["mean"],
            }
        )
    return pd.DataFrame(rows).sort_values("cls_auroc_mean", ascending=False)


def build_descriptor_benchmark_table():
    benchmark = load_json(RESULT_DIR / "descriptor_benchmark" / "summary.json")
    rows = []
    for model, metrics in benchmark["models"].items():
        rows.append(
            {
                "model": model,
                "reg_rmse_mean": metrics["regression"]["rmse"]["mean"],
                "reg_r2_mean": metrics["regression"]["r2"]["mean"],
                "cls_acc_mean": metrics["classification"]["accuracy"]["mean"],
                "cls_f1_mean": metrics["classification"]["f1"]["mean"],
                "cls_mcc_mean": metrics["classification"]["mcc"]["mean"],
                "cls_auroc_mean": metrics["classification"]["auroc"]["mean"],
            }
        )
    return pd.DataFrame(rows).sort_values("cls_auroc_mean", ascending=False)


def build_loso_table():
    loso = load_json(RESULT_DIR / "loso_random_forest" / "summary.json")
    rows = []
    for subset_name, subset_metrics in [("all_sources", loso["all_sources"]), ("strict_sources_only", loso["strict_sources_only"])]:
        rows.append(
            {
                "subset": subset_name,
                "reg_rmse_weighted": subset_metrics["regression"]["rmse"]["weighted_mean"],
                "reg_r2_weighted": subset_metrics["regression"]["r2"]["weighted_mean"],
                "cls_acc_weighted": subset_metrics["classification"]["accuracy"]["weighted_mean"],
                "cls_bal_acc_weighted": subset_metrics["classification"]["balanced_accuracy"]["weighted_mean"],
                "cls_f1_weighted": subset_metrics["classification"]["f1"]["weighted_mean"],
                "cls_mcc_weighted": subset_metrics["classification"]["mcc"]["weighted_mean"],
                "cls_auroc_weighted": subset_metrics["classification"]["auroc"]["weighted_mean"],
            }
        )
    return pd.DataFrame(rows)


def main():
    out_dir = RESULT_DIR / "paper_tables"
    out_dir.mkdir(parents=True, exist_ok=True)

    tables = {
        "main_comparison.csv": build_main_comparison(),
        "ablation.csv": build_ablation_table(),
        "descriptor_benchmark.csv": build_descriptor_benchmark_table(),
        "loso_summary.csv": build_loso_table(),
    }

    for filename, df in tables.items():
        df.to_csv(out_dir / filename, index=False)
        print(f"Saved {filename} to {out_dir / filename}")
        print(df.head().to_string(index=False))
        print("---")


if __name__ == "__main__":
    main()
