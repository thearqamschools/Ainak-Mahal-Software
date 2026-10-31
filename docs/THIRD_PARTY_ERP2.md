# Third-party components and replacement instructions

Ainak Mahal 2.0 uses the unmodified Qt for Python Essentials 6.12.0 (PySide6/shiboken6),
dynamically linked in a PyInstaller **onedir** package. It does not use Qt WebEngine,
Qt Quick, cloud APIs or a local web server. Qt/PySide6 licensing and LGPL obligations:
https://doc.qt.io/qtforpython-6/ and https://www.qt.io/development/open-source-lgpl-obligations

The application does not prohibit reverse engineering for debugging modifications to LGPL
components. DLLs remain separate and replaceable in `_internal/PySide6` and related package
folders. Keep an untouched backup, then replace with ABI-compatible unmodified/rebuilt Qt
6.12/PySide6 libraries, or rebuild the application with the replacement wheels using
`tools/build.ps1`. The complete application source, build instructions and exact version
pins are available in this repository and the accompanying source ZIP. Qt source and
corresponding version tags are available from https://code.qt.io/ and
https://download.qt.io/official_releases/QtForPython/pyside6/ . The application does not
modify Qt/PySide6. License texts are copied from the exact installed distributions into
the installer's `licenses` folder; keep them when redistributing the application.

Code 128 encoding: python-barcode 0.16.1, MIT; https://pypi.org/project/python-barcode/0.16.1/
Python: PSF license; Tcl/Tk (recovery and legacy UI): upstream permissive license notices.
PyInstaller: GPL with its bootloader exception, https://pyinstaller.org/ .

Brand artwork and geometric wordmark are original, authored as SVG paths. No proprietary
reference logos, illustrations, fonts or icons are redistributed. Segoe UI is used as an
installed Windows system UI font. It is not copied into the package.

Development-only tools: Pillow 12.0.0 (HPND/Pillow license), resvg-py 0.5.0 (upstream
resvg/MIT-family notices), imageio-ffmpeg 0.6.0 (BSD wrapper; bundled FFmpeg build GPL).
These development tools and the reference media are not application runtime dependencies
and are not bundled in the installer. No external Taste, Motion or Impeccable skill was
installed. Their described design principles were applied directly.

Mathematical optical-calculator references: University of Iowa ophthalmology optics review,
https://webeye.ophth.uiowa.edu/eyeforum/video/Refraction/pdfs/Optics-Review.pdf ;
Punjab Medical Faculty Opticianary textbook, https://pmfpunjab.edu.pk/Downloads/Books/Opticianary-B.pdf .
Calculators convert notation; they do not diagnose or prescribe lenses.
