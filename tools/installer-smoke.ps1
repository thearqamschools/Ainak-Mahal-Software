param([string]$Installer = 'output/AinakMahal_Setup.exe')
$ErrorActionPreference = 'Stop'
$installerPath = (Resolve-Path -LiteralPath $Installer).Path
$testRoot = Join-Path $env:TEMP ('ainak-install-' + [guid]::NewGuid().ToString('N'))
$installDir = Join-Path $testRoot 'app'
New-Item -ItemType Directory -Path $testRoot | Out-Null
$oldTcl = $env:TCL_LIBRARY; $oldTk = $env:TK_LIBRARY; $oldData = $env:AINAK_DATA_DIR; $oldResult = $env:AINAK_SMOKE_RESULT
$oldFixture = $env:AINAK_UPGRADE_FIXTURE
try {
    $p = Start-Process $installerPath -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/NOICONS','/TASKS=',('/DIR="'+$installDir+'"'),'/SMOKETEST=1',('/LOG="'+(Join-Path $testRoot 'install.log')+'"')) -PassThru -WindowStyle Hidden
    $p.WaitForExit()
    if ($p.ExitCode) { throw "Installer failed: $($p.ExitCode)" }
    $env:TCL_LIBRARY=$null; $env:TK_LIBRARY=$null
    $env:AINAK_DATA_DIR=Join-Path $testRoot 'data'
    New-Item -ItemType Directory -Force $env:AINAK_DATA_DIR | Out-Null
    $env:AINAK_UPGRADE_FIXTURE=Join-Path $env:AINAK_DATA_DIR 'ainak_mahal.db'
    $env:AINAK_SMOKE_RESULT=Join-Path $testRoot 'smoke.json'
    $exe = Join-Path $installDir 'AinakMahal.exe'
    $p=Start-Process $exe -ArgumentList '--smoke-test' -PassThru -WindowStyle Hidden
    if (!$p.WaitForExit(120000)) { $p.Kill(); throw 'Installed smoke check timed out' }
    if ($p.ExitCode -or !(Test-Path $env:AINAK_SMOKE_RESULT)) { throw 'Installed executable smoke check failed' }
    $result=Get-Content -Raw $env:AINAK_SMOKE_RESULT | ConvertFrom-Json
    if (!$result.passed) { throw ($result | ConvertTo-Json -Depth 8) }
    $beforeHash=(Get-FileHash -Algorithm SHA256 $env:AINAK_UPGRADE_FIXTURE).Hash
    New-Item -ItemType Directory -Force $env:AINAK_DATA_DIR | Out-Null
    $sentinel=Join-Path $env:AINAK_DATA_DIR 'upgrade-preservation.txt'
    Set-Content -LiteralPath $sentinel -Value 'Preserve customer data'
    $p=Start-Process $installerPath -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/NOICONS','/TASKS=',('/DIR="'+$installDir+'"'),'/SMOKETEST=1') -PassThru -WindowStyle Hidden
    $p.WaitForExit()
    if ($p.ExitCode -or (Get-Content $sentinel) -ne 'Preserve customer data') { throw 'Upgrade preservation check failed' }
    if ((Get-FileHash -Algorithm SHA256 $env:AINAK_UPGRADE_FIXTURE).Hash -ne $beforeHash) { throw 'Upgrade modified the customer database' }
    New-Item -ItemType Directory -Force test-results | Out-Null
    Copy-Item $env:AINAK_SMOKE_RESULT test-results/installed-smoke.json
    Get-FileHash -Algorithm SHA256 -LiteralPath $installerPath | Format-List
    Write-Output "PASS: installed executable and upgrade smoke checks. Isolated installation: $installDir"
} finally {
    $env:TCL_LIBRARY=$oldTcl; $env:TK_LIBRARY=$oldTk; $env:AINAK_DATA_DIR=$oldData; $env:AINAK_SMOKE_RESULT=$oldResult
    $env:AINAK_UPGRADE_FIXTURE=$oldFixture
}
