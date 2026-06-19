import re
import sys
from io import BytesIO
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main.train_enhanced_predictor import parse_helm_monomers
from utils.project_paths import DATASET_DIR, RESULT_DIR


def safe_import_rdkit():
    try:
        from rdkit import Chem
        from rdkit.Chem import Draw
        return Chem, Draw
    except Exception:
        return None, None


def token_ring(ax, tokens, title, color):
    ax.set_aspect("equal")
    ax.axis("off")
    n = len(tokens)
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pts = np.c_[np.cos(theta), np.sin(theta)]
    ax.plot(np.r_[pts[:, 0], pts[0, 0]], np.r_[pts[:, 1], pts[0, 1]], color=color, lw=2)
    for i, (x, y) in enumerate(pts):
        ax.scatter([x], [y], s=400, color="white", edgecolor=color, linewidth=1.5, zorder=2)
        ax.text(x, y, tokens[i], ha="center", va="center", fontsize=8, zorder=3)
    ax.set_title(title, fontsize=11)


def smiles_to_image(smiles, chem, draw, size=(260, 180)):
    if not isinstance(smiles, str) or not smiles:
        return None
    mol = chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    img = draw.MolToImage(mol, size=size)
    return img


def parse_mutations(desc):
    if not isinstance(desc, str) or not desc:
        return []
    matches = re.findall(r"(\d+):([^;]+?)\-\>([^;]+)", desc)
    return [(int(pos), old, new) for pos, old, new in matches]


def main():
    chem, draw = safe_import_rdkit()
    out_dir = RESULT_DIR / "paper_figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    case_df = pd.read_csv(RESULT_DIR / "case_analysis" / "representative_cases_compact.csv")
    mono_df = pd.read_csv(DATASET_DIR / "CycPeptMPDB_Monomer_All.csv", low_memory=False)
    mono_lookup = (
        mono_df.drop_duplicates(subset=["Symbol"])
        .set_index("Symbol")[["capped_SMILES", "Compound_Name"]]
        .to_dict("index")
    )

    opt_case = case_df.loc[case_df["route"] == "optimized"].iloc[0]
    denovo_case = case_df.loc[case_df["route"] == "de_novo"].iloc[0]

    fig = plt.figure(figsize=(14, 9))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.0, 1.15], width_ratios=[1.0, 1.0, 1.25], hspace=0.28, wspace=0.22)

    # Optimized route: parent / candidate / mutation chemistry
    ax0 = fig.add_subplot(gs[0, 0])
    token_ring(ax0, parse_helm_monomers(opt_case["parent_helm"]), "Optimized parent", "#9a3412")

    ax1 = fig.add_subplot(gs[0, 1])
    token_ring(ax1, parse_helm_monomers(opt_case["candidate_helm"]), "Optimized candidate", "#0f766e")

    ax2 = fig.add_subplot(gs[0, 2])
    ax2.axis("off")
    muts = parse_mutations(opt_case["mutation_description"])
    ax2.set_title("Key substitutions", fontsize=11)
    if chem is not None and draw is not None and muts:
        y_positions = [0.68, 0.30]
        for (pos, old, new), y in zip(muts[:2], y_positions):
            old_img = smiles_to_image(mono_lookup.get(old, {}).get("capped_SMILES"), chem, draw)
            new_img = smiles_to_image(mono_lookup.get(new, {}).get("capped_SMILES"), chem, draw)
            if old_img is not None:
                ax2.imshow(old_img, extent=(0.02, 0.36, y, y + 0.22))
            if new_img is not None:
                ax2.imshow(new_img, extent=(0.62, 0.96, y, y + 0.22))
            ax2.annotate("", xy=(0.58, y + 0.11), xytext=(0.40, y + 0.11), arrowprops=dict(arrowstyle="->", lw=1.6))
            ax2.text(0.19, y - 0.04, f"Pos {pos}: {old}", ha="center", fontsize=9)
            ax2.text(0.79, y - 0.04, f"{new}", ha="center", fontsize=9)
    else:
        ax2.text(0.05, 0.75, f"Mutation: {opt_case['mutation_description']}", fontsize=10)
    ax2.text(0.02, 0.05, f"Predicted permeability: {opt_case['predicted_permeability']:.3f}\nImprovement: {opt_case['improvement']:.3f}", fontsize=10)

    # De novo route: candidate / nearest reference / descriptor shifts
    ax3 = fig.add_subplot(gs[1, 0])
    token_ring(ax3, parse_helm_monomers(denovo_case["candidate_helm"]), "De novo candidate", "#1d4ed8")

    ax4 = fig.add_subplot(gs[1, 1])
    token_ring(ax4, parse_helm_monomers(denovo_case["reference_helm"]), "Nearest high-permeability reference", "#6b7280")

    ax5 = fig.add_subplot(gs[1, 2])
    shift_items = [
        ("MolLogP", denovo_case["delta_to_reference_MolLogP_mean"]),
        ("TPSA", denovo_case["delta_to_reference_TPSA_mean"]),
        ("Fsp3", denovo_case["delta_to_reference_FractionCSP3_mean"]),
        ("QED", denovo_case["delta_to_reference_qed_mean"]),
        ("N-methyl", denovo_case["delta_to_reference_n_methyl_ratio"]),
        ("D-ratio", denovo_case["delta_to_reference_d_ratio"]),
    ]
    labels = [k for k, _ in shift_items]
    vals = [float(v) for _, v in shift_items]
    colors = ["#2563eb" if v >= 0 else "#dc2626" for v in vals]
    ax5.barh(labels, vals, color=colors, alpha=0.9)
    ax5.axvline(0, color="#374151", lw=1)
    ax5.set_title("Shift to nearest reference", fontsize=11)
    ax5.set_xlabel("Candidate - reference")
    ax5.spines["top"].set_visible(False)
    ax5.spines["right"].set_visible(False)
    ax5.grid(alpha=0.2, axis="x")
    ax5.text(
        0.02,
        0.02,
        f"Predicted permeability = {denovo_case['predicted_permeability']:.3f}\nPositive probability = {denovo_case['predicted_positive_prob']:.3f}",
        transform=ax5.transAxes,
        fontsize=9,
        va="bottom",
    )

    for ax, letter in zip([ax0, ax3], ["A", "B"]):
        ax.text(-0.12, 1.06, letter, transform=ax.transAxes, fontsize=15, weight="bold")

    fig.suptitle("Figure 13. Representative case-study panels with chemically interpretable edits", fontsize=16, y=0.98)
    fig.tight_layout(rect=[0, 0, 1, 0.965])
    out_path = out_dir / "figure13_case_study_panels.png"
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved case-study panel figure to: {out_path}")


if __name__ == "__main__":
    main()
