$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$srcDocx = Join-Path $root "SCI_submission_revised_v14_workflow_methods.docx"
$mainOut = Join-Path $root "SCI_submission_revised_v15_MolecularDiversity.docx"
$suppOut = Join-Path $root "SCI_submission_supplementary_tables.docx"
$graphicalAbstract = Join-Path $root "Graphical_Abstract_MolecularDiversity.png"
$workflowFig = Join-Path $root "figure1_workflow_for_manuscript.png"
$gaDesc = Join-Path $root "Graphical_Abstract_description.txt"

if (-not (Test-Path -LiteralPath $srcDocx)) { throw "Missing $srcDocx" }

Copy-Item -LiteralPath $srcDocx -Destination $mainOut -Force

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
Add-Type -AssemblyName System.Drawing

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

function Esc($s) {
  return [System.Security.SecurityElement]::Escape([string]$s)
}

function Para($text, $bold = $false) {
  $b = if ($bold) { "<w:b/>" } else { "" }
  return '<w:p><w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>' + $b + '<w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr><w:t>' + (Esc $text) + '</w:t></w:r></w:p>'
}

function Clean-ParagraphText($xml) {
  return (($xml -replace '<w:tab/>',' ' -replace '</w:p>',' ' -replace '<[^>]+>',' ' -replace '&amp;','&' -replace '&lt;','<' -replace '&gt;','>' -replace '\s+',' ').Trim())
}

$zip = [System.IO.Compression.ZipFile]::Open($mainOut, [System.IO.Compression.ZipArchiveMode]::Update)
try {
  $docXml = Read-ZipText $zip "word/document.xml"
  $typesXml = Read-ZipText $zip "[Content_Types].xml"

  # Molecular Diversity asks for Times Roman/10 pt body text. This normalizes explicit run formatting.
  $docXml = [regex]::Replace($docXml, '<w:rFonts[^>]*/>', '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:cs="Times New Roman"/>')
  $docXml = [regex]::Replace($docXml, '<w:sz w:val="\d+"\s*/>', '<w:sz w:val="20"/>')
  $docXml = [regex]::Replace($docXml, '<w:szCs w:val="\d+"\s*/>', '<w:szCs w:val="20"/>')

  # Expand first abstract occurrence of AUROC.
  $docXml = $docXml.Replace(
    "The framework combines HELM-token features, peptide-level physicochemical descriptors, monomer-level aggregate descriptors, natural/non-natural composition, N-methylation ratio, and D-monomer ratio.",
    "The framework combines hierarchical editing language (HELM)-token features, peptide-level physicochemical descriptors, monomer-level aggregate descriptors, natural/non-natural composition, N-methylation ratio, and D-monomer ratio."
  )
  $docXml = $docXml.Replace(
    "The hybrid predictor achieved AUROC=0.846 on the random split but dropped to AUROC=0.625 under source-aware testing",
    "The hybrid predictor achieved area under the receiver operating characteristic curve (AUROC)=0.846 on the random split but dropped to AUROC=0.625 under source-aware testing"
  )
  $docXml = $docXml.Replace(
    "3D polarity-proxy analysis as safeguards",
    "three-dimensional (3D) polarity-proxy analysis as safeguards"
  )

  # Make computational-only scope explicit to avoid requests for synthetic compound characterization data.
  $docXml = $docXml.Replace(
    "All analyses were implemented as executable Python scripts in the project directory.",
    "This study is a computational chemistry and computer-aided drug-design study; no candidate peptides were synthesized, purified, or experimentally characterized, and the generated molecules should be interpreted as virtual priority candidates. All analyses were implemented as executable Python scripts in the project directory."
  )

  # Competing interests wording required even when there is no conflict.
  $docXml = $docXml.Replace(
    "The authors declare no competing interests, unless updated before submission.",
    "The authors declare that they have no relevant financial or non-financial interests to disclose."
  )
  $docXml = $docXml.Replace("<w:t>Declarations</w:t>", "<w:t>Statements and Declarations</w:t>")

  $suppItems = New-Object System.Collections.Generic.List[object]

  # Move Tables 3-11 to supplementary information without touching nearby result text.
  $xmlDoc = New-Object System.Xml.XmlDocument
  $xmlDoc.PreserveWhitespace = $true
  $xmlDoc.LoadXml($docXml)
  $nsmgr = New-Object System.Xml.XmlNamespaceManager($xmlDoc.NameTable)
  $nsmgr.AddNamespace("w", "http://schemas.openxmlformats.org/wordprocessingml/2006/main")
  $body = $xmlDoc.SelectSingleNode("//w:body", $nsmgr)
  $nodes = @($body.ChildNodes)
  for ($i = 0; $i -lt $nodes.Count; $i++) {
    $node = $nodes[$i]
    if ($node.LocalName -ne "p") { continue }
    $captionText = Clean-ParagraphText $node.OuterXml
    $mCap = [regex]::Match($captionText, '^Table ([3-9]|10|11)\.\s*(.+)$')
    if (-not $mCap.Success) { continue }
    $tableNo = [int]$mCap.Groups[1].Value
    $sNo = $tableNo - 2
    $next = $node.NextSibling
    while ($null -ne $next -and $next.NodeType -ne [System.Xml.XmlNodeType]::Element) {
      $next = $next.NextSibling
    }
    if ($null -eq $next -or $next.LocalName -ne "tbl") {
      throw "Could not locate table XML after Table $tableNo caption."
    }
    $suppCaption = "Supplementary Table S$sNo. " + $mCap.Groups[2].Value
    $suppItems.Add([pscustomobject]@{ Caption = $suppCaption; TableXml = $next.OuterXml; Number = $sNo }) | Out-Null
    [void]$body.RemoveChild($next)
    [void]$body.RemoveChild($node)
  }
  $docXml = $xmlDoc.OuterXml

  # Update references to moved tables, using descending order so Table 10/11 are not partially replaced.
  $docXml = $docXml.Replace("Tables 2 and 3", "Table 2 and Supplementary Table S1")
  $docXml = [regex]::Replace($docXml, 'Table 11(?!\d)', 'Supplementary Table S9')
  $docXml = [regex]::Replace($docXml, 'Table 10(?!\d)', 'Supplementary Table S8')
  $docXml = [regex]::Replace($docXml, 'Table 9(?!\d)', 'Supplementary Table S7')
  $docXml = [regex]::Replace($docXml, 'Table 8(?!\d)', 'Supplementary Table S6')
  $docXml = [regex]::Replace($docXml, 'Table 7(?!\d)', 'Supplementary Table S5')
  $docXml = [regex]::Replace($docXml, 'Table 6(?!\d)', 'Supplementary Table S4')
  $docXml = [regex]::Replace($docXml, 'Table 5(?!\d)', 'Supplementary Table S3')
  $docXml = [regex]::Replace($docXml, 'Table 4(?!\d)', 'Supplementary Table S2')
  $docXml = [regex]::Replace($docXml, 'Table 3(?!\d)', 'Supplementary Table S1')

  # Reference DOI format requested by the journal.
  $docXml = [regex]::Replace($docXml, 'doi:(10\.[^<\s]+)', 'https://doi.org/$1')

  # Formula paragraphs are kept intact here; if required by the submission portal,
  # replace equations (1)-(5) using Word Equation Editor or MathType before upload.

  # Add a compact signpost to the supplement after Table 2.
  $table2Block = [regex]::Match($docXml, '<w:p[\s\S]*?<w:t>Table 2\.[\s\S]*?</w:p>\s*<w:tbl[\s\S]*?</w:tbl>')
  if ($table2Block.Success) {
    $note = Para "Additional operating-point metrics, feature ablations, descriptor importances, calibration summaries, candidate-composition statistics, generator ablations, 3D polarity-proxy summaries, and novelty-depth tables are provided in Supplementary Tables S1-S9."
    $docXml = $docXml.Insert($table2Block.Index + $table2Block.Length, $note)
  }

  if ($typesXml -notmatch 'PartName="/word/footer1.xml"') {
    $typesXml = $typesXml.Replace('</Types>', '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>')
  }

  Write-ZipText $zip "word/document.xml" $docXml
  Write-ZipText $zip "[Content_Types].xml" $typesXml
}
finally {
  $zip.Dispose()
}

# Build supplementary-tables DOCX by reusing the cleaned main document shell.
Copy-Item -LiteralPath $mainOut -Destination $suppOut -Force
$zip = [System.IO.Compression.ZipFile]::Open($suppOut, [System.IO.Compression.ZipArchiveMode]::Update)
try {
  $docXml = Read-ZipText $zip "word/document.xml"
  $bodyStart = [regex]::Match($docXml, '<w:body>').Index + '<w:body>'.Length
  $sectPr = [regex]::Match($docXml, '<w:sectPr[\s\S]*?</w:sectPr>').Value
  $suppBody = Para "Supplementary Information" $true
  $suppBody += Para "Supplementary tables for: Descriptor-guided robust prediction and dual-route design of membrane-permeable cyclic peptides"
  foreach ($item in $suppItems) {
    $suppBody += Para $item.Caption $true
    $suppBody += $item.TableXml
  }
  $docXml = $docXml.Substring(0, $bodyStart) + $suppBody + $sectPr + '</w:body></w:document>'
  Write-ZipText $zip "word/document.xml" $docXml
}
finally {
  $zip.Dispose()
}

# Graphical abstract asset: same workflow figure, white background, width >=1328 px and height >=531 px.
if (Test-Path -LiteralPath $workflowFig) {
  $img = [System.Drawing.Image]::FromFile($workflowFig)
  try {
    $targetW = [Math]::Max(1328, $img.Width)
    $targetH = [int][Math]::Round($img.Height * ($targetW / [double]$img.Width))
    if ($targetH -lt 531) {
      $targetH = 531
    }
    $bmp = New-Object System.Drawing.Bitmap $targetW, $targetH
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    try {
      $g.Clear([System.Drawing.Color]::White)
      $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
      $g.DrawImage($img, 0, 0, $targetW, $targetH)
      $bmp.Save($graphicalAbstract, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
      $g.Dispose()
      $bmp.Dispose()
    }
  }
  finally {
    $img.Dispose()
  }
  "Descriptor-guided cyclic peptide permeability prediction and diversity-focused candidate design." | Set-Content -LiteralPath $gaDesc -Encoding UTF8
}

Write-Host "Saved $mainOut"
Write-Host "Saved $suppOut"
Write-Host "Saved $graphicalAbstract"
