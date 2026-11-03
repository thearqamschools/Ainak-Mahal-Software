# Issue #4 handover audit and implementation record

3 November 2026. Authoritative inputs: [handover #4](https://github.com/thearqamschools/Ainak-Mahal-Software/issues/4), [original #1](https://github.com/thearqamschools/Ainak-Mahal-Software/issues/1), and [PR #2](https://github.com/thearqamschools/Ainak-Mahal-Software/pull/2).

PR #2 was OPEN and unmerged when inspected. Its actual head was `506761c090474281dfbc826e8bc9b23d0f816de7` on `feature/issue-1-offline-desktop`, targeting `main`. Continuation fetched the latest `feature/issue-1-offline-desktop` at `f3de6edc7a6406f456405d427767cb47f058ee5c`, which adds `docs/CODEX_HANDOVER.md` to that implementation. The current review branch starts at that newer commit and carries forward the prior design upgrade without changing either published branch history. Its 47 tests passed afresh on Linux before changes. The default checkout was an older 29-test implementation; developing there would have lost the PR's workflows. No PR was merged and no live customer database was opened or reset.

## Feature / gap matrix

| Area | PR #2 baseline | This upgrade | Remaining boundary |
| --- | --- | --- | --- |
| Branding | Text wordmark | Original light/dark eyeglasses SVG, transparent PNG, tile PNG, ICO, light/dark lockups; sidebar, login, window, print and installer integration | Operator visual approval |
| First run / sign-in | Functional basic form | Split brand panel, show/hide passwords, inline validation, Caps Lock feedback, Enter/Tab, safe help, credential clearing | Physical Windows scaling / screen reader |
| Desktop | 12 functional pages | Consistent navy/blue/teal system, grouped navigation, focus/hover/press states, sortable striped grids and empty states | Operator acceptance |
| Global search | Page-local search only | Ctrl+K searches customers/mobile, products/SKU/barcode, jobs and invoices; Enter selects actual record | Results bounded to 12, deterministic source priority |
| Dashboard | Six metrics and jobs | Refined metrics, switchable upcoming jobs, recent invoices and low-stock views | No fabricated trends or percentage comparisons |
| Customers / Rx | Profiles/history; validated OD/OS/ADD/PD | Redesigned grids/forms; separate customer dues/credit summary; global search selection; original mark on print | Physical Rx printing |
| Catalog / lenses | Variants, barcode, movements, power matrix | Combined category/search/low-stock/out-of-stock filters | No online catalog |
| POS | Atomic quote/sale/payment, tax/discount, partial payment | Readable two-pane checkout, stable save/clear actions, scrollable payment fields with keyboard reveal, clearer overpayment feedback | Physical scanner / printer |
| Lab / repairs | Jobs, links, status/delivery gate; repair service items | Customer/instruction search plus status and overdue filters | Repairs use job instructions and service catalog items; no separate repair-warranty subsystem |
| Purchasing | Suppliers, multi-line PO and direct receipts | Supplier-specific receipt/item/PO history; dated purchase receipt report | POs receive in full once; use direct receipt for staged goods, never receive the same shipment twice |
| Returns / credit / cash | Exact-cent returns, payouts, credit, closing | Preserved service authorization/transactions; redesigned presentation | Operational records, no statutory ledger or tax filing |
| Reports | Sales, stock, dues, expense, closing, profit | Adds collections, stock valuation, low-stock and purchases; CSV retained | Valuation uses current cost; historical legacy profit remains estimated |
| Accounts / recovery | Staff and authenticated restore | Current-password change, audited admin staff reset with fresh password verification; no login bypass | If every admin credential is lost, preserve files and obtain technician-assisted recovery |
| Packaging | CI build/install/upgrade smoke | Version 1.1.0 icon/assets; source and installed real-login checks; Windows screenshot artifact step | New Windows build result must be verified separately |
| Data / offline | Local SQLite, additive v1 migrations, locks and backups | No schema changes; legacy services and IDs retained; runtime still standard library | Single workstation; no sync or multi-PC mode |

## Toolkit decision

Retain Tkinter. It already supports all working workflows and the required offline Windows distribution with no runtime packages. Material gains come from hierarchy, search, stable actions, keyboard support and reusable table states. A toolkit rewrite would put the existing tested service/UI parity at risk without an established requirement it alone resolves. Presentation stays in `desktop.py`/`brand.py`, writes in `retail.py` and existing domain modules.

## Reference evidence and design principles

No Asaan Optics screenshots/videos were attached to the task, linked in the accessible issue content, or present in the checkout. Reference-by-reference analysis cannot be claimed. Reattach those references for a subsequent specific comparison; their absence did not block the approved original design direction.

Taste, Emil Kowalski Motion and Impeccable are not installed skills in this environment. Their requested principles were applied directly: restrained original palette, larger hierarchy, consistent spacing, visible focus, useful states, native immediate feedback and no animation that delays checkout. No third-party design skill or proprietary artwork was downloaded.

Visual QA caught missing Linux Segoe font fallback, a clipped brand-panel sentence, flattened label hierarchy caused by an inherited global font option, and minimum-size checkout action clipping. These were corrected and the actual windows recaptured. Windows uses Segoe UI; Linux selects a supported scalable fallback. Baseline PNGs record the original Linux display rendering, not a Windows screenshot.
