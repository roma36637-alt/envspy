# envspy terminal demo for Windows / PowerShell.
#
# Play it:   powershell -ExecutionPolicy Bypass -File docs\demo.ps1
# Record it: not needed — use docs/demo.sh under Git Bash for asciinema.
#
# Writes a throwaway .env file so the --check step fails on a fresh checkout.

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$py = $null
foreach ($candidate in @("python", "py", "python3")) {
    if (-not (Get-Command $candidate -ErrorAction SilentlyContinue)) { continue }
    & $candidate -c "import sys" 2>$null
    if ($LASTEXITCODE -eq 0) { $py = $candidate; break }
}
if (-not $py) { throw "No working Python interpreter found (tried python, py, python3)." }

function Say([string] $command) {
    Write-Host ""
    Write-Host "`$ $command" -ForegroundColor Cyan
    Start-Sleep -Milliseconds 500
}

Say "envspy -- python examples/demo.py"
& $py -m envspy -- $py examples/demo.py

if (Get-Command node -ErrorAction SilentlyContinue) {
    Say "envspy -- node examples/demo.js"
    & $py -m envspy -- node examples/demo.js
}

$tmp = ".env.example.demo"
# ASCII keeps the file BOM-free; a BOM would break the first variable name.
Set-Content -Path $tmp -Value "DATABASE_URL=`nDEBUG=`nPORT=" -Encoding ascii -NoNewline

Say "envspy --check $tmp -- python examples/demo.py   # fails CI, exits 1"
& $py -m envspy --check $tmp -- $py examples/demo.py
Write-Host "exit=$LASTEXITCODE" -ForegroundColor Yellow

Remove-Item $tmp -ErrorAction SilentlyContinue