# Ainak Mahal — Phase 3 development alpha

Run `python app.py` on Windows with Python 3.11+ (Tkinter included). Database is stored in `~/AinakMahal/ainak_mahal.db`. Before updating an existing installation, make a verified backup.

## New features
- Purchase order creation and receiving, with one-time receiving enforcement.
- Optical job state transitions (Pending -> In Lab -> Ready -> Delivered; cancellation allowed from Pending/In Lab).
- Printable invoice export as HTML, opened in browser for printing or Save as PDF.
- User authentication functions with PBKDF2 password hashes, admin/cashier role records, and audit log foundation.

## Limitations
- Authentication is backend-only: no login dialog or role-based access restriction yet. Do not use for live sensitive records.
- No PDF renderer included; use browser Print -> Save as PDF.
- No customer returns, supplier balances, tax compliance, multi-device sync, or migration tooling yet.
- Tkinter UI remains basic; planned PySide6 redesign has not been implemented.
- Test on a copy of shop data. Backups should be stored off-device as well.

Run tests: `python -m unittest discover -v`.
