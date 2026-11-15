"""Install the painted captain frames (FLUX over the rig) as starport_avatar (+tiers).
usage: install_avatar.py <bin/data> <frames dir>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
DATA, FR = sys.argv[1], sys.argv[2]
S = 948; FW = 237
sheet = Image.new('RGBA', (S * 8, S * 2), (0, 0, 0, 0))
for i in range(8):
    cut = Image.open(os.path.join(FR, f'f{i}.png')).convert('RGBA').crop((38, 38, 38 + S, 38 + S))
    a = np.array(cut).astype(np.float32); a[:, :, 3] = np.where(a[:, :, 3] < 24, 0, a[:, :, 3])
    a[:, :, :3] *= np.array([0.86, 0.80, 0.70])          # warm, dimmer: the concourse's amber work light
    cut = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    f = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    sh = Image.new('RGBA', (S, S), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((116 * 4 - 176, 227 * 4, 116 * 4 + 200, 239 * 4), fill=(0, 0, 0, 120))
    f = Image.alpha_composite(f, sh.filter(ImageFilter.GaussianBlur(16)))
    f.alpha_composite(cut)
    sheet.alpha_composite(f, (i * S, 0)); sheet.alpha_composite(f.transpose(Image.FLIP_LEFT_RIGHT), (i * S, S))
stem = os.path.join(DATA, 'starport', 'starport_avatar')
sheet.save(stem + '@4x.png'); sheet.resize((FW * 16, FW * 4), Image.LANCZOS).save(stem + '@2x.png'); sheet.resize((FW * 8, FW * 2), Image.LANCZOS).save(stem + '.png')
print('ok')
