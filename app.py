"""Phase 2 desktop entry point. Tkinter bundled with standard Python on Windows."""
import tkinter as tk
from tkinter import ttk,messagebox,filedialog,simpledialog
from pathlib import Path
from core import Store
import phase3
import phase6
import webbrowser
from deployment_tools import verified_backup, reconcile_stock, reconcile_payments, export_invoice
# Authentication is established in-process by launcher.py.
# Do not accept a user/role supplied via command-line arguments.
from auth_session import current_session
session = current_session()
if session is None:
    raise PermissionError('Start Ainak Mahal using launcher.py and sign in')
class AuthenticatedUser:
    def __init__(self, user, role): self.user=user; self.role=role
args=AuthenticatedUser(session['username'],session['role'])

DATA=Path.home()/'AinakMahal';DATA.mkdir(exist_ok=True)
store=Store(DATA/'ainak_mahal.db')
phase6.init(store.db)
if not store.db.execute("SELECT 1 FROM app_users WHERE username=? AND role=? AND active=1",(args.user,args.role)).fetchone(): raise PermissionError("Unknown or inactive user")
root=tk.Tk();root.title(f'AINAK MAHAL | Offline Optical POS | {args.user} ({args.role})');root.geometry('1080x720')
style=ttk.Style();style.theme_use('clam')
ttk.Label(root,text='AINAK MAHAL   |   Millat Chowk, Faisalabad   |   OFFLINE',font=('Segoe UI',17,'bold')).pack(pady=12)
nb=ttk.Notebook(root);nb.pack(fill='both',expand=True,padx=12,pady=8)
def page(name):
    f=ttk.Frame(nb,padding=12);nb.add(f,text=name);return f
def inputs(parent,fields):
    out={}
    for i,(key,label) in enumerate(fields):
        ttk.Label(parent,text=label).grid(row=i,column=0,sticky='w',pady=4)
        e=ttk.Entry(parent,width=36);e.grid(row=i,column=1,pady=4);out[key]=e
    return out
def table(parent,cols,query):
    t=ttk.Treeview(parent,columns=cols,show='headings',height=12)
    for c in cols:t.heading(c,text=c.replace('_',' ').title());t.column(c,width=120)
    t.pack(fill='both',expand=True,pady=8)
    def refresh():
        t.delete(*t.get_children())
        for row in store.db.execute(query):t.insert('', 'end',values=row)
    refresh();return refresh
def safe(action,admin=False):
    try:
        if admin: phase4.require_role(args.role,{'admin'})
        action()
    except Exception as e:messagebox.showerror('Operation failed',str(e))

customers=page('Customers'); cf=ttk.Frame(customers);cf.pack(anchor='w')
ce=inputs(cf,[('name','Name'),('phone','Phone'),('address','Address')])
cr=table(customers,['id','name','phone','address'],'SELECT id,name,phone,address FROM customers ORDER BY id DESC')
def save_customer():
    store.add_customer(*(ce[k].get() for k in ('name','phone','address')));cr()
ttk.Button(cf,text='Save Customer',command=lambda:safe(save_customer)).grid(row=3,column=1)

products=page('Inventory');pf=ttk.Frame(products);pf.pack(anchor='w')
pe=inputs(pf,[('sku','SKU'),('name','Name'),('category','Category'),('cost','Cost'),('price','Price'),('qty','Opening Qty')])
pr=table(products,['id','sku','name','price','qty'],'SELECT id,sku,name,price,qty FROM products ORDER BY id DESC')
def save_product():
    store.add_product(pe['sku'].get(),pe['name'].get(),pe['price'].get(),pe['cost'].get() or 0,int(pe['qty'].get() or 0),pe['category'].get());pr()
ttk.Button(pf,text='Save Product',command=lambda:safe(save_product)).grid(row=6,column=1)

sales=page('Multi-item POS');sf=ttk.Frame(sales);sf.pack(anchor='w')
se=inputs(sf,[('customer','Customer ID (optional)'),('product','Product ID'),('qty','Quantity'),('paid','Amount Paid')])
cart=[];cart_label=ttk.Label(sf,text='Cart: empty');cart_label.grid(row=5,column=0,columnspan=2,sticky='w')
def add_cart():
    pid=int(se['product'].get());qty=int(se['qty'].get())
    if qty<=0 or not store.db.execute('SELECT 1 FROM products WHERE id=?',(pid,)).fetchone():raise ValueError('Invalid product or quantity')
    cart.append((pid,qty));cart_label.config(text='Cart: '+', '.join(f'#{p} x{q}' for p,q in cart))
def clear_cart():cart.clear();cart_label.config(text='Cart: empty')
def checkout():
    cid=int(se['customer'].get()) if se['customer'].get().strip() else None
    sid,total,due=store.sell(cart,cid,se['paid'].get() or 0)
    clear_cart();pr();sr();messagebox.showinfo('Invoice saved',f'Invoice #{sid}\nTotal: Rs. {total:,.2f}\nDue: Rs. {due:,.2f}')
ttk.Button(sf,text='Add to Cart',command=lambda:safe(add_cart)).grid(row=6,column=0,pady=8)
ttk.Button(sf,text='Clear Cart',command=clear_cart).grid(row=6,column=1)
ttk.Button(sf,text='Complete Sale',command=lambda:safe(checkout)).grid(row=7,column=1,pady=8)
sr=table(sales,['invoice','customer','date','total','paid','due'],"SELECT s.id,COALESCE(c.name,'Walk-in'),s.date,s.total,s.paid,ROUND(s.total-s.paid,2) FROM sales s LEFT JOIN customers c ON c.id=s.customer_id ORDER BY s.id DESC")

payments=page('Receive Payments');payf=ttk.Frame(payments);payf.pack(anchor='w')
pa=inputs(payf,[('invoice','Invoice ID'),('amount','Payment Amount'),('method','Method')])
def receive_payment():store.pay(int(pa['invoice'].get()),pa['amount'].get(),pa['method'].get() or 'Cash');sr();messagebox.showinfo('Saved','Payment recorded')
ttk.Button(payf,text='Record Payment',command=lambda:safe(receive_payment)).grid(row=3,column=1)

suppliers=page('Purchases');suf=ttk.Frame(suppliers);suf.pack(anchor='w')
sue=inputs(suf,[('name','Supplier Name'),('phone','Phone')])
def add_supplier():
    if not sue['name'].get().strip():raise ValueError('Supplier name required')
    with store.db:store.db.execute('INSERT INTO suppliers(name,phone) VALUES(?,?)',(sue['name'].get(),sue['phone'].get()))
ttk.Button(suf,text='Add Supplier',command=lambda:safe(add_supplier,admin=True)).grid(row=2,column=1)
recv=ttk.Frame(suppliers);recv.pack(anchor='w',pady=12)
re=inputs(recv,[('supplier','Supplier ID'),('product','Product ID'),('qty','Received Qty'),('cost','Unit Cost')])
def purchase():store.receive(int(re['supplier'].get()),[(int(re['product'].get()),int(re['qty'].get()),re['cost'].get())]);pr();messagebox.showinfo('Saved','Stock received')
ttk.Button(recv,text='Receive Stock',command=lambda:safe(purchase,admin=True)).grid(row=4,column=1)

rx=page('Prescriptions');rf=ttk.Frame(rx);rf.pack(anchor='w')
rxfields=['customer_id','od_sph','od_cyl','od_axis','os_sph','os_cyl','os_axis','pd','notes']
re=inputs(rf,[(k,k.replace('_',' ').upper()) for k in rxfields])
def save_rx():
    from core import now
    with store.db:store.db.execute('INSERT INTO prescriptions(customer_id,date,od_sph,od_cyl,od_axis,os_sph,os_cyl,os_axis,pd,notes) VALUES(?,?,?,?,?,?,?,?,?,?)',(int(re['customer_id'].get()),now(),*[re[k].get() for k in rxfields[1:]]))
ttk.Button(rf,text='Save Prescription',command=lambda:safe(save_rx)).grid(row=9,column=1)

jobs=page('Optical Jobs');jf=ttk.Frame(jobs);jf.pack(anchor='w')
je=inputs(jf,[('customer','Customer ID'),('description','Job Description'),('due','Due Date (YYYY-MM-DD)')])
def save_job():
    import uuid
    from core import now
    with store.db:store.db.execute('INSERT INTO optical_jobs(id,customer_id,description,due_date,created_at) VALUES(?,?,?,?,?)',(str(uuid.uuid4()),int(je['customer'].get()),je['description'].get(),je['due'].get(),now()))
    jr()
ttk.Button(jf,text='Create Job',command=lambda:safe(save_job)).grid(row=3,column=1)
jr=table(jobs,['customer','description','status','due_date'],'SELECT customer_id,description,status,due_date FROM optical_jobs ORDER BY created_at DESC')

# Phase 3: purchase orders, lab tracking and invoice printing.
po_page=page('Purchase Orders');po_form=ttk.Frame(po_page);po_form.pack(anchor='w')
po_fields=inputs(po_form,[('supplier','Supplier ID'),('product','Product ID'),('qty','Quantity'),('cost','Unit Cost'),('receive_id','PO ID to Receive')])
po_refresh=table(po_page,['po','supplier','date','status'],"SELECT id,supplier_id,created_at,status FROM purchase_orders ORDER BY id DESC")
def po_create():
    po=phase3.create_po(store,int(po_fields['supplier'].get()),[(int(po_fields['product'].get()),int(po_fields['qty'].get()),po_fields['cost'].get())]);po_refresh();messagebox.showinfo('Purchase Order',f'Created PO #{po}')
def po_receive():
    phase3.receive_po(store,int(po_fields['receive_id'].get()));po_refresh();pr();messagebox.showinfo('Received','Stock received successfully')
ttk.Button(po_form,text='Create Purchase Order',command=lambda:safe(po_create,admin=True)).grid(row=5,column=0,pady=8)
ttk.Button(po_form,text='Receive Purchase Order',command=lambda:safe(po_receive,admin=True)).grid(row=5,column=1,pady=8)
jobtrack=page('Job Tracking');jt=ttk.Frame(jobtrack);jt.pack(anchor='w')
jte=inputs(jt,[('id','Full Job ID'),('status','New Status (In Lab / Ready / Delivered / Cancelled)')])
def job_change():
    phase3.update_job(store,jte['id'].get(),jte['status'].get());jr();messagebox.showinfo('Updated','Job status updated')
ttk.Button(jt,text='Update Job Status',command=lambda:safe(job_change,admin=True)).grid(row=2,column=1)
printpage=page('Print Invoice');ip=ttk.Frame(printpage);ip.pack(anchor='w')
ie=inputs(ip,[('invoice','Invoice ID')])
def export_invoice():
    sid=int(ie['invoice'].get());path=filedialog.asksaveasfilename(defaultextension='.html',filetypes=[('Printable HTML','*.html')],initialfile=f'invoice_{sid}.html')
    if path:phase3.save_invoice(store,sid,path);webbrowser.open(Path(path).resolve().as_uri())
ttk.Button(ip,text='Save & Open Printable Invoice',command=lambda:safe(export_invoice)).grid(row=1,column=1,pady=8)

returns=page('Returns & Reports');ret=ttk.Frame(returns);ret.pack(anchor='w')
retfields=inputs(ret,[('invoice','Invoice ID'),('product','Product ID'),('qty','Return Qty'),('reason','Return Reason')])
def process_return():
    rid,refund=phase4.return_item(store,int(retfields['invoice'].get()),int(retfields['product'].get()),int(retfields['qty'].get()),retfields['reason'].get(),args.user,args.role)
    pr();messagebox.showinfo('Return Recorded',f'Return #{rid} value Rs. {refund:,.2f}\nCash refund must be handled and recorded separately.')
ttk.Button(ret,text='Record Return (Admin)',command=lambda:safe(process_return,admin=True)).grid(row=4,column=1,pady=8)
def export_report(kind):
    path=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')])
    if path:
        count=(phase4.export_sales_csv(store,path) if kind=='sales' else phase4.export_inventory_csv(store,path))
        messagebox.showinfo('Exported',f'{count} rows exported')
# Phase 7: refund settlement and payout UI (admin only).
settle_page=page('Refund Settlement')
settle_form=ttk.Frame(settle_page);settle_form.pack(anchor='w')
settle_fields=inputs(settle_form,[('invoice','Invoice ID'),('product','Product ID'),('qty','Return Qty'),('reason','Reason'),('method','Method: Cash / Bank / Credit')])
settle_result=ttk.Label(settle_page,text='');settle_result.pack(anchor='w',pady=6)
def settle_return():
    result=phase5.return_and_settle(store,int(settle_fields['invoice'].get()),int(settle_fields['product'].get()),int(settle_fields['qty'].get()),settle_fields['reason'].get(),args.user,args.role,settle_fields['method'].get().strip().title())
    pr()
    settle_result.config(text=f"Return #{result['return_id']} | Value Rs. {result['refund_value']:.2f} | Payout due Rs. {result['payout_due']:.2f} | Credit adjustment Rs. {result['credit_adjustment']:.2f}")
    messagebox.showinfo('Return settled','Settlement saved. Record payout ONLY after cash/bank refund is actually completed.')
ttk.Button(settle_form,text='Create Settled Return (Admin)',command=lambda:safe(settle_return,admin=True)).grid(row=5,column=1,pady=8)
payout_frame=ttk.Frame(settle_page);payout_frame.pack(anchor='w',pady=12)
payout_fields=inputs(payout_frame,[('return_id','Return ID'),('amount','Amount actually refunded'),('method','Cash / Bank'),('reference','Unique payment reference')])
def show_payout_status():
    result=phase6.payout_status(store,int(payout_fields['return_id'].get()))
    settle_result.config(text=f"Return refund due: Rs. {result['due']:.2f}; paid: Rs. {result['paid']:.2f}; remaining: Rs. {result['remaining']:.2f}; method: {result['method']}")
def record_payout():
    if not messagebox.askyesno('Confirm payout','Have you ALREADY paid the customer this amount by cash/bank? This action only records a completed payment.'):
        return
    phase6.record_payout(store,int(payout_fields['return_id'].get()),payout_fields['amount'].get(),payout_fields['method'].get().strip().title(),payout_fields['reference'].get(),args.user,args.role)
    show_payout_status()
    messagebox.showinfo('Recorded','Completed refund payment has been recorded.')
ttk.Button(payout_frame,text='Check Refund Balance',command=lambda:safe(show_payout_status,admin=True)).grid(row=4,column=0,pady=8)
ttk.Button(payout_frame,text='Record Completed Payout (Admin)',command=lambda:safe(record_payout,admin=True)).grid(row=4,column=1,pady=8)

ttk.Button(returns,text='Export Sales CSV',command=lambda:safe(lambda:export_report('sales'))).pack(anchor='w',pady=5)
ttk.Button(returns,text='Export Inventory CSV',command=lambda:safe(lambda:export_report('inventory'))).pack(anchor='w',pady=5)
backup=page('Backup & Summary')
summary=ttk.Label(backup,text='');summary.pack(anchor='w',pady=8)
def refresh_summary():
    q=store.db.execute
    summary.config(text=f"Customers: {q('SELECT COUNT(*) FROM customers').fetchone()[0]}\nProducts: {q('SELECT COUNT(*) FROM products').fetchone()[0]}\nInvoices: {q('SELECT COUNT(*) FROM sales').fetchone()[0]}\nUnpaid: Rs. {q('SELECT COALESCE(SUM(total-paid),0) FROM sales').fetchone()[0]:,.2f}")
def do_backup():
    path=filedialog.asksaveasfilename(defaultextension='.db',filetypes=[('SQLite database','*.db')])
    if path:store.backup(path);messagebox.showinfo('Backup','Backup saved and verified')
def open_invoice():
    sid=simpledialog.askinteger('Print Invoice','Invoice number',parent=root,minvalue=1)
    if sid:
        path=export_invoice(store.db,sid,DATA/'invoices')
        webbrowser.open(path.as_uri())
def check_data():
    stock=reconcile_stock(store.db);payments=reconcile_payments(store.db)
    messagebox.showinfo('Reconciliation',f'Stock discrepancies: {len(stock)}\nPayment discrepancies: {len(payments)}\nPlease investigate discrepancies before deployment.')
def auto_backup():
    dest=verified_backup(store,DATA/'backups')
    messagebox.showinfo('Verified Backup',f'Backup saved to: {dest}')
ttk.Button(backup,text='Refresh Summary',command=refresh_summary).pack(anchor='w')
ttk.Button(backup,text='Print / Export Invoice',command=lambda:safe(open_invoice)).pack(anchor='w')
ttk.Button(backup,text='Reconcile Stock and Payments (Admin)',command=lambda:safe(check_data,admin=True)).pack(anchor='w')
ttk.Button(backup,text='Create Timestamped Backup (Admin)',command=lambda:safe(auto_backup,admin=True)).pack(anchor='w')
ttk.Button(backup,text='Save Verified Backup',command=lambda:safe(do_backup)).pack(anchor='w')
ttk.Label(backup,text='To restore a backup, close this application and run restore_tool.py.').pack(anchor='w',pady=8)
refresh_summary()
def exit_app():store.close();root.destroy()
root.protocol('WM_DELETE_WINDOW',exit_app);root.mainloop()
