import os
from PIL import Image, ImageDraw, ImageFilter
R = os.environ['USERPROFILE'] + r'\Documents\GitHub\tlc-remaster'
K = 4; w, h = 18, 25
pts = [(1, 1), (1, 19), (5.5, 15), (8.5, 22), (11, 21), (8, 14.5), (14, 14.5)]
P = [(x * K, y * K) for x, y in pts]
sh = Image.new('RGBA', (w * K, h * K), (0, 0, 0, 0))
ImageDraw.Draw(sh).polygon([(x + K, y + 1.5 * K) for x, y in P], fill=(0, 0, 0, 120))
sh = sh.filter(ImageFilter.GaussianBlur(K))
im = Image.new('RGBA', (w * K, h * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
d.polygon(P, fill=(238, 244, 255, 255), outline=(8, 18, 30, 235), width=K)
d.line([(2 * K + K // 2, 4 * K), (2 * K + K // 2, 15 * K)], fill=(143, 216, 255, 255), width=K)
im = Image.alpha_composite(sh, im)
b = os.path.join(R, r'bin\data\gui\cursor')
im.save(b + '@4x.png'); im.resize((w * 2, h * 2), Image.LANCZOS).save(b + '@2x.png'); im.resize((w, h), Image.LANCZOS).save(b + '.png')
p = os.path.join(R, 'src', 'Game.cpp')
s = open(p, 'rb').read()
old, new = b'"data/gui/cursor.tga"', b'"data/gui/cursor.png"'
assert s.count(old) == 1
open(p, 'wb').write(s.replace(old, new))
print('ok')
