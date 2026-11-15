"""Render the scene+glass interface backgrounds (and the title logo and menu
buttons) at 4x, 2x and 1x from a spec that mirrors the design canvas.
usage: compose_ui.py <out_data_dir> [preview_dir]
Writes into <out_data_dir> (a mirror of bin/data): the base file with its
original name, size and format, plus name@2x.png and name@4x.png.
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageFont

OUT = sys.argv[1]; PREV = sys.argv[2] if len(sys.argv) > 2 else None
SH = r'\\192.168.1.50\ai-workspace\starflight'
SCN = os.path.join(SH, 'step5', 'scenes'); FONTS = os.path.join(SH, 'fonts')
REPO = os.environ['USERPROFILE'] + r'\Documents\GitHub\tlc-remaster'
K = 4                                   # master scale
W, H = 1024 * K, 768 * K

# ------------------------------------------------------------------ fonts
_fc = {}
def font(family, weight, px):
    key = (family, weight, px)
    if key in _fc: return _fc[key]
    if family == 'barlow':
        f = {300: 'Light', 400: 'Regular', 500: 'Medium', 600: 'SemiBold'}[weight]
        ft = ImageFont.truetype(os.path.join(FONTS, f'barlowcondensed_BarlowCondensed-{f}.ttf'), round(px * K))
    else:
        ft = ImageFont.truetype(os.path.join(FONTS, 'inter_Inter-Variable.ttf'), round(px * K))
        try:
            axes = ft.get_variation_axes()
            vals = [min(max(14, a['minimum']), a['maximum']) if 'opsz' in str(a.get('name', '')).lower() else weight for a in axes]
            ft.set_variation_by_axes(vals)
        except Exception:
            pass
    _fc[key] = ft
    return ft

def rgba(c, a=1.0):
    c = c.lstrip('#'); return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), round(255 * a))

def text(im, x, y, s, fam, wt, px, fill, track=0.0, center_w=None):
    """draw s with letter spacing; x,y in 1x units at the top of the line box"""
    d = ImageDraw.Draw(im)
    ft = font(fam, wt, px)
    total = sum(ft.getlength(ch) for ch in s) + track * K * max(0, len(s) - 1)
    if center_w is not None:
        x = x + (center_w - total / K) / 2
    cx = x * K
    asc, desc = ft.getmetrics()
    top = y * K + (px * K * 1.2 - (asc + desc)) / 2      # CSS-like line box (line-height 1.2)
    for ch in s:
        d.text((cx, top), ch, font=ft, fill=fill)
        cx += ft.getlength(ch) + track * K
    return total / K

# ------------------------------------------------------------------ layers
def scrim(base, kind, tint=(4, 6, 12)):
    w, h = base.size
    if kind == 'L':
        stops = [(0, .78), (.45, .4), (.7, .2), (1, .45)]; axis = 'x'
    else:
        stops = [(0, .7), (.3, .2), (.65, .25), (1, .85)]; axis = 'y'
    n = w if axis == 'x' else h
    t = np.linspace(0, 1, n)
    a = np.interp(t, [s[0] for s in stops], [s[1] for s in stops])
    A = (np.tile(a, (h, 1)) if axis == 'x' else np.tile(a[:, None], (1, w))) * 255
    layer = Image.new('RGBA', (w, h), tint + (0,)); layer.putalpha(Image.fromarray(A.astype(np.uint8)))
    return Image.alpha_composite(base, layer)

def scrim_bottom(base, y0, tint=(4, 6, 12), amax=.85):
    w, h = base.size
    a = np.zeros((h,)); y0 *= K
    a[y0:] = np.linspace(0, amax, h - y0)
    layer = Image.new('RGBA', (w, h), tint + (0,)); layer.putalpha(Image.fromarray((np.tile(a[:, None], (1, w)) * 255).astype(np.uint8)))
    return Image.alpha_composite(base, layer)

def rmask(w, h, r):
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    return m

class Screen:
    def __init__(self, scene, scrim_kind, tint=(8, 12, 22), scrim_tint=(4, 6, 12)):
        im = Image.open(os.path.join(SCN, scene)).convert('RGB')
        k = max(W / im.width, H / im.height)
        im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        x = (im.width - W) // 2; y = (im.height - H) // 2
        self.im = scrim(im.crop((x, y, x + W, y + H)).convert('RGBA'), scrim_kind, scrim_tint)
        self.tint = tint
        self._blur = None

    def blurred(self):
        if self._blur is None:
            b = self.im.convert('RGB').filter(ImageFilter.GaussianBlur(18 * K))
            self._blur = ImageEnhance.Color(b).enhance(1.4).convert('RGBA')
        return self._blur

    def glass(self, x, y, w, h, r=14, border=(255, 255, 255, 36), tint=None, sides='all'):
        X, Y, Wd, Hd, R = x * K, y * K, w * K, h * K, r * K
        tint = tint or self.tint
        g = self.blurred().crop((X, Y, X + Wd, Y + Hd))
        g = Image.alpha_composite(g, Image.new('RGBA', g.size, tint + (round(255 * .52),)))
        m = rmask(Wd, Hd, R)
        self.im.paste(g, (X, Y), m)
        bd = Image.new('RGBA', (Wd, Hd), (0, 0, 0, 0))
        dd = ImageDraw.Draw(bd)
        if sides == 'all':
            dd.rounded_rectangle((0, 0, Wd - 1, Hd - 1), radius=R, outline=border, width=K)
        else:
            dd.line((0, 0, 0, Hd), fill=border, width=K); dd.line((Wd - K, 0, Wd - K, Hd), fill=border, width=K)
        self.im.alpha_composite(bd, (X, Y))

    def well(self, x, y, w, h, r=8, a=.28):
        layer = Image.new('RGBA', (w * K, h * K), (0, 0, 0, round(255 * a)))
        self.im.paste(Image.alpha_composite(self.im.crop((x * K, y * K, (x + w) * K, (y + h) * K)), layer), (x * K, y * K), rmask(w * K, h * K, r * K))

    def rect(self, x, y, w, h, fill):
        layer = Image.new('RGBA', (round(w * K), round(h * K)), fill)
        self.im.alpha_composite(layer, (round(x * K), round(y * K)))

    def dot(self, x, y, d, fill):
        layer = Image.new('RGBA', (d * K, d * K), (0, 0, 0, 0))
        ImageDraw.Draw(layer).ellipse((0, 0, d * K - 1, d * K - 1), fill=fill)
        self.im.alpha_composite(layer, (x * K, y * K))

    def header(self, x, y, eyebrow, title, sub, accent):
        acc = rgba(accent)
        self.rect(x, y + 6, 18, 2, acc)
        text(self.im, x + 28, y, eyebrow.upper(), 'inter', 600, 11, acc, 3)
        text(self.im, x, y + 18, title, 'barlow', 400, 52, (255, 255, 255, 255), 1)
        if sub: text(self.im, x, y + 18 + 52 + 6, sub, 'inter', 400, 13, (238, 244, 255, 184))

    def label(self, x, y, s, px=13, fill=(238, 244, 255, 153), wt=500, track=3, center_w=None):
        text(self.im, x, y, s.upper(), 'barlow', wt, px, fill, track, center_w=center_w)

    def save(self, rel, name_for_preview):
        save_tiers(self.im.convert('RGB'), rel)
        if PREV:
            os.makedirs(PREV, exist_ok=True)
            self.im.convert('RGB').resize((1024, 768), Image.LANCZOS).save(os.path.join(PREV, name_for_preview + '.jpg'), quality=90)

def save_tiers(im4, rel, mode='RGB'):
    """im4 is the 4x master; writes base (1x, original format) and @2x/@4x PNGs"""
    stem, ext = os.path.splitext(rel)
    dst = os.path.join(OUT, rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
    w, h = im4.width // K, im4.height // K
    im4.save(os.path.join(OUT, stem + '@4x.png'))
    im4.resize((w * 2, h * 2), Image.LANCZOS).save(os.path.join(OUT, stem + '@2x.png'))
    base = im4.resize((w, h), Image.LANCZOS)
    if ext.lower() == '.bmp': base = base.convert('RGB')
    base.save(dst)
    print(rel, base.size, base.mode, flush=True)

# ====================================================================== screens
def lounge():
    s = Screen('lounge_1.jpg', 'L')
    s.im = scrim_bottom(s.im, 600)
    s.header(36, 34, 'Arth Station · Deck 4', "Captain's Lounge", 'Choose a captain to continue, or start a new career.', '#5CE1FF')
    for i in range(5):
        s.glass(18, 182 + i * 96, 341, 82, 12)
        s.well(31, 195 + i * 96, 312, 47, 8)
        s.label(31, 245 + i * 96, f'Slot 0{i + 1}', 12, (238, 244, 255, 140))
        s.dot(331, 251 + i * 96, 6, (238, 244, 255, 64))
    s.glass(637, 179, 371, 475, 16)
    s.save('captainslounge/captainslounge_background.bmp', 'lounge')

def depot():
    s = Screen('depot_0.jpg', 'V', tint=(14, 10, 6), scrim_tint=(6, 5, 4))
    acc = '#FFC46B'
    s.header(36, 30, 'Arth Station · Cargo Level', 'Trade Depot', '', acc)
    for x, y, w, h, lab in ((13, 182, 431, 223, 'Your cargo'), (575, 182, 437, 223, 'Depot stock'),
                            (12, 523, 422, 152, 'Selling'), (588, 523, 424, 152, 'Buying')):
        s.glass(x, y, w, h, 14)
        s.label(x + 17, y + 14, lab, 22, (255, 255, 255, 255), 500, 2)
        s.rect(x, y + (49 if y == 182 else 52), w, 1, (255, 255, 255, 31))
    s.glass(447, 443, 128, 128, 16, border=rgba(acc, .45))
    s.label(447, 422, 'Selected', 12, rgba(acc), 500, 3, center_w=128)
    s.save('tradedepot/tradedepot_background.bmp', 'tradedepot')

def creation():
    s = Screen('creation_1.jpg', 'L')
    s.header(36, 22, 'Starfleet Academy · Enlistment', 'Choose your profession', 'Your profession sets your starting ship and the skills your captain can grow.', '#5CE1FF')
    for x, name in ((13, 'Science'), (349, 'Freelance'), (687, 'Military')):
        s.glass(x, 180, 329, 207, 16)
        s.label(x + 18, 194, name, 18, (255, 255, 255, 255), 500)
        s.well(x + 16, 224, 297, 140, 10)
    s.glass(71, 397, 887, 264, 16)
    s.label(95, 414, 'Profession briefing', 12, rgba('#5CE1FF'))
    s.save('captaincreation/captaincreation_professionbackground.bmp', 'creation')
    s = Screen('creation_1.jpg', 'L')
    s.header(36, 22, 'Starfleet Academy · Enlistment', 'Captain details', 'Name your captain and spend attribute points.', '#5CE1FF')
    s.glass(68, 172, 887, 489, 16)
    s.save('captaincreation/captaincreation_detailsbackground.bmp', 'details')

def crewhire():
    s = Screen('crewhire_1.jpg', 'L')
    s.header(36, 26, 'Arth Station · Personnel', 'Crew Hire', 'Assign officers to your bridge stations.', '#4FE3C1')
    s.glass(18, 158, 477, 506, 16)
    s.glass(527, 61, 487, 626, 16)
    s.save('crewhire/personel_background.bmp', 'crewhire')

def halls():
    for scene, rel, title, acc in (('military_1.jpg', 'cantina/militaryops_background.bmp', 'War Room', '#FF6A55'),
                                   ('cantina2_0.jpg', 'cantina/cantina_background.bmp', 'Cantina', '#FFB547'),
                                   ('research_0.jpg', 'cantina/researchlab_background.bmp', 'Research Lab', '#A98BFF')):
        s = Screen(scene, 'L')
        s.header(36, 26, 'Arth Station · Missions', title, '', acc)
        s.glass(18, 140, 477, 263, 16); s.label(40, 152, 'Available missions', 13, (255, 255, 255, 255))
        s.glass(18, 412, 477, 252, 16); s.label(40, 424, 'Current missions', 13, (255, 255, 255, 255))
        s.glass(541, 46, 468, 619, 16)
        s.save(rel, rel.split('/')[1].split('_')[0])

def bank():
    s = Screen('bank_1.jpg', 'L')
    s.header(36, 22, 'Sidhichean Star Bank', 'Bank', 'Deposit, withdraw and check your account.', '#E8C46A')
    s.glass(183, 186, 215, 239, 16)
    s.glass(584, 160, 328, 429, 18)
    s.save('bank/bank_background.bmp', 'bank')

def shipconfig():
    s = Screen('shipyard_0.jpg', 'L')
    s.header(36, 26, 'Arth Station · Drydock', 'Ship Configuration', 'Outfit your ship and buy a terrain vehicle.', '#FF9A3D')
    s.glass(14, 168, 482, 60, 14); s.glass(119, 244, 262, 426, 16)
    s.glass(530, 60, 470, 440, 16); s.glass(560, 520, 410, 210, 16)
    s.save('shipconfig/ShipConfig.bmp', 'shipconfig')

def settings():
    s = Screen('settings_1.jpg', 'L')
    s.glass(20, 20, 300, 400, 16); s.glass(650, 20, 354, 560, 16)
    text(s.im, 36, 600, 'Settings', 'barlow', 300, 52, (255, 255, 255, 255), 1)
    s.save('settings/background.tga', 'settings')

def credits():
    s = Screen('credits_1.jpg', 'V')
    s.glass(220, 0, 584, 768, 0, sides='lr')
    s.save('credits/background.tga', 'credits')

def title():
    s = Screen('title_1.jpg', 'V')
    s.glass(372, 430, 280, 312, 18)
    s.label(36, 736, 'Remastered edition', 11, (238, 244, 255, 128))
    s.save('titlescreen/title_background.bmp', 'title')
    # logo (1024x202 at y=100): eyebrow, wordmark, rule
    for rel, glow in (('titlescreen/title_normal.tga', False), ('titlescreen/title_over.tga', True)):
        lg = Image.new('RGBA', (1024 * K, 202 * K), (0, 0, 0, 0))
        text(lg, 0, 12, 'STARFLIGHT', 'barlow', 600, 15, rgba('#8FD8FF'), 14, center_w=1024)
        text(lg, 0, 34, 'THE LOST COLONY', 'barlow', 300, 96, (255, 255, 255, 255), 10, center_w=1024)
        ImageDraw.Draw(lg).rectangle((452 * K, 158 * K, 572 * K, 159 * K), fill=(255, 255, 255, 102))
        if glow:
            gl = lg.filter(ImageFilter.GaussianBlur(10 * K)); lg = Image.alpha_composite(gl, lg)
        save_tiers(lg, rel)
    # menu buttons 240x60: a 48px pill centred vertically
    for name, label in (('newgame', 'NEW GAME'), ('loadgame', 'LOAD GAME'), ('settings', 'SETTINGS'),
                        ('credits', 'CREDITS'), ('quit', 'QUIT'), ('prologue', 'PROLOGUE')):
        for state in ('normal', 'over'):
            b = Image.new('RGBA', (240 * K, 60 * K), (0, 0, 0, 0))
            d = ImageDraw.Draw(b)
            box = (0, 6 * K, 240 * K - 1, 54 * K - 1)
            if state == 'over':
                d.rounded_rectangle(box, radius=24 * K, fill=rgba('#8FD8FF'))
                fg = (6, 16, 26, 255)
            else:
                d.rounded_rectangle(box, radius=24 * K, fill=(8, 12, 22, 90), outline=(255, 255, 255, 56), width=K)
                fg = (238, 244, 255, 255)
            text(b, 0, 6 + (48 - 24) / 2, label, 'barlow', 500, 20, fg, 4, center_w=240)
            save_tiers(b, f'titlescreen/title_{name}_{state}.tga')

for fn in (title, creation, lounge, crewhire, halls, depot, bank, shipconfig, settings, credits):
    fn()
print('done')
