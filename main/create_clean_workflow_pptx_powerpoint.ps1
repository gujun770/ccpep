$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$out = Join-Path $root "molecular_diversity_workflow_clean_editable.pptx"

$ppLayoutBlank = 12
$msoFalse = 0
$msoTrue = -1
$ppSaveAsOpenXMLPresentation = 24

function Rgb($r, $g, $b) {
    return [int]($r + ($g * 256) + ($b * 65536))
}

function Add-Box($slide, $x, $y, $w, $h, $fill, $line, $radius = $true) {
    $shapeType = if ($radius) { 5 } else { 1 }
    $s = $slide.Shapes.AddShape($shapeType, $x, $y, $w, $h)
    $s.Fill.ForeColor.RGB = $fill
    $s.Line.ForeColor.RGB = $line
    $s.Line.Weight = 1.2
    return $s
}

function Add-Text($slide, $text, $x, $y, $w, $h, $size, $bold = $false, $color = $null, $align = 1) {
    $box = $slide.Shapes.AddTextbox(1, $x, $y, $w, $h)
    $box.TextFrame2.TextRange.Text = $text
    $box.TextFrame2.MarginLeft = 3
    $box.TextFrame2.MarginRight = 3
    $box.TextFrame2.MarginTop = 2
    $box.TextFrame2.MarginBottom = 2
    $box.TextFrame2.TextRange.Font.Name = "Arial"
    $box.TextFrame2.TextRange.Font.Size = [single]$size
    $box.TextFrame2.TextRange.Font.Bold = if ($bold) { $msoTrue } else { $msoFalse }
    if ($null -ne $color) { $box.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = $color }
    $box.TextFrame2.TextRange.ParagraphFormat.Alignment = $align
    return $box
}

function Add-Arrow($slide, $x1, $y1, $x2, $y2, $color) {
    $line = $slide.Shapes.AddLine($x1, $y1, $x2, $y2)
    $line.Line.ForeColor.RGB = $color
    $line.Line.Weight = 2.0
    $line.Line.EndArrowheadStyle = 3
    return $line
}

function Add-Stage($slide, $num, $title, $subtitle, $x, $y, $w, $h, $accent, $fill) {
    Add-Box $slide $x $y $w $h $fill $accent | Out-Null
    Add-Box $slide $x $y $w 34 $accent $accent $false | Out-Null
    Add-Text $slide $num ($x + 8) ($y + 6) 18 20 13 $true (Rgb 255 255 255) 2 | Out-Null
    Add-Text $slide $title ($x + 30) ($y + 4) ($w - 36) 26 11.5 $true (Rgb 255 255 255) 1 | Out-Null
    if (-not [string]::IsNullOrWhiteSpace($subtitle)) {
        Add-Text $slide $subtitle ($x + 12) ($y + $h - 48) ($w - 24) 34 8.5 $false (Rgb 45 52 64) 2 | Out-Null
    }
}

function Add-BulletList($slide, $items, $x, $y, $w, $h) {
    $text = ($items -join [Environment]::NewLine)
    $box = Add-Text $slide $text $x $y $w $h 10 $false (Rgb 24 31 42) 1
    $box.TextFrame2.TextRange.ParagraphFormat.FirstLineIndent = -10
    $box.TextFrame2.TextRange.ParagraphFormat.LeftIndent = 12
    return $box
}

function Add-DatabaseIcon($slide, $x, $y, $color) {
    $x = [double]$x
    $y = [double]$y
    $body = $slide.Shapes.AddShape(1, $x, ($y + 10), 48, 40)
    $body.Fill.ForeColor.RGB = $color
    $body.Line.ForeColor.RGB = $color
    $top = $slide.Shapes.AddShape(9, $x, $y, 48, 20)
    $top.Fill.ForeColor.RGB = (Rgb 255 255 255)
    $top.Line.ForeColor.RGB = $color
    $top.Line.Weight = 1.5
    $mid = $slide.Shapes.AddLine($x, ($y + 28), ($x + 48), ($y + 28))
    $mid.Line.ForeColor.RGB = (Rgb 255 255 255)
    $mid.Line.Weight = 1.3
}

function Add-MoleculeIcon($slide, $x, $y, $color) {
    $x = [double]$x
    $y = [double]$y
    $pts = @(
        @(($x + 18), ($y + 4)),
        @(($x + 50), ($y + 14)),
        @(($x + 56), ($y + 45)),
        @(($x + 30), ($y + 64)),
        @(($x + 4), ($y + 45)),
        @(($x + 9), ($y + 15))
    )
    for ($i = 0; $i -lt 6; $i++) {
        $a = $pts[$i]
        $b = $pts[($i + 1) % 6]
        $line = $slide.Shapes.AddLine($a[0], $a[1], $b[0], $b[1])
        $line.Line.ForeColor.RGB = $color
        $line.Line.Weight = 1.8
    }
    foreach ($p in $pts) {
        $node = $slide.Shapes.AddShape(9, ($p[0] - 5), ($p[1] - 5), 10, 10)
        $node.Fill.ForeColor.RGB = (Rgb 255 255 255)
        $node.Line.ForeColor.RGB = $color
        $node.Line.Weight = 1.4
    }
}

function Add-CurveIcon($slide, $x, $y, $color) {
    $x = [double]$x
    $y = [double]$y
    $axis1 = $slide.Shapes.AddLine($x, ($y + 44), ($x + 70), ($y + 44))
    $axis2 = $slide.Shapes.AddLine($x, ($y + 44), $x, $y)
    $axis1.Line.ForeColor.RGB = (Rgb 125 137 153)
    $axis2.Line.ForeColor.RGB = (Rgb 125 137 153)
    $prevX = $x
    $prevY = $y + 42
    for ($i = 1; $i -le 10; $i++) {
        $nx = $x + ($i * 7)
        $ny = $y + 42 - (40 * (1 - [Math]::Exp(-0.28 * $i)))
        $seg = $slide.Shapes.AddLine($prevX, $prevY, $nx, $ny)
        $seg.Line.ForeColor.RGB = $color
        $seg.Line.Weight = 2
        $prevX = $nx
        $prevY = $ny
    }
}

function Add-ValidationBadges($slide, $x, $y) {
    $x = [double]$x
    $y = [double]$y
    $labels = @("Novelty", "Diversity", "Uncertainty", "3D polarity")
    for ($i = 0; $i -lt $labels.Count; $i++) {
        $yy = $y + ($i * 29)
        Add-Box $slide $x $yy 82 22 (Rgb 255 255 255) (Rgb 213 119 42) $true | Out-Null
        Add-Text $slide $labels[$i] ($x + 5) ($yy + 3) 72 14 9.5 $true (Rgb 37 45 57) 2 | Out-Null
    }
}

$ppt = New-Object -ComObject PowerPoint.Application
$ppt.Visible = $msoTrue
$pres = $ppt.Presentations.Add($msoTrue)
$pres.PageSetup.SlideWidth = 960
$pres.PageSetup.SlideHeight = 540

$slide = $pres.Slides.Add(1, $ppLayoutBlank)
$slide.FollowMasterBackground = $msoFalse
$slide.Background.Fill.ForeColor.RGB = (Rgb 248 250 252)

$ink = Rgb 20 28 38
$muted = Rgb 72 83 98
$blue = Rgb 44 130 188
$teal = Rgb 22 153 162
$indigo = Rgb 77 106 178
$green = Rgb 25 151 107
$orange = Rgb 218 124 43
$arrow = Rgb 69 96 125

Add-Text $slide "Descriptor-guided workflow for cyclic peptide permeability prediction" 70 18 820 24 20 $true $ink 2 | Out-Null
Add-Text $slide "and molecular diversity design" 70 43 820 24 20 $true $ink 2 | Out-Null
Add-Text $slide "Public cyclic peptide data, source-aware validation, and dual-route candidate generation" 150 72 660 18 9.5 $false $muted 2 | Out-Null

$y = 105
$h = 355
$w = 148
$gap = 18
$x1 = 42
$x2 = $x1 + $w + $gap
$x3 = $x2 + $w + $gap
$x4 = $x3 + 216 + $gap
$x5 = $x4 + 178 + $gap

Add-Stage $slide "1" "Data curation" "" $x1 $y $w $h $blue (Rgb 235 245 252)
Add-DatabaseIcon $slide ($x1 + 49) ($y + 78) $blue
Add-BulletList $slide @("Cyclic peptide records", "29 literature sources", "Source labels", "Source shift check") ($x1 + 22) ($y + 165) ($w - 42) 96 | Out-Null

Add-Stage $slide "2" "Descriptor representation" "" $x2 $y $w $h $teal (Rgb 234 249 248)
Add-MoleculeIcon $slide ($x2 + 45) ($y + 58) $teal
Add-BulletList $slide @("HELM tokens", "2D physicochemical descriptors", "Composition features", "3D polarity proxy") ($x2 + 22) ($y + 160) ($w - 42) 112 | Out-Null

Add-Stage $slide "3" "Source-aware scoring" "" $x3 $y 216 $h $indigo (Rgb 239 243 253)
Add-Text $slide "Hybrid permeability scorer" ($x3 + 22) ($y + 58) 172 24 16 $true $ink 2 | Out-Null
Add-Box $slide ($x3 + 31) ($y + 104) 58 38 (Rgb 255 255 255) $indigo $true | Out-Null
Add-Text $slide "Model`ntraining" ($x3 + 37) ($y + 111) 46 22 9 $true $ink 2 | Out-Null
Add-Arrow $slide ($x3 + 94) ($y + 123) ($x3 + 122) ($y + 123) $indigo | Out-Null
Add-Box $slide ($x3 + 127) ($y + 104) 58 38 (Rgb 255 255 255) $indigo $true | Out-Null
Add-Text $slide "Predictor" ($x3 + 132) ($y + 115) 49 14 9 $true $ink 2 | Out-Null
Add-Text $slide "Descriptors + HELM tokens" ($x3 + 35) ($y + 157) 145 18 10 $false $ink 2 | Out-Null
Add-CurveIcon $slide ($x3 + 34) ($y + 207) $indigo
Add-CurveIcon $slide ($x3 + 119) ($y + 207) $orange
Add-Text $slide "Random split" ($x3 + 29) ($y + 255) 78 14 7.5 $false $ink 2 | Out-Null
Add-Text $slide "Source split" ($x3 + 115) ($y + 255) 78 14 7.5 $false $ink 2 | Out-Null
Add-Box $slide ($x3 + 36) ($y + 286) 64 22 (Rgb 255 255 255) $indigo $true | Out-Null
Add-Text $slide "Group CV" ($x3 + 42) ($y + 290) 52 12 9 $true $ink 2 | Out-Null
Add-Box $slide ($x3 + 116) ($y + 286) 64 22 (Rgb 255 255 255) $indigo $true | Out-Null
Add-Text $slide "LOSO" ($x3 + 122) ($y + 290) 52 12 9 $true $ink 2 | Out-Null

Add-Stage $slide "4" "Dual-route design" "" $x4 $y 178 $h $green (Rgb 235 250 244)
Add-Box $slide ($x4 + 18) ($y + 58) 142 95 (Rgb 255 255 255) $green $true | Out-Null
Add-Text $slide "Route A" ($x4 + 32) ($y + 73) 96 16 12 $true $ink 1 | Out-Null
Add-Text $slide "Constrained local optimization" ($x4 + 32) ($y + 94) 96 26 9.5 $false $ink 1 | Out-Null
Add-Arrow $slide ($x4 + 42) ($y + 132) ($x4 + 126) ($y + 132) $green | Out-Null
Add-Box $slide ($x4 + 18) ($y + 174) 142 95 (Rgb 255 255 255) $green $true | Out-Null
Add-Text $slide "Route B" ($x4 + 32) ($y + 189) 96 16 12 $true $ink 1 | Out-Null
Add-Text $slide "De novo fragment generation" ($x4 + 32) ($y + 210) 96 26 9.5 $false $ink 1 | Out-Null
Add-Arrow $slide ($x4 + 42) ($y + 248) ($x4 + 126) ($y + 248) $green | Out-Null
Add-Box $slide ($x4 + 24) ($y + 288) 130 50 (Rgb 255 255 255) $green $true | Out-Null
Add-Text $slide "Objectives" ($x4 + 34) ($y + 297) 110 12 10 $true $ink 2 | Out-Null
Add-Text $slide "permeability, polarity, diversity, uncertainty" ($x4 + 32) ($y + 314) 114 18 7.5 $false $ink 2 | Out-Null

Add-Stage $slide "5" "Validation analysis" "" $x5 $y $w $h $orange (Rgb 255 245 236)
Add-Text $slide "Validation metrics" ($x5 + 24) ($y + 58) 100 18 12 $true $ink 2 | Out-Null
Add-ValidationBadges $slide ($x5 + 34) ($y + 91)
Add-Text $slide "Candidate sets" ($x5 + 24) ($y + 232) 100 16 12 $true $ink 2 | Out-Null
Add-Box $slide ($x5 + 26) ($y + 262) 42 42 (Rgb 255 255 255) $green $true | Out-Null
Add-Text $slide "12" ($x5 + 29) ($y + 269) 36 24 22 $true $ink 2 | Out-Null
Add-Text $slide "optimized`ncandidates" ($x5 + 76) ($y + 267) 58 28 9 $false $ink 1 | Out-Null
Add-Box $slide ($x5 + 26) ($y + 318) 42 42 (Rgb 255 255 255) $orange $true | Out-Null
Add-Text $slide "24" ($x5 + 29) ($y + 325) 36 24 22 $true $ink 2 | Out-Null
Add-Text $slide "de novo`ncandidates" ($x5 + 76) ($y + 323) 58 28 9 $false $ink 1 | Out-Null

$arrowY = $y + 180
Add-Arrow $slide ($x1 + $w + 3) $arrowY ($x2 - 5) $arrowY $arrow | Out-Null
Add-Arrow $slide ($x2 + $w + 3) $arrowY ($x3 - 5) $arrowY $arrow | Out-Null
Add-Arrow $slide ($x3 + 216 + 3) $arrowY ($x4 - 5) $arrowY $arrow | Out-Null
Add-Arrow $slide ($x4 + 178 + 3) $arrowY ($x5 - 5) $arrowY $arrow | Out-Null

Add-Box $slide 110 482 740 30 (Rgb 255 255 255) (Rgb 184 198 216) $true | Out-Null
Add-Text $slide "Output: membrane-permeable cyclic peptide candidates prioritized by prediction, molecular diversity, novelty, uncertainty, and 3D polarity-proxy evidence" 120 488 720 16 9.5 $false $ink 2 | Out-Null

if (Test-Path -LiteralPath $out) {
    Remove-Item -LiteralPath $out -Force
}

$pres.SaveAs($out, $ppSaveAsOpenXMLPresentation)
$pres.Close()
$ppt.Quit()

[Runtime.InteropServices.Marshal]::ReleaseComObject($slide) | Out-Null
[Runtime.InteropServices.Marshal]::ReleaseComObject($pres) | Out-Null
[Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null

Write-Host "Saved $out"
