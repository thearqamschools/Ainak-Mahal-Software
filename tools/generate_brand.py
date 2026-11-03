"""Generate original SVG/PNG/ICO artwork. Pillow is a development-only dependency."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / 'assets' / 'brand'
OUT.mkdir(parents=True, exist_ok=True)
PATHS = ('M13 23 Q8 23 8 28 L9 36 Q10 41 15 41 L23 41 Q28 41 28 35 L28 23 Z',
         'M41 23 Q36 23 36 28 L36 35 Q36 41 41 41 L49 41 Q54 41 55 36 L56 28 Q56 23 51 23 Z')
mark = ''.join(f'<path d="{p}"/>' for p in PATHS)
mark += '<path d="M3 23 L8 26 M56 26 L61 23"/><path d="M28 28 Q32 23 36 28" stroke="#0D9488"/>'
inner = f'<g fill="none" stroke="#142D4E" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">{mark}</g>'
svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="Ainak Mahal eyeglasses">{inner}</svg>'
(OUT/'ainak-mark.svg').write_text(svg, encoding='utf-8')
(OUT/'ainak-mark-dark.svg').write_text(svg.replace('#142D4E','#FFFFFF').replace('#0D9488','#5EEAD4'),encoding='utf-8')
(OUT/'ainak-lockup.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 340 72" role="img" aria-label="Ainak Mahal optical store"><g transform="translate(0 4)">{inner}</g><text x="80" y="35" font-family="Segoe UI, sans-serif" font-size="26" font-weight="700" fill="#142D4E">Ainak Mahal</text><text x="81" y="56" font-family="Segoe UI, sans-serif" font-size="11" letter-spacing="2" fill="#52647A">OPTICAL STORE</text></svg>', encoding='utf-8')

# Raster paths use the same control geometry as the SVG, sampled with cubic-free quadratic curves.
def quadratic(a,b,c, steps=24):
    return [((1-t)**2*a[0]+2*(1-t)*t*b[0]+t*t*c[0],(1-t)**2*a[1]+2*(1-t)*t*b[1]+t*t*c[1]) for t in (i/steps for i in range(steps+1))]
def render(size, tile=False, inverted=False):
    factor=4; side=size*factor
    image=Image.new('RGBA',(side,side),(255,255,255,0));d=ImageDraw.Draw(image)
    if tile:d.rounded_rectangle((0,0,side-1,side-1),radius=side*.23,fill='#142D4E')
    scale=side/64
    def stroke(points,color):
        points=[(x*scale,y*scale) for x,y in points]
        width=round(3*scale);d.line(points,fill=color,width=width,joint='curve')
        for x,y in (points[0],points[-1]):d.ellipse((x-width/2,y-width/2,x+width/2,y+width/2),fill=color)
    ink='#FFFFFF' if tile or inverted else '#142D4E'
    for x in (8,36):
        pts=quadratic((x+5,23),(x,23),(x,28))+[(x+1,36)]+quadratic((x+1,36),(x+2,41),(x+7,41))+[(x+15,41)]+quadratic((x+15,41),(x+20,41),(x+20,35))+[(x+20,23),(x+5,23)]
        stroke(pts,ink)
    stroke([(3,23),(8,26)],ink);stroke([(56,26),(61,23)],ink)
    stroke(quadratic((28,28),(32,23),(36,28)),'#5EEAD4' if tile or inverted else '#0D9488')
    return image.resize((size,size),Image.Resampling.LANCZOS)

render(512).save(OUT/'ainak-mark.png')
render(512,inverted=True).save(OUT/'ainak-mark-dark.png')
icon=render(256,True);icon.save(OUT/'ainak-icon.png')
icon.save(OUT/'ainak.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
lockup=Image.new('RGBA',(1360,288),'white');lockup.alpha_composite(render(256),(8,16))
font_path=next((p for p in (Path('C:/Windows/Fonts/segoeuib.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')) if p.exists()),None)
if font_path:
    draw=ImageDraw.Draw(lockup);draw.text((320,70),'Ainak Mahal',font=ImageFont.truetype(str(font_path),100),fill='#142D4E')
    draw.text((324,190),'OPTICAL STORE',font=ImageFont.truetype(str(font_path),36),fill='#52647A')
lockup.resize((680,144),Image.Resampling.LANCZOS).save(OUT/'ainak-lockup.png')
dark=Image.new('RGBA',(1360,288),'#142D4E');dark.alpha_composite(render(256,inverted=True),(8,16))
if font_path:
    draw=ImageDraw.Draw(dark);draw.text((320,70),'Ainak Mahal',font=ImageFont.truetype(str(font_path),100),fill='#FFFFFF')
    draw.text((324,190),'OPTICAL STORE',font=ImageFont.truetype(str(font_path),36),fill='#CDDBEC')
dark.resize((680,144),Image.Resampling.LANCZOS).save(OUT/'ainak-lockup-dark.png')
lockup_svg=(OUT/'ainak-lockup.svg').read_text()
(OUT/'ainak-lockup-dark.svg').write_text(lockup_svg.replace('#142D4E','#FFFFFF').replace('#0D9488','#5EEAD4').replace('#52647A','#CDDBEC'),encoding='utf-8')
print('Generated original mark, lockup and Windows icon in', OUT)
