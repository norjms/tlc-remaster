"""Scroll bar parts and the crew hire skill icons in the glass style.
usage: widgets2.py <bin/data dir> <preview.png>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
DATA, PREV = sys.argv[1], sys.argv[2]
K = 4
INK = (238, 244, 255); ACC = (143, 216, 255)

def save(rel, im4):
    dst = os.path.join(DATA, os.path.splitext(rel)[0])
    w, h = im4.width // K, im4.height // K
    im4.save(dst + '@4x.png')
    im4.resize((w * 2, h * 2), Image.LANCZOS).save(dst + '@2x.png')
    im4.resize((w, h), Image.LANCZOS).save(dst + '.png')

def new(w, h): return Image.new('RGBA', (w * K, h * K), (0, 0, 0, 0))

# ---- scroll bar, 16 px wide (ScrollBox geometry)
t = new(16, 16); ImageDraw.Draw(t).rectangle((7 * K, 0, 9 * K - 1, 16 * K - 1), fill=(255, 255, 255, 34))
save('gui/scroll_track.png', t)
for name, col in (('scroll_thumb', INK + (130,)), ('scroll_thumb_over', ACC + (240,))):
    im = new(16, 16); ImageDraw.Draw(im).rounded_rectangle((5 * K, 1 * K, 11 * K - 1, 15 * K - 1), radius=3 * K, fill=col)
    save(f'gui/{name}.png', im)
for name, col in (('', INK + (150,)), ('_over', ACC + (255,))):
    for d in ('up', 'down'):
        im = new(16, 16); dr = ImageDraw.Draw(im)
        k = -1 if d == 'up' else 1
        cx, cy, h = 8 * K, 8 * K, 4 * K
        dr.line((cx - h, cy - k * 2 * K, cx, cy + k * 2 * K), fill=col, width=round(1.6 * K))
        dr.line((cx + h, cy - k * 2 * K, cx, cy + k * 2 * K), fill=col, width=round(1.6 * K))
        save(f'gui/scroll_{d}{name}.png', im)

# ---- crew hire skill icons: 8 x 40x40 tiles in a 452x420 sprite
src = Image.open(os.path.join(DATA, 'crewhire', 'personel_miniPositions.bmp')).convert('RGB')
a = np.array(src).astype(int)
mask = ~((a[:, :, 0] == 255) & (a[:, :, 1] == 0) & (a[:, :, 2] == 255))
out = new(src.width, src.height)
rows = [15, 65, 114, 164, 214, 265, 315, 364]
for y in rows:
    tile = a[y:y + 40, 0:40]
    lum = tile.mean(2)
    panel = new(40, 40)
    ImageDraw.Draw(panel).rounded_rectangle((K, K, 39 * K - 1, 39 * K - 1), radius=9 * K, fill=(10, 16, 28, 170), outline=(255, 255, 255, 62), width=K)
    # icon: dark strokes on the old light tile, inside a 3 px border
    ic = np.zeros((40, 40, 4), np.uint8)
    inner = np.zeros((40, 40), bool); inner[4:36, 4:36] = True
    alpha = np.clip((150 - lum) * 255 / 110, 0, 255) * inner
    ic[:, :, 0], ic[:, :, 1], ic[:, :, 2], ic[:, :, 3] = INK[0], INK[1], INK[2], alpha.astype(np.uint8)
    icon = Image.fromarray(ic, 'RGBA').resize((40 * K, 40 * K), Image.LANCZOS)
    panel.alpha_composite(icon)
    out.alpha_composite(panel, (0, y * K))
save('crewhire/personel_miniPositions.png', out)

# preview over the crew hire background
bg = Image.open(os.path.join(DATA, 'crewhire', 'personel_background.bmp')).convert('RGBA').crop((0, 200, 520, 640))
pv = Image.open(os.path.join(DATA, 'crewhire', 'personel_miniPositions@2x.png'))
S = bg.resize((1040, 880)); S.alpha_composite(pv, (40, 0))
x = 960
for i, n in enumerate(('scroll_up', 'scroll_thumb', 'scroll_track', 'scroll_down', 'scroll_up_over', 'scroll_thumb_over', 'scroll_down_over')):
    S.alpha_composite(Image.open(os.path.join(DATA, 'gui', n + '@4x.png')), (x, 40 + i * 70))
S.convert('RGB').save(PREV)
print('ok')
