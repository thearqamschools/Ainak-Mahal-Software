import os, sqlite3, tempfile, unittest
from pathlib import Path
from unittest import mock
import access_recovery as ar
from erp import ERP
from paths import InstanceLock

PW = 'lost-forever-pw'
NEW = 'brand-new-password'


class AccessRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.db = self.dir / ar.DB_NAME
        s = ERP(self.db)
        s.bootstrap('owner', PW, PW)
        s.create_user('staff', 'staff-password', 'cashier')
        cid = s.customer('Customer A', '0300-0000000')
        pid = s.product('F1', 'Frame', 1000, 400, 5, 'Frames', '111')
        s.login('owner', PW)
        s.checkout([(pid, 1)], cid, 300)
        s.close()
        self.before = self.fingerprint()

    def tearDown(self):
        self.tmp.cleanup()

    def fingerprint(self):
        con = sqlite3.connect(self.db)
        try:
            return ar.business_fingerprint(con)
        finally:
            con.close()

    def users(self):
        con = sqlite3.connect(self.db)
        try:
            return con.execute('SELECT username,role,active,password_hash FROM app_users ORDER BY id').fetchall()
        finally:
            con.close()

    def reset(self, **kw):
        args = dict(target_username='owner', mode='password', new_password=NEW, confirm_password=NEW,
                    confirmation='RESET owner', operator=('tester', 'PC'))
        args.update(kw)
        return ar.reset_access(self.db, **args)

    def assert_unchanged(self, users_before):
        self.assertEqual(self.users(), users_before)
        self.assertEqual(self.fingerprint(), self.before)

    def test_username_recovery_lists_accounts_without_secrets(self):
        accounts = ar.list_accounts(self.db)
        self.assertEqual({a['username'] for a in accounts}, {'owner', 'staff'})
        self.assertTrue(all(set(a) == {'username', 'role', 'active'} for a in accounts))

    def test_password_reset_success_preserves_business_data(self):
        result = self.reset()
        self.assertTrue(result['backup'].is_file())
        self.assertEqual(result['backup'].parent, self.dir / ar.BACKUP_FOLDER)
        self.assertEqual((result['stock_mismatches'], result['payment_mismatches']), (0, 0))
        self.assertEqual(self.fingerprint(), self.before)
        # backup still holds the old credentials, live database has the new one
        old = sqlite3.connect(result['backup'])
        try:
            import phase3
            self.assertEqual(phase3.authenticate(old, 'owner', PW), 'admin')
        finally:
            old.close()
        s = ERP(self.db)
        try:
            with self.assertRaises(ValueError):
                s.login('owner', PW)
            self.assertEqual(s.login('owner', NEW), 'admin')
            self.assertEqual(len(s.access_notices), 1)
            self.assertEqual(s.scalar("SELECT COUNT(*) FROM audit_events WHERE action='access_reset_acknowledged'"), 1)
            self.assertEqual(s.scalar("SELECT COUNT(*) FROM audit_events WHERE action='access_reset_password'"), 1)
            s.actor = s.role = None
            s.login('owner', NEW)
            self.assertEqual(s.access_notices, [])  # shown once only
        finally:
            s.close()
        stored = [u for u in self.users() if u[0] == 'owner'][0][3]
        self.assertNotIn(NEW, stored)
        self.assertEqual(len(stored), 64)

    def test_replacement_admin_success(self):
        result = self.reset(mode='replace', new_username='owner2')
        self.assertEqual(result['username'], 'owner2')
        users = {u[0]: u[1:3] for u in self.users()}
        self.assertEqual(users['owner'], ('admin', 0))
        self.assertEqual(users['owner2'], ('admin', 1))
        self.assertEqual(self.fingerprint(), self.before)
        s = ERP(self.db)
        try:
            self.assertEqual(s.login('owner2', NEW), 'admin')
            self.assertEqual(len(s.access_notices), 1)
        finally:
            s.close()

    def test_cashier_sign_in_does_not_acknowledge(self):
        self.reset()
        s = ERP(self.db)
        try:
            s.login('staff', 'staff-password')
            self.assertEqual(s.access_notices, [])
            self.assertEqual(len(ar.pending_notices(s.db)), 1)
        finally:
            s.close()

    def test_wrong_target_cashier_target_and_confirmation_change_nothing(self):
        before = self.users()
        for kw in ({'target_username': 'nobody', 'confirmation': 'RESET nobody'},
                   {'target_username': 'staff', 'confirmation': 'RESET staff'},
                   {'confirmation': 'reset owner'},
                   {'confirmation': ''},
                   {'mode': 'delete'}):
            with self.subTest(kw=kw):
                with self.assertRaises(ar.RecoveryError):
                    self.reset(**kw)
                self.assert_unchanged(before)
        self.assertFalse((self.dir / ar.BACKUP_FOLDER).exists())

    def test_duplicate_and_invalid_inputs(self):
        before = self.users()
        for kw in ({'mode': 'replace', 'new_username': 'staff'},
                   {'mode': 'replace', 'new_username': 'OWNER'},
                   {'mode': 'replace', 'new_username': ''},
                   {'mode': 'replace', 'new_username': ' padded '},
                   {'mode': 'replace', 'new_username': 'bad\x00name'},
                   {'new_password': 'short', 'confirm_password': 'short'},
                   {'confirm_password': 'something-else'},
                   {'mode': 'replace', 'new_username': 'manager1', 'new_password': 'manager1', 'confirm_password': 'manager1'}):
            with self.subTest(kw=kw):
                with self.assertRaises(ar.RecoveryError):
                    self.reset(**kw)
                self.assert_unchanged(before)

    def test_refuses_while_application_is_open(self):
        before = self.users()
        lock = InstanceLock(self.dir)
        try:
            with self.assertRaisesRegex(ar.RecoveryError, 'still open'):
                self.reset()
        finally:
            lock.close()
        self.assert_unchanged(before)

    def test_missing_and_corrupt_database(self):
        with self.assertRaisesRegex(ar.RecoveryError, 'No Ainak Mahal database'):
            ar.reset_access(self.dir / 'missing.db', 'owner', 'password', NEW, NEW, 'RESET owner')
        self.assertFalse((self.dir / 'missing.db').exists())
        bad = self.dir / 'bad' / ar.DB_NAME
        bad.parent.mkdir()
        bad.write_bytes(b'not a database at all' * 100)
        with self.assertRaisesRegex(ar.RecoveryError, 'safety check'):
            ar.reset_access(bad, 'owner', 'password', NEW, NEW, 'RESET owner')
        self.assertEqual(bad.read_bytes(), b'not a database at all' * 100)

    def test_backup_failure_changes_nothing(self):
        before = self.users()
        blocker = self.dir / 'blocked'
        blocker.write_text('a file, not a folder')
        with self.assertRaisesRegex(ar.RecoveryError, 'backup could not be created'):
            self.reset(backup_dir=blocker / 'sub')
        self.assert_unchanged(before)
        with mock.patch.object(ar, 'business_fingerprint', side_effect=[{'x': 1}, {'x': 2}]):
            with self.assertRaisesRegex(ar.RecoveryError, 'backup could not be created'):
                self.reset()
        self.assert_unchanged(before)

    def test_failure_after_backup_rolls_back(self):
        before = self.users()
        with mock.patch.object(ar.phase3, 'authenticate', return_value=None):
            with self.assertRaisesRegex(ar.RecoveryError, 'could not be confirmed'):
                self.reset()
        self.assert_unchanged(before)
        con = sqlite3.connect(self.db)
        try:
            self.assertIsNone(con.execute("SELECT 1 FROM sqlite_master WHERE name='access_recovery_events'").fetchone())
        finally:
            con.close()

    def test_switched_off_admin_can_be_recovered(self):
        con = sqlite3.connect(self.db)
        with con:
            con.execute("UPDATE app_users SET active=0 WHERE username='owner'")
        con.close()
        self.reset()
        s = ERP(self.db)
        try:
            self.assertEqual(s.login('owner', NEW), 'admin')
        finally:
            s.close()

    def test_wal_content_is_in_backup(self):
        con = sqlite3.connect(self.db)
        con.execute('PRAGMA journal_mode=WAL')
        with con:
            con.execute("INSERT INTO customers(name,phone,address) VALUES('WAL customer','','')")
        self.before = self.fingerprint()
        result = self.reset()  # while the WAL connection still has pages un-checkpointed
        con.close()
        backup = sqlite3.connect(result['backup'])
        try:
            self.assertEqual(backup.execute("SELECT COUNT(*) FROM customers WHERE name='WAL customer'").fetchone()[0], 1)
        finally:
            backup.close()


if __name__ == '__main__':
    unittest.main()
