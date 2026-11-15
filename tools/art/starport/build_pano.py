"""Industrial starport concourse 4000x768 from the chosen concept and two img2img
variants: painted service doors are patched out with wall, segments are joined
(the middle one mirrored so its seams meet like content), the floor line is moved
to y=585, and painted door bays with backlit signs sit on the game's eight doors.
usage: build_pano.py <bin/data> [--no-esr]"""
import os, sys, subprocess, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
DATA = sys.argv[1]; ESR_ON = '--no-esr' not in sys.argv
S7 = r'\\192.168.1.50\ai-workspace\starflight\step7'
FONTS = r'\\192.168.1.50\ai-workspace\starflight\fonts'
ESR = os.path.join(os.environ['LOCALAPPDATA'], 'realesrgan', 'realesrgan-ncnn-vulkan.exe')
W, H = 4000, 768
DOORS = [(558, 'Research Lab'), (961, 'Personnel'), (1299, "Captain's Lounge"), (1958, 'Docking Bay'),
         (2326, 'Trade Depot'), (2807, 'Bank'), (3194, 'Cantina'), (3615, 'War Room')]
DW = 228
AMBER = (255, 178, 74)

def load(n): return Image.open(os.path.join(S7, n)).convert('RGB')

def patch_doors(im):
    """clone plain riveted wall over the painted service doors (rows 290..552)"""
    a = np.array(im)
    src = a[290:553, 880:1240]                       # plain wall with the hazard stripe
    for x0, x1 in ((660, 875), (1245, 1735)):
        w = x1 - x0
        tile = np.concatenate([src] * (w // src.shape[1] + 1), 1)[:, :w]
        # feather the patch edges
        m = np.ones((tile.shape[0], w, 1), np.float32)
        f = 24
        ramp = np.linspace(0, 1, f)
        m[:, :f, 0] *= ramp; m[:, -f:, 0] *= ramp[::-1]
        a[290:553, x0:x1] = (a[290:553, x0:x1] * (1 - m) + tile * m).astype(np.uint8)
    return Image.fromarray(a)

def join(a, b, f=160):
    A = np.array(a).astype(np.float32); B = np.array(b).astype(np.float32)
    w = np.linspace(0, 1, f)[None, :, None]
    mid = A[:, -f:] * (1 - w) + B[:, :f] * w
    return Image.fromarray(np.concatenate([A[:, :-f], mid, B[:, f:]], 1).astype(np.uint8))

b1, v0, v2 = load('concepts/B_industrial_1.jpg'), load('bvar_0.jpg'), load('bvar_2.jpg')
door_src = b1.copy()
segs = [patch_doors(x).crop((500, 0, 2048, 768)) for x in (b1, v0, v2)]
segs[1] = segs[1].transpose(Image.FLIP_LEFT_RIGHT)
pano = join(join(segs[0], segs[1]), segs[2])
# floor line 550 -> 585
k = 585 / 550
pano = pano.resize((int(pano.width * k), int(pano.height * k)), Image.LANCZOS)
top = pano.height - H
from PIL import ImageEnhance
pano = ImageEnhance.Brightness(pano.crop((0, top, W, top + H))).enhance(1.2).convert('RGBA')

# ---- painted door bays from the concept's double door (native coords)
fx0, fy0, fx1, fy1 = 1250, 290, 1725, 552            # frame with its pipe surround
ox0, ox1, oy0 = 1345, 1630, 330                      # opening inside it (to the floor)
sx = DW / (ox1 - ox0); sy = (585 - 348) / (fy1 - oy0)
bay = door_src.crop((fx0, fy0, fx1, fy1)).resize((int((fx1 - fx0) * sx), int((fy1 - fy0) * sy)), Image.LANCZOS).convert('RGBA')
bx = int((ox0 - fx0) * sx); by = int((oy0 - fy0) * sy)
# soften the bay's outer edge into the wall
m = Image.new('L', bay.size, 0); ImageDraw.Draw(m).rectangle((10, 6, bay.width - 11, bay.height), fill=255)
bay.putalpha(m.filter(ImageFilter.GaussianBlur(5)))
ft = ImageFont.truetype(os.path.join(FONTS, 'barlowcondensed_BarlowCondensed-SemiBold.ttf'), 17)
d = ImageDraw.Draw(pano)
for dx, name in DOORS:
    pano.alpha_composite(bay, (dx - bx, 348 - by))
    # backlit sign above the frame
    s = name.upper(); tr = 2
    tw = sum(ft.getlength(c) for c in s) + tr * (len(s) - 1)
    sw_, sh_ = int(tw + 40), 28
    sx0 = dx + DW // 2 - sw_ // 2; sy0 = 348 - by - sh_ - 10
    glow = Image.new('RGBA', pano.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((sx0 - 6, sy0 - 6, sx0 + sw_ + 6, sy0 + sh_ + 6), radius=8, fill=AMBER + (70,))
    pano.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(pano)
    d.rounded_rectangle((sx0, sy0, sx0 + sw_, sy0 + sh_), radius=5, fill=(22, 20, 18), outline=(92, 84, 70), width=1)
    tl = Image.new('RGBA', pano.size, (0, 0, 0, 0)); td = ImageDraw.Draw(tl)
    cx = sx0 + (sw_ - tw) / 2; l, t, r, b = ft.getbbox('H')
    for c in s:
        td.text((cx, sy0 + sh_ / 2 - (b + t) / 2), c, font=ft, fill=AMBER + (255,)); cx += ft.getlength(c) + tr
    pano.alpha_composite(tl.filter(ImageFilter.GaussianBlur(2)))
    pano.alpha_composite(tl)
# openings: exactly the original magenta rectangles
orig = np.array(Image.open(os.path.join(DATA, 'starport', 'starport.bmp')).convert('RGB')).astype(int)
mag = (orig[:, :, 0] > 240) & (orig[:, :, 1] < 20) & (orig[:, :, 2] > 240)
al = np.array(pano.getchannel('A'))
for dx, _ in DOORS:
    sub = mag[348:585, dx - 30:dx + DW + 30]; ys, xs = np.where(sub)
    al[348 + ys.min():348 + ys.max() + 1, dx - 30 + xs.min():dx - 30 + xs.max() + 1] = 0
pano.putalpha(Image.fromarray(al))
stem = os.path.join(DATA, 'starport', 'starport')
pano.save(stem + '.png')
if ESR_ON:
    tmp = tempfile.mkdtemp(); i = os.path.join(tmp, 'i.png'); o = os.path.join(tmp, 'o.png')
    pano.convert('RGB').save(i)
    subprocess.run([ESR, '-i', i, '-o', o, '-n', 'realesrgan-x4plus', '-s', '4', '-t', '256'], check=True, capture_output=True)
    up = Image.open(o).convert('RGB').resize((W * 2, H * 2), Image.LANCZOS)
    up.putalpha(Image.fromarray(al).resize((W * 2, H * 2), Image.NEAREST))
    up.save(stem + '@2x.png')
elif os.path.exists(stem + '@2x.png'):
    os.remove(stem + '@2x.png')

# ---- sliding door leaves from the painted door (360x237, frames of 180)
leaf_l = door_src.crop((ox0, oy0, (ox0 + ox1) // 2, fy1)).resize((114, 237), Image.LANCZOS)
leaf_r = door_src.crop(((ox0 + ox1) // 2, oy0, ox1, fy1)).resize((114, 237), Image.LANCZOS)
dp = Image.new('RGBA', (360, 237), (0, 0, 0, 0))
dp.paste(leaf_l, (42, 0)); dp.paste(leaf_r, (180 + 66, 0))
stem = os.path.join(DATA, 'starport', 'starport_door')
dp.save(stem + '.png')
dp.resize((720, 474), Image.LANCZOS).save(stem + '@2x.png')
if os.path.exists(stem + '@4x.png'): os.remove(stem + '@4x.png')
pano.resize((W // 2, H // 2)).convert('RGB').save(os.path.join(S7, 'pano_preview.jpg'), quality=86)
print('ok')
