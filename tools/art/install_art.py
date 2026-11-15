"""Install the new trade icons and alien portraits into bin/data:
base files keep their name, size and format; tiers name@2x.png / name@4x.png."""
import os, shutil
from PIL import Image
S = r'\\192.168.1.50\ai-workspace\starflight\step5'
REPO = os.environ['USERPROFILE'] + r'\Documents\GitHub\tlc-remaster'
D = os.path.join(REPO, 'bin', 'data')
n = 0
for f in sorted(os.listdir(os.path.join(S, 'masters_v2'))):
    if not f.endswith('_4x.png'): continue
    stem = f[:-7]
    base = os.path.join(D, 'tradedepot', stem + '.tga')
    if not os.path.exists(base): print('no base', stem); continue
    m = Image.open(os.path.join(S, 'masters_v2', f)).convert('RGBA')
    w, h = Image.open(base).size
    m.resize((w, h), Image.LANCZOS).save(base)                      # RGBA TGA, same size
    for k in (2, 4):
        shutil.copyfile(os.path.join(S, 'tiers_v2', 'tradedepot', f'{stem}@{k}x.png'), os.path.join(D, 'tradedepot', f'{stem}@{k}x.png'))
    n += 1
print('icons', n)
n = 0
for f in sorted(os.listdir(os.path.join(S, 'masters_v3'))):
    stem = f[:-7]                                                     # portrait_x
    base = os.path.join(D, 'encounter', stem + '.bmp')
    w, h = Image.open(base).size
    m = Image.open(os.path.join(S, 'masters_v3', f)).convert('RGB')
    m.resize((w, h), Image.LANCZOS).save(base)                        # 24-bit BMP, same size
    for k in (2, 4):
        shutil.copyfile(os.path.join(S, 'tiers_v2', 'encounter', f'{stem}@{k}x.png'), os.path.join(D, 'encounter', f'{stem}@{k}x.png'))
    n += 1
print('portraits', n)
