import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.project_paths import RESULT_DIR


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def round_df(df: pd.DataFrame, digits=3) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]):
            out[col] = out[col].round(digits)
    return out


def df_to_markdown_table(df: pd.DataFrame) -> str:
    header = "| " + " | ".join(str(c) for c in df.columns) + " |"
    sep = "| " + " | ".join("---" for _ in df.columns) + " |"
    rows = []
    for _, row in df.iterrows():
        rows.append("| " + " | ".join(str(row[c]) for c in df.columns) + " |")
    return "\n".join([header, sep] + rows)


def df_to_three_line_html(df: pd.DataFrame, title: str) -> str:
    header = "".join(f"<th>{c}</th>" for c in df.columns)
    rows = []
    for _, row in df.iterrows():
        cells = "".join(f"<td>{row[c]}</td>" for c in df.columns)
        rows.append(f"<tr>{cells}</tr>")
    rows_html = "\n".join(rows)
    return f"""
    <div class="table-block">
      <div class="table-title">{title}</div>
      <table class="three-line">
        <thead><tr>{header}</tr></thead>
        <tbody>
        {rows_html}
        </tbody>
      </table>
    </div>
    """


def main():
    out_dir = RESULT_DIR / "manuscript_draft"
    out_dir.mkdir(parents=True, exist_ok=True)

    pred = round_df(pd.read_csv(RESULT_DIR / "final_experiment_tables" / "table1_prediction_and_baselines.csv"), 3)
    gen = round_df(pd.read_csv(RESULT_DIR / "final_experiment_tables" / "table2_generation_summary.csv"), 3)
    qd = round_df(pd.read_csv(RESULT_DIR / "final_experiment_tables" / "table3_quality_diversity.csv"), 3)
    gen_ablation = round_df(pd.read_csv(RESULT_DIR / "final_experiment_tables" / "table4_generator_ablation.csv"), 3)
    source_het = round_df(pd.read_csv(RESULT_DIR / "final_experiment_tables" / "table6b_source_heterogeneity.csv"), 3)
    novelty_depth = round_df(pd.read_csv(RESULT_DIR / "final_experiment_tables" / "table6d_novelty_depth.csv"), 3)
    route_stats = round_df(pd.read_csv(RESULT_DIR / "design_statistics" / "route_comparison_stats.csv"), 3)
    case_df = round_df(pd.read_csv(RESULT_DIR / "case_analysis" / "representative_cases_compact.csv"), 3)
    project_summary = load_json(RESULT_DIR / "project_summary" / "project_summary.json")

    pred_small = pred[["model", "setting", "r2", "f1", "auroc"]]
    gen_small = gen[["group", "count", "novelty_vs_train", "pairwise_jaccard_diversity", "mean_predicted_permeability", "mean_predicted_positive_prob"]]
    qd_small = qd[["route", "count", "quality_mean", "diversity_mean"]]
    ablation_small = gen_ablation[["variant", "pairwise_jaccard_diversity", "mean_predicted_permeability", "mean_predicted_positive_prob", "mean_motif_score", "mean_composition_alignment"]]
    source_small = source_het[["metric", "weighted_mean", "weighted_std", "min", "max"]]
    novelty_small = novelty_depth[["route", "count", "mean_nearest_train_token_jaccard", "mean_nearest_descriptor_distance"]]
    route_small = route_stats[["metric", "group_a_mean", "group_b_mean", "mean_diff", "permutation_pvalue"]]

    opt_case = case_df.loc[case_df["route"] == "optimized"].head(1).iloc[0]
    denovo_case = case_df.loc[case_df["route"] == "de_novo"].head(1).iloc[0]

    refs = [
        "Wang Z, Chen Y, Shang Y, et al. MultiCycPermea: accurate and interpretable prediction of cyclic peptide permeability using a multimodal image-sequence model. BMC Biology, 2025, 23:63. DOI: 10.1186/s12915-025-02166-2.",
        "Aerts R, Tavernier J, Kerstjens A, et al. C2PO: an ML-powered optimizer of the membrane permeability of cyclic peptides through chemical modification. Journal of Cheminformatics, 2025, 17:168. DOI: 10.1186/s13321-025-01109-x.",
        "Yunxiang et al. Ai-driven de novo design of customizable membrane permeable cyclic peptides. Journal of Computer-Aided Molecular Design, 2025. DOI: 10.1007/S10822-025-00639-8.",
    ]

    md = f"""# 中文二稿（精修版）

## 拟题
基于描述符引导与来源感知评估的膜渗透环肽预测及设计框架

## 摘要
膜渗透性是环肽进入细胞内靶点的关键限制因素，但现有人工智能方法常依赖私有权重、不可复现实验配置，或者仅在随机划分上报告乐观结果。针对这一问题，本文基于公开 CycPeptMPDB 数据库，构建了一套可复现的膜渗透环肽预测与设计框架。首先，我们系统比较了文本特征模型、增强描述符模型和混合模型，并在 random split、source split、repeated group CV 和 leave-one-source-out（LOSO）等设置下评估模型的稳健性。结果表明，Hybrid predictor 在随机划分下获得最佳 AUROC=0.846，而 descriptor-based RandomForest 在 repeated group CV 下表现最稳健，说明跨来源泛化而非随机划分得分才是更关键的问题。进一步地，我们在该稳健预测器基础上设计了两条候选生成路线：一条是基于高质量种子环肽的受约束优化路线，另一条是显式多目标驱动的 de novo 生成路线。最终，优化路线得到 12 个 novelty=1.0、uniqueness=1.0 的高质量候选，de novo 路线得到 24 个 novelty=1.0、uniqueness=1.0 的全新候选，并在质量、多样性、组成约束及不确定性之间表现出清晰的 trade-off。进一步的机制分析、3D polarity proxy 分析、来源异质性分析和深度新颖性分析表明，该框架生成的候选并非训练集样本的简单复写，而是在高渗透化学模式附近进行合理探索。综上，本文建立了一套面向膜渗透环肽设计的公开、可复现、来源感知的计算框架，为后续更高层次的环肽从头设计研究提供了可靠基础。

## 1 引言
环肽兼具小分子和大分子药物的部分优势，是进入“不可成药”靶点的重要候选分子类型。然而，大多数环肽难以跨膜进入细胞，这使得膜渗透性成为限制其药物开发的核心瓶颈。近年来，围绕环肽膜渗透性的机器学习研究主要集中在两类方向：一类是建立渗透性预测模型，另一类是进一步利用预测器指导环肽优化或生成。已有代表性工作如 MultiCycPermea 通过图像-序列多模态建模提升了 CycPeptMPDB 上的随机划分预测精度，在 ID 设置下可将 MSE 降至 0.16；C2PO 则更进一步，尝试用机器学习方法指导化学修饰，从而提升环肽膜渗透性。

尽管这些工作推动了该方向的发展，但仍然存在两方面不足。第一，许多方法主要报告 random split 指标，而忽视了实验来源差异带来的分布偏移问题；第二，已有设计框架往往依赖私有权重或不公开的中间特征，使得方法难以严格复现，也限制了后续研究在公开基线之上的持续推进。尤其对于本文所对照的 CCPep 基线，其方法叙事完整，但公开仓库缺失核心 checkpoint 和关键模拟特征文件，因此难以作为真正可重复的研究起点。

基于此，本文不再机械复现不完整的私有实现，而是将研究重点转向“公开、可复现、来源感知”的膜渗透环肽设计问题。我们基于 CycPeptMPDB 重建了长度为 6 的环肽渗透性数据集，构建并比较了多种预测器，在更严格的 cross-source 场景下考察模型稳健性；在此基础上，进一步提出了两条互补的设计路线：基于模板的受约束优化与显式多目标 de novo 生成。相比仅与文献比拼 random split 分数，我们更强调：即便 random split AUROC 已达到 0.846，source-aware 表现仍显著下降，这说明跨来源泛化才是更具科学意义的问题设定。

本文的主要贡献包括：
1. 基于公开 CycPeptMPDB 数据，构建了一套可复现的膜渗透环肽预测与设计流程。
2. 系统揭示了 random split 与 source-aware evaluation 之间的显著差异，证明跨来源泛化是该任务的关键难点。
3. 提出了一套双路线设计框架，包括高质量模板优化路线和显式多目标 de novo 生成路线，并结合 novelty、diversity、uncertainty 与机制分析完成候选筛选。

## 2 材料与方法
### 2.1 数据集构建
本文使用公开 CycPeptMPDB 数据库，并从中筛选主链长度为 6、具有 permeability 标注的环肽作为研究对象。最终工作集包含 2168 条样本。为保证研究可复现，我们进一步从公开数据中构建了 `pretrain.csv` 和 `CycPeptMPDB_Peptide_Length_6.csv` 两个核心数据文件，并统一修正了原始仓库中的硬编码路径依赖。

### 2.2 来源感知预测器构建
我们首先建立公开弱基线 `TF-IDF + 线性模型`，随后构建增强型描述符模型与混合模型。增强型模型引入了多层分子描述符，包括：
- peptide-level 理化性质；
- monomer-level 聚合统计特征；
- 组成特征，如 natural ratio、N-methyl ratio、D-monomer ratio 等。

在实验评价上，我们不局限于 random split，而是同时引入 source split、repeated group CV 和 LOSO，从而更真实地评估模型的跨来源稳健性。

### 2.3 双路线候选设计
在预测器基础上，我们进一步设计了两条候选生成路线。

1. **优化路线（optimized route）**  
从高渗透种子环肽出发，进行单点/双点受约束替换，并通过预测器筛选高质量候选。该路线偏向 exploitation，更适合局部精修。

2. **de novo 路线（de novo route）**  
直接从高频单体池出发进行生成，并通过多目标得分进行筛选。其目标函数不仅考虑渗透性和正类概率，还显式加入：
- motif prior
- composition alignment
- uncertainty stability
- novelty

### 2.4 统计与机制分析
为提升结果可信度，我们进一步进行：
- bootstrap confidence intervals；
- route-level permutation statistics；
- generator ablation；
- descriptor shift analysis；
- 3D polarity proxy analysis；
- source heterogeneity analysis；
- deep novelty analysis。

## 3 结果与分析
### 3.1 预测器性能与来源感知泛化
表 1 总结了主要预测器结果。可以看到，Hybrid predictor 在 random split 下获得最佳 AUROC=0.846，明显优于公开 TF-IDF 弱基线（AUROC=0.773）。然而，当任务切换到更严格的 source split / group CV / LOSO 后，模型性能明显下降，表明跨来源泛化是该问题的真正难点，而不仅仅是 random split 上的刷分问题。

{df_to_markdown_table(pred_small)}

与已有公开工作相比，MultiCycPermea 在 CycPeptMPDB 的 ID setting 下将 MSE 降至 0.16，说明多模态表示在随机划分上确实有明显优势；但本文的结果表明，即便本工作 random split AUROC 已达到 0.846，在更严格的 source-aware 场景中性能仍明显回落。因此，仅比较 random split 指标并不能充分反映模型的真实鲁棒性。

### 3.2 双路线设计结果
在设计阶段，我们分别得到 optimized shortlist 和 de novo shortlist。两者 novelty 均达到 1.0，说明最终候选并非训练集的直接重复；但在质量-多样性空间中，两条路线呈现出明显差异。optimized 路线质量更高、预测 permeability 更好，而 de novo 路线保持了更高的探索性和更大的整体多样性覆盖。

{df_to_markdown_table(gen_small)}

{df_to_markdown_table(qd_small)}

从统计比较结果看，optimized 路线相对于 de novo 路线在 quality score、predicted permeability 和 natural ratio 上更高，而 de novo 路线则表现出更高的 N-methyl ratio 和更远的训练集距离。这说明两条路线并非简单竞争关系，而是分别承担 exploitation 与 exploration 的不同功能。

{df_to_markdown_table(route_small)}

### 3.3 多目标 de novo 生成器消融
为验证 de novo 生成器不是简单“随机采样+打分”的工程拼接，我们对其多目标函数进行了消融。结果表明，full 版本并非在所有单一指标上都绝对最优，但它在 motif、composition alignment 和 uncertainty stability 之间达到了更均衡的平衡；去除某些模块虽然可能带来更高表面多样性或略高单指标，但会削弱组成约束或稳定性。

{df_to_markdown_table(ablation_small)}

这说明 full generator 的贡献不在于单一指标碾压，而在于构建了一个更可信的、多目标平衡的设计策略。

### 3.4 Representative Case Study
为增强化学直觉展示，我们从两条路线中各选取代表性候选进行案例分析。

**Case 1：优化路线代表候选**  
候选肽为 `{opt_case['candidate_helm']}`，其 parent 为 `{opt_case['parent_helm']}`。该候选的预测 permeability 为 {opt_case['predicted_permeability']:.3f}，相对于 parent 的 improvement 为 {opt_case['improvement']:.3f}。其关键修改为 `{opt_case['mutation_description']}`。从结构-描述符角度看，这类替换并未粗暴改变整体骨架，而是通过将较不利于渗透的残基替换为更接近高渗透 motif 的单体，使候选在 MolLogP、TPSA 和组成特征上更接近高渗透参考肽。这说明 optimized route 的本质是**围绕已知高质量模板进行局部修正**。

**Case 2：de novo 路线代表候选**  
候选肽为 `{denovo_case['candidate_helm']}`，其预测 permeability 为 {denovo_case['predicted_permeability']:.3f}，预测正类概率为 {denovo_case['predicted_positive_prob']:.3f}。虽然它并不直接继承一个已知训练模板，但其 token 组合和描述符特征向高渗透参考肽靠拢，例如在 N-methyl 富集、疏水性增强以及 3D polarity proxy 上呈现出与高渗透邻域相近的模式。这说明 de novo route 的生成结果不是“乱码肽”，而是在**高渗透 motif 附近进行重组探索**。

这种 case study 结果对于化学/药学审稿人是必要的，因为它表明模型输出并非仅在统计意义上成立，也具备一定的物理化学合理性。

### 3.5 来源异质性与深层新颖性
LOSO 结果显示，来源级 AUROC 的加权均值约为 0.737，但不同来源之间跨度极大（0.167 到 1.000），且与来源样本量的相关性仅为 -0.234，说明来源异质性并不能简单归因于样本多少。

{df_to_markdown_table(source_small)}

同时，我们进一步进行了 deep novelty analysis。结果表明，optimized 候选与训练集最近邻的 token Jaccard 平均值约为 0.928，而 de novo 候选约为 0.774；对应的最近描述符距离分别约为 0.288 和 0.689。也就是说，optimized route 更接近已知高渗透模板，而 de novo route 在 token 空间和描述符空间上都明显更远，说明其具有更强的“非记忆式重组”特征。

{df_to_markdown_table(novelty_small)}

## 4 讨论
本文的结果表明，如果仅从 random split 角度评价环肽膜渗透性预测模型，很容易高估模型能力。与此相比，source-aware generalization 更能反映实际应用中的难点。我们基于公开数据构建的描述符引导框架，不依赖私有 checkpoint，能够在公开条件下稳定完成预测、优化和 de novo 设计任务。

与已有工作相比，本文的真正优势不在于单点刷高某一项 random split 指标，而在于构建了一条更完整的证据链：从预测器稳健性、双路线设计、生成器消融，到机制分析、proxy 分析、来源异质性和深层新颖性分析，形成了比较完整的设计闭环。这也是本文相对于简单“换 backbone 提高一点分数”的工作更具发表潜力的地方。

当然，本文仍然是计算研究。当前的主要局限在于缺少湿实验验证，此外 de novo generator 仍是 descriptor-guided 的多目标生成器，而非更复杂的端到端深度生成网络。因此，如果后续希望进一步冲击更高档次期刊，实验验证或更强的结构层建模仍是值得推进的方向。

## 5 结论
本文围绕公开 CycPeptMPDB 数据，建立了一套面向膜渗透环肽的来源感知预测与设计框架。研究表明：
1. cross-source 泛化是比 random split 得分更关键的问题；
2. optimized 与 de novo 两条路线分别承担 exploitation 与 exploration 的不同功能；
3. 多目标生成器、机制分析、3D proxy 和 novelty-depth 分析共同支撑了候选分子的化学合理性与非记忆式新颖性。

因此，本文不仅给出了一套可复现的计算框架，也为后续更高层次的环肽从头设计研究提供了可靠基础。

## 参考文献（建议稿）
""" + "\n".join([f"{i+1}. {ref}" for i, ref in enumerate(refs)]) + "\n"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <title>中文二稿（精修版）</title>
  <style>
    body {{
      font-family: "Times New Roman", "SimSun", serif;
      max-width: 1050px;
      margin: 32px auto;
      line-height: 1.8;
      color: #1f2937;
      padding: 0 18px;
    }}
    h1, h2, h3 {{
      color: #111827;
    }}
    h1 {{
      text-align: center;
      margin-bottom: 20px;
    }}
    .lead {{
      background: #f8fafc;
      border-left: 4px solid #475569;
      padding: 12px 16px;
      margin: 20px 0;
    }}
    .table-block {{
      margin: 24px 0 30px 0;
    }}
    .table-title {{
      font-weight: bold;
      margin-bottom: 8px;
    }}
    table.three-line {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    table.three-line thead tr:first-child {{
      border-top: 2px solid #111827;
      border-bottom: 1px solid #111827;
    }}
    table.three-line tbody tr:last-child {{
      border-bottom: 2px solid #111827;
    }}
    table.three-line th, table.three-line td {{
      padding: 6px 8px;
      text-align: center;
      vertical-align: middle;
    }}
    .ref {{
      font-size: 14px;
    }}
    .small {{
      font-size: 13px;
      color: #4b5563;
    }}
  </style>
</head>
<body>
  <h1>中文二稿（精修版）</h1>
  <div class="lead">
    本稿基于公开数据重建了一条可复现的膜渗透环肽设计框架，重点强调来源感知评估、双路线候选设计和多层验证链，而不是仅在 random split 上追求单点高分。
  </div>
  <h2>摘要</h2>
  <p>膜渗透性是环肽进入细胞内靶点的关键限制因素，但现有人工智能方法常依赖私有权重、不可复现实验配置，或者仅在随机划分上报告乐观结果。针对这一问题，本文基于公开 CycPeptMPDB 数据库，构建了一套可复现的膜渗透环肽预测与设计框架。首先，我们系统比较了文本特征模型、增强描述符模型和混合模型，并在 random split、source split、repeated group CV 和 leave-one-source-out（LOSO）等设置下评估模型的稳健性。结果表明，Hybrid predictor 在随机划分下获得最佳 AUROC=0.846，而 descriptor-based RandomForest 在 repeated group CV 下表现最稳健，说明跨来源泛化而非随机划分得分才是更关键的问题。进一步地，我们在该稳健预测器基础上设计了两条候选生成路线：一条是基于高质量种子环肽的受约束优化路线，另一条是显式多目标驱动的 de novo 生成路线。最终，优化路线得到 12 个 novelty=1.0、uniqueness=1.0 的高质量候选，de novo 路线得到 24 个 novelty=1.0、uniqueness=1.0 的全新候选，并在质量、多样性、组成约束及不确定性之间表现出清晰的 trade-off。进一步的机制分析、3D polarity proxy 分析、来源异质性分析和深度新颖性分析表明，该框架生成的候选并非训练集样本的简单复写，而是在高渗透化学模式附近进行合理探索。综上，本文建立了一套面向膜渗透环肽设计的公开、可复现、来源感知的计算框架，为后续更高层次的环肽从头设计研究提供了可靠基础。</p>

  <h2>核心结果表</h2>
  {df_to_three_line_html(pred_small, "表1 主要预测模型性能比较（保留三位小数）")}
  {df_to_three_line_html(gen_small, "表2 优化路线与 de novo 路线生成结果汇总")}
  {df_to_three_line_html(qd_small, "表3 质量-多样性结果汇总")}
  {df_to_three_line_html(ablation_small, "表4 多目标 de novo 生成器消融结果")}
  {df_to_three_line_html(source_small, "表5 来源异质性汇总")}
  {df_to_three_line_html(novelty_small, "表6 深层新颖性汇总")}

  <h2>Representative Case Study</h2>
  <p><b>优化路线候选案例：</b>{opt_case['candidate_helm']} 相对于 parent {opt_case['parent_helm']} 的 improvement 为 {opt_case['improvement']:.3f}。其核心修改为 {opt_case['mutation_description']}。这一案例说明模型倾向于通过局部替换，将较不利于渗透的单体替换为更接近高渗透 motif 的残基组合，从而在不剧烈破坏整体骨架的前提下改善渗透性。</p>
  <p><b>de novo 候选案例：</b>{denovo_case['candidate_helm']} 的 predicted permeability 为 {denovo_case['predicted_permeability']:.3f}，predicted positive probability 为 {denovo_case['predicted_positive_prob']:.3f}。虽然该候选并不直接来源于训练集模板，但其组合模式向高渗透参考肽靠拢，体现为更高的 N-methyl 富集和更合理的疏水性-极性平衡。</p>

  <h2>外部对照与相关工作</h2>
  <p>已有公开工作中，MultiCycPermea 在 CycPeptMPDB 的 ID setting 下将 MSE 降至 0.16，说明其在随机划分条件下具有很强的预测能力；C2PO 则将研究重点放在化学修饰驱动的 permeability 优化上。但本文结果显示，即便 random split AUROC 已达到 0.846，在更严格的 source-aware 设置下性能仍明显下降。因此，与现有文献单纯比较 random split 分数并不足以说明模型的真实泛化能力，跨来源稳健性才是更具科学意义的评估维度。</p>

  <h2>图件建议</h2>
  <p class="small">建议正文主图保留 Figure 1、2、3、6、8、9、10、11、12，其他图放入补充材料。Figure 5 可保留为案例图，但建议后续继续美化。若后面可以进一步补二维结构图或单体示意图，则优先替换现有 case analysis 图。</p>

  <h2>参考文献（建议稿）</h2>
  <div class="ref">
    <ol>
      {"".join(f"<li>{ref}</li>" for ref in refs)}
    </ol>
  </div>
</body>
</html>
"""

    (out_dir / "中文二稿_精修版.md").write_text(md, encoding="utf-8")
    (out_dir / "中文二稿_精修版.html").write_text(html, encoding="utf-8")

    print(f"Saved refined Chinese second draft to: {out_dir}")
    print(out_dir / "中文二稿_精修版.md")
    print(out_dir / "中文二稿_精修版.html")


if __name__ == "__main__":
    main()
