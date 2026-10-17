# Ainak Mahal — Phase 7 Integration Alpha

## New in Phase 7
- Refund Settlement desktop tab for creating a returned-item settlement.
- Separate completed-payout recording with explicit confirmation and unique reference.
- Refund balance lookup; both actions restricted in UI to administrator role.
- Latest refund schema initialized during launcher startup.

## Run (Windows)
1. Install Python 3.11+ with Tkinter.
2. Extract this ZIP; open Command Prompt in the extracted directory.
3. Run `python launcher.py`.
4. Create an administrator on first run.
5. Use the Refund Settlement tab only for verified real-world returns and payouts.

## IMPORTANT LIMITATIONS
- **NOT production-ready.** `app.py` still accepts user/role command-line parameters, so UI roles are NOT a secure authorization boundary. Do not rely on it for multi-user security.
- Older Returns & Reports tab creates returns without settlement; use the new Refund Settlement tab for reconciled returns. Existing un-settled returns require a future migration/reconciliation workflow.
- No cash-drawer integration or actual bank transfer. Recording a payout is a manual accounting record.
- No Windows executable or installer included; Windows compilation and printer testing are still pending.
- No automated migration from all older versions guaranteed. Make a verified backup before testing with existing data.
- Backups should be stored on another device as well as locally.
- Source is a Tkinter-based prototype; proposed PySide6 architecture has not been migrated yet.

## Test
`python -m unittest discover -p "test_*.py" -v`
