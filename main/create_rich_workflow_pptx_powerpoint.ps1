$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$out = Join-Path $root "molecular_diversity_workflow_rich_editable.pptx"

$figDir = Join-Path $root "Result\paper_figures"
$figRoc = Join-Path $figDir "figure2b_roc_pr_curves.png"
$figGen = Join-Path $figDir "figure3_generation.png"
$figQD = Join-Path $figDir "figure8_quality_diversity.png"
$figPol = Join-Path $figDir "figure6_conformation_proxy.png"
$figNovel = Join-Path $figDir "figure12_novelty_depth.png"

$ppLayoutBlank = 12
$msoFalse = 0
$msoTrue = -1
$ppSaveAsOpenXMLPresentation = 24

Add-Type -AssemblyName System.Drawing

function Rgb($r, $g, $b) {
    return [int]($r + ($g * 256) + ($b * 65536))
}

function Set-TextStyle($shape, $size, $bold, $color, $align) {
    $shape.TextFrame2.MarginLeft = 3
    $shape.TextFrame2.MarginRight = 3
    $shape.TextFrame2.MarginTop = 2
    $shape.TextFrame2.MarginBottom = 2
    $shape.TextFrame2.WordWrap = $msoTrue
    $shape.TextFrame2.TextRange.Font.Name = "Arial"
    $shape.TextFrame2.TextRange.Font.Size = [single]$size
    $shape.TextFrame2.TextRange.Font.Bold = if ($bold) { $msoTrue } else { $msoFalse }
    $shape.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = $color
    $shape.TextFrame2.TextRange.ParagraphFormat.Alignment = $align
}

function Add-Text($slide, $text, $x, $y, $w, $h, $size, $bold = $false, $color = $null, $align = 1) {
    if ($null -eq $color) { $color = Rgb 25 31 42 }
    $box = $slide.Shapes.AddTextbox(1, [double]$x, [double]$y, [double]$w, [double]$h)
    $box.TextFrame2.TextRange.Text = $text
    Set-TextStyle $box $size $bold $color $align
    return $box
}

function Add-Box($slide, $x, $y, $w, $h, $fill, $line, $radius = $true, $weight = 1.2) {
    $shapeType = if ($radius) { 5 } else { 1 }
    $s = $slide.Shapes.AddShape($shapeType, [double]$x, [double]$y, [double]$w, [double]$h)
    $s.Fill.ForeColor.RGB = $fill
    $s.Line.ForeColor.RGB = $line
    $s.Line.Weight = [single]$weight
    return $s
}

function Add-Arrow($slide, $x1, $y1, $x2, $y2, $color, $weight = 1.8) {
    $line = $slide.Shapes.AddLine([double]$x1, [double]$y1, [double]$x2, [double]$y2)
    $line.Line.ForeColor.RGB = $color
    $line.Line.Weight = [single]$weight
    $line.Line.EndArrowheadStyle = 3
    return $line
}

function Add-Panel($slide, $num, $title, $x, $y, $w, $h, $accent, $fill) {
    Add-Box $slide $x $y $w $h $fill $accent $true 1.4 | Out-Null
    Add-Box $slide $x $y $w 33 $accent $accent $false 1.0 | Out-Null
    Add-Text $slide $num ($x + 8) ($y + 7) 18 17 12 $true (Rgb 255 255 255) 2 | Out-Null
    Add-Text $slide $title ($x + 31) ($y + 5) ($w - 38) 22 10.5 $true (Rgb 255 255 255) 1 | Out-Null
}

function Add-PictureFit($slide, $path, $x, $y, $w, $h) {
    $img = [System.Drawing.Image]::FromFile($path)
    $iw = [double]$img.Width
    $ih = [double]$img.Height
    $img.Dispose()
    $scale = [Math]::Min(([double]$w / $iw), ([double]$h / $ih))
    $dw = $iw * $scale
    $dh = $ih * $scale
    $dx = [double]$x + (([double]$w - $dw) / 2.0)
    $dy = [double]$y + (([double]$h - $dh) / 2.0)
    $pic = $slide.Shapes.AddPicture($path, $msoFalse, $msoTrue, $dx, $dy, $dw, $dh)
    $pic.Line.ForeColor.RGB = Rgb 206 216 226
    $pic.Line.Weight = 0.75
    return $pic
}

function Add-DatabaseIcon($slide, $x, $y, $accent) {
    Add-Box $slide $x ($y + 9) 42 38 $accent $accent $false 1.0 | Out-Null
    $top = $slide.Shapes.AddShape(9, [double]$x, [double]$y, 42, 18)
    $top.Fill.ForeColor.RGB = Rgb 255 255 255
    $top.Line.ForeColor.RGB = $accent
    $top.Line.Weight = 1.3
    foreach ($yy in @($y + 25, $y + 40)) {
        $line = $slide.Shapes.AddLine($x + 2, $yy, $x + 40, $yy)
        $line.Line.ForeColor.RGB = Rgb 255 255 255
        $line.Line.Weight = 1.2
    }
}

function Add-MoleculeRing($slide, $x, $y, $accent, $scale = 1.0) {
    $pts = @(
        @(18, 3), @(48, 15), @(53, 45), @(28, 62), @(4, 45), @(8, 15)
    )
    for ($i = 0; $i -lt 6; $i++) {
        $a = $pts[$i]
        $b = $pts[($i + 1) % 6]
        $line = $slide.Shapes.AddLine($x + $a[0] * $scale, $y + $a[1] * $scale, $x + $b[0] * $scale, $y + $b[1] * $scale)
        $line.Line.ForeColor.RGB = $accent
        $line.Line.Weight = 1.6
    }
    $colors = @((Rgb 75 121 190), (Rgb 32 151 160), (Rgb 230 142 49), (Rgb 82 105 177), (Rgb 32 151 160), (Rgb 75 121 190))
    for ($i = 0; $i -lt 6; $i++) {
        $p = $pts[$i]
        $node = $slide.Shapes.AddShape(9, $x + ($p[0] - 5) * $scale, $y + ($p[1] - 5) * $scale, 10 * $scale, 10 * $scale)
        $node.Fill.ForeColor.RGB = $colors[$i]
        $node.Line.ForeColor.RGB = Rgb 36 43 55
        $node.Line.Weight = 0.7
    }
}

function Add-Heatmap($slide, $x, $y) {
    $colors = @(
        (Rgb 232 93 83), (Rgb 245 174 80), (Rgb 248 218 130), (Rgb 138 200 137), (Rgb 84 155 200),
        (Rgb 245 174 80), (Rgb 248 218 130), (Rgb 138 200 137), (Rgb 84 155 200), (Rgb 232 93 83),
        (Rgb 138 200 137), (Rgb 84 155 200), (Rgb 232 93 83), (Rgb 245 174 80), (Rgb 248 218 130),
        (Rgb 84 155 200), (Rgb 232 93 83), (Rgb 245 174 80), (Rgb 248 218 130), (Rgb 138 200 137)
    )
    for ($r = 0; $r -lt 4; $r++) {
        for ($c = 0; $c -lt 5; $c++) {
            $idx = $r * 5 + $c
            $sq = $slide.Shapes.AddShape(1, $x + $c * 9, $y + $r * 9, 8, 8)
            $sq.Fill.ForeColor.RGB = $colors[$idx]
            $sq.Line.Visible = $msoFalse
        }
    }
}

function Add-DescriptorTile($slide, $label, $x, $y, $w, $h, $accent) {
    Add-Box $slide $x $y $w $h (Rgb 255 255 255) $accent $true 1.0 | Out-Null
    Add-Text $slide $label ($x + 5) ($y + 7) ($w - 10) ($h - 12) 8.2 $true (Rgb 31 42 56) 2 | Out-Null
}

function Add-MiniCurve($slide, $x, $y, $color) {
    $axis = Rgb 128 142 158
    $l1 = $slide.Shapes.AddLine($x, $y + 39, $x + 60, $y + 39)
    $l2 = $slide.Shapes.AddLine($x, $y + 39, $x, $y + 2)
    foreach ($l in @($l1, $l2)) { $l.Line.ForeColor.RGB = $axis; $l.Line.Weight = 0.7 }
    $px = $x + 2
    $py = $y + 36
    for ($i = 1; $i -le 10; $i++) {
        $nx = $x + 2 + $i * 5.4
        $ny = $y + 36 - 31 * (1 - [Math]::Exp(-0.32 * $i))
        $seg = $slide.Shapes.AddLine($px, $py, $nx, $ny)
        $seg.Line.ForeColor.RGB = $color
        $seg.Line.Weight = 1.7
        $px = $nx
        $py = $ny
    }
}

function Add-DotCloud($slide, $x, $y, $accent) {
    $pts = @(@(3,20),@(12,9),@(18,24),@(25,14),@(32,28),@(40,16),@(48,31),@(55,11),@(62,23),@(70,18),@(77,30),@(84,12),@(92,25))
    foreach ($p in $pts) {
        $dot = $slide.Shapes.AddShape(9, $x + $p[0], $y + $p[1], 4.5, 4.5)
        $dot.Fill.ForeColor.RGB = $accent
        $dot.Line.Visible = $msoFalse
    }
}

$ppt = New-Object -ComObject PowerPoint.Application
$ppt.Visible = $msoTrue
$pres = $ppt.Presentations.Add($msoTrue)
$pres.PageSetup.SlideWidth = 1200
$pres.PageSetup.SlideHeight = 675

$slide = $pres.Slides.Add(1, $ppLayoutBlank)
$slide.FollowMasterBackground = $msoFalse
$slide.Background.Fill.ForeColor.RGB = Rgb 246 250 251

$ink = Rgb 19 26 35
$muted = Rgb 78 91 108
$blue = Rgb 48 129 184
$teal = Rgb 30 155 166
$indigo = Rgb 75 104 176
$green = Rgb 28 150 103
$orange = Rgb 219 124 43
$border = Rgb 77 115 139

Add-Text $slide "Descriptor-guided workflow for cyclic peptide permeability prediction" 120 18 960 28 20 $true $ink 2 | Out-Null
Add-Text $slide "and molecular diversity design" 120 44 960 28 20 $true $ink 2 | Out-Null
Add-Text $slide "Schematic Figure 1 assembled from manuscript-supported modules and existing result panels" 210 77 780 18 9.5 $false $muted 2 | Out-Null

$topY = 112
$panelH = 492
$gap = 16
$x1 = 30;  $w1 = 142
$x2 = 188; $w2 = 142
$x3 = 346; $w3 = 250
$x4 = 612; $w4 = 255
$x5 = 883; $w5 = 287

Add-Panel $slide "1" "Data sources & curation" $x1 $topY $w1 $panelH $blue (Rgb 233 244 251)
Add-DatabaseIcon $slide ($x1 + 50) ($topY + 58) $blue
Add-Text $slide "CycPeptMPDB" ($x1 + 17) ($topY + 122) ($w1 - 34) 16 10.5 $true $ink 2 | Out-Null
Add-Text $slide "Length-6 cyclic peptides" ($x1 + 16) ($topY + 143) ($w1 - 32) 28 9.2 $false $ink 2 | Out-Null
Add-Text $slide "2168 records" ($x1 + 19) ($topY + 180) ($w1 - 38) 17 10 $true $blue 2 | Out-Null
Add-Text $slide "29 literature sources" ($x1 + 18) ($topY + 203) ($w1 - 36) 16 8.8 $false $ink 2 | Out-Null
for ($i = 0; $i -lt 5; $i++) {
    $badge = $slide.Shapes.AddShape(5, $x1 + 25 + $i * 19, $topY + 232, 16, 16)
    $badge.Fill.ForeColor.RGB = @(Rgb 48 129 184, Rgb 30 155 166, Rgb 82 105 177, Rgb 31 150 103, Rgb 222 135 43)[$i]
    $badge.Line.Visible = $msoFalse
    Add-Text $slide ("S" + ($i + 1)) ($x1 + 25 + $i * 19) ($topY + 234) 16 10 5.7 $true (Rgb 255 255 255) 2 | Out-Null
}
Add-Heatmap $slide ($x1 + 48) ($topY + 284)
Add-Text $slide "Source labels and source shift" ($x1 + 15) ($topY + 334) ($w1 - 30) 30 8.2 $false $ink 2 | Out-Null

Add-Panel $slide "2" "Descriptor representation" $x2 $topY $w2 $panelH $teal (Rgb 232 248 248)
Add-MoleculeRing $slide ($x2 + 45) ($topY + 54) $teal 1.0
Add-DescriptorTile $slide "HELM tokens" ($x2 + 20) ($topY + 132) 102 32 $teal
Add-DescriptorTile $slide "2D descriptors" ($x2 + 20) ($topY + 176) 102 32 $teal
Add-DescriptorTile $slide "Composition" ($x2 + 20) ($topY + 220) 102 32 $teal
Add-DescriptorTile $slide "3D polarity proxy" ($x2 + 20) ($topY + 264) 102 32 $teal
Add-DotCloud $slide ($x2 + 23) ($topY + 328) $teal
Add-Text $slide "Descriptor matrix for robust source-aware learning" ($x2 + 14) ($topY + 382) ($w2 - 28) 42 8.2 $false $ink 2 | Out-Null

Add-Panel $slide "3" "Source-aware permeability scoring" $x3 $topY $w3 $panelH $indigo (Rgb 237 242 253)
Add-Text $slide "Hybrid permeability scorer" ($x3 + 24) ($topY + 50) ($w3 - 48) 24 15 $true $ink 2 | Out-Null
Add-Box $slide ($x3 + 38) ($topY + 91) 66 40 (Rgb 255 255 255) $indigo $true 1.0 | Out-Null
Add-Text $slide "Training" ($x3 + 44) ($topY + 103) 54 14 8.5 $true $ink 2 | Out-Null
Add-Arrow $slide ($x3 + 110) ($topY + 111) ($x3 + 145) ($topY + 111) $indigo 1.8 | Out-Null
Add-Box $slide ($x3 + 152) ($topY + 91) 66 40 (Rgb 255 255 255) $indigo $true 1.0 | Out-Null
Add-Text $slide "Predictor" ($x3 + 158) ($topY + 103) 54 14 8.5 $true $ink 2 | Out-Null
Add-Text $slide "Descriptor features + HELM tokens" ($x3 + 43) ($topY + 143) 164 16 8.7 $false $ink 2 | Out-Null
Add-Box $slide ($x3 + 18) ($topY + 171) ($w3 - 36) 122 (Rgb 255 255 255) (Rgb 198 207 222) $true 0.8 | Out-Null
Add-PictureFit $slide $figRoc ($x3 + 22) ($topY + 176) ($w3 - 44) 112 | Out-Null
Add-Text $slide "Random split vs. source split" ($x3 + 42) ($topY + 300) 166 15 8.2 $true $indigo 2 | Out-Null
Add-Box $slide ($x3 + 31) ($topY + 330) 82 26 (Rgb 255 255 255) $indigo $true 1.0 | Out-Null
Add-Text $slide "Group CV" ($x3 + 39) ($topY + 335) 66 12 8.5 $true $ink 2 | Out-Null
Add-Box $slide ($x3 + 136) ($topY + 330) 82 26 (Rgb 255 255 255) $indigo $true 1.0 | Out-Null
Add-Text $slide "LOSO" ($x3 + 144) ($topY + 335) 66 12 8.5 $true $ink 2 | Out-Null
Add-Text $slide "Quantifies hidden generalization gap" ($x3 + 34) ($topY + 372) 182 20 8.5 $false $ink 2 | Out-Null

Add-Panel $slide "4" "Dual-route candidate design" $x4 $topY $w4 $panelH $green (Rgb 233 249 243)
Add-Box $slide ($x4 + 18) ($topY + 50) ($w4 - 36) 110 (Rgb 255 255 255) $green $true 1.0 | Out-Null
Add-Text $slide "Route A: local optimization" ($x4 + 34) ($topY + 63) ($w4 - 68) 18 10.8 $true $ink 2 | Out-Null
Add-MoleculeRing $slide ($x4 + 42) ($topY + 92) $green 0.56
Add-Arrow $slide ($x4 + 95) ($topY + 112) ($x4 + 145) ($topY + 112) $green 1.6 | Out-Null
$gear = $slide.Shapes.AddShape(10, $x4 + 158, $topY + 94, 30, 30)
$gear.Fill.ForeColor.RGB = Rgb 255 255 255
$gear.Line.ForeColor.RGB = $green
$gear.Line.Weight = 1.4
Add-Text $slide "Analog edits with improved predicted permeability" ($x4 + 38) ($topY + 132) ($w4 - 76) 18 7.6 $false $ink 2 | Out-Null
Add-Box $slide ($x4 + 18) ($topY + 178) ($w4 - 36) 126 (Rgb 255 255 255) $green $true 1.0 | Out-Null
Add-Text $slide "Route B: de novo generation" ($x4 + 35) ($topY + 191) ($w4 - 70) 18 10.8 $true $ink 2 | Out-Null
Add-Box $slide ($x4 + 45) ($topY + 224) 38 47 (Rgb 247 252 250) $green $true 1.2 | Out-Null
Add-Arrow $slide ($x4 + 92) ($topY + 247) ($x4 + 142) ($topY + 247) $green 1.6 | Out-Null
Add-MoleculeRing $slide ($x4 + 150) ($topY + 220) $green 0.62
Add-Text $slide "Fragment library -> diversity optimization" ($x4 + 38) ($topY + 276) ($w4 - 76) 18 7.6 $false $ink 2 | Out-Null
Add-Box $slide ($x4 + 18) ($topY + 321) ($w4 - 36) 80 (Rgb 255 255 255) (Rgb 194 208 220) $true 0.8 | Out-Null
Add-PictureFit $slide $figGen ($x4 + 22) ($topY + 326) ($w4 - 44) 70 | Out-Null
Add-Text $slide "Multi-objective score: permeability, polarity, diversity, novelty, uncertainty" ($x4 + 32) ($topY + 414) ($w4 - 64) 28 8.0 $false $ink 2 | Out-Null

Add-Panel $slide "5" "Validation & analysis" $x5 $topY $w5 $panelH $orange (Rgb 255 245 236)
$thumbW = 118
$thumbH = 72
Add-Text $slide "Candidate validation panels" ($x5 + 20) ($topY + 49) ($w5 - 40) 17 10.5 $true $ink 2 | Out-Null
Add-Box $slide ($x5 + 18) ($topY + 74) $thumbW $thumbH (Rgb 255 255 255) (Rgb 201 210 222) $true 0.8 | Out-Null
Add-PictureFit $slide $figQD ($x5 + 21) ($topY + 78) ($thumbW - 6) ($thumbH - 8) | Out-Null
Add-Text $slide "Quality-diversity" ($x5 + 144) ($topY + 97) 116 20 8.8 $true $ink 1 | Out-Null
Add-Box $slide ($x5 + 18) ($topY + 163) $thumbW $thumbH (Rgb 255 255 255) (Rgb 201 210 222) $true 0.8 | Out-Null
Add-PictureFit $slide $figNovel ($x5 + 21) ($topY + 167) ($thumbW - 6) ($thumbH - 8) | Out-Null
Add-Text $slide "Novelty depth" ($x5 + 144) ($topY + 186) 116 20 8.8 $true $ink 1 | Out-Null
Add-Box $slide ($x5 + 18) ($topY + 252) $thumbW $thumbH (Rgb 255 255 255) (Rgb 201 210 222) $true 0.8 | Out-Null
Add-PictureFit $slide $figPol ($x5 + 21) ($topY + 256) ($thumbW - 6) ($thumbH - 8) | Out-Null
Add-Text $slide "3D polarity proxy" ($x5 + 144) ($topY + 274) 116 20 8.8 $true $ink 1 | Out-Null
foreach ($item in @(@("Uncertainty", 345), @("Exact novelty", 374), @("Diversity filter", 403))) {
    Add-Box $slide ($x5 + 18) ($topY + [int]$item[1]) 110 22 (Rgb 255 255 255) $orange $true 1.0 | Out-Null
    Add-Text $slide $item[0] ($x5 + 22) ($topY + [int]$item[1] + 4) 102 10 7.8 $true $ink 2 | Out-Null
}
Add-Box $slide ($x5 + 152) ($topY + 345) 48 48 (Rgb 255 255 255) $green $true 1.3 | Out-Null
Add-Text $slide "12" ($x5 + 157) ($topY + 354) 38 22 21 $true $ink 2 | Out-Null
Add-Text $slide "optimized`ncandidates" ($x5 + 208) ($topY + 350) 58 30 8.2 $true $ink 1 | Out-Null
Add-Box $slide ($x5 + 152) ($topY + 411) 48 48 (Rgb 255 255 255) $orange $true 1.3 | Out-Null
Add-Text $slide "24" ($x5 + 157) ($topY + 420) 38 22 21 $true $ink 2 | Out-Null
Add-Text $slide "de novo`ncandidates" ($x5 + 208) ($topY + 416) 58 30 8.2 $true $ink 1 | Out-Null

$arrowY = $topY + 243
Add-Arrow $slide ($x1 + $w1 + 5) $arrowY ($x2 - 6) $arrowY $border 2.0 | Out-Null
Add-Arrow $slide ($x2 + $w2 + 5) $arrowY ($x3 - 6) $arrowY $border 2.0 | Out-Null
Add-Arrow $slide ($x3 + $w3 + 5) $arrowY ($x4 - 6) $arrowY $border 2.0 | Out-Null
Add-Arrow $slide ($x4 + $w4 + 5) $arrowY ($x5 - 6) $arrowY $border 2.0 | Out-Null

Add-Box $slide 135 622 930 32 (Rgb 255 255 255) (Rgb 190 203 218) $true 0.9 | Out-Null
Add-Text $slide "Output: membrane-permeable cyclic peptide candidates prioritized by prediction, molecular diversity, novelty depth, uncertainty, and 3D polarity-proxy evidence" 150 629 900 14 8.8 $false $ink 2 | Out-Null

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
