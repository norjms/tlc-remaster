"""Build every in-game copy of the upgraded ships from their 8x masters.

usage: derive_ships.py <repo> <masters_dir> <out_data_dir> <preview.png>
Reads the ORIGINAL sprites from <repo>/bin/data, writes new files with the same
names, sizes and formats under <out_data_dir> (a mirror of bin/data).
Each derived image is placed exactly like the original: same rotation, same
bounding box. Planet-surface frames keep their original thruster-flame pixels.

Next to each file it also writes high resolution tiers, name@2x.png and
name@4x.png (RGBA, exactly 2x and 4x the size), rendered from the master. The
game picks the tier that suits the display (see a4sdl load_bitmap).
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw

repo, masters, out, preview = sys.argv[1:5]
DATA = os.path.join(repo, 'bin', 'data')
MAG = np.array([255, 0, 255], np.uint8)

def load_rgba(path):
    im = Image.open(path)
    if im.mode == 'RGBA':
        return np.asarray(im, np.uint8).copy(), 'tga'
    rgb = np.asarray(im.convert('RGB'), np.uint8)
    a = (~np.all(rgb == MAG, axis=2)).astype(np.uint8) * 255
    return np.dstack([rgb, a]), 'bmp'

def save(arr, path, fmt):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if fmt == 'tga':
        Image.fromarray(arr, 'RGBA').save(path)
    else:
        rgb = arr[..., :3].copy()
        rgb[np.all(rgb == MAG, axis=2)] = (254, 0, 254)    # never let ship pixels become the transparent key
        rgb[arr[..., 3] < 128] = MAG
        Image.fromarray(rgb, 'RGB').save(path)

def bbox(a):
    ys, xs = np.nonzero(a > 127)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1

def crop_to_alpha(img):
    a = np.asarray(img)[..., 3]
    x0, y0, x1, y1 = bbox(a)
    return img.crop((x0, y0, x1, y1))

def best_rotation(orig_src, target_alpha):
    """which of 0/90/180/270 turns the original game sprite into the target's silhouette"""
    tx0, ty0, tx1, ty1 = bbox(target_alpha)
    t = target_alpha[ty0:ty1, tx0:tx1] > 127
    best = None
    for rot in (0, 90, 180, 270):
        r = crop_to_alpha(Image.fromarray(orig_src, 'RGBA').rotate(rot, expand=True))
        r = np.asarray(r.resize((tx1 - tx0, ty1 - ty0), Image.BILINEAR))[..., 3] > 127
        iou = (r & t).sum() / max(1, (r | t).sum())
        if best is None or iou > best[0]: best = (iou, rot)
    return best

def fit(master, rot, target_shape, box):
    x0, y0, x1, y1 = box
    m = crop_to_alpha(master.rotate(rot, expand=True, resample=Image.BICUBIC))
    m = m.resize((x1 - x0, y1 - y0), Image.LANCZOS)
    canvas = Image.new('RGBA', (target_shape[1], target_shape[0]), (0, 0, 0, 0))
    canvas.paste(m, (x0, y0))
    return np.asarray(canvas, np.uint8).copy()

TIERS = (2, 4)

def tier_path(rel, n):
    return os.path.join(out, os.path.splitext(rel)[0] + f'@{n}x.png')

def scale_box(box, n):
    return tuple(v * n for v in box)

def save_tier(arr, rel, n):
    os.makedirs(os.path.dirname(tier_path(rel, n)), exist_ok=True)
    Image.fromarray(arr, 'RGBA').save(tier_path(rel, n))

report = []; tiles = []
def derive(name, rel, master, orig_src):
    target, fmt = load_rgba(os.path.join(DATA, rel))
    iou, rot = best_rotation(orig_src, target[..., 3])
    box = bbox(target[..., 3])
    new = fit(master, rot, target.shape, box)
    save(new, os.path.join(out, rel), fmt)
    h, w = target.shape[:2]
    for n in TIERS:
        save_tier(fit(master, rot, (h * n, w * n), scale_box(box, n)), rel, n)
    report.append(f'{rel}: rotation {rot}, silhouette match {iou:.2f}')
    tiles.append((rel, target, new))

def derive_strip(name, rel, master, orig_src):
    """planet-surface animation: N square frames; copy each frame's extra pixels (thruster flames) over the new ship"""
    strip, fmt = load_rgba(os.path.join(DATA, rel))
    h = strip.shape[0]; n = strip.shape[1] // h
    frames = [strip[:, i * h:(i + 1) * h] for i in range(n)]
    base = frames[0]
    iou, rot = best_rotation(orig_src, base[..., 3])
    new_base = fit(master, rot, base.shape, bbox(base[..., 3]))
    out_frames = []
    for f in frames:
        diff = (np.abs(f.astype(np.int16) - base.astype(np.int16)).max(2) > 24) & (f[..., 3] > 127)
        nf = new_base.copy(); nf[diff] = f[diff]
        out_frames.append(nf)
    new = np.concatenate(out_frames, axis=1)
    save(new, os.path.join(out, rel), fmt)
    box = bbox(base[..., 3])
    for k in TIERS:
        big_base = fit(master, rot, (h * k, h * k, 4), scale_box(box, k))
        tf = []
        for f in frames:
            diff = (np.abs(f.astype(np.int16) - base.astype(np.int16)).max(2) > 24) & (f[..., 3] > 127)
            d = np.kron(diff, np.ones((k, k), bool))
            fk = np.kron(f, np.ones((k, k, 1), np.uint8))
            nf = big_base.copy(); nf[d] = fk[d]
            tf.append(nf)
        save_tier(np.concatenate(tf, axis=1), rel, k)
    report.append(f'{rel}: {n} frames, rotation {rot}, silhouette match {iou:.2f}')
    tiles.append((rel, strip, new))

for p in ('military', 'science', 'freelance'):
    master = Image.open(os.path.join(masters, f'{p}_8x.png')).convert('RGBA')
    orig_src, _ = load_rgba(os.path.join(DATA, 'engineer', f'high_res_ship_{p}.tga'))
    for rel in (f'engineer/high_res_ship_{p}.tga', f'engineer/high_res_ship_{p}.bmp', f'auxiliary/high_res_ship_{p}.tga',
                f'auxiliary/aux_icon_{p}.tga', f'shipconfig/{p}.tga', f'spacetravel/{p}_128.bmp'):
        if os.path.exists(os.path.join(DATA, rel)):
            derive(p, rel, master, orig_src)
    derive_strip(p, f'planetsurface/ship_{p}.bmp', master, orig_src)

for a in ('barzhon', 'coalition', 'elowan', 'minex', 'nyssian', 'pirate', 'spemin', 'tafel', 'thrynn'):
    master = Image.open(os.path.join(masters, f'{a}_8x.png')).convert('RGBA')
    rel = f'encounter/ship_{a}.bmp'
    orig_src, _ = load_rgba(os.path.join(DATA, rel))
    derive(a, rel, master, orig_src)

print('\n'.join(report))

# preview: each file before | after, shown large with hard pixels
rows = []
for rel, before, after in tiles:
    k = max(1, min(6, 300 // before.shape[0])) if before.shape[1] < 600 else 2
    def show(a):
        im = Image.fromarray(a, 'RGBA'); im = im.resize((im.width * k, im.height * k), Image.NEAREST)
        bg = Image.new('RGB', im.size, (24, 26, 40)); bg.paste(im, (0, 0), im); return bg
    b, f = show(before), show(after)
    row = Image.new('RGB', (b.width + f.width + 60, max(b.height, f.height) + 40), (10, 12, 22))
    row.paste(b, (20, 30)); row.paste(f, (b.width + 40, 30))
    ImageDraw.Draw(row).text((20, 6), rel + '   (before | after)', fill=(230, 230, 240), font_size=18)
    rows.append(row)
W = max(r.width for r in rows); H = sum(r.height for r in rows)
sheet = Image.new('RGB', (W, H), (10, 12, 22)); y = 0
for r in rows: sheet.paste(r, (0, y)); y += r.height
sheet.save(preview)
print('preview', sheet.size)
