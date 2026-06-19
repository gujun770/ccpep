# Figure Captions (v0)

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
