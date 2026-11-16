"""Alien ship schematics for the encounter's right viewer: the remastered ship (8x master) nose-right on a tactical
hologram display (grid, silhouette outline, scan lines, corner brackets). Writes schematic_<race>.bmp-replacing PNGs
(name.png at 1x, @2x, @4x) into bin/data/encounter.
usage: schematics.py <bin/data> [preview.jpg]"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi
DATA = sys.argv[1]; PREV = sys.argv[2] if len(sys.argv) > 2 else None
M = r'\\192.168.1.50\ai-workspace\starflight\ships\batch'
RACES = ['thrynn', 'elowan', 'spemin', 'barzhon', 'nyssian', 'tafel', 'minex', 'coalition', 'pirate']
W, H = 294, 268; K = 4; SW, SH = W * K, H * K
CYAN = np.array([90, 210, 255], np.float32)

def backdrop():
    y, x = np.mgrid[0:SH, 0:SW].astype(np.float32)
    r = np.hypot((x - SW / 2) / SW, (y - SH / 2) / SH)
    base = np.dstack([np.full_like(x, 8), np.full_like(x, 16), np.full_like(x, 28)]) * (1.25 - 0.9 * r)[..., None]
    g = np.zeros((SH, SW), np.float32)
    step = 24 * K // 2
    g[(np.abs(((x - SW / 2) % step)) < 1.2) | (np.abs(((y - SH / 2) % step)) < 1.2)] = 0.10
    g[(np.abs(((x - SW / 2) % (step * 4))) < 1.6) | (np.abs(((y - SH / 2) % (step * 4))) < 1.6)] = 0.20
    g[(np.abs(x - SW / 2) < 1.6) | (np.abs(y - SH / 2) < 1.6)] = 0.28
    img = base + g[..., None] * CYAN * (1.1 - r)[..., None]
    return img

def ship_layer(name):
    m = Image.open(os.path.join(M, f'{name}_8x.png')).convert('RGBA').rotate(-90, expand=True, resample=Image.BICUBIC)
    bb = m.getchannel('A').point(lambda a: 255 if a > 20 else 0).getbbox(); m = m.crop(bb)
    s = min(SW * 0.80 / m.width, SH * 0.74 / m.height)
    m = m.resize((max(1, int(m.width * s)), max(1, int(m.height * s))), Image.LANCZOS)
    L = Image.new('RGBA', (SW, SH), (0, 0, 0, 0)); L.paste(m, ((SW - m.width) // 2, (SH - m.height) // 2), m)
    return np.asarray(L, np.float32)

def compose(name):
    img = backdrop()
    sh = ship_layer(name); a = sh[..., 3] / 255.0; rgb = sh[..., :3]
    # hologram glow under the ship
    glow = ndi.gaussian_filter(a, 22 * K / 4)
    img = img + glow[..., None] * CYAN * 0.35
    # outline: offset echo of the silhouette, like a scan return
    sm = ndi.gaussian_filter(a, 2.5 * K / 4) > 0.5
    dout = ndi.distance_transform_edt(~sm)
    edge = np.exp(-((dout - 5.0 * K / 2) / (1.1 * K / 2)) ** 2) * (dout > 0)
    img = img * (1 - edge[..., None] * 0.8) + edge[..., None] * CYAN * 0.95
    # ship, slightly cooled toward the display colour
    cool = rgb * 0.88 + CYAN * 0.12 * (rgb.mean(2, keepdims=True) / 255.0)
    img = img * (1 - a[..., None]) + cool * a[..., None]
    # scan lines and a soft sweep band
    y = np.arange(SH, dtype=np.float32)[:, None]
    img *= (0.93 + 0.07 * (np.sin(y * np.pi / (1.5 * K)) > 0))[..., None]
    band = np.exp(-((y - SH * 0.32) / (SH * 0.05)) ** 2)
    img += band[..., None] * CYAN * 0.10
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGB')
    d = ImageDraw.Draw(im)
    c = tuple(int(v) for v in CYAN); L = 22 * K; t = 2 * K // 2 + 1; p = 10 * K
    for (x0, y0, dx, dy) in ((p, p, 1, 1), (SW - p, p, -1, 1), (p, SH - p, 1, -1), (SW - p, SH - p, -1, -1)):
        d.line([(x0, y0), (x0 + dx * L, y0)], fill=c, width=t); d.line([(x0, y0), (x0, y0 + dy * L)], fill=c, width=t)
    # tick marks along the edges
    for i in range(1, 12):
        xx = p + i * (SW - 2 * p) / 12; d.line([(xx, SH - p), (xx, SH - p - (6 if i % 3 else 12) * K // 2)], fill=c + (0,), width=max(1, K // 2))
        yy = p + i * (SH - 2 * p) / 12; d.line([(SW - p, yy), (SW - p - (6 if i % 3 else 12) * K // 2, yy)], fill=c, width=max(1, K // 2))
    return im

prev = []
for r in RACES:
    im4 = compose(r)
    base = os.path.join(DATA, 'encounter', f'schematic_{r}')
    im4.save(base + '@4x.png'); im4.resize((W * 2, H * 2), Image.LANCZOS).save(base + '@2x.png'); im4.resize((W, H), Image.LANCZOS).save(base + '.png')
    prev.append(im4.resize((W * 2, H * 2), Image.LANCZOS)); print(r, flush=True)
if PREV:
    sheet = Image.new('RGB', (W * 2 * 3, H * 2 * 3))
    for i, p in enumerate(prev): sheet.paste(p, ((i % 3) * W * 2, (i // 3) * H * 2))
    sheet.save(PREV, quality=88)
