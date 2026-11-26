"""Screens fit common shop laptops at Windows scaling 100-150%, work by keyboard and meet WCAG AA contrast."""
import json, os, re, subprocess, sys, tempfile, unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from erp import ERP
import qdesktop
from qdesktop import Window, Login, STYLE, NAV, PLACEHOLDER

ROOT = Path(__file__).resolve().parent
# Usable area (screen minus taskbar) in logical pixels, and the Windows scale factor.
SCREENS = {
    '1366x768 at 100%': (1366, 720, 1.0),
    '1366x768 at 125%': (1093, 576, 1.25),
    '1600x900 at 150%': (1067, 568, 1.5),
    '1920x1080 at 125%': (1536, 830, 1.25),
    '1920x1080 at 150%': (1280, 688, 1.5),
    '1280x720 at 100%': (1280, 672, 1.0),
}


class ScreenFitTests(unittest.TestCase):
    def test_every_screen_fits_and_every_input_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Second pass: text 30% larger in a wide font, so pages must adapt rather than fit by luck.
            stress = {'AINAK_AUDIT_FONT': 'DejaVu Sans', 'AINAK_AUDIT_EXTRA_STYLE': 'QWidget{font-size:13pt;}'}
            for (name, (w, h, dpr)), extra in [(item, {}) for item in SCREENS.items()] + [(item, stress) for item in SCREENS.items()]:
                with self.subTest(screen=name, large_text=bool(extra)):
                    config = Path(tmp) / 'screen.json'
                    config.write_text(json.dumps({'screens': [{'name': 's', 'x': 0, 'y': 0, 'width': w, 'height': h,
                                                               'logicalDpi': 96, 'logicalBaseDpi': 96, 'dpr': dpr}]}))
                    # Relative path: a Windows drive letter ("C:") would be read as an option separator.
                    env = dict(os.environ, QT_QPA_PLATFORM='offscreen:configfile=screen.json', **extra)
                    run = subprocess.run([sys.executable, str(ROOT / 'tools' / 'screen_audit.py')], env=env,
                                         capture_output=True, text=True, timeout=300, cwd=tmp)
                    self.assertEqual(run.returncode, 0, run.stderr[-2000:])
                    report = json.loads(run.stdout.strip().splitlines()[-1])
                    self.assertEqual(report['screen'][:2], [w, h])
                    self.assertEqual(report['problems'], [])
                    self.assertEqual(report['unnamed'], [])


def luminance(hex_colour):
    channels = [int(hex_colour.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    channels = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class ContrastTests(unittest.TestCase):
    PAIRS = {  # text colour, background, both as used in STYLE / qdesktop
        'body text': ('#0F172A', '#F8FAFC'), 'muted text': ('#526277', '#F8FAFC'), 'muted on card': ('#526277', '#FFFFFF'),
        'table headings': ('#526277', '#F1F5F9'), 'sidebar text': ('#C9D8E7', '#142D4E'), 'sidebar focus': ('#FFFFFF', '#1D3D63'),
        'sidebar current page': ('#FFFFFF', '#264B74'), 'primary button': ('#FFFFFF', '#2563EB'), 'offline badge': ('#0F766E', '#ECFDF5'),
        'error message': ('#B91C1C', '#F8FAFC'), 'selected tab': ('#2563EB', '#FFFFFF'), 'placeholder': (PLACEHOLDER, '#FFFFFF'),
    }

    def test_text_meets_wcag_aa(self):
        for name, (fg, bg) in self.PAIRS.items():
            with self.subTest(name=name):
                self.assertIn(fg.upper(), (Path(qdesktop.__file__).read_text(encoding='utf-8') + '#FFFFFF').upper())  # colour really used
                self.assertGreaterEqual(contrast(fg, bg), 4.5)

    def test_focus_indicators_visible(self):
        self.assertGreaterEqual(contrast('#2563EB', '#FFFFFF'), 3)      # focus ring on white inputs/buttons
        self.assertGreaterEqual(contrast('#FBBF24', '#142D4E'), 3)      # focus ring in the sidebar
        for selector in ('QPushButton#nav:focus', 'QPushButton:focus', 'QLineEdit:focus', 'QCheckBox:focus', 'QTableWidget:focus'):
            self.assertIn(selector, STYLE)


class KeyboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        qdesktop.apply_theme(cls.app)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = ERP(Path(self.tmp.name) / 'a.db')

    def tearDown(self):
        self.s.close(); self.tmp.cleanup()

    def test_first_run_and_sign_in_by_keyboard_only(self):
        done = []
        login = Login(self.s, lambda: done.append(1)); login.show(); login.activateWindow(); self.app.processEvents()
        self.assertTrue(login.fields['username'].hasFocus())
        QTest.keyClicks(login.fields['username'], 'owner'); QTest.keyClick(login.fields['username'], Qt.Key_Tab)
        self.assertTrue(login.fields['password'].hasFocus())
        QTest.keyClicks(login.fields['password'], 'strong-password'); QTest.keyClick(login.fields['password'], Qt.Key_Tab)
        self.assertTrue(login.fields['confirm'].hasFocus())
        QTest.keyClicks(login.fields['confirm'], 'strong-password'); QTest.keyClick(login.fields['confirm'], Qt.Key_Return)
        self.assertEqual(done, [1]); self.assertEqual(self.s.role, 'admin')

    def test_sidebar_and_pages_reachable_by_keyboard(self):
        self.s.bootstrap('owner', 'strong-password', 'strong-password')
        w = Window(self.s); w.show(); w.activateWindow(); self.app.processEvents()
        reached, widget = set(), w.nav[0]
        widget.setFocus(); self.app.processEvents()
        for _ in range(400):                                   # follow the Tab order like a keyboard user
            current = QApplication.focusWidget()
            if current in reached:
                break
            reached.add(current)
            QTest.keyClick(current, Qt.Key_Tab); self.app.processEvents()
        self.assertTrue(all(b in reached for b in w.nav), 'every sidebar entry must be reachable with Tab')
        self.assertIn(w.search, reached)
        w.nav[4].setFocus(); QTest.keyClick(w.nav[4], Qt.Key_Space); self.app.processEvents()
        self.assertEqual(w.current, 4)                            # Space opens the focused page
        QTest.keyClick(w, Qt.Key_F2); self.assertEqual(w.current, 1)
        QTest.keyClick(w, Qt.Key_K, Qt.ControlModifier); self.assertTrue(w.search.hasFocus())
        w.close()

    def test_flow_bar_wraps_instead_of_widening(self):
        from qdesktop import FlowBar
        from PySide6.QtWidgets import QWidget
        host = QWidget(); bar = FlowBar(host)
        for i in range(8):
            bar.addWidget(QPushButton(f'Long action button {i}'))
        one_line = bar.sizeHint().width()
        self.assertLess(bar.minimumSize().width(), one_line / 4)
        self.assertGreater(bar.heightForWidth(300), bar.heightForWidth(one_line) * 3)
        host.resize(300, bar.heightForWidth(300)); host.show(); self.app.processEvents()
        self.assertTrue(all(b.geometry().right() <= 300 for b in host.findChildren(QPushButton)))
        host.close()


if __name__ == '__main__':
    unittest.main()
