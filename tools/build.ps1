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
} catch {
    # Keep synthetic test failures visible in public annotations even where viewing
    # runner logs/step summaries requires authentication. Never dump environment values.
    if ($env:GITHUB_ACTIONS) {
        $details = $_.Exception.Message
        foreach ($log in @('test-results/unit-tests.log','test-results/source-smoke.log')) {
            if (Test-Path $log) { $details += "`n$log`n" + ((Get-Content $log -Tail 22) -join "`n") }
        }
        $details = $details.Replace('%','%25').Replace("`r",'%0D').Replace("`n",'%0A')
        Write-Output "::error title=Windows build diagnostics::$details"
    }
    throw
} finally { Pop-Location }
