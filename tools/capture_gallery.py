"""Capture actual desktop windows with disposable shop data. Never uses the live DB.

Development only: Pillow; requires a real Windows desktop or an X display on Linux.
"""
import argparse
from datetime import date, timedelta
from pathlib import Path
import sys
import tempfile
import tkinter as tk

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import ImageGrab
from desktop import Desktop, sign_in
from retail import Retail


def capture(root,path):
    root.update_idletasks();root.update()
    x,y=root.winfo_rootx(),root.winfo_rooty()
    ImageGrab.grab(bbox=(x,y,x+root.winfo_width(),y+root.winfo_height())).save(path)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='docs/screenshots')
    args=parser.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ainak-gallery-') as temp:
        service=Retail(Path(temp)/'sample.db');root=tk.Tk()
        try:
            sign_in(root,service,lambda:None);capture(root,out/'01-first-run.png')
            service.bootstrap('Ayesha','gallery-password','gallery-password')
            for child in root.winfo_children():child.destroy()
            sign_in(root,service,lambda:None);capture(root,out/'02-sign-in.png')
            customers=[service.customer(n,p,'Faisalabad') for n,p in (
                ('Ali Hassan','0300 1234567'),('Sara Ahmed','0321 7654321'),('Usman Khalid','0301 9876543'),('Fatima Noor','0333 4567890'))]
            frames=[]
            for sku,name,price,cost,qty,cat,variant in (
                ('FR-100','Horizon / Acetate frame',3500,1800,12,'Frames','Navy · Medium'),
                ('FR-102','Contour / Metal frame',4200,2100,8,'Frames','Gold · Small'),
                ('LN-050','Single vision / AR lenses',2200,900,20,'Lenses','Anti-reflective'),
                ('SG-200','Daylight / Polarised sunglasses',4800,2300,2,'Sunglasses','Tortoise · Large'),
                ('AC-010','Microfibre care kit',350,120,1,'Accessories','Cloth + spray')):
                frames.append(service.product(sku,name,price,cost,qty,cat,'890'+sku[-3:]+str(len(frames)),variant))
            service.product('SV-001','Frame fitting',250,0,0,'Service',service=True)
            today=date.today()
            for i,(cid,paid) in enumerate(zip(customers,(4000,3500,2500,3500))):
                sale,_,_=service.checkout([(frames[0],1),(frames[2],1)] if i==0 else [(frames[0],1)],cid,paid)
                rx=service.save_rx(cid,{'od_sph':'-1.25','od_cyl':'-0.50','od_axis':'90','od_add':'1.50','os_sph':'-1.00','pd':'62'})
                job=service.job(cid,('AR coating · navy frame','New lenses · customer frame','Adjust temples · repair','Single vision · clear lenses')[i],(today+timedelta(days=i-1)).isoformat(),sale,rx)
                if i in (1,2):service.advance_job(job,'In Lab')
                if i==1:service.advance_job(job,'Ready')
            supplier=service.supplier('Faisal Optical Supplies','041 0000000')
            service.receive(supplier,[(frames[0],3,1800)])
            service.cash('Opening',5000,'Morning float');service.expense('Lab delivery',250)
            for child in root.winfo_children():child.destroy()
            root.resizable(True,True);ui=Desktop(root,service)
            errors=[];root.report_callback_exception=lambda *exc:errors.append(str(exc))
            ui.safe=lambda action:action()
            for number,page in enumerate(Desktop.PAGES,3):
                ui.show(page)
                if page=='Checkout':
                    ui.cart=[(frames[0],1),(frames[2],1)];ui.draft_paid='4000'
                    ui.draft_customer=next(k for k,v in ui.customer_choices().items() if v==customers[0]);ui.refresh()
                capture(root,out/f'{number:02d}-{page.lower().replace(" & ","-").replace(" ","-")}.png')
            ui.open_search();root.update();win=ui.search_window
            def entries(widget):
                for child in widget.winfo_children():
                    if isinstance(child,tk.ttk.Entry):yield child
                    yield from entries(child)
            next(entries(win)).insert(0,'Ali');capture(win,out/'15-global-search.png');win.destroy()
            ui.show('Purchasing');ui.supplier_history();root.update()
            win=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
            capture(win,out/'16-supplier-history.png');win.destroy()
            ui.show('Customers');root.update()
            key=next(key for key,row in ui.page_grid.data.items() if row[0]==customers[0]);ui.page_grid.tree.selection_set(key)
            def buttons(widget):
                for child in widget.winfo_children():
                    if isinstance(child,tk.ttk.Button):yield child
                    yield from buttons(child)
            next(w for w in buttons(ui.body) if w.cget('text')=='View sales & Rx history').invoke();root.update()
            win=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
            capture(win,out/'17-customer-history.png');win.destroy()
            if errors:raise RuntimeError('; '.join(errors))
            print('Captured 17 actual desktop windows in',out)
        finally:
            root.destroy();service.close()


if __name__=='__main__':main()
