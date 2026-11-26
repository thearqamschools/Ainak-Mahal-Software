"""Offline administrator access recovery for a shop that has lost its sign-in.

This is an explicit, separate tool (Start menu: "Ainak Mahal Access Recovery").
It is NOT a sign-in bypass. Trust boundary: whoever can open the Windows account
that holds the shop data can already copy or edit the SQLite file, so this tool
adds safety and visibility rather than pretending to add secrecy:

* the main application must be closed (instance lock);
* the live database must pass integrity checks before anything happens;
* a timestamped backup is written and verified, and its location is shown;
* the operator must type an exact confirmation naming the account;
* only the ``app_users`` row(s) change; every business table is fingerprinted
  before and after and the change is rolled back if anything else differs;
* passwords stay PBKDF2-hashed; no default/shared password exists;
* the reset is recorded and shown to the next administrator who signs in,
  who also gets an ``access_reset_acknowledged`` audit event.
"""
import getpass
import hashlib
import os
import platform
import sqlite3
from datetime import datetime
from pathlib import Path

import phase3
from phase4 import verify_database
from paths import InstanceLock
from deployment_tools import reconcile_stock, reconcile_payments

DB_NAME = 'ainak_mahal.db'
BACKUP_FOLDER = 'access-recovery-backups'
MODES = ('password', 'replace')
# Tables the reset is allowed to touch. Everything else must be byte-for-byte equal.
ACCESS_TABLES = {'app_users', 'audit_events', 'access_recovery_events', 'sqlite_sequence'}

EVENTS_DDL = '''CREATE TABLE IF NOT EXISTS access_recovery_events(
 id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, windows_user TEXT NOT NULL,
 computer TEXT NOT NULL, mode TEXT NOT NULL, target_username TEXT NOT NULL,
 new_username TEXT NOT NULL, backup_path TEXT NOT NULL,
 acknowledged_by TEXT, acknowledged_at TEXT)'''


class RecoveryError(Exception):
    """A safe, operator-readable refusal. Nothing was changed when this is raised."""


def confirmation_phrase(target_username):
    return f'RESET {target_username}'


def _connect_ro(path):
    return sqlite3.connect(f'file:{Path(path).resolve().as_posix()}?mode=ro', uri=True)


def _check_live(db_path):
    db_path = Path(db_path)
    if not db_path.is_file():
        raise RecoveryError(f'No Ainak Mahal database was found at:\n{db_path}\n'
                            'Nothing was changed. Check the data folder before continuing.')
    try:
        verify_database(db_path)
    except (ValueError, sqlite3.Error) as ex:
        raise RecoveryError(f'The database did not pass its safety check ({ex}). Nothing was changed. '
                            'Keep the file and its -wal/-shm files and ask a technician for help.') from None
    con = _connect_ro(db_path)
    try:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='app_users'").fetchone():
            raise RecoveryError('This database has no staff accounts yet. Open Ainak Mahal normally '
                                'to create the first administrator. Nothing was changed.')
    finally:
        con.close()


def list_accounts(db_path):
    """Username recovery: every account name, role and status. Never returns hashes."""
    _check_live(db_path)
    con = _connect_ro(db_path)
    try:
        return [{'username': u, 'role': r, 'active': bool(a)} for u, r, a in
                con.execute('SELECT username,role,active FROM app_users ORDER BY role, username COLLATE NOCASE')]
    finally:
        con.close()


def business_fingerprint(con):
    """Row count and content hash for every table the reset must not touch."""
    result = {}
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    for table in tables:
        if table in ACCESS_TABLES:
            continue
        digest = hashlib.sha256()
        count = 0
        for row in con.execute(f'SELECT * FROM "{table}" ORDER BY rowid'):
            digest.update(repr(row).encode('utf-8'))
            count += 1
        result[table] = (count, digest.hexdigest())
    return result


def _validate_username(username):
    if username != username.strip() or not 3 <= len(username) <= 40:
        raise RecoveryError('Usernames must be 3 to 40 characters without spaces at the start or end.')
    if any(not ch.isprintable() for ch in username):
        raise RecoveryError('Usernames cannot contain hidden or control characters.')


def _validate_password(username, password, confirm):
    if password != confirm:
        raise RecoveryError('The two passwords do not match. Nothing was changed.')
    if len(password) < 10:
        raise RecoveryError('Use a password of at least 10 characters. Nothing was changed.')
    if password.strip().lower() == username.lower():
        raise RecoveryError('The password cannot be the same as the username. Nothing was changed.')


def make_backup(db_path, backup_dir=None, stamp=None):
    """SQLite online backup (includes WAL content), then verify it matches the live data."""
    db_path = Path(db_path)
    backup_dir = Path(backup_dir) if backup_dir else db_path.parent / BACKUP_FOLDER
    stamp = stamp or datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        target = backup_dir / f'{db_path.stem}_before_access_reset_{stamp}{db_path.suffix}'
        if target.exists():
            raise FileExistsError(f'{target} already exists')
        source = _connect_ro(db_path)
        out = sqlite3.connect(target)
        try:
            source.backup(out)
            before = business_fingerprint(source)
            users = source.execute('SELECT * FROM app_users ORDER BY id').fetchall()
        finally:
            out.close()
            source.close()
        verify_database(target)
        check = _connect_ro(target)
        try:
            if business_fingerprint(check) != before or check.execute('SELECT * FROM app_users ORDER BY id').fetchall() != users:
                raise ValueError('backup contents differ from the live database')
        finally:
            check.close()
    except (OSError, ValueError, sqlite3.Error) as ex:
        raise RecoveryError(f'A safety backup could not be created or verified ({ex}). '
                            'Nothing was changed. Free disk space or check folder permissions, then try again.') from None
    return target


def reset_access(db_path, target_username, mode, new_password, confirm_password, confirmation,
                 new_username=None, backup_dir=None, lock_directory=None, operator=None):
    """Restore administrator access. Returns a summary dict. Raises RecoveryError on refusal.

    mode='password': keep the administrator's username and set a new password.
    mode='replace' : create a new administrator account and switch off the lost one.
    """
    db_path = Path(db_path)
    if mode not in MODES:
        raise RecoveryError('Choose either "New password" or "Replacement administrator".')
    try:
        lock = InstanceLock(lock_directory or db_path.parent)
    except RuntimeError:
        raise RecoveryError('Ainak Mahal is still open on this computer. Close every Ainak Mahal '
                            'window (and the Recovery tool if it is open twice), then try again. Nothing was changed.') from None
    try:
        _check_live(db_path)
        con = _connect_ro(db_path)
        try:
            target = con.execute('SELECT id,username,role,active FROM app_users WHERE username=?',
                                 (target_username,)).fetchone()
            existing = [u for (u,) in con.execute('SELECT username FROM app_users')]
        finally:
            con.close()
        if not target:
            raise RecoveryError(f'There is no account named "{target_username}". Choose it from the list. Nothing was changed.')
        if target[2] != 'admin':
            raise RecoveryError(f'"{target_username}" is a cashier account. Choose an administrator account. '
                                'Staff passwords are reset by an administrator inside Ainak Mahal.')
        if confirmation != confirmation_phrase(target_username):
            raise RecoveryError(f'Type exactly:  {confirmation_phrase(target_username)}\nNothing was changed.')
        login_name = target_username
        if mode == 'replace':
            login_name = new_username or ''
            _validate_username(login_name)
            if any(u.casefold() == login_name.casefold() for u in existing):
                raise RecoveryError(f'The username "{login_name}" is already used. Choose a different name. Nothing was changed.')
        _validate_password(login_name, new_password, confirm_password)

        backup = make_backup(db_path, backup_dir)

        operator = operator or _operator()
        con = sqlite3.connect(db_path)
        try:
            con.execute('PRAGMA foreign_keys=ON')
            con.execute('PRAGMA busy_timeout=5000')
            before = business_fingerprint(con)
            con.execute('BEGIN IMMEDIATE')
            con.execute(EVENTS_DDL)
            salt = phase3.secrets.token_hex(16)
            digest = phase3.hash_password(new_password, salt)
            if mode == 'password':
                con.execute('UPDATE app_users SET salt=?,password_hash=?,active=1 WHERE id=?', (salt, digest, target[0]))
            else:
                con.execute("INSERT INTO app_users(username,salt,password_hash,role,active) VALUES(?,?,?,'admin',1)",
                            (login_name, salt, digest))
                con.execute('UPDATE app_users SET active=0 WHERE id=?', (target[0],))
            stamp = datetime.now().isoformat(timespec='seconds')
            con.execute('''INSERT INTO access_recovery_events(created_at,windows_user,computer,mode,target_username,new_username,backup_path)
                           VALUES(?,?,?,?,?,?,?)''', (stamp, operator[0], operator[1], mode, target_username, login_name, str(backup)))
            phase3.audit(con, f'access-recovery:{operator[0]}', f'access_reset_{mode}',
                         f'{target_username} -> {login_name}; backup {backup}')
            if business_fingerprint(con) != before:
                raise RecoveryError('Business records would have changed, so the reset was cancelled. Nothing was changed.')
            if phase3.authenticate(con, login_name, new_password) != 'admin':
                raise RecoveryError('The new sign-in could not be confirmed, so the reset was cancelled. Nothing was changed.')
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()

        verify_database(db_path)
        con = _connect_ro(db_path)
        try:
            stock, payments = reconcile_stock(con), reconcile_payments(con)
        finally:
            con.close()
        return {'username': login_name, 'mode': mode, 'backup': backup,
                'stock_mismatches': len(stock), 'payment_mismatches': len(payments)}
    finally:
        lock.close()


def _operator():
    try:
        user = getpass.getuser()
    except Exception:
        user = os.environ.get('USERNAME', 'unknown')
    return user or 'unknown', platform.node() or 'unknown'


def pending_notices(db):
    """Unacknowledged resets, for display to the next administrator."""
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='access_recovery_events'").fetchone():
        return []
    return db.execute('''SELECT id,created_at,windows_user,computer,mode,target_username,new_username,backup_path
        FROM access_recovery_events WHERE acknowledged_at IS NULL ORDER BY id''').fetchall()


def acknowledge(db, actor):
    """Called inside the sign-in transaction for administrators. Returns the notices shown."""
    notices = pending_notices(db)
    for notice in notices:
        db.execute('UPDATE access_recovery_events SET acknowledged_by=?,acknowledged_at=? WHERE id=?',
                   (actor, datetime.now().isoformat(timespec='seconds'), notice[0]))
        phase3.audit(db, actor, 'access_reset_acknowledged',
                     f'event {notice[0]}: {notice[4]} {notice[5]} -> {notice[6]} by Windows user {notice[2]} on {notice[3]} at {notice[1]}')
    return notices
