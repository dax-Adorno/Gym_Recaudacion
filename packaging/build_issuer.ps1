param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$oldPath = $env:PATH
$pythonDirectory = Split-Path -Parent (Get-Command $Python -ErrorAction Stop).Source
$env:PATH = "$pythonDirectory;$env:SystemRoot\System32;$env:SystemRoot"
Push-Location $root
try {
    & $Python -m PyInstaller --noconfirm --clean --onefile --windowed --name GeneradorLicenciasDAX --workpath build/issuer --paths src --paths tools/license_issuer --add-data "src/moove_recovery/infrastructure/license_public.txt:moove_recovery/infrastructure" tools/license_issuer/gui.py
    if ($LASTEXITCODE -ne 0) { throw "Fallo la compilacion del emisor." }
    Write-Output "Emisor creado sin claves privadas ni contrasenas incrustadas."
} finally {
    $env:PATH = $oldPath
    Pop-Location
}
