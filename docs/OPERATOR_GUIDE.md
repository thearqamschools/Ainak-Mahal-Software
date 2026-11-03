# Ainak Mahal operator guide

## Install and first run

Run `AinakMahal_Setup.exe` on Windows 10/11 x64. Installation is per user and needs no
Python, internet, hosting or subscription. Open Ainak Mahal from the Start menu.
Create the first administrator with a unique username and a password of at least 10
characters; repeat the password. There is no default password. Keep credentials securely.
Subsequent launches show Sign in. Administrators add cashier accounts under Settings & team.

Data remains in `%USERPROFILE%\AinakMahal\ainak_mahal.db`, outside the application folder.
An upgrade automatically takes `ainak_mahal_before_v1.db` before additive schema migration.
Close the application before running an upgrade. Uninstalling the program does not remove data.
Do not install a second copy for simultaneous use: a local instance lock protects the database.

## Set up the shop

Settings & team → Edit shop settings: confirm shop name, address, mobile, receipt format
(A4 or 80 mm), preferred local printer and backup folder. Tax is 0% unless configured.
The preferred printer is a reminder; choose that printer in the local print dialog.
Add staff accounts with cashier access; administrators control purchasing, stock changes,
returns/refund payouts, expenses/cash closing, backups and team settings.

## Customers and prescriptions

Add a customer with their name and mobile. Search either field. Select a profile to edit
contact details or view all prior transactions and prescriptions. Existing prescriptions
are preserved as history; add a new dated prescription rather than replacing a clinical record.

Prescriptions → Add prescription: choose the customer, date, right (OD) and left (OS)
SPH/CYL/AXIS/ADD and PD. Powers use quarter-dioptre steps. Enter an axis if cylinder is
nonzero; axis 0–180; SPH −30 to +30; CYL −15 to +15; ADD 0–6; PD 20–80 mm in half-mm steps.
These limits validate input, not clinical suitability. Leave unmeasured values blank.
Select Print selected Rx to open a self-contained printable document.

## Catalog and inventory

Inventory → Add catalog item: enter unique SKU, name, category, selling price, unit cost,
opening quantity and optional barcode/variant. Lens powers populate the lens matrix.
Service items (fitting, repairs, etc.) do not consume stock. The low stock threshold defaults
to two units. Opening stock creates an auditable movement. Select an item → Adjust selected
stock to record loss/count corrections; a reason is mandatory and negative stock is blocked.
View movements to investigate changes. Do not change quantities directly in SQLite.

## Checkout

Press F2. Scan a barcode or search a name/SKU, select the product, enter quantity and press
Enter/Add item. Repeat for frame, lenses and services. The cart keeps running totals. Remove
selected line corrects an unsaved cart. Select a customer for any unpaid balance; a fully
paid sale may use Walk-in. Set invoice discount in PKR, amount received and Cash/Bank/Card.
The amount received is money retained, so exclude change given. Review total/tax/balance.
Ctrl+Enter saves stock, invoice and payment in one transaction. Choose Print when prompted.

A saved invoice is immutable. Correct mistakes using a return rather than editing history.
Payments & returns → select an invoice → Receive payment to collect its balance. Reprint
at any time. Printed invoices include gross total, returns and adjusted balance; use the
adjusted balance after returns. Invoices and Rx/job documents are saved under `documents`
inside the data folder. The local browser's print dialog controls the printer and paper.

## Optical lab

Optical jobs → Create job: choose the customer, write clear lab instructions and promised
date, optionally link the invoice and Rx numbers. Links must belong to that customer.
Print a job slip. Select Update status: Pending → In Lab → Ready → Delivered. Pending/In Lab
may be cancelled. Delivery is blocked until the linked invoice balance is paid. Cancelling
a lab job does not cancel its sale; handle any financial correction separately.

## Suppliers and purchasing

Add supplier, then Create purchase order. Choose products and add multiple quantities/unit
costs. Review lines before saving. Once all goods arrive, select Receive selected PO;
this posts stock, costs and receipt atomically, and cannot be repeated. For partial deliveries,
use Receive without PO for actual goods delivered and keep the supplier paperwork; V1 POs
support full receipt only. Do not also receive the same shipment through the PO.

## Returns and completed refund payouts

Administrator: Payments & returns → select sale → Return selected sale. Select the sold
product, quantity, reason and settlement method. Returns cannot exceed sold units. Stock
is restored for physical items. Discounts/taxes are allocated to units so all returned units
sum to the exact invoice value. Cash/Bank settlements first allocate already-received money
to refund payable; remaining return value offsets the unpaid balance.

Returning goods does not pay the customer. After actually paying cash/bank, select the refund
settlement → Record completed refund payout. Enter amount and unique receipt/reference,
and confirm it was paid. Partial payouts are supported; overpayment and duplicate references
are blocked. Credit method records store credit/adjustment; negative customer balances are
liabilities. Select an invoice with a negative balance, choose Apply store credit, and enter the
destination invoice number and amount. Both invoices must belong to the same named
customer. Redemption is atomic and blocks spending more than available credit or balance. Existing legacy returns remain visible in reports.

## Cash, expenses and reporting

Cash & expenses records opening float, cash added/removed, and cash-paid expenses. Expected
cash = cash collections + opening/in − out − cash expenses − completed cash refunds.
Bank/card collections do not affect the drawer. Close day saves counted cash, expected cash,
variance, notes and staff as an immutable snapshot. Run this after all trading activity;
later transactions do not rewrite a closing. Include any later correction in a documented
next-day movement and check current reports. Only one closing is allowed per calendar day.

Reports include Sales, Stock, Customer dues, Expenses, Cash closing and estimated Profit.
Date ranges apply to dated activity; stock and dues are current positions. Profit excludes
invoice tax and cash expenses, using saved sale-time costs for new invoices. Legacy sale
costs and returned-goods recovery costs use available catalog costs, so estimates can change;
do not use this operational estimate as a statutory accounting ledger. CSV export protects
customer-entered text from spreadsheet formula execution.

## Back up and recover

Administrator: Backup & recovery → Create verified backup uses the configured destination;
Save backup as lets you select a USB/external location. Every backup uses SQLite's online
backup API and an integrity check. Keep daily rotated copies on another drive. Customer
data and password hashes are sensitive; protect the drive. No backup is uploaded anywhere.

Close Ainak Mahal. Open **Ainak Mahal Recovery** in Start. Enter current administrator
credentials, choose a backup, confirm restore. Recovery refuses to run beside an open shop
application. It verifies the database and preserves a timestamped copy before replacement.
Reopen, sign in, then Check stock & payments. Do not overwrite data files manually.
If the current database is physically corrupt, automated authenticated recovery stops;
preserve it and contact your technician for isolated repair/recovery rather than deleting it.

## Sample-data acceptance procedure

Use a separate Windows test account, or developer environment `AINAK_DATA_DIR` pointing to
an empty test directory. Never enter sample transactions into a real customer database.
Create admin, customer, frame (5 units, price 1500), lens and service; sell a frame/lens with
partial payment; print invoice/Rx/job; receive the balance; deliver job; receive a multi-line
PO once; record a return and actual partial payout; record expense/opening float and close
day. Export reports, check reconciliation, back up, close, restore and verify all counts.
Test real A4/80 mm printer output, scanner Enter suffix, keyboard navigation and Windows
display scaling before daily use. `AinakMahal.exe --smoke-test` runs an isolated automated
sample without touching the live data folder.

## Version 1.1: finding records and managing access

Press **Ctrl+K** anywhere in the main desktop to search customer names/mobile numbers,
product names/SKUs/barcodes, lab instructions or an invoice number (`#123` also works).
Select a result and press Enter to open its page and select that record. Escape closes
search. Results are limited to 12; refine broad searches. All searching stays offline.
Click table headings to sort; click again to reverse. Empty tables explain the next step.

Inventory supports combined category, stock and text filters. Low stock means quantity
at or below its reorder level; service items are excluded. Optical jobs supports status,
overdue, and customer/instruction filtering. Overdue means an unfinished job whose promised
date is before today. Dashboard's counter selector switches jobs, recent invoices and low stock.

Checkout keeps Save sale and Clear cart visible at the bottom of its summary. On smaller
windows, scroll the payment panel; Tab also reveals its inputs. Scan/search, Enter adds an
item, Ctrl+Enter saves the sale. Enter only the amount retained, excluding cash change.

Reports now also includes Collections (receipts before refund payouts), Purchases (goods
receipts within the date range), Low stock and Stock valuation. Stock and valuation are
current positions, not historical snapshots; valuation uses current unit cost, excludes
services and is not a statutory accounting report. All can be exported as CSV.

Sign-in supports Show password for both new-password fields, Enter submission and normal
Tab navigation. There is no default or universal recovery password. Use at least ten
characters and store credentials safely. **Ctrl+Shift+P** changes the signed-in user's
password after confirming their current password. Administrators can also use Settings
& team → Change my password or select a staff account → Reset staff password. Resetting
requires the administrator's current password, is audited, and does not reactivate a
disabled account. Passwords are stored as salted PBKDF2 hashes, never in the audit log.

If you cannot sign in, ask another active administrator to reset your account. If no
administrator can authenticate, keep the database and backups intact and arrange
technician-assisted recovery. The sign-in help does not bypass authentication and the
Recovery tool still requires current administrator credentials. Never delete shop data
merely to recover access. Normal installation/upgrades leave the data directory intact.
