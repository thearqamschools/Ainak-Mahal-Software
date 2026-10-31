"""Reject unrelated ICU libraries captured from a development tool's PATH."""
from pathlib import Path
import pefile

root=Path(__file__).resolve().parents[1]/'dist'/'AinakMahal'
for path in root.rglob('icuuc.dll'):
    pe=pefile.PE(str(path),fast_load=True,max_symbol_exports=100000)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT']])
    symbols={item.name for item in pe.DIRECTORY_ENTRY_EXPORT.symbols}
    if b'ucnv_open' not in symbols:
        raise RuntimeError(f'Incompatible ICU captured in bundle: {path}. Qt needs the Windows ICU API, not a version-suffixed third-party ICU build.')
for filename in ('QtCore.pyd','QtGui.pyd','QtWidgets.pyd','Qt6Core.dll','Qt6Gui.dll','Qt6Widgets.dll'):
    if not (root/'_internal'/'PySide6'/filename).exists():raise RuntimeError('Missing packaged Qt component: '+filename)
if any(root.rglob('Qt6WebEngineCore.dll')):raise RuntimeError('Unexpected web runtime in offline desktop bundle')
print('PASS: Qt components present, no WebEngine, ICU ABI is compatible or supplied by Windows.')
