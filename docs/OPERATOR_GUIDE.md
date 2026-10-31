# Ainak Mahal Desktop ERP 2.0 · Operator guide

## Install and open

Run `AinakMahal_Setup.exe` on Windows 10/11 x64. The application installs for the current
Windows user and includes its own Python/Qt runtime. No internet, hosting or subscription
is needed after installation. Open Ainak Mahal from Start or the desktop shortcut.
First launch creates an administrator: choose a username and a password of at least 10
characters, then confirm it. No default or shared password is provided. Later launches
show Sign in. Show password changes visibility only; it does not save a password elsewhere.

The new eyeglasses mark and navy/blue/teal interface identify version 2.0. The left sidebar
opens every module. F2 opens checkout, F3 customers, Ctrl+K workspace search. Tables sort
by column headers, select full rows and scroll horizontally when needed. Small windows
scroll the page instead of hiding lower actions. The minimum window is 1080×720 logical px.

## Upgrade without losing data

Business data remains `%USERPROFILE%\AinakMahal\ainak_mahal.db`, separate from installation
files. Close Ainak Mahal before upgrading. Existing rows, integer IDs and foreign keys are
retained. Schema 2 adds related tables rather than replacing existing records. Before the
upgrade, the application saves `ainak_mahal_before_v2.db`. Keep a separate verified backup
as well. Never delete a database to solve a login or migration error. Uninstalling the app
does not delete business data. Downgrading to an old release is not supported; retained
legacy UI code is for support and regression work, not for trading against schema 2 data.

## Shop setup and staff

Settings & Staff → Edit shop settings: confirm name, Faisalabad address, contact number,
optional tax percentage, receipt format, printer and backup folder. Tax defaults to zero.
Choose the real local printer in the Print dialog; a saved preferred name is a convenience,
not a Windows system-default change. Add individual cashier accounts; administrators manage
purchases, supplier payments, stock changes, returns/refunds, cash closing, backups and team.
Disable former staff accounts; you cannot disable your own account. Audit history records
sensitive actions. Cashier navigation disables administrator-only modules. Windows account
permissions protect the local database; protect the PC and backup drive.

## Dashboard and workspace search

Dashboard shows gross invoice sales today, collections, balances due, low-stock counts and
pending/ready jobs. Its seven-day line uses real invoice totals. Use the Sales/Profit reports
for returns and profitability. Shortcuts open checkout, customer entry, repairs or jobs.
Global search accepts customer name/mobile/ID, product/SKU/barcode, invoice or job details.
Customer results open a profile; other result types open the relevant workspace.

## Customers and history

Customers → Add customer. Name is required; mobile, address, WhatsApp, referring doctor,
gender and birth date are optional. Do not collect unnecessary personal details. Date of
birth cannot be in the future. Search name/mobile/customer number; select Open profile or
double-click to view invoices and balances, prescription history and optical jobs. Contact
edits leave historical transactions intact. Customer export is CSV and works offline.

## Prescriptions

Prescriptions → Add prescription. Choose the customer and date. The grid labels OD/right
and OS/left, each with SPH, CYL, AXIS and ADD. Enter PD in mm and notes as needed. Leave
unmeasured values blank; do not enter zero to mean unknown. Powers are quarter-dioptre
steps, AXIS 0–180, SPH −30..30, CYL −15..15, ADD 0..6, PD 20..80 in half-mm steps. A nonzero
cylinder needs an axis. These checks validate entry, not clinical suitability. Save a new
prescription rather than editing a historic clinical record. Print/PDF selected prescription
opens an offline preview and the native Windows printer or PDF-save dialog.

Optical calculators provide notation transposition and spherical equivalent only. They
are mathematical tools and do not replace measurements or professional dispensing judgement.

## One connected optical order

1. Press F2. Select an existing customer, or enter a new customer's name and mobile. Fully
   paid counter sales may use Walk-in; unpaid balances, Rx and jobs require a named customer.
2. Choose that customer's existing Rx, or Enter new prescription for this order. Do not
   choose both. A new Rx is pending until the complete order succeeds.
3. Search/scan frame, lenses, contact lenses, accessories or services. Enter units and Add
   to order, or press Enter on the scanner field. Scanners must act as keyboard devices
   with an Enter suffix. Repeat for additional products or pairs. Remove selected line
   corrects an unsaved cart. Right/left lenses are separate catalog lines when powers differ.
4. Enter invoice discount in PKR, amount actually retained after giving change, and Cash,
   Bank or Card. Configured tax is calculated after discount. Review total and balance.
5. If lab work is needed, tick Create a linked optical job, select type, instructions,
   promised date (YYYY-MM-DD) and collection/delivery. Delivery here records the fulfillment
   method; the application does not book a courier.
6. Ctrl+Enter or Save optical order commits customer/Rx/sale/payment/job/stock together.
   Any failure rolls back the whole order, preserving the draft for correction. Receipt
   preview can print or save PDF. Navigation preserves the unsaved checkout context.

Saved invoices cannot be edited. Correct a completed transaction with a guarded return.
The invoice shows subtotal, discount, tax, recorded payments and adjusted balance after
returns. Invoice, Rx and job HTML are saved under the data folder's `documents` directory.
PDF uses Qt's local printer engine; no browser or web service is required by the new UI.

## Inventory and product labels

Add unique SKU/name, category, cost, selling price, opening units and reorder threshold.
Categories include frames, lenses, contact lenses, sunglasses, accessories and services.
Optional barcode, variant, lens SPH and CYL improve stock lookup. Service items do not
consume stock. Opening stock and every adjustment create a traceable movement. Select
Edit item for price/contact-label changes; historical sale costs remain saved. Adjust stock
requires an administrator and a reason, and cannot make stock negative. Stock history
explains each change. Lens matrix groups optical lens/contact-lens powers and variants.
Print label renders a local Code 128 from the assigned ASCII barcode or SKU. Test label
size, printer resolution and scan readability with real hardware before shop rollout.

## Optical jobs and repairs

New optical job / repair supports New glasses, Lens replacement, Frame repair and General
repair, plus instructions, promised date, optional Rx/invoice, fulfillment and outsourcing
supplier. For an existing invoice, charges/payments belong on that sale. For a new charged
repair, enter subtotal charges and advance; configured tax applies and a repair invoice is
created atomically. Repairs use a service line and do not deduct physical stock. Add real
replacement parts through normal POS if stock needs to be deducted.

Statuses: Pending → In Lab → Ready → Delivered. Pending or In Lab may be cancelled.
Delivering a linked job is blocked until its invoice balance is cleared. Receive job payment
opens the normal payment service. Cancellation changes the job only; handle financial
returns separately. Printed job receipts include type, fulfillment, instructions, charges,
received payment and outstanding balance. Outsourcing records the lab/supplier link; it
does not silently create a purchase or supplier debt.

## Purchasing and supplier balances

Add supplier, then New purchase order. Add multiple products, quantities and unit costs;
review before saving. Receive selected PO only once all listed goods arrive. Receipt posts
stock/costs and purchase history atomically. For partial shipments use Receive without PO
for actual goods, and avoid receiving the same units again via the PO. PO partial receipt
is not part of this release.

Receipts & payments shows total, paid, due and opening status. New receipts start with a
verified unpaid balance. Record supplier payment only after paying, with positive amount,
method and unique reference. The service blocks overpayment and duplicate references.
Cash supplier payments reduce the expected cash drawer; bank/card payments do not.

Legacy receipts have **Opening unverified**, rather than invented debts. Reconcile with
supplier statements and choose Confirm legacy opening; enter the verified unpaid amount.
The remainder becomes a historical opening paid adjustment, not a new cash outflow. Opening
confirmation is audited and allowed once. Supplier profiles show confirmed due and a count
of unverified receipts; do not treat confirmed due as total liability until all openings are
reconciled. Supplier history and reports show purchase receipts and payment history.

## Customer payments, returns and store credit

Payments & Returns → select invoice → Receive payment. Positive payments cannot exceed
adjusted balance. Returns are administrator-only, need a reason and cannot exceed sold
unreturned units. Physical goods are restocked; services are not. Discount/tax allocation
ensures returned units sum to the original invoice value. Paid money is allocated to a
refund payable, while unpaid amounts are offset. Return creation never transfers money.

After actually paying a refund, choose its settlement and Record completed refund payout.
Enter actual amount, method and a unique reference, then confirm completion. Partial payouts
are allowed; duplicates and overpayments are blocked. Credit settlements may create a
negative invoice balance: select it and Apply credit to another invoice for the same named
customer. Redemption cannot exceed available credit or destination balance, and does not
create a cash receipt. Customer/store credit liabilities remain visible as negative balances.

## Cash and accounts

Expenses & Accounts records cash-paid expenses, opening float, cash added/removed and a
reason. Expected cash = cash collections + opening/in − cash out − expenses − completed
cash refunds − supplier cash payments. Bank/card activity is excluded from cash. Close day
at the end of trading: save actual cash count, day and notes. One immutable count snapshot
per date records expected/count/variance; later activity does not rewrite it. Closing is not
a shift lock. Use documented later/next-day movements for corrections and reconcile reports.

## Reports and exports

Sales, Collections, Customer dues, Stock, Inventory valuation, Low stock, Purchases, Supplier
balances/payments, Expenses, Cash closing and Profit are available. Date ranges apply to dated
activity; inventory and balance reports are current positions. Cost/retail stock value and
potential margin are not realised profit. Profit subtracts sales tax, returns, historical cost
of goods and expenses, reversing new-sale return costs/tax. Legacy costs without snapshots
are estimates. This is operational reporting, not statutory accounting or tax filing.
CSV opens in spreadsheet software; Print / save PDF uses local Qt printing. Exports escape
untrusted customer text to prevent spreadsheet formula execution. Check filters before export.

## Back up and recover

Administrator: Backup & Recovery → Save verified backup. Choose a protected drive/location;
SQLite online backup and integrity verification complete before success is reported. Keep
daily copies off the computer; backups are not encrypted or uploaded. Close the application,
then open Ainak Mahal Recovery from Start. Authenticate as administrator, choose a verified
backup and confirm replacement. Recovery preserves a timestamped safety copy and refuses
another running instance. After restore, sign in and check stock/payment reconciliation.
If a corrupt database prevents login, preserve it and seek isolated technician-led recovery;
the app does not bypass authentication or delete it automatically.

## Sample acceptance and troubleshooting

Use a separate Windows test account or set AINAK_DATA_DIR to an empty test directory. Do
not put sample sales in real business data. Create admin/customer/frame/lenses; make an
optical order with Rx/advance/job, receive the balance, deliver it, receive a multi-line PO,
pay a supplier, process a repair, return/refund, count cash, export and restore a backup.
Check real printer/scanner, Windows scaling and screen-reader use. `AinakMahal.exe
--smoke-test` runs its own isolated sample and does not open the live database.

The installer is unsigned unless a trusted signing certificate is provided. The tested
build is for review; complete real-device and operator acceptance before daily trading.


Developed by **Ahsan Iftikhar**. Current release: **2.0.1**.
