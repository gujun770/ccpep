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
    out_dir = RESULT_DIR / "manuscript_draft"
    out_dir.mkdir(parents=True, exist_ok=True)

    main_comp = pd.read_csv(RESULT_DIR / "paper_tables" / "main_comparison.csv")
    gen_eval = pd.read_csv(RESULT_DIR / "generation_evaluation" / "summary.csv")
    qd = pd.read_csv(RESULT_DIR / "quality_diversity_analysis" / "summary.csv")
    route_stats = pd.read_csv(RESULT_DIR / "design_statistics" / "route_comparison_stats.csv")
    gen_ablation = pd.read_csv(RESULT_DIR / "generator_ablation" / "summary.csv")
    source_het = pd.read_csv(RESULT_DIR / "source_heterogeneity" / "heterogeneity_summary.csv")
    novelty_depth = pd.read_csv(RESULT_DIR / "candidate_novelty_depth" / "summary.csv")
    ci = load_json(RESULT_DIR / "confidence_intervals" / "hybrid_bootstrap_ci.json")

    best_random = main_comp.loc[main_comp["auroc"].idxmax()]
    optimized = gen_eval.loc[gen_eval["group"] == "optimized_shortlist"].iloc[0]
    denovo = gen_eval.loc[gen_eval["group"] == "de_novo_shortlist"].iloc[0]
    route_quality = route_stats.loc[route_stats["metric"] == "quality_score"].iloc[0]
    route_div = route_stats.loc[route_stats["metric"] == "local_diversity"].iloc[0]
    full_ablation = gen_ablation.loc[gen_ablation["variant"] == "full"].iloc[0]
    hetero_auroc = source_het.loc[source_het["metric"] == "cls_auroc"].iloc[0]
    novelty_opt = novelty_depth.loc[novelty_depth["route"] == "optimized_shortlist"].iloc[0]
    novelty_denovo = novelty_depth.loc[novelty_depth["route"] == "de_novo_shortlist"].iloc[0]

    manuscript = f"""# Descriptor-Guided Design of Membrane-Permeable Cyclic Peptides

## Title candidates
1. Descriptor-guided source-aware design of membrane-permeable cyclic peptides
2. A source-aware framework for prediction and design of membrane-permeable cyclic peptides
3. Robust permeability-guided optimization and de novo generation of cyclic peptides

## Abstract (v0)
Membrane-permeable cyclic peptides are attractive therapeutic scaffolds, but existing AI pipelines often rely on private checkpoints, incomplete simulation features, or optimistic random-split evaluation. Here we present a reproducible descriptor-guided framework for cyclic peptide permeability design built on public CycPeptMPDB data. We first establish source-aware prediction baselines and show that random-split evaluation substantially overestimates performance relative to cross-source settings. A hybrid predictor achieved the best random-split AUROC of {best_random['auroc']:.3f}, while descriptor-driven models yielded the strongest repeated group-CV generalization. Building on this scorer, we developed two complementary design routes: constrained optimization of high-quality seeds and multi-objective de novo generation with motif, composition, novelty, and uncertainty terms. The optimized shortlist produced {int(optimized['count'])} fully novel candidates with mean predicted permeability {optimized['mean_predicted_permeability']:.3f}, whereas the de novo shortlist produced {int(denovo['count'])} fully novel candidates with mean predicted permeability {denovo['mean_predicted_permeability']:.3f}. Statistical comparison showed that the optimized route had significantly higher quality than the de novo route (delta={route_quality['mean_diff']:.3f}, p={route_quality['permutation_pvalue']:.4f}), while the de novo route preserved broader exploratory diversity. Mechanism and proxy analyses further indicated that both routes move candidates toward permeability-favorable physicochemical regions. These results support a reproducible and source-aware computational framework for cyclic peptide permeability design.

## 1. Introduction
- Cyclic peptides occupy a promising space between small molecules and biologics, but membrane permeability remains a core bottleneck.
- Existing AI methods have started to move from pure prediction toward controllable peptide generation, yet public reproducibility and rigorous cross-source evaluation remain limited.
- Random train/test splits are likely to overestimate performance because cyclic peptide datasets are collected from heterogeneous experimental sources.
- A practical design framework should therefore satisfy three properties:
  - robust permeability scoring under source shift,
  - controllable candidate generation or optimization,
  - interpretable candidate selection rather than score-only ranking.
- In this study, we reconstructed a public permeability design workflow from CycPeptMPDB and developed a descriptor-guided two-route design system.

## 2. Methods
### 2.1 Dataset construction
- Public source: CycPeptMPDB.
- Task subset: cyclic peptides with main-chain length 6 and available permeability labels.
- Final working dataset size: 2168 peptides.

### 2.2 Source-aware prediction
- Public baseline: TF-IDF text features with linear models.
- Enhanced predictor: sequence-pattern features plus peptide- and monomer-level descriptors.
- Hybrid predictor: text branch + descriptor branch.
- Robustness evaluation:
  - random split,
  - source split,
  - repeated group CV,
  - leave-one-source-out (LOSO).

### 2.3 Descriptor-guided design
- Route 1: constrained optimization of high-quality seed peptides.
- Route 2: multi-objective de novo generation.
- De novo generator objective included:
  - permeability quality,
  - positive class probability,
  - elite motif prior,
  - composition alignment,
  - uncertainty stability,
  - novelty.

### 2.4 Candidate analysis
- novelty and diversity evaluation,
- quality-diversity comparison,
- mechanism analysis using descriptor shifts,
- polarity/conformation proxy analysis,
- nearest-neighbor novelty depth analysis,
- bootstrap confidence intervals and permutation tests.

## 3. Results
### 3.1 Source-aware prediction is substantially harder than random-split prediction
- The strongest random-split AUROC was {best_random['auroc']:.3f} from the hybrid predictor.
- Bootstrap analysis showed a hybrid random-split AUROC mean of {ci['hybrid_random_split']['classification']['auroc']['mean']:.3f} with 95% CI [{ci['hybrid_random_split']['classification']['auroc']['ci_lower']:.3f}, {ci['hybrid_random_split']['classification']['auroc']['ci_upper']:.3f}].
- Under source split, performance decreased markedly, highlighting cross-source generalization as a central challenge.
- LOSO analysis further showed strong source heterogeneity, with source-level AUROC ranging from {hetero_auroc['min']:.3f} to {hetero_auroc['max']:.3f}.

### 3.2 The optimized and de novo routes occupy different regions of the quality-diversity landscape
- The optimized shortlist contained {int(optimized['count'])} candidates with novelty {optimized['novelty_vs_train']:.2f}, uniqueness {optimized['uniqueness']:.2f}, and mean predicted permeability {optimized['mean_predicted_permeability']:.3f}.
- The de novo shortlist contained {int(denovo['count'])} candidates with novelty {denovo['novelty_vs_train']:.2f}, uniqueness {denovo['uniqueness']:.2f}, and mean predicted permeability {denovo['mean_predicted_permeability']:.3f}.
- Optimized candidates achieved significantly higher quality than de novo candidates (delta={route_quality['mean_diff']:.3f}, 95% CI [{route_quality['ci_lower']:.3f}, {route_quality['ci_upper']:.3f}], p={route_quality['permutation_pvalue']:.4f}).
- The routes also differed strongly in diversity (delta={route_div['mean_diff']:.3f}, p={route_div['permutation_pvalue']:.4f}), supporting an exploitation-versus-exploration interpretation.

### 3.3 Multi-objective generation yields a balanced rather than trivial optimum
- The full generator retained mean motif score {full_ablation['mean_motif_score']:.3f}, mean composition alignment {full_ablation['mean_composition_alignment']:.3f}, and mean uncertainty stability {full_ablation['mean_uncertainty_stability']:.3f}.
- Generator ablation showed that removing motif, composition, or uncertainty terms changes the balance among diversity, stability, and composition fidelity rather than monotonically improving all metrics.
- This indicates that the full generator is not merely a score-maximizing sampler, but a balanced multi-objective design policy.

### 3.4 Designed candidates move toward permeability-favorable physicochemical neighborhoods
- Descriptor-shift analysis indicated that optimized and de novo routes move candidates through different physicochemical directions while preserving high predicted permeability.
- Public 3D polarity proxy analysis further placed designed candidates in neighborhoods of high-permeability training peptides.
- Together, these results provide a physically interpretable explanation for why the framework selects these candidates.

### 3.5 Deep novelty analysis separates template refinement from motif recombination
- Optimized candidates had mean nearest-train token Jaccard {novelty_opt['mean_nearest_train_token_jaccard']:.3f}, indicating close local refinement around known high-permeability templates.
- De novo candidates had lower mean nearest-train token Jaccard {novelty_denovo['mean_nearest_train_token_jaccard']:.3f} and larger mean nearest descriptor distance {novelty_denovo['mean_nearest_descriptor_distance']:.3f}.
- This supports the interpretation that the de novo route recombines high-permeability motifs instead of simply duplicating training peptides.

## 4. Discussion
- The framework demonstrates that source-aware evaluation materially changes the conclusions drawn from cyclic peptide permeability modeling.
- Descriptor-guided modeling is currently more robust across heterogeneous sources than purely text-based sequence modeling.
- The optimized and de novo routes should not be interpreted as competing methods alone; they provide complementary exploitation and exploration behaviors.
- The study remains computational and proxy-based, so future work should incorporate external wet-lab validation or richer 3D/MD information where available.

## 5. Conclusion
- We established a reproducible public framework for cyclic peptide permeability prediction and design.
- We showed that cross-source robustness is a central challenge.
- We proposed a two-route design system that produces fully novel optimized and de novo candidate sets.
- We supported the framework with uncertainty analysis, mechanism analysis, polarity proxy validation, and novelty-depth analysis.

## Main figures
- Figure 1: workflow
- Figure 2: prediction results
- Figure 3: generation summary
- Figure 4: candidate landscape
- Figure 5: case analysis
- Figure 6: conformation proxy
- Figure 7: confidence intervals
- Figure 8: quality-diversity
- Figure 9: generator ablation
- Figure 10: statistical summary
- Figure 11: source heterogeneity
- Figure 12: novelty depth

## Current risks before a strong submission
- The framework is now methodologically much stronger than the initial prototype, but it is still entirely computational.
- The main remaining risk for a stronger SCI submission is the lack of external biological validation.
- Another risk is that the generator is descriptor-guided rather than a richer end-to-end deep generative model, so framing and ablation quality remain important.
"""

    captions = """# Figure Captions (v0)

## Figure 1
Overview of the public descriptor-guided cyclic peptide permeability design framework. CycPeptMPDB data are used to train source-aware permeability scorers, which then drive two complementary design routes: constrained optimization and de novo generation. Final candidates are selected with novelty, diversity, and uncertainty-aware filtering.

## Figure 2
Prediction performance across baseline and improved models. The left panel summarizes AUROC changes across the main prediction settings, while the right panel compares descriptor-only model families under repeated group cross-validation.

## Figure 3
Generation outcome summary. The profile map contrasts train, optimized, and de novo candidate sets across novelty, diversity, composition, and confidence metrics. Additional panels summarize de novo motif frequencies and the relative contribution of optimized and de novo routes to the final validation set.

## Figure 4
Candidate landscape for optimized and de novo routes. The left panel maps shortlisted candidates by predicted permeability and probability with uncertainty-aware marker size, while the right panel summarizes route-wise robust-score distributions.

## Figure 5
Representative case analysis of optimized and de novo candidates. The figure highlights route-specific candidate examples and their descriptor shifts relative to nearby high-permeability references.

## Figure 6
Conformation and polarity proxy analysis based on public descriptors. Designed candidates are compared with permeability-stratified reference peptides using solvent-exposed polarity proxies.

## Figure 7
Bootstrap confidence intervals for the hybrid predictor and descriptor models. The figure quantifies uncertainty under random and source-aware evaluation settings.

## Figure 8
Quality-diversity tradeoff analysis. Optimized candidates occupy a high-quality exploitation regime, while de novo candidates provide broader exploratory diversity.

## Figure 9
Generator ablation analysis. The full multi-objective generator is compared with reduced variants lacking motif, composition, or uncertainty terms, showing tradeoffs among quality, diversity, stability, and composition alignment.

## Figure 10
Statistical summary of route comparison and generator ablation. Route-level mean differences and significance values are shown together with generator-ablation effect summaries.

## Figure 11
Source heterogeneity under leave-one-source-out evaluation. Source-level AUROC, sample size, and metric dispersion reveal substantial cross-source variability.

## Figure 12
Deep novelty analysis against the training set. Token-space and descriptor-space nearest-neighbor comparisons distinguish template-refinement behavior from broader motif recombination.
"""

    outline = """# Writing Plan

## Main text order
1. Introduction
2. Methods
3. Results
4. Discussion
5. Conclusion

## Results order
1. Prediction and source-aware generalization
2. Two-route design performance
3. Generator ablation
4. Mechanism and proxy analysis
5. Novelty-depth analysis

## Supplementary material
- Additional prediction tables
- Additional LOSO per-source metrics
- Full candidate lists
- Full ablation shortlist tables
- Full nearest-neighbor novelty tables
"""

    (out_dir / "manuscript_v0.md").write_text(manuscript, encoding="utf-8")
    (out_dir / "figure_captions_v0.md").write_text(captions, encoding="utf-8")
    (out_dir / "writing_plan_v0.md").write_text(outline, encoding="utf-8")

    print(f"Saved manuscript draft materials to: {out_dir}")
    for path in sorted(out_dir.glob("*.md")):
        print(path)


if __name__ == "__main__":
    main()
