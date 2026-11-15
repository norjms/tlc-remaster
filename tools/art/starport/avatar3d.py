"""Starport captain, painted 3D look: every body part is a lit volume
(height map from its shape -> normals -> diffuse, specular, warm rim light),
8-frame walk cycle facing right (row 0) and left (row 1), 237x237 frames,
feet on y~233. usage: avatar3d.py <bin/data> <preview.jpg>"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
DATA, PREV = sys.argv[1], sys.argv[2]
K = 4; FW = 237; N = 8; S = FW * K
L = np.array([-0.45, -0.65, 0.62]); L /= np.linalg.norm(L)          # key light, top left, toward viewer
RIM = np.array([0.8, -0.3, 0.2]); RIM /= np.linalg.norm(RIM)          # warm rim from the right (amber work lights)

ARMOR = (92, 98, 108); ARMOR_D = (64, 69, 78); SOFT = (46, 50, 58); ORANGE = (236, 146, 46); VISOR = (40, 190, 230)

def lit(mask, color, sigma, gloss=40, spec=0.35, rim=0.5):
    """mask: float 0..1 (S,S). Returns RGBA float image of the shaded part."""
    m = mask.astype(np.float32)
    h = np.array(Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(sigma))).astype(np.float32) / 255
    gy, gx = np.gradient(h)
    k = sigma * 1.6
    nx, ny, nz = -gx * k, -gy * k, np.ones_like(h) * 0.6
    n = np.sqrt(nx * nx + ny * ny + nz * nz) + 1e-6
    nx, ny, nz = nx / n, ny / n, nz / n
    diff = np.clip(nx * L[0] + ny * L[1] + nz * L[2], 0, 1)
    # Blinn specular with the viewer along +z
    hv = L + np.array([0, 0, 1.0]); hv /= np.linalg.norm(hv)
    sp = np.clip(nx * hv[0] + ny * hv[1] + nz * hv[2], 0, 1) ** gloss
    rm = np.clip(nx * RIM[0] + ny * RIM[1] + nz * RIM[2], 0, 1) ** 3 * (1 - nz)
    c = np.array(color, np.float32)
    rgb = c[None, None, :] * (0.28 + 0.85 * diff[:, :, None]) + 255 * spec * sp[:, :, None] + np.array(ORANGE, np.float32) * rim * rm[:, :, None]
    return np.dstack([np.clip(rgb, 0, 255), m * 255])

def over(dst, src):
    a = src[:, :, 3:4] / 255
    dst[:, :, :3] = dst[:, :, :3] * (1 - a) + src[:, :, :3] * a
    dst[:, :, 3:4] = np.maximum(dst[:, :, 3:4], src[:, :, 3:4])

def shape(draw_fn):
    im = Image.new('L', (S, S), 0); draw_fn(ImageDraw.Draw(im))
    return np.array(im.filter(ImageFilter.GaussianBlur(K * .5))).astype(np.float32) / 255

def capsule(d, p0, p1, r):
    d.line((p0, p1), fill=255, width=int(2 * r))
    for p in (p0, p1): d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=255)

def joint(base, a, l):
    return (base[0] + l * math.sin(math.radians(a)), base[1] + l * math.cos(math.radians(a)))

def limb(img, base, a1, l1, a2, l2, r, col, foot=False, dark=1.0):
    col = tuple(int(c * dark) for c in col)
    j = joint(base, a1, l1); e = joint(j, a2, l2)
    def taper(d, p0, p1, r0, r1):
        n = 12
        for k in range(n + 1):
            u = k / n; x = p0[0] + (p1[0] - p0[0]) * u; y = p0[1] + (p1[1] - p0[1]) * u; rr = r0 + (r1 - r0) * u
            d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=255)
    over(img, lit(shape(lambda d: taper(d, base, j, r * 1.1, r * .82)), col, r * .5, 30, .28))
    over(img, lit(shape(lambda d: taper(d, j, e, r * .86, r * .72)), col, r * .45, 30, .28))
    # armour plate over the knee / elbow, oriented along the limb
    pl = shape(lambda d: taper(d, joint(base, a1, l1 * .78), joint(j, a2, l2 * .22), r * .72, r * .62))
    over(img, lit(pl, tuple(int(c * dark) for c in ARMOR_D), r * .3, 50, .45))
    if foot:
        fw, fh = 34 * K, 15 * K
        over(img, lit(shape(lambda d: d.rounded_rectangle((e[0] - fw * .32, e[1] - fh * .35, e[0] + fw * .72, e[1] + fh * .65), radius=fh * .45, fill=255)),
                      tuple(int(c * dark) for c in SOFT), fh * .3, 20, .2))
    return e

def frame(i):
    img = np.zeros((S, S, 4), np.float32)
    t = 2 * math.pi * i / N; sw = math.sin(t)
    bob = abs(math.cos(t)) * 3 * K
    cx = 116 * K
    hip = (cx, 136 * K - bob)
    def leg(ph):
        s = math.sin(t + ph); a1 = 26 * s
        return a1, a1 - max(0.0, 42 * math.sin(t + ph - 1.2))
    # far leg and arm (darker)
    fa1, fa2 = leg(math.pi)
    limb(img, (hip[0] - 3 * K, hip[1]), -fa1, 46 * K, -fa2, 48 * K, 12 * K, ARMOR, True, .62)
    limb(img, (cx + 2 * K, 72 * K - bob), 22 * sw + 8, 33 * K, 22 * sw + 30, 31 * K, 9 * K, ARMOR, False, .62)
    # backpack with amber status light
    over(img, lit(shape(lambda d: d.rounded_rectangle((cx - 40 * K, 60 * K - bob, cx - 14 * K, 116 * K - bob), radius=9 * K, fill=255)), SOFT, 6 * K, 25, .25))
    over(img, lit(shape(lambda d: d.rounded_rectangle((cx - 36 * K, 70 * K - bob, cx - 31 * K, 104 * K - bob), radius=2 * K, fill=255)), ORANGE, 1 * K, 10, .6, 0))
    # torso armour shell
    over(img, lit(shape(lambda d: d.polygon([(cx - 26 * K, 62 * K - bob), (cx + 28 * K, 62 * K - bob), (cx + 22 * K, 140 * K - bob), (cx - 20 * K, 140 * K - bob)], fill=255)), ARMOR, 10 * K, 45, .4))
    over(img, lit(shape(lambda d: d.rounded_rectangle((cx - 26 * K, 56 * K - bob, cx + 28 * K, 84 * K - bob), radius=12 * K, fill=255)), ARMOR, 8 * K, 50, .45))
    over(img, lit(shape(lambda d: d.rounded_rectangle((cx - 4 * K, 70 * K - bob, cx + 22 * K, 100 * K - bob), radius=7 * K, fill=255)), ARMOR_D, 4 * K, 60, .5))
    over(img, lit(shape(lambda d: d.ellipse((cx + 10 * K, 80 * K - bob, cx + 17 * K, 87 * K - bob), fill=255)), ORANGE, 1.5 * K, 10, .7, 0))
    over(img, lit(shape(lambda d: d.rounded_rectangle((cx - 25 * K, 120 * K - bob, cx + 27 * K, 132 * K - bob), radius=4 * K, fill=255)), SOFT, 3 * K, 20, .2))
    # near leg
    na1, na2 = leg(0)
    limb(img, (hip[0] + 3 * K, hip[1]), -na1, 46 * K, -na2, 48 * K, 13 * K, ARMOR, True)
    # helmet: lit sphere, dark glass visor with a sharp reflection
    hx, hy = cx + 3 * K, 33 * K - bob
    over(img, lit(shape(lambda d: d.rounded_rectangle((hx - 14 * K, hy + 14 * K, hx + 14 * K, hy + 27 * K), radius=5 * K, fill=255)), SOFT, 3 * K, 20, .2))
    over(img, lit(shape(lambda d: d.ellipse((hx - 24 * K, hy - 26 * K, hx + 26 * K, hy + 26 * K), fill=255)), ARMOR, 14 * K, 60, .55))
    vis = shape(lambda d: d.chord((hx - 22 * K, hy - 20 * K, hx + 27 * K, hy + 16 * K), -88, 88, fill=255))
    over(img, lit(vis, (12, 16, 22), 7 * K, 140, .95, .1))
    glow = np.zeros_like(img); g = shape(lambda d: d.chord((hx - 12 * K, hy - 14 * K, hx + 23 * K, hy + 11 * K), -80, 80, fill=255))
    glow[:, :, :3] = (255, 170, 80); glow[:, :, 3] = g * 70; over(img, glow)
    ref = np.zeros_like(img); r = shape(lambda d: d.arc((hx + 2 * K, hy - 16 * K, hx + 24 * K, hy + 14 * K), -60, -20, fill=255, width=2 * K))
    ref[:, :, :3] = 255; ref[:, :, 3] = r * 200; over(img, ref)
    # near arm
    limb(img, (cx + 2 * K, 72 * K - bob), -22 * sw + 6, 33 * K, -22 * sw + 26, 31 * K, 9.5 * K, ARMOR)
    # contact shadow
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    sh = Image.new('RGBA', (S, S), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((cx - 44 * K, 227 * K, cx + 50 * K, 239 * K), fill=(0, 0, 0, 120))
    out = Image.alpha_composite(out, sh.filter(ImageFilter.GaussianBlur(4 * K)))
    out = Image.alpha_composite(out, Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGBA'))
    return out

frames = [frame(i) for i in range(N)]
sheet = Image.new('RGBA', (S * N, S * 2), (0, 0, 0, 0))
for i, f in enumerate(frames):
    sheet.alpha_composite(f, (i * S, 0)); sheet.alpha_composite(f.transpose(Image.FLIP_LEFT_RIGHT), (i * S, S))
stem = os.path.join(DATA, 'starport', 'starport_avatar')
w, h = FW * N, FW * 2
sheet.save(stem + '@4x.png'); sheet.resize((w * 2, h * 2), Image.LANCZOS).save(stem + '@2x.png'); sheet.resize((w, h), Image.LANCZOS).save(stem + '.png')
pv = Image.new('RGBA', (w * 2, h * 2), (52, 46, 38, 255)); pv.alpha_composite(Image.open(stem + '@2x.png'))
pv.convert('RGB').save(PREV, quality=90)
print('ok')
