"""Starport avatar: a sleek suited captain, 8-frame walk cycle facing right
(row 0) and left (row 1), 237x237 frames, feet on y=233 like the original.
usage: avatar.py <bin/data> <preview.png>"""
import os, sys, math
from PIL import Image, ImageDraw, ImageFilter
DATA, PREV = sys.argv[1], sys.argv[2]
K = 4; FW = 237; N = 8
SUIT = (226, 232, 240); SUIT_D = (150, 160, 176); TRIM = (40, 48, 62); VISOR = (60, 200, 255); ACC = (143, 216, 255)

def capsule(d, p0, p1, r, fill):
    d.line((p0, p1), fill=fill, width=int(2 * r))
    for p in (p0, p1): d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=fill)

def limb(d, base, a1, l1, a2, l2, r, fill, foot=None):
    """two-segment limb from base, angles in degrees from straight down"""
    j = (base[0] + l1 * math.sin(math.radians(a1)), base[1] + l1 * math.cos(math.radians(a1)))
    e = (j[0] + l2 * math.sin(math.radians(a2)), j[1] + l2 * math.cos(math.radians(a2)))
    capsule(d, base, j, r, fill); capsule(d, j, e, r * .9, fill)
    if foot:
        fw, fh = foot
        d.rounded_rectangle((e[0] - fw * .35, e[1] - fh * .2, e[0] + fw * .75, e[1] + fh * .8), radius=fh * .45, fill=TRIM)
    return e

def frame(i):
    S = FW * K
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    t = 2 * math.pi * i / N
    sw = math.sin(t)
    bob = abs(math.cos(t)) * 3 * K
    cx = 118 * K
    hip = (cx, 138 * K - bob)
    thigh, shin = 46 * K, 48 * K
    # leg angles (positive = forward, toward +x)
    def leg(ph):
        s = math.sin(t + ph)
        a1 = 26 * s
        knee = max(0.0, 40 * math.sin(t + ph - 1.2))
        return a1, a1 - knee
    # far limbs first, darker
    fa1, fa2 = leg(math.pi)
    limb(d, (hip[0] - 2 * K, hip[1]), -fa1, thigh, -fa2 + 0, shin, 11 * K, SUIT_D, (30 * K, 13 * K))
    sh = (cx + 2 * K, 66 * K - bob)
    limb(d, sh, 22 * sw + 8, 34 * K, 22 * sw + 30, 32 * K, 8 * K, SUIT_D)
    # backpack
    d.rounded_rectangle((cx - 34 * K, 62 * K - bob, cx - 12 * K, 112 * K - bob), radius=8 * K, fill=(70, 80, 96))
    d.rounded_rectangle((cx - 31 * K, 70 * K - bob, cx - 26 * K, 104 * K - bob), radius=2 * K, fill=ACC + (255,))
    # torso
    d.rounded_rectangle((cx - 25 * K, 56 * K - bob, cx + 26 * K, 140 * K - bob), radius=18 * K, fill=SUIT)
    d.rounded_rectangle((cx - 25 * K, 118 * K - bob, cx + 26 * K, 130 * K - bob), radius=4 * K, fill=TRIM)   # belt
    d.rounded_rectangle((cx + 4 * K, 74 * K - bob, cx + 18 * K, 94 * K - bob), radius=3 * K, fill=(200, 208, 220))  # chest unit
    d.ellipse((cx + 9 * K, 80 * K - bob, cx + 14 * K, 85 * K - bob), fill=ACC + (255,))
    # near leg
    na1, na2 = leg(0)
    limb(d, (hip[0] + 2 * K, hip[1]), -na1, thigh, -na2, shin, 12 * K, SUIT, (30 * K, 13 * K))
    # helmet
    hx, hy = cx + 2 * K, 34 * K - bob
    d.ellipse((hx - 24 * K, hy - 26 * K, hx + 24 * K, hy + 24 * K), fill=SUIT)
    d.rounded_rectangle((hx - 2 * K, hy - 14 * K, hx + 23 * K, hy + 10 * K), radius=11 * K, fill=(16, 26, 40))
    vis = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(vis).rounded_rectangle((hx + 1 * K, hy - 11 * K, hx + 21 * K, hy + 7 * K), radius=9 * K, fill=VISOR + (210,))
    im = Image.alpha_composite(im, vis); d = ImageDraw.Draw(im)
    d.line((hx + 6 * K, hy - 8 * K, hx + 15 * K, hy - 8 * K), fill=(255, 255, 255, 200), width=2 * K)
    d.rounded_rectangle((hx - 14 * K, hy + 18 * K, hx + 14 * K, hy + 26 * K), radius=4 * K, fill=TRIM)   # collar
    # near arm (counter swing)
    limb(d, (cx + 2 * K, 70 * K - bob), -22 * sw + 6, 34 * K, -22 * sw + 26, 32 * K, 9 * K, SUIT)
    # rim light and soft shadow under the feet
    a = im.getchannel('A')
    rim = Image.new('RGBA', (S, S), ACC + (0,)); rim.putalpha(a.filter(ImageFilter.GaussianBlur(3 * K)).point(lambda v: int(v * .35)))
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    sh_ = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(sh_).ellipse((cx - 40 * K, 228 * K, cx + 46 * K, 238 * K), fill=(0, 0, 0, 90))
    out = Image.alpha_composite(out, sh_.filter(ImageFilter.GaussianBlur(3 * K)))
    out = Image.alpha_composite(out, rim); out = Image.alpha_composite(out, im)
    return out

frames = [frame(i) for i in range(N)]
# feet baseline: lowest opaque pixel should sit at y=233
sheet = Image.new('RGBA', (FW * N * K, FW * 2 * K), (0, 0, 0, 0))
for i, f in enumerate(frames):
    sheet.alpha_composite(f, (i * FW * K, 0))
    sheet.alpha_composite(f.transpose(Image.FLIP_LEFT_RIGHT), (i * FW * K, FW * K))
stem = os.path.join(DATA, 'starport', 'starport_avatar')
w, h = FW * N, FW * 2
sheet.save(stem + '@4x.png')
sheet.resize((w * 2, h * 2), Image.LANCZOS).save(stem + '@2x.png')
sheet.resize((w, h), Image.LANCZOS).save(stem + '.png')
pv = Image.new('RGBA', (w, h), (30, 36, 48, 255)); pv.alpha_composite(Image.open(stem + '.png'))
pv.convert('RGB').save(PREV)
print('ok')
