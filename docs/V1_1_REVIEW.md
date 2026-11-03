# Version 1.1 review build — Issue #4

Prepared 3 November 2026 (Asia/Karachi). Synced from PR #2 branch head `f3de6edc7a6406f456405d427767cb47f058ee5c`, including `docs/CODEX_HANDOVER.md`, and preserving implementation head `506761c090474281dfbc826e8bc9b23d0f816de7`; no merge or database reset.

## Implemented

Original light/dark eyeglasses logo/lockups/application icon; consistent navy, royal blue and teal desktop; first-run and returning sign-in with password visibility and help; grouped navigation; bounded global search; sortable tables and empty states; dashboard activity selector; category/stock and lab/overdue filters; stable checkout actions; additional collections, purchases, low-stock and stock-valuation reports; authenticated and audited password changes/staff resets; inline offline print branding; customer dues/credit summary and supplier receipts/item/order history. All 12 functional PR #2 pages, legacy support entry points, transaction services, migrations, locks, backup/restore, financial safeguards and offline distribution remain.

See [feature/gap audit](ISSUE_4_AUDIT.md), [brand guide](BRAND_GUIDE.md), [17-window gallery](SCREENSHOT_GALLERY.md) and updated [operator guide](OPERATOR_GUIDE.md).

## Current-instance evidence

Linux / CPython 3.12.14 / Tk 9.0 / SQLite 3.53.1, using a local Xvfb display:

- `DISPLAY=:99 PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -v`: **57 passed, zero skipped**. This includes all 47 PR #2 tests and 10 new tests. Original transaction/rollback, exact-cent financial, migration and backup/restore tests remain intact.
- `DISPLAY=:99 PYTHONDONTWRITEBYTECODE=1 python3 launcher.py --smoke-test`: **passed**. Exercises actual first-run and subsequent sign-in submission, 12 screen constructions and minimum-1050×700 button visibility; sale/stock/payment/Rx/job delivery/PO receipt/expense/printing/backup/restore. Packaged icon presence is also asserted.
- `DISPLAY=:99 PYTHONDONTWRITEBYTECODE=1 python3 tools/capture_gallery.py`: **17 actual windows captured**, synthetic data only, no callback errors.
- Python 3.11 AST syntax compatibility and `git diff --check`: passed. Syntax compatibility is not a claim of a full Python 3.11 runtime test.

Images use the Linux scalable fallback font. No screenshot is represented as Windows validation. Visual review corrected font fallback, style hierarchy, clipped login copy and minimum-size checkout actions.

## Windows delivery gate

`tools/build.ps1` now bundles the committed icon and brand assets. Inno Setup reports version 1.1.0 while retaining the existing AppId and separate data path. The workflow triggers for this `feat/**` branch and PRs. It builds the offline x64 executable/installer, runs source and installed-executable smoke checks, reinstalls over an isolated populated database, checks SHA-256 data preservation and emits installer SHA-256, smoke JSON and a Windows screenshot gallery.

A source check on Linux is not a new Windows installer. The v1.1 Windows build/install/upgrade result and artifact must be confirmed from this branch's GitHub Actions run before calling the installer delivered. The previously linked v1.0 artifact is not this version. GitHub API access was denied by the environment's destination policy; an `api.github.com` addition was saved in the configuration draft for user application. Git HTTPS read access works. Remote PR/build status is reported separately once observed; no API or CI success is inferred from configuration saving.

## Remaining external acceptance

- Fresh normal Windows 10/11 x64 installation without Python; Start-menu/uninstall behavior and standard-user upgrades.
- Shop printer A4/80 mm output and scanner suffix behavior.
- Windows display scaling, keyboard audit with the operator, screen reader and visual approval.
- Optional trusted Windows signing certificate. The review installer is unsigned.
- Asaan reference image/video comparison: source attachments were not accessible in this task.

Product boundaries: one workstation, no cloud sync; full PO receipt once (direct receipts for staged goods); current-cost inventory valuation; estimated legacy historical profit; no statutory ledger or tax filing. Password recovery never bypasses authentication or deletes data. If every administrator loses credentials, preserve databases/backups for technician-assisted recovery.

## Windows search focus correction

The first Windows build exposed a real global-search keyboard focus issue. The search entry was focused before its window was mapped; Linux accepted that request, Windows did not. Search now waits for visibility, acquires modal keyboard ownership, and explicitly focuses the entry. The regression asserts actual focus before Enter navigation. A visible Open selected action supports pointer users too. No test was removed, skipped or weakened. Windows run [41613695786](https://github.com/thearqamschools/Ainak-Mahal-Software/actions/runs/41613695786) subsequently passed the combined source test/build and installed/upgrade smoke steps; full workflow/artifact completion and the later history additions require their own observed results.
