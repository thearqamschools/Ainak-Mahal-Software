import os, tempfile, unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QMessageBox
from erp import ERP
from qdesktop import Login, STYLE
import access_recovery as ar
from access_recovery_ui import AccessRecovery


class AccessRecoveryUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / ar.DB_NAME
        s = ERP(self.db)
        s.bootstrap('owner', 'forgotten-pass', 'forgotten-pass')
        s.create_user('staff', 'staff-password', 'cashier')
        s.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_window_lists_usernames_and_offers_only_admins(self):
        d = AccessRecovery(self.db)
        try:
            names = {d.accounts.item(i, 0).text() for i in range(d.accounts.rowCount())}
            self.assertEqual(names, {'owner', 'staff'})
            self.assertEqual([d.target.itemData(i) for i in range(d.target.count())], ['owner'])
            self.assertIn('RESET owner', d.phrase_hint.text())
            self.assertFalse(d.new_username.isEnabled())
            d.mode_replace.setChecked(True)
            self.assertTrue(d.new_username.isEnabled())
        finally:
            d.close()

    def test_wrong_confirmation_shows_error_and_keeps_data(self):
        d = AccessRecovery(self.db)
        try:
            d.password.setText('new-password-1'); d.confirm.setText('new-password-1'); d.phrase.setText('RESET')
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes):
                d.submit()
            self.assertIn('RESET owner', d.error.text())
            self.assertIsNone(d.result_summary)
            self.assertFalse((self.db.parent / ar.BACKUP_FOLDER).exists())
        finally:
            d.close()

    def test_cancelled_confirmation_changes_nothing(self):
        d = AccessRecovery(self.db)
        try:
            d.password.setText('new-password-1'); d.confirm.setText('new-password-1'); d.phrase.setText('RESET owner')
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.No):
                d.submit()
            self.assertIsNone(d.result_summary)
            self.assertFalse((self.db.parent / ar.BACKUP_FOLDER).exists())
        finally:
            d.close()

    def test_full_recovery_then_sign_in_notice(self):
        d = AccessRecovery(self.db)
        try:
            d.mode_replace.setChecked(True); d.new_username.setText('owner-new')
            d.password.setText('new-password-1'); d.confirm.setText('new-password-1'); d.phrase.setText('RESET owner')
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.Yes), \
                 patch.object(QMessageBox, 'information') as info:
                d.submit()
            self.assertEqual(d.result_summary['username'], 'owner-new')
            self.assertIn(str(d.result_summary['backup']), info.call_args[0][2])
            self.assertEqual(d.password.text(), '')
        finally:
            d.close()
        s = ERP(self.db)
        try:
            login = Login(s, lambda: None)
            login.fields['username'].setText('owner-new'); login.fields['password'].setText('new-password-1')
            with patch.object(QMessageBox, 'warning') as warning:
                login.submit()
            self.assertEqual(s.role, 'admin')
            self.assertIn('Access Recovery', warning.call_args[0][2])
            self.assertIn('was switched off', warning.call_args[0][2])
        finally:
            s.close()


if __name__ == '__main__':
    unittest.main()
