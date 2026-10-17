# Phase 8: In-process login integration and Windows build preparation

## What changed
- Launcher authenticates and starts desktop UI **in the same Python process**.
- `app.py` no longer accepts `--user` or `--role` command-line arguments.
- Directly launching `app.py` fails closed unless a session was established by the launcher.
- Windows PyInstaller script uses onedir and includes auth_session.

## Run
`python launcher.py` (Python 3.11+; no paid dependencies for this Tkinter build).

## Build on Windows
Run `build_windows.bat`; then test `dist\AinakMahal\AinakMahal.exe` on a clean Windows PC.
No precompiled Windows executable is included.

## Important limitations
This is still a **beta**, not a security-certified POS. Local Python code can be modified by an administrator or attacker with file-system access. Backend service functions still accept caller-supplied roles; complete permission enforcement at every service boundary is not finished. Do not use for live financial operations until reconciliations, invoice layouts, data migration, restore drills, installer testing, and user acceptance testing are complete. The database must be backed up before upgrades. Windows build is not tested in this Linux environment.
