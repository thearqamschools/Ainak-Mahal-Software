"""Offline restore utility; launch only after Ainak Mahal has closed."""
import tkinter as tk
from tkinter import filedialog,messagebox
from pathlib import Path
from phase4 import restore_database
root=tk.Tk();root.withdraw()
if messagebox.askyesno('Restore database','Close Ainak Mahal before restoring. Continue?'):
    source=filedialog.askopenfilename(filetypes=[('SQLite database','*.db')])
    if source:
        try:
            safety=restore_database(source,Path.home()/'AinakMahal'/'ainak_mahal.db')
            messagebox.showinfo('Restore complete',f'Database restored. Previous copy: {safety}')
        except Exception as e:messagebox.showerror('Restore failed',str(e))
root.destroy()
