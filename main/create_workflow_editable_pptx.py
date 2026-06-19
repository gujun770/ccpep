import math
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cyclic_peptide_workflow_editable_native_v2.pptx"

CANVAS_W = 2200
CANVAS_H = 1000
SLIDE_CX = 14859000
SLIDE_CY = 6750000


def X(v):
    return int(v / CANVAS_W * SLIDE_CX)


def Y(v):
    return int(v / CANVAS_H * SLIDE_CY)


def W(v):
    return int(v / CANVAS_W * SLIDE_CX)


def H(v):
    return int(v / CANVAS_H * SLIDE_CY)


def rgb(c):
    return c.replace("#", "").upper()


C = {
    "blue": "#0B4FA3",
    "blue2": "#1769C2",
    "teal": "#008C87",
    "teal2": "#12A39B",
    "orange": "#E26A16",
    "orange2": "#F08A2B",
    "ink": "#111827",
    "muted": "#4B5563",
    "line": "#B9C9DC",
    "paper": "#FFFFFF",
    "light_blue": "#F7FBFF",
    "light_teal": "#F6FFFD",
    "light_orange": "#FFF8F1",
    "cream": "#FDEBD7",
    "green": "#26A65B",
    "purple": "#7E6AB8",
    "red": "#D84A4A",
    "yellow": "#F2A91F",
    "cyan": "#42B7B4",
    "gray": "#9CA3AF",
}


class Builder:
    def __init__(self):
        self.parts = []
        self.sid = 10

    def next_id(self):
        self.sid += 1
        return self.sid

    def shape(self, x, y, w, h, prst="rect", fill="#FFFFFF", line="#000000", lw=1.0,
              text=None, font=12, bold=False, color=None, align="ctr", name="shape",
              radius=False, no_line=False, no_fill=False):
        sid = self.next_id()
        prst = "roundRect" if radius else prst
        fill_xml = "<a:noFill/>" if no_fill else f'<a:solidFill><a:srgbClr val="{rgb(fill)}"/></a:solidFill>'
        if no_line:
            line_xml = "<a:ln><a:noFill/></a:ln>"
        else:
            line_xml = f'<a:ln w="{int(lw * 12700)}"><a:solidFill><a:srgbClr val="{rgb(line)}"/></a:solidFill></a:ln>'
        tx = ""
        if text is not None:
            tx = self.text_body(text, font, bold, color or C["ink"], align)
        self.parts.append(f"""
        <p:sp>
          <p:nvSpPr><p:cNvPr id="{sid}" name="{escape(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
          <p:spPr>
            <a:xfrm><a:off x="{X(x)}" y="{Y(y)}"/><a:ext cx="{W(w)}" cy="{H(h)}"/></a:xfrm>
            <a:prstGeom prst="{prst}"><a:avLst/></a:prstGeom>
            {fill_xml}{line_xml}
          </p:spPr>
          {tx}
        </p:sp>""")
        return sid

    def block_arrow(self, x, y, w, h, color, name="block arrow"):
        self.shape(x, y, w, h, prst="rightArrow", fill=color, line=color, lw=0.0, name=name)

    def text_body(self, content, font, bold, color, align):
        paras = []
        for line in str(content).split("\n"):
            paras.append(
                f'<a:p><a:pPr algn="{align}"/>'
                f'<a:r><a:rPr lang="en-US" sz="{int(font * 100)}" b="{1 if bold else 0}">'
                f'<a:latin typeface="Arial"/><a:solidFill><a:srgbClr val="{rgb(color)}"/></a:solidFill>'
                f'</a:rPr><a:t>{escape(line)}</a:t></a:r></a:p>'
            )
        return '<p:txBody><a:bodyPr wrap="square" anchor="mid"><a:spAutoFit/></a:bodyPr><a:lstStyle/>' + "".join(paras) + '</p:txBody>'

    def textbox(self, x, y, w, h, text, font=12, bold=False, color=None, align="ctr", name="textbox"):
        return self.shape(x, y, w, h, fill="#FFFFFF", no_fill=True, no_line=True,
                          text=text, font=font, bold=bold, color=color or C["ink"], align=align, name=name)

    def line(self, x1, y1, x2, y2, color="#000000", lw=1.5, arrow=False, dash=False, name="line"):
        sid = self.next_id()
        x = min(x1, x2)
        y = min(y1, y2)
        ww = max(abs(x2 - x1), 0.1)
        hh = max(abs(y2 - y1), 0.1)
        flip_h = ' flipH="1"' if x2 < x1 else ""
        flip_v = ' flipV="1"' if y2 < y1 else ""
        arrow_xml = '<a:tailEnd type="triangle" w="med" len="med"/>' if arrow else ""
        dash_xml = '<a:prstDash val="dash"/>' if dash else ""
        self.parts.append(f"""
        <p:cxnSp>
          <p:nvCxnSpPr><p:cNvPr id="{sid}" name="{escape(name)}"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>
          <p:spPr>
            <a:xfrm{flip_h}{flip_v}><a:off x="{X(x)}" y="{Y(y)}"/><a:ext cx="{W(ww)}" cy="{H(hh)}"/></a:xfrm>
            <a:prstGeom prst="straightConnector1"><a:avLst/></a:prstGeom>
            <a:ln w="{int(lw * 12700)}"><a:solidFill><a:srgbClr val="{rgb(color)}"/></a:solidFill>{dash_xml}{arrow_xml}</a:ln>
          </p:spPr>
        </p:cxnSp>""")

    def card(self, x, y, w, h, color, fill, num, title):
        self.shape(x, y, w, h, fill=fill, line=color, lw=2.0, radius=True, name=f"card {num}")
        self.shape(x + 20, y + 20, 48, 48, prst="ellipse", fill=color, line=color, text=str(num), font=22, bold=True, color="#FFFFFF", name=f"number {num}")
        self.textbox(x + 82, y + 18, w - 100, 54, title, font=20, bold=True, color=color, align="l", name=f"title {num}")

    def subbox(self, x, y, w, h, title, color=C["blue2"]):
        self.shape(x, y, w, h, fill="#FFFFFF", line=C["line"], lw=1.2, radius=True, name=title)
        self.textbox(x + 16, y + 8, w - 32, 26, title, font=13, bold=True, color=color, align="l")

    def ring(self, cx, cy, r, colors=None, dashed_edges=()):
        colors = colors or [C["blue2"], C["purple"], C["green"], C["cyan"], C["orange2"], C["gray"]]
        pts = []
        for i in range(6):
            a = -math.pi / 2 + i * math.pi / 3
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        for i in range(6):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % 6]
            self.line(x1, y1, x2, y2, C["ink"], 1.2, dash=i in dashed_edges, name="ring edge")
        for i, (x, y) in enumerate(pts):
            self.shape(x - 9, y - 9, 18, 18, prst="ellipse", fill=colors[i % len(colors)], line=C["ink"], lw=0.7, name="monomer node")

    def db_icon(self, x, y):
        self.shape(x, y, 112, 34, prst="ellipse", fill=C["blue"], line=C["blue"], name="database top")
        self.shape(x, y + 17, 112, 86, fill=C["blue"], line=C["blue"], name="database body")
        self.shape(x, y + 52, 112, 34, prst="ellipse", fill=C["blue"], line=C["blue"], name="database bottom")
        for yy in (y + 45, y + 73):
            self.line(x + 4, yy, x + 108, yy, "#FFFFFF", 2.0, name="database divider")
        self.shape(x + 88, y + 45, 8, 8, prst="ellipse", fill="#FFFFFF", line="#FFFFFF")
        self.shape(x + 88, y + 72, 8, 8, prst="ellipse", fill="#FFFFFF", line="#FFFFFF")

    def docs_icon(self, x, y):
        self.shape(x + 30, y, 116, 132, fill="#EEF5FF", line=C["blue"], lw=1.3, radius=True)
        self.shape(x + 15, y + 24, 116, 132, fill="#F8FBFF", line=C["blue"], lw=1.3, radius=True)
        self.shape(x, y + 48, 116, 132, fill="#FFFFFF", line=C["blue"], lw=1.5, radius=True)
        for yy, ww in [(y + 90, 72), (y + 114, 74), (y + 138, 55)]:
            self.line(x + 22, yy, x + 22 + ww, yy, C["line"], 1.0)

    def mini_roc(self, x, y):
        self.line(x, y + 108, x + 150, y + 108, C["ink"], 1.0)
        self.line(x, y + 108, x, y, C["ink"], 1.0)
        self.line(x + 5, y + 103, x + 144, y + 8, C["gray"], 0.8, dash=True)
        # step-like approximation of ROC curve
        pts = [(x + 5, y + 100), (x + 18, y + 65), (x + 38, y + 44), (x + 75, y + 31), (x + 112, y + 22), (x + 150, y + 13)]
        for a, b in zip(pts, pts[1:]):
            self.line(a[0], a[1], b[0], b[1], C["blue2"], 1.7)
        self.textbox(x + 85, y + 68, 42, 22, "AUC", font=10, align="ctr")
        self.textbox(x + 30, y + 118, 118, 18, "False Positive Rate", font=7, align="ctr")

    def source_grid(self, x, y):
        cols = ["Fold 1", "Fold 2", "...", "Fold N"]
        colors = [C["blue2"], C["purple"], C["green"], C["orange2"], C["gray"]]
        for col, label in enumerate(cols):
            self.textbox(x + col * 58, y, 54, 18, label, font=7, align="ctr")
            for row in range(5):
                xx = x + col * 58 + (row % 2) * 22
                yy = y + 22 + row * 24
                self.shape(xx, yy, 15, 18, fill="#FFFFFF", line=colors[row], lw=1.0, radius=False, name="source cell")

    def filter_row(self, cx, cy, label, desc, icon):
        self.shape(cx - 56, cy - 56, 112, 112, prst="ellipse", fill=C["cream"], line=C["cream"], name=label)
        if icon == "gauge":
            for i in range(7):
                angle = math.pi * (1 + i / 6)
                x1 = cx + 34 * math.cos(angle)
                y1 = cy + 34 * math.sin(angle)
                x2 = cx + 44 * math.cos(angle)
                y2 = cy + 44 * math.sin(angle)
                self.line(x1, y1, x2, y2, C["ink"], 1.0)
            self.line(cx - 42, cy + 12, cx + 42, cy + 12, C["ink"], 1.0)
            self.line(cx, cy + 12, cx + 23, cy - 18, C["ink"], 2.1)
            self.shape(cx - 5, cy + 7, 10, 10, prst="ellipse", fill=C["ink"], line=C["ink"])
        elif icon == "dots":
            palette = [C["red"], C["blue"], C["teal"], C["orange2"], C["green"]]
            for i in range(25):
                self.shape(cx - 34 + (i % 6) * 13, cy - 28 + (i // 6) * 14, 7, 7, prst="ellipse", fill=palette[i % 5], line=palette[i % 5])
        elif icon == "finger":
            for i in range(6):
                self.shape(cx - 38 + i * 8, cy - 35 + i * 4, 76 - i * 12, 96 - i * 8, prst="arc", fill="#FFFFFF", line=C["ink"], lw=1.2, no_fill=True)
        else:
            self.shape(cx - 36, cy - 20, 72, 58, prst="cloud", fill="#DDE7F2", line="#607D8B", lw=1.0)
            self.shape(cx - 25, cy - 8, 34, 34, prst="ellipse", fill=C["blue2"], line=C["blue2"])
            self.shape(cx + 3, cy, 34, 34, prst="ellipse", fill=C["red"], line=C["red"])
            self.shape(cx - 44, cy + 50, 88, 7, fill=C["blue2"], line=C["blue2"])
            self.shape(cx - 4, cy + 50, 44, 7, fill=C["red"], line=C["red"])
        self.textbox(cx + 82, cy - 22, 220, 28, label, font=15, bold=True, color=C["ink"], align="l")
        self.textbox(cx + 82, cy + 8, 220, 48, desc, font=10.5, color=C["muted"], align="l")

    def build(self):
        # Background
        self.shape(0, 0, CANVAS_W, CANVAS_H, fill="#FFFFFF", line="#FFFFFF")
        # Cards
        self.card(26, 34, 424, 900, C["blue"], C["light_blue"], 1, "Public CycPeptMPDB data")
        self.card(478, 34, 402, 900, C["blue2"], C["light_blue"], 2, "Source-aware predictor")
        self.card(926, 34, 500, 900, C["teal"], C["light_teal"], 3, "Dual-route design")
        self.card(1460, 34, 382, 900, C["orange"], C["light_orange"], 4, "Safety filters")
        self.card(1876, 34, 298, 900, C["blue"], C["light_blue"], 5, "Validated shortlist")
        # Large module-to-module arrows. These intentionally overlap the card margins
        # slightly, matching the reference figure and avoiding skinny connector drift.
        self.block_arrow(430, 454, 72, 52, C["blue2"], "data to predictor")
        self.block_arrow(856, 454, 84, 52, C["blue2"], "predictor to design")
        self.block_arrow(1406, 454, 72, 52, C["teal"], "design to filters")
        self.block_arrow(1818, 454, 72, 52, C["orange"], "filters to shortlist")

        # Panel 1
        self.db_icon(78, 220)
        self.ring(270, 212, 64)
        self.ring(220, 376, 44)
        self.ring(338, 352, 46)
        self.textbox(236, 418, 70, 28, "...", font=18)
        self.docs_icon(62, 560)
        for i, (label, col) in enumerate([
            ("CycPeptMPDB", C["blue"]), ("HELM strings", C["teal"]), ("Sources", C["green"]),
            ("Permeability", C["orange"]), ("Year labels", C["muted"])
        ]):
            self.textbox(270, 612 + i * 48, 150, 26, label, font=12, color=col, align="l")

        # Panel 2
        self.subbox(492, 130, 366, 136, "Descriptor representation")
        self.shape(530, 166, 9, 9, prst="ellipse", fill="#FFFFFF", line=C["ink"])
        self.shape(575, 147, 9, 9, prst="ellipse", fill="#FFFFFF", line=C["ink"])
        self.shape(626, 190, 9, 9, prst="ellipse", fill="#FFFFFF", line=C["ink"])
        self.line(534, 170, 579, 151, C["ink"], 1.0)
        self.line(579, 151, 630, 194, C["ink"], 1.0)
        self.textbox(516, 234, 128, 20, "Physicochemical", font=7.5)
        self.ring(672, 194, 32, dashed_edges=(1, 2))
        self.textbox(632, 234, 90, 20, "Topological", font=7.5)
        self.ring(790, 194, 32, dashed_edges=(0, 3))
        self.textbox(746, 234, 92, 20, "Geometrical", font=7.5)
        self.subbox(492, 300, 366, 142, "HELM representation")
        self.shape(522, 340, 62, 62, prst="ellipse", fill="#FFFFFF", line=C["line"])
        self.textbox(532, 345, 42, 48, "H\nE\nLM", font=10)
        for i, s in enumerate(["PEPTIDE1{A.A.C.D.E.F}$$$$", "PEPTIDE2{H.I.K.L.M.N}$$$$", "CONNECT{C1-C6}$$$$", "CLOSE{C1.C10}$$$$"]):
            self.textbox(604, 333 + i * 26, 226, 20, s, font=8.5, align="l")
        self.subbox(492, 476, 366, 184, "Source split / LOSO CV")
        self.source_grid(520, 522)
        self.shape(540, 632, 18, 18, fill="#FFFFFF", line=C["muted"])
        self.textbox(566, 628, 120, 22, "Training sources", font=8, align="l")
        self.shape(704, 632, 18, 18, fill="#FFFFFF", line=C["ink"])
        self.textbox(730, 628, 120, 22, "Held-out source", font=8, align="l")
        self.subbox(492, 696, 366, 186, "Performance (LOSO)")
        self.mini_roc(590, 734)

        # Panel 3
        self.shape(1010, 170, 38, 38, prst="ellipse", fill=C["teal"], line=C["teal"], text="A", font=14, bold=True, color="#FFFFFF")
        self.textbox(1064, 170, 300, 44, "Constrained optimization", font=16, bold=True, color=C["teal"], align="l")
        self.textbox(1094, 238, 210, 28, "Local analog edits", font=12)
        self.ring(1066, 350, 54)
        self.block_arrow(1132, 334, 54, 34, C["teal"], "local edit arrow")
        self.ring(1270, 350, 60, dashed_edges=(1, 2, 3))
        self.textbox(1350, 333, 48, 30, "...", font=16)
        self.line(950, 494, 1398, 494, C["teal"], 2.0, dash=True)
        self.shape(1010, 538, 38, 38, prst="ellipse", fill=C["teal"], line=C["teal"], text="B", font=14, bold=True, color="#FFFFFF")
        self.textbox(1064, 538, 300, 44, "De novo generation", font=16, bold=True, color=C["teal"], align="l")
        self.textbox(1080, 606, 220, 28, "Diverse peptide rings", font=12)
        for cx, cy in [(1044, 735), (1172, 710), (1304, 738), (1106, 846), (1242, 844)]:
            self.ring(cx, cy, 43)
        self.textbox(1360, 742, 56, 30, "...", font=16)
        # Branching arrow inside design panel: vertical trunk plus two aligned arrows.
        self.line(936, 355, 936, 736, C["teal"], 4.0, name="design branch trunk")
        self.line(936, 355, 982, 355, C["teal"], 4.0, arrow=True, name="branch to optimization")
        self.line(936, 736, 982, 736, C["teal"], 4.0, arrow=True, name="branch to denovo")

        # Panel 4
        self.filter_row(1548, 190, "Uncertainty", "(low predicted\nuncertainty)", "gauge")
        self.line(1478, 310, 1824, 310, C["orange"], 1.6, dash=True)
        self.filter_row(1548, 405, "Diversity", "(high structural\ndiversity)", "dots")
        self.line(1478, 526, 1824, 526, C["orange"], 1.6, dash=True)
        self.filter_row(1548, 620, "Novelty", "(low similarity to\ntraining data)", "finger")
        self.line(1478, 742, 1824, 742, C["orange"], 1.6, dash=True)
        self.filter_row(1548, 828, "3D polarity proxy", "(balanced polar\nsurface)", "surface")

        # Panel 5
        self.textbox(1920, 160, 214, 35, "Optimized (route A)", font=14, bold=True, color=C["teal"])
        self.ring(2025, 300, 76)
        self.line(1995, 390, 2019, 414, C["teal"], 4.0)
        self.line(2019, 414, 2062, 362, C["teal"], 4.0)
        self.line(1905, 506, 2146, 506, C["blue"], 1.8, dash=True)
        self.textbox(1920, 590, 214, 35, "De novo (route B)", font=14, bold=True, color=C["teal"])
        self.ring(2025, 750, 76)
        self.line(1995, 840, 2019, 864, C["teal"], 4.0)
        self.line(2019, 864, 2062, 812, C["teal"], 4.0)

    def xml(self):
        self.build()
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
    {''.join(self.parts)}
  </p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>"""


def write_pptx():
    slide = Builder().xml()
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
</Types>""",
        "_rels/.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>""",
        "ppt/presentation.xml": f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst><p:sldIdLst><p:sldId id="256" r:id="rId2"/></p:sldIdLst>
<p:sldSz cx="{SLIDE_CX}" cy="{SLIDE_CY}" type="custom"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>""",
        "ppt/_rels/presentation.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>""",
        "ppt/slides/slide1.xml": slide,
        "ppt/slides/_rels/slide1.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/></Relationships>""",
        "ppt/slideMasters/slideMaster1.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/><p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst></p:sldMaster>""",
        "ppt/slideMasters/_rels/slideMaster1.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/></Relationships>""",
        "ppt/slideLayouts/slideLayout1.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1"><p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>""",
        "ppt/slideLayouts/_rels/slideLayout1.xml.rels": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/></Relationships>""",
        "ppt/theme/theme1.xml": """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Scientific editable"><a:themeElements><a:clrScheme name="Office"><a:dk1><a:srgbClr val="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="111827"/></a:dk2><a:lt2><a:srgbClr val="F7FBFF"/></a:lt2><a:accent1><a:srgbClr val="0B4FA3"/></a:accent1><a:accent2><a:srgbClr val="008C87"/></a:accent2><a:accent3><a:srgbClr val="E26A16"/></a:accent3><a:accent4><a:srgbClr val="7E6AB8"/></a:accent4><a:accent5><a:srgbClr val="26A65B"/></a:accent5><a:accent6><a:srgbClr val="4B5563"/></a:accent6><a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink></a:clrScheme><a:fontScheme name="Arial"><a:majorFont><a:latin typeface="Arial"/></a:majorFont><a:minorFont><a:latin typeface="Arial"/></a:minorFont></a:fontScheme><a:fmtScheme name="Default"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>""",
    }
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    write_pptx()
