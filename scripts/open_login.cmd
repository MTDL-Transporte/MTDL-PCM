@echo off
setlocal
REM Tenta abrir o domínio central; se falhar, abre localhost e garante servidor
set "LOGIN_URL=https://pcm.mtdl.com.br/admin/login"
set "LOCAL_URL=http://127.0.0.1:8000/admin/login"

REM Testa rapidamente se o domínio está acessível
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -Uri '%LOGIN_URL%' -UseBasicParsing -TimeoutSec 3; exit 0 } catch { exit 1 }"
if %ERRORLEVEL%==0 (
  start "" "%LOGIN_URL%"
  goto :EOF
)

REM Domínio indisponível: inicia servidor local (se necessário) e abre localhost
for /f "tokens=1" %%P in ('tasklist /FI "IMAGENAME eq MTDL-PCM.exe" ^| find /I "MTDL-PCM.exe"') do set RUNNING=1
if not defined RUNNING (
  echo Iniciando MTDL-PCM local...
  start "" "%~dp0MTDL-PCM.exe"
  timeout /t 3 >nul
) else (
  echo MTDL-PCM local ja esta em execucao.
)
start "" "%LOCAL_URL%"
endlocal