"""Native Windows desktop presentation. All mutations go through Retail services."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, font as tkfont
from datetime import date
from pathlib import Path
import webbrowser
import sqlite3
from retail import Retail
from paths import data_dir

from brand import NAVY, BLUE, TEAL, BG, MUTED, WHITE, TEXT, LINE, ERROR, mark, window_icon

def error_copy(error):
    if isinstance(error,sqlite3.IntegrityError):
        return 'This record conflicts with existing data. Check for a duplicate SKU, barcode, username, payment reference or closing date. Linked records must exist.'
    if isinstance(error,sqlite3.OperationalError):
        return 'The database could not complete this action. Close other copies of Ainak Mahal, check disk space and try again. Your transaction was not saved.'
    return str(error)

FONT='Segoe UI'

def theme(root):
    global FONT
    available={name.casefold() for name in tkfont.families(root)}
    FONT=next((name for name in (FONT,'DejaVu Sans','Helvetica') if name.casefold() in available),'TkDefaultFont')
    root.configure(bg=BG)
    window_icon(root)
    s=ttk.Style(root);s.theme_use('clam')
    s.configure('.',font=(FONT,10),background=BG,foreground=TEXT)
    s.configure('TFrame',background=BG);s.configure('Card.TFrame',background=WHITE)
    s.configure('TLabel',background=BG);s.configure('Muted.TLabel',foreground=MUTED)
    s.configure('Title.TLabel',font=(FONT,26,'bold'),foreground=NAVY)
    s.configure('Card.TLabel',background=WHITE)
    s.configure('Metric.TLabel',background=WHITE,font=(FONT,25,'bold'),foreground=NAVY)
    s.configure('TButton',padding=(12,9),background=WHITE,borderwidth=1,bordercolor=LINE,relief='flat')
    s.map('TButton',background=[('pressed','#DBEAFE'),('active','#EFF6FF')],bordercolor=[('focus',BLUE)])
    s.configure('Primary.TButton',background=BLUE,foreground=WHITE,bordercolor=BLUE)
    s.map('Primary.TButton',background=[('disabled','#E2E8F0'),('pressed','#1E40AF'),('active','#1D4ED8')],foreground=[('disabled',MUTED)],bordercolor=[('focus',NAVY)])
    s.configure('Quiet.TButton',background=BG,foreground=MUTED,bordercolor=BG)
    s.configure('TEntry',padding=8,fieldbackground=WHITE,bordercolor=LINE,lightcolor=LINE,darkcolor=LINE)
    s.map('TEntry',bordercolor=[('invalid',ERROR),('focus',BLUE)],lightcolor=[('focus',BLUE)],darkcolor=[('focus',BLUE)])
    s.configure('TCombobox',padding=7,fieldbackground=WHITE,bordercolor=LINE)
    s.map('TCombobox',fieldbackground=[('readonly',WHITE)],foreground=[('readonly',TEXT)])
    s.configure('Treeview',background=WHITE,fieldbackground=WHITE,foreground=TEXT,rowheight=38,borderwidth=0)
    s.map('Treeview',background=[('selected','#DBEAFE')],foreground=[('selected',NAVY)])
    s.configure('Treeview.Heading',background='#F1F5F9',foreground=MUTED,font=(FONT,9,'bold'),padding=(10,11),relief='flat')
    s.configure('TScrollbar',background='#CBD5E1',troughcolor=BG,borderwidth=0,arrowsize=12)
    s.configure('TSeparator',background=LINE)
    s.configure('TCheckbutton',background=WHITE)

class Grid:
    def __init__(self,parent,columns,rows=(),height=12):
        self.columns=columns
        self.frame=ttk.Frame(parent);self.frame.pack(fill='both',expand=True,pady=10)
        # Request a compact minimum, then expand into available space. A fixed tall
        # request otherwise pushes later financial actions outside a 700px window.
        self.tree=ttk.Treeview(self.frame,columns=list(range(len(columns))),show='headings',height=min(height,2),selectmode='browse')
        for i,label in enumerate(columns):
            self.tree.heading(i,text=label,command=lambda col=i:self.sort(col))
            width=240 if label in ('Item','Name','Product','Lab instructions','Instructions') else 170 if label=='Customer' else 65 if label in ('ID','Qty','Stock','Available','Service') else 110
            self.tree.column(i,width=width,minwidth=45,stretch=True,anchor='e' if 'PKR' in label or label in ('Qty','Available','Stock','Reorder') else 'w')
        y=ttk.Scrollbar(self.frame,orient='vertical',command=self.tree.yview)
        x=ttk.Scrollbar(self.frame,orient='horizontal',command=self.tree.xview)
        self.tree.configure(yscrollcommand=y.set,xscrollcommand=x.set)
        self.tree.grid(row=0,column=0,sticky='nsew');y.grid(row=0,column=1,sticky='ns');x.grid(row=1,column=0,sticky='ew')
        self.frame.rowconfigure(0,weight=1);self.frame.columnconfigure(0,weight=1)
        self.tree.tag_configure('even',background=WHITE)
        self.tree.tag_configure('odd',background='#F8FAFC')
        self.empty=ttk.Label(self.frame,text='No records yet. Use the action above to add your first record.',background=WHITE,foreground=MUTED,wraplength=420,justify='center')
        self.data={};self.sort_column=None;self.descending=False;self.replace(rows)
    def replace(self,rows):
        previous=self.data.get(self.tree.selection()[0]) if self.tree.selection() else None
        rows=list(rows)
        if self.sort_column is not None:
            col=self.sort_column
            rows.sort(key=lambda r:(r[col] is None,r[col] if isinstance(r[col],(int,float)) else str(r[col]).casefold()),reverse=self.descending)
        self.tree.delete(*self.tree.get_children());self.data={}
        for i,row in enumerate(rows):
            values=['—' if v is None or v=='' else f'{v:,.2f}' if isinstance(v,(int,float)) and 'PKR' in self.columns[col] else v for col,v in enumerate(row)]
            self.tree.insert('','end',iid=str(i),values=values,tags=('odd' if i%2 else 'even',));self.data[str(i)]=row
            if previous and row[0]==previous[0]:self.tree.selection_set(str(i))
        if rows:self.empty.place_forget()
        else:self.empty.place(relx=.5,rely=.5,anchor='center')
    def sort(self,column):
        self.descending=not self.descending if self.sort_column==column else False
        self.sort_column=column;self.replace(self.data.values())
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
        ttk.Label(shell,text=title,font=(FONT,18,'bold')).pack(anchor='w')
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
                        ttk.Label(eye_grid,text=text,font=(FONT,10,'bold')).grid(row=0,column=col,padx=4,pady=6)
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
        sidebar=tk.Frame(root,bg=NAVY,width=224);sidebar.pack(side='left',fill='y');sidebar.pack_propagate(False)
        brandrow=tk.Frame(sidebar,bg=NAVY);brandrow.pack(fill='x',padx=18,pady=(20,2))
        mark(brandrow,48,NAVY,WHITE,'#5EEAD4').pack(side='left')
        tk.Label(brandrow,text='Ainak Mahal',bg=NAVY,fg=WHITE,font=(FONT,17,'bold')).pack(side='left',padx=(6,0))
        tk.Label(sidebar,text='OPTICAL STORE  /  FAISALABAD',bg=NAVY,fg='#C4D3E6',font=(FONT,8)).pack(anchor='w',padx=24,pady=(0,20))
        self.nav={}
        groups={0:'WORKSPACE',6:'OPERATIONS',10:'ADMINISTRATION'}
        for i,name in enumerate(self.PAGES):
            if i in groups:tk.Label(sidebar,text=groups[i],bg=NAVY,fg='#AFC4DE',font=(FONT,8,'bold')).pack(anchor='w',padx=24,pady=(12 if i else 0,5))
            b=tk.Button(sidebar,text=name,anchor='w',bg=NAVY,fg='#DFE8F5',activebackground='#294968',activeforeground=WHITE,
              relief='flat',borderwidth=0,padx=16,pady=7,command=lambda n=name:self.show(n),takefocus=True,
              highlightthickness=1,highlightbackground=NAVY,highlightcolor='#93C5FD')
            b.pack(fill='x',padx=12,pady=1);self.nav[name]=b
            b.bind('<Enter>',lambda e,button=b,n=name:button.configure(bg='#244366' if self.current!=n else '#2856A0'))
            b.bind('<Leave>',lambda e,button=b,n=name:button.configure(bg=NAVY if self.current!=n else '#2856A0'))
        user=tk.Frame(sidebar,bg='#1A385D');user.pack(side='bottom',fill='x',padx=12,pady=14)
        tk.Label(user,text=f'{service.actor}  ·  {service.role.title()}',bg='#1A385D',fg=WHITE,anchor='w',font=(FONT,10,'bold')).pack(fill='x',padx=12,pady=(10,3))
        tk.Label(user,text='●  Offline workspace',bg='#1A385D',fg='#99F6E4',anchor='w',font=(FONT,9)).pack(fill='x',padx=12,pady=(0,10))
        outer=ttk.Frame(root,padding=(26,18));outer.pack(side='left',fill='both',expand=True)
        top=ttk.Frame(outer);top.pack(fill='x',pady=(0,16))
        ttk.Label(top,text='WORKSPACE  /  MAIN STORE',style='Muted.TLabel',font=(FONT,9,'bold')).pack(side='left')
        ttk.Button(top,text='Search anything   Ctrl+K',command=self.open_search,style='Quiet.TButton').pack(side='right')
        ttk.Separator(outer).pack(fill='x',pady=(0,18))
        self.heading=ttk.Label(outer,style='Title.TLabel');self.heading.pack(anchor='w')
        self.sub=ttk.Label(outer,style='Muted.TLabel');self.sub.pack(anchor='w',pady=(5,18))
        self.body=ttk.Frame(outer);self.body.pack(fill='both',expand=True)
        ttk.Label(outer,textvariable=self.notice,style='Muted.TLabel',wraplength=900).pack(anchor='w',pady=(10,0))
        root.bind('<F2>',lambda e:self.show('Checkout'));root.bind('<F3>',lambda e:self.show('Customers'))
        root.bind('<Control-k>',lambda e:self.open_search())
        root.bind('<Control-Shift-P>',lambda e:Dialog(self,'Change password',[('current','Current password *','password'),('new','New password (10+ characters) *','password'),('confirm','Confirm password *','password')],lambda v:self.s.change_password(v['current'],v['new'],v['confirm'])))
        root.bind('<Control-Return>',lambda e:self.complete() if self.current=='Checkout' else None)
        root.protocol('WM_DELETE_WINDOW',self.exit);self.show('Overview')
    def open_search(self):
        if getattr(self,'search_window',None) and self.search_window.winfo_exists():
            self.search_window.focus_force();return
        win=tk.Toplevel(self.root);self.search_window=win;win.title('Search Ainak Mahal');win.geometry('820x500');win.transient(self.root)
        shell=ttk.Frame(win,padding=24);shell.pack(fill='both',expand=True)
        ttk.Label(shell,text='Find it in your shop',font=(FONT,20,'bold')).pack(anchor='w')
        ttk.Label(shell,text='Customers, mobile numbers, products, barcodes, jobs or invoice numbers.',style='Muted.TLabel').pack(anchor='w',pady=(5,10))
        query=tk.StringVar();entry=ttk.Entry(shell,textvariable=query);entry.pack(fill='x')
        grid=Grid(shell,('Type','Reference','Name','Details'))
        grid.empty.configure(text='Start typing to search. Your search stays on this computer.')
        results=[]
        def find(*_):
            nonlocal results
            results=self.s.search(query.get());grid.replace([r[:4] for r in results])
            grid.empty.configure(text='No matches. Try a name, mobile number, SKU or barcode.' if query.get().strip() else 'Start typing to search. Your search stays on this computer.')
        def activate(event=None):
            if not grid.tree.selection() and grid.data:grid.tree.selection_set('0')
            if not grid.tree.selection():return
            row=grid.selected();match=next(r for r in results if r[:4]==tuple(row));page=match[4]
            win.destroy();self.show(page)
            target=getattr(self,'page_grid',None)
            if target:
                for key,value in target.data.items():
                    if value[0]==row[1]:target.tree.selection_set(key);target.tree.see(key);target.tree.focus(key);break
            self.notice.set(f'{row[0]} #{row[1]} · {row[2]}')
        query.trace_add('write',lambda *_:self.safe(find))
        entry.bind('<Return>',activate);grid.tree.bind('<Return>',activate);grid.tree.bind('<Double-1>',activate)
        win.bind('<Escape>',lambda e:win.destroy())
        footer=ttk.Frame(shell);footer.pack(fill='x')
        ttk.Label(footer,text='Enter to open selected result · Escape to close',style='Muted.TLabel').pack(side='left')
        ttk.Button(footer,text='Open selected',command=activate,style='Primary.TButton').pack(side='right')
        # Windows cannot reliably focus an Entry before its Toplevel is mapped.
        # Map first, then establish modal keyboard ownership, as with other dialogs.
        win.wait_visibility();win.grab_set();entry.focus_force()
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
        if self.current!=name:self.notice.set('Ready. All changes are saved on this computer.')
        self.current=name;self.page_grid=None
        for child in self.body.winfo_children():child.destroy()
        for n,b in self.nav.items():b.configure(bg='#2856A0' if n==name else NAVY,fg=WHITE if n==name else '#DFE8F5')
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
    def ready_jobs(self):
        self.next_job_status='Ready';self.show('Optical jobs')
    def overview(self):
        bar=self.toolbar()
        self.button(bar,'New sale  F2',lambda:self.show('Checkout'),True)
        self.button(bar,'Add customer',self.new_customer)
        self.button(bar,'View ready jobs',self.ready_jobs)
        metrics=self.s.dashboard();cards=ttk.Frame(self.body);cards.pack(fill='x',pady=(10,4))
        notes=('Saved invoices today','Cash, card and bank receipts','Outstanding across all customers','Items at their reorder threshold','Pending or in the lab','Ready for customer collection')
        for i,(label,value) in enumerate(metrics.items()):
            f=ttk.Frame(cards,style='Card.TFrame',padding=(18,12));f.grid(row=i//3,column=i%3,sticky='nsew',padx=(0,10),pady=(0,10))
            cards.columnconfigure(i%3,weight=1,uniform='metric')
            ttk.Label(f,text=label.upper(),style='Card.TLabel',foreground=MUTED,font=(FONT,9,'bold')).pack(anchor='w')
            metric=ttk.Label(f,text=f'PKR {value:,.0f}' if i<3 else str(value),style='Metric.TLabel')
            metric.pack(anchor='w',pady=(7,5))
            def fit_metric(event,widget=metric):
                room=max(80,event.width-36)
                size=next((n for n in (25,23,21,19,17,15,13,11) if tkfont.Font(family=FONT,size=n,weight='bold').measure(widget.cget('text'))<=room),11)
                widget.configure(font=(FONT,size,'bold'))
            f.bind('<Configure>',fit_metric)
            ttk.Label(f,text=notes[i],style='Card.TLabel',foreground=TEAL if i==5 else MUTED,font=(FONT,9)).pack(anchor='w')
        row=ttk.Frame(self.body);row.pack(fill='x',pady=(6,0))
        ttk.Label(row,text='At the counter',font=(FONT,15,'bold'),foreground=NAVY).pack(side='left')
        view=tk.StringVar(value='Upcoming jobs')
        choice=ttk.Combobox(row,textvariable=view,values=('Upcoming jobs','Recent invoices','Low-stock items'),state='readonly',width=20);choice.pack(side='right')
        holder=ttk.Frame(self.body);holder.pack(fill='both',expand=True)
        def render(event=None):
            for child in holder.winfo_children():child.destroy()
            if view.get()=='Upcoming jobs':
                rows=[(r[1],r[2],r[3],r[4]) for r in self.s.jobs() if r[3] not in ('Delivered','Cancelled')]
                cols=('Customer','Lab instructions','Status','Promised date')
            elif view.get()=='Recent invoices':
                rows=[(f'#{r[0]}',r[1],r[2][:10],f'PKR {r[3]:,.2f}',f'PKR {r[5]:,.2f}') for r in self.s.sales()[:20]]
                cols=('Invoice','Customer','Date','Total','Balance')
            else:
                rows=[(r[1],r[2],r[5],r[8]) for r in self.s.products() if not r[9] and r[5]<=r[8]]
                cols=('SKU','Product','Available','Reorder at')
            Grid(holder,cols,rows,height=4)
        choice.bind('<<ComboboxSelected>>',render);render()
    def new_customer(self,row=None):
        Dialog(self,'Customer',[('name','Full name *','',row[1] if row else ''),('phone','Mobile number','',row[2] if row else ''),('address','Address','',row[3] if row else '')],lambda v:self.s.customer(v['name'],v['phone'],v['address'],row[0] if row else None))
    def customers(self):
        bar=self.toolbar();self.button(bar,'Add customer',self.new_customer,True)
        ttk.Label(bar,text='Name or mobile',style='Muted.TLabel').pack(side='left',padx=(12,8))
        search=tk.StringVar();e=ttk.Entry(bar,textvariable=search);e.pack(side='right',fill='x',expand=True,padx=(30,0))
        grid=Grid(self.body,('Customer #','Name','Mobile','Address'),self.s.customers());self.page_grid=grid
        search.trace_add('write',lambda *_:grid.replace(self.s.customers(search.get())))
        actions=self.toolbar();self.button(actions,'Edit selected',lambda:self.new_customer(grid.selected()))
        def history():
            row=grid.selected();sales,rx=self.s.history(row[0]);w=tk.Toplevel(self.root);w.title(row[1]+' · History');w.geometry('900x600')
            ttk.Label(w,text=row[1]+' · Sales',font=(FONT,16,'bold')).pack(anchor='w',padx=16,pady=12)
            Grid(w,('Invoice','Date','Total PKR','Paid PKR'),sales,height=5)
            ttk.Label(w,text='Prescription history',font=(FONT,14,'bold')).pack(anchor='w',padx=16)
            Grid(w,('Rx','Customer','Date','OD SPH','OD CYL','OD AXIS','OD ADD','OS SPH','OS CYL','OS AXIS','OS ADD','PD','Notes'),rx,height=5)
        self.button(actions,'View sales & Rx history',history);e.focus_set()
    def pos(self):
        layout=ttk.Frame(self.body);layout.pack(fill='both',expand=True);layout.columnconfigure(0,weight=1);layout.columnconfigure(1,weight=0);layout.rowconfigure(0,weight=1)
        left=ttk.Frame(layout);left.grid(row=0,column=0,sticky='nsew',padx=(0,24))
        right_shell=ttk.Frame(layout,style='Card.TFrame',padding=14,width=296);right_shell.grid(row=0,column=1,sticky='ns');right_shell.pack_propagate(False)
        checkout_actions=ttk.Frame(right_shell,style='Card.TFrame');checkout_actions.pack(side='bottom',fill='x')
        canvas=tk.Canvas(right_shell,bg=WHITE,highlightthickness=0,width=266)
        scrollbar=ttk.Scrollbar(right_shell,orient='vertical',command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set);scrollbar.pack(side='right',fill='y');canvas.pack(fill='both',expand=True)
        right=ttk.Frame(canvas,style='Card.TFrame');window=canvas.create_window((0,0),window=right,anchor='nw')
        right.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(window,width=e.width))
        def reveal(event):
            canvas.update_idletasks();y=event.widget.winfo_rooty()-right.winfo_rooty();height=max(1,right.winfo_height())
            if y<canvas.canvasy(0) or y+event.widget.winfo_height()>canvas.canvasy(canvas.winfo_height()):canvas.yview_moveto(max(0,(y-30)/height))

        ttk.Label(left,text='Search name, SKU or barcode').pack(anchor='w')
        search=tk.StringVar();entry=ttk.Entry(left,textvariable=search);entry.pack(fill='x',pady=(5,8))
        catalog=Grid(left,('ID','SKU','Item','PKR','Available'),[(r[0],r[1],r[2],f'{r[4]:,.2f}','Service' if r[9] else r[5]) for r in self.s.products()],height=5)
        def find(*_):catalog.replace([(r[0],r[1],r[2],f'{r[4]:,.2f}','Service' if r[9] else r[5]) for r in self.s.products(search.get())])
        search.trace_add('write',find)
        bar=ttk.Frame(left);bar.pack(fill='x');qty=tk.StringVar(value='1');ttk.Label(bar,text='Qty').pack(side='left');ttk.Entry(bar,textvariable=qty,width=5).pack(side='left',padx=8)
        cartgrid=Grid(left,('ID','Item','Qty','Unit PKR','Line PKR'),height=5)
        self.checkout_customer=tk.StringVar(value=getattr(self,'draft_customer','Walk-in / none'));choices=self.customer_choices(True)
        self.pos_choices=choices
        ttk.Label(right,text='Checkout',style='Card.TLabel',font=(FONT,17,'bold')).pack(anchor='w',pady=(0,12))
        ttk.Label(right,text='Customer',style='Card.TLabel').pack(anchor='w')
        ttk.Combobox(right,textvariable=self.checkout_customer,values=list(choices),state='readonly',width=26).pack(fill='x',pady=(5,10))
        self.discount=tk.StringVar(value=getattr(self,'draft_discount','0'));self.paid=tk.StringVar(value=getattr(self,'draft_paid','0'));self.method=tk.StringVar(value=getattr(self,'draft_method','Cash'))
        for label,var in (('Discount (PKR)',self.discount),('Amount received (PKR)',self.paid)):
            ttk.Label(right,text=label,style='Card.TLabel').pack(anchor='w');ttk.Entry(right,textvariable=var,width=20).pack(fill='x',pady=(5,10))
        ttk.Label(right,text='Payment method',style='Card.TLabel').pack(anchor='w')
        ttk.Combobox(right,textvariable=self.method,values=('Cash','Bank','Card'),state='readonly',width=20).pack(fill='x',pady=(5,10))
        total=tk.StringVar();ttk.Label(right,textvariable=total,style='Card.TLabel',font=(FONT,11,'bold'),wraplength=255).pack(anchor='w',pady=12)
        def redraw(*_):
            products={r[0]:r for r in self.s.products()};cartgrid.replace([(p,products[p][2],q,f'{products[p][4]:,.2f}',f'{q*products[p][4]:,.2f}') for p,q in self.cart])
            self.draft_discount=self.discount.get();self.draft_paid=self.paid.get();self.draft_method=self.method.get()
            self.draft_customer=self.checkout_customer.get()
            if not self.cart:total.set('Cart is empty\nAdd a frame, lens or service.');return
            try:
                _,sub,disc,tax,final=self.s.quote(self.cart,self.discount.get() or 0)
                from core import money
                due=final-money(self.paid.get() or 0)
                balance_label='Balance due' if due>=0 else 'Reduce payment by'
                total.set(f'Subtotal  PKR {sub/100:,.2f}\nDiscount  PKR {disc/100:,.2f}\nTax  PKR {tax/100:,.2f}\n\nTotal  PKR {final/100:,.2f}\n{balance_label}  PKR {abs(due)/100:,.2f}')
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
        self.button(checkout_actions,'Save sale  Ctrl+Enter',self.complete,True).pack_configure(side='top',fill='x',pady=12)
        def clear():
            if self.cart and messagebox.askyesno('Clear cart','Remove all items from this cart?',parent=self.root):self.cart=[];redraw()
        self.button(checkout_actions,'Clear cart',clear).pack_configure(side='top',fill='x')
        ttk.Label(right,text='A balance requires a named customer. A saved sale cannot be edited; use a return to correct it.',style='Card.TLabel',foreground=MUTED,wraplength=240,font=(FONT,9)).pack(anchor='w',pady=10)
        for widget in right.winfo_children():
            if isinstance(widget,(ttk.Entry,ttk.Combobox)):widget.bind('<FocusIn>',reveal,add='+')
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
        ttk.Label(bar,text='Name, SKU or barcode',style='Muted.TLabel').pack(side='left',padx=(12,8))
        search=tk.StringVar();ttk.Entry(bar,textvariable=search).pack(side='right',fill='x',expand=True,padx=(30,0))
        grid=Grid(self.body,('ID','SKU','Name','Category','Price PKR','Stock','Barcode','Variant','Reorder','Service'),self.s.products());self.page_grid=grid
        filters=ttk.Frame(self.body);filters.pack(fill='x',before=grid.frame)
        category=tk.StringVar(value='All categories');stock=tk.StringVar(value='All stock')
        ttk.Label(filters,text='Filter inventory',style='Muted.TLabel').pack(side='left',padx=(0,12))
        for var,options in ((category,('All categories','Frames','Lenses','Sunglasses','Accessories','Service')),(stock,('All stock','Low stock','Out of stock'))):
            widget=ttk.Combobox(filters,textvariable=var,values=options,state='readonly',width=17);widget.pack(side='left',padx=(0,10))
        def filter_products(*_):
            rows=[r for r in self.s.products(search.get()) if (category.get()=='All categories' or r[3]==category.get()) and (stock.get()=='All stock' or not r[9] and (r[5]<=r[8] if stock.get()=='Low stock' else r[5]==0))]
            grid.replace(rows);grid.empty.configure(text='No matching items. Try another category, stock filter or search.')
        for var in (search,category,stock):var.trace_add('write',filter_products)
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
        grid=Grid(self.body,('Job ID','Customer','Instructions','Status','Promised','Invoice','Rx'),self.s.jobs());self.page_grid=grid
        filters=ttk.Frame(self.body);filters.pack(fill='x',before=grid.frame)
        status=tk.StringVar(value=self.__dict__.pop('next_job_status','All statuses'));search=tk.StringVar()
        ttk.Label(filters,text='Job status',style='Muted.TLabel').pack(side='left',padx=(0,8))
        ttk.Combobox(filters,textvariable=status,values=('All statuses','Pending','In Lab','Ready','Delivered','Cancelled','Overdue'),state='readonly',width=16).pack(side='left')
        ttk.Label(filters,text='Find customer or instructions',style='Muted.TLabel').pack(side='left',padx=(18,8))
        ttk.Entry(filters,textvariable=search).pack(side='left',fill='x',expand=True)
        def filter_jobs(*_):
            rows=[r for r in self.s.jobs() if search.get().casefold() in (r[1]+' '+r[2]).casefold() and (status.get()=='All statuses' or r[3]==status.get() or status.get()=='Overdue' and r[3] not in ('Delivered','Cancelled') and r[4]<date.today().isoformat())]
            grid.replace(rows);grid.empty.configure(text='No matching jobs. Try another status or customer name.')
        for var in (status,search):var.trace_add('write',filter_jobs)
        filter_jobs()
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
        grid=Grid(self.body,('Invoice','Customer','Date','Total PKR','Paid PKR','Balance PKR'),self.s.sales(),height=5);self.page_grid=grid
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
        ttk.Label(self.body,text='Refund settlements',font=(FONT,14,'bold')).pack(anchor='w',pady=(12,0))
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
        ttk.Label(self.body,text=f'Expected cash today: PKR {expected/100:,.2f}',font=(FONT,18,'bold')).pack(anchor='w',pady=20)
        self.button(bar,'Close day',lambda:Dialog(self,'Daily closing',[('day','Closing date','',today),('counted','Cash counted PKR *'),('note','Count notes')],lambda v:self.s.close_day(v['day'],v['counted'],v['note']),'Count the drawer first. A closing is an immutable snapshot; later activity is shown in reports.'))
        ttk.Label(self.body,text='Cash expenses',font=(FONT,13,'bold')).pack(anchor='w')
        Grid(self.body,('Date','Description','PKR'),self.s.rows('SELECT date,description,amount FROM expenses ORDER BY id DESC'),height=5)
        ttk.Label(self.body,text='Cash movements',font=(FONT,13,'bold')).pack(anchor='w')
        Grid(self.body,('Day','Kind','PKR','Reason','Staff'),self.s.rows('SELECT day,kind,amount_cents/100.0,note,actor FROM cash_movements ORDER BY created_at DESC'),height=5)
    def reports(self):
        bar=self.toolbar();kind=tk.StringVar(value='Sales');start=tk.StringVar(value=date.today().replace(day=1).isoformat());end=tk.StringVar(value=date.today().isoformat())
        ttk.Combobox(bar,textvariable=kind,values=('Sales','Collections','Stock','Stock valuation','Low stock','Purchases','Customer dues','Expenses','Cash closing','Profit'),state='readonly',width=16).pack(side='left',padx=(0,10))
        for label,var in (('From',start),('To',end)):
            ttk.Label(bar,text=label).pack(side='left',padx=6);ttk.Entry(bar,textvariable=var,width=12).pack(side='left')
        holder=ttk.Frame(self.body);holder.pack(fill='both',expand=True);current={}
        def run():
            cols,rows=self.s.report(kind.get(),start.get(),end.get());current.update(cols=cols,rows=rows)
            for c in holder.winfo_children():c.destroy()
            Grid(holder,cols,rows)
            self.notice.set(f'{len(rows)} rows · Stock, valuation, low stock and dues show current positions. Collections are receipts before refunds. Profit uses historical costs; legacy costs are estimates.')
        self.button(bar,'Apply',run,True)
        def export():
            if not current:run()
            path=filedialog.asksaveasfilename(parent=self.root,defaultextension='.csv',filetypes=[('CSV spreadsheet','*.csv')],initialfile=kind.get().lower().replace(' ','_')+'.csv')
            if path:self.s.export_csv(path,current['cols'],current['rows']);self.notice.set('Report exported.')
        self.button(self.toolbar(),'Export CSV',export);run()
    def settings(self):
        self.s.authorize(True);values=self.s.settings();bar=self.toolbar()
        def password(target=None):
            Dialog(self,'Reset staff password' if target else 'Change password',[
                ('current','Your current password *','password'),('new','New password (10+ characters) *','password'),('confirm','Confirm new password *','password')],
                lambda v:self.s.change_password(v['current'],v['new'],v['confirm'],target),
                f'Reset access for {target}. Your own administrator password is required.' if target else 'Confirm your current password. Your shop data will remain unchanged.')

        def shop():
            fields=[('shop_name','Shop name','',values.get('shop_name','AINAK MAHAL')),('address','Address','',values.get('address','Millat Chowk, Faisalabad')),('phone','Shop mobile','',values.get('phone','')),('tax_rate','Tax rate (%)','',values.get('tax_rate','0')),('receipt_format','Receipt format',('A4','80 mm'),values.get('receipt_format','A4')),('printer','Preferred local printer (print dialog)','',values.get('printer','System default')),('backup_destination','Backup folder','',values.get('backup_destination',str(data_dir()/'backups')))]
            Dialog(self,'Shop settings',fields,self.s.save_settings)
        self.button(bar,'Edit shop settings',shop,True)
        self.button(bar,'Add staff account',lambda:Dialog(self,'Staff account',[('username','Username *'),('password','Password (10+ characters) *','password'),('role','Role',('cashier','admin'))],lambda v:self.s.create_user(v['username'],v['password'],v['role'])))
        ttk.Label(self.body,text='Staff accounts',font=(FONT,14,'bold')).pack(anchor='w',pady=(20,0))
        grid=Grid(self.body,('ID','Username','Role','Active'),self.s.users(),height=5)
        account_bar=self.toolbar()
        self.button(account_bar,'Enable / disable selected',lambda:(self.s.set_active(grid.selected()[1],not grid.selected()[3]),self.refresh()))
        self.button(account_bar,'Change my password',password)
        self.button(account_bar,'Reset staff password',lambda:password(grid.selected()[1]))
        ttk.Label(self.body,text='Audit trail · Latest 200 events',font=(FONT,14,'bold')).pack(anchor='w')
        Grid(self.body,('Staff','Action','Reference','Date'),self.s.rows('SELECT actor,action,reference,created_at FROM audit_events ORDER BY id DESC LIMIT 200'),height=5)
    def backup(self):
        self.s.authorize(True)
        ttk.Label(self.body,text='Your store data stays on this computer',font=(FONT,18,'bold')).pack(anchor='w',pady=(8,16))
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
        ttk.Label(self.body,text='Restore a backup',font=(FONT,16,'bold')).pack(anchor='w',pady=(32,12))
        ttk.Label(self.body,text='Close Ainak Mahal, then open “Ainak Mahal Recovery” from the Start menu.\nRecovery keeps a safety copy before restoring. Your administrator login is required.\nAfter restoring, sign in and run the stock and payment checks.',wraplength=800).pack(anchor='w')

def sign_in(root,service,on_login):
    theme(root);root.title('Ainak Mahal · Sign in');root.geometry('940x700');root.resizable(False,False)
    first=service.first_run()
    story=tk.Frame(root,bg=NAVY,width=348);story.pack(side='left',fill='y');story.pack_propagate(False)
    mark(story,80,NAVY,WHITE,'#5EEAD4').pack(anchor='w',padx=32,pady=(38,8))
    tk.Label(story,text='Ainak Mahal',bg=NAVY,fg=WHITE,font=(FONT,27,'bold')).pack(anchor='w',padx=38)
    tk.Label(story,text='OPTICAL STORE  /  FAISALABAD',bg=NAVY,fg='#BCD0E8',font=(FONT,9)).pack(anchor='w',padx=40,pady=(10,0))
    tk.Frame(story,bg='#36506E',height=1).pack(fill='x',padx=40,pady=(42,28))
    tk.Label(story,text='A clearer view.\nA better working day.',justify='left',anchor='w',wraplength=270,bg=NAVY,fg=WHITE,font=(FONT,22,'bold')).pack(anchor='w',padx=38)
    tk.Label(story,text='From the first fitting to the final collection.\nYour customers, prescriptions and shop,\ntogether in one place.',justify='left',bg=NAVY,fg='#CDDBEC',font=(FONT,10),wraplength=280).pack(anchor='w',padx=40,pady=20)
    tk.Label(story,text='●  WORKS COMPLETELY OFFLINE\nNo subscriptions. Your data stays yours.',justify='left',bg=NAVY,fg='#99F6E4',font=(FONT,9)).pack(side='bottom',anchor='w',padx=40,pady=36)
    frame=ttk.Frame(root,style='Card.TFrame',padding=(48,32));frame.pack(side='left',fill='both',expand=True)
    ttk.Label(frame,text='LET’S GET STARTED' if first else 'YOUR SHOP, READY WHEN YOU ARE',style='Card.TLabel',foreground=TEAL,font=(FONT,9,'bold')).pack(anchor='w',pady=(6,10))
    ttk.Label(frame,text='Set up your shop' if first else 'Welcome back',style='Card.TLabel',foreground=NAVY,font=(FONT,27,'bold')).pack(anchor='w')
    ttk.Label(frame,text='Create the administrator account for this computer.' if first else 'Sign in to your offline workspace.',style='Card.TLabel',foreground=MUTED,wraplength=450).pack(anchor='w',pady=(10,24))
    values={};entries={}
    for key,label in [('username','Username'),('password','Password')]+([('confirm','Confirm password')] if first else []):
        ttk.Label(frame,text=label,style='Card.TLabel',font=(FONT,10,'bold')).pack(anchor='w')
        var=tk.StringVar();values[key]=var
        entry=ttk.Entry(frame,textvariable=var,show='' if key=='username' else '•');entry.pack(fill='x',pady=(6,12));entries[key]=entry
    controls=ttk.Frame(frame,style='Card.TFrame');controls.pack(fill='x')
    visible=tk.BooleanVar(value=False)
    def toggle():
        for key,entry in entries.items():
            if key!='username':entry.configure(show='' if visible.get() else '•')
    ttk.Checkbutton(controls,text='Show password',variable=visible,command=toggle).pack(side='left')
    hint=ttk.Label(frame,text='Use 10 or more characters. Store your credentials safely.' if first else 'Passwords are case-sensitive.',style='Card.TLabel',foreground=MUTED,wraplength=440)
    hint.pack(anchor='w',pady=(10,0))
    def caps(event):
        hint.configure(text='Caps Lock is on.' if event.state & 2 else ('Use 10 or more characters. Store your credentials safely.' if first else 'Passwords are case-sensitive.'))
    for key,entry in entries.items():
        if key!='username':entry.bind('<KeyRelease>',caps)
    error=ttk.Label(frame,text='',background=WHITE,foreground=ERROR,wraplength=440);error.pack(fill='x',pady=(8,0))
    attempts=[0];pending=[None]
    def help_account():
        w=tk.Toplevel(root);w.title('Account access');w.geometry('540x370');w.transient(root)
        f=ttk.Frame(w,padding=28);f.pack(fill='both',expand=True)
        ttk.Label(f,text='Keep your shop data safe',font=(FONT,19,'bold')).pack(anchor='w')
        ttk.Label(f,text='There is no default password or master reset.\n\nAsk another active administrator to sign in, open Settings & team, select your account and use Reset staff password. They must confirm their own password.\n\nIf no administrator can sign in, keep the database and backups untouched and arrange technician-assisted recovery. Recovery never bypasses authentication or deletes your shop data.',wraplength=480,justify='left').pack(anchor='w',pady=18)
        ttk.Button(f,text='Back to sign in',command=w.destroy).pack(anchor='e')
        w.bind('<Escape>',lambda e:w.destroy())
    def submit():
        if button.instate(['disabled']):return
        for entry in entries.values():entry.state(['!invalid'])
        for key,var in values.items():
            if not var.get().strip():
                error.configure(text={'username':'Enter your username.','password':'Enter your password.','confirm':'Confirm your password.'}[key]);entries[key].state(['invalid']);entries[key].focus_set();return
        button.state(['disabled']);button.configure(text='Creating account…' if first else 'Signing in…');root.update_idletasks()
        try:
            if first:service.bootstrap(values['username'].get(),values['password'].get(),values['confirm'].get())
            else:service.login(values['username'].get(),values['password'].get())
        except Exception as ex:
            attempts[0]+=1;error.configure(text=error_copy(ex));entries['password'].state(['invalid'])
            def retry():
                if button.winfo_exists():button.state(['!disabled']);button.configure(text='Create administrator' if first else 'Sign in')
            pending[0]=root.after(min(500*attempts[0],5000),retry);return
        for var in values.values():var.set('')
        for child in root.winfo_children():child.destroy()
        root.unbind('<Return>');root.resizable(True,True);on_login()
    button=ttk.Button(frame,text='Create administrator' if first else 'Sign in',style='Primary.TButton',command=submit);button.pack(fill='x',pady=(14,10))
    ttk.Button(frame,text='Need help signing in?',style='Quiet.TButton',command=help_account).pack(anchor='w')
    ttk.Label(frame,text='Credentials are stored as salted password hashes on this computer.\nMillat Chowk, Faisalabad · Ainak Mahal',style='Card.TLabel',foreground=MUTED,font=(FONT,9),wraplength=440).pack(side='bottom',anchor='w',pady=(12,0))
    root.bind('<Return>',lambda e:submit())
    root.after_idle(entries['username'].focus_set)
    # Small controller also permits real widget interaction in source/installed smoke checks.
    root.sign_in_controls={'values':values,'entries':entries,'visible':visible,'toggle':toggle,'submit':submit,'error':error,'button':button}
