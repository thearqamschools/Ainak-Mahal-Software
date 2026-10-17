import unittest,tempfile
from pathlib import Path
from core import Store
import phase3
class Phase3Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'db.sqlite');phase3.init(self.store.db)
  self.pid=self.store.add_product('F001','Frame',1500,800,2)
  with self.store.db:self.supplier=self.store.db.execute("INSERT INTO suppliers(name) VALUES('Supplier')").lastrowid
 def tearDown(self):self.store.close();self.tmp.cleanup()
 def test_login(self):
  phase3.create_user(self.store.db,'admin','strongpassword','admin')
  self.assertEqual(phase3.authenticate(self.store.db,'admin','strongpassword'),'admin')
  self.assertIsNone(phase3.authenticate(self.store.db,'admin','bad'))
 def test_purchase_order_once(self):
  po=phase3.create_po(self.store,self.supplier,[(self.pid,3,700)])
  phase3.receive_po(self.store,po)
  self.assertEqual(self.store.db.execute('SELECT qty FROM products WHERE id=?',(self.pid,)).fetchone()[0],5)
  with self.assertRaises(ValueError):phase3.receive_po(self.store,po)
 def test_invoice_escape(self):
  cid=self.store.add_customer('<script>alert(1)</script>')
  sid,_,_=self.store.sell([(self.pid,1)],cid,100)
  rendered=phase3.invoice_html(self.store,sid)
  self.assertIn('&lt;script&gt;',rendered)
  self.assertNotIn('<script>',rendered)
 def test_job_transition(self):
  import uuid
  cid=self.store.add_customer('Client');jid=str(uuid.uuid4())
  with self.store.db:self.store.db.execute("INSERT INTO optical_jobs(id,customer_id,description,created_at) VALUES(?,?,?,?)",(jid,cid,'Glasses','2026-10-16'))
  phase3.update_job(self.store,jid,'In Lab')
  with self.assertRaises(ValueError):phase3.update_job(self.store,jid,'Delivered')
if __name__=='__main__':unittest.main()
