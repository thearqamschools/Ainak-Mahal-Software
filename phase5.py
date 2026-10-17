"""Phase 5: transactional return settlements and reconciliation; not a production auth boundary."""
from decimal import Decimal
from core import money, now
import phase4, phase3

DDL = '''
CREATE TABLE IF NOT EXISTS return_settlements(
 id INTEGER PRIMARY KEY, return_id INTEGER NOT NULL UNIQUE,
 method TEXT NOT NULL CHECK(method IN ('Cash','Bank','Credit')),
 cash_refund_cents INTEGER NOT NULL CHECK(cash_refund_cents>=0),
 credit_cents INTEGER NOT NULL CHECK(credit_cents>=0),
 created_at TEXT NOT NULL,
 FOREIGN KEY(return_id) REFERENCES sale_returns(id));
'''

def init(db):
    phase4.init(db)
    db.executescript(DDL)
    db.commit()

def return_and_settle(store, sale_id, product_id, qty, reason, actor, role, method='Cash', restock=True):
    """Return one sold item; allocate refund against received cash first, remainder as credit.

    Credit is a liability/adjustment pending a dedicated ledger. This function does not
    send money or post bank transactions; cashier must perform cash/bank payout separately.
    """
    phase4.require_role(role, {'admin'})
    if method not in ('Cash','Bank','Credit'):
        raise ValueError('Invalid refund method')
    with store.db:
        rid, refund = phase4.return_item(store, sale_id, product_id, qty, reason, actor, role, restock)
        paid = store.db.execute('SELECT paid FROM sales WHERE id=?', (sale_id,)).fetchone()[0]
        already_cash = store.db.execute('''SELECT COALESCE(SUM(rs.cash_refund_cents),0)
            FROM return_settlements rs JOIN sale_returns r ON r.id=rs.return_id
            WHERE r.sale_id=?''', (sale_id,)).fetchone()[0]
        remaining_received = max(0, money(paid) - already_cash)
        refund_cents = money(refund)
        cash = 0 if method == 'Credit' else min(refund_cents, remaining_received)
        credit = refund_cents - cash
        store.db.execute('INSERT INTO return_settlements(return_id,method,cash_refund_cents,credit_cents,created_at) VALUES(?,?,?,?,?)',
                         (rid,method,cash,credit,now()))
        phase3.audit(store.db, actor, 'settle_return', rid)
        return {'return_id':rid,'refund_value':refund,'payout_due':cash/100,'credit_adjustment':credit/100}

def invoice_position(store,sale_id):
    row=store.db.execute('SELECT total,paid FROM sales WHERE id=?',(sale_id,)).fetchone()
    if row is None: raise ValueError('Invoice not found')
    returned=store.db.execute('SELECT COALESCE(SUM(refund),0) FROM sale_returns WHERE sale_id=?',(sale_id,)).fetchone()[0]
    cash=store.db.execute('''SELECT COALESCE(SUM(rs.cash_refund_cents),0) FROM return_settlements rs
       JOIN sale_returns r ON r.id=rs.return_id WHERE r.sale_id=?''',(sale_id,)).fetchone()[0]
    return {'original_total':row[0], 'return_value':returned,
            'net_sale':(money(row[0])-money(returned))/100,
            'payments_received':row[1], 'payout_due':cash/100,
            'net_customer_balance':(money(row[0])-money(returned)-money(row[1])+cash)/100}
