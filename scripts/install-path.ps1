<#
.SYNOPSIS
    Installs vde-vlm global CLI shims into ~/.local/bin and verifies PATH.
.DESCRIPTION
    Ensures vde-vlm is instantly callable from any working directory across
    PowerShell (pwsh), Command Prompt (cmd.exe), and Bash/sh.
#>

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$binDir = Join-Path $env:USERPROFILE ".local\bin"

if (-not (Test-Path $binDir)) {
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
    Write-Host "[OK] Created directory: $binDir"
}

# Locate python executable
$pythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonExe) {
    $pythonExe = "python"
}

# 1. Shell script for sh/bash (Git Bash, WSL, MSYS2)
$shShim = Join-Path $binDir "vde-vlm"
$shContent = @"
#!/usr/bin/env sh
exec "$($pythonExe -replace '\\', '/')" -m vde_vlm "`$@"
"@
Set-Content -Path $shShim -Value $shContent -Encoding utf8 -NoNewline
Write-Host "[OK] Installed sh shim: $shShim"

# 2. Batch script for cmd.exe
$cmdShim = Join-Path $binDir "vde-vlm.cmd"
$cmdContent = @"
@echo off
"$pythonExe" -m vde_vlm %*
"@
Set-Content -Path $cmdShim -Value $cmdContent -Encoding ascii
Write-Host "[OK] Installed cmd shim: $cmdShim"

# 3. Native Windows executable launcher
$pipExe = Join-Path (Split-Path -Parent $pythonExe) "Scripts\vde-vlm.exe"
$destExe = Join-Path $binDir "vde-vlm.exe"
if (Test-Path $pipExe) {
    Copy-Item -Path $pipExe -Destination $destExe -Force
    Write-Host "[OK] Installed Windows binary launcher: $destExe"
}

# 4. Verify ~/.local/bin is in User PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$binDir*") {
    $newPath = "$binDir;$userPath"
    [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
    $env:Path = "$binDir;$env:Path"
    Write-Host "[OK] Added $binDir to User PATH."
} else {
    Write-Host "[OK] $binDir is already present in User PATH."
}

Write-Host "`nvde-vlm is now globally accessible in pwsh, cmd, and sh!"
Write-Host "Test by running: vde-vlm list"
