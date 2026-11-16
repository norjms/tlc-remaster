"""Encounter effects in the glass style: spinning power-up coins, mineral crystal, hex shield bubble, laser bolt,
missile with flame tail, plasma orb. Writes name.png (+@2x, @4x) next to the original files (same sheet sizes).
usage: effects.py <bin/data> [preview.jpg]"""
import os, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi
DATA = sys.argv[1]; PREV = sys.argv[2] if len(sys.argv) > 2 else None
ENC = os.path.join(DATA, 'encounter')
R = 4  # render scale relative to the 4x tier (we draw at 16x then downsample to 4x/2x/1x for clean edges)

def save_tiers(sheet16, name, w1, h1):
    """sheet16 is drawn at 16x the 1x size; write 1x, 2x, 4x PNGs."""
    for k, suf in ((1, ''), (2, '@2x'), (4, '@4x')):
        sheet16.resize((w1 * k, h1 * k), Image.LANCZOS).save(os.path.join(ENC, name + suf + '.png'))

def glow(img, radius, strength=1.0):
    a = img.getchannel('A').filter(ImageFilter.GaussianBlur(radius))
    return a.point(lambda v: min(255, int(v * strength)))

# ---------- power-up coins ----------
ICONS = {
    'health': ((235, 70, 80), 'cross'),
    'shield': ((70, 150, 255), 'crest'),
    'armor': ((80, 210, 110), 'plate'),
    'fuel': ((255, 160, 50), 'drop'),
}
def icon_shape(d, kind, cx, cy, s, fill):
    if kind == 'cross':
        w = s * 0.22; d.rounded_rectangle((cx - w, cy - s * 0.55, cx + w, cy + s * 0.55), radius=w * 0.4, fill=fill)
        d.rounded_rectangle((cx - s * 0.55, cy - w, cx + s * 0.55, cy + w), radius=w * 0.4, fill=fill)
    elif kind == 'crest':
        pts = [(cx - s * 0.5, cy - s * 0.55), (cx + s * 0.5, cy - s * 0.55), (cx + s * 0.5, cy - s * 0.05), (cx, cy + s * 0.62), (cx - s * 0.5, cy - s * 0.05)]
        d.polygon(pts, fill=fill)
    elif kind == 'plate':
        pts = [(cx + s * 0.58 * math.cos(math.radians(a)), cy + s * 0.58 * math.sin(math.radians(a))) for a in range(30, 390, 60)]
        d.polygon(pts, fill=fill)
    elif kind == 'drop':
        d.ellipse((cx - s * 0.38, cy - s * 0.08, cx + s * 0.38, cy + s * 0.62), fill=fill)
        d.polygon([(cx, cy - s * 0.62), (cx - s * 0.36, cy + s * 0.2), (cx + s * 0.36, cy + s * 0.2)], fill=fill)

def coin(color, kind, size):
    """Front face of a glass coin, size x size RGBA."""
    c = np.array(color, np.float32)
    y, x = (np.mgrid[0:size, 0:size].astype(np.float32) - size / 2) / (size * 0.40)
    r = np.hypot(x, y); inside = np.clip((1 - r) * size * 0.4, 0, 1)
    body = (c * 0.35)[None, None] * (1 - r[..., None] * 0.4) + (c * 0.75)[None, None] * np.clip(1 - np.hypot(x + 0.35, y + 0.4), 0, 1)[..., None]
    rim = np.exp(-((r - 0.93) / 0.05) ** 2)[..., None] * (c * 0.5 + 120)
    inner = np.exp(-((r - 0.74) / 0.025) ** 2)[..., None] * (c * 0.6 + 80)
    rgb = body + rim + inner
    im = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), inside * 255]).astype(np.uint8), 'RGBA')
    # icon: white with a coloured glow
    ic = Image.new('RGBA', (size, size), (0, 0, 0, 0)); icon_shape(ImageDraw.Draw(ic), kind, size / 2, size / 2, size * 0.36, (255, 255, 255, 255))
    gl = Image.new('RGBA', (size, size), tuple(int(v) for v in np.clip(c * 1.1 + 40, 0, 255)) + (0,)); gl.putalpha(glow(ic, size * 0.04, 1.6))
    im.alpha_composite(gl); im.alpha_composite(ic)
    # glass highlight
    hl = np.clip(1 - np.hypot((x + 0.25) / 0.75, (y + 0.55) / 0.35), 0, 1) ** 1.5 * 0.55 * (r < 0.9)
    H = Image.fromarray(np.dstack([np.full_like(x, 255)] * 3 + [hl * 255]).astype(np.uint8), 'RGBA'); im.alpha_composite(H)
    return im

def spin_sheet(face, frames, size, rim_color):
    out = []
    for i in range(frames):
        th = 2 * math.pi * i / frames
        sx = abs(math.cos(th)); w = max(2, int(size * max(sx, 0.10)))
        f = face if math.cos(th) >= 0 else face  # same face on both sides (no mirrored icon)
        fr = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        sq = f.resize((w, size), Image.LANCZOS)
        # edge thickness: a darker band beside the face when turned
        t = int(size * 0.035 * abs(math.sin(th)))
        if t > 0:
            ed = Image.fromarray((np.asarray(sq).astype(np.float32) * np.array([0.45, 0.45, 0.45, 1.0])).astype(np.uint8), 'RGBA')
            for k in range(1, t + 1): fr.alpha_composite(ed, ((size - w) // 2 + (k if math.sin(th) > 0 else -k), 0))
        fr.alpha_composite(sq, ((size - w) // 2, 0))
        # outer soft glow so it reads against space
        g = Image.new('RGBA', (size, size), tuple(rim_color) + (0,)); g.putalpha(glow(fr, size * 0.05, 0.6))
        o = Image.new('RGBA', (size, size), (0, 0, 0, 0)); o.alpha_composite(g); o.alpha_composite(fr)
        out.append(o)
    return out

def strip(frames, size):
    s = Image.new('RGBA', (size * len(frames), size), (0, 0, 0, 0))
    for i, f in enumerate(frames): s.paste(f, (i * size, 0))
    return s

previews = []
B = 64 * 16  # 1024 px cell, downsampled to 64/128/256
for name, (col, kind) in ICONS.items():
    face = coin(col, kind, int(B * 0.80))
    pad = Image.new('RGBA', (B, B), (0, 0, 0, 0)); pad.paste(face, ((B - face.width) // 2, (B - face.height) // 2))
    frames = spin_sheet(pad, 9, B, col)
    sh = strip(frames, B)
    save_tiers(sh, f'powerup_{name}', 576, 64); previews.append(sh.resize((576 * 2, 128), Image.LANCZOS)); print(name, flush=True)

# ---------- mineral crystal (7 frames of 24, sheet 170x24) ----------
def crystal(th, size):
    im = Image.new('RGBA', (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cx, cy = size / 2, size / 2; hw = size * 0.30; hh = size * 0.44
    sx = math.cos(th)
    cols = [(150, 220, 255), (90, 170, 240), (60, 120, 210), (120, 200, 250)]
    # 4 vertical facets of a hexagonal prism seen from the side
    for k in range(4):
        a0 = th + k * math.pi / 2; a1 = a0 + math.pi / 2
        x0, x1 = cx + hw * math.sin(a0), cx + hw * math.sin(a1)
        if math.cos(a0 + math.pi / 4) < 0: continue
        shade = 0.55 + 0.45 * math.cos(a0 + math.pi / 4)
        c = tuple(int(v * shade) for v in cols[k]) + (255,)
        d.polygon([(x0, cy - hh * 0.55), (x1, cy - hh * 0.55), (x1, cy + hh * 0.55), (x0, cy + hh * 0.55)], fill=c)
        d.polygon([(x0, cy - hh * 0.55), (x1, cy - hh * 0.55), (cx, cy - hh)], fill=tuple(min(255, int(v * 1.15)) for v in c[:3]) + (255,))
        d.polygon([(x0, cy + hh * 0.55), (x1, cy + hh * 0.55), (cx, cy + hh)], fill=tuple(int(v * 0.7) for v in c[:3]) + (255,))
    g = Image.new('RGBA', (size, size), (120, 200, 255, 0)); g.putalpha(glow(im, size * 0.06, 0.8))
    o = Image.new('RGBA', (size, size), (0, 0, 0, 0)); o.alpha_composite(g); o.alpha_composite(im); return o
C = 24 * 16
fr = [crystal(2 * math.pi * i / 7, C) for i in range(7)]
sh = Image.new('RGBA', (170 * 16, 24 * 16), (0, 0, 0, 0))
for i, f in enumerate(fr): sh.paste(f, (i * C, 0))
save_tiers(sh, 'powerup_mineral', 170, 24); previews.append(sh.resize((340, 48), Image.LANCZOS)); print('mineral', flush=True)

# ---------- shield bubble (14 frames, 7x2, 96px) ----------
S = 96 * 8
yy, xx = (np.mgrid[0:S, 0:S].astype(np.float32) - S / 2) / (S / 2)
rr = np.hypot(xx, yy)
def hexgrid(x, y, scale):
    q = (x * 2 / 3) / scale; r_ = (-x / 3 + math.sqrt(3) / 3 * y) / scale
    # distance to nearest hex edge, cheap approximation
    a = np.abs(((q - np.round(q))))
    b = np.abs(((r_ - np.round(r_))))
    c = np.abs((((q + r_) - np.round(q + r_))))
    return np.minimum(np.minimum(a, b), c)
frames = []
for i in range(14):
    t = i / 14
    pulse = 0.75 + 0.25 * math.sin(2 * math.pi * t)
    fres = np.clip((rr - 0.55) / 0.40, 0, 1) ** 2.2 * (rr < 0.97)
    edge = np.exp(-((rr - 0.94) / 0.03) ** 2)
    # sphere-mapped hex pattern drifting
    z = np.sqrt(np.clip(1 - (rr / 0.97) ** 2, 0, 1))
    hx = hexgrid(xx / (z + 0.4) + t * 0.3, yy / (z + 0.4), 0.16)
    lines = np.exp(-(hx / 0.035) ** 2) * (rr < 0.95)
    sweep = np.exp(-((np.arctan2(yy, xx) - (2 * math.pi * t - math.pi)) % (2 * math.pi) / 0.9)) * 0.6
    a = np.clip(fres * 0.55 + edge * 0.9 + lines * (0.10 + 0.35 * fres) * pulse + sweep * fres * 0.5, 0, 1) * pulse
    col = np.dstack([90 + 120 * edge, 190 + 50 * edge, np.full_like(xx, 255)])
    frames.append(Image.fromarray(np.dstack([np.clip(col, 0, 255), a * 255]).astype(np.uint8), 'RGBA'))
sh = Image.new('RGBA', (S * 7, S * 2), (0, 0, 0, 0))
for i, f in enumerate(frames): sh.paste(f, ((i % 7) * S, (i // 7) * S))
for k, suf in ((1, ''), (2, '@2x'), (4, '@4x')):
    sh.resize((672 * k, 192 * k), Image.LANCZOS).save(os.path.join(ENC, 'shield' + suf + '.png'))
previews.append(sh.resize((672, 192), Image.LANCZOS)); print('shield', flush=True)

# ---------- projectiles ----------
def bolt_frame(size, kind, t):
    y, x = (np.mgrid[0:size, 0:size].astype(np.float32) - size / 2) / (size / 2)
    if kind == 'laser':   # vertical beam segment, white core, red glow (points up, angle 0 = up)
        core = np.exp(-(x / 0.10) ** 2) * np.clip(1 - np.abs(y) ** 4, 0, 1)
        halo = np.exp(-(x / 0.32) ** 2) * np.clip(1 - np.abs(y) ** 2, 0, 1)
        rgb = np.dstack([255 * np.ones_like(x), 70 + 185 * core, 60 + 195 * core])
        a = np.clip(core + halo * 0.6, 0, 1)
    elif kind == 'missile':   # orange-red plasma head with a flickering flame tail below
        head = np.exp(-((x) ** 2 + (y + 0.25) ** 2) / 0.05)
        ang = np.arctan2(y + 0.25, x)
        spikes = np.exp(-((x) ** 2 + (y + 0.25) ** 2) / 0.12) * (0.5 + 0.5 * np.cos(6 * ang + t * 2 * math.pi))
        tail = np.exp(-(x / (0.12 + 0.18 * np.clip(y + 0.25, 0, 1))) ** 2) * np.clip(1 - (y + 0.25) / 1.1, 0, 1) * (y > -0.25)
        tail *= 0.75 + 0.25 * math.sin(t * 6 * math.pi)
        a = np.clip(head * 1.3 + spikes * 0.45 + tail * 0.7, 0, 1)
        hot = np.clip(head * 1.4, 0, 1)
        rgb = np.dstack([255 * np.ones_like(x), 90 + 160 * hot, 40 + 200 * hot ** 2])
    else:   # plasma orb
        d2 = x ** 2 + y ** 2; ang = np.arctan2(y, x)
        core = np.exp(-d2 / 0.06); halo = np.exp(-d2 / 0.30) * (0.7 + 0.3 * np.cos(5 * ang))
        a = np.clip(core * 1.4 + halo * 0.6, 0, 1)
        rgb = np.dstack([150 + 105 * core, 120 + 135 * core, 255 * np.ones_like(x)])
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8), 'RGBA')

Z = 16 * 16
lz = bolt_frame(Z, 'laser', 0); save_tiers(lz, 'laser_beam', 16, 16)
ms = Image.new('RGBA', (160 * 16, 48 * 16), (0, 0, 0, 0))
for i in range(30): ms.paste(bolt_frame(Z, 'missile', i / 30), ((i % 10) * Z, (i // 10) * Z))
save_tiers(ms, 'red_bolt', 160, 48)
pl = bolt_frame(32 * 16, 'plasma', 0); save_tiers(pl, 'weapon_plasma_32', 32, 32)
previews.append(ms.resize((640, 192), Image.LANCZOS)); print('projectiles', flush=True)

if PREV:
    W = max(p.width for p in previews); Hh = sum(p.height + 10 for p in previews)
    c = Image.new('RGBA', (W, Hh), (14, 16, 24, 255)); yy0 = 0
    for p in previews: c.alpha_composite(p, (0, yy0)); yy0 += p.height + 10
    c.convert('RGB').save(PREV, quality=90)
