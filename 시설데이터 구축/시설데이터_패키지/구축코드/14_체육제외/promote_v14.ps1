param([Parameter(Mandatory=$true)][string]$ArchiveRoot)
$ErrorActionPreference='Stop'
$packageRoot=(Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$researchRoot=(Get-Item -LiteralPath $packageRoot).Parent.Parent.Parent.FullName
$allowedArchive=[System.IO.Path]::GetFullPath((Join-Path $researchRoot '_archive\facility-v1.3_superseded_20260929'))
$archiveTarget=[System.IO.Path]::GetFullPath($ArchiveRoot)
if($archiveTarget -ne $allowedArchive){throw 'Archive target differs from authorized exact directory'}
$manifestPath=Join-Path $PSScriptRoot 'promotion_manifest.json'
$manifest=Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if($manifest.file_count -ne 5){throw 'Unexpected file count'}
$allowedNames=@('데이터/서울시설_2020_2025_분석용.parquet','데이터/통합_신뢰도상_2020_2025.parquet','데이터/_요약_시설별_수_좌표.csv','데이터/채택목록.csv','데이터/검증결과.json')
if(@(Compare-Object $allowedNames @($manifest.files.relative_path)).Count -ne 0){throw 'Unexpected replacement files'}
$planned=@()
foreach($item in $manifest.files){
 $source=[System.IO.Path]::GetFullPath((Join-Path $packageRoot $item.relative_path))
 $staged=[System.IO.Path]::GetFullPath((Join-Path $packageRoot $item.staged_relative_path))
 $archive=[System.IO.Path]::GetFullPath((Join-Path $archiveTarget $item.relative_path))
 if(-not $source.StartsWith(($packageRoot+'\데이터\'),[StringComparison]::OrdinalIgnoreCase)){throw 'Source escaped data directory'}
 if(-not $staged.StartsWith(($PSScriptRoot+'\staging\'),[StringComparison]::OrdinalIgnoreCase)){throw 'Staged path escaped release directory'}
 if(-not $archive.StartsWith(($archiveTarget+'\'),[StringComparison]::OrdinalIgnoreCase)){throw 'Archive path escaped authorized directory'}
 if(Test-Path -LiteralPath $archive){throw 'Archive file already exists'}
 if((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLower() -ne $item.old_sha256){throw 'Old file changed since inventory'}
 if((Get-FileHash -LiteralPath $staged -Algorithm SHA256).Hash.ToLower() -ne $item.new_sha256){throw 'Staged file changed since verification'}
 $planned+=@{source=$source;staged=$staged;archive=$archive;old_sha256=$item.old_sha256;new_sha256=$item.new_sha256;relative_path=$item.relative_path;old_bytes=$item.old_bytes}
}
New-Item -ItemType Directory -Path $archiveTarget -Force | Out-Null
$archiveManifest=Join-Path $archiveTarget 'archive_manifest.json'
@{release='facility-v1.3';replaced_by='facility-v1.4';status='in_progress';package_root=$packageRoot;files=$planned} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $archiveManifest -Encoding utf8
$completed=@()
try{
 foreach($item in $planned){
  New-Item -ItemType Directory -Path (Split-Path -Parent $item.archive) -Force | Out-Null
  Move-Item -LiteralPath $item.source -Destination $item.archive
  $completed+=$item
  if((Get-FileHash -LiteralPath $item.archive -Algorithm SHA256).Hash.ToLower() -ne $item.old_sha256){throw 'Archive integrity mismatch'}
  Move-Item -LiteralPath $item.staged -Destination $item.source
  if((Get-FileHash -LiteralPath $item.source -Algorithm SHA256).Hash.ToLower() -ne $item.new_sha256){throw 'Promoted integrity mismatch'}
 }
}catch{
 for($i=$completed.Count-1;$i -ge 0;$i--){
  $item=$completed[$i]
  if(Test-Path -LiteralPath $item.source){Move-Item -LiteralPath $item.source -Destination $item.staged}
  Move-Item -LiteralPath $item.archive -Destination $item.source
 }
 @{status='rolled_back';files=$planned} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $archiveManifest -Encoding utf8
 throw
}
$result=@{release='facility-v1.3';replaced_by='facility-v1.4';status='complete';package_root=$packageRoot;file_count=$completed.Count;old_total_bytes=$manifest.old_total_bytes;archived_hashes_verified=$true;active_hashes_verified=$true;permanent_deletions=0;retention='Keep old v1.3 until accessibility v1.4 recalculation and validation completes';files=$planned}
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $archiveManifest -Encoding utf8
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'archive_result.json') -Encoding utf8
@{status='complete';archived_files=$completed.Count;old_total_bytes=$manifest.old_total_bytes;archive_root=$archiveTarget;permanent_deletions=0} | ConvertTo-Json
