"""Upgrade every ship sprite: Real-ESRGAN 8x -> Hunyuan3D mesh -> clean hybrid lighting -> game-ready file + before/after."""
import os, sys, json, time, glob, shutil, subprocess, urllib.request
import numpy as np, torch
import nvdiffrast.torch as dr
import trimesh
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

SHARE = r'\\192.168.1.50\ai-workspace\starflight\ships'
OUT = os.path.join(SHARE, 'batch'); os.makedirs(OUT, exist_ok=True)
DATA = os.path.join(os.environ['USERPROFILE'], r'Documents\GitHub\tlc-remaster\bin\data')
ROOT = r'D:\AI\comfyui\ComfyUI'; COMFY = 'http://127.0.0.1:8188'
ESR = glob.glob(os.path.join(os.environ['LOCALAPPDATA'], 'realesrgan', '**', 'realesrgan-ncnn-vulkan.exe'), recursive=True)[0]
TMP = os.path.join(os.environ['TEMP'], 'shipbatch'); os.makedirs(TMP, exist_ok=True)
dev = 'cuda'; glctx = dr.RasterizeCudaContext()
MAGENTA = (255, 0, 255)

SHIPS = [('military', 'engineer/high_res_ship_military.tga'), ('science', 'engineer/high_res_ship_science.tga'),
         ('freelance', 'engineer/high_res_ship_freelance.tga')] + \
        [(n, f'encounter/ship_{n}.bmp') for n in ('barzhon', 'coalition', 'elowan', 'minex', 'nyssian', 'pirate', 'spemin', 'tafel', 'thrynn')]
only = set(sys.argv[1:])

def log(*a): print(*a, flush=True)

def load_sprite(rel):
    im = Image.open(os.path.join(DATA, rel))
    if im.mode == 'RGBA':
        rgba = np.asarray(im, np.uint8).copy()
    else:
        rgb = np.asarray(im.convert('RGB'), np.uint8)
        a = ~np.all(rgb == MAGENTA, axis=2)
        rgba = np.dstack([rgb, a.astype(np.uint8) * 255])
    # give transparent pixels the nearest opaque color so the upscaler can't bleed magenta/white into edges
    a = rgba[..., 3] > 127
    idx = ndi.distance_transform_edt(~a, return_distances=False, return_indices=True)
    rgba[..., :3] = rgba[..., :3][idx[0], idx[1]]
    return rgba

def esrgan_8x(rgba, name):
    src = os.path.join(TMP, f'{name}_1x.png'); Image.fromarray(rgba, 'RGBA').save(src)
    p4, p16 = os.path.join(TMP, f'{name}_4x.png'), os.path.join(TMP, f'{name}_16x.png')
    for i, o in ((src, p4), (p4, p16)):
        subprocess.run([ESR, '-i', i, '-o', o, '-n', 'realesrgan-x4plus-anime', '-f', 'png'], cwd=os.path.dirname(ESR), capture_output=True, check=True)
    h, w = rgba.shape[:2]
    up = Image.open(p16).convert('RGB').resize((w * 8, h * 8), Image.LANCZOS)
    a8 = Image.fromarray(rgba[..., 3]).resize((w * 8, h * 8), Image.LANCZOS)
    return np.asarray(up, np.float32) / 255.0, np.asarray(a8) > 140

def comfy(wf):
    def post(path, body=None):
        r = urllib.request.Request(COMFY + path, data=json.dumps(body).encode() if body else None, headers={'Content-Type': 'application/json'})
        return json.load(urllib.request.urlopen(r, timeout=120))
    r = post('/prompt', {'prompt': wf})
    if 'prompt_id' not in r: raise RuntimeError(json.dumps(r)[:1500])
    pid = r['prompt_id']
    while True:
        h = post('/history/' + pid)
        if pid in h:
            st = h[pid].get('status', {})
            if st.get('status_str') == 'error': raise RuntimeError(json.dumps(st)[:1500])
            if st.get('completed'): return
        time.sleep(2)

def hunyuan_mesh(col, alpha, name):
    sp = Image.fromarray(np.dstack([col * 255, alpha * 255]).astype(np.uint8), 'RGBA')
    S = 1024; s = sp.copy(); s.thumbnail((int(S * 0.9), int(S * 0.9)), Image.LANCZOS)
    c = Image.new('RGB', (S, S), (255, 255, 255)); c.paste(s, ((S - s.width) // 2, (S - s.height) // 2), s)
    c.save(os.path.join(ROOT, 'input', f'sfb_{name}.png'))
    prefix = f'3D/sfb_{name}'
    comfy({
        '1': {'class_type': 'LoadImage', 'inputs': {'image': f'sfb_{name}.png'}},
        '2': {'class_type': 'Hy3DModelLoader', 'inputs': {'model': 'hunyuan3d-dit-v2-0-fp16.safetensors', 'attention_mode': 'sdpa', 'cublas_ops': False}},
        '3': {'class_type': 'Hy3DGenerateMesh', 'inputs': {'pipeline': ['2', 0], 'image': ['1', 0], 'guidance_scale': 7.5, 'steps': 40, 'seed': 42,
                                                           'scheduler': 'FlowMatchEulerDiscreteScheduler', 'force_offload': True}},
        '4': {'class_type': 'Hy3DVAEDecode', 'inputs': {'vae': ['2', 1], 'latents': ['3', 0], 'box_v': 1.01, 'octree_resolution': 512,
                                                        'num_chunks': 8000, 'mc_level': 0.0, 'mc_algo': 'mc'}},
        '5': {'class_type': 'Hy3DPostprocessMesh', 'inputs': {'trimesh': ['4', 0], 'remove_floaters': False, 'remove_degenerate_faces': True,
                                                              'reduce_faces': True, 'max_facenum': 120000, 'smooth_normals': False}},
        '6': {'class_type': 'Hy3DExportMesh', 'inputs': {'trimesh': ['5', 0], 'filename_prefix': prefix, 'file_format': 'glb', 'save_file': True}},
    })
    g = sorted(glob.glob(os.path.join(ROOT, 'output', '3D', f'sfb_{name}*.glb')), key=os.path.getmtime)[-1]
    shutil.copy(g, os.path.join(OUT, f'{name}.glb'))
    m = trimesh.load(g, force='mesh')
    return np.asarray(m.vertices, np.float32), np.asarray(m.faces, np.int32)

def raster(V, F, u, v, e, W, H, ss=1, normals=False):
    Vt = torch.tensor(V, device=dev); Ft = torch.tensor(F, device=dev)
    U, Vv, E = (torch.tensor(x, device=dev, dtype=torch.float32) for x in (u, v, e))
    pu, pv, pe = Vt @ U, Vt @ Vv, Vt @ E
    nx = (pu - pu.min()) / (pu.max() - pu.min()) * 2 - 1
    ny = -((pv - pv.min()) / (pv.max() - pv.min()) * 2 - 1)
    nz = -(pe - pe.min()) / (pe.max() - pe.min() + 1e-9) * 0.9
    pos = torch.stack([nx, ny, nz, torch.ones_like(nx)], 1)[None].contiguous()
    rast, _ = dr.rasterize(glctx, pos, Ft, (H * ss, W * ss))
    cov = (rast[..., 3:4] > 0).float()
    if not normals:
        return cov.flip(1)[0, ..., 0].cpu().numpy()
    fn = torch.cross(Vt[Ft[:, 1]] - Vt[Ft[:, 0]], Vt[Ft[:, 2]] - Vt[Ft[:, 0]], dim=1)
    vn = torch.zeros_like(Vt).index_add_(0, Ft[:, 0], fn).index_add_(0, Ft[:, 1], fn).index_add_(0, Ft[:, 2], fn)
    vn = torch.nn.functional.normalize(vn, dim=1)
    n, _ = dr.interpolate(vn[None], rast, Ft); n = torch.nn.functional.normalize(n, dim=-1)
    sn = torch.stack([(n * U).sum(-1), (n * Vv).sum(-1), (n * E).sum(-1)], -1)   # screen: x right, y down, z to viewer
    out = torch.cat([sn, cov], -1).flip(1).permute(0, 3, 1, 2)
    out = torch.nn.functional.avg_pool2d(out, ss).permute(0, 2, 3, 1)[0].cpu().numpy()
    return out[..., :3], out[..., 3]

def best_orientation(V, F, alpha_box):
    hh, ww = alpha_box.shape
    k = 160 / max(hh, ww); sw, sh = max(8, int(ww * k)), max(8, int(hh * k))
    target = np.asarray(Image.fromarray(alpha_box.astype(np.uint8) * 255).resize((sw, sh), Image.BILINEAR), np.float32) / 255
    I = np.eye(3, dtype=np.float32); best = None
    for a in range(3):
        for s in (1, -1):
            e = I[a] * s; others = [b for b in range(3) if b != a]
            for ua, va in ((others[0], others[1]), (others[1], others[0])):
                for su in (1, -1):
                    for sv in (1, -1):
                        u, v = I[ua] * su, I[va] * sv
                        sil = raster(V, F, u, v, e, sw, sh)
                        iou = (sil * target).sum() / (np.maximum(sil, target).sum() + 1e-6)
                        # prefer views where the visible side faces the camera (more front-facing area is not knowable here; IoU decides)
                        if best is None or iou > best[0]: best = (iou, u, v, e)
    return best

Lr = np.array([-0.55, -0.62, 0.56], np.float32); Lr /= np.linalg.norm(Lr)
Hv = Lr + np.array([0, 0, 1], np.float32); Hv /= np.linalg.norm(Hv)

def hybrid(col, alpha, V, F):
    ys, xs = np.nonzero(alpha); x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    TH, TW = alpha.shape
    iou, u, v, e = best_orientation(V, F, alpha[y0:y1 + 1, x0:x1 + 1])
    # the side facing the camera: if the opposite side matches equally, pick the one whose normals face us more (top side)
    sn, cov = raster(V, F, u, v, e, x1 - x0 + 1, y1 - y0 + 1, ss=2, normals=True)
    sn2, cov2 = raster(V, F, u * np.array([-1, -1, -1], np.float32) * -1, v, -e, x1 - x0 + 1, y1 - y0 + 1, ss=1, normals=True)
    mn = np.zeros((TH, TW, 3), np.float32); mc = np.zeros((TH, TW), np.float32)
    mn[y0:y1 + 1, x0:x1 + 1] = sn; mc[y0:y1 + 1, x0:x1 + 1] = cov
    mn /= np.maximum(np.linalg.norm(mn, axis=2, keepdims=True), 1e-6)
    scale = max(x1 - x0, y1 - y0) / 2736.0      # tune blur/bevel sizes to the sprite's size (military = 1.0)
    sc = lambda px: max(1.0, px * max(scale, 0.18))
    mesh_shade = 0.28 + 0.95 * np.clip((mn * Lr).sum(2), 0, 1)
    rgb = col
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    dist = ndi.distance_transform_edt(alpha)
    bevel = np.clip(dist / max(6.0, 26.0 * max(scale, 0.25)), 0, 1) ** 0.6
    h = (bevel + ndi.gaussian_filter(lum, sc(6)) * 0.55 + (lum - ndi.gaussian_filter(lum, sc(3))) * 1.2 - np.clip(0.18 - lum, 0, None) * 1.5) * alpha
    h = ndi.gaussian_filter(h, 1.2)
    gy, gx = np.gradient(h * 9.0)
    nrm = np.dstack([-gx, -gy, np.ones_like(h)]); nrm /= np.linalg.norm(nrm, axis=2, keepdims=True)
    spr_shade = 0.30 + 0.95 * np.clip((nrm * Lr).sum(2), 0, 1)
    ao = 1.0 - np.clip((ndi.gaussian_filter(h, sc(10)) - h) * 3.2, 0, 0.55)
    spr_low = ndi.gaussian_filter(spr_shade, sc(10))
    spr_detail = spr_shade / np.maximum(spr_low, 1e-3)
    bl = sc(9)
    mesh_low = ndi.gaussian_filter(mesh_shade * mc, bl) / np.maximum(ndi.gaussian_filter(mc, bl), 1e-3)
    w = ndi.gaussian_filter((mc > 0.5).astype(np.float32) * alpha, sc(8))
    w = np.clip(w * 1.15, 0, 1) * alpha
    # trust the mesh less when its silhouette is a poor match overall
    w *= np.clip((iou - 0.45) / 0.3, 0, 1)
    big = mesh_low * w + spr_low * (1 - w)
    shade = big * spr_detail * ao
    nb = ndi.gaussian_filter(mn, (bl, bl, 0)) * w[..., None] + nrm * (1 - w[..., None])
    nmix = nb + (nrm - ndi.gaussian_filter(nrm, (sc(6), sc(6), 0)))
    nmix /= np.maximum(np.linalg.norm(nmix, axis=2, keepdims=True), 1e-6)
    sat = rgb.max(2) - rgb.min(2)
    spec = np.clip((nmix * Hv).sum(2), 0, 1) ** 40 * np.clip(0.7 - sat * 1.5, 0.12, 0.7)
    emis = np.clip((rgb[..., 0] - rgb[..., 1] - 0.18) * 2.2, 0, 1) * (rgb[..., 0] > 0.55)
    c = rgb * shade[..., None] + spec[..., None] * np.array([1.0, 0.97, 0.94])
    c = c * (1 - emis[..., None] * 0.5) + rgb * emis[..., None] * 0.62
    c = np.clip(c, 0, 1)
    A = ndi.gaussian_filter(ndi.binary_opening(alpha, iterations=2).astype(np.float32), 1.2)
    band = (ndi.distance_transform_edt(alpha) < 6) & alpha
    l2 = c.mean(2); cap = ndi.median_filter(l2, 9)
    c = np.where((band & (l2 > cap * 1.15))[..., None], c * (cap / np.maximum(l2, 1e-3))[..., None], c)
    return Image.fromarray(np.dstack([c * 255, A * 255]).astype(np.uint8), 'RGBA'), iou, float((w > 0.5).sum() / alpha.sum())

def save_game(master, rel, name, size):
    gdir = os.path.join(OUT, 'game', os.path.dirname(rel)); os.makedirs(gdir, exist_ok=True)
    g = master.resize(size, Image.LANCZOS)
    if rel.endswith('.tga'):
        g.save(os.path.join(gdir, os.path.basename(rel)))
    else:   # Allegro magenta-keyed BMP, hard edge
        arr = np.asarray(g, np.uint8)
        rgb = arr[..., :3].copy()
        ism = np.all(rgb == MAGENTA, axis=2); rgb[ism] = (254, 0, 254)
        rgb[arr[..., 3] < 128] = MAGENTA
        Image.fromarray(rgb, 'RGB').save(os.path.join(gdir, os.path.basename(rel)))
    for k in (2, 4):
        master.resize((size[0] * k, size[1] * k), Image.LANCZOS).save(os.path.join(OUT, f'{name}_{size[0]*k}x{size[1]*k}.png'))

def before_after(orig_rgba, master, name, target_h):
    h, w = orig_rgba.shape[:2]
    k = max(1, round(target_h / h))
    a_ = Image.fromarray(orig_rgba, 'RGBA'); a_.putalpha(Image.fromarray((orig_rgba[..., 3] > 127).astype(np.uint8) * 255))
    left = a_.resize((w * k, h * k), Image.NEAREST)
    right = master.resize((w * k, h * k), Image.LANCZOS)
    pad, lab = 50, 60
    sheet = Image.new('RGB', (2 * (w * k + 2 * pad), h * k + 2 * pad + lab), (10, 12, 22))
    sheet.paste(left, (pad, pad + lab), left); sheet.paste(right, (w * k + 3 * pad, pad + lab), right)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 18), f'{name}: before (game file)', fill=(230, 230, 240), font_size=30)
    d.text((w * k + 3 * pad, 18), 'after', fill=(230, 230, 240), font_size=30)
    p = os.path.join(OUT, f'before_after_{name}.jpg'); sheet.save(p, quality=91)
    return p

for name, rel in SHIPS:
    if only and name not in only: continue
    t0 = time.time()
    orig = load_sprite(rel)
    h, w = orig.shape[:2]
    if name == 'military':      # already approved look: reuse it
        master = Image.open(os.path.join(SHARE, 'military_h3dclean_8x.png')).convert('RGBA'); iou, trust = 0, 0
    else:
        col, alpha = esrgan_8x(orig, name)
        V, F = hunyuan_mesh(col, alpha, name)
        master, iou, trust = hybrid(col, alpha, V, F)
    master.save(os.path.join(OUT, f'{name}_8x.png'))
    save_game(master, rel, name, (w, h))
    p = before_after(orig, master, name, 1300 if h > 200 else 520)
    log(f'{name}: {time.time() - t0:.0f}s  mesh match {iou:.2f}  mesh shaping {trust*100:.0f}%  -> {os.path.basename(p)} {os.path.getsize(p)}')
log('done')
