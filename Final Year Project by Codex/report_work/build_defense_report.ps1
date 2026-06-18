$ErrorActionPreference = "Stop"

$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$projectDir = Join-Path $root "Final Year Project by Codex"
$draftPath = Join-Path $projectDir "Draft of Final Year Project with Mendeley cite.docx"
$workingPath = Join-Path $projectDir "Defense Ready Final Year Project Report.docx"
$backupPath = Join-Path $projectDir ("Draft of Final Year Project with Mendeley cite - ORIGINAL BACKUP {0}.docx" -f (Get-Date -Format "yyyy-MM-dd-HHmmss"))
$screenshotsDir = Join-Path $projectDir "report_assets\screenshots"
$diagramsDir = Join-Path $projectDir "report_assets\diagrams"
$logPath = Join-Path $projectDir "report_work\runtime\build_defense_report.trace.log"

$wdCollapseStart = 1
$wdCollapseEnd = 0
$wdPageBreak = 7
$wdSectionBreakNextPage = 2
$wdAlignLeft = 0
$wdAlignCenter = 1
$wdFindStop = 0
$wdGoToAbsolute = 1
$wdGoToPage = 1
$wdLineSpaceMultiple = 4

function Clean-ParagraphText {
    param([string]$Text)
    if ($null -eq $Text) { return "" }
    return ($Text -replace "[`r`a]", "").Trim()
}

function Add-Paragraph {
    param(
        [object]$Selection,
        [object]$Word,
        [string]$Text,
        [string]$Style = "Normal",
        [int]$Alignment = 0,
        [double]$LineMultiple = 1.5,
        [double]$SpaceBefore = 0,
        [double]$SpaceAfter = 0,
        [double]$FontSize = 12,
        [bool]$Bold = $false,
        [bool]$Italic = $false,
        [bool]$AllCaps = $false
    )

    $Selection.Style = $Style
    $Selection.ParagraphFormat.Alignment = $Alignment
    $Selection.ParagraphFormat.SpaceBefore = $SpaceBefore
    $Selection.ParagraphFormat.SpaceAfter = $SpaceAfter
    $Selection.ParagraphFormat.LineSpacingRule = $wdLineSpaceMultiple
    $Selection.ParagraphFormat.LineSpacing = $Word.LinesToPoints($LineMultiple)
    $Selection.Font.Name = "Times New Roman"
    $Selection.Font.Size = $FontSize
    $Selection.Font.Bold = [int]$Bold
    $Selection.Font.Italic = [int]$Italic
    $Selection.Font.AllCaps = [int]$AllCaps
    $Selection.TypeText($Text)
    $Selection.TypeParagraph()
}

function Add-BlankParagraph {
    param([object]$Selection, [int]$Count = 1)
    for ($i = 0; $i -lt $Count; $i++) {
        $Selection.TypeParagraph()
    }
}

function Find-Paragraph {
    param([object]$Doc, [string]$Text)
    foreach ($paragraph in @($Doc.Paragraphs)) {
        if ((Clean-ParagraphText $paragraph.Range.Text) -eq $Text) {
            return $paragraph
        }
    }
    return $null
}

function Find-ParagraphContains {
    param([object]$Doc, [string]$Snippet)
    foreach ($paragraph in @($Doc.Paragraphs)) {
        if ((Clean-ParagraphText $paragraph.Range.Text) -like "*$Snippet*") {
            return $paragraph
        }
    }
    return $null
}

function Set-HeadingStyle {
    param(
        [object]$Paragraph,
        [string]$StyleName,
        [int]$Alignment = 0,
        [double]$FontSize = 12
    )

    $Paragraph.Range.Style = $StyleName
    $Paragraph.Range.Font.Name = "Times New Roman"
    $Paragraph.Range.Font.Size = $FontSize
    $Paragraph.Range.Font.Bold = 1
    $Paragraph.Range.Font.AllCaps = 0
    $Paragraph.Alignment = $Alignment
    $Paragraph.SpaceAfter = 6
    $Paragraph.SpaceBefore = 6
    $Paragraph.LineSpacingRule = $wdLineSpaceMultiple
}

function Replace-WholeParagraphText {
    param([object]$Paragraph, [string]$Text)
    $Paragraph.Range.Text = $Text
}

function Insert-FigureAfterParagraph {
    param(
        [object]$Doc,
        [object]$Selection,
        [object]$Word,
        [object]$Paragraph,
        [string]$IntroText,
        [string]$ImagePath,
        [string]$CaptionText,
        [double]$WidthPoints = 430
    )

    $Selection.SetRange($Paragraph.Range.End, $Paragraph.Range.End)
    Add-Paragraph -Selection $Selection -Word $Word -Text $IntroText -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.5 -SpaceAfter 6
    $shape = $Selection.InlineShapes.AddPicture($ImagePath)
    if ($shape.Width -gt $WidthPoints) {
        $shape.LockAspectRatio = -1
        $shape.Width = $WidthPoints
    }
    $Selection.ParagraphFormat.Alignment = $wdAlignCenter
    $Selection.TypeParagraph()
    Add-Paragraph -Selection $Selection -Word $Word -Text $CaptionText -Style "Normal" -Alignment $wdAlignCenter -LineMultiple 1.0 -SpaceAfter 12 -Italic $true
}

function Insert-BenchmarkTable {
    param([object]$Doc, [object]$Selection)

    $table = $Doc.Tables.Add($Selection.Range, 3, 5)
    $table.Borders.Enable = 1
    $table.Range.Font.Name = "Times New Roman"
    $table.Range.Font.Size = 11
    $table.Range.ParagraphFormat.LineSpacingRule = $wdLineSpaceMultiple
    $table.Range.ParagraphFormat.LineSpacing = 18
    $table.Cell(1,1).Range.Text = "Vote Type"
    $table.Cell(1,2).Range.Text = "Runs"
    $table.Cell(1,3).Range.Text = "Generation Time (ms)"
    $table.Cell(1,4).Range.Text = "Verification Time (ms)"
    $table.Cell(1,5).Range.Text = "Proof Size (bytes)"
    $table.Rows.Item(1).Range.Bold = 1

    $table.Cell(2,1).Range.Text = "Yes"
    $table.Cell(2,2).Range.Text = "30"
    $table.Cell(2,3).Range.Text = "Avg 0.8141 | Min 0.4601 | Max 3.9797"
    $table.Cell(2,4).Range.Text = "Avg 0.5196 | Min 0.3506 | Max 1.3268"
    $table.Cell(2,5).Range.Text = "Avg 4523 | Min 4523 | Max 4523"

    $table.Cell(3,1).Range.Text = "No"
    $table.Cell(3,2).Range.Text = "30"
    $table.Cell(3,3).Range.Text = "Avg 0.7186 | Min 0.4566 | Max 2.4700"
    $table.Cell(3,4).Range.Text = "Avg 0.4011 | Min 0.3227 | Max 0.7621"
    $table.Cell(3,5).Range.Text = "Avg 4521 | Min 4521 | Max 4521"

    $Selection.SetRange($table.Range.End, $table.Range.End)
    $Selection.TypeParagraph()
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
        [System.Collections.ArrayList]$Entries,
        [bool]$UseRomanForPrelims = $false
    )

    $finder = $Selection.Find
    $Selection.HomeKey(6) | Out-Null
    $finder.ClearFormatting()
    $finder.Text = $Placeholder
    $finder.Forward = $true
    $finder.Wrap = $wdFindStop
    if (-not $finder.Execute()) {
        return
    }

    $Selection.Range.Text = ""
    foreach ($entry in $Entries) {
        $title = $entry.Title
        $page = $entry.Page
        if ($UseRomanForPrelims -and $entry.Prelim) {
            $pageText = Convert-ToRoman $page
        } else {
            $pageText = [string]$page
        }
        $line = ("{0}`t{1}" -f $title, $pageText)
        Add-Paragraph -Selection $Selection -Word $Word -Text $line -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.15 -SpaceAfter 0 -FontSize 11
        $Selection.Paragraphs.Last.TabStops.ClearAll()
        [void]$Selection.Paragraphs.Last.TabStops.Add(430, 2, 1)
    }
}

Copy-Item $draftPath $backupPath -Force
Set-Content -Path $logPath -Value "backup created: $backupPath"
Write-Host "backup created"

$word = $null
$draftDoc = $null
$doc = $null

try {
    Add-Content -Path $logPath -Value "opening Word COM"
    Write-Host "opening Word COM"
    try {
        $word = [Runtime.InteropServices.Marshal]::GetActiveObject("Word.Application")
        Add-Content -Path $logPath -Value "attached to active Word instance"
        Write-Host "attached to active Word instance"
    } catch {
        $word = New-Object -ComObject Word.Application
        Add-Content -Path $logPath -Value "created new Word instance"
        Write-Host "created new Word instance"
    }
    $word.Visible = $false
    $word.DisplayAlerts = 0

    Add-Content -Path $logPath -Value "opening draft"
    Write-Host "opening draft"
    $draftDoc = $word.Documents.Open($draftPath, $false, $true)
    Add-Content -Path $logPath -Value "creating new document"
    Write-Host "creating new document"
    $doc = $word.Documents.Add()
    $selection = $word.Selection

    $doc.PageSetup.TopMargin = $word.CentimetersToPoints(2.54)
    $doc.PageSetup.BottomMargin = $word.CentimetersToPoints(2.54)
    $doc.PageSetup.RightMargin = $word.CentimetersToPoints(2.54)
    $doc.PageSetup.LeftMargin = $word.CentimetersToPoints(3.0)

    Add-Content -Path $logPath -Value "writing front matter"
    Write-Host "writing front matter"
    Add-Paragraph -Selection $selection -Word $word -Text "COVER PAGE" -Style "Heading 1" -Alignment $wdAlignCenter -LineMultiple 1.0 -SpaceAfter 0 -FontSize 1
    $selection.Font.Color = 16777215
    $selection.Paragraphs.Last.Range.Font.Color = 16777215
    Add-BlankParagraph -Selection $selection -Count 2
    Add-Paragraph -Selection $selection -Word $word -Text "DESIGN AND IMPLEMENTATION OF A SECURE DIASPORA E-VOTING PROTOTYPE USING zk-STARK PROTOCOLS" -Style "Title" -Alignment $wdAlignCenter -LineMultiple 1.15 -SpaceAfter 18 -FontSize 16 -Bold $true
    Add-BlankParagraph -Selection $selection -Count 2
    Add-Paragraph -Selection $selection -Word $word -Text "BY" -Style "Normal" -Alignment $wdAlignCenter -LineMultiple 1.15 -FontSize 12 -Bold $true
    Add-BlankParagraph -Selection $selection -Count 1
    Add-Paragraph -Selection $selection -Word $word -Text "ADELUKA OLUWAMBEPELUMI EMMANUEL" -Style "Normal" -Alignment $wdAlignCenter -LineMultiple 1.15 -FontSize 14 -Bold $true
    Add-BlankParagraph -Selection $selection -Count 2
    Add-Paragraph -Selection $selection -Word $word -Text "A PROJECT SUBMITTED TO THE DEPARTMENT OF COMPUTER AND INFORMATION SCIENCES, COLLEGE OF SCIENCE AND TECHNOLOGY, COVENANT UNIVERSITY, OTA, OGUN STATE." -Style "Normal" -Alignment $wdAlignCenter -LineMultiple 1.15 -FontSize 12
    Add-BlankParagraph -Selection $selection -Count 1
    Add-Paragraph -Selection $selection -Word $word -Text "IN PARTIAL FULFILMENT OF THE REQUIREMENTS FOR THE AWARD OF THE BACHELOR OF SCIENCE (HONOURS) DEGREE IN COMPUTER SCIENCE." -Style "Normal" -Alignment $wdAlignCenter -LineMultiple 1.15 -FontSize 12
    Add-BlankParagraph -Selection $selection -Count 3
    Add-Paragraph -Selection $selection -Word $word -Text "JUNE, 2026" -Style "Normal" -Alignment $wdAlignCenter -LineMultiple 1.15 -FontSize 12 -Bold $true
    $selection.InsertBreak($wdPageBreak)

    Add-Paragraph -Selection $selection -Word $word -Text "CERTIFICATION" -Style "Heading 1" -Alignment $wdAlignCenter -LineMultiple 1.15 -SpaceAfter 18 -FontSize 14 -Bold $true
    Add-Paragraph -Selection $selection -Word $word -Text "I hereby certify that this project was carried out by Adeluka Oluwambepelumi Emmanuel in the Department of Computer and Information Sciences, College of Science and Technology, Covenant University, Ota, Ogun State, Nigeria, under appropriate academic supervision." -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.5 -SpaceAfter 18
    Add-BlankParagraph -Selection $selection -Count 3
    Add-Paragraph -Selection $selection -Word $word -Text "______________________________`t`t______________________________" -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.15
    Add-Paragraph -Selection $selection -Word $word -Text "Supervisor`t`t`t`tSignature and Date" -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.15
    Add-BlankParagraph -Selection $selection -Count 2
    Add-Paragraph -Selection $selection -Word $word -Text "______________________________`t`t______________________________" -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.15
    Add-Paragraph -Selection $selection -Word $word -Text "Head of Department`t`t`tSignature and Date" -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.15
    $selection.InsertBreak($wdPageBreak)

    Add-Paragraph -Selection $selection -Word $word -Text "DEDICATION" -Style "Heading 1" -Alignment $wdAlignCenter -LineMultiple 1.15 -SpaceAfter 18 -FontSize 14 -Bold $true
    Add-Paragraph -Selection $selection -Word $word -Text "This work is dedicated to God and to everyone whose support, discipline, and encouragement made the successful completion of this project possible." -Style "Normal" -Alignment $wdAlignCenter -LineMultiple 1.15
    $selection.InsertBreak($wdPageBreak)

    Add-Paragraph -Selection $selection -Word $word -Text "ACKNOWLEDGEMENTS" -Style "Heading 1" -Alignment $wdAlignCenter -LineMultiple 1.15 -SpaceAfter 18 -FontSize 14 -Bold $true
    Add-Paragraph -Selection $selection -Word $word -Text "My sincere gratitude goes to God for His grace, strength, and guidance throughout the course of this project. I am also grateful to my family and loved ones for their patience, encouragement, and support during the research, implementation, and documentation stages of this work." -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.5
    Add-Paragraph -Selection $selection -Word $word -Text "I further appreciate the academic guidance, technical feedback, and institutional support received from the Department of Computer and Information Sciences, Covenant University. The comments and reviews provided during the development of the DiasporaVote prototype contributed significantly to the clarity, scope control, and final presentation of this study." -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.5
    $selection.InsertBreak($wdPageBreak)

    Add-Paragraph -Selection $selection -Word $word -Text "TABLE OF CONTENTS" -Style "Heading 1" -Alignment $wdAlignCenter -LineMultiple 1.15 -SpaceAfter 12 -FontSize 14 -Bold $true
    Add-Paragraph -Selection $selection -Word $word -Text "[[TOC_BODY]]" -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.15 -FontSize 11
    $selection.InsertBreak($wdPageBreak)

    Add-Paragraph -Selection $selection -Word $word -Text "LIST OF FIGURES" -Style "Heading 1" -Alignment $wdAlignCenter -LineMultiple 1.15 -SpaceAfter 12 -FontSize 14 -Bold $true
    Add-Paragraph -Selection $selection -Word $word -Text "[[LOF_BODY]]" -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.15 -FontSize 11
    $selection.InsertBreak($wdPageBreak)

    Add-Paragraph -Selection $selection -Word $word -Text "LIST OF TABLES" -Style "Heading 1" -Alignment $wdAlignCenter -LineMultiple 1.15 -SpaceAfter 12 -FontSize 14 -Bold $true
    Add-Paragraph -Selection $selection -Word $word -Text "[[LOT_BODY]]" -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.15 -FontSize 11
    $selection.InsertBreak($wdPageBreak)

    Add-Paragraph -Selection $selection -Word $word -Text "ABBREVIATIONS" -Style "Heading 1" -Alignment $wdAlignCenter -LineMultiple 1.15 -SpaceAfter 12 -FontSize 14 -Bold $true
    $abbreviations = @(
        "API`tApplication Programming Interface",
        "BVAS`tBimodal Voter Accreditation System",
        "CIS`tComputer and Information Sciences",
        "INEC`tIndependent National Electoral Commission",
        "NIMC`tNational Identity Management Commission",
        "NIN`tNational Identification Number",
        "RAM`tRandom Access Memory",
        "SQLite`tStructured Query Language Lite",
        "STARK`tScalable Transparent Argument of Knowledge",
        "UI`tUser Interface",
        "URL`tUniform Resource Locator",
        "ZKP`tZero-Knowledge Proof"
    )
    foreach ($item in $abbreviations) {
        Add-Paragraph -Selection $selection -Word $word -Text $item -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.15 -FontSize 11 -SpaceAfter 0
        $selection.Paragraphs.Last.TabStops.ClearAll()
        [void]$selection.Paragraphs.Last.TabStops.Add(130, 0, 0)
    }
    $selection.InsertBreak($wdPageBreak)

    Add-Paragraph -Selection $selection -Word $word -Text "ABSTRACT" -Style "Heading 1" -Alignment $wdAlignCenter -LineMultiple 1.0 -SpaceAfter 12 -FontSize 14 -Bold $true
    Add-Paragraph -Selection $selection -Word $word -Text "This study addressed the challenge of how secure diaspora voting could be demonstrated in a controlled Nigerian context without overclaiming institutional integration or national-election readiness. The project designed and implemented DiasporaVote, a secure binary referendum prototype that combined a React frontend, a Flask backend, SQLite persistence, a mock National Identification Number registry, and a Winterfell-based zk-STARK proof engine. The implemented workflow covered mock voter accreditation, camera-based prototype verification, event-aware ballot access, controlled Yes/No vote submission, proof generation and verification, encrypted ballot storage, receipt issuance, public-board publication of privacy-preserving verification metadata, and tally display for the active referendum event. System evaluation was evidence-based and included registered-voter login, rejection of unregistered users, verification-state enforcement, valid and invalid ballot handling, duplicate-vote rejection, proof-engine health checking, proof verification, tally behaviour, admin registry operations, deployment smoke testing, and persistence checks. Direct proof-engine benchmarks were executed against synthetic Yes and No ballots with three warm-up runs excluded and thirty measured runs retained for each case. The results showed average proof-generation times below one millisecond, average proof-verification times below one millisecond, and proof sizes of approximately 4.5 KB, indicating that the controlled binary referendum workflow was feasible within the scope of the prototype. The main contribution of the study was the implementation of a technically defensible diaspora voting prototype that demonstrated proof-backed ballot acceptance and server-mediated public verification while clearly stating its limitations, including mock identity assurance, binary-ballot scope, and non-production deployment status." -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.0 -SpaceAfter 12
    Add-Paragraph -Selection $selection -Word $word -Text "Keywords: diaspora voting, e-voting, zk-STARK, zero-knowledge proof, public verification, referendum prototype" -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.0 -Italic $true

    $selection.InsertBreak($wdSectionBreakNextPage)

    Add-Content -Path $logPath -Value "copying draft body"
    Write-Host "copying draft body"
    $chapterStart = Find-Paragraph -Doc $draftDoc -Text "CHAPTER ONE"
    if ($null -eq $chapterStart) {
        throw "Could not locate CHAPTER ONE in the draft report."
    }

    $draftRange = $draftDoc.Range($chapterStart.Range.Start, $draftDoc.Content.End)
    $selection.EndKey(6) | Out-Null
    $selection.Range.FormattedText = $draftRange.FormattedText
    $selection.EndKey(6) | Out-Null

    Add-Content -Path $logPath -Value "writing chapter five"
    Write-Host "writing chapter five"
    Add-Paragraph -Selection $selection -Word $word -Text "CHAPTER FIVE: SUMMARY, RECOMMENDATIONS, LIMITATIONS, AND CONCLUSION" -Style "Heading 1" -Alignment $wdAlignCenter -LineMultiple 1.15 -FontSize 14 -Bold $true -SpaceAfter 12
    Add-Paragraph -Selection $selection -Word $word -Text "5.1 Summary" -Style "Heading 2" -Alignment $wdAlignLeft -LineMultiple 1.5 -Bold $true
    Add-Paragraph -Selection $selection -Word $word -Text "This study implemented a secure diaspora e-voting prototype for a controlled binary referendum using zk-STARK protocols. The completed system brought together mock voter accreditation, camera-based prototype verification, event-aware ballot handling, proof-backed vote acceptance, encrypted storage, public receipt publication, server-mediated proof verification, and tally display within a single workflow designed for academic demonstration." -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.5
    Add-Paragraph -Selection $selection -Word $word -Text "The project also demonstrated that the trust problem in remote voting is broader than interface design alone. The implemented prototype showed how registry checks, duplicate-vote control, proof generation, proof hashing, privacy-preserving public verification metadata, and aggregate tally logic can work together as layers in a defensible technical design. By narrowing the scope to a referendum rather than a multi-candidate national election, the study kept the cryptographic design testable and the implementation claims academically honest." -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.5

    Add-Paragraph -Selection $selection -Word $word -Text "5.2 Recommendations" -Style "Heading 2" -Alignment $wdAlignLeft -LineMultiple 1.5 -Bold $true
    Add-Paragraph -Selection $selection -Word $word -Text "The following recommendations arise from the implementation and evaluation outcomes of the study:" -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.5
    $recommendations = @(
        "1. Independent client-side or auditor-side proof verification should be added so that verification does not depend entirely on the election server.",
        "2. Stronger identity assurance should be explored only under proper institutional, legal, and privacy approval.",
        "3. The proof workflow and surrounding backend logic should undergo a formal cryptographic and security audit.",
        "4. Larger-scale performance testing should be carried out with higher ballot volumes and concurrent users.",
        "5. Additional research should address coercion resistance, usability evaluation, and broader public-audit models.",
        "6. Deployment hardening should be improved before any real-world pilot use is considered."
    )
    foreach ($item in $recommendations) {
        Add-Paragraph -Selection $selection -Word $word -Text $item -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.5 -SpaceAfter 0
    }

    Add-Paragraph -Selection $selection -Word $word -Text "5.3 Limitations of the Study" -Style "Heading 2" -Alignment $wdAlignLeft -LineMultiple 1.5 -Bold $true
    Add-Paragraph -Selection $selection -Word $word -Text "The implemented prototype was intentionally limited so that its claims remained technically accurate and defensible. The main limitations are stated clearly as follows:" -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.5
    $limitations = @(
        "1. The identity layer used a mock NIN registry and did not connect to live NIMC infrastructure.",
        "2. The system did not integrate with live INEC infrastructure or any official national election backend.",
        "3. The camera-based verification step was a prototype presence check and not certified biometric identity matching.",
        "4. Public verification was server-mediated and did not yet provide fully independent local verification.",
        "5. The ballot model was restricted to a controlled binary referendum.",
        "6. The system did not implement national collation, multi-level aggregation, or polling-unit-to-state result flow.",
        "7. The backend still participated in tallying and proof access, which means the architecture was not trust-minimised to production standards.",
        "8. The prototype was not production-ready for national elections."
    )
    foreach ($item in $limitations) {
        Add-Paragraph -Selection $selection -Word $word -Text $item -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.5 -SpaceAfter 0
    }

    Add-Paragraph -Selection $selection -Word $word -Text "5.4 Conclusion" -Style "Heading 2" -Alignment $wdAlignLeft -LineMultiple 1.5 -Bold $true
    Add-Paragraph -Selection $selection -Word $word -Text "The study achieved its main aim of designing and implementing a secure diaspora e-voting prototype using zk-STARK protocols. Within the limits of a final year technical project, the implemented system demonstrated that proof-backed ballot acceptance, controlled accreditation, privacy-preserving public verification metadata, and event-aware tallying can be combined into a coherent remote-voting workflow. The strongest conclusion of the work is therefore not that national diaspora voting has been solved, but that a careful, scope-controlled prototype can make the security and verification problem more concrete, measurable, and academically defensible for future research and development." -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.5

    Add-Content -Path $logPath -Value "writing references"
    Write-Host "writing references"
    Add-Paragraph -Selection $selection -Word $word -Text "REFERENCES" -Style "Heading 1" -Alignment $wdAlignCenter -LineMultiple 1.15 -FontSize 14 -Bold $true -SpaceAfter 12
    $references = @(
        "Ali, S. T., & Murray, J. (2016). An overview of end-to-end verifiable voting systems. arXiv. https://arxiv.org/abs/1605.08554",
        "Alsadi, M., Casey, M., Dragan, C. C., Dupressoir, F., Riley, L., Sallal, M., Schneider, S., Treharne, H., Wadsworth, J., & Wright, P. (2019). Towards end-to-end verifiable online voting: Adding verifiability to established voting systems. arXiv. https://arxiv.org/abs/1912.00288",
        "Ben-Sasson, E., Bentov, I., Horesh, Y., & Riabzev, M. (2018). Scalable, transparent, and post-quantum secure computational integrity. IACR ePrint Archive, 2018/046. https://eprint.iacr.org/2018/046",
        "Federal Republic of Nigeria. (2022). Electoral Act, 2022. Government of the Federal Republic of Nigeria.",
        "Goldwasser, S., Micali, S., & Rackoff, C. (1989). The knowledge complexity of interactive proof systems. SIAM Journal on Computing, 18(1), 186-208.",
        "International IDEA. (2007). Voting from abroad: The International IDEA handbook. International Institute for Democracy and Electoral Assistance.",
        "Quaglia, E. A., & Smyth, B. (2017). A short introduction to secrecy and verifiability for elections. arXiv. https://arxiv.org/abs/1702.03168"
    )
    foreach ($item in $references) {
        Add-Paragraph -Selection $selection -Word $word -Text $item -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.0 -SpaceAfter 6
        $selection.Paragraphs.Last.LeftIndent = $word.CentimetersToPoints(0.63)
        $selection.Paragraphs.Last.FirstLineIndent = -$word.CentimetersToPoints(0.63)
    }

    foreach ($paragraph in @($doc.Paragraphs)) {
        $text = Clean-ParagraphText $paragraph.Range.Text
        if ($text -match "^CHAPTER ONE$") {
            Replace-WholeParagraphText -Paragraph $paragraph -Text "CHAPTER ONE: INTRODUCTION"
            Set-HeadingStyle -Paragraph $paragraph -StyleName "Heading 1" -Alignment $wdAlignCenter -FontSize 14
        } elseif ($text -match "^CHAPTER TWO$") {
            Replace-WholeParagraphText -Paragraph $paragraph -Text "CHAPTER TWO: LITERATURE REVIEW"
            Set-HeadingStyle -Paragraph $paragraph -StyleName "Heading 1" -Alignment $wdAlignCenter -FontSize 14
        } elseif ($text -match "^CHAPTER THREE$") {
            Replace-WholeParagraphText -Paragraph $paragraph -Text "CHAPTER THREE: SYSTEM ANALYSIS AND DESIGN"
            Set-HeadingStyle -Paragraph $paragraph -StyleName "Heading 1" -Alignment $wdAlignCenter -FontSize 14
        } elseif ($text -match "^CHAPTER FOUR$") {
            Replace-WholeParagraphText -Paragraph $paragraph -Text "CHAPTER FOUR: IMPLEMENTATION, EVALUATION, AND INTERFACES"
            Set-HeadingStyle -Paragraph $paragraph -StyleName "Heading 1" -Alignment $wdAlignCenter -FontSize 14
        } elseif ($text -match "^CHAPTER FIVE:") {
            Set-HeadingStyle -Paragraph $paragraph -StyleName "Heading 1" -Alignment $wdAlignCenter -FontSize 14
        } elseif ($text -match "^[1-5]\.\d+\.\d+\s") {
            Set-HeadingStyle -Paragraph $paragraph -StyleName "Heading 3" -Alignment $wdAlignLeft -FontSize 12
        } elseif ($text -match "^[1-5]\.\d+\s") {
            Set-HeadingStyle -Paragraph $paragraph -StyleName "Heading 2" -Alignment $wdAlignLeft -FontSize 12
        } elseif ($text -in @("CERTIFICATION", "DEDICATION", "ACKNOWLEDGEMENTS", "TABLE OF CONTENTS", "LIST OF FIGURES", "LIST OF TABLES", "ABBREVIATIONS", "ABSTRACT", "REFERENCES")) {
            Set-HeadingStyle -Paragraph $paragraph -StyleName "Heading 1" -Alignment $wdAlignCenter -FontSize 14
        } elseif ($text -match "^Table\s+\d+\.\d+:") {
            $paragraph.Range.Font.Bold = 1
            $paragraph.Range.ParagraphFormat.Alignment = $wdAlignLeft
            $paragraph.Range.ParagraphFormat.SpaceAfter = 6
            $paragraph.Range.ParagraphFormat.LineSpacingRule = $wdLineSpaceMultiple
            $paragraph.Range.ParagraphFormat.LineSpacing = $word.LinesToPoints(1.0)
        }
    }

    $titlesToDelete = @("INTRODUCTION", "LITERATURE REVIEW", "SYSTEM ANALYSIS AND DESIGN", "IMPLEMENTATION, TESTING AND DISCUSSION")
    foreach ($paragraph in @($doc.Paragraphs)) {
        $text = Clean-ParagraphText $paragraph.Range.Text
        if ($titlesToDelete -contains $text) {
            $paragraph.Range.Delete()
        }
    }

    $doc.Content.Find.Execute("Table 4.5: Comparative Benchmark Against Existing Systems", $false, $false, $false, $false, $false, $true, 1, $false, "Table 4.6: Comparative Benchmark Against Existing Systems", 2) | Out-Null
    $doc.Content.Find.Execute("Table 4.6: Program Interfaces", $false, $false, $false, $false, $false, $true, 1, $false, "Table 4.7: Program Interfaces", 2) | Out-Null
    $doc.Content.Find.Execute("Table 4.5 presents the comparative benchmark.", $false, $false, $false, $false, $false, $true, 1, $false, "Table 4.6 presents the comparative benchmark.", 2) | Out-Null
    $doc.Content.Find.Execute("The major user-facing interfaces of the system are summarised in Table 4.6.", $false, $false, $false, $false, $false, $true, 1, $false, "The major user-facing interfaces of the system are summarised in Table 4.7.", 2) | Out-Null
    $doc.Content.Find.Execute("blockchain-centred", $false, $false, $false, $false, $false, $true, 1, $false, "blockchain-focused", 2) | Out-Null
    $doc.Content.Find.Execute("real facial recognition", $false, $false, $false, $false, $false, $true, 1, $false, "certified facial recognition", 2) | Out-Null
    $doc.Content.Find.Execute("complete anonymity", $false, $false, $false, $false, $false, $true, 1, $false, "full voter anonymity", 2) | Out-Null
    $doc.Content.Find.Execute("independently verifying the proof locally", $false, $false, $false, $false, $false, $true, 1, $false, "verifying the proof through an independent local verifier", 2) | Out-Null
    $doc.Content.Find.Execute("stronger independent verification tooling", $false, $false, $false, $false, $false, $true, 1, $false, "stronger independent local verification tooling", 2) | Out-Null

    $benchHeading = Find-Paragraph -Doc $doc -Text "4.5.3 Benchmarking Against Existing Systems"
    if ($benchHeading -ne $null) {
        $selection.SetRange($benchHeading.Range.Start, $benchHeading.Range.Start)
        Add-Paragraph -Selection $selection -Word $word -Text "Benchmark evidence was generated directly from the Winterfell proof engine so that frontend rendering delay, user interaction delay, and network latency did not distort the measurement results. Three warm-up runs were discarded, thirty measured runs were retained for each synthetic ballot case, and the timing source was the engine’s internal high-resolution timer. The run used Cargo 1.96.0 and did not access the SQLite database while collecting the reported benchmark statistics." -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.5
        Add-Paragraph -Selection $selection -Word $word -Text "Table 4.5: Benchmark Results for Binary Referendum Proofs" -Style "Normal" -Alignment $wdAlignLeft -LineMultiple 1.0 -Bold $true
        Insert-BenchmarkTable -Doc $doc -Selection $selection
    }

    $benchPlaceholder = Find-ParagraphContains -Doc $doc -Snippet "Final average proof generation time and proof verification time should be inserted"
    if ($benchPlaceholder -ne $null) {
        Replace-WholeParagraphText -Paragraph $benchPlaceholder -Text "Measured benchmark results confirmed that valid binary referendum proofs remained lightweight and fast within the prototype scope. The Yes-ballot case produced an average proof size of 4,523 bytes, while the No-ballot case produced an average proof size of 4,521 bytes. Average proof-generation time was 0.8141 ms for the Yes case and 0.7186 ms for the No case, while average proof-verification time was 0.5196 ms and 0.4011 ms respectively. These results support the feasibility of proof-backed ballot acceptance in a controlled technical prototype."
    }

    $systemArchitecture = Find-Paragraph -Doc $doc -Text "3.3 System Architecture"
    if ($systemArchitecture -ne $null) {
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $systemArchitecture -IntroText "Figure 3.1 presents the system architecture used in the implemented prototype and shows how the React frontend, Flask backend, proof adapter, SQLite storage, and Winterfell proof engine interact." -ImagePath (Join-Path $diagramsDir "system_architecture.png") -CaptionText "Figure 3.1: DiasporaVote system architecture" -WidthPoints 430
    }

    $votingProtocol = Find-Paragraph -Doc $doc -Text "3.5 Voting Protocol Design"
    if ($votingProtocol -ne $null) {
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $votingProtocol -IntroText "Figure 3.2 illustrates the end-to-end workflow followed by a mock voter from accreditation through receipt issuance and tally visibility." -ImagePath (Join-Path $diagramsDir "voting_workflow.png") -CaptionText "Figure 3.2: Voting workflow for the controlled referendum prototype" -WidthPoints 430
    }

    $requirementsHeading = Find-Paragraph -Doc $doc -Text "3.2 Requirement Analysis"
    if ($requirementsHeading -ne $null) {
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $requirementsHeading -IntroText "Figure 3.3 summarises the principal actors and interactions considered during the use-case analysis of the prototype." -ImagePath (Join-Path $diagramsDir "use_case_diagram.png") -CaptionText "Figure 3.3: Use-case diagram for DiasporaVote actors" -WidthPoints 430
    }

    $databaseHeading = Find-Paragraph -Doc $doc -Text "3.7 Database Design"
    if ($databaseHeading -ne $null) {
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $databaseHeading -IntroText "Figure 3.4 shows the logical entity relationships used to store mock voter records, ballot metadata, and proof-linked artifacts." -ImagePath (Join-Path $diagramsDir "database_er_diagram.png") -CaptionText "Figure 3.4: Database and entity-relationship design" -WidthPoints 430
    }

    $constraintHeading = Find-Paragraph -Doc $doc -Text "3.6 zk-STARK Constraint System Design"
    if ($constraintHeading -ne $null) {
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $constraintHeading -IntroText "Figure 3.5 depicts the proof-generation and verification flow that links accepted ballots to their proof hashes and verification responses." -ImagePath (Join-Path $diagramsDir "zk_stark_verification_flow.png") -CaptionText "Figure 3.5: zk-STARK proof verification flow" -WidthPoints 430
    }

    $interfaceHeading = Find-Paragraph -Doc $doc -Text "4.6 Program Modules and Interfaces"
    if ($interfaceHeading -ne $null) {
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $interfaceHeading -IntroText "Figure 4.1 shows the DiasporaVote landing page used to introduce the secure binary referendum prototype." -ImagePath (Join-Path $screenshotsDir "figure_4_1_landing_page.png") -CaptionText "Figure 4.1: Landing page of the DiasporaVote prototype" -WidthPoints 410
        $landingCaption = Find-ParagraphContains -Doc $doc -Snippet "Figure 4.1: Landing page of the DiasporaVote prototype"
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $landingCaption -IntroText "Figure 4.2 presents the mock NIN accreditation interface through which the voter submits an eligible demonstration identity." -ImagePath (Join-Path $screenshotsDir "figure_4_2_accreditation_page.png") -CaptionText "Figure 4.2: Mock NIN accreditation page" -WidthPoints 410
        $cap2 = Find-ParagraphContains -Doc $doc -Snippet "Figure 4.2: Mock NIN accreditation page"
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $cap2 -IntroText "Figure 4.3 presents the camera-based prototype verification screen used to confirm face presence before ballot access." -ImagePath (Join-Path $screenshotsDir "figure_4_3_camera_verification_page.png") -CaptionText "Figure 4.3: Camera-based prototype verification page" -WidthPoints 410
        $cap3 = Find-ParagraphContains -Doc $doc -Snippet "Figure 4.3: Camera-based prototype verification page"
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $cap3 -IntroText "Figure 4.4 shows the event dashboard through which the voter accesses the active diaspora referendum." -ImagePath (Join-Path $screenshotsDir "figure_4_4_event_dashboard.png") -CaptionText "Figure 4.4: Event dashboard showing the active referendum" -WidthPoints 410
        $cap4 = Find-ParagraphContains -Doc $doc -Snippet "Figure 4.4: Event dashboard showing the active referendum"
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $cap4 -IntroText "Figure 4.5 shows the ballot interface for the controlled Yes/No referendum question." -ImagePath (Join-Path $screenshotsDir "figure_4_5_ballot_page.png") -CaptionText "Figure 4.5: Active referendum ballot page" -WidthPoints 410
        $cap5 = Find-ParagraphContains -Doc $doc -Snippet "Figure 4.5: Active referendum ballot page"
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $cap5 -IntroText "Figure 4.6 presents the vote-review stage used to confirm the selected option before final submission." -ImagePath (Join-Path $screenshotsDir "figure_4_6_vote_review_page.png") -CaptionText "Figure 4.6: Vote review page" -WidthPoints 410
        $cap6 = Find-ParagraphContains -Doc $doc -Snippet "Figure 4.6: Vote review page"
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $cap6 -IntroText "Figure 4.7 presents the receipt issued after a successful proof-backed ballot submission, including the Ballot ID and Proof Hash." -ImagePath (Join-Path $screenshotsDir "figure_4_7_receipt_page.png") -CaptionText "Figure 4.7: Receipt page showing the Ballot ID and Proof Hash" -WidthPoints 410
        $cap7 = Find-ParagraphContains -Doc $doc -Snippet "Figure 4.7: Receipt page showing the Ballot ID and Proof Hash"
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $cap7 -IntroText "Figure 4.8 shows the public verification board that publishes privacy-preserving receipt metadata for accepted ballots." -ImagePath (Join-Path $screenshotsDir "figure_4_8_public_verification_board.png") -CaptionText "Figure 4.8: Public verification board" -WidthPoints 410
        $cap8 = Find-ParagraphContains -Doc $doc -Snippet "Figure 4.8: Public verification board"
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $cap8 -IntroText "Figure 4.9 shows the proof-verification result returned when a published ballot receipt is re-checked through the server-mediated verifier." -ImagePath (Join-Path $screenshotsDir "figure_4_9_proof_verification_result.png") -CaptionText "Figure 4.9: Proof verification result" -WidthPoints 410
        $cap9 = Find-ParagraphContains -Doc $doc -Snippet "Figure 4.9: Proof verification result"
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $cap9 -IntroText "Figure 4.10 presents the tally dashboard used to display aggregate Yes and No counts for the active referendum event." -ImagePath (Join-Path $screenshotsDir "figure_4_10_tally_dashboard.png") -CaptionText "Figure 4.10: Tally dashboard" -WidthPoints 410
        $cap10 = Find-ParagraphContains -Doc $doc -Snippet "Figure 4.10: Tally dashboard"
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $cap10 -IntroText "Figure 4.11 presents the protected admin entry page used for prototype registry management." -ImagePath (Join-Path $screenshotsDir "figure_4_11_admin_login.png") -CaptionText "Figure 4.11: Admin login page" -WidthPoints 410
        $cap11 = Find-ParagraphContains -Doc $doc -Snippet "Figure 4.11: Admin login page"
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $cap11 -IntroText "Figure 4.12 shows the admin registry interface, which exposes masked identity data for controlled voter management." -ImagePath (Join-Path $screenshotsDir "figure_4_12_admin_registry.png") -CaptionText "Figure 4.12: Admin mock voter registry page" -WidthPoints 410
        $cap12 = Find-ParagraphContains -Doc $doc -Snippet "Figure 4.12: Admin mock voter registry page"
        Insert-FigureAfterParagraph -Doc $doc -Selection $selection -Word $word -Paragraph $cap12 -IntroText "Figure 4.13 shows the confirmation state after a new mock voter has been created through the admin console." -ImagePath (Join-Path $screenshotsDir "figure_4_13_admin_create_voter.png") -CaptionText "Figure 4.13: Admin create-voter confirmation page" -WidthPoints 410
    }

    $figureEntries = [System.Collections.ArrayList]::new()
    $tableEntries = [System.Collections.ArrayList]::new()
    $tocEntries = [System.Collections.ArrayList]::new()

    [void]$tocEntries.Add([pscustomobject]@{ Title = "Cover Page"; Page = 1; Prelim = $true })

    foreach ($paragraph in @($doc.Paragraphs)) {
        $text = Clean-ParagraphText $paragraph.Range.Text
        if ([string]::IsNullOrWhiteSpace($text)) { continue }
        $page = $paragraph.Range.Information(3)
        if ($text -in @("CERTIFICATION", "DEDICATION", "ACKNOWLEDGEMENTS", "TABLE OF CONTENTS", "LIST OF FIGURES", "LIST OF TABLES", "ABBREVIATIONS", "ABSTRACT")) {
            [void]$tocEntries.Add([pscustomobject]@{ Title = $text; Page = $page; Prelim = $true })
        } elseif ($text -match "^CHAPTER (ONE|TWO|THREE|FOUR|FIVE):") {
            [void]$tocEntries.Add([pscustomobject]@{ Title = $text; Page = $page; Prelim = $false })
        } elseif ($text -match "^[1-5]\.\d+(\.\d+)?\s") {
            [void]$tocEntries.Add([pscustomobject]@{ Title = $text; Page = $page; Prelim = $false })
        }

        if ($text -match "^Figure\s+\d+\.\d+:") {
            [void]$figureEntries.Add([pscustomobject]@{ Title = $text; Page = $page; Prelim = $false })
        }
        if ($text -match "^Table\s+\d+\.\d+:") {
            [void]$tableEntries.Add([pscustomobject]@{ Title = $text; Page = $page; Prelim = $false })
        }
    }

    Add-ManualListEntries -Doc $doc -Selection $selection -Word $word -Placeholder "[[TOC_BODY]]" -Entries $tocEntries -UseRomanForPrelims $true
    Add-ManualListEntries -Doc $doc -Selection $selection -Word $word -Placeholder "[[LOF_BODY]]" -Entries $figureEntries
    Add-ManualListEntries -Doc $doc -Selection $selection -Word $word -Placeholder "[[LOT_BODY]]" -Entries $tableEntries

    Add-Content -Path $logPath -Value "saving document"
    Write-Host "saving document"
    $doc.SaveAs([ref]$workingPath)
    Add-Content -Path $logPath -Value "saved document"
    Write-Host "saved document"
    $doc.Close()
    $draftDoc.Close()
    $word.Quit()
} finally {
    if ($doc -ne $null) { try { $doc.Close() } catch {} }
    if ($draftDoc -ne $null) { try { $draftDoc.Close() } catch {} }
    if ($word -ne $null) { try { $word.Quit() } catch {} }
}
