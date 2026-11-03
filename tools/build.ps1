param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot)
try {
    New-Item -ItemType Directory -Force test-results | Out-Null
    & $Python -m unittest discover -v 2>&1 | Tee-Object -FilePath test-results/unit-tests.log
    $testExit = $LASTEXITCODE
    if ($env:GITHUB_STEP_SUMMARY) {
        '## Automated tests' | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
        '```text' | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
        Get-Content -Raw test-results/unit-tests.log | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
        '```' | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
    }
    if ($testExit) { throw 'Automated tests failed; see the workflow summary and test-results/unit-tests.log' }
    & $Python launcher.py --smoke-test 2>&1 | Tee-Object -FilePath test-results/source-smoke.log
    $smokeExit = $LASTEXITCODE
    if ($env:GITHUB_STEP_SUMMARY) {
        '## Source GUI smoke' | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
        '```json' | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
        Get-Content -Raw test-results/source-smoke.log | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
        '```' | Add-Content -LiteralPath $env:GITHUB_STEP_SUMMARY
    }
    if ($smokeExit) { throw 'Source GUI smoke check failed; see the workflow summary' }
    & $Python -m pip install -r requirements-build.txt
    if ($LASTEXITCODE) { throw 'Build dependency installation failed' }
    & $Python -m PyInstaller --noconfirm --clean --onedir --windowed --name AinakMahal --icon assets/brand/ainak.ico --add-data 'docs;docs' --add-data 'assets;assets' --hidden-import recovery --hidden-import smoke_test launcher.py
    if ($LASTEXITCODE) { throw 'Executable build failed' }
    $compiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (!(Test-Path -LiteralPath $compiler)) { throw 'Install Inno Setup 6 from https://jrsoftware.org/isinfo.php' }
    & $compiler installer/AinakMahal.iss
    if ($LASTEXITCODE) { throw 'Installer compilation failed' }
    Write-Output 'Built output/AinakMahal_Setup.exe'
} finally { Pop-Location }
