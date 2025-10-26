$ErrorActionPreference = 'Stop'

$root = (Get-Location).Path
$ts = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupDir = Join-Path $root 'backups'
if (-not (Test-Path $backupDir)) { New-Item -ItemType Directory -Path $backupDir | Out-Null }

$dest = Join-Path $backupDir ("backup-" + $ts + ".zip")

# Diretórios/itens a excluir do backup
$excludeNames = @('.venv', '.pytest_cache', '__pycache__', 'dist', 'build', 'releases', 'backups', '.git', '.gitignore', 'mtdl_pcm.db')

# Copiar snapshot do banco antes do zip (evita arquivo bloqueado)
$dbPath = Join-Path $root 'mtdl_pcm.db'
$dbCopy = $null
if (Test-Path $dbPath) {
  $dbCopy = Join-Path $backupDir ("mtdl_pcm-" + $ts + ".db")
  try {
    Copy-Item -Path $dbPath -Destination $dbCopy -ErrorAction Stop
  } catch {
    Write-Warning "Não foi possível copiar o banco (arquivo em uso). Prosseguindo sem DB."
    $dbCopy = $null
  }
}

$items = Get-ChildItem -LiteralPath $root -Force |
  Where-Object { -not ($excludeNames -contains $_.Name) }

# Monta lista final para o zip
$pathsToZip = @($items.FullName)
if ($dbCopy) { $pathsToZip += $dbCopy }

Compress-Archive -Path $pathsToZip -DestinationPath $dest -Force

# Remover snapshot temporário do DB
if ($dbCopy -and (Test-Path $dbCopy)) { Remove-Item -Path $dbCopy -Force }

Get-Item $dest | Select-Object FullName, Length | Format-List
Write-Host "Backup criado em $dest"