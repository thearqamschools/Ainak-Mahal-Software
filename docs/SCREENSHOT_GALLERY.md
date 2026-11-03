# Actual desktop screenshot gallery

Captured from running Tkinter windows on Linux, with temporary synthetic shop data and scalable Helvetica fallback. No real customer database was opened. These are functional application windows, not web mockups or generated illustrations. Windows CI is configured to capture the same gallery with native Segoe UI; its outputs are separate evidence only after that workflow passes.

Reproduce from the checkout with a display and development-only Pillow: `python tools/capture_gallery.py`. Use `--output PATH` to write elsewhere. The source application's normal runtime does not require Pillow.

| Window | Screenshot |
| --- | --- |
| First-run setup | [PNG](screenshots/01-first-run.png) |
| Returning sign-in | [PNG](screenshots/02-sign-in.png) |
| Overview | [PNG](screenshots/03-overview.png) |
| Checkout | [PNG](screenshots/04-checkout.png) |
| Customers | [PNG](screenshots/05-customers.png) |
| Prescriptions | [PNG](screenshots/06-prescriptions.png) |
| Inventory | [PNG](screenshots/07-inventory.png) |
| Optical jobs | [PNG](screenshots/08-optical-jobs.png) |
| Purchasing | [PNG](screenshots/09-purchasing.png) |
| Payments and returns | [PNG](screenshots/10-payments-returns.png) |
| Cash and expenses | [PNG](screenshots/11-cash-expenses.png) |
| Reports | [PNG](screenshots/12-reports.png) |
| Settings and team | [PNG](screenshots/13-settings-team.png) |
| Backup and recovery | [PNG](screenshots/14-backup-recovery.png) |
| Global search | [PNG](screenshots/15-global-search.png) |
| Supplier history | [PNG](screenshots/16-supplier-history.png) |
| Customer history | [PNG](screenshots/17-customer-history.png) |

[Original setup](screenshots/baseline/setup.png) and [original overview](screenshots/baseline/overview.png) preserve the PR #2 baseline, including its original Linux font fallback behavior. Visual checks at 1280×850 and automated action-visibility checks at 1050×700 do not establish screen-reader, Windows scaling, printer or operator approval.
