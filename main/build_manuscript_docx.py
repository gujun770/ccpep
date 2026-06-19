import csv
import io
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULT_DIR = PROJECT_ROOT / "Result"
OUT_PATH = PROJECT_ROOT / "初稿.docx"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
}


def p(text="", style=None, bold=False, center=False, font_size=22):
    ppr = []
    if style:
        ppr.append(f'<w:pStyle w:val="{style}"/>')
    if center:
        ppr.append("<w:jc w:val=\"center\"/>")
    ppr_xml = f"<w:pPr>{''.join(ppr)}</w:pPr>" if ppr else ""
    rpr_bits = [f'<w:sz w:val="{font_size}"/>', f'<w:szCs w:val="{font_size}"/>']
    if bold:
        rpr_bits.append("<w:b/>")
    rpr = f"<w:rPr>{''.join(rpr_bits)}</w:rPr>"
    if text == "":
        run = "<w:r/>"
    else:
        run = f"<w:r>{rpr}<w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r>"
    return f"<w:p>{ppr_xml}{run}</w:p>"


def page_break():
    return "<w:p><w:r><w:br w:type=\"page\"/></w:r></w:p>"


def table_from_csv(path, title, max_rows=20):
    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            rows.append(row)
            if i >= max_rows:
                break
    if not rows:
        return p(f"{title}（表格为空）")

    def cell(text, header=False):
        text = "" if text is None else str(text)
        rpr = "<w:rPr><w:b/><w:sz w:val=\"18\"/><w:szCs w:val=\"18\"/></w:rPr>" if header else "<w:rPr><w:sz w:val=\"18\"/><w:szCs w:val=\"18\"/></w:rPr>"
        return (
            "<w:tc>"
            "<w:tcPr><w:tcW w:w=\"2400\" w:type=\"dxa\"/></w:tcPr>"
            "<w:p><w:pPr><w:jc w:val=\"center\"/></w:pPr>"
            f"<w:r>{rpr}<w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r></w:p>"
            "</w:tc>"
        )

    tbl_rows = []
    header = rows[0]
    tbl_rows.append("<w:tr>" + "".join(cell(c, header=True) for c in header) + "</w:tr>")
    for row in rows[1:]:
        tbl_rows.append("<w:tr>" + "".join(cell(c, header=False) for c in row) + "</w:tr>")

    tbl = (
        "<w:tbl>"
        "<w:tblPr>"
        "<w:tblStyle w:val=\"TableGrid\"/>"
        "<w:tblW w:w=\"0\" w:type=\"auto\"/>"
        "<w:tblBorders>"
        "<w:top w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"000000\"/>"
        "<w:left w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"000000\"/>"
        "<w:bottom w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"000000\"/>"
        "<w:right w:val=\"single\" w:sz=\"8\" w:space=\"0\" w:color=\"000000\"/>"
        "<w:insideH w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"999999\"/>"
        "<w:insideV w:val=\"single\" w:sz=\"4\" w:space=\"0\" w:color=\"999999\"/>"
        "</w:tblBorders>"
        "</w:tblPr>"
        + "".join(tbl_rows)
        + "</w:tbl>"
    )
    return p(title, center=True, font_size=20) + tbl


def image_paragraph(rid, name, cx=5200000, cy=3200000):
    return f"""
    <w:p>
      <w:pPr><w:jc w:val="center"/></w:pPr>
      <w:r>
        <w:drawing>
          <wp:inline distT="0" distB="0" distL="0" distR="0">
            <wp:extent cx="{cx}" cy="{cy}"/>
            <wp:docPr id="1" name="{escape(name)}"/>
            <a:graphic xmlns:a="{NS['a']}">
              <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
                <pic:pic xmlns:pic="{NS['pic']}">
                  <pic:nvPicPr>
                    <pic:cNvPr id="0" name="{escape(name)}"/>
                    <pic:cNvPicPr/>
                  </pic:nvPicPr>
                  <pic:blipFill>
                    <a:blip r:embed="{rid}"/>
                    <a:stretch><a:fillRect/></a:stretch>
                  </pic:blipFill>
                  <pic:spPr>
                    <a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
                    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
                  </pic:spPr>
                </pic:pic>
              </a:graphicData>
            </a:graphic>
          </wp:inline>
        </w:drawing>
      </w:r>
    </w:p>
    """


def build_document(image_map):
    parts = []
    parts.append(p("基于描述符引导的膜渗透环肽稳健预测与双路线设计框架", center=True, bold=True, font_size=30))
    parts.append(p("摘要", style="Heading1", bold=True, font_size=26))
    parts.append(
        p(
            "膜渗透性是限制环肽成药性的关键瓶颈之一。现有人工智能方法虽然已开始从性质预测走向分子设计，但公开代码往往依赖私有权重、缺失模拟特征或采用过于乐观的随机划分评估，导致可复现性和泛化可信度不足。本文基于公开的 CycPeptMPDB 数据库，构建了一套面向膜渗透环肽的可复现计算框架。首先，我们系统比较了文本特征模型、多视角增强模型和混合预测模型，并在 random split、source split、repeated group cross-validation 以及 leave-one-source-out 等更严格设置下评估其泛化能力。结果表明，Hybrid predictor 在随机划分下取得最高 AUROC=0.846，但跨来源泛化显著下降，说明 source-aware generalization 才是该任务的关键挑战。"
        )
    )
    parts.append(
        p(
            "在稳健评分器基础上，本文进一步提出双路线设计策略：其一是围绕高质量种子肽进行受约束优化，其二是基于显式多目标目标函数开展 de novo 生成。优化路线产生 12 条完全新颖的候选环肽，平均预测渗透值为 -4.511；de novo 路线产生 24 条完全新颖候选，平均预测渗透值为 -4.725，同时保持与高渗透参考集接近的多样性水平。通过生成器消融、质量—多样性分析、描述符机制分析、3D 极性代理验证、来源异质性分析以及深层新颖性分析，本文证明该框架并非简单的打分搜索，而是在利用与探索之间形成可解释平衡。本文工作为膜渗透环肽的公开可复现设计提供了一条具有较强工程可实施性和方法学价值的路线。"
        )
    )
    parts.append(p("关键词：环肽；膜渗透性；从头设计；跨来源泛化；多目标生成；描述符建模"))

    parts.append(p("引言", style="Heading1", bold=True, font_size=26))
    parts.append(
        p(
            "环肽兼具小分子和大分子的部分优势，通常具有较好的构象刚性、靶点适应能力和代谢稳定性，因此在蛋白—蛋白相互作用调控、肿瘤治疗和感染性疾病治疗中表现出重要潜力。然而，与线性肽和传统小分子相比，环肽普遍面临膜通透性不足的问题，这直接限制了其口服生物利用度和细胞内靶点可达性。如何在保持药效相关骨架的同时提高膜渗透能力，已经成为环肽药物设计中的核心问题。"
        )
    )
    parts.append(
        p(
            "近年来，随着深度学习和生成式人工智能的发展，研究者开始尝试利用机器学习模型对环肽渗透性进行预测，并进一步将其扩展到候选序列的优化和生成。然而，该方向仍存在三个现实困难。第一，现有公开工作中不少方法依赖作者私有的模型参数或分子动力学特征文件，导致严格复现困难。第二，很多研究只在随机划分上报告较高指标，忽视了不同实验来源之间的系统性偏差，从而高估了实际泛化能力。第三，设计环节往往仅强调生成分数较高的候选，而缺乏对新颖性、多样性、机制合理性和不确定性的系统分析。"
        )
    )
    parts.append(
        p(
            "基于上述问题，本文不再简单复现不完整的基线代码，而是围绕公开数据库重新构建一条可复现、可解释、可扩展的环肽渗透性设计流程。本文的核心思想是：先建立 source-aware 的稳健评分器，再在此基础上分别开展局部优化式设计和多目标 de novo 生成，并用一系列统计与机制分析证明候选分子并非训练集的简单拷贝。与仅做 predictor 提升或仅做生成搜索不同，本文试图把“稳健预测—双路线设计—机制验证—统计支撑”打通为一个完整的方法框架。"
        )
    )

    parts.append(p("相关工作", style="Heading1", bold=True, font_size=26))
    parts.append(
        p(
            "关于环肽膜渗透性的计算研究大体可以分为三类。第一类是性质预测方法，通常基于序列、图结构、理化描述符或构象代理信息建立回归或分类模型。这类方法的目标是给定一个环肽后，预测其是否具有较高膜渗透性。第二类是优化式设计方法，即从已有高质量模板出发，通过局部突变、替换或强化学习策略获得更优候选。第三类是从头生成方法，直接在定义好的单体空间中组合出新环肽，再借助评分器进行筛选。"
        )
    )
    parts.append(
        p(
            "现有研究虽然在随机划分下常能取得较高指标，但公开文献也已逐渐指出，环肽数据库具有明显来源异质性，不同研究中的实验体系、测量条件与样本分布存在显著差异。因此，仅依赖 random split 得到的性能并不足以代表真实应用场景。另一方面，很多设计类工作会使用复杂的生成网络或强化学习框架，但由于训练代价高、实现细节复杂、代码公开不完整，实际复现和复用难度较大。"
        )
    )
    parts.append(
        p(
            "与上述工作相比，本文有两点不同。第一，本文将 source-aware robust prediction 作为方法起点，而非直接追求随机划分上的最高分数。第二，本文同时保留局部优化和 de novo 生成两条设计路线，并将 novelty、diversity、composition alignment、uncertainty stability 等多个目标统一纳入分析框架。这样的设计更符合公开数据条件下的可复现研究需求，也更适合作为后续进一步引入 3D 信息或实验验证的基础。"
        )
    )

    parts.append(p("方法", style="Heading1", bold=True, font_size=26))
    parts.append(p("3.1 整体框架", style="Heading2", bold=True, font_size=24))
    parts.append(
        p(
            "本文方法框架如图1所示，整体由四部分组成：数据构建、稳健评分器训练、双路线候选设计以及候选过滤与分析。首先，从公开 CycPeptMPDB 数据库中筛选主链长度为 6 且带有 permeability 标注的环肽，构建统一工作数据集。随后，以该数据集为基础训练多种性质预测模型，并通过 source split、group CV 和 LOSO 等方式获得更可靠的性能评估。之后，在稳健评分器的指导下，同时开展基于高质量 seed 的受约束优化和面向高渗透 motif 的多目标 de novo 生成。最后，利用新颖性、多样性、不确定性、机制描述符和邻域代理分析，对候选分子进行逐层筛选。"
        )
    )
    parts.append(image_paragraph(image_map["figure1"], "figure1_workflow", cx=5600000, cy=1800000))
    parts.append(p("图1 公开可复现的环肽膜渗透性设计框架。", center=True, font_size=18))

    parts.append(p("3.2 数据集构建与特征表示", style="Heading2", bold=True, font_size=24))
    parts.append(
        p(
            "本文使用 CycPeptMPDB 的公开数据构建训练集。为减少长度差异带来的偏置，并与后续设计流程保持一致，本文选取主链长度为 6 的环肽子集，共得到 2168 条带 permeability 标注的样本。对于每条样本，我们保留其 HELM 表示、渗透性数值、来源文献和年份信息。"
        )
    )
    parts.append(
        p(
            "在特征表示方面，本文没有依赖私有的分子动力学时间序列，而是以公开单体描述符和聚合描述符为主。具体地，单体层面统计天然单体比例、N-甲基化比例、D-单体比例、芳香性比例等；肽分子层面则使用 MolWt、TPSA、MolLogP、qed、FractionCSP3、HeavyAtomCount、氢键受体/供体数、环数等聚合描述符。对于某些模型，我们还保留了基于 HELM 解析得到的序列 token 特征，从而支持文本分支与描述符分支的组合建模。"
        )
    )

    parts.append(p("3.3 稳健预测器", style="Heading2", bold=True, font_size=24))
    parts.append(
        p(
            "本文建立了三层预测体系。第一层是公开弱基线，即基于 TF-IDF 的文本表示与线性模型，用于提供最低可复现对照。第二层是增强预测器，将序列模式特征与理化描述符联合建模。第三层是混合预测器，将文本分支和数值描述符分支融合，作为随机划分下表现最好的模型。与此同时，考虑到来源差异会显著影响性能，本文并不把 random split 作为唯一评估标准，而是强调 source split、repeated group CV 和 LOSO。"
        )
    )

    parts.append(p("3.4 双路线设计策略", style="Heading2", bold=True, font_size=24))
    parts.append(
        p(
            "在设计阶段，本文采用两条互补路线。第一条路线是 constrained optimization，即从预测高分或真实高渗透的 seed 环肽出发，通过单点或双点替换生成局部候选，再利用渗透性评分器、改善幅度阈值和多样性过滤得到最终优化 shortlist。该路线更偏向 exploitation，适合从已知优质模板周围寻找低风险改造方案。"
        )
    )
    parts.append(
        p(
            "第二条路线是 de novo generation。本文没有直接使用复现困难的强化学习网络，而是提出显式多目标生成框架：先从高渗透 elite 集合中学习位置先验和全局单体分布，再在单体池中进行 guided sampling 与局部 refinement。生成候选的排序不再只依赖单一分数，而是综合 permeability quality、分类正类概率、motif 先验、组成对齐、uncertainty stability 和 novelty 形成 multi-objective score。"
        )
    )

    parts.append(p("3.5 候选筛选与统计分析", style="Heading2", bold=True, font_size=24))
    parts.append(
        p(
            "为避免候选列表退化为训练集近邻的简单拷贝，本文设计了多层筛选与分析机制。首先，在候选排序阶段引入 robust score、多样性约束和 composition 去重。其次，在结果评估阶段计算 novelty、uniqueness、pairwise Jaccard diversity、quality-diversity tradeoff，并利用 bootstrap 置信区间和 permutation test 进行统计比较。进一步地，本文还构建了机制分析、3D 极性代理分析、来源异质性分析以及深层新颖性分析，用于从不同角度验证候选的合理性。"
        )
    )

    parts.append(p("实验", style="Heading1", bold=True, font_size=26))
    parts.append(p("4.1 预测性能与跨来源泛化", style="Heading2", bold=True, font_size=24))
    parts.append(
        p(
            "表1给出了主要预测模型的核心结果。可以看到，纯 TF-IDF 基线在 random split 下只能获得中等水平表现；增强预测器和混合预测器则在随机划分上进一步提升，其中 Hybrid predictor 在 random split 下取得最高 AUROC=0.846。"
        )
    )
    parts.append(table_from_csv(RESULT_DIR / "final_experiment_tables" / "table1_prediction_and_baselines.csv", "表1 主要预测模型性能比较（截取核心结果）", max_rows=6))
    parts.append(image_paragraph(image_map["figure2"], "figure2_prediction", cx=5600000, cy=2200000))
    parts.append(p("图2 预测模型性能与描述符模型基准结果。", center=True, font_size=18))
    parts.append(
        p(
            "然而，bootstrap 置信区间和 source-aware 评估表明，random split 性能会明显高估实际泛化能力。Hybrid random-split AUROC 的均值为 0.845，但在 source split 下均值降至约 0.625，说明来源偏移才是该问题的关键难点。进一步地，LOSO 结果显示不同来源之间的性能波动很大，来源级 AUROC 范围从 0.167 到 1.000，这一跨度不可能仅由样本量差异解释。"
        )
    )
    parts.append(table_from_csv(RESULT_DIR / "final_experiment_tables" / "table7_confidence_intervals.csv", "表2 关键预测指标的 bootstrap 置信区间", max_rows=10))
    parts.append(image_paragraph(image_map["figure11"], "figure11_source_heterogeneity", cx=5600000, cy=3400000))
    parts.append(p("图3 留一来源评估下的来源异质性分析。", center=True, font_size=18))

    parts.append(p("4.2 双路线设计结果", style="Heading2", bold=True, font_size=24))
    parts.append(
        p(
            "在稳健评分器指导下，本文分别获得优化式候选和 de novo 候选。优化路线最终得到 12 条完全新颖的候选，平均预测渗透值为 -4.511；de novo 路线得到 24 条完全新颖候选，平均预测渗透值为 -4.725。两条路线在 novelty 和 uniqueness 上都达到 1.00，但在质量与多样性结构上存在明显差异。"
        )
    )
    parts.append(table_from_csv(RESULT_DIR / "final_experiment_tables" / "table2_generation_summary.csv", "表3 优化路线与 de novo 路线的生成结果概览", max_rows=10))
    parts.append(image_paragraph(image_map["figure3"], "figure3_generation", cx=5600000, cy=2200000))
    parts.append(p("图4 训练集、优化候选与 de novo 候选的生成结果画像。", center=True, font_size=18))
    parts.append(
        p(
            "质量—多样性分析进一步表明，优化路线更像 exploitation：它能够在保持较高置信度的同时输出更高质量的候选；de novo 路线更像 exploration：平均质量略低，但探索范围更广，且多样性接近高渗透参考集。两条路线并非互相替代，而是分别对应局部改良与全局探索两种设计需求。"
        )
    )
    parts.append(table_from_csv(RESULT_DIR / "final_experiment_tables" / "table3_quality_diversity.csv", "表4 不同候选集合的质量—多样性统计", max_rows=10))
    parts.append(image_paragraph(image_map["figure8"], "figure8_quality_diversity", cx=5600000, cy=2200000))
    parts.append(p("图5 优化路线与 de novo 路线的质量—多样性权衡。", center=True, font_size=18))

    parts.append(p("4.3 生成器消融与统计比较", style="Heading2", bold=True, font_size=24))
    parts.append(
        p(
            "为了验证 de novo 生成器不是简单的打分搜索器，本文对多目标生成器进行了系统消融。与仅保留 quality 的版本相比，完整生成器在 motif score、composition alignment 和 uncertainty stability 上表现出更平衡的结果；与去掉组成约束或 motif 项的版本相比，full 版本并不在所有指标上绝对占优，但能在质量、稳定性和组成合理性之间维持更好的整体折中。这一结果说明本文提出的多目标生成器并非在单一指标上“刷分”，而是形成了可解释的多目标平衡机制。"
        )
    )
    parts.append(table_from_csv(RESULT_DIR / "final_experiment_tables" / "table4_generator_ablation.csv", "表5 多目标生成器消融结果", max_rows=10))
    parts.append(image_paragraph(image_map["figure9"], "figure9_generator_ablation", cx=5600000, cy=2400000))
    parts.append(p("图6 多目标生成器消融结果。", center=True, font_size=18))
    parts.append(image_paragraph(image_map["figure10"], "figure10_statistical_summary", cx=5600000, cy=3200000))
    parts.append(p("图7 双路线设计与生成器消融的统计比较。", center=True, font_size=18))

    parts.append(p("4.4 机制分析、代理验证与深层新颖性分析", style="Heading2", bold=True, font_size=24))
    parts.append(
        p(
            "描述符偏移分析和 3D 极性代理分析表明，优化路线和 de novo 路线虽然走向不同，但都在朝高渗透参考样本的物化区域靠近。前者更强调对已有模板的定向修正，后者更倾向于围绕高渗透 motif 做重组探索。公开 3D 代理结果进一步说明，候选分子并未脱离高渗透样本所在的极性—疏水邻域。"
        )
    )
    parts.append(table_from_csv(RESULT_DIR / "final_experiment_tables" / "table6_conformation_proxy_neighbors.csv", "表6 候选分子的 3D 极性代理邻域统计", max_rows=10))
    parts.append(image_paragraph(image_map["figure6"], "figure6_conformation_proxy", cx=5600000, cy=2500000))
    parts.append(p("图8 基于公开 3D 极性代理描述符的候选邻域分析。", center=True, font_size=18))
    parts.append(
        p(
            "更进一步，本文引入深层新颖性分析，从 token 相似度和描述符空间最近邻两方面比较候选与训练集的关系。结果显示，optimized 候选的平均最近训练 token Jaccard 约为 0.928，说明其确实属于局部精修；de novo 候选的平均最近训练 token Jaccard 降至约 0.774，平均最近描述符距离也明显更大，说明其并非训练集高分肽的简单重排，而是在高渗透 motif 邻域内进行更广泛的组合探索。"
        )
    )
    parts.append(table_from_csv(RESULT_DIR / "final_experiment_tables" / "table6d_novelty_depth.csv", "表7 深层新颖性分析结果", max_rows=10))
    parts.append(image_paragraph(image_map["figure12"], "figure12_novelty_depth", cx=5600000, cy=3200000))
    parts.append(p("图9 针对训练集的深层新颖性分析。", center=True, font_size=18))

    parts.append(p("结论", style="Heading1", bold=True, font_size=26))
    parts.append(
        p(
            "本文围绕膜渗透环肽设计问题，构建了一套基于公开数据的可复现计算框架。与仅追求 random split 高分或仅依赖复杂生成网络的工作不同，本文从 source-aware robust prediction 出发，进一步打通了 constrained optimization、multi-objective de novo generation、uncertainty/diversity-aware selection、机制分析与统计验证等多个环节。实验表明，random split 会明显高估真实性能，而来源异质性是该领域必须正视的关键问题；同时，优化路线和 de novo 路线分别对应 exploitation 与 exploration 两种互补设计模式。"
        )
    )
    parts.append(
        p(
            "尽管本文仍属于纯计算研究，尚未引入湿实验验证或更高精度的分子动力学模拟，但其优点在于数据公开、流程可复现、结果具有统计支撑且机制解释相对完整。未来工作可以在此基础上继续引入更丰富的 3D/4D 构象信息、外部实验验证或靶点导向的后续活性筛选，从而进一步提升模型的药物设计价值。"
        )
    )

    sect = (
        "<w:sectPr>"
        "<w:pgSz w:w=\"11906\" w:h=\"16838\"/>"
        "<w:pgMar w:top=\"1440\" w:right=\"1440\" w:bottom=\"1440\" w:left=\"1440\" w:header=\"708\" w:footer=\"708\" w:gutter=\"0\"/>"
        "</w:sectPr>"
    )

    body = "".join(parts) + sect
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{NS['w']}" xmlns:r="{NS['r']}" xmlns:wp="{NS['wp']}" xmlns:a="{NS['a']}" xmlns:pic="{NS['pic']}">
  <w:body>
    {body}
  </w:body>
</w:document>
"""


def build_styles():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
    <w:rPr><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:uiPriority w:val="9"/>
    <w:qFormat/>
    <w:rPr><w:b/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:uiPriority w:val="9"/>
    <w:qFormat/>
    <w:rPr><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>
  </w:style>
</w:styles>
"""


def build_content_types(image_exts):
    png_default = '<Default Extension="png" ContentType="image/png"/>'
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  {png_default}
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>
"""


def build_root_rels():
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""


def build_document_rels(images):
    rels = [
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    ]
    for idx, (rid, target_name, _) in enumerate(images, start=2):
        rels.append(
            f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{target_name}"/>'
        )
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + \
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + \
        "".join(rels) + "</Relationships>"


def main():
    image_files = [
        ("figure1", RESULT_DIR / "paper_figures" / "figure1_workflow.png"),
        ("figure2", RESULT_DIR / "paper_figures" / "figure2_prediction.png"),
        ("figure3", RESULT_DIR / "paper_figures" / "figure3_generation.png"),
        ("figure6", RESULT_DIR / "paper_figures" / "figure6_conformation_proxy.png"),
        ("figure8", RESULT_DIR / "paper_figures" / "figure8_quality_diversity.png"),
        ("figure9", RESULT_DIR / "paper_figures" / "figure9_generator_ablation.png"),
        ("figure10", RESULT_DIR / "paper_figures" / "figure10_statistical_summary.png"),
        ("figure11", RESULT_DIR / "paper_figures" / "figure11_source_heterogeneity.png"),
        ("figure12", RESULT_DIR / "paper_figures" / "figure12_novelty_depth.png"),
    ]

    image_map = {}
    images_for_rels = []
    for idx, (key, path) in enumerate(image_files, start=2):
        rid = f"rId{idx}"
        target_name = f"{key}.png"
        image_map[key] = rid
        images_for_rels.append((rid, target_name, path))

    document_xml = build_document(image_map)
    styles_xml = build_styles()
    content_types = build_content_types(["png"])
    root_rels = build_root_rels()
    doc_rels = build_document_rels(images_for_rels)

    with zipfile.ZipFile(OUT_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("word/document.xml", document_xml)
        zf.writestr("word/styles.xml", styles_xml)
        zf.writestr("word/_rels/document.xml.rels", doc_rels)
        for _, target_name, path in images_for_rels:
            zf.write(path, f"word/media/{target_name}")

    print(f"Saved manuscript docx to: {OUT_PATH}")


if __name__ == "__main__":
    main()
