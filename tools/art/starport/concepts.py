"""Starport concept directions: painted side-scrolling promenade, 2 candidates each."""
import os, random
from PIL import Image, ImageDraw
S5 = r'\\192.168.1.50\ai-workspace\starflight\step5'
S7 = r'\\192.168.1.50\ai-workspace\starflight\step7'
exec(open(os.path.join(S5, 'scenes.py'), encoding='utf-8').read().split('SCENES = {')[0])
os.makedirs(os.path.join(S7, 'concepts'), exist_ok=True)
BASE = ('2D side-scrolling video game background, flat side view straight on, no perspective, '
        'a long wall with a row of large sliding doors at floor level, a walkway floor along the bottom edge, ')
TAIL = ', painterly AAA concept art, highly detailed, cinematic lighting, no people, no characters, no text, no letters'
DIRS = {
 'A_promenade': 'futuristic space station promenade, tall panoramic windows above the doors showing a blue planet and stars, '
                'clean graphite and white panels, soft teal light strips, polished reflective floor',
 'B_industrial': 'gritty industrial spaceport concourse, heavy riveted bulkheads, pipes and vents, warm amber work lights, '
                 'small hazard stripes, steam haze, worn metal grating floor',
 'C_concourse': 'luxurious orbital spaceport concourse, warm lighting, glass railings, potted alien plants, '
                'holographic display panels without text, curved ceiling with skylights showing a nebula',
}
for name, p in DIRS.items():
    for k in range(2):
        f = txt2img(BASE + p + TAIL, 2048, 768, f'sf7_{name}', random.randint(1, 2 ** 31))
        Image.open(f).convert('RGB').save(os.path.join(S7, 'concepts', f'{name}_{k}.jpg'), quality=92)
        print(name, k, flush=True)
ims = sorted(os.listdir(os.path.join(S7, 'concepts')))
sheet = Image.new('RGB', (2048, 800 * len(ims)), (20, 20, 24)); d = ImageDraw.Draw(sheet)
for i, f in enumerate(ims):
    sheet.paste(Image.open(os.path.join(S7, 'concepts', f)), (0, i * 800 + 30))
    d.text((10, i * 800 + 4), f, fill=(255, 255, 255), font_size=22)
sheet.resize((1024, 400 * len(ims))).save(os.path.join(S7, 'concepts_sheet.jpg'), quality=85)
print('done')
