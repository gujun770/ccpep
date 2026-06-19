import copy
import re
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
NS_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
NS_A = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS_PIC = "http://schemas.openxmlformats.org/drawingml/2006/picture"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"

ET.register_namespace("w", NS_W)
ET.register_namespace("r", NS_R)
ET.register_namespace("wp", NS_WP)
ET.register_namespace("a", NS_A)
ET.register_namespace("pic", NS_PIC)


def w_tag(tag: str) -> str:
    return f"{{{NS_W}}}{tag}"


def wp_tag(tag: str) -> str:
    return f"{{{NS_WP}}}{tag}"


def a_tag(tag: str) -> str:
    return f"{{{NS_A}}}{tag}"


def pic_tag(tag: str) -> str:
    return f"{{{NS_PIC}}}{tag}"


def rel_tag(tag: str) -> str:
    return f"{{{NS_REL}}}{tag}"


def first_text(element) -> str:
    return "".join(t.text or "" for t in element.findall(".//" + w_tag("t")))


def add_text_run(paragraph, text: str, bold: bool = False, size: int | None = None):
    run = ET.SubElement(paragraph, w_tag("r"))
    if bold or size:
        rpr = ET.SubElement(run, w_tag("rPr"))
        if bold:
            ET.SubElement(rpr, w_tag("b"))
        if size:
            ET.SubElement(rpr, w_tag("sz"), {w_tag("val"): str(size)})
            ET.SubElement(rpr, w_tag("szCs"), {w_tag("val"): str(size)})
    text_node = ET.SubElement(run, w_tag("t"))
    if text.startswith(" ") or text.endswith(" "):
        text_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    text_node.text = text
    return run


def make_paragraph(text: str = "", style: str | None = None, align: str | None = None):
    p = ET.Element(w_tag("p"))
    if style or align:
        ppr = ET.SubElement(p, w_tag("pPr"))
        if style:
            ET.SubElement(ppr, w_tag("pStyle"), {w_tag("val"): style})
        if align:
            ET.SubElement(ppr, w_tag("jc"), {w_tag("val"): align})
    if text:
        add_text_run(p, text)
    return p


def copy_paragraph(paragraph):
    return copy.deepcopy(paragraph)


def numeric_text(value: str) -> str:
    value = value.strip()
    if not value:
        return value
    if re.fullmatch(r"-?\d+\.\d{4,}", value):
        rounded = f"{float(value):.3f}".rstrip("0").rstrip(".")
        return rounded
    return value


def standardize_table(tbl):
    rows = tbl.findall(w_tag("tr"))
    max_cols = 0
    for row in rows:
        max_cols = max(max_cols, len(row.findall(w_tag("tc"))))
    if max_cols == 0:
        return

    tbl_pr = tbl.find(w_tag("tblPr"))
    if tbl_pr is None:
        tbl_pr = ET.Element(w_tag("tblPr"))
        tbl.insert(0, tbl_pr)

    for child in list(tbl_pr):
        if child.tag in {
            w_tag("tblW"),
            w_tag("tblLayout"),
            w_tag("tblBorders"),
            w_tag("jc"),
        }:
            tbl_pr.remove(child)

    ET.SubElement(tbl_pr, w_tag("tblW"), {w_tag("w"): "5000", w_tag("type"): "pct"})
    ET.SubElement(tbl_pr, w_tag("tblLayout"), {w_tag("type"): "fixed"})
    ET.SubElement(tbl_pr, w_tag("jc"), {w_tag("val"): "center"})

    borders = ET.SubElement(tbl_pr, w_tag("tblBorders"))
    ET.SubElement(borders, w_tag("top"), {w_tag("val"): "single", w_tag("sz"): "12", w_tag("space"): "0", w_tag("color"): "000000"})
    ET.SubElement(borders, w_tag("left"), {w_tag("val"): "nil"})
    ET.SubElement(borders, w_tag("bottom"), {w_tag("val"): "single", w_tag("sz"): "12", w_tag("space"): "0", w_tag("color"): "000000"})
    ET.SubElement(borders, w_tag("right"), {w_tag("val"): "nil"})
    ET.SubElement(borders, w_tag("insideH"), {w_tag("val"): "nil"})
    ET.SubElement(borders, w_tag("insideV"), {w_tag("val"): "nil"})

    total_width = 9000
    cell_width = str(total_width // max_cols)

    tbl_grid = tbl.find(w_tag("tblGrid"))
    if tbl_grid is not None:
        tbl.remove(tbl_grid)
    tbl_grid = ET.Element(w_tag("tblGrid"))
    for _ in range(max_cols):
        ET.SubElement(tbl_grid, w_tag("gridCol"), {w_tag("w"): cell_width})
    tbl.insert(1, tbl_grid)

    for row_idx, row in enumerate(rows):
        for tc in row.findall(w_tag("tc")):
            tc_pr = tc.find(w_tag("tcPr"))
            if tc_pr is None:
                tc_pr = ET.SubElement(tc, w_tag("tcPr"))
            for child in list(tc_pr):
                if child.tag in {w_tag("tcW"), w_tag("tcBorders"), w_tag("vAlign")}:
                    tc_pr.remove(child)
            ET.SubElement(tc_pr, w_tag("tcW"), {w_tag("w"): cell_width, w_tag("type"): "dxa"})
            ET.SubElement(tc_pr, w_tag("vAlign"), {w_tag("val"): "center"})
            if row_idx == 0:
                tc_borders = ET.SubElement(tc_pr, w_tag("tcBorders"))
                ET.SubElement(tc_borders, w_tag("bottom"), {w_tag("val"): "single", w_tag("sz"): "8", w_tag("space"): "0", w_tag("color"): "000000"})

            for p in tc.findall(w_tag("p")):
                ppr = p.find(w_tag("pPr"))
                if ppr is None:
                    ppr = ET.SubElement(p, w_tag("pPr"))
                if ppr.find(w_tag("jc")) is None:
                    ET.SubElement(ppr, w_tag("jc"), {w_tag("val"): "center"})
                for t in p.findall(".//" + w_tag("t")):
                    t.text = numeric_text(t.text or "")


def next_relation_id(rels_root) -> str:
    ids = []
    for rel in rels_root.findall(rel_tag("Relationship")):
        rid = rel.attrib.get("Id", "")
        if rid.startswith("rId"):
            try:
                ids.append(int(rid[3:]))
            except ValueError:
                pass
    return f"rId{max(ids, default=0) + 1}"


def add_image_relationship(rels_root, target: str) -> str:
    rid = next_relation_id(rels_root)
    ET.SubElement(
        rels_root,
        rel_tag("Relationship"),
        {
            "Id": rid,
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
            "Target": target,
        },
    )
    return rid


def make_drawing_paragraph(rel_id: str, name: str, cx: int = 5400000, cy: int = 3600000):
    p = make_paragraph(align="center")
    run = ET.SubElement(p, w_tag("r"))
    drawing = ET.SubElement(run, w_tag("drawing"))
    inline = ET.SubElement(drawing, wp_tag("inline"), {"distT": "0", "distB": "0", "distL": "0", "distR": "0"})
    ET.SubElement(inline, wp_tag("extent"), {"cx": str(cx), "cy": str(cy)})
    ET.SubElement(inline, wp_tag("docPr"), {"id": "99", "name": name})
    graphic = ET.SubElement(inline, a_tag("graphic"))
    graphic_data = ET.SubElement(graphic, a_tag("graphicData"), {"uri": "http://schemas.openxmlformats.org/drawingml/2006/picture"})
    pic = ET.SubElement(graphic_data, pic_tag("pic"))
    nv_pic_pr = ET.SubElement(pic, pic_tag("nvPicPr"))
    ET.SubElement(nv_pic_pr, pic_tag("cNvPr"), {"id": "0", "name": name})
    ET.SubElement(nv_pic_pr, pic_tag("cNvPicPr"))
    blip_fill = ET.SubElement(pic, pic_tag("blipFill"))
    ET.SubElement(blip_fill, a_tag("blip"), {f"{{{NS_R}}}embed": rel_id})
    stretch = ET.SubElement(blip_fill, a_tag("stretch"))
    ET.SubElement(stretch, a_tag("fillRect"))
    sp_pr = ET.SubElement(pic, pic_tag("spPr"))
    xfrm = ET.SubElement(sp_pr, a_tag("xfrm"))
    ET.SubElement(xfrm, a_tag("off"), {"x": "0", "y": "0"})
    ET.SubElement(xfrm, a_tag("ext"), {"cx": str(cx), "cy": str(cy)})
    prst = ET.SubElement(sp_pr, a_tag("prstGeom"), {"prst": "rect"})
    ET.SubElement(prst, a_tag("avLst"))
    return p


def insert_before(body, index: int, element):
    body.insert(index, element)


def replace_paragraph_text(body, startswith_text: str, new_text: str):
    for p in body.findall(w_tag("p")):
        text = first_text(p).strip()
        if text.startswith(startswith_text):
            for child in list(p):
                p.remove(child)
            ppr = ET.SubElement(p, w_tag("pPr"))
            ET.SubElement(ppr, w_tag("pStyle"), {w_tag("val"): "Normal"})
            add_text_run(p, new_text)
            return True
    return False


def replace_or_insert_after(body, anchor_startswith: str, new_text: str):
    children = list(body)
    for idx, p in enumerate(children):
        if p.tag == w_tag("p") and first_text(p).strip().startswith(anchor_startswith):
            body.insert(idx + 1, make_paragraph(new_text))
            return True
    return False


def helm_to_cyclo(helm: str) -> str:
    match = re.search(r"\{(.+?)\}", str(helm))
    if not match:
        return str(helm)
    tokens = [token.strip().strip("[]") for token in match.group(1).split(".")]
    return "cyclo(" + "-".join(tokens) + ")"


def clean_mutation_description(desc: str) -> str:
    if not isinstance(desc, str) or not desc:
        return ""
    parts = []
    for item in desc.split(";"):
        item = item.strip()
        match = re.match(r"(\d+):(.+?)->(.+)", item)
        if not match:
            continue
        pos = int(match.group(1)) + 1
        parts.append(f"第{pos}位 {match.group(2)}→{match.group(3)}")
    return "；".join(parts) if parts else desc


def build_case_paragraphs():
    case_df = pd.read_csv(RESULT_DIR / "case_analysis" / "representative_cases_compact.csv")
    case_df = case_df.round(3)
    opt_case = case_df.loc[case_df["route"] == "optimized"].head(1).iloc[0]
    de_case = case_df.loc[case_df["route"] == "de_novo"].head(1).iloc[0]
    opt_candidate = helm_to_cyclo(opt_case["candidate_helm"])
    opt_parent = helm_to_cyclo(opt_case["parent_helm"])
    de_candidate = helm_to_cyclo(de_case["candidate_helm"])
    mutation_text = clean_mutation_description(opt_case["mutation_description"])

    texts = [
        (
            "4.5 代表性案例分析",
            "Heading2",
        ),
        (
            "为了补足统计结果之外的化学直觉展示，本文进一步选取优化路线与 de novo 路线中的代表候选进行案例分析。图13展示了优化路线中的 parent→candidate 替换、de novo 候选与最近高渗透参考肽之间的关系，以及关键描述符偏移情况。",
            None,
        ),
        (
            f"在优化路线中，代表候选可简写为 {opt_candidate}，其 parent 为 {opt_parent}。"
            f"该候选的预测渗透性相对 parent 提升 {opt_case['improvement']:.3f}，关键替换为 {mutation_text}。"
            "这一结果说明模型并非简单追求序列差异最大化，而是倾向于在保留高质量骨架的前提下，通过引入更有利于疏水/甲基化平衡的单体来完成局部精修。完整 HELM 表达建议放入补充表。",
            None,
        ),
        (
            f"在 de novo 路线中，代表候选可简写为 {de_candidate}，其预测 permeability 为 "
            f"{de_case['predicted_permeability']:.3f}，预测正类概率为 {de_case['predicted_positive_prob']:.3f}。"
            "虽然该候选不直接继承训练集模板，但其组成与描述符特征向高渗透参考肽邻域靠拢，体现出围绕高渗透 motif 的合理重组而非训练样本拷贝。",
            None,
        ),
    ]
    return texts


def build_novelty_paragraph():
    summary = pd.read_csv(RESULT_DIR / "candidate_novelty_depth" / "summary.csv").round(3)
    opt = summary.loc[summary["route"] == "optimized_shortlist"].iloc[0]
    de = summary.loc[summary["route"] == "de_novo_shortlist"].iloc[0]
    text = (
        f"深层新颖性分析进一步表明，optimized 候选与训练集最近邻的 token Jaccard 平均值约为 "
        f"{opt['mean_nearest_train_token_jaccard']:.3f}，平均描述符距离约为 "
        f"{opt['mean_nearest_descriptor_distance']:.3f}；de novo 候选对应数值分别为 "
        f"{de['mean_nearest_train_token_jaccard']:.3f} 和 {de['mean_nearest_descriptor_distance']:.3f}。"
        "这说明两条路线并非做同一件事：前者更接近局部精修，后者则在合理化学邻域内保持了更远的新颖性。"
    )
    return text


def build_source_paragraph():
    het = pd.read_csv(RESULT_DIR / "source_heterogeneity" / "heterogeneity_summary.csv").round(3)
    auroc_row = het.loc[het["metric"] == "cls_auroc"].iloc[0]
    corr = pd.read_csv(RESULT_DIR / "source_heterogeneity" / "correlation_summary.csv").round(3)
    corr_row = corr.loc[corr["metric"] == "cls_auroc"].iloc[0]
    text = (
        f"来源异质性分析显示，LOSO 设定下 AUROC 的加权均值约为 {auroc_row['weighted_mean']:.3f}，"
        f"不同来源之间的范围从 {auroc_row['min']:.3f} 到 {auroc_row['max']:.3f}。"
        f"与此同时，AUROC 与来源样本量对数的相关仅为 {corr_row['corr_with_log_test_samples']:.3f}，"
        "说明跨来源难度并不能简单归因于样本量大小，而是真实存在明显的来源异质性。"
    )
    return text


def main():
    template = PROJECT_ROOT / "初稿.docx"
    target = PROJECT_ROOT / "二稿.docx"
    fallback_target = PROJECT_ROOT / "二稿_更新版.docx"
    polished_target = PROJECT_ROOT / "二稿_投稿精修版.docx"
    polished_fallback_target = PROJECT_ROOT / "二稿_投稿精修版_v2.docx"
    figure13 = RESULT_DIR / "paper_figures" / "figure13_case_study_panels.png"

    if not template.exists():
        raise FileNotFoundError(f"Template not found: {template}")
    if not figure13.exists():
        raise FileNotFoundError(f"Figure not found: {figure13}")

    actual_target = polished_target
    try:
        shutil.copyfile(template, actual_target)
    except PermissionError:
        actual_target = polished_fallback_target
        shutil.copyfile(template, actual_target)

    with zipfile.ZipFile(actual_target, "r") as zin:
        file_map = {item.filename: zin.read(item.filename) for item in zin.infolist()}

    doc_root = ET.fromstring(file_map["word/document.xml"])
    rels_root = ET.fromstring(file_map["word/_rels/document.xml.rels"])
    body = doc_root.find(w_tag("body"))

    # Standardize all existing tables and shorten numeric text.
    for tbl in body.findall(".//" + w_tag("tbl")):
        standardize_table(tbl)

    # Soften related-work wording: cite prior work without negative judgment.
    replace_paragraph_text(
        body,
        "尽管这些工作推动了该方向的发展",
        "尽管这些工作推动了环肽膜渗透性研究从性质预测走向候选设计，但当前公开研究在评价设定、可复现实现与结果展示层面仍存在进一步完善空间。特别是，随着该领域逐渐从预测迈向设计，如何在公开数据条件下建立可复现、可比较、且具备跨来源泛化能力的研究框架，正成为一个更加重要的问题。",
    )
    replace_paragraph_text(
        body,
        "基于上述问题",
        "基于此，本文将研究重点放在公开数据条件下的可复现预测与设计流程构建上。我们基于 CycPeptMPDB 重建长度为 6 的环肽渗透性数据集，系统比较多种预测器在更严格的 cross-source 场景下的稳健性，并进一步提出两条互补的设计路线：基于模板的受约束优化与显式多目标 de novo 生成。相比单纯比较 random split 分数，本文更关注跨来源泛化、候选新颖性与设计结果的化学合理性。",
    )
    replace_paragraph_text(
        body,
        "在稳健评分器基础上，本文进一步提出双路线设计策略",
        "在稳健评分器基础上，本文进一步提出双路线设计策略：其一是围绕高质量 seed 进行受约束优化，以获得高置信、低风险的局部改良候选；其二是通过显式多目标 de novo 生成进行更大范围的组合探索。两条路线分别对应 exploitation 与 exploration，并最终通过不确定性、多样性与新颖性约束完成统一筛选。",
    )
    replace_paragraph_text(
        body,
        "描述符偏移分析和 3D 极性代理分析表明",
        "描述符偏移分析和 3D 极性代理分析表明，优化路线与 de novo 路线虽然在搜索方式上不同，但都在向高渗透参考样本的物化区域靠拢。前者更强调对已有模板的定向修正，后者则更强调围绕高渗透 motif 的合理重组与探索。",
    )
    replace_paragraph_text(
        body,
        "本文围绕膜渗透环肽设计问题",
        "本文围绕膜渗透环肽设计问题，构建了一套基于公开数据的可复现计算框架。与仅追求 random split 高分或仅依赖复杂生成网络的工作不同，本文从 source-aware robust prediction 出发，进一步打通了 constrained optimization、de novo generation、统计检验与机制分析，形成了较完整的研究闭环。",
    )
    replace_paragraph_text(
        body,
        "尽管本文仍属于纯计算研究",
        "尽管本文仍属于纯计算研究，尚未引入湿实验验证或更高精度分子动力学模拟，但其优势在于数据公开、流程可复现、统计证据较完整，且对候选分子的化学合理性给出了多层次解释。后续工作可以在此基础上继续引入更丰富的 3D/4D 构象信息、外部实验验证或靶点导向的后续活性筛选。",
    )

    # Add a concise study-position paragraph after the introduction to improve paper tone.
    replace_or_insert_after(
        body,
        "与上述工作相比",
        "从研究定位上看，本文并不试图通过更换单一 backbone 来追求局部指标提升，而是更关注在公开条件下建立一套可复现、可扩展且对真实分布偏移更敏感的环肽膜渗透性设计流程。这一点也是本文与一般“只报随机划分高分”的工作最主要的区别。",
    )

    # Update/add a stronger source heterogeneity paragraph before the conclusion section.
    body_children = list(body)
    conclusion_idx = None
    for idx, child in enumerate(body_children):
        if child.tag == w_tag("p") and first_text(child).strip() == "结论":
            conclusion_idx = idx
            break
    if conclusion_idx is None:
        conclusion_idx = max(len(body_children) - 1, 0)

    insert_idx = conclusion_idx
    insert_before(body, insert_idx, make_paragraph(build_source_paragraph()))
    insert_idx += 1
    insert_before(body, insert_idx, make_paragraph(build_novelty_paragraph()))
    insert_idx += 1

    # Add figure13 relationship and media.
    figure_rid = add_image_relationship(rels_root, "media/figure13_case_study_panels.png")
    file_map["word/media/figure13_case_study_panels.png"] = figure13.read_bytes()

    # Insert case-study section before conclusion.
    for text, style in build_case_paragraphs():
        insert_before(body, insert_idx, make_paragraph(text, style=style))
        insert_idx += 1
    insert_before(body, insert_idx, make_drawing_paragraph(figure_rid, "figure13_case_study_panels", cx=5200000, cy=3600000))
    insert_idx += 1
    insert_before(body, insert_idx, make_paragraph("图13 代表性案例分析：优化路线 parent→candidate 替换、de novo 候选与最近高渗透参考肽对照，以及关键描述符偏移。", align="center"))
    insert_idx += 1

    # Keep result tables visually aligned by ensuring blank paragraph after each table.
    for idx, child in enumerate(list(body)):
        if child.tag == w_tag("tbl"):
            nxt = list(body)[idx + 1] if idx + 1 < len(list(body)) else None
            if nxt is None or nxt.tag != w_tag("p") or first_text(nxt).strip():
                body.insert(idx + 1, make_paragraph(""))

    file_map["word/document.xml"] = ET.tostring(doc_root, encoding="utf-8", xml_declaration=True)
    file_map["word/_rels/document.xml.rels"] = ET.tostring(rels_root, encoding="utf-8", xml_declaration=True)

    tmp = PROJECT_ROOT / "二稿_tmp.docx"
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name, data in file_map.items():
            zout.writestr(name, data)

    shutil.move(tmp, actual_target)
    print(f"Saved refined second draft docx to: {actual_target}")


if __name__ == "__main__":
    main()
