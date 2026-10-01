param([Parameter(Mandatory=$true)][string]$Docx,[Parameter(Mandatory=$true)][string]$Pdf)
$ErrorActionPreference='Stop'
$docxPath=[IO.Path]::GetFullPath($Docx)
$pdfPath=[IO.Path]::GetFullPath($Pdf)
if(-not (Test-Path -LiteralPath $docxPath)){throw 'DOCX absent'}
$word=$null;$document=$null
try {
  $word=New-Object -ComObject Word.Application
  $word.Visible=$false;$word.DisplayAlerts=0
  $document=$word.Documents.Open($docxPath,$false,$true)
  $document.ExportAsFixedFormat($pdfPath,17)
  Write-Output ('Exported with Word '+$word.Version+': '+$pdfPath)
} finally {
  if($null -ne $document){$document.Close([ref]0);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($document)}
  if($null -ne $word){$word.Quit([ref]0);[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($word)}
  [GC]::Collect();[GC]::WaitForPendingFinalizers()
}
