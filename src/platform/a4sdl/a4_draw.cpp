/*
 * a4sdl drawing: bitmaps, primitives, blits, sprites, rotation,
 * translucency and Allegro's built-in 8x8 text font.
 */
#include "a4_internal.h"
#include "a4_font8x8.h"

#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

using a4::row;
using a4::is_mask;

bool a4::screen_dirty = false;

/* ---------------------------------------------------------------- colors */

int makecol(int r, int g, int b)            { return makecol32(r, g, b); }
int makeacol(int r, int g, int b, int a)    { return makeacol32(r, g, b, a); }
int makecol32(int r, int g, int b)          { return ((r & 255) << 16) | ((g & 255) << 8) | (b & 255); }
int makeacol32(int r, int g, int b, int a)  { return (int)(((uint32_t)(a & 255) << 24) | (uint32_t)makecol32(r, g, b)); }
int getr(int c) { return (c >> 16) & 255; }
int getg(int c) { return (c >> 8) & 255; }
int getb(int c) { return c & 255; }
int geta(int c) { return (int)(((uint32_t)c >> 24) & 255); }

void set_color_depth(int) {}
int bitmap_color_depth(BITMAP *) { return 32; }
int bitmap_mask_color(BITMAP *)  { return MASK_COLOR_32; }

/* --------------------------------------------------------------- bitmaps */

BITMAP *create_bitmap(int width, int height)
{
	if (width < 0 || height < 0) return NULL;
	BITMAP *b = (BITMAP *)calloc(1, sizeof(BITMAP));
	if (!b) return NULL;
	b->w = width;
	b->h = height;
	b->pitch = width;
	b->pixels = (uint32_t *)calloc((size_t)(width > 0 ? width : 1) * (height > 0 ? height : 1), sizeof(uint32_t));
	if (!b->pixels) { free(b); return NULL; }
	b->owns_pixels = 1;
	b->clip = 1;
	b->cl = 0; b->ct = 0; b->cr = width; b->cb = height;
	return b;
}

BITMAP *create_sub_bitmap(BITMAP *parent, int x, int y, int width, int height)
{
	if (!parent) return NULL;
	if (x < 0) x = 0;
	if (y < 0) y = 0;
	if (x + width > parent->w) width = parent->w - x;
	if (y + height > parent->h) height = parent->h - y;
	if (width < 0) width = 0;
	if (height < 0) height = 0;
	BITMAP *b = (BITMAP *)calloc(1, sizeof(BITMAP));
	if (!b) return NULL;
	b->w = width;
	b->h = height;
	b->pitch = parent->pitch;
	b->pixels = parent->pixels + (size_t)y * parent->pitch + x;
	b->owns_pixels = 0;
	b->parent = parent;
	b->is_screen = parent->is_screen;
	b->clip = 1;
	b->cl = 0; b->ct = 0; b->cr = width; b->cb = height;
	return b;
}

void destroy_bitmap(BITMAP *b)
{
	if (!b) return;
	if (b == screen) return;  /* owned by the display */
	if (b->owns_pixels) free(b->pixels);
	free(b);
}

void set_clip_rect(BITMAP *b, int x1, int y1, int x2, int y2)
{
	if (!b) return;
	b->cl = MID(0, x1, b->w);
	b->ct = MID(0, y1, b->h);
	b->cr = MID(0, x2 + 1, b->w);
	b->cb = MID(0, y2 + 1, b->h);
}

static BITMAP *root_of(BITMAP *b)
{
	while (b->parent) b = b->parent;
	return b;
}

/* ------------------------------------------------------------ primitives */

static inline void pset(BITMAP *b, int x, int y, uint32_t c)
{
	if (x >= b->cl && x < b->cr && y >= b->ct && y < b->cb)
		row(b, y)[x] = c;
}

void clear_to_color(BITMAP *b, int color)
{
	if (!b) return;
	for (int y = b->ct; y < b->cb; y++) {
		uint32_t *p = row(b, y);
		for (int x = b->cl; x < b->cr; x++) p[x] = (uint32_t)color;
	}
	a4::touch(b);
}

void clear_bitmap(BITMAP *b) { clear_to_color(b, 0); }

void putpixel(BITMAP *b, int x, int y, int color)
{
	if (!b) return;
	pset(b, x, y, (uint32_t)color);
	a4::touch(b);
}

int getpixel(BITMAP *b, int x, int y)
{
	if (!b || x < 0 || y < 0 || x >= b->w || y >= b->h) return -1;
	return (int)row(b, y)[x];
}

void hline(BITMAP *b, int x1, int y, int x2, int color)
{
	if (!b || y < b->ct || y >= b->cb) return;
	if (x1 > x2) { int t = x1; x1 = x2; x2 = t; }
	if (x1 < b->cl) x1 = b->cl;
	if (x2 >= b->cr) x2 = b->cr - 1;
	uint32_t *p = row(b, y);
	for (int x = x1; x <= x2; x++) p[x] = (uint32_t)color;
	a4::touch(b);
}

void vline(BITMAP *b, int x, int y1, int y2, int color)
{
	if (!b || x < b->cl || x >= b->cr) return;
	if (y1 > y2) { int t = y1; y1 = y2; y2 = t; }
	if (y1 < b->ct) y1 = b->ct;
	if (y2 >= b->cb) y2 = b->cb - 1;
	for (int y = y1; y <= y2; y++) row(b, y)[x] = (uint32_t)color;
	a4::touch(b);
}

void line(BITMAP *b, int x1, int y1, int x2, int y2, int color)
{
	if (!b) return;
	if (y1 == y2) { hline(b, x1, y1, x2, color); return; }
	if (x1 == x2) { vline(b, x1, y1, y2, color); return; }
	int dx = abs(x2 - x1), sx = x1 < x2 ? 1 : -1;
	int dy = -abs(y2 - y1), sy = y1 < y2 ? 1 : -1;
	int err = dx + dy;
	for (;;) {
		pset(b, x1, y1, (uint32_t)color);
		if (x1 == x2 && y1 == y2) break;
		int e2 = 2 * err;
		if (e2 >= dy) { err += dy; x1 += sx; }
		if (e2 <= dx) { err += dx; y1 += sy; }
	}
	a4::touch(b);
}

void rect(BITMAP *b, int x1, int y1, int x2, int y2, int color)
{
	hline(b, x1, y1, x2, color);
	hline(b, x1, y2, x2, color);
	vline(b, x1, y1, y2, color);
	vline(b, x2, y1, y2, color);
}

void rectfill(BITMAP *b, int x1, int y1, int x2, int y2, int color)
{
	if (!b) return;
	if (y1 > y2) { int t = y1; y1 = y2; y2 = t; }
	for (int y = y1; y <= y2; y++) hline(b, x1, y, x2, color);
}

void circle(BITMAP *b, int cx, int cy, int r, int color)
{
	if (!b || r < 0) return;
	int x = r, y = 0, err = 1 - r;
	while (x >= y) {
		pset(b, cx + x, cy + y, color); pset(b, cx - x, cy + y, color);
		pset(b, cx + x, cy - y, color); pset(b, cx - x, cy - y, color);
		pset(b, cx + y, cy + x, color); pset(b, cx - y, cy + x, color);
		pset(b, cx + y, cy - x, color); pset(b, cx - y, cy - x, color);
		y++;
		if (err < 0) err += 2 * y + 1;
		else { x--; err += 2 * (y - x) + 1; }
	}
	a4::touch(b);
}

void circlefill(BITMAP *b, int cx, int cy, int r, int color)
{
	if (!b || r < 0) return;
	int x = r, y = 0, err = 1 - r;
	while (x >= y) {
		hline(b, cx - x, cy + y, cx + x, color);
		hline(b, cx - x, cy - y, cx + x, color);
		hline(b, cx - y, cy + x, cx + y, color);
		hline(b, cx - y, cy - x, cx + y, color);
		y++;
		if (err < 0) err += 2 * y + 1;
		else { x--; err += 2 * (y - x) + 1; }
	}
}

/* midpoint ellipse; fill == true draws spans instead of the outline */
static void do_ellipse(BITMAP *b, int cx, int cy, int rx, int ry, int color, bool fill)
{
	if (!b || rx < 0 || ry < 0) return;
	long rx2 = (long)rx * rx, ry2 = (long)ry * ry;
	long x = 0, y = ry;
	long px = 0, py = 2 * rx2 * y;
	auto plot4 = [&](long X, long Y) {
		if (fill) {
			hline(b, (int)(cx - X), (int)(cy + Y), (int)(cx + X), color);
			hline(b, (int)(cx - X), (int)(cy - Y), (int)(cx + X), color);
		} else {
			pset(b, (int)(cx + X), (int)(cy + Y), color); pset(b, (int)(cx - X), (int)(cy + Y), color);
			pset(b, (int)(cx + X), (int)(cy - Y), color); pset(b, (int)(cx - X), (int)(cy - Y), color);
		}
	};
	long p = (long)(ry2 - rx2 * ry + 0.25 * rx2);
	while (px < py) {
		plot4(x, y);
		x++; px += 2 * ry2;
		if (p < 0) p += ry2 + px;
		else { y--; py -= 2 * rx2; p += ry2 + px - py; }
	}
	p = (long)(ry2 * (x + 0.5) * (x + 0.5) + rx2 * (y - 1) * (y - 1) - rx2 * ry2);
	while (y >= 0) {
		plot4(x, y);
		y--; py -= 2 * rx2;
		if (p > 0) p += rx2 - py;
		else { x++; px += 2 * ry2; p += rx2 - py + px; }
	}
	a4::touch(b);
}

void ellipse(BITMAP *b, int x, int y, int rx, int ry, int color)     { do_ellipse(b, x, y, rx, ry, color, false); }
void ellipsefill(BITMAP *b, int x, int y, int rx, int ry, int color) { do_ellipse(b, x, y, rx, ry, color, true); }

void triangle(BITMAP *b, int x1, int y1, int x2, int y2, int x3, int y3, int color)
{
	if (!b) return;
	/* sort by y */
	if (y2 < y1) { int t; t = x1; x1 = x2; x2 = t; t = y1; y1 = y2; y2 = t; }
	if (y3 < y1) { int t; t = x1; x1 = x3; x3 = t; t = y1; y1 = y3; y3 = t; }
	if (y3 < y2) { int t; t = x2; x2 = x3; x3 = t; t = y2; y2 = y3; y3 = t; }
	for (int y = y1; y <= y3; y++) {
		double xa = (y3 == y1) ? x1 : x1 + (double)(x3 - x1) * (y - y1) / (y3 - y1);
		double xb;
		if (y < y2) xb = (y2 == y1) ? x1 : x1 + (double)(x2 - x1) * (y - y1) / (y2 - y1);
		else        xb = (y3 == y2) ? x2 : x2 + (double)(x3 - x2) * (y - y2) / (y3 - y2);
		hline(b, (int)floor(xa + 0.5), y, (int)floor(xb + 0.5), color);
	}
}

/* ----------------------------------------------------------------- blits */

/* clip a source rectangle against the source bounds and the destination
   clip rectangle; returns false when nothing is left */
static bool clip_blit(BITMAP *s, BITMAP *d, int &sx, int &sy, int &dx, int &dy, int &w, int &h)
{
	if (sx < 0) { w += sx; dx -= sx; sx = 0; }
	if (sy < 0) { h += sy; dy -= sy; sy = 0; }
	if (sx + w > s->w) w = s->w - sx;
	if (sy + h > s->h) h = s->h - sy;
	if (dx < d->cl) { int k = d->cl - dx; w -= k; sx += k; dx = d->cl; }
	if (dy < d->ct) { int k = d->ct - dy; h -= k; sy += k; dy = d->ct; }
	if (dx + w > d->cr) w = d->cr - dx;
	if (dy + h > d->cb) h = d->cb - dy;
	return w > 0 && h > 0;
}

void blit(BITMAP *s, BITMAP *d, int sx, int sy, int dx, int dy, int w, int h)
{
	if (!s || !d || !clip_blit(s, d, sx, sy, dx, dy, w, h)) return;
	if (root_of(s) == root_of(d)) {
		/* overlapping regions: go through a temporary copy */
		std::vector<uint32_t> tmp((size_t)w * h);
		for (int y = 0; y < h; y++) memcpy(&tmp[(size_t)y * w], row(s, sy + y) + sx, (size_t)w * 4);
		for (int y = 0; y < h; y++) memcpy(row(d, dy + y) + dx, &tmp[(size_t)y * w], (size_t)w * 4);
	} else {
		for (int y = 0; y < h; y++) memcpy(row(d, dy + y) + dx, row(s, sy + y) + sx, (size_t)w * 4);
	}
	a4::touch(d);
}

void masked_blit(BITMAP *s, BITMAP *d, int sx, int sy, int dx, int dy, int w, int h)
{
	if (!s || !d || !clip_blit(s, d, sx, sy, dx, dy, w, h)) return;
	for (int y = 0; y < h; y++) {
		const uint32_t *sp = row(s, sy + y) + sx;
		uint32_t *dp = row(d, dy + y) + dx;
		for (int x = 0; x < w; x++)
			if (!is_mask(sp[x])) dp[x] = sp[x];
	}
	a4::touch(d);
}

static void do_stretch(BITMAP *s, BITMAP *d, int s_x, int s_y, int s_w, int s_h,
                       int d_x, int d_y, int d_w, int d_h, bool masked)
{
	if (!s || !d || s_w <= 0 || s_h <= 0 || d_w <= 0 || d_h <= 0) return;
	if (!masked && s_w == d_w && s_h == d_h) { blit(s, d, s_x, s_y, d_x, d_y, s_w, s_h); return; }
	int x0 = MAX(d_x, d->cl), x1 = MIN(d_x + d_w, d->cr);
	int y0 = MAX(d_y, d->ct), y1 = MIN(d_y + d_h, d->cb);
	for (int y = y0; y < y1; y++) {
		int sy = s_y + (int)(((long long)(y - d_y) * s_h) / d_h);
		if (sy < 0 || sy >= s->h) continue;
		const uint32_t *sp = row(s, sy);
		uint32_t *dp = row(d, y);
		for (int x = x0; x < x1; x++) {
			int sx = s_x + (int)(((long long)(x - d_x) * s_w) / d_w);
			if (sx < 0 || sx >= s->w) continue;
			uint32_t c = sp[sx];
			if (masked && is_mask(c)) continue;
			dp[x] = c;
		}
	}
	a4::touch(d);
}

void stretch_blit(BITMAP *s, BITMAP *d, int s_x, int s_y, int s_w, int s_h, int d_x, int d_y, int d_w, int d_h)
{
	do_stretch(s, d, s_x, s_y, s_w, s_h, d_x, d_y, d_w, d_h, false);
}

void masked_stretch_blit(BITMAP *s, BITMAP *d, int s_x, int s_y, int s_w, int s_h, int d_x, int d_y, int d_w, int d_h)
{
	do_stretch(s, d, s_x, s_y, s_w, s_h, d_x, d_y, d_w, d_h, true);
}

void stretch_sprite(BITMAP *bmp, BITMAP *sprite, int x, int y, int w, int h)
{
	if (!sprite) return;
	do_stretch(sprite, bmp, 0, 0, sprite->w, sprite->h, x, y, w, h, true);
}

/* --------------------------------------------------------------- sprites */

static void sprite_flip(BITMAP *d, BITMAP *s, int x, int y, bool hf, bool vf)
{
	if (!s || !d) return;
	int x0 = MAX(x, d->cl), x1 = MIN(x + s->w, d->cr);
	int y0 = MAX(y, d->ct), y1 = MIN(y + s->h, d->cb);
	for (int dy = y0; dy < y1; dy++) {
		int sy = dy - y;
		if (vf) sy = s->h - 1 - sy;
		const uint32_t *sp = row(s, sy);
		uint32_t *dp = row(d, dy);
		for (int dx = x0; dx < x1; dx++) {
			int sx = dx - x;
			if (hf) sx = s->w - 1 - sx;
			uint32_t c = sp[sx];
			if (!is_mask(c)) dp[dx] = c;
		}
	}
	a4::touch(d);
}

void draw_sprite(BITMAP *bmp, BITMAP *sprite, int x, int y)         { sprite_flip(bmp, sprite, x, y, false, false); }
void draw_sprite_h_flip(BITMAP *bmp, BITMAP *sprite, int x, int y)  { sprite_flip(bmp, sprite, x, y, true, false); }
void draw_sprite_v_flip(BITMAP *bmp, BITMAP *sprite, int x, int y)  { sprite_flip(bmp, sprite, x, y, false, true); }
void draw_sprite_vh_flip(BITMAP *bmp, BITMAP *sprite, int x, int y) { sprite_flip(bmp, sprite, x, y, true, true); }

/* Allegro rotates around the sprite centre, the sprite's top-left corner
   (before rotation) at x,y. Angles are fixed point with 256 units per
   full turn; positive is clockwise on screen. */
void rotate_scaled_sprite(BITMAP *d, BITMAP *s, int x, int y, fixed angle, fixed scale)
{
	if (!s || !d || s->w <= 0 || s->h <= 0) return;
	double theta = fixtof(angle) * (2.0 * AL_PI / 256.0);
	double sc = fixtof(scale);
	if (sc <= 0) return;
	double c = cos(theta), sn = sin(theta);
	double cx = x + s->w / 2.0, cy = y + s->h / 2.0;
	double rad = 0.5 * sqrt((double)s->w * s->w + (double)s->h * s->h) * sc + 1;
	int x0 = MAX((int)floor(cx - rad), d->cl), x1 = MIN((int)ceil(cx + rad), d->cr);
	int y0 = MAX((int)floor(cy - rad), d->ct), y1 = MIN((int)ceil(cy + rad), d->cb);
	for (int py = y0; py < y1; py++) {
		uint32_t *dp = row(d, py);
		double ry = py + 0.5 - cy;
		for (int px = x0; px < x1; px++) {
			double rx = px + 0.5 - cx;
			double lx = ( c * rx + sn * ry) / sc + s->w / 2.0;
			double ly = (-sn * rx + c * ry) / sc + s->h / 2.0;
			int sx = (int)floor(lx), sy = (int)floor(ly);
			if (sx < 0 || sy < 0 || sx >= s->w || sy >= s->h) continue;
			uint32_t col = row(s, sy)[sx];
			if (!is_mask(col)) dp[px] = col;
		}
	}
	a4::touch(d);
}

void rotate_sprite(BITMAP *bmp, BITMAP *sprite, int x, int y, fixed angle)
{
	rotate_scaled_sprite(bmp, sprite, x, y, angle, itofix(1));
}

/* ---------------------------------------------------------- translucency */

static bool g_alpha_blender = false;
static int  g_trans_alpha = 255;

void set_trans_blender(int, int, int, int a)
{
	g_alpha_blender = false;
	g_trans_alpha = MID(0, a, 255);
}

void set_alpha_blender(void)
{
	g_alpha_blender = true;
}

void draw_trans_sprite(BITMAP *d, BITMAP *s, int x, int y)
{
	if (!s || !d) return;
	int x0 = MAX(x, d->cl), x1 = MIN(x + s->w, d->cr);
	int y0 = MAX(y, d->ct), y1 = MIN(y + s->h, d->cb);
	for (int dy = y0; dy < y1; dy++) {
		const uint32_t *sp = row(s, dy - y);
		uint32_t *dp = row(d, dy);
		for (int dx = x0; dx < x1; dx++) {
			uint32_t c = sp[dx - x];
			if (is_mask(c)) continue;
			unsigned a = g_alpha_blender ? (c >> 24) : (unsigned)g_trans_alpha;
			dp[dx] = a4::blend(c, dp[dx], a);
		}
	}
	a4::touch(d);
}

/* ------------------------------------------------------- built-in 8x8 text */

struct FONT { int dummy; };
static FONT g_builtin_font = { 0 };
FONT *font = &g_builtin_font;

int text_length(const FONT *, const char *str) { return str ? 8 * (int)strlen(str) : 0; }
int text_height(const FONT *) { return 8; }

void textout_ex(BITMAP *b, const FONT *, const char *str, int x, int y, int color, int bg)
{
	if (!b || !str) return;
	uint32_t fg = (color == -1) ? 0x00FFFFFFu : (uint32_t)color;
	for (const unsigned char *p = (const unsigned char *)str; *p; p++, x += 8) {
		if (bg >= 0) rectfill(b, x, y, x + 7, y + 7, bg);
		unsigned ch = *p;
		const unsigned char *g = a4_font8x8[(ch >= 0x20 && ch < 0x7F) ? ch - 0x20 : '?' - 0x20];
		for (int r = 0; r < 8; r++)
			for (int c = 0; c < 8; c++)
				if (g[r] & (0x80 >> c)) pset(b, x + c, y + r, fg);
	}
	a4::touch(b);
}

void textout_centre_ex(BITMAP *b, const FONT *f, const char *str, int x, int y, int color, int bg)
{
	textout_ex(b, f, str, x - text_length(f, str) / 2, y, color, bg);
}

void textout_right_ex(BITMAP *b, const FONT *f, const char *str, int x, int y, int color, int bg)
{
	textout_ex(b, f, str, x - text_length(f, str), y, color, bg);
}

#define A4_FORMAT(buf, fmt) \
	char buf[1024]; \
	va_list ap; va_start(ap, fmt); vsnprintf(buf, sizeof buf, fmt, ap); va_end(ap)

void textprintf_ex(BITMAP *b, const FONT *f, int x, int y, int color, int bg, const char *format, ...)
{
	A4_FORMAT(buf, format);
	textout_ex(b, f, buf, x, y, color, bg);
}

void textprintf_centre_ex(BITMAP *b, const FONT *f, int x, int y, int color, int bg, const char *format, ...)
{
	A4_FORMAT(buf, format);
	textout_centre_ex(b, f, buf, x, y, color, bg);
}

void textprintf_right_ex(BITMAP *b, const FONT *f, int x, int y, int color, int bg, const char *format, ...)
{
	A4_FORMAT(buf, format);
	textout_right_ex(b, f, buf, x, y, color, bg);
}
