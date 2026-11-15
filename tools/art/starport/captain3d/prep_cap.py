"""Cut out the white-suit front view and erase the pack edges beside the helmet so image-to-3D builds no backpack."""
from rembg import remove, new_session
from PIL import Image, ImageDraw
import numpy as np
im = Image.open(r'\\192.168.1.50\ai-workspace\starflight\step8\nasb_3.png').convert('RGB')
out = remove(im, session=new_session('isnet-general-use'))
a = np.array(out)
# helmet is a circle centred about (389, 172), radius ~ 82 incl. rim; the pack shows outside it above the shoulders
yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
helmet = (xx - 389) ** 2 + (yy - 170) ** 2 <= 84 ** 2
pack = (yy < 248) & (xx > 255) & (xx < 525) & ~helmet & (yy > 60)
neck = (yy >= 225) & (yy < 252) & (xx > 318) & (xx < 462)          # keep the neck ring
a[pack & ~neck, 3] = 0
out = Image.fromarray(a)
bb = out.getchannel('A').point(lambda v: 255 if v > 16 else 0).getbbox()
out = out.crop(bb)
s = max(out.size); c = Image.new('RGBA', (int(s * 1.1),) * 2, (0, 0, 0, 0))
c.paste(out, ((c.width - out.width) // 2, (c.height - out.height) // 2), out)
c = c.resize((1024, 1024), Image.LANCZOS)
c.save(r'D:\AI\comfyui\ComfyUI\input\sf8_nasa2.png')
v = Image.new('RGBA', c.size, (60, 60, 70, 255)); v.alpha_composite(c); v.convert('RGB').save(r'\\192.168.1.50\ai-workspace\starflight\step8\nasa2_check.jpg', quality=90)
print('ok')
