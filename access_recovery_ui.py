"""Qt window for Ainak Mahal Access Recovery (AinakMahal.exe --reset-access)."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (QDialog, QLabel, QLineEdit, QComboBox, QRadioButton, QTableWidget,
                               QTableWidgetItem, QHeaderView, QVBoxLayout, QHBoxLayout, QPushButton,
                               QMessageBox, QAbstractItemView, QCheckBox, QFormLayout, QWidget)
import access_recovery as ar
from app_info import DEVELOPER_CREDIT, DISPLAY_VERSION
from qdesktop import ASSETS


class AccessRecovery(QDialog):
    def __init__(self, db_path):
        super().__init__()
        self.db_path = db_path
        self.result_summary = None
        self.setWindowTitle('Ainak Mahal · Access Recovery')
        self.setWindowIcon(QIcon(str(ASSETS / 'ainak-mahal.ico')))
        from qdesktop import fit_to_screen, scrolling
        outer = QVBoxLayout(self)
        content = QWidget()
        layout = QVBoxLayout(content)
        outer.addWidget(scrolling(content), 1)
        fit_to_screen(self, 720, 680)
        title = QLabel('Recover administrator access')
        title.setObjectName('heading')
        title.setStyleSheet('font-size:18pt;font-weight:600')
        layout.addWidget(title)
        intro = QLabel('Use this only if the shop administrator cannot sign in. Close Ainak Mahal first. '
                       'A safety backup is made and checked before anything changes. Customers, stock, '
                       'sales and payments are not touched.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        where = QLabel(f'Shop data: {db_path}')
        where.setTextInteractionFlags(Qt.TextSelectableByMouse)
        where.setWordWrap(True)
        layout.addWidget(where)

        layout.addWidget(QLabel('<b>Step 1 · Find the username</b> — accounts on this computer:'))
        self.accounts = QTableWidget(0, 3)
        self.accounts.setHorizontalHeaderLabels(('Username', 'Role', 'Status'))
        self.accounts.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.accounts.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.accounts.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.accounts.setAccessibleName('Accounts on this computer')
        self.accounts.setMaximumHeight(160)
        layout.addWidget(self.accounts)

        layout.addWidget(QLabel('<b>Step 2 · Choose what to do</b>'))
        self.mode_password = QRadioButton('Set a new password and keep the same username')
        self.mode_replace = QRadioButton('Create a replacement administrator and switch off the lost account')
        self.mode_password.setChecked(True)
        layout.addWidget(self.mode_password)
        layout.addWidget(self.mode_replace)

        form_widget = QWidget()
        form = QFormLayout(form_widget)
        self.target = QComboBox()
        self.target.setAccessibleName('Administrator account to recover')
        self.new_username = QLineEdit()
        self.new_username.setAccessibleName('New administrator username')
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setAccessibleName('New password')
        self.confirm = QLineEdit()
        self.confirm.setEchoMode(QLineEdit.Password)
        self.confirm.setAccessibleName('Confirm new password')
        self.phrase = QLineEdit()
        self.phrase.setAccessibleName('Typed confirmation')
        self.phrase_hint = QLabel()
        form.addRow('Administrator account', self.target)
        form.addRow('New username', self.new_username)
        form.addRow('New password (10+ characters)', self.password)
        form.addRow('Confirm new password', self.confirm)
        form.addRow(self.phrase_hint)
        form.addRow('Confirmation', self.phrase)
        layout.addWidget(form_widget)
        show = QCheckBox('Show password')
        show.toggled.connect(lambda on: [w.setEchoMode(QLineEdit.Normal if on else QLineEdit.Password)
                                         for w in (self.password, self.confirm)])
        layout.addWidget(show)

        self.error = QLabel('')
        self.error.setWordWrap(True)
        self.error.setStyleSheet('color:#B91C1C')
        layout.addWidget(self.error)
        buttons = QHBoxLayout()
        self.reset_button = QPushButton('Make backup and recover access')
        self.reset_button.clicked.connect(self.submit)
        close = QPushButton('Close')
        close.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(close)
        buttons.addWidget(self.reset_button)
        outer.addLayout(buttons)
        footer = QLabel(f'{DEVELOPER_CREDIT} · {DISPLAY_VERSION}')
        footer.setStyleSheet('font-size:8pt;color:#5B6B7F')
        layout.addWidget(footer)

        self.target.currentIndexChanged.connect(self._update)
        self.mode_password.toggled.connect(self._update)
        self.load()

    def load(self):
        rows = ar.list_accounts(self.db_path)
        self.accounts.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate((row['username'], row['role'].title(), 'Active' if row['active'] else 'Switched off')):
                self.accounts.setItem(i, j, QTableWidgetItem(value))
        self.target.clear()
        for row in rows:
            if row['role'] == 'admin':
                self.target.addItem(row['username'] + ('' if row['active'] else '  (switched off)'), row['username'])
        if not self.target.count():
            self.error.setText('No administrator account exists. Ask a technician for help; nothing will be changed.')
            self.reset_button.setEnabled(False)
        self._update()

    def _update(self):
        name = self.target.currentData() or ''
        self.new_username.setEnabled(self.mode_replace.isChecked())
        self.phrase_hint.setText(f'To confirm, type exactly:  <b>{ar.confirmation_phrase(name)}</b>')

    def submit(self):
        self.error.setText('')
        mode = 'replace' if self.mode_replace.isChecked() else 'password'
        name = self.target.currentData() or ''
        summary_line = (f'Set a new password for "{name}".' if mode == 'password' else
                        f'Create administrator "{self.new_username.text()}" and switch off "{name}".')
        if QMessageBox.question(self, 'Recover access?', summary_line + '\n\nA verified backup will be made first. Continue?') != QMessageBox.Yes:
            return
        try:
            result = ar.reset_access(self.db_path, name, mode, self.password.text(), self.confirm.text(),
                                     self.phrase.text(), new_username=self.new_username.text())
        except ar.RecoveryError as ex:
            self.error.setText(str(ex))
            return
        except Exception as ex:  # unexpected: never leave the operator guessing
            self.error.setText(f'Recovery stopped: {ex}. Your data was backed up only if a backup path was shown.')
            return
        finally:
            for w in (self.password, self.confirm):
                w.clear()
        self.result_summary = result
        checks = ('Stock and payment checks passed.' if not (result['stock_mismatches'] or result['payment_mismatches'])
                  else f'Note: {result["stock_mismatches"]} stock and {result["payment_mismatches"]} payment differences '
                       'already existed before this reset. Review them in Backup & Recovery → Reconciliation.')
        QMessageBox.information(self, 'Access recovered',
                                f'You can now sign in to Ainak Mahal as "{result["username"]}".\n\n'
                                f'Safety backup (kept on this computer):\n{result["backup"]}\n\n{checks}\n\n'
                                'Copy the backup to a USB drive or other safe place. Write the new username down somewhere secure.')
        self.load()
        self.phrase.clear()
        self.new_username.clear()


def main():
    from paths import data_dir
    from paths import InstanceLock
    db_path = data_dir() / ar.DB_NAME
    try:
        InstanceLock(data_dir()).close()
    except RuntimeError:
        QMessageBox.critical(None, 'Access Recovery', 'Ainak Mahal is open. Close every Ainak Mahal window, then open Access Recovery again. Nothing was changed.')
        return 1
    try:
        window = AccessRecovery(db_path)
    except ar.RecoveryError as ex:
        QMessageBox.critical(None, 'Access Recovery', str(ex))
        return 1
    window.exec()
    return 0
