"""Extend the industrial concourse concept to the right with FLUX outpainting.
usage: outpaint.py <seed image> <out png> <target width> [variants]"""
import os, sys, json, time, random, urllib.request, shutil
import numpy as np
from PIL import Image
COMFY = r'D:\AI\comfyui\ComfyUI'; API = 'http://127.0.0.1:8188'
PROMPT = ('2D side-scrolling video game background, flat side view straight on, no perspective, a long wall with a row of large '
          'sliding doors at floor level, a walkway floor along the bottom edge, gritty industrial spaceport concourse, heavy riveted '
          'bulkheads, pipes and vents, warm amber work lights, small hazard stripes, steam haze, worn metal grating floor, '
          'painterly AAA concept art, highly detailed, cinematic lighting, no people, no characters, no text, no letters')

def post(path, obj):
    r = urllib.request.Request(API + path, json.dumps(obj).encode(), {'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())

def inpaint(img_rgba, seed, name):
    fn = f'sf7_op_{name}.png'
    img_rgba.save(os.path.join(COMFY, 'input', fn))
    g = {
        '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'flux1-schnell-fp8.safetensors'}},
        '2': {'class_type': 'CLIPTextEncode', 'inputs': {'clip': ['1', 1], 'text': PROMPT}},
        '3': {'class_type': 'CLIPTextEncode', 'inputs': {'clip': ['1', 1], 'text': ''}},
        '4': {'class_type': 'LoadImage', 'inputs': {'image': fn}},
        '5': {'class_type': 'VAEEncode', 'inputs': {'pixels': ['4', 0], 'vae': ['1', 2]}},
        '9': {'class_type': 'SetLatentNoiseMask', 'inputs': {'samples': ['5', 0], 'mask': ['4', 1]}},
        '6': {'class_type': 'KSampler', 'inputs': {'model': ['1', 0], 'positive': ['2', 0], 'negative': ['3', 0], 'latent_image': ['9', 0],
              'seed': seed, 'steps': 4, 'cfg': 1.0, 'sampler_name': 'euler', 'scheduler': 'simple', 'denoise': 1.0}},
        '7': {'class_type': 'VAEDecode', 'inputs': {'samples': ['6', 0], 'vae': ['1', 2]}},
        '8': {'class_type': 'SaveImage', 'inputs': {'images': ['7', 0], 'filename_prefix': f'sf7_op_{name}'}},
    }
    pid = post('/prompt', {'prompt': g, 'front': True})['prompt_id']
    while True:
        time.sleep(2)
        h = json.loads(urllib.request.urlopen(f'{API}/history/{pid}').read())
        if pid in h:
            i = h[pid]['outputs']['8']['images'][0]
            return Image.open(os.path.join(COMFY, 'output', i.get('subfolder', ''), i['filename'])).convert('RGB')

def extend(pan, step=1024, ctx=1024, seed=None):
    H = pan.height
    win = Image.new('RGBA', (ctx + step, H), (0, 0, 0, 0))
    win.paste(pan.crop((pan.width - ctx, 0, pan.width, H)).convert('RGBA'), (0, 0))
    out = inpaint(win, seed or random.randint(1, 2 ** 31), str(pan.width))
    new = Image.new('RGB', (pan.width + step, H)); new.paste(pan, (0, 0))
    # crossfade the last 160 px of context into the generated version to hide the seam
    gen = np.array(out).astype(np.float32); old = np.array(pan.crop((pan.width - ctx, 0, pan.width, H))).astype(np.float32)
    f = 160
    blend = gen[:, :ctx].copy()
    w = np.clip((np.arange(ctx) - (ctx - f)) / f, 0, 1)[None, :, None]
    blend = old * (1 - w) + gen[:, :ctx] * w
    new.paste(Image.fromarray(blend.astype(np.uint8)), (pan.width - ctx, 0))
    new.paste(out.crop((ctx, 0, ctx + step, H)), (pan.width, 0))
    return new

if __name__ == '__main__':
    src, dst, target = sys.argv[1], sys.argv[2], int(sys.argv[3])
    pan = Image.open(src).convert('RGB')
    while pan.width < target:
        pan = extend(pan)
        print('width', pan.width, flush=True)
    pan.save(dst)
    pan.resize((pan.width // 4, pan.height // 4)).save(dst.replace('.png', '_small.jpg'), quality=85)
