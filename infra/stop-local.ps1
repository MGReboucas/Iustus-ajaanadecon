$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$stateFile = Join-Path $root '.local\processes.json'
if (Test-Path $stateFile) {
    $records = Get-Content $stateFile -Raw | ConvertFrom-Json
    foreach ($record in $records) {
        $process = Get-Process -Id $record.processId -ErrorAction SilentlyContinue
        if ($process -and $process.StartTime.ToUniversalTime().ToString('o') -eq $record.started) {
            Stop-Process -Id $process.Id
            Write-Host "$($record.name) parado."
        }
    }
    Remove-Item -LiteralPath $stateFile
}
Write-Host 'PostgreSQL permanece ativo; dados preservados.'
