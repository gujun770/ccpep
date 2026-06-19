$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$srcDocx = Join-Path $root "SCI_submission_revised_v12.docx"
$outDocx = Join-Path $root "SCI_submission_revised_v14_workflow_methods.docx"
$figurePng = Join-Path $root "figure1_workflow_for_manuscript.png"

if (-not (Test-Path -LiteralPath $srcDocx)) { throw "Missing $srcDocx" }
if (-not (Test-Path -LiteralPath $figurePng)) { throw "Missing $figurePng" }

Copy-Item -LiteralPath $srcDocx -Destination $outDocx -Force

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Read-ZipText($zip, $name) {
  $entry = $zip.GetEntry($name)
  if ($null -eq $entry) { throw "Missing zip entry $name" }
  $stream = $entry.Open()
  $reader = New-Object System.IO.StreamReader($stream)
  try { return $reader.ReadToEnd() }
  finally { $reader.Dispose() }
}

function Write-ZipText($zip, $name, $text) {
  $old = $zip.GetEntry($name)
  if ($null -ne $old) { $old.Delete() }
  $entry = $zip.CreateEntry($name)
  $stream = $entry.Open()
  $writer = New-Object System.IO.StreamWriter($stream, [System.Text.UTF8Encoding]::new($false))
  try { $writer.Write($text) }
  finally { $writer.Dispose() }
}

function Write-ZipBytes($zip, $name, $bytes) {
  $old = $zip.GetEntry($name)
  if ($null -ne $old) { $old.Delete() }
  $entry = $zip.CreateEntry($name)
  $stream = $entry.Open()
  try { $stream.Write($bytes, 0, $bytes.Length) }
  finally { $stream.Dispose() }
}

function Esc($s) {
  return [System.Security.SecurityElement]::Escape([string]$s)
}

$zip = [System.IO.Compression.ZipFile]::Open($outDocx, [System.IO.Compression.ZipArchiveMode]::Update)
try {
  $docXml = Read-ZipText $zip "word/document.xml"
  $relsXml = Read-ZipText $zip "word/_rels/document.xml.rels"
  $typesXml = Read-ZipText $zip "[Content_Types].xml"

  # Existing result figures become Figure 2-8 after adding the workflow as Figure 1.
  $docXml = [regex]::Replace($docXml, 'Figure ([1-7])(?=[\.\s,\)])', {
    param($m)
    "Figure " + ([int]$m.Groups[1].Value + 1)
  })

  # Methods section signposts. These are deliberately short so the original content is preserved.
  $docXml = $docXml.Replace(
    "The working dataset was reconstructed from the public CycPeptMPDB peptide table.",
    "As shown in Stage 1 of Figure 1, the working dataset was reconstructed from the public CycPeptMPDB peptide table."
  )
  $docXml = $docXml.Replace(
    "The feature representation avoided private molecular dynamics trajectories.",
    "Stage 2 of Figure 1 summarizes the feature representation, which avoided private molecular dynamics trajectories."
  )
  $docXml = $docXml.Replace(
    "We compared three main predictor families.",
    "Stage 3 of Figure 1 summarizes the source-aware scoring module. We compared three main predictor families."
  )
  $docXml = $docXml.Replace(
    "The constrained optimization route starts from high-quality seeds and applies single- or double-site monomer substitutions.",
    "Stage 4 of Figure 1 summarizes the dual-route design module. The constrained optimization route starts from high-quality seeds and applies single- or double-site monomer substitutions."
  )
  $docXml = $docXml.Replace(
    "Generated candidates were evaluated using exact novelty against the training set, uniqueness, pairwise Jaccard diversity, quality-diversity tradeoff, generator ablation, uncertainty summaries, source-heterogeneity analysis, 3D polarity proxy nearest-neighbor analysis, and token/descriptor-space novelty depth.",
    "Stage 5 of Figure 1 summarizes the validation and analysis module. Generated candidates were evaluated using exact novelty against the training set, uniqueness, pairwise Jaccard diversity, quality-diversity tradeoff, generator ablation, uncertainty summaries, source-heterogeneity analysis, 3D polarity proxy nearest-neighbor analysis, and token/descriptor-space novelty depth."
  )

  # Normalize table-border child order inherited from the earlier DOCX generator.
  $docXml = [regex]::Replace($docXml, '<w:tblBorders><w:top([^>]*)/><w:bottom([^>]*)/><w:left([^>]*)/><w:right([^>]*)/><w:insideH([^>]*)/><w:insideV([^>]*)/></w:tblBorders>', {
    param($m)
    '<w:tblBorders><w:top' + $m.Groups[1].Value + '/><w:left' + $m.Groups[3].Value + '/><w:bottom' + $m.Groups[2].Value + '/><w:right' + $m.Groups[4].Value + '/><w:insideH' + $m.Groups[5].Value + '/><w:insideV' + $m.Groups[6].Value + '/></w:tblBorders>'
  })

  $caption = "Figure 1. Overall framework for the descriptor-guided prediction and dual-route design of membrane-permeable cyclic peptides. The pipeline consists of five key stages: (1) Data curation: reconstructing the cyclic peptide dataset from CycPeptMPDB while highlighting literature source heterogeneity; (2) Descriptor representation: extracting multimodal features, including 2D physicochemical descriptors, 3D polarity proxies, HELM-token features, and composition descriptors; (3) Source-aware scoring: developing a hybrid permeability predictor evaluated via a Leave-One-Source-Out (LOSO) protocol, which exposes the generalization gap hidden by random dataset splits; (4) Dual-route design: generating candidates through local structural optimization (Route A) and fragment-based de novo exploration (Route B), guided by multi-objective optimization balancing permeability, polarity, diversity, and uncertainty; and (5) Validation and analysis: assessing the 12 optimized and 24 de novo candidates through uncertainty estimates, 3D polarity proxies, and structural novelty/diversity checks."

  $rid = "rId1001"
  $mediaName = "word/media/figure1_workflow_overview.png"
  $cx = 5943600
  $cy = 3343275
  $docPrId = 1001
  $docPrMatches = [regex]::Matches($docXml, 'wp:docPr id="(\d+)"')
  if ($docPrMatches.Count -gt 0) {
    $maxId = ($docPrMatches | ForEach-Object { [int]$_.Groups[1].Value } | Measure-Object -Maximum).Maximum
    $docPrId = [int]$maxId + 1
  }

  $imageParagraph = @"
<w:p><w:pPr><w:jc w:val="center" /></w:pPr><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="$cx" cy="$cy" /><wp:effectExtent l="0" t="0" r="0" b="0" /><wp:docPr id="$docPrId" name="Figure 1 workflow overview" /><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1" /></wp:cNvGraphicFramePr><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="figure1_workflow_overview.png" /><pic:cNvPicPr /></pic:nvPicPr><pic:blipFill><a:blip r:embed="$rid" /><a:stretch><a:fillRect /></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0" /><a:ext cx="$cx" cy="$cy" /></a:xfrm><a:prstGeom prst="rect"><a:avLst /></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>
"@
  $captionParagraph = '<w:p><w:r><w:t>' + (Esc $caption) + '</w:t></w:r></w:p>'
  $insertXml = $imageParagraph + $captionParagraph

  $methodsHeading = [regex]::Matches($docXml, '<w:p[\s\S]*?</w:p>') | Where-Object { $_.Value -like '*<w:t>3. Materials and Methods</w:t>*' } | Select-Object -First 1
  if ($null -eq $methodsHeading) { throw "Could not find Materials and Methods heading for figure insertion." }
  $docXml = $docXml.Remove($methodsHeading.Index, $methodsHeading.Length).Insert($methodsHeading.Index, $methodsHeading.Value + $insertXml)

  if ($relsXml -notmatch [regex]::Escape($rid)) {
    $rel = '<ns0:Relationship Id="' + $rid + '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/figure1_workflow_overview.png" />'
    if ($relsXml -match '</ns0:Relationships>') {
      $relsXml = $relsXml.Replace('</ns0:Relationships>', $rel + '</ns0:Relationships>')
    } else {
      $relsXml = $relsXml.Replace('</Relationships>', '<Relationship Id="' + $rid + '" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/figure1_workflow_overview.png" /></Relationships>')
    }
  }

  if ($typesXml -notmatch 'Extension="png"') {
    $typesXml = $typesXml.Replace('</Types>', '<Default Extension="png" ContentType="image/png"/></Types>')
  }
  if ($typesXml -notmatch 'PartName="/word/footer1.xml"') {
    $typesXml = $typesXml.Replace('</Types>', '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>')
  }

  Write-ZipText $zip "word/document.xml" $docXml
  Write-ZipText $zip "word/_rels/document.xml.rels" $relsXml
  Write-ZipText $zip "[Content_Types].xml" $typesXml
  Write-ZipBytes $zip $mediaName ([System.IO.File]::ReadAllBytes($figurePng))
}
finally {
  $zip.Dispose()
}

Write-Host "Saved $outDocx"
