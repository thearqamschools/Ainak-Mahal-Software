"""Printer and barcode-scanner support that works on real shop hardware.

* Labels are drawn straight onto the printer with QPainter. Each Code 128 bar
  is a whole number of printer dots wide, so thermal 203/300 dpi printers print
  sharp, scannable bars instead of a resampled picture.
* Label, receipt and test-page sizes are explicit millimetre page sizes.
* Scanner input is matched exactly (barcode, then SKU) so one scan never adds
  the wrong product because its code is part of another code or a name.
"""
import time
from barcode import Code128
from PySide6.QtCore import QRectF, QSizeF, QMarginsF, Qt
from PySide6.QtGui import QPainter, QPageSize, QPageLayout, QFont, QPen, QColor
from PySide6.QtPrintSupport import QPrinter, QPrinterInfo

SYSTEM_DEFAULT = 'System default'
LABEL_SIZES = {'50 × 25 mm': (50, 25), '38 × 25 mm': (38, 25), '60 × 40 mm': (60, 40), '80 × 60 mm': (80, 60)}
DEFAULT_LABEL = '80 × 60 mm'          # unchanged from 2.0.2 so existing shops print the same size
RECEIPT_KINDS = ('Invoice', 'Job')    # documents that follow the 80 mm receipt setting
TEST_CODE = 'AM-TEST-2468'
QUIET_MODULES = 10                    # Code 128 needs at least 10 modules of white each side


def installed_printers():
    try:
        return list(QPrinterInfo.availablePrinterNames())
    except Exception:
        return []


def printer_choices(current=''):
    names = [SYSTEM_DEFAULT] + installed_printers()
    if current and current not in names:
        names.append(current)       # keep a saved name visible even while that printer is unplugged
    return tuple(names)


def apply_printer(printer, preferred):
    """Select the saved printer. Returns a warning when it is not installed now."""
    if not preferred or preferred == SYSTEM_DEFAULT:
        return ''
    if preferred not in installed_printers():
        return (f'The saved printer "{preferred}" is not installed or not switched on. '
                'Choose a printer in the next window, or update Settings & Staff → Edit shop settings.')
    printer.setPrinterName(preferred)
    return ''


def page_size(printer, width_mm, height_mm, margin_mm):
    printer.setPageSize(QPageSize(QSizeF(width_mm, height_mm), QPageSize.Millimeter, '', QPageSize.ExactMatch))
    # The size is given exactly as the roll feeds (width × height). Never rotate it: a landscape
    # orientation would swap the sides and squeeze a 38 mm-wide label into 25 mm.
    printer.setPageOrientation(QPageLayout.Portrait)
    printer.setPageMargins(QMarginsF(margin_mm, margin_mm, margin_mm, margin_mm), QPageLayout.Millimeter)


def label_size(settings):
    return LABEL_SIZES.get(settings.get('label_size', DEFAULT_LABEL), LABEL_SIZES[DEFAULT_LABEL])


def modules(code):
    code = str(code or '')
    if not code or not code.isascii() or not code.isprintable():
        raise ValueError('Use a non-empty barcode or SKU with plain English letters, numbers and symbols for Code 128 labels')
    return Code128(code).build()[0]


def draw_barcode(painter, rect, code, dots_per_mm):
    """Draw bars into rect (device units). Returns the module width in dots."""
    bars = modules(code)
    total = len(bars) + 2 * QUIET_MODULES
    module = int(rect.width() // total)
    if module < 1 or module / dots_per_mm < 0.12:
        raise ValueError(f'"{code}" is too long for this label size. Use a shorter barcode or a wider label.')
    left = rect.left() + (rect.width() - module * total) / 2 + QUIET_MODULES * module
    painter.save()
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor('black'))
    x = left
    run = 0
    for i, bit in enumerate(bars + '0'):
        if bit == '1':
            run += 1
            continue
        if run:
            painter.drawRect(QRectF(x + (i - run) * module, rect.top(), run * module, rect.height()))
            run = 0
    painter.restore()
    return module


def paint_label(printer_or_device, name, code, price_text, dpi=None):
    """Print one product label sized to the page. Text shrinks to fit small labels."""
    painter = QPainter()
    if not painter.begin(printer_or_device):
        raise RuntimeError('The printer could not start. Check it is on, has labels loaded and is not paused.')
    try:
        page = (printer_or_device.pageLayout().paintRectPixels(printer_or_device.resolution())
                if isinstance(printer_or_device, QPrinter) else printer_or_device.rect())
        dpi = dpi or (printer_or_device.resolution() if isinstance(printer_or_device, QPrinter) else printer_or_device.logicalDpiX())
        dots_per_mm = dpi / 25.4
        w, h = page.width(), page.height()
        gap = 0.06 * h
        text_h = 0.18 * h
        font = QFont('Segoe UI')
        font.setPixelSize(max(6, int(text_h * 0.8)))
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor('black'))
        painter.drawText(QRectF(0, 0, w, text_h), Qt.AlignHCenter | Qt.AlignVCenter | Qt.TextSingleLine,
                         painter.fontMetrics().elidedText(str(name), Qt.ElideRight, int(w)))
        bars = QRectF(0, text_h + gap, w, h - 2 * (text_h + gap))
        module = draw_barcode(painter, bars, code, dots_per_mm)
        font.setBold(False)
        painter.setFont(font)
        bottom = f'{code}   {price_text}'.strip()
        painter.drawText(QRectF(0, h - text_h, w, text_h), Qt.AlignHCenter | Qt.AlignVCenter | Qt.TextSingleLine,
                         painter.fontMetrics().elidedText(bottom, Qt.ElideRight, int(w)))
        return module
    finally:
        painter.end()


def print_label(printer, settings, name, code, price_text, copies=1):
    width, height = label_size(settings)
    page_size(printer, width, height, 1.5)
    printer.setCopyCount(max(1, int(copies)))
    return paint_label(printer, name, code, price_text)


def paint_test_page(printer, title, width_mm):
    """Rulers and edge marks so the operator can see scaling and cut-off at a glance."""
    painter = QPainter()
    if not painter.begin(printer):
        raise RuntimeError('The printer could not start. Check it is on, has paper and is not paused.')
    try:
        dpmm = printer.resolution() / 25.4
        rect = printer.pageLayout().paintRectPixels(printer.resolution())
        w = rect.width()
        pen = QPen(QColor('black'))
        pen.setWidth(max(1, int(dpmm * 0.3)))
        painter.setPen(pen)
        painter.drawRect(0, 0, w - 1, rect.height() - 1)
        font = QFont('Segoe UI')
        font.setPixelSize(int(dpmm * (5 if width_mm > 100 else 3.2)))
        font.setBold(True)
        painter.setFont(font)
        y = dpmm * 4
        painter.drawText(QRectF(0, y, w, dpmm * 8), Qt.AlignHCenter, 'AINAK MAHAL · ' + title)
        font.setBold(False)
        painter.setFont(font)
        y += dpmm * 10
        lines = ['If this text and the ruler print clearly, the printer works.',
                 'Each long ruler mark is 10 mm. Measure it: it should be exactly 10 mm.',
                 'All four sides of the box should be visible.']
        for line in lines:
            painter.drawText(QRectF(dpmm * 2, y, w - dpmm * 4, dpmm * 12), Qt.TextWordWrap, line)
            y += dpmm * (9 if width_mm > 100 else 11)
        ruler_mm = int(min(width_mm - 12, 150))
        x0 = dpmm * 3
        for mm in range(ruler_mm + 1):
            tall = dpmm * (6 if mm % 10 == 0 else 3 if mm % 5 == 0 else 1.5)
            painter.drawLine(int(x0 + mm * dpmm), int(y), int(x0 + mm * dpmm), int(y + tall))
        painter.drawText(QRectF(x0, y + dpmm * 7, w, dpmm * 6), f'0 … {ruler_mm} mm')
        y += dpmm * 16
        draw_barcode(painter, QRectF(dpmm * 2, y, min(w - dpmm * 4, dpmm * 70), dpmm * 14), TEST_CODE, dpmm)
        painter.drawText(QRectF(0, y + dpmm * 15, w, dpmm * 6), Qt.AlignHCenter,
                         f'Scan this test barcode: {TEST_CODE}')
    finally:
        painter.end()


def print_test_page(printer, kind):
    if kind == 'A4':
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setPageOrientation(QPageLayout.Portrait)
        printer.setPageMargins(QMarginsF(10, 10, 10, 10), QPageLayout.Millimeter)
        paint_test_page(printer, 'A4 printer test', 190)
    elif kind == '80 mm':
        page_size(printer, 80, 120, 4)
        paint_test_page(printer, '80 mm receipt test', 72)
    else:
        raise ValueError('Choose A4 or 80 mm')


def find_scanned(db, scanned):
    """Exact barcode first, then exact SKU (ignoring letter case). Returns product id or None."""
    code = scanned.strip()
    if not code:
        return None
    row = db.execute('SELECT product_id FROM product_details WHERE barcode=?', (code,)).fetchone()
    if row:
        return row[0]
    rows = db.execute('SELECT id FROM products WHERE sku=? COLLATE NOCASE', (code,)).fetchall()
    return rows[0][0] if len(rows) == 1 else None


class ScanTimer:
    """Tells a scanner from hand typing and reports the suffix key the scanner sends."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.reset()

    def reset(self):
        self.first = self.last = None
        self.count = 0

    def key(self):
        now = self.clock()
        if self.first is None:
            self.first = now
        self.last = now
        self.count += 1

    def finish(self, text, suffix):
        seconds = (self.last - self.first) if self.first is not None and self.count > 1 else 0.0
        rate = (self.count - 1) / seconds if seconds > 0 else float('inf') if self.count > 1 else 0.0
        result = {'text': text, 'chars': len(text), 'seconds': round(seconds, 3), 'suffix': suffix,
                  'scanner_speed': rate >= 25, 'matches_test': text.strip() == TEST_CODE}
        self.reset()
        return result


def scan_advice(result):
    lines = []
    if result['suffix'] == 'Enter':
        lines.append('Scanner sends Enter after each code: correct for Ainak Mahal.')
    elif result['suffix'] == 'Tab':
        lines.append('Scanner sends Tab, not Enter. Scan the "Enter / CR suffix" setup code in the scanner manual.')
    if result['text'] != result['text'].strip():
        lines.append('Extra spaces were received. They are ignored when selling, but check the scanner prefix/suffix setup.')
    if result['chars'] and not result['scanner_speed']:
        lines.append('This looked like typing by hand. Scan again with the scanner to confirm its speed.')
    if result['text'] and not result['matches_test'] and result['text'].strip().upper() == TEST_CODE.upper():
        lines.append('Letters came through in the wrong case. Turn Caps Lock off and set the scanner to USB keyboard (US) mode.')
    elif result['text'] and not result['matches_test']:
        lines.append(f'Expected {TEST_CODE}. If this is a product barcode, that is fine; otherwise check the scanner keyboard language.')
    if result['matches_test'] and result['suffix'] == 'Enter':
        lines.append('PASS: the test barcode was read exactly.')
    return '\n'.join(lines)
