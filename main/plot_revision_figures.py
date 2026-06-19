import ast
import math
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main.plot_case_study_panels import safe_import_rdkit, smiles_to_image
from main.train_enhanced_predictor import parse_helm_monomers
from utils.project_paths import DATASET_DIR, RESULT_DIR


COLORS = {
    "ink": "#263238",
    "muted": "#607D8B",
    "grid": "#D8DEE2",
    "data": "#4E79A7",
    "predict": "#59A14F",
    "design": "#F28E2B",
    "screen": "#E15759",
    "purple": "#7B6D8D",
    "gold": "#EDC948",
    "cyan": "#76B7B2",
    "light": "#F7F9FB",
    "train": "#B0B7C3",
    "top": "#D64E4E",
    "opt": "#1F77B4",
    "denovo": "#F28E2B",
}


def out_dir() -> Path:
    path = RESULT_DIR / "paper_figures"
    path.mkdir(parents=True, exist_ok=True)
    return path


def style(ax, grid_axis="y"):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis=grid_axis, color=COLORS["grid"], linewidth=0.8, alpha=0.7)
    ax.tick_params(labelsize=9, colors=COLORS["ink"])


def add_panel_label(ax, label):
    ax.text(-0.10, 1.06, label, transform=ax.transAxes, fontsize=14, fontweight="bold", color=COLORS["ink"])


def fig1_workflow():
    fig, ax = plt.subplots(figsize=(12.6, 5.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    stages = [
        ("DATA", "Public CycPeptMPDB\nLength-6 cyclic peptides", COLORS["data"], "D"),
        ("PREDICT", "Multi-level descriptors\nSource-aware scorer", COLORS["predict"], "P"),
        ("DESIGN", "Constrained optimization\nMulti-objective de novo", COLORS["design"], "G"),
        ("FILTER", "Novelty, diversity\nUncertainty control", COLORS["screen"], "S"),
    ]
    xs = [0.13, 0.38, 0.63, 0.87]
    for i, ((title, text, color, icon), x) in enumerate(zip(stages, xs)):
        ax.add_patch(plt.Rectangle((x - 0.105, 0.42), 0.21, 0.30, facecolor="white", edgecolor=color, lw=2.0))
        ax.add_patch(plt.Circle((x - 0.075, 0.66), 0.035, facecolor=color, edgecolor="none"))
        ax.text(x - 0.075, 0.66, icon, ha="center", va="center", fontsize=12, color="white", fontweight="bold")
        ax.text(x, 0.61, title, ha="center", va="center", fontsize=12, fontweight="bold", color=color)
        ax.text(x, 0.51, text, ha="center", va="center", fontsize=9.5, color=COLORS["ink"], linespacing=1.35)
        if i < len(xs) - 1:
            ax.annotate("", xy=(xs[i + 1] - 0.125, 0.57), xytext=(x + 0.125, 0.57),
                        arrowprops=dict(arrowstyle="->", lw=2.1, color=COLORS["muted"]))

    ax.add_patch(plt.Rectangle((0.18, 0.18), 0.64, 0.12, facecolor=COLORS["light"], edgecolor=COLORS["grid"], lw=1.2))
    ax.text(0.50, 0.24, "Outputs: robust prediction evidence + optimized shortlist + de novo shortlist + interpretable case studies",
            ha="center", va="center", fontsize=10.5, color=COLORS["ink"])
    ax.text(0.02, 0.94, "Figure 1. Descriptor-guided permeability design framework", fontsize=14, fontweight="bold", color=COLORS["ink"])
    fig.savefig(out_dir() / "figure1_workflow.png", dpi=350, bbox_inches="tight")
    plt.close(fig)


def fig2_prediction():
    main = pd.read_csv(RESULT_DIR / "paper_tables" / "main_comparison.csv")
    bench = pd.read_csv(RESULT_DIR / "paper_tables" / "descriptor_benchmark.csv")

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.3), gridspec_kw={"width_ratios": [1.2, 1.1, 1.1]})

    random_rows = main.loc[main["setting"].isin(["random", "group_cv"])].copy()
    random_rows["label"] = random_rows["model"].replace({
        "Public baseline (TF-IDF)": "TF-IDF",
        "Enhanced predictor": "Enhanced",
        "Hybrid predictor": "Hybrid",
        "Descriptor RF (group CV mean)": "RF group-CV",
    })
    bars = axes[0].bar(random_rows["label"], random_rows["auroc"], color=["#D5DEE7", "#9DBAD5", "#4E79A7", "#2F5D7C"], edgecolor="white")
    axes[0].set_ylim(0.65, 0.88)
    axes[0].set_ylabel("AUROC")
    axes[0].set_title("Random / group-level performance")
    axes[0].tick_params(axis="x", rotation=18)
    for bar in bars:
        axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.006, f"{bar.get_height():.3f}", ha="center", fontsize=8)
    style(axes[0])

    source_rows = main.loc[main["model"].eq("Enhanced predictor") & main["setting"].isin(["random", "source"])].copy()
    source_rows = pd.concat([
        source_rows,
        pd.DataFrame([{"model": "Hybrid predictor", "setting": "random", "auroc": main.loc[main["model"].eq("Hybrid predictor"), "auroc"].iloc[0]}])
    ], ignore_index=True)
    labels = ["Enhanced\nrandom", "Enhanced\nsource", "Hybrid\nrandom"]
    vals = [source_rows.iloc[0]["auroc"], source_rows.iloc[1]["auroc"], source_rows.iloc[2]["auroc"]]
    bars = axes[1].bar(labels, vals, color=["#9DBAD5", "#E6A35A", "#4E79A7"], edgecolor="white")
    axes[1].set_ylim(0.58, 0.88)
    axes[1].set_title("Split sensitivity")
    axes[1].set_ylabel("AUROC")
    for bar in bars:
        axes[1].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.008, f"{bar.get_height():.3f}", ha="center", fontsize=8)
    style(axes[1])

    bench = bench.sort_values("cls_auroc_mean")
    grad = plt.cm.Blues(np.linspace(0.45, 0.85, len(bench)))
    axes[2].barh(bench["model"], bench["cls_auroc_mean"], color=grad, edgecolor="white")
    axes[2].set_xlim(0.62, 0.75)
    axes[2].set_xlabel("Mean AUROC")
    axes[2].set_title("Descriptor model benchmark")
    for y, v in enumerate(bench["cls_auroc_mean"]):
        axes[2].text(v + 0.003, y, f"{v:.3f}", va="center", fontsize=8)
    style(axes[2], "x")

    for ax, lab in zip(axes, "ABC"):
        add_panel_label(ax, lab)
    fig.tight_layout()
    fig.savefig(out_dir() / "figure2_prediction.png", dpi=350, bbox_inches="tight")
    plt.close(fig)


def fig3_source_heterogeneity():
    per = pd.read_csv(RESULT_DIR / "source_heterogeneity" / "per_source_metrics.csv")
    per = per.loc[per["is_valid_for_strict_summary"].astype(bool)].copy()
    per = per.sort_values("cls_auroc")
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), gridspec_kw={"width_ratios": [1.55, 1.0]})

    colors = ["#D6604D" if v < 0.6 else "#4E79A7" if v < 0.8 else "#59A14F" for v in per["cls_auroc"]]
    axes[0].barh(per["source"], per["cls_auroc"], color=colors, edgecolor="white")
    axes[0].axvline(0.5, color=COLORS["muted"], ls="--", lw=1.1, label="random")
    axes[0].axvline(per["cls_auroc"].mean(), color=COLORS["ink"], lw=1.5, label=f"mean={per['cls_auroc'].mean():.3f}")
    axes[0].set_xlabel("LOSO AUROC")
    axes[0].set_title("Per-source generalization")
    axes[0].legend(frameon=False, fontsize=8, loc="lower right")
    style(axes[0], "x")

    sizes = 28 + np.sqrt(per["test_samples"]) * 5
    sc = axes[1].scatter(per["log_test_samples"], per["cls_auroc"], s=sizes, c=per["permeability_std"], cmap="viridis",
                         edgecolor="white", linewidth=0.8, alpha=0.92)
    axes[1].set_xlabel("log10(test samples)")
    axes[1].set_ylabel("LOSO AUROC")
    axes[1].set_title("Source size and label variability")
    axes[1].axhline(0.5, color=COLORS["muted"], ls="--", lw=1.0)
    cbar = fig.colorbar(sc, ax=axes[1], fraction=0.05, pad=0.03)
    cbar.set_label("Permeability std.", fontsize=8)
    axes[1].text(0.02, 0.04, "Bubble size: test samples", transform=axes[1].transAxes, fontsize=8, color=COLORS["ink"])
    style(axes[1])

    for ax, lab in zip(axes, "AB"):
        add_panel_label(ax, lab)
    fig.tight_layout()
    fig.savefig(out_dir() / "figure11_source_heterogeneity.png", dpi=350, bbox_inches="tight")
    plt.close(fig)


def fig4_generation():
    summary = pd.read_csv(RESULT_DIR / "generation_evaluation" / "summary.csv")
    freq = pd.read_csv(RESULT_DIR / "generation_evaluation" / "monomer_frequency.csv")
    route_counts = pd.read_csv(RESULT_DIR / "docking_candidates" / "candidate_type_summary.csv")
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.2), gridspec_kw={"width_ratios": [1.35, 1.0, 0.85]})

    metrics = ["novelty_vs_train", "pairwise_jaccard_diversity", "mean_natural_ratio", "mean_n_methyl_ratio", "mean_predicted_positive_prob"]
    groups = ["train_top100", "optimized_shortlist", "de_novo_shortlist"]
    labels = ["Train top-100", "Optimized", "De novo"]
    heat = summary.set_index("group").loc[groups, metrics].fillna(0).values
    im = axes[0].imshow(heat, cmap="YlGnBu", vmin=0, vmax=1, aspect="auto")
    axes[0].set_yticks(range(len(groups)), labels)
    axes[0].set_xticks(range(len(metrics)), ["Novelty", "Diversity", "Natural", "N-methyl", "Prob."], rotation=20, ha="right")
    axes[0].set_title("Generation profile")
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            axes[0].text(j, i, f"{heat[i,j]:.2f}", ha="center", va="center", fontsize=9, color="white" if heat[i,j] > 0.58 else COLORS["ink"])
    fig.colorbar(im, ax=axes[0], fraction=0.045, pad=0.03)
    axes[0].spines[:].set_visible(False)

    de_freq = freq.loc[freq["group"].eq("de_novo_shortlist")].head(8).sort_values("count")
    axes[1].barh(de_freq["monomer"], de_freq["count"], color=COLORS["denovo"], edgecolor="white")
    axes[1].set_xlabel("Count")
    axes[1].set_title("De novo monomer motif")
    style(axes[1], "x")

    route_counts["label"] = route_counts["candidate_type"].replace({"optimized": "Optimized", "de_novo": "De novo"})
    axes[2].bar(route_counts["label"], route_counts["count"], color=[COLORS["opt"], COLORS["denovo"]], edgecolor="white")
    axes[2].set_ylabel("Candidates")
    axes[2].set_title("Validation set")
    for idx, row in route_counts.iterrows():
        axes[2].text(idx, row["count"] + 0.4, str(row["count"]), ha="center", fontsize=9)
    style(axes[2])

    for ax, lab in zip(axes, "ABC"):
        add_panel_label(ax, lab)
    fig.tight_layout()
    fig.savefig(out_dir() / "figure3_generation.png", dpi=350, bbox_inches="tight")
    plt.close(fig)


def fig5_quality_diversity():
    pts = pd.read_csv(RESULT_DIR / "quality_diversity_analysis" / "shortlist_qd_points.csv")
    summary = pd.read_csv(RESULT_DIR / "quality_diversity_analysis" / "summary.csv")
    if "diversity" not in pts.columns:
        pts["diversity"] = pts["local_diversity"]
    if "quality" not in pts.columns:
        pts["quality"] = pts["quality_score"]
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.8), gridspec_kw={"width_ratios": [1.35, 1]})
    ax = axes[0]
    color_map = {"optimized_pool": "#C8D9EA", "optimized_shortlist": COLORS["opt"], "de_novo_pool": "#F8D7A6", "de_novo_shortlist": COLORS["denovo"]}
    size_map = {"optimized_pool": 28, "optimized_shortlist": 95, "de_novo_pool": 28, "de_novo_shortlist": 95}
    for route, sub in pts.groupby("route"):
        ax.scatter(sub["diversity"], sub["quality"], s=size_map.get(route, 40), color=color_map.get(route, COLORS["muted"]),
                   edgecolor="black" if "shortlist" in route else "white", linewidth=0.9 if "shortlist" in route else 0.3,
                   alpha=0.92, label=route.replace("_", " "))
    ax.set_xlabel("Local diversity")
    ax.set_ylabel("Quality score")
    ax.set_title("Quality-diversity landscape")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    style(ax)

    small = summary.loc[summary["route"].isin(["optimized_shortlist", "de_novo_shortlist"])].copy()
    x = np.arange(len(small))
    width = 0.36
    axes[1].bar(x - width/2, small["quality_mean"], width, label="Quality", color=COLORS["opt"], edgecolor="white")
    axes[1].bar(x + width/2, small["diversity_mean"], width, label="Diversity", color=COLORS["denovo"], edgecolor="white")
    axes[1].set_xticks(x, small["route"].str.replace("_shortlist", "").str.replace("_", "\n"))
    axes[1].set_ylim(0, 1.08)
    axes[1].set_title("Route-level trade-off")
    axes[1].legend(frameon=False, fontsize=8)
    style(axes[1])
    for ax_i, lab in zip(axes, "AB"):
        add_panel_label(ax_i, lab)
    fig.tight_layout()
    fig.savefig(out_dir() / "figure8_quality_diversity.png", dpi=350, bbox_inches="tight")
    plt.close(fig)


def fig6_generator_ablation():
    df = pd.read_csv(RESULT_DIR / "generator_ablation" / "summary.csv")
    metric_cols = ["mean_perm_quality", "mean_motif_score", "mean_composition_alignment", "mean_uncertainty_stability", "pairwise_jaccard_diversity"]
    labels = ["Quality", "Motif", "Composition", "Stability", "Diversity"]
    df["balance"] = df[metric_cols].mean(axis=1)
    df = df.sort_values("balance", ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(12.8, 4.7), gridspec_kw={"width_ratios": [1.25, 1]})
    heat = df[metric_cols].values
    im = axes[0].imshow(heat, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    axes[0].set_yticks(range(len(df)), df["variant"].str.replace("_", " ").str.title())
    axes[0].set_xticks(range(len(labels)), labels, rotation=20, ha="right")
    axes[0].set_title("Generator objective ablation")
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            axes[0].text(j, i, f"{heat[i,j]:.2f}", ha="center", va="center", fontsize=8.5, color="white" if heat[i,j] > 0.62 else COLORS["ink"])
    axes[0].spines[:].set_visible(False)
    fig.colorbar(im, ax=axes[0], fraction=0.045, pad=0.03)

    axes[1].plot(df["variant"].str.replace("_", " ").str.title(), df["balance"], marker="o", lw=2.2, color=COLORS["data"])
    axes[1].set_ylim(0.58, 0.82)
    axes[1].set_ylabel("Mean normalized objective")
    axes[1].set_title("Balanced multi-objective score")
    axes[1].tick_params(axis="x", rotation=25)
    style(axes[1])
    for ax, lab in zip(axes, "AB"):
        add_panel_label(ax, lab)
    fig.tight_layout()
    fig.savefig(out_dir() / "figure9_generator_ablation.png", dpi=350, bbox_inches="tight")
    plt.close(fig)


def fig7_stats():
    route = pd.read_csv(RESULT_DIR / "design_statistics" / "route_comparison_stats.csv")
    ab = pd.read_csv(RESULT_DIR / "design_statistics" / "generator_ablation_stats.csv")
    fig, axes = plt.subplots(2, 2, figsize=(12.6, 8.2))
    axes = axes.ravel()

    plot_route = route.loc[route["metric"].isin(["quality_score", "local_diversity", "predicted_permeability", "natural_ratio", "n_methyl_ratio"])].copy()
    y = np.arange(len(plot_route))
    axes[0].errorbar(plot_route["mean_diff"], y,
                     xerr=[plot_route["mean_diff"] - plot_route["ci_lower"], plot_route["ci_upper"] - plot_route["mean_diff"]],
                     fmt="o", color=COLORS["opt"], ecolor=COLORS["ink"], elinewidth=2.0, capsize=4, markersize=6)
    axes[0].axvline(0, color=COLORS["muted"], ls="--", lw=1.2)
    axes[0].set_yticks(y, plot_route["metric"].str.replace("_", " "))
    axes[0].set_xlabel("Mean difference (optimized - de novo)")
    axes[0].set_title("Route comparison with 95% CI")
    style(axes[0], "x")

    route_sig = plot_route.copy()
    route_sig["neglogp"] = -np.log10(route_sig["permutation_pvalue"].clip(lower=1e-6))
    axes[1].barh(route_sig["metric"].str.replace("_", " "), route_sig["neglogp"], color=COLORS["denovo"], edgecolor="white")
    axes[1].axvline(-math.log10(0.05), color=COLORS["screen"], ls="--", lw=1.5)
    axes[1].text(-math.log10(0.05) + 0.05, len(route_sig) - 0.7, "p=0.05", color=COLORS["screen"], fontsize=9)
    axes[1].set_xlabel("-log10(p)")
    axes[1].set_title("Route-level permutation tests")
    style(axes[1], "x")

    ab["comparison"] = "full_vs_" + ab["group_b"].astype(str)
    key = ab.loc[ab["comparison"].isin(["full_vs_no_motif", "full_vs_no_composition", "full_vs_quality_only"])].copy()
    key = key.loc[key["metric"].isin(["motif_score", "composition_alignment", "uncertainty_stability"])]
    pivot = key.pivot_table(index="comparison", columns="metric", values="permutation_pvalue", aggfunc="first")
    mat = -np.log10(pivot.fillna(1.0).clip(lower=1e-6).values)
    im = axes[2].imshow(mat, cmap="YlGnBu", aspect="auto", vmin=0, vmax=max(3, np.nanmax(mat)))
    axes[2].set_yticks(range(len(pivot.index)), [s.replace("full_vs_", "Full vs ").replace("_", " ") for s in pivot.index])
    axes[2].set_xticks(range(len(pivot.columns)), [c.replace("_", " ") for c in pivot.columns], rotation=20, ha="right")
    axes[2].set_title("Generator ablation significance")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            axes[2].text(j, i, f"{mat[i,j]:.1f}", ha="center", va="center", fontsize=8, color="white" if mat[i,j] > 1.5 else COLORS["ink"])
    axes[2].spines[:].set_visible(False)
    fig.colorbar(im, ax=axes[2], fraction=0.045, pad=0.03, label="-log10(p)")

    gen = pd.read_csv(RESULT_DIR / "generation_evaluation" / "summary.csv")
    gen = gen.loc[gen["group"].isin(["optimized_shortlist", "de_novo_shortlist"])]
    x = np.arange(len(gen))
    axes[3].bar(x - 0.18, gen["pairwise_jaccard_diversity"], 0.36, label="Diversity", color=COLORS["denovo"], edgecolor="white")
    axes[3].bar(x + 0.18, gen["mean_predicted_positive_prob"], 0.36, label="Positive prob.", color=COLORS["opt"], edgecolor="white")
    axes[3].set_xticks(x, ["Optimized", "De novo"])
    axes[3].set_ylim(0, 1.08)
    axes[3].legend(frameon=False, fontsize=8)
    axes[3].set_title("Shortlist quality and diversity")
    style(axes[3])

    for ax, lab in zip(axes, "ABCD"):
        add_panel_label(ax, lab)
    fig.tight_layout()
    fig.savefig(out_dir() / "figure10_statistical_summary.png", dpi=350, bbox_inches="tight")
    plt.close(fig)


def fig8_conformation_proxy():
    neigh = pd.read_csv(RESULT_DIR / "conformation_proxy_analysis" / "proxy_neighbor_summary.csv")
    train = pd.read_csv(RESULT_DIR / "conformation_proxy_analysis" / "proxy_summary.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.6), gridspec_kw={"width_ratios": [1, 1.15]})

    vals = pd.DataFrame({
        "group": ["All train", "Train top-100", "Optimized NN", "De novo NN"],
        "CHCl3_3DPSA": [
            train.loc[train["group"].eq("overall_train"), "CHCl3_3DPSA_mean"].iloc[0],
            train.loc[train["group"].eq("train_top100"), "CHCl3_3DPSA_mean"].iloc[0],
            neigh.loc[neigh["route"].eq("optimized"), "neighbor_CHCl3_3DPSA"].iloc[0],
            neigh.loc[neigh["route"].eq("de_novo"), "neighbor_CHCl3_3DPSA"].iloc[0],
        ],
        "H2O_3DPSA": [
            train.loc[train["group"].eq("overall_train"), "H2O_3DPSA_mean"].iloc[0],
            train.loc[train["group"].eq("train_top100"), "H2O_3DPSA_mean"].iloc[0],
            neigh.loc[neigh["route"].eq("optimized"), "neighbor_H2O_3DPSA"].iloc[0],
            neigh.loc[neigh["route"].eq("de_novo"), "neighbor_H2O_3DPSA"].iloc[0],
        ],
    })
    x = np.arange(len(vals))
    axes[0].plot(x, vals["CHCl3_3DPSA"], marker="o", lw=2.2, color=COLORS["opt"], label="CHCl3_3DPSA")
    axes[0].plot(x, vals["H2O_3DPSA"], marker="s", lw=2.2, color=COLORS["denovo"], label="H2O_3DPSA")
    axes[0].set_xticks(x, vals["group"], rotation=20, ha="right")
    axes[0].set_ylabel("Mean 3DPSA proxy")
    axes[0].set_title("Proxy shift toward permeable region")
    axes[0].legend(frameon=False, fontsize=8)
    style(axes[0])

    axes[1].scatter(vals["CHCl3_3DPSA"], vals["H2O_3DPSA"], s=[70, 110, 140, 140],
                    color=[COLORS["train"], COLORS["top"], COLORS["opt"], COLORS["denovo"]],
                    edgecolor="black", linewidth=0.8)
    for _, row in vals.iterrows():
        axes[1].annotate(row["group"], (row["CHCl3_3DPSA"], row["H2O_3DPSA"]), xytext=(6, 5), textcoords="offset points", fontsize=8)
    axes[1].set_xlabel("CHCl3_3DPSA")
    axes[1].set_ylabel("H2O_3DPSA")
    axes[1].set_title("Candidate nearest-neighbor proxy space")
    style(axes[1])
    for ax, lab in zip(axes, "AB"):
        add_panel_label(ax, lab)
    fig.tight_layout()
    fig.savefig(out_dir() / "figure6_conformation_proxy.png", dpi=350, bbox_inches="tight")
    plt.close(fig)


def fig9_novelty_depth():
    summary = pd.read_csv(RESULT_DIR / "candidate_novelty_depth" / "summary.csv")
    nn = pd.read_csv(RESULT_DIR / "candidate_novelty_depth" / "candidate_nearest_neighbors.csv")
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.3))
    route_colors = {"optimized_shortlist": COLORS["opt"], "de_novo_shortlist": COLORS["denovo"]}

    for route, sub in nn.groupby("route"):
        axes[0].hist(sub["nearest_train_token_jaccard"], bins=np.linspace(0, 1, 11), alpha=0.55, label=route.replace("_shortlist", ""), color=route_colors[route])
    axes[0].set_xlabel("Nearest-train token Jaccard")
    axes[0].set_ylabel("Candidates")
    axes[0].set_title("Token-space novelty")
    axes[0].legend(frameon=False, fontsize=8)
    style(axes[0])

    for route, sub in nn.groupby("route"):
        axes[1].hist(sub["nearest_descriptor_distance"], bins=10, alpha=0.55, label=route.replace("_shortlist", ""), color=route_colors[route])
    axes[1].set_xlabel("Nearest descriptor distance")
    axes[1].set_title("Descriptor-space novelty")
    style(axes[1])

    x = np.arange(len(summary))
    width = 0.36
    labels = summary["route"].str.replace("_shortlist", "").str.replace("_", " ").str.title()
    axes[2].bar(x - width/2, summary["mean_nearest_train_token_jaccard"], width, color=COLORS["opt"], label="Jaccard", edgecolor="black", linewidth=0.7)
    axes[2].bar(x + width/2, summary["mean_nearest_descriptor_distance"], width, color=COLORS["denovo"], label="Distance", edgecolor="black", linewidth=0.7)
    axes[2].set_xticks(x, labels)
    axes[2].set_title("Route-level novelty summary")
    axes[2].legend(frameon=False, fontsize=8)
    style(axes[2])
    for ax, lab in zip(axes, "ABC"):
        add_panel_label(ax, lab)
    fig.tight_layout()
    fig.savefig(out_dir() / "figure12_novelty_depth.png", dpi=350, bbox_inches="tight")
    plt.close(fig)


def ring_panel(ax, tokens, title, color):
    ax.axis("off")
    ax.set_aspect("equal")
    theta = np.linspace(np.pi / 2, np.pi / 2 + 2 * np.pi, len(tokens), endpoint=False)
    pts = np.c_[np.cos(theta), np.sin(theta)]
    ax.plot(np.r_[pts[:, 0], pts[0, 0]], np.r_[pts[:, 1], pts[0, 1]], color=color, lw=3.0, solid_capstyle="round")
    for token, (x, y) in zip(tokens, pts):
        ax.scatter([x], [y], s=760, facecolor="white", edgecolor=color, linewidth=2.1, zorder=3)
        ax.text(x, y, token, ha="center", va="center", fontsize=10, fontweight="bold", color=COLORS["ink"], zorder=4)
    ax.set_xlim(-1.45, 1.45)
    ax.set_ylim(-1.35, 1.35)
    ax.set_title(title, fontsize=12, fontweight="bold", color=COLORS["ink"])


def fig10_case_study():
    chem, draw = safe_import_rdkit()
    case_df = pd.read_csv(RESULT_DIR / "case_analysis" / "representative_cases_compact.csv")
    mono = pd.read_csv(DATASET_DIR / "CycPeptMPDB_Monomer_All.csv", low_memory=False)
    mono_lookup = mono.drop_duplicates("Symbol").set_index("Symbol")["capped_SMILES"].to_dict()
    opt = case_df.loc[case_df["route"].eq("optimized")].iloc[0]
    de = case_df.loc[case_df["route"].eq("de_novo")].iloc[0]

    fig = plt.figure(figsize=(14, 8.6))
    gs = fig.add_gridspec(2, 4, height_ratios=[1, 1], width_ratios=[1, 1, 1, 1.15], hspace=0.32, wspace=0.24)
    ax0 = fig.add_subplot(gs[0, 0])
    ax1 = fig.add_subplot(gs[0, 1])
    ax2 = fig.add_subplot(gs[0, 2])
    ax3 = fig.add_subplot(gs[0, 3])
    ax4 = fig.add_subplot(gs[1, 0])
    ax5 = fig.add_subplot(gs[1, 1])
    ax6 = fig.add_subplot(gs[1, 2:])

    ring_panel(ax0, parse_helm_monomers(opt["parent_helm"]), "Optimized parent", COLORS["muted"])
    ring_panel(ax1, parse_helm_monomers(opt["candidate_helm"]), "Optimized candidate", COLORS["opt"])
    ax2.axis("off")
    ax2.set_title("Key edits", fontsize=12, fontweight="bold")
    muts = re.findall(r"(\d+):([^;]+?)->([^;]+)", str(opt["mutation_description"]))
    y = 0.78
    for idx, old, new in muts[:3]:
        ax2.text(0.05, y, f"Position {int(idx)+1}", fontsize=10, fontweight="bold", color=COLORS["ink"])
        ax2.text(0.05, y - 0.13, f"{old}  →  {new}", fontsize=13, color=COLORS["screen"], fontweight="bold")
        y -= 0.28
    ax2.text(0.05, 0.08, f"Improvement = {opt['improvement']:.3f}", fontsize=10, color=COLORS["ink"])

    ax3.axis("off")
    ax3.set_title("Representative monomers", fontsize=12, fontweight="bold")
    if chem is not None and draw is not None and muts:
        shown = []
        for _, old, new in muts[:2]:
            shown.extend([old, new])
        for k, sym in enumerate(shown[:4]):
            img = smiles_to_image(mono_lookup.get(sym), chem, draw, size=(220, 150))
            x0 = 0.03 + (k % 2) * 0.49
            y0 = 0.52 - (k // 2) * 0.42
            if img is not None:
                ax3.imshow(img, extent=(x0, x0 + 0.42, y0, y0 + 0.30))
            ax3.text(x0 + 0.21, y0 - 0.04, sym, ha="center", fontsize=9)

    ring_panel(ax4, parse_helm_monomers(de["candidate_helm"]), "De novo candidate", COLORS["denovo"])
    ring_panel(ax5, parse_helm_monomers(de["reference_helm"]), "Nearest high-permeability reference", COLORS["train"])

    shift_items = [
        ("MolLogP", de["delta_to_reference_MolLogP_mean"]),
        ("TPSA", de["delta_to_reference_TPSA_mean"]),
        ("Fsp3", de["delta_to_reference_FractionCSP3_mean"]),
        ("QED", de["delta_to_reference_qed_mean"]),
        ("N-methyl", de["delta_to_reference_n_methyl_ratio"]),
        ("D-ratio", de["delta_to_reference_d_ratio"]),
    ]
    labels = [x[0] for x in shift_items]
    vals = [float(x[1]) for x in shift_items]
    ax6.barh(labels, vals, color=[COLORS["opt"] if v >= 0 else COLORS["screen"] for v in vals], edgecolor="white")
    ax6.axvline(0, color=COLORS["ink"], lw=1.2)
    ax6.set_title("Descriptor shift to nearest reference", fontsize=12, fontweight="bold")
    ax6.set_xlabel("Candidate - reference")
    ax6.text(0.02, 0.04, f"De novo permeability={de['predicted_permeability']:.3f}; prob={de['predicted_positive_prob']:.3f}",
             transform=ax6.transAxes, fontsize=10)
    style(ax6, "x")

    for ax, lab in zip([ax0, ax4], "AB"):
        add_panel_label(ax, lab)
    fig.suptitle("Representative cyclic peptide case study", fontsize=15, fontweight="bold", color=COLORS["ink"])
    fig.savefig(out_dir() / "figure13_case_study_panels.png", dpi=350, bbox_inches="tight")
    plt.close(fig)


def main():
    fig1_workflow()
    fig2_prediction()
    fig3_source_heterogeneity()
    fig4_generation()
    fig5_quality_diversity()
    fig6_generator_ablation()
    fig7_stats()
    fig8_conformation_proxy()
    fig9_novelty_depth()
    fig10_case_study()
    print(f"Saved revised figures to {out_dir()}")


if __name__ == "__main__":
    main()
