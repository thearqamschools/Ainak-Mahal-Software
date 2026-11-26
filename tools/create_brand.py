"""Original geometric artwork. No downloaded visual or font assets."""
from pathlib import Path
from io import BytesIO
from PIL import Image,ImageDraw,ImageFont
import resvg_py
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'assets'/'brand';DEST.mkdir(parents=True,exist_ok=True)
LETTERS={'A':'M0 42 L16 0 L32 42 M6 28 H26','I':'M4 0 H28 M16 0 V42 M4 42 H28','N':'M0 42 V0 L32 42 V0','K':'M0 0 V42 M30 0 L0 24 M12 15 L32 42','M':'M0 42 V0 L18 24 L36 0 V42','H':'M0 0 V42 M32 0 V42 M0 21 H32','L':'M0 0 V42 H30'}
def wordmark(color):
    x=0;parts=[]
    for c in 'AINAK MAHAL':
        if c==' ':x+=26;continue
        parts.append(f'<path d="{LETTERS[c]}" transform="translate({x},0)"/>');x+=51 if c=='M' else 47
    return f'<g transform="translate(262 60)" fill="none" stroke="{color}" stroke-width="4.4" stroke-linejoin="round" stroke-linecap="square">'+''.join(parts)+'</g>'
def symbol(color,accent,concept=1):
    if concept==2:
        return f'<g fill="none" stroke="{color}" stroke-width="11"><circle cx="60" cy="82" r="32"/><circle cx="160" cy="82" r="32"/><path d="M92 78 Q110 56 128 78" stroke="{accent}"/><path d="M28 72 H12 M192 72 H208"/></g>'
    if concept==3:
        return f'<g fill="none" stroke="{color}" stroke-width="11" stroke-linejoin="round"><path d="M18 58 H88 L96 84 Q92 114 56 110 Q20 110 18 58 Z M132 58 H202 L202 84 Q198 114 164 110 Q132 110 132 58 Z"/><path d="M88 58 Q110 36 132 58" stroke="{accent}"/></g>'
    return f'<g fill="none" stroke="{color}" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"><path d="M25 56 H78 Q91 56 91 69 V87 Q91 111 66 111 H50 Q25 111 25 87 Z M142 56 H195 V87 Q195 111 170 111 H154 Q129 111 129 87 V69 Q129 56 142 56 Z"/><path d="M91 69 Q110 51 129 69" stroke="{accent}"/><path d="M25 67 H12 M195 67 H208"/></g>'
def svg(content,w,h):return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="Ainak Mahal">{content}</svg>'
def save(name,source,width=None):
    (DEST/(name+'.svg')).write_text(source,encoding='utf-8')
    (DEST/(name+'.png')).write_bytes(resvg_py.svg_to_bytes(svg_string=source,width=width))
for dark in (False,True):
    color='#F8FAFC' if dark else '#142D4E';accent='#2DD4BF' if dark else '#0D9488'
    name='logo-dark' if dark else 'logo-light'
    save(name,svg(symbol(color,accent)+wordmark(color),760,164),1520)
    save('symbol-dark' if dark else 'symbol-light',svg(symbol(color,accent),220,164),880)
for n in (1,2,3):save(f'concept-{n}',svg(symbol('#142D4E','#0D9488',n)+wordmark('#142D4E'),760,164),1520)
icon=svg('<rect width="256" height="256" rx="54" fill="#142D4E"/><g transform="translate(18,48)">'+symbol('#F8FAFC','#2DD4BF')+'</g>',256,256)
save('app-icon',icon,1024)
im=Image.open(DEST/'app-icon.png');im.save(DEST/'ainak-mahal.ico',sizes=[(s,s) for s in (16,20,24,32,40,48,64,128,256)])
board=Image.new('RGB',(1680,1150),'#F8FAFC');d=ImageDraw.Draw(board)
font=lambda n:ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',n)
d.text((70,45),'AINAK MAHAL / IDENTITY EXPLORATION',font=font(24),fill='#64748B')
for i,(title,body) in enumerate([('01   Clear bridge / selected','Balanced silhouette. Strong at small sizes. A restrained teal bridge connects both lenses.'),('02   Round frame','Friendly and familiar; less distinctive and weaker beside compact UI labels.'),('03   Browline','Confident upper frame; more visual weight and less neutral across product categories.')]):
    y=110+i*225;d.text((70,y),title,font=font(26),fill='#142D4E')
    image=Image.open(DEST/f'concept-{i+1}.png');image.thumbnail((950,150));board.paste(image,(65,y+40),image)
    d.text((70,y+177),body,font=font(19),fill='#64748B')
d.rounded_rectangle((60,805,1620,1100),radius=24,fill='#142D4E')
image=Image.open(DEST/'logo-dark.png');image.thumbnail((1100,240));board.paste(image,(100,830),image)
d.text((100,1045),'DEEP NAVY   /   TEAL BRIDGE   /   ORIGINAL GEOMETRIC WORDMARK',font=font(20),fill='#B6CDD8')
board.save(DEST/'identity-board.png')

