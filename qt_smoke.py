"""Real Qt widgets, isolated sample workflows and rendered UI capture."""
import os,json,tempfile,traceback,sys
from pathlib import Path
from datetime import date,timedelta
from contextlib import ExitStack

def run(app):
    result={'passed':False};window=None
    stage='starting'
    def progress(text):
        nonlocal stage
        stage=text
        output=os.environ.get('AINAK_SMOKE_RESULT')
        if output:Path(output+'.progress.log').write_text(text,encoding='utf-8')
    try:
        progress('importing smoke dependencies')
        from erp import ERP
        from qdesktop import Window,Login,NAV,STYLE,QPushButton,QDialog,Table,Form
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from PySide6.QtGui import QTextDocument
        from PySide6.QtPrintSupport import QPrinter
        from phase4 import restore_database
        capture=Path(os.environ['AINAK_SCREENSHOTS']) if os.environ.get('AINAK_SCREENSHOTS') else None
        if capture:capture.mkdir(parents=True,exist_ok=True)
        app.setStyleSheet(STYLE)
        with tempfile.TemporaryDirectory(prefix='ainak_erp2_') as temp,ExitStack() as cleanup:
            path=Path(temp)/'shop.db';s=ERP(path);cleanup.callback(s.close)
            login=Login(s,lambda:None);login.show();app.processEvents()
            progress('onboarding rendered')
            if capture:login.grab().save(str(capture/'01-onboarding.png'))
            # Exercise first-run button instead of calling the bootstrap service only.
            login.fields['username'].setText('review-owner');login.fields['password'].setText('sample-password');login.fields['confirm'].setText('sample-password')
            QTest.mouseClick(login.submit_button,Qt.LeftButton);app.processEvents()
            assert s.role=='admin';s.login('review-owner','sample-password')
            progress('onboarding authenticated')
            cid=s.customer('Ali Hassan','0300 1234567','Faisalabad');s.customer('Sara Ahmed','0321 7654321','Millat Town')
            p=s.product('FR-100','Classic acetate frame',3500,1800,12,'Frames','8901001','Navy · Medium')
            lens=s.product('LN-050','Single vision lenses',2200,900,20,'Lenses','8901002','Anti-reflective','-0.50','0',4)
            s.product('SG-200','Everyday sunglasses',2800,1300,2,'Sunglasses','8901003')
            s.product('CL-100','Daily contact lenses',1500,800,8,'Contact lenses','8901004','30 pack','-1.00','0')
            rx=s.save_rx(cid,{'od_sph':'-0.50','os_sph':'-0.75','pd':'62'})
            sid,total,due,jid=s.place_order([(p,1),(lens,2)],cid,rx_id=rx,paid=4000,job_description='Navy frame · AR lenses',due=str(date.today()+timedelta(days=2)))
            repair=s.create_job(cid,'Frame repair','Replace hinge',date.today().isoformat(),charge=750,paid=250)
            supplier=s.supplier('Faisal Optical Supplies','041 0000000');po=s.create_po(supplier,[(p,2,1800),(lens,4,900)]);s.receive_po(po)
            purchase=s.purchases()[0][0];s.supplier_payment(purchase,1000,'Bank','QA-BANK-1')
            s.cash('Opening',1500,'Opening float');s.expense('Counter supplies',250)
            window=Window(s);window.safe=lambda f:f();window.show();app.processEvents()
            progress('workspace rendered')
            for i,name in enumerate(NAV):
                progress('navigation: '+name)
                QTest.mouseClick(window.nav[i],Qt.LeftButton);app.processEvents();assert window.current==i
                window.resize(1440,920);app.processEvents()
                if capture:window.grab().save(str(capture/f'{i+2:02d}-{name.split(" /")[0].replace(" & ","-").replace(" ","-").lower()}.png'))
                window.resize(1080,720);app.processEvents()
                for b in window.nav:assert b.isVisible(),f'Navigation hidden: {b.text()}'
            # Real scanner-style input and cart manipulation through Qt key events.
            window.show_page(1);window.scan.setFocus();QTest.keyClicks(window.scan,'8901001');QTest.keyClick(window.scan,Qt.Key_Return);app.processEvents();assert window.cart==[(p,1)]
            progress('scanner input exercised')
            window.cart_table.selectRow(0);window.remove_cart();assert not window.cart
            # Test PDF creation through the same native Qt printing engine.
            doc=QTextDocument();doc.setHtml(s.print_document('Invoice',sid,temp).read_text(encoding='utf-8'))
            printer=QPrinter(QPrinter.HighResolution);printer.setOutputFormat(QPrinter.PdfFormat);pdf=Path(temp)/'invoice.pdf';printer.setOutputFileName(str(pdf));doc.print_(printer);assert pdf.stat().st_size>100
            progress('PDF printed')
            s.pay(sid,due,'Cash')
            for status in ('In Lab','Ready','Delivered'):s.advance_job(jid,status)
            s.backup(Path(temp)/'backup.db')
            if os.environ.get('AINAK_UPGRADE_FIXTURE'):s.backup(os.environ['AINAK_UPGRADE_FIXTURE'])
            assert s.reconcile()==([],[]);window.close();window=None;s.close()
            restore_database(Path(temp)/'backup.db',path);s2=ERP(path);cleanup.callback(s2.close);s2.login('review-owner','sample-password');assert s2.scalar('PRAGMA user_version')==2
            progress('restore verified')
            result={'passed':True,'pages':list(NAV),'workflows':['first-run UI','login','atomic optical order','Rx','barcode keyboard input','cart removal','repairs','delivery','purchasing','supplier payment','cash','reconciliation','PDF','backup','restore','schema 2']}
    except Exception:result['error']=traceback.format_exc();result['stage']=stage
    finally:
        if window:window.cart=[];window.close()
    output=os.environ.get('AINAK_SMOKE_RESULT')
    if output:Path(output).write_text(json.dumps(result,indent=2),encoding='utf-8')
    else:print(json.dumps(result,indent=2))
    return 0 if result['passed'] else 1
