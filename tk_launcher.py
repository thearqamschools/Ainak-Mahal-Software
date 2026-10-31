"""Packaged entry point; no database is touched until main() runs."""
import sys
import tkinter as tk
from tkinter import messagebox
from paths import data_dir, InstanceLock
from retail import Retail
from desktop import Desktop, sign_in

def main():
    if '--smoke-test' in sys.argv:
        from smoke_test import run
        return run()
    if '--restore' in sys.argv:
        from recovery import main as recover
        return recover()
    root=tk.Tk();service=None;lock=None
    try:
        lock=InstanceLock(data_dir())
        service=Retail(data_dir()/'ainak_mahal.db')
        sign_in(root,service,lambda:Desktop(root,service))
        root.mainloop()
    except Exception as ex:
        messagebox.showerror('Ainak Mahal could not start',str(ex),parent=root)
        root.destroy()
        return 1
    finally:
        if service:
            try:service.close()
            except Exception:pass
        if lock:lock.close()
    return 0

if __name__=='__main__':sys.exit(main())
