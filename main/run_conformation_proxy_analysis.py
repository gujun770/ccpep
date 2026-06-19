import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import DATASET_DIR, RESULT_DIR


PALETTE = {
    "ink": "#27313A",
    "blue": "#315C72",
    "green": "#8FAF6B",
    "gold": "#D9A441",
    "rust": "#B85C47",
}


PROXY_COLS = [
    "CHCl3_3DPSA",
    "H2O_3DPSA",
    "EPSA",
    "PC1",
    "PC2",
    "_3DPSA",
]

MATCH_COLS = ["MolLogP", "TPSA", "FractionCSP3", "qed"]


def style_ax(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(alpha=0.18, linewidth=0.8)
    ax.tick_params(labelsize=9)


def main():
    peptide_all = pd.read_csv(DATASET_DIR / "CycPeptMPDB_Peptide_All.csv", low_memory=False)
    peptide_all = peptide_all.loc[peptide_all["Monomer_Length_in_Main_Chain"] == 6].copy()
    peptide_all["permeability_rank"] = peptide_all["Permeability"].rank(ascending=False, method="first")
    peptide_all["solvent_3DPSA_gap"] = peptide_all["H2O_3DPSA"] - peptide_all["CHCl3_3DPSA"]

    top_train = peptide_all.sort_values("Permeability", ascending=False).head(100).copy()

    optimized = pd.read_csv(RESULT_DIR / "design_pipeline" / "final_shortlist.csv")
    de_novo = pd.read_csv(RESULT_DIR / "de_novo_generation" / "final_generated_shortlist.csv")

    merged_opt = optimized.merge(
        peptide_all[["HELM", "Permeability"] + PROXY_COLS + ["solvent_3DPSA_gap"]],
        on="HELM",
        how="left",
    )
    merged_denovo = de_novo.merge(
        peptide_all[["HELM", "Permeability"] + PROXY_COLS + ["solvent_3DPSA_gap"]],
        on="HELM",
        how="left",
    )

    summary_rows = []
    for name, df in [
        ("overall_train", peptide_all),
        ("train_top100", top_train),
        ("optimized_shortlist_overlap", merged_opt.loc[merged_opt["Permeability"].notna()]),
        ("de_novo_shortlist_overlap", merged_denovo.loc[merged_denovo["Permeability"].notna()]),
    ]:
        row = {"group": name, "count": int(len(df))}
        for col in PROXY_COLS + ["solvent_3DPSA_gap"]:
            row[f"{col}_mean"] = float(df[col].mean()) if len(df) else None
        summary_rows.append(row)
    summary_df = pd.DataFrame(summary_rows)

    out_dir = RESULT_DIR / "conformation_proxy_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(out_dir / "proxy_summary.csv", index=False)

    available_opt = merged_opt.loc[merged_opt["Permeability"].notna()].copy()
    available_denovo = merged_denovo.loc[merged_denovo["Permeability"].notna()].copy()
    overlap_df = pd.concat(
        [
            available_opt.assign(route="optimized"),
            available_denovo.assign(route="de_novo"),
        ],
        ignore_index=True,
    )
    overlap_df.to_csv(out_dir / "proxy_overlap_candidates.csv", index=False)

    ref_pool = top_train[["HELM"] + MATCH_COLS + PROXY_COLS + ["solvent_3DPSA_gap", "Permeability"]].copy()
    ref_pool = ref_pool.dropna(subset=MATCH_COLS).copy()

    match_mean = ref_pool[MATCH_COLS].mean()
    match_std = ref_pool[MATCH_COLS].std().replace(0, 1.0)
    ref_mat_z = ((ref_pool[MATCH_COLS] - match_mean) / match_std).to_numpy(dtype=float)

    def attach_proxy_neighbors(df, route_name, top_k=5):
        rows = []
        for _, row in df.iterrows():
            cand = np.array(
                [
                    row.get("MolLogP_mean", np.nan),
                    row.get("TPSA_mean", np.nan),
                    row.get("FractionCSP3_mean", np.nan),
                    row.get("qed_mean", np.nan),
                ],
                dtype=float,
            )
            if np.isnan(cand).any():
                continue
            if len(ref_pool) == 0:
                continue
            cand_z = ((cand - match_mean.to_numpy(dtype=float)) / match_std.to_numpy(dtype=float))
            dists = np.sqrt(((ref_mat_z - cand_z) ** 2).sum(axis=1))
            top_idx = np.argsort(dists)[:top_k]
            top_dists = dists[top_idx]
            weights = 1.0 / (top_dists + 1e-6)
            weights = weights / weights.sum()
            neighbor_block = ref_pool.iloc[top_idx]
            rows.append(
                {
                    "route": route_name,
                    "candidate_helm": row["HELM"],
                    "neighbor_helm": "|".join(neighbor_block["HELM"].astype(str).tolist()),
                    "neighbor_distance": float(np.average(top_dists, weights=weights)),
                    "neighbor_permeability": float(np.average(neighbor_block["Permeability"], weights=weights)),
                    "neighbor_CHCl3_3DPSA": float(np.average(neighbor_block["CHCl3_3DPSA"].fillna(neighbor_block["CHCl3_3DPSA"].mean()), weights=weights)),
                    "neighbor_H2O_3DPSA": float(np.average(neighbor_block["H2O_3DPSA"].fillna(neighbor_block["H2O_3DPSA"].mean()), weights=weights)),
                    "neighbor_EPSA": float(np.average(neighbor_block["EPSA"].fillna(neighbor_block["EPSA"].mean()), weights=weights)) if neighbor_block["EPSA"].notna().any() else np.nan,
                    "neighbor_solvent_3DPSA_gap": float(np.average(neighbor_block["solvent_3DPSA_gap"].fillna(neighbor_block["solvent_3DPSA_gap"].mean()), weights=weights)),
                }
            )
        return pd.DataFrame(rows)

    opt_neighbor_df = attach_proxy_neighbors(optimized, "optimized")
    denovo_neighbor_df = attach_proxy_neighbors(de_novo, "de_novo")
    neighbor_df = pd.concat([opt_neighbor_df, denovo_neighbor_df], ignore_index=True)
    neighbor_df.to_csv(out_dir / "proxy_neighbor_matches.csv", index=False)

    narrative = pd.DataFrame(
        [
            {
                "finding": "solvent_gap",
                "summary": (
                    f"Top-100 training peptides show mean solvent 3DPSA gap "
                    f"{top_train['solvent_3DPSA_gap'].mean():.3f}, compared with "
                    f"{peptide_all['solvent_3DPSA_gap'].mean():.3f} for the overall training pool."
                ),
            },
            {
                "finding": "optimized_overlap",
                "summary": (
                    f"Among optimized shortlist peptides found in the public set, mean CHCl3_3DPSA is "
                    f"{available_opt['CHCl3_3DPSA'].mean():.3f} and H2O_3DPSA is {available_opt['H2O_3DPSA'].mean():.3f}."
                ) if len(available_opt) else {"finding": "optimized_overlap", "summary": "No optimized shortlist peptide matched public 3D proxy records."},
            },
            {
                "finding": "denovo_overlap",
                "summary": (
                    f"Among de novo shortlist peptides found in the public set, mean CHCl3_3DPSA is "
                    f"{available_denovo['CHCl3_3DPSA'].mean():.3f} and H2O_3DPSA is {available_denovo['H2O_3DPSA'].mean():.3f}."
                ) if len(available_denovo) else {"finding": "denovo_overlap", "summary": "No de novo shortlist peptide matched public 3D proxy records."},
            },
            {
                "finding": "neighbor_proxy_context",
                "summary": (
                    f"Nearest high-permeability neighbors for optimized candidates show mean solvent 3DPSA gap "
                    f"{opt_neighbor_df['neighbor_solvent_3DPSA_gap'].mean():.3f}, while de novo neighbors show "
                    f"{denovo_neighbor_df['neighbor_solvent_3DPSA_gap'].mean():.3f}."
                ) if len(neighbor_df) else {"finding": "neighbor_proxy_context", "summary": "No nearest-neighbor proxy match could be computed."},
            },
        ]
    )
    narrative.to_csv(out_dir / "narrative_summary.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4))

    box_df = peptide_all[["Permeability", "solvent_3DPSA_gap"]].copy()
    box_df["bucket"] = pd.qcut(box_df["Permeability"], q=4, labels=["Low", "Mid-low", "Mid-high", "High"])
    grouped = [box_df.loc[box_df["bucket"] == label, "solvent_3DPSA_gap"].dropna().to_numpy() for label in ["Low", "Mid-low", "Mid-high", "High"]]
    axes[0].boxplot(grouped, patch_artist=True, boxprops=dict(facecolor=PALETTE["green"], alpha=0.65), medianprops=dict(color=PALETTE["ink"]))
    axes[0].set_xticklabels(["Low", "Mid-low", "Mid-high", "High"])
    axes[0].set_title("Solvent 3DPSA gap across permeability quartiles")
    axes[0].set_ylabel("H2O_3DPSA - CHCl3_3DPSA")
    style_ax(axes[0])

    axes[1].scatter(peptide_all["CHCl3_3DPSA"], peptide_all["H2O_3DPSA"], s=10, alpha=0.12, color=PALETTE["ink"], label="Train")
    axes[1].scatter(top_train["CHCl3_3DPSA"], top_train["H2O_3DPSA"], s=20, alpha=0.45, color=PALETTE["green"], label="Train top-100")
    if len(available_opt):
        axes[1].scatter(available_opt["CHCl3_3DPSA"], available_opt["H2O_3DPSA"], s=60, color=PALETTE["blue"], edgecolor="white", linewidth=0.8, label="Optimized overlap")
    if len(available_denovo):
        axes[1].scatter(available_denovo["CHCl3_3DPSA"], available_denovo["H2O_3DPSA"], s=60, color=PALETTE["gold"], edgecolor="white", linewidth=0.8, label="De novo overlap")
    axes[1].set_xlabel("CHCl3_3DPSA")
    axes[1].set_ylabel("H2O_3DPSA")
    axes[1].set_title("3D polarity proxy landscape")
    axes[1].legend(frameon=False, fontsize=8)
    style_ax(axes[1])

    axes[0].text(-0.14, 1.05, "A", transform=axes[0].transAxes, fontsize=15, weight="bold")
    axes[1].text(-0.14, 1.05, "B", transform=axes[1].transAxes, fontsize=15, weight="bold")
    fig.tight_layout()
    fig.savefig(RESULT_DIR / "paper_figures" / "figure6_conformation_proxy.png", dpi=300)
    plt.close(fig)

    if len(neighbor_df):
        neighbor_summary = (
            neighbor_df.groupby("route")[["neighbor_CHCl3_3DPSA", "neighbor_H2O_3DPSA", "neighbor_EPSA", "neighbor_solvent_3DPSA_gap", "neighbor_distance"]]
            .mean()
            .reset_index()
        )
        neighbor_summary.to_csv(out_dir / "proxy_neighbor_summary.csv", index=False)

    print("Conformation proxy summary:")
    print(summary_df.to_string(index=False))
    if len(neighbor_df):
        print("---")
        print("Nearest high-permeability neighbor proxy summary:")
        print(neighbor_summary.to_string(index=False))
    print(f"Saved conformation proxy analysis to: {out_dir}")


if __name__ == "__main__":
    main()
