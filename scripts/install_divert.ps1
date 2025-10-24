# WinDivert install for SW-Exporter (single path, no prompts)
# RUN AS ADMIN from repo root: powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\install_divert.ps1"

$ErrorActionPreference = "Stop"

# Config
$WinDivertVersion = "2.2.2"
$ZipUrl = "https://github.com/basil00/WinDivert/releases/download/v$WinDivertVersion/WinDivert-$WinDivertVersion-A.zip"
$RepoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$OutDir   = Join-Path $RepoRoot "tools\windivert"
$SwexDir  = Join-Path $RepoRoot "tools\sw-exporter"

# Admin check
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
  ).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)) {
  throw "Run this script as Administrator."
}

# Prep
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$zipFile = Join-Path $env:TEMP "WinDivert-$WinDivertVersion.zip"

Write-Host "== WinDivert $WinDivertVersion setup =="

# Download
Write-Host "Downloading: $ZipUrl"
Invoke-WebRequest -Uri $ZipUrl -OutFile $zipFile -UseBasicParsing

# Extract
Write-Host "Extracting to: $OutDir"
Add-Type -AssemblyName System.IO.Compression.FileSystem
$extractRoot = Join-Path $OutDir "WinDivert-$WinDivertVersion-A"
if (Test-Path $extractRoot) { Remove-Item -Recurse -Force $extractRoot }
[IO.Compression.ZipFile]::ExtractToDirectory($zipFile, $OutDir)

# Find files (prefer x64)
$dll = Get-ChildItem -Path $extractRoot -Recurse -Filter "WinDivert.dll"   | Where-Object {$_.FullName -match "\\(x64|amd64)\\"} | Select-Object -First 1
if (-not $dll) { $dll = Get-ChildItem -Path $extractRoot -Recurse -Filter "WinDivert.dll" | Select-Object -First 1 }
$sys = Get-ChildItem -Path $extractRoot -Recurse -Filter "WinDivert64.sys" | Select-Object -First 1
$inf = Get-ChildItem -Path $extractRoot -Recurse -Filter "*.inf"           | Select-Object -First 1

if (-not $dll) { throw "WinDivert.dll not found in $extractRoot" }
if (-not $sys) { throw "WinDivert64.sys not found in $extractRoot" }

# Copy DLL next to SW-Exporter for easy loading
if (Test-Path $SwexDir) {
  Copy-Item -Force $dll.FullName (Join-Path $SwexDir "WinDivert.dll")
  Write-Host "Copied DLL -> $SwexDir\WinDivert.dll"
} else {
  Write-Warning "SW-Exporter folder not found at $SwexDir (skipping DLL copy)."
}

# Install driver
Write-Host "Installing WinDivert driver..."
if ($inf) {
  pnputil /add-driver "$($inf.FullName)" /install | Out-Null
  Write-Host "pnputil install attempted."
} else {
  $destSys = Join-Path $env:WINDIR "System32\drivers\WinDivert64.sys"
  Copy-Item -Force $sys.FullName $destSys
  try {
    sc.exe query WinDivert | Out-Null
    $exists = $LASTEXITCODE -eq 0
  } catch { $exists = $false }
  if (-not $exists) { sc.exe create WinDivert binPath= "`"$destSys`"" type= kernel start= demand | Out-Null }
  sc.exe start WinDivert | Out-Null
  Write-Host "WinDivert service created/started."
}

Write-Host "Done. WinDivert installed and DLL placed for SW-Exporter."
