param([string]$PostgresBin = 'C:\Program Files\PostgreSQL\18\bin')
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$local = Join-Path $root '.local'
$python = Join-Path $root 'backend\.venv\Scripts\python.exe'
$stateFile = Join-Path $local 'processes.json'
$records = @()
if (Test-Path $stateFile) { $records = Get-Content $stateFile -Raw | ConvertFrom-Json }

function Start-LocalProcess($name, $exe, $arguments, $directory) {
    $previous = $records | Where-Object { $_.name -eq $name }
    if ($previous) {
        $running = Get-Process -Id $previous.processId -ErrorAction SilentlyContinue
        if ($running -and $running.StartTime.ToUniversalTime().ToString('o') -eq $previous.started) {
            Write-Host "$name ja esta em execucao."
            return
        }
    }
    $process = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $directory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $local "$name.log") -RedirectStandardError (Join-Path $local "$name.error.log")
    $script:records = @($records | Where-Object { $_.name -ne $name }) + @(@{ name = $name; processId = $process.Id; started = $process.StartTime.ToUniversalTime().ToString('o') })
    ConvertTo-Json -InputObject @($script:records) | Set-Content $stateFile
}

Push-Location $root
try {
    & $python infra/setup_local.py --postgres-bin $PostgresBin --start-db
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar PostgreSQL.' }
    & $python backend/manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw 'Falha nas migracoes.' }
    if (!(Test-Path frontend/.next/BUILD_ID)) { throw 'Execute npm.cmd run build antes de iniciar.' }
    $scannerDir = Join-Path $local 'clamav\clamav-1.4.6.win.x64'
    $scanner = Join-Path $scannerDir 'clamd.exe'
    if ((Test-Path $scanner) -and (Test-Path (Join-Path $scannerDir 'clamd.conf'))) {
        Start-LocalProcess 'scanner' $scanner '--config-file=clamd.conf' $scannerDir
        $scannerReady = $false
        for ($attempt = 0; $attempt -lt 60; $attempt++) {
            $connection = New-Object System.Net.Sockets.TcpClient
            try {
                $pending = $connection.ConnectAsync('127.0.0.1', 3310)
                if ($pending.Wait(1000) -and $connection.Connected) { $scannerReady = $true; break }
            } catch { } finally { $connection.Dispose() }
            Start-Sleep -Seconds 1
        }
        if (!$scannerReady) { throw 'Scanner indisponivel. Consulte .local/scanner.error.log.' }
    } else { Write-Warning 'Scanner nao configurado: documentos permanecem em quarentena.' }
    Start-LocalProcess 'backend' $python 'manage.py runserver 127.0.0.1:8000 --noreload' (Join-Path $root 'backend')
    Start-LocalProcess 'worker' $python 'manage.py run_operations' (Join-Path $root 'backend')
    Start-LocalProcess 'frontend' (Get-Command node.exe).Source 'node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3000' (Join-Path $root 'frontend')
    foreach ($url in @('http://127.0.0.1:8000/api/v1/health/', 'http://127.0.0.1:3000/acessar')) {
        $ready = $false
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            try { $null = Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 2; $ready = $true; break } catch { Start-Sleep -Seconds 1 }
        }
        if (!$ready) { throw "Servico indisponivel: $url. Consulte os logs em .local." }
    }
    Write-Host 'Iustus pronto: http://localhost:3000/acessar'
    Write-Host 'Logs e emails locais: .local (nao versionados). Parar: npm.cmd run local:stop'
} finally { Pop-Location }
