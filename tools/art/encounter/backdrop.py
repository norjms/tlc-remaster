"""Seamless encounter backdrop: 6x4 tiles of 256 (1536x1024 at 1x) with @2x and @4x.
Deep space, faint nebula clouds, dense small stars, a few bright stars with glow. Everything wraps.
usage: backdrop.py <bin/data> [preview.jpg]"""
import os, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
DATA = sys.argv[1]; PREV = sys.argv[2] if len(sys.argv) > 2 else None
W1, H1 = 1536, 1024

def periodic_noise(h, w, beta, seed):
    rng = np.random.default_rng(seed)
    f = np.fft.fft2(rng.standard_normal((h, w)).astype(np.float32))
    fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.fftfreq(w)[None, :]
    k = np.sqrt(fx * fx + fy * fy); k[0, 0] = 1
    n = np.real(np.fft.ifft2(f / k ** beta)).astype(np.float32)
    return (n - n.min()) / (n.max() - n.min())

def render(K, seed=7):
    W, H = W1 * K, H1 * K
    rng = np.random.default_rng(seed)
    # nebula: low-frequency fields shaped into wisps, in a few tints, kept dim
    base = periodic_noise(H // 4, W // 4, 1.6, seed)
    detail = periodic_noise(H // 4, W // 4, 1.1, seed + 1)
    tint_a = periodic_noise(H // 4, W // 4, 1.8, seed + 2)
    neb = np.clip((base - 0.44) * 2.2, 0, 1) ** 1.4 * (0.55 + 0.75 * detail)
    neb = np.clip(neb, 0, 1)
    dust = np.clip((periodic_noise(H // 4, W // 4, 1.4, seed + 3) - 0.6) * 3.0, 0, 1)   # dark lanes
    cA = np.array([28, 60, 110], np.float32)    # blue
    cB = np.array([95, 40, 120], np.float32)    # violet
    cC = np.array([20, 85, 95], np.float32)     # teal
    t = np.clip((tint_a[..., None] - 0.3) * 2.2, 0, 1)
    col = cA * (1 - t) + cB * t
    col = col * (1 - detail[..., None] * 0.55) + cC * detail[..., None] * 0.7
    img4 = col * neb[..., None] * (1 - dust[..., None] * 0.6)
    bgc = np.array([4, 6, 13], np.float32)
    img = np.empty((H, W, 3), np.float32)
    for c in range(3):
        img[..., c] = ndi.zoom(img4[..., c], 4, order=3, mode='grid-wrap')[:H, :W] + bgc[c]
    # stars: impulses per brightness class, blurred with wrap so they stay seamless
    pal = np.array([[255, 255, 255], [200, 220, 255], [170, 200, 255], [255, 240, 210], [255, 215, 160], [255, 190, 150]], np.float32)
    def stars(n, amp, sigma, glow=0.0, gsig=0.0):
        layer = np.zeros((H, W, 3), np.float32)
        ys = rng.integers(0, H, n); xs = rng.integers(0, W, n)
        a = amp * rng.uniform(0.35, 1.0, n) ** 2
        cc = pal[rng.integers(0, len(pal), n)]
        for c in range(3): np.add.at(layer[..., c], (ys, xs), a * cc[:, c] / 255.0)
        out = np.stack([ndi.gaussian_filter(layer[..., c], sigma, mode='wrap') for c in range(3)], -1) * (2 * np.pi * sigma * sigma)
        if glow:
            out += np.stack([ndi.gaussian_filter(layer[..., c], gsig, mode='wrap') for c in range(3)], -1) * (2 * np.pi * gsig * gsig) * glow
        return out
    area = (W1 * H1) / (1536 * 1024)
    img += stars(int(5200 * area), 150, 0.55 * K)
    img += stars(int(900 * area), 260, 0.75 * K)
    img += stars(int(90 * area), 560, 1.0 * K, glow=0.09, gsig=6.0 * K)
    # stars sit a little brighter inside nebula (embedded clusters)
    return np.clip(img, 0, 255).astype(np.uint8)

out = None
for K, suf in ((1, ''), (2, '@2x'), (4, '@4x')):
    im = Image.fromarray(render(K), 'RGB')
    im.save(os.path.join(DATA, 'encounter', 'space_backdrop' + suf + '.png'))
    if K == 2: out = im
    print(K, flush=True)
if PREV:
    out.resize((1536, 1024), Image.LANCZOS).save(PREV, quality=90)
