[CmdletBinding()]
param(
    [ValidateSet('V1', 'V2', 'V3', 'Tests')]
    [string]$Version = 'V1',
    [string[]]$Arguments = @()
)

$ErrorActionPreference = 'Stop'
$candidateList = [System.Collections.Generic.List[object]]::new()
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $venvPython) {
    $candidateList.Add(@{ Path = $venvPython; Prefix = @() })
}
foreach ($commandName in @('python', 'python3', 'py')) {
    $resolvedCommand = Get-Command $commandName -CommandType Application -ErrorAction SilentlyContinue
    if ($resolvedCommand) {
        $candidateList.Add(@{ Path = $resolvedCommand.Source; Prefix = $(if ($commandName -eq 'py') { @('-3') } else { @() }) })
    }
}
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (Test-Path -LiteralPath $bundledPython) {
    $candidateList.Add(@{ Path = $bundledPython; Prefix = @() })
}
$selectedPython = $null
foreach ($candidate in $candidateList) {
    try {
        $candidatePrefix = @($candidate.Prefix)
        & $candidate.Path @candidatePrefix -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) {
            $selectedPython = $candidate
            break
        }
    } catch {
        # Un alias Windows Store inactif n'empêche pas les autres candidats.
    }
}
if (-not $selectedPython) {
    throw 'Python 3.11 ou supérieur introuvable. Installer Python puis relancer.'
}
$previousEncoding = $env:PYTHONIOENCODING
$previousBytecode = $env:PYTHONDONTWRITEBYTECODE
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
Push-Location -LiteralPath $PSScriptRoot
try {
    $launchArguments = @($selectedPython.Prefix)
    if ($Version -eq 'Tests') {
        $launchArguments += @('-m', 'unittest', 'discover', '-s', 'tests', '-v')
    } else {
        $launchArguments += @('-m', ('dijkstra.' + $Version.ToLowerInvariant()))
    }
    $launchArguments += $Arguments
    & $selectedPython.Path @launchArguments
    $resultCode = $LASTEXITCODE
} finally {
    Pop-Location
    $env:PYTHONIOENCODING = $previousEncoding
    $env:PYTHONDONTWRITEBYTECODE = $previousBytecode
}
exit $resultCode
