"""Star system view tiles (data/spacetravel/ip_tiles): a seamless deep-space tile (faint periodic nebula, irregular
stars, no grid pattern) and a glowing star with corona on tile 1. Planets are rendered by the game onto tiles 2..8.
Writes ip_tiles.png (+@2x, @4x), opaque RGB, 10 tiles of 256 at 1x.
usage: ip_tiles.py <bin/data> [preview.jpg] [seed]"""
import os, sys
import numpy as np
from PIL import Image
DATA = sys.argv[1]; PREV = sys.argv[2] if len(sys.argv) > 2 else None
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 5
T = 1024                      # tile size at 4x
rng = np.random.default_rng(SEED)

def periodic_noise(n, octaves, base, seed):
    """Tileable fractal noise via random Fourier components on integer frequencies."""
    r = np.random.default_rng(seed); y, x = np.mgrid[0:n, 0:n].astype(np.float32) / n
    out = np.zeros((n, n), np.float32); amp = 1.0
    for o in range(octaves):
        f = base * 2 ** o
        for _ in range(6):
            kx, ky = r.integers(-f, f + 1, 2)
            if kx == 0 and ky == 0: continue
            out += amp * np.cos(2 * np.pi * (kx * x + ky * y) + r.uniform(0, 2 * np.pi))
        amp *= 0.55
    return (out - out.min()) / (out.max() - out.min())

def space_tile():
    n1 = periodic_noise(T, 5, 1, SEED + 1); n2 = periodic_noise(T, 5, 2, SEED + 2)
    neb = np.clip((n1 - 0.55) * 2.2, 0, 1) ** 1.6
    base = np.dstack([np.full((T, T), 5.0), np.full((T, T), 7.0), np.full((T, T), 13.0)])
    tint = np.array([40, 30, 70]) * (1 - n2[..., None]) + np.array([20, 45, 70]) * n2[..., None]
    img = base + neb[..., None] * tint * 0.16
    # stars: many faint, few bright, wrap-around placement
    yy, xx = np.mgrid[0:T, 0:T].astype(np.float32)
    def add_star(cx, cy, mag, col, sigma):
        for dx in (-T, 0, T):
            for dy in (-T, 0, T):
                x0, y0 = cx + dx, cy + dy
                if -40 < x0 < T + 40 and -40 < y0 < T + 40:
                    sx0, sx1 = int(max(0, x0 - 6 * sigma - 8)), int(min(T, x0 + 6 * sigma + 8))
                    sy0, sy1 = int(max(0, y0 - 6 * sigma - 8)), int(min(T, y0 + 6 * sigma + 8))
                    if sx1 <= sx0 or sy1 <= sy0: continue
                    gx, gy = xx[sy0:sy1, sx0:sx1], yy[sy0:sy1, sx0:sx1]
                    d2 = (gx - x0) ** 2 + (gy - y0) ** 2
                    img[sy0:sy1, sx0:sx1] += (mag * np.exp(-d2 / (2 * sigma ** 2)) + mag * 0.12 * np.exp(-d2 / (2 * (sigma * 4) ** 2)))[..., None] * col
    cols = [np.array(c, np.float32) for c in ((1, 1, 1), (0.8, 0.88, 1), (1, 0.92, 0.8), (1, 0.8, 0.7), (0.75, 0.85, 1))]
    for _ in range(260):   # faint
        add_star(rng.uniform(0, T), rng.uniform(0, T), rng.uniform(25, 90), cols[rng.integers(0, 5)], rng.uniform(1.4, 2.0))
    for _ in range(22):    # medium
        add_star(rng.uniform(0, T), rng.uniform(0, T), rng.uniform(110, 190), cols[rng.integers(0, 5)], rng.uniform(2.0, 2.8))
    for _ in range(3):     # bright
        add_star(rng.uniform(0, T), rng.uniform(0, T), rng.uniform(220, 255), cols[rng.integers(0, 5)], 3.2)
    return np.clip(img, 0, 255)

def star_tile(bg):
    y, x = (np.mgrid[0:T, 0:T].astype(np.float32) - T / 2) / (T / 2)
    r = np.hypot(x, y); R = 0.42                        # photosphere radius (fraction of half tile)
    ang = np.arctan2(y, x)
    from scipy import ndimage as ndi
    g0 = np.random.default_rng(SEED + 9).standard_normal((T, T)).astype(np.float32)
    gran = ndi.gaussian_filter(g0, 3.0) * 0.6 + ndi.gaussian_filter(g0, 9.0) * 1.6
    gran = (gran - gran.min()) / (gran.max() - gran.min())
    inside = r < R
    mu = np.sqrt(np.clip(1 - (r / R) ** 2, 0, 1))
    limb = 0.45 + 0.55 * mu ** 0.6                       # limb darkening
    core = np.array([255, 242, 190]); edge = np.array([255, 128, 24])
    t = (1 - mu)[..., None]
    v = np.clip(mu ** 0.7 * (0.78 + 0.34 * gran), 0, 1)
    RT = np.array([0.0, 0.35, 0.7, 1.0]); RC = np.array([[220, 70, 10], [255, 140, 30], [255, 215, 90], [255, 250, 225]], np.float32)
    surf = np.stack([np.interp(v, RT, RC[:, k]) for k in range(3)], -1)
    # corona: radial glow with soft streamers, fades to zero at the tile edge so the tile stays seamless
    stream = 0.75 + 0.25 * np.cos(ang * 7 + gran * 3) * np.cos(ang * 3)
    glow = np.exp(-np.clip(r - R, 0, None) / 0.06) * 1.1 + np.exp(-np.clip(r - R, 0, None) / 0.22) * 0.55 * stream
    glow *= np.clip((1.0 - r) / 0.25, 0, 1) ** 1.5 * (~inside)
    gcol = np.array([255, 170, 60])
    img = bg + glow[..., None] * gcol
    aa = np.clip((R - r) * T / 2 / 1.5 + 0.5, 0, 1)[..., None]   # antialiased disc edge
    img = img * (1 - aa) + surf * aa
    return np.clip(img, 0, 255)

bg = space_tile(); st = star_tile(bg)
sheet = np.concatenate([bg, st] + [bg] * 8, axis=1).astype(np.uint8)
im4 = Image.fromarray(sheet, 'RGB')
stem = os.path.join(DATA, 'spacetravel', 'ip_tiles')
im4.save(stem + '@4x.png'); im4.resize((2560 * 2, 512), Image.LANCZOS).save(stem + '@2x.png'); im4.resize((2560, 256), Image.LANCZOS).save(stem + '.png')
if PREV:
    # 3x3 of the space tile with the star in the middle, to check seams and repetition
    g = Image.new('RGB', (768, 768))
    b1 = Image.fromarray(bg.astype(np.uint8)).resize((256, 256), Image.LANCZOS); s1 = Image.fromarray(st.astype(np.uint8)).resize((256, 256), Image.LANCZOS)
    for i in range(3):
        for j in range(3): g.paste(s1 if (i, j) == (1, 1) else b1, (i * 256, j * 256))
    g.save(PREV, quality=92)
print('ok')
