# Release review · Issue #1

Build date: 30 October 2026 (Asia/Karachi). Version: 1.0.0, unsigned review build.
Master issue: https://github.com/thearqamschools/Ainak-Mahal-Software/issues/1

## Verified locally

* 47 automated tests pass on Windows 10 x64 / CPython 3.14.8. The original 29 regression
  tests remain, with 18 new application-service integration tests.
* Source GUI smoke check constructs all 12 screens and runs first administrator creation,
  subsequent login, inventory sale, balance collection, Rx, linked lab delivery, PO receipt,
  expenses, printable invoice/Rx/job, verified backup and restore against temporary data.
  It also verifies that action buttons stay visible at the minimum 1050×700 window size;
  this caught and corrected a clipped refund-payout action during the final layout audit.
* PyInstaller 6.22.3 and Inno Setup 6.7.3 produce `AinakMahal_Setup.exe` successfully.
* Installer extracts into an isolated temporary directory, and its installed executable
  passes the same GUI/workflow smoke check with external TCL_LIBRARY/TK_LIBRARY cleared.
  Python is embedded in the frozen application; it is not launched as a separate interpreter.
* A populated SQLite sample database is preserved byte-for-byte (SHA-256) through a second
  install over the same application directory. Customer data sits outside installation files.
* Backup connections close on Windows; backups can be renamed immediately. Verified restore
  preserves a timestamped safety copy; integrity and foreign-key checks reject invalid data.
* Fault-injection tests prove that failed PO receipt and failed return settlement roll back
  inner writes, stock changes, movement rows and invoices together.
* Decimal payments, tax/discount allocation, exact-cent multi-unit refunds, returned-tax
  reversal, historical cost preservation, role checks, overpayment/over-return protection,
  credit redemption, delivery balance gates and repeat goods receipt safeguards are tested.
* HTML escaping and CSV formula protection cover untrusted customer names. Application
  data and credentials are never uploaded by the runtime.

The build scripts and CI reproduce these checks. Independent Windows CI passed at
https://github.com/thearqamschools/Ainak-Mahal-Software/actions/runs/41044885627
with installer artifact
https://github.com/thearqamschools/Ainak-Mahal-Software/actions/runs/41044885627/artifacts/12971812293
(prior to the final layout-only improvement and its additional minimum-size smoke assertion).
See the feature branch's latest GitHub Actions
run for independent CI status and downloadable installer artifacts; each artifact contains
the executable, its own SHA-256 checksum and installed-smoke JSON. A checksum from one
build must not be assumed to match another build made on a different runner.

## Data and compatibility

Legacy Tkinter entry points are retained and repaired. Their receipt form and invoice-export
name collisions and missing phase4/phase5 imports are fixed. They share the new single-instance
lock and established data directory. New UI writes go through the application-service boundary.
Existing databases receive additive tables/triggers only; no legacy rows or columns are deleted.
The pre-upgrade snapshot is preserved separately. Registry-based UUIDs leave legacy foreign
keys intact. Schema version and change journals support future work; no sync is enabled.

## Deliberate product boundaries

* One Windows workstation, branch MAIN. V1 has no cloud sync or shared-network database mode.
* Purchase orders are received in full once. Direct goods receipts handle staged shipments.
* Printing opens escaped, offline HTML in the system browser; A4 and 80 mm layouts are
  available. The preferred printer setting is a reminder for that print dialog, not an OS
  printer-default change. No printer driver or browser component is installed.
* New sales and returns retain historical cost values. Legacy transactions lacking those
  snapshots use available catalog costs; their profit reports remain clearly marked estimates.
* Closing is an immutable daily count snapshot. Run it after trading; later transactions
  do not silently alter the snapshot. V1 has no statutory accounting or tax-filing integration.
* Data is protected by normal Windows account permissions, PBKDF2 password hashes and
  application roles. SQLite backups are not encrypted; protect the backup medium.
* If the live database is corrupt enough that administrator authentication cannot run,
  recovery stops and preserves it for technician-led recovery. It does not bypass login.

## Remaining rollout checks

- [ ] Install normally on a fresh Windows 10/11 x64 machine with no developer tools or Python.
- [ ] Confirm normal Start-menu shortcuts, uninstall registration and upgrade under a standard
  Windows user. Local smoke mode deliberately skips shell/registry registration.
- [ ] Print real A4 and 80 mm receipts, Rx and job slips on the shop's printers.
- [ ] Test the real scanner's keyboard/Enter suffix, Windows display scaling and screen reader.
- [ ] Review rendered screens visually with the store operator. The Computer Use helper could
  not enumerate the preview launched inside this execution session; screenshot-based visual
  inspection is not claimed. Automated Tk screen construction and workflow checks did pass.
- [ ] Add a trusted Windows code-signing certificate if a signed distribution is required.
- [ ] Run a representative test day on copied data, reconcile it and obtain shop-owner sign-off.

This is a tested implementation for final review. Physical hardware, a pristine Windows 11
environment, accessibility tooling and operator sign-off are not represented as verified.
