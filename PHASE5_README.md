# Ainak Mahal Phase 5 — Accounting hardening preview

This package builds on Phase 4. It adds `phase5.py` and `test_phase5.py` with transactional return settlement recording and invoice balance reconciliation.

## Run
Install Python 3.11+, then run `python launcher.py` from this folder. Run tests with `python -m unittest discover -v`.

## New service API
`phase5.init(store.db)` creates the additional table. `phase5.return_and_settle(...)` records the return, inventory movement, and a refund allocation in one SQLite transaction. `phase5.invoice_position(store, sale_id)` calculates the post-return balance.

## Critical limitations
- The existing GUI does NOT yet expose the new settlement service. The Phase 4 login launcher still passes a role on the command line to an independently runnable `app.py`; this is NOT a secure authorization boundary. Do not use it to protect real customer data or cash.
- `payout_due` records a proposed cash/bank refund; it does not execute or confirm an actual payout. `credit_adjustment` is a calculated adjustment, not a redeemable store credit ledger.
- Phase 4 returns created without settlement entries remain outside this new settlement workflow; migration/reconciliation is needed before production.
- There is no completed double-entry ledger, tax compliance review, stock costing methodology, thermal printer integration, or signed Windows installer.
- Existing SQLite schema uses REAL amounts; production accounting should migrate to integer minor units.
- Test on a COPY of the database. Back up first. Never replace your live shop database with sample/test data.
- PyInstaller batch file is a build helper, not a compiled installer; builds should be executed and validated on Windows.

## Next development priorities
1. Enforce permissions in a single application service layer and prevent direct UI bypass.
2. Complete refund disbursement ledger and receipt printing.
3. Integrate new services into the GUI, test real printer models and Windows packaging.
4. Implement schema migrations, recoverable backups, and end-to-end acceptance tests.
