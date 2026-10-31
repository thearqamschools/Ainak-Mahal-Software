param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$previousPath=$env:PATH
$previousCache=$env:PYINSTALLER_CONFIG_DIR
Push-Location (Split-Path $PSScriptRoot)
try {
    & $Python -m pip install --disable-pip-version-check -r requirements-build.txt
    if ($LASTEXITCODE) { throw 'Build dependency installation failed' }
    & $Python tools/version_resource.py
    if ($LASTEXITCODE) { throw 'Version metadata generation failed' }
    & $Python -m unittest discover -v
    if ($LASTEXITCODE) { throw 'Automated tests failed' }
    & $Python qt_launcher.py --smoke-test
    if ($LASTEXITCODE) { throw 'Source GUI smoke check failed' }
    & $Python -m pip install -r requirements-build.txt
    if ($LASTEXITCODE) { throw 'Build dependency installation failed' }
    # Keep unrelated tool DLLs (notably Poppler's incompatible ICU) off the resolver PATH.
    $pythonFolder=Split-Path (& $Python -c 'import sys; print(sys.executable)')
    $env:PATH=[Environment]::SystemDirectory+';'+$env:SystemRoot+';'+$pythonFolder
    $env:PYINSTALLER_CONFIG_DIR=Join-Path (Get-Location) 'build/packager-cache'
    & $Python -m PyInstaller --noconfirm --clean --onedir --windowed --name AinakMahal --icon assets/brand/ainak-mahal.ico --version-file build/windows-version.txt --add-data 'docs;docs' --add-data 'assets;assets' --hidden-import recovery --hidden-import qt_smoke --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick --exclude-module PySide6.QtPdf --exclude-module PIL --exclude-module resvg_py --exclude-module imageio_ffmpeg qt_launcher.py
    if ($LASTEXITCODE) { throw 'Executable build failed' }
    & $Python tools/validate_bundle.py
    if ($LASTEXITCODE) { throw 'Packaged DLL ABI validation failed' }
    & $Python tools/collect_notices.py
    if ($LASTEXITCODE) { throw 'License notice collection failed' }
    $compiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (!(Test-Path -LiteralPath $compiler)) { throw 'Install Inno Setup 6 from https://jrsoftware.org/isinfo.php' }
    $release=Get-Content -Raw build/release-metadata.json | ConvertFrom-Json
    & $compiler "/DMyAppVersion=$($release.version)" "/DMyFileVersion=$($release.file_version)" "/DMyBuildId=$($release.build_id)" installer/AinakMahal.iss
    if ($LASTEXITCODE) { throw 'Installer compilation failed' }
    Copy-Item -LiteralPath build/release-metadata.json -Destination output/release-metadata.json -Force
    Write-Output 'Built output/AinakMahal_Setup.exe'
} finally { $env:PATH=$previousPath; $env:PYINSTALLER_CONFIG_DIR=$previousCache; Pop-Location }
