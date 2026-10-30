# Changelog 3 - Global Universal PATH Support for pwsh, cmd, and sh

### Summary
Configured universal global PATH integration for `vde-vlm` so it can be launched from any working directory across PowerShell (`pwsh`), Command Prompt (`cmd.exe`), and POSIX shells (`sh`, `bash`, `Git Bash`, `w64devkit`).

### Highlights & Modifications
1. **Universal Multi-Shell Launcher Shims (`C:\Users\Victor\.local\bin`)**:
   - `vde-vlm.exe`: Native binary launcher for Windows shells without execution policy restrictions.
   - `vde-vlm.cmd`: Command Prompt batch wrapper for `cmd.exe`.
   - `vde-vlm`: POSIX shell executable script (`#!/usr/bin/env sh`) for `sh`, `bash`, Git Bash, and WSL.
2. **Automated Cross-Platform Installation Scripts**:
   - `scripts/install-path.ps1`: Automated PowerShell installer that generates shims in `~/.local/bin` and ensures user PATH persistence.
   - `scripts/install-path.sh`: Automated shell installer for POSIX environments.
3. **Documentation**:
   - Updated `README.md` with instructions on universal global PATH execution.
