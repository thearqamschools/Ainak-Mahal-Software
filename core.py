"""Ainak Mahal phase-2 transactional core. Python standard library only."""
import sqlite3, uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

SCHEMA = '''
CREATE TABLE IF NOT EXISTS branches(id TEXT PRIMARY KEY,name TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY,name TEXT NOT NULL,phone TEXT,address TEXT,branch_id TEXT DEFAULT 'MAIN');
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,sku TEXT UNIQUE NOT NULL,name TEXT NOT NULL,category TEXT,cost REAL DEFAULT 0,price REAL NOT NULL,qty INTEGER NOT NULL DEFAULT 0,branch_id TEXT DEFAULT 'MAIN');
CREATE TABLE IF NOT EXISTS prescriptions(id INTEGER PRIMARY KEY,customer_id INTEGER NOT NULL,date TEXT,od_sph TEXT,od_cyl TEXT,od_axis TEXT,os_sph TEXT,os_cyl TEXT,os_axis TEXT,pd TEXT,notes TEXT,FOREIGN KEY(customer_id) REFERENCES customers(id));
CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY,customer_id INTEGER,date TEXT NOT NULL,total REAL NOT NULL,paid REAL NOT NULL,FOREIGN KEY(customer_id) REFERENCES customers(id));
CREATE TABLE IF NOT EXISTS sale_items(id INTEGER PRIMARY KEY,sale_id INTEGER NOT NULL,product_id INTEGER NOT NULL,qty INTEGER NOT NULL,price REAL NOT NULL,FOREIGN KEY(sale_id) REFERENCES sales(id),FOREIGN KEY(product_id) REFERENCES products(id));
CREATE TABLE IF NOT EXISTS suppliers(id INTEGER PRIMARY KEY,name TEXT NOT NULL,phone TEXT);
CREATE TABLE IF NOT EXISTS purchases(id INTEGER PRIMARY KEY,supplier_id INTEGER,date TEXT,total REAL,FOREIGN KEY(supplier_id) REFERENCES suppliers(id));
CREATE TABLE IF NOT EXISTS purchase_items(id INTEGER PRIMARY KEY,purchase_id INTEGER,product_id INTEGER,qty INTEGER,cost REAL,FOREIGN KEY(purchase_id) REFERENCES purchases(id),FOREIGN KEY(product_id) REFERENCES products(id));
CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY,date TEXT,description TEXT,amount REAL);
CREATE TABLE IF NOT EXISTS stock_movements(id TEXT PRIMARY KEY,product_id INTEGER NOT NULL,delta INTEGER NOT NULL,reason TEXT NOT NULL,reference_id TEXT,created_at TEXT NOT NULL,branch_id TEXT NOT NULL DEFAULT 'MAIN',FOREIGN KEY(product_id) REFERENCES products(id));
CREATE TABLE IF NOT EXISTS customer_payments(id TEXT PRIMARY KEY,sale_id INTEGER NOT NULL,amount REAL NOT NULL CHECK(amount>0),method TEXT NOT NULL,created_at TEXT NOT NULL,FOREIGN KEY(sale_id) REFERENCES sales(id));
CREATE TABLE IF NOT EXISTS optical_jobs(id TEXT PRIMARY KEY,customer_id INTEGER NOT NULL,sale_id INTEGER,description TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'Pending',due_date TEXT,created_at TEXT NOT NULL,FOREIGN KEY(customer_id) REFERENCES customers(id));
CREATE TABLE IF NOT EXISTS sync_outbox(id TEXT PRIMARY KEY,entity_type TEXT NOT NULL,entity_id TEXT NOT NULL,event_type TEXT NOT NULL,created_at TEXT NOT NULL,synced_at TEXT);
'''

def money(value):
    try:
        d=Decimal(str(value))
        if not d.is_finite() or d<0 or d.as_tuple().exponent < -2: raise ValueError('Amount must be nonnegative with up to 2 decimals')
        return int(d*100)
    except (InvalidOperation,TypeError): raise ValueError('Invalid monetary amount')

def now(): return datetime.now().isoformat(timespec='seconds')

class Store:
    def __init__(self,path):
        self.path=str(path); self.db=sqlite3.connect(self.path)
        self.db.execute('PRAGMA foreign_keys=ON');self.db.execute('PRAGMA busy_timeout=5000')
        self.db.executescript(SCHEMA)
        self.db.execute("INSERT OR IGNORE INTO branches(id,name) VALUES('MAIN','Ainak Mahal - Millat Chowk')")
        self.db.commit()
    def close(self):self.db.close()
    def add_customer(self,name,phone='',address=''):
        if not name.strip():raise ValueError('Customer name required')
        with self.db:return self.db.execute('INSERT INTO customers(name,phone,address) VALUES(?,?,?)',(name.strip(),phone,address)).lastrowid
    def add_product(self,sku,name,price,cost=0,qty=0,category=''):
        if not sku.strip() or not name.strip() or int(qty)!=qty or qty<0:raise ValueError('Invalid product')
        p,c=money(price),money(cost)
        with self.db:
            cur=self.db.execute('INSERT INTO products(sku,name,category,cost,price,qty) VALUES(?,?,?,?,?,?)',(sku,name,category,c/100,p/100,qty))
            if qty:self._move(cur.lastrowid,qty,'opening',str(cur.lastrowid))
            return cur.lastrowid
    def _move(self,pid,delta,reason,ref):
        self.db.execute('INSERT INTO stock_movements VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),pid,delta,reason,str(ref),now(),'MAIN'))
        self.db.execute('INSERT INTO sync_outbox VALUES(?,?,?,?,?,NULL)',(str(uuid.uuid4()),'stock',str(pid),reason,now()))
    def sell(self,items,customer_id=None,paid=0,method='Cash'):
        """items: [(product_id, qty), ...]. Atomic stock and invoice transaction."""
        if not items:raise ValueError('Cart is empty')
        grouped={}
        for pid,qty in items:
            pid=int(pid);qty=int(qty)
            if qty<=0:raise ValueError('Quantity must be positive')
            grouped[pid]=grouped.get(pid,0)+qty
        paid_cents=money(paid)
        with self.db:
            if customer_id is not None and not self.db.execute('SELECT 1 FROM customers WHERE id=?',(customer_id,)).fetchone():raise ValueError('Customer not found')
            lines=[];total=0
            for pid,qty in grouped.items():
                row=self.db.execute('SELECT price,qty FROM products WHERE id=?',(pid,)).fetchone()
                if not row or row[1]<qty:raise ValueError(f'Insufficient stock for product #{pid}')
                unit=money(row[0]);total+=unit*qty;lines.append((pid,qty,unit))
            if paid_cents>total:raise ValueError('Payment exceeds invoice total')
            cur=self.db.execute('INSERT INTO sales(customer_id,date,total,paid) VALUES(?,?,?,?)',(customer_id,now(),total/100,paid_cents/100))
            sid=cur.lastrowid
            for pid,qty,unit in lines:
                self.db.execute('INSERT INTO sale_items(sale_id,product_id,qty,price) VALUES(?,?,?,?)',(sid,pid,qty,unit/100))
                self.db.execute('UPDATE products SET qty=qty-? WHERE id=?',(qty,pid))
                self._move(pid,-qty,'sale',sid)
            if paid_cents:self.db.execute('INSERT INTO customer_payments VALUES(?,?,?,?,?)',(str(uuid.uuid4()),sid,paid_cents/100,method,now()))
            self.db.execute('INSERT INTO sync_outbox VALUES(?,?,?,?,?,NULL)',(str(uuid.uuid4()),'sale',str(sid),'created',now()))
            return sid,total/100,(total-paid_cents)/100
    def pay(self,sale_id,amount,method='Cash'):
        cents=money(amount)
        if cents<=0:raise ValueError('Payment must be positive')
        with self.db:
            row=self.db.execute('SELECT total,paid FROM sales WHERE id=?',(sale_id,)).fetchone()
            if not row:raise ValueError('Invoice not found')
            if cents>money(row[0])-money(row[1]):raise ValueError('Payment exceeds balance')
            self.db.execute('UPDATE sales SET paid=paid+? WHERE id=?',(cents/100,sale_id))
            self.db.execute('INSERT INTO customer_payments VALUES(?,?,?,?,?)',(str(uuid.uuid4()),sale_id,cents/100,method,now()))
            self.db.execute('INSERT INTO sync_outbox VALUES(?,?,?,?,?,NULL)',(str(uuid.uuid4()),'sale',str(sale_id),'payment',now()))
    def receive(self,supplier_id,items):
        if not items:raise ValueError('No purchase lines')
        with self.db:
            if not self.db.execute('SELECT 1 FROM suppliers WHERE id=?',(supplier_id,)).fetchone():raise ValueError('Supplier not found')
            total=0;lines=[]
            for pid,qty,cost in items:
                qty=int(qty); cents=money(cost)
                if qty<=0:raise ValueError('Quantity must be positive')
                if not self.db.execute('SELECT 1 FROM products WHERE id=?',(pid,)).fetchone():raise ValueError('Product not found')
                lines.append((pid,qty,cents));total+=qty*cents
            cur=self.db.execute('INSERT INTO purchases(supplier_id,date,total) VALUES(?,?,?)',(supplier_id,now(),total/100))
            for pid,qty,cents in lines:
                self.db.execute('INSERT INTO purchase_items(purchase_id,product_id,qty,cost) VALUES(?,?,?,?)',(cur.lastrowid,pid,qty,cents/100))
                self.db.execute('UPDATE products SET qty=qty+?,cost=? WHERE id=?',(qty,cents/100,pid))
                self._move(pid,qty,'purchase',cur.lastrowid)
            return cur.lastrowid
    def backup(self,destination):
        dest=Path(destination)
        if dest.resolve()==Path(self.path).resolve():raise ValueError('Choose a different backup path')
        out=sqlite3.connect(str(dest))
        try:
            with out:self.db.backup(out)
            if out.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Backup integrity check failed')
        finally:out.close()
