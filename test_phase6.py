import tempfile,unittest,sqlite3
from pathlib import Path
from core import Store
import phase5,phase6
class Phase6Tests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.store=Store(Path(self.temp.name)/'data.db');phase6.init(self.store.db)
  pid=self.store.add_product('X','Frame',1000,400,2);sid,_,_=self.store.sell([(pid,1)],paid=800)
  self.rid=phase5.return_and_settle(self.store,sid,pid,1,'Customer return','admin','admin')['return_id']
 def tearDown(self):self.store.close();self.temp.cleanup()
 def test_partial_then_full(self):
  phase6.record_payout(self.store,self.rid,300,'Cash','R1','admin','admin')
  self.assertEqual(phase6.payout_status(self.store,self.rid)['remaining'],500)
  phase6.record_payout(self.store,self.rid,500,'Cash','R2','admin','admin')
  self.assertEqual(phase6.payout_status(self.store,self.rid)['remaining'],0)
 def test_overpayment_rejected(self):
  with self.assertRaises(ValueError):phase6.record_payout(self.store,self.rid,801,'Cash','R3','admin','admin')
 def test_duplicate_reference_rejected(self):
  phase6.record_payout(self.store,self.rid,100,'Cash','R4','admin','admin')
  with self.assertRaises(sqlite3.IntegrityError):phase6.record_payout(self.store,self.rid,100,'Cash','R4','admin','admin')
 def test_cashier_rejected(self):
  with self.assertRaises(PermissionError):phase6.record_payout(self.store,self.rid,100,'Cash','R5','cashier','cashier')
 def test_wrong_method_rejected(self):
  with self.assertRaises(ValueError):phase6.record_payout(self.store,self.rid,100,'Bank','R6','admin','admin')
if __name__=='__main__':unittest.main()
