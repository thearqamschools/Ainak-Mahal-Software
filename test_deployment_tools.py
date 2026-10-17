import tempfile,unittest
from pathlib import Path
from core import Store
from deployment_tools import verified_backup,reconcile_stock,reconcile_payments,invoice_html,export_invoice
class DeploymentTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name);self.store=Store(self.path/'db.sqlite')
 def tearDown(self):self.store.close();self.tmp.cleanup()
 def test_backup_and_stock(self):
  self.store.add_product('F01','Frame',1200,500,4)
  self.assertEqual(reconcile_stock(self.store.db),[])
  self.assertTrue(verified_backup(self.store,self.path/'backups').exists())
 def test_receipt_escapes(self):
  pid=self.store.add_product('F02','<script>alert(1)</script>',100,30,3)
  sid,_,_=self.store.sell([(pid,1)],paid=30)
  self.assertIn('&lt;script&gt;',invoice_html(self.store.db,sid))
  self.assertEqual(reconcile_payments(self.store.db),[])
  self.assertTrue(export_invoice(self.store.db,sid,self.path/'invoices').exists())
 def test_detect_stock_discrepancy(self):
  pid=self.store.add_product('F03','Case',20,5,2)
  self.store.db.execute('UPDATE products SET qty=100 WHERE id=?',(pid,));self.store.db.commit()
  self.assertEqual(len(reconcile_stock(self.store.db)),1)
if __name__=='__main__':unittest.main()
