"""Phase 4: guarded authentication, returns, reporting and safe restore."""
import csv, sqlite3, os, shutil, tempfile
from pathlib import Path
from datetime import datetime
from core import money, now
import phase3

DDL='''
CREATE TABLE IF NOT EXISTS sale_returns(id INTEGER PRIMARY KEY,sale_id INTEGER NOT NULL,product_id INTEGER NOT NULL,qty INTEGER NOT NULL CHECK(qty>0),refund REAL NOT NULL CHECK(refund>=0),reason TEXT NOT NULL,actor TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(sale_id) REFERENCES sales(id),FOREIGN KEY(product_id) REFERENCES products(id));
CREATE TABLE IF NOT EXISTS app_settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
'''
def init(db):
    phase3.init(db);db.executescript(DDL);db.commit()

def bootstrap_admin(db, username, password):
    if db.execute('SELECT COUNT(*) FROM app_users').fetchone()[0]:raise ValueError('Users already exist')
    phase3.create_user(db,username,password,'admin')

def require_role(role,allowed):
    if role not in allowed:raise PermissionError('Insufficient permissions')

def return_item(store,sale_id,product_id,qty,reason,actor,role,restock=True):
    require_role(role,{'admin'})
    if type(qty) is not int or qty<=0:raise ValueError('Quantity must be a positive integer')
    if not reason.strip():raise ValueError('Return reason required')
    with store.db:
        row=store.db.execute('SELECT COALESCE(SUM(qty),0),MAX(price) FROM sale_items WHERE sale_id=? AND product_id=?',(sale_id,product_id)).fetchone()
        sold,price=row
        returned=store.db.execute('SELECT COALESCE(SUM(qty),0) FROM sale_returns WHERE sale_id=? AND product_id=?',(sale_id,product_id)).fetchone()[0]
        if not sold or qty>sold-returned:raise ValueError('Return exceeds unreturned sold quantity')
        refund_cents=money(price)*qty
        rid=store.db.execute('INSERT INTO sale_returns(sale_id,product_id,qty,refund,reason,actor,created_at) VALUES(?,?,?,?,?,?,?)',(sale_id,product_id,qty,refund_cents/100,reason.strip(),actor,now())).lastrowid
        if restock:
            store.db.execute('UPDATE products SET qty=qty+? WHERE id=?',(qty,product_id))
            store._move(product_id,qty,'return',rid)
        phase3.audit(store.db,actor,'sale_return',rid)
        return rid,refund_cents/100

def export_sales_csv(store,path):
    path=Path(path)
    rows=store.db.execute('''SELECT s.id,s.date,COALESCE(c.name,'Walk-in'),s.total,s.paid,
        COALESCE((SELECT SUM(r.refund) FROM sale_returns r WHERE r.sale_id=s.id),0)
        FROM sales s LEFT JOIN customers c ON c.id=s.customer_id ORDER BY s.id''').fetchall()
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['Invoice ID','Date','Customer','Gross Total','Recorded Payments','Return Value']);w.writerows(rows)
    return len(rows)

def export_inventory_csv(store,path):
    rows=store.db.execute('SELECT sku,name,category,cost,price,qty FROM products ORDER BY sku').fetchall()
    with Path(path).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(['SKU','Name','Category','Cost','Price','Quantity']);w.writerows(rows)
    return len(rows)

def verify_database(path):
    con=sqlite3.connect(f'file:{Path(path).resolve().as_posix()}?mode=ro',uri=True)
    try:
        if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Database integrity check failed')
        required={'customers','products','sales','sale_items'}
        found={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not required<=found:raise ValueError('Not an Ainak Mahal database')
    finally:con.close()

def restore_database(backup_path,live_path):
    """Only call while app is closed. Preserve original database in timestamped safety copy."""
    backup_path=Path(backup_path).resolve();live_path=Path(live_path).resolve()
    if backup_path==live_path:raise ValueError('Backup and live database cannot be the same')
    verify_database(backup_path)
    if live_path.exists():
        verify_database(live_path)
        safety=live_path.with_name(live_path.stem+'_before_restore_'+datetime.now().strftime('%Y%m%d_%H%M%S')+live_path.suffix)
        shutil.copy2(live_path,safety)
    else:safety=None
    fd,tmp=tempfile.mkstemp(prefix='.ainak_restore_',dir=live_path.parent);os.close(fd)
    try:
        shutil.copyfile(backup_path,tmp);verify_database(tmp);os.replace(tmp,live_path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return safety
