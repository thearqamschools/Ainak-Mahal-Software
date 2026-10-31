"""Offline Qt desktop entry point and frozen application launcher."""
import sys
from PySide6.QtWidgets import QApplication,QMessageBox
from paths import data_dir,InstanceLock
from erp import ERP
from qdesktop import Window,Login,STYLE

def main():
    app=QApplication.instance() or QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLE);app.setApplicationName('Ainak Mahal')
    if '--smoke-test' in sys.argv:
        from qt_smoke import run
        return run(app)
    if '--restore' in sys.argv:
        from recovery import main as recover
        return recover()
    service=None;lock=None;windows=[]
    try:
        lock=InstanceLock(data_dir());service=ERP(data_dir()/'ainak_mahal.db')
        def signed_in():
            window=Window(service);windows.append(window);window.show()
        login=Login(service,signed_in);windows.append(login);login.show();return app.exec()
    except Exception as ex:QMessageBox.critical(None,'Ainak Mahal could not start',str(ex));return 1
    finally:
        if service:service.close()
        if lock:lock.close()

if __name__=='__main__':sys.exit(main())
