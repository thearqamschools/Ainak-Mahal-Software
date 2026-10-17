# Ainak Mahal — Phase 2 working alpha

Windows offline optical store desktop software. No hosting or subscription required. **Not production-ready.**

## Run
1. Install Python 3.11+ for Windows, including Tkinter.
2. Open Command Prompt in this folder.
3. Run `python app.py`.
4. Data is saved at `%USERPROFILE%\AinakMahal\ainak_mahal.db`.
5. Run tests: `python -m unittest -v test_core.py`.

## Implemented
Customer and product entry, prescription entry, multi-item cart and atomic checkout, payment receipts, supplier stock receiving, optical job entry, verified SQLite backup, branch-aware stock movement records and future sync outbox. Works offline.

## Limitations / before live use
This is an **alpha**. There is no login/access control, invoice printing, refund workflow, sales discount/tax, purchase-order approvals, lab job status editing, stock count adjustments, or full accounting reports. UI is functional but basic. Avoid real customer data until security and backup restore testing are completed. Backups should be stored off the PC as well. Legacy prototype database is **not automatically migrated**; do not overwrite old data. Currency uses PKR. Future sync is a schema placeholder, not a working service.
