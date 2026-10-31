import tempfile,unittest,sqlite3
from pathlib import Path
from datetime import date
from erp import ERP
from retail import Retail

class ERPTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'erp.db';self.s=ERP(self.path);self.s.bootstrap('owner','strong-password','strong-password');self.cid=self.s.customer('Customer','03000000000');self.pid=self.s.product('F','Frame',1000,400,10,'Frames')
    def tearDown(self):self.s.close();self.tmp.cleanup()
    def test_atomic_connected_order(self):
        sid,total,due,jid=self.s.place_order([(self.pid,2)],new_customer={'name':'New','phone':'0333'},rx_values={'od_sph':'-1.25','pd':'62'},paid=500,job_description='AR lenses',due='2027-01-01')
        self.assertEqual((total,due),(2000,1500));self.assertTrue(jid);self.assertEqual(self.s.scalar('SELECT COUNT(*) FROM order_links'),1);self.assertEqual(self.s.scalar('SELECT COUNT(*) FROM prescriptions'),1);self.assertEqual(self.s.reconcile(),([],[]))
    def test_failed_job_rolls_back_entire_optical_order(self):
        with self.assertRaises(ValueError):self.s.place_order([(self.pid,1)],new_customer={'name':'Rollback'},rx_values={'pd':'62'},paid=500,job_description='Invalid due',due='bad-date')
        self.assertEqual(self.s.scalar('SELECT COUNT(*) FROM sales'),0);self.assertEqual(len(self.s.customers()),1);self.assertEqual(self.s.scalar('SELECT COUNT(*) FROM prescriptions'),0);self.assertEqual(self.s.scalar('SELECT qty FROM products'),10)
    def test_rx_customer_link_guard(self):
        other=self.s.customer('Other');rx=self.s.save_rx(other,{'pd':'62'})
        with self.assertRaises(ValueError):self.s.place_order([(self.pid,1)],self.cid,rx_id=rx,paid=1000)
        self.assertEqual(self.s.scalar('SELECT COUNT(*) FROM sales'),0)
    def test_repair_charges_payments_and_delivery(self):
        jid=self.s.create_job(self.cid,'Frame repair','Replace hinge','2027-01-01',charge=500,paid=100)
        row=next(r for r in self.s.job_list() if r[0]==jid);sid=row[6];self.assertEqual(row[2],'Frame repair');self.assertEqual(self.s.sales()[0][5],400)
        self.s.advance_job(jid,'In Lab');self.s.advance_job(jid,'Ready')
        with self.assertRaises(ValueError):self.s.advance_job(jid,'Delivered')
        self.s.pay(sid,400,'Cash');self.s.advance_job(jid,'Delivered');self.assertEqual(self.s.reconcile(),([],[]))
    def test_repair_tax_and_refund_do_not_add_stock(self):
        self.s.save_settings({'tax_rate':'17','receipt_format':'A4'});jid=self.s.create_job(self.cid,'General repair','Clean','2027-01-01',charge=100,paid=117)
        sid=self.s.job_list()[0][6];self.assertEqual(self.s.sales()[0][3],117)
        pid=self.s.scalar("SELECT id FROM products WHERE sku='AM-REPAIR-SERVICE'");self.s.return_item(sid,pid,1,'Correction','Cash');self.assertEqual(self.s.scalar('SELECT qty FROM products WHERE id=?',(pid,)),0)
    def test_no_double_charge_for_linked_job(self):
        sid,_,_=self.s.checkout([(self.pid,1)],self.cid,1000)
        with self.assertRaises(ValueError):self.s.create_job(self.cid,'Frame repair','Repair','2027-01-01',sid=sid,charge=100)
        self.assertEqual(self.s.scalar('SELECT COUNT(*) FROM sales'),1)
    def test_supplier_payment_caps_and_cash(self):
        vendor=self.s.supplier('Vendor','');receipt=self.s.receive(vendor,[(self.pid,2,400)])
        self.assertEqual(self.s.purchases()[0][5],800);self.s.supplier_payment(receipt,300,'Cash','P1');self.assertEqual(self.s.purchases()[0][5],500)
        self.assertEqual(self.s.expected_cash(date.today().isoformat()),-30000)
        with self.assertRaises(ValueError):self.s.supplier_payment(receipt,501,'Bank','P2')
        with self.assertRaises(sqlite3.IntegrityError):self.s.supplier_payment(receipt,100,'Bank','P1')
        self.assertEqual(self.s.purchases()[0][5],500)
    def test_legacy_supplier_opening_is_not_invented(self):
        path=Path(self.tmp.name)/'old.db';s=Retail(path);s.bootstrap('admin','strong-password','strong-password');pid=s.product('OLD','Old',10,5,0,'Frames');vendor=s.supplier('Old vendor','');receipt=s.receive(vendor,[(pid,10,5)]);s.close()
        upgraded=ERP(path)
        try:
            upgraded.login('admin','strong-password');self.assertIsNone(upgraded.purchases()[0][5]);self.assertEqual(upgraded.supplier_balances()[0][6],1)
            with self.assertRaises(ValueError):upgraded.supplier_payment(receipt,10,'Cash','X')
            upgraded.confirm_supplier_opening(receipt,20);self.assertEqual(upgraded.purchases()[0][5],20);self.assertEqual(upgraded.expected_cash(date.today().isoformat()),0)
            upgraded.supplier_payment(receipt,20,'Cash','X');self.assertEqual(upgraded.purchases()[0][5],0)
            with self.assertRaises(ValueError):upgraded.confirm_supplier_opening(receipt,0)
        finally:upgraded.close()
    def test_cashier_cannot_pay_supplier(self):
        vendor=self.s.supplier('V','');receipt=self.s.receive(vendor,[(self.pid,1,400)]);self.s.create_user('staff','staff-password','cashier');self.s.login('staff','staff-password')
        with self.assertRaises(PermissionError):self.s.supplier_payment(receipt,10,'Cash','X')
        jid=self.s.create_job(self.cid,'General repair','Repair','2027-01-01',charge=100,paid=100);self.assertTrue(jid)
    def test_profile_validation_and_id_search(self):
        self.s.save_profile(self.cid,doctor='Dr Test',dob='1990-01-01');self.assertEqual(self.s.profile(self.cid)['doctor'],'Dr Test');self.assertEqual(self.s.customers(str(self.cid))[0][0],self.cid)
        with self.assertRaises(ValueError):self.s.save_profile(self.cid,dob='2999-01-01')
        self.assertEqual(self.s.profile(self.cid)['dob'],'1990-01-01')
    def test_global_search_and_extended_reports(self):
        sid,_,_=self.s.checkout([(self.pid,1)],self.cid,1000);self.assertTrue(self.s.global_search('Frame'));self.assertTrue(self.s.global_search(str(sid)))
        for kind in ('Collections','Inventory valuation','Low stock','Purchases','Supplier balances','Supplier payments'):
            cols,rows=self.s.report(kind,'2000-01-01','2099-01-01')
            for row in rows:self.assertEqual(len(cols),len(row))
    def test_schema2_backup_and_legacy_compatibility(self):
        self.assertEqual(self.s.scalar('PRAGMA user_version'),2);self.assertTrue(self.path.with_name('erp_before_v2.db').exists());self.s.close();legacy=Retail(self.path);legacy.close();self.s=ERP(self.path);self.s.login('owner','strong-password');self.assertEqual(self.s.scalar('PRAGMA user_version'),2);self.assertEqual(len(self.s.customers()),1)

if __name__=='__main__':unittest.main()
