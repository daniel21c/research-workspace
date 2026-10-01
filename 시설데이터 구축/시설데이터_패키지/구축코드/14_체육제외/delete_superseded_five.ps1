param([Parameter(Mandatory=$true)][string]$ArchiveRoot)
$ErrorActionPreference='Stop'
$releaseRoot=$PSScriptRoot
$cleanupRoot=Join-Path $releaseRoot 'cleanup_20260929'
$packageRoot=(Resolve-Path -LiteralPath (Join-Path $releaseRoot '..\..')).Path
$researchRoot=(Get-Item -LiteralPath $packageRoot).Parent.Parent.Parent.FullName
$allowedRoot=[System.IO.Path]::GetFullPath((Join-Path $researchRoot '_archive\facility-v1.3_superseded_20260929'))
$targetRoot=[System.IO.Path]::GetFullPath($ArchiveRoot)
if($targetRoot -cne $allowedRoot){throw 'Archive root is not the exact authorized directory'}
$historyPath=Join-Path $cleanupRoot 'historical_evidence.json'
$expectedHistoryHash='87088f4155bdab48f0137d07dc8ce8a9239e79d3b8ebcf4eef7d4a859f4cd31a'
if((Get-FileHash -LiteralPath $historyPath -Algorithm SHA256).Hash.ToLower() -ne $expectedHistoryHash){throw 'Historical evidence digest mismatch'}
$history=Get-Content -LiteralPath $historyPath -Raw | ConvertFrom-Json
if($history.accessibility_condition.verdict -ne 'PASS' -or $history.accessibility_condition.tests -ne 35 -or $history.accessibility_condition.engine_runs -ne 22){throw 'Accessibility release validation missing'}
$pre=Get-Content -LiteralPath (Join-Path $cleanupRoot 'modified_verifier_precheck.json') -Raw | ConvertFrom-Json
if(-not $pre.PASS -or -not $pre.offline_rebuild_hashes_exact -or -not $pre.historical_comparison_performed_this_run){throw 'Modified verifier precheck not passed'}
$receiptPath=Join-Path $cleanupRoot 'deletion_receipt.json'
if(Test-Path -LiteralPath $receiptPath){throw 'Deletion receipt already exists; no repeat action'}
$expectedNames=@('서울시설_2020_2025_분석용.parquet','통합_신뢰도상_2020_2025.parquet','_요약_시설별_수_좌표.csv','채택목록.csv','검증결과.json')
if($history.old_generated_files.Count -ne 5){throw 'Expected exactly five files'}
if(@(Compare-Object $expectedNames @($history.old_generated_files | ForEach-Object {Split-Path -Leaf $_.archive})).Count -ne 0){throw 'Unexpected file names'}

function Assert-NoReparseAncestors([string]$FilePath){
 $walk=[System.IO.Path]::GetFullPath($FilePath)
 while($walk){
  $entry=Get-Item -LiteralPath $walk -Force
  if(($entry.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Reparse point in target ancestry'}
  $parent=[System.IO.Path]::GetDirectoryName($walk)
  if($parent -eq $walk){break}
  $walk=$parent
 }
}

$total=0L
foreach($item in $history.old_generated_files){
 $resolved=[System.IO.Path]::GetFullPath($item.archive)
 $expected=[System.IO.Path]::GetFullPath((Join-Path $targetRoot $item.relative_path))
 if($resolved -cne $expected -or [System.IO.Path]::GetDirectoryName($resolved) -cne (Join-Path $targetRoot '데이터')){throw 'Target escaped exact authorized data directory'}
 Assert-NoReparseAncestors $resolved
 $entry=Get-Item -LiteralPath $resolved -Force
 if($entry.PSIsContainer -or $entry.Length -ne $item.old_bytes){throw 'Target type or size mismatch'}
 if((Get-FileHash -LiteralPath $resolved -Algorithm SHA256).Hash.ToLower() -ne $item.old_sha256){throw 'Old target hash mismatch'}
 $canonical=[System.IO.Path]::GetFullPath((Join-Path $packageRoot $item.relative_path))
 Assert-NoReparseAncestors $canonical
 if((Get-FileHash -LiteralPath $canonical -Algorithm SHA256).Hash.ToLower() -ne $item.replacement_sha256){throw 'Current replacement hash mismatch'}
 $total+=$entry.Length
}
if($total -ne 76782692){throw 'Unexpected total deletion size'}
$archiveManifest=Join-Path $targetRoot 'archive_manifest.json'
$archiveManifestHash=(Get-FileHash -LiteralPath $archiveManifest -Algorithm SHA256).Hash.ToLower()
$plan=@{status='preflight_passed';utc=[DateTime]::UtcNow.ToString('o');files=$history.old_generated_files;bytes=$total;reparse_ancestor_checks='all_passed';old_hashes_sizes='all_passed';canonical_hashes='all_passed';archive_manifest_sha256=$archiveManifestHash;historical_evidence_sha256=$expectedHistoryHash}
$plan | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $cleanupRoot 'deletion_preflight.json') -Encoding utf8

$completed=@()
try{
 foreach($item in $history.old_generated_files){
  # The only filesystem deletion: one exact, validated file per call; never recursive.
  Remove-Item -LiteralPath $item.archive -ErrorAction Stop
  if(Test-Path -LiteralPath $item.archive){throw 'Target remained after deletion'}
  $completed+=$item
 }
 foreach($item in $history.old_generated_files){
  $canonical=Join-Path $packageRoot $item.relative_path
  if((Get-FileHash -LiteralPath $canonical -Algorithm SHA256).Hash.ToLower() -ne $item.replacement_sha256){throw 'Current canonical changed during cleanup'}
 }
 if((Get-FileHash -LiteralPath $archiveManifest -Algorithm SHA256).Hash.ToLower() -ne $archiveManifestHash){throw 'Preserved archive manifest changed'}
 $receipt=@{status='deleted';completed_at_utc=[DateTime]::UtcNow.ToString('o');authorization='user_authorized_after_access_v3.3_validation';deleted_file_count=$completed.Count;deleted_bytes=$total;historical_evidence_sha256=$expectedHistoryHash;files=$history.old_generated_files;all_targets_absent_after=$true;all_old_hashes_sizes_verified_before=$true;canonical_sha256_verified=$history.new_analysis_sha256;archive_manifest_preserved_sha256=$archiveManifestHash;recursive_deletions=0;outside_scope_deletions=0}
 $receipt | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $receiptPath -Encoding utf8
 @{status='deleted';files=$completed.Count;bytes=$total;receipt_sha256=(Get-FileHash -LiteralPath $receiptPath -Algorithm SHA256).Hash.ToLower()} | ConvertTo-Json
}catch{
 # Record partial progress without retrying, moving, or using an alternate shell.
 @{status='failed_or_partial';completed_files=$completed;completed_count=$completed.Count;error_type=$_.Exception.GetType().Name;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $cleanupRoot 'deletion_failure.json') -Encoding utf8
 throw
}
