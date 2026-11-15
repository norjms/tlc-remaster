"""Glass buttons and widgets in the scene+glass style, drawn at 4x.
Each image is written next to the original as name.png (RGBA, 1x) plus
name@2x.png and name@4x.png, and the module's .assets list is pointed at
the PNG. a4sdl blends PNGs with alpha wherever the game masks.
usage: buttons.py <bin/data dir> [preview.png]
"""
import os, sys, re
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

DATA = sys.argv[1]; PREV = sys.argv[2] if len(sys.argv) > 2 else None
FONTS = r'\\192.168.1.50\ai-workspace\starflight\fonts'
K = 4
INK = (238, 244, 255)
ACC = (143, 216, 255)          # title accent
RED = (255, 122, 104)

_fc = {}
def font(weight, px):
    key = (weight, px)
    if key not in _fc:
        f = {300: 'Light', 400: 'Regular', 500: 'Medium', 600: 'SemiBold'}[weight]
        _fc[key] = ImageFont.truetype(os.path.join(FONTS, f'barlowcondensed_BarlowCondensed-{f}.ttf'), round(px * K))
    return _fc[key]

def label(im, s, px, fill, track=2, box=None):
    d = ImageDraw.Draw(im)
    ft = font(500, px)
    s = s.upper()
    total = sum(ft.getlength(c) for c in s) + track * K * (len(s) - 1)
    bx, by, bw, bh = box or (0, 0, im.width, im.height)
    l, t, r, b = ft.getbbox('HEXAGON')
    x = bx + (bw - total) / 2
    y = by + (bh - (b - t)) / 2 - t
    for c in s:
        d.text((x, y), c, font=ft, fill=fill)
        x += ft.getlength(c) + track * K

def panel(w, h, state, radius=None, accent=ACC, inset=1, fill_a=None):
    """state: normal, over, disabled, on. Returns a 4x RGBA image."""
    W, H = w * K, h * K
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    I = inset * K
    box = (I, I, W - 1 - I, H - 1 - I)
    bh = box[3] - box[1]
    r = (min(bh / 2, 24 * K) if radius is None else radius * K)
    d = ImageDraw.Draw(im)
    if state == 'over':
        d.rounded_rectangle(box, radius=r, fill=(12, 22, 36, 205))
        tint = Image.new('RGBA', (W, H), accent + (64,))
        m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).rounded_rectangle(box, radius=r, fill=255)
        im = Image.composite(Image.alpha_composite(im, tint), im, m)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle(box, radius=r, outline=accent + (235,), width=round(1.5 * K))
    elif state == 'on':
        d.rounded_rectangle(box, radius=r, fill=accent + (235,))
    elif state == 'disabled':
        d.rounded_rectangle(box, radius=r, fill=(10, 14, 22, 110), outline=(255, 255, 255, 30), width=K)
    else:
        d.rounded_rectangle(box, radius=r, fill=(10, 16, 28, fill_a or 165), outline=(255, 255, 255, 62), width=K)
    if state in ('normal', 'over'):
        # soft top sheen
        sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        for i in range(int(bh * .45)):
            a = round(22 * (1 - i / (bh * .45)))
            sd.line((box[0], box[1] + i, box[2], box[1] + i), fill=(255, 255, 255, a))
        m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).rounded_rectangle((box[0] + K, box[1] + K, box[2] - K, box[3] - K), radius=max(0, r - K), fill=255)
        im = Image.alpha_composite(im, Image.composite(sh, Image.new('RGBA', (W, H), (0, 0, 0, 0)), m))
    return im

def fg(state):
    return {'over': (255, 255, 255, 255), 'on': (6, 16, 26, 255), 'disabled': INK + (90,)}.get(state, INK + (255,))

# ---------------------------------------------------------------- icons
def icon(im, kind, col, size=None):
    W, H = im.size
    s = size or min(W, H) * .42
    cx, cy = W / 2, H / 2
    d = ImageDraw.Draw(im)
    lw = max(K, round(min(W, H) * .07))
    h = s / 2
    if kind == 'plus':
        d.line((cx - h, cy, cx + h, cy), fill=col, width=lw); d.line((cx, cy - h, cx, cy + h), fill=col, width=lw)
    elif kind == 'minus':
        d.line((cx - h, cy, cx + h, cy), fill=col, width=lw)
    elif kind == 'x':
        h *= .8
        d.line((cx - h, cy - h, cx + h, cy + h), fill=col, width=lw); d.line((cx - h, cy + h, cx + h, cy - h), fill=col, width=lw)
    elif kind == 'play':
        h *= .85
        d.polygon(((cx - h * .7, cy - h), (cx + h, cy), (cx - h * .7, cy + h)), fill=col)
    elif kind == 'save':                       # arrow down into a tray
        d.line((cx, cy - h, cx, cy + h * .35), fill=col, width=lw)
        d.line((cx - h * .5, cy - h * .1, cx, cy + h * .4), fill=col, width=lw); d.line((cx + h * .5, cy - h * .1, cx, cy + h * .4), fill=col, width=lw)
        d.line((cx - h, cy + h * .45, cx - h, cy + h), fill=col, width=lw); d.line((cx - h, cy + h, cx + h, cy + h), fill=col, width=lw); d.line((cx + h, cy + h, cx + h, cy + h * .45), fill=col, width=lw)
    elif kind in ('up', 'down'):
        k = -1 if kind == 'up' else 1
        d.line((cx - h, cy - k * h * .45, cx, cy + k * h * .45), fill=col, width=lw); d.line((cx + h, cy - k * h * .45, cx, cy + k * h * .45), fill=col, width=lw)
    elif kind == 'help':
        ft = font(600, min(W, H) / K * .55)
        l, t, r, b = ft.getbbox('?')
        d.text((cx - (r + l) / 2, cy - (b + t) / 2), '?', font=ft, fill=col)
    return im

# ---------------------------------------------------------------- output
written = []
def save(rel, im4):
    stem = os.path.splitext(rel)[0]
    dst = os.path.join(DATA, stem)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    w, h = im4.width // K, im4.height // K
    im4.save(dst + '@4x.png')
    im4.resize((w * 2, h * 2), Image.LANCZOS).save(dst + '@2x.png')
    im4.resize((w, h), Image.LANCZOS).save(dst + '.png')
    written.append((rel, im4))

def size_of(rel):
    with Image.open(os.path.join(DATA, rel)) as im: return im.size

def btn(rel, state, text=None, ico=None, px=None, radius=None, accent=ACC, icol=None, fill_a=None):
    w, h = size_of(rel)
    im = panel(w, h, state, radius, accent, fill_a=fill_a)
    if text:
        label(im, text, px or min(20, round(h * .42)), fg(state))
    if ico:
        c = icol if (icol and state != 'disabled') else fg(state)
        if state == 'over' and icol: c = (255, 255, 255, 255)
        icon(im, ico, c)
    save(rel, im)

def set3(base, ext, text=None, ico=None, states=(('', 'normal'), ('_mouseover', 'over'), ('_disabled', 'disabled')), **kw):
    for suf, st in states:
        rel = f'{base}{suf}{ext}'
        if os.path.exists(os.path.join(DATA, rel)):
            btn(rel, st, text, ico, **kw)

def cursor(rel, on):
    w, h = size_of(rel)
    im = Image.new('RGBA', (w * K, h * K), (0, 0, 0, 0))
    if on:
        ImageDraw.Draw(im).rectangle((round(w * K / 2 - K), 4 * K, round(w * K / 2 + K), h * K - 4 * K), fill=ACC + (255,))
    save(rel, im)

def prompt_panel(rel, title=None):
    w, h = size_of(rel)
    W, H = w * K, h * K
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, W - 1, H - 1), radius=16 * K, fill=(8, 13, 24, 232), outline=(255, 255, 255, 56), width=K)
    d.rectangle((24 * K, 18 * K, 42 * K, 19 * K), fill=ACC + (255,))
    if title:
        ft = font(400, 30)
        d.text((24 * K, 28 * K), title, font=ft, fill=(255, 255, 255, 255))
    save(rel, im)

def profession(rel, ship_rel, over):
    w, h = size_of(rel)
    W, H = w * K, h * K
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    well = (16 * K, 5 * K, 313 * K, 145 * K)
    src = os.path.join(DATA, os.path.splitext(ship_rel)[0] + '@4x.png')
    ship = Image.open(src if os.path.exists(src) else os.path.join(DATA, ship_rel)).convert('RGBA')
    bb = ship.getbbox(); ship = ship.crop(bb)
    bw, bh = well[2] - well[0] - 24 * K, well[3] - well[1] - 20 * K
    k = min(bw / ship.width, bh / ship.height)
    ship = ship.resize((round(ship.width * k), round(ship.height * k)), Image.LANCZOS)
    if not over:
        a = ship.getchannel('A')
        ship = ImageEnhance.Brightness(ship.convert('RGB')).enhance(.62).convert('RGBA'); ship.putalpha(a)
    x = well[0] + (well[2] - well[0] - ship.width) // 2; y = well[1] + (well[3] - well[1] - ship.height) // 2
    if over:
        d = ImageDraw.Draw(im)
        d.rounded_rectangle(well, radius=10 * K, fill=ACC + (34,))
        glow = Image.new('RGBA', (W, H), (0, 0, 0, 0)); glow.alpha_composite(ship, (x, y))
        a = glow.getchannel('A').filter(ImageFilter.GaussianBlur(10 * K)).point(lambda v: v * .55)
        g = Image.new('RGBA', (W, H), ACC + (0,)); g.putalpha(a)
        im = Image.alpha_composite(im, g)
        ImageDraw.Draw(im).rounded_rectangle(well, radius=10 * K, outline=ACC + (235,), width=round(1.5 * K))
    im.alpha_composite(ship, (x, y))
    save(rel, im)

# ================================================================= screens
def creation():
    p = 'captaincreation/'
    set3(p + 'captaincreation_back', '.bmp', 'Back')
    set3(p + 'captaincreation_finish', '.bmp', 'Accept')
    set3(p + 'captaincreation_reset', '.bmp', 'Reset')
    set3(p + 'captaincreation_plus', '.bmp', ico='plus', radius=10)
    set3(p + 'from_dat/minus', '.bmp', ico='minus', radius=10)
    cursor(p + 'captaincreation_cursor0.bmp', True); cursor(p + 'captaincreation_cursor1.bmp', False)
    for prof, ship in (('scientific', 'science'), ('freelance', 'freelance'), ('military', 'military')):
        profession(f'{p}from_dat/captaincreation_{prof}.bmp', f'shipconfig/{ship}.tga', False)
        profession(f'{p}from_dat/captaincreation_{prof}_mouseover.bmp', f'shipconfig/{ship}.tga', True)

def lounge():
    p = 'captainslounge/'
    set3(p + 'captainslounge_del', '.tga', ico='x', radius=10, accent=RED, icol=RED + (255,))
    set3(p + 'captainslounge_plus', '.tga', ico='plus', radius=10)
    set3(p + 'from_dat/captainslounge_sel', '.tga', ico='play', radius=10)
    set3(p + 'from_dat/captainslounge_save', '.bmp', ico='save', radius=10)
    set3(p + 'captainslounge_yes', '.bmp', 'Yes')
    set3(p + 'captainslounge_no', '.bmp', 'No')
    set3(p + 'from_dat/generic_exit_btn', '.bmp', states=(('_norm', 'normal'), ('_over', 'over')))
    prompt_panel(p + 'from_dat/captainslounge_modalprompt_background.bmp')

PAIR = (('_norm', 'normal'), ('_over', 'over'))
HDO = (('', 'normal'), ('_hov', 'over'), ('_dis', 'disabled'))

def crewhire():
    p = 'crewhire/'
    set3(p + 'generic_exit_btn', '.bmp', states=PAIR)
    set3(p + 'personel_Btn', '.bmp', states=HDO)
    set3(p + 'personel_Btn2', '.bmp', states=HDO)
    # station rows: the game blits a 30px icon at the left end
    set3(p + 'personel_catBtn', '.bmp', states=HDO, radius=10, fill_a=120)

def cantina():
    p = 'cantina/'
    set3(p + 'cantina_exit_btn', '.bmp', states=PAIR)
    set3(p + 'cantina_Btn', '.bmp', states=HDO)

def depot():
    p = 'tradedepot/'
    set3(p + 'generic_exit_btn', '.bmp', states=PAIR)
    for b in ('tradedepot_btn', 'tradedepot_filterbtn', 'tradedepot_promptbtn'):
        set3(p + b, '.bmp', states=(('', 'normal'), ('_mo', 'over')))
    set3(p + 'tradedepot_spinupbtn', '.bmp', ico='up', radius=4, states=(('', 'normal'), ('_mo', 'over')))
    set3(p + 'tradedepot_spindownbtn', '.bmp', ico='down', radius=4, states=(('', 'normal'), ('_mo', 'over')))
    cursor(p + 'tradedepot_cursor0.bmp', True); cursor(p + 'tradedepot_cursor1.bmp', False)
    prompt_panel(p + 'from_dat/tradedepot_quantity_prompt.bmp', 'How many?')

def bank():
    p = 'bank/'
    set3(p + 'bank_button_exit', '.bmp', 'Exit', states=(('', 'normal'), ('_hover', 'over')))
    set3(p + 'bank_button_help', '.bmp', ico='help', radius=31, states=(('', 'normal'), ('_hover', 'over')))
    for b in ('confirm', 'pay', 'take'):
        set3(p + f'bank_button_{b}', '.bmp', states=(('_normal', 'normal'), ('_hover', 'over')), radius=8)
    set3(p + 'bank_calc_button', '.bmp', radius=12, states=(('_normal', 'normal'), ('_hover', 'over'), ('_deactivate', 'disabled')))

def shipconfig():
    p = 'shipconfig/'
    set3(p + 'shipconfig_btn', '.bmp', states=(('_norm', 'normal'), ('_over', 'over'), ('_deactive', 'disabled')), radius=12)

def settings():
    p = 'settings/'
    btn(p + 'button1.tga', 'normal', radius=8)
    btn(p + 'button.tga', 'over', radius=8)
    btn(p + 'button32_normal.bmp', 'normal', radius=8)
    btn(p + 'button32_over.bmp', 'over', radius=8)

def gui():
    set3('gui/generic_exit_btn', '.bmp', states=PAIR)

for fn in (creation, lounge, crewhire, cantina, depot, bank, shipconfig, settings, gui):
    fn()

# ---------------------------------------------------------- .assets lists
changed = {os.path.normcase(os.path.normpath(r)) for r, _ in written}
for root, _, fs in os.walk(DATA):
    for f in fs:
        if not f.endswith('.assets'): continue
        path = os.path.join(root, f)
        rel_dir = os.path.relpath(root, DATA)
        raw = open(path, 'rb').read()
        nl = b'\r\n' if b'\r\n' in raw else b'\n'
        lines = raw.decode().splitlines()
        out = []; n = 0
        for ln in lines:
            t = ln.strip()
            if t and not t.startswith(('#', '?')):
                key = os.path.normcase(os.path.normpath(os.path.join(rel_dir, t)))
                if key in changed:
                    ln = ln.replace(t, os.path.splitext(t)[0] + '.png'); n += 1
            out.append(ln)
        if n:
            open(path, 'wb').write(nl.join(l.encode() for l in out) + (nl if raw.endswith(nl) else b''))
            print(f'{os.path.relpath(path, DATA)}: {n} entries -> png')

print(len(written), 'images')

if PREV:
    cols = 6; cw, ch = 340, 130
    rows = (len(written) + cols - 1) // cols
    S = Image.new('RGB', (cols * cw, rows * ch), (0, 0, 0))
    bg = Image.open(os.path.join(DATA, 'tradedepot/tradedepot_background.bmp')).convert('RGB').resize((cols * cw, rows * ch))
    S.paste(bg)
    dr = ImageDraw.Draw(S)
    for i, (rel, im4) in enumerate(written):
        im = im4.resize((im4.width // 2, im4.height // 2), Image.LANCZOS)
        im.thumbnail((cw - 16, ch - 30))
        x = (i % cols) * cw; y = (i // cols) * ch
        S.paste(im, (x + 8, y + 24), im)
        dr.text((x + 6, y + 4), rel.split('/')[-1][-40:], fill=(255, 255, 255), font_size=12)
    S.save(PREV)
