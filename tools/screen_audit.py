"""Check that every screen fits common shop laptops at Windows scaling 100-150%.

Run one screen per process (Qt's screen is fixed per application):
    QT_QPA_PLATFORM="offscreen:configfile=<screen.json>" python tools/screen_audit.py
Prints a JSON report. test_scaling.py runs it for each supported screen.
"""
import json, os, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from PySide6.QtWidgets import (QApplication, QPushButton, QLineEdit, QComboBox, QSpinBox, QTableWidget, QCheckBox,
                               QScrollArea, QAbstractButton, QFormLayout, QWidget, QDialog, QPlainTextEdit, QTextBrowser)
from PySide6.QtCore import QPoint, Qt

FRAME = 32          # Windows title bar at 100-150% in logical pixels (approx.)
INPUTS = (QLineEdit, QComboBox, QSpinBox, QTableWidget, QCheckBox, QPlainTextEdit)


def problems_in(top, name, area):
    out = []
    lay = top.layout()
    need = lay.totalMinimumSize() if lay else top.minimumSizeHint()
    need_w, need_h = max(need.width(), top.minimumWidth()), max(need.height(), top.minimumHeight())
    if need_w > area.width() or need_h + (0 if top.isMaximized() else FRAME) > area.height():
        out.append(f'{name}: needs at least {need_w}x{need_h + FRAME}, screen gives {area.width()}x{area.height()}')
    frame = 0 if top.isMaximized() else FRAME   # a maximized window's title bar is inside the screen area
    if top.width() > area.width() or top.height() + frame > area.height():
        out.append(f'{name}: opens at {top.width()}x{top.height() + frame}, larger than the screen')
    for b in top.findChildren(QAbstractButton):
        if b.isVisibleTo(top) and b.text() and b.width() + 1 < b.minimumSizeHint().width():
            out.append(f'{name}: button "{b.text()}" is cut off')
    return out


def squashed(top, name):
    """Controls drawn smaller than they need: text or content would be hidden."""
    out = []
    for w in top.findChildren(QWidget):
        if not w.isVisibleTo(top) or w.width() <= 0:
            continue
        need = w.minimumSizeHint()
        # Wrapped text needs a height that depends on the width actually given.
        need_h = w.heightForWidth(w.width()) if w.hasHeightForWidth() and w.heightForWidth(w.width()) > 0 else need.height()
        if isinstance(w, (QAbstractButton, QLineEdit, QComboBox, QSpinBox)) or w.objectName() == 'card':
            if w.height() + 3 < need_h:   # a 1-2 px difference is the stylesheet's fixed input height
                label = getattr(w, 'text', lambda: '')() if isinstance(w, QAbstractButton) else (w.accessibleName() or w.objectName())
                out.append(f'{name}: {type(w).__name__} "{label}" squashed to {w.height()}px high, needs {need_h}px')
        # inside a scroll area that never scrolls sideways, nothing may stick out on the right
        parent = w.parentWidget()
        while parent is not None and parent is not top and not isinstance(parent, QScrollArea):
            parent = parent.parentWidget()
        if isinstance(parent, QScrollArea) and not isinstance(parent, (QTableWidget, QPlainTextEdit, QTextBrowser)) \
                and parent.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff and isinstance(w, QAbstractButton):
            right = w.mapTo(parent.viewport(), QPoint(w.width(), 0)).x()
            if right > parent.viewport().width() + 1:
                out.append(f'{name}: "{w.text()}" is cut off on the right')
    return out


def unreachable(top, name):
    """Every visible control must be on screen, or inside a scroll area that can bring it into view."""
    out = []
    for w in top.findChildren(QWidget):
        if not w.isVisibleTo(top) or not isinstance(w, (QAbstractButton, *INPUTS)):
            continue
        parent, scroller = w.parentWidget(), None
        while parent is not None and parent is not top:
            if isinstance(parent, QScrollArea) and not isinstance(parent, (QTableWidget, QPlainTextEdit, QTextBrowser)):
                scroller = parent
                break
            parent = parent.parentWidget()
        if scroller is not None:
            continue
        pos = w.mapTo(top, QPoint(0, 0))
        if pos.x() + w.width() > top.width() + 1 or pos.y() + w.height() > top.height() + 1 or pos.x() < 0 or pos.y() < 0:
            label = getattr(w, 'text', lambda: '')() if isinstance(w, QAbstractButton) else w.accessibleName()
            out.append(f'{name}: "{label or type(w).__name__}" is outside the window and cannot be scrolled to')
    return out


def unnamed(top, name):
    """Inputs a screen reader would announce without a name."""
    out = []
    for w in top.findChildren(QWidget):
        if not isinstance(w, INPUTS) or not w.isVisibleTo(top) or w.accessibleName() or (isinstance(w, QCheckBox) and w.text()):
            continue
        if isinstance(w, QLineEdit) and isinstance(w.parentWidget(), (QComboBox, QSpinBox)):
            continue
        parent = w.parentWidget()
        lay = parent.layout() if parent else None
        if isinstance(lay, QFormLayout) and lay.labelForField(w) is not None:
            continue
        out.append(f'{name}: {type(w).__name__} has no accessible name')
    return out


def run():
    app = QApplication.instance() or QApplication([])
    substitute = os.environ.get('AINAK_AUDIT_FONT')   # test with a wider font than Segoe UI where Segoe is not installed
    if substitute:
        from PySide6.QtGui import QFont
        QFont.insertSubstitution('Segoe UI', substitute)
    from qdesktop import Window, Login, Form, STYLE, NAV
    app.setStyleSheet(STYLE + os.environ.get('AINAK_AUDIT_EXTRA_STYLE', ''))   # e.g. larger text to stress-test layouts
    from erp import ERP
    from hardware_ui import HardwareCheck, LabelDialog
    from access_recovery_ui import AccessRecovery
    screen = app.primaryScreen()
    area = screen.availableGeometry()
    report = {'screen': [area.width(), area.height(), screen.devicePixelRatio()], 'problems': [], 'unnamed': []}
    tmp = tempfile.mkdtemp()
    s = ERP(Path(tmp) / 'ainak_mahal.db')
    login = Login(s, lambda: None); login.show(); app.processEvents(); app.processEvents()
    report['problems'] += problems_in(login, 'Sign-in (first run)', area) + unreachable(login, 'Sign-in') + squashed(login, 'Sign-in')
    report['unnamed'] += unnamed(login, 'Sign-in')
    login.close()
    s.bootstrap('owner', 'strong-password', 'strong-password')
    cid = s.customer('Customer A', '0300-1234567')
    s.product('F1', 'Frame classic', 1000, 400, 5, 'Frames', '111')
    vendor = s.supplier('Lens House', '0300')
    w = Window(s)
    w.showMaximized() if getattr(w, 'start_maximized', False) else w.show()
    w.resize(min(w.width(), area.width()), min(w.height(), area.height() - FRAME)); app.processEvents()
    report['window'] = [w.width(), w.height(), bool(getattr(w, 'start_maximized', False))]
    report['problems'] += problems_in(w, 'Main window', area)
    for i, page in enumerate(NAV):
        w.show_page(i); app.processEvents(); app.processEvents()
        body = w.area.widget()
        need = body.layout().totalMinimumSize().width() if body.layout() else body.minimumSizeHint().width()
        if need > w.area.viewport().width():
            widest = sorted(((c.minimumSizeHint().width(), type(c).__name__ + ':' + (getattr(c, 'text', lambda: '')() or c.accessibleName() or c.objectName()))
                             for c in body.findChildren(QWidget) if c.isVisibleTo(body)), reverse=True)[:4]
            report['problems'].append(f'{page}: needs {need}px wide, only {w.area.viewport().width()}px visible (sideways scrolling); widest: {widest}')
        report['problems'] += [p for p in problems_in(w, page, area) if 'cut off' in p] + unreachable(w, page) + squashed(w, page)
        report['unnamed'] += unnamed(w, page)
    dialogs = [
        ('Add product form', lambda: Form(w, 'Product', [('sku', 'SKU *'), ('name', 'Item name *'), ('category', 'Category', ('Frames', 'Lenses')),
                                                          ('price', 'Selling price PKR *'), ('cost', 'Purchase cost PKR'), ('qty', 'Opening units'),
                                                          ('barcode', 'Barcode'), ('variant', 'Variant'), ('sph', 'SPH'), ('cyl', 'CYL'),
                                                          ('reorder', 'Reorder level'), ('service', 'Service item', 'check')], lambda v: None)),
        ('Printer & scanner check', lambda: HardwareCheck(w, s)),
        ('Product label', lambda: LabelDialog(w, s, 'Frame classic', '111', 'PKR 1,000')),
        ('Access Recovery', lambda: AccessRecovery(Path(tmp) / 'ainak_mahal.db')),
    ]
    for name, make in dialogs:
        d = make(); d.show(); app.processEvents(); app.processEvents()
        report['problems'] += problems_in(d, name, area) + unreachable(d, name) + squashed(d, name)
        report['unnamed'] += unnamed(d, name)
        d.close()
    w.close(); s.close()
    print(json.dumps(report))


if __name__ == '__main__':
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    run()
