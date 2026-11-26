"""Additive schema upgrades. Legacy tables and integer identifiers stay intact."""
import uuid
from core import now
import phase6

DDL = '''
CREATE TABLE IF NOT EXISTS schema_versions(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS entity_identity(entity TEXT NOT NULL, local_id TEXT NOT NULL,
 uuid TEXT NOT NULL UNIQUE, branch_id TEXT NOT NULL DEFAULT 'MAIN', created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL, PRIMARY KEY(entity,local_id));
CREATE TABLE IF NOT EXISTS product_details(product_id INTEGER PRIMARY KEY REFERENCES products(id),
 barcode TEXT UNIQUE, variant TEXT NOT NULL DEFAULT '', sph TEXT, cyl TEXT, reorder_level INTEGER NOT NULL DEFAULT 2,
 is_service INTEGER NOT NULL DEFAULT 0 CHECK(is_service IN (0,1)));
CREATE TABLE IF NOT EXISTS rx_details(rx_id INTEGER PRIMARY KEY REFERENCES prescriptions(id), od_add TEXT, os_add TEXT);
CREATE TABLE IF NOT EXISTS job_details(job_id TEXT PRIMARY KEY REFERENCES optical_jobs(id),
 rx_id INTEGER REFERENCES prescriptions(id), delivered_at TEXT);
CREATE TABLE IF NOT EXISTS sale_terms(sale_id INTEGER PRIMARY KEY REFERENCES sales(id),
 subtotal_cents INTEGER NOT NULL, discount_cents INTEGER NOT NULL, tax_cents INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS line_costs(line_id INTEGER PRIMARY KEY REFERENCES sale_items(id), unit_cost_cents INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS credit_transfers(id TEXT PRIMARY KEY, source_sale_id INTEGER NOT NULL REFERENCES sales(id),
 target_sale_id INTEGER NOT NULL REFERENCES sales(id), amount_cents INTEGER NOT NULL CHECK(amount_cents>0),
 actor TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS return_values(return_id INTEGER PRIMARY KEY REFERENCES sale_returns(id), cost_cents INTEGER NOT NULL,
 tax_cents INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS cash_movements(id TEXT PRIMARY KEY, day TEXT NOT NULL, kind TEXT NOT NULL,
 amount_cents INTEGER NOT NULL CHECK(amount_cents>0), note TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS daily_closings(id TEXT PRIMARY KEY, day TEXT NOT NULL UNIQUE,
 expected_cents INTEGER NOT NULL, counted_cents INTEGER NOT NULL, note TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_customers_phone ON customers(phone);
CREATE INDEX IF NOT EXISTS ix_sales_date ON sales(date);
CREATE INDEX IF NOT EXISTS ix_jobs_status ON optical_jobs(status,due_date);
'''

TRACKED = ('customers','products','prescriptions','sales','sale_items','suppliers',
 'purchases','purchase_items','expenses','stock_movements','customer_payments','optical_jobs',
 'purchase_orders','purchase_order_lines','sale_returns','return_settlements','refund_payouts',
 'cash_movements','daily_closings','credit_transfers')

def migrate(store):
    db = store.db
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version > 2:
        raise RuntimeError('This database needs a newer Ainak Mahal version. No changes were made.')
    phase6.init(store.db)
    db.executescript(DDL)
    with db:
        for table in TRACKED:
            for (local_id,) in db.execute(f'SELECT id FROM {table}').fetchall():
                db.execute('INSERT OR IGNORE INTO entity_identity VALUES(?,?,?,?,?,?)',
                           (table,str(local_id),str(uuid.uuid4()),'MAIN',now(),now()))
            # SQLite generates random identifiers offline. Registry survives updates; deletes are journaled.
            for event in ('INSERT','UPDATE','DELETE'):
                alias = 'OLD' if event == 'DELETE' else 'NEW'
                identity = '' if event == 'DELETE' else f'''INSERT INTO entity_identity
                  VALUES('{table}',CAST(NEW.id AS TEXT),lower(hex(randomblob(16))),'MAIN',
                  strftime('%Y-%m-%dT%H:%M:%f','now'),strftime('%Y-%m-%dT%H:%M:%f','now'))
                  ON CONFLICT(entity,local_id) DO UPDATE SET updated_at=excluded.updated_at;'''
                db.execute(f'''CREATE TRIGGER IF NOT EXISTS journal_{table}_{event}
                  AFTER {event} ON {table} BEGIN {identity}
                  INSERT INTO sync_outbox VALUES(lower(hex(randomblob(16))),'{table}',
                  CAST({alias}.id AS TEXT),'{event.lower()}',strftime('%Y-%m-%dT%H:%M:%f','now'),NULL); END''')
        db.execute('INSERT OR IGNORE INTO schema_versions VALUES(1,?)',(now(),))
        for table,key in (('product_details','product_id'),('rx_details','rx_id'),('job_details','job_id'),('sale_terms','sale_id'),('line_costs','line_id'),('return_values','return_id'),('app_settings','key')):
            for event in ('INSERT','UPDATE','DELETE'):
                alias='OLD' if event=='DELETE' else 'NEW'
                db.execute(f'''CREATE TRIGGER IF NOT EXISTS journal_{table}_{event} AFTER {event} ON {table}
                  BEGIN INSERT INTO sync_outbox VALUES(lower(hex(randomblob(16))),'{table}',CAST({alias}.{key} AS TEXT),
                  '{event.lower()}',strftime('%Y-%m-%dT%H:%M:%f','now'),NULL); END''')
        if version < 1: db.execute('PRAGMA user_version=1')
