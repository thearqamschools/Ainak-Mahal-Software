"""Native Qt Widgets presentation. Business rules live in ERP/Retail services."""
import html
from datetime import date,timedelta
from pathlib import Path
from PySide6.QtCore import Qt,QTimer,QSizeF,QMarginsF
from PySide6.QtGui import QIcon,QKeySequence,QShortcut,QPainter,QPen,QColor,QFont,QPageSize,QPageLayout
from PySide6.QtWidgets import *
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtPrintSupport import QPrinter,QPrintDialog
from paths import data_dir

ASSETS=Path(__file__).resolve().parent/'assets'/'brand'
NAV=('Dashboard','New Sale / POS','Customers','Prescriptions','Inventory','Optical Jobs & Repairs','Purchases & Suppliers','Payments & Returns','Expenses & Accounts','Reports','Settings & Staff','Backup & Recovery')
STYLE='''
QWidget{font-family:"Segoe UI";font-size:10pt;color:#0F172A;}
QMainWindow,QDialog,#canvas{background:#F8FAFC;}
QFrame#sidebar{background:#142D4E;border:0;} QFrame#sidebar QLabel{color:#C9D8E7;}
QLabel#eyebrow{font-size:9pt;font-weight:600;color:#526277;}
QLabel#heading{font-size:24pt;font-weight:650;color:#142D4E;}
QLabel#section{font-size:13pt;font-weight:600;color:#142D4E;}
QLabel#muted{color:#526277;} QLabel#metric{font-size:25pt;font-weight:600;color:#142D4E;}
QFrame#card{background:white;border:1px solid #E2E8F0;border-radius:12px;}
QLabel#badge{color:#0F766E;background:#ECFDF5;border-radius:8px;padding:6px 10px;font-size:9pt;font-weight:600;}
QPushButton{background:white;border:1px solid #CBD5E1;border-radius:7px;padding:8px 14px;min-height:20px;font-weight:550;}
QPushButton:hover{background:#EFF6FF;border-color:#93C5FD;} QPushButton:pressed{background:#DBEAFE;}
QPushButton:focus{border:2px solid #2563EB;} QPushButton:disabled{color:#94A3B8;background:#F1F5F9;}
QPushButton#primary{background:#2563EB;color:white;border:1px solid #2563EB;}
QPushButton#primary:hover{background:#1D4ED8;} QPushButton#primary:pressed{background:#1E40AF;}
QPushButton#nav{text-align:left;color:#C9D8E7;background:transparent;border:0;padding:9px 12px;}
QPushButton#nav:hover{background:#1D3D63;color:white;} QPushButton#nav:checked{background:#264B74;color:white;border-left:3px solid #2DD4BF;}
QLineEdit,QComboBox,QSpinBox{background:white;border:1px solid #CBD5E1;border-radius:7px;padding:8px;min-height:20px;selection-background-color:#DBEAFE;}
QLineEdit:focus,QComboBox:focus,QSpinBox:focus{border:2px solid #2563EB;}
QComboBox::drop-down{border:0;width:24px;} QComboBox QAbstractItemView{background:white;selection-background-color:#DBEAFE;}
QTableWidget{background:white;alternate-background-color:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;selection-background-color:#DBEAFE;selection-color:#142D4E;}
QHeaderView::section{background:#F1F5F9;color:#526277;border:0;border-bottom:1px solid #E2E8F0;padding:10px;font-size:9pt;font-weight:600;}
QTabWidget::pane{background:white;border:1px solid #E2E8F0;border-radius:8px;}
QTabBar::tab{padding:10px 18px;background:#F1F5F9;border:0;} QTabBar::tab:selected{background:white;color:#2563EB;border-bottom:2px solid #2563EB;}
QScrollArea{border:0;background:transparent;} QScrollBar:vertical{background:#F1F5F9;width:10px;} QScrollBar::handle:vertical{background:#CBD5E1;border-radius:5px;min-height:24px;}
QCheckBox{spacing:8px;padding:5px;} QToolTip{background:#142D4E;color:white;padding:6px;}
'''

def label(text,kind=None):
    w=QLabel(str(text));w.setWordWrap(True)
    if kind:w.setObjectName(kind)
    return w
def vbox(parent=None,margin=0,spacing=12):
    l=QVBoxLayout(parent);l.setContentsMargins(margin,margin,margin,margin);l.setSpacing(spacing);return l
def card(title=None):
    w=QFrame();w.setObjectName('card');l=vbox(w,20)
    if title:l.addWidget(label(title,'section'))
    return w,l
def action(text,callback,primary=False):
    b=QPushButton(text.replace('&','&&'));b.setCursor(Qt.PointingHandCursor);b.clicked.connect(lambda _=False:callback())
    if primary:b.setObjectName('primary')
    return b
def combo(items):
    w=QComboBox()
    for text,val in (items.items() if isinstance(items,dict) else [(x,x) for x in items]):w.addItem(str(text),val)
    return w
def value(w):return w.currentData() if isinstance(w,QComboBox) else w.value() if isinstance(w,QSpinBox) else w.isChecked() if isinstance(w,QCheckBox) else w.text().strip()
def error_text(ex):
    import sqlite3
    if isinstance(ex,sqlite3.IntegrityError):return 'This record conflicts with existing data. Check unique SKU, barcode, username, reference or closing date, and confirm linked records exist.'
    return str(ex)

class NumberItem(QTableWidgetItem):
    def __lt__(self,other):
        a,b=self.data(Qt.UserRole+1),other.data(Qt.UserRole+1)
        if isinstance(a,(int,float)) and isinstance(b,(int,float)):return a<b
        return self.text().casefold()<other.text().casefold()
class Tabs(QTabWidget):
    def addTab(self,widget,title):return super().addTab(widget,title.replace('&','&&'))
class Table(QTableWidget):
    def __init__(self,columns,rows=()):
        super().__init__(0,len(columns));self.columns=columns;self.setHorizontalHeaderLabels(columns)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers);self.setSelectionBehavior(QAbstractItemView.SelectRows);self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setAlternatingRowColors(True);self.setShowGrid(False);self.verticalHeader().hide();self.verticalHeader().setDefaultSectionSize(38)
        self.horizontalHeader().setStretchLastSection(True);self.setMinimumHeight(180);self.replace(rows)
    def replace(self,rows):
        self.setSortingEnabled(False);self.setRowCount(0)
        for row in rows:
            n=self.rowCount();self.insertRow(n)
            for col,v in enumerate(row):
                if col>=self.columnCount():break
                cell=NumberItem('—' if v is None or v=='' else f'{v:,.2f}' if isinstance(v,float) else str(v));cell.setData(Qt.UserRole,tuple(row));cell.setData(Qt.UserRole+1,v)
                if 'PKR' in self.columns[col]:cell.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
                if str(v) in ('Ready','Delivered','Pending','In Lab','Cancelled'):cell.setForeground(QColor('#15803D' if v in ('Ready','Delivered') else '#92400E'))
                self.setItem(n,col,cell)
        self.resizeColumnsToContents()
        for col in range(self.columnCount()):self.setColumnWidth(col,min(320,max(100,self.columnWidth(col))))
        self.setSortingEnabled(True)
    def selected(self):
        if self.currentRow()<0 or not self.item(self.currentRow(),0):raise ValueError('Select a row first')
        return self.item(self.currentRow(),0).data(Qt.UserRole)
    def filter(self,text):
        for row in range(self.rowCount()):self.setRowHidden(row,not any(text.casefold() in self.item(row,col).text().casefold() for col in range(self.columnCount()) if self.item(row,col)))

class Form(QDialog):
    def __init__(self,parent,title,fields,save,context=''):
        super().__init__(parent);self.setWindowTitle(title);self.resize(650,650);self.setMinimumSize(470,380);self.inputs={};self.save=save
        outer=vbox(self,24);outer.addWidget(label(title,'section'))
        if context:outer.addWidget(label(context,'muted'))
        area=QScrollArea();area.setWidgetResizable(True);body=QWidget();form=QFormLayout(body);form.setVerticalSpacing(14);form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow);area.setWidget(body);outer.addWidget(area,1);eye_grid=None
        for spec in fields:
            key,text,*rest=spec;options=rest[0] if rest else None;default=rest[1] if len(rest)>1 else ''
            if key.startswith(('od_','os_')):
                if eye_grid is None:
                    eye=QWidget();eye_grid=QGridLayout(eye)
                    for i,caption in enumerate(('Eye','SPH','CYL','AXIS','ADD')):eye_grid.addWidget(label(caption,'eyebrow'),0,i)
                    eye_grid.addWidget(label('OD · Right'),1,0);eye_grid.addWidget(label('OS · Left'),2,0);form.addRow(eye)
                widget=QLineEdit(str(default));widget.setPlaceholderText('—');self.inputs[key]=widget;widget.setAccessibleName(text)
                eye_grid.addWidget(widget,1 if key.startswith('od') else 2,('sph','cyl','axis','add').index(key.split('_')[1])+1);continue
            if isinstance(options,(list,tuple,dict)):
                widget=combo(options);index=widget.findData(default)
                if index>=0:widget.setCurrentIndex(index)
            elif options=='check':widget=QCheckBox();widget.setChecked(bool(default))
            else:
                widget=QLineEdit(str(default))
                if options=='password':widget.setEchoMode(QLineEdit.Password)
            widget.setAccessibleName(text);self.inputs[key]=widget;form.addRow(text,widget)
        self.error=label('');self.error.setStyleSheet('color:#B91C1C');outer.addWidget(self.error)
        buttons=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);buttons.accepted.connect(self.submit);buttons.rejected.connect(self.reject);outer.addWidget(buttons);QShortcut(QKeySequence('Ctrl+Return'),self,activated=self.submit)
    def submit(self):
        try:self.save({k:value(w) for k,w in self.inputs.items()});self.accept()
        except Exception as ex:self.error.setText(error_text(ex))

class Trend(QWidget):
    def __init__(self,points):super().__init__();self.points=points;self.setMinimumHeight(150);self.setAccessibleName('Seven-day sales chart. Exact totals are available in Sales report.')
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);w,h=self.width(),self.height();left,right,top,bottom=30,w-25,20,h-35;p.setPen(QColor('#E2E8F0'))
        for i in range(4):y=top+(bottom-top)*i/3;p.drawLine(left,int(y),right,int(y))
        maximum=max([v for _,v in self.points]+[1]);points=[(left+(right-left)*i/max(1,len(self.points)-1),bottom-(bottom-top)*total/maximum) for i,(_,total) in enumerate(self.points)];p.setPen(QPen(QColor('#2563EB'),2.5))
        for (x,y),(x2,y2) in zip(points,points[1:]):p.drawLine(int(x),int(y),int(x2),int(y2))
        p.setBrush(QColor('#2563EB'))
        for x,y in points:p.drawEllipse(int(x)-3,int(y)-3,6,6)
        p.setPen(QColor('#526277'));p.setFont(QFont('Segoe UI',8))
        for (day,total),(x,y) in zip(self.points,points):p.drawText(int(x)-15,h-10,day[5:])

class Window(QMainWindow):
    def __init__(self,s):
        super().__init__();self.s=s;self.cart=[];self.current=0;self.report_data=None;self.resize(1440,920);self.setMinimumSize(1080,720)
        self.setWindowTitle('Ainak Mahal · Desktop ERP 2.0');self.setWindowIcon(QIcon(str(ASSETS/'ainak-mahal.ico')))
        shell=QWidget();self.setCentralWidget(shell);layout=QHBoxLayout(shell);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        sidebar=QFrame();sidebar.setObjectName('sidebar');sidebar.setFixedWidth(220);nav=vbox(sidebar,16,5);brand=QSvgWidget(str(ASSETS/'logo-dark.svg'));brand.setFixedSize(184,55);nav.addWidget(brand);nav.addWidget(label('OPTICAL STORE / FAISALABAD'));nav.addSpacing(18);self.nav=[]
        for i,name in enumerate(NAV):
            b=action(name,lambda i=i:self.safe(lambda:self.show_page(i)));b.setObjectName('nav');b.setCheckable(True);nav.addWidget(b);self.nav.append(b)
            if s.role!='admin' and i in (6,8,10,11):b.setEnabled(False);b.setToolTip('Administrator access required')
            if i in (3,7):nav.addSpacing(6)
        nav.addStretch();nav.addWidget(label('●  OFFLINE · LOCAL DATA'));nav.addWidget(label(f'{s.actor} / {s.role}'));layout.addWidget(sidebar)
        right=QWidget();right.setObjectName('canvas');content=vbox(right,24,14);layout.addWidget(right,1);top=QHBoxLayout();top.addWidget(label('AINAK MAHAL / WORKSPACE','eyebrow'));top.addStretch()
        self.search=QLineEdit();self.search.setPlaceholderText('Search workspace…  Ctrl+K');self.search.setMinimumWidth(260);self.search.returnPressed.connect(lambda:self.safe(self.global_search));top.addWidget(self.search);top.addWidget(action('Refresh',lambda:self.safe(self.refresh)));top.addWidget(label('Offline','badge'));content.addLayout(top)
        self.title=label('','heading');content.addWidget(self.title);self.subtitle=label('','muted');content.addWidget(self.subtitle);self.area=QScrollArea();self.area.setWidgetResizable(True);content.addWidget(self.area,1);self.notice=label('All changes are saved on this computer.','muted');content.addWidget(self.notice)
        QShortcut(QKeySequence('F2'),self,activated=lambda:self.show_page(1));QShortcut(QKeySequence('F3'),self,activated=lambda:self.show_page(2));QShortcut(QKeySequence('Ctrl+K'),self,activated=self.search.setFocus);QShortcut(QKeySequence('Ctrl+Return'),self,activated=lambda:self.safe(self.complete) if self.current==1 else None);self.show_page(0)
    def safe(self,f):
        try:return f()
        except Exception as ex:QMessageBox.warning(self,'Could not complete action',error_text(ex))
    def show_page(self,index):
        if self.current==1 and hasattr(self,'pos_customer') and not getattr(self,'skip_stash',False):
            self.pos_draft={k:value(getattr(self,k)) for k in ('pos_customer','pos_rx','new_name','new_phone','discount','paid','payment_method','make_job','job_kind','job_note','job_due','fulfillment')}
        self.skip_stash=False
        self.current=index
        for i,b in enumerate(self.nav):b.setChecked(i==index)
        self.title.setText(NAV[index]);self.subtitle.setText(('Your shop, in focus · '+date.today().strftime('%A, %d %B %Y')) if index==0 else {
            1:'Customer → prescription → eyewear → payment. One connected optical order.',2:'Search by name, mobile or customer number. Open a profile for the full history.',3:'OD = right eye · OS = left eye · Powers in dioptres · PD in millimetres.',4:'Know what is available, what needs replenishing and where every unit went.',5:'New glasses, lens replacements and repairs — from intake to delivery.',6:'Order, receive and pay suppliers. Receipt updates stock in one transaction.',7:'Collect balances, settle returns and record completed refunds.',8:'Cash movements, expenses and a clear daily count.',9:'Filter dated activity or inspect current stock and balances.',10:'Your shop identity, staff accounts and audit trail.',11:'Verified backups, safe recovery and local data checks.'}[index])
        old=self.area.takeWidget()
        if old:old.deleteLater()
        page=QWidget();page.setObjectName('canvas');self.body=vbox(page,0,16);self.area.setWidget(page);getattr(self,('dashboard','pos','customers','rx','inventory','jobs','purchasing','payments','accounts','reports','settings','backup')[index])()
    def refresh(self):self.show_page(self.current)
    def bar(self,parent=None):
        bar=QHBoxLayout();bar.setSpacing(8);(parent or self.body).addLayout(bar);return bar
    def button(self,bar,text,callback,primary=False):
        b=action(text,lambda:self.safe(callback),primary);bar.addWidget(b);return b
    def form(self,title,fields,save,context=''):
        d=Form(self,title,fields,save,context)
        if d.exec():self.notice.setText(title+' saved.');self.refresh()
        return d
    def customer_choices(self,optional=False):
        d={'Walk-in / none':None} if optional else {};d.update({f'{n} · {p or "no mobile"} · #{i}':i for i,n,p,_ in self.s.customers()});return d
    def product_choices(self):return {f'{r[1]} · {r[2]} · PKR {r[4]:,.2f}':r[0] for r in self.s.products()}
    def table(self,cols,rows,parent=None):
        t=Table(cols,rows);(parent or self.body).addWidget(t,1);return t
    def searchable(self,t,placeholder='Filter this table…'):
        e=QLineEdit();e.setPlaceholderText(placeholder);e.textChanged.connect(t.filter);self.body.insertWidget(0,e);return e
    def dashboard(self):
        metrics=self.s.dashboard();grid=QGridLayout()
        for i,(name,n) in enumerate(metrics.items()):
            w,l=card();l.addWidget(label('Gross sales today' if i==0 else name,'muted'));l.addWidget(label(f'PKR {n:,.0f}' if i<3 else str(n),'metric'))
            if i>=3:l.addWidget(action('Review low stock' if i==3 else 'Open optical jobs',lambda i=i:self.show_page(4 if i==3 else 5)))
            grid.addWidget(w,i//3,i%3)
        self.body.addLayout(grid);bar=self.bar();self.button(bar,'New optical sale  F2',lambda:self.show_page(1),True);self.button(bar,'Add customer',self.new_customer);self.button(bar,'New repair',self.new_job);bar.addStretch()
        panels=QHBoxLayout();w,l=card('Gross invoice sales · last seven days');points=[]
        for i in range(6,-1,-1):
            d=(date.today()-timedelta(days=i)).isoformat();points.append((d,self.s.scalar('SELECT COALESCE(SUM(total),0) FROM sales WHERE substr(date,1,10)=?',(d,))))
        l.addWidget(Trend(points));panels.addWidget(w,2);w,l=card('Ready for collection');ready=[r for r in self.s.job_list() if r[4]=='Ready'];l.addWidget(label(f'{len(ready)} jobs ready','metric'));l.addWidget(label('Collect the remaining balance before handing over a completed job.','muted'));l.addWidget(action('View jobs',lambda:self.show_page(5)));panels.addWidget(w,1);self.body.addLayout(panels)
        w,l=card('Recent transactions');self.table(('Invoice','Customer','Date','Total PKR','Paid PKR','Balance PKR'),self.s.sales()[:6],l);self.body.addWidget(w)
    def new_customer(self,row=None):
        p=self.s.profile(row[0]) if row else {}
        fields=[('name','Customer name *',None,row[1] if row else ''),('phone','Mobile',None,row[2] if row else ''),('address','Address',None,row[3] if row else ''),('whatsapp','WhatsApp · optional',None,p.get('whatsapp','')),('doctor','Referring doctor · optional',None,p.get('doctor','')),('gender','Gender · optional',('','Male','Female','Other','Prefer not to say'),p.get('gender','')),('dob','Date of birth · optional (YYYY-MM-DD)',None,p.get('dob',''))]
        def save(v):
            with self.s.db:
                cid=self.s.customer(v['name'],v['phone'],v['address'],row[0] if row else None);self.s.save_profile(cid,v['whatsapp'],v['doctor'],v['gender'],v['dob'])
        self.form('Customer profile',fields,save)
    def customers(self):
        bar=self.bar();self.button(bar,'Add customer',self.new_customer,True);bar.addStretch();t=self.table(('Customer #','Name','Mobile','Address'),self.s.customers());self.searchable(t,'Search name, mobile or customer number…')
        bar=self.bar();self.button(bar,'Open profile',lambda:self.customer_profile(t.selected()[0]));self.button(bar,'Edit contact details',lambda:self.new_customer(t.selected()));self.button(bar,'Export customers',lambda:self.export_table(t));t.itemDoubleClicked.connect(lambda *_:self.safe(lambda:self.customer_profile(t.selected()[0])))
        if not t.rowCount():self.body.addWidget(label('No customers yet. Add one to keep prescriptions, orders and balances together.','muted'))
    def customer_profile(self,cid):
        r=next(r for r in self.s.customers(str(cid)) if r[0]==cid);sales,rx,jobs=self.s.customer_position(cid);p=self.s.profile(cid);d=QDialog(self);d.setWindowTitle(r[1]+' · Profile');d.resize(1060,690);l=vbox(d,24)
        l.addWidget(label(r[1],'heading'));l.addWidget(label(f'Customer #{cid} · {r[2] or "No mobile"} · {r[3] or "No address"}','muted'));l.addWidget(label(f'Net balance PKR {sum(r[5] for r in sales):,.2f} / {len(sales)} invoices / {len(rx)} prescriptions','section'))
        if p['doctor'] or p['whatsapp']:l.addWidget(label(f'Referred by: {p["doctor"] or "—"} · WhatsApp: {p["whatsapp"] or "—"}','muted'))
        tabs=Tabs();l.addWidget(tabs,1)
        for title,cols,rows in [('Sales & balances',('Invoice','Customer','Date','Total PKR','Paid PKR','Due PKR'),sales),('Prescription history',('Rx','Customer','Date','OD SPH','OD CYL','OD AXIS','OD ADD','OS SPH','OS CYL','OS AXIS','OS ADD','PD','Notes'),rx),('Optical jobs',('Job','Instructions','Status','Promised','Invoice'),jobs)]:tabs.addTab(Table(cols,rows),title)
        l.addWidget(action('Close',d.accept));d.exec()
    def rx_fields(self):return [(eye+'_'+f,eye.upper()+' '+f.upper()) for eye in ('od','os') for f in ('sph','cyl','axis','add')]+[('pd','PD (mm)'),('notes','Prescription notes')]
    def new_rx(self):self.form('New prescription',[('customer','Customer *',self.customer_choices()),('date','Date *',None,date.today().isoformat())]+self.rx_fields(),lambda v:self.s.save_rx(v['customer'],v,v['date']),'Leave unmeasured powers blank. Cylinder requires an axis. Add a new record to preserve history.')
    def rx(self):
        bar=self.bar();self.button(bar,'Add prescription',self.new_rx,True);self.button(bar,'Optical calculators',self.calculators);bar.addStretch();t=self.table(('Rx','Customer','Date','OD SPH','OD CYL','OD AXIS','OD ADD','OS SPH','OS CYL','OS AXIS','OS ADD','PD','Notes'),self.s.prescriptions());self.searchable(t);self.button(self.bar(),'Print / PDF selected prescription',lambda:self.print_doc('Prescription',t.selected()[0]))
    def calculators(self):
        def calc(v):
            from retail import rx_number
            from decimal import Decimal
            s=Decimal(rx_number(v['sph'],-30,30,.25));c=Decimal(rx_number(v['cyl'],-15,15,.25));a=int(rx_number(v['axis'],0,180,1))
            QMessageBox.information(self,'Optical calculation',f'Transposed: {s+c:+.2f} / {-c:+.2f} × {(a+90-1)%180+1}°\nSpherical equivalent: {s+c/2:+.2f} D')
        self.form('Optical calculations',[('sph','SPH *'),('cyl','CYL *'),('axis','AXIS *')],calc,'Mathematical conversion only. Verify measurements and use professional judgement.')
    def pos(self):
        columns=QHBoxLayout();columns.setSpacing(20);left=QWidget();ll=vbox(left);right=QWidget();rl=vbox(right);right.setMinimumWidth(300);right.setMaximumWidth(390);columns.addWidget(left,3);columns.addWidget(right,2);self.body.addLayout(columns)
        w,l=card('1  Customer & prescription');self.pos_customer=combo(self.customer_choices(True));self.pos_customer.setAccessibleName('Customer');l.addWidget(self.pos_customer)
        self.new_name=QLineEdit();self.new_name.setPlaceholderText('New customer name · optional');self.new_phone=QLineEdit();self.new_phone.setPlaceholderText('New customer mobile');nr=QHBoxLayout();nr.addWidget(self.new_name);nr.addWidget(self.new_phone);l.addLayout(nr)
        self.pos_rx=combo({'No prescription':None});self.pos_rx.setAccessibleName('Prescription');l.removeWidget(self.pos_customer);customer_row=QHBoxLayout();customer_row.addWidget(self.pos_customer,1);customer_row.addWidget(self.pos_rx,1);l.insertLayout(1,customer_row)
        def prescriptions():
            cid=value(self.pos_customer);self.pos_rx.clear();self.pos_rx.addItem('No prescription',None)
            if cid:
                for r in self.s.prescriptions(cid):self.pos_rx.addItem(f'Rx #{r[0]} · {r[2]} · OD {r[3] or "—"} / OS {r[7] or "—"}',r[0])
        self.pos_customer.currentIndexChanged.connect(prescriptions);self.draft_rx=getattr(self,'draft_rx',None)
        def new_prescription():
            d=Form(self,'Prescription for this order',self.rx_fields(),lambda v:setattr(self,'draft_rx',v),'Saved with this order in the same transaction. Select or enter a customer first.')
            if d.exec():self.pos_rx.setCurrentIndex(0);self.rx_hint.setText('New prescription entered · pending checkout')
        l.addWidget(action('Enter new prescription for this order',new_prescription));self.rx_hint=label('Optional for counter sales.','muted');l.addWidget(self.rx_hint);ll.addWidget(w)
        w,l=card('2  Eyewear & services');self.scan=QLineEdit();self.scan.setPlaceholderText('Scan barcode or search name / SKU');self.scan.setAccessibleName('Product search or barcode');l.addWidget(self.scan)
        self.catalog=Table(('ID','SKU','Item','PKR','Available'),[(r[0],r[1],r[2],r[4],'Service' if r[9] else r[5]) for r in self.s.products()]);self.catalog.setMinimumHeight(100);self.catalog.setMaximumHeight(120);l.addWidget(self.catalog)
        self.scan.textChanged.connect(lambda term:self.catalog.replace([(r[0],r[1],r[2],r[4],'Service' if r[9] else r[5]) for r in self.s.products(term)]))
        row=QHBoxLayout();self.qty=QSpinBox();self.qty.setRange(1,10000);self.qty.setAccessibleName('Units');row.addWidget(label('Units'));row.addWidget(self.qty);self.button(row,'Add to order',self.add_cart,True);row.addStretch();l.addLayout(row)
        self.scan.returnPressed.connect(lambda:self.safe(self.add_cart));self.catalog.itemDoubleClicked.connect(lambda *_:self.safe(self.add_cart));self.cart_table=Table(('ID','Item','Units','Unit PKR','Line PKR'));self.cart_table.setMinimumHeight(130);self.cart_table.setMaximumHeight(180);l.addWidget(self.cart_table);self.button(l,'Remove selected line',self.remove_cart);ll.addWidget(w)
        w,l=card('3  Checkout');self.discount=QLineEdit(getattr(self,'draft_discount','0'));self.paid=QLineEdit(getattr(self,'draft_paid','0'));self.payment_method=combo(('Cash','Bank','Card'))
        for text,widget in (('Discount · PKR',self.discount),('Amount received · PKR',self.paid),('Payment method',self.payment_method)):l.addWidget(label(text,'muted'));l.addWidget(widget)
        self.total=label('','section');l.addWidget(self.total);self.discount.textChanged.connect(self.redraw_cart);self.paid.textChanged.connect(self.redraw_cart);self.button(l,'Save optical order   Ctrl+Enter',self.complete,True);l.addWidget(label('Enter money retained after giving change. A balance requires a named customer.','muted'));rl.addWidget(w)
        w,l=card('4  Optical job · optional');self.make_job=QCheckBox('Create a linked optical job');l.addWidget(self.make_job);self.job_kind=combo(('New glasses','Lens replacement','Frame repair','General repair'));l.addWidget(self.job_kind);self.job_note=QLineEdit();self.job_note.setPlaceholderText('Lab instructions');l.addWidget(self.job_note)
        self.job_due=QLineEdit(date.today().isoformat());self.job_due.setAccessibleName('Promised date');l.addWidget(label('Promised date · YYYY-MM-DD','muted'));l.addWidget(self.job_due);self.fulfillment=combo(('Collection','Delivery'));l.addWidget(self.fulfillment);rl.addWidget(w);rl.addStretch()
        for key,val in getattr(self,'pos_draft',{}).items():
            widget=getattr(self,key)
            if isinstance(widget,QComboBox):
                index=widget.findData(val)
                if index>=0:widget.setCurrentIndex(index)
            elif isinstance(widget,QCheckBox):widget.setChecked(bool(val))
            else:widget.setText(str(val))
        if self.draft_rx:self.rx_hint.setText('New prescription entered · pending checkout')
        self.redraw_cart();self.scan.setFocus()
    def add_cart(self):
        if self.catalog.rowCount()==1:self.catalog.selectRow(0)
        pid=self.catalog.selected()[0];candidate=self.cart+[(pid,self.qty.value())];self.s.quote(candidate,self.discount.text() or 0);grouped={}
        for p,q in candidate:grouped[p]=grouped.get(p,0)+q
        self.cart=list(grouped.items());self.scan.clear();self.redraw_cart();self.scan.setFocus()
    def remove_cart(self):
        pid=self.cart_table.selected()[0];self.cart=[(p,q) for p,q in self.cart if p!=pid];self.redraw_cart()
    def redraw_cart(self,*_):
        products={r[0]:r for r in self.s.products()};self.cart_table.replace([(pid,products[pid][2],q,products[pid][4],q*products[pid][4]) for pid,q in self.cart]);self.draft_discount=self.discount.text();self.draft_paid=self.paid.text()
        if not self.cart:self.total.setText('Your order is empty\nAdd a frame, lenses or service.');return
        try:
            _,sub,disc,tax,total=self.s.quote(self.cart,self.discount.text() or 0)
            from core import money
            self.total.setText(f'Subtotal   PKR {sub/100:,.2f}\nDiscount  PKR {disc/100:,.2f}\nTax             PKR {tax/100:,.2f}\n\nTotal          PKR {total/100:,.2f}\nBalance    PKR {(total-money(self.paid.text() or 0))/100:,.2f}')
        except Exception as ex:self.total.setText(error_text(ex))
    def complete(self):
        new={'name':self.new_name.text(),'phone':self.new_phone.text()} if self.new_name.text().strip() else None
        if new and value(self.pos_customer):raise ValueError('Choose an existing customer or enter a new one, rather than both')
        if self.make_job.isChecked() and not self.job_note.text().strip():raise ValueError('Enter instructions for the linked job')
        sid,total,due,jid=self.s.place_order(self.cart,value(self.pos_customer),new,value(self.pos_rx),self.draft_rx,self.paid.text() or 0,value(self.payment_method),self.discount.text() or 0,self.job_note.text() if self.make_job.isChecked() else '',self.job_due.text(),value(self.job_kind),value(self.fulfillment))
        self.cart=[];self.draft_rx=None;self.draft_discount='0';self.draft_paid='0';self.pos_draft={};self.skip_stash=True;self.refresh();self.notice.setText(f'Invoice #{sid} saved · PKR {total:,.2f} · Balance PKR {due:,.2f}'+(' · Optical job created' if jid else ''))
        if QMessageBox.question(self,'Order saved',f'Invoice #{sid} is saved. Open its receipt now?')==QMessageBox.Yes:self.print_doc('Invoice',sid)
    def inventory(self):
        products=self.s.products();physical=[r for r in products if not r[9]];bar=self.bar();self.button(bar,'Add product',self.new_product,True);category=combo(('All categories','Frames','Lenses','Contact lenses','Sunglasses','Accessories','Service'));bar.addWidget(category);bar.addStretch();self.body.addWidget(label(f'{len(products)} catalog items · {sum(r[5] for r in physical)} physical units · {sum(r[5]<=r[8] for r in physical)} low stock','muted'))
        t=self.table(('ID','SKU','Item','Category','Price PKR','Stock','Barcode','Variant','Reorder','Service'),products);search=QLineEdit();search.setPlaceholderText('Search SKU, name, barcode or variant…');self.body.insertWidget(1,search)
        def filt():t.replace([r for r in self.s.products(search.text()) if value(category)=='All categories' or r[3]==value(category)])
        search.textChanged.connect(filt);category.currentIndexChanged.connect(filt);bar=self.bar();self.button(bar,'Edit item',lambda:self.edit_product(t.selected()));self.button(bar,'Adjust stock',lambda:self.adjust_stock(t.selected()));self.button(bar,'Stock history',lambda:self.stock_history(t.selected()));self.button(bar,'Lens matrix',self.lens_matrix);self.button(bar,'Print label',lambda:self.product_label(t.selected()))
    def new_product(self):
        fields=[('sku','SKU *'),('name','Item name *'),('category','Category',('Frames','Lenses','Contact lenses','Sunglasses','Accessories','Service')),('price','Selling price PKR *'),('cost','Purchase cost PKR',None,0),('qty','Opening units',None,0),('barcode','Barcode · optional'),('variant','Variant / size / colour'),('sph','Lens SPH · optional'),('cyl','Lens CYL · optional'),('reorder','Reorder threshold',None,2)]
        self.form('New catalog item',fields,lambda v:self.s.product(v['sku'],v['name'],v['price'],v['cost'],v['qty'],v['category'],v['barcode'],v['variant'],v['sph'],v['cyl'],v['reorder'],v['category']=='Service'))
    def edit_product(self,r):
        cost=self.s.scalar('SELECT cost FROM products WHERE id=?',(r[0],));self.form('Catalog details',[('name','Item name *',None,r[2]),('price','Selling price PKR',None,r[4]),('cost','Unit cost PKR',None,cost),('barcode','Barcode',None,r[6]),('variant','Variant',None,r[7]),('reorder','Reorder threshold',None,r[8])],lambda v:self.s.edit_product(r[0],v['name'],v['price'],v['cost'],v['barcode'],v['variant'],v['reorder']))
    def adjust_stock(self,r):self.form('Stock adjustment',[('delta','Units to add / remove (negative for reduction)'),('reason','Reason *')],lambda v:self.s.adjust(r[0],v['delta'],v['reason']),f'{r[2]} · Current stock: {r[5]}')
    def stock_history(self,r):self.viewer('Stock history · '+r[2],('Units','Reason','Reference','Date'),self.s.rows('SELECT delta,reason,reference_id,created_at FROM stock_movements WHERE product_id=? ORDER BY created_at DESC',(r[0],)))
    def lens_matrix(self):self.viewer('Lens power inventory',('Category','SPH','CYL','Variant','Units'),self.s.rows("SELECT p.category,d.sph,d.cyl,d.variant,SUM(p.qty) FROM product_details d JOIN products p ON p.id=d.product_id WHERE p.category IN ('Lenses','Contact lenses') GROUP BY p.category,d.sph,d.cyl,d.variant ORDER BY p.category,CAST(d.sph AS REAL),CAST(d.cyl AS REAL)"))
    def product_label(self,r):
        from labels import barcode_png
        path=barcode_png(r[6] or r[1],data_dir()/'documents'/f'barcode_{r[0]}.png')
        self.document('Product label',f'<h2>{html.escape(r[2])}</h2><p>SKU {html.escape(r[1])}</p><img src="{path.as_uri()}" width="300" height="90"><p>{html.escape(r[6] or r[1])} · PKR {r[4]:,.2f}</p>')
    def viewer(self,title,cols,rows):
        d=QDialog(self);d.setWindowTitle(title);d.resize(1000,650);l=vbox(d,24);l.addWidget(label(title,'section'));t=Table(cols,rows);l.addWidget(t,1);bar=QHBoxLayout();bar.addWidget(action('Export CSV',lambda:self.safe(lambda:self.export_table(t))));bar.addWidget(action('Close',d.accept));l.addLayout(bar);d.exec()
    def new_job(self):
        fields=[('customer','Customer *',self.customer_choices()),('kind','Job type',('New glasses','Lens replacement','Frame repair','General repair')),('description','Instructions *'),('due','Promised date *',None,date.today().isoformat()),('invoice','Existing invoice # · optional'),('rx','Existing Rx # · optional'),('charge','New repair charges PKR',None,0),('paid','Advance received PKR',None,0),('method','Advance method',('Cash','Bank','Card')),('fulfillment','Fulfillment',('Collection','Delivery')),('supplier','Outsourced supplier',{'In-house':None,**{f'{r[1]} · #{r[0]}':r[0] for r in self.s.suppliers()}})]
        self.form('Optical job or repair',fields,lambda v:self.s.create_job(v['customer'],v['kind'],v['description'],v['due'],int(v['invoice']) if v['invoice'] else None,int(v['rx']) if v['rx'] else None,v['fulfillment'],v['supplier'],v['charge'],v['paid'],v['method']),'For a linked sale, charges/payments belong on that invoice. For a new repair, enter charges and advance here.')
    def jobs(self):
        bar=self.bar();self.button(bar,'New optical job / repair',self.new_job,True);status=combo(('Active jobs','All jobs','Pending','In Lab','Ready','Delivered','Cancelled'));bar.addWidget(status);bar.addStretch();t=self.table(('Job ID','Customer','Type','Instructions','Status','Promised','Invoice','Rx','Fulfillment','Lab / supplier'),self.s.job_list())
        def filt():t.replace([r for r in self.s.job_list() if value(status)=='All jobs' or (value(status)=='Active jobs' and r[4] not in ('Delivered','Cancelled')) or r[4]==value(status)])
        status.currentIndexChanged.connect(filt);filt();self.searchable(t,'Filter customer, job number or instructions…')
        def update():
            r=t.selected();allowed={'Pending':['In Lab','Cancelled'],'In Lab':['Ready','Cancelled'],'Ready':['Delivered']}.get(r[4],[])
            if not allowed:raise ValueError('This job is complete and cannot advance further')
            self.form('Update job status',[('status','Next status',allowed)],lambda v:self.s.advance_job(r[0],v['status']),r[1]+' · '+r[3])
        bar=self.bar();self.button(bar,'Update status',update);self.button(bar,'Print / PDF job receipt',lambda:self.print_doc('Job',t.selected()[0]));self.button(bar,'Receive job payment',lambda:self.receive_payment(t.selected()[6]))
    def purchasing(self):
        self.s.authorize(True);bar=self.bar();self.button(bar,'Add supplier',lambda:self.form('Supplier',[('name','Supplier name *'),('phone','Mobile')],lambda v:self.s.supplier(v['name'],v['phone'])));self.button(bar,'New purchase order',lambda:self.purchase_dialog(False),True);self.button(bar,'Receive without PO',lambda:self.purchase_dialog(True));bar.addStretch()
        tabs=Tabs();self.body.addWidget(tabs,1);orders=Table(('PO','Supplier','Created','Status'),self.s.purchase_orders());receipts=Table(('Receipt','Supplier','Date','Total PKR','Paid PKR','Due PKR','Opening status'),self.s.purchases());suppliers=Table(('ID','Supplier','Phone','Purchased PKR','Paid PKR','Confirmed due PKR','Unverified'),self.s.supplier_balances());tabs.addTab(orders,'Purchase orders');tabs.addTab(receipts,'Receipts & payments');tabs.addTab(suppliers,'Supplier profiles');bar=self.bar()
        def receive():
            r=orders.selected()
            if QMessageBox.question(self,'Receive order',f'Receive all lines on PO #{r[0]}? Confirm delivered quantities first.')==QMessageBox.Yes:self.s.receive_po(r[0]);self.refresh()
        self.button(bar,'Receive selected PO',receive)
        def pay():
            r=receipts.selected()
            if r[5] is None:raise ValueError('Confirm the legacy opening balance before recording a payment')
            self.form('Supplier payment',[('amount','Amount actually paid PKR *'),('method','Method',('Cash','Bank','Card')),('reference','Unique receipt / transfer reference *')],lambda v:self.s.supplier_payment(r[0],v['amount'],v['method'],v['reference']),f'Receipt #{r[0]} · {r[1]} · Balance PKR {r[5]:,.2f}')
        self.button(bar,'Record supplier payment',pay)
        def opening():
            r=receipts.selected();self.form('Confirm legacy supplier opening',[('balance','Verified unpaid balance PKR')],lambda v:self.s.confirm_supplier_opening(r[0],v['balance']),'Check the supplier statement. Historical paid amounts are opening adjustments, not new cash payments.')
        self.button(bar,'Confirm legacy opening',opening);self.button(bar,'Supplier history',lambda:self.viewer('Supplier purchase history',('Receipt','Date','Total PKR'),self.s.rows('SELECT id,date,total FROM purchases WHERE supplier_id=? ORDER BY id DESC',(suppliers.selected()[0],))))
    def purchase_dialog(self,direct=False):
        self.s.authorize(True);suppliers={f'{r[1]} · #{r[0]}':r[0] for r in self.s.suppliers()};products=self.product_choices()
        if not suppliers or not products:raise ValueError('Add a supplier and products before creating a purchase')
        d=QDialog(self);d.setWindowTitle('Goods receipt' if direct else 'Purchase order');d.resize(950,650);l=vbox(d,24);supplier=combo(suppliers);product=combo(products);l.addWidget(label('Supplier','section'));l.addWidget(supplier);l.addWidget(label('Product'));l.addWidget(product);qty=QSpinBox();qty.setRange(1,100000);cost=QLineEdit('0');row=QHBoxLayout();row.addWidget(label('Units'));row.addWidget(qty);row.addWidget(label('Unit cost PKR'));row.addWidget(cost);l.addLayout(row);lines=[];t=Table(('Product #','Units','Unit cost PKR'));l.addWidget(t,1)
        def add():
            from core import money
            lines.append((value(product),qty.value(),money(cost.text())/100));t.replace(lines)
        self.button(row,'Add line',add);bar=QHBoxLayout();l.addLayout(bar)
        def remove():lines.remove(tuple(t.selected()));t.replace(lines)
        self.button(bar,'Remove line',remove)
        def save():
            if direct:self.s.receive(value(supplier),lines)
            else:self.s.create_po(value(supplier),lines)
            d.accept();self.refresh();self.notice.setText('Goods received.' if direct else 'Purchase order saved.')
        self.button(bar,'Receive goods' if direct else 'Save order',save,True);self.button(bar,'Cancel',d.reject);d.exec()
    def receive_payment(self,sid):
        if not sid:raise ValueError('This job has no invoice; create a charged repair or link a sale first')
        r=next(r for r in self.s.sales() if r[0]==sid);self.form('Customer payment',[('amount','Amount received PKR *'),('method','Method',('Cash','Bank','Card'))],lambda v:self.s.pay(sid,v['amount'],v['method']),f'Invoice #{sid} · {r[1]} · Balance PKR {r[5]:,.2f}')
    def payments(self):
        tabs=Tabs();self.body.addWidget(tabs,1);sales=Table(('Invoice','Customer','Date','Total PKR','Paid PKR','Balance PKR'),self.s.sales());refunds=Table(('Return','Invoice','Method','Payout due PKR','Paid PKR'),self.s.rows('''SELECT r.id,r.sale_id,s.method,s.cash_refund_cents/100.0,COALESCE((SELECT SUM(amount_cents)/100.0 FROM refund_payouts WHERE return_id=r.id),0) FROM sale_returns r JOIN return_settlements s ON s.return_id=r.id ORDER BY r.id DESC'''));tabs.addTab(sales,'Invoices & balances');tabs.addTab(refunds,'Refund settlements');search=QLineEdit();search.setPlaceholderText('Filter customer or invoice…');search.textChanged.connect(sales.filter);self.body.insertWidget(0,search);bar=self.bar();self.button(bar,'Receive payment',lambda:self.receive_payment(sales.selected()[0]),True);self.button(bar,'Print invoice',lambda:self.print_doc('Invoice',sales.selected()[0]))
        def ret():
            self.s.authorize(True);r=sales.selected();products={f'{n} · #{pid}':pid for pid,n in self.s.rows('SELECT DISTINCT p.id,p.name FROM sale_items i JOIN products p ON p.id=i.product_id WHERE sale_id=?',(r[0],))}
            def save(v):
                result=self.s.return_item(r[0],v['product'],v['qty'],v['reason'],v['method']);QMessageBox.information(self,'Return saved',f'Return #{result["return_id"]} · PKR {result["refund_value"]:,.2f}\nPayout due PKR {result["payout_due"]:,.2f}\nRecord payout only after actually paying the customer.')
            self.form('Return items',[('product','Product',products),('qty','Units',None,1),('reason','Reason *'),('method','Settlement',('Cash','Bank','Credit'))],save)
        self.button(bar,'Return items',ret)
        def credit():
            r=sales.selected()
            if r[5]>=0:raise ValueError('Select an invoice with a negative balance (available store credit)')
            self.form('Redeem store credit',[('target','Destination invoice #'),('amount','Amount PKR')],lambda v:self.s.redeem_credit(r[0],int(v['target']),v['amount']),f'Available credit PKR {-r[5]:,.2f}. Both invoices must belong to the same customer.')
        self.button(bar,'Apply credit',credit)
        def payout():
            r=refunds.selected()
            def save(v):
                if QMessageBox.question(self,'Confirm completed payout','Have you already paid this money to the customer? This records payment; it does not transfer money.')!=QMessageBox.Yes:raise ValueError('Payout was not recorded')
                self.s.payout(r[0],v['amount'],v['method'],v['reference'])
            self.form('Completed refund payout',[('amount','Amount actually paid PKR'),('method','Method',('Cash','Bank')),('reference','Unique reference *')],save,f'Return #{r[0]} · Remaining PKR {r[3]-r[4]:,.2f}')
        self.button(self.bar(),'Record completed refund payout',payout)
    def accounts(self):
        self.s.authorize(True);today=date.today().isoformat();w,l=card('Cash drawer · today');l.addWidget(label(f'PKR {self.s.expected_cash(today)/100:,.2f}','metric'));l.addWidget(label('Collections + opening/in − cash out − expenses − completed refunds − supplier cash payments.','muted'));self.body.addWidget(w);bar=self.bar()
        self.button(bar,'Record expense',lambda:self.form('Cash expense',[('description','Description *'),('amount','Cash paid PKR *')],lambda v:self.s.expense(v['description'],v['amount'])),True)
        self.button(bar,'Cash movement',lambda:self.form('Cash movement',[('kind','Movement',('Opening','Cash in','Cash out')),('amount','Amount PKR'),('note','Reason *')],lambda v:self.s.cash(v['kind'],v['amount'],v['note'])))
        self.button(bar,'Close day',lambda:self.form('Daily cash closing',[('day','Closing day',None,today),('counted','Cash counted PKR'),('note','Count notes')],lambda v:self.s.close_day(v['day'],v['counted'],v['note']),'Count after all trading. Closing saves an immutable snapshot; later transactions do not alter it.'))
        tabs=Tabs();self.body.addWidget(tabs,1);tabs.addTab(Table(('Date','Description','PKR'),self.s.rows('SELECT date,description,amount FROM expenses ORDER BY id DESC')),'Expenses');tabs.addTab(Table(('Day','Movement','PKR','Reason','Staff'),self.s.rows('SELECT day,kind,amount_cents/100.0,note,actor FROM cash_movements ORDER BY created_at DESC')),'Cash movements');cols,rows=self.s.report('Cash closing','2000-01-01','2099-12-31');tabs.addTab(Table(cols,rows),'Closing history')
    def reports(self):
        bar=self.bar();self.report_kind=combo(('Sales','Collections','Customer dues','Stock','Inventory valuation','Low stock','Purchases','Supplier balances','Supplier payments','Expenses','Cash closing','Profit'));self.report_start=QLineEdit(date.today().replace(day=1).isoformat());self.report_end=QLineEdit(date.today().isoformat());self.report_start.setMaximumWidth(140);self.report_end.setMaximumWidth(140)
        bar.addWidget(self.report_kind);bar.addWidget(label('From'));bar.addWidget(self.report_start);bar.addWidget(label('To'));bar.addWidget(self.report_end);self.button(bar,'Apply',self.run_report,True);self.report_table=Table(('Report',),[]);self.body.addWidget(self.report_table,1);bar=self.bar();self.button(bar,'Export CSV',lambda:self.export_table(self.report_table));self.button(bar,'Print / save PDF',self.print_report);self.body.addWidget(label('Stock, supplier and customer balances are current positions. Profit is an operational estimate; legacy costs may be unavailable.','muted'));self.run_report()
    def run_report(self):
        cols,rows=self.s.report(value(self.report_kind),self.report_start.text(),self.report_end.text());self.report_data=(cols,rows);self.report_table.columns=cols;self.report_table.setColumnCount(len(cols));self.report_table.setHorizontalHeaderLabels(cols);self.report_table.replace(rows);self.notice.setText(f'{len(rows)} report rows.')
    def export_table(self,t):
        path,_=QFileDialog.getSaveFileName(self,'Export CSV','ainak_mahal.csv','CSV spreadsheet (*.csv)')
        if path:
            rows=[tuple(t.item(i,0).data(Qt.UserRole)) for i in range(t.rowCount()) if not t.isRowHidden(i) and t.item(i,0)];self.s.export_csv(path,t.columns,rows);self.notice.setText('CSV report exported.')
    def print_report(self):
        if not self.report_data:self.run_report()
        cols,rows=self.report_data;esc=lambda v:html.escape(str(v if v is not None else ''));content='<h1>'+esc(value(self.report_kind))+'</h1><p>'+esc(self.report_start.text())+' to '+esc(self.report_end.text())+'</p><table border="1" cellpadding="6"><tr>'+''.join('<th>'+esc(c)+'</th>' for c in cols)+'</tr>';content+=''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in r)+'</tr>' for r in rows)+'</table>';self.document('Ainak Mahal report',content)
    def settings(self):
        self.s.authorize(True);settings=self.s.settings();bar=self.bar()
        def shop():
            fields=[('shop_name','Shop name',None,settings.get('shop_name','AINAK MAHAL')),('address','Address',None,settings.get('address','Millat Chowk, Faisalabad')),('phone','Mobile',None,settings.get('phone','')),('tax_rate','Tax rate %',None,settings.get('tax_rate','0')),('receipt_format','Receipt format',('A4','80 mm'),settings.get('receipt_format','A4')),('printer','Preferred local printer',None,settings.get('printer','System default')),('backup_destination','Backup folder',None,settings.get('backup_destination',str(data_dir()/'backups')))]
            self.form('Shop settings',fields,self.s.save_settings)
        self.button(bar,'Edit shop settings',shop,True);self.button(bar,'Add staff account',lambda:self.form('Staff account',[('username','Username *'),('password','Password (10+ characters) *','password'),('role','Role',('cashier','admin'))],lambda v:self.s.create_user(v['username'],v['password'],v['role'])));self.button(bar,'About & offline data',self.about)
        t=self.table(('ID','Username','Role','Active'),self.s.users());self.button(self.bar(),'Enable / disable selected',lambda:(self.s.set_active(t.selected()[1],not t.selected()[3]),self.refresh()));self.body.addWidget(label('Audit trail · latest 200 events','section'));self.table(('Staff','Action','Reference','Date'),self.s.rows('SELECT actor,action,reference,created_at FROM audit_events ORDER BY id DESC LIMIT 200'))
    def about(self):self.document('About Ainak Mahal','<h1>Ainak Mahal Desktop ERP 2.0</h1><p>Millat Chowk, Faisalabad · Offline optical store management.</p><p>Data stays in your Windows profile. No subscription, telemetry or cloud account. Keep verified backups on another drive.</p><p>Original artwork and Qt Widgets UI. Qt/PySide6 are dynamically distributed under their applicable open-source licenses. See bundled license notices, source and replacement instructions.</p>')
    def backup(self):
        self.s.authorize(True);w,l=card('Keep a verified copy, every day');l.addWidget(label(str(data_dir()/'ainak_mahal.db'),'muted'));l.addWidget(label('Backups contain customer details and password hashes. Keep a protected copy on another drive.'));row=QHBoxLayout();l.addLayout(row)
        def backup():
            directory=Path(self.s.settings().get('backup_destination',str(data_dir()/'backups')));directory.mkdir(parents=True,exist_ok=True)
            path,_=QFileDialog.getSaveFileName(self,'Save verified backup',str(directory/'ainak_mahal_backup.db'),'SQLite backup (*.db)')
            if path:self.s.backup(path);self.notice.setText('Backup saved and verified: '+path)
        self.button(row,'Save verified backup',backup,True)
        def check():
            stock,payments=self.s.reconcile();QMessageBox.information(self,'Reconciliation',f'Stock discrepancies: {len(stock)}\nPayment discrepancies: {len(payments)}\nInvestigate discrepancies; records are never silently rewritten.')
        self.button(row,'Check stock & payments',check);self.body.addWidget(w);w,l=card('Restore safely');l.addWidget(label('Close Ainak Mahal, then open Ainak Mahal Recovery from Start. Recovery requires the current administrator login, verifies the backup and keeps a safety copy before replacement. Never restore over an open application.'));self.body.addWidget(w);self.body.addStretch()
    def global_search(self):
        rows=self.s.global_search(self.search.text());d=QDialog(self);d.setWindowTitle('Search workspace');d.resize(960,600);l=vbox(d,24);l.addWidget(label(f'{len(rows)} results','section'));t=Table(('Type','ID','Name','Details'),rows);l.addWidget(t,1)
        def open_result():
            r=t.selected();d.accept()
            if r[0]=='Customer':self.customer_profile(r[1])
            else:self.show_page({'Product':4,'Invoice':7,'Job':5}[r[0]])
        l.addWidget(action('Open selected result',lambda:self.safe(open_result),True));t.itemDoubleClicked.connect(lambda *_:self.safe(open_result));d.exec()
    def print_doc(self,kind,identifier):
        path=self.s.print_document(kind,identifier,data_dir()/'documents');self.document(kind,path.read_text(encoding='utf-8'))
    def document(self,title,content):
        d=QDialog(self);d.setWindowTitle(title);d.resize(900,760);l=vbox(d,24);view=QTextBrowser();view.setOpenExternalLinks(False);view.setHtml(content);l.addWidget(view,1);bar=QHBoxLayout();l.addLayout(bar)
        def printer(pdf=False):
            p=QPrinter(QPrinter.HighResolution);preferred=self.s.settings().get('printer','')
            if title=='Invoice' and self.s.settings().get('receipt_format')=='80 mm':
                p.setPageSize(QPageSize(QSizeF(80,240),QPageSize.Millimeter));p.setPageMargins(QMarginsF(4,4,4,4),QPageLayout.Millimeter)
            elif title=='Product label':
                p.setPageSize(QPageSize(QSizeF(80,60),QPageSize.Millimeter));p.setPageMargins(QMarginsF(3,3,3,3),QPageLayout.Millimeter)
            if preferred and preferred!='System default':p.setPrinterName(preferred)
            if pdf:
                path,_=QFileDialog.getSaveFileName(d,'Save PDF',title.lower().replace(' ','_')+'.pdf','PDF document (*.pdf)')
                if not path:return
                p.setOutputFormat(QPrinter.PdfFormat);p.setOutputFileName(path)
            elif QPrintDialog(p,d).exec()!=QDialog.Accepted:return
            view.document().print_(p)
        bar.addWidget(action('Print',lambda:self.safe(lambda:printer(False)),True));bar.addWidget(action('Save PDF',lambda:self.safe(lambda:printer(True))));bar.addStretch();bar.addWidget(action('Close',d.accept));d.exec()
    def closeEvent(self,event):
        if self.cart and QMessageBox.question(self,'Unsaved order','Discard the current cart and close Ainak Mahal?')!=QMessageBox.Yes:event.ignore();return
        event.accept()

class Login(QWidget):
    def __init__(self,s,on_login):
        super().__init__();self.s=s;self.on_login=on_login;self.setWindowTitle('Ainak Mahal · Sign in');self.resize(1040,700);self.setMinimumSize(850,640);self.setWindowIcon(QIcon(str(ASSETS/'ainak-mahal.ico')));outer=QHBoxLayout(self);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0)
        hero=QFrame();hero.setObjectName('sidebar');left=vbox(hero,44,20);logo=QSvgWidget(str(ASSETS/'logo-dark.svg'));logo.setFixedSize(350,90);left.addWidget(logo);left.addStretch();h=label('A clearer view\nof your shop.');h.setStyleSheet('font-size:30pt;color:white;font-weight:600');left.addWidget(h);left.addWidget(label('Customers, prescriptions and eyewear.\nEvery order, from counter to collection.'));left.addSpacing(24);left.addWidget(label('01   Connected optical orders\n\n02   Accurate stock and balances\n\n03   Your data, safely offline'));left.addStretch();left.addWidget(label('MILLAT CHOWK · FAISALABAD'));outer.addWidget(hero,1)
        right=QWidget();right.setObjectName('canvas');rl=vbox(right,48,16);rl.addStretch();first=s.first_run();rl.addWidget(label('YOUR LOCAL WORKSPACE','eyebrow'));rl.addWidget(label('Set up your shop' if first else 'Welcome back','heading'));rl.addWidget(label('Create your administrator account. No internet or subscription required.' if first else 'Sign in to continue. Your data stays on this computer.','muted'));self.fields={}
        for key,title in [('username','Username'),('password','Password')]+([('confirm','Confirm password')] if first else []):
            rl.addWidget(label(title));entry=QLineEdit();entry.setAccessibleName(title)
            if key!='username':entry.setEchoMode(QLineEdit.Password)
            self.fields[key]=entry;rl.addWidget(entry);entry.returnPressed.connect(self.submit)
        show=QCheckBox('Show password');show.toggled.connect(lambda checked:[w.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password) for k,w in self.fields.items() if k!='username']);rl.addWidget(show);self.error=label('');self.error.setStyleSheet('color:#B91C1C');rl.addWidget(self.error);self.submit_button=action('Create administrator' if first else 'Sign in',self.submit,True);rl.addWidget(self.submit_button);rl.addWidget(label('Use at least 10 characters. Administrators manage staff, backups and stock adjustments.' if first else 'Need access? Ask your shop administrator. Recovery is available from the Windows Start menu.','muted'));rl.addStretch();outer.addWidget(right,1);self.fields['username'].setFocus()
    def submit(self):
        if not self.submit_button.isEnabled():return
        self.submit_button.setEnabled(False)
        try:
            if self.s.first_run():self.s.bootstrap(value(self.fields['username']),self.fields['password'].text(),self.fields['confirm'].text())
            else:self.s.login(value(self.fields['username']),self.fields['password'].text())
        except Exception as ex:self.error.setText(error_text(ex));QTimer.singleShot(700,lambda:self.submit_button.setEnabled(True));return
        for key in ('password','confirm'):
            if key in self.fields:self.fields[key].clear()
        self.on_login();self.close()
