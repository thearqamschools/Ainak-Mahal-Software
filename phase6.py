"""Phase 6: auditable refund payout recording. Does not transfer money."""
import uuid
from core import money, now
import phase5

DDL = """
CREATE TABLE IF NOT EXISTS refund_payouts (
 id TEXT PRIMARY KEY, return_id INTEGER NOT NULL, amount_cents INTEGER NOT NULL CHECK(amount_cents>0),
 method TEXT NOT NULL CHECK(method IN ('Cash','Bank')),
 reference TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL,
 FOREIGN KEY(return_id) REFERENCES return_settlements(return_id));
CREATE UNIQUE INDEX IF NOT EXISTS uq_refund_reference ON refund_payouts(method,reference);
"""

def init(db):
    phase5.init(db)
    db.executescript(DDL)
    db.commit()

def payout_status(store, return_id):
    row=store.db.execute('SELECT cash_refund_cents,method FROM return_settlements WHERE return_id=?',(return_id,)).fetchone()
    if row is None: raise ValueError('Return settlement not found')
    paid=store.db.execute('SELECT COALESCE(SUM(amount_cents),0) FROM refund_payouts WHERE return_id=?',(return_id,)).fetchone()[0]
    return {'due':row[0]/100,'paid':paid/100,'remaining':(row[0]-paid)/100,'method':row[1]}

def record_payout(store, return_id, amount, method, reference, actor, role):
    """Record an externally completed payout. Caller must verify actual cash/bank transfer."""
    if role != 'admin': raise PermissionError('Administrator required')
    cents=money(amount)
    if cents<=0: raise ValueError('Positive payout required')
    if method not in ('Cash','Bank'): raise ValueError('Cash or Bank required')
    if not reference or not reference.strip(): raise ValueError('Unique receipt/reference required')
    if not actor or not actor.strip(): raise ValueError('Actor required')
    with store.db:
        status=payout_status(store,return_id)
        if status['method'] != method: raise ValueError('Payout method differs from settlement')
        due=money(status['remaining'])
        if cents>due: raise ValueError('Payout exceeds outstanding refund')
        payout_id=str(uuid.uuid4())
        store.db.execute('INSERT INTO refund_payouts VALUES(?,?,?,?,?,?,?)',
            (payout_id,return_id,cents,method,reference.strip(),actor.strip(),now()))
        store.db.execute('INSERT INTO sync_outbox VALUES(?,?,?,?,?,NULL)',
            (str(uuid.uuid4()),'refund_payout',payout_id,'created',now()))
    return payout_id
