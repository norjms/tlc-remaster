"""Paint the rig poses into a detailed captain with FLUX img2img (same seed for
every frame so the look stays steady), cut out with rembg.
usage: avatar_flux.py <bin/data> <denoise> <seed> <out dir>"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, r'\\192.168.1.50\ai-workspace\starflight\step7')
from variant import img2img
from rembg import remove, new_session
DATA, DN, SEED, OUT = sys.argv[1], float(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
os.makedirs(OUT, exist_ok=True)
PROMPT = ('full body side view of a space captain walking, profile facing right, wearing a plain dark grey armored spacesuit without logos or emblems, grey armor plates on shoulders, chest, knees and shins, black gloves and boots, '
          'with orange accent lights and a backpack, rounded helmet with a glowing teal visor, highly detailed 3D render, '
          'cinematic studio lighting, plain flat white background, no text')
sheet = Image.open(os.path.join(DATA, 'starport', 'starport_avatar@4x.png')).convert('RGBA')
F = 948
sess = new_session('isnet-general-use')
outs = []
for i in range(8):
    fr = sheet.crop((i * F, 0, (i + 1) * F, F))
    init = Image.new('RGBA', (1024, 1024), (255, 255, 255, 255)); init.alpha_composite(fr, (38, 38))
    res = img2img(init, PROMPT, DN, SEED, f'av_{i}')
    cut = remove(res, session=sess)
    cut.save(os.path.join(OUT, f'f{i}.png')); outs.append(cut)
    print(i, flush=True)
pv = Image.new('RGB', (8 * 256, 256), (52, 46, 38))
for i, c in enumerate(outs):
    t = c.resize((256, 256)); pv.paste(t, (i * 256, 0), t)
pv.save(os.path.join(OUT, 'sheet.jpg'), quality=88)
