import csv
import copy
import json
import math
import re
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from statistics import mean, pstdev


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = PROJECT_ROOT / "三稿_投稿修改版.docx"
SOURCE_INFO_DOC = Path(r"C:\Users\AMDYES\Desktop\文\Shen_Manuscript_Revised_R1.docx")
OUT_PATH = PROJECT_ROOT / "SCI_submission_revised_v12.docx"
RESULT_DIR = PROJECT_ROOT / "Result"

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"

ET.register_namespace("w", NS_W)
ET.register_namespace("r", NS_R)
ET.register_namespace("wp", NS_WP)
ET.register_namespace("a", NS_A)
ET.register_namespace("pic", NS_PIC)


def tag(ns, name):
    return f"{{{ns}}}{name}"


def w(name):
    return tag(NS_W, name)


def rel(name):
    return tag(NS_REL, name)


def para(text="", style=None, align=None, bold=False, italic=False, size=None):
    p = ET.Element(w("p"))
    if style or align:
        ppr = ET.SubElement(p, w("pPr"))
        if style:
            ET.SubElement(ppr, w("pStyle"), {w("val"): style})
        if align:
            ET.SubElement(ppr, w("jc"), {w("val"): align})
    if text:
        add_run(p, text, bold=bold, italic=italic, size=size)
    return p


def add_run(p, text, bold=False, italic=False, size=None):
    r = ET.SubElement(p, w("r"))
    if bold or italic or size:
        rpr = ET.SubElement(r, w("rPr"))
        if bold:
            ET.SubElement(rpr, w("b"))
        if italic:
            ET.SubElement(rpr, w("i"))
        if size:
            ET.SubElement(rpr, w("sz"), {w("val"): str(size)})
            ET.SubElement(rpr, w("szCs"), {w("val"): str(size)})
    t = ET.SubElement(r, w("t"))
    if text.startswith(" ") or text.endswith(" "):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text


def heading(text, level=1):
    return para(text, style=f"Heading{level}", bold=True)


def page_break():
    p = ET.Element(w("p"))
    r = ET.SubElement(p, w("r"))
    ET.SubElement(r, w("br"), {w("type"): "page"})
    return p


def read_csv_rows(path, max_rows=None):
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            rows.append(row)
            if max_rows and len(rows) >= max_rows:
                break
    return rows


def read_csv_dicts(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def select_csv_columns(path, columns, rename=None):
    rows = read_csv_rows(path)
    header = rows[0]
    idx = [header.index(c) for c in columns]
    out_header = [rename.get(c, c) if rename else c for c in columns]
    out = [out_header]
    for row in rows[1:]:
        out.append([row[i] if i < len(row) else "" for i in idx])
    return out


def fmt(value):
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            return value
    if isinstance(value, float):
        if math.isnan(value):
            return ""
        return f"{value:.3f}".rstrip("0").rstrip(".")
    return str(value)


def fmt_ci(item):
    return f"{item['mean']:.3f} [{item['ci_lower']:.3f}, {item['ci_upper']:.3f}]"


def bootstrap_mean_ci(values, n_boot=2000, seed=42):
    import random

    values = [float(v) for v in values if v != "" and v is not None]
    if not values:
        return ""
    rng = random.Random(seed)
    boots = []
    n = len(values)
    for _ in range(n_boot):
        boots.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    boots.sort()
    lo = boots[int(0.025 * n_boot)]
    hi = boots[int(0.975 * n_boot)]
    return f"{sum(values)/n:.3f} [{lo:.3f}, {hi:.3f}]"


def read_feature_ablation_rows():
    rows = read_csv_dicts(RESULT_DIR / "paper_tables" / "ablation.csv")
    out = [["Feature setting", "RMSE", "R2", "AUROC", "MCC"]]
    label_map = {
        "descriptor_only": "Descriptor only",
        "text_plus_peptide_descriptors": "Text + peptide desc.",
        "text_plus_descriptors": "Text + all desc.",
        "text_plus_monomer_stats": "Text + monomer stats",
        "text_only": "Text only",
    }
    for r in rows:
        out.append([
            label_map.get(r["config"], r["config"]),
            f'{float(r["reg_rmse_mean"]):.3f}',
            f'{float(r["reg_r2_mean"]):.3f}',
            f'{float(r["cls_auroc_mean"]):.3f}',
            f'{float(r["cls_mcc_mean"]):.3f}',
        ])
    return out


def read_top_feature_rows(n=8):
    rows = read_csv_dicts(RESULT_DIR / "loso_random_forest" / "feature_importance.csv")
    out = [["Rank", "Feature", "Importance"]]
    for i, r in enumerate(rows[:n], start=1):
        out.append([str(i), r["feature"], f'{float(r["importance"]):.3f}'])
    return out


def table(rows):
    tbl = ET.Element(w("tbl"))
    tbl_pr = ET.SubElement(tbl, w("tblPr"))
    ET.SubElement(tbl_pr, w("tblW"), {w("w"): "5000", w("type"): "pct"})
    borders = ET.SubElement(tbl_pr, w("tblBorders"))
    for border in ["top", "bottom"]:
        ET.SubElement(borders, w(border), {w("val"): "single", w("sz"): "8", w("space"): "0", w("color"): "000000"})
    for border in ["left", "right", "insideH", "insideV"]:
        ET.SubElement(borders, w(border), {w("val"): "nil"})

    ncols = max(len(r) for r in rows)
    grid = ET.SubElement(tbl, w("tblGrid"))
    for _ in range(ncols):
        ET.SubElement(grid, w("gridCol"), {w("w"): str(9000 // ncols)})

    for r_i, row in enumerate(rows):
        tr = ET.SubElement(tbl, w("tr"))
        for c_i in range(ncols):
            value = row[c_i] if c_i < len(row) else ""
            tc = ET.SubElement(tr, w("tc"))
            tc_pr = ET.SubElement(tc, w("tcPr"))
            ET.SubElement(tc_pr, w("tcW"), {w("w"): str(9000 // ncols), w("type"): "dxa"})
            if r_i == 0:
                tc_borders = ET.SubElement(tc_pr, w("tcBorders"))
                ET.SubElement(tc_borders, w("bottom"), {w("val"): "single", w("sz"): "6", w("space"): "0", w("color"): "000000"})
            p = ET.SubElement(tc, w("p"))
            ppr = ET.SubElement(p, w("pPr"))
            ET.SubElement(ppr, w("jc"), {w("val"): "center"})
            add_run(p, fmt(value), bold=(r_i == 0), size=18)
    return tbl


def image_paragraph(rid, name, doc_id, cx=5600000, cy=3300000):
    p = ET.Element(w("p"))
    ppr = ET.SubElement(p, w("pPr"))
    ET.SubElement(ppr, w("jc"), {w("val"): "center"})
    r = ET.SubElement(p, w("r"))
    drawing = ET.SubElement(r, w("drawing"))
    inline = ET.SubElement(drawing, tag(NS_WP, "inline"), {"distT": "0", "distB": "0", "distL": "0", "distR": "0"})
    ET.SubElement(inline, tag(NS_WP, "extent"), {"cx": str(cx), "cy": str(cy)})
    ET.SubElement(inline, tag(NS_WP, "docPr"), {"id": str(doc_id), "name": name})
    graphic = ET.SubElement(inline, tag(NS_A, "graphic"))
    graphic_data = ET.SubElement(graphic, tag(NS_A, "graphicData"), {"uri": "http://schemas.openxmlformats.org/drawingml/2006/picture"})
    pic = ET.SubElement(graphic_data, tag(NS_PIC, "pic"))
    nv = ET.SubElement(pic, tag(NS_PIC, "nvPicPr"))
    ET.SubElement(nv, tag(NS_PIC, "cNvPr"), {"id": str(doc_id), "name": name})
    ET.SubElement(nv, tag(NS_PIC, "cNvPicPr"))
    fill = ET.SubElement(pic, tag(NS_PIC, "blipFill"))
    ET.SubElement(fill, tag(NS_A, "blip"), {tag(NS_R, "embed"): rid})
    stretch = ET.SubElement(fill, tag(NS_A, "stretch"))
    ET.SubElement(stretch, tag(NS_A, "fillRect"))
    sp = ET.SubElement(pic, tag(NS_PIC, "spPr"))
    xfrm = ET.SubElement(sp, tag(NS_A, "xfrm"))
    ET.SubElement(xfrm, tag(NS_A, "off"), {"x": "0", "y": "0"})
    ET.SubElement(xfrm, tag(NS_A, "ext"), {"cx": str(cx), "cy": str(cy)})
    geom = ET.SubElement(sp, tag(NS_A, "prstGeom"), {"prst": "rect"})
    ET.SubElement(geom, tag(NS_A, "avLst"))
    return p


def load_metrics():
    metrics = json.loads((RESULT_DIR / "hybrid_predictor" / "metrics.json").read_text(encoding="utf-8"))
    loso = json.loads((RESULT_DIR / "loso_random_forest" / "summary.json").read_text(encoding="utf-8"))
    dataset_rows = read_csv_rows(PROJECT_ROOT / "dataset" / "CycPeptMPDB_Peptide_Length_6.csv")
    header = dataset_rows[0]
    src_i = header.index("Source")
    year_i = header.index("Year")
    perm_i = header.index("Permeability")
    sources = {}
    years = []
    perms = []
    positives = 0
    for row in dataset_rows[1:]:
        sources[row[src_i]] = sources.get(row[src_i], 0) + 1
        years.append(int(float(row[year_i])))
        perm = float(row[perm_i])
        perms.append(perm)
        positives += perm >= -6.0
    return metrics, loso, len(dataset_rows) - 1, sources, min(years), max(years), positives / (len(dataset_rows) - 1), perms


def manuscript_elements(rids):
    metrics, loso, n_samples, sources, y_min, y_max, pos_rate, perms = load_metrics()
    ci = json.loads((RESULT_DIR / "confidence_intervals" / "hybrid_bootstrap_ci.json").read_text(encoding="utf-8"))
    rnd = metrics["random_split"]
    src = metrics["source_split"]
    loso_auc = loso["strict_sources_only"]["classification"]["auroc"]
    opt_rows = read_csv_dicts(RESULT_DIR / "design_pipeline" / "final_shortlist.csv")
    denovo_rows = read_csv_dicts(RESULT_DIR / "de_novo_generation" / "final_generated_shortlist.csv")
    opt_summary = read_csv_dicts(RESULT_DIR / "design_pipeline" / "summary.csv")[0]
    denovo_summary = read_csv_dicts(RESULT_DIR / "de_novo_generation" / "summary.csv")[0]

    els = []
    els.append(para("Descriptor-guided robust prediction and dual-route design of membrane-permeable cyclic peptides", align="center", bold=True, size=32))
    els.append(para("Shiqian Han 1, Yuxing Shen 2*, Honghui An 2, Jun Wang 2", align="center"))
    els.append(para("1. College of Science, Shenyang University of Chemical Technology, Shenyang, Liaoning 110142, China", align="center"))
    els.append(para("2. College of Computer Science and Technology, Shenyang University of Chemical Technology, Shenyang, Liaoning 110142, China", align="center"))
    els.append(para("3. Key Laboratory for Chemical Process Industry Intelligent Technology of Liaoning Province, Shenyang, Liaoning 110142, China", align="center"))
    els.append(para("*Correspondence: Yuxing Shen, gujunxiaoan@gmail.com; ORCID: 0009-0008-1190-6170", align="center"))
    els.append(para("Running title: Source-aware cyclic peptide permeability design", align="center"))
    els.append(heading("Abstract", 1))
    els += [
        para("Background: Passive membrane permeability remains a major bottleneck for cyclic peptides that target intracellular proteins. Recent machine-learning studies have improved permeability prediction and have started to connect predictors with molecular design, but random splits can overestimate practical performance and generated candidates are often reported without sufficient checks on novelty, uncertainty, diversity, and chemical plausibility."),
        para(f"Methods: We reconstructed a public length-six cyclic peptide subset from CycPeptMPDB, containing {n_samples} annotated peptides from {len(sources)} literature sources published between {y_min} and {y_max}. The framework combines HELM-token features, peptide-level physicochemical descriptors, monomer-level aggregate descriptors, natural/non-natural composition, N-methylation ratio, and D-monomer ratio. Predictors were evaluated under random split, source split, repeated group cross-validation, and leave-one-source-out settings. We then coupled the scorer to two design routes: constrained local optimization around high-quality seeds and multi-objective de novo generation guided by motif, composition, uncertainty, diversity, and novelty terms."),
        para(f"Results: The hybrid predictor achieved AUROC={rnd['classification']['hybrid']['auroc']:.3f} on the random split but dropped to AUROC={src['classification']['hybrid']['auroc']:.3f} under source-aware testing, quantifying a 0.221 AUROC generalization gap that is hidden by random evaluation. This source-aware gap is itself a central finding: it shows that cyclic peptide permeability benchmarks can be dominated by source structure rather than only by molecular representation. Rather than treating the scorer as a stand-alone oracle, the design stage used uncertainty penalties, diversity filtering, exact and nearest-neighbor novelty checks, and 3D polarity-proxy analysis as safeguards against overconfident extrapolation. The optimization route produced 12 non-duplicate candidates with mean predicted permeability -4.511, whereas the de novo route produced 24 non-duplicate candidates with mean predicted permeability -4.725 and higher exploration diversity."),
        para("Scientific Contribution: This study contributes a reproducible source-aware evaluation and design workflow for cyclic peptide permeability. It quantifies the gap between random and source-aware evaluation, reports feature-group ablations showing the dominant role of descriptor information, and differentiates local optimization from de novo exploration through uncertainty, diversity, novelty-depth, and mechanistic proxy analyses."),
        para("Conclusions: This work provides a public, reproducible, source-aware computational framework for cyclic peptide permeability prediction and candidate design. The contribution is both diagnostic and generative: it exposes source shift in current evaluation practice and then builds a conservative design workflow around that limitation."),
        para("Keywords: cyclic peptide; membrane permeability; de novo design; source-aware validation; multi-objective generation; molecular descriptors"),
        heading("1. Introduction", 1),
        para("Cyclic peptides occupy an important region between small molecules and biologics. Their conformational constraint, broad interaction surface, and proteolytic stability make them attractive for modulating protein-protein interactions and other difficult targets [1-3]. However, many cyclic peptides still show poor passive membrane permeability, which limits oral exposure and intracellular target engagement [4,5]. Improving permeability while preserving a chemically meaningful peptide scaffold is therefore a central problem in cyclic peptide drug design."),
        para("Previous studies have shown that passive permeability of cyclic peptides is strongly coupled to conformation, internal hydrogen bonding, polarity shielding, N-methylation, and chameleonic behavior across aqueous and membrane-like environments [6-11]. These mechanisms motivate descriptor- and proxy-based modeling, but they also warn against relying on a single two-dimensional score. Modern machine-learning models have increasingly been used to predict cyclic peptide permeability and to guide candidate search [12-16]."),
        para("Nevertheless, three issues remain particularly important for a practical design workflow. First, some published pipelines depend on private model weights, molecular dynamics trajectories, or preprocessing assets that are difficult to reproduce. Second, random train-test splits can mix highly related peptide chemotypes and experimental sources, thereby inflating performance estimates [17]. Third, design studies often emphasize top predicted scores while providing less evidence for diversity, novelty, uncertainty, and mechanistic plausibility."),
        para("Here we address these issues by building a reproducible descriptor-guided workflow on public data. We focus on length-six cyclic peptides from CycPeptMPDB [12] to reduce length-driven confounding and to keep the generation space controlled. The study makes three contributions: (i) a source-aware evaluation of multiple predictors under random, source, group-CV, and leave-one-source-out settings; (ii) a dual-route design strategy that separates local exploitation from broader de novo exploration; and (iii) a multi-layer candidate validation package covering uncertainty, quality-diversity structure, source heterogeneity, 3D polarity proxies, and nearest-neighbor novelty depth."),
        heading("2. Related Work", 1),
        para("CycPeptMPDB provided a key public basis for modeling membrane permeability of cyclic peptides by organizing HELM strings, monomer annotations, permeability values, sources, and years [12]. Subsequent methods have explored sequence features, graph representations, molecular descriptors, and multimodal encodings. MuCoCP, Multi_CycGT, and MultiCycPermea illustrate the trend toward richer representations and stronger same-distribution performance [13-15]. A recent systematic benchmark further emphasized that evaluation protocol and distribution shift strongly influence the apparent reliability of permeability predictors [16]."),
        para("The broader drug-discovery literature also shows why permeability cannot be reduced to molecular weight or a simple rule-of-five filter. Macrocycles and cyclic peptides often operate in beyond-rule-of-five space, where solvent-exposed polarity, conformational flexibility, and intramolecular hydrogen bonding can dominate passive diffusion [4,6-11,18-20]. For this reason, our framework uses public descriptors and 3D polarity proxies as conservative mechanistic checks rather than as definitive experimental substitutes."),
        para("Design-oriented studies, including AI-driven de novo cyclic peptide design and C2PO, demonstrate that permeability models can be connected to candidate optimization [21,22]. These studies are valuable because they move beyond prediction toward actionable molecules. However, generated candidates remain difficult to assess when the scorer is itself sensitive to source shift. This motivated our choice to treat source-aware reliability as the starting point of design rather than as a secondary analysis."),
        heading("3. Materials and Methods", 1),
        heading("3.1 Dataset Reconstruction", 2),
        para(f"The working dataset was reconstructed from the public CycPeptMPDB peptide table. We retained cyclic peptides with main-chain monomer length equal to 6 and available permeability labels, yielding {n_samples} samples. The dataset spans {len(sources)} sources and years {y_min}-{y_max}. The positive class was defined using a permeability threshold of -6.0, resulting in a positive rate of {pos_rate:.3f}. The two largest sources were 2020_Townsend ({sources.get('2020_Townsend', 0)} peptides) and 2016_Furukawa ({sources.get('2016_Furukawa', 0)} peptides), making source-aware evaluation necessary."),
        para("Exact HELM strings, permeability values, source labels, and years were retained. Candidate novelty was assessed against exact training HELM strings and through token-level and descriptor-space nearest-neighbor analysis. Because repeated or near-repeated chemotypes can bias random splits, source-level splits and leave-one-source-out analysis were used as stricter stress tests."),
        heading("3.2 Feature Representation", 2),
        para("The feature representation avoided private molecular dynamics trajectories. HELM strings were tokenized to generate text features. Peptide-level descriptors included MolWt, TPSA, MolLogP, QED, FractionCSP3, heavy atom count, hydrogen bond acceptor/donor counts, and ring count. Monomer-level summaries included mean, standard deviation, and maximum values for selected descriptors. Composition features included natural residue ratio, N-methylated residue ratio, D-monomer ratio, aromatic ratio, sequence length, and unique monomer ratio."),
        para("For text-based models, HELM tokens were represented using word-level TF-IDF n-grams with ngram_range=(1, 2) and character-window TF-IDF features with ngram_range=(3, 5), both using min_df=2. Numeric descriptor matrices were standardized inside each training split to avoid information leakage. Missing descriptor values were not imputed from the test set; feature construction was performed before splitting, while all model fitting, scaling, and threshold selection used training-only information."),
        heading("3.3 Predictors and Evaluation", 2),
        para("We compared three main predictor families. The public baseline used TF-IDF HELM-token features and linear models. The enhanced predictor combined sequence-pattern and physicochemical descriptors. The hybrid predictor fused text and numeric descriptor branches. Descriptor-only models, including Random Forest, were used as source-aware baselines because they are easier to reproduce and inspect. Regression was evaluated by RMSE, MAE, and R2; classification was evaluated by accuracy, F1, AUROC, PR-AUC, MCC, and calibration statistics."),
        para("We intentionally used transparent and reproducible baselines rather than reimplementing recent complex cyclic-peptide deep learning models as direct competitors. Multi_CycGT reported average accuracy 0.8206 and AUC 0.8650 under its published evaluation protocol, and MultiCycPermea reported an in-distribution MSE reduction from 0.29 to 0.16 relative to Multi_CycGT. These numbers demonstrate that deep multimodal models can be strong under their own settings, but directly comparing them to the present source-split protocol would not be fair unless the same held-out-source split and preprocessing were used. To our knowledge, source-split performance for these models has not been reported on the length-six subset used here. We therefore frame our transparent baselines as a reproducible source-aware stress test rather than as a claim of state-of-the-art same-distribution accuracy."),
        para(f"The random split used {rnd['train_samples']} training and {rnd['test_samples']} test samples. The source split used {src['train_samples']} training samples from {src['num_train_sources']} sources and {src['test_samples']} test samples from {src['num_test_sources']} held-out sources. Leave-one-source-out evaluation was performed for sources with sufficient test samples."),
        para("Linear regression baselines used Ridge regression with alpha=1.0. Classification baselines used logistic regression with max_iter=3000 and class_weight='balanced'. Descriptor Random Forest models used 400-500 trees, unrestricted depth, min_samples_leaf=2, random_state=42, and class_weight='balanced_subsample' for classification. Repeated group-CV and descriptor benchmark splits used GroupShuffleSplit with five repeated source-aware splits. Classification thresholds for hybrid models were selected on an inner validation split by maximizing MCC over thresholds from 0.20 to 0.80."),
        para("For a peptide x_i with observed permeability y_i and source label s_i, the regression objective was defined as:"),
        para("{L_reg = (1/N) sum_i (y_i - f(x_i))^2.}    (1)"),
        para("The binary permeability label was z_i = 1[y_i >= -6.0]. Classification performance was evaluated from p_i = P(z_i = 1 | x_i). To emphasize source-aware reliability, we report both random-split risk and held-out-source risk:"),
        para("{R_source = (1/|S_test|) sum_{s in S_test} (1/n_s) sum_{i:s_i=s} loss(y_i, f(x_i)).}    (2)"),
        heading("3.4 Dual-Route Candidate Design", 2),
        para("The constrained optimization route starts from high-quality seeds and applies single- or double-site monomer substitutions. Candidate ranking combines predicted permeability, predicted positive probability, estimated improvement over the parent, uncertainty penalties, and diversity filtering. This route is intended for low-risk exploitation around known permeable scaffolds."),
        para("In the constrained route, candidate pools were generated by single- and double-site substitutions from high-quality parent peptides using the observed monomer vocabulary. Candidates were then filtered by exact HELM uniqueness, predicted improvement, predicted positive probability, uncertainty, and composition-level diversity. The final shortlist was selected after composition de-duplication to avoid reporting multiple near-identical analogs."),
        para("The de novo route learns position-level and global monomer preferences from high-permeability elite peptides and then performs guided sampling followed by local refinement. Candidates are scored by a multi-objective function including permeability quality, classification probability, motif prior, composition alignment, uncertainty stability, and novelty. This route is intended to explore a broader but still chemically constrained neighborhood."),
        para("For de novo generation, the first stage sampled candidates from learned position priors and global monomer frequencies. A second focused-refinement stage perturbed high-scoring candidates while preserving the length-six cyclic peptide constraint. The full generator and its ablated variants used the same final count target so that quality-diversity differences reflected scoring terms rather than list size. The reported shortlists were deliberately conservative: they are high-confidence, composition-unique priority sets for downstream validation, not the full output capacity of either generator."),
        para("The robust candidate score used for prioritization can be summarized as:"),
        para("{Score_robust(x) = f_perm(x) + lambda_p p_pos(x) - lambda_u sigma_perm(x) - lambda_d D_near(x).}    (3)"),
        para("Here f_perm is the predicted permeability, p_pos is the predicted positive probability, sigma_perm is the prediction uncertainty proxy, and D_near penalizes excessive closeness to already selected or training-set candidates when diversity filtering is applied. The weights were used as ranking hyperparameters and were fixed before final shortlist reporting after preliminary inspection of validation-set ranking behavior; they were not optimized on the final held-out candidates. Because these weights can affect the exploitation-exploration balance, we report generator ablations to test whether the individual scoring terms change shortlist properties. For de novo generation, the final multi-objective score was:"),
        para("{Score_MO(x) = w_q Q(x) + w_m M(x) + w_c C(x) + w_s U(x) + w_n N(x), with sum_k w_k = 1.}    (4)"),
        para("Q, M, C, U, and N denote permeability quality, motif prior, composition alignment, uncertainty stability, and novelty, respectively. Equal-order weights were used to avoid letting any single term dominate by construction, while the ablation experiments remove each term or constraint to assess sensitivity. Novelty against the training set was measured by exact HELM matching and nearest-neighbor token Jaccard similarity:"),
        para("{J(A,B) = |A intersect B| / |A union B|.}    (5)"),
        heading("3.5 Candidate Validation", 2),
        para("Generated candidates were evaluated using exact novelty against the training set, uniqueness, pairwise Jaccard diversity, quality-diversity tradeoff, generator ablation, uncertainty summaries, source-heterogeneity analysis, 3D polarity proxy nearest-neighbor analysis, and token/descriptor-space novelty depth. These analyses were designed to reduce the risk that the shortlist simply reproduces training-set neighbors or exploits a poorly calibrated scorer."),
        para("Calibration was assessed using Brier score and expected calibration error (ECE) on held-out predictions. Confidence intervals for prediction metrics were computed by nonparametric bootstrap with 1000 resamples. Route-level quality and diversity comparisons used bootstrap confidence intervals with 4000 resamples and permutation tests with 6000 permutations. Nearest-neighbor novelty was reported both in token space and standardized descriptor space so that exact HELM novelty would not be overinterpreted as complete chemical novelty."),
        heading("3.6 Implementation and Reproducibility", 2),
        para("All analyses were implemented as executable Python scripts in the project directory. Core scripts include train_public_baseline.py, train_enhanced_predictor.py, train_hybrid_predictor.py, run_descriptor_model_benchmark.py, run_loso_random_forest.py, optimize_cyclic_peptides.py, generate_de_novo_peptides.py, run_generator_ablation.py, compute_metric_confidence_intervals.py, compute_design_statistics.py, analyze_source_heterogeneity.py, and analyze_candidate_novelty_depth.py. Result tables were exported to Result/final_experiment_tables and figures to Result/paper_figures. The repository should include exact package versions and a short reproduction command sequence before submission."),
        heading("4. Results", 1),
        heading("4.1 Dataset and Protocol Summary", 2),
    ]
    els.append(para("Table 1. Dataset and evaluation protocol summary.", bold=True))
    els.append(table([
        ["Item", "Value"],
        ["Length-six peptides", str(n_samples)],
        ["Sources", str(len(sources))],
        ["Year range", f"{y_min}-{y_max}"],
        ["Positive threshold", "Permeability >= -6.0"],
        ["Positive rate", f"{pos_rate:.3f}"],
        ["Permeability distribution", f"{mean(perms):.3f} +/- {pstdev(perms):.3f}; range {min(perms):.2f} to {max(perms):.2f}"],
        ["Random split", f"{rnd['train_samples']} train / {rnd['test_samples']} test"],
        ["Source split", f"{src['train_samples']} train / {src['test_samples']} test"],
    ]))
    els += [
        para("This first experiment establishes the data regime and evaluation protocol before any model comparison. We report sample counts, source counts, threshold definition, and split sizes because these quantities determine whether a random split is likely to be representative. The goal is not to optimize a model in this section, but to show why source-aware validation is required."),
        para("The dataset is highly source-imbalanced. The largest source contributes nearly half of the length-six subset, and the second largest source contributes another large fraction; together, 2020_Townsend and 2016_Furukawa account for approximately 81% of the length-six dataset. This structure can make random splits optimistic and can also make any single source split sensitive to which source is held out. We therefore interpret source-aware results as a stress test of distribution shift rather than as a definitive estimate for every future assay condition."),
        heading("4.2 Prediction Performance and Source Shift", 2),
    ]
    els.append(para("The prediction experiment asks whether models that perform well under random splitting remain reliable when entire literature sources are held out. We therefore compare random split, source split, group-CV, and LOSO-style results. The same permeability threshold (-6.0) was used for classification across protocols, while regression metrics were computed on the original permeability values."))
    els.append(image_paragraph(rids["figure2b_roc_pr_curves.png"], "ROC and PR curves", 1, cy=3000000))
    els.append(para("Figure 1. ROC and precision-recall curves for the hybrid classifier under random and source-aware splits. The curves visualize the discrimination gap that is summarized numerically in Tables 2 and 3."))
    els.append(para("Table 2. Compact prediction summary.", bold=True))
    els.append(table([
        ["Model", "Setting", "RMSE", "R2", "AUROC"],
        ["Public baseline", "random", "0.945", "0.277", "0.773"],
        ["Enhanced predictor", "random", "0.877", "0.376", "0.839"],
        ["Enhanced predictor", "source", "1.340", "-0.771", "0.663"],
        ["Hybrid predictor", "random", fmt_ci(ci["hybrid_random_split"]["regression"]["rmse"]), fmt_ci(ci["hybrid_random_split"]["regression"]["r2"]), fmt_ci(ci["hybrid_random_split"]["classification"]["auroc"])],
        ["Hybrid predictor", "source", fmt_ci(ci["hybrid_source_split"]["regression"]["rmse"]), fmt_ci(ci["hybrid_source_split"]["regression"]["r2"]), fmt_ci(ci["hybrid_source_split"]["classification"]["auroc"])],
        ["Descriptor RF", "group CV", "0.943", "0.073", "0.725"],
    ]))
    els.append(para("Table 3. Classification operating-point metrics.", bold=True))
    els.append(table([
        ["Model", "Setting", "Accuracy", "F1", "MCC"],
        ["Public baseline", "random", "0.705", "0.767", ""],
        ["Enhanced predictor", "random", "0.751", "0.812", ""],
        ["Hybrid predictor", "random", f"{rnd['classification']['hybrid']['accuracy']:.3f}", fmt_ci(ci["hybrid_random_split"]["classification"]["f1"]), fmt_ci(ci["hybrid_random_split"]["classification"]["mcc"])],
        ["Hybrid predictor", "source", f"{src['classification']['hybrid']['accuracy']:.3f}", fmt_ci(ci["hybrid_source_split"]["classification"]["f1"]), fmt_ci(ci["hybrid_source_split"]["classification"]["mcc"])],
        ["Descriptor RF", "group CV", "0.725", "0.803", "0.264"],
    ]))
    els.append(para("Table 4. Feature-group ablation under repeated source-aware group splits.", bold=True))
    els.append(table(read_feature_ablation_rows()))
    els.append(para("The ablation results show that descriptor-only models outperform text-only HELM TF-IDF features under source-aware repeated group splits. Adding text features did not consistently improve AUROC over descriptor-only features, suggesting that public physicochemical and composition descriptors carry most of the robust signal in this length-six subset. Feature importance from the LOSO descriptor Random Forest further emphasized lipophilicity, polarity, QED-related features, and 3DPSA proxy terms."))
    els.append(para("Table 5. Top LOSO Random Forest descriptor importances.", bold=True))
    els.append(table(read_top_feature_rows()))
    els += [
        para(f"The hybrid model achieved AUROC={rnd['classification']['hybrid']['auroc']:.3f} on the random split, but source-aware AUROC dropped to {src['classification']['hybrid']['auroc']:.3f}. This gap is the key empirical warning of the study. The classifier still produced high recall in the source split, but balanced accuracy and MCC were weak, showing that candidate probabilities should be interpreted as prioritization scores rather than experimental guarantees."),
        para(f"LOSO analysis also showed substantial source heterogeneity. The strict-source AUROC weighted mean was {loso_auc['weighted_mean']:.3f}, with mean {loso_auc['mean']:.3f} and standard deviation {loso_auc['std']:.3f}. Performance variation was therefore not a minor sampling artifact."),
    ]
    els.append(image_paragraph(rids["figure11_source_heterogeneity.png"], "Source heterogeneity", 2, cy=3300000))
    els.append(para("Figure 2. Leave-one-source-out source heterogeneity. The wide range of source-level AUROC values indicates that held-out-source performance depends strongly on experimental source."))
    els += [
        heading("4.3 Calibration and Reliability Checks", 2),
        para("Because the design stages use model scores to prioritize candidates, the next experiment examines whether predicted probabilities are reasonably calibrated. This analysis is not intended to prove experimental success; it quantifies whether probability-like outputs are safe to use as ranking signals and whether additional uncertainty penalties are necessary."),
        para("Table 6. Added calibration summary for hybrid classifier probabilities.", bold=True),
        table([
            ["Split", "N", "Positive rate", "Mean predicted prob.", "Brier score", "ECE"],
            ["Random", "434", "0.687", "0.627", "0.146", "0.080"],
            ["Source", "1105", "0.776", "0.708", "0.176", "0.086"],
        ]),
        para("The calibration analysis was added because generated candidates are selected by a learned scorer. The Brier and ECE values suggest that probabilities are usable for ranking and filtering, but they should not be read as calibrated experimental success probabilities. For this reason, the design pipeline combines predicted permeability with uncertainty penalties, diversity constraints, and novelty analysis."),
        heading("4.4 Dual-Route Design Results", 2),
    ]
    els.append(image_paragraph(rids["figure3_generation.png"], "Design route overview", 3, cy=3300000))
    els.append(para("Figure 3. Generated candidate profiles for the optimization and de novo routes."))
    els.append(para("Table 7. Optimization and de novo generation summary.", bold=True))
    els.append(table([
        ["group", "N", "diversity", "pred. perm. mean [95% CI]", "prob. mean [95% CI]"],
        ["optimized_shortlist", "12", "0.554", bootstrap_mean_ci([r["predicted_permeability"] for r in opt_rows], seed=1), bootstrap_mean_ci([r["predicted_positive_prob"] for r in opt_rows], seed=2)],
        ["de_novo_shortlist", "24", "0.705", bootstrap_mean_ci([r["predicted_permeability"] for r in denovo_rows], seed=3), bootstrap_mean_ci([r["predicted_positive_prob"] for r in denovo_rows], seed=4)],
    ]))
    els.append(para("Table 8. Candidate composition summary.", bold=True))
    els.append(table(select_csv_columns(
        RESULT_DIR / "final_experiment_tables" / "table2_generation_summary.csv",
        ["group", "uniqueness", "novelty_vs_train", "mean_natural_ratio", "mean_n_methyl_ratio", "mean_d_ratio"],
        {"group": "group", "uniqueness": "unique", "novelty_vs_train": "exact novelty", "mean_natural_ratio": "natural", "mean_n_methyl_ratio": "N-methyl", "mean_d_ratio": "D-ratio"},
    )))
    els += [
        para(f"Both design routes produced exact-HELM non-duplicates relative to the training set. The optimized shortlist contains 12 candidates and reflects local scaffold exploitation, whereas the de novo shortlist contains 24 candidates and maintains broader exploration. These numbers are intentionally small because the paper reports a priority shortlist rather than all generated molecules: the optimization route generated {int(float(opt_summary['generated_candidates'])):,} candidates, retained {int(float(opt_summary['filtered_candidates']))} filtered candidates and {int(float(opt_summary['diverse_top_candidates']))} diverse high-confidence candidates before selecting 12 composition-unique representatives; the de novo route sampled {int(float(denovo_summary['global_samples'])):,} initial sequences, produced {int(float(denovo_summary['stage1_candidates'])):,} stage-1 candidates, {int(float(denovo_summary['stage2_candidates'])):,} refinement candidates, and 120 final candidates before selecting 24 composition-unique representatives. The optimized route achieved a higher mean predicted permeability, while the de novo route retained higher pairwise diversity."),
    ]
    els.append(image_paragraph(rids["figure8_quality_diversity.png"], "Quality diversity", 4, cy=3300000))
    els.append(para("Figure 4. Quality-diversity tradeoff. The optimization route emphasizes high-confidence local improvement, while the de novo route covers a broader candidate region."))
    els += [
        heading("4.5 Generator Ablation", 2),
        para("The ablation experiment tests whether the de novo generator is simply selecting the highest predicted score or whether the multi-objective terms change the chemical profile of the shortlist. Each ablated variant removes one design pressure while keeping the same candidate-count target and downstream filtering protocol."),
        para("Table 9. Multi-objective generator ablation.", bold=True),
        table(select_csv_columns(
            RESULT_DIR / "final_experiment_tables" / "table4_generator_ablation.csv",
            ["variant", "pairwise_jaccard_diversity", "mean_perm_quality", "mean_motif_score", "mean_composition_alignment", "mean_uncertainty_stability"],
            {"variant": "variant", "pairwise_jaccard_diversity": "diversity", "mean_perm_quality": "quality mean", "mean_motif_score": "motif mean", "mean_composition_alignment": "composition mean", "mean_uncertainty_stability": "stability mean"},
        )),
        para("For the full-vs-ablation comparisons, route-level bootstrap/permutation analysis showed that adding composition constraints significantly improved composition alignment relative to no_composition (mean difference 0.175, 95% CI [0.077, 0.276], p=0.0010), while the full model improved composition alignment relative to quality_only (mean difference 0.212, 95% CI [0.124, 0.304], p=0.0002). These intervals support the conclusion that the added terms change the shortlist profile rather than only re-ranking candidates by a single quality score."),
        para("The quality-only variant achieved higher raw quality but reduced composition alignment and uncertainty stability. The full generator did not maximize a single metric; instead, it balanced quality, motif prior, composition, stability, and novelty. This supports the interpretation that the de novo route is not merely a score maximizer."),
    ]
    els.append(image_paragraph(rids["figure9_generator_ablation.png"], "Generator ablation", 5, cy=3300000))
    els.append(para("Figure 5. Generator ablation across quality, diversity, motif, composition, and stability terms."))
    els += [
        heading("4.6 Mechanistic Proxies and Novelty Depth", 2),
        para("The final validation experiment asks whether generated peptides are chemically plausible and whether exact novelty hides near-duplicate behavior. We therefore combine token- and descriptor-space novelty depth with a lightweight 3D polarity-proxy sanity check. The EPSA literature supports exposed polarity as a useful permeability surrogate for cyclic peptides, especially when comparing broad polarity regimes or discrete design-cycle trends, but the proxy values here should not be treated as experimental permeability measurements."),
        para("Descriptor-shift and 3D polarity-proxy analyses showed that both generated groups remained near the physicochemical neighborhood of high-permeability reference peptides. This analysis is reported as a sanity check that the shortlist does not move into an obviously unfavorable polarity region; the main novelty and route-difference evidence comes from the token/descriptor nearest-neighbor analysis below."),
        para("Table 10. 3D polarity proxy nearest-neighbor sanity check.", bold=True),
        table(read_csv_rows(RESULT_DIR / "final_experiment_tables" / "table6_conformation_proxy_neighbors.csv")),
        para("The optimized and de novo candidates have similar nearest-neighbor CHCl3_3DPSA, H2O_3DPSA, and EPSA values. We therefore use Table 10 only to rule out gross polarity drift, not to rank the two design routes mechanistically."),
        para("Table 11. Deep novelty analysis.", bold=True),
        table(select_csv_columns(
            RESULT_DIR / "final_experiment_tables" / "table6d_novelty_depth.csv",
            ["route", "count", "mean_nearest_train_token_jaccard", "mean_nearest_descriptor_distance"],
            {"route": "route", "count": "N", "mean_nearest_train_token_jaccard": "mean token Jaccard", "mean_nearest_descriptor_distance": "mean descriptor distance"},
        )),
        para("Exact HELM novelty was 1.0 for both shortlists. However, deep novelty analysis clarified the difference between the routes: optimized candidates had high nearest-neighbor token similarity, consistent with local refinement, whereas de novo candidates showed lower token similarity and larger descriptor distances. Cases with maximum token Jaccard or minimum descriptor distance equal to one or zero should therefore be interpreted as near-neighbor novelty rather than complete chemical dissimilarity."),
    ]
    els.append(image_paragraph(rids["figure12_novelty_depth.png"], "Novelty depth", 6, cy=3000000))
    els.append(para("Figure 6. Nearest-neighbor novelty depth against the training set."))
    els += [
        heading("4.7 Representative Case Analysis", 2),
        para("A representative optimized candidate can be summarized as cyclo(Me_dV-meL-meL-meA-F-P), derived from cyclo(Me_dV-dF-meL-dP-F-P). The key substitutions dF to meL and dP to meA increased predicted permeability by 0.471 while preserving a locally related scaffold. This illustrates the exploitation role of constrained optimization."),
        para("A representative de novo candidate can be summarized as cyclo(Me_dA-Nle-meL-P-meL-F), with predicted permeability -4.479 and predicted positive probability 0.996. Although it is not an exact copy of a training HELM string, its descriptor profile remains close to the high-permeability region, supporting the idea of motif-guided recombination."),
    ]
    els.append(image_paragraph(rids["figure13_case_study_panels.png"], "Representative cases", 7, cy=3300000))
    els.append(para("Figure 7. Representative case analysis for local optimization and de novo generation."))
    els += [
        heading("5. Discussion", 1),
        para("The central message of this study is that cyclic peptide permeability design should be evaluated under source-aware conditions before generated candidates are trusted. The random-split hybrid model appears strong, but the source split and LOSO results reveal a substantial reliability gap. Rather than hiding this gap, the framework uses it to motivate uncertainty-aware candidate filtering and conservative interpretation."),
        para("The source-aware performance drop is also the main limitation of using a learned scorer for design. In this manuscript, the scorer is therefore embedded in a safety-net workflow: uncertainty penalties reduce reliance on unstable predictions, diversity filtering prevents shortlist collapse, exact and nearest-neighbor novelty checks reduce training-set copying, and 3D polarity-proxy analysis tests whether candidates remain near permeability-favorable physicochemical neighborhoods. These safeguards do not replace experimental validation, but they make the design stage more defensible than using the predictor alone."),
        para("The two design routes serve different medicinal-chemistry needs. Constrained optimization is suitable when a known permeable scaffold is available and the goal is to propose limited modifications. De novo generation is more useful when broader exploration is desired, but it requires stronger downstream filtering. Combining both routes allows the shortlist to contain both low-risk analogs and more exploratory candidates."),
        para("The candidate composition is also relevant to experimental feasibility. The optimized shortlist has a mean natural residue ratio of 0.556, mean N-methylation ratio of 0.278, and mean D-residue ratio of 0.167, whereas the de novo shortlist has corresponding values of 0.340, 0.451, and 0.076. These values are within the range commonly explored in synthetic cyclic peptide optimization, where N-methylation, D-amino acids, and non-natural residues are routinely used to tune permeability and proteolytic stability. The shortlist size is also deliberate: a wet-lab follow-up would normally test tens rather than thousands of cyclic peptide analogs, so the 12 and 24 candidate sets are meant as experimentally manageable priority lists. However, the current study does not estimate synthesis cost, protecting-group compatibility, stereochemical purity, or purification difficulty. Comparison to classical orally absorbed cyclic peptides such as cyclosporin A should therefore be qualitative: our candidates are smaller length-six scaffolds designed for prioritization, not experimentally established oral drugs."),
        para("This study also clarifies the meaning of novelty. Exact HELM novelty is necessary but insufficient, because a generated peptide may still be a near-neighbor of a training peptide. Reporting both exact novelty and nearest-neighbor novelty depth gives a more honest view of how far candidates move from the training distribution."),
        para("Mechanistic interpretation remains intentionally conservative. The current 3DPSA/EPSA-style proxy analysis provides only a neighborhood-level indication of polarity behavior. Future work should combine the generated candidates with explicit molecular dynamics simulations in aqueous and membrane-like environments to examine chameleonic conformational behavior, intramolecular hydrogen bonding, and solvent-exposed polarity changes. Such simulations would provide a stronger mechanistic bridge between descriptor-level prioritization and wet-lab permeability assays."),
        heading("6. Limitations", 1),
        para("First, the study focuses on length-six cyclic peptides. This choice controls the design space but limits direct generalization to shorter or longer peptides. Second, the work remains computational and lacks PAMPA, Caco-2, cellular uptake, or target-engagement validation. The generated shortlists should therefore be viewed as prioritized candidates rather than confirmed permeable molecules. Third, the scorer still loses performance under source shift, indicating that future work should incorporate richer 3D/4D conformational ensembles, experimental-condition metadata, or external validation sets. Fourth, the calibration analysis reduces but does not eliminate uncertainty in probability-based ranking. Fifth, HELM tokenization provides a practical macromolecular representation but can underrepresent stereochemical subtleties, conformational ensembles, and context-dependent side-chain shielding. Sixth, the binary threshold of -6.0 follows a pragmatic permeability cutoff, but threshold sensitivity was not exhaustively explored; future work should report continuous regression, multiple classification thresholds, and assay-specific decision boundaries."),
        heading("7. Conclusions", 1),
        para("We developed a public and reproducible source-aware workflow for membrane-permeable cyclic peptide prediction and design. The framework combines descriptor-guided robust prediction, constrained optimization, multi-objective de novo generation, uncertainty-aware filtering, and multi-layer candidate validation. The results show that random-split performance overstates practical reliability, while source-aware evaluation provides a more useful basis for design. The final shortlists should be carried forward to higher-fidelity conformational modeling and experimental validation."),
        heading("List of Abbreviations", 1),
        para("AUROC: area under the receiver operating characteristic curve; ECE: expected calibration error; HELM: hierarchical editing language for macromolecules; LOSO: leave-one-source-out; MCC: Matthews correlation coefficient; RF: Random Forest; TPSA: topological polar surface area."),
        heading("Declarations", 1),
        heading("Availability of Data and Materials", 2),
        para("All data and scripts used to generate this manuscript are contained in the accompanying project directory. The reconstructed dataset is stored at dataset/CycPeptMPDB_Peptide_Length_6.csv. Prediction, design, ablation, heterogeneity, novelty, and figure-generation scripts are stored in the main directory. Result tables and figures are stored under the Result directory. Code and processed data will be made available at: [GitHub repository URL to be inserted before submission]. The repository should include a README, environment file, license, and commands required to reproduce the tables and figures."),
        heading("Competing Interests", 2),
        para("The authors declare no competing interests, unless updated before submission."),
        heading("Funding", 2),
        para("This work was supported by the Liaoning Province Nature Fund Project (No. 2022-MS-291); the National Foreign Expert Project Plan (G2022006008L); and the Scientific Research Project of Liaoning Province Education Department (LJKMZ20220781, LJKMZ20220783)."),
        heading("Authors' Contributions", 2),
        para("Yuxing Shen conceived and supervised the study. Shiqian Han performed data curation, model implementation, computational experiments, result analysis, and manuscript drafting. Honghui An contributed to workflow implementation, validation, and figure/table preparation. Jun Wang contributed to project supervision, interpretation of results, and manuscript revision. All authors read and approved the final manuscript."),
        heading("Acknowledgements", 2),
        para("The authors thank Shenyang University of Chemical Technology for research support."),
        heading("References", 1),
    ]
    refs = [
        "1. White CJ, Yudin AK. Contemporary strategies for peptide macrocyclization. Nature Chemistry. 2011;3:509-524. doi:10.1038/nchem.1062.",
        "2. Muttenthaler M, King GF, Adams DJ, Alewood PF. Trends in peptide drug discovery. Nature Reviews Drug Discovery. 2021;20:309-325. doi:10.1038/s41573-020-00135-8.",
        "3. Zorzi A, Deyle K, Heinis C. Cyclic peptide therapeutics: past, present and future. Current Opinion in Chemical Biology. 2017;38:24-29. doi:10.1016/j.cbpa.2017.02.006.",
        "4. Nielsen DS, Shepherd NE, Xu W, Lucke AJ, Stoermer MJ, Fairlie DP. Orally absorbed cyclic peptides. Chemical Reviews. 2017;117:8094-8128. doi:10.1021/acs.chemrev.6b00838.",
        "5. Naylor MR, Bockus AT, Blanco MJ, Lokey RS. Cyclic peptide natural products chart the frontier of oral bioavailability in the pursuit of undruggable targets. Current Opinion in Chemical Biology. 2017;38:141-147. doi:10.1016/j.cbpa.2017.04.012.",
        "6. Rezai T, Yu B, Millhauser GL, Jacobson MP, Lokey RS. Testing the conformational hypothesis of passive membrane permeability using synthetic cyclic peptide diastereomers. Journal of the American Chemical Society. 2006;128:2510-2511. doi:10.1021/ja0563455.",
        "7. Rezai T, Bock JE, Zhou MV, Kalyanaraman C, Lokey RS, Jacobson MP. Conformational flexibility, internal hydrogen bonding, and passive membrane permeability: successful in silico prediction of the relative permeabilities of cyclic peptides. Journal of the American Chemical Society. 2006;128:14073-14080. doi:10.1021/ja063076p.",
        "8. Chatterjee J, Gilon C, Hoffman A, Kessler H. N-methylation of peptides: a new perspective in medicinal chemistry. Accounts of Chemical Research. 2008;41:1331-1342. doi:10.1021/ar8000603.",
        "9. Over B, Matsson P, Tyrchan C, Artursson P, Doak BC, Foley MA, Hilgendorf C, Johnston SE, Lee MD IV, Lewis RJ, McCarren P, Muncipinto G, Norinder U, Perry MWD, Duvall JR, Kihlberg J. Structural and conformational determinants of macrocycle cell permeability. Nature Chemical Biology. 2016;12:1065-1074. doi:10.1038/nchembio.2203.",
        "10. Walport LJ, Obexer R, Suga H. Strategies for transitioning macrocyclic peptides to cell-permeable drug leads. Current Opinion in Biotechnology. 2017;48:242-250. doi:10.1016/j.copbio.2017.07.007.",
        "11. Whitty A, Zhong M, Viarengo L, Beglov D, Hall DR, Vajda S. Quantifying the chameleonic properties of macrocycles and other high-molecular-weight drugs. Drug Discovery Today. 2016;21:712-717. doi:10.1016/j.drudis.2016.02.005.",
        "12. Li J, Yanagisawa K, Sugita M, Fujie T, Ohue M, Akiyama Y. CycPeptMPDB: a comprehensive database of membrane permeability of cyclic peptides. Journal of Chemical Information and Modeling. 2023;63:2240-2250. doi:10.1021/acs.jcim.2c01573.",
        "13. Yu Y, Gu M, Guo H, Deng Y, Chen D, Wang J, Wang C, Liu X, Yan W, Huang J. MuCoCP: a priori chemical knowledge-based multimodal contrastive learning pre-trained neural network for the prediction of cyclic peptide membrane penetration ability. Bioinformatics. 2024;40:btae473. doi:10.1093/bioinformatics/btae473.",
        "14. Cao L, Xu Z, Shang T, Zhang C, Wu X, Wu Y, Zhai S, Zhan Z, Duan H. Multi_CycGT: a deep learning-based multimodal model for predicting the membrane permeability of cyclic peptides. Journal of Medicinal Chemistry. 2024;67:1888-1899. doi:10.1021/acs.jmedchem.3c01611.",
        "15. Wang Z, Chen Y, Shang Y, Yang X, Pan W, Ye X, Sakurai T, Zeng X. MultiCycPermea: accurate and interpretable prediction of cyclic peptide permeability using a multimodal image-sequence model. BMC Biology. 2025;23:63. doi:10.1186/s12915-025-02166-2.",
        "16. Liu W, Li J, Verma CS, Lee HK. Systematic benchmarking of 13 AI methods for predicting cyclic peptide membrane permeability. Journal of Cheminformatics. 2025;17:129. doi:10.1186/s13321-025-01083-4.",
        "17. Sheridan RP. Time-split cross-validation as a method for estimating the goodness of prospective prediction. Journal of Chemical Information and Modeling. 2013;53:783-790. doi:10.1021/ci400084k.",
        "18. Hill TA, Lohman RJ, Hoang HN, Nielsen DS, Scully CCG, Kok WM, Liu L, Lucke AJ, Stoermer MJ, Schroeder CI, Chaousis S, Colless B, Bernhardt PV, Edmonds DJ, Griffith DA, Rotter CJ, Ruggeri RB, Price DA, Liras S, Craik DJ, Fairlie DP. Cyclic penta- and hexaleucine peptides without N-methylation are orally absorbed. ACS Medicinal Chemistry Letters. 2014;5:1148-1151. doi:10.1021/ml5002823.",
        "19. Liras S, McClure KF. Permeability of cyclic peptide macrocycles and cyclotides and their potential as therapeutics. ACS Medicinal Chemistry Letters. 2019;10:1026-1032. doi:10.1021/acsmedchemlett.9b00149.",
        "20. Bhardwaj G, O'Connor J, Rettie S, Huang YH, Ramelot TA, Mulligan VK, Alpkilic GG, Palmer J, Bera AK, Bick MJ, Di Piazza M, Li X, Hosseinzadeh P, Craven TW, Tejero R, Lauko A, Choi R, Glynn C, Dong L, Griffin R, van Voorhis WC, Rodriguez J, Stewart L, Montelione GT, Craik D, Baker D. Accurate de novo design of membrane-traversing macrocycles. Cell. 2022;185:3520-3532.e26. doi:10.1016/j.cell.2022.07.019.",
        "21. Yu Y, Zhang Z, Guo H, Ren X, Zhang Y, Meng J, Zhou Y, Han J, Tian J, Yan W, Huang J. AI-driven de novo design of customizable membrane permeable cyclic peptides. Journal of Computer-Aided Molecular Design. 2025;39:63. doi:10.1007/s10822-025-00639-8.",
        "22. Aerts R, Tavernier J, Kerstjens A, Ahmad M, Gómez-Tamayo JC, Tresadern G, De Winter H. C2PO: an ML-powered optimizer of the membrane permeability of cyclic peptides through chemical modification. Journal of Cheminformatics. 2025;17:168. doi:10.1186/s13321-025-01109-x.",
    ]
    for ref_idx, ref_text in enumerate(refs, start=1):
        ref_text = re.sub(r"^\d+\.\s*", "", ref_text)
        els.append(para(f"[{ref_idx}] {ref_text}"))
    return els


def build_docx():
    if not TEMPLATE.exists():
        raise FileNotFoundError(TEMPLATE)

    image_files = [
        "figure2b_roc_pr_curves.png",
        "figure11_source_heterogeneity.png",
        "figure3_generation.png",
        "figure8_quality_diversity.png",
        "figure9_generator_ablation.png",
        "figure12_novelty_depth.png",
        "figure13_case_study_panels.png",
    ]

    file_map = {}
    with zipfile.ZipFile(TEMPLATE, "r") as zin:
        for item in zin.infolist():
            file_map[item.filename] = zin.read(item.filename)

    doc_root = ET.fromstring(file_map["word/document.xml"])
    body = doc_root.find(w("body"))
    sect = body.find(w("sectPr"))
    for child in list(body):
        body.remove(child)

    rels_root = ET.fromstring(file_map["word/_rels/document.xml.rels"])
    existing_ids = {r.attrib["Id"] for r in rels_root.findall(rel("Relationship"))}
    rid_num = 900
    rids = {}
    for image_file in image_files:
        while f"rId{rid_num}" in existing_ids:
            rid_num += 1
        rid = f"rId{rid_num}"
        rid_num += 1
        target = f"media/sci_{image_file}"
        image_path = RESULT_DIR / "paper_figures" / image_file
        if not image_path.exists():
            raise FileNotFoundError(image_path)
        file_map[f"word/{target}"] = image_path.read_bytes()
        ET.SubElement(rels_root, rel("Relationship"), {
            "Id": rid,
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
            "Target": target,
        })
        rids[image_file] = rid

    footer_rid = None
    if SOURCE_INFO_DOC.exists():
        with zipfile.ZipFile(SOURCE_INFO_DOC, "r") as src_zip:
            footer_entry = src_zip.getinfo("word/footer1.xml")
            file_map["word/footer1.xml"] = src_zip.read(footer_entry)
            source_doc = ET.fromstring(src_zip.read("word/document.xml"))
            source_body = source_doc.find(w("body"))
            source_sect = source_body.find(w("sectPr")) if source_body is not None else None
            if source_sect is not None:
                sect = copy.deepcopy(source_sect)
        while f"rId{rid_num}" in existing_ids:
            rid_num += 1
        footer_rid = f"rId{rid_num}"
        ET.SubElement(rels_root, rel("Relationship"), {
            "Id": footer_rid,
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer",
            "Target": "footer1.xml",
        })

    for el in manuscript_elements(rids):
        body.append(el)
    if sect is not None:
        if footer_rid:
            for old_ref in list(sect.findall(w("footerReference"))):
                sect.remove(old_ref)
            sect.insert(0, ET.Element(w("footerReference"), {w("type"): "default", tag(NS_R, "id"): footer_rid}))
        body.append(sect)

    file_map["word/document.xml"] = ET.tostring(doc_root, encoding="utf-8", xml_declaration=True)
    file_map["word/_rels/document.xml.rels"] = ET.tostring(rels_root, encoding="utf-8", xml_declaration=True)

    ct_root = ET.fromstring(file_map["[Content_Types].xml"])
    has_png = any(e.attrib.get("Extension") == "png" for e in ct_root.findall(tag(NS_CT, "Default")))
    if not has_png:
        ET.SubElement(ct_root, tag(NS_CT, "Default"), {"Extension": "png", "ContentType": "image/png"})
        file_map["[Content_Types].xml"] = ET.tostring(ct_root, encoding="utf-8", xml_declaration=True)

    tmp = OUT_PATH.with_suffix(".tmp.docx")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in file_map.items():
            zout.writestr(name, data)
    shutil.move(tmp, OUT_PATH)
    print(f"Saved SCI revision to: {OUT_PATH}")


if __name__ == "__main__":
    build_docx()
