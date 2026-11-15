"""Planet surface sprites (buildings, lifeforms, flora) redrawn with FLUX.
gen:     surface_sprites.py gen            -> candidates in step6/sprites/<name>_<k>.png (cut out) + sheet
install: surface_sprites.py install <bin/data> picks.json  (picks: name -> [k, flip_h, rot_deg])"""
import os, sys, json, random
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
S5 = r'\\192.168.1.50\ai-workspace\starflight\step5'
S6 = r'\\192.168.1.50\ai-workspace\starflight\step6'
OUT = os.path.join(S6, 'sprites')
STYLE_TOP = ('seen from directly above, top-down view, game sprite, highly detailed painterly digital art, soft studio light from the top left, '
             'isolated on a plain flat white background, no shadow on the background, centered, no text')
STYLE_ISO = ('three-quarter top-down isometric view, game sprite, highly detailed painterly digital art, soft light, '
             'isolated on a plain flat white background, centered, no text, no ground plane')
SPR = {
 'B_Factory': ('rusty alien industrial factory complex with tall smokestacks, pipes, orange warning lights and vents', STYLE_ISO),
 'B_ListeningPost': ('large metal satellite dish antenna on a small round concrete base with a tiny control hut', STYLE_ISO),
 'B_Metropolis': ('dense cluster of glowing teal and cyan crystalline alien skyscrapers, a compact futuristic city block', STYLE_ISO),
 'B_Mine': ('square open-pit mine dug into brown earth with terraced walls, a small yellow mining truck and crates', STYLE_ISO),
 'B_Pottery': ('group of ancient alien clay pots, vases and bowls painted with spiral patterns, ochre and green glaze', STYLE_ISO),
 'B_Research': ('round domed white research station shaped like a saucer, blue glass dome on top, ring of cyan lights', STYLE_ISO),
 'B_ShantyTown': ('scattered small rusty metal shacks and huts with a little water tower, frontier settlement', STYLE_ISO),
 'B_Tomb': ('tall tapered green stone obelisk tomb covered in creeping vines with a glowing green gem on top', STYLE_ISO),
 'B_WeaponsPlacement': ('long green artillery cannon emplacement on a heavy armored tracked base, pointing diagonally', STYLE_ISO),
 'C_2Leg_Fuzz': ('a round red furry alien creature with one big eye and two small legs, head on the right side', STYLE_TOP),
 'C_2Leg_Large': ('a chunky olive green two-legged alien beast with a pink snout, head on the right side', STYLE_TOP),
 'C_2Leg_Small': ('a small pink two-legged alien critter with a curled tail, head on the right side', STYLE_TOP),
 'C_2Leg_Yellow': ('a round bright yellow blob-like alien creature with small green markings, head on the right side', STYLE_TOP),
 'C_4Leg_Large': ('a large purple spotted four-legged hippo-like alien beast, head on the right side', STYLE_TOP),
 'C_4Leg_Small': ('a small grey and orange four-legged alien rodent with a red nose, head on the right side', STYLE_TOP),
 'C_Bat_Large': ('a purple alien bat with wings fully spread wide, glowing yellow eyes, head on the right side', STYLE_TOP),
 'C_Bird_Large': ('a magenta alien bird with wings spread wide and long tail feathers, head on the right side', STYLE_TOP),
 'C_Bird_Yellow': ('a round yellow puffball alien bird with an orange crest and short beak, head on the right side', STYLE_TOP),
 'C_Plain_Galists': ('a dark grey furry alien creature with a white tufted tail, head on the right side', STYLE_TOP),
 'C_Plain_Vertruk': ('a cute blue spotted alien creature with a long tube-shaped nose, round body, head and tube nose on the right side', STYLE_TOP),
 'C_Rabid_Vertruk': ('an angry green spiky alien creature with a long tube-shaped nose, head and tube nose on the right side', STYLE_TOP),
 'C_Rodent_Huge': ('a huge brown alien rodent with a red nose and a bony tusk-like tail, head on the right side', STYLE_TOP),
 'C_Slug_Giant': ('a giant green alien slug with yellow spots, head on the right side', STYLE_TOP),
 'C_Snake_Large': ('a long orange and brown striped alien snake in an S curve, head on the right side', STYLE_TOP),
 'C_Spider_Giant': ('a giant orange-brown alien spider with red eyes and long purple legs, head on the right side', STYLE_TOP),
 'C_Sponge_Large': ('a yellow porous sponge-like alien organism with a crater in its center', STYLE_TOP),
 'C_Starfish_Large': ('a pink spotted five-armed alien starfish creature with one blue eye in the center', STYLE_TOP),
 'C_Swift_Galists': ('a sleek brown furry alien runner creature with a white tufted tail, head on the right side', STYLE_TOP),
 'Hypercube': ('a translucent glowing blue tesseract hypercube artifact, a cube inside a cube, faint energy glow', STYLE_ISO),
 'P_Bush_Law': ('a dense dark green alien bush with tiny red berries', STYLE_TOP),
 'P_Crystal_Small': ('an alien crystal plant with petal-like translucent blue crystal shards radiating from the center', STYLE_TOP),
 'P_Crystal_Small2': ('an alien crystal plant with petal-like translucent magenta crystal shards radiating from the center', STYLE_TOP),
 'P_Crystal_Small3': ('an alien crystal plant with petal-like translucent yellow-green crystal shards radiating from the center', STYLE_TOP),
 'P_Crystal_Small4': ('an alien crystal plant with petal-like translucent indigo crystal shards radiating from the center', STYLE_TOP),
 'P_Crystal_Small5': ('an alien crystal plant with petal-like translucent peach crystal shards radiating from the center', STYLE_TOP),
 'P_Plant_Small': ('a small alien flowering vine with green tendrils and yellow flowers', STYLE_TOP),
 'P_Tree_Large': ('a large round alien tree canopy with layered green foliage', STYLE_TOP),
 'P_Tree_Small': ('a small round alien tree canopy with deep green foliage', STYLE_TOP),
}

def gen():
    exec(open(os.path.join(S5, 'scenes.py'), encoding='utf-8').read().split('SCENES = {')[0], globals())
    from rembg import remove, new_session
    sess = new_session('isnet-general-use')
    os.makedirs(OUT, exist_ok=True)
    names = sys.argv[2].split(',') if len(sys.argv) > 2 else list(SPR)
    for name in names:
        desc, style = SPR[name]
        for k in range(3):
            f = txt2img(f'{desc}, {style}', 1024, 1024, f'sf6_spr_{name}', random.randint(1, 2 ** 31))
            cut = remove(Image.open(f).convert('RGB'), session=sess)
            bb = cut.getbbox()
            if bb: cut = cut.crop(bb)
            cut.save(os.path.join(OUT, f'{name}_{k}.png'))
        print(name, flush=True)
    sheet(names)

def sheet(names):
    cw = 200
    S = Image.new('RGB', (cw * 4, cw * len(names)), (60, 64, 72)); d = ImageDraw.Draw(S)
    src = os.environ['USERPROFILE'] + r'\Documents\GitHub\tlc-remaster\bin\data\planetsurface'
    for i, n in enumerate(names):
        o = Image.open(os.path.join(src, n + '.tga')).convert('RGBA'); o.thumbnail((180, 180), Image.NEAREST)
        S.paste(o, (10, i * cw + 15), o); d.text((4, i * cw + 2), n, fill='white', font_size=12)
        for k in range(3):
            p = os.path.join(OUT, f'{n}_{k}.png')
            if not os.path.exists(p): continue
            im = Image.open(p); im.thumbnail((180, 180))
            S.paste(im, ((k + 1) * cw + 10, i * cw + 15), im); d.text(((k + 1) * cw + 4, i * cw + 2), str(k), fill='yellow', font_size=12)
    S.save(os.path.join(S6, 'sprites_sheet.jpg'), quality=82)

def install(data, picks):
    K = 4
    for name, (k, flip, rot) in picks.items():
        src = os.path.join(data, 'planetsurface', name + '.tga')
        w, h = Image.open(src).size
        cut = Image.open(os.path.join(OUT, f'{name}_{k}.png')).convert('RGBA')
        if flip: cut = cut.transpose(Image.FLIP_LEFT_RIGHT)
        if rot: cut = cut.rotate(rot, expand=True, resample=Image.BICUBIC); cut = cut.crop(cut.getbbox())
        W, H = w * K, h * K
        # fit with margin, matching how much of the frame the original fills
        o = np.array(Image.open(src).convert('RGBA'))
        ys, xs = np.where(o[:, :, 3] > 40)
        fill = max(xs.max() - xs.min(), ys.max() - ys.min()) / max(w, h) if len(xs) else .85
        fill = min(.92, max(.6, fill))
        s = fill * min(W / cut.width, H / cut.height)
        cut = cut.resize((max(1, int(cut.width * s)), max(1, int(cut.height * s))), Image.LANCZOS)
        out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        x, y = (W - cut.width) // 2, (H - cut.height) // 2
        # soft drop shadow down-right like the originals
        sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        a = cut.getchannel('A').point(lambda v: int(v * .45))
        shadow = Image.new('RGBA', cut.size, (0, 0, 0, 255)); shadow.putalpha(a)
        sh.alpha_composite(shadow, (x + 3 * K, y + 4 * K))
        out = Image.alpha_composite(out, sh.filter(ImageFilter.GaussianBlur(2.5 * K)))
        out.alpha_composite(cut, (x, y))
        stem = os.path.join(data, 'planetsurface', name)
        out.save(stem + '@4x.png'); out.resize((w * 2, h * 2), Image.LANCZOS).save(stem + '@2x.png')
        out.resize((w, h), Image.LANCZOS).save(stem + '.png')
        print('installed', name)

if __name__ == '__main__':
    if sys.argv[1] == 'gen': gen()
    elif sys.argv[1] == 'sheet': sheet(list(SPR))
    else: install(sys.argv[2], json.load(open(sys.argv[3])))
