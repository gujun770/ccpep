import argparse
from pathlib import Path
import pandas as pd

from utils.project_paths import DATASET_DIR


def clean_permeability(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype(str)
        .str.strip()
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    )
    return pd.to_numeric(cleaned, errors="coerce")


def build_pretrain_dataset(peptide_df: pd.DataFrame) -> pd.DataFrame:
    pretrain_df = (
        peptide_df.loc[peptide_df["HELM"].notna(), ["HELM"]]
        .drop_duplicates(subset=["HELM"])
        .reset_index(drop=True)
    )
    return pretrain_df


def build_length_dataset(peptide_df: pd.DataFrame, target_length: int) -> pd.DataFrame:
    filtered = peptide_df.copy()
    filtered["Permeability"] = clean_permeability(filtered["Permeability"])
    filtered["Monomer_Length_in_Main_Chain"] = pd.to_numeric(
        filtered["Monomer_Length_in_Main_Chain"], errors="coerce"
    )

    length_df = (
        filtered.loc[
            filtered["HELM"].notna()
            & filtered["Permeability"].notna()
            & (filtered["Monomer_Length_in_Main_Chain"] == target_length),
            ["HELM", "Permeability", "Monomer_Length_in_Main_Chain", "Source", "Year"],
        ]
        .drop_duplicates(subset=["HELM"])
        .sort_values(by="Permeability", ascending=True)
        .reset_index(drop=True)
    )
    return length_df


def main():
    parser = argparse.ArgumentParser(description="Prepare CCPep-compatible datasets from CycPeptMPDB.")
    parser.add_argument(
        "--peptide-csv",
        default=str(DATASET_DIR / "CycPeptMPDB_Peptide_All.csv"),
        help="Path to CycPeptMPDB peptide CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DATASET_DIR),
        help="Directory for generated CSV files.",
    )
    parser.add_argument(
        "--target-length",
        type=int,
        default=6,
        help="Main-chain monomer length used for the labeled subset.",
    )
    args = parser.parse_args()

    peptide_csv = Path(args.peptide_csv)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    peptide_df = pd.read_csv(peptide_csv)

    pretrain_df = build_pretrain_dataset(peptide_df)
    length_df = build_length_dataset(peptide_df, target_length=args.target_length)

    pretrain_path = output_dir / "pretrain.csv"
    length_path = output_dir / f"CycPeptMPDB_Peptide_Length_{args.target_length}.csv"

    pretrain_df.to_csv(pretrain_path, index=False)
    length_df.to_csv(length_path, index=False)

    print(f"Saved pretrain dataset to: {pretrain_path}")
    print(f"Rows: {len(pretrain_df)}")
    print(f"Saved labeled length-{args.target_length} dataset to: {length_path}")
    print(f"Rows: {len(length_df)}")


if __name__ == "__main__":
    main()
