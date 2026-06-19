import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import RESULT_DIR


def read_csv(path):
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def main():
    out_dir = RESULT_DIR / "project_summary"
    out_dir.mkdir(parents=True, exist_ok=True)

    main_comparison = read_csv(RESULT_DIR / "paper_tables" / "main_comparison.csv")
    ablation = read_csv(RESULT_DIR / "paper_tables" / "ablation.csv")
    descriptor_benchmark = read_csv(RESULT_DIR / "paper_tables" / "descriptor_benchmark.csv")
    generation_summary = read_csv(RESULT_DIR / "generation_evaluation" / "summary.csv")
    docking_candidates = read_csv(RESULT_DIR / "docking_candidates" / "top20_docking_candidates.csv")

    highlights = []
    if not main_comparison.empty:
        best_random = main_comparison.loc[main_comparison["setting"] == "random"].sort_values("auroc", ascending=False).head(1)
        if not best_random.empty:
            row = best_random.iloc[0]
            highlights.append({
                "section": "random_split_prediction",
                "finding": f"Best random-split AUROC is {row['auroc']:.3f} from {row['model']}."
            })
    if not descriptor_benchmark.empty:
        row = descriptor_benchmark.sort_values("cls_auroc_mean", ascending=False).iloc[0]
        highlights.append({
            "section": "group_cv_prediction",
            "finding": f"Best repeated group-CV descriptor model is {row['model']} with AUROC {row['cls_auroc_mean']:.3f}."
        })
    if not generation_summary.empty:
        for group in ["optimized_shortlist", "de_novo_shortlist"]:
            sub = generation_summary.loc[generation_summary["group"] == group]
            if not sub.empty:
                row = sub.iloc[0]
                highlights.append({
                    "section": group,
                    "finding": (
                        f"{group} contains {int(row['count'])} candidates with novelty {row['novelty_vs_train']:.2f}, "
                        f"uniqueness {row['uniqueness']:.2f}, and mean predicted permeability {row['mean_predicted_permeability']:.3f}."
                    )
                })
    if not docking_candidates.empty:
        highlights.append({
            "section": "validation_candidates",
            "finding": f"Unified validation set contains {len(docking_candidates)} top candidates from optimized and de novo routes."
        })

    highlight_df = pd.DataFrame(highlights)
    highlight_df.to_csv(out_dir / "highlights.csv", index=False)

    report = {
        "available_tables": {
            "main_comparison": str(RESULT_DIR / "paper_tables" / "main_comparison.csv"),
            "ablation": str(RESULT_DIR / "paper_tables" / "ablation.csv"),
            "descriptor_benchmark": str(RESULT_DIR / "paper_tables" / "descriptor_benchmark.csv"),
            "generation_summary": str(RESULT_DIR / "generation_evaluation" / "summary.csv"),
            "docking_candidates": str(RESULT_DIR / "docking_candidates" / "top20_docking_candidates.csv"),
        },
        "highlights": highlights,
    }
    with open(out_dir / "project_summary.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("Project highlights:")
    print(highlight_df.to_string(index=False))
    print(f"Saved project summary to: {out_dir / 'project_summary.json'}")


if __name__ == "__main__":
    main()
