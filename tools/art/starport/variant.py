"""img2img variants of an image with FLUX (keeps palette and composition).
usage: variant.py <in> <out_prefix> <denoise> <n> [prompt file]"""
import os, sys, json, time, random, urllib.request
from PIL import Image
COMFY = r'D:\AI\comfyui\ComfyUI'; API = 'http://127.0.0.1:8188'
sys.path.insert(0, r'\\192.168.1.50\ai-workspace\starflight\step7')
from outpaint import PROMPT, post

def img2img(img, prompt, denoise, seed, name):
    fn = f'sf7_v_{name}.png'; img.convert('RGB').save(os.path.join(COMFY, 'input', fn))
    g = {
        '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'flux1-schnell-fp8.safetensors'}},
        '2': {'class_type': 'CLIPTextEncode', 'inputs': {'clip': ['1', 1], 'text': prompt}},
        '3': {'class_type': 'CLIPTextEncode', 'inputs': {'clip': ['1', 1], 'text': ''}},
        '4': {'class_type': 'LoadImage', 'inputs': {'image': fn}},
        '5': {'class_type': 'VAEEncode', 'inputs': {'pixels': ['4', 0], 'vae': ['1', 2]}},
        '6': {'class_type': 'KSampler', 'inputs': {'model': ['1', 0], 'positive': ['2', 0], 'negative': ['3', 0], 'latent_image': ['5', 0],
              'seed': seed, 'steps': 6, 'cfg': 1.0, 'sampler_name': 'euler', 'scheduler': 'simple', 'denoise': denoise}},
        '7': {'class_type': 'VAEDecode', 'inputs': {'samples': ['6', 0], 'vae': ['1', 2]}},
        '8': {'class_type': 'SaveImage', 'inputs': {'images': ['7', 0], 'filename_prefix': f'sf7_v_{name}'}},
    }
    pid = post('/prompt', {'prompt': g, 'front': True})['prompt_id']
    while True:
        time.sleep(1.5)
        h = json.loads(urllib.request.urlopen(f'{API}/history/{pid}').read())
        if pid in h:
            i = h[pid]['outputs']['8']['images'][0]
            return Image.open(os.path.join(COMFY, 'output', i.get('subfolder', ''), i['filename'])).convert('RGB')

if __name__ == '__main__':
    src, pre, dn, n = sys.argv[1], sys.argv[2], float(sys.argv[3]), int(sys.argv[4])
    prompt = open(sys.argv[5], encoding='utf-8').read() if len(sys.argv) > 5 else PROMPT
    im = Image.open(src)
    for k in range(n):
        img2img(im, prompt, dn, random.randint(1, 2 ** 31), f'{os.path.basename(pre)}_{k}').save(f'{pre}_{k}.jpg', quality=93)
        print(k, flush=True)
