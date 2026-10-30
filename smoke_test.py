"""Packaged smoke check: isolated temporary data, actual Tk screen construction."""
import json
import os
import tempfile
import traceback
from pathlib import Path

def run():
    result={'passed':False}
    try:
        import tkinter as tk
        from retail import Retail
        from desktop import Desktop,sign_in
        from datetime import date
        from phase4 import restore_database
        with tempfile.TemporaryDirectory(prefix='ainak_smoke_') as temp:
            path=Path(temp)/'test.db';s=Retail(path)
            root=tk.Tk();sign_in(root,s,lambda:None);root.update()
            s.bootstrap('smoke-admin','test-password','test-password')
            cid=s.customer('Smoke Customer','03000000000');pid=s.product('SMK','Frame',1500,500,4,'Frames')
            sid,total,due=s.checkout([(pid,1)],cid,500)
            s.pay(sid,1000,'Cash')
            rx=s.save_rx(cid,{'od_sph':'-1.25','os_sph':'-1.0','pd':'62'})
            job=s.job(cid,'Single vision',date.today().isoformat(),sid,rx)
            for status in ('In Lab','Ready','Delivered'):s.advance_job(job,status)
            supplier=s.supplier('Test Supplier','');po=s.create_po(supplier,[(pid,2,600)]);s.receive_po(po)
            s.expense('Test cash expense',50);s.cash('Opening',100,'Test float')
            for child in root.winfo_children():child.destroy()
            # Catch Tk callback errors rather than silently logging them.
            errors=[];root.report_callback_exception=lambda *args:errors.append(str(args))
            ui=Desktop(root,s)
            ui.safe=lambda action:action()
            for page in Desktop.PAGES:
                ui.show(page);root.update()
            if errors:raise RuntimeError('; '.join(errors))
            for kind,ref in (('Invoice',sid),('Prescription',rx),('Job',job)):
                assert s.print_document(kind,ref,temp).exists()
            assert s.reconcile()==([],[])
            s.backup(Path(temp)/'backup.db')
            if os.environ.get('AINAK_UPGRADE_FIXTURE'):s.backup(os.environ['AINAK_UPGRADE_FIXTURE'])
            s.close();root.destroy()
            restore_database(Path(temp)/'backup.db',path)
            s=Retail(path);s.login('smoke-admin','test-password');assert s.scalar('SELECT COUNT(*) FROM sales')==1;s.close()
            result={'passed':True,'pages':list(Desktop.PAGES),'workflows':['admin','login','sale','stock','payment','rx','job delivery','procurement','expense','backup','restore','printing']}
    except Exception:
        result['error']=traceback.format_exc()
    output=os.environ.get('AINAK_SMOKE_RESULT')
    if output:Path(output).write_text(json.dumps(result,indent=2),encoding='utf-8')
    else:print(json.dumps(result,indent=2))
    return 0 if result['passed'] else 1
