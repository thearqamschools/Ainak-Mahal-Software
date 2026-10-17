import tempfile,unittest
from pathlib import Path
from core import Store
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'store.db')
  self.cid=self.s.add_customer('Ali','03000000000');self.pid=self.s.add_product('F-1','Frame',1500,900,10)
 def tearDown(self):self.s.close();self.tmp.cleanup()
 def test_multi_item_and_payment(self):
  sid,total,due=self.s.sell([(self.pid,2),(self.pid,1)],self.cid,1000)
  self.assertEqual((total,due),(4500,3500));self.assertEqual(self.s.db.execute('SELECT qty FROM products').fetchone()[0],7)
  self.s.pay(sid,3500);self.assertEqual(self.s.db.execute('SELECT paid FROM sales').fetchone()[0],4500)
 def test_atomic_insufficient_stock(self):
  with self.assertRaises(ValueError):self.s.sell([(self.pid,2),(999,1)])
  self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM sales').fetchone()[0],0)
  self.assertEqual(self.s.db.execute('SELECT qty FROM products').fetchone()[0],10)
 def test_backup(self):
  path=Path(self.tmp.name)/'backup.db';self.s.backup(path);self.assertTrue(path.exists())
 def test_overpayment(self):
  with self.assertRaises(ValueError):self.s.sell([(self.pid,1)],paid=2000)
 def test_purchase(self):
  with self.s.db:self.s.db.execute("INSERT INTO suppliers(name) VALUES('Supplier')")
  self.s.receive(1,[(self.pid,4,700)]);self.assertEqual(self.s.db.execute('SELECT qty FROM products').fetchone()[0],14)
if __name__=='__main__':unittest.main()
