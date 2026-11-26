"""Authenticated, locked, offline recovery shipped in the same executable."""
import sqlite3
import tkinter as tk
from tkinter import filedialog,messagebox,simpledialog
from paths import data_dir,InstanceLock
from phase4 import restore_database,verify_database
import phase3

def main():
    root=tk.Tk();root.withdraw();lock=None
    try:
        lock=InstanceLock(data_dir());live=data_dir()/'ainak_mahal.db'
        if live.exists():
            verify_database(live)
            user=simpledialog.askstring('Recovery administrator','Administrator username',parent=root)
            if user is None:return 0
            password=simpledialog.askstring('Recovery administrator','Password',show='*',parent=root)
            con=sqlite3.connect(live)
            try:
                if phase3.authenticate(con,user,password or '')!='admin':raise PermissionError('Administrator credentials are required')
            finally:con.close()
        source=filedialog.askopenfilename(parent=root,title='Choose verified Ainak Mahal backup',filetypes=[('SQLite backup','*.db *.sqlite3')])
        if not source:return 0
        if not messagebox.askyesno('Restore backup','Replace the current database with this backup? A safety copy will preserve the current data.',parent=root):return 0
        safety=restore_database(source,live)
        messagebox.showinfo('Recovery complete',f'Backup restored.\nPrevious data: {safety or "No previous database"}\nOpen Ainak Mahal and check stock and payments.',parent=root)
        return 0
    except Exception as ex:
        messagebox.showerror('Recovery could not complete',str(ex),parent=root);return 1
    finally:
        if lock:lock.close()
        root.destroy()

if __name__=='__main__':main()
