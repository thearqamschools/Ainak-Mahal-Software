# ERP 2.0 reference review and gap analysis

Reviewed all 15 screenshots supplied in chat and both MP4 visual timelines (video 1:
120.65 seconds; video 2: 86.05 seconds). Videos decoded across their entire duration;
visual samples every three seconds were inspected, including all major sequences.
They are promotional presentations, not continuous instrumented software sessions.
Narration was not independently transcribed. Timing and back-end correctness cannot
be inferred from edited transitions. Reference media and visible credentials are never
copied into application assets, tests, documentation or Git history.

| Evidence | Observed / shown | Existing foundation | ERP 2.0 decision |
|---|---|---|---|
| Screens 1–3 | Local-looking shop login, account types, Google login, language selector | Username/password admin/cashier | Original local onboarding/login, password visibility; no cloud identity or subscription |
| Screens 4–6 | Expandable terms/privacy/support | Operator guide | Own factual offline-data/help content; no copied legal terms or support contacts |
| Screen 7; video 1 27–33s | Quick actions, revenue, new customers, dues, expense overview, trend graphics | Six basic metrics, pending jobs | Actionable dashboard, recent sales, low stock, live date-based trend and job shortcuts |
| Screen 8; video 1 39–45s | Customer/Rx, frame and separate eye lenses, additional pairs, advances, delivery on one order | Separate customer/Rx/POS/job forms | Atomic integrated order: existing/new customer, existing/new Rx, multi-line cart, payment and optional linked job |
| Screen 8 | WhatsApp, referring doctor, optional sex/date of birth, VA, PD, contact-lens section | Name/phone/address and core Rx | Optional customer profile fields, full specified OD/OS powers; no inferred clinical VA rules |
| Screen 9; video 1 33–36s | Search name/phone/serial, filters, history, date and balance | Name/phone only | Name/phone/ID search, profile tabs for Rx/sales/jobs/dues, current balance filter and export |
| Screen 10; video 2 33–42s | Sales filtering, cash count, shift history, expense, Excel/PDF buttons | Cash opening/movements/daily snapshot | Preserve cash model, clearer closing and cash history; dated collections and printable/PDF reports |
| Screen 11; video 1 60–66s | Category valuation, potential margin, low/out-of-stock, inactive stock and health signals | Stock list, threshold and movements | Category filters, cost/retail valuation, low-stock list, lens matrix and stock history; do not call potential margin realized profit |
| Screen 12 | Shop identity, currency, message-template placeholders | Shop/tax/printer/backup settings | Shop identity and receipt settings; no automatic external messages or account data copied |
| Screens 13–14 | Tax configuration, organisation/invitations | Local tax, MAIN branch | Retain configured tax; branch/cloud invitation controls excluded from offline V1 scope |
| Screen 15; videos | Staff screen access, audit | Two roles and audit log | Preserve enforced roles, account activation and audit history; no unsupported cloud branch claims |
| Video 1 69–90s | Mobile app and 19 calculators advertised; transposition example shown | None | Desktop mathematical transposition/spherical equivalent tools only; mobile/sync not implemented |
| Video 2 45–54s | Stock deduction, low-stock and barcode-label printing described | Deduction and barcode lookup | Keep transactional deduction and barcode keyboard search; add local printable product labels |
| Both videos | Repair entry mentioned; detailed repair processing not demonstrated | General optical jobs | Dedicated repair/lens-replacement/frame-repair type, instructions, charges, invoice/payment, due date and lifecycle |
| User master brief | Supplier profiles/history/balances where proper accounting exists | PO and receipt, no supplier payments | Add purchase-linked payments and capped balances; cash payments included in drawer reconciliation |

## Assumptions and explicit boundaries

Marketing labels such as cloud synced, premium active, mobile sharing and optional language
selectors do not prove offline correctness. No subscription, cloud login, copied mascots,
trademark, proprietary icons, watermark, legal boilerplate or online service is included.
Existing audit trails and irreversible sale/return safeguards are retained. Full receipt
of purchase orders remains explicit; partial shipments use direct goods receipt. Financial
and operational rules follow the master prompt rather than inferred reference behavior.

## Framework decision

Migrate the presentation to Qt Widgets / PySide6 Essentials, with native table sorting,
scroll areas, high-DPI rendering, SVG icons, printing and keyboard shortcuts. Reuse Retail,
Store and phase services. Retain desktop.py and legacy launchers for support and regression
coverage. No WebEngine, JavaScript runtime, local HTTP server or remote UI assets are used.
Qt is dynamically bundled in an onedir package, with license notices and replacement/source
instructions. The original database path and all legacy tables/IDs remain unchanged.
