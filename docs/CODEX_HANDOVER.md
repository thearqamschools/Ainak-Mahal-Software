# Ainak Mahal ERP — Codex Handover and Continuation

**Last updated:** 2026-11-03  
**Canonical detailed handover:** https://github.com/thearqamschools/Ainak-Mahal-Software/issues/4  
**Original requirements:** https://github.com/thearqamschools/Ainak-Mahal-Software/issues/1  
**Latest implemented code (unmerged):** https://github.com/thearqamschools/Ainak-Mahal-Software/pull/2  
**Implementation branch:** `feature/issue-1-offline-desktop` (commit `506761c090474281dfbc826e8bc9b23d0f816de7` before this documentation commit)

## Product and decisions
Ainak Mahal is an **offline Windows 10/11 x64 optical store ERP** for a shop in Faisalabad, Pakistan. Deliver a standalone `AinakMahal_Setup.exe` with no required internet, Python installation, hosting or subscription. Use local SQLite and modular services to enable *future optional* multi-store/cloud expansion. Do not turn it into a web app. Do not mix in school branding.

## What has been built
PR #2 reports 12 desktop screens, transaction-safe services for customers, prescriptions, stock, POS, payments, optical jobs, purchasing, returns, reporting, staff and recovery; 47 automated tests; Windows CI installer and upgrade checks. It remains **open and unmerged**. See `docs/BUILD_PLAN.md`, `docs/OPERATOR_GUIDE.md`, and `docs/RELEASE_REVIEW.md` for specifics. Re-run tests before asserting current success.

## What remains
1. Review user-supplied Asaan Optics reference videos/screenshots, if actually accessible, and map observed features to the implementation; do not copy their proprietary UI.
2. Design an original minimalist eyeglasses-based **Ainak Mahal** logo (SVG, PNG, ICO), including light/dark and icon-only variants.
3. Create a cohesive design system and significantly improve the interactive desktop UI/UX, especially login, dashboard, sidebar, POS, customers, inventory and repair workflows.
4. Apply **Taste**, **Emil Kowalski Motion**, **Impeccable** principles; check availability of any named skills and avoid falsely claiming installed tooling.
5. Finish missing/weak workflows and UX states without losing existing services or data compatibility. Assess Tkinter versus PySide6 pragmatically.
6. Verify database integrity, secure account onboarding/recovery, printing/barcode support, accessibility, install/upgrade, backup/restore and accounting reconciliation.
7. Produce a new reviewable PR, screenshots, operator guide, test evidence and verified Windows installer. Physical printer/scanner and pristine Windows 11/operator sign-off remain pending until actually tested.

## Credentials / testing note
No default username or password. Fresh installation must let the operator create an administrator with a password of at least 10 characters. User forgot credentials for a **test-only** installation with no valuable data; a local database reset was explained, but not confirmed performed. Do not silently erase any data or introduce insecure password bypasses.

## Codex execution instruction
Read this file and Issue #4 in full, then Issue #1 and PR #2. **Start from the latest working PR #2 branch**, not the outdated `main` code. Continue autonomously from audit and logo to complete offline desktop UI/UX redesign, functionality, automated tests and installer. Preserve functionality and history, work on a reviewable branch/PR, do not auto-merge. Request missing reference attachments only if they are not accessible. Distinguish verified work from remaining checks.
