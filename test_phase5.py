import tempfile, unittest
from pathlib import Path
from core import Store
import phase5

class Phase5Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(Path(self.tmp.name)/'test.db')
        phase5.init(self.store.db)
        self.pid=self.store.add_product('FRAME01','Frame',1000,500,5)
    def tearDown(self):
        self.store.close();self.tmp.cleanup()
    def test_partial_paid_refund_allocates_credit(self):
        sid,_,_=self.store.sell([(self.pid,1)],paid=300)
        r=phase5.return_and_settle(self.store,sid,self.pid,1,'Wrong size','admin','admin')
        self.assertEqual(r['payout_due'],300)
        self.assertEqual(r['credit_adjustment'],700)
        self.assertEqual(phase5.invoice_position(self.store,sid)['net_customer_balance'],0)
        self.assertEqual(self.store.db.execute('SELECT qty FROM products WHERE id=?',(self.pid,)).fetchone()[0],5)
    def test_over_return_rollback(self):
        sid,_,_=self.store.sell([(self.pid,1)],paid=1000)
        phase5.return_and_settle(self.store,sid,self.pid,1,'Defect','admin','admin')
        with self.assertRaises(ValueError):
            phase5.return_and_settle(self.store,sid,self.pid,1,'Duplicate','admin','admin')
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM return_settlements').fetchone()[0],1)
    def test_cashier_cannot_return(self):
        sid,_,_=self.store.sell([(self.pid,1)],paid=1000)
        with self.assertRaises(PermissionError):
            phase5.return_and_settle(self.store,sid,self.pid,1,'Defect','cashier','cashier')
    def test_credit_method(self):
        sid,_,_=self.store.sell([(self.pid,1)],paid=1000)
        r=phase5.return_and_settle(self.store,sid,self.pid,1,'Exchange','admin','admin','Credit')
        self.assertEqual(r['payout_due'],0)
        self.assertEqual(r['credit_adjustment'],1000)
if __name__=='__main__':unittest.main()
