"""Front reference views of the captain for image-to-3D."""
import os, json, time, urllib.request, shutil
COMFY = r'D:\AI\comfyui\ComfyUI'; API = 'http://127.0.0.1:8188'
OUT = r'\\192.168.1.50\ai-workspace\starflight\step8'

def post(path, obj):
    r = urllib.request.Request(API + path, json.dumps(obj).encode(), {'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(r).read())

def txt2img(prompt, w, h, prefix, seed):
    g = {
        '1': {'class_type': 'CheckpointLoaderSimple', 'inputs': {'ckpt_name': 'flux1-schnell-fp8.safetensors'}},
        '2': {'class_type': 'CLIPTextEncode', 'inputs': {'clip': ['1', 1], 'text': prompt}},
        '3': {'class_type': 'CLIPTextEncode', 'inputs': {'clip': ['1', 1], 'text': ''}},
        '4': {'class_type': 'EmptySD3LatentImage', 'inputs': {'width': w, 'height': h, 'batch_size': 1}},
        '6': {'class_type': 'KSampler', 'inputs': {'model': ['1', 0], 'positive': ['2', 0], 'negative': ['3', 0], 'latent_image': ['4', 0],
              'seed': seed, 'steps': 4, 'cfg': 1.0, 'sampler_name': 'euler', 'scheduler': 'simple', 'denoise': 1.0}},
        '7': {'class_type': 'VAEDecode', 'inputs': {'samples': ['6', 0], 'vae': ['1', 2]}},
        '8': {'class_type': 'SaveImage', 'inputs': {'images': ['7', 0], 'filename_prefix': prefix}},
    }
    pid = post('/prompt', {'prompt': g})['prompt_id']
    while True:
        time.sleep(2)
        h_ = json.loads(urllib.request.urlopen(f'{API}/history/{pid}').read())
        if pid in h_:
            i = h_[pid]['outputs']['8']['images'][0]
            return os.path.join(COMFY, 'output', i.get('subfolder', ''), i['filename'])

P = ('full body 3D character render of a starship captain in a sci-fi spacesuit, standing in A-pose, arms slightly away from the body, '
     'front view facing the camera, symmetrical, whole figure visible head to boots, '
     'dark slate grey armoured spacesuit with lighter grey chest plate and segmented belt, round helmet with large amber tinted visor, '
     'small backpack with glowing orange light tubes, black gloves, black boots, knee pads, '
     'plain white background, soft studio lighting, game character model, no shadow')
if __name__ == '__main__':
    for i, seed in enumerate([11, 23, 37, 51]):
        shutil.copy(txt2img(P, 768, 1152, f'sf8_front_{i}', seed), rf'{OUT}\front_{i}.png'); print(i, flush=True)
