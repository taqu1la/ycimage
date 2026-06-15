$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$root = Split-Path -Parent $PSScriptRoot
$repoDir = Join-Path $root "assets\awesome-gpt-image-2"
$assetsRoot = Join-Path $root "assets"
$tempRoot = Join-Path $root ".codex-temp\repo-sync"
$tempRepoDir = Join-Path $tempRoot "awesome-gpt-image-2"
$buildScript = Join-Path $root "tools\build-awesome-db.mjs"
$repoUrl = "https://github.com/freestylefly/awesome-gpt-image-2.git"

if (-not (Test-Path $buildScript)) {
    $buildCandidates = Get-ChildItem -Path (Join-Path $root "tools") -Filter "build-awesome-db*.mjs" -File | Sort-Object LastWriteTime -Descending
    if ($buildCandidates.Count -gt 0) {
        $buildScript = $buildCandidates[0].FullName
    }
}

if (-not (Test-Path $buildScript)) {
    throw "Missing build script under tools\build-awesome-db*.mjs"
}

function Assert-InsideRoot {
    param(
        [Parameter(Mandatory = $true)][string]$PathValue,
        [Parameter(Mandatory = $true)][string]$RootValue
    )

    $resolvedPath = [System.IO.Path]::GetFullPath($PathValue)
    $resolvedRoot = [System.IO.Path]::GetFullPath($RootValue)
    if (-not $resolvedPath.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to operate outside project root: $resolvedPath"
    }

    return $resolvedPath
}

Assert-InsideRoot -PathValue $repoDir -RootValue $assetsRoot | Out-Null
Assert-InsideRoot -PathValue $tempRepoDir -RootValue (Join-Path $root ".codex-temp") | Out-Null

$gitProcesses = Get-CimInstance Win32_Process -Filter "name = 'git.exe'" |
    Where-Object {
        ($_.CommandLine -like "*awesome-gpt-image-2*") -or
        ($_.CommandLine -like "*repo-sync*")
    }
foreach ($process in $gitProcesses) {
    Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue
}

if (Test-Path $tempRoot) {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

git clone --depth 1 --filter=blob:none --sparse $repoUrl $tempRepoDir
git -C $tempRepoDir sparse-checkout init --cone
git -C $tempRepoDir sparse-checkout set data docs
git -C $tempRepoDir read-tree -mu HEAD

if (-not (Test-Path (Join-Path $tempRepoDir "data\cases.json"))) {
    throw "Repository sync incomplete: missing data\cases.json after clone"
}

if (Test-Path $repoDir) {
    Remove-Item -LiteralPath $repoDir -Recurse -Force
}
New-Item -ItemType Directory -Path $repoDir -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $tempRepoDir '*') -Destination $repoDir -Recurse -Force
Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue

node $buildScript
