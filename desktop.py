"""Native Windows desktop presentation. All mutations go through Retail services."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date
from pathlib import Path
import webbrowser
import sqlite3
from retail import Retail
from paths import data_dir

NAVY='#142D4E'; BG='#F4F6F8'; MUTED='#536278'; WHITE='#FFFFFF'

def error_copy(error):
    if isinstance(error,sqlite3.IntegrityError):
        return 'This record conflicts with existing data. Check for a duplicate SKU, barcode, username, payment reference or closing date. Linked records must exist.'
    if isinstance(error,sqlite3.OperationalError):
        return 'The database could not complete this action. Close other copies of Ainak Mahal, check disk space and try again. Your transaction was not saved.'
    return str(error)

def theme(root):
    root.configure(bg=BG)
    root.option_add('*Font',('Segoe UI',10))
    s=ttk.Style(root);s.theme_use('clam')
    s.configure('.',font=('Segoe UI',10),background=BG,foreground=NAVY)
    s.configure('TFrame',background=BG);s.configure('Card.TFrame',background=WHITE)
    s.configure('TLabel',background=BG);s.configure('Muted.TLabel',foreground=MUTED)
    s.configure('Title.TLabel',font=('Segoe UI',25,'bold'))
    s.configure('Card.TLabel',background=WHITE)
    s.configure('Metric.TLabel',background=WHITE,font=('Segoe UI',24,'bold'))
    s.configure('TButton',padding=(14,9),background=WHITE,borderwidth=1)
    s.map('TButton',background=[('active','#E5ECF4')])
    s.configure('Primary.TButton',background=NAVY,foreground=WHITE)
    s.map('Primary.TButton',background=[('active','#244C7C'),('disabled','#CBD5E1')],foreground=[('disabled','#536278')])
    s.configure('TEntry',padding=7,fieldbackground=WHITE)
    s.configure('TCombobox',padding=7,fieldbackground=WHITE)
    s.configure('Treeview',background=WHITE,fieldbackground=WHITE,rowheight=36,borderwidth=0)
    s.map('Treeview',background=[('selected',NAVY)],foreground=[('selected',WHITE)])
    s.configure('Treeview.Heading',background='#E8EDF3',font=('Segoe UI',10,'bold'),padding=8)

class Grid:
    def __init__(self,parent,columns,rows=(),height=12):
        self.frame=ttk.Frame(parent);self.frame.pack(fill='both',expand=True,pady=10)
        self.tree=ttk.Treeview(self.frame,columns=list(range(len(columns))),show='headings',height=height,selectmode='browse')
        for i,label in enumerate(columns):
            self.tree.heading(i,text=label);self.tree.column(i,width=130,minwidth=70,stretch=True)
        y=ttk.Scrollbar(self.frame,orient='vertical',command=self.tree.yview)
        x=ttk.Scrollbar(self.frame,orient='horizontal',command=self.tree.xview)
        self.tree.configure(yscrollcommand=y.set,xscrollcommand=x.set)
        self.tree.grid(row=0,column=0,sticky='nsew');y.grid(row=0,column=1,sticky='ns');x.grid(row=1,column=0,sticky='ew')
        self.frame.rowconfigure(0,weight=1);self.frame.columnconfigure(0,weight=1)
        self.data={};self.replace(rows)
    def replace(self,rows):
        self.tree.delete(*self.tree.get_children());self.data={}
        for i,row in enumerate(rows):
            self.tree.insert('','end',iid=str(i),values=['—' if v is None or v=='' else v for v in row]);self.data[str(i)]=row
    def selected(self):
        ids=self.tree.selection()
        if not ids:raise ValueError('Select a row first')
        return self.data[ids[0]]

class Dialog:
    def __init__(self,app,title,fields,on_save,help_text=''):
        self.app=app;self.win=tk.Toplevel(app.root);self.win.title(title);self.win.transient(app.root)
        self.win.geometry('560x650');self.win.minsize(460,400)
        self.values={};self.lookups={}
        shell=ttk.Frame(self.win,padding=24);shell.pack(fill='both',expand=True)
        ttk.Label(shell,text=title,font=('Segoe UI',18,'bold')).pack(anchor='w')
        if help_text:ttk.Label(shell,text=help_text,wraplength=480,style='Muted.TLabel').pack(anchor='w',pady=8)
        canvas=tk.Canvas(shell,bg=BG,highlightthickness=0);scroll=ttk.Scrollbar(shell,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');canvas.pack(fill='both',expand=True,pady=12)
        form=ttk.Frame(canvas);window=canvas.create_window((0,0),window=form,anchor='nw')
        form.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
        first=None
        eye_grid=None
        for spec in fields:
            key,label,*rest=spec; options=rest[0] if rest else '';default=rest[1] if len(rest)>1 else ''
            if key in ('od_sph','od_cyl','od_axis','od_add','os_sph','os_cyl','os_axis','os_add'):
                if eye_grid is None:
                    eye_grid=ttk.Frame(form);eye_grid.pack(fill='x',pady=16)
                    for col,text in enumerate(('Eye','SPH','CYL','AXIS','ADD')):
                        ttk.Label(eye_grid,text=text,font=('Segoe UI',10,'bold')).grid(row=0,column=col,padx=4,pady=6)
                    ttk.Label(eye_grid,text='OD · Right').grid(row=1,column=0,sticky='w',padx=4)
                    ttk.Label(eye_grid,text='OS · Left').grid(row=2,column=0,sticky='w',padx=4)
                eye,field=key.split('_');var=tk.StringVar(value=str(default));self.values[key]=var
                col=('sph','cyl','axis','add').index(field)+1
                entry=ttk.Entry(eye_grid,textvariable=var,width=7)
                entry.grid(row=1 if eye=='od' else 2,column=col,padx=3,pady=6,sticky='ew');eye_grid.columnconfigure(col,weight=1)
                continue
            ttk.Label(form,text=label).pack(anchor='w',pady=(8,3))
            var=tk.StringVar(value=str(default));self.values[key]=var
            if isinstance(options,(list,tuple,dict)):
                if isinstance(options,dict): self.lookups[key]=options;choices=list(options)
                else: choices=list(options)
                widget=ttk.Combobox(form,textvariable=var,values=choices,state='readonly')
                if choices and not default:var.set(choices[0])
            else: widget=ttk.Entry(form,textvariable=var,show='*' if options=='password' else '')
            widget.pack(fill='x')
            if first is None:first=widget
        self.error=ttk.Label(shell,text='',foreground='#A52A24',wraplength=480);self.error.pack(fill='x',pady=6)
        buttons=ttk.Frame(shell);buttons.pack(fill='x')
        ttk.Button(buttons,text='Cancel',command=self.win.destroy).pack(side='left')
        def save():
            try:
                values={k:self.lookups[k].get(v.get()) if k in self.lookups else v.get() for k,v in self.values.items()}
                on_save(values);self.win.destroy()
                app.notice.set(title+' saved.');app.refresh()
            except Exception as e:
                self.error.configure(text=error_copy(e));self.win.bell()
        ttk.Button(buttons,text='Save',style='Primary.TButton',command=save).pack(side='right')
        self.win.bind('<Escape>',lambda e:self.win.destroy());self.win.bind('<Control-Return>',lambda e:save())
        self.win.grab_set()
        if first:first.focus_set()

class Desktop:
    PAGES=('Overview','Checkout','Customers','Prescriptions','Inventory','Optical jobs','Purchasing','Payments & returns','Cash & expenses','Reports','Settings & team','Backup & recovery')
    def __init__(self,root,service):
        self.root=root;self.s=service;self.cart=[];self.current='Overview';self.notice=tk.StringVar(value='Ready. All changes are saved on this computer.')
        theme(root);root.title('Ainak Mahal · Optical store');root.geometry('1280x850');root.minsize(1050,700)
        sidebar=tk.Frame(root,bg=NAVY,width=220);sidebar.pack(side='left',fill='y');sidebar.pack_propagate(False)
        tk.Label(sidebar,text='AINAK\nMAHAL',bg=NAVY,fg=WHITE,font=('Segoe UI',23,'bold'),justify='left').pack(anchor='w',padx=22,pady=(28,2))
        tk.Label(sidebar,text='OPTICAL STORE',bg=NAVY,fg='#B9CBE0',font=('Segoe UI',9)).pack(anchor='w',padx=24,pady=(0,26))
        self.nav={}
        for name in self.PAGES:
            b=tk.Button(sidebar,text=name,anchor='w',bg=NAVY,fg=WHITE,activebackground='#294968',activeforeground=WHITE,
              relief='flat',borderwidth=0,padx=22,pady=10,command=lambda n=name:self.show(n),takefocus=True)
            b.pack(fill='x',padx=8,pady=1);self.nav[name]=b
        tk.Label(sidebar,text=f'●  Offline · {service.role}\n{service.actor}',bg=NAVY,fg='#BDDFD0',justify='left').pack(side='bottom',anchor='w',padx=24,pady=22)
        outer=ttk.Frame(root,padding=(28,20));outer.pack(side='left',fill='both',expand=True)
        self.heading=ttk.Label(outer,style='Title.TLabel');self.heading.pack(anchor='w')
        self.sub=ttk.Label(outer,style='Muted.TLabel');self.sub.pack(anchor='w',pady=(5,16))
        self.body=ttk.Frame(outer);self.body.pack(fill='both',expand=True)
        ttk.Label(outer,textvariable=self.notice,style='Muted.TLabel',wraplength=960).pack(anchor='w',pady=(12,0))
        root.bind('<F2>',lambda e:self.show('Checkout'));root.bind('<F3>',lambda e:self.show('Customers'))
        root.bind('<Control-Return>',lambda e:self.complete() if self.current=='Checkout' else None)
        root.protocol('WM_DELETE_WINDOW',self.exit);self.show('Overview')
    def exit(self):
        if self.cart and not messagebox.askyesno('Unsaved cart','Discard the current cart and close Ainak Mahal?',parent=self.root):return
        self.s.close();self.root.destroy()
    def safe(self,action):
        try:return action()
        except Exception as e:messagebox.showerror('Could not complete action',error_copy(e),parent=self.root)
    def button(self,parent,text,action,primary=False):
        b=ttk.Button(parent,text=text,command=lambda:self.safe(action),style='Primary.TButton' if primary else 'TButton');b.pack(side='left',padx=(0,8),pady=4);return b
    def toolbar(self):
        f=ttk.Frame(self.body);f.pack(fill='x',pady=(0,4));return f
    def refresh(self):self.show(self.current)
    def show(self,name):
        self.current=name
        for child in self.body.winfo_children():child.destroy()
        for n,b in self.nav.items():b.configure(bg='#2A496C' if n==name else NAVY)
        self.heading.configure(text=name)
        self.sub.configure(text={
          'Overview':'Your shop at a glance · '+date.today().strftime('%A, %d %B %Y'),
          'Checkout':'F2 checkout · Scan a barcode or search by name · Ctrl+Enter to save sale',
          'Customers':'Find a customer by name or mobile. Keep their sales and prescriptions together.',
          'Prescriptions':'OD = right eye · OS = left eye · Powers in 0.25 D steps · PD in millimetres',
          'Inventory':'Frames, lenses and services · Every stock change has a traceable movement.',
          'Optical jobs':'Track each pair from the counter to the lab and back to your customer.',
          'Purchasing':'Create an order, then receive it once the goods arrive.',
          'Payments & returns':'Collect balances and record returns. Refund payouts record money already paid.',
          'Cash & expenses':'Expenses are cash payments. Count the drawer before closing the day.',
          'Reports':'Filter by date and export to a spreadsheet. Amounts are in Pakistan rupees (PKR).',
          'Settings & team':'Configure the shop and staff accounts. Administrator access is required to save.',
          'Backup & recovery':'Keep a verified copy on another drive. Restore only while the application is closed.'}[name])
        self.safe(getattr(self,{'Overview':'overview','Checkout':'pos','Customers':'customers','Prescriptions':'rx','Inventory':'inventory','Optical jobs':'jobs','Purchasing':'purchasing','Payments & returns':'payments','Cash & expenses':'cash','Reports':'reports','Settings & team':'settings','Backup & recovery':'backup'}[name]))
    def customer_choices(self,optional=False):
        d={'Walk-in / none':None} if optional else {}
        d.update({f'{n} · {p or "no mobile"} [#{i}]':i for i,n,p,_ in self.s.customers()});return d
    def product_choices(self):return {f'{r[1]} · {r[2]} · PKR {r[4]:,.2f} [#{r[0]}]':r[0] for r in self.s.products()}
    def overview(self):
        metrics=self.s.dashboard();cards=ttk.Frame(self.body);cards.pack(fill='x')
        for i,(label,value) in enumerate(metrics.items()):
            f=ttk.Frame(cards,style='Card.TFrame',padding=20);f.grid(row=i//3,column=i%3,sticky='nsew',padx=(0,12),pady=(0,12))
            cards.columnconfigure(i%3,weight=1)
            ttk.Label(f,text=label,style='Card.TLabel').pack(anchor='w')
            ttk.Label(f,text=f'PKR {value:,.0f}' if i<3 else str(value),style='Metric.TLabel').pack(anchor='w',pady=(10,0))
        bar=self.toolbar();self.button(bar,'New sale  F2',lambda:self.show('Checkout'),True);self.button(bar,'Add customer',self.new_customer);self.button(bar,'View ready jobs',lambda:self.show('Optical jobs'))
        ttk.Label(self.body,text='Upcoming optical jobs',font=('Segoe UI',14,'bold')).pack(anchor='w',pady=(20,0))
        Grid(self.body,('Customer','Instructions','Status','Promised date'),[(r[1],r[2],r[3],r[4]) for r in self.s.jobs() if r[3] not in ('Delivered','Cancelled')])
        ttk.Label(self.body,text='No pending jobs. Create one in Optical jobs when an order goes to the lab.' if not metrics['Pending jobs'] and not metrics['Ready for pickup'] else 'Open Optical jobs to update a status or print a job slip.',style='Muted.TLabel').pack(anchor='w')
    def new_customer(self,row=None):
        Dialog(self,'Customer',[('name','Full name *','',row[1] if row else ''),('phone','Mobile number','',row[2] if row else ''),('address','Address','',row[3] if row else '')],lambda v:self.s.customer(v['name'],v['phone'],v['address'],row[0] if row else None))
    def customers(self):
        bar=self.toolbar();self.button(bar,'Add customer',self.new_customer,True)
        search=tk.StringVar();e=ttk.Entry(bar,textvariable=search);e.pack(side='right',fill='x',expand=True,padx=(30,0))
        grid=Grid(self.body,('Customer #','Name','Mobile','Address'),self.s.customers())
        search.trace_add('write',lambda *_:grid.replace(self.s.customers(search.get())))
        actions=self.toolbar();self.button(actions,'Edit selected',lambda:self.new_customer(grid.selected()))
        def history():
            row=grid.selected();sales,rx=self.s.history(row[0]);w=tk.Toplevel(self.root);w.title(row[1]+' · History');w.geometry('900x600')
            ttk.Label(w,text=row[1]+' · Sales',font=('Segoe UI',16,'bold')).pack(anchor='w',padx=16,pady=12)
            Grid(w,('Invoice','Date','Total PKR','Paid PKR'),sales,height=5)
            ttk.Label(w,text='Prescription history',font=('Segoe UI',14,'bold')).pack(anchor='w',padx=16)
            Grid(w,('Rx','Customer','Date','OD SPH','OD CYL','OD AXIS','OD ADD','OS SPH','OS CYL','OS AXIS','OS ADD','PD','Notes'),rx,height=5)
        self.button(actions,'View sales & Rx history',history);e.focus_set()
    def pos(self):
        layout=ttk.Frame(self.body);layout.pack(fill='both',expand=True);layout.columnconfigure(0,weight=1);layout.columnconfigure(1,weight=0);layout.rowconfigure(0,weight=1)
        left=ttk.Frame(layout);left.grid(row=0,column=0,sticky='nsew',padx=(0,24))
        right=ttk.Frame(layout,style='Card.TFrame',padding=20,width=300);right.grid(row=0,column=1,sticky='ns');right.grid_propagate(False)
        ttk.Label(left,text='Search name, SKU or barcode').pack(anchor='w')
        search=tk.StringVar();entry=ttk.Entry(left,textvariable=search);entry.pack(fill='x',pady=(5,8))
        catalog=Grid(left,('ID','SKU','Item','PKR','Available'),[(r[0],r[1],r[2],f'{r[4]:,.2f}','Service' if r[9] else r[5]) for r in self.s.products()],height=5)
        def find(*_):catalog.replace([(r[0],r[1],r[2],f'{r[4]:,.2f}','Service' if r[9] else r[5]) for r in self.s.products(search.get())])
        search.trace_add('write',find)
        bar=ttk.Frame(left);bar.pack(fill='x');qty=tk.StringVar(value='1');ttk.Label(bar,text='Qty').pack(side='left');ttk.Entry(bar,textvariable=qty,width=5).pack(side='left',padx=8)
        cartgrid=Grid(left,('ID','Item','Qty','Unit PKR','Line PKR'),height=5)
        self.checkout_customer=tk.StringVar(value=getattr(self,'draft_customer','Walk-in / none'));choices=self.customer_choices(True)
        self.pos_choices=choices
        ttk.Label(right,text='Checkout',style='Card.TLabel',font=('Segoe UI',17,'bold')).pack(anchor='w',pady=(0,20))
        ttk.Label(right,text='Customer',style='Card.TLabel').pack(anchor='w')
        ttk.Combobox(right,textvariable=self.checkout_customer,values=list(choices),state='readonly',width=26).pack(fill='x',pady=(5,16))
        self.discount=tk.StringVar(value=getattr(self,'draft_discount','0'));self.paid=tk.StringVar(value=getattr(self,'draft_paid','0'));self.method=tk.StringVar(value=getattr(self,'draft_method','Cash'))
        for label,var in (('Discount (PKR)',self.discount),('Amount received (PKR)',self.paid)):
            ttk.Label(right,text=label,style='Card.TLabel').pack(anchor='w');ttk.Entry(right,textvariable=var,width=20).pack(fill='x',pady=(5,16))
        ttk.Label(right,text='Payment method',style='Card.TLabel').pack(anchor='w')
        ttk.Combobox(right,textvariable=self.method,values=('Cash','Bank','Card'),state='readonly',width=20).pack(fill='x',pady=(5,20))
        total=tk.StringVar();ttk.Label(right,textvariable=total,style='Card.TLabel',font=('Segoe UI',12,'bold'),wraplength=255).pack(anchor='w',pady=12)
        def redraw(*_):
            products={r[0]:r for r in self.s.products()};cartgrid.replace([(p,products[p][2],q,f'{products[p][4]:,.2f}',f'{q*products[p][4]:,.2f}') for p,q in self.cart])
            self.draft_discount=self.discount.get();self.draft_paid=self.paid.get();self.draft_method=self.method.get()
            self.draft_customer=self.checkout_customer.get()
            if not self.cart:total.set('Cart is empty\nAdd a frame, lens or service.');return
            try:
                _,sub,disc,tax,final=self.s.quote(self.cart,self.discount.get() or 0)
                from core import money
                due=final-money(self.paid.get() or 0)
                total.set(f'Subtotal  PKR {sub/100:,.2f}\nDiscount  PKR {disc/100:,.2f}\nTax  PKR {tax/100:,.2f}\n\nTotal  PKR {final/100:,.2f}\nBalance  PKR {due/100:,.2f}')
            except Exception as e:total.set(str(e))
        def add():
            from core import quantity
            if not catalog.tree.selection():
                if len(catalog.data)==1:catalog.tree.selection_set('0')
                else:raise ValueError('Choose a matching product')
            pid=catalog.selected()[0];count=quantity(qty.get());candidate=self.cart+[(pid,count)]
            self.s.quote(candidate,self.discount.get() or 0)
            merged={}
            for p,q in candidate:merged[p]=merged.get(p,0)+q
            self.cart=list(merged.items());redraw();search.set('');entry.focus_set()
        self.button(bar,'Add item  Enter',add,True)
        def remove():
            pid=cartgrid.selected()[0];self.cart=[(p,q) for p,q in self.cart if p!=pid];redraw()
        self.button(bar,'Remove selected line',remove)
        entry.bind('<Return>',lambda e:self.safe(add));catalog.tree.bind('<Double-1>',lambda e:self.safe(add))
        self.discount.trace_add('write',redraw);self.paid.trace_add('write',redraw);self.method.trace_add('write',redraw);self.checkout_customer.trace_add('write',redraw)
        self.button(right,'Save sale  Ctrl+Enter',self.complete,True).pack_configure(side='top',fill='x',pady=12)
        def clear():
            if self.cart and messagebox.askyesno('Clear cart','Remove all items from this cart?',parent=self.root):self.cart=[];redraw()
        self.button(right,'Clear cart',clear).pack_configure(side='top',fill='x')
        ttk.Label(right,text='A balance requires a named customer. A saved sale cannot be edited; use a return to correct it.',style='Card.TLabel',wraplength=240).pack(anchor='w',pady=20)
        redraw();entry.focus_set()
    def complete(self):
        def save():
            sid,total,due=self.s.checkout(self.cart,self.pos_choices.get(self.checkout_customer.get()),self.paid.get() or 0,self.method.get(),self.discount.get() or 0)
            self.cart=[];self.draft_discount='0';self.draft_paid='0';self.draft_method='Cash';self.draft_customer='Walk-in / none';self.refresh()
            self.notice.set(f'Invoice #{sid} saved · PKR {total:,.2f} · Balance PKR {due:,.2f}')
            if messagebox.askyesno('Sale saved',f'Invoice #{sid} saved.\nPrint or save the receipt now?',parent=self.root):self.print_doc('Invoice',sid)
        self.safe(save)
    def print_doc(self,kind,identifier):
        path=self.s.print_document(kind,identifier,data_dir()/'documents');webbrowser.open(path.resolve().as_uri());self.notice.set('Printable document opened. Use Print and select your local printer.')
    def rx(self):
        bar=self.toolbar()
        def new():
            fields=[('customer','Customer *',self.customer_choices()),('date','Prescription date *','',date.today().isoformat())]
            for eye in ('od','os'):
                for k in ('sph','cyl','axis','add'):fields.append((eye+'_'+k,eye.upper()+' '+k.upper()))
            fields += [('pd','PD (mm)'),('notes','Notes')]
            Dialog(self,'Prescription',fields,lambda v:self.s.save_rx(v['customer'],v,v['date']),'Enter only measured values. Leave unmeasured values blank. Cylinder requires an axis between 0 and 180.')
        self.button(bar,'Add prescription',new,True)
        grid=Grid(self.body,('Rx','Customer #','Date','OD SPH','OD CYL','OD AXIS','OD ADD','OS SPH','OS CYL','OS AXIS','OS ADD','PD','Notes'),self.s.prescriptions())
        self.button(self.toolbar(),'Print selected Rx',lambda:self.print_doc('Prescription',grid.selected()[0]))
    def inventory(self):
        bar=self.toolbar()
        def new():
            fields=[('sku','SKU *'),('name','Product name *'),('category','Category',('Frames','Lenses','Sunglasses','Accessories','Service')),('price','Selling price (PKR) *'),('cost','Unit cost (PKR)','',0),('qty','Opening stock','',0),('barcode','Barcode (optional)'),('variant','Variant / size / colour'),('sph','Lens SPH (optional)'),('cyl','Lens CYL (optional)'),('reorder','Low stock threshold','',2)]
            Dialog(self,'Catalog item',fields,lambda v:self.s.product(v['sku'],v['name'],v['price'],v['cost'],v['qty'],v['category'],v['barcode'],v['variant'],v['sph'],v['cyl'],v['reorder'],v['category']=='Service'))
        self.button(bar,'Add catalog item',new,True)
        search=tk.StringVar();ttk.Entry(bar,textvariable=search).pack(side='right',fill='x',expand=True,padx=(30,0))
        grid=Grid(self.body,('ID','SKU','Name','Category','Price PKR','Stock','Barcode','Variant','Reorder','Service'),self.s.products());search.trace_add('write',lambda *_:grid.replace(self.s.products(search.get())))
        bar=self.toolbar()
        def adjust():
            row=grid.selected();Dialog(self,'Stock adjustment',[('delta','Change in units (use - for reduction)'),('reason','Reason *')],lambda v:self.s.adjust(row[0],v['delta'],v['reason']),row[2]+f' · Current stock: {row[5]}')
        self.button(bar,'Adjust selected stock',adjust)
        def movements():
            row=grid.selected();w=tk.Toplevel(self.root);w.title(row[2]+' · Stock movements');w.geometry('850x500')
            Grid(w,('Change','Reason','Reference','Date'),self.s.rows('SELECT delta,reason,reference_id,created_at FROM stock_movements WHERE product_id=? ORDER BY created_at DESC',(row[0],)))
        self.button(bar,'View movements',movements)
        def edit():
            row=grid.selected();cost=self.s.scalar('SELECT cost FROM products WHERE id=?',(row[0],))
            Dialog(self,'Catalog details',[('name','Name *','',row[2]),('price','Price PKR','',row[4]),('cost','Unit cost PKR','',cost),('barcode','Barcode','',row[6]),('variant','Variant','',row[7]),('reorder','Reorder level','',row[8])],lambda v:self.s.edit_product(row[0],v['name'],v['price'],v['cost'],v['barcode'],v['variant'],v['reorder']))
        self.button(bar,'Edit details & price',edit)
        def matrix():
            w=tk.Toplevel(self.root);w.title('Lens power matrix');w.geometry('900x550')
            Grid(w,('SPH','CYL','Variant','Available'),self.s.rows("SELECT d.sph,d.cyl,d.variant,SUM(p.qty) FROM product_details d JOIN products p ON p.id=d.product_id WHERE p.category='Lenses' GROUP BY d.sph,d.cyl,d.variant ORDER BY CAST(d.sph AS REAL),CAST(d.cyl AS REAL)"))
        self.button(bar,'Lens power matrix',matrix)
    def jobs(self):
        bar=self.toolbar()
        def new():
            Dialog(self,'Optical job',[('customer','Customer *',self.customer_choices()),('description','Lab instructions *'),('due','Promised date *','',date.today().isoformat()),('sale','Invoice # (optional)'),('rx','Prescription # (optional)')],lambda v:self.s.job(v['customer'],v['description'],v['due'],int(v['sale']) if v['sale'] else None,int(v['rx']) if v['rx'] else None))
        self.button(bar,'Create job',new,True)
        grid=Grid(self.body,('Job ID','Customer','Instructions','Status','Promised','Invoice','Rx'),self.s.jobs())
        bar=self.toolbar()
        def update():
            row=grid.selected();allowed={'Pending':['In Lab','Cancelled'],'In Lab':['Ready','Cancelled'],'Ready':['Delivered']}.get(row[3],[])
            if not allowed:raise ValueError('This job is complete and has no further transitions')
            Dialog(self,'Job status',[('status','Next status',allowed)],lambda v:self.s.advance_job(row[0],v['status']),row[1]+' · '+row[2])
        self.button(bar,'Update status',update);self.button(bar,'Print job slip',lambda:self.print_doc('Job',grid.selected()[0]))
    def purchasing(self):
        bar=self.toolbar()
        self.button(bar,'Add supplier',lambda:Dialog(self,'Supplier',[('name','Supplier name *'),('phone','Mobile')],lambda v:self.s.supplier(v['name'],v['phone'])))
        def order(direct=False):
            suppliers={f'{n} · {p} [#{i}]':i for i,n,p in self.s.suppliers()}
            if not suppliers:raise ValueError('Add a supplier first')
            # Dedicated cart supports multiple purchase lines, not repeated one-line receipts.
            w=tk.Toplevel(self.root);w.title('Receive goods' if direct else 'New purchase order');w.geometry('950x680');w.transient(self.root);w.grab_set()
            f=ttk.Frame(w,padding=20);f.pack(fill='both',expand=True)
            ttk.Label(f,text='Supplier').pack(anchor='w');supplier=tk.StringVar(value=next(iter(suppliers)))
            ttk.Combobox(f,textvariable=supplier,values=list(suppliers),state='readonly').pack(fill='x',pady=6)
            products=self.product_choices();product=tk.StringVar(value=next(iter(products),'') )
            ttk.Label(f,text='Product').pack(anchor='w');ttk.Combobox(f,textvariable=product,values=list(products),state='readonly').pack(fill='x',pady=6)
            qty=tk.StringVar(value='1');cost=tk.StringVar(value='0');line=ttk.Frame(f);line.pack(fill='x')
            for label,var in (('Units',qty),('Unit cost PKR',cost)):
                ttk.Label(line,text=label).pack(side='left',padx=6);ttk.Entry(line,textvariable=var,width=12).pack(side='left')
            lines=[];grid=Grid(f,('Product #','Units','Unit cost PKR'))
            def add():
                from core import quantity,money
                if not product.get():raise ValueError('Add a catalog product first')
                lines.append((products[product.get()],quantity(qty.get()),money(cost.get())/100));grid.replace(lines)
            self.button(line,'Add line',add)
            bar=ttk.Frame(f);bar.pack(fill='x')
            def remove():
                idx=int(grid.tree.selection()[0]);lines.pop(idx);grid.replace(lines)
            self.button(bar,'Remove selected line',remove)
            def save():
                if direct:self.s.receive(suppliers[supplier.get()],lines)
                else:self.s.create_po(suppliers[supplier.get()],lines)
                w.destroy();self.notice.set('Goods received.' if direct else 'Purchase order saved.');self.refresh()
            self.button(bar,'Receive goods' if direct else 'Save purchase order',save,True)
        self.button(bar,'Create purchase order',order,True);self.button(bar,'Receive without PO',lambda:order(True))
        grid=Grid(self.body,('PO #','Supplier','Created','Status'),self.s.purchase_orders())
        def receive():
            row=grid.selected()
            if messagebox.askyesno('Receive purchase order',f'Receive every line on PO #{row[0]}? Verify the delivered quantities first.',parent=self.root):
                self.s.receive_po(row[0]);self.notice.set('Purchase order received. Stock and costs updated.');self.refresh()
        self.button(self.toolbar(),'Receive selected PO',receive)
    def payments(self):
        bar=self.toolbar()
        grid=Grid(self.body,('Invoice','Customer','Date','Total PKR','Paid PKR','Balance PKR'),self.s.sales(),height=5)
        def collect():
            row=grid.selected();Dialog(self,'Receive payment',[('amount','Amount received PKR *'),('method','Method',('Cash','Bank','Card'))],lambda v:self.s.pay(row[0],v['amount'],v['method']),f'Invoice #{row[0]} · Balance PKR {row[5]:,.2f}')
        self.button(bar,'Receive payment',collect,True);self.button(bar,'Print invoice',lambda:self.print_doc('Invoice',grid.selected()[0]))
        def ret():
            row=grid.selected();products={f'{n} [#{pid}]':pid for pid,n in self.s.rows('SELECT DISTINCT p.id,p.name FROM sale_items i JOIN products p ON p.id=i.product_id WHERE sale_id=?',(row[0],))}
            def save(v):
                result=self.s.return_item(row[0],v['product'],v['qty'],v['reason'],v['method'])
                messagebox.showinfo('Return saved',f'Return #{result["return_id"]}\nValue PKR {result["refund_value"]:,.2f}\nRefund payout due PKR {result["payout_due"]:,.2f}\nCredit adjustment PKR {result["credit_adjustment"]:,.2f}\nRecord a payout after actually paying the customer.',parent=self.root)
            Dialog(self,'Return items',[('product','Product',products),('qty','Units returned','',1),('reason','Reason *'),('method','Settlement method',('Cash','Bank','Credit'))],save)
        self.button(bar,'Return selected sale',ret)
        def credit():
            row=grid.selected()
            if row[5]>=0:raise ValueError('Select an invoice with a negative balance (available store credit)')
            Dialog(self,'Apply store credit',[('target','Destination invoice # *'),('amount','Credit to apply PKR *')],lambda v:self.s.redeem_credit(row[0],int(v['target']),v['amount']),f'Available credit PKR {-row[5]:,.2f}. Both invoices must belong to the same customer.')
        self.button(bar,'Apply store credit',credit)
        ttk.Label(self.body,text='Refund settlements',font=('Segoe UI',14,'bold')).pack(anchor='w',pady=(12,0))
        refunds=Grid(self.body,('Return','Invoice','Method','Payout due PKR','Paid PKR'),self.s.rows('''SELECT r.id,r.sale_id,s.method,s.cash_refund_cents/100.0,
          COALESCE((SELECT SUM(amount_cents)/100.0 FROM refund_payouts WHERE return_id=r.id),0)
          FROM sale_returns r JOIN return_settlements s ON s.return_id=r.id ORDER BY r.id DESC'''),height=3)
        def payout():
            row=refunds.selected()
            def save(v):
                if not messagebox.askyesno('Record completed payout','Have you already paid this amount to the customer? This records the payment and does not transfer money.',parent=self.root):raise ValueError('Payout was not recorded')
                self.s.payout(row[0],v['amount'],v['method'],v['reference'])
            Dialog(self,'Completed refund payout',[('amount','Amount actually paid PKR'),('method','Method',('Cash','Bank'),row[2] if row[2]!='Credit' else 'Cash'),('reference','Unique receipt / transfer reference *')],save,f'Return #{row[0]} · Remaining PKR {row[3]-row[4]:,.2f}')
        self.button(self.toolbar(),'Record completed refund payout',payout)
    def cash(self):
        bar=self.toolbar()
        self.button(bar,'Record expense',lambda:Dialog(self,'Expense',[('description','Description *'),('amount','Cash paid PKR *')],lambda v:self.s.expense(v['description'],v['amount'])),True)
        self.button(bar,'Cash movement',lambda:Dialog(self,'Cash movement',[('kind','Movement',('Opening','Cash in','Cash out')),('amount','Amount PKR *'),('note','Reason *')],lambda v:self.s.cash(v['kind'],v['amount'],v['note'])))
        today=date.today().isoformat();expected=self.s.expected_cash(today)
        ttk.Label(self.body,text=f'Expected cash today: PKR {expected/100:,.2f}',font=('Segoe UI',18,'bold')).pack(anchor='w',pady=20)
        self.button(bar,'Close day',lambda:Dialog(self,'Daily closing',[('day','Closing date','',today),('counted','Cash counted PKR *'),('note','Count notes')],lambda v:self.s.close_day(v['day'],v['counted'],v['note']),'Count the drawer first. A closing is an immutable snapshot; later activity is shown in reports.'))
        ttk.Label(self.body,text='Cash expenses',font=('Segoe UI',13,'bold')).pack(anchor='w')
        Grid(self.body,('Date','Description','PKR'),self.s.rows('SELECT date,description,amount FROM expenses ORDER BY id DESC'),height=5)
        ttk.Label(self.body,text='Cash movements',font=('Segoe UI',13,'bold')).pack(anchor='w')
        Grid(self.body,('Day','Kind','PKR','Reason','Staff'),self.s.rows('SELECT day,kind,amount_cents/100.0,note,actor FROM cash_movements ORDER BY created_at DESC'),height=5)
    def reports(self):
        bar=self.toolbar();kind=tk.StringVar(value='Sales');start=tk.StringVar(value=date.today().replace(day=1).isoformat());end=tk.StringVar(value=date.today().isoformat())
        ttk.Combobox(bar,textvariable=kind,values=('Sales','Stock','Customer dues','Expenses','Cash closing','Profit'),state='readonly',width=16).pack(side='left',padx=(0,10))
        for label,var in (('From',start),('To',end)):
            ttk.Label(bar,text=label).pack(side='left',padx=6);ttk.Entry(bar,textvariable=var,width=12).pack(side='left')
        holder=ttk.Frame(self.body);holder.pack(fill='both',expand=True);current={}
        def run():
            cols,rows=self.s.report(kind.get(),start.get(),end.get());current.update(cols=cols,rows=rows)
            for c in holder.winfo_children():c.destroy()
            Grid(holder,cols,rows)
            self.notice.set(f'{len(rows)} rows · Stock and customer dues show current positions. Profit uses historical costs for new invoices; legacy costs are estimates.')
        self.button(bar,'Apply',run,True)
        def export():
            if not current:run()
            path=filedialog.asksaveasfilename(parent=self.root,defaultextension='.csv',filetypes=[('CSV spreadsheet','*.csv')],initialfile=kind.get().lower().replace(' ','_')+'.csv')
            if path:self.s.export_csv(path,current['cols'],current['rows']);self.notice.set('Report exported.')
        self.button(self.toolbar(),'Export CSV',export);run()
    def settings(self):
        self.s.authorize(True);values=self.s.settings();bar=self.toolbar()
        def shop():
            fields=[('shop_name','Shop name','',values.get('shop_name','AINAK MAHAL')),('address','Address','',values.get('address','Millat Chowk, Faisalabad')),('phone','Shop mobile','',values.get('phone','')),('tax_rate','Tax rate (%)','',values.get('tax_rate','0')),('receipt_format','Receipt format',('A4','80 mm'),values.get('receipt_format','A4')),('printer','Preferred local printer (print dialog)','',values.get('printer','System default')),('backup_destination','Backup folder','',values.get('backup_destination',str(data_dir()/'backups')))]
            Dialog(self,'Shop settings',fields,self.s.save_settings)
        self.button(bar,'Edit shop settings',shop,True)
        self.button(bar,'Add staff account',lambda:Dialog(self,'Staff account',[('username','Username *'),('password','Password (10+ characters) *','password'),('role','Role',('cashier','admin'))],lambda v:self.s.create_user(v['username'],v['password'],v['role'])))
        ttk.Label(self.body,text='Staff accounts',font=('Segoe UI',14,'bold')).pack(anchor='w',pady=(20,0))
        grid=Grid(self.body,('ID','Username','Role','Active'),self.s.users(),height=5)
        self.button(self.toolbar(),'Enable / disable selected',lambda:(self.s.set_active(grid.selected()[1],not grid.selected()[3]),self.refresh()))
        ttk.Label(self.body,text='Audit trail · Latest 200 events',font=('Segoe UI',14,'bold')).pack(anchor='w')
        Grid(self.body,('Staff','Action','Reference','Date'),self.s.rows('SELECT actor,action,reference,created_at FROM audit_events ORDER BY id DESC LIMIT 200'),height=5)
    def backup(self):
        self.s.authorize(True)
        ttk.Label(self.body,text='Your store data stays on this computer',font=('Segoe UI',18,'bold')).pack(anchor='w',pady=(8,16))
        ttk.Label(self.body,text=str(data_dir()/'ainak_mahal.db'),style='Muted.TLabel').pack(anchor='w')
        ttk.Label(self.body,text='Create a backup at the end of each day. Keep another copy on a USB drive.\nA database backup contains customer details and password hashes; store it securely.',wraplength=750).pack(anchor='w',pady=20)
        bar=self.toolbar()
        def backup():
            from datetime import datetime
            directory=Path(self.s.settings().get('backup_destination',str(data_dir()/'backups')));directory.mkdir(parents=True,exist_ok=True)
            path=directory/('ainak_mahal_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.db')
            self.s.backup(path);self.notice.set(f'Backup verified: {path}')
        self.button(bar,'Create verified backup',backup,True)
        def copy():
            path=filedialog.asksaveasfilename(parent=self.root,defaultextension='.db',filetypes=[('Ainak Mahal backup','*.db')])
            if path:self.s.backup(path);self.notice.set('Backup saved and verified.')
        self.button(bar,'Save backup as…',copy)
        def reconcile():
            stock,payments=self.s.reconcile();messagebox.showinfo('Data checks',f'Stock discrepancies: {len(stock)}\nPayment discrepancies: {len(payments)}\nDiscrepancies must be investigated; records are never silently rewritten.',parent=self.root)
        self.button(bar,'Check stock & payments',reconcile)
        ttk.Label(self.body,text='Restore a backup',font=('Segoe UI',16,'bold')).pack(anchor='w',pady=(32,12))
        ttk.Label(self.body,text='Close Ainak Mahal, then open “Ainak Mahal Recovery” from the Start menu.\nRecovery keeps a safety copy before restoring. Your administrator login is required.\nAfter restoring, sign in and run the stock and payment checks.',wraplength=800).pack(anchor='w')

def sign_in(root,service,on_login):
    theme(root);root.title('Ainak Mahal · Sign in');root.geometry('510x650');root.resizable(False,False)
    frame=ttk.Frame(root,padding=40);frame.pack(fill='both',expand=True)
    first=service.first_run()
    ttk.Label(frame,text='AINAK MAHAL',font=('Segoe UI',25,'bold')).pack(anchor='w',pady=(10,4))
    ttk.Label(frame,text='Millat Chowk, Faisalabad',style='Muted.TLabel').pack(anchor='w')
    ttk.Label(frame,text='Set up your shop' if first else 'Welcome back',font=('Segoe UI',19,'bold')).pack(anchor='w',pady=(32,10))
    ttk.Label(frame,text='Create your administrator account. Use a password\nof at least 10 characters.' if first else 'Sign in to start your day. Your data stays offline.',style='Muted.TLabel').pack(anchor='w',pady=(0,20))
    values={}
    for key,label in [('username','Username'),('password','Password')]+([('confirm','Confirm password')] if first else []):
        ttk.Label(frame,text=label).pack(anchor='w');var=tk.StringVar();values[key]=var
        e=ttk.Entry(frame,textvariable=var,show='' if key=='username' else '*');e.pack(fill='x',pady=(5,14))
        if key=='username':e.focus_set()
    error=ttk.Label(frame,text='',foreground='#A52A24',wraplength=420);error.pack(anchor='w',pady=8)
    attempts=[0]
    def submit():
        button.state(['disabled']);root.update_idletasks()
        try:
            if first:service.bootstrap(values['username'].get(),values['password'].get(),values['confirm'].get())
            else:service.login(values['username'].get(),values['password'].get())
        except Exception as ex:
            attempts[0]+=1;error.configure(text=str(ex))
            root.after(min(500*attempts[0],5000),lambda:button.state(['!disabled']));return
        for child in root.winfo_children():child.destroy()
        root.unbind('<Return>')
        root.resizable(True,True);on_login()
    button=ttk.Button(frame,text='Create administrator' if first else 'Sign in',style='Primary.TButton',command=submit);button.pack(fill='x',pady=12)
    root.bind('<Return>',lambda e:submit() if not button.instate(['disabled']) else None)
    ttk.Label(frame,text='Offline by design · No subscription required',style='Muted.TLabel').pack(anchor='w',pady=20)
