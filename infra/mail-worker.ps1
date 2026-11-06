param([ValidateSet('start', 'stop', 'status', 'check')][string]$Action = 'status')
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$mailLocal = Join-Path $repoRoot '.local'
$mailPython = Join-Path $repoRoot 'backend\.venv\Scripts\python.exe'
$mailBackend = Join-Path $repoRoot 'backend'
$mailState = Join-Path $mailLocal 'mail-worker-process.json'
$mailSettings = '--settings=config.settings.mail_worker'

function Get-MailProcess {
    if (!(Test-Path -LiteralPath $mailState)) { return $null }
    $record = Get-Content -LiteralPath $mailState -Raw | ConvertFrom-Json
    $process = Get-Process -Id $record.processId -ErrorAction SilentlyContinue
    if ($process -and $process.StartTime.ToUniversalTime().ToString('o') -eq $record.started -and $process.Path -eq $mailPython) {
        return $process
    }
    return $null
}

$existing = Get-MailProcess
if ($Action -eq 'status') {
    if ($existing) { Write-Host 'Email worker running.' } else { Write-Host 'Email worker stopped.' }
    exit 0
}
if ($Action -eq 'stop') {
    if ($existing) { Stop-Process -Id $existing.Id; Write-Host 'Email worker stopped. Pending messages remain in the database.' }
    exit 0
}
if (!(Test-Path -LiteralPath (Join-Path $mailBackend '.env'))) {
    throw 'Configure backend/.env with production database keys and Gmail SMTP first.'
}
Push-Location $mailBackend
try {
    if ($Action -eq 'check') {
        & $mailPython manage.py check_mail --connect $mailSettings
        if ($LASTEXITCODE -ne 0) { throw 'Email connection check failed.' }
    } else {
        if ($existing) { Write-Host 'Email worker already running.'; exit 0 }
        New-Item -ItemType Directory -Path $mailLocal -Force | Out-Null
        & $mailPython manage.py check_mail --connect $mailSettings
        if ($LASTEXITCODE -ne 0) { throw 'Configure Gmail SMTP before starting the queue.' }
        $process = Start-Process -FilePath $mailPython -ArgumentList @('manage.py', 'run_mail_queue', $mailSettings) -WorkingDirectory $mailBackend -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $mailLocal 'mail-worker.log') -RedirectStandardError (Join-Path $mailLocal 'mail-worker.error.log')
        @{ processId = $process.Id; started = $process.StartTime.ToUniversalTime().ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath $mailState
        Start-Sleep -Seconds 2
        if ($process.HasExited) { throw 'Email worker exited. Check .local/mail-worker.error.log.' }
        Write-Host 'Email worker started in background. Keep the computer awake and online.'
    }
} finally { Pop-Location }
