import unittest,tempfile
from pathlib import Path
from core import Store
import phase4,phase3
class Phase4Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'db.sqlite');phase4.init(self.s.db)
  self.p=self.s.add_product('F01','Frame',1500,500,5)
 def tearDown(self):self.s.close();self.tmp.cleanup()
 def test_admin_bootstrap(self):
  phase4.bootstrap_admin(self.s.db,'owner','verystrongpassword');self.assertEqual(phase3.authenticate(self.s.db,'owner','verystrongpassword'),'admin')
  with self.assertRaises(ValueError):phase4.bootstrap_admin(self.s.db,'another','verystrongpassword')
 def test_return_once(self):
  sid,_,_=self.s.sell([(self.p,2)],paid=3000)
  phase4.return_item(self.s,sid,self.p,1,'Wrong size','owner','admin')
  self.assertEqual(self.s.db.execute('SELECT qty FROM products WHERE id=?',(self.p,)).fetchone()[0],4)
  with self.assertRaises(ValueError):phase4.return_item(self.s,sid,self.p,2,'Too many','owner','admin')
 def test_cashier_blocked(self):
  sid,_,_=self.s.sell([(self.p,1)])
  with self.assertRaises(PermissionError):phase4.return_item(self.s,sid,self.p,1,'test','cashier','cashier')
 def test_exports(self):
  self.s.sell([(self.p,1)]);path=Path(self.tmp.name)/'sales.csv'
  self.assertEqual(phase4.export_sales_csv(self.s,path),1);self.assertIn('Invoice ID',path.read_text(encoding='utf-8-sig'))
 def test_restore(self):
  backup=Path(self.tmp.name)/'backup.db';self.s.backup(backup)
  self.s.add_customer('Later Customer');self.s.close()
  safety=phase4.restore_database(backup,Path(self.tmp.name)/'db.sqlite');self.assertTrue(safety.exists())
  self.s=Store(Path(self.tmp.name)/'db.sqlite');self.assertEqual(self.s.db.execute('SELECT COUNT(*) FROM customers').fetchone()[0],0)
if __name__=='__main__':unittest.main()
