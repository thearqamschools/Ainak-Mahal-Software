"""Phase 3 extensions: login, PO lifecycle, lab tracking, printable HTML invoices."""
import hashlib, hmac, secrets, sqlite3, html
from pathlib import Path
from datetime import datetime

DDL='''
CREATE TABLE IF NOT EXISTS app_users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL, salt TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','cashier')),active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS purchase_orders(id INTEGER PRIMARY KEY,supplier_id INTEGER NOT NULL,created_at TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'Open' CHECK(status IN ('Open','Received','Cancelled')),FOREIGN KEY(supplier_id) REFERENCES suppliers(id));
CREATE TABLE IF NOT EXISTS purchase_order_lines(id INTEGER PRIMARY KEY,po_id INTEGER NOT NULL,product_id INTEGER NOT NULL,qty INTEGER NOT NULL CHECK(qty>0),unit_cost REAL NOT NULL CHECK(unit_cost>=0),FOREIGN KEY(po_id) REFERENCES purchase_orders(id),FOREIGN KEY(product_id) REFERENCES products(id));
CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY,actor TEXT NOT NULL,action TEXT NOT NULL,reference TEXT,created_at TEXT NOT NULL);
'''

def init(db):
    db.executescript(DDL)
    db.commit()

def hash_password(password,salt):
    return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),250000).hex()

def create_user(db,username,password,role='cashier'):
    if role not in ('admin','cashier') or len(password)<10 or not username.strip():raise ValueError('Username and password (minimum 10 characters) required')
    salt=secrets.token_hex(16)
    with db: db.execute('INSERT INTO app_users(username,salt,password_hash,role) VALUES(?,?,?,?)',(username.strip(),salt,hash_password(password,salt),role))

def authenticate(db,username,password):
    row=db.execute('SELECT salt,password_hash,role FROM app_users WHERE username=? AND active=1',(username,)).fetchone()
    if row and hmac.compare_digest(hash_password(password,row[0]),row[1]):return row[2]
    return None

def audit(db,actor,action,reference=''):
    db.execute('INSERT INTO audit_events(actor,action,reference,created_at) VALUES(?,?,?,?)',(actor,action,str(reference),datetime.now().isoformat(timespec='seconds')))

def create_po(store,supplier_id,lines,actor='admin'):
    from core import money,now
    if not lines:raise ValueError('Purchase order needs items')
    with store.db:
        if not store.db.execute('SELECT 1 FROM suppliers WHERE id=?',(supplier_id,)).fetchone():raise ValueError('Supplier not found')
        normalized=[]
        for pid,qty,cost in lines:
            if int(qty)!=qty or qty<=0:raise ValueError('Invalid quantity')
            if not store.db.execute('SELECT 1 FROM products WHERE id=?',(pid,)).fetchone():raise ValueError('Product not found')
            normalized.append((pid,qty,money(cost)/100))
        po=store.db.execute('INSERT INTO purchase_orders(supplier_id,created_at) VALUES(?,?)',(supplier_id,now())).lastrowid
        store.db.executemany('INSERT INTO purchase_order_lines(po_id,product_id,qty,unit_cost) VALUES(?,?,?,?)',[(po,*x) for x in normalized])
        audit(store.db,actor,'create_po',po)
        return po

def receive_po(store,po_id,actor='admin'):
    with store.db:
        row=store.db.execute('SELECT supplier_id,status FROM purchase_orders WHERE id=?',(po_id,)).fetchone()
        if not row or row[1]!='Open':raise ValueError('PO not open')
        lines=store.db.execute('SELECT product_id,qty,unit_cost FROM purchase_order_lines WHERE po_id=?',(po_id,)).fetchall()
        purchase_id=store.receive(row[0],lines)
        store.db.execute("UPDATE purchase_orders SET status='Received' WHERE id=?",(po_id,))
        audit(store.db,actor,'receive_po',po_id)
        return purchase_id

def update_job(store,job_id,status,actor='admin'):
    allowed={'Pending':{'In Lab','Cancelled'},'In Lab':{'Ready','Cancelled'},'Ready':{'Delivered'},'Delivered':set(),'Cancelled':set()}
    with store.db:
        row=store.db.execute('SELECT status FROM optical_jobs WHERE id=?',(job_id,)).fetchone()
        if not row or status not in allowed.get(row[0],set()):raise ValueError('Invalid job status transition')
        store.db.execute('UPDATE optical_jobs SET status=? WHERE id=?',(status,job_id))
        audit(store.db,actor,'job_'+status,job_id)

def invoice_html(store,sale_id):
    sale=store.db.execute('SELECT s.id,s.date,s.total,s.paid,COALESCE(c.name,"Walk-in"),COALESCE(c.phone,"") FROM sales s LEFT JOIN customers c ON c.id=s.customer_id WHERE s.id=?',(sale_id,)).fetchone()
    if not sale:raise ValueError('Invoice not found')
    items=store.db.execute('SELECT p.name,i.qty,i.price FROM sale_items i JOIN products p ON p.id=i.product_id WHERE i.sale_id=?',(sale_id,)).fetchall()
    esc=lambda v:html.escape(str(v))
    rows=''.join(f'<tr><td>{esc(n)}</td><td>{q}</td><td>Rs. {price:,.2f}</td><td>Rs. {q*price:,.2f}</td></tr>' for n,q,price in items)
    return f'''<!doctype html><html><head><meta charset="utf-8"><title>Invoice {sale_id}</title><style>body{{font:14px Arial;margin:35px;color:#172333}}h1{{margin-bottom:0}}table{{border-collapse:collapse;width:100%;margin-top:24px}}td,th{{padding:9px;border-bottom:1px solid #ccc;text-align:left}}.total{{text-align:right;margin-top:20px}}@media print{{button{{display:none}}}}</style></head><body><h1>AINAK MAHAL</h1><p>Optical Store · Millat Chowk, Faisalabad</p><h2>Invoice #{sale[0]}</h2><p>Date: {esc(sale[1])}<br>Customer: {esc(sale[4])}<br>Phone: {esc(sale[5])}</p><table><tr><th>Item</th><th>Qty</th><th>Unit price</th><th>Amount</th></tr>{rows}</table><div class="total"><p>Total: Rs. {sale[2]:,.2f}</p><p>Paid: Rs. {sale[3]:,.2f}</p><strong>Balance: Rs. {sale[2]-sale[3]:,.2f}</strong></div><p>Thank you for shopping with us.</p><button onclick="print()">Print</button></body></html>'''

def save_invoice(store,sale_id,destination):
    p=Path(destination);p.write_text(invoice_html(store,sale_id),encoding='utf-8');return p
