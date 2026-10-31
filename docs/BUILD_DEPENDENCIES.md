# Build dependency review

The runtime uses only Python's standard library, SQLite and Tcl/Tk. No external design
skill was installed: Taste, Emil Kowalski Motion and Impeccable were unavailable in the
installed catalog, so their requested principles were applied directly (see BUILD_PLAN.md).

Build tools are pinned in `requirements-build.txt`. PyInstaller is obtained from PyPI and
uses its normal bootloader exception for packaged applications. CPython ships under the
PSF license; Tcl/Tk use their upstream permissive licenses. Preserve the bundled license
files with redistributions. The repository's original code has no declared general license;
this change does not grant a new license to third parties.

Primary upstream references verified during implementation:

* https://pypi.org/project/pyinstaller/ — Windows packaging and Python support.
* https://pyinstaller.org/ — packaging documentation and licensing exception.
* https://www.python.org/downloads/windows/ — official Windows Python distributions.
* https://github.com/actions/checkout/releases — checkout v7.0.1.
* https://github.com/actions/setup-python/releases — setup-python v7.1.0.
* https://github.com/actions/upload-artifact/releases — upload-artifact v7.0.2.
* https://jrsoftware.org/isinfo.php — Inno Setup compiler.

The local Python 3.14.8 installation lacked discoverable Tcl data. Matching Tcl/Tk 9.0.4
data was extracted from the official python.org 3.14.8 tcltk.msi into the workspace and
provided to the build through TCL_LIBRARY/TK_LIBRARY. No system runtime files were
overwritten. A separately downloaded CPython installer had a valid Python Software
Foundation Authenticode signature; no external skills or scripts were executed from it.
The packaged smoke check clears those environment variables to verify bundled Tcl data.
CI uses the complete Python runtime from actions/setup-python and needs no local workaround.
