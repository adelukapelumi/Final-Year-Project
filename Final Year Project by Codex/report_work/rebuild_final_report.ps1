$ErrorActionPreference = "Stop"

$projectDir = Resolve-Path (Join-Path $PSScriptRoot "..")
$draftPath = Join-Path $projectDir "Draft of Final Year Project with Mendeley cite.docx"
$samplePath = Join-Path $projectDir "Sample 2.docx"
$outputPath = Join-Path $projectDir "Defense Ready Final Year Project Report.docx"
$backupDir = Join-Path $projectDir "report_work\backups"
$orderedJsonPath = Join-Path $projectDir "report_work\draft_ordered.json"
$draftExtractPath = Join-Path $projectDir "report_work\draft_extract.json"
$screenshotsDir = Join-Path $projectDir "report_assets\screenshots"
$diagramsDir = Join-Path $projectDir "report_assets\diagrams"
$benchmarkJsonPath = Join-Path $projectDir "benchmark_results.json"
$logPath = Join-Path $projectDir "report_work\runtime\rebuild_final_report.log"

$wdCollapseStart = 1
$wdCollapseEnd = 0
$wdPageBreak = 7
$wdSectionBreakNextPage = 2
$wdAlignLeft = 0
$wdAlignCenter = 1
$wdLineSpaceMultiple = 4
$wdSeekMainDocument = 0
$wdHeaderFooterPrimary = 1
$wdPageNumberStyleArabic = 0
$wdPageNumberStyleLowercaseRoman = 2
$wdStatisticPages = 2

function Write-Log {
    param([string]$Message)
    Add-Content -Path $logPath -Value $Message
    Write-Host $Message
}

function Clean-Text {
    param([string]$Text)
    if ($null -eq $Text) { return "" }
    return ($Text -replace "[`r`a]", "").Trim()
}

function Read-JsonCompat {
    param([string]$Path)

    $raw = Get-Content -Raw $Path
    $cmd = Get-Command ConvertFrom-Json
    $supportsDepth = $false
    if ($cmd -and $cmd.Parameters) {
        $supportsDepth = $cmd.Parameters.ContainsKey("Depth")
    }

    if ($supportsDepth) {
        return $raw | ConvertFrom-Json -Depth 100
    }

    return $raw | ConvertFrom-Json
}

function Add-Paragraph {
    param(
        [object]$Selection,
        [object]$Word,
        [string]$Text,
        [double]$LineMultiple = 1.5,
        [double]$SpaceBefore = 0,
        [double]$SpaceAfter = 6,
        [double]$FontSize = 12,
        [bool]$Bold = $false,
        [bool]$Italic = $false,
        [int]$Alignment = $wdAlignLeft,
        [double]$LeftIndentCm = 0,
        [double]$FirstLineIndentCm = 0
    )

    $Selection.Font.Name = "Times New Roman"
    $Selection.Font.Size = $FontSize
    $Selection.Font.Bold = [int]$Bold
    $Selection.Font.Italic = [int]$Italic
    $Selection.ParagraphFormat.Alignment = $Alignment
    $Selection.ParagraphFormat.LineSpacingRule = $wdLineSpaceMultiple
    $Selection.ParagraphFormat.LineSpacing = $Word.LinesToPoints($LineMultiple)
    $Selection.ParagraphFormat.SpaceBefore = $SpaceBefore
    $Selection.ParagraphFormat.SpaceAfter = $SpaceAfter
    $Selection.ParagraphFormat.LeftIndent = $Word.CentimetersToPoints($LeftIndentCm)
    $Selection.ParagraphFormat.FirstLineIndent = $Word.CentimetersToPoints($FirstLineIndentCm)
    $Selection.TypeText($Text)
    $Selection.TypeParagraph()
}

function Add-Heading {
    param(
        [object]$Selection,
        [object]$Word,
        [string]$Text,
        [int]$Level = 1,
        [int]$Alignment = $wdAlignLeft
    )

    $styleName = switch ($Level) {
        1 { "Heading 1" }
        2 { "Heading 2" }
        default { "Heading 3" }
    }
    $Selection.Style = $styleName
    Add-Paragraph -Selection $Selection -Word $Word -Text $Text -LineMultiple 1.5 -SpaceBefore 6 -SpaceAfter 6 -FontSize 12 -Bold $true -Alignment $Alignment
}

function Add-BlankParagraph {
    param([object]$Selection, [int]$Count = 1)
    for ($i = 0; $i -lt $Count; $i++) {
        $Selection.TypeParagraph()
    }
}

function Set-PageNumbers {
    param(
        [object]$Section,
        [int]$Style,
        [int]$StartAt,
        [bool]$ShowNumbers
    )

    $Section.Headers.Item($wdHeaderFooterPrimary).PageNumbers.RestartNumberingAtSection = $true
    $Section.Headers.Item($wdHeaderFooterPrimary).PageNumbers.StartingNumber = $StartAt
    $Section.Headers.Item($wdHeaderFooterPrimary).PageNumbers.NumberStyle = $Style
    if ($ShowNumbers) {
        $null = $Section.Headers.Item($wdHeaderFooterPrimary).PageNumbers.Add(2)
    }
}

function Convert-ToRoman {
    param([int]$Number)

    $map = @(
        @{ Value = 1000; Symbol = "M" },
        @{ Value = 900; Symbol = "CM" },
        @{ Value = 500; Symbol = "D" },
        @{ Value = 400; Symbol = "CD" },
        @{ Value = 100; Symbol = "C" },
        @{ Value = 90; Symbol = "XC" },
        @{ Value = 50; Symbol = "L" },
        @{ Value = 40; Symbol = "XL" },
        @{ Value = 10; Symbol = "X" },
        @{ Value = 9; Symbol = "IX" },
        @{ Value = 5; Symbol = "V" },
        @{ Value = 4; Symbol = "IV" },
        @{ Value = 1; Symbol = "I" }
    )

    $result = ""
    $remaining = $Number
    foreach ($item in $map) {
        while ($remaining -ge $item.Value) {
            $result += $item.Symbol
            $remaining -= $item.Value
        }
    }
    return $result.ToLower()
}

function Add-ManualListEntries {
    param(
        [object]$Doc,
        [object]$Selection,
        [object]$Word,
        [string]$Placeholder,
        [System.Collections.IEnumerable]$Entries,
        [bool]$UseRoman
    )

    $range = $Doc.Content
    $find = $range.Find
    $find.ClearFormatting()
    $find.Text = $Placeholder
    if (-not $find.Execute()) {
        return
    }

    $range.Text = ""
    $Selection.SetRange($range.Start, $range.Start)
    foreach ($entry in $Entries) {
        $pageText = if ($UseRoman -and $entry.Prelim) { Convert-ToRoman([int]$entry.Page) } else { [string]$entry.Page }
        Add-Paragraph -Selection $Selection -Word $Word -Text ("{0}`t{1}" -f $entry.Title, $pageText) -LineMultiple $(if ($UseRoman) { 1.15 } else { 1.5 }) -SpaceAfter 0 -FontSize 11
        $Selection.Paragraphs.Last.TabStops.ClearAll()
        [void]$Selection.Paragraphs.Last.TabStops.Add($Word.CentimetersToPoints(15.5), 2, 1)
    }
}

function Add-TableFromRows {
    param(
        [object]$Doc,
        [object]$Selection,
        [object]$Word,
        [object[]]$Rows
    )

    $rowCount = $Rows.Count
    $colCount = 0
    foreach ($row in $Rows) {
        if ($row.Count -gt $colCount) { $colCount = $row.Count }
    }
    $table = $Doc.Tables.Add($Selection.Range, $rowCount, $colCount)
    $table.Borders.Enable = 1
    $table.Range.Font.Name = "Times New Roman"
    $table.Range.Font.Size = 11
    $table.Range.ParagraphFormat.LineSpacingRule = $wdLineSpaceMultiple
    $table.Range.ParagraphFormat.LineSpacing = $Word.LinesToPoints(1.5)
    $table.Rows.Item(1).Range.Bold = 1
    $table.Range.Cells.VerticalAlignment = 1
    for ($r = 1; $r -le $rowCount; $r++) {
        $cells = $Rows[$r - 1]
        for ($c = 1; $c -le $colCount; $c++) {
            $text = ""
            if ($c -le $cells.Count) { $text = [string]$cells[$c - 1] }
            $table.Cell($r, $c).Range.Text = $text
        }
    }
    $table.AutoFitBehavior(2) | Out-Null
    $Selection.SetRange($table.Range.End, $table.Range.End)
    $Selection.TypeParagraph()
}

function Add-EmbeddedFigure {
    param(
        [object]$Selection,
        [object]$Word,
        [string]$IntroText,
        [string]$ImagePath,
        [string]$CaptionText,
        [double]$MaxWidthCm = 14.5
    )

    Add-Paragraph -Selection $Selection -Word $Word -Text $IntroText -LineMultiple 1.5 -SpaceAfter 6
    $Selection.ParagraphFormat.Alignment = $wdAlignCenter
    $shape = $Selection.InlineShapes.AddPicture($ImagePath, $false, $true)
    $maxWidth = $Word.CentimetersToPoints($MaxWidthCm)
    if ($shape.Width -gt $maxWidth) {
        $shape.LockAspectRatio = $true
        $shape.Width = $maxWidth
    }
    $Selection.TypeParagraph()
    Add-Paragraph -Selection $Selection -Word $Word -Text $CaptionText -LineMultiple 1.0 -SpaceAfter 12 -FontSize 11 -Italic $true -Alignment $wdAlignCenter
}

function Convert-ObjectiveToNumber {
    param([string]$Text)
    switch ($Text) {
        "To review existing e-voting systems and the cryptographic approaches they use." { return "1. To review existing e-voting systems and the cryptographic approaches they use." }
        "To analyse the security requirements and threat model for diaspora e-voting." { return "2. To analyse the security requirements and threat model for diaspora e-voting." }
        "To design a zk-STARK-based ballot validity constraint system." { return "3. To design a zk-STARK-based ballot validity constraint system." }
        "To implement a working prototype integrating zk-STARK proof generation, encrypted ballot submission, and public verification." { return "4. To implement a working prototype integrating zk-STARK proof generation, encrypted ballot submission, and public verification." }
        "To evaluate the prototype’s performance and security properties." { return "5. To evaluate the prototype’s performance and security properties." }
        default { return $Text }
    }
}

function Build-ReferenceList {
    return @(
        "Adida, B. (2008). Helios: Web-based open-audit voting. Proceedings of the 17th USENIX Security Symposium, 335-348.",
        "Ali, S. T., & Murray, J. (2016). An overview of end-to-end verifiable voting systems. arXiv. https://arxiv.org/abs/1605.08554",
        "Alsadi, M., Casey, M., Dragan, C. C., Dupressoir, F., Riley, L., Sallal, M., Schneider, S., Treharne, H., Wadsworth, J., & Wright, P. (2019). Towards end-to-end verifiable online voting: Adding verifiability to established voting systems. arXiv. https://arxiv.org/abs/1912.00288",
        "Ben-Sasson, E., Bentov, I., Horesh, Y., & Riabzev, M. (2018). Scalable, transparent, and post-quantum secure computational integrity. IACR ePrint Archive, 2018/046. https://eprint.iacr.org/2018/046",
        "Chondros, N., Zhang, B., Zacharias, T., Diamantopoulos, P., Maneas, S., Patsonakis, C., Delis, A., Kiayias, A., & Roussopoulos, M. (2015). D-DEMOS: A distributed, end-to-end verifiable, internet voting system. arXiv. https://arxiv.org/abs/1507.06812",
        "Federal Republic of Nigeria. (2022). Electoral Act, 2022.",
        "Goldwasser, S., Micali, S., & Rackoff, C. (1989). The knowledge complexity of interactive proof systems. SIAM Journal on Computing, 18(1), 186-208. https://doi.org/10.1137/0218012",
        "International IDEA. (2007). Voting from abroad: The International IDEA handbook. International Institute for Democracy and Electoral Assistance.",
        "McMurtry, E., Boyen, X., Culnane, C., Gjøsteen, K., Haines, T., & Teague, V. (2021). Towards verifiable remote voting with paper assurance. arXiv. https://arxiv.org/abs/2111.04210",
        "Quaglia, E. A., & Smyth, B. (2017). A short introduction to secrecy and verifiability for elections. arXiv. https://arxiv.org/abs/1702.03168",
        "University of Lorraine, CNRS, & Inria. (n.d.). Belenios online voting system. https://www.belenios.org/"
    )
}

function Add-ChapterFive {
    param([object]$Selection, [object]$Word)

    $Selection.InsertBreak($wdPageBreak)
    Add-Heading -Selection $Selection -Word $Word -Text "CHAPTER FIVE: SUMMARY, RECOMMENDATIONS, LIMITATIONS, AND CONCLUSION" -Level 1 -Alignment $wdAlignCenter
    Add-Heading -Selection $Selection -Word $Word -Text "5.1 Summary" -Level 2
    Add-Paragraph -Selection $Selection -Word $Word -Text "This study designed and implemented a secure diaspora e-voting prototype for a controlled Nigerian referendum scenario using zk-STARK protocols. The completed system combined a React-based frontend, a Flask backend, SQLite persistence, a mock NIN registry, and a Winterfell-based proof engine to demonstrate an end-to-end workflow from accreditation through receipt verification and tally display." -LineMultiple 1.5
    Add-Paragraph -Selection $Selection -Word $Word -Text "The study also demonstrated that remote voting trust depends on more than interface design. The implemented prototype brought together mock eligibility checks, duplicate-vote prevention, proof-backed ballot acceptance, encrypted vote storage, public receipt metadata, and event-aware tallying. This combination made the system suitable as a scope-controlled final year implementation that demonstrates verifiability concepts without overclaiming institutional readiness." -LineMultiple 1.5
    Add-Heading -Selection $Selection -Word $Word -Text "5.2 Recommendations" -Level 2
    Add-Paragraph -Selection $Selection -Word $Word -Text "The following recommendations arise from the implementation and evaluation of the study:" -LineMultiple 1.5
    foreach ($item in @(
        "1. Future work should add independent local proof verification so that verification does not rely entirely on the backend server.",
        "2. Future work should evaluate stronger identity-assurance models only under proper legal, privacy, and institutional controls.",
        "3. A formal security review should be carried out on both the proof workflow and the surrounding application logic.",
        "4. Larger-scale benchmarking should be performed under higher ballot volumes and concurrent-user conditions.",
        "5. Further research should examine coercion resistance, usability testing, and broader public-audit models for remote voting."
    )) {
        Add-Paragraph -Selection $Selection -Word $Word -Text $item -LineMultiple 1.5 -LeftIndentCm 0.4 -FirstLineIndentCm 0
    }
    Add-Heading -Selection $Selection -Word $Word -Text "5.3 Limitations of the Study" -Level 2
    Add-Paragraph -Selection $Selection -Word $Word -Text "The prototype was intentionally limited so that its claims remained academically defensible. First, the identity layer used a mock NIN registry and did not connect to live national identity infrastructure. Second, the camera-based verification step was a prototype face-presence check rather than certified biometric identity matching. Third, the public verification workflow remained server-mediated and did not yet provide a fully independent local verifier. Fourth, the ballot model was limited to a controlled binary referendum rather than a full multi-candidate national election. Finally, the architecture remained a prototype implementation and was not presented as production-ready for official deployment." -LineMultiple 1.5
    Add-Heading -Selection $Selection -Word $Word -Text "5.4 Conclusion" -Level 2
    Add-Paragraph -Selection $Selection -Word $Word -Text "The study achieved its aim of designing and implementing a secure diaspora e-voting prototype using zk-STARK protocols. Within the scope of a final year project, the implemented system showed that proof-backed ballot acceptance, controlled accreditation, privacy-preserving public verification metadata, and event-aware tallying can be combined into a coherent remote-voting workflow. The key conclusion is therefore not that diaspora voting has been solved in practice, but that a careful and scope-controlled prototype can make the security and verification problem concrete, testable, and academically meaningful for future work." -LineMultiple 1.5
}

function Add-ReferencesSection {
    param([object]$Selection, [object]$Word)

    Add-Heading -Selection $Selection -Word $Word -Text "REFERENCES" -Level 1 -Alignment $wdAlignCenter
    foreach ($item in Build-ReferenceList) {
        Add-Paragraph -Selection $Selection -Word $Word -Text $item -LineMultiple 1.0 -SpaceAfter 6 -LeftIndentCm 0.63 -FirstLineIndentCm -0.63
    }
}

New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $logPath) | Out-Null
Set-Content -Path $logPath -Value ("rebuild started {0}" -f (Get-Date -Format s))

if (-not (Test-Path $orderedJsonPath)) {
    Write-Log "extracting ordered draft content"
    @"
from pathlib import Path
import subprocess, sys
root = Path(r"$PSScriptRoot")
"@ | Out-Null
    & python (Join-Path $PSScriptRoot "extract_ordered_docx.py") $draftPath --json $orderedJsonPath
}

$ordered = Read-JsonCompat -Path $orderedJsonPath
$draftExtract = Read-JsonCompat -Path $draftExtractPath
$benchmark = Read-JsonCompat -Path $benchmarkJsonPath

if (Test-Path $outputPath) {
    $backupName = "Defense Ready Final Year Project Report - pre-rebuild backup {0}.docx" -f (Get-Date -Format "yyyy-MM-dd-HHmmss")
    Copy-Item $outputPath (Join-Path $backupDir $backupName) -Force
}

$word = $null
$doc = $null

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    Write-Log "creating new Word document"
    $doc = $word.Documents.Add()
    $selection = $word.Selection

    $doc.PageSetup.TopMargin = $word.CentimetersToPoints(2.54)
    $doc.PageSetup.BottomMargin = $word.CentimetersToPoints(2.54)
    $doc.PageSetup.RightMargin = $word.CentimetersToPoints(2.54)
    $doc.PageSetup.LeftMargin = $word.CentimetersToPoints(3.0)

    Write-Log "writing front matter"
    Add-BlankParagraph -Selection $selection -Count 4
    Add-Paragraph -Selection $selection -Word $word -Text "DESIGN AND IMPLEMENTATION OF A SECURE DIASPORA E-VOTING PROTOTYPE USING zk-STARK PROTOCOLS" -LineMultiple 1.15 -SpaceAfter 18 -FontSize 16 -Bold $true -Alignment $wdAlignCenter
    Add-BlankParagraph -Selection $selection -Count 2
    Add-Paragraph -Selection $selection -Word $word -Text "BY" -LineMultiple 1.15 -SpaceAfter 12 -FontSize 12 -Bold $true -Alignment $wdAlignCenter
    Add-Paragraph -Selection $selection -Word $word -Text "ADELUKA OLUWAMBEPELUMI EMMANUEL" -LineMultiple 1.15 -SpaceAfter 18 -FontSize 14 -Bold $true -Alignment $wdAlignCenter
    Add-BlankParagraph -Selection $selection -Count 2
    Add-Paragraph -Selection $selection -Word $word -Text "A PROJECT SUBMITTED TO THE DEPARTMENT OF COMPUTER AND INFORMATION SCIENCES, COLLEGE OF SCIENCE AND TECHNOLOGY, COVENANT UNIVERSITY, OTA, OGUN STATE." -LineMultiple 1.15 -Alignment $wdAlignCenter
    Add-Paragraph -Selection $selection -Word $word -Text "IN PARTIAL FULFILMENT OF THE REQUIREMENTS FOR THE AWARD OF THE BACHELOR OF SCIENCE (HONOURS) DEGREE IN COMPUTER SCIENCE." -LineMultiple 1.15 -Alignment $wdAlignCenter
    Add-BlankParagraph -Selection $selection -Count 3
    Add-Paragraph -Selection $selection -Word $word -Text "JUNE, 2026" -LineMultiple 1.15 -SpaceAfter 0 -FontSize 12 -Bold $true -Alignment $wdAlignCenter

    $selection.InsertBreak($wdSectionBreakNextPage)
    Add-Heading -Selection $selection -Word $word -Text "CERTIFICATION" -Level 1 -Alignment $wdAlignCenter
    Add-Paragraph -Selection $selection -Word $word -Text "I hereby certify that this project was carried out by Adeluka Oluwambepelumi Emmanuel in the Department of Computer and Information Sciences, College of Science and Technology, Covenant University, Ota, Ogun State, Nigeria, under appropriate academic supervision." -LineMultiple 1.5
    Add-BlankParagraph -Selection $selection -Count 4
    Add-Paragraph -Selection $selection -Word $word -Text "______________________________`t`t______________________________" -LineMultiple 1.15
    Add-Paragraph -Selection $selection -Word $word -Text "Supervisor`t`t`t`tSignature and Date" -LineMultiple 1.15
    Add-BlankParagraph -Selection $selection -Count 2
    Add-Paragraph -Selection $selection -Word $word -Text "______________________________`t`t______________________________" -LineMultiple 1.15
    Add-Paragraph -Selection $selection -Word $word -Text "Head of Department`t`t`tSignature and Date" -LineMultiple 1.15

    $selection.InsertBreak($wdPageBreak)
    Add-Heading -Selection $selection -Word $word -Text "DEDICATION" -Level 1 -Alignment $wdAlignCenter
    Add-Paragraph -Selection $selection -Word $word -Text "This work is dedicated to God and to everyone whose support, encouragement, and discipline made the successful completion of this project possible." -LineMultiple 1.15 -Alignment $wdAlignCenter

    $selection.InsertBreak($wdPageBreak)
    Add-Heading -Selection $selection -Word $word -Text "ACKNOWLEDGEMENTS" -Level 1 -Alignment $wdAlignCenter
    Add-Paragraph -Selection $selection -Word $word -Text "My sincere gratitude goes to God for His grace, strength, and guidance throughout the course of this project. I am also grateful to my family and loved ones for their patience, encouragement, and support during the research, implementation, and documentation stages of this work." -LineMultiple 1.5
    Add-Paragraph -Selection $selection -Word $word -Text "I further appreciate the academic guidance, technical feedback, and institutional support received from the Department of Computer and Information Sciences, Covenant University. The comments and reviews provided during the development of the DiasporaVote prototype contributed significantly to the clarity, scope control, and final presentation of this study." -LineMultiple 1.5

    $selection.InsertBreak($wdPageBreak)
    Add-Heading -Selection $selection -Word $word -Text "TABLE OF CONTENT" -Level 1 -Alignment $wdAlignCenter
    Add-Paragraph -Selection $selection -Word $word -Text "[[TOC_BODY]]" -LineMultiple 1.15 -SpaceAfter 0 -FontSize 11

    $selection.InsertBreak($wdPageBreak)
    Add-Heading -Selection $selection -Word $word -Text "LIST OF FIGURES" -Level 1 -Alignment $wdAlignCenter
    Add-Paragraph -Selection $selection -Word $word -Text "[[LOF_BODY]]" -LineMultiple 1.15 -SpaceAfter 0 -FontSize 11

    $selection.InsertBreak($wdPageBreak)
    Add-Heading -Selection $selection -Word $word -Text "LIST OF TABLES" -Level 1 -Alignment $wdAlignCenter
    Add-Paragraph -Selection $selection -Word $word -Text "[[LOT_BODY]]" -LineMultiple 1.15 -SpaceAfter 0 -FontSize 11

    $selection.InsertBreak($wdPageBreak)
    Add-Heading -Selection $selection -Word $word -Text "ABBREVIATIONS" -Level 1 -Alignment $wdAlignCenter
    foreach ($line in @(
        "API`tApplication Programming Interface",
        "BVAS`tBimodal Voter Accreditation System",
        "CIS`tComputer and Information Sciences",
        "HTML`tHyperText Markup Language",
        "INEC`tIndependent National Electoral Commission",
        "NIMC`tNational Identity Management Commission",
        "NIN`tNational Identification Number",
        "RAM`tRandom Access Memory",
        "STARK`tScalable Transparent Argument of Knowledge",
        "UI`tUser Interface",
        "URL`tUniform Resource Locator",
        "ZKP`tZero-Knowledge Proof"
    )) {
        Add-Paragraph -Selection $selection -Word $word -Text $line -LineMultiple 1.15 -SpaceAfter 0 -FontSize 11
        $selection.Paragraphs.Last.TabStops.ClearAll()
        [void]$selection.Paragraphs.Last.TabStops.Add($word.CentimetersToPoints(3.5), 0, 0)
    }

    $selection.InsertBreak($wdPageBreak)
    Add-Heading -Selection $selection -Word $word -Text "ABSTRACT" -Level 1 -Alignment $wdAlignCenter
    Add-Paragraph -Selection $selection -Word $word -Text "This study addressed the challenge of how secure diaspora voting could be demonstrated in a controlled Nigerian context without overclaiming institutional integration or national-election readiness. The project designed and implemented DiasporaVote, a secure binary referendum prototype that combined a React frontend, a Flask backend, SQLite persistence, a mock National Identification Number registry, and a Winterfell-based zk-STARK proof engine. The implemented workflow covered mock voter accreditation, camera-based prototype verification, event-aware ballot access, controlled Yes/No vote submission, proof generation and verification, encrypted ballot storage, receipt issuance, public-board publication of privacy-preserving verification metadata, and tally display for the active referendum event. System evaluation included registered-voter login, rejection of unregistered users, verification-state enforcement, valid and invalid ballot handling, duplicate-vote rejection, proof-engine health checking, proof verification, tally behaviour, admin registry operations, deployment smoke testing, and persistence checks. Direct proof-engine benchmarks showed sub-millisecond average proof-generation and proof-verification times with proof sizes of roughly 4.5 KB. The study therefore demonstrated a technically defensible diaspora voting prototype that integrates proof-backed ballot acceptance and public verification while clearly stating its limits, including mock identity assurance, binary-ballot scope, and non-production status." -LineMultiple 1.0 -SpaceAfter 12
    Add-Paragraph -Selection $selection -Word $word -Text "Keywords: diaspora voting, e-voting, zk-STARK, zero-knowledge proof, public verification, referendum prototype" -LineMultiple 1.0 -SpaceAfter 0 -FontSize 11 -Italic $true

    $selection.InsertBreak($wdSectionBreakNextPage)

    Write-Log "configuring page numbering"
    $doc.Sections.Item(1).Headers.Item($wdHeaderFooterPrimary).PageNumbers.RestartNumberingAtSection = $true
    $doc.Sections.Item(1).Headers.Item($wdHeaderFooterPrimary).PageNumbers.StartingNumber = 1
    $doc.Sections.Item(1).Headers.Item($wdHeaderFooterPrimary).PageNumbers.NumberStyle = $wdPageNumberStyleLowercaseRoman
    $doc.Sections.Item(2).Headers.Item($wdHeaderFooterPrimary).PageNumbers.RestartNumberingAtSection = $true
    $doc.Sections.Item(2).Headers.Item($wdHeaderFooterPrimary).PageNumbers.StartingNumber = 2
    $doc.Sections.Item(2).Headers.Item($wdHeaderFooterPrimary).PageNumbers.NumberStyle = $wdPageNumberStyleLowercaseRoman
    $null = $doc.Sections.Item(2).Headers.Item($wdHeaderFooterPrimary).PageNumbers.Add(2)
    $doc.Sections.Item(3).Headers.Item($wdHeaderFooterPrimary).PageNumbers.RestartNumberingAtSection = $true
    $doc.Sections.Item(3).Headers.Item($wdHeaderFooterPrimary).PageNumbers.StartingNumber = 1
    $doc.Sections.Item(3).Headers.Item($wdHeaderFooterPrimary).PageNumbers.NumberStyle = $wdPageNumberStyleArabic
    $null = $doc.Sections.Item(3).Headers.Item($wdHeaderFooterPrimary).PageNumbers.Add(2)

    Write-Log "writing reconstructed body"
    $chapterMap = @{
        "CHAPTER ONE" = "CHAPTER ONE: INTRODUCTION"
        "CHAPTER TWO" = "CHAPTER TWO: LITERATURE REVIEW"
        "CHAPTER THREE" = "CHAPTER THREE: SYSTEM ANALYSIS AND DESIGN"
        "CHAPTER FOUR" = "CHAPTER FOUR: SYSTEM IMPLEMENTATION, EVALUATION, AND DISCUSSION"
    }
    $skipStandalone = @("INTRODUCTION", "LITERATURE REVIEW", "SYSTEM ANALYSIS AND DESIGN", "SYSTEM IMPLEMENTATION, EVALUATION, AND DISCUSSION")
    $objectiveLines = @(
        "To review existing e-voting systems and the cryptographic approaches they use.",
        "To analyse the security requirements and threat model for diaspora e-voting.",
        "To design a zk-STARK-based ballot validity constraint system.",
        "To implement a working prototype integrating zk-STARK proof generation, encrypted ballot submission, and public verification.",
        "To evaluate the prototype’s performance and security properties."
    )

    $elements = $ordered.elements
    for ($i = 0; $i -lt $elements.Count; $i++) {
        $element = $elements[$i]
        if ($element.type -eq "paragraph") {
            $text = Clean-Text([string]$element.text)
            if ([string]::IsNullOrWhiteSpace($text)) { continue }
            if ($skipStandalone -contains $text) { continue }

            if ($chapterMap.ContainsKey($text)) {
                if ($text -ne "CHAPTER ONE") {
                    $selection.InsertBreak($wdPageBreak)
                }
                Add-Heading -Selection $selection -Word $word -Text $chapterMap[$text] -Level 1 -Alignment $wdAlignCenter
                continue
            }

            if ($text -match "^[1-5]\.\d+\.\d+\s") {
                Add-Heading -Selection $selection -Word $word -Text $text -Level 3
                continue
            }
            if ($text -match "^[1-5]\.\d+\s") {
                Add-Heading -Selection $selection -Word $word -Text $text -Level 2
                continue
            }
            if ($objectiveLines -contains $text) {
                Add-Paragraph -Selection $selection -Word $word -Text (Convert-ObjectiveToNumber $text) -LineMultiple 1.5 -LeftIndentCm 0.4 -FirstLineIndentCm 0
                continue
            }
            if ($text -eq "This section reviews two existing verifiable online voting systems that are relevant to this project: Helios and Belenios. These systems were selected because they are well-known examples of cryptographic online voting platforms that use public verification ideas. The purpose of this review is not to claim that the implemented prototype is more complete than these systems. Rather, it is to understand how existing systems approach privacy, public auditability, ballot posting, voter verification, and tallying. The review also helps identify where the present study differs, especially in its focus on a Nigerian diaspora voting scenario, mock NIN accreditation, a controlled binary referendum, and zk-STARK proof-backed ballot acceptance.") {
                $text += " "
            }
            Add-Paragraph -Selection $selection -Word $word -Text $text -LineMultiple 1.5

            switch ($text) {
                "3.2 Requirement Analysis" {
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 3.1 presents the use-case relationships considered during the requirement analysis of the DiasporaVote prototype." -ImagePath (Join-Path $diagramsDir "use_case_diagram.png") -CaptionText "Figure 3.1: Use-case diagram for DiasporaVote actors"
                }
                "3.3 System Architecture" {
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 3.2 presents the overall architecture of the implemented prototype, showing how the frontend, backend, database, and proof engine interact." -ImagePath (Join-Path $diagramsDir "system_architecture.png") -CaptionText "Figure 3.2: DiasporaVote system architecture"
                }
                "3.5 Voting Protocol Design" {
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 3.3 illustrates the controlled referendum workflow from accreditation through receipt publication and tally display." -ImagePath (Join-Path $diagramsDir "voting_workflow.png") -CaptionText "Figure 3.3: Voting workflow for the controlled referendum prototype"
                }
                "3.6 zk-STARK Constraint System Design" {
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 3.4 shows the proof-generation and verification flow linked to accepted ballots in the prototype." -ImagePath (Join-Path $diagramsDir "zk_stark_verification_flow.png") -CaptionText "Figure 3.4: zk-STARK proof verification flow"
                }
                "3.7 Database Design" {
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 3.5 presents the database and entity-relationship design used for voter, ballot, and event storage." -ImagePath (Join-Path $diagramsDir "database_er_diagram.png") -CaptionText "Figure 3.5: Database and entity-relationship design"
                }
                "4.6 Program Modules and Interfaces" {
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 4.1 shows the landing page that introduces the DiasporaVote prototype." -ImagePath (Join-Path $screenshotsDir "figure_4_1_landing_page.png") -CaptionText "Figure 4.1: Landing page of the DiasporaVote prototype"
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 4.2 shows the accreditation page used for mock NIN submission." -ImagePath (Join-Path $screenshotsDir "figure_4_2_accreditation_page.png") -CaptionText "Figure 4.2: Mock NIN accreditation page"
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 4.3 shows the camera-based verification page used to confirm face presence before ballot access." -ImagePath (Join-Path $screenshotsDir "figure_4_3_camera_verification_page.png") -CaptionText "Figure 4.3: Camera-based prototype verification page"
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 4.4 shows the event dashboard used to access the active referendum." -ImagePath (Join-Path $screenshotsDir "figure_4_4_event_dashboard.png") -CaptionText "Figure 4.4: Event dashboard showing the active referendum"
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 4.5 shows the controlled ballot page used for the binary referendum." -ImagePath (Join-Path $screenshotsDir "figure_4_5_ballot_page.png") -CaptionText "Figure 4.5: Active referendum ballot page"
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 4.6 shows the vote-review screen used before ballot submission." -ImagePath (Join-Path $screenshotsDir "figure_4_6_vote_review_page.png") -CaptionText "Figure 4.6: Vote review page"
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 4.7 shows the receipt issued after a successful proof-backed ballot submission." -ImagePath (Join-Path $screenshotsDir "figure_4_7_receipt_page.png") -CaptionText "Figure 4.7: Receipt page showing the Ballot ID and Proof Hash"
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 4.8 shows the public verification board that exposes only safe receipt metadata." -ImagePath (Join-Path $screenshotsDir "figure_4_8_public_verification_board.png") -CaptionText "Figure 4.8: Public verification board"
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 4.9 shows the proof-verification response for a selected ballot receipt." -ImagePath (Join-Path $screenshotsDir "figure_4_9_proof_verification_result.png") -CaptionText "Figure 4.9: Proof verification result"
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 4.10 shows the tally dashboard for the active referendum event." -ImagePath (Join-Path $screenshotsDir "figure_4_10_tally_dashboard.png") -CaptionText "Figure 4.10: Tally dashboard"
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 4.11 shows the protected admin login page used for prototype registry management." -ImagePath (Join-Path $screenshotsDir "figure_4_11_admin_login.png") -CaptionText "Figure 4.11: Admin login page"
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 4.12 shows the admin registry view used to manage mock voters safely." -ImagePath (Join-Path $screenshotsDir "figure_4_12_admin_registry.png") -CaptionText "Figure 4.12: Admin mock voter registry page"
                    Add-EmbeddedFigure -Selection $selection -Word $word -IntroText "Figure 4.13 shows the confirmation state after creating a new mock voter." -ImagePath (Join-Path $screenshotsDir "figure_4_13_admin_create_voter.png") -CaptionText "Figure 4.13: Admin create-voter confirmation page"
                }
            }
        }
        elseif ($element.type -eq "table") {
            Add-TableFromRows -Doc $doc -Selection $selection -Word $word -Rows $element.rows
        }
    }

    Add-ChapterFive -Selection $selection -Word $word
    Add-ReferencesSection -Selection $selection -Word $word

    Write-Log "building front matter lists"
    $figureEntries = New-Object System.Collections.ArrayList
    $tableEntries = New-Object System.Collections.ArrayList
    $tocEntries = New-Object System.Collections.ArrayList
    [void]$tocEntries.Add([pscustomobject]@{ Title = "COVER PAGE"; Page = 1; Prelim = $true })

    foreach ($paragraph in @($doc.Paragraphs)) {
        $text = Clean-Text($paragraph.Range.Text)
        if ([string]::IsNullOrWhiteSpace($text)) { continue }
        $page = $paragraph.Range.Information(3)
        if ($text -in @("CERTIFICATION", "DEDICATION", "ACKNOWLEDGEMENTS", "TABLE OF CONTENT", "LIST OF FIGURES", "LIST OF TABLES", "ABBREVIATIONS", "ABSTRACT")) {
            [void]$tocEntries.Add([pscustomobject]@{ Title = $text; Page = [int]$page; Prelim = $true })
        }
        elseif ($text -match "^CHAPTER (ONE|TWO|THREE|FOUR|FIVE):") {
            [void]$tocEntries.Add([pscustomobject]@{ Title = $text; Page = [int]$page; Prelim = $false })
        }
        elseif ($text -match "^[1-5]\.\d+(\.\d+)?\s") {
            [void]$tocEntries.Add([pscustomobject]@{ Title = $text; Page = [int]$page; Prelim = $false })
        }
        if ($text -match "^Figure\s+\d+\.\d+:") {
            [void]$figureEntries.Add([pscustomobject]@{ Title = $text; Page = [int]$page; Prelim = $false })
        }
        if ($text -match "^Table\s+\d+\.\d+:") {
            [void]$tableEntries.Add([pscustomobject]@{ Title = $text; Page = [int]$page; Prelim = $false })
        }
    }

    Add-ManualListEntries -Doc $doc -Selection $selection -Word $word -Placeholder "[[TOC_BODY]]" -Entries $tocEntries -UseRoman $true
    Add-ManualListEntries -Doc $doc -Selection $selection -Word $word -Placeholder "[[LOF_BODY]]" -Entries $figureEntries -UseRoman $false
    Add-ManualListEntries -Doc $doc -Selection $selection -Word $word -Placeholder "[[LOT_BODY]]" -Entries $tableEntries -UseRoman $false

    Write-Log "saving reconstructed report"
    $doc.SaveAs([ref]$outputPath)
    $doc.Close()
    $word.Quit()
    Write-Log "rebuild complete"
}
finally {
    if ($doc -ne $null) { try { $doc.Close() } catch {} }
    if ($word -ne $null) { try { $word.Quit() } catch {} }
}
