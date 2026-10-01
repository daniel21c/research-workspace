# Word(COM)로 manuscript/*.docx 를 PDF로 출력한다. 경로는 스크립트 위치에서 계산한다(한글 경로 인코딩 문제를 피하려고 ASCII만 사용).
param([string]$PackageRoot = (Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference = 'Stop'
$docx = (Get-ChildItem (Join-Path $PackageRoot 'manuscript') -Filter '*.docx' | Select-Object -First 1).FullName
$pdf = [IO.Path]::ChangeExtension($docx, '.pdf')
$word = $null; $doc = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false; $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($docx, $false, $true)
    $doc.Repaginate()
    $doc.ExportAsFixedFormat($pdf, 17)
    Write-Output "PDF exported: $pdf (Word $($word.Version))"
} finally {
    if ($doc) { [void]$doc.Close(0) }
    if ($word) { [void]$word.Quit() }
}
