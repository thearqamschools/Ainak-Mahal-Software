import os,tempfile,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QMessageBox,QDialog
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from erp import ERP
from qdesktop import Window,Login,Form,Table,STYLE

class QtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([]);cls.app.setStyleSheet(STYLE)
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.s=ERP(Path(self.tmp.name)/'test.db');self.s.bootstrap('owner','strong-password','strong-password');self.cid=self.s.customer('Customer');self.pid=self.s.product('F','Frame',1000,400,5,'Frames','12345');self.w=Window(self.s);self.w.safe=lambda f:f();self.w.show();self.app.processEvents()
    def tearDown(self):self.w.cart=[];self.w.close();self.app.processEvents();self.s.close();self.tmp.cleanup()
    def test_scanner_keyboard_cart_and_real_checkout_button(self):
        self.w.show_page(1);self.w.scan.setFocus();QTest.keyClicks(self.w.scan,'12345');QTest.keyClick(self.w.scan,Qt.Key_Return);self.assertEqual(self.w.cart,[(self.pid,1)])
        self.w.pos_customer.setCurrentIndex(self.w.pos_customer.findData(self.cid));self.w.paid.setText('1000')
        with patch.object(QMessageBox,'question',return_value=QMessageBox.No):self.w.complete()
        self.assertEqual(self.s.scalar('SELECT COUNT(*) FROM sales'),1);self.assertEqual(self.s.scalar('SELECT qty FROM products'),4);self.assertFalse(self.w.cart)
    def test_navigation_preserves_unsaved_order_context(self):
        self.w.show_page(1);self.w.pos_customer.setCurrentIndex(self.w.pos_customer.findData(self.cid));self.w.paid.setText('200');self.w.job_note.setText('Keep these instructions');self.w.make_job.setChecked(True);self.w.show_page(2);self.w.show_page(1)
        self.assertEqual(self.w.pos_customer.currentData(),self.cid);self.assertEqual(self.w.paid.text(),'200');self.assertEqual(self.w.job_note.text(),'Keep these instructions');self.assertTrue(self.w.make_job.isChecked())
    def test_form_validation_preserves_input(self):
        d=Form(self.w,'Rx',[('od_cyl','OD CYL'),('od_axis','OD AXIS')],lambda v:self.s.save_rx(self.cid,v));d.inputs['od_cyl'].setText('-1');d.inputs['od_axis'].setText('190');d.submit();self.assertNotEqual(d.result(),QDialog.Accepted);self.assertTrue(d.error.text());self.assertEqual(d.inputs['od_axis'].text(),'190');d.close()
    def test_sorting_keeps_correct_identity(self):
        t=Table(('ID','Name'),[(2,'B'),(10,'A')]);t.sortItems(0,Qt.DescendingOrder);t.selectRow(0);self.assertEqual(t.selected()[0],10)
    def test_all_pages_and_role_navigation(self):
        for i in range(12):QTest.mouseClick(self.w.nav[i],Qt.LeftButton);self.app.processEvents();self.assertEqual(self.w.current,i)
        self.s.create_user('staff','staff-password','cashier');self.s.login('staff','staff-password');w=Window(self.s)
        try:
            for i in (6,8,10,11):self.assertFalse(w.nav[i].isEnabled())
        finally:w.close()
    def test_barcode_local_image(self):
        from labels import barcode_png
        p=barcode_png('123456789',Path(self.tmp.name)/'label.png');self.assertGreater(p.stat().st_size,100)

if __name__=='__main__':unittest.main()
