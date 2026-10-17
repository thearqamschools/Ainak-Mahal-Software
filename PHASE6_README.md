# Ainak Mahal — Phase 6 Accounting Alpha

This release adds an **auditable refund payout recording backend**, not an integrated cashier GUI or an actual bank transfer system.

## Run

Python 3.11+; `python launcher.py` for the existing desktop alpha. To run tests: `python -m unittest discover -v`.

## Integration

Call `phase6.init(store.db)` on application initialization, and `phase6.record_payout(...)` only after a real cash/bank refund has been verified. The Phase 6 service is **not wired into the UI**. Never enter fake payout confirmations.

## Outstanding production blockers

- Launcher authentication can be bypassed; roles are supplied by caller and not validated against a server-side session.
- Existing `sales.paid` aggregates and Phase 5 credit adjustment are not a full general ledger.
- Full purchase-to-return integration and database migrations remain incomplete.
- GUI integration, Windows .exe compilation, recovery drill, printer testing, and acceptance tests on Windows are pending.
- Back up existing database before trying this release; do not use with real customer data yet.
