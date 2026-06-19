import copy
import shutil
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import RESULT_DIR


NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
ET.register_namespace("w", NS_W)
ET.register_namespace("r", NS_R)


def w_tag(tag):
    return f"{{{NS_W}}}{tag}"


def rel_tag(tag):
    return f"{{{NS_REL}}}{tag}"


def text_of(el):
    return "".join(t.text or "" for t in el.findall(".//" + w_tag("t"))).strip()


def add_run(p, text, bold=False, size=None):
    r = ET.SubElement(p, w_tag("r"))
    if bold or size:
        rpr = ET.SubElement(r, w_tag("rPr"))
        if bold:
            ET.SubElement(rpr, w_tag("b"))
        if size:
            ET.SubElement(rpr, w_tag("sz"), {w_tag("val"): str(size)})
            ET.SubElement(rpr, w_tag("szCs"), {w_tag("val"): str(size)})
    t = ET.SubElement(r, w_tag("t"))
    if text.startswith(" ") or text.endswith(" "):
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text


def para(text="", style=None, align=None, bold=False):
    p = ET.Element(w_tag("p"))
    if style or align:
        ppr = ET.SubElement(p, w_tag("pPr"))
        if style:
            ET.SubElement(ppr, w_tag("pStyle"), {w_tag("val"): style})
        if align:
            ET.SubElement(ppr, w_tag("jc"), {w_tag("val"): align})
    if text:
        add_run(p, text, bold=bold)
    return p


def make_table(df: pd.DataFrame):
    tbl = ET.Element(w_tag("tbl"))
    tbl_pr = ET.SubElement(tbl, w_tag("tblPr"))
    ET.SubElement(tbl_pr, w_tag("tblW"), {w_tag("w"): "5000", w_tag("type"): "pct"})
    ET.SubElement(tbl_pr, w_tag("tblLayout"), {w_tag("type"): "fixed"})
    borders = ET.SubElement(tbl_pr, w_tag("tblBorders"))
    ET.SubElement(borders, w_tag("top"), {w_tag("val"): "single", w_tag("sz"): "12", w_tag("space"): "0", w_tag("color"): "000000"})
    ET.SubElement(borders, w_tag("left"), {w_tag("val"): "nil"})
    ET.SubElement(borders, w_tag("bottom"), {w_tag("val"): "single", w_tag("sz"): "12", w_tag("space"): "0", w_tag("color"): "000000"})
    ET.SubElement(borders, w_tag("right"), {w_tag("val"): "nil"})
    ET.SubElement(borders, w_tag("insideH"), {w_tag("val"): "nil"})
    ET.SubElement(borders, w_tag("insideV"), {w_tag("val"): "nil"})

    ncols = len(df.columns)
    width = str(9000 // max(ncols, 1))
    grid = ET.SubElement(tbl, w_tag("tblGrid"))
    for _ in range(ncols):
        ET.SubElement(grid, w_tag("gridCol"), {w_tag("w"): width})

    def cell(value, header=False):
        tc = ET.Element(w_tag("tc"))
        tc_pr = ET.SubElement(tc, w_tag("tcPr"))
        ET.SubElement(tc_pr, w_tag("tcW"), {w_tag("w"): width, w_tag("type"): "dxa"})
        if header:
            tc_borders = ET.SubElement(tc_pr, w_tag("tcBorders"))
            ET.SubElement(tc_borders, w_tag("bottom"), {w_tag("val"): "single", w_tag("sz"): "8", w_tag("space"): "0", w_tag("color"): "000000"})
        p = ET.SubElement(tc, w_tag("p"))
        ppr = ET.SubElement(p, w_tag("pPr"))
        ET.SubElement(ppr, w_tag("jc"), {w_tag("val"): "center"})
        add_run(p, str(value), bold=header, size=18)
        return tc

    tr = ET.SubElement(tbl, w_tag("tr"))
    for col in df.columns:
        tr.append(cell(col, header=True))
    for _, row in df.iterrows():
        tr = ET.SubElement(tbl, w_tag("tr"))
        for col in df.columns:
            val = row[col]
            if isinstance(val, float):
                val = f"{val:.3f}".rstrip("0").rstrip(".")
            tr.append(cell(val))
    return tbl


def find_idx(children, exact=None, starts=None):
    for i, el in enumerate(children):
        if el.tag != w_tag("p"):
            continue
        txt = text_of(el)
        if exact is not None and txt == exact:
            return i
        if starts is not None and txt.startswith(starts):
            return i
    return None


def replace_range(body, start_idx, end_idx, elements):
    for _ in range(end_idx - start_idx):
        body.remove(list(body)[start_idx])
    for offset, el in enumerate(elements):
        body.insert(start_idx + offset, el)


def standardize_existing_tables(body):
    for tbl in body.findall(".//" + w_tag("tbl")):
        tbl_pr = tbl.find(w_tag("tblPr"))
        if tbl_pr is None:
            tbl_pr = ET.Element(w_tag("tblPr"))
            tbl.insert(0, tbl_pr)
        for child in list(tbl_pr):
            if child.tag in {w_tag("tblW"), w_tag("tblLayout")}:
                tbl_pr.remove(child)
        ET.SubElement(tbl_pr, w_tag("tblW"), {w_tag("w"): "5000", w_tag("type"): "pct"})
        ET.SubElement(tbl_pr, w_tag("tblLayout"), {w_tag("type"): "fixed"})
        for t in tbl.findall(".//" + w_tag("t")):
            txt = t.text or ""
            try:
                if "." in txt and len(txt.split(".")[-1]) > 3:
                    t.text = f"{float(txt):.3f}".rstrip("0").rstrip(".")
            except ValueError:
                pass


def replace_embedded_figures(file_map, rels_root):
    mapping = {
        "figure1_workflow": "figure1_workflow.png",
        "figure2_prediction": "figure2_prediction.png",
        "figure11_source_heterogeneity": "figure11_source_heterogeneity.png",
        "figure3_generation": "figure3_generation.png",
        "figure8_quality_diversity": "figure8_quality_diversity.png",
        "figure9_generator_ablation": "figure9_generator_ablation.png",
        "figure10_statistical_summary": "figure10_statistical_summary.png",
        "figure6_conformation_proxy": "figure6_conformation_proxy.png",
        "figure12_novelty_depth": "figure12_novelty_depth.png",
        "figure13_case_study_panels": "figure13_case_study_panels.png",
    }
    rel_by_id = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels_root.findall(rel_tag("Relationship"))}
    doc_root = ET.fromstring(file_map["word/document.xml"])
    for drawing in doc_root.findall(".//" + w_tag("drawing")):
        doc_pr = drawing.find(".//{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr")
        blip = drawing.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip")
        if doc_pr is None or blip is None:
            continue
        name = doc_pr.attrib.get("name", "")
        if name not in mapping:
            continue
        rid = blip.attrib.get(f"{{{NS_R}}}embed")
        target = rel_by_id.get(rid)
        if not target:
            continue
        fig_path = RESULT_DIR / "paper_figures" / mapping[name]
        if fig_path.exists():
            file_map[f"word/{target}"] = fig_path.read_bytes()
    file_map["word/document.xml"] = ET.tostring(doc_root, encoding="utf-8", xml_declaration=True)


def abstract_elements():
    return [
        para("Background: 膜渗透性是限制环肽进入细胞内靶点和发挥药效的关键瓶颈。现有环肽渗透性研究已经从性质预测逐步走向候选设计，但随机划分评价可能高估模型能力，且生成候选的多样性、新颖性和化学合理性仍需更系统的验证。", "Normal"),
        para("Methods: 本文基于公开 CycPeptMPDB 数据库构建主链长度为 6 的膜渗透性环肽数据集，并整合 HELM token 特征、peptide-level 理化描述符、monomer-level 聚合描述符、天然/非天然组成比例、N-甲基化比例和 D-单体比例等多层特征。预测阶段比较 TF-IDF 线性模型、增强描述符模型、混合模型和 descriptor-based RandomForest，并在 random split、source split、repeated group CV 和 LOSO 设置下评估泛化能力。在设计阶段，本文进一步构建 constrained optimization 和 multi-objective de novo generation 两条路线，并通过 uncertainty、diversity、novelty 和 motif/composition 约束进行候选筛选。", "Normal"),
        para("Results: Hybrid predictor 在 random split 下达到 AUROC=0.846，但在更严格的 source-aware 设置下性能下降至约 AUROC=0.625，说明跨来源泛化是该任务的关键难点。descriptor-based RandomForest 在 repeated group CV 下取得 AUROC=0.725，表现出更稳健的跨来源趋势。设计结果方面，优化路线得到 12 条完全新颖候选，平均预测 permeability 为 -4.511；de novo 路线得到 24 条完全新颖候选，平均预测 permeability 为 -4.725。进一步的生成器消融、质量-多样性分析、3D polarity proxy、来源异质性和深层新颖性分析共同表明，两条设计路线分别承担 exploitation 与 exploration 功能。", "Normal"),
        para("Conclusions: 本文提出了一套公开、可复现、来源感知的环肽膜渗透性预测与设计框架。该框架不仅能够生成高置信候选，还能通过多层统计和机制代理分析解释候选的化学合理性，为后续环肽从头设计和实验验证提供了可扩展基础。", "Normal"),
    ]


def related_work_elements():
    return [
        para("关于环肽膜渗透性的计算研究可分为数据库构建、性质预测、生成式设计和评估基准四条主线。CycPeptMPDB 为环肽膜渗透性建模提供了关键公开数据基础，其整理的 HELM 表达、单体信息和渗透性标签使得可复现建模成为可能[1]。在该数据库基础上，后续研究逐渐从单一序列建模扩展到图结构、分子描述符和多模态表示。", "Normal"),
        para("在性质预测方面，早期工作多依赖序列 token、分子指纹或常规理化描述符。MuCoCP 等方法开始引入多尺度表示以预测环肽膜渗透性[2]；Multi_CycGT 进一步探索了图 Transformer 对环肽结构信息的利用[3]。这些工作证明机器学习能够捕捉环肽渗透性相关模式，但许多结果主要在随机划分或同分布测试上报告，难以充分反映跨实验来源的泛化难度。", "Normal"),
        para("近期 MultiCycPermea 将图像和序列信息结合，在 CycPeptMPDB 上报告了较强的同分布预测性能，并强调了可解释性分析的重要性[4]。与此同时，系统 benchmark 研究比较了多类 AI 方法在环肽渗透性任务中的表现，指出图模型和更严格的分布外评估是该方向的重要趋势[5]。这些结果共同提示：仅比较 random split 指标并不足以判断模型在真实应用中的可靠性。", "Normal"),
        para("在设计与优化方面，AI-driven cyclic peptide design 和 C2PO 等工作表明，环肽渗透性研究已从性质预测走向候选优化和生成[6,7]。这类工作的重要贡献在于将 scorer 与候选搜索结合起来，但也对后续研究提出了更高要求：生成候选不仅要高分，还需要具备新颖性、多样性、可解释性和可追踪的评价链。", "Normal"),
        para("与上述研究相比，本文的定位不是单纯提出一个更复杂的 backbone，而是在公开数据条件下构建一套 source-aware、可复现、可扩展的预测与设计流程。本文同时报告 random split、source split、repeated group CV 与 LOSO 结果，并将优化式设计和 de novo 生成纳入同一框架，通过消融、置信区间、来源异质性、3D polarity proxy 和深层新颖性分析解释候选的可靠性。", "Normal"),
        para("因此，本文的主要补充在于将稳健预测、双路线设计和多层验证整合到一个公开可复现流程中，为后续环肽膜渗透性设计研究提供更清晰的评价基准和候选筛选策略。", "Normal"),
    ]


def limitations_elements():
    return [
        para("局限性", "Heading1"),
        para("首先，本文为了控制长度差异和生成空间复杂度，主要聚焦于主链长度为 6 的环肽子集，因此当前结论是否能够直接推广到更长或更短的环肽仍需进一步验证。后续工作可以在长度分层或条件生成框架中扩展该方法。", "Normal"),
        para("其次，本文仍属于纯计算研究，尚未开展 PAMPA、Caco-2 或细胞摄取等湿实验验证。因此，本文得到的 optimized shortlist 和 de novo shortlist 应被视为优先候选，而不是已经实验确认的高渗透分子。", "Normal"),
        para("第三，source-aware 评估显示模型在跨来源场景下仍存在明显性能下降。该结果一方面证明了本文强调跨来源泛化的必要性，另一方面也提示当前 descriptor-guided scorer 仍需结合更丰富的 3D/4D 构象信息、实验条件建模或外部验证集来进一步提升泛化能力。", "Normal"),
    ]


def references_elements():
    refs = [
        "[1] Li J, Yanagisawa K, Sugita M, et al. CycPeptMPDB: a comprehensive database of membrane permeability of cyclic peptides. Journal of Chemical Information and Modeling, 2023, 63(7): 2240-2250. DOI: 10.1021/acs.jcim.2c01573.",
        "[2] Yu et al. MuCoCP: accurate prediction of cyclic peptide membrane permeability. Bioinformatics, 2024. DOI: 10.1093/bioinformatics/btae473.",
        "[3] Cao L, Xu Z, Shang T, et al. Multi_CycGT: a deep learning-based multimodal model for predicting the membrane permeability of cyclic peptides. 2024.",
        "[4] Wang Z, Chen Y, Shang Y, et al. MultiCycPermea: accurate and interpretable prediction of cyclic peptide permeability using a multimodal image-sequence model. BMC Biology, 2025, 23: 63. DOI: 10.1186/s12915-025-02166-2.",
        "[5] Liu W, Li J, Verma C S, et al. Systematic benchmarking of 13 AI methods for predicting cyclic peptide membrane permeability. Journal of Cheminformatics, 2025, 17: 129. DOI: 10.1186/s13321-025-01083-4.",
        "[6] Yunxiang et al. AI-driven de novo design of customizable membrane permeable cyclic peptides. Journal of Computer-Aided Molecular Design, 2025. DOI: 10.1007/S10822-025-00639-8.",
        "[7] Aerts R, Tavernier J, Kerstjens A, et al. C2PO: an ML-powered optimizer of the membrane permeability of cyclic peptides through chemical modification. Journal of Cheminformatics, 2025, 17: 168. DOI: 10.1186/s13321-025-01109-x.",
        "[8] Rezai T, Bock J E, Zhou M V, et al. Conformational flexibility, internal hydrogen bonding, and passive membrane permeability of cyclic peptides. Journal of the American Chemical Society, 2006.",
        "[9] Chatterjee J, Gilon C, Hoffman A, Kessler H. N-methylation of peptides: a new perspective in medicinal chemistry. Accounts of Chemical Research, 2008.",
        "[10] Nielsen D S, Shepherd N E, Xu W, et al. Orally absorbed cyclic peptides. Chemical Reviews, 2017.",
    ]
    return [para("参考文献", "Heading1")] + [para(ref, "Normal") for ref in refs]


def replace_table5(body):
    children = list(body)
    cap_idx = find_idx(children, starts="表5")
    if cap_idx is None:
        return
    table_idx = None
    for idx in range(cap_idx + 1, len(children)):
        if children[idx].tag == w_tag("tbl"):
            table_idx = idx
            break
    if table_idx is None:
        return

    raw = pd.read_csv(RESULT_DIR / "generator_ablation" / "summary.csv")
    slim = raw[[
        "variant",
        "final_count",
        "pairwise_jaccard_diversity",
        "mean_perm_quality",
        "mean_motif_score",
        "mean_composition_alignment",
        "mean_uncertainty_stability",
        "mean_predicted_positive_prob",
    ]].copy()
    slim.columns = ["Variant", "N", "Diversity", "Quality", "Motif", "Composition", "Stability", "Positive prob."]
    slim = slim.round(3)
    body.remove(children[table_idx])
    body.insert(table_idx, make_table(slim))
    body.insert(table_idx + 1, para("表5仅保留生成器消融中最能支撑方法结论的关键指标。完整版本可放入补充材料。结果显示，full 版本并非在单一质量指标上机械取最优，而是在 motif prior、composition alignment 与 uncertainty stability 之间取得更均衡的折中。", "Normal"))


def main():
    base = PROJECT_ROOT / "二稿_投稿精修版_v2.docx"
    if not base.exists():
        base = max(PROJECT_ROOT.glob("*.docx"), key=lambda p: p.stat().st_mtime)
    out = PROJECT_ROOT / "三稿_投稿修改版.docx"
    shutil.copyfile(base, out)

    with zipfile.ZipFile(out, "r") as zin:
        file_map = {item.filename: zin.read(item.filename) for item in zin.infolist()}

    rels_root = ET.fromstring(file_map["word/_rels/document.xml.rels"])
    replace_embedded_figures(file_map, rels_root)

    root = ET.fromstring(file_map["word/document.xml"])
    body = root.find(w_tag("body"))
    children = list(body)

    # Structured abstract.
    abs_idx = find_idx(children, exact="摘要")
    key_idx = find_idx(children, starts="关键词")
    if abs_idx is not None and key_idx is not None and key_idx > abs_idx:
        replace_range(body, abs_idx + 1, key_idx, abstract_elements())

    # Expanded related work.
    children = list(body)
    rel_idx = find_idx(children, exact="相关工作")
    method_idx = find_idx(children, exact="方法")
    if rel_idx is not None and method_idx is not None and method_idx > rel_idx:
        replace_range(body, rel_idx + 1, method_idx, related_work_elements())

    # Add more analytical text after table-rich parts.
    children = list(body)
    idx = find_idx(children, starts="表3 优化路线")
    if idx is not None:
        body.insert(idx + 2, para("从表3可以看出，两条路线都达到 novelty=1.0 和 uniqueness=1.0，但其角色并不相同：optimized route 更适合围绕已知高质量模板进行局部精修，de novo route 则以略低的预测渗透性换取更高的探索空间覆盖。这种差异使二者可以形成互补，而不是简单竞争。", "Normal"))

    replace_table5(body)

    # Limitations before conclusion.
    children = list(body)
    conc_idx = find_idx(children, exact="结论")
    if conc_idx is not None:
        for offset, el in enumerate(limitations_elements()):
            body.insert(conc_idx + offset, el)

    # References before final sectPr.
    children = list(body)
    sect_idx = len(children) - 1
    if children and children[-1].tag == w_tag("sectPr"):
        sect_idx = len(children) - 1
    for offset, el in enumerate(references_elements()):
        body.insert(sect_idx + offset, el)

    standardize_existing_tables(body)
    file_map["word/document.xml"] = ET.tostring(root, encoding="utf-8", xml_declaration=True)

    tmp = PROJECT_ROOT / "三稿_投稿修改版_tmp.docx"
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name, data in file_map.items():
            zout.writestr(name, data)
    shutil.move(tmp, out)
    print(f"Saved review-revised manuscript to: {out}")


if __name__ == "__main__":
    main()
