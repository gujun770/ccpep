# Descriptor-Guided Design of Membrane-Permeable Cyclic Peptides

## Title candidates
1. Descriptor-guided source-aware design of membrane-permeable cyclic peptides
2. A source-aware framework for prediction and design of membrane-permeable cyclic peptides
3. Robust permeability-guided optimization and de novo generation of cyclic peptides

## Abstract (v0)
Membrane-permeable cyclic peptides are attractive therapeutic scaffolds, but existing AI pipelines often rely on private checkpoints, incomplete simulation features, or optimistic random-split evaluation. Here we present a reproducible descriptor-guided framework for cyclic peptide permeability design built on public CycPeptMPDB data. We first establish source-aware prediction baselines and show that random-split evaluation substantially overestimates performance relative to cross-source settings. A hybrid predictor achieved the best random-split AUROC of 0.846, while descriptor-driven models yielded the strongest repeated group-CV generalization. Building on this scorer, we developed two complementary design routes: constrained optimization of high-quality seeds and multi-objective de novo generation with motif, composition, novelty, and uncertainty terms. The optimized shortlist produced 12 fully novel candidates with mean predicted permeability -4.511, whereas the de novo shortlist produced 24 fully novel candidates with mean predicted permeability -4.725. Statistical comparison showed that the optimized route had significantly higher quality than the de novo route (delta=0.294, p=0.0002), while the de novo route preserved broader exploratory diversity. Mechanism and proxy analyses further indicated that both routes move candidates toward permeability-favorable physicochemical regions. These results support a reproducible and source-aware computational framework for cyclic peptide permeability design.

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
- The strongest random-split AUROC was 0.846 from the hybrid predictor.
- Bootstrap analysis showed a hybrid random-split AUROC mean of 0.845 with 95% CI [0.805, 0.885].
- Under source split, performance decreased markedly, highlighting cross-source generalization as a central challenge.
- LOSO analysis further showed strong source heterogeneity, with source-level AUROC ranging from 0.167 to 1.000.

### 3.2 The optimized and de novo routes occupy different regions of the quality-diversity landscape
- The optimized shortlist contained 12 candidates with novelty 1.00, uniqueness 1.00, and mean predicted permeability -4.511.
- The de novo shortlist contained 24 candidates with novelty 1.00, uniqueness 1.00, and mean predicted permeability -4.725.
- Optimized candidates achieved significantly higher quality than de novo candidates (delta=0.294, 95% CI [0.282, 0.307], p=0.0002).
- The routes also differed strongly in diversity (delta=0.295, p=0.0002), supporting an exploitation-versus-exploration interpretation.

### 3.3 Multi-objective generation yields a balanced rather than trivial optimum
- The full generator retained mean motif score 0.162, mean composition alignment 0.642, and mean uncertainty stability 0.767.
- Generator ablation showed that removing motif, composition, or uncertainty terms changes the balance among diversity, stability, and composition fidelity rather than monotonically improving all metrics.
- This indicates that the full generator is not merely a score-maximizing sampler, but a balanced multi-objective design policy.

### 3.4 Designed candidates move toward permeability-favorable physicochemical neighborhoods
- Descriptor-shift analysis indicated that optimized and de novo routes move candidates through different physicochemical directions while preserving high predicted permeability.
- Public 3D polarity proxy analysis further placed designed candidates in neighborhoods of high-permeability training peptides.
- Together, these results provide a physically interpretable explanation for why the framework selects these candidates.

### 3.5 Deep novelty analysis separates template refinement from motif recombination
- Optimized candidates had mean nearest-train token Jaccard 0.928, indicating close local refinement around known high-permeability templates.
- De novo candidates had lower mean nearest-train token Jaccard 0.774 and larger mean nearest descriptor distance 0.689.
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
