"""Assemble the Blender asteroid frames into the game's sheets: smlasteroid (8x8 of 60px) and bigasteroid (128px),
as name.png (+@2x, @4x).  usage: install_asteroids.py <bin/data> <frames dir> [preview.jpg]"""
import os, sys
from PIL import Image
DATA, FR = sys.argv[1], sys.argv[2]; PREV = sys.argv[3] if len(sys.argv) > 3 else None
ENC = os.path.join(DATA, 'encounter')
import numpy as np
def grade(im):
    a = np.asarray(im).astype(np.float32); rgb = a[..., :3] / 255.0
    rgb = (rgb ** 1.35) * np.array([0.70, 0.64, 0.58]) * 1.05
    a[..., :3] = np.clip(rgb * 255, 0, 255); return Image.fromarray(a.astype(np.uint8), 'RGBA')
def trim(im, frac):   # scale the rock to fill frac of the cell
    bb = im.getchannel('A').point(lambda a: 255 if a > 10 else 0).getbbox(); return im, bb
big = grade(Image.open(os.path.join(FR, 'big_00.png')).convert('RGBA'))
for k, suf in ((1, ''), (2, '@2x'), (4, '@4x')):
    big.resize((128 * k, 128 * k), Image.LANCZOS).save(os.path.join(ENC, 'bigasteroid' + suf + '.png'))
for k, suf in ((1, ''), (2, '@2x'), (4, '@4x')):
    c = 60 * k; sh = Image.new('RGBA', (8 * c, 8 * c), (0, 0, 0, 0))
    for i in range(64):
        f = grade(Image.open(os.path.join(FR, f'small_{i:02d}.png')).convert('RGBA')).resize((c, c), Image.LANCZOS)
        sh.paste(f, ((i % 8) * c, (i // 8) * c))
    sh.save(os.path.join(ENC, 'smlasteroid' + suf + '.png'))
    if k == 1 and PREV:
        p = Image.new('RGBA', (480 + 140, 480), (14, 16, 24, 255)); p.alpha_composite(sh); p.alpha_composite(big.resize((128, 128), Image.LANCZOS), (486, 10))
        p.convert('RGB').resize((1240, 960), Image.LANCZOS).save(PREV, quality=90)
print('ok')
