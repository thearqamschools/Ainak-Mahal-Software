# Ainak Mahal ERP 2.0 · Release review

Review date: 31 October 2026, Asia/Karachi. This is the original Qt desktop redesign on
branch `feature/erp-2-redesign`, built on the prior Issue #1 foundation. No production
customer database was opened, overwritten or distributed during development.

## Feature checklist

- [x] Reference review: 15 supplied screenshots and both promotional-video visual timelines;
  observed screens, marketing claims and implementation assumptions distinguished.
- [x] Three original vector logo concepts evaluated; Clear Bridge selected. Light/dark
  lockups, standalone symbols, PNG exports and nine-size Windows ICO included.
- [x] Navy/royal-blue/teal design system with typography, spacing, interactive states,
  table/form/navigation/empty/error/accessibility guidelines.
- [x] Native Qt Widgets shell, original local assets, first-run onboarding and secure login.
- [x] Dashboard with real daily metrics, seven-day invoice trend, jobs, recent sales and shortcuts.
- [x] Atomic customer + existing/new Rx + multi-line POS + payment + optional optical job.
- [x] Customer contact editing, optional profile details, ID/name/mobile search and history tabs.
- [x] OD/OS SPH/CYL/AXIS/ADD, PD, date, notes, validation, historical and printable records.
- [x] Frames/lenses/contact lenses/sunglasses/accessories/services, variants, barcodes, powers,
  stock movements, guarded adjustments, lens matrix and Code 128 label rendering.
- [x] New-glasses/lens-replacement/frame-repair/general-repair workflows, instructions,
  due dates, fulfillment, optional lab/supplier link, charges/advance and delivery balance gate.
- [x] Supplier/PO/multi-line receipt history and purchase-linked payment ledger. Overpayment
  and duplicate references blocked; supplier cash payments included in expected drawer cash.
- [x] Legacy supplier openings marked unverified, requiring audited statement confirmation
  instead of inventing debts or cash outflows.
- [x] Collections, customer dues, refunds/payouts, store-credit redemption, expenses,
  cash movements and immutable daily count snapshots.
- [x] Sales/collections/dues/stock/valuation/low-stock/purchases/supplier balances/payments/
  expenses/closing/profit reports, date filters, CSV export, native print and PDF output.
- [x] Staff roles/account activation, audit trail, verified backups and authenticated recovery.
- [x] Additive schema 2 with pre-upgrade snapshot; legacy IDs, rows and storage path preserved.
- [x] Offline runtime, no web view/server/cloud account, no subscription, no runtime telemetry.
- [x] Updated operator/installation/design/reference/dependency documents and retained legacy UI.

## Evidence and quality gates

The automated suite has **65 passing tests**: 47 prior regression tests, 12 ERP integration
cases and 6 Qt interaction cases. Tests cover whole-order rollback, customer/Rx ownership,
repair invoicing/tax/delivery, supplier opening reconciliation and payment caps, cash effects,
profile validation, schema upgrade/reopen compatibility, barcode key input, checkout, cart
removal, draft preservation during navigation, form-validation state, numeric sorting/row
identity, all-module navigation, role-disabled navigation and local barcode rendering.

Source smoke additionally exercises the first administrator through the actual login button,
all 12 pages, Windows-size layouts, a full optical order, a charged repair, multi-line receipt,
supplier payment, cash, reconciliation, native PDF output, backup and restore. It renders
13 real application screenshots at 1440×920 and tests navigation at 1080×720. These are Qt
widget renders of the real application with disposable sample data, not static mockups.
All page captures were visually reviewed; ampersand/mnemonic rendering and a tall checkout
layout were corrected. Screenshot assets are delivered separately from the source repository.

Build gate: pinned PyInstaller and Inno Setup compile the x64 installer. A development-PATH
collision was diagnosed: Poppler's version-suffixed ICU DLL had been captured instead of
the Windows ICU API required by Qt. The build now sanitizes its resolver PATH and validates
packaged ICU exports before compiling. A failed early installer is not a release artifact.
Final installed-app smoke/checksum evidence is supplied beside the installer and in Windows CI.

Installer smoke installs to an isolated folder, runs the embedded executable with external
Tcl settings cleared, performs sample workflows, reinstalls and verifies that a populated
SQLite fixture's SHA-256 is unchanged. This is separate from the schema-1-to-2 migration
integration test. Normal Start-menu/uninstall registration is intentionally skipped by the
isolated smoke mode. Clean-machine hardware acceptance remains below.

## Known boundaries and rollout checks

- One workstation, branch MAIN. No cloud synchronization, Google login, mobile app,
  automatic WhatsApp, remote AI/support or multi-branch invitations are added.
- POs receive fully once; staged shipments use direct receipts. Outsourced jobs record
  their supplier but do not silently create a purchase liability.
- Daily closing is a count snapshot, not a shift lock. Complete trading before counting;
  subsequent transactions do not rewrite it. No statutory accounting/tax filing integration.
- Old sale costs without snapshots remain profit estimates. Supplier debt is incomplete
  until unverified legacy openings are confirmed against statements.
- Mathematical optical conversions are not prescribing/diagnostic recommendations.
- Backups are local and unencrypted; protect their storage. Corrupt-live-database recovery
  stops if administrator authentication cannot be established, preserving data for a technician.
- The installer is unsigned: no signing certificate was supplied. No claim of pristine Windows
  11 certification, real printer/scanner acceptance, screen-reader testing or operator sign-off.
- Before shop rollout: install under a standard user on a clean Windows 10/11 x64 machine
  without Python; verify normal shortcuts/uninstall, A4/80mm printing, label scanning,
  100/125/150% display scaling, keyboard/screen-reader behavior, a representative copied-data
  trading day, reconciliation and restore. Retain an off-device verified backup.

All source changes are reviewable; no history rewrite or automatic merge is required.
