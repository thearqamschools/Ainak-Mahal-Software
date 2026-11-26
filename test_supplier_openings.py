import os, sqlite3, tempfile, unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
from retail import Retail
from erp import ERP
import supplier_openings as so

TODAY = date.today().isoformat()


class SupplierOpeningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'ainak_mahal.db'
        old = Retail(self.path)
        old.bootstrap('admin', 'strong-password', 'strong-password')
        pid = old.product('OLD', 'Old frame', 10, 5, 0, 'Frames')
        self.vendor = old.supplier('Lens House', '0300')
        self.other = old.supplier('Frame Co', '')
        self.legacy = [old.receive(self.vendor, [(pid, q, 100)]) for q in (10, 20, 30)]  # 1000, 2000, 3000
        self.other_legacy = old.receive(self.other, [(pid, 5, 100)])
        for receipt, day in zip(self.legacy, ('2026-01-10', '2026-02-10', '2026-03-10')):
            old.db.execute('UPDATE purchases SET date=? WHERE id=?', (day + 'T10:00:00', receipt))
        old.db.execute('UPDATE purchases SET date=? WHERE id=?', ('2026-02-01T10:00:00', self.other_legacy))
        old.db.commit(); old.close()
        self.s = ERP(self.path)
        self.s.login('admin', 'strong-password')
        self.pid = pid

    def tearDown(self):
        self.s.close(); self.tmp.cleanup()

    def due(self, receipt):
        return next(r for r in self.s.purchases() if r[0] == receipt)[5]

    def test_statement_allocates_unpaid_to_newest_receipts(self):
        plan = self.s.supplier_statement_preview(self.vendor, '2026-03-31', 4000)
        self.assertEqual([r['unpaid_cents'] for r in plan['receipts']], [0, 100000, 300000])
        result = self.s.confirm_supplier_statement(self.vendor, '2026-03-31', 4000, 'Statement Mar-2026', 'Checked with Ali')
        self.assertEqual([self.due(r) for r in self.legacy], [0, 1000, 3000])
        self.assertTrue(result['backup'].is_file())
        self.assertEqual(self.s.supplier_opening_worksheet()[0][1], 'Frame Co')          # only the other supplier left
        balances = {r[1]: r for r in self.s.supplier_balances()}
        self.assertEqual((balances['Lens House'][5], balances['Lens House'][6], balances['Lens House'][7]), (4000, 0, 0))
        self.assertEqual(balances['Frame Co'][7], 500)
        self.assertEqual(self.s.expected_cash(TODAY), 0)                                  # no cash invented
        self.assertEqual(self.s.scalar('SELECT COUNT(*) FROM supplier_payments'), 0)
        self.assertEqual(self.s.scalar('SELECT COUNT(*) FROM supplier_opening_evidence'), 3)
        self.assertEqual(self.s.scalar("SELECT COUNT(*) FROM audit_events WHERE action='supplier_statement_confirmed'"), 1)
        self.assertEqual(self.s.supplier_statements()[0][2], 'Statement Mar-2026')
        self.s.supplier_payment(self.legacy[2], 3000, 'Bank', 'TRF-1')                   # normal payments now allowed
        self.assertEqual(self.due(self.legacy[2]), 0)

    def test_backup_holds_the_state_before_confirmation(self):
        result = self.s.confirm_supplier_statement(self.vendor, '2026-03-31', 0, 'Statement zero')
        self.assertEqual([self.due(r) for r in self.legacy], [0, 0, 0])
        con = sqlite3.connect(result['backup'])
        try:
            self.assertEqual(con.execute('SELECT COUNT(*) FROM purchase_openings WHERE verified=0').fetchone()[0], 4)
            self.assertEqual(con.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        finally:
            con.close()

    def test_verified_receipts_and_payments_counted_only_up_to_statement_date(self):
        new = self.s.receive(self.vendor, [(self.pid, 5, 100)])                            # verified, 500
        self.s.db.execute("UPDATE purchases SET date='2026-04-01T09:00:00' WHERE id=?", (new,)); self.s.db.commit()
        self.s.supplier_payment(new, 200, 'Bank', 'TRF-A')
        self.s.db.execute("UPDATE supplier_payments SET created_at='2026-04-20T09:00:00'"); self.s.db.commit()
        plan = self.s.supplier_statement_preview(self.vendor, '2026-04-10', 3500)          # payment after statement date
        self.assertEqual((plan['verified_due_cents'], plan['legacy_unpaid_cents']), (50000, 300000))
        plan = self.s.supplier_statement_preview(self.vendor, '2026-04-30', 3300)          # payment included
        self.assertEqual((plan['verified_due_cents'], plan['legacy_unpaid_cents']), (30000, 300000))
        plan = self.s.supplier_statement_preview(self.vendor, '2026-03-31', 3000)          # new receipt not yet issued
        self.assertEqual(plan['verified_due_cents'], 0)

    def test_disagreements_are_refused_and_nothing_changes(self):
        future = (date.today() + timedelta(days=1)).isoformat()
        cases = [((self.vendor, '2026-03-01', 1000), 'before the last legacy receipt'),
                 ((self.vendor, future, 1000), 'future'),
                 ((self.vendor, '31-03-2026', 1000), 'YYYY-MM-DD'),
                 ((self.vendor, '2026-03-31', -5), 'positive'),
                 ((self.vendor, '2026-03-31', 'abc'), 'number'),
                 ((self.vendor, '2026-03-31', 6000.01), 'more than all'),
                 ((999, '2026-03-31', 0), 'Choose a supplier')]
        for args, message in cases:
            with self.subTest(args=args), self.assertRaisesRegex(ValueError, message):
                self.s.confirm_supplier_statement(*args, 'REF-1')
        new = self.s.receive(self.vendor, [(self.pid, 5, 100)])
        self.s.db.execute("UPDATE purchases SET date='2026-03-20T09:00:00' WHERE id=?", (new,)); self.s.db.commit()
        with self.assertRaisesRegex(ValueError, 'less than the amount Ainak Mahal already shows'):
            self.s.confirm_supplier_statement(self.vendor, '2026-03-31', 400, 'REF-1')
        with self.assertRaisesRegex(ValueError, 'statement number'):
            self.s.confirm_supplier_statement(self.vendor, '2026-03-31', 1000, ' ')
        self.assertIsNone(self.due(self.legacy[0]))
        self.assertFalse((self.path.parent / 'backups').exists())                         # refused before any backup

    def test_reference_reuse_and_second_confirmation(self):
        self.s.confirm_supplier_statement(self.vendor, '2026-03-31', 1000, 'ST-1')
        with self.assertRaisesRegex(ValueError, 'no unverified legacy receipts'):
            self.s.confirm_supplier_statement(self.vendor, '2026-03-31', 1000, 'ST-2')
        self.s.confirm_supplier_statement(self.other, '2026-03-31', 500, 'ST-1')          # same text, other supplier
        self.assertEqual(self.due(self.other_legacy), 500)

    def test_failure_inside_transaction_rolls_back(self):
        with patch.object(so.phase3, 'audit', side_effect=RuntimeError('disk')):
            with self.assertRaises(RuntimeError):
                self.s.confirm_supplier_statement(self.vendor, '2026-03-31', 4000, 'ST-X')
        self.assertIsNone(self.due(self.legacy[2]))
        self.assertIsNone(self.s.db.execute("SELECT 1 FROM sqlite_master WHERE name='supplier_statements'").fetchone())

    def test_cashier_cannot_confirm(self):
        self.s.create_user('staff', 'staff-password', 'cashier')
        self.s.actor = self.s.role = None; self.s.login('staff', 'staff-password')
        with self.assertRaises(PermissionError):
            self.s.confirm_supplier_statement(self.vendor, '2026-03-31', 0, 'ST-1')
        with self.assertRaises(PermissionError):
            self.s.supplier_statement_preview(self.vendor, '2026-03-31', 0)

    def test_reports(self):
        cols, rows = self.s.report('Supplier openings to confirm', '2026-01-01', TODAY)
        self.assertEqual([r[1] for r in rows], ['Frame Co', 'Lens House'])
        self.assertEqual(rows[1][3:5], (3, 6000))
        self.s.confirm_supplier_statement(self.vendor, '2026-03-31', 4000, 'ST-1')
        cols, rows = self.s.report('Supplier statements', '2026-01-01', TODAY)
        self.assertEqual(rows[0][3:6], (4000, 0, 4000))


class SupplierOpeningUiTests(unittest.TestCase):
    def test_purchasing_page_reconcile_flow(self):
        from PySide6.QtWidgets import QApplication, QMessageBox
        from qdesktop import Window, STYLE, Form
        app = QApplication.instance() or QApplication([]); app.setStyleSheet(STYLE)
        case = SupplierOpeningTests('test_reports'); case.setUp()
        try:
            w = Window(case.s); w.safe = lambda f: f()
            forms = []
            original = Form.exec
            def fill(form):
                forms.append(form)
                form.inputs['supplier'].setCurrentIndex(form.inputs['supplier'].findData(case.vendor))
                form.inputs['date'].setText('2026-03-31'); form.inputs['balance'].setText('4000'); form.inputs['reference'].setText('ST-UI')
                with patch.object(QMessageBox, 'question', return_value=QMessageBox.No):
                    form.submit()
                self_error = form.error.text()
                assert 'Not saved' in self_error, self_error
                with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes), patch.object(QMessageBox, 'information') as info:
                    form.submit()
                assert 'Backup made before the change' in info.call_args[0][2]
                return 1
            with patch.object(Form, 'exec', fill):
                w.supplier_statement()
            self.assertEqual(len(forms), 1)
            self.assertEqual(case.due(case.legacy[2]), 3000)
            w.close()
        finally:
            case.tearDown()


if __name__ == '__main__':
    unittest.main()
