import math
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "Result" / "paper_figures"
SVG_OUT = OUT_DIR / "figure1_workflow_reference_style.svg"
PPTX_OUT = ROOT / "cyclic_peptide_workflow_reference_style.pptx"


C = {
    "blue": "#0B4FA3",
    "blue2": "#1769C2",
    "teal": "#008C87",
    "teal2": "#11A39C",
    "orange": "#E26A16",
    "orange2": "#F08A2B",
    "ink": "#111827",
    "muted": "#4B5563",
    "light_blue": "#F7FBFF",
    "light_teal": "#F6FFFD",
    "light_orange": "#FFF9F4",
    "line": "#B6C7DD",
    "cream": "#FDECD9",
    "paper": "#F9FAFB",
    "green": "#26A65B",
    "purple": "#7E6AB8",
    "red": "#D84A4A",
    "yellow": "#F1A91F",
    "cyan": "#42B7B4",
}


def ring(cx, cy, r, colors=None, dash=False, label=None):
    colors = colors or [C["blue2"], C["purple"], C["green"], C["cyan"], C["orange2"], "#9CA3AF"]
    pts = []
    for i in range(6):
        a = -math.pi / 2 + i * math.pi / 3
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    segs = []
    for i in range(6):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % 6]
        dash_attr = ' stroke-dasharray="7 7"' if dash and i in (1, 2) else ""
        segs.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#111827" stroke-width="2.2" stroke-linecap="round"'
            f'{dash_attr}/>'
        )
    nodes = []
    for i, (x, y) in enumerate(pts):
        nodes.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="10" fill="{colors[i % len(colors)]}" stroke="#263238" stroke-width="1.4"/>')
    extra = ""
    if label:
        extra = f'<text x="{cx}" y="{cy + r + 25}" text-anchor="middle" class="tiny">{escape(label)}</text>'
    return "\n".join(segs + nodes) + extra


def text(x, y, s, cls="text", anchor="start"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" class="{cls}">{escape(s)}</text>'


def card(x, y, w, h, color, fill, num, title):
    return f"""
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{fill}" stroke="{color}" stroke-width="2.2"/>
  <circle cx="{x+38}" cy="{y+40}" r="24" fill="{color}"/>
  <text x="{x+38}" y="{y+49}" text-anchor="middle" class="num">{num}</text>
  <text x="{x+76}" y="{y+48}" class="title" fill="{color}">{escape(title)}</text>
  """


def subbox(x, y, w, h, title, color=C["blue2"]):
    return f"""
  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="11" fill="white" stroke="{C['line']}" stroke-width="1.5"/>
  <text x="{x+18}" y="{y+26}" class="subhead" fill="{color}">{escape(title)}</text>
  """


def db_icon(x, y):
    return f"""
  <ellipse cx="{x+52}" cy="{y+15}" rx="52" ry="18" fill="{C['blue']}" stroke="{C['blue']}" stroke-width="2"/>
  <path d="M{x} {y+15} v85 c0 10 23 18 52 18 s52-8 52-18 v-85" fill="{C['blue']}" stroke="{C['blue']}" stroke-width="2"/>
  <path d="M{x} {y+43} c0 10 23 18 52 18 s52-8 52-18" fill="none" stroke="white" stroke-width="3"/>
  <path d="M{x} {y+72} c0 10 23 18 52 18 s52-8 52-18" fill="none" stroke="white" stroke-width="3"/>
  <circle cx="{x+86}" cy="{y+42}" r="4" fill="white"/><circle cx="{x+86}" cy="{y+72}" r="4" fill="white"/>
  """


def docs_icon(x, y):
    return f"""
  <rect x="{x+30}" y="{y}" width="110" height="138" rx="9" fill="#EEF5FF" stroke="{C['blue']}" stroke-width="2"/>
  <rect x="{x+15}" y="{y+22}" width="110" height="138" rx="9" fill="#F8FBFF" stroke="{C['blue']}" stroke-width="2"/>
  <rect x="{x}" y="{y+46}" width="110" height="138" rx="9" fill="white" stroke="{C['blue']}" stroke-width="2"/>
  <line x1="{x+22}" y1="{y+88}" x2="{x+88}" y2="{y+88}" stroke="{C['line']}" stroke-width="2"/>
  <line x1="{x+22}" y1="{y+112}" x2="{x+88}" y2="{y+112}" stroke="{C['line']}" stroke-width="2"/>
  <line x1="{x+22}" y1="{y+136}" x2="{x+72}" y2="{y+136}" stroke="{C['line']}" stroke-width="2"/>
  """


def arrow(x1, y1, x2, y2, color):
    return f'<path d="M{x1},{y1} C{(x1+x2)/2},{y1} {(x1+x2)/2},{y2} {x2},{y2}" fill="none" stroke="{color}" stroke-width="8" stroke-linecap="round" marker-end="url(#{color.strip("#")})"/>'


def mini_roc(x, y):
    return f"""
  <line x1="{x}" y1="{y+110}" x2="{x+150}" y2="{y+110}" stroke="{C['ink']}" stroke-width="2"/>
  <line x1="{x}" y1="{y+110}" x2="{x}" y2="{y}" stroke="{C['ink']}" stroke-width="2"/>
  <path d="M{x+5},{y+105} C{x+25},{y+62} {x+50},{y+35} {x+88},{y+28} S{x+130},{y+18} {x+150},{y+12}" fill="none" stroke="{C['blue2']}" stroke-width="4"/>
  <line x1="{x+4}" y1="{y+106}" x2="{x+145}" y2="{y+8}" stroke="#9CA3AF" stroke-width="1.5" stroke-dasharray="5 5"/>
  <text x="{x+92}" y="{y+83}" class="tiny">AUC</text>
  <text x="{x+44}" y="{y+132}" class="tiny">False Positive Rate</text>
  <text x="{x-22}" y="{y+72}" class="tiny" transform="rotate(-90 {x-22} {y+72})">True Positive Rate</text>
  """


def source_grid(x, y):
    out = []
    colors = [C["blue2"], C["purple"], C["green"], C["orange2"], "#9CA3AF"]
    for col in range(4):
        out.append(f'<text x="{x+col*58}" y="{y}" class="tiny">Fold {col+1 if col<3 else "N"}</text>')
        for row in range(5):
            xx = x + col * 58 + (row % 2) * 22
            yy = y + 18 + row * 26
            dash = ' stroke-dasharray="5 4"' if col == 3 and row in (1, 3) else ""
            out.append(f'<rect x="{xx}" y="{yy}" width="15" height="20" fill="{colors[row]}" fill-opacity="0.16" stroke="{colors[row]}" stroke-width="1.8"{dash}/>')
    return "\n".join(out)


def filter_row(cx, cy, label, desc, icon):
    if icon == "gauge":
        icon_svg = f"""
        <path d="M{cx-36},{cy+12} A42,42 0 0 1 {cx+36},{cy+12}" fill="none" stroke="{C['ink']}" stroke-width="4"/>
        <line x1="{cx}" y1="{cy+12}" x2="{cx+22}" y2="{cy-18}" stroke="{C['ink']}" stroke-width="4" stroke-linecap="round"/>
        <circle cx="{cx}" cy="{cy+12}" r="5" fill="{C['ink']}"/>"""
    elif icon == "dots":
        dots = []
        for i in range(26):
            dx = (i % 6) * 13 - 32
            dy = (i // 6) * 13 - 28
            col = [C["red"], C["blue"], C["teal"], C["orange"], C["green"]][i % 5]
            dots.append(f'<circle cx="{cx+dx}" cy="{cy+dy}" r="4" fill="{col}"/>')
        icon_svg = "".join(dots)
    elif icon == "finger":
        icon_svg = "".join([f'<path d="M{cx-35+i*8},{cy+30} C{cx-18+i*3},{cy-35} {cx+18-i*2},{cy-35} {cx+35-i*8},{cy+30}" fill="none" stroke="{C["ink"]}" stroke-width="2"/>' for i in range(6)])
    else:
        icon_svg = f"""
        <path d="M{cx-35},{cy+20} C{cx-45},{cy-22} {cx+10},{cy-45} {cx+38},{cy-12} C{cx+58},{cy+12} {cx+20},{cy+42} {cx-35},{cy+20}Z" fill="#DDE7F2" stroke="#607D8B" stroke-width="2"/>
        <circle cx="{cx-10}" cy="{cy}" r="18" fill="#2F80ED" fill-opacity="0.72"/>
        <circle cx="{cx+18}" cy="{cy+8}" r="18" fill="#D84A4A" fill-opacity="0.72"/>
        <rect x="{cx-44}" y="{cy+48}" width="88" height="8" fill="url(#polarity)"/>"""
    return f"""
      <circle cx="{cx}" cy="{cy}" r="56" fill="{C['cream']}"/>
      {icon_svg}
      <text x="{cx+88}" y="{cy-12}" class="filterTitle">{escape(label)}</text>
      <text x="{cx+88}" y="{cy+18}" class="filterDesc">{escape(desc)}</text>
    """


def svg():
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="2200" height="1000" viewBox="0 0 2200 1000">
<defs>
  <marker id="{C['blue2'].strip('#')}" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M0,0 L0,12 L12,6 z" fill="{C['blue2']}"/></marker>
  <marker id="{C['teal'].strip('#')}" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M0,0 L0,12 L12,6 z" fill="{C['teal']}"/></marker>
  <marker id="{C['orange'].strip('#')}" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto"><path d="M0,0 L0,12 L12,6 z" fill="{C['orange']}"/></marker>
  <linearGradient id="polarity" x1="0" x2="1"><stop offset="0" stop-color="#2F80ED"/><stop offset="0.5" stop-color="#FFFFFF"/><stop offset="1" stop-color="#D84A4A"/></linearGradient>
  <filter id="shadow" x="-10%" y="-10%" width="130%" height="130%"><feDropShadow dx="0" dy="6" stdDeviation="8" flood-color="#0F172A" flood-opacity="0.12"/></filter>
</defs>
<style>
  .title {{ font-family: Arial, Helvetica, sans-serif; font-size: 30px; font-weight: 700; }}
  .num {{ font-family: Arial, Helvetica, sans-serif; font-size: 30px; font-weight: 700; fill: white; }}
  .subhead {{ font-family: Arial, Helvetica, sans-serif; font-size: 20px; font-weight: 700; }}
  .text {{ font-family: Arial, Helvetica, sans-serif; font-size: 20px; fill: {C['ink']}; }}
  .tiny {{ font-family: Arial, Helvetica, sans-serif; font-size: 14px; fill: {C['ink']}; }}
  .filterTitle {{ font-family: Arial, Helvetica, sans-serif; font-size: 24px; font-weight: 700; fill: {C['ink']}; }}
  .filterDesc {{ font-family: Arial, Helvetica, sans-serif; font-size: 18px; fill: {C['muted']}; }}
  .route {{ font-family: Arial, Helvetica, sans-serif; font-size: 26px; font-weight: 700; fill: {C['teal']}; }}
</style>
<rect width="2200" height="1000" fill="white"/>
<g filter="url(#shadow)">
{card(26, 34, 424, 900, C['blue'], C['light_blue'], 1, 'Public CycPeptMPDB data')}
{card(478, 34, 402, 900, C['blue2'], C['light_blue'], 2, 'Source-aware predictor')}
{card(926, 34, 500, 900, C['teal'], C['light_teal'], 3, 'Dual-route design')}
{card(1460, 34, 382, 900, C['orange'], C['light_orange'], 4, 'Safety filters')}
{card(1876, 34, 298, 900, C['blue'], C['light_blue'], 5, 'Validated shortlist')}
</g>
{arrow(450, 480, 478, 480, C['blue2'])}
{arrow(880, 480, 926, 480, C['blue2'])}
{arrow(1426, 480, 1460, 480, C['teal'])}
{arrow(1842, 480, 1876, 480, C['orange'])}

<!-- Panel 1 -->
{db_icon(76, 220)}
{ring(260, 202, 62)}
{ring(225, 375, 44)}
{ring(334, 350, 46)}
<text x="268" y="340" class="text" text-anchor="middle">...</text>
{docs_icon(62, 560)}
<text x="270" y="620" class="text" fill="{C['blue']}">CycPeptMPDB</text>
<text x="270" y="668" class="text" fill="{C['teal']}">HELM strings</text>
<text x="270" y="716" class="text" fill="{C['green']}">Sources</text>
<text x="270" y="764" class="text" fill="{C['orange']}">Permeability</text>
<text x="270" y="812" class="text" fill="{C['muted']}">Year labels</text>

<!-- Panel 2 -->
{subbox(492, 130, 366, 136, 'Descriptor representation')}
<g transform="translate(528,165)">
  <circle cx="24" cy="18" r="6" fill="white" stroke="{C['ink']}" stroke-width="2"/><circle cx="75" cy="2" r="6" fill="white" stroke="{C['ink']}" stroke-width="2"/><circle cx="106" cy="45" r="6" fill="white" stroke="{C['ink']}" stroke-width="2"/>
  <line x1="24" y1="18" x2="75" y2="2" stroke="{C['ink']}" stroke-width="2"/><line x1="75" y1="2" x2="106" y2="45" stroke="{C['ink']}" stroke-width="2"/><line x1="24" y1="18" x2="45" y2="62" stroke="{C['ink']}" stroke-width="2"/>
  <text x="35" y="98" class="tiny">Physicochemical</text>
</g>
{ring(672, 194, 32, dash=True)}
<text x="635" y="263" class="tiny">Topological</text>
{ring(785, 194, 32, dash=True)}
<text x="748" y="263" class="tiny">Geometrical</text>
{subbox(492, 300, 366, 142, 'HELM representation')}
<circle cx="546" cy="370" r="34" fill="white" stroke="{C['line']}" stroke-width="2"/>
<text x="546" y="358" text-anchor="middle" class="tiny">H</text><text x="546" y="378" text-anchor="middle" class="tiny">E</text><text x="546" y="398" text-anchor="middle" class="tiny">LM</text>
<text x="604" y="340" class="tiny">PEPTIDE1{{A.A.C.D.E.F}}$$$$</text>
<text x="604" y="368" class="tiny">PEPTIDE2{{H.I.K.L.M.N}}$$$$</text>
<text x="604" y="396" class="tiny">CONNECT{{C1-C6}}$$$$</text>
<text x="604" y="424" class="tiny">CLOSE{{C1.C10}}$$$$</text>
{subbox(492, 476, 366, 184, 'Source split / LOSO CV')}
{source_grid(520, 522)}
<rect x="540" y="632" width="18" height="18" fill="white" stroke="{C['muted']}" stroke-width="1.5"/><text x="566" y="646" class="tiny">Training sources</text>
<rect x="704" y="632" width="18" height="18" fill="white" stroke="{C['ink']}" stroke-width="1.5" stroke-dasharray="5 4"/><text x="730" y="646" class="tiny">Held-out source</text>
{subbox(492, 696, 366, 186, 'Performance (LOSO)')}
{mini_roc(590, 734)}

<!-- Panel 3 -->
<circle cx="1015" cy="188" r="19" fill="{C['teal']}"/><text x="1015" y="197" text-anchor="middle" class="num" style="font-size:22px">A</text>
<text x="1050" y="197" class="route">Constrained optimization</text>
<text x="1090" y="250" class="text">Local analog edits</text>
{ring(1050, 350, 52)}
{arrow(1115, 350, 1182, 350, C['teal'])}
{ring(1260, 350, 58, dash=True)}
<text x="1360" y="350" class="text">...</text>
<line x1="952" y1="494" x2="1394" y2="494" stroke="{C['teal']}" stroke-width="3" stroke-dasharray="3 8"/>
<circle cx="1015" cy="556" r="19" fill="{C['teal']}"/><text x="1015" y="565" text-anchor="middle" class="num" style="font-size:22px">B</text>
<text x="1050" y="565" class="route">De novo generation</text>
<text x="1072" y="618" class="text">Diverse peptide rings</text>
{ring(1035, 735, 43)}
{ring(1166, 710, 43)}
{ring(1304, 738, 43)}
{ring(1100, 846, 43)}
{ring(1240, 844, 43)}
<text x="1370" y="758" class="text">...</text>
<path d="M926,360 C900,360 900,735 952,735" fill="none" stroke="{C['teal']}" stroke-width="8" stroke-linecap="round"/>

<!-- Panel 4 -->
{filter_row(1548, 190, 'Uncertainty', '(low predicted uncertainty)', 'gauge')}
<line x1="1478" y1="310" x2="1824" y2="310" stroke="{C['orange']}" stroke-width="3" stroke-dasharray="3 8"/>
{filter_row(1548, 405, 'Diversity', '(high structural diversity)', 'dots')}
<line x1="1478" y1="526" x2="1824" y2="526" stroke="{C['orange']}" stroke-width="3" stroke-dasharray="3 8"/>
{filter_row(1548, 620, 'Novelty', '(low similarity to training data)', 'finger')}
<line x1="1478" y1="742" x2="1824" y2="742" stroke="{C['orange']}" stroke-width="3" stroke-dasharray="3 8"/>
{filter_row(1548, 828, '3D polarity proxy', '(balanced polar surface)', 'surface')}

<!-- Panel 5 -->
<text x="2025" y="178" text-anchor="middle" class="route" style="font-size:22px">Optimized (route A)</text>
{ring(2025, 300, 76)}
<path d="M1995,390 l24,24 l43,-52" fill="none" stroke="{C['teal']}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
<line x1="1905" y1="506" x2="2146" y2="506" stroke="{C['blue']}" stroke-width="3" stroke-dasharray="3 8"/>
<text x="2025" y="608" text-anchor="middle" class="route" style="font-size:22px">De novo (route B)</text>
{ring(2025, 750, 76)}
<path d="M1995,840 l24,24 l43,-52" fill="none" stroke="{C['teal']}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""


def emu(v):
    return int(v)


def pptx_with_svg():
    svg_text = svg()
    # Use embedded SVG as a vector image in PowerPoint. It remains vector on export/print.
    files = {
        "[Content_Types].xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="svg" ContentType="image/svg+xml"/>
<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
<Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
</Types>""",
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>""",
        "ppt/presentation.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst><p:sldSz cx="12192000" cy="6858000" type="wide"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>""",
        "ppt/_rels/presentation.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>""",
        "ppt/slides/slide1.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
<p:pic><p:nvPicPr><p:cNvPr id="2" name="workflow.svg"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="rId1"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>
</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>""",
        "ppt/slides/_rels/slide1.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/workflow.svg"/>
</Relationships>""",
        "ppt/media/workflow.svg": svg_text,
    }
    with zipfile.ZipFile(PPTX_OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SVG_OUT.write_text(svg(), encoding="utf-8")
    pptx_with_svg()
    print(f"Saved {SVG_OUT}")
    print(f"Saved {PPTX_OUT}")


if __name__ == "__main__":
    main()
