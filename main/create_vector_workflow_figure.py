import math
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "Result" / "paper_figures"
PPTX_OUT = PROJECT_ROOT / "cyclic_peptide_workflow_vector.pptx"
SVG_OUT = OUT_DIR / "figure1_workflow_vector.svg"

EMU_PER_IN = 914400
SLIDE_W = 13.333
SLIDE_H = 7.5


def emu(inches):
    return int(inches * EMU_PER_IN)


def rgb(hex_color):
    return hex_color.replace("#", "").upper()


COLORS = {
    "ink": "#24323A",
    "muted": "#5C6F7A",
    "grid": "#C9D3DA",
    "light": "#F6FAFC",
    "data": "#2F80ED",
    "predict": "#00A6A6",
    "design": "#F2994A",
    "filter": "#7B61FF",
    "final": "#27AE60",
    "opt": "#1F77B4",
    "denovo": "#F28E2B",
}


def shape_xml(shape_id, name, x, y, w, h, fill, line="#FFFFFF", radius=True, text="", font_size=13, bold=False):
    prst = "roundRect" if radius else "rect"
    tx_body = ""
    if text:
        paragraphs = []
        for i, line_text in enumerate(text.split("\n")):
            paragraphs.append(
                f'<a:p><a:pPr algn="ctr"/>'
                f'<a:r><a:rPr lang="en-US" sz="{font_size * 100}" b="{1 if bold else 0}">'
                f'<a:solidFill><a:srgbClr val="{rgb(COLORS["ink"])}"/></a:solidFill>'
                f'</a:rPr><a:t>{escape(line_text)}</a:t></a:r></a:p>'
            )
        tx_body = (
            '<p:txBody><a:bodyPr wrap="square" anchor="mid" rtlCol="0">'
            '<a:spAutoFit/></a:bodyPr><a:lstStyle/>'
            + "".join(paragraphs)
            + "</p:txBody>"
        )
    return f"""
    <p:sp>
      <p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
      <p:spPr>
        <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
        <a:prstGeom prst="{prst}"><a:avLst/></a:prstGeom>
        <a:solidFill><a:srgbClr val="{rgb(fill)}"/></a:solidFill>
        <a:ln w="12700"><a:solidFill><a:srgbClr val="{rgb(line)}"/></a:solidFill></a:ln>
      </p:spPr>
      {tx_body}
    </p:sp>
    """


def text_xml(shape_id, name, x, y, w, h, text, size=18, bold=False, color=None, align="ctr"):
    color = color or COLORS["ink"]
    paragraphs = []
    for line in text.split("\n"):
        paragraphs.append(
            f'<a:p><a:pPr algn="{align}"/>'
            f'<a:r><a:rPr lang="en-US" sz="{size * 100}" b="{1 if bold else 0}">'
            f'<a:solidFill><a:srgbClr val="{rgb(color)}"/></a:solidFill>'
            f'</a:rPr><a:t>{escape(line)}</a:t></a:r></a:p>'
        )
    return f"""
    <p:sp>
      <p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>
      <p:spPr>
        <a:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>
        <a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln>
      </p:spPr>
      <p:txBody><a:bodyPr wrap="square" anchor="mid"/><a:lstStyle/>{''.join(paragraphs)}</p:txBody>
    </p:sp>
    """


def line_xml(shape_id, name, x1, y1, x2, y2, color="#5C6F7A", width=2.0, arrow=True):
    x = min(x1, x2)
    y = min(y1, y2)
    w = abs(x2 - x1)
    h = abs(y2 - y1)
    flip_h = ' flipH="1"' if x2 < x1 else ""
    flip_v = ' flipV="1"' if y2 < y1 else ""
    arrow_xml = '<a:tailEnd type="triangle" w="med" len="med"/>' if arrow else ""
    return f"""
    <p:cxnSp>
      <p:nvCxnSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>
      <p:spPr>
        <a:xfrm{flip_h}{flip_v}><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(max(w, 0.01))}" cy="{emu(max(h, 0.01))}"/></a:xfrm>
        <a:prstGeom prst="straightConnector1"><a:avLst/></a:prstGeom>
        <a:ln w="{int(width * 12700)}"><a:solidFill><a:srgbClr val="{rgb(color)}"/></a:solidFill>{arrow_xml}</a:ln>
      </p:spPr>
    </p:cxnSp>
    """


def icon_ring(shape_id_start, cx, cy, r, color):
    parts = []
    for i in range(6):
        a1 = math.pi / 3 * i - math.pi / 6
        a2 = math.pi / 3 * ((i + 1) % 6) - math.pi / 6
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        x2, y2 = cx + r * math.cos(a2), cy + r * math.sin(a2)
        parts.append(line_xml(shape_id_start + i, "peptide ring edge", x1, y1, x2, y2, color=color, width=2.0, arrow=False))
    return "".join(parts)


def slide_xml():
    sid = 10
    shapes = []
    shapes.append(text_xml(sid, "title", 0.9, 0.28, 11.5, 0.55, "Descriptor-guided source-aware design of membrane-permeable cyclic peptides", 20, True))
    sid += 1
    shapes.append(text_xml(sid, "subtitle", 1.15, 0.78, 11.0, 0.35, "public data  |  robust prediction  |  dual-route generation  |  uncertainty-aware filtering", 11, False, COLORS["muted"]))
    sid += 1

    panels = [
        ("Public\nCycPeptMPDB", COLORS["data"], "2168 length-6\ncyclic peptides", 0.60),
        ("Source-aware\npredictor", COLORS["predict"], "HELM tokens +\ndescriptors", 3.05),
        ("Dual-route\ndesign", COLORS["design"], "optimization +\nde novo", 5.50),
        ("Safety\nfilters", COLORS["filter"], "uncertainty\ndiversity novelty\n3D polarity proxy", 7.95),
        ("Validated\nshortlist", COLORS["final"], "optimized\nand de novo\ncandidates", 10.40),
    ]
    y = 2.05
    pw, ph = 1.95, 2.35
    for idx, (title, color, body, x) in enumerate(panels):
        shapes.append(shape_xml(sid, f"panel {idx+1}", x, y, pw, ph, "#FFFFFF", color, True))
        sid += 1
        shapes.append(shape_xml(sid, f"panel {idx+1} header", x, y, pw, 0.48, color, color, True, title, 12, True))
        sid += 1
        shapes.append(text_xml(sid, f"panel {idx+1} body", x + 0.16, y + 1.48, pw - 0.32, 0.65, body, 10, False, COLORS["muted"]))
        sid += 1
        if idx < len(panels) - 1:
            shapes.append(line_xml(sid, "pipeline arrow", x + pw + 0.13, y + ph / 2, panels[idx + 1][3] - 0.16, y + ph / 2, COLORS["muted"], 1.7, True))
            sid += 1

    shapes.append(icon_ring(sid, 1.57, 3.05, 0.32, COLORS["data"]))
    sid += 6
    shapes.append(shape_xml(sid, "database", 0.92, 2.78, 0.34, 0.68, "#EAF3FF", COLORS["data"], True))
    sid += 1
    shapes.append(shape_xml(sid, "token block", 3.42, 2.70, 0.48, 0.26, "#E8FAFA", COLORS["predict"], True, "HELM", 7, True))
    sid += 1
    shapes.append(shape_xml(sid, "descriptor block", 4.02, 2.70, 0.48, 0.26, "#E8FAFA", COLORS["predict"], True, "DESC", 7, True))
    sid += 1
    shapes.append(line_xml(sid, "mini roc", 3.40, 3.50, 4.50, 3.05, COLORS["predict"], 2.0, False))
    sid += 1

    shapes.append(line_xml(sid, "branch top", 6.45, 3.00, 7.22, 2.62, COLORS["design"], 1.5, True))
    sid += 1
    shapes.append(line_xml(sid, "branch bottom", 6.45, 3.42, 7.22, 3.82, COLORS["design"], 1.5, True))
    sid += 1
    shapes.append(shape_xml(sid, "opt branch", 6.90, 2.30, 0.72, 0.34, "#FFF3E7", COLORS["opt"], True, "opt", 9, True))
    sid += 1
    shapes.append(shape_xml(sid, "denovo branch", 6.90, 3.76, 0.72, 0.34, "#FFF3E7", COLORS["denovo"], True, "de novo", 8, True))
    sid += 1

    filter_labels = [("U", 8.36, 2.60), ("D", 9.00, 2.60), ("N", 8.36, 3.42), ("3D", 9.00, 3.42)]
    for label, fx, fy in filter_labels:
        shapes.append(shape_xml(sid, f"filter {label}", fx, fy, 0.45, 0.35, "#F1EEFF", COLORS["filter"], True, label, 9, True))
        sid += 1

    shapes.append(icon_ring(sid, 11.20, 2.82, 0.25, COLORS["opt"]))
    sid += 6
    shapes.append(icon_ring(sid, 11.55, 3.55, 0.25, COLORS["denovo"]))
    sid += 6

    shapes.append(shape_xml(sid, "footer band", 1.35, 5.40, 10.65, 0.72, COLORS["light"], COLORS["grid"], True))
    sid += 1
    shapes.append(text_xml(sid, "footer text", 1.55, 5.48, 10.25, 0.52, "Output: prioritized candidate shortlists with prediction evidence, calibration checks, novelty depth, and mechanistic proxy analysis", 11, False, COLORS["ink"]))

    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
    {''.join(shapes)}
  </p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""


def svg():
    # SVG companion for manuscript import. Text is kept as real text and shapes are vector paths.
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" viewBox="0 0 1600 900">
  <rect width="1600" height="900" fill="white"/>
  <text x="800" y="72" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="34" font-weight="700" fill="{COLORS['ink']}">Descriptor-guided source-aware design of membrane-permeable cyclic peptides</text>
  <text x="800" y="112" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="18" fill="{COLORS['muted']}">public data | robust prediction | dual-route generation | uncertainty-aware filtering</text>
  {svg_pipeline()}
</svg>"""


def svg_panel(x, title, body, color):
    return f"""
  <rect x="{x}" y="250" width="235" height="282" rx="20" fill="white" stroke="{color}" stroke-width="4"/>
  <rect x="{x}" y="250" width="235" height="58" rx="20" fill="{color}"/>
  <text x="{x+117.5}" y="276" text-anchor="middle" font-family="Arial" font-size="18" font-weight="700" fill="white">{title[0]}</text>
  <text x="{x+117.5}" y="298" text-anchor="middle" font-family="Arial" font-size="18" font-weight="700" fill="white">{title[1]}</text>
  <text x="{x+117.5}" y="470" text-anchor="middle" font-family="Arial" font-size="17" fill="{COLORS['muted']}">{body[0]}</text>
  <text x="{x+117.5}" y="493" text-anchor="middle" font-family="Arial" font-size="17" fill="{COLORS['muted']}">{body[1]}</text>
  """


def svg_arrow(x1, x2):
    return f'<line x1="{x1}" y1="391" x2="{x2}" y2="391" stroke="{COLORS["muted"]}" stroke-width="3" marker-end="url(#arrow)"/>'


def svg_pipeline():
    panels = [
        (72, ("Public", "CycPeptMPDB"), ("2168 length-6", "cyclic peptides"), COLORS["data"]),
        (366, ("Source-aware", "predictor"), ("HELM tokens +", "descriptors"), COLORS["predict"]),
        (660, ("Dual-route", "design"), ("optimization +", "de novo"), COLORS["design"]),
        (954, ("Safety", "filters"), ("uncertainty diversity", "novelty 3D proxy"), COLORS["filter"]),
        (1248, ("Validated", "shortlist"), ("optimized and", "de novo candidates"), COLORS["final"]),
    ]
    defs = f"""<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L9,3 z" fill="{COLORS['muted']}"/></marker></defs>"""
    body = [defs]
    for i, p in enumerate(panels):
        body.append(svg_panel(*p))
        if i < len(panels) - 1:
            body.append(svg_arrow(p[0] + 250, panels[i + 1][0] - 18))
    body.append(f'<rect x="162" y="648" width="1276" height="82" rx="18" fill="{COLORS["light"]}" stroke="{COLORS["grid"]}" stroke-width="2"/>')
    body.append(f'<text x="800" y="696" text-anchor="middle" font-family="Arial" font-size="20" fill="{COLORS["ink"]}">Output: prioritized candidate shortlists with calibration, novelty depth, and mechanistic proxy analysis</text>')
    return "\n".join(body)


def write_pptx():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "[Content_Types].xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
<Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>""",
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>""",
        "docProps/core.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Cyclic peptide workflow vector figure</dc:title></cp:coreProperties>""",
        "docProps/app.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>Codex OpenXML</Application><Slides>1</Slides></Properties>""",
        "ppt/presentation.xml": f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
<p:sldIdLst><p:sldId id="256" r:id="rId2"/></p:sldIdLst>
<p:sldSz cx="{emu(SLIDE_W)}" cy="{emu(SLIDE_H)}" type="wide"/><p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>""",
        "ppt/_rels/presentation.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>""",
        "ppt/slides/slide1.xml": slide_xml(),
        "ppt/slides/_rels/slide1.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
</Relationships>""",
        "ppt/slideMasters/slideMaster1.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
</p:sldMaster>""",
        "ppt/slideMasters/_rels/slideMaster1.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>""",
        "ppt/slideLayouts/slideLayout1.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
<p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>""",
        "ppt/slideLayouts/_rels/slideLayout1.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>""",
        "ppt/theme/theme1.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Scientific Workflow">
<a:themeElements>
<a:clrScheme name="Office"><a:dk1><a:srgbClr val="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="1F1F1F"/></a:dk2><a:lt2><a:srgbClr val="F6FAFC"/></a:lt2><a:accent1><a:srgbClr val="2F80ED"/></a:accent1><a:accent2><a:srgbClr val="00A6A6"/></a:accent2><a:accent3><a:srgbClr val="F2994A"/></a:accent3><a:accent4><a:srgbClr val="7B61FF"/></a:accent4><a:accent5><a:srgbClr val="27AE60"/></a:accent5><a:accent6><a:srgbClr val="5C6F7A"/></a:accent6><a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink></a:clrScheme>
<a:fontScheme name="Arial"><a:majorFont><a:latin typeface="Arial"/></a:majorFont><a:minorFont><a:latin typeface="Arial"/></a:minorFont></a:fontScheme>
<a:fmtScheme name="Default"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
</a:themeElements>
</a:theme>""",
    }
    with zipfile.ZipFile(PPTX_OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    SVG_OUT.write_text(svg(), encoding="utf-8")
    print(f"Saved {PPTX_OUT}")
    print(f"Saved {SVG_OUT}")


if __name__ == "__main__":
    write_pptx()
