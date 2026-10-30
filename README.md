# Ainak Mahal · Offline Windows optical store

A native Windows desktop application for Ainak Mahal, Millat Chowk, Faisalabad.
Implemented against [Issue #1](https://github.com/thearqamschools/Ainak-Mahal-Software/issues/1).
No runtime internet connection, Python installation, hosting or subscription is required
when installed using `AinakMahal_Setup.exe`.

## Start

Install `output/AinakMahal_Setup.exe`, open Ainak Mahal, and create the first administrator.
There is no default password. For development, install CPython 3.14 x64 including Tcl/Tk
and run `python launcher.py`. Keep `app.py` and `legacy_launcher.py` for legacy support;
`app.py` intentionally refuses a direct launch without its authenticated session.

Customer, prescription, inventory, barcode checkout, partial payment, returns/refund payouts,
store-credit redemption, lab jobs, supplier/PO receipt, cash/expenses, closing, reports,
printing, staff administration and verified backup/recovery are available through the sidebar.
F2 opens checkout; F3 opens customers; Ctrl+Enter saves a sale.

## Data and upgrade

Data stays at `%USERPROFILE%\AinakMahal\ainak_mahal.db`. Installation and uninstallation
never delete it. Additive schema version 1 preserves legacy integer IDs, rows and tables;
a pre-migration backup is made automatically. UUID identities, timestamps, branch MAIN and
change journals prepare a future sync boundary, with no network dependency now.

## Build and test

On Windows, with CPython 3.14 x64 (Tcl/Tk included) and Inno Setup 6 installed:

```powershell
python -m venv .venv
./tools/build.ps1 -Python ./.venv/Scripts/python.exe
./tools/installer-smoke.ps1
```

The build runs all unit/integration tests and source GUI smoke checks, installs pinned
packaging dependencies, freezes the app and compiles the installer. CI repeats this on
Windows and uploads the installer, checksum and smoke evidence as an Actions artifact.
The installer smoke mode uses a temporary directory and does not register Start-menu or
uninstall entries. It verifies the installed executable with external Tcl variables cleared,
then reinstalls and checks the fixture database hash is unchanged. It is not a substitute
for physical printer/scanner tests or a fresh Windows 11 machine.

```powershell
python -m unittest discover -v
python launcher.py --smoke-test
python tools/preview.py
```

Smoke tests use temporary databases. `AINAK_DATA_DIR` can isolate a manual test instance;
leave it unset for normal operation. Never put sample transactions in live customer data.

## Documentation

- [Operator guide](docs/OPERATOR_GUIDE.md) and [offline printable guide](docs/OPERATOR_GUIDE.html)
- [Audit, implementation decisions and UX specification](docs/BUILD_PLAN.md)
- [Release verification and remaining checks](docs/RELEASE_REVIEW.md)
- [Marketing copy](docs/MARKETING.md)

## Product boundaries

Single Windows workstation; future synchronization is not enabled. POs support full
receipt once; use direct receipts for partial shipments. Printing uses the local browser
and printer dialog. Profit estimates disclose unrecoverable legacy cost history. Cash
closings are immutable snapshots; complete all trading activity first. Store-credit
redemption is available between invoices for the same named customer. The installer is
unsigned; a signing certificate has not been provided. Review the verification report
and complete the hardware/clean-machine checklist before shop rollout.
