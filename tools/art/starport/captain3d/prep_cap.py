from rembg import remove, new_session
from PIL import Image
im = Image.open(r'\\192.168.1.50\ai-workspace\starflight\step8\front_1.png').convert('RGB')
out = remove(im, session=new_session('isnet-general-use'))
bb = out.getchannel('A').point(lambda a: 255 if a > 16 else 0).getbbox()
out = out.crop(bb)
s = max(out.size); c = Image.new('RGBA', (int(s * 1.1),) * 2, (0, 0, 0, 0))
c.paste(out, ((c.width - out.width) // 2, (c.height - out.height) // 2), out)
c = c.resize((1024, 1024), Image.LANCZOS)
c.save(r'D:\AI\comfyui\ComfyUI\input\sf8_cap.png'); c.save(r'\\192.168.1.50\ai-workspace\starflight\step8\cap_rgba.png')
print(c.size)
