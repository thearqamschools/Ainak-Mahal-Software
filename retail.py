"""Application services and read models. UI never writes SQL directly."""
import csv
import html
import sqlite3
import uuid
import secrets
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from core import Store, money, now, quantity
from migrations import migrate
import phase3, phase4, phase5, phase6
from deployment_tools import reconcile_stock, reconcile_payments

def required(value, label):
    if not str(value).strip(): raise ValueError(f'{label} is required')
    return str(value).strip()

def day(value):
    return date.fromisoformat(value).isoformat()

def rx_number(value, low, high, step=None):
    if not str(value).strip(): return ''
    try:
        n = Decimal(str(value))
        if not n.is_finite() or not low <= n <= high or (step and n % Decimal(str(step))):
            raise ValueError('Prescription value outside the allowed range or step')
        return str(n)
    except InvalidOperation:
        raise ValueError('Enter a numeric prescription value') from None

class Retail:
    def __init__(self, path, actor=None, role=None):
        self.store = Store(path)
        self.db = self.store.db
        try:
            # Snapshot BEFORE additive upgrade, including all legacy data.
            if self.db.execute('PRAGMA user_version').fetchone()[0] == 0:
                backup = Path(path).with_name(Path(path).stem+'_before_v1.db')
                if not backup.exists(): self.store.backup(backup)
            migrate(self.store)
        except Exception:
            self.store.close()
            raise
        self.actor, self.role = actor, role

    def close(self): self.store.close()
    def rows(self, sql, args=()): return self.db.execute(sql,args).fetchall()
    def scalar(self, sql, args=()): return self.db.execute(sql,args).fetchone()[0]
    def authorize(self, admin=False):
        row = self.db.execute('SELECT role FROM app_users WHERE username=? AND active=1',(self.actor,)).fetchone()
        if not row or row[0] != self.role: raise PermissionError('Sign in with an active account')
        if admin and self.role != 'admin': raise PermissionError('Administrator access is required')
    def audit(self, action, reference=''): phase3.audit(self.db,self.actor,action,reference)
    def first_run(self): return not self.scalar('SELECT COUNT(*) FROM app_users')
    def login(self, username, password):
        role = phase3.authenticate(self.db,username.strip(),password)
        if not role: raise ValueError('Username or password is incorrect')
        self.actor, self.role = username.strip(), role
        with self.db: self.audit('sign_in')
        return role
    def bootstrap(self, username, password, confirm):
        if password != confirm: raise ValueError('Passwords do not match')
        with self.db: phase4.bootstrap_admin(self.db,username,password)
        return self.login(username,password)
    def users(self):
        self.authorize(True)
        return self.rows('SELECT id,username,role,active FROM app_users ORDER BY username')
    def create_user(self, username, password, role):
        self.authorize(True)
        with self.db:
            phase3.create_user(self.db,username,password,role)
            self.audit('create_user',username)
    def set_active(self, username, active):
        self.authorize(True)
        if username == self.actor: raise ValueError('You cannot disable your own account')
        with self.db:
            self.db.execute('UPDATE app_users SET active=? WHERE username=?',(int(active),username))
            self.audit('user_active',username)
    def change_password(self, current_password, new_password, confirm, username=None):
        """Require fresh authentication; another account can only be reset by an admin."""
        self.authorize(admin=username is not None and username != self.actor)
        if phase3.authenticate(self.db,self.actor,current_password) != self.role:
            raise ValueError('Your current password is incorrect')
        target=username if username is not None else self.actor
        if new_password != confirm: raise ValueError('Passwords do not match')
        if len(new_password)<10: raise ValueError('Use a password of at least 10 characters')
        if not self.scalar('SELECT COUNT(*) FROM app_users WHERE username=?',(target,)):
            raise ValueError('Staff account not found')
        # Reuse exactly the existing salted PBKDF2 representation.
        salt=secrets.token_hex(16);digest=phase3.hash_password(new_password,salt)
        with self.db:
            self.db.execute('UPDATE app_users SET salt=?,password_hash=? WHERE username=?',(salt,digest,target))
            self.audit('change_password' if target==self.actor else 'reset_staff_password',target)

    def search(self, query, limit=12):
        """Bounded, read-only search across people, catalog, jobs and invoices."""
        self.authorize()
        query=query.strip()
        if not query: return []
        limit=max(1,min(int(limit),30));term='%'+query+'%'
        result=[]
        sources=(
            ('Customer','Customers','SELECT id,name,COALESCE(phone,\'\') FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY name LIMIT ?', (term,term,limit)),
            ('Product','Inventory',"SELECT p.id,p.name,p.sku FROM products p LEFT JOIN product_details d ON d.product_id=p.id WHERE p.name LIKE ? OR p.sku LIKE ? OR d.barcode LIKE ? ORDER BY p.name LIMIT ?",(term,term,term,limit)),
            ('Job','Optical jobs','SELECT j.id,c.name,j.description FROM optical_jobs j JOIN customers c ON c.id=j.customer_id WHERE j.description LIKE ? OR c.name LIKE ? ORDER BY j.created_at DESC LIMIT ?',(term,term,limit)),
            ('Invoice','Payments & returns',"SELECT s.id,COALESCE(c.name,'Walk-in'),printf('PKR %.2f',s.total) FROM sales s LEFT JOIN customers c ON c.id=s.customer_id WHERE CAST(s.id AS TEXT)=? OR c.name LIKE ? ORDER BY s.id DESC LIMIT ?",(query.lstrip('#'),term,limit)))
        for kind,page,sql,args in sources:
            result.extend((kind,identifier,name,detail,page) for identifier,name,detail in self.rows(sql,args))
        return result[:limit]
    def customers(self, search=''):
        self.authorize()
        term='%'+search+'%'
        return self.rows('SELECT id,name,phone,address FROM customers WHERE name LIKE ? OR phone LIKE ? ORDER BY name',(term,term))
    def customer(self, name, phone='', address='', cid=None):
        self.authorize(); name=required(name,'Customer name')
        with self.db:
            if cid:
                self.db.execute('UPDATE customers SET name=?,phone=?,address=? WHERE id=?',(name,phone,address,cid))
            else: cid=self.store.add_customer(name,phone,address)
            self.audit('save_customer',cid)
        return cid
    def history(self, cid):
        self.authorize()
        return self.rows('SELECT id,date,total,paid FROM sales WHERE customer_id=? ORDER BY id DESC',(cid,)), self.prescriptions(cid)
    def products(self, search=''):
        self.authorize(); term='%'+search+'%'
        return self.rows('''SELECT p.id,p.sku,p.name,p.category,p.price,p.qty,COALESCE(d.barcode,''),
          COALESCE(d.variant,''),COALESCE(d.reorder_level,2),COALESCE(d.is_service,0)
          FROM products p LEFT JOIN product_details d ON d.product_id=p.id
          WHERE p.name LIKE ? OR p.sku LIKE ? OR d.barcode LIKE ? OR d.variant LIKE ? ORDER BY p.name''',(term,term,term,term))
    def product(self, sku,name,price,cost,qty,category,barcode='',variant='',sph='',cyl='',reorder=2,service=False):
        self.authorize(True)
        qty = int(qty)
        if qty < 0 or int(reorder)<0: raise ValueError('Stock and reorder level cannot be negative')
        sph=rx_number(sph,-30,30,.25); cyl=rx_number(cyl,-15,15,.25)
        with self.db:
            pid=self.store.add_product(sku.strip(),name.strip(),price,cost,qty,category)
            self.db.execute('INSERT INTO product_details VALUES(?,?,?,?,?,?,?)',
              (pid,barcode.strip() or None,variant.strip(),sph,cyl,int(reorder),int(service)))
            self.audit('create_product',pid)
        return pid
    def adjust(self, pid, delta, reason):
        self.authorize(True); reason=required(reason,'Adjustment reason')
        delta=int(delta)
        if not delta: raise ValueError('Enter a nonzero stock adjustment')
        with self.db:
            row=self.db.execute('SELECT qty FROM products WHERE id=?',(pid,)).fetchone()
            if not row or row[0]+delta<0: raise ValueError('Adjustment would make stock negative')
            self.db.execute('UPDATE products SET qty=qty+? WHERE id=?',(delta,pid))
            self.store._move(pid,delta,'adjustment',reason); self.audit('stock_adjustment',f'{pid}: {reason}')
    def edit_product(self,pid,name,price,cost,barcode,variant,reorder):
        self.authorize(True)
        p,c=money(price),money(cost);reorder=int(reorder)
        if reorder<0:raise ValueError('Reorder threshold cannot be negative')
        with self.db:
            self.db.execute('UPDATE products SET name=?,price=?,cost=? WHERE id=?',(required(name,'Name'),p/100,c/100,pid))
            self.db.execute('INSERT INTO product_details(product_id,barcode,variant,reorder_level) VALUES(?,?,?,?) ON CONFLICT(product_id) DO UPDATE SET barcode=excluded.barcode,variant=excluded.variant,reorder_level=excluded.reorder_level',(pid,barcode.strip() or None,variant,reorder))
            self.audit('edit_product',pid)
    def quote(self, items, discount=0, tax_rate=None):
        self.authorize()
        grouped={}
        for pid,qty in items: grouped[int(pid)]=grouped.get(int(pid),0)+quantity(qty)
        if not grouped: raise ValueError('Add an item to the cart')
        lines=[]; subtotal=0
        for pid,qty in grouped.items():
            row=self.db.execute('''SELECT p.name,p.price,p.cost,p.qty,COALESCE(d.is_service,0)
              FROM products p LEFT JOIN product_details d ON d.product_id=p.id WHERE p.id=?''',(pid,)).fetchone()
            if not row: raise ValueError('Product no longer exists')
            if not row[4] and row[3]<qty: raise ValueError(f'Only {row[3]} available: {row[0]}')
            unit=money(row[1]); subtotal+=unit*qty
            lines.append((pid,qty,unit,money(row[2]),row[4]))
        discount=money(discount)
        if discount>subtotal: raise ValueError('Discount exceeds subtotal')
        rate=Decimal(str(tax_rate if tax_rate is not None else self.settings().get('tax_rate','0')))
        if not rate.is_finite() or not 0<=rate<=100: raise ValueError('Tax rate must be between 0 and 100')
        tax=int((Decimal(subtotal-discount)*rate/100).quantize(Decimal('1')))
        return lines,subtotal,discount,tax,subtotal-discount+tax
    def checkout(self, items,cid=None,paid=0,method='Cash',discount=0):
        self.authorize()
        if method not in ('Cash','Bank','Card'): raise ValueError('Select a valid payment method')
        with self.db:
            lines,sub,disc,tax,total=self.quote(items,discount)
            cents=money(paid)
            if cents>total: raise ValueError('Payment exceeds total; enter the amount retained')
            if cents<total and not cid: raise ValueError('Select a customer for an unpaid balance')
            if cid and not self.scalar('SELECT COUNT(*) FROM customers WHERE id=?',(cid,)): raise ValueError('Customer not found')
            sid=self.db.execute('INSERT INTO sales(customer_id,date,total,paid) VALUES(?,?,?,?)',(cid,now(),total/100,cents/100)).lastrowid
            self.db.execute('INSERT INTO sale_terms VALUES(?,?,?,?)',(sid,sub,disc,tax))
            # Allocate final invoice value by cents; per-unit lines make returns exact after discount/tax.
            allocated=0; units=sum(q for _,q,_,_,_ in lines); index=0
            for pid,qty,unit,cost,service in lines:
                for _ in range(qty):
                    index+=1
                    value=total-allocated if index==units else (unit*total//sub if sub else 0)
                    allocated+=value
                    lid=self.db.execute('INSERT INTO sale_items(sale_id,product_id,qty,price) VALUES(?,?,1,?)',(sid,pid,value/100)).lastrowid
                    self.db.execute('INSERT INTO line_costs VALUES(?,?)',(lid,cost))
                if not service:
                    self.db.execute('UPDATE products SET qty=qty-? WHERE id=?',(qty,pid)); self.store._move(pid,-qty,'sale',sid)
            if cents: self.db.execute('INSERT INTO customer_payments VALUES(?,?,?,?,?)',(str(uuid.uuid4()),sid,cents/100,method,now()))
            self.audit('checkout',sid)
        return sid,total/100,(total-cents)/100
    def sales(self):
        self.authorize()
        rows=self.rows('''SELECT s.id,COALESCE(c.name,'Walk-in'),s.date,s.total,s.paid
          FROM sales s LEFT JOIN customers c ON c.id=s.customer_id ORDER BY s.id DESC''')
        return [(*r,phase5.invoice_position(self.store,r[0])['net_customer_balance']) for r in rows]
    def redeem_credit(self,source,target,amount):
        self.authorize(True);cents=money(amount)
        if source==target:raise ValueError('Choose a different destination invoice')
        with self.db:
            a=self.db.execute('SELECT customer_id FROM sales WHERE id=?',(source,)).fetchone()
            b=self.db.execute('SELECT customer_id FROM sales WHERE id=?',(target,)).fetchone()
            if not a or not b or not a[0] or a[0]!=b[0]:raise ValueError('Both invoices must belong to the same named customer')
            available=-phase5.invoice_position(self.store,source)['net_customer_balance']
            due=phase5.invoice_position(self.store,target)['net_customer_balance']
            if not 0<cents<=min(money(max(0,available)),money(max(0,due))):raise ValueError('Amount exceeds available credit or target balance')
            self.db.execute('INSERT INTO credit_transfers VALUES(?,?,?,?,?,?)',(str(uuid.uuid4()),source,target,cents,self.actor,now()));self.audit('redeem_credit',f'{source} to {target}')
    def pay(self,sid,amount,method):
        self.authorize(); cents=money(amount)
        if method not in ('Cash','Bank','Card'): raise ValueError('Invalid method')
        with self.db:
            balance=money(max(0,phase5.invoice_position(self.store,sid)['net_customer_balance']))
            if not 0<cents<=balance: raise ValueError('Payment must be positive and no more than the balance')
            self.db.execute('UPDATE sales SET paid=ROUND(paid+?,2) WHERE id=?',(cents/100,sid))
            self.db.execute('INSERT INTO customer_payments VALUES(?,?,?,?,?)',(str(uuid.uuid4()),sid,cents/100,method,now()))
            self.audit('payment',sid)
    def save_rx(self,cid,values,rx_date=None):
        self.authorize(); normalized={}
        for eye in ('od','os'):
            for field,low,high,step in (('sph',-30,30,.25),('cyl',-15,15,.25),('axis',0,180,1),('add',0,6,.25)):
                key=f'{eye}_{field}'; normalized[key]=rx_number(values.get(key,''),low,high,step)
            if normalized[f'{eye}_cyl'] and Decimal(normalized[f'{eye}_cyl']) and not normalized[f'{eye}_axis']:
                raise ValueError(f'{eye.upper()} axis is required when cylinder is entered')
        pd=rx_number(values.get('pd',''),20,80,.5)
        with self.db:
            rid=self.db.execute('''INSERT INTO prescriptions(customer_id,date,od_sph,od_cyl,od_axis,os_sph,os_cyl,os_axis,pd,notes)
              VALUES(?,?,?,?,?,?,?,?,?,?)''',(cid,day(rx_date or date.today().isoformat()),*[normalized[k] for k in ('od_sph','od_cyl','od_axis','os_sph','os_cyl','os_axis')],pd,values.get('notes',''))).lastrowid
            self.db.execute('INSERT INTO rx_details VALUES(?,?,?)',(rid,normalized['od_add'],normalized['os_add'])); self.audit('prescription',rid)
        return rid
    def prescriptions(self,cid=None):
        self.authorize()
        return self.rows('''SELECT r.id,r.customer_id,r.date,r.od_sph,r.od_cyl,r.od_axis,COALESCE(d.od_add,''),
          r.os_sph,r.os_cyl,r.os_axis,COALESCE(d.os_add,''),r.pd,r.notes FROM prescriptions r
          LEFT JOIN rx_details d ON d.rx_id=r.id'''+(' WHERE r.customer_id=?' if cid else '')+' ORDER BY r.id DESC', (cid,) if cid else ())
    def job(self,cid,description,due,sid=None,rid=None):
        self.authorize(); description=required(description,'Job description'); due=day(due)
        with self.db:
            for table,ref in (('sales',sid),('prescriptions',rid)):
                if ref and not self.scalar(f'SELECT COUNT(*) FROM {table} WHERE id=? AND customer_id=?',(ref,cid)):
                    raise ValueError('Sale and prescription must belong to the selected customer')
            jid=str(uuid.uuid4())
            self.db.execute('INSERT INTO optical_jobs(id,customer_id,sale_id,description,due_date,created_at) VALUES(?,?,?,?,?,?)',(jid,cid,sid,description,due,now()))
            self.db.execute('INSERT INTO job_details(job_id,rx_id) VALUES(?,?)',(jid,rid)); self.audit('create_job',jid)
        return jid
    def jobs(self):
        self.authorize()
        return self.rows('''SELECT j.id,c.name,j.description,j.status,j.due_date,j.sale_id,d.rx_id
          FROM optical_jobs j JOIN customers c ON c.id=j.customer_id LEFT JOIN job_details d ON d.job_id=j.id ORDER BY j.due_date''')
    def advance_job(self,jid,status):
        self.authorize()
        with self.db:
            row=self.db.execute('SELECT sale_id FROM optical_jobs WHERE id=?',(jid,)).fetchone()
            if status=='Delivered' and row and row[0] and phase5.invoice_position(self.store,row[0])['net_customer_balance']>0:
                raise ValueError('Collect the outstanding balance before delivery')
            phase3.update_job(self.store,jid,status,self.actor)
            if status=='Delivered': self.db.execute('UPDATE job_details SET delivered_at=? WHERE job_id=?',(now(),jid))
    def suppliers(self):
        self.authorize(); return self.rows('SELECT id,name,phone FROM suppliers ORDER BY name')
    def supplier(self,name,phone):
        self.authorize(True)
        with self.db:
            sid=self.db.execute('INSERT INTO suppliers(name,phone) VALUES(?,?)',(required(name,'Supplier name'),phone)).lastrowid
            self.audit('supplier',sid)
        return sid
    def create_po(self,sid,lines):
        self.authorize(True); return phase3.create_po(self.store,sid,lines,self.actor)
    def receive_po(self,po):
        self.authorize(True); return phase3.receive_po(self.store,po,self.actor)
    def purchase_orders(self):
        self.authorize()
        return self.rows('SELECT p.id,s.name,p.created_at,p.status FROM purchase_orders p JOIN suppliers s ON s.id=p.supplier_id ORDER BY p.id DESC')
    def receive(self,sid,lines):
        self.authorize(True)
        with self.db:
            pid=self.store.receive(sid,lines); self.audit('goods_receipt',pid)
        return pid
    def expense(self,description,amount):
        self.authorize(True); cents=money(amount)
        if not cents: raise ValueError('Expense must be positive')
        with self.db:
            eid=self.db.execute('INSERT INTO expenses(date,description,amount) VALUES(?,?,?)',(now(),required(description,'Description'),cents/100)).lastrowid
            self.audit('expense',eid)
        return eid
    def cash(self,kind,amount,note):
        self.authorize(True); cents=money(amount)
        if kind not in ('Opening','Cash in','Cash out') or not cents: raise ValueError('Choose a valid movement and positive amount')
        with self.db:
            self.db.execute('INSERT INTO cash_movements VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),date.today().isoformat(),kind,cents,required(note,'Reason'),self.actor,now())); self.audit('cash_movement',note)
    def expected_cash(self,selected_day):
        day(selected_day)
        collections=self.scalar("SELECT COALESCE(SUM(amount),0) FROM customer_payments WHERE method='Cash' AND substr(created_at,1,10)=?",(selected_day,))
        refunds=self.scalar("SELECT COALESCE(SUM(amount_cents),0) FROM refund_payouts WHERE method='Cash' AND substr(created_at,1,10)=?",(selected_day,))
        expenses=self.scalar('SELECT COALESCE(SUM(amount),0) FROM expenses WHERE substr(date,1,10)=?',(selected_day,))
        moves=self.scalar("SELECT COALESCE(SUM(CASE WHEN kind='Cash out' THEN -amount_cents ELSE amount_cents END),0) FROM cash_movements WHERE day=?",(selected_day,))
        return money(round(collections,2))-refunds-money(round(expenses,2))+moves
    def close_day(self,selected_day,counted,note):
        self.authorize(True)
        with self.db:
            expected=self.expected_cash(selected_day)
            self.db.execute('INSERT INTO daily_closings VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),day(selected_day),expected,money(counted),note,self.actor,now())); self.audit('daily_closing',selected_day)
        return expected/100
    def return_item(self,sid,pid,qty,reason,method):
        self.authorize(True)
        service=self.scalar('SELECT COALESCE((SELECT is_service FROM product_details WHERE product_id=?),0)',(pid,))
        qty=quantity(qty)
        with self.db:
            skip=self.scalar('SELECT COALESCE(SUM(qty),0) FROM sale_returns WHERE sale_id=? AND product_id=?',(sid,pid))
            needed=qty;cost=0
            for units,cents in self.rows('''SELECT i.qty,COALESCE(c.unit_cost_cents,CAST(ROUND(p.cost*100) AS INTEGER))
              FROM sale_items i JOIN products p ON p.id=i.product_id LEFT JOIN line_costs c ON c.line_id=i.id
              WHERE i.sale_id=? AND i.product_id=? ORDER BY i.id''',(sid,pid)):
                ignored=min(skip,units);skip-=ignored;take=min(needed,units-ignored);cost+=take*cents;needed-=take
                if not needed:break
            result=phase5.return_and_settle(self.store,sid,pid,qty,reason,self.actor,self.role,method,not service)
            tax=self.scalar('SELECT COALESCE((SELECT tax_cents FROM sale_terms WHERE sale_id=?),0)',(sid,))
            total=money(self.scalar('SELECT total FROM sales WHERE id=?',(sid,)))
            returned=money(self.scalar('SELECT ROUND(COALESCE(SUM(refund),0),2) FROM sale_returns WHERE sale_id=?',(sid,)))
            previous_tax=self.scalar('SELECT COALESCE(SUM(v.tax_cents),0) FROM return_values v JOIN sale_returns r ON r.id=v.return_id WHERE r.sale_id=?',(sid,))
            tax_returned=max(0,(tax*returned//total if total else 0)-previous_tax)
            self.db.execute('INSERT INTO return_values VALUES(?,?,?)',(result['return_id'],cost,tax_returned))
            return result
    def payout(self,rid,amount,method,reference):
        self.authorize(True); return phase6.record_payout(self.store,rid,amount,method,reference,self.actor,self.role)
    def settings(self): return dict(self.rows('SELECT key,value FROM app_settings'))
    def save_settings(self,values):
        self.authorize(True)
        rate=Decimal(values.get('tax_rate','0'))
        if not rate.is_finite() or not 0<=rate<=100: raise ValueError('Tax rate must be between 0 and 100')
        if values.get('receipt_format','A4') not in ('A4','80 mm'): raise ValueError('Select A4 or 80 mm receipt format')
        with self.db:
            self.db.executemany('INSERT INTO app_settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',values.items()); self.audit('settings')
    def dashboard(self):
        self.authorize(); today=date.today().isoformat()
        return {
          'Sales today':self.scalar('SELECT COALESCE(SUM(total),0) FROM sales WHERE substr(date,1,10)=?',(today,)),
          'Collections today':self.scalar('SELECT COALESCE(SUM(amount),0) FROM customer_payments WHERE substr(created_at,1,10)=?',(today,)),
          'Balances due':sum(max(0,r[5]) for r in self.sales()),
          'Low stock':self.scalar('''SELECT COUNT(*) FROM products p LEFT JOIN product_details d ON d.product_id=p.id
           WHERE p.qty<=COALESCE(d.reorder_level,2) AND COALESCE(d.is_service,0)=0'''),
          'Pending jobs':self.scalar("SELECT COUNT(*) FROM optical_jobs WHERE status IN ('Pending','In Lab')"),
          'Ready for pickup':self.scalar("SELECT COUNT(*) FROM optical_jobs WHERE status='Ready'")}
    def report(self,kind,start,end):
        self.authorize(); day(start);day(end)
        if start>end: raise ValueError('Start date must be before the end date')
        if kind=='Sales': return ('Invoice','Customer','Date','Total PKR','Paid PKR','Due PKR'),[r for r in self.sales() if start<=r[2][:10]<=end]
        if kind=='Stock': return ('ID','SKU','Name','Category','Price PKR','Stock','Barcode','Variant','Reorder','Service'),self.products()
        if kind=='Low stock':
            return ('ID','SKU','Name','Category','Price PKR','Stock','Barcode','Variant','Reorder','Service'),[r for r in self.products() if not r[9] and r[5]<=r[8]]
        if kind=='Stock valuation':
            return ('SKU','Product','Units','Unit cost PKR','Value PKR'),self.rows('''SELECT p.sku,p.name,p.qty,p.cost,ROUND(p.qty*p.cost,2)
              FROM products p LEFT JOIN product_details d ON d.product_id=p.id WHERE COALESCE(d.is_service,0)=0 ORDER BY p.name''')
        if kind=='Purchases':
            return ('Receipt','Supplier','Date','Total PKR'),self.rows('''SELECT p.id,COALESCE(s.name,'Unknown'),p.date,p.total
              FROM purchases p LEFT JOIN suppliers s ON s.id=p.supplier_id WHERE substr(p.date,1,10) BETWEEN ? AND ? ORDER BY p.id DESC''',(start,end))
        if kind=='Collections':
            return ('Invoice','Customer','Received','Method','Amount PKR'),self.rows('''SELECT p.sale_id,COALESCE(c.name,'Walk-in'),p.created_at,p.method,p.amount
              FROM customer_payments p JOIN sales s ON s.id=p.sale_id LEFT JOIN customers c ON c.id=s.customer_id
              WHERE substr(p.created_at,1,10) BETWEEN ? AND ? ORDER BY p.created_at DESC''',(start,end))
        if kind=='Customer dues': return ('Invoice','Customer','Date','Total PKR','Paid PKR','Due PKR'),[r for r in self.sales() if r[5]>0]
        if kind=='Expenses': return ('Date','Description','PKR'),self.rows('SELECT date,description,amount FROM expenses WHERE substr(date,1,10) BETWEEN ? AND ?',(start,end))
        if kind=='Cash closing': return ('Day','Expected PKR','Counted PKR','Variance PKR','Note','Actor'),self.rows('SELECT day,expected_cents/100.0,counted_cents/100.0,(counted_cents-expected_cents)/100.0,note,actor FROM daily_closings WHERE day BETWEEN ? AND ?',(start,end))
        if kind=='Profit':
            gross=self.scalar('SELECT COALESCE(SUM(total),0) FROM sales WHERE substr(date,1,10) BETWEEN ? AND ?',(start,end))
            returns=self.scalar('SELECT COALESCE(SUM(refund),0) FROM sale_returns WHERE substr(created_at,1,10) BETWEEN ? AND ?',(start,end))
            cost=self.scalar('''SELECT COALESCE(SUM(i.qty*COALESCE(l.unit_cost_cents/100.0,p.cost)),0)
              FROM sale_items i JOIN sales s ON s.id=i.sale_id JOIN products p ON p.id=i.product_id
              LEFT JOIN line_costs l ON l.line_id=i.id WHERE substr(s.date,1,10) BETWEEN ? AND ?''',(start,end))
            recovered=self.scalar('''SELECT COALESCE(SUM(COALESCE(v.cost_cents/100.0,r.qty*p.cost)),0)
              FROM sale_returns r JOIN products p ON p.id=r.product_id LEFT JOIN return_values v ON v.return_id=r.id
              WHERE substr(r.created_at,1,10) BETWEEN ? AND ?''',(start,end))
            expense=self.scalar('SELECT COALESCE(SUM(amount),0) FROM expenses WHERE substr(date,1,10) BETWEEN ? AND ?',(start,end))
            tax=self.scalar('SELECT COALESCE(SUM(t.tax_cents),0)/100.0 FROM sale_terms t JOIN sales s ON s.id=t.sale_id WHERE substr(s.date,1,10) BETWEEN ? AND ?',(start,end))
            tax-=self.scalar('SELECT COALESCE(SUM(v.tax_cents),0)/100.0 FROM return_values v JOIN sale_returns r ON r.id=v.return_id WHERE substr(r.created_at,1,10) BETWEEN ? AND ?',(start,end))
            return ('Metric','PKR'),[('Invoice sales',gross),('Returns',returns),('Tax collected',tax),('Cost of goods',cost-recovered),('Expenses',expense),('Estimated profit',gross-returns-tax-cost+recovered-expense)]
        raise ValueError('Unknown report')
    def export_csv(self,path,columns,rows):
        self.authorize()
        def cell(v):
            # Prevent spreadsheet formula execution in untrusted names/notes.
            return "'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v
        with Path(path).open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.writer(f);w.writerow(columns);w.writerows([[cell(v) for v in row] for row in rows])
    def reconcile(self):
        self.authorize(True);return reconcile_stock(self.db),reconcile_payments(self.db)
    def backup(self,path):
        self.authorize(True);self.store.backup(path)
        with self.db:self.audit('backup',str(path))
    def print_document(self,kind,identifier,directory):
        self.authorize(); settings=self.settings(); esc=lambda v:html.escape(str(v if v is not None else ''))
        if kind=='Invoice':
            from deployment_tools import invoice_html
            content=invoice_html(self.db,identifier,settings.get('shop_name','AINAK MAHAL'),settings.get('address','Millat Chowk, Faisalabad'))
            position=phase5.invoice_position(self.store,identifier)
            content=content.replace('</body>',f'<p>Returns: PKR {position["return_value"]:,.2f} · Adjusted balance: PKR {position["net_customer_balance"]:,.2f}</p></body>')
        elif kind=='Prescription':
            rx=next((r for r in self.prescriptions() if r[0]==identifier),None)
            if not rx: raise ValueError('Prescription not found')
            customer=self.db.execute('SELECT name,phone FROM customers WHERE id=?',(rx[1],)).fetchone()
            content=f'<h2>Prescription #{rx[0]}</h2><p>{esc(customer[0])} · {esc(customer[1])} · {esc(rx[2])}</p><table><tr><th>Eye</th><th>SPH</th><th>CYL</th><th>AXIS</th><th>ADD</th></tr>'
            for eye,values in (('OD (right)',rx[3:7]),('OS (left)',rx[7:11])):
                content+='<tr><th>'+eye+'</th>'+''.join('<td>'+esc(v)+'</td>' for v in values)+'</tr>'
            content+=f'</table><p>PD: {esc(rx[11])} mm</p><p>{esc(rx[12])}</p>'
        else:
            job=next((r for r in self.jobs() if r[0]==identifier),None)
            if not job: raise ValueError('Job not found')
            content='<h2>Optical job slip</h2>'+''.join(f'<p><b>{label}:</b> {esc(v)}</p>' for label,v in zip(('Job','Customer','Instructions','Status','Promised date','Invoice','Prescription'),job))
        if kind!='Invoice':
            content=f'<!doctype html><meta charset="utf-8"><title>{esc(kind)}</title><style>body{{font:16px Segoe UI;margin:32px;color:#17263d}}td,th{{padding:12px;border:1px solid #ccc}}table{{border-collapse:collapse}}@media print{{button{{display:none}}}}</style><h1>{esc(settings.get("shop_name","AINAK MAHAL"))}</h1>'+content+'<button onclick="print()">Print</button>'
        from brand import print_mark
        content=content.replace('<h1>',print_mark()+'<h1>',1)
        if settings.get('receipt_format')=='80 mm' and kind=='Invoice': content=content.replace('</style>','body{max-width:72mm;margin:4mm;font-size:11px}td,th{padding:3px}@page{size:80mm auto;margin:4mm}</style>')
        directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
        path=directory/f'{kind.lower()}_{identifier}.html';path.write_text(content,encoding='utf-8');return path
