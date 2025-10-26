param(
  [string]$Version = "1.0.0",
  [string]$Name = "MTDL-PCM",
  [string]$Port = "8000"
)

Write-Host "==> Preparando build do instalador: $Name v$Version"

# Escreve versão no arquivo VERSION e exporta env var
$versionFile = Join-Path $PSScriptRoot "..\VERSION"
Set-Content -Path $versionFile -Value $Version -NoNewline
$env:APP_VERSION = $Version

# Limpa saída anterior
if (Test-Path (Join-Path $PSScriptRoot "..\dist")) { Remove-Item -Recurse -Force (Join-Path $PSScriptRoot "..\dist") }
if (Test-Path (Join-Path $PSScriptRoot "..\build")) { Remove-Item -Recurse -Force (Join-Path $PSScriptRoot "..\build") }

# Caminhos de dados
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$templates = Join-Path $root "templates"; if (-Not (Test-Path $templates)) { New-Item -ItemType Directory -Path $templates | Out-Null }
$static = Join-Path $root "static"; if (-Not (Test-Path $static)) { New-Item -ItemType Directory -Path $static | Out-Null }

# Detecta ou gera ícone (app.ico) se possível
$iconPath = $null
$iconCandidates = @(
  (Join-Path $root "static\img\app.ico"),
  (Join-Path $root "static\img\favicon.ico")
)
foreach ($c in $iconCandidates) { if (Test-Path $c) { $iconPath = $c; break } }

if (-Not $iconPath) {
  $svgPath = Join-Path $root "static\img\favicon.svg"
  if (Test-Path $svgPath) {
    Write-Host "==> Gerando ícone app.ico a partir de favicon.svg"
    try {
      & .\.venv\Scripts\pip.exe install --disable-pip-version-check -q cairosvg pillow | Out-Null
    } catch {
      Write-Warning "Falha ao instalar conversores (cairosvg/pillow). Prosseguindo sem geração automática."
    }
    $tempDir = Join-Path $root "temp"
    if (-Not (Test-Path $tempDir)) { New-Item -ItemType Directory -Path $tempDir | Out-Null }
    $pyFile = Join-Path $tempDir "make_ico.py"
    $pyContent = @'
import io, os
from PIL import Image
import cairosvg

root = r"{root}"
svg_path = os.path.join(root, "static", "img", "favicon.svg")
ico_path = os.path.join(root, "static", "img", "app.ico")
png_bytes = cairosvg.svg2png(url=svg_path, output_width=256, output_height=256)
img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
img.save(ico_path, format="ICO", sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
print("ICO written:", ico_path)
'@
    $pyContent = $pyContent.Replace("{root}", $root)
    Set-Content -Path $pyFile -Value $pyContent
    try {
      & .\.venv\Scripts\python.exe $pyFile | Out-Null
    } catch {
      Write-Warning "Falha ao converter favicon.svg em app.ico"
    }
    $generated = Join-Path $root "static\img\app.ico"
    if (Test-Path $generated) { $iconPath = $generated }
  }
}

# Monta argumentos do PyInstaller
$pyArgs = @(
  "pyinstaller",
  "--noconfirm",
  "--clean",
  "--onefile",
  "--name", $Name,
  "--hidden-import=uvicorn",
  "--hidden-import=fastapi",
  "--hidden-import=jinja2",
  "--hidden-import=sqlalchemy",
  "--hidden-import=pydantic",
  "--hidden-import=starlette",
  "--hidden-import=main",
  "--add-data", "`"$templates;templates`"",
  "--add-data", "`"$static;static`""
)

if ($iconPath) {
  Write-Host "==> Ícone detectado: $iconPath"
  $pyArgs += @("--icon", "`"$iconPath`"")
} else {
  Write-Warning "Nenhum ícone encontrado/gerado. Prosseguindo sem --icon."
}

$pyArgs += "run.py"
$cmd = $pyArgs -join " "

Write-Host "==> Rodando: $cmd"
Invoke-Expression $cmd

# Copia artefato para releases (apenas se existir)
$releaseDir = Join-Path $root ("releases\" + $Name + "-" + $Version)
if (-Not (Test-Path $releaseDir)) { New-Item -ItemType Directory -Path $releaseDir | Out-Null }
$exePath = Join-Path $root ("dist\" + $Name + ".exe")
if (Test-Path $exePath) {
  Copy-Item $exePath -Destination $releaseDir -Force
  Write-Host "==> Build finalizado. Arquivo: " (Join-Path $releaseDir ($Name + ".exe"))
  Write-Host "==> Publique no Google Drive e atualize static/version.json com a URL"
} else {
  Write-Error "Build falhou: Executável não encontrado em $exePath"
}