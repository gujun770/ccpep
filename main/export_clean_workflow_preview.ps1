$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pptx = Join-Path $root "molecular_diversity_workflow_clean_editable.pptx"
$png = Join-Path $root "molecular_diversity_workflow_clean_preview.png"

$msoTrue = -1
$msoFalse = 0

$ppt = New-Object -ComObject PowerPoint.Application
$ppt.Visible = $msoTrue
$pres = $ppt.Presentations.Open($pptx, $msoFalse, $msoFalse, $msoFalse)
$slide = $pres.Slides.Item(1)
$slide.Export($png, "PNG", 1600, 900)
$pres.Close()
$ppt.Quit()

[Runtime.InteropServices.Marshal]::ReleaseComObject($slide) | Out-Null
[Runtime.InteropServices.Marshal]::ReleaseComObject($pres) | Out-Null
[Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null

Write-Host "Saved $png"
