param(
    [string]$Python = "python",
    [string]$Iscc = ""
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$originalPath = $env:PATH
$pythonDirectory = Split-Path -Parent (Get-Command $Python -ErrorAction Stop).Source
$env:PATH = "$pythonDirectory;$env:SystemRoot\System32;$env:SystemRoot"
Push-Location $root
try {
    & $Python -m PyInstaller --noconfirm --clean --onedir --windowed --name MooveRecovery --paths src --add-data "assets/branding/moove_recovery.png:assets/branding" --add-data "assets/branding/dax.png:assets/branding" --add-data "src/moove_recovery/infrastructure/license_public.txt:moove_recovery/infrastructure" --exclude-module pytest --exclude-module tools packaging/launcher.py
    if ($LASTEXITCODE -ne 0) { throw "Fallo el empaquetado." }
    $bundle = Join-Path $root "dist/MooveRecovery"
    $forbidden = Get-ChildItem -LiteralPath $bundle -Recurse -File | Where-Object {
        $_.Extension -in @(".sqlite3", ".db", ".license", ".licence", ".pem", ".key", ".backup") -or
        $_.FullName -match "license_issuer|preview_navigation|\.local-data"
    }
    if ($forbidden) { throw "El paquete contiene archivos prohibidos. No distribuir." }
    foreach ($asset in @("assets/branding/moove_recovery.png", "assets/branding/dax.png", "moove_recovery/infrastructure/license_public.txt")) {
        if (-not (Test-Path -LiteralPath (Join-Path "$bundle/_internal" $asset))) { throw "Falta recurso: $asset" }
    }
    if ($Iscc) {
        & $Iscc (Join-Path $PSScriptRoot "installer.iss")
        if ($LASTEXITCODE -ne 0) { throw "Fallo el instalador." }
    } else {
        Write-Output "Ejecutable creado. Falta compilar installer.iss con Inno Setup."
    }
} finally {
    $env:PATH = $originalPath
    Pop-Location
}
