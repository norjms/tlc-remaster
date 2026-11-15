"""Planet surface tilesets: new seamless FLUX ground textures poured into the
original tile layout (512x256 TGA, 64 px tiles: left 4x4 transitions keep
their alpha masks, right 4x4 keep their decorations). Writes .png + @2x/@4x.
gen:   tilesets.py gen [names]
build: tilesets.py build <bin/data> [names]"""
import os, sys, random
import numpy as np
from PIL import Image, ImageFilter
S5 = r'\\192.168.1.50\ai-workspace\starflight\step5'
S6 = r'\\192.168.1.50\ai-workspace\starflight\step6'
TEX = os.path.join(S6, 'textures')
TAIL = ', seamless tileable texture, seen from directly above, flat even lighting, highly detailed, natural, game ground texture, no objects, no text'
T = {
 'TileSet_Ash': 'grey volcanic ash ground with fine dust and small cinders',
 'Tileset_Desert': 'golden desert sand with soft wind ripples',
 'Tileset_Dirt': 'dry brown dirt ground with small pebbles',
 'Tileset_Gas_Acid_1': 'swirling purple and magenta toxic gas clouds',
 'Tileset_Gas_Acid_2': 'swirling bright green acidic gas clouds',
 'Tileset_Gas_Grass': 'swirling violet gas clouds with soft bands',
 'Tileset_Gas_Rock_1': 'dark indigo stormy gas clouds with subtle swirls',
 'Tileset_Gas_Rock_2': 'dark purple stormy gas clouds with subtle swirls',
 'Tileset_Glass': 'dark grey glassy obsidian plain with faint cracks',
 'Tileset_Grass_Dark': 'dense dark green alien grass',
 'Tileset_Grass_Dead': 'dry yellow and ochre dead grass',
 'Tileset_Grass_Light': 'lush bright green grass',
 'Tileset_Ice': 'pale blue cracked ice sheet with frost',
 'Tileset_Lava': 'bright orange molten lava with dark cooling crust',
 'Tileset_Magma': 'dark red magma crust with glowing orange cracks',
 'Tileset_Mud': 'dark brown wet mud with puddles',
 'Tileset_Rock_Dark': 'dark grey rocky ground with cracks and stones',
 'Tileset_Rock_Light': 'light grey cobbled rocky ground',
 'Tileset_Snow': 'fresh white snow with soft drifts',
 'Tileset_Stars': 'black outer space with sparse tiny stars',
 'Tileset_Water_Dark': 'deep dark blue ocean water surface with small waves',
 'Tileset_Water_Light': 'light turquoise shallow water surface with gentle ripples',
 'Tileset_Water_Mid': 'medium blue water surface with ripples',
}

def gen(names):
    exec(open(os.path.join(S5, 'scenes.py'), encoding='utf-8').read().split('SCENES = {')[0], globals())
    os.makedirs(TEX, exist_ok=True)
    for n in names:
        f = txt2img(T[n] + TAIL, 1024, 1024, f'sf6_tex_{n}', random.randint(1, 2 ** 31))
        Image.open(f).convert('RGB').save(os.path.join(TEX, n + '.jpg'), quality=94)
        print(n, flush=True)

def seamless(img, size):
    a = np.array(img.convert('RGB')).astype(np.float32)
    h, w = a.shape[:2]
    r = np.roll(np.roll(a, h // 2, 0), w // 2, 1)
    y = np.abs(np.linspace(-1, 1, h))[:, None]; x = np.abs(np.linspace(-1, 1, w))[None, :]
    wgt = np.clip(1 - np.maximum(x, y), 0, 1) ** .7          # 1 at the centre, 0 at the edges
    wgt = wgt[:, :, None]
    s = a * wgt + r * (1 - wgt)
    return Image.fromarray(np.clip(s, 0, 255).astype(np.uint8)).resize((size, size), Image.LANCZOS)

def build(data, names):
    K = 4; TS = 64
    for n in names:
        src = os.path.join(data, 'planetsurface', n + '.tga')
        o = Image.open(src).convert('RGBA'); oa = np.array(o).astype(np.float32)
        W, H = o.size
        tex = Image.open(os.path.join(TEX, n + '.jpg'))
        # match the old terrain's overall colour so maps keep their character
        base = seamless(tex.crop((128, 128, 896, 896)), TS * K)
        b = np.array(base).astype(np.float32)
        # flatten large-scale light and blotches so the 64 px repeat does not show
        from PIL import ImageFilter as _F
        low = np.array(base.filter(_F.GaussianBlur(TS * K / 6))).astype(np.float32)
        b = b - low + low.mean((0, 1))
        full = oa[:, :, 3] > 250
        old_mean = oa[full][:, :3].mean(0); old_std = oa[full][:, :3].std(0) + 1
        b = (b - b.mean((0, 1))) / (b.std((0, 1)) + 1) * np.maximum(old_std, b.std((0, 1)) * .6) + old_mean * .6 + b.mean((0, 1)) * .4
        base = Image.fromarray(np.clip(b, 0, 255).astype(np.uint8))
        variants = [base] * 4          # one seamless tile: flipped copies read as kaleidoscope patterns
        out = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
        # decoration mask from the plain tile statistics (right half tiles)
        plain = oa[0:TS, 0:TS, :3].reshape(-1, 3) if oa[0:TS, 0:TS, 3].min() > 250 else oa[full][:, :3]
        pm, ps = plain.mean(0), plain.std(0) + 6
        up = o.resize((W * K, H * K), Image.LANCZOS)
        for ty in range(H // TS):
            for tx in range(W // TS):
                v = variants[(tx + 2 * ty) % 4]
                tile = Image.new('RGBA', (TS * K, TS * K)); tile.paste(v.convert('RGBA'))
                t_o = oa[ty * TS:(ty + 1) * TS, tx * TS:(tx + 1) * TS]
                if tx * TS < W // 2:
                    al = Image.fromarray(t_o[:, :, 3].astype(np.uint8)).resize((TS * K, TS * K), Image.BICUBIC)
                    al = al.filter(ImageFilter.GaussianBlur(K * .6))
                    tile.putalpha(al)
                else:
                    med = np.median(t_o[:, :, :3].reshape(-1, 3), 0)
                    d = np.abs(t_o[:, :, :3] - med) / ps
                    m = (d.max(2) > 2.2).astype(np.uint8) * 255
                    mi = Image.fromarray(m).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(5))
                    mi = mi.resize((TS * K, TS * K), Image.BICUBIC).filter(ImageFilter.GaussianBlur(K * .7))
                    deco = up.crop((tx * TS * K, ty * TS * K, (tx + 1) * TS * K, (ty + 1) * TS * K))
                    tile.paste(deco, (0, 0), mi)
                    tile.putalpha(255)
                out.paste(tile, (tx * TS * K, ty * TS * K))
        stem = os.path.join(data, 'planetsurface', n)
        out.save(stem + '@4x.png'); out.resize((W * 2, H * 2), Image.LANCZOS).save(stem + '@2x.png')
        out.resize((W, H), Image.LANCZOS).save(stem + '.png')
        print('built', n, flush=True)

if __name__ == '__main__':
    if sys.argv[1] == 'gen':
        gen(sys.argv[2].split(',') if len(sys.argv) > 2 else list(T))
    else:
        build(sys.argv[2], sys.argv[3].split(',') if len(sys.argv) > 3 else list(T))
