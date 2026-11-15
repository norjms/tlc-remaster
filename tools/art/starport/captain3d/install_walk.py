"""Install the Blender-rendered captain walk (16 frames per direction) as starport_avatar (+tiers).
usage: install_walk.py <bin/data> <frames dir> [tint r,g,b]"""
import os, sys, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
DATA, FR = sys.argv[1], sys.argv[2]
TINT = np.array([float(v) for v in (sys.argv[3] if len(sys.argv) > 3 else '0.66,0.62,0.56').split(',')])
S = 948; FW = 237
fs = sorted(glob.glob(os.path.join(FR, 'walk_*.png'))); N = len(fs)
sheet = Image.new('RGBA', (S * N, S * 2), (0, 0, 0, 0))
for i, fn in enumerate(fs):
    cut = Image.open(fn).convert('RGBA')
    assert cut.size == (S, S), cut.size
    a = np.array(cut).astype(np.float32)
    a[:, :, :3] *= TINT                                    # slate suit under the concourse's amber work light
    cut = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    al = np.array(cut.getchannel('A'))
    xs = np.nonzero(al[S - 60:].max(0) > 40)[0]             # feet span, for the contact shadow
    cx = (xs.min() + xs.max()) // 2 if len(xs) else S // 2
    hw = max(150, (xs.max() - xs.min()) // 2 + 40) if len(xs) else 180
    f = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    sh = Image.new('RGBA', (S, S), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((cx - hw, S - 40, cx + hw, S - 4), fill=(0, 0, 0, 120))
    f = Image.alpha_composite(f, sh.filter(ImageFilter.GaussianBlur(14)))
    f.alpha_composite(cut)
    sheet.alpha_composite(f, (i * S, 0)); sheet.alpha_composite(f.transpose(Image.FLIP_LEFT_RIGHT), (i * S, S))
stem = os.path.join(DATA, 'starport', 'starport_avatar')
sheet.save(stem + '@4x.png')
sheet.resize((FW * 2 * N, FW * 4), Image.LANCZOS).save(stem + '@2x.png')
sheet.resize((FW * N, FW * 2), Image.LANCZOS).save(stem + '.png')
print('ok', N, sheet.size)
