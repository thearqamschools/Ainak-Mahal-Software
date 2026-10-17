# Ainak Mahal — Windows installer build kit

**No Windows EXE is included in this archive.** This environment is Linux and cannot validate or produce a native Windows installer. The package contains an automated Windows build workflow.

## Option A — GitHub Actions (no Python on shop PC)
1. Create a **private** GitHub repository and upload the **contents of this folder** to the repository root (including `.github/workflows/windows-installer.yml`). Do not upload customer databases.
2. Open the repository's **Actions** tab → **Build Windows installer** → **Run workflow**.
3. After a successful run, open the run → **Artifacts** → download **AinakMahal-Windows-Installer**.
4. Extract the artifact ZIP, then run `AinakMahal_Setup.exe` on Windows.

## Option B — Windows build computer
Install Python 3.11+ and Inno Setup 6 on the **build computer only**, then double-click `build_installer_windows.bat`. The installer will be in `output\AinakMahal_Setup.exe`. Shop PCs do not need Python.

## Installation and data
The installer creates Start Menu and optional Desktop shortcuts. The application stores its SQLite database under the current Windows user's home directory, `AinakMahal\ainak_mahal.db`. Uninstalling the application should not remove this user database. Back up data before upgrades.

## Critical limitations
This is **beta code**, not a production-certified accounting/POS system. Automated tests do not establish Windows compatibility or operational safety. Backend authorization, accounting reconciliation, migration from older databases, backup recovery, and printer testing still require validation. Do not enter live financial/customer records until acceptance testing passes. GitHub Actions usage is subject to GitHub plan and quotas; it is not part of offline runtime costs.
