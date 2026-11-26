"""Confirm legacy supplier opening balances from a real supplier statement.

Receipts entered before schema 2 have no reliable record of what was paid, so they
are marked "Opening unverified". Nothing here guesses: the only input is the
balance printed on the supplier's own statement. From it we subtract what Ainak
Mahal already knows is unpaid on verified receipts up to the statement date; the
remainder is the unpaid amount on the legacy receipts. It must be between zero
and the legacy receipts' total, otherwise the statement and the records disagree
and nothing is saved.

The supplier-level amount is the confirmed fact. Splitting it across receipts
follows the usual trade practice that payments settle the oldest invoices first,
so the unpaid balance sits on the newest legacy receipts. Opening "paid" amounts
are historical adjustments, never new cash or bank movements.
"""
import uuid
from datetime import date, datetime
from pathlib import Path
from core import money, now
import phase3

DDL = '''
CREATE TABLE IF NOT EXISTS supplier_statements(id TEXT PRIMARY KEY,
 supplier_id INTEGER NOT NULL REFERENCES suppliers(id), statement_date TEXT NOT NULL, reference TEXT NOT NULL,
 statement_balance_cents INTEGER NOT NULL CHECK(statement_balance_cents>=0),
 verified_due_cents INTEGER NOT NULL, legacy_unpaid_cents INTEGER NOT NULL CHECK(legacy_unpaid_cents>=0),
 note TEXT NOT NULL DEFAULT '', backup_path TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(supplier_id, reference));
CREATE TABLE IF NOT EXISTS supplier_opening_evidence(purchase_id INTEGER PRIMARY KEY REFERENCES purchases(id),
 statement_id TEXT NOT NULL REFERENCES supplier_statements(id), unpaid_cents INTEGER NOT NULL CHECK(unpaid_cents>=0));
'''


def _pkr(cents):
    return f'PKR {cents / 100:,.2f}'


def _day(value):
    try:
        parsed = date.fromisoformat(str(value).strip())
    except ValueError:
        raise ValueError('Enter the statement date as YYYY-MM-DD, for example 2026-11-30') from None
    if parsed > date.today():
        raise ValueError('The statement date cannot be in the future')
    return parsed.isoformat()


def _amount(value):
    text = str(value).strip().replace(',', '')
    if text.startswith('-'):
        raise ValueError('Enter the balance the shop owes as a positive number. If the supplier owes the shop, '
                         'record that separately; it is not an opening balance.')
    try:
        return money(text)
    except ValueError:
        raise ValueError('Enter the statement balance as a number with up to 2 decimals, for example 45000') from None


def unverified_receipts(db, supplier_id):
    return db.execute('''SELECT p.id, substr(p.date,1,10), p.total FROM purchases p
        JOIN purchase_openings o ON o.purchase_id=p.id
        WHERE p.supplier_id=? AND o.verified=0 ORDER BY p.date, p.id''', (supplier_id,)).fetchall()


def verified_due_on(db, supplier_id, statement_date):
    """Unpaid on verified receipts dated up to the statement date, counting only payments made by then."""
    rows = db.execute('''SELECT p.id, p.total, o.paid_cents FROM purchases p
        JOIN purchase_openings o ON o.purchase_id=p.id
        WHERE p.supplier_id=? AND o.verified=1 AND substr(p.date,1,10)<=?''', (supplier_id, statement_date)).fetchall()
    due = 0
    for pid, total, opening_paid in rows:
        paid = db.execute('''SELECT COALESCE(SUM(amount_cents),0) FROM supplier_payments
            WHERE purchase_id=? AND substr(created_at,1,10)<=?''', (pid, statement_date)).fetchone()[0]
        due += max(0, money(total) - opening_paid - paid)
    return due


def preview(db, supplier_id, statement_date, balance):
    supplier = db.execute('SELECT id,name FROM suppliers WHERE id=?', (supplier_id,)).fetchone()
    if not supplier:
        raise ValueError('Choose a supplier')
    statement_date = _day(statement_date)
    balance_cents = _amount(balance)
    legacy = unverified_receipts(db, supplier_id)
    if not legacy:
        raise ValueError(f'{supplier[1]} has no unverified legacy receipts. Nothing needs confirming.')
    latest = max(r[1] for r in legacy)
    if statement_date < latest:
        raise ValueError(f'This statement is dated {statement_date}, before the last legacy receipt ({latest}). '
                         'Use a statement dated on or after that receipt so it includes every legacy receipt.')
    legacy_total = sum(money(r[2]) for r in legacy)
    verified_due = verified_due_on(db, supplier_id, statement_date)
    unpaid = balance_cents - verified_due
    if unpaid < 0:
        raise ValueError(f'The statement balance ({_pkr(balance_cents)}) is less than the amount Ainak Mahal already shows as '
                         f'unpaid on confirmed receipts up to {statement_date} ({_pkr(verified_due)}). '
                         'Check the statement date and any supplier payments not yet recorded. Nothing was saved.')
    if unpaid > legacy_total:
        raise ValueError(f'The statement asks for {_pkr(unpaid - legacy_total)} more than all of this supplier\'s legacy '
                         f'receipts together ({_pkr(legacy_total)}). Ainak Mahal cannot create a debt without the '
                         'purchase record. Ask the supplier for the missing invoices and enter them as purchases first. '
                         'Nothing was saved.')
    remaining = unpaid
    allocation = []
    for pid, day_, total in sorted(legacy, key=lambda r: (r[1], r[0]), reverse=True):
        share = min(money(total), remaining)
        remaining -= share
        allocation.append({'purchase_id': pid, 'date': day_, 'total_cents': money(total),
                           'unpaid_cents': share, 'paid_cents': money(total) - share})
    allocation.reverse()
    return {'supplier_id': supplier[0], 'supplier': supplier[1], 'statement_date': statement_date,
            'statement_balance_cents': balance_cents, 'verified_due_cents': verified_due,
            'legacy_unpaid_cents': unpaid, 'legacy_total_cents': legacy_total, 'receipts': allocation}


def describe(p):
    lines = [f'Supplier: {p["supplier"]}', f'Statement date: {p["statement_date"]}',
             f'Balance on statement: {_pkr(p["statement_balance_cents"])}',
             f'Less unpaid on receipts already confirmed: {_pkr(p["verified_due_cents"])}',
             f'= Unpaid on {len(p["receipts"])} legacy receipt(s): {_pkr(p["legacy_unpaid_cents"])} '
             f'of {_pkr(p["legacy_total_cents"])}', '', 'Receipts (oldest treated as paid first):']
    for r in p['receipts']:
        lines.append(f'  #{r["purchase_id"]}  {r["date"]}  total {_pkr(r["total_cents"])}  →  unpaid {_pkr(r["unpaid_cents"])}')
    lines += ['', 'Paid parts are historical adjustments. No cash or bank payment is recorded.']
    return '\n'.join(lines)


def confirm(service, supplier_id, statement_date, balance, reference, note=''):
    """Back up, then confirm every legacy receipt of one supplier from one statement."""
    service.authorize(True)
    reference = str(reference or '').strip()
    if len(reference) < 3:
        raise ValueError('Enter the statement number or a short description, for example "Statement Nov-2026"')
    db = service.db
    plan = preview(db, supplier_id, statement_date, balance)
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='supplier_statements'").fetchone() and \
       db.execute('SELECT 1 FROM supplier_statements WHERE supplier_id=? AND reference=?', (supplier_id, reference)).fetchone():
        raise ValueError(f'Statement "{reference}" was already used for this supplier. Nothing was saved.')
    folder = Path(service.store.path).resolve().parent / 'backups'
    folder.mkdir(parents=True, exist_ok=True)
    backup = folder / f'before_supplier_statement_{datetime.now().strftime("%Y%m%d_%H%M%S_%f")}.db'
    service.store.backup(backup)
    statement_id = str(uuid.uuid4())
    with db:
        for statement in DDL.strip().split(';'):
            if statement.strip():
                db.execute(statement)
        again = preview(db, supplier_id, plan['statement_date'], balance)
        if again != plan:
            raise ValueError('Supplier records changed while confirming. Nothing was saved; please try again.')
        db.execute('INSERT INTO supplier_statements VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                   (statement_id, supplier_id, plan['statement_date'], reference, plan['statement_balance_cents'],
                    plan['verified_due_cents'], plan['legacy_unpaid_cents'], str(note or '').strip(), str(backup),
                    service.actor, now()))
        for r in plan['receipts']:
            changed = db.execute('UPDATE purchase_openings SET paid_cents=?,verified=1 WHERE purchase_id=? AND verified=0',
                                 (r['paid_cents'], r['purchase_id'])).rowcount
            if changed != 1:
                raise ValueError('A receipt was confirmed by someone else meanwhile. Nothing was saved.')
            db.execute('INSERT INTO supplier_opening_evidence VALUES(?,?,?)', (r['purchase_id'], statement_id, r['unpaid_cents']))
        phase3.audit(db, service.actor, 'supplier_statement_confirmed',
                     f'{plan["supplier"]} #{supplier_id}; {reference} dated {plan["statement_date"]}; '
                     f'statement {_pkr(plan["statement_balance_cents"])}; legacy unpaid {_pkr(plan["legacy_unpaid_cents"])}; '
                     f'{len(plan["receipts"])} receipts; backup {backup}')
    return dict(plan, statement_id=statement_id, backup=backup, reference=reference)


def worksheet(db):
    """What to ask each supplier for: one row per supplier with unverified legacy receipts."""
    return db.execute('''SELECT s.id, s.name, COALESCE(s.phone,''), COUNT(p.id), ROUND(SUM(p.total),2),
          MIN(substr(p.date,1,10)), MAX(substr(p.date,1,10))
        FROM purchases p JOIN suppliers s ON s.id=p.supplier_id JOIN purchase_openings o ON o.purchase_id=p.id
        WHERE o.verified=0 GROUP BY s.id ORDER BY s.name''').fetchall()


def statements(db):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='supplier_statements'").fetchone():
        return []
    return db.execute('''SELECT st.statement_date, s.name, st.reference, st.statement_balance_cents/100.0,
          st.verified_due_cents/100.0, st.legacy_unpaid_cents/100.0, st.actor, st.created_at
        FROM supplier_statements st JOIN suppliers s ON s.id=st.supplier_id ORDER BY st.created_at DESC''').fetchall()
