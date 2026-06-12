$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$currentName = Split-Path -Leaf $MyInvocation.MyCommand.Path
$candidates = Get-ChildItem -Path $currentDir -Filter "sync-awesome-gpt-image-2*.ps1" -File |
    Where-Object { $_.Name -ne $currentName } |
    Sort-Object LastWriteTime -Descending

if ($candidates.Count -eq 0) {
    throw "Missing sync-awesome-gpt-image-2*.ps1 implementation"
}

& $candidates[0].FullName
