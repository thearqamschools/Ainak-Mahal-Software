# Ainak Mahal Phase 4 — Development Beta

## Launch
Windows: Install Python 3.11+, extract ZIP, run `python launcher.py`.
On first launch create the admin username/password (10+ characters). Later sign in with the same credentials. The local database lives at `%USERPROFILE%\AinakMahal\ainak_mahal.db`.

## Features added
- Login launcher with first-time admin creation
- Admin-only UI restrictions on supplier creation, stock receiving, purchase orders, job status changes and returns
- Sales returns with quantity validation and stock restocking
- CSV exports for sales and inventory
- Database restore tool (`python restore_tool.py`) with integrity check and safety copy

## Known limitations — not production-ready
- This is a beta, not a signed Windows installer or `.exe`.
- App CLI arguments (`--user` / `--role`) are NOT secure authorization. A user with local computer access can bypass the launcher. Secure server-side/service-layer authorization is required before deployment.
- Refund values are recorded but cash refund disbursement and accounting reconciliation are NOT implemented.
- User creation/deactivation interface and role management are not implemented.
- Financial reporting uses floats inherited from earlier versions; migrate to integer minor units before production.
- Offline multi-user or multi-branch sync is not implemented.
- Database restore MUST be performed with application closed; no automatic lock check.
- Existing Phase 3 data should be backed up before opening this version.

## Tests
`python -m unittest discover -p 'test_*.py' -v`

## Build
`build_windows.bat` from the earlier alpha is outdated; it targets app.py. For testing, run from Python source. Installer packaging is pending.
