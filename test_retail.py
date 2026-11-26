import tempfile
import unittest
import sqlite3
from pathlib import Path
from datetime import date
from retail import Retail
from core import Store
from paths import InstanceLock
import phase3,phase4

class RetailTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'shop.db'
        self.s=Retail(self.path);self.s.bootstrap('owner','strong-password','strong-password')
        self.cid=self.s.customer('Ali','03001234567')
        self.pid=self.s.product('F1','Frame',1000,400,5,'Frames','12345')
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def test_legacy_migration_is_additive_and_idempotent(self):
        path=Path(self.tmp.name)/'old.db';old=Store(path);cid=old.add_customer('Existing');pid=old.add_product('OLD','Legacy',50,20,3)
        old.sell([(pid,1)],cid,20);old.close()
        new=Retail(path)
        try:
            original=new.scalar('SELECT uuid FROM entity_identity WHERE entity=? AND local_id=?',('customers',str(cid)))
            from migrations import migrate
            migrate(new.store)
            self.assertEqual(original,new.scalar('SELECT uuid FROM entity_identity WHERE entity=? AND local_id=?',('customers',str(cid))))
            self.assertEqual(new.scalar('SELECT qty FROM products'),2)
            self.assertEqual(new.scalar('PRAGMA user_version'),1)
            self.assertTrue(path.with_name('old_before_v1.db').exists())
            self.assertEqual(new.scalar('SELECT name FROM customers'),'Existing')
        finally:new.close()
    def test_checkout_discount_tax_return_cents_and_stock(self):
        self.s.save_settings({'tax_rate':'17','receipt_format':'A4'})
        sid,total,due=self.s.checkout([(self.pid,3)],self.cid,1000,discount='100.01')
        self.assertEqual(total,3392.99);self.assertEqual(due,2392.99)
        a=self.s.return_item(sid,self.pid,1,'Size','Cash');b=self.s.return_item(sid,self.pid,2,'Size','Cash')
        self.assertEqual(round(a['refund_value']+b['refund_value'],2),total)
        self.assertEqual(self.s.sales()[0][5],0)
        self.assertEqual(self.s.scalar('SELECT qty FROM products WHERE id=?',(self.pid,)),5)
        self.assertEqual(self.s.reconcile(),([],[]))
        with self.assertRaises(ValueError):self.s.pay(sid,1,'Cash')
    def test_payment_and_delivery_gate(self):
        sid,_,_=self.s.checkout([(self.pid,1)],self.cid,100)
        rid=self.s.save_rx(self.cid,{'od_sph':'-1.25','od_cyl':'-.5','od_axis':'90','od_add':'1.5','pd':'62'})
        jid=self.s.job(self.cid,'Single vision',date.today().isoformat(),sid,rid)
        self.s.advance_job(jid,'In Lab');self.s.advance_job(jid,'Ready')
        with self.assertRaises(ValueError):self.s.advance_job(jid,'Delivered')
        self.s.pay(sid,900,'Cash');self.s.advance_job(jid,'Delivered')
        self.assertEqual(self.s.jobs()[0][3],'Delivered')
    def test_store_credit_cannot_be_double_spent_or_cross_customer(self):
        sid,_,_=self.s.checkout([(self.pid,1)],self.cid,1000)
        self.s.return_item(sid,self.pid,1,'Exchange','Credit')
        target,_,_=self.s.checkout([(self.pid,1)],self.cid,0)
        other=self.s.customer('Other');wrong,_,_=self.s.checkout([(self.pid,1)],other,0)
        with self.assertRaises(ValueError):self.s.redeem_credit(sid,wrong,100)
        self.s.redeem_credit(sid,target,1000)
        self.assertEqual(dict((r[0],r[5]) for r in self.s.sales())[target],0)
        with self.assertRaises(ValueError):self.s.redeem_credit(sid,wrong,1)
        self.assertEqual(self.s.reconcile(),([],[]))
    def test_product_edit_keeps_historical_cost(self):
        sid,_,_=self.s.checkout([(self.pid,1)],self.cid,1000)
        self.s.edit_product(self.pid,'Updated frame',1500,900,'12345','Black',3)
        self.assertEqual(self.s.scalar('SELECT unit_cost_cents FROM line_costs'),40000)
        self.assertEqual(self.s.scalar('SELECT total FROM sales WHERE id=?',(sid,)),1000)
    def test_full_return_reverses_tax_and_historical_cost_in_profit(self):
        self.s.save_settings({'tax_rate':'17','receipt_format':'A4'})
        sid,_,_=self.s.checkout([(self.pid,2)],self.cid,2340)
        self.s.edit_product(self.pid,'New name',1000,900,'12345','Black',2)
        self.s.return_item(sid,self.pid,1,'Wrong size','Cash')
        self.s.return_item(sid,self.pid,1,'Wrong size','Cash')
        metrics=dict(self.s.report('Profit','2000-01-01','2099-01-01')[1])
        self.assertEqual(metrics['Tax collected'],0)
        self.assertEqual(metrics['Cost of goods'],0)
        self.assertEqual(metrics['Estimated profit'],0)
    def test_rx_validation(self):
        for values in ({'od_sph':'nan'},{'od_cyl':'-1'},{'os_axis':'181'},{'od_add':'1.1'},{'pd':'90'}):
            with self.assertRaises(ValueError):self.s.save_rx(self.cid,values)
        self.assertEqual(self.s.prescriptions(),[])
    def test_service_does_not_consume_or_return_stock(self):
        pid=self.s.product('SV','Fitting',100,0,0,'Service',service=True)
        sid,_,_=self.s.checkout([(pid,2)],self.cid,200)
        self.s.return_item(sid,pid,1,'Correction','Cash')
        self.assertEqual(self.s.scalar('SELECT qty FROM products WHERE id=?',(pid,)),0)
        self.assertEqual(self.s.reconcile(),([],[]))
    def test_atomic_failure_rolls_back_nested_goods_receipt(self):
        supplier=self.s.supplier('Supplier','')
        po=self.s.create_po(supplier,[(self.pid,2,300)])
        self.s.db.execute("CREATE TRIGGER fail_receive BEFORE UPDATE OF status ON purchase_orders BEGIN SELECT RAISE(ABORT,'injected failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.s.receive_po(po)
        self.assertEqual(self.s.scalar('SELECT COUNT(*) FROM purchases'),0)
        self.assertEqual(self.s.scalar('SELECT qty FROM products WHERE id=?',(self.pid,)),5)
        self.assertEqual(self.s.scalar('SELECT status FROM purchase_orders'),'Open')
    def test_atomic_failure_rolls_back_nested_return(self):
        sid,_,_=self.s.checkout([(self.pid,1)],self.cid,1000)
        self.s.db.execute("CREATE TRIGGER fail_return BEFORE INSERT ON return_settlements BEGIN SELECT RAISE(ABORT,'injected failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.s.return_item(sid,self.pid,1,'Size','Cash')
        self.assertEqual(self.s.scalar('SELECT COUNT(*) FROM sale_returns'),0)
        self.assertEqual(self.s.scalar('SELECT qty FROM products'),4)
    def test_no_fractional_quantity_or_walkin_credit(self):
        with self.assertRaises(ValueError):self.s.checkout([(self.pid,1.5)],self.cid)
        with self.assertRaises(ValueError):self.s.checkout([(self.pid,1)])
        self.assertEqual(self.s.scalar('SELECT COUNT(*) FROM sales'),0)
    def test_adjustment_and_roles(self):
        self.s.adjust(self.pid,-2,'Damaged frame');self.assertEqual(self.s.reconcile(),([],[]))
        with self.assertRaises(ValueError):self.s.adjust(self.pid,-4,'Too many')
        self.s.create_user('staff','staff-password','cashier');self.s.login('staff','staff-password')
        for action in (lambda:self.s.adjust(self.pid,1,'x'),lambda:self.s.expense('x',1),lambda:self.s.backup(Path(self.tmp.name)/'copy.db'),lambda:self.s.supplier('x','')):
            with self.assertRaises(PermissionError):action()
        self.s.checkout([(self.pid,1)],self.cid,1000)
    def test_cash_closing_and_refund_payout(self):
        sid,_,_=self.s.checkout([(self.pid,1)],self.cid,1000)
        self.s.cash('Opening',500,'Float');self.s.expense('Electricity',100)
        r=self.s.return_item(sid,self.pid,1,'Defect','Cash');self.s.payout(r['return_id'],200,'Cash','P1')
        today=date.today().isoformat();self.assertEqual(self.s.expected_cash(today),120000)
        self.assertEqual(self.s.close_day(today,1190,'Short 10'),1200)
        self.assertEqual(self.s.report('Cash closing',today,today)[1][0][3],-10)
        with self.assertRaises(sqlite3.IntegrityError):self.s.close_day(today,1200,'Duplicate')
    def test_fractional_cash_aggregates_and_returns_stay_in_cents(self):
        pid=self.s.product('CENT','Small accessory','.10','0',20,'Accessories')
        for _ in range(3):self.s.checkout([(pid,1)],self.cid,'.10')
        self.assertEqual(self.s.expected_cash(date.today().isoformat()),30)
        sid,_,_=self.s.checkout([(pid,3)],self.cid,'.30')
        for _ in range(3):self.s.return_item(sid,pid,1,'Test','Cash')
        self.assertEqual(dict((r[0],r[5]) for r in self.s.sales())[sid],0)
    def test_csv_and_print_escaping(self):
        cid=self.s.customer('=CMD() <script>');sid,_,_=self.s.checkout([(self.pid,1)],cid,1000)
        path=Path(self.tmp.name)/'report.csv';cols,rows=self.s.report('Sales','2000-01-01','2099-12-31');self.s.export_csv(path,cols,rows)
        self.assertIn("'=CMD()",path.read_text(encoding='utf-8-sig'))
        document=self.s.print_document('Invoice',sid,self.tmp.name).read_text(encoding='utf-8')
        self.assertNotIn('<script>',document);self.assertIn('&lt;script&gt;',document)
    def test_backup_restore_windows_handles(self):
        path=Path(self.tmp.name)/'backup.db';self.s.backup(path)
        renamed=path.with_name('renamed.db');path.rename(renamed)
        self.s.customer('Later');self.s.close()
        safety=phase4.restore_database(renamed,self.path);self.assertTrue(safety.exists())
        self.s=Retail(self.path);self.s.login('owner','strong-password');self.assertEqual(len(self.s.customers()),1)
    def test_single_instance_lock(self):
        a=InstanceLock(self.tmp.name)
        try:
            with self.assertRaises(RuntimeError):InstanceLock(self.tmp.name)
        finally:a.close()
        b=InstanceLock(self.tmp.name);b.close()
    def test_invalid_job_link_and_double_receive(self):
        other=self.s.customer('Other');sid,_,_=self.s.checkout([(self.pid,1)],self.cid,1000)
        with self.assertRaises(ValueError):self.s.job(other,'Test','2027-01-01',sid)
        supplier=self.s.supplier('Vendor','');po=self.s.create_po(supplier,[(self.pid,2,200)])
        self.s.receive_po(po)
        with self.assertRaises(ValueError):self.s.receive_po(po)
        self.assertEqual(self.s.reconcile(),([],[]))

if __name__=='__main__':unittest.main()
