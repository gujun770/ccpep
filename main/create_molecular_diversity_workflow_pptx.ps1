$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Out = Join-Path $ProjectRoot "molecular_diversity_workflow_reference_rich_editable.pptx"
$FigDir = Join-Path $ProjectRoot "Result\paper_figures"
$FigRoc = Join-Path $FigDir "figure2b_roc_pr_curves.png"
$FigQD = Join-Path $FigDir "figure8_quality_diversity.png"
$FigPolarity = Join-Path $FigDir "figure6_conformation_proxy.png"
$FigNovelty = Join-Path $FigDir "figure12_novelty_depth.png"

Add-Type -AssemblyName System.Drawing

$CanvasW = 1600.0
$CanvasH = 900.0
$SlideCx = 12192000
$SlideCy = 6858000

function Px($v) { [int]($v / $CanvasW * $SlideCx) }
function Py($v) { [int]($v / $CanvasH * $SlideCy) }
function Pw($v) { [int]($v / $CanvasW * $SlideCx) }
function Ph($v) { [int]($v / $CanvasH * $SlideCy) }
function Rgb($c) { $c.Replace("#", "").ToUpperInvariant() }
function Esc($s) { [System.Security.SecurityElement]::Escape([string]$s) }

$C = @{
  Ink = "#10202A"
  Muted = "#536878"
  Line = "#B8C8D6"
  Paper = "#FFFFFF"
  Bg = "#F7FBFC"
  Data = "#2C7FB8"
  Desc = "#2496A6"
  Score = "#4F6FB3"
  Design = "#189477"
  Filter = "#D17930"
  Final = "#5B5DA8"
  PaleData = "#ECF6FC"
  PaleDesc = "#ECFAFA"
  PaleScore = "#F0F4FF"
  PaleDesign = "#EEFBF5"
  PaleFilter = "#FFF5E9"
  PaleFinal = "#F4F2FF"
  Green = "#31A66A"
  Coral = "#D95F59"
  Gold = "#E2A32C"
}

$script:Sid = 1
$script:Parts = New-Object System.Collections.Generic.List[string]
$script:Media = New-Object System.Collections.Generic.List[object]
$script:ImgNo = 0

function New-Id {
  $script:Sid += 1
  return $script:Sid
}

function TextBody($Text, $Font = 12, $Bold = $false, $Color = "#10202A", $Align = "ctr") {
  $paras = New-Object System.Collections.Generic.List[string]
  foreach ($line in ([string]$Text).Split("`n")) {
    $b = if ($Bold) { "1" } else { "0" }
    $paras.Add("<a:p><a:pPr algn=""$Align""/><a:r><a:rPr lang=""en-US"" sz=""$([int]($Font * 100))"" b=""$b""><a:solidFill><a:srgbClr val=""$(Rgb $Color)""/></a:solidFill><a:latin typeface=""Arial""/><a:ea typeface=""Arial""/><a:cs typeface=""Arial""/></a:rPr><a:t>$(Esc $line)</a:t></a:r></a:p>")
  }
  return "<p:txBody><a:bodyPr wrap=""square"" anchor=""ctr""><a:spAutoFit/></a:bodyPr><a:lstStyle/>$($paras -join '')</p:txBody>"
}

function Add-Shape($X, $Y, $W, $H, $Text = $null, $Fill = "#FFFFFF", $Line = "#000000", $Lw = 1.0, $Prst = "rect", $Font = 12, $Bold = $false, $Color = "#10202A", $Align = "ctr", $Name = "shape", [switch]$NoFill, [switch]$NoLine) {
  $id = New-Id
  $fillXml = if ($NoFill) { "<a:noFill/>" } else { "<a:solidFill><a:srgbClr val=""$(Rgb $Fill)""/></a:solidFill>" }
  $lineXml = if ($NoLine) { "<a:ln><a:noFill/></a:ln>" } else { "<a:ln w=""$([int]($Lw * 12700))""><a:solidFill><a:srgbClr val=""$(Rgb $Line)""/></a:solidFill></a:ln>" }
  $tx = if ($null -ne $Text) { TextBody $Text $Font $Bold $Color $Align } else { "" }
  $script:Parts.Add(@"
<p:sp>
  <p:nvSpPr><p:cNvPr id="$id" name="$(Esc $Name)"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>
  <p:spPr>
    <a:xfrm><a:off x="$(Px $X)" y="$(Py $Y)"/><a:ext cx="$(Pw $W)" cy="$(Ph $H)"/></a:xfrm>
    <a:prstGeom prst="$Prst"><a:avLst/></a:prstGeom>
    $fillXml$lineXml
  </p:spPr>
  $tx
</p:sp>
"@)
}

function Add-Text($X, $Y, $W, $H, $Text, $Font = 12, $Bold = $false, $Color = "#10202A", $Align = "ctr", $Name = "textbox") {
  Add-Shape $X $Y $W $H $Text "#FFFFFF" "#FFFFFF" 0.0 "rect" $Font $Bold $Color $Align $Name -NoFill -NoLine
}

function Add-PictureFit($Path, $X, $Y, $W, $H, $Name = "picture") {
  if (-not (Test-Path -LiteralPath $Path)) { return }
  $script:ImgNo += 1
  $id = New-Id
  $rid = "rImg$script:ImgNo"
  $target = "../media/rich_img$script:ImgNo.png"
  $script:Media.Add([pscustomobject]@{
    RelId = $rid
    Path = $Path
    Target = $target
    PackagePath = "ppt/media/rich_img$script:ImgNo.png"
  })

  $img = [System.Drawing.Image]::FromFile($Path)
  $iw = [double]$img.Width
  $ih = [double]$img.Height
  $img.Dispose()
  $scale = [Math]::Min(([double]$W / $iw), ([double]$H / $ih))
  $dw = $iw * $scale
  $dh = $ih * $scale
  $dx = [double]$X + (([double]$W - $dw) / 2.0)
  $dy = [double]$Y + (([double]$H - $dh) / 2.0)

  $script:Parts.Add(@"
<p:pic>
  <p:nvPicPr><p:cNvPr id="$id" name="$(Esc $Name)"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>
  <p:blipFill><a:blip r:embed="$rid"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>
  <p:spPr>
    <a:xfrm><a:off x="$(Px $dx)" y="$(Py $dy)"/><a:ext cx="$(Pw $dw)" cy="$(Ph $dh)"/></a:xfrm>
    <a:prstGeom prst="rect"><a:avLst/></a:prstGeom>
    <a:ln w="6350"><a:solidFill><a:srgbClr val="CCD6E0"/></a:solidFill></a:ln>
  </p:spPr>
</p:pic>
"@)
}

function Add-Line($X1, $Y1, $X2, $Y2, $Color = "#10202A", $Lw = 1.5, [switch]$Arrow, [switch]$Dash, $Name = "line") {
  $id = New-Id
  $x = [Math]::Min($X1, $X2)
  $y = [Math]::Min($Y1, $Y2)
  $w = [Math]::Max([Math]::Abs($X2 - $X1), 0.1)
  $h = [Math]::Max([Math]::Abs($Y2 - $Y1), 0.1)
  $flipH = if ($X2 -lt $X1) { ' flipH="1"' } else { "" }
  $flipV = if ($Y2 -lt $Y1) { ' flipV="1"' } else { "" }
  $arrowXml = if ($Arrow) { '<a:tailEnd type="triangle" w="med" len="med"/>' } else { "" }
  $dashXml = if ($Dash) { '<a:prstDash val="dash"/>' } else { "" }
  $script:Parts.Add(@"
<p:cxnSp>
  <p:nvCxnSpPr><p:cNvPr id="$id" name="$(Esc $Name)"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>
  <p:spPr>
    <a:xfrm$flipH$flipV><a:off x="$(Px $x)" y="$(Py $y)"/><a:ext cx="$(Pw $w)" cy="$(Ph $h)"/></a:xfrm>
    <a:prstGeom prst="straightConnector1"><a:avLst/></a:prstGeom>
    <a:ln w="$([int]($Lw * 12700))"><a:solidFill><a:srgbClr val="$(Rgb $Color)"/></a:solidFill>$dashXml$arrowXml</a:ln>
  </p:spPr>
</p:cxnSp>
"@)
}

function Add-Ring($Cx, $Cy, $Radius, $Color = $null) {
  if ($null -eq $Color) { $Color = $C.Design }
  $Cx = [double](@($Cx)[0])
  $Cy = [double](@($Cy)[0])
  $Radius = [double](@($Radius)[0])
  $pts = @()
  for ($i = 0; $i -lt 6; $i++) {
    $a = -[Math]::PI / 2 + $i * [Math]::PI / 3
    $px0 = $Cx + ($Radius * [Math]::Cos($a))
    $py0 = $Cy + ($Radius * [Math]::Sin($a))
    $pts += ,@($px0, $py0)
  }
  for ($i = 0; $i -lt 6; $i++) {
    $p1 = $pts[$i]
    $p2 = $pts[($i + 1) % 6]
    Add-Line $p1[0] $p1[1] $p2[0] $p2[1] $C.Ink 1.4
  }
  $nodeColors = @($C.Data, $C.Desc, $C.Score, $C.Design, $C.Filter, $C.Final)
  for ($i = 0; $i -lt 6; $i++) {
    Add-Shape ($pts[$i][0] - 7) ($pts[$i][1] - 7) 14 14 $null $nodeColors[$i] $C.Ink 0.6 "ellipse"
  }
}

function Add-Database($X, $Y, $Color) {
  Add-Shape $X $Y 84 22 $null $Color $Color 0 "ellipse"
  Add-Shape $X ($Y + 12) 84 68 $null $Color $Color 0 "rect"
  Add-Shape $X ($Y + 58) 84 22 $null $Color $Color 0 "ellipse"
  Add-Line ($X + 6) ($Y + 36) ($X + 78) ($Y + 36) "#FFFFFF" 1.5
  Add-Line ($X + 6) ($Y + 58) ($X + 78) ($Y + 58) "#FFFFFF" 1.5
}

function Add-Heatmap($X, $Y) {
  $cols = @("#E85D4F", "#F0C04E", "#75B56A", "#4AA6B5", "#4F77B3")
  for ($r = 0; $r -lt 5; $r++) {
    for ($c0 = 0; $c0 -lt 5; $c0++) {
      $idx = ($r * 2 + $c0) % $cols.Count
      Add-Shape ($X + $c0 * 14) ($Y + $r * 14) 14 14 $null $cols[$idx] "#FFFFFF" 0.3 "rect"
    }
  }
}

function Add-Roc($X, $Y, $Color, $Label) {
  Add-Line $X ($Y + 86) ($X + 120) ($Y + 86) $C.Ink 0.9
  Add-Line $X ($Y + 86) $X $Y $C.Ink 0.9
  Add-Line ($X + 5) ($Y + 81) ($X + 114) ($Y + 8) $C.Line 0.9 -Dash
  $pts = @(
    @(($X + 5), ($Y + 78)),
    @(($X + 18), ($Y + 50)),
    @(($X + 38), ($Y + 35)),
    @(($X + 75), ($Y + 22)),
    @(($X + 112), ($Y + 12))
  )
  for ($i = 0; $i -lt $pts.Count - 1; $i++) {
    Add-Line $pts[$i][0] $pts[$i][1] $pts[$i + 1][0] $pts[$i + 1][1] $Color 1.8
  }
  Add-Text ($X + 10) ($Y + 91) 104 18 $Label 8 $false $C.Muted
}

function Add-Badge($X, $Y, $Text, $Color) {
  Add-Shape $X $Y 98 34 $Text "#FFFFFF" $Color 1.2 "roundRect" 11 $true $Color
}

function Add-Panel($X, $Y, $W0, $H0, $Num, $Title, $Color, $Fill) {
  Add-Shape $X $Y $W0 $H0 $null $Fill $Color 1.6 "roundRect"
  Add-Shape $X $Y $W0 56 $null $Color $Color 0 "roundRect"
  Add-Text ($X + 12) ($Y + 8) 34 34 $Num 16 $true "#FFFFFF"
  Add-Text ($X + 48) ($Y + 8) ($W0 - 60) 38 $Title 13 $true "#FFFFFF" "l"
}

Add-Shape 0 0 $CanvasW $CanvasH $null "#FFFFFF" "#FFFFFF" 0 "rect"
Add-Text 76 18 1448 60 "Descriptor-guided workflow for cyclic peptide permeability prediction and molecular diversity design" 25 $true $C.Ink
Add-Text 165 75 1270 28 "Public cyclic peptide data, source-aware scoring, dual-route design, and conservative candidate validation" 12 $false $C.Muted

$top = 126
$height = 670
$gap = 18
$w1 = 210
$w2 = 225
$w3 = 315
$w4 = 365
$w5 = 238
$x1 = 28
$x2 = $x1 + $w1 + $gap
$x3 = $x2 + $w2 + $gap
$x4 = $x3 + $w3 + $gap
$x5 = $x4 + $w4 + $gap

Add-Panel $x1 $top $w1 $height "1" "Data curation" $C.Data $C.PaleData
Add-Panel $x2 $top $w2 $height "2" "Descriptor representation" $C.Desc $C.PaleDesc
Add-Panel $x3 $top $w3 $height "3" "Source-aware permeability scoring" $C.Score $C.PaleScore
Add-Panel $x4 $top $w4 $height "4" "Dual-route candidate design" $C.Design $C.PaleDesign
Add-Panel $x5 $top $w5 $height "5" "Validation & analysis" $C.Filter $C.PaleFilter

Add-Line ($x1 + $w1 + 4) 462 ($x2 - 4) 462 $C.Muted 2.1 -Arrow
Add-Line ($x2 + $w2 + 4) 462 ($x3 - 4) 462 $C.Muted 2.1 -Arrow
Add-Line ($x3 + $w3 + 4) 462 ($x4 - 4) 462 $C.Muted 2.1 -Arrow
Add-Line ($x4 + $w4 + 4) 462 ($x5 - 4) 462 $C.Muted 2.1 -Arrow

# Stage 1
Add-Database ($x1 + 62) 218 $C.Data
Add-Text ($x1 + 26) 310 158 26 "CycPeptMPDB" 14 $true $C.Ink
Add-Text ($x1 + 32) 340 148 38 "Length-6 cyclic peptides" 11 $false $C.Muted
Add-Text ($x1 + 30) 405 150 32 "29 literature sources" 11 $true $C.Data
foreach ($i in 0..4) {
  $colors = @($C.Data, $C.Desc, $C.Score, $C.Design, $C.Filter)
  Add-Shape ($x1 + 28 + $i * 32) 452 24 24 "S$($i + 1)" $colors[$i] $colors[$i] 0 "roundRect" 7 $true "#FFFFFF"
}
Add-Heatmap ($x1 + 68) 526
Add-Text ($x1 + 30) 615 150 38 "Source labels & source shift" 10.5 $false $C.Muted

# Stage 2
Add-Ring -Cx ($x2 + 112) -Cy 224 -Radius 42 -Color ($C.Desc)
Add-Text ($x2 + 50) 286 125 28 "HELM tokens" 12.5 $true $C.Ink
Add-Shape ($x2 + 40) 350 64 48 $null "#FFFFFF" $C.Desc 1.2 "roundRect"
Add-Line ($x2 + 52) 380 ($x2 + 94) 360 $C.Desc 2 -Arrow
Add-Text ($x2 + 112) 344 94 58 "Physicochemical`ndescriptors" 11 $true $C.Ink
Add-Shape ($x2 + 42) 455 55 55 $null "#FFFFFF" $C.Desc 1.2 "roundRect"
foreach ($r in 0..3) {
  Add-Line ($x2 + 52) (468 + $r * 10) ($x2 + 86) (468 + $r * 10) $C.Line 0.9
}
Add-Text ($x2 + 112) 454 92 46 "Composition`nfeatures" 11 $true $C.Ink
Add-Shape ($x2 + 50) 570 42 42 $null "#D9E8F2" $C.Desc 1.1 "cloud"
Add-Text ($x2 + 112) 562 92 58 "3D polarity`nproxy" 11 $true $C.Ink
Add-Text ($x2 + 34) 665 158 38 "Descriptor matrix for robust representation" 10 $false $C.Muted

# Stage 3
Add-Text ($x3 + 34) 190 248 36 "Hybrid permeability scorer" 20 $true $C.Ink
Add-Shape ($x3 + 48) 262 86 54 "Training" "#FFFFFF" $C.Score 1.2 "roundRect" 11 $true $C.Score
Add-Line ($x3 + 140) 290 ($x3 + 182) 290 $C.Score 2 -Arrow
Add-Shape ($x3 + 186) 262 86 54 "Predictive`nmodel" "#FFFFFF" $C.Score 1.2 "roundRect" 11 $true $C.Score
Add-Line ($x3 + 150) 360 ($x3 + 150) 424 $C.Score 1.6 -Arrow
Add-Text ($x3 + 40) 420 240 36 "Descriptor features + HELM tokens" 12 $false $C.Muted
Add-Text ($x3 + 42) 488 230 26 "Source-aware evaluation" 13 $true $C.Score
Add-Roc ($x3 + 42) 540 $C.Score "Random split"
Add-Roc ($x3 + 172) 540 $C.Filter "Source split"
Add-Shape ($x3 + 35) 528 245 100 $null "#FFFFFF" $C.Line 0.6 "roundRect"
Add-PictureFit $FigRoc ($x3 + 40) 533 235 90 "ROC and PR curves"
Add-Badge ($x3 + 40) 670 "Group CV" $C.Score
Add-Badge ($x3 + 170) 670 "LOSO" $C.Score
Add-Text ($x3 + 44) 723 230 36 "Quantifies hidden generalization gap" 10.5 $false $C.Muted

# Stage 4
Add-Shape ($x4 + 24) 190 316 210 $null "#FFFFFF" $C.Design 1.4 "roundRect"
Add-Text ($x4 + 42) 204 278 28 "Route A: constrained optimization" 13 $true $C.Design
Add-Ring -Cx ($x4 + 74) -Cy 300 -Radius 36 -Color ($C.Design)
Add-Line ($x4 + 122) 300 ($x4 + 172) 300 $C.Design 1.8 -Arrow
Add-Shape ($x4 + 182) 270 52 52 $null "#FFFFFF" $C.Design 1.2 "gear6"
Add-Line ($x4 + 242) 300 ($x4 + 292) 300 $C.Design 1.8 -Arrow
Add-Shape ($x4 + 288) 274 38 44 $null "#E9FBF3" $C.Design 1.2 "line"
Add-Text ($x4 + 42) 345 278 30 "Local analog edits with improved predicted permeability" 10 $false $C.Muted

Add-Shape ($x4 + 24) 430 316 220 $null "#FFFFFF" $C.Design 1.4 "roundRect"
Add-Text ($x4 + 42) 446 278 28 "Route B: de novo generation" 13 $true $C.Design
Add-Shape ($x4 + 54) 512 50 62 $null "#FFFFFF" $C.Design 1.2 "roundRect"
Add-Shape ($x4 + 62) 504 50 62 $null "#F0FBF7" $C.Design 1.2 "roundRect"
Add-Text ($x4 + 41) 584 100 26 "Fragment library" 9.5 $true $C.Ink
Add-Line ($x4 + 130) 535 ($x4 + 186) 535 $C.Design 1.8 -Arrow
Add-Ring -Cx ($x4 + 220) -Cy 535 -Radius 36 -Color ($C.Design)
Add-Line ($x4 + 262) 535 ($x4 + 314) 535 $C.Design 1.8 -Arrow
Add-Text ($x4 + 76) 620 222 28 "Multi-objective optimization" 12 $true $C.Ink
Add-Text ($x4 + 48) 680 268 34 "permeability + polarity + diversity + uncertainty" 10 $false $C.Muted

# Stage 5
Add-Text ($x5 + 36) 190 166 26 "Validation filters" 13 $true $C.Filter
Add-Shape ($x5 + 25) 228 188 62 $null "#FFFFFF" $C.Line 0.6 "roundRect"
Add-PictureFit $FigQD ($x5 + 29) 232 180 54 "Quality-diversity panel"
Add-Text ($x5 + 37) 293 164 18 "quality-diversity" 8.5 $true $C.Ink
Add-Shape ($x5 + 25) 322 188 58 $null "#FFFFFF" $C.Line 0.6 "roundRect"
Add-PictureFit $FigNovelty ($x5 + 29) 326 180 50 "Novelty-depth panel"
Add-Text ($x5 + 46) 383 146 18 "novelty depth" 8.5 $true $C.Ink
Add-Badge ($x5 + 36) 420 "Uncertainty" $C.Filter
Add-Shape ($x5 + 25) 465 188 62 $null "#FFFFFF" $C.Line 0.6 "roundRect"
Add-PictureFit $FigPolarity ($x5 + 29) 469 180 54 "3D polarity proxy panel"
Add-Text ($x5 + 37) 530 164 18 "3D polarity proxy" 8.5 $true $C.Ink
Add-Shape ($x5 + 34) 638 76 76 "12" "#FFFFFF" $C.Design 2.2 "roundRect" 31 $true $C.Design
Add-Text ($x5 + 116) 646 92 48 "optimized`ncandidates" 11 $true $C.Ink "l"
Add-Shape ($x5 + 34) 724 76 76 "24" "#FFFFFF" $C.Filter 2.2 "roundRect" 31 $true $C.Filter
Add-Text ($x5 + 116) 732 92 48 "de novo`ncandidates" 11 $true $C.Ink "l"

Add-Shape 112 827 1376 42 "Output: membrane-permeable cyclic peptide candidates prioritized by prediction, molecular diversity, novelty depth, uncertainty, and 3D polarity-proxy evidence" "#F7FAFC" $C.Line 1.0 "roundRect" 12 $false $C.Ink

$SlideXml = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree>
    <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
    <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>
    $($script:Parts -join "`n")
  </p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>
"@

$MediaRels = ($script:Media | ForEach-Object {
  '<Relationship Id="' + $_.RelId + '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="' + $_.Target + '"/>'
}) -join "`n"

$Files = @{
  "[Content_Types].xml" = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="png" ContentType="image/png"/>
<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
<Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"@
  "_rels/.rels" = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"@
  "docProps/core.xml" = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Molecular Diversity workflow figure</dc:title></cp:coreProperties>
"@
  "docProps/app.xml" = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>Codex OpenXML</Application><Slides>1</Slides></Properties>
"@
  "ppt/presentation.xml" = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>
<p:sldIdLst><p:sldId id="256" r:id="rId2"/></p:sldIdLst>
<p:sldSz cx="$SlideCx" cy="$SlideCy" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/>
</p:presentation>
"@
  "ppt/_rels/presentation.xml.rels" = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>
"@
  "ppt/slides/slide1.xml" = $SlideXml
  "ppt/slides/_rels/slide1.xml.rels" = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
$MediaRels
</Relationships>
"@
  "ppt/slideMasters/slideMaster1.xml" = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
</p:sldMaster>
"@
  "ppt/slideMasters/_rels/slideMaster1.xml.rels" = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>
"@
  "ppt/slideLayouts/slideLayout1.xml" = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
<p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>
"@
  "ppt/slideLayouts/_rels/slideLayout1.xml.rels" = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>
"@
  "ppt/theme/theme1.xml" = @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Molecular Diversity Workflow">
<a:themeElements>
<a:clrScheme name="Office"><a:dk1><a:srgbClr val="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="10202A"/></a:dk2><a:lt2><a:srgbClr val="F7FBFC"/></a:lt2><a:accent1><a:srgbClr val="2C7FB8"/></a:accent1><a:accent2><a:srgbClr val="2496A6"/></a:accent2><a:accent3><a:srgbClr val="189477"/></a:accent3><a:accent4><a:srgbClr val="D17930"/></a:accent4><a:accent5><a:srgbClr val="5B5DA8"/></a:accent5><a:accent6><a:srgbClr val="536878"/></a:accent6><a:hlink><a:srgbClr val="0563C1"/></a:hlink><a:folHlink><a:srgbClr val="954F72"/></a:folHlink></a:clrScheme>
<a:fontScheme name="Arial"><a:majorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme>
<a:fmtScheme name="Default">
<a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:schemeClr val="phClr"/></a:gs><a:gs pos="100000"><a:schemeClr val="phClr"/></a:gs></a:gsLst><a:lin ang="5400000" scaled="0"/></a:gradFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>
<a:lnStyleLst><a:ln w="9525" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln><a:ln w="25400" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln><a:ln w="38100" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln></a:lnStyleLst>
<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>
<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>
</a:fmtScheme>
</a:themeElements>
</a:theme>
"@
}

if (Test-Path -LiteralPath $Out) {
  Remove-Item -LiteralPath $Out -Force
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$fs = [System.IO.File]::Open($Out, [System.IO.FileMode]::CreateNew)
try {
  $zip = New-Object System.IO.Compression.ZipArchive($fs, [System.IO.Compression.ZipArchiveMode]::Create)
  try {
    foreach ($key in $Files.Keys) {
      $entry = $zip.CreateEntry($key)
      $stream = $entry.Open()
      $writer = New-Object System.IO.StreamWriter($stream, [System.Text.UTF8Encoding]::new($false))
      try { $writer.Write($Files[$key]) }
      finally { $writer.Dispose() }
    }
    foreach ($media in $script:Media) {
      $entry = $zip.CreateEntry($media.PackagePath)
      $stream = $entry.Open()
      $bytes = [System.IO.File]::ReadAllBytes($media.Path)
      try { $stream.Write($bytes, 0, $bytes.Length) }
      finally { $stream.Dispose() }
    }
  }
  finally { $zip.Dispose() }
}
finally { $fs.Dispose() }

Write-Host "Saved $Out"
