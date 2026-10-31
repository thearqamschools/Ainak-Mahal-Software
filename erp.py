"""ERP 2.0 application services. All older business services remain reusable."""
from pathlib import Path
from datetime import date
from decimal import Decimal
import uuid
import html
from retail import Retail,required,day,rx_number
from core import now,money
import phase3

DDL = '''
CREATE TABLE IF NOT EXISTS customer_profiles(customer_id INTEGER PRIMARY KEY REFERENCES customers(id),
 whatsapp TEXT NOT NULL DEFAULT '',doctor TEXT NOT NULL DEFAULT '',gender TEXT NOT NULL DEFAULT '',dob TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS job_specs(job_id TEXT PRIMARY KEY REFERENCES optical_jobs(id),
 kind TEXT NOT NULL,fulfillment TEXT NOT NULL DEFAULT 'Collection',supplier_id INTEGER REFERENCES suppliers(id));
CREATE TABLE IF NOT EXISTS order_links(sale_id INTEGER PRIMARY KEY REFERENCES sales(id),
 rx_id INTEGER REFERENCES prescriptions(id),job_id TEXT REFERENCES optical_jobs(id));
CREATE TABLE IF NOT EXISTS supplier_payments(id TEXT PRIMARY KEY,purchase_id INTEGER NOT NULL REFERENCES purchases(id),
 amount_cents INTEGER NOT NULL CHECK(amount_cents>0),method TEXT NOT NULL,reference TEXT NOT NULL UNIQUE,
 actor TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS purchase_openings(purchase_id INTEGER PRIMARY KEY REFERENCES purchases(id),
 paid_cents INTEGER NOT NULL CHECK(paid_cents>=0),verified INTEGER NOT NULL DEFAULT 0);
'''

class ERP(Retail):
    def __init__(self,path,actor=None,role=None):
        super().__init__(path,actor,role)
        version=self.scalar('PRAGMA user_version')
        try:
            if version<2:
                backup=Path(path).with_name(Path(path).stem+'_before_v2.db')
                if not backup.exists():self.store.backup(backup)
                with self.db:
                    for statement in DDL.strip().split(';'):
                        if statement.strip():self.db.execute(statement)
                    self.db.execute('INSERT INTO purchase_openings SELECT id,0,0 FROM purchases')
                    self.db.execute('CREATE TRIGGER purchase_opening AFTER INSERT ON purchases BEGIN INSERT INTO purchase_openings VALUES(NEW.id,0,0); END')
                    for table,key in (('customer_profiles','customer_id'),('job_specs','job_id'),('order_links','sale_id'),('supplier_payments','id'),('purchase_openings','purchase_id')):
                        for event in ('INSERT','UPDATE','DELETE'):
                            alias='OLD' if event=='DELETE' else 'NEW'
                            self.db.execute(f'''CREATE TRIGGER journal_{table}_{event} AFTER {event} ON {table} BEGIN
                              INSERT INTO sync_outbox VALUES(lower(hex(randomblob(16))),'{table}',CAST({alias}.{key} AS TEXT),
                              '{event.lower()}',strftime('%Y-%m-%dT%H:%M:%f','now'),NULL); END''')
                    self.db.execute('INSERT INTO schema_versions VALUES(2,?)',(now(),))
                    self.db.execute('PRAGMA user_version=2')
        except Exception:
            self.close();raise
    def customers(self,search=''):
        self.authorize();term='%'+search.strip()+'%'
        return self.rows('SELECT id,name,phone,address FROM customers WHERE name LIKE ? OR phone LIKE ? OR CAST(id AS TEXT)=? ORDER BY name',(term,term,search.strip()))
    def profile(self,cid):
        self.authorize()
        row=self.db.execute('SELECT whatsapp,doctor,gender,dob FROM customer_profiles WHERE customer_id=?',(cid,)).fetchone()
        return dict(zip(('whatsapp','doctor','gender','dob'),row or ('','','','')))
    def save_profile(self,cid,whatsapp='',doctor='',gender='',dob=''):
        self.authorize()
        if dob and day(dob)>date.today().isoformat():raise ValueError('Date of birth cannot be in the future')
        if gender not in ('','Male','Female','Other','Prefer not to say'):raise ValueError('Choose a valid gender value')
        with self.db:
            self.db.execute('INSERT INTO customer_profiles VALUES(?,?,?,?,?) ON CONFLICT(customer_id) DO UPDATE SET whatsapp=excluded.whatsapp,doctor=excluded.doctor,gender=excluded.gender,dob=excluded.dob',(cid,whatsapp,doctor,gender,dob))
            self.audit('customer_profile',cid)
    def customer_position(self,cid):
        self.authorize()
        ids={r[0] for r in self.rows('SELECT id FROM sales WHERE customer_id=?',(cid,))}
        invoices=[r for r in self.sales() if r[0] in ids]
        jobs=self.rows('SELECT id,description,status,due_date,sale_id FROM optical_jobs WHERE customer_id=? ORDER BY created_at DESC',(cid,))
        return invoices,self.prescriptions(cid),jobs
    def place_order(self,items,cid=None,new_customer=None,rx_id=None,rx_values=None,paid=0,method='Cash',discount=0,
                    job_description='',due='',kind='New glasses',fulfillment='Collection',supplier_id=None):
        self.authorize()
        if rx_id and rx_values:raise ValueError('Choose an existing prescription or enter a new one, rather than both')
        with self.db:
            if new_customer:
                cid=self.customer(new_customer['name'],new_customer.get('phone',''),new_customer.get('address',''))
            if (rx_id or rx_values or job_description) and not cid:raise ValueError('Select or create a customer for a prescription or optical job')
            if rx_id and not self.scalar('SELECT COUNT(*) FROM prescriptions WHERE id=? AND customer_id=?',(rx_id,cid)):
                raise ValueError('The selected prescription belongs to another customer')
            if rx_values:rx_id=self.save_rx(cid,rx_values)
            sid,total,balance=self.checkout(items,cid,paid,method,discount)
            jid=None
            if job_description:
                jid=self.create_job(cid,kind,job_description,due,sid,rx_id,fulfillment,supplier_id)
            self.db.execute('INSERT INTO order_links VALUES(?,?,?)',(sid,rx_id,jid))
            self.audit('optical_order',sid)
            return sid,total,balance,jid
    def create_job(self,cid,kind,description,due,sid=None,rid=None,fulfillment='Collection',supplier_id=None,charge=0,paid=0,method='Cash'):
        self.authorize()
        if kind not in ('New glasses','Lens replacement','Frame repair','General repair'):raise ValueError('Choose a job type')
        if fulfillment not in ('Collection','Delivery'):raise ValueError('Choose a fulfillment method')
        if supplier_id and not self.scalar('SELECT COUNT(*) FROM suppliers WHERE id=?',(supplier_id,)):raise ValueError('Supplier not found')
        with self.db:
            cents=money(charge)
            if cents:
                if sid:raise ValueError('Enter charges in the linked invoice; do not charge the same job twice')
                sid=self._repair_invoice(cid,cents,money(paid),method)
            elif money(paid):raise ValueError('A payment requires a charge or an existing invoice')
            jid=self.job(cid,description,due,sid,rid)
            self.db.execute('INSERT INTO job_specs VALUES(?,?,?,?)',(jid,kind,fulfillment,supplier_id))
            self.audit('job_details',jid)
            return jid
    def _repair_invoice(self,cid,charge,paid,method):
        rate=Decimal(self.settings().get('tax_rate','0'))
        tax=int((Decimal(charge)*rate/100).quantize(Decimal('1')));total=charge+tax
        if paid>total:raise ValueError('Advance exceeds job charges including tax')
        if method not in ('Cash','Bank','Card'):raise ValueError('Invalid payment method')
        pid=self.scalar("SELECT COALESCE((SELECT id FROM products WHERE sku='AM-REPAIR-SERVICE'),0)")
        if not pid:
            pid=self.store.add_product('AM-REPAIR-SERVICE','Optical repair service',0,0,0,'Service')
            self.db.execute('INSERT INTO product_details(product_id,is_service) VALUES(?,1)',(pid,))
        elif not self.scalar('SELECT COALESCE((SELECT is_service FROM product_details WHERE product_id=?),0)',(pid,)):
            raise ValueError('Reserved repair-service SKU conflicts with a physical product; ask the administrator to resolve it')
        sid=self.db.execute('INSERT INTO sales(customer_id,date,total,paid) VALUES(?,?,?,?)',(cid,now(),total/100,paid/100)).lastrowid
        self.db.execute('INSERT INTO sale_terms VALUES(?,?,0,?)',(sid,charge,tax))
        lid=self.db.execute('INSERT INTO sale_items(sale_id,product_id,qty,price) VALUES(?,?,1,?)',(sid,pid,total/100)).lastrowid
        self.db.execute('INSERT INTO line_costs VALUES(?,0)',(lid,))
        if paid:self.db.execute('INSERT INTO customer_payments VALUES(?,?,?,?,?)',(str(uuid.uuid4()),sid,paid/100,method,now()))
        self.audit('repair_invoice',sid)
        return sid
    def job_list(self):
        self.authorize()
        return self.rows('''SELECT j.id,c.name,COALESCE(s.kind,'New glasses'),j.description,j.status,j.due_date,j.sale_id,
          d.rx_id,COALESCE(s.fulfillment,'Collection'),COALESCE(p.name,'In-house') FROM optical_jobs j
          JOIN customers c ON c.id=j.customer_id LEFT JOIN job_specs s ON s.job_id=j.id
          LEFT JOIN job_details d ON d.job_id=j.id LEFT JOIN suppliers p ON p.id=s.supplier_id ORDER BY j.due_date''')
    def purchases(self):
        self.authorize()
        return self.rows('''SELECT p.id,s.name,p.date,p.total,
          (o.paid_cents+COALESCE((SELECT SUM(amount_cents) FROM supplier_payments WHERE purchase_id=p.id),0))/100.0,
          CASE WHEN o.verified=1 THEN ROUND(p.total-(o.paid_cents+COALESCE((SELECT SUM(amount_cents) FROM supplier_payments WHERE purchase_id=p.id),0))/100.0,2) ELSE NULL END,
          CASE WHEN o.verified=1 THEN 'Verified' ELSE 'Opening unverified' END
          FROM purchases p JOIN suppliers s ON s.id=p.supplier_id JOIN purchase_openings o ON o.purchase_id=p.id ORDER BY p.id DESC''')
    def receive(self,sid,lines):
        with self.db:
            pid=super().receive(sid,lines)
            self.db.execute('INSERT INTO purchase_openings VALUES(?,0,1) ON CONFLICT(purchase_id) DO UPDATE SET verified=1',(pid,));return pid
    def receive_po(self,po):
        with self.db:
            pid=super().receive_po(po)
            self.db.execute('INSERT INTO purchase_openings VALUES(?,0,1) ON CONFLICT(purchase_id) DO UPDATE SET verified=1',(pid,));return pid
    def confirm_supplier_opening(self,purchase_id,balance):
        self.authorize(True);cents=money(balance)
        with self.db:
            row=self.db.execute('SELECT p.total,o.verified FROM purchases p JOIN purchase_openings o ON o.purchase_id=p.id WHERE p.id=?',(purchase_id,)).fetchone()
            if not row or row[1]:raise ValueError('Only unverified legacy receipts can have their opening balance confirmed')
            if cents>money(row[0]):raise ValueError('Opening balance exceeds the original purchase total')
            self.db.execute('UPDATE purchase_openings SET paid_cents=?,verified=1 WHERE purchase_id=?',(money(row[0])-cents,purchase_id));self.audit('supplier_opening_confirmed',purchase_id)
    def supplier_payment(self,purchase_id,amount,method,reference):
        self.authorize(True);cents=money(amount);reference=required(reference,'Unique payment reference')
        if method not in ('Cash','Bank','Card'):raise ValueError('Choose a payment method')
        with self.db:
            row=self.db.execute('SELECT p.total,o.paid_cents,o.verified FROM purchases p JOIN purchase_openings o ON o.purchase_id=p.id WHERE p.id=?',(purchase_id,)).fetchone()
            if not row:raise ValueError('Purchase receipt not found')
            if not row[2]:raise ValueError('Confirm the legacy opening balance before recording a payment')
            settled=self.scalar('SELECT COALESCE(SUM(amount_cents),0) FROM supplier_payments WHERE purchase_id=?',(purchase_id,))
            if not 0<cents<=money(row[0])-row[1]-settled:raise ValueError('Payment must be positive and no more than the supplier balance')
            self.db.execute('INSERT INTO supplier_payments VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),purchase_id,cents,method,reference,self.actor,now()))
            self.audit('supplier_payment',purchase_id)
    def supplier_balances(self):
        self.authorize()
        result=[]
        for sid,name,phone in self.suppliers():
            receipts=[r for r in self.purchases() if self.scalar('SELECT supplier_id FROM purchases WHERE id=?',(r[0],))==sid]
            gross=sum(r[3] for r in receipts);paid=sum(r[4] for r in receipts);due=sum(r[5] for r in receipts if r[5] is not None)
            result.append((sid,name,phone,gross,paid,round(due,2),sum(r[6]!='Verified' for r in receipts)))
        return result
    def expected_cash(self,selected_day):
        value=super().expected_cash(selected_day)
        return value-self.scalar("SELECT COALESCE(SUM(amount_cents),0) FROM supplier_payments WHERE method='Cash' AND substr(created_at,1,10)=?",(selected_day,))
    def global_search(self,term):
        self.authorize();term=term.strip()
        if not term:return []
        found=[('Customer',r[0],r[1],r[2]) for r in self.customers(term)[:20]]
        found += [('Product',r[0],r[2],r[1]) for r in self.products(term)[:20]]
        found += [('Invoice',r[0],r[1],f'PKR {r[5]:,.2f} balance') for r in self.sales() if term.casefold() in str(r[0]).casefold() or term.casefold() in r[1].casefold()][:20]
        found += [('Job',r[0],r[1],r[3]) for r in self.job_list() if term.casefold() in ' '.join(map(str,r)).casefold()][:20]
        return found
    def report(self,kind,start,end):
        self.authorize();day(start);day(end)
        if start>end:raise ValueError('Start date must be before the end date')
        if kind=='Collections':return ('Payment ID','Invoice','Customer','PKR','Method','Date'),self.rows('''SELECT p.id,p.sale_id,COALESCE(c.name,'Walk-in'),p.amount,p.method,p.created_at
          FROM customer_payments p JOIN sales s ON s.id=p.sale_id LEFT JOIN customers c ON c.id=s.customer_id WHERE substr(p.created_at,1,10) BETWEEN ? AND ? ORDER BY p.created_at DESC''',(start,end))
        if kind=='Inventory valuation':return ('Category','Units','Cost value PKR','Retail value PKR','Potential margin PKR'),self.rows('''SELECT category,SUM(qty),ROUND(SUM(cost*qty),2),ROUND(SUM(price*qty),2),ROUND(SUM((price-cost)*qty),2)
          FROM products WHERE id NOT IN (SELECT product_id FROM product_details WHERE is_service=1) GROUP BY category''')
        if kind=='Low stock':return ('ID','SKU','Item','Available','Reorder'),self.rows('''SELECT p.id,p.sku,p.name,p.qty,COALESCE(d.reorder_level,2) FROM products p LEFT JOIN product_details d ON d.product_id=p.id
          WHERE p.qty<=COALESCE(d.reorder_level,2) AND COALESCE(d.is_service,0)=0 ORDER BY p.qty''')
        if kind=='Purchases':return ('Receipt','Supplier','Date','Total PKR','Paid PKR','Due PKR','Opening status'),[r for r in self.purchases() if start<=r[2][:10]<=end]
        if kind=='Supplier balances':return ('ID','Supplier','Phone','Purchased PKR','Paid PKR','Confirmed due PKR','Unverified receipts'),self.supplier_balances()
        if kind=='Supplier payments':return ('ID','Receipt','PKR','Method','Reference','Staff','Date'),self.rows('SELECT id,purchase_id,amount_cents/100.0,method,reference,actor,created_at FROM supplier_payments WHERE substr(created_at,1,10) BETWEEN ? AND ? ORDER BY created_at DESC',(start,end))
        return super().report(kind,start,end)
    def print_document(self,kind,identifier,directory):
        path=super().print_document(kind,identifier,directory)
        content=path.read_text(encoding='utf-8')
        import base64
        logo=Path(__file__).resolve().parent/'assets'/'brand'/'logo-light.png'
        if logo.exists():
            image='<img width="290" height="63" alt="Ainak Mahal" src="data:image/png;base64,'+base64.b64encode(logo.read_bytes()).decode('ascii')+'">'
            content=content.replace('<h1>',image+'<h1>',1)
        if kind=='Job':
            spec=self.db.execute('SELECT kind,fulfillment FROM job_specs WHERE job_id=?',(identifier,)).fetchone()
            sale=self.scalar('SELECT sale_id FROM optical_jobs WHERE id=?',(identifier,))
            if spec:content+=f'<p>Type: {html.escape(spec[0])} · Fulfillment: {html.escape(spec[1])}</p>'
            if sale:
                import phase5
                pos=phase5.invoice_position(self.store,sale)
                content+=f'<p>Charges: PKR {pos["original_total"]:,.2f} · Received: PKR {pos["payments_received"]:,.2f} · Balance: PKR {pos["net_customer_balance"]:,.2f}</p>'
        elif kind=='Invoice':
            terms=self.db.execute('SELECT subtotal_cents,discount_cents,tax_cents FROM sale_terms WHERE sale_id=?',(identifier,)).fetchone()
            if terms:
                details=f'<p>Subtotal: PKR {terms[0]/100:,.2f} · Discount: PKR {terms[1]/100:,.2f} · Tax: PKR {terms[2]/100:,.2f}</p>'
                content=content.replace('</body>',details+'</body>')
            link=self.db.execute('SELECT rx_id,job_id FROM order_links WHERE sale_id=?',(identifier,)).fetchone()
            if link:content+=f'<p>Prescription: {html.escape(str(link[0] or "None"))} · Job: {html.escape(str(link[1] or "None"))}</p>'
        path.write_text(content,encoding='utf-8');return path
