"""Ship dependency licenses, exact version inventory and rebuild instructions."""
import importlib.metadata as md
import shutil,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
dest=root/'dist'/'AinakMahal'/'licenses';dest.mkdir(parents=True,exist_ok=True)
versions=[]
for name in ('PySide6-Essentials','shiboken6','python-barcode','pyinstaller'):
    dist=md.distribution(name);versions.append(f'{name}=={dist.version}')
    for file in dist.files or []:
        if any(word in str(file).lower() for word in ('license','copying','copyright','notice')):
            source=Path(dist.locate_file(file))
            if source.is_file():
                target=dest/name/str(file);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
python_license=Path(sys.base_prefix)/'LICENSE.txt'
if python_license.exists():shutil.copy2(python_license,dest/'PYTHON_LICENSE.txt')
(dest/'VERSIONS.txt').write_text('\n'.join(versions),encoding='utf-8')
shutil.copy2(root/'docs'/'THIRD_PARTY_ERP2.md',dest/'README.md')
