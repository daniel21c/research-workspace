$ErrorActionPreference = 'Stop'
$taskScratch = 'C:\Users\cyion\.codex\tmp\access-v33-20260929-01a0ea59'
$exactTarget = 'C:\Users\cyion\.codex\tmp\access-v33-20260929-01a0ea59\접근성분석_패키지'
$inventoryPath = Join-Path $taskScratch 'private_stage_inventory.json'
$ledger = Get-Content -LiteralPath $inventoryPath -Raw -Encoding utf8 | ConvertFrom-Json
$resolvedScratch = (Resolve-Path -LiteralPath $taskScratch).ProviderPath
$resolvedTarget = (Resolve-Path -LiteralPath $exactTarget).ProviderPath
if ($resolvedTarget -ne $exactTarget -or $resolvedTarget -ne $ledger.stage_root -or -not $resolvedTarget.StartsWith($resolvedScratch + '\', [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Target containment failed' }
$ancestor = Get-Item -LiteralPath $resolvedTarget -Force
while ($null -ne $ancestor) {
    if (($ancestor.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { throw "Reparse ancestor: $($ancestor.FullName)" }
    $ancestor = $ancestor.Parent
}
$all = @(Get-ChildItem -LiteralPath $resolvedTarget -Force -Recurse)
if (@($all | Where-Object { ($_.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0 }).Count -gt 0) { throw 'Reparse descendant' }
$files = @($all | Where-Object { -not $_.PSIsContainer })
if ($files.Count -ne $ledger.file_count) { throw 'File count changed since duplicate validation' }
$seen = @{}
foreach ($entry in $ledger.files) {
    $path = (Resolve-Path -LiteralPath $entry.path).ProviderPath
    if (-not $path.StartsWith($resolvedTarget + '\', [System.StringComparison]::OrdinalIgnoreCase)) { throw 'Outside stage file' }
    if ($seen.ContainsKey($path)) { throw 'Duplicate inventory entry' }
    $seen[$path] = $true
    $file = Get-Item -LiteralPath $path -Force
    if ($file.Length -ne $entry.bytes -or (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Stage changed: $path" }
}
$record = [ordered]@{ target=$resolvedTarget; file_count=$files.Count; bytes=[long]$ledger.bytes; inventory_sha256=(Get-FileHash -LiteralPath $inventoryPath -Algorithm SHA256).Hash.ToLowerInvariant(); boundary_and_reparse_checks='PASS'; prior_denied_targets_in_scope=$false; status='preflight_pass'; verified_at=(Get-Date).ToString('o') }
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskScratch 'private_stage_delete_preflight.json') -Encoding utf8
Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
if (Test-Path -LiteralPath $resolvedTarget) { throw 'Stage remains after removal' }
$record.status = 'deleted'
$record['completed_at'] = (Get-Date).ToString('o')
$record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskScratch 'private_stage_delete_receipt.json') -Encoding utf8
$record | ConvertTo-Json -Depth 5
