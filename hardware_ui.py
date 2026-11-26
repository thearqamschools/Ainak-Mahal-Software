"""Label printing window and the in-app Printer & scanner check."""
import json
from PySide6.QtCore import Qt, QEvent, QSize
from PySide6.QtGui import QImage, QPixmap, QColor
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtWidgets import (QDialog, QLabel, QLineEdit, QComboBox, QPushButton, QSpinBox, QCheckBox,
                               QHBoxLayout, QVBoxLayout, QMessageBox, QFileDialog, QGroupBox, QPlainTextEdit, QWidget, QSizePolicy)
import hardware as hw


def label_preview(settings, name, code, price_text, scale=8):
    """Screen preview at `scale` px per mm; uses the same drawing code as the printer."""
    width, height = hw.label_size(settings)
    image = QImage(QSize(width * scale, height * scale), QImage.Format_RGB32)
    image.fill(QColor('white'))
    image.setDotsPerMeterX(scale * 1000)
    image.setDotsPerMeterY(scale * 1000)
    hw.paint_label(image, name, code, price_text, dpi=scale * 25.4)
    return image


def choose_printer(parent, printer, settings, pdf, default_name):
    """Shared print/PDF flow. Returns False when the operator cancels."""
    if pdf:
        path, _ = QFileDialog.getSaveFileName(parent, 'Save PDF', default_name, 'PDF document (*.pdf)')
        if not path:
            return False
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        return True
    warning = hw.apply_printer(printer, settings.get('printer', ''))
    if warning:
        QMessageBox.warning(parent, 'Printer not found', warning)
    return QPrintDialog(printer, parent).exec() == QDialog.Accepted


class LabelDialog(QDialog):
    def __init__(self, parent, service, name, code, price_text):
        super().__init__(parent)
        self.s, self.name, self.code, self.price = service, name, code, price_text
        settings = service.settings()
        self.setWindowTitle('Product label')
        layout = QVBoxLayout(self)
        size = settings.get('label_size', hw.DEFAULT_LABEL)
        layout.addWidget(QLabel(f'<b>{name}</b><br>Label size: {size} (change in Settings & Staff → Edit shop settings)'))
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet('background:white;border:1px solid #CBD5E1;padding:8px')
        from qdesktop import available_area
        area = available_area(parent)
        width_mm, height_mm = hw.label_size(settings)
        scale = max(3, min(8, int((area.height() - 260) / height_mm), int((area.width() - 120) / width_mm)))
        self.preview.setPixmap(QPixmap.fromImage(label_preview(settings, name, code, price_text, scale)))
        self.preview.setAccessibleName('Label preview')
        layout.addWidget(self.preview)
        row = QHBoxLayout()
        row.addWidget(QLabel('Copies'))
        self.copies = QSpinBox()
        self.copies.setRange(1, 500)
        self.copies.setAccessibleName('Number of labels')
        self.copies.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)   # grow with large text instead of clipping
        row.addWidget(self.copies)
        row.addStretch()
        for text, pdf in (('Print labels', False), ('Save PDF', True)):
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, pdf=pdf: self.run(pdf))
            row.addWidget(b)
        close = QPushButton('Close')
        close.clicked.connect(self.accept)
        row.addWidget(close)
        layout.addLayout(row)
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)

    def showEvent(self, event):
        # Styles are applied on first show; re-measure so large text is never clipped.
        super().showEvent(event)
        self.copies.setMinimumHeight(self.copies.minimumSizeHint().height())
        self.adjustSize()

    def run(self, pdf):
        try:
            printer = QPrinter(QPrinter.HighResolution)
            settings = self.s.settings()
            width, height = hw.label_size(settings)
            hw.page_size(printer, width, height, 1.5)
            if not choose_printer(self, printer, settings, pdf, f'label_{self.code}.pdf'):
                return
            hw.print_label(printer, settings, self.name, self.code, self.price, self.copies.value())
        except Exception as ex:
            QMessageBox.warning(self, 'Label could not print', str(ex))


class HardwareCheck(QDialog):
    """Step-by-step acceptance test an operator can run on the real shop printer and scanner."""
    CHECKS = (('a4', 'A4 test page printed clearly; 10 mm marks measure 10 mm'),
              ('receipt', '80 mm test receipt fits the paper; all four box sides visible'),
              ('label', 'Test label printed on the label roll and is not cut off'),
              ('scan_label', 'Scanner read the barcode on the printed test label or receipt'),
              ('scan_product', 'Scanning a real product added the right item in New Sale'))

    def __init__(self, parent, service):
        super().__init__(parent)
        self.s = service
        self.timer = hw.ScanTimer()
        self.last_scan = None
        self.setWindowTitle('Printer & scanner check')
        from qdesktop import fit_to_screen, scrolling
        outer = QVBoxLayout(self)
        content = QWidget()
        layout = QVBoxLayout(content)
        outer.addWidget(scrolling(content), 1)
        fit_to_screen(self, 760, 720)
        intro = QLabel('Run this once on the shop computer after installing, and again after changing a printer or scanner. '
                       'Nothing is sold and no stock changes.')
        intro.setWordWrap(True)
        layout.addWidget(intro)

        box = QGroupBox('1 · Printers')
        b = QVBoxLayout(box)
        settings = service.settings()
        row = QHBoxLayout()
        row.addWidget(QLabel('Printer'))
        self.printer = QComboBox()
        self.printer.setAccessibleName('Printer to test')
        self.printer.addItems(hw.printer_choices(settings.get('printer', '')))
        index = self.printer.findText(settings.get('printer', hw.SYSTEM_DEFAULT))
        self.printer.setCurrentIndex(max(0, index))
        row.addWidget(self.printer, 1)
        b.addLayout(row)
        found = hw.installed_printers()
        self.printer_note = QLabel(f'{len(found)} printer(s) installed in Windows.' if found else
                                   'No printers are installed in Windows. Install the printer driver first (Windows Settings → Printers & scanners).')
        self.printer_note.setWordWrap(True)
        b.addWidget(self.printer_note)
        row = QHBoxLayout()
        for text, kind in (('Print A4 test page', 'A4'), ('Print 80 mm test receipt', '80 mm'), ('Print test label', 'label')):
            button = QPushButton(text)
            button.clicked.connect(lambda _=False, kind=kind: self.print_test(kind))
            row.addWidget(button)
        b.addLayout(row)
        layout.addWidget(box)

        box = QGroupBox('2 · Barcode scanner')
        b = QVBoxLayout(box)
        b.addWidget(QLabel(f'Click the box, then scan the test barcode ({hw.TEST_CODE}) from the printed page or label.'))
        self.scan = QLineEdit()
        self.scan.setAccessibleName('Scanner test input')
        self.scan.setPlaceholderText('Scan here')
        self.scan.installEventFilter(self)
        self.scan.textEdited.connect(lambda _text: self.timer.key())
        self.scan.returnPressed.connect(lambda: self.finish_scan('Enter'))
        b.addWidget(self.scan)
        self.scan_result = QPlainTextEdit()
        self.scan_result.setReadOnly(True)
        self.scan_result.setMaximumHeight(110)
        self.scan_result.setAccessibleName('Scanner test result')
        b.addWidget(self.scan_result)
        layout.addWidget(box)

        box = QGroupBox('3 · Confirm what you saw')
        b = QVBoxLayout(box)
        self.ticks = {}
        for key, text in self.CHECKS:
            tick = QCheckBox(text)
            self.ticks[key] = tick
            b.addWidget(tick)
        self.note = QLineEdit()
        self.note.setPlaceholderText('Printer / scanner model and any problem seen (optional)')
        self.note.setAccessibleName('Check notes')
        b.addWidget(self.note)
        layout.addWidget(box)
        row = QHBoxLayout()
        outer.addLayout(row)
        row.addStretch()
        save = QPushButton('Save check result')
        save.setObjectName('primary')
        save.clicked.connect(self.save)
        close = QPushButton('Close')
        close.clicked.connect(self.reject)
        row.addWidget(close)
        row.addWidget(save)
        # A scanner ends every code with Enter. No button may react to it, or a scan would start printing.
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
            button.setDefault(False)
        last = service.hardware_check_last()
        if last:
            layout.addWidget(QLabel(f'Last saved check: {last.get("result", "?")} on {last.get("at", "?")} by {last.get("by", "?")}'))

    def eventFilter(self, obj, event):
        if obj is self.scan and event.type() == QEvent.KeyPress and event.key() == Qt.Key_Tab:
            self.finish_scan('Tab')
            return True
        return super().eventFilter(obj, event)

    def finish_scan(self, suffix):
        text = self.scan.text()
        result = self.timer.finish(text, suffix)
        product = self.s.find_code(text) if text.strip() else None
        if product is not None:
            row = next((r for r in self.s.products() if r[0] == product), None)
            if row:
                result['product'] = row[2]
        self.last_scan = result
        lines = [f'Received: "{text}"  ({result["chars"]} characters in {result["seconds"]:.2f} s, suffix: {suffix})',
                 hw.scan_advice(result)]
        if result.get('product'):
            lines.append(f'This is the barcode of product: {result["product"]}')
        self.scan_result.setPlainText('\n'.join(l for l in lines if l))
        if result['matches_test'] and suffix == 'Enter':
            self.ticks['scan_label'].setChecked(True)
        self.scan.clear()
        self.scan.setFocus()

    def selected_printer_settings(self):
        settings = dict(self.s.settings())
        settings['printer'] = self.printer.currentText()
        return settings

    def print_test(self, kind, pdf=False):
        try:
            printer = QPrinter(QPrinter.HighResolution)
            settings = self.selected_printer_settings()
            if kind == 'label':
                width, height = hw.label_size(settings)
                hw.page_size(printer, width, height, 1.5)
            if not choose_printer(self, printer, settings, pdf, f'ainak_mahal_{kind.replace(" ", "")}_test.pdf'):
                return
            if kind == 'label':
                hw.print_label(printer, settings, 'Ainak Mahal test label', hw.TEST_CODE, 'PKR 0')
            else:
                hw.print_test_page(printer, kind)
        except Exception as ex:
            QMessageBox.warning(self, 'Test print failed', str(ex))

    def summary(self):
        passed = {key: tick.isChecked() for key, tick in self.ticks.items()}
        return {'result': 'PASS' if all(passed.values()) else 'INCOMPLETE', 'checks': passed,
                'printer': self.printer.currentText(), 'label_size': self.s.settings().get('label_size', hw.DEFAULT_LABEL),
                'receipt_format': self.s.settings().get('receipt_format', 'A4'), 'scan': self.last_scan, 'note': self.note.text().strip()}

    def save(self):
        data = self.summary()
        try:
            self.s.save_hardware_check(data)
        except Exception as ex:
            QMessageBox.warning(self, 'Could not save', str(ex))
            return
        missing = [text for key, text in self.CHECKS if not data['checks'][key]]
        QMessageBox.information(self, 'Check saved',
                                'All checks passed. The printer and scanner are ready for trading.' if not missing else
                                'Saved as incomplete. Still to confirm:\n• ' + '\n• '.join(missing))
        self.accept()
