$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Out = Join-Path $ProjectRoot "molecular_diversity_workflow_reference_like_editable.pptx"
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

function Add-DocIcon($X, $Y, $Color) {
  $X = [double](@($X)[0]); $Y = [double](@($Y)[0])
  Add-Shape $X $Y 42 52 $null $Color "#123044" 1.0 "roundRect"
  Add-Shape ($X + 28) $Y 14 14 $null "#F7FBFC" "#123044" 0.8 "rtTriangle"
  Add-Line ($X + 9) ($Y + 21) ($X + 30) ($Y + 21) "#123044" 1.0
  Add-Line ($X + 9) ($Y + 32) ($X + 32) ($Y + 32) "#123044" 1.0
  Add-Line ($X + 9) ($Y + 43) ($X + 29) ($Y + 43) "#123044" 1.0
}

function Add-DescriptorTrend($X, $Y) {
  $X = [double](@($X)[0]); $Y = [double](@($Y)[0])
  Add-Line $X ($Y + 120) ($X + 140) ($Y + 120) $C.Ink 1.3 -Arrow
  Add-Line $X ($Y + 120) $X ($Y + 8) $C.Ink 1.3 -Arrow
  $pts = @(
    @(($X + 18), ($Y + 100)),
    @(($X + 48), ($Y + 72)),
    @(($X + 78), ($Y + 83)),
    @(($X + 104), ($Y + 55)),
    @(($X + 128), ($Y + 25))
  )
  for ($i = 0; $i -lt $pts.Count - 1; $i++) {
    Add-Line $pts[$i][0] $pts[$i][1] $pts[$i+1][0] $pts[$i+1][1] $C.Desc 2.2
  }
  foreach ($p in $pts) {
    Add-Shape ($p[0]-7) ($p[1]-7) 14 14 $null $C.Desc $C.Ink 0.7 "ellipse"
  }
}

function Add-PolarityBlob($X, $Y, $S = 1.0) {
  $X = [double](@($X)[0]); $Y = [double](@($Y)[0]); $S = [double](@($S)[0])
  $parts = @(
    @(24,24,58,50,"#BFD3F6"), @(58,18,62,58,"#EAF0F8"), @(94,34,62,54,"#F7B4A8"),
    @(35,60,74,58,"#E8ECF2"), @(82,66,70,52,"#DCE4EF"), @(10,50,58,52,"#AFC6EF"),
    @(118,58,48,46,"#E77E70")
  )
  foreach ($p in $parts) {
    Add-Shape ($X + $p[0]*$S) ($Y + $p[1]*$S) ($p[2]*$S) ($p[3]*$S) $null $p[4] "#C6CFD9" 0.45 "ellipse"
  }
  Add-Shape ($X + 24*$S) ($Y + 24*$S) (132*$S) (96*$S) $null "#FFFFFF" "#8896A8" 0.6 "cloud" -NoFill
}

function Add-Fingerprint($X, $Y, $Color) {
  $X = [double](@($X)[0]); $Y = [double](@($Y)[0])
  foreach ($i in 0..6) {
    $w = 24 + $i * 17
    $h = 34 + $i * 22
    Add-Shape ($X + (108 - $w)/2) ($Y + (126 - $h)/2) $w $h $null "#FFFFFF" $Color 2.2 "arc" -NoFill
  }
  Add-Line ($X + 52) ($Y + 85) ($X + 52) ($Y + 122) $Color 2.0
}

function Add-Gauge($X, $Y) {
  $X = [double](@($X)[0]); $Y = [double](@($Y)[0])
  Add-Shape $X $Y 78 78 $null "#EAF3FB" $C.Score 1.1 "arc"
  Add-Shape ($X + 8) ($Y + 8) 62 62 $null "#FFFFFF" "#FFFFFF" 0 "arc"
  Add-Line ($X + 39) ($Y + 51) ($X + 58) ($Y + 28) $C.Score 2.1
  Add-Shape ($X + 34) ($Y + 46) 10 10 $null $C.Score $C.Score 0 "ellipse"
}

function Add-Uncertainty($X, $Y) {
  $X = [double](@($X)[0]); $Y = [double](@($Y)[0])
  Add-Line $X ($Y + 92) ($X + 154) ($Y + 92) $C.Ink 1.0
  Add-Line $X ($Y + 92) $X ($Y + 8) $C.Ink 1.0
  Add-Shape ($X + 26) ($Y + 32) 40 32 $null "#D8E6FF" "#D8E6FF" 0 "ellipse"
  Add-Shape ($X + 86) ($Y + 28) 54 34 $null "#D8E6FF" "#D8E6FF" 0 "ellipse"
  $pts = @(
    @(($X + 8), ($Y + 68)),
    @(($X + 32), ($Y + 42)),
    @(($X + 60), ($Y + 55)),
    @(($X + 86), ($Y + 70)),
    @(($X + 112), ($Y + 38)),
    @(($X + 136), ($Y + 43)),
    @(($X + 154), ($Y + 30))
  )
  for ($i = 0; $i -lt $pts.Count - 1; $i++) { Add-Line $pts[$i][0] $pts[$i][1] $pts[$i+1][0] $pts[$i+1][1] $C.Score 2.0 }
  foreach ($p in $pts) { Add-Shape ($p[0]-4) ($p[1]-4) 8 8 $null "#86B4EA" $C.Score 0.8 "ellipse" }
}

function Add-Scatter($X, $Y) {
  $X = [double](@($X)[0]); $Y = [double](@($Y)[0])
  Add-Line $X ($Y + 118) ($X + 186) ($Y + 118) $C.Ink 1.0 -Arrow
  Add-Line $X ($Y + 118) $X $Y $C.Ink 1.0 -Arrow
  $clusters = @(
    @("#4A9AD6", 54, 38), @("#5DBB88", 65, 88), @("#A16AC7", 142, 82), @("#F0A64C", 138, 36)
  )
  foreach ($cl in $clusters) {
    for ($i = 0; $i -lt 18; $i++) {
      $dx = (($i * 17) % 35) - 17
      $dy = (($i * 29) % 29) - 14
      Add-Shape ($X + $cl[1] + $dx) ($Y + $cl[2] + $dy) 6 6 $null $cl[0] $C.Ink 0.25 "ellipse"
    }
  }
}

Add-Shape 0 0 $CanvasW $CanvasH $null "#F7FBFC" "#F7FBFC" 0 "rect"
Add-Text 165 24 1270 92 "Descriptor-guided workflow for cyclic peptide permeability prediction`nand molecular diversity design" 29 $true $C.Ink

$top = 140
$height = 740
$w1 = 245
$w2 = 235
$w3 = 330
$w4 = 380
$w5 = 250
$x1 = 28
$x2 = 300
$x3 = 558
$x4 = 915
$x5 = 1322

Add-Panel $x1 $top $w1 $height "1." "Data curation" $C.Data $C.PaleData
Add-Panel $x2 $top $w2 $height "2." "Descriptor`nrepresentation" $C.Desc $C.PaleDesc
Add-Panel $x3 $top $w3 $height "3." "Source-aware scoring" $C.Score $C.PaleScore
Add-Panel $x4 $top $w4 $height "4." "Dual-route design" $C.Design $C.PaleDesign
Add-Panel $x5 $top $w5 $height "5." "Validation & analysis" $C.Filter $C.PaleFilter

Add-Line ($x1 + $w1 + 7) 500 ($x2 - 8) 500 $C.Score 4.0 -Arrow
Add-Line ($x2 + $w2 + 7) 500 ($x3 - 8) 500 $C.Score 4.0 -Arrow
Add-Line ($x3 + $w3 + 7) 500 ($x4 - 8) 500 $C.Score 4.0 -Arrow
Add-Line ($x4 + $w4 + 7) 500 ($x5 - 8) 500 $C.Score 4.0 -Arrow

# Stage 1: data curation
Add-Database ($x1 + 80) 235 $C.Data
Add-Text ($x1 + 38) 365 168 30 "CycPeptMPDB" 15 $true $C.Ink
Add-Line ($x1 + 122) 407 ($x1 + 122) 452 $C.Score 4.0 -Arrow
Add-DocIcon ($x1 + 28) 485 $C.Data
Add-DocIcon ($x1 + 78) 485 $C.Desc
Add-DocIcon ($x1 + 128) 485 $C.Final
Add-DocIcon ($x1 + 178) 485 $C.Filter
Add-Text ($x1 + 34) 560 178 34 "Literature sources" 14 $true $C.Ink
Add-Heatmap ($x1 + 70) 645
Add-Text ($x1 + 52) 776 142 28 "Source shift" 14 $true $C.Ink

# Stage 2: descriptor representation
Add-DescriptorTrend ($x2 + 52) 245
Add-Text ($x2 + 52) 384 140 28 "2D descriptors" 13.5 $true $C.Ink
Add-PolarityBlob ($x2 + 36) 423 0.95
Add-Text ($x2 + 48) 556 148 28 "3D polarity proxy" 13.5 $true $C.Ink
Add-Fingerprint ($x2 + 60) 612 $C.Desc
Add-Text ($x2 + 60) 764 130 28 "Fingerprints" 13.5 $true $C.Ink

# Stage 3: source-aware scoring
Add-Text ($x3 + 42) 220 250 30 "Hybrid permeability scorer" 15 $true $C.Ink
Add-Shape ($x3 + 38) 274 104 78 $null "#FFFFFF" $C.Score 1.3 "roundRect"
Add-Ring -Cx ($x3 + 90) -Cy 313 -Radius 32 -Color ($C.Score)
Add-Text ($x3 + 48) 365 86 48 "Model`ntraining" 12.5 $true $C.Ink
Add-Line ($x3 + 153) 312 ($x3 + 205) 312 $C.Score 3.0 -Arrow
Add-Shape ($x3 + 220) 274 104 78 $null "#FFFFFF" $C.Score 1.3 "roundRect"
Add-Gauge ($x3 + 233) 284
Add-Text ($x3 + 225) 365 94 48 "Predictive`nmodel" 12.5 $true $C.Ink
Add-Line ($x3 + 172) 402 ($x3 + 172) 462 $C.Score 2.0 -Arrow
Add-Line ($x3 + 172) 462 ($x3 + 258) 462 $C.Score 2.0
Add-Line ($x3 + 258) 462 ($x3 + 258) 408 $C.Score 2.0 -Arrow
Add-Text ($x3 + 116) 480 110 46 "Descriptor`nfeatures" 12.2 $true $C.Ink
Add-Line ($x3 + 28) 555 ($x3 + 300) 555 $C.Score 1.6 -Dash
Add-Shape ($x3 + 42) 585 36 36 $null "#E5F1FC" $C.Score 1.0 "ellipse"
Add-Line ($x3 + 50) 613 ($x3 + 28) 640 $C.Score 4.0
Add-Text ($x3 + 94) 594 160 26 "LOSO evaluation" 15 $true $C.Ink
Add-Roc ($x3 + 42) 665 $C.Score "random split"
Add-Roc ($x3 + 176) 665 $C.Filter "source split"

# Stage 4: dual-route design
Add-Shape ($x4 + 18) 212 344 190 $null "#FFFFFF" $C.Design 1.4 "roundRect"
Add-Text ($x4 + 74) 225 214 28 "Route A: local optimization" 14.5 $true $C.Ink
Add-Ring -Cx ($x4 + 88) -Cy 308 -Radius 46 -Color ($C.Design)
Add-Text ($x4 + 48) 275 86 60 "O`nH-N     N-O`n   N      N" 9 $false $C.Ink
Add-Line ($x4 + 146) 312 ($x4 + 182) 312 $C.Design 2.4 -Arrow
Add-Shape ($x4 + 195) 282 58 58 $null "#BCE4C9" $C.Design 2.0 "gear6"
Add-Line ($x4 + 262) 312 ($x4 + 302) 312 $C.Design 2.4 -Arrow
Add-Line ($x4 + 315) 360 ($x4 + 315) 270 $C.Ink 1.3
Add-Line ($x4 + 315) 360 ($x4 + 385) 360 $C.Ink 1.3
Add-Line ($x4 + 322) 348 ($x4 + 338) 318 $C.Design 2.5
Add-Line ($x4 + 338) 318 ($x4 + 360) 292 $C.Design 2.5
Add-Line ($x4 + 360) 292 ($x4 + 386) 286 $C.Design 2.5

Add-Shape ($x4 + 18) 420 344 192 $null "#FFFFFF" $C.Design 1.4 "roundRect"
Add-Text ($x4 + 57) 436 250 28 "Multi-objective optimization" 14.5 $true $C.Ink
Add-Shape ($x4 + 58) 520 105 15 $null "#D8F0DD" $C.Design 1.0 "trapezoid"
Add-Line ($x4 + 110) 465 ($x4 + 110) 550 $C.Design 3.2
Add-Line ($x4 + 66) 470 ($x4 + 154) 470 $C.Ink 1.5
Add-Line ($x4 + 74) 470 ($x4 + 50) 525 $C.Ink 1.1
Add-Line ($x4 + 74) 470 ($x4 + 98) 525 $C.Ink 1.1
Add-Line ($x4 + 146) 470 ($x4 + 122) 525 $C.Ink 1.1
Add-Line ($x4 + 146) 470 ($x4 + 170) 525 $C.Ink 1.1
Add-Shape ($x4 + 42) 515 56 25 $null "#9AD7A9" $C.Design 1.0 "arc"
Add-Shape ($x4 + 122) 515 56 25 $null "#9AD7A9" $C.Design 1.0 "arc"
Add-Shape ($x4 + 78) 552 64 14 $null "#9AD7A9" $C.Design 1.0 "rect"
Add-Shape ($x4 + 224) 472 15 15 $null $C.Data $C.Ink 0.6 "ellipse"
Add-Shape ($x4 + 224) 512 15 15 $null $C.Green $C.Ink 0.6 "ellipse"
Add-Shape ($x4 + 224) 552 15 15 $null "#9E67C8" $C.Ink 0.6 "ellipse"
Add-Shape ($x4 + 224) 592 15 15 $null "#F28E22" $C.Ink 0.6 "ellipse"
Add-Text ($x4 + 246) 466 98 26 "Permeability" 10.5 $false $C.Ink "l"
Add-Text ($x4 + 246) 506 98 26 "Polarity" 10.5 $false $C.Ink "l"
Add-Text ($x4 + 246) 546 98 26 "Diversity" 10.5 $false $C.Ink "l"
Add-Text ($x4 + 246) 586 98 26 "Uncertainty" 10.5 $false $C.Ink "l"

Add-Shape ($x4 + 18) 630 344 220 $null "#FFFFFF" $C.Design 1.4 "roundRect"
Add-Text ($x4 + 78) 646 210 28 "Route B: de novo design" 14.5 $true $C.Ink
Add-Shape ($x4 + 54) 696 52 62 $null "#FFFFFF" $C.Design 1.1 "roundRect"
Add-Shape ($x4 + 64) 686 52 62 $null "#F0FBF7" $C.Design 1.1 "roundRect"
Add-Shape ($x4 + 74) 676 52 62 $null "#FFFFFF" $C.Design 1.1 "roundRect"
Add-Ring -Cx ($x4 + 100) -Cy 707 -Radius 14 -Color ($C.Design)
Add-Line ($x4 + 140) 720 ($x4 + 196) 720 $C.Design 2.6 -Arrow
Add-Shape ($x4 + 238) 685 44 44 $null "#F2B545" $C.Filter 1.2 "star5"
for ($i = 0; $i -lt 7; $i++) {
  $ang = -[Math]::PI / 2 + $i * 2 * [Math]::PI / 7
  $sx = $x4 + 260 + 72 * [Math]::Cos($ang)
  $sy = 707 + 58 * [Math]::Sin($ang)
  Add-Line ($x4 + 260) 707 $sx $sy $C.Ink 1.0
  Add-Shape ($sx - 8) ($sy - 8) 16 16 $null @( $C.Data, $C.Desc, $C.Design, $C.Final, $C.Filter, $C.Green, "#9E67C8")[$i] $C.Ink 0.6 "ellipse"
}
Add-Text ($x4 + 54) 770 100 44 "Fragment`nlibrary" 11.5 $true $C.Ink
Add-Text ($x4 + 210) 770 120 44 "Diversity`nexploration" 11.5 $true $C.Ink

# Stage 5: validation and analysis
Add-Text ($x5 + 72) 222 120 24 "Uncertainty" 13 $true $C.Ink
Add-Uncertainty ($x5 + 44) 260
Add-Text ($x5 + 72) 377 120 24 "3D polarity" 13 $true $C.Ink
Add-PolarityBlob ($x5 + 38) 402 1.0
Add-Text ($x5 + 48) 548 154 24 "Novelty & diversity" 13 $true $C.Ink
Add-Scatter ($x5 + 34) 592
Add-Shape ($x5 + 18) 745 112 98 $null "#EFFAF2" $C.Design 1.4 "roundRect"
Add-Text ($x5 + 37) 758 72 36 "12" 30 $true $C.Design
Add-Text ($x5 + 34) 802 78 28 "optimized" 13 $true $C.Ink
Add-Shape ($x5 + 142) 745 90 98 $null "#FFF5EA" $C.Filter 1.4 "roundRect"
Add-Text ($x5 + 155) 758 62 36 "24" 30 $true $C.Filter
Add-Text ($x5 + 151) 800 72 36 "de novo" 13 $true $C.Ink

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
