"""Startup: story background (FLUX galaxy, upscaled) and the copyright card.
usage: startup.py <bin/data> <space candidate jpg>"""
import os, sys, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont
DATA, SPACE = sys.argv[1], sys.argv[2]
FONTS = r'\\192.168.1.50\ai-workspace\starflight\fonts'
ESR = os.path.join(os.environ['LOCALAPPDATA'], 'realesrgan', 'realesrgan-ncnn-vulkan.exe')

# ---- story background 1280x960 (+@2x); the game blits it 1:1 into 1024x768
tmp = tempfile.mkdtemp()
src = os.path.join(tmp, 'in.png'); up = os.path.join(tmp, 'up.png')
Image.open(SPACE).convert('RGB').save(src)
subprocess.run([ESR, '-i', src, '-o', up, '-n', 'realesrgan-x4plus', '-s', '4'], check=True, capture_output=True)
big = Image.open(up).convert('RGB').resize((2560, 1920), Image.LANCZOS)
# darken the left two thirds where the story text scrolls
a = np.array(big).astype(np.float32)
x = np.linspace(0, 1, a.shape[1])[None, :, None]
a *= (0.42 + 0.58 * np.clip((x - .25) / .6, 0, 1))
big = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
stem = os.path.join(DATA, 'startup', 'space_1280')
big.save(stem + '@2x.png'); big.resize((1280, 960), Image.LANCZOS).save(stem + '.png')

# ---- copyright card 1024x768 at 4x
K = 4; W, H = 1024 * K, 768 * K
def f(w, px): return ImageFont.truetype(os.path.join(FONTS, f'barlowcondensed_BarlowCondensed-{w}.ttf'), round(px * K))
inter = lambda px: ImageFont.truetype(os.path.join(FONTS, 'inter_Inter-Variable.ttf'), round(px * K))
bg = big.resize((W, H), Image.LANCZOS).convert('RGBA')
bg = Image.alpha_composite(bg, Image.new('RGBA', (W, H), (4, 6, 12, 150)))
d = ImageDraw.Draw(bg)
def centred(y, s, ft, fill, track=0):
    tw = sum(ft.getlength(c) for c in s) + track * K * (len(s) - 1)
    x = (W - tw) / 2
    for c in s:
        d.text((x, y * K), c, font=ft, fill=fill); x += ft.getlength(c) + track * K
centred(170, 'STARFLIGHT', f('SemiBold', 18), (143, 216, 255, 255), 14)
centred(200, 'THE LOST COLONY', f('Light', 72), (255, 255, 255, 255), 8)
d.rectangle(((512 - 60) * K, 300 * K, (512 + 60) * K, 301 * K), fill=(255, 255, 255, 102))
centred(350, 'Created with love by fans.', inter(20), (238, 244, 255, 230))
centred(388, 'This game may not be distributed or sold!', inter(20), (238, 244, 255, 230))
centred(600, 'BUILT WITH', f('Medium', 13), (238, 244, 255, 140), 4)
centred(624, 'SDL3   \u00b7   Lua 5.1   \u00b7   libnoise   \u00b7   miniaudio   \u00b7   stb', f('Regular', 22), (238, 244, 255, 200), 1)
stem = os.path.join(DATA, 'startup', 'startup_copyrights')
card = bg.convert('RGB')
card.save(stem + '@4x.png'); card.resize((2048, 1536), Image.LANCZOS).save(stem + '@2x.png'); card.resize((1024, 768), Image.LANCZOS).save(stem + '.png')
card.resize((1024, 768), Image.LANCZOS).save(r'\\192.168.1.50\ai-workspace\starflight\step6\startup_card.jpg', quality=88)
print('ok')
