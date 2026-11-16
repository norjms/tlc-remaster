"""Procedural explosion sheets (30 frames, 6x5) for the encounter: flash, shock ring, turbulent fireball cooling
to smoke, flying sparks. Writes explosion_30_<cell>.png (+@2x, @4x) next to the original TGAs.
usage: explosions.py <bin/data> [preview.jpg]"""
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
DATA = sys.argv[1]; PREV = sys.argv[2] if len(sys.argv) > 2 else None
NF, COLS, ROWS = 30, 6, 5
S = 512   # render cell size

def fbm(n, seed, octaves=5):
    rng = np.random.default_rng(seed); out = np.zeros((n, n), np.float32); amp = 1.0; tot = 0
    for o in range(octaves):
        k = 4 * 2 ** o
        g = rng.standard_normal((k + 3, k + 3)).astype(np.float32)
        up = ndi.zoom(g, (n / k), order=3)[:n, :n]
        out += up * amp; tot += amp; amp *= 0.55
    out /= tot
    return (out - out.min()) / (out.max() - out.min())

# colour ramp by temperature (0 cold smoke .. 1 white hot)
RAMP_T = np.array([0.0, 0.12, 0.25, 0.42, 0.6, 0.78, 0.92, 1.0])
RAMP_C = np.array([[30, 26, 24], [58, 44, 36], [120, 46, 18], [205, 70, 14], [250, 130, 24], [255, 200, 70], [255, 240, 170], [255, 255, 245]], np.float32)
def ramp(t):
    t = np.clip(t, 0, 1)
    return np.stack([np.interp(t, RAMP_T, RAMP_C[:, i]) for i in range(3)], -1)

def render(seed):
    rng = np.random.default_rng(seed)
    y, x = (np.mgrid[0:S, 0:S].astype(np.float32) - S / 2) / (S / 2)       # -1..1
    r = np.hypot(x, y); ang = np.arctan2(y, x)
    N1, N2 = fbm(S, seed), fbm(S, seed + 7, 6)
    # puffs: lobes of the fireball
    P = 14; pa = rng.uniform(0, 2 * np.pi, P); pd = rng.uniform(0.15, 0.55, P); ps = rng.uniform(0.25, 0.45, P)
    # sparks
    K = 60; ka = rng.uniform(0, 2 * np.pi, K); kv = rng.uniform(0.6, 1.0, K); kl = rng.uniform(0.5, 1.0, K)
    frames = []
    for f in range(NF):
        t = f / (NF - 1)
        grow = 1 - (1 - min(1.0, t / 0.55)) ** 3            # fireball expands, then settles
        R = 0.12 + 0.62 * grow
        # density from puffs, warped by noise for turbulence
        wx = x + (N1 - 0.5) * 0.35 * grow; wy = y + (N2 - 0.5) * 0.35 * grow
        dens = np.zeros_like(x)
        for i in range(P):
            cx, cy = np.cos(pa[i]) * pd[i] * grow, np.sin(pa[i]) * pd[i] * grow
            rr = ps[i] * (0.35 + 0.75 * grow)
            dens += np.exp(-((wx - cx) ** 2 + (wy - cy) ** 2) / (2 * rr * rr))
        dens += 1.4 * np.exp(-(wx ** 2 + wy ** 2) / (2 * (0.30 * (0.3 + grow)) ** 2))
        dens = dens / dens.max()
        # break up with noise as it ages (holes, wisps)
        rot = ndi.rotate(N2, f * 2.0, reshape=False, order=1, mode='reflect')
        detail = 0.35 + 1.25 * rot ** 1.3
        dens = np.clip(dens * detail - 0.25 - 0.45 * t * (1 - rot), 0, 1)
        # temperature: hot early and in the core, cools outward and over time
        core = np.exp(-(r / (R * 0.6)) ** 2)
        temp = np.clip((1.15 - 1.25 * t) * (0.45 + 0.75 * core) * (0.55 + 0.6 * N1) + 0.15 * dens, 0, 1) * (dens > 0)
        col = ramp(temp)
        bd = ndi.gaussian_filter(dens, 6); gy_, gx_ = np.gradient(bd)
        shade = np.clip(1.0 + (gx_ + gy_) * 9.0 + (N2 - 0.5) * 0.5, 0.55, 1.35)
        col = np.clip(col * shade[..., None], 0, 255)
        alpha = np.clip(dens * 1.6, 0, 1) * np.clip(1.25 - t * 1.05, 0, 1) ** 0.8
        alpha *= np.clip((1.0 - r / (R + 0.25)) * 3, 0, 1)
        # flash core (first frames)
        flash = np.exp(-(r / 0.18) ** 2) * max(0.0, 1 - t / 0.16) * 1.4
        # shock ring
        ring_r = 0.15 + 0.75 * min(1.0, t / 0.38)
        ring = np.exp(-((r - ring_r) / 0.025) ** 2) * max(0.0, 1 - t / 0.38) ** 1.5 * (0.6 + 0.4 * N1)
        # sparks: short streaks flying out
        spark = np.zeros_like(x)
        for i in range(K):
            d = kv[i] * (0.15 + 1.05 * t ** 0.7)
            if d > 1.0 or t > kl[i]: continue
            px, py = np.cos(ka[i]) * d, np.sin(ka[i]) * d
            # streak along the direction of travel
            along = (x - px) * np.cos(ka[i]) + (y - py) * np.sin(ka[i])
            perp = -(x - px) * np.sin(ka[i]) + (y - py) * np.cos(ka[i])
            L = 0.06 * (1 - t)
            spark += np.exp(-(perp / 0.006) ** 2) * np.exp(-(np.clip(-along, 0, None) / max(L, 1e-3)) ** 2) * (along < 0.008) * (1 - t / kl[i])
        spark = np.clip(spark, 0, 1)
        rgb = col * alpha[..., None]
        rgb += np.array([255, 250, 235]) * flash[..., None]
        rgb += np.array([200, 225, 255]) * ring[..., None] * 0.9
        rgb += np.array([255, 205, 120]) * spark[..., None]
        a = np.clip(alpha + flash + ring * 0.8 + spark, 0, 1)
        out = np.dstack([np.clip(rgb / np.maximum(a, 1e-4)[..., None], 0, 255), a * 255])
        frames.append(out.astype(np.uint8))
    return frames

def sheet(frames, cell):
    sh = Image.new('RGBA', (cell * COLS, cell * ROWS), (0, 0, 0, 0))
    for i, fr in enumerate(frames):
        sh.paste(Image.fromarray(fr, 'RGBA').resize((cell, cell), Image.LANCZOS), ((i % COLS) * cell, (i // COLS) * cell))
    return sh

prev = None
for cell, seed in ((128, 11), (64, 23), (48, 37)):
    fr = render(seed)
    stem = os.path.join(DATA, 'encounter', f'explosion_30_{cell}')
    # the original 48 sheet is 288x241: keep the game's sheet size exactly
    w0, h0 = Image.open(stem + '.tga').size
    for k, suf in ((1, ''), (2, '@2x'), (4, '@4x')):
        sh = sheet(fr, cell * k)
        if sh.size != (w0 * k, h0 * k):
            c = Image.new('RGBA', (w0 * k, h0 * k), (0, 0, 0, 0)); c.paste(sh, (0, 0)); sh = c
        sh.save(stem + suf + '.png')
    if cell == 128: prev = sheet(fr, 128)
    print(cell, flush=True)
if PREV:
    bg = Image.new('RGBA', prev.size, (20, 22, 30, 255)); bg.alpha_composite(prev); bg.convert('RGB').save(PREV, quality=90)
