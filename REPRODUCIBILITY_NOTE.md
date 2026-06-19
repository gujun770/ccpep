# CCPep reproducibility package

This package contains the code, data files, result tables, figures, final manuscript file, and supplementary tables for the cyclic peptide permeability prediction and design workflow.

Main folders:

- `main/`: core preprocessing, benchmarking, candidate generation, analysis, and figure/table scripts.
- `dataset/`: public input data and vocabulary files used by the workflow.
- `Result/`: generated benchmark outputs, candidate lists, analysis tables, and figures.
- `extra_model/`, `HELM/`, `utils/`, `gmx_files/`, `gmx_utils/`: auxiliary model, tokenizer, utility, and molecular simulation helper files.

Revision baseline:

- `main/run_xgboost_baseline.py` runs the added XGBoost descriptor baseline under identical random, held-out-source, and leave-one-source-out protocols.
- `Result/xgboost_baseline/` contains the generated XGBoost metrics, predictions, per-source results, and feature importance table.

The manuscript and supplementary tables are included as Word documents. Generated virtual candidates are computational priorities only and have not been experimentally synthesized or characterized.
