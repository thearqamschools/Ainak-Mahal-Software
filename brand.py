"""Original Ainak Mahal mark and desktop design tokens; no external assets needed."""
import tkinter as tk
from pathlib import Path

NAVY = '#142D4E'
BLUE = '#2563EB'
TEAL = '#0D9488'
BG = '#F8FAFC'
WHITE = '#FFFFFF'
TEXT = '#0F172A'
MUTED = '#52647A'
LINE = '#E2E8F0'
ERROR = '#B42318'


def print_mark():
    """Trusted, self-contained SVG; never includes user data or a network URL."""
    return '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="52" viewBox="0 0 64 64" role="img" aria-label="Ainak Mahal eyeglasses"><g fill="none" stroke="#142D4E" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M13 23 Q8 23 8 28 L9 36 Q10 41 15 41 L23 41 Q28 41 28 35 L28 23 Z M41 23 Q36 23 36 28 L36 35 Q36 41 41 41 L49 41 Q54 41 55 36 L56 28 Q56 23 51 23 Z M3 23 L8 26 M56 26 L61 23"/><path d="M28 28 Q32 23 36 28" stroke="#0D9488"/></g></svg>'


def mark(parent, size=64, background=WHITE, color=NAVY, accent=TEAL):
    """Two softly rectangular lenses, a bridge and temples on a shared grid."""
    c = tk.Canvas(parent, width=size, height=size, bg=background,
                  highlightthickness=0, borderwidth=0, takefocus=False)
    scale = size / 64
    def line(points, ink=color, width=3):
        c.create_line(*[v * scale for v in points], fill=ink,
                      width=width * scale, capstyle='round', joinstyle='round', smooth=True)
    for x in (8, 36):
        line((x+5,23,x,23,x,28,x+1,38,x+5,41,x+15,41,x+19,38,x+20,28,x+20,23,x+15,23,x+5,23))
    line((28,28,32,25,36,28), accent)
    line((3,23,8,26)); line((56,26,61,23))
    return c


def window_icon(root):
    """PhotoImage works both from source and PyInstaller's bundled module directory."""
    path = Path(__file__).resolve().parent / 'assets' / 'brand' / 'ainak-icon.png'
    if path.exists():
        root._ainak_icon = tk.PhotoImage(file=str(path))
        root.iconphoto(True, root._ainak_icon)
