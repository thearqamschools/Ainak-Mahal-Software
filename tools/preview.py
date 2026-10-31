"""Disposable visual QA fixture. Never opens the live shop database."""
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import tkinter as tk
from retail import Retail
from desktop import Desktop
from datetime import date,timedelta

with tempfile.TemporaryDirectory(prefix='ainak_preview_') as temp:
    s=Retail(Path(temp)/'preview.db');s.bootstrap('preview','preview-password','preview-password')
    cid=s.customer('Ali Hassan','0300 1234567','Faisalabad')
    s.customer('Sara Ahmed','0321 7654321','Millat Town')
    p=s.product('FR-100','Classic acetate · Navy',3500,1800,12,'Frames','8901001','Medium · Navy')
    lens=s.product('LN-050','Single vision lenses',2200,900,20,'Lenses','8901002','Anti-reflective','-0.50','0',4)
    s.product('SG-200','Everyday sunglasses',2800,1300,2,'Sunglasses','8901003')
    s.product('SV-001','Frame fitting',250,0,0,'Service',service=True)
    sid,_,_=s.checkout([(p,1),(lens,2)],cid,4000)
    rx=s.save_rx(cid,{'od_sph':'-0.50','os_sph':'-0.75','pd':'62'})
    s.job(cid,'Navy frame · AR lenses',str(date.today()+timedelta(days=2)),sid,rx)
    s.supplier('Faisal Optical Supplies','041 0000000')
    root=tk.Tk();ui=Desktop(root,s)
    if len(sys.argv)>1:ui.show(sys.argv[1])
    root.mainloop()
