"""Unpack Allegro 4 datafiles (as read by a4sdl/a4_load.cpp) into plain image files.

usage: dat_extract.py <data_dir> [--write]
Without --write it only reports. With --write, for each data/<m>/<name>.dat:
  * a bitmap identical to a loose file already in the folder reuses that file;
  * any other bitmap is written to data/<m>/from_dat/ (RGBA -> .tga, RGB -> .bmp),
    so loose files that other code loads directly are never changed;
  * data/<m>/<name>.assets lists the objects in order (the order the game's
    #defines index), '?' marking non-image objects.
"""
import os, sys, struct, glob
import numpy as np
from PIL import Image

def DAT_ID(s): return struct.unpack('>I', s.encode())[0]
F_PACK, F_NOPACK = 0x736C6821, 0x736C682E
DAT_MAGIC, PROP, BMP, FILE_ = DAT_ID('ALL.'), DAT_ID('prop'), DAT_ID('BMP '), DAT_ID('FILE')
NAME = DAT_ID('NAME')

def lzss(src, pos, end, out_len=-1):
    N, F, TH = 4096, 18, 2
    buf = bytearray(N); r = N - F; flags = 0; out = bytearray()
    while pos < end and (out_len < 0 or len(out) < out_len):
        flags >>= 1
        if (flags & 256) == 0:
            flags = src[pos] | 0xFF00; pos += 1
            if pos >= end: break
        if flags & 1:
            c = src[pos]; pos += 1; buf[r] = c; r = (r + 1) & (N - 1); out.append(c)
        else:
            if pos + 1 >= end: break
            i, j = src[pos], src[pos + 1]; pos += 2
            i |= (j & 0xF0) << 4; j = (j & 0x0F) + TH
            for k in range(j + 1):
                if out_len >= 0 and len(out) >= out_len: break
                c = buf[(i + k) & (N - 1)]; buf[r] = c; r = (r + 1) & (N - 1); out.append(c)
    return bytes(out)

class R:
    def __init__(s, b, pos=0): s.b, s.p = b, pos
    def l(s): v = struct.unpack('>i', s.b[s.p:s.p + 4])[0]; s.p += 4; return v
    def w(s): v = struct.unpack('>h', s.b[s.p:s.p + 2])[0]; s.p += 2; return v

def read_bitmap(body):
    r = R(body); bits = r.w(); rgba = bits < 0; bits = abs(bits)
    w, h = r.w() & 0xFFFF, r.w() & 0xFFFF
    d = body[6:]
    if bits in (24, 32):
        ch = 4 if rgba else 3
        a = np.frombuffer(d[:w * h * ch], np.uint8).reshape(h, w, ch)
        return Image.fromarray(a, 'RGBA' if rgba else 'RGB'), bits, rgba
    if bits in (15, 16):
        c = np.frombuffer(d[:w * h * 2], '<u2').reshape(h, w).astype(np.uint32)
        rgb = np.dstack([((c >> 11) & 31) * 255 // 31, ((c >> 5) & 63) * 255 // 63, (c & 31) * 255 // 31]).astype(np.uint8)
        return Image.fromarray(rgb, 'RGB'), bits, False
    return None, bits, rgba

def read_objects(b, pos):
    r = R(b, pos); count = r.l(); objs = []; props = {}
    while len(objs) < count:
        t = r.l()
        if t == PROP:
            pt = r.l(); size = r.l(); props[pt] = b[r.p:r.p + size].decode('latin-1'); r.p += size; continue
        fsize, dsize = r.l(), r.l()
        raw = b[r.p:r.p + fsize]; r.p += fsize
        body = lzss(raw, 0, len(raw), -dsize) if dsize < 0 else raw[:dsize] if dsize < len(raw) else raw
        name = props.get(NAME, f'OBJ{len(objs)}')
        if t == BMP:
            img, bits, rgba = read_bitmap(body); objs.append(('BMP', name, img, bits, rgba))
        elif t == FILE_:
            objs.append(('FILE', name, read_objects(body, 0), 0, False))
        else:
            objs.append((struct.pack('>I', t).decode('latin-1'), name, body, 0, False))
        props = {}
    return objs

def load(path):
    f = open(path, 'rb').read()
    m = struct.unpack('>I', f[:4])[0]
    body = lzss(f, 4, len(f)) if m == F_PACK else f[4:] if m == F_NOPACK else None
    assert body and struct.unpack('>I', body[:4])[0] == DAT_MAGIC, path
    return read_objects(body, 4)

def filename_for(name, rgba):
    base = name.lower()
    for ext in ('_tga', '_bmp', '_pcx', '_png'):
        if base.endswith(ext): base = base[:-len(ext)]; break
    return base + ('.tga' if rgba else '.bmp')

def find_loose(folder, fn):
    """the real file name (any case) of a loose file in folder, or None"""
    low = fn.lower()
    for f in os.listdir(folder):
        if f.lower() == low and os.path.isfile(os.path.join(folder, f)): return f
    return None

def identical(img, path):
    o = Image.open(path)
    if o.size != img.size: return False
    a = np.asarray(o.convert('RGBA'), np.int16); b = np.asarray(img.convert('RGBA'), np.int16)
    if img.mode == 'RGB': a, b = a[..., :3], b[..., :3]
    return int(np.abs(a - b).max()) == 0

data = sys.argv[1]; write = '--write' in sys.argv
totals = {'reused': 0, 'extracted': 0, 'slots': 0}
for dat in sorted(glob.glob(os.path.join(data, '**', '*.dat'), recursive=True)):
    objs = load(dat); folder = os.path.dirname(dat)
    index = []
    for i, (kind, name, payload, bits, rgba) in enumerate(objs):
        if kind == 'BMP' and payload is not None:
            fn = filename_for(name, rgba)
            loose = find_loose(folder, fn)
            if loose and identical(payload, os.path.join(folder, loose)):
                index.append(loose); totals['reused'] += 1
            else:
                rel = 'from_dat/' + fn
                if write:
                    os.makedirs(os.path.join(folder, 'from_dat'), exist_ok=True)
                    payload.save(os.path.join(folder, 'from_dat', fn))
                index.append(rel); totals['extracted'] += 1
        else:
            index.append(f'?{name}'); totals['slots'] += 1
    print(f'{os.path.relpath(dat, data)}: ' + ', '.join(index))
    if write:
        with open(os.path.splitext(dat)[0] + '.assets', 'w', newline='\n') as fh:
            fh.write(f'# images for code that indexes this group, in object order (formerly {os.path.basename(dat)})\n')
            fh.write('\n'.join(index) + '\n')
print(totals)
