"""Login gate for Ainak Mahal. Run this instead of app.py."""
import tkinter as tk
from tkinter import ttk,messagebox
from pathlib import Path
import sys
from core import Store
import phase4,phase3,phase6
DATA=Path.home()/'AinakMahal';DATA.mkdir(exist_ok=True)
store=Store(DATA/'ainak_mahal.db');phase6.init(store.db)
root=tk.Tk();root.title('Ainak Mahal | Secure Login');root.geometry('410x320');root.resizable(False,False)
frame=ttk.Frame(root,padding=24);frame.pack(fill='both',expand=True)
ttk.Label(frame,text='AINAK MAHAL',font=('Segoe UI',20,'bold')).pack(pady=(0,14))
ttk.Label(frame,text='Username').pack(anchor='w');username=ttk.Entry(frame);username.pack(fill='x',pady=4)
ttk.Label(frame,text='Password (minimum 10 characters for new users)').pack(anchor='w');password=ttk.Entry(frame,show='*');password.pack(fill='x',pady=4)
first=store.db.execute('SELECT COUNT(*) FROM app_users').fetchone()[0]==0
status=ttk.Label(frame,text='First launch: create administrator' if first else 'Sign in to continue');status.pack(pady=8)
def login():
    u=username.get().strip();p=password.get()
    try:
        if first:
            phase4.bootstrap_admin(store.db,u,p);role='admin'
        else:
            role=phase3.authenticate(store.db,u,p)
            if not role:raise ValueError('Invalid credentials')
        store.close();root.destroy()
        import auth_session
        auth_session.start_session(u,role)
        import app
    except Exception as e:messagebox.showerror('Login failed',str(e))
ttk.Button(frame,text='Create Admin & Open' if first else 'Login',command=login).pack(pady=8)
root.mainloop()
