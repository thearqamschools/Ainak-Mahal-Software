"""Issue #4 regressions: authenticated recovery, search and real desktop interactions."""
from pathlib import Path
import tempfile
import unittest

import phase3
from retail import Retail


class ServiceUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.s=Retail(Path(self.temp.name)/'shop.db')
        self.s.bootstrap('admin','original-password','original-password')

    def tearDown(self):
        self.s.close();self.temp.cleanup()

    def test_password_change_requires_current_password_and_rotates_salt(self):
        original=self.s.rows('SELECT salt,password_hash FROM app_users')[0]
        for current,new,confirm in (('wrong','new-password','new-password'),('original-password','short','short'),('original-password','new-password','mismatch')):
            with self.assertRaises(ValueError):self.s.change_password(current,new,confirm)
            self.assertEqual(original,self.s.rows('SELECT salt,password_hash FROM app_users')[0])
        self.s.change_password('original-password','new-password','new-password')
        self.assertNotEqual(original[0],self.s.scalar('SELECT salt FROM app_users'))
        self.assertIsNone(phase3.authenticate(self.s.db,'admin','original-password'))
        self.assertEqual(phase3.authenticate(self.s.db,'admin','new-password'),'admin')
        self.assertEqual(self.s.scalar("SELECT COUNT(*) FROM audit_events WHERE action='change_password'"),1)
        self.assertNotIn('new-password',str(self.s.rows('SELECT * FROM audit_events')))

    def test_staff_reset_requires_admin_and_fresh_authentication(self):
        self.s.create_user('cashier','cashier-password','cashier')
        self.s.login('cashier','cashier-password')
        with self.assertRaises(PermissionError):self.s.change_password('cashier-password','changed-password','changed-password','admin')
        self.s.change_password('cashier-password','changed-password','changed-password')
        self.s.login('admin','original-password')
        with self.assertRaises(ValueError):self.s.change_password('wrong','reset-password','reset-password','cashier')
        with self.assertRaises(ValueError):self.s.change_password('original-password','reset-password','reset-password','missing')
        self.s.change_password('original-password','reset-password','reset-password','cashier')
        self.assertEqual(phase3.authenticate(self.s.db,'cashier','reset-password'),'cashier')
        self.assertEqual(self.s.scalar("SELECT COUNT(*) FROM audit_events WHERE action='reset_staff_password'"),1)

    def test_search_covers_workflows_and_never_mutates_data(self):
        cid=self.s.customer('Ali Hassan','03001234567')
        pid=self.s.product('ALI-FR','Ali frame',500,200,4,'Frames','998877')
        sid,_,_=self.s.checkout([(pid,1)],cid,500)
        self.s.job(cid,'Ali fitting','2026-11-03',sid)
        changes=self.s.db.total_changes
        results=self.s.search('Ali')
        self.assertEqual({r[0] for r in results},{'Customer','Product','Job','Invoice'})
        self.assertEqual(self.s.search('998877')[0][1],pid)
        self.assertEqual(self.s.search('03001234567')[0][1],cid)
        self.assertTrue(any(r[0]=='Invoice' and r[1]==sid for r in self.s.search('#'+str(sid))))
        self.assertEqual(self.s.search('   '),[])
        self.assertEqual(self.s.search("' OR 1=1 --"),[])
        self.assertLessEqual(len(self.s.search('Ali',2)),2)
        self.assertEqual(self.s.db.total_changes,changes)
        self.s.role=None
        with self.assertRaises(PermissionError):self.s.search('Ali')

    def test_operating_reports_and_offline_print_brand(self):
        from datetime import date
        today=date.today().isoformat()
        cid=self.s.customer('Report Customer','03000000000')
        pid=self.s.product('LOW','Low frame',500,200,1,'Frames',reorder=2)
        self.s.product('SVC','Fitting service',100,0,0,'Service',service=True)
        self.assertEqual([r[0] for r in self.s.report('Low stock',today,today)[1]],[pid])
        valuation=self.s.report('Stock valuation',today,today)[1]
        self.assertEqual(len(valuation),1);self.assertEqual(valuation[0][-1],200)
        supplier=self.s.supplier('Optical Supplies','')
        self.s.receive(supplier,[(pid,2,250)])
        self.assertEqual(self.s.report('Purchases',today,today)[1][0][3],500)
        sid,_,_=self.s.checkout([(pid,1)],cid,250)
        self.s.pay(sid,250,'Bank')
        collections=self.s.report('Collections',today,today)[1]
        self.assertEqual(sum(r[-1] for r in collections),500)
        self.assertEqual({r[3] for r in collections},{'Cash','Bank'})
        self.assertEqual(self.s.report('Collections','2000-01-01','2000-01-02')[1],[])
        with self.assertRaises(ValueError):self.s.report('Purchases','2026-12-01','2026-01-01')
        rx=self.s.save_rx(cid,{'pd':'62'})
        job=self.s.job(cid,'Frame fitting',today,sid,rx)
        for kind,reference in (('Invoice',sid),('Prescription',rx),('Job',job)):
            document=self.s.print_document(kind,reference,self.temp.name).read_text()
            self.assertIn('aria-label="Ainak Mahal eyeglasses"',document)
            self.assertNotIn('<script src=',document)
            self.assertNotIn('<img src="http',document)


class DesktopUpgradeTests(unittest.TestCase):
    def setUp(self):
        import tkinter as tk
        try:self.root=tk.Tk()
        except tk.TclError as error:self.skipTest('A desktop display is required: '+str(error))
        self.temp=tempfile.TemporaryDirectory();self.s=Retail(Path(self.temp.name)/'ui.db')
        self.errors=[];self.root.report_callback_exception=lambda *args:self.errors.append(str(args))

    def tearDown(self):
        if hasattr(self,'s'):
            self.s.close();self.root.destroy();self.temp.cleanup()
            self.assertEqual(self.errors,[])

    def test_first_run_login_mask_validation_and_actual_submit(self):
        from desktop import sign_in
        signed=[];sign_in(self.root,self.s,lambda:signed.append(True));self.root.update()
        controls=self.root.sign_in_controls
        controls['submit']();self.assertEqual(controls['error'].cget('text'),'Enter your username.')
        controls['values']['username'].set('operator')
        controls['values']['password'].set('operator-password');controls['values']['confirm'].set('operator-password')
        self.assertTrue(controls['entries']['password'].cget('show'))
        controls['visible'].set(True);controls['toggle']()
        self.assertEqual(controls['entries']['password'].cget('show'),'')
        controls['visible'].set(False);controls['toggle']()
        controls['submit']();self.assertEqual(signed,[True]);self.assertFalse(self.s.first_run())
        self.assertEqual(controls['values']['password'].get(),'')
        sign_in(self.root,self.s,lambda:signed.append(True));self.root.update()
        controls=self.root.sign_in_controls;self.assertNotIn('confirm',controls['values'])
        controls['values']['username'].set('operator');controls['values']['password'].set('operator-password')
        self.root.event_generate('<Return>');self.root.update()
        self.assertEqual(len(signed),2)

    def test_grid_sort_preserves_record_selection_and_empty_state(self):
        from desktop import Grid, theme
        theme(self.root);grid=Grid(self.root,('ID','Name'),[(2,'Zara'),(1,'Ali')]);self.root.update()
        grid.tree.selection_set('0');grid.sort(1)
        self.assertEqual(grid.selected()[0],2)
        self.assertEqual(grid.data['0'][1],'Ali')
        grid.sort(1);self.assertEqual(grid.data['0'][1],'Zara')
        grid.replace([]);self.root.update();self.assertTrue(grid.empty.winfo_ismapped())
        amount=Grid(self.root,('Price PKR',),[(2500.5,)])
        self.assertEqual(amount.tree.item('0','values'),('2,500.50',))
        amount.tree.selection_set('0');self.assertEqual(amount.selected()[0],2500.5)

    def test_global_search_opens_and_selects_actual_record(self):
        import tkinter as tk
        from tkinter import ttk
        from desktop import Desktop
        self.s.bootstrap('admin','admin-password','admin-password')
        cid=self.s.customer('Search Person','03001234567')
        ui=Desktop(self.root,self.s);ui.safe=lambda fn:fn();ui.open_search();self.root.update()
        def descendants(widget):
            for child in widget.winfo_children():
                yield child;yield from descendants(child)
        entry=next(w for w in descendants(ui.search_window) if isinstance(w,ttk.Entry))
        entry.insert(0,'Search Person');self.root.update()
        entry.event_generate('<Return>');self.root.update()
        self.assertEqual(ui.current,'Customers');self.assertEqual(ui.page_grid.selected()[0],cid)
        self.assertFalse(ui.search_window.winfo_exists())

    def test_inventory_and_job_filters_retain_correct_records(self):
        from datetime import date,timedelta
        from tkinter import ttk
        from desktop import Desktop
        self.s.bootstrap('admin','admin-password','admin-password')
        low=self.s.product('LOW','Low frame',100,20,1,'Frames')
        self.s.product('FULL','Lens pair',100,20,10,'Lenses')
        cid=self.s.customer('Job Person')
        overdue=self.s.job(cid,'Repair hinge',(date.today()-timedelta(days=1)).isoformat())
        self.s.job(cid,'New glasses',(date.today()+timedelta(days=1)).isoformat())
        ui=Desktop(self.root,self.s);ui.safe=lambda fn:fn()
        def descendants(widget):
            for child in widget.winfo_children():
                yield child;yield from descendants(child)
        ui.show('Inventory');self.root.update()
        choices=[w for w in descendants(ui.body) if isinstance(w,ttk.Combobox)]
        stock=next(w for w in choices if 'Low stock' in w.cget('values'))
        stock.set('Low stock');self.root.update()
        self.assertEqual([r[0] for r in ui.page_grid.data.values()],[low])
        ui.show('Optical jobs');self.root.update()
        status=next(w for w in descendants(ui.body) if isinstance(w,ttk.Combobox))
        status.set('Overdue');self.root.update()
        self.assertEqual([r[0] for r in ui.page_grid.data.values()],[overdue])
        ui.ready_jobs();self.root.update()
        self.assertEqual(list(ui.page_grid.data.values()),[])


if __name__=='__main__':unittest.main()
