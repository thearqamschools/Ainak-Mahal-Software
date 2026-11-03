param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot)
try {
    & $Python -m unittest discover -v
    if ($LASTEXITCODE) { throw 'Automated tests failed' }
    & $Python launcher.py --smoke-test
    if ($LASTEXITCODE) { throw 'Source GUI smoke check failed' }
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
