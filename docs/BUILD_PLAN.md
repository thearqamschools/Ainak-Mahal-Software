# Issue #1 baseline and implementation decisions

Master specification: https://github.com/thearqamschools/Ainak-Mahal-Software/issues/1

## Baseline audit

The original standard-library Tkinter application has 29 passing tests. Reuse `core.py`
for inventory, stock movements, database backups and purchasing; retain phase 3–6
authentication, PO lifecycle, guarded returns, refund allocation and payout recording.
`app.py` already imports phase6, so retain that fix and the direct-launch auth regressions.
`deployment_tools.py` already explicitly closes backup validation handles.

Concrete gaps found: ID-only checkout, no dashboard, no Rx validation/ADD, no delivery
payment gate, no cash closing or expenses UI, mutable cost basis in reports, unversioned
schema, missing identities on legacy tables, and no install smoke check. Legacy receipt
form variables were overwritten by the Rx form and the invoice exporter was shadowed.
Nested SQLite contexts committed inner purchases/returns before outer operations finished.

## Ordered implementation

1. Preserve legacy launcher and UI; fix both form/export regressions and add nested savepoints.
2. Introduce additive schema version 1, automatic pre-upgrade backup, identity registry,
   timestamps, branch identity and SQL change journal triggers. Keep all original IDs/tables.
3. Add an application-service boundary for role checks, validated optical workflows,
   snapshot costs, exact-cent checkout/returns, purchasing, cash, reports and printing.
4. Build a native Tkinter sidebar shell, search-first tables, keyboard POS and concise forms.
5. Test migrations, rollback injection, money/stock consistency, backup/restore and screen creation.
6. Package one offline executable directory and an Inno Setup installer; install into a
   temporary test location, run its bundled smoke check, verify upgrade/data preservation.
7. Publish the feature branch and reviewable PR, CI installer and operator documentation.

## Architecture and defaults

Tkinter is retained for proven compatibility, small footprint and zero runtime dependencies.
The old `legacy_launcher.py` and `app.py` remain for support, not as the recommended entry.
`desktop.py` owns presentation; `retail.py` owns application orchestration, authorization and
read models; `core.py`/phase services own transaction-safe persistence; migrations and
printing/recovery are independent. UI SQL is read-only through the service read-model API.

PKR; tax defaults to zero, optional percentage; discount is an invoice amount. Bank/card
record collections without affecting cash drawer. Services have no physical stock. Full
PO receipt is atomic and allowed once; use direct goods receipt for staged deliveries.
Customer identity is required for credit. Delivery requires zero outstanding invoice balance.
Current user profile's `~/AinakMahal/ainak_mahal.db` stays unchanged from previous releases.
No cloud connection, background network request, subscription or runtime telemetry.

## Design specification and external skill verification

The available skill catalog contains no Taste, Emil Kowalski Motion or Impeccable package.
No canonical source/version/license was supplied. No external code or skill was installed.
The issue expressly permits direct application of the principles, which this implementation uses:

* Taste: light neutral canvas, deep navy navigation, Segoe UI, restrained white metric cards,
  consistent 8–24 px spacing, a single primary action per workflow, clear empty states.
* Motion: immediate native pressed/hover/focus feedback, brief login retry delay, no
  decorative transitions, no animation dependency or delay in checkout. Native Windows
  widgets respect system interaction conventions and avoid motion sensitivity concerns.
* Impeccable: audit minimum 1050×700 and standard 1280×850 layouts, scroll long dialogs and
  wide tables, explicit OD/OS labels, keyboard focus, visible errors, accessible contrast,
  plain-English confirmations for completed money movements, consistent PKR labels.

F2 opens checkout; F3 customers; Enter adds a selected/scanned product; Ctrl+Enter saves
checkout; dialog Ctrl+Enter saves, Escape cancels. Barcode scanners act as keyboard input.
Printing uses self-contained escaped HTML and the local browser's printer dialog. No CDN.
Marketing copy is documentation only and has no runtime SEO dependency.

## Review boundaries

Single workstation, single branch MAIN; UUID registry/outbox is a future sync boundary,
not a synchronization protocol. Legacy historical unit costs cannot be reconstructed;
profit labels disclose estimates. Test actual shop printer and scanner before rollout.
No invented clean-machine, hardware or signing verification: see release verification report.
