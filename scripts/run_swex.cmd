@echo off
setlocal

rem --- resolve repo + swex paths ---
set "REPO=%~dp0.."
for %%# in ("%REPO%") do set "REPO=%%~f#"
set "SWEX=%REPO%\tools\sw-exporter"

if not exist "%SWEX%\package.json" (
  echo [ERROR] SW-Exporter not found at "%SWEX%".
  exit /b 1
)

rem --- find node/npm (absolute paths) ---
set "NODE_EXE="
for /f "delims=" %%N in ('where node 2^>nul') do if not defined NODE_EXE set "NODE_EXE=%%N"
if not defined NODE_EXE if exist "C:\Program Files\nodejs\node.exe" set "NODE_EXE=C:\Program Files\nodejs\node.exe"
if not defined NODE_EXE (
  echo [ERROR] Node.js not found. Install LTS: winget install OpenJS.NodeJS.LTS
  exit /b 1
)

for %%D in ("%NODE_EXE%") do set "NODE_DIR=%%~dpD"
set "NPM_CMD=%NODE_DIR%npm.cmd"
if not exist "%NPM_CMD%" (
  echo [ERROR] npm not found at "%NPM_CMD%".
  exit /b 1
)

pushd "%SWEX%"

if not exist "node_modules" (
  echo [+] Installing SW-Exporter deps...
  call "%NPM_CMD%" ci || goto :fail
)

echo [+] Starting webpack dev server...
start "" "%NPM_CMD%" run dev

rem small delay so dev server starts
timeout /t 2 >nul

echo [+] Launching SW-Exporter...
call "%NPM_CMD%" start
set "RC=%ERRORLEVEL%"

popd
exit /b %RC%

:fail
popd
echo [ERROR] Setup failed.
exit /b 1
