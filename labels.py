"""Local Code 128 product label images; no fonts or online services required."""
from pathlib import Path
from barcode import Code128
from barcode.writer import SVGWriter
from PySide6.QtCore import QByteArray,Qt
from PySide6.QtGui import QImage,QPainter
from PySide6.QtSvg import QSvgRenderer

def barcode_png(code,path):
    if not code or not str(code).isascii():raise ValueError('Use a nonempty ASCII SKU or barcode for Code 128 labels')
    svg=Code128(str(code),writer=SVGWriter()).render({'write_text':False,'quiet_zone':4,'module_height':12})
    renderer=QSvgRenderer(QByteArray(svg))
    if not renderer.isValid():raise ValueError('Could not render this barcode')
    size=renderer.defaultSize()*3;image=QImage(size,QImage.Format_ARGB32);image.fill(Qt.white)
    painter=QPainter(image);renderer.render(painter);painter.end();path=Path(path).resolve();path.parent.mkdir(parents=True,exist_ok=True)
    if not image.save(str(path)):raise OSError('Could not save the product barcode')
    return path
