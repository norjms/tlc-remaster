"""Modern line icons for every control-panel command button (61x61 game size; also @2x, @4x).
Light strokes with a soft cyan glow on transparent; the glass button background is drawn by the game underneath.
usage: cmd_icons.py <bin/data> [preview.jpg]"""
import os, sys, math
from PIL import Image, ImageDraw, ImageFilter
DATA = sys.argv[1]; PREV = sys.argv[2] if len(sys.argv) > 2 else None
CP = os.path.join(DATA, 'controlpanel')
N = 61; K = 16; S = N * K                # draw at 16x
INK = (226, 238, 255, 255); ACC = (110, 205, 255, 255)
LW = int(3.2 * K)                       # stroke width at 1x ~3.2 px

class P:
    def __init__(self):
        self.im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); self.d = ImageDraw.Draw(self.im)
    def u(self, v): return v * S / 100.0           # icon coordinates are 0..100
    def line(self, pts, w=1.0, col=INK, closed=False):
        pts = [(self.u(x), self.u(y)) for x, y in pts]
        if closed: pts = pts + [pts[0]]
        ww = int(LW * w)
        self.d.line(pts, fill=col, width=ww, joint='curve')
        r = ww / 2
        for x, y in (pts if not closed else pts[:-1]):
            self.d.ellipse((x - r, y - r, x + r, y + r), fill=col)
    def circle(self, cx, cy, r, w=1.0, col=INK, fill=None):
        cx, cy, r = self.u(cx), self.u(cy), self.u(r)
        self.d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=col, width=int(LW * w), fill=fill)
    def dot(self, cx, cy, r, col=INK):
        cx, cy, r = self.u(cx), self.u(cy), self.u(r); self.d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    def arc(self, cx, cy, r, a0, a1, w=1.0, col=INK):
        cx, cy, r = self.u(cx), self.u(cy), self.u(r)
        self.d.arc((cx - r, cy - r, cx + r, cy + r), a0, a1, fill=col, width=int(LW * w))
    def ellipse(self, cx, cy, rx, ry, w=1.0, col=INK):
        cx, cy, rx, ry = self.u(cx), self.u(cy), self.u(rx), self.u(ry)
        self.d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=col, width=int(LW * w))
    def poly(self, pts, col=INK):
        self.d.polygon([(self.u(x), self.u(y)) for x, y in pts], fill=col)
    def rrect(self, x0, y0, x1, y1, r, w=1.0, col=INK):
        self.d.rounded_rectangle((self.u(x0), self.u(y0), self.u(x1), self.u(y1)), radius=self.u(r), outline=col, width=int(LW * w))
    def text(self, s, cx, cy, size, col=INK):
        from PIL import ImageFont
        try: f = ImageFont.truetype('segoeuib.ttf', int(self.u(size)))
        except Exception: f = ImageFont.load_default()
        self.d.text((self.u(cx), self.u(cy)), s, font=f, fill=col, anchor='mm')

def arrow(p, x, y0, y1, head=12, col=INK):
    p.line([(x, y0), (x, y1)], col=col)
    s = 1 if y1 > y0 else -1
    p.line([(x - head, y1 - s * head), (x, y1), (x + head, y1 - s * head)], col=col)

def bubble(p, x0=20, y0=24, x1=80, y1=66):
    p.rrect(x0, y0, x1, y1, 10)
    p.line([(x0 + 14, y1), (x0 + 10, y1 + 12), (x0 + 26, y1)])

ICONS = {}
def icon(name):
    def deco(fn): ICONS[name] = fn; return fn
    return deco

@icon('captain_launch')
def _(p): p.arc(50, 112, 42, 228, 312, col=ACC); arrow(p, 50, 72, 22)
@icon('captain_descend')
def _(p): p.arc(50, 112, 42, 228, 312, col=ACC); arrow(p, 50, 20, 62)
@icon('captain_cargo')
def _(p):
    p.line([(50, 22), (78, 36), (78, 66), (50, 80), (22, 66), (22, 36)], closed=True)
    p.line([(22, 36), (50, 50), (78, 36)]); p.line([(50, 50), (50, 80)])
    p.line([(36, 29), (64, 43)], w=0.7, col=ACC)
@icon('captain_disembark')
def _(p):
    p.line([(26, 22), (26, 80)], w=0.9); p.line([(26, 22), (50, 22)], w=0.9); p.line([(26, 80), (50, 80)], w=0.9)
    p.dot(64, 32, 6.5); p.line([(62, 42), (58, 60), (66, 80)]); p.line([(58, 60), (48, 76)]); p.line([(60, 48), (72, 54)]); p.line([(60, 48), (50, 52)])
@icon('captain_logplanet')
def _(p):
    p.circle(44, 52, 20); p.ellipse(44, 52, 32, 9, w=0.8, col=ACC)
    p.line([(70, 20), (70, 40)], w=0.9); p.line([(60, 30), (80, 30)], w=0.9)
@icon('com_questlog')
def _(p):
    p.rrect(26, 18, 74, 84, 6)
    for i, y in enumerate((36, 52, 68)):
        p.line([(34, y), (38, y + 4), (45, y - 4)], w=0.8, col=ACC); p.line([(52, y), (66, y)], w=0.8)
@icon('com_distress')
def _(p):
    p.line([(50, 24), (78, 74), (22, 74)], closed=True); p.line([(50, 42), (50, 58)]); p.dot(50, 66, 3.2)
    p.arc(50, 50, 40, 200, 250, w=0.7, col=ACC); p.arc(50, 50, 40, 290, 340, w=0.7, col=ACC)
@icon('com_hail')
def _(p):
    p.arc(40, 60, 22, 160, 340); p.line([(40, 60), (56, 44)], w=0.8); p.line([(40, 60), (34, 82), (48, 82)], w=0.8)
    for r in (12, 22, 32): p.arc(56, 44, r, 280, 350, w=0.7, col=ACC)
@icon('com_posture')
def _(p):
    p.arc(50, 62, 32, 180, 360); p.line([(50, 62), (66, 40)])
    for a in (200, 230, 270, 310, 340):
        x, y = 50 + 32 * math.cos(math.radians(a)), 62 + 32 * math.sin(math.radians(a))
        x2, y2 = 50 + 24 * math.cos(math.radians(a)), 62 + 24 * math.sin(math.radians(a))
        p.line([(x, y), (x2, y2)], w=0.6, col=ACC)
    p.dot(50, 62, 5)
@icon('com_question')
def _(p): bubble(p); p.text('?', 50, 45, 30)
@icon('com_statement')
def _(p): bubble(p); p.text('!', 50, 45, 30)
@icon('com_respond')            # used for "Inject fuel" on the engineer panel
def _(p):
    pts = [(44 + 22 * math.sin(a) * math.sin(a / 2), 48 - 30 * math.cos(a) * 0.95 + 4) for a in [i * 2 * math.pi / 48 for i in range(48)]]
    p.line(pts, closed=True)
    p.line([(70, 60), (70, 82)], w=0.9, col=ACC); p.line([(59, 71), (81, 71)], w=0.9, col=ACC)
@icon('com_terminate')
def _(p): bubble(p); p.line([(40, 35), (60, 55)], col=ACC); p.line([(60, 35), (40, 55)], col=ACC)
def wrench(p, x0, y0, x1, y1):
    p.line([(x0, y0), (x1, y1)], w=1.4)
    dx, dy = x1 - x0, y1 - y0; L = math.hypot(dx, dy); ux, uy = dx / L, dy / L; nx, ny = -uy, ux
    hx, hy = x1 + ux * 6, y1 + uy * 6
    p.line([(hx + nx * 9, hy + ny * 9), (hx + nx * 9 + ux * 12, hy + ny * 9 + uy * 12)], w=1.2)
    p.line([(hx - nx * 9, hy - ny * 9), (hx - nx * 9 + ux * 12, hy - ny * 9 + uy * 12)], w=1.2)
    p.line([(hx + nx * 9, hy + ny * 9), (hx - nx * 9, hy - ny * 9)], w=1.2)

@icon('eng_damage')
def _(p):
    wrench(p, 24, 76, 54, 46)
    p.line([(62, 62), (70, 70), (64, 76), (74, 84)], w=0.7, col=ACC)
@icon('eng_repair')
def _(p):
    wrench(p, 22, 78, 50, 50)
    p.circle(68, 70, 10, w=0.8, col=ACC)
    for a in range(0, 360, 60):
        x, y = 68 + 10 * math.cos(math.radians(a)), 70 + 10 * math.sin(math.radians(a))
        p.line([(x, y), (68 + 16 * math.cos(math.radians(a)), 70 + 16 * math.sin(math.radians(a)))], w=0.7, col=ACC)
@icon('med_examine')
def _(p):
    p.circle(50, 50, 30)
    p.line([(24, 52), (36, 52), (42, 38), (50, 66), (57, 44), (62, 52), (76, 52)], w=0.8, col=ACC)
@icon('med_treat')
def _(p):
    p.rrect(24, 32, 76, 68, 18)
    p.line([(50, 40), (50, 60)], col=ACC); p.line([(40, 50), (60, 50)], col=ACC)
@icon('nav_dock')
def _(p):
    p.circle(62, 40, 14); p.line([(62, 20), (62, 26)], w=0.8); p.line([(62, 54), (62, 60)], w=0.8); p.line([(42, 40), (48, 40)], w=0.8); p.line([(76, 40), (82, 40)], w=0.8)
    p.line([(22, 80), (46, 56)], col=ACC); p.line([(34, 56), (46, 56), (46, 68)], col=ACC)
@icon('nav_hyperspace')
def _(p):
    p.circle(50, 50, 8, w=0.9)
    for a in range(0, 360, 30):
        r0, r1 = 16, 36 if a % 60 == 0 else 28
        p.line([(50 + r0 * math.cos(math.radians(a)), 50 + r0 * math.sin(math.radians(a))),
                (50 + r1 * math.cos(math.radians(a)), 50 + r1 * math.sin(math.radians(a)))], w=0.7, col=ACC if a % 60 else INK)
@icon('nav_maneuver')
def _(p):
    p.circle(50, 50, 30, w=0.7, col=ACC)
    p.poly([(50, 20), (57, 50), (50, 44), (43, 50)]); p.poly([(50, 80), (57, 50), (50, 56), (43, 50)], col=(160, 175, 195, 255))
@icon('nav_orbit')
def _(p):
    p.circle(50, 52, 14); p.ellipse(50, 52, 34, 16, w=0.8, col=ACC); p.dot(80, 46, 4.5)
@icon('nav_starmap')
def _(p):
    pts = [(24, 66), (40, 40), (58, 54), (76, 28)]
    p.line(pts, w=0.6, col=ACC)
    for x, y in pts: p.dot(x, y, 5)
    p.dot(34, 76, 2.6); p.dot(70, 72, 2.6); p.dot(60, 24, 2.6)
@icon('science_analysis')
def _(p):
    p.line([(22, 22), (22, 78), (78, 78)], w=0.9)
    for x, h in ((34, 20), (48, 34), (62, 26)): p.line([(x, 70), (x, 70 - h)], w=1.3, col=ACC)
    p.line([(30, 44), (46, 32), (60, 40), (76, 22)], w=0.7)
@icon('science_scan')
def _(p):
    p.circle(50, 50, 30); p.circle(50, 50, 16, w=0.6, col=ACC)
    p.line([(50, 50), (72, 30)], w=0.9); p.dot(36, 40, 3.5, col=ACC); p.dot(62, 64, 3.5, col=ACC)
@icon('tac_combat')
def _(p):
    p.circle(50, 50, 24)
    for a, b in (((50, 16), (50, 34)), ((50, 66), (50, 84)), ((16, 50), (34, 50)), ((66, 50), (84, 50))): p.line([a, b])
    p.dot(50, 50, 4, col=ACC)
@icon('tac_shields')
def _(p):
    p.line([(50, 18), (76, 28), (74, 54), (50, 82), (26, 54), (24, 28)], closed=True)
    p.arc(50, 52, 14, 200, 340, w=0.7, col=ACC); p.arc(50, 52, 22, 210, 330, w=0.7, col=ACC)
@icon('tac_weapons')
def _(p):
    for x, c in ((34, ACC), (50, INK), (66, ACC)):
        p.line([(x, 80), (x, 34)], w=0.9, col=c); p.poly([(x - 6, 36), (x, 20), (x + 6, 36)], col=c)

def finish(p):
    ink = p.im
    g = ink.getchannel('A').filter(ImageFilter.GaussianBlur(K * 2.2)).point(lambda v: int(v * 0.55))
    glow = Image.new('RGBA', (S, S), (90, 190, 255, 0)); glow.putalpha(g)
    out = Image.new('RGBA', (S, S), (0, 0, 0, 0)); out.alpha_composite(glow); out.alpha_composite(ink)
    return out

prev = []
for name, fn in ICONS.items():
    p = P(); fn(p); im = finish(p)
    for k, suf in ((1, ''), (2, '@2x'), (4, '@4x')):
        im.resize((N * k, N * k), Image.LANCZOS).save(os.path.join(CP, f'commandicon_{name}{suf}.png'))
    prev.append((name, im.resize((122, 122), Image.LANCZOS)))
print(len(prev), 'icons')
if PREV:
    bg = Image.open(os.path.join(CP, 'command_button_bg@2x.png')).convert('RGBA')
    cols = 9; rows = (len(prev) + cols - 1) // cols
    c = Image.new('RGBA', (cols * 132, rows * 132), (10, 14, 22, 255))
    for i, (n, im) in enumerate(prev):
        x, y = (i % cols) * 132 + 5, (i // cols) * 132 + 5
        c.alpha_composite(bg, (x, y)); c.alpha_composite(im, (x, y))
    c.convert('RGB').save(PREV, quality=92)
