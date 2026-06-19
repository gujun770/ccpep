# CCPep source-aware cyclic peptide permeability workflow

This repository contains the reproducibility package for the manuscript:

**Descriptor-Guided Workflow for Cyclic Peptide Permeability Prediction and Molecular Diversity Design**

The project builds a public, source-aware workflow for length-six cyclic peptide permeability prediction and virtual candidate prioritization using CycPeptMPDB-derived data.

## Repository contents

- `dataset/`: public input tables and vocabulary files.
- `main/`: preprocessing, model training, source-aware benchmarking, candidate generation, analysis, and figure/table scripts.
- `Result/`: generated benchmark outputs, candidate shortlists, analysis tables, and manuscript figures.
- `extra_model/`, `HELM/`, `utils/`, `gmx_files/`, `gmx_utils/`: auxiliary model, tokenizer, utility, and molecular simulation helper files.
- `SCI_submission_revised_v15_MolecularDiversity.docx`: manuscript file included in the original submission package.
- `SCI_submission_supplementary_tables.docx`: supplementary tables included in the original submission package.

## Key reproducibility scripts

Examples:

```bash
python main/train_public_baseline.py
python main/train_enhanced_predictor.py
python main/train_hybrid_predictor.py
python main/run_xgboost_baseline.py
python main/run_loso_random_forest.py
python main/optimize_cyclic_peptides.py
python main/generate_de_novo_peptides.py
```

The XGBoost baseline was added during revision to provide an external strong tabular-learning comparator under the same random, held-out-source, and leave-one-source-out protocols.

## Installation

Install the Python dependencies listed in `requirements.txt`. The project was developed and tested with Python 3.11 in the authors' local conda environment.

```bash
pip install -r requirements.txt
```

Some molecular descriptor workflows may require a working RDKit installation from conda-forge depending on the local platform.

## Interpretation note

Generated virtual candidates are computational priorities only. They have not been synthesized, purified, or experimentally characterized. Model scores should be interpreted as candidate-prioritization signals rather than direct predictions of experimental success.
