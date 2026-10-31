# Ainak Mahal Desktop ERP 2.0

Original branding and a native Qt Widgets interface for an offline optical shop in
Millat Chowk, Faisalabad. No web application, cloud account, subscription or hosting.
The Windows installer includes the runtime; users do not need Python or internet.

## Run or install

Install `AinakMahal_Setup.exe` and open Ainak Mahal from Start. Create a first administrator;
there is no default password. For source development use CPython 3.14 x64, install
`requirements-build.txt`, then `python launcher.py` (or `python qt_launcher.py`).
`python launcher.py --legacy` retains the earlier Tkinter UI for diagnostic/regression use.
Do not use old UI builds for trading against the new supplier ledger.

Data remains `%USERPROFILE%\AinakMahal\ainak_mahal.db`, outside installation files.
Schema 2 preserves legacy tables, rows and identifiers and takes a pre-upgrade snapshot.
No production database is shipped in the repository or installer. Use AINAK_DATA_DIR only
for isolated manual tests. A local instance lock protects application/recovery exclusivity.

## Workflows

The sidebar covers live dashboard, integrated customer/Rx/cart/payment/optical-job checkout,
customer profiles/history, printable prescriptions, frame/lens/contact-lens inventory,
Code 128 labels, optical jobs/repairs with charges, supplier PO/receipt/payment ledger,
customer dues/returns/store credit, cash/expenses/closing, reports/PDF/CSV, staff/audit and
verified backup/recovery. F2 checkout, F3 customers, Ctrl+K search, Ctrl+Enter save order.
Original navy/teal eyeglasses identity is included as SVG, PNG and multi-size ICO.

## Build and verify on Windows

Install CPython 3.14 x64 with Tcl/Tk (retained for recovery) and Inno Setup 6:

```powershell
python -m venv .venv
./tools/build.ps1 -Python ./.venv/Scripts/python.exe
./tools/installer-smoke.ps1
```

The script installs exact runtime/build pins, runs all unit/integration/Qt tests, runs the
sample GUI smoke workflow, freezes a dynamic onedir application, collects license notices,
and compiles `output/AinakMahal_Setup.exe`. CI repeats build/install/upgrade checks on Windows
and uploads installer, checksum and smoke evidence. Installed smoke clears external Tcl
variables, runs embedded-runtime workflows and checks the populated database hash through
reinstallation. It is not a physical printer/scanner or pristine Windows 11 certification.

```powershell
python -m unittest discover -v
python qt_launcher.py --smoke-test
```

Set AINAK_SCREENSHOTS to a test output folder to capture real rendered Qt screens during
smoke. All sample data is disposable. Never run manual sample sales against the live shop.
Brand generation alone uses development tools Pillow 12.0.0 and resvg-py 0.5.0; reference
video decoding used imageio-ffmpeg 0.6.0. None is a runtime dependency.

## Review documentation

- [Operator guide](docs/OPERATOR_GUIDE.md) / [offline printable HTML](docs/OPERATOR_GUIDE.html)
- [Reference evidence and gap analysis](docs/ERP2_REFERENCE_REVIEW.md)
- [Original logo and complete design system](docs/DESIGN_SYSTEM_2.md)
- [Feature checklist and verification](docs/ERP2_RELEASE_REVIEW.md)
- [Dependency licenses and replacement/source instructions](docs/THIRD_PARTY_ERP2.md)
- [Original foundation audit](docs/BUILD_PLAN.md)

## Deliberate boundaries

Single workstation/branch MAIN; no cloud sync, Google login, mobile app, subscription or
remote messaging. POs receive in full once; use direct receipts for partial shipments.
Legacy supplier receipts are unverified until an administrator confirms their opening
balance. Closing is an immutable daily count snapshot rather than a shift lock. Legacy
profit costs without historical snapshots remain estimates. Printing uses Qt's local
Windows/PDF engine. Installer is unsigned without a supplied trusted signing certificate.
Complete hardware, accessibility and shop-operator acceptance before daily trading.
