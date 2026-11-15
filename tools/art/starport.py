"""Starport promenade (4000x768) and its sliding doors, scene+glass style.
The door openings keep the original's exact shape (alpha 0 where it was magenta).
usage: starport.py <bin/data> <view jpg> <preview dir>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
DATA, VIEW, PREV = sys.argv[1:4]
FONTS = r'\\192.168.1.50\ai-workspace\starflight\fonts'
Z = 2                                     # master scale (8000x1536)
W, H = 4000, 768
DOORS = [(558, 'Research Lab', (169, 139, 255)), (961, 'Personnel', (79, 227, 193)), (1299, "Captain's Lounge", (92, 225, 255)),
         (1958, 'Docking Bay', (255, 154, 61)), (2326, 'Trade Depot', (255, 196, 107)), (2807, 'Bank', (232, 196, 106)),
         (3194, 'Cantina', (255, 181, 71)), (3615, 'War Room', (255, 106, 85))]
DW = 228
ACC = (143, 216, 255)
z = lambda v: int(round(v * Z))

def font(w, px): return ImageFont.truetype(os.path.join(FONTS, f'barlowcondensed_BarlowCondensed-{w}.ttf'), z(px))

def vgrad(w, h, c0, c1):
    t = np.linspace(0, 1, h)[:, None, None]
    a = np.array(c0, np.float32) * (1 - t) + np.array(c1, np.float32) * t
    return Image.fromarray(np.repeat(a, w, 1).astype(np.uint8), 'RGB')

def glow_line(im, box, col, blur=6, a=200):
    g = Image.new('RGBA', im.size, (0, 0, 0, 0)); ImageDraw.Draw(g).rectangle(box, fill=col + (a,))
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(z(blur))))
    ImageDraw.Draw(im).rectangle(box, fill=tuple(min(255, c + 60) for c in col) + (255,))

# ------------------------------------------------------------------ wall
img = Image.new('RGBA', (z(W), z(H)), (0, 0, 0, 255))
img.paste(vgrad(z(W), z(585 - 64), (214, 220, 228), (178, 186, 198)), (0, z(64)))
d = ImageDraw.Draw(img)
# ceiling
img.paste(vgrad(z(W), z(64), (22, 28, 38), (40, 48, 60)), (0, 0))
for x in range(80, W, 240):
    d.rounded_rectangle((z(x), z(22), z(x + 120), z(30)), radius=z(4), fill=(235, 244, 255))
glow_line(img, (0, z(62), z(W), z(64) - 1), ACC, 5, 160)
d = ImageDraw.Draw(img)
# panel seams
for x in range(0, W, 160):
    d.line((z(x), z(64), z(x), z(470)), fill=(160, 170, 184), width=max(1, Z // 2))
    d.line((z(x) + Z, z(64), z(x) + Z, z(470)), fill=(232, 238, 244), width=max(1, Z // 2))
for y in (180, 300, 400):
    d.line((0, z(y), z(W), z(y)), fill=(170, 180, 194), width=max(1, Z // 2))
# windows between doors: a continuous view strip seen through cutouts
view = Image.open(VIEW).convert('RGB')
strip = Image.new('RGB', (view.width * 2, view.height)); strip.paste(view, (0, 0)); strip.paste(view.transpose(Image.FLIP_LEFT_RIGHT), (view.width, 0))
sh = z(W) * strip.height // strip.width
strip = strip.resize((z(W), sh), Image.LANCZOS)
wy0, wy1 = 96, 264
off = max(0, sh // 2 - z(wy1 - wy0) // 2 - z(10))
strip = strip.crop((0, off, z(W), off + z(wy1 - wy0)))
spans = [(x + 24, x + 376) for x in range(0, W, 400)]
for a, b in spans:
    m = Image.new('L', img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((z(a), z(wy0), z(b), z(wy1)), radius=z(26), fill=255)
    full = Image.new('RGBA', img.size, (0, 0, 0, 0)); full.paste(strip, (0, z(wy0)))
    img.paste(full, (0, 0), m)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((z(a) - z(6), z(wy0) - z(6), z(b) + z(6), z(wy1) + z(6)), radius=z(30), outline=(70, 80, 96), width=z(6))
    d.rounded_rectangle((z(a) - z(1), z(wy0) - z(1), z(b) + z(1), z(wy1) + z(1)), radius=z(26), outline=(230, 240, 250), width=Z)
    # glass reflection
    refl = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(refl).polygon([(z(a + 40), z(wy0)), (z(a + 120), z(wy0)), (z(a + 40), z(wy1)), (z(a - 40), z(wy1))], fill=(255, 255, 255, 18))
    img.alpha_composite(Image.composite(refl, Image.new('RGBA', img.size, (0, 0, 0, 0)), m))
# teal light rail and wainscot
glow_line(img, (0, z(312), z(W), z(314)), ACC, 6, 150)
img.paste(vgrad(z(W), z(585 - 470), (64, 72, 86), (40, 46, 58)), (0, z(470)))
d = ImageDraw.Draw(img)
d.line((0, z(470), z(W), z(470)), fill=(230, 238, 246), width=Z)
for x in range(0, W, 160):
    d.line((z(x), z(472), z(x), z(585)), fill=(30, 36, 46), width=Z)
# ------------------------------------------------------------------ floor
img.paste(vgrad(z(W), z(H - 585), (34, 40, 52), (12, 15, 21)), (0, z(585)))
band = img.crop((0, z(405), z(W), z(585))).transpose(Image.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(z(3)))
fade = np.linspace(.28, 0, band.height)[:, None]
band.putalpha(Image.fromarray((np.repeat(fade, band.width, 1) * 255).astype(np.uint8)))
img.alpha_composite(band, (0, z(585)))
ov = Image.new('RGBA', img.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
for y, a in ((640, 40), (700, 30), (760, 24)):
    od.line((0, z(y), z(W), z(y)), fill=(255, 255, 255, a), width=max(1, Z // 2))
img.alpha_composite(ov)
glow_line(img, (0, z(585), z(W), z(586)), ACC, 8, 120)
# ------------------------------------------------------------------ doors
orig = np.array(Image.open(os.path.join(DATA, 'starport', 'starport.bmp')).convert('RGB')).astype(int)
mag = (orig[:, :, 0] > 240) & (orig[:, :, 1] < 20) & (orig[:, :, 2] > 240)
d = ImageDraw.Draw(img)
for dx, name, col in DOORS:
    x0, x1 = dx - 22, dx + DW + 22
    # recessed frame
    d.rounded_rectangle((z(x0), z(292), z(x1), z(590)), radius=z(18), fill=(30, 36, 48))
    d.rounded_rectangle((z(x0), z(292), z(x1), z(590)), radius=z(18), outline=(90, 104, 124), width=Z)
    d.rounded_rectangle((z(dx - 6), z(344), z(dx + DW + 6), z(590)), radius=z(10), outline=col, width=z(2))
    g = Image.new('RGBA', img.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).rounded_rectangle((z(dx - 6), z(344), z(dx + DW + 6), z(590)), radius=z(10), outline=col + (200,), width=z(4))
    img.alpha_composite(g.filter(ImageFilter.GaussianBlur(z(5))))
    d = ImageDraw.Draw(img)
    # sign
    d.rounded_rectangle((z(dx + 8), z(302), z(dx + DW - 8), z(334)), radius=z(8), fill=(10, 16, 28), outline=(96, 108, 126), width=Z)
    d.ellipse((z(dx + 20), z(314), z(dx + 28), z(322)), fill=col)
    ft = font('Medium', 17); s = name.upper(); tr = z(2)
    tw = sum(ft.getlength(c) for c in s) + tr * (len(s) - 1)
    cx = z(dx + DW / 2 + 6) - tw / 2
    l, t, r, b = ft.getbbox('H')
    for c in s:
        d.text((cx, z(318) - (b + t) / 2), c, font=ft, fill=(238, 244, 255)); cx += ft.getlength(c) + tr
# punch the door openings exactly where the original was magenta (middle band)
hole = np.zeros((H, W), bool)
for dx, _, _ in DOORS:
    sub = mag[348:585, dx - 30:dx + DW + 30]
    ys, xs = np.where(sub)
    hole[348 + ys.min():348 + ys.max() + 1, dx - 30 + xs.min():dx - 30 + xs.max() + 1] = True
hz = Image.fromarray((hole * 255).astype(np.uint8)).resize((z(W), z(H)), Image.NEAREST)
al = np.array(img.getchannel('A')); al[np.array(hz) > 0] = 0
img.putalpha(Image.fromarray(al))
stem = os.path.join(DATA, 'starport', 'starport')
img.save(stem + '@2x.png'); img.resize((W, H), Image.LANCZOS).save(stem + '.png')
prev = img.resize((W // 2, H // 2), Image.LANCZOS)
bgp = Image.new('RGBA', prev.size, (255, 0, 255, 255)); bgp.alpha_composite(prev)
bgp.convert('RGB').save(os.path.join(PREV, 'starport_prev.jpg'), quality=86)

# ------------------------------------------------------------------ door panels (360x237, two 180 frames)
K = 4
dp = Image.new('RGBA', (360 * K, 237 * K), (0, 0, 0, 0))
def panel(x0, x1, strip_x):
    p = vgrad((x1 - x0) * K, 237 * K, (70, 80, 96), (42, 48, 60)).convert('RGBA')
    pd = ImageDraw.Draw(p)
    pd.rectangle((0, 0, p.width - 1, p.height - 1), outline=(120, 134, 154), width=K)
    for y in (60, 118, 176):
        pd.line((2 * K, y * K, p.width - 2 * K, y * K), fill=(30, 36, 46), width=K)
        pd.line((2 * K, y * K + K, p.width - 2 * K, y * K + K), fill=(96, 110, 130), width=K)
    sx = (strip_x - x0) * K
    g = Image.new('RGBA', p.size, (0, 0, 0, 0)); ImageDraw.Draw(g).rectangle((sx, 0, sx + 3 * K, p.height), fill=ACC + (220,))
    p.alpha_composite(g.filter(ImageFilter.GaussianBlur(3 * K)))
    ImageDraw.Draw(p).rectangle((sx + K, 0, sx + 2 * K, p.height), fill=(220, 245, 255))
    return p
dp.alpha_composite(panel(42, 156, 151), (42 * K, 0))
dp.alpha_composite(panel(180 + 66, 360, 180 + 67), ((180 + 66) * K, 0))
stem = os.path.join(DATA, 'starport', 'starport_door')
dp.save(stem + '@4x.png'); dp.resize((720, 474), Image.LANCZOS).save(stem + '@2x.png'); dp.resize((360, 237), Image.LANCZOS).save(stem + '.png')
print('ok')
