"""Starmap art in the scene+glass style: viewer panel (map window with a nebula backdrop, coordinate grid,
brackets and labelled readout slots), glowing star sprites per spectral class and a flux gate marker.
Writes name.png (+@2x, @4x) beside the originals in data/starmap.
usage: starmap.py <bin/data> [preview.jpg]"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage as ndi
DATA = sys.argv[1]; PREV = sys.argv[2] if len(sys.argv) > 2 else None
SM = os.path.join(DATA, 'starmap')
FONTS = r'\\192.168.1.50\ai-workspace\starflight\fonts'
K = 4
INK = (238, 244, 255); ACC = (143, 216, 255); GLASS = (10, 16, 28); SCREEN = (4, 7, 14)
W, H = 799, 500                       # viewer size (game coordinates)
MX0, MY0, MW, MH = 52, 80, 688, 382   # map window inside the viewer (starmap.lua X_OFFSET, Y_OFFSET, MAP_*)
RX, RY = MW / 250.0, MH / 220.0       # map units -> pixels (ModuleStarmap ratioX/ratioY)

def font(weight, px):
    f = {400: 'Regular', 500: 'Medium', 600: 'SemiBold'}[weight]
    return ImageFont.truetype(os.path.join(FONTS, f'barlowcondensed_BarlowCondensed-{f}.ttf'), round(px * K))

def save(name, im4, w, h):
    stem = os.path.join(SM, name)
    im4.save(stem + '@4x.png'); im4.resize((w * 2, h * 2), Image.LANCZOS).save(stem + '@2x.png'); im4.resize((w, h), Image.LANCZOS).save(stem + '.png')

def fbm(w, h, seed, octaves=6):
    rng = np.random.default_rng(seed); out = np.zeros((h, w), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        k = 3 * 2 ** o
        g = rng.standard_normal((k + 3, int(k * w / h) + 3)).astype(np.float32)
        up = np.asarray(Image.fromarray(g).resize((w, h), Image.BICUBIC), np.float32)
        out += up * amp; tot += amp; amp *= 0.55
    out /= tot; return (out - out.min()) / (out.max() - out.min())

def tracked(d, xy, s, ft, fill, track=1.5, anchor_center=False):
    total = sum(ft.getlength(c) for c in s) + track * K * (len(s) - 1)
    x, y = xy
    if anchor_center: x -= total / 2
    for c in s:
        d.text((x, y), c, font=ft, fill=fill); x += ft.getlength(c) + track * K
    return total

def viewer():
    S = lambda v: round(v * K)
    im = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    # glass body (the top 30 px sit above the screen when the viewer is down)
    d.rounded_rectangle((S(3), S(26), S(W - 3), S(H - 2)), radius=S(14), fill=GLASS + (228,), outline=(255, 255, 255, 62), width=K)
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    for i in range(S(60)):
        sd.line((S(10), S(28) + i, S(W - 10), S(28) + i), fill=(255, 255, 255, round(14 * (1 - i / S(60)))))
    im = Image.alpha_composite(im, sh); d = ImageDraw.Draw(im)
    # map window: deep space with a soft nebula
    mw, mh = S(MW + 8), S(MH + 8)
    n1, n2, n3 = fbm(mw, mh, 3), fbm(mw, mh, 11), fbm(mw, mh, 29, 4)
    neb = np.clip((n1 - 0.48) * 2.2, 0, 1) ** 1.6
    neb2 = np.clip((n2 - 0.55) * 2.4, 0, 1) ** 1.8
    rgb = np.dstack([np.full((mh, mw), SCREEN[i], np.float32) for i in range(3)])
    rgb += neb[..., None] * np.array([40, 70, 120]) * (0.6 + 0.6 * n3[..., None])
    rgb += neb2[..., None] * np.array([70, 40, 95])
    # faint dust stars
    rng = np.random.default_rng(5)
    for _ in range(900):
        x, y = rng.integers(0, mw), rng.integers(0, mh); b = rng.uniform(30, 120)
        rgb[y:y + 2, x:x + 2] += b
    win = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB').filter(ImageFilter.GaussianBlur(0.6))
    mask = Image.new('L', win.size, 0); ImageDraw.Draw(mask).rounded_rectangle((0, 0, mw - 1, mh - 1), radius=S(8), fill=255)
    im.paste(win, (S(MX0 - 4), S(MY0 - 4)), mask); d = ImageDraw.Draw(im)
    # grid every 25 units, stronger every 50, with unit labels
    ft = font(500, 8.5)
    for u in range(0, 251, 25):
        x = S(MX0 + u * RX); a = 70 if u % 50 == 0 else 34
        d.line((x, S(MY0), x, S(MY0 + MH)), fill=ACC + (a,), width=1 if u % 50 else 2)
        if u % 50 == 0 and 0 < u < 250: d.text((x + S(3), S(MY0 + MH - 12)), str(u), font=ft, fill=ACC + (120,))
    for v in range(0, 221, 25):
        y = S(MY0 + v * RY); a = 70 if v % 50 == 0 else 34
        d.line((S(MX0), y, S(MX0 + MW), y), fill=ACC + (a,), width=1 if v % 50 else 2)
        if v % 50 == 0 and 0 < v < 220: d.text((S(MX0 + 4), y + S(2)), str(v), font=ft, fill=ACC + (120,))
    d.rounded_rectangle((S(MX0 - 4), S(MY0 - 4), S(MX0 + MW + 4), S(MY0 + MH + 4)), radius=S(8), outline=ACC + (110,), width=K)
    L, t, p = S(22), round(1.5 * K), S(MX0 + 2)
    for (x0, y0, dx, dy) in ((S(MX0 + 2), S(MY0 + 2), 1, 1), (S(MX0 + MW - 2), S(MY0 + 2), -1, 1),
                             (S(MX0 + 2), S(MY0 + MH - 2), 1, -1), (S(MX0 + MW - 2), S(MY0 + MH - 2), -1, -1)):
        d.line([(x0, y0), (x0 + dx * L, y0)], fill=ACC + (230,), width=t); d.line([(x0, y0), (x0, y0 + dy * L)], fill=ACC + (230,), width=t)
    # title, left of the HUD's top gauge bar
    tracked(d, (S(16), S(40)), 'STARMAP', font(600, 15), ACC + (255,), track=2.5)
    tracked(d, (S(16), S(58)), 'GALACTIC CHART', font(500, 9), INK + (150,), track=1.5)
    # readout: value slots exactly where ModuleStarmap prints (text x + X_OFFSET/2, y 480)
    slots = [('POSITION', [141, 215]), ('TARGET', [336, 406]), ('DISTANCE', [531]), ('FUEL', [646])]
    lf = font(600, 9.5)
    for name, xs in slots:
        x0 = xs[0] - 31
        wlab = sum(lf.getlength(c) for c in name) + 1.2 * K * (len(name) - 1)
        tracked(d, (S(x0) - wlab - S(6), S(476)), name, lf, ACC + (215,), track=1.2)
        for cx in xs:
            d.rounded_rectangle((S(cx - 31), S(472), S(cx + 31), S(492)), radius=S(5), fill=(2, 6, 12, 235), outline=ACC + (120,), width=K)
    return im

def stars():
    cols = [(240, 245, 255), (240, 245, 255), (175, 212, 255), (255, 244, 205), (255, 222, 125), (255, 168, 88), (255, 108, 86), (125, 162, 255)]
    C = 8 * K * 2   # draw at 8x per frame, downsample
    strip = Image.new('RGBA', (8 * C, C), (0, 0, 0, 0))
    y, x = (np.mgrid[0:C, 0:C].astype(np.float32) - C / 2 + 0.5) / (C / 8)   # in 1x pixels
    r = np.hypot(x, y)
    for i, c in enumerate(cols):
        c = np.array(c, np.float32)
        core = np.exp(-(r / 1.1) ** 2); halo = np.exp(-(r / 2.5) ** 2) * 0.9
        spike = (np.exp(-(np.abs(x) / 0.22) ** 2) * np.exp(-(np.abs(y) / 3.0) ** 2) + np.exp(-(np.abs(y) / 0.22) ** 2) * np.exp(-(np.abs(x) / 3.0) ** 2)) * 0.35
        a = np.clip(core + halo + spike, 0, 1) * (r < 3.9)
        rgb = c * (1 - core[..., None] * 0.65) + 255 * core[..., None] * 0.65
        strip.paste(Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8), 'RGBA'), (i * C, 0))
    return strip.resize((8 * 8 * K, 8 * K), Image.LANCZOS)

def flux():
    C = 8 * K * 2
    y, x = (np.mgrid[0:C, 0:C].astype(np.float32) - C / 2 + 0.5) / (C / 8)
    r = np.hypot(x, y); ang = np.arctan2(y, x)
    ring = np.exp(-((r - 2.7) / 0.55) ** 2) * (0.65 + 0.35 * np.cos(3 * ang))
    core = np.exp(-(r / 1.0) ** 2) * 0.55
    a = np.clip(ring + core, 0, 1) * (r < 3.95)
    rgb = np.dstack([90 + 120 * ring, 200 + 50 * ring, np.full_like(r, 255)])
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8), 'RGBA').resize((8 * K, 8 * K), Image.LANCZOS)

v = viewer(); save('starmap_viewer', v, W, H)
s = stars(); save(os.path.join('from_dat', 'is_tiles_trans'), s, 64, 8)
f = flux(); save('flux_tile_trans', f, 8, 8)
print('ok')
if PREV:
    p = v.resize((W * 2, H * 2), Image.LANCZOS); bg = Image.new('RGBA', p.size, (30, 30, 36, 255)); bg.alpha_composite(p)
    st = s.resize((64 * 8, 64), Image.LANCZOS); fl = f.resize((64, 64), Image.LANCZOS)
    bg.alpha_composite(st, (120, 140)); bg.alpha_composite(fl, (700, 140))
    bg.convert('RGB').save(PREV, quality=90)
