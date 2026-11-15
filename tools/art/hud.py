"""In-flight HUD and shared panels in the scene+glass style.
Writes name.png (+@2x/@4x) beside each original; a4sdl loads a PNG that
sits next to a requested .bmp/.tga in its place.
usage: hud.py <bin/data> <preview dir>"""
import os, sys, re
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

DATA, PREV = sys.argv[1], sys.argv[2]
os.makedirs(PREV, exist_ok=True)
FONTS = r'\\192.168.1.50\ai-workspace\starflight\fonts'
K = 4
INK = (238, 244, 255); ACC = (143, 216, 255)
GLASS = (10, 16, 28); SCREEN = (5, 9, 16)
done = []

def font(weight, px):
    f = {300: 'Light', 400: 'Regular', 500: 'Medium', 600: 'SemiBold'}[weight]
    return ImageFont.truetype(os.path.join(FONTS, f'barlowcondensed_BarlowCondensed-{f}.ttf'), round(px * K))

def save(rel, im4):
    stem = os.path.join(DATA, os.path.splitext(rel)[0])
    w, h = im4.width // K, im4.height // K
    im4.save(stem + '@4x.png')
    im4.resize((w * 2, h * 2), Image.LANCZOS).save(stem + '@2x.png')
    im4.resize((w, h), Image.LANCZOS).save(stem + '.png')
    done.append(rel)

def load(rel):
    return Image.open(os.path.join(DATA, rel)).convert('RGBA')

def is_magenta(a):
    return (a[:, :, 0] > 240) & (a[:, :, 1] < 20) & (a[:, :, 2] > 240)

def disk(r):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))

# ------------------------------------------------------------------ frames
def frame(rel, radius=12, drop_thin=6, screen_lum=75):
    """A clean glass rectangle over the frame's main body, with its main
    window (enclosed magenta or a dark screen) as an inner rectangle."""
    src = load(rel); a = np.array(src).astype(int)
    h, w = a.shape[:2]
    mag = is_magenta(a)
    if rel.lower().endswith('.tga'):
        mag |= a[:, :, 3] < 128
    lab = cv2.connectedComponents(mag.astype(np.uint8), connectivity=4)[1]
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    outside = mag & np.isin(lab, [l for l in border if l != 0] or [-1])
    hole = mag & ~outside
    body = (~outside).astype(np.uint8)
    body = cv2.morphologyEx(body, cv2.MORPH_OPEN, disk(drop_thin))
    n, l, st, _ = cv2.connectedComponentsWithStats(body, connectivity=4)
    if n < 2: return
    i = 1 + int(np.argmax(st[1:, 4])); bx, by, bw, bh = [int(v) for v in st[i, :4]]
    lum = a[:, :, :3].mean(2)
    inner, kind = None, None
    for m, k in ((hole, 'hole'), ((~mag) & (lum < screen_lum), 'screen')):
        n2, l2, st2, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=4)
        if n2 > 1:
            j = 1 + int(np.argmax(st2[1:, 4]))
            x, y, ww, hh, area = [int(v) for v in st2[j]]
            if ww * hh > .2 * bw * bh and area > .5 * ww * hh:
                inner, kind = (x, y, ww, hh), k; break
    W, H = w * K, h * K
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    R = min(radius, bw // 4, bh // 4) * K
    box = (bx * K, by * K, (bx + bw) * K - 1, (by + bh) * K - 1)
    d.rounded_rectangle(box, radius=R, fill=GLASS + (200,))
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    n_s = max(1, min(bh * K // 3, 60 * K))
    for k in range(n_s):
        sd.line((box[0], box[1] + k, box[2], box[1] + k), fill=(255, 255, 255, round(16 * (1 - k / n_s))))
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).rounded_rectangle(box, radius=R, fill=255)
    im = Image.composite(Image.alpha_composite(im, sh), im, m)
    d = ImageDraw.Draw(im)
    if inner:
        x, y, ww, hh = inner
        ib = (x * K, y * K, (x + ww) * K - 1, (y + hh) * K - 1)
        ri = max(2 * K, R - 4 * K)
        cut = Image.new('L', (W, H), 0); ImageDraw.Draw(cut).rounded_rectangle(ib, radius=ri, fill=255)
        c = np.array(cut) > 0
        arr = np.array(im)
        arr[c] = (SCREEN[0], SCREEN[1], SCREEN[2], 110 if kind == 'hole' else 205)
        im = Image.fromarray(arr, 'RGBA'); d = ImageDraw.Draw(im)
        d.rounded_rectangle(ib, radius=ri, outline=(255, 255, 255, 34), width=K)
    d.rounded_rectangle(box, radius=R, outline=(255, 255, 255, 62), width=K)
    save(rel, im)
    return im

# ------------------------------------------------------------------ gauges
SOFT = {}
def bar_colour(rel):
    a = np.array(load(rel)).astype(int)
    m = ~is_magenta(a)
    px = a[m][:, :3]
    sat = px.max(1) - px.min(1)
    px = px[sat > 60] if (sat > 60).sum() > 20 else px
    c = np.median(px, 0)
    # soften: pull toward a bright, slightly desaturated tone
    hsv = cv2.cvtColor(np.uint8([[c]]), cv2.COLOR_RGB2HSV)[0, 0].astype(int)
    hsv[1] = min(hsv[1], 170); hsv[2] = max(hsv[2], 225)
    return tuple(int(v) for v in cv2.cvtColor(np.uint8([[hsv]]), cv2.COLOR_HSV2RGB)[0, 0])

def gauge(rel, colour=None, thick=.5):
    w, h = Image.open(os.path.join(DATA, rel)).size
    col = colour or bar_colour(rel)
    W, H = w * K, h * K
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    t = max(4 * K, round(h * thick * K)); y0 = (H - t) // 2
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle((K, y0, W - K, y0 + t), radius=t // 2, fill=col + (110,))
    im = Image.alpha_composite(im, glow.filter(ImageFilter.GaussianBlur(2 * K)))
    bar = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(bar)
    d.rounded_rectangle((K, y0, W - K, y0 + t), radius=t // 2, fill=col + (255,))
    # light top half
    hi = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(hi).rounded_rectangle((2 * K, y0 + K, W - 2 * K, y0 + t // 2), radius=t // 4, fill=(255, 255, 255, 70))
    im = Image.alpha_composite(Image.alpha_composite(im, bar), hi)
    save(rel, im)

def track(rel, w=None, h=None, thick=.5):
    if w is None: w, h = Image.open(os.path.join(DATA, rel)).size
    W, H = w * K, h * K
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    t = max(4 * K, round(h * thick * K)); y0 = (H - t) // 2
    ImageDraw.Draw(im).rounded_rectangle((K, y0, W - K, y0 + t), radius=t // 2, fill=(255, 255, 255, 26), outline=(255, 255, 255, 50), width=K)
    save(rel, im)

# ------------------------------------------------------------------ buttons
def panel(w, h, state, radius=10, accent=ACC):
    W, H = w * K, h * K
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    box = (K, K, W - 1 - K, H - 1 - K); r = min(radius * K, (H - 2 * K) // 2)
    if state == 'over':
        d.rounded_rectangle(box, radius=r, fill=(20, 34, 52, 215), outline=accent + (235,), width=round(1.5 * K))
    elif state == 'select':
        d.rounded_rectangle(box, radius=r, fill=accent + (95,), outline=accent + (255,), width=round(1.5 * K))
    elif state == 'disabled':
        d.rounded_rectangle(box, radius=r, fill=(10, 14, 22, 120), outline=(255, 255, 255, 30), width=K)
    else:
        d.rounded_rectangle(box, radius=r, fill=GLASS + (180,), outline=(255, 255, 255, 62), width=K)
    if state != 'disabled':
        sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
        n = int((H - 2 * K) * .45)
        for i in range(n):
            sd.line((box[0] + 2 * K, box[1] + K + i, box[2] - 2 * K, box[1] + K + i), fill=(255, 255, 255, round(20 * (1 - i / n))))
        im = Image.alpha_composite(im, sh)
    return im

def label(im, s, px, fill, track_=2, weight=500):
    d = ImageDraw.Draw(im); ft = font(weight, px)
    total = sum(ft.getlength(c) for c in s) + track_ * K * (len(s) - 1)
    l, t, r, b = ft.getbbox('HEXAGON')
    x = (im.width - total) / 2; y = (im.height - (b - t)) / 2 - t
    for c in s:
        d.text((x, y), c, font=ft, fill=fill); x += ft.getlength(c) + track_ * K
    return im

def button(rel, state, radius=10, text=None, px=None):
    w, h = Image.open(os.path.join(DATA, rel)).size
    im = panel(w, h, state, radius)
    if text:
        col = {'disabled': INK + (90,), 'select': (255, 255, 255, 255)}.get(state, INK + (255,))
        label(im, text, px or min(18, round(h * .42)), col)
    save(rel, im)

def glyph(rel, col=INK, inset=0):
    """black line icon on magenta -> light icon with alpha"""
    a = np.array(load(rel)).astype(int)
    h, w = a.shape[:2]
    mag = is_magenta(a)
    lum = a[:, :, :3].mean(2)
    alpha = np.where(mag, 0, np.clip((170 - lum) * 255 / 120, 0, 255) * .82)
    if inset:
        alpha[:inset] = 0; alpha[-inset:] = 0; alpha[:, :inset] = 0; alpha[:, -inset:] = 0
    ic = np.zeros((h, w, 4), np.uint8); ic[:, :, 0], ic[:, :, 1], ic[:, :, 2] = col; ic[:, :, 3] = alpha
    im = Image.fromarray(ic, 'RGBA').resize((w * K, h * K), Image.LANCZOS)
    save(rel, im)

def recolour_icons(rel, col):
    """TGA strip of icons (black / green / red): keep shapes, new colour"""
    im = load(rel); a = np.array(im).astype(int)
    h, w = a.shape[:2]
    mag = is_magenta(a)
    alpha = a[:, :, 3].copy()
    # strength from how far the pixel is from the background (alpha already set in these TGAs)
    out = np.zeros((h, w, 4), np.uint8); out[:, :, :3] = col; out[:, :, 3] = np.where(mag, 0, alpha)
    save(rel, Image.fromarray(out, 'RGBA').resize((w * K, h * K), Image.LANCZOS))

# ================================================================= content
def run():
    # shared frames
    for rel in ('messagegui/gui_aux.bmp', 'messagegui/gui_messagewindow.bmp', 'messagegui/gui_socket.bmp',
                'messagegui/gui_viewer.bmp', 'messagegui/gui_viewer_right.bmp', 'questviewer/quest_viewer.bmp',
                'medical/medical_gui_viewer.bmp', 'medical/medical_gui_viewer_left.bmp', 'medical/medical_gui_viewer_right.bmp',
                'engineer/gui.bmp', 'engineer/starmap_viewer.bmp', 'starmap/starmap_viewer.bmp',
                'controlpanel/gui_controlpanel.bmp', 'messagegui/gui_gauges.bmp'):
        if os.path.exists(os.path.join(DATA, rel)):
            frame(rel)
    # flat screen backgrounds
    for rel in ('engineer/eng_background.bmp',):
        w, h = Image.open(os.path.join(DATA, rel)).size
        im = Image.new('RGBA', (w * K, h * K), SCREEN + (215,)); save(rel, im)
    # top gauge bar with labels
    topgauge()
    # gauge fills
    for d in ('topgui', 'engineer', 'planetsurface'):
        for f in sorted(os.listdir(os.path.join(DATA, d))):
            if re.match(r'Element_(Small|Big)?Gauge_(?!Empty)\w+\.bmp$', f):
                gauge(f'{d}/{f}')
    if os.path.exists(os.path.join(DATA, 'planetsurface/Element_BigGauge_Empty.bmp')):
        track('planetsurface/Element_BigGauge_Empty.bmp')
    for f in sorted(os.listdir(os.path.join(DATA, 'medical'))):
        if f.startswith('med_bar_') and f.endswith('.bmp'): gauge('medical/' + f)
    # labelled surface bars: label + track
    for f, text in (('armor_bar.bmp', 'Armor'), ('cargo_bar.bmp', 'Cargo'), ('fuel_bar.bmp', 'Fuel'), ('hull_bar.bmp', 'Hull')):
        labelled_track('planetsurface/' + f, text)
    # buttons
    for d in ('controlpanel', 'planetsurface'):
        for base, rad in (('command_button_bg', 12), ('command_bigbutton_bg', 14)):
            for suf, st in (('', 'normal'), ('_disabled', 'disabled'), ('_mo', 'over'), ('_select', 'select')):
                rel = f'{d}/{base}{suf}.bmp'
                if os.path.exists(os.path.join(DATA, rel)): button(rel, st, rad)
    for f in sorted(os.listdir(os.path.join(DATA, 'controlpanel'))):
        if f.startswith('commandicon_') and f.endswith('.bmp'): glyph('controlpanel/' + f, inset=2)
        m = re.match(r'cp_(\w+)_(mo|select)\.bmp$', f)
        if m:
            name = {'captain': 'CAP', 'comm': 'COM', 'engineer': 'ENG', 'medical': 'MED', 'navigation': 'NAV', 'science': 'SCI', 'tactical': 'TAC'}[m.group(1)]
            button('controlpanel/' + f, 'select' if m.group(2) == 'select' else 'normal', 8, name, 15)
    for suf, st in (('_norm', 'normal'), ('_hov', 'over'), ('_dis', 'disabled')):
        button(f'medical/btn{suf}.bmp', st, 10)
    for suf, st in (('', 'normal'), ('_hov', 'over'), ('_dis', 'disabled')):
        button(f'medical/medical_captBtn{suf}.bmp', st, 8)
    button('cargohold/cargo_btn.bmp', 'normal', 8); button('cargohold/cargo_btn_mo.bmp', 'over', 8)
    for suf, st in (('', 'normal'), ('_over', 'over'), ('_dis', 'disabled')):
        button(f'pausemenu/button{suf}.tga', st, 14)
    for d in ('topgui', 'medical'):
        plus(f'{d}/icon_plus.bmp', True); plus(f'{d}/icon_plus_disabled.bmp', False)
    for f, st in (('aux_repair.bmp', 'normal'), ('aux_repair_hover.bmp', 'over')):
        w, h = Image.open(os.path.join(DATA, 'engineer/' + f)).size
        im = panel(w, h, st, 6); wrench(im, ACC if st == 'over' else INK); save('engineer/' + f, im)
    # pause menu panel and rule
    pm = Image.new('RGBA', (400 * K, 400 * K), (0, 0, 0, 0))
    ImageDraw.Draw(pm).rounded_rectangle((0, 0, 400 * K - 1, 400 * K - 1), radius=18 * K, fill=(8, 13, 24, 225), outline=(255, 255, 255, 56), width=K)
    save('pausemenu/pausemenu_bg.tga', pm)
    rule = Image.new('RGBA', (400 * K, 16 * K), (0, 0, 0, 0))
    ImageDraw.Draw(rule).rectangle((24 * K, 7 * K, 376 * K, 8 * K - 1), fill=(255, 255, 255, 60)); save('pausemenu/pausemenu_bar.tga', rule)
    # icon strips
    for d in ('medical',):
        recolour_icons(f'{d}/Icons_small.tga', INK)
        recolour_icons(f'{d}/Icons_small_Green.tga', (110, 232, 150))
        recolour_icons(f'{d}/Icons_small_Red.tga', (255, 105, 95))

def plus(rel, enabled):
    w, h = Image.open(os.path.join(DATA, rel)).size
    im = panel(w, h, 'normal' if enabled else 'disabled', 5)
    d = ImageDraw.Draw(im); c = (ACC + (255,)) if enabled else (INK + (80,))
    W = w * K; m = W // 2; s = W // 4; lw = max(K, W // 10)
    d.line((m - s, m, m + s, m), fill=c, width=lw); d.line((m, m - s, m, m + s), fill=c, width=lw)
    save(rel, im)

def wrench(im, col):
    d = ImageDraw.Draw(im); W = im.width; lw = max(K, W // 11)
    d.line((W * .3, W * .7, W * .62, W * .38), fill=col + (255,), width=lw)
    d.ellipse((W * .55, W * .2, W * .8, W * .45), outline=col + (255,), width=lw)

def labelled_track(rel, text):
    src = load(rel); a = np.array(src).astype(int); h, w = a.shape[:2]
    # the pipe starts where light grey columns begin
    grey = (np.abs(a[:, :, 0] - a[:, :, 1]) < 18) & (np.abs(a[:, :, 1] - a[:, :, 2]) < 18) & (a[:, :, :3].mean(2) > 140)
    cols = np.where(grey.sum(0) >= h * .3)[0]
    x0 = int(cols[0]) if len(cols) else w // 3
    W, H = w * K, h * K
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, W - 1, H - 1), radius=8 * K, fill=GLASS + (170,), outline=(255, 255, 255, 50), width=K)
    t = round(h * .38 * K); y0 = (H - t) // 2
    ImageDraw.Draw(im).rounded_rectangle((x0 * K, y0, W - 4 * K, y0 + t), radius=t // 2, fill=(255, 255, 255, 26), outline=(255, 255, 255, 50), width=K)
    lab = Image.new('RGBA', (x0 * K, H), (0, 0, 0, 0)); label(lab, text.upper(), min(15, h * .55), INK + (230,), 2)
    im.alpha_composite(lab, (0, 0))
    save(rel, im)

def topgauge():
    rel = 'topgui/topgauge.tga'
    w, h = Image.open(os.path.join(DATA, rel)).size        # 788 x 82
    W, H = w * K, h * K
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((10 * K, 2 * K, (w - 4) * K, 46 * K), radius=14 * K, fill=GLASS + (190,), outline=(255, 255, 255, 60), width=K)
    bars = ((89, 'HULL', (110, 232, 150)), (273, 'ARMOR', (255, 120, 105)), (464, 'SHIELDS', (110, 214, 255)), (630, 'FUEL', (255, 186, 92)))
    for x, name, col in bars:
        y = 15 if name != 'FUEL' else 14
        t = 10 * K; y0 = (y + 10) * K - t // 2
        d.rounded_rectangle(((x + 1) * K, y0, (x + 116) * K, y0 + t), radius=t // 2, fill=(255, 255, 255, 22), outline=(255, 255, 255, 46), width=K)
        lab = Image.new('RGBA', (80 * K, 20 * K), (0, 0, 0, 0))
        ft = font(500, 13); dl = ImageDraw.Draw(lab)
        tw = sum(ft.getlength(c) for c in name) + 2 * K * (len(name) - 1)
        cx = 80 * K - 8 * K - tw
        for c in name:
            dl.text((cx, 2 * K), c, font=ft, fill=col + (255,)); cx += ft.getlength(c) + 2 * K
        im.alpha_composite(lab, ((x - 80) * K, (y) * K))
    save(rel, im)

run()

# preview over a space scene
bg = Image.open(os.path.join(DATA, 'spacetravel', 'starfield.bmp')).convert('RGBA').resize((1600, 1000))
x = y = 10; rowh = 0
for rel in done:
    im = Image.open(os.path.join(DATA, os.path.splitext(rel)[0] + '@2x.png'))
    s = min(1, 360 / max(im.width, im.height)); im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))))
    if x + im.width > 1590: x = 10; y += rowh + 10; rowh = 0
    if y + im.height > 1000: break
    bg.alpha_composite(im, (x, y)); x += im.width + 10; rowh = max(rowh, im.height)
bg.convert('RGB').save(os.path.join(PREV, 'hud_preview.jpg'), quality=88)
print(len(done), 'images')
