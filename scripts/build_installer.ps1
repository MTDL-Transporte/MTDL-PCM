param(
  [string]$Version = "",
  [string]$Name = "MTDL-PCM"
)

$ErrorActionPreference = 'Stop'

Write-Host "==> Preparando compilação do instalador: $Name v$Version"

# Raiz do projeto
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$distExe = Join-Path $root "dist\$Name.exe"
$issFile = Join-Path $PSScriptRoot "installer.iss"
$versionFile = Join-Path $root "VERSION"

# Descobrir versão se não informada
if (-not $Version -or $Version.Trim().Length -eq 0) {
  if (Test-Path $versionFile) {
    $Version = (Get-Content -Path $versionFile -Raw).Trim()
  } else {
    $Version = "1.0.1"
  }
}

# Sincroniza feeds de versão com a versão alvo
try {
  & .\.venv\Scripts\python.exe scripts\bump_version.py --set $Version | Out-Null
} catch {
  Write-Warning "Não foi possível sincronizar feeds de versão. Prosseguindo mesmo assim."
}

# Garantir que o EXE existe (gerar se necessário)
if (-not (Test-Path $distExe)) {
  Write-Host "==> Executável não encontrado em dist/. Vou gerar com build.ps1"
  $buildScript = Join-Path $PSScriptRoot "build.ps1"
  if (-not (Test-Path $buildScript)) { throw "Script de build não encontrado: $buildScript" }
  & $buildScript -Version $Version -Name $Name
  if (-not (Test-Path $distExe)) { throw "Build falhou: $distExe não existe" }
}

# Verificar ISCC.exe (Inno Setup Compiler)
$possible = @(
  "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe",
  "C:\\Program Files\\Inno Setup 6\\ISCC.exe"
)
$iscc = $null

# Tentar descobrir via PATH
$cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if ($cmd) { $iscc = $cmd.Path }

# Tentar nos caminhos comuns
if (-not $iscc) {
  foreach ($p in $possible) { if (Test-Path $p) { $iscc = $p; break } }
}

# Instalar automaticamente via Chocolatey se não encontrado (em runners Windows)
if (-not $iscc) {
  Write-Warning "ISCC.exe não encontrado. Tentando instalar Inno Setup via Chocolatey..."
  try {
    choco install innosetup -y | Out-Null
  } catch {
    Write-Warning "Falha ao instalar Inno Setup via Chocolatey."
  }
  # Procurar novamente
  $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
  if ($cmd) { $iscc = $cmd.Path }
  if (-not $iscc) {
    foreach ($p in $possible) { if (Test-Path $p) { $iscc = $p; break } }
  }
}

if (-not $iscc) { throw "ISCC.exe não encontrado após tentativa de instalação. Instale o Inno Setup 6: https://jrsoftware.org/isdl.php" }

# Compilar o instalador
Write-Host "==> Compilando instalador com Inno Setup"
Write-Host "==> Rodando: $iscc /DMyAppVersion=$Version $issFile"
& $iscc "/DMyAppVersion=$Version" "$issFile"

$releaseDir = Join-Path $root "releases"
Get-ChildItem -Path $releaseDir -Filter "$Name-Setup-$Version*.exe" | ForEach-Object {
  Write-Host "==> Instalador gerado: " $_.FullName
}