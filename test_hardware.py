import os, re, tempfile, unittest
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QColor, QPageLayout
from PySide6.QtTest import QTest
from PySide6.QtPrintSupport import QPrinter
import hardware as hw
from erp import ERP
from qdesktop import Window, STYLE

MM_TO_PT = 72 / 25.4


def decode_row(image, y):
    """Read bars back from a rendered image row, the way a scanner would."""
    row = [image.pixelColor(x, y).lightness() < 128 for x in range(image.width())]
    first, last = row.index(True), len(row) - 1 - row[::-1].index(True)
    runs, current, length = [], row[first], 0
    for dark in row[first:last + 1]:
        if dark == current:
            length += 1
        else:
            runs.append((current, length)); current, length = dark, 1
    runs.append((current, length))
    module = min(l for _, l in runs)
    bits = ''.join(('1' if dark else '0') * round(l / module) for dark, l in runs)
    quiet_left = first / module
    quiet_right = (len(row) - 1 - last) / module
    return bits, module, quiet_left, quiet_right


def render(settings, name, code, dpi=203):
    w, h = hw.label_size(settings)
    image = QImage(round(w / 25.4 * dpi), round(h / 25.4 * dpi), QImage.Format_RGB32)
    image.fill(QColor('white'))
    hw.paint_label(image, name, code, 'PKR 1,500', dpi=dpi)
    return image


def media_box(pdf_path):
    data = Path(pdf_path).read_bytes()
    m = re.search(rb'/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]', data)
    return float(m.group(1)) / MM_TO_PT, float(m.group(2)) / MM_TO_PT


class BarcodeAndPrintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_label_bars_decode_exactly_on_thermal_printers(self):
        for size in hw.LABEL_SIZES:
            for dpi in (203, 300):
                for code in ('8964000123457', 'FR-1023', hw.TEST_CODE):
                    with self.subTest(size=size, dpi=dpi, code=code):
                        image = render({'label_size': size}, 'Ray frame black', code, dpi)
                        bits, module, left, right = decode_row(image, image.height() // 2)
                        self.assertEqual(bits, hw.modules(code))
                        self.assertGreaterEqual(left, hw.QUIET_MODULES - 0.01)
                        self.assertGreaterEqual(right, hw.QUIET_MODULES - 0.01)
                        self.assertGreaterEqual(module / (dpi / 25.4), 0.12)

    def test_code_too_long_for_small_label_is_refused_clearly(self):
        with self.assertRaisesRegex(ValueError, 'too long for this label size'):
            render({'label_size': '38 × 25 mm'}, 'X', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ-0123456789')

    def test_invalid_codes_refused(self):
        for code in ('', 'عینک', 'tab\tcode'):
            with self.subTest(code=code), self.assertRaises(ValueError):
                hw.modules(code)

    def test_label_pdf_has_exact_label_size_and_copies(self):
        for size, (w, h) in hw.LABEL_SIZES.items():
            with self.subTest(size=size):
                path = Path(self.tmp.name) / f'{w}x{h}.pdf'
                p = QPrinter(QPrinter.HighResolution); p.setOutputFormat(QPrinter.PdfFormat); p.setOutputFileName(str(path))
                hw.print_label(p, {'label_size': size}, 'Frame', 'FR-1', 'PKR 900', copies=3)
                self.assertEqual(p.copyCount(), 3)
                pw, ph = media_box(path)
                self.assertAlmostEqual(pw, w, delta=0.6)   # same orientation as the label roll
                self.assertAlmostEqual(ph, h, delta=0.6)
                printable = p.pageLayout().paintRect(QPageLayout.Millimeter)
                self.assertAlmostEqual(printable.width(), w - 3, delta=0.6)
        for size in hw.LABEL_SIZES:
            with self.subTest(size=size, printer='1200 dpi'):
                p = QPrinter(QPrinter.HighResolution); p.setOutputFormat(QPrinter.PdfFormat); p.setOutputFileName(str(Path(self.tmp.name) / 't.pdf'))
                hw.print_label(p, {'label_size': size}, 'Test', hw.TEST_CODE, 'PKR 0')

    def test_test_pages_print_to_pdf(self):
        for kind, width in (('A4', 210), ('80 mm', 80)):
            with self.subTest(kind=kind):
                path = Path(self.tmp.name) / f'{kind}.pdf'
                p = QPrinter(QPrinter.HighResolution); p.setOutputFormat(QPrinter.PdfFormat); p.setOutputFileName(str(path))
                hw.print_test_page(p, kind)
                self.assertGreater(path.stat().st_size, 1000)
                self.assertAlmostEqual(media_box(path)[0], width, delta=0.6)

    def test_missing_saved_printer_warns_instead_of_failing_silently(self):
        p = QPrinter()
        self.assertEqual(hw.apply_printer(p, hw.SYSTEM_DEFAULT), '')
        self.assertEqual(hw.apply_printer(p, ''), '')
        self.assertIn('not installed', hw.apply_printer(p, 'Unplugged Thermal 80'))
        with patch.object(hw, 'installed_printers', return_value=['Shop Thermal']):
            self.assertEqual(hw.apply_printer(p, 'Shop Thermal'), '')
            self.assertEqual(hw.printer_choices('Old'), (hw.SYSTEM_DEFAULT, 'Shop Thermal', 'Old'))


class ScannerLogicTests(unittest.TestCase):
    def scan(self, text, suffix='Enter', step=0.01):
        clock = iter([i * step for i in range(len(text) + 1)])
        timer = hw.ScanTimer(clock=lambda: next(clock))
        for _ in text:
            timer.key()
        return timer.finish(text, suffix)

    def test_fast_exact_enter_scan_passes(self):
        result = self.scan(hw.TEST_CODE)
        self.assertTrue(result['scanner_speed'] and result['matches_test'])
        self.assertIn('PASS', hw.scan_advice(result))

    def test_tab_suffix_slow_typing_and_wrong_case_get_advice(self):
        self.assertIn('sends Tab', hw.scan_advice(self.scan(hw.TEST_CODE, 'Tab')))
        self.assertIn('typing by hand', hw.scan_advice(self.scan(hw.TEST_CODE, step=0.4)))
        self.assertIn('Caps Lock', hw.scan_advice(self.scan(hw.TEST_CODE.lower())))
        self.assertNotIn('PASS', hw.scan_advice(self.scan('AM-TEST-246')))


class ShopWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([]); cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.s = ERP(Path(self.tmp.name) / 'shop.db')
        self.s.bootstrap('owner', 'strong-password', 'strong-password')
        self.a = self.s.product('SKU-A', 'Frame 123 Classic', 1000, 400, 5, 'Frames', '123')
        self.b = self.s.product('SKU-B', 'Lens', 2000, 900, 5, 'Lenses', '1234')
        self.c = self.s.product('ab-77', 'Case', 300, 100, 5, 'Accessories', '')
        self.w = Window(self.s); self.errors = []
        def safe(f):
            try: f()
            except Exception as ex: self.errors.append(ex)
        self.w.safe = safe; self.w.show(); self.app.processEvents()

    def tearDown(self):
        self.w.cart = []; self.w.close(); self.app.processEvents(); self.s.close(); self.tmp.cleanup()

    def scan(self, code):
        self.w.show_page(1); self.w.scan.setFocus(); QTest.keyClicks(self.w.scan, code); QTest.keyClick(self.w.scan, Qt.Key_Return)

    def test_exact_barcode_wins_over_partial_matches(self):
        self.scan('123'); self.assertEqual(self.w.cart, [(self.a, 1)]); self.assertEqual(self.errors, [])
        self.scan('1234'); self.assertEqual(self.w.cart, [(self.a, 1), (self.b, 1)])
        self.scan(' 123 '); self.assertEqual(dict(self.w.cart)[self.a], 2)

    def test_sku_scan_ignores_case_and_unknown_code_is_explained(self):
        self.scan('AB-77'); self.assertEqual(self.w.cart, [(self.c, 1)])
        self.scan('9999')
        self.assertRegex(str(self.errors[-1]), 'No product has the barcode or SKU "9999"')
        self.assertEqual(self.w.cart, [(self.c, 1)])

    def test_find_code(self):
        self.assertEqual(self.s.find_code('123'), self.a)
        self.assertEqual(self.s.find_code('sku-b'), self.b)
        self.assertIsNone(self.s.find_code('12'))
        self.assertIsNone(self.s.find_code('  '))

    def test_label_size_setting_validated(self):
        self.s.save_settings({'label_size': '50 × 25 mm'})
        self.assertEqual(hw.label_size(self.s.settings()), (50, 25))
        with self.assertRaisesRegex(ValueError, 'label size'):
            self.s.save_settings({'label_size': '10 × 10 mm'})

    def test_80mm_receipts_cover_jobs_and_shrink_logo(self):
        sale = self.s.checkout([(self.a, 1)], None, 1000)
        sale = sale[0] if isinstance(sale, tuple) else sale
        self.s.save_settings({'receipt_format': '80 mm'})
        content = self.s.print_document('Invoice', sale, Path(self.tmp.name)).read_text(encoding='utf-8')
        self.assertIn('width="170"', content); self.assertIn('max-width:72mm', content)
        self.s.save_settings({'receipt_format': 'A4'})
        content = self.s.print_document('Invoice', sale, Path(self.tmp.name)).read_text(encoding='utf-8')
        self.assertIn('width="290"', content); self.assertNotIn('max-width:72mm', content)

    def test_label_dialog_previews_and_prints_pdf(self):
        from hardware_ui import LabelDialog
        d = LabelDialog(self.w, self.s, 'Frame 123 Classic', '123', 'PKR 1,000')
        self.assertFalse(d.preview.pixmap().isNull())
        out = Path(self.tmp.name) / 'label.pdf'
        with patch('hardware_ui.QFileDialog.getSaveFileName', return_value=(str(out), '')):
            d.copies.setValue(2); d.run(True)
        self.assertGreater(out.stat().st_size, 500)
        d.close()

    def test_hardware_check_scan_and_saved_acceptance(self):
        from hardware_ui import HardwareCheck
        d = HardwareCheck(self.w, self.s); d.show(); self.app.processEvents()
        with patch('hardware_ui.QPrintDialog') as print_dialog, patch('hardware_ui.QFileDialog') as file_dialog:
            d.scan.setFocus(); QTest.keyClicks(d.scan, hw.TEST_CODE); QTest.keyClick(d.scan, Qt.Key_Return)
        print_dialog.assert_not_called(); file_dialog.getSaveFileName.assert_not_called()  # Enter must never start printing
        self.assertTrue(d.isVisible())
        self.assertIn('PASS', d.scan_result.toPlainText())
        self.assertTrue(d.ticks['scan_label'].isChecked())
        QTest.keyClicks(d.scan, '1234'); QTest.keyClick(d.scan, Qt.Key_Tab)
        self.assertIn('sends Tab', d.scan_result.toPlainText())
        self.assertIn('Lens', d.scan_result.toPlainText())
        with patch('hardware_ui.QMessageBox.information') as info:
            d.save()
        self.assertIn('incomplete', info.call_args[0][2])
        self.assertEqual(self.s.hardware_check_last()['result'], 'INCOMPLETE')
        d = HardwareCheck(self.w, self.s)
        for tick in d.ticks.values(): tick.setChecked(True)
        d.note.setText('BlackCopper 80 mm, Zebra GC420t, Honeywell 1250g')
        with patch('hardware_ui.QMessageBox.information'):
            d.save()
        last = self.s.hardware_check_last()
        self.assertEqual((last['result'], last['by']), ('PASS', 'owner'))
        self.assertEqual(self.s.scalar("SELECT COUNT(*) FROM audit_events WHERE action='hardware_check_pass'"), 1)

    def test_hardware_check_test_print_to_pdf(self):
        from hardware_ui import HardwareCheck
        d = HardwareCheck(self.w, self.s)
        for kind in ('A4', '80 mm', 'label'):
            out = Path(self.tmp.name) / f'{kind.replace(" ", "")}.pdf'
            with patch('hardware_ui.QFileDialog.getSaveFileName', return_value=(str(out), '')), \
                 patch('hardware_ui.QMessageBox.warning') as warn:
                d.print_test(kind, pdf=True)
            warn.assert_not_called()
            self.assertGreater(out.stat().st_size, 500)

    def test_cashier_cannot_open_hardware_check(self):
        self.s.create_user('staff', 'staff-password', 'cashier'); self.s.actor = self.s.role = None
        self.s.login('staff', 'staff-password')
        with self.assertRaises(PermissionError):
            self.s.save_hardware_check({'result': 'PASS'})


if __name__ == '__main__':
    unittest.main()
