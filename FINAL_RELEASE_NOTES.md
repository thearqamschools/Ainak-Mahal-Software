# Ainak Mahal — Consolidated development build

This package consolidates prior phases and adds: HTML printable invoice export, verified timestamped local backups, stock/payment reconciliation diagnostics, and tests.

## Run
Windows: install Python 3.11+ with Tkinter, extract this archive, run `python launcher.py`. Do **not** launch app.py directly. Build optional Windows executable by running `build_windows.bat` on Windows with Python and internet access to install PyInstaller. No compiled EXE is included.

## Validation
Run `python -m unittest discover -v`. 29 automated tests pass in the build environment. Windows installer, printer hardware, restore workflow, migrations from earlier databases, end-to-end GUI, and real financial accounting have **not** been independently validated.

## Important limitations
- This is a development candidate, **not a certified production release**. No real customer financial records until acceptance tests pass.
- Role checks are not consistently enforced at the business-service layer. Local database and source files can be changed by anyone with filesystem access. Protect the Windows account and local database.
- Invoices export as printable HTML (open in browser), not a dedicated thermal printer driver or PDF engine.
- Stock/payment reconciliation is diagnostic, not an accounting general ledger; returns and refunds need careful manual reconciliation.
- Timestamped backups are initiated manually, not scheduled. Keep off-computer copies.
- Online sync, multi-device use, multi-branch deployment, and safe concurrent database access are **not implemented**. `sync_outbox` is only a preparatory schema.
- No automatic database migration from earlier builds. Back up old data and test upgrades on a copy.
- A Windows .exe can be built with included script, but this package is source code only.

## Acceptance checklist before shop use
1. Back up database and test restoration on a second computer.
2. Test all role permissions including direct service calls.
3. Print sample invoices on actual A4/thermal printer.
4. Test partial payments, returns, refund payouts, inventory reconciliation and day-end cash totals.
5. Verify migration on a **copy** of existing data.
6. Test Windows installation, antivirus false positives, power failure, backups and recovery.
