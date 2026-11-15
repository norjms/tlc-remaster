/*
 * a4sdl drawing: bitmaps, primitives, blits, sprites, rotation,
 * translucency and Allegro's built-in 8x8 text font.
 *
 * Every function takes game (logical) coordinates. A bitmap stores
 * scale x scale real pixels per game pixel, so the same calls draw sharper
 * on a higher resolution display: shapes are drawn at full resolution,
 * and image transfers resample between the source's and destination's
 * scales (box-averaged when shrinking, nearest when enlarging, which keeps
 * the original art's look). At scale 1 everything is exactly Allegro 4.
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
int a4::g_scale = 1;

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

/* bitmaps the game creates use the display scale, unless they are huge
   (keeps memory sane for very large work surfaces) */
static const long long SCALED_BITMAP_BUDGET = 4LL * 1024 * 1024;   /* game pixels */

BITMAP *a4::create_bitmap_scaled(int width, int height, int scale)
{
	if (width < 0 || height < 0) return NULL;
	if (scale < 1) scale = 1;
	BITMAP *b = (BITMAP *)calloc(1, sizeof(BITMAP));
	if (!b) return NULL;
	b->w = width;
	b->h = height;
	b->scale = scale;
	b->pitch = width * scale;
	size_t n = (size_t)(width > 0 ? width * scale : 1) * (height > 0 ? height * scale : 1);
	b->pixels = (uint32_t *)calloc(n, sizeof(uint32_t));
	if (!b->pixels) { free(b); return NULL; }
	b->owns_pixels = 1;
	b->clip = 1;
	b->cl = 0; b->ct = 0; b->cr = width; b->cb = height;
	return b;
}

BITMAP *create_bitmap(int width, int height)
{
	int s = a4::g_scale;
	if ((long long)width * height > SCALED_BITMAP_BUDGET) s = 1;
	return a4::create_bitmap_scaled(width, height, s);
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
	int s = parent->scale;
	b->w = width;
	b->h = height;
	b->scale = s;
	b->pitch = parent->pitch;
	b->pixels = parent->pixels + (size_t)y * s * parent->pitch + (size_t)x * s;
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

/* fill storage rectangle [X0,X1) x [Y0,Y1), clipped to the clip rectangle */
static void fill_s(BITMAP *b, int X0, int Y0, int X1, int Y1, uint32_t c)
{
	int s = b->scale;
	/* opaque game colours (alpha byte 0) stay opaque on remaster art */
	if (b->alpha_sprite && (c >> 24) == 0 && !is_mask(c)) c |= 0xFF000000u;
	X0 = MAX(X0, b->cl * s); X1 = MIN(X1, b->cr * s);
	Y0 = MAX(Y0, b->ct * s); Y1 = MIN(Y1, b->cb * s);
	for (int Y = Y0; Y < Y1; Y++) {
		uint32_t *p = row(b, Y);
		for (int X = X0; X < X1; X++) p[X] = c;
	}
}

/* one game pixel */
static inline void pset(BITMAP *b, int x, int y, uint32_t c)
{
	if (x < b->cl || x >= b->cr || y < b->ct || y >= b->cb) return;
	int s = b->scale;
	if (s == 1) { row(b, y)[x] = c; return; }
	fill_s(b, x * s, y * s, x * s + s, y * s + s, c);
}

/* a game-pixel sized square centred on storage point X,Y */
static inline void stamp(BITMAP *b, int X, int Y, uint32_t c)
{
	int s = b->scale, h = s / 2;
	fill_s(b, X - h, Y - h, X - h + s, Y - h + s, c);
}

void clear_to_color(BITMAP *b, int color)
{
	if (!b) return;
	fill_s(b, 0, 0, a4::sw(b), a4::sh(b), (uint32_t)color);
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
	int s = b->scale;
	return (int)row(b, y * s + s / 2)[x * s + s / 2];
}

void hline(BITMAP *b, int x1, int y, int x2, int color)
{
	if (!b || y < b->ct || y >= b->cb) return;
	if (x1 > x2) { int t = x1; x1 = x2; x2 = t; }
	int s = b->scale;
	fill_s(b, x1 * s, y * s, (x2 + 1) * s, (y + 1) * s, (uint32_t)color);
	a4::touch(b);
}

void vline(BITMAP *b, int x, int y1, int y2, int color)
{
	if (!b || x < b->cl || x >= b->cr) return;
	if (y1 > y2) { int t = y1; y1 = y2; y2 = t; }
	int s = b->scale;
	fill_s(b, x * s, y1 * s, (x + 1) * s, (y2 + 1) * s, (uint32_t)color);
	a4::touch(b);
}

void line(BITMAP *b, int x1, int y1, int x2, int y2, int color)
{
	if (!b) return;
	if (y1 == y2) { hline(b, x1, y1, x2, color); return; }
	if (x1 == x2) { vline(b, x1, y1, y2, color); return; }
	int s = b->scale;
	if (s == 1) {
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
	} else {
		/* same line at full resolution, one game pixel thick */
		int X1 = x1 * s + s / 2, Y1 = y1 * s + s / 2, X2 = x2 * s + s / 2, Y2 = y2 * s + s / 2;
		int dx = abs(X2 - X1), sx = X1 < X2 ? 1 : -1;
		int dy = -abs(Y2 - Y1), sy = Y1 < Y2 ? 1 : -1;
		int err = dx + dy;
		for (;;) {
			stamp(b, X1, Y1, (uint32_t)color);
			if (X1 == X2 && Y1 == Y2) break;
			int e2 = 2 * err;
			if (e2 >= dy) { err += dy; X1 += sx; }
			if (e2 <= dx) { err += dx; Y1 += sy; }
		}
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
	if (x1 > x2) { int t = x1; x1 = x2; x2 = t; }
	if (y1 > y2) { int t = y1; y1 = y2; y2 = t; }
	int s = b->scale;
	fill_s(b, x1 * s, y1 * s, (x2 + 1) * s, (y2 + 1) * s, (uint32_t)color);
	a4::touch(b);
}

/* Scaled ellipse (circle when rx == ry), at full resolution. Pixel (cx,cy)
   is the centre; a game pixel at distance r spans (r-0.5 .. r+0.5) game
   pixels from it, so the filled shape reaches r+0.5 and an outline is the
   ring between r-0.5 and r+0.5. */
static void ellipse_s(BITMAP *b, int cx, int cy, int rx, int ry, uint32_t color, bool fill)
{
	int s = b->scale;
	double Cx = (cx + 0.5) * s, Cy = (cy + 0.5) * s;
	double ox = (rx + 0.5) * s, oy = (ry + 0.5) * s;
	double ix = (rx - 0.5) * s, iy = (ry - 0.5) * s;
	int Y0 = (int)floor(Cy - oy), Y1 = (int)ceil(Cy + oy);
	for (int Y = Y0; Y < Y1; Y++) {
		double dy = Y + 0.5 - Cy;
		double t = 1.0 - (dy * dy) / (oy * oy);
		if (t < 0) continue;
		double hw = ox * sqrt(t);
		int A = (int)ceil(Cx - hw - 0.5), B = (int)floor(Cx + hw - 0.5) + 1;
		if (fill || ix <= 0 || iy <= 0 || fabs(dy) >= iy) {
			fill_s(b, A, Y, B, Y + 1, color);
		} else {
			double hi = ix * sqrt(1.0 - (dy * dy) / (iy * iy));
			int a2 = (int)ceil(Cx - hi - 0.5), b2 = (int)floor(Cx + hi - 0.5) + 1;
			fill_s(b, A, Y, a2, Y + 1, color);
			fill_s(b, b2, Y, B, Y + 1, color);
		}
	}
	a4::touch(b);
}

void circle(BITMAP *b, int cx, int cy, int r, int color)
{
	if (!b || r < 0) return;
	if (b->scale > 1) { ellipse_s(b, cx, cy, r, r, (uint32_t)color, false); return; }
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
	if (b->scale > 1) { ellipse_s(b, cx, cy, r, r, (uint32_t)color, true); return; }
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
	if (b->scale > 1) { ellipse_s(b, cx, cy, rx, ry, (uint32_t)color, fill); return; }
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
	int s = b->scale;
	if (s == 1) {
		for (int y = y1; y <= y3; y++) {
			double xa = (y3 == y1) ? x1 : x1 + (double)(x3 - x1) * (y - y1) / (y3 - y1);
			double xb;
			if (y < y2) xb = (y2 == y1) ? x1 : x1 + (double)(x2 - x1) * (y - y1) / (y2 - y1);
			else        xb = (y3 == y2) ? x2 : x2 + (double)(x3 - x2) * (y - y2) / (y3 - y2);
			hline(b, (int)floor(xa + 0.5), y, (int)floor(xb + 0.5), color);
		}
		return;
	}
	/* full resolution: the triangle through the vertex pixels' centres,
	   widened by half a game pixel so it covers what scale 1 covers */
	double X1 = (x1 + 0.5) * s, Y1 = (y1 + 0.5) * s, X2 = (x2 + 0.5) * s, Y2 = (y2 + 0.5) * s;
	double X3 = (x3 + 0.5) * s, Y3 = (y3 + 0.5) * s, h = s * 0.5;
	for (int Y = y1 * s; Y < (y3 + 1) * s; Y++) {
		double yc = MID(Y1, Y + 0.5, Y3);
		double xa = (Y3 == Y1) ? X1 : X1 + (X3 - X1) * (yc - Y1) / (Y3 - Y1);
		double xb;
		if (yc < Y2) xb = (Y2 == Y1) ? X1 : X1 + (X2 - X1) * (yc - Y1) / (Y2 - Y1);
		else         xb = (Y3 == Y2) ? X2 : X2 + (X3 - X2) * (yc - Y2) / (Y3 - Y2);
		if (xa > xb) { double t = xa; xa = xb; xb = t; }
		fill_s(b, (int)floor(xa - h + 0.5), Y, (int)floor(xb + h + 0.5), Y + 1, (uint32_t)color);
	}
	a4::touch(b);
}

/* ------------------------------------------------------------- transfers */

namespace {

enum Mode { COPY, MASK, TRANS, ALPHA };

bool g_alpha_blender = false;
int  g_trans_alpha = 255;

/* Copy source rectangle sx,sy,sw_,sh_ to destination rectangle
   dx,dy,dw,dh (game coordinates), at the destination's storage
   resolution. Sampling matches Allegro's stretch: each destination pixel
   takes the source pixel under its top-left corner. */
void transfer(BITMAP *s, BITMAP *d, int sx, int sy, int sw_, int sh_,
              int dx, int dy, int dw, int dh, Mode mode, bool hflip = false, bool vflip = false)
{
	if (!s || !d || dw <= 0 || dh <= 0 || sw_ <= 0 || sh_ <= 0) return;
	/* remaster art saved as PNG with alpha blends wherever the game masks */
	if (mode == MASK && s->alpha_sprite) mode = ALPHA;
	const int as = s->scale, ds = d->scale;
	int X0 = MAX(dx, d->cl) * ds, X1 = MIN(dx + dw, d->cr) * ds;
	int Y0 = MAX(dy, d->ct) * ds, Y1 = MIN(dy + dh, d->cb) * ds;
	if (X0 >= X1 || Y0 >= Y1) return;
	const int SW = a4::sw(s), SH = a4::sh(s);

	/* source storage span over destination storage span */
	const long long nx = (long long)sw_ * as, mx = (long long)dw * ds;
	const long long ny = (long long)sh_ * as, my = (long long)dh * ds;
	/* box-average integer reductions when either side is high resolution
	   (at scale 1 everywhere, keep Allegro's nearest sampling exactly) */
	int box = 1;
	if ((as > 1 || ds > 1) && nx % mx == 0 && ny % my == 0 && nx / mx == ny / my && nx / mx >= 2 && !hflip && !vflip)
		box = (int)(nx / mx);

	std::vector<int> xmap((size_t)(X1 - X0)), ymap((size_t)(Y1 - Y0));
	for (int X = X0; X < X1; X++) {
		long long o = (long long)(X - dx * ds) * nx / mx;
		if (hflip) o = (mx - 1 - (X - dx * ds)) * nx / mx;   /* mirrored position */
		xmap[X - X0] = (int)(sx * as + o);
	}
	for (int Y = Y0; Y < Y1; Y++) {
		long long o = (long long)(Y - dy * ds) * ny / my;
		if (vflip) o = (my - 1 - (Y - dy * ds)) * ny / my;
		ymap[Y - Y0] = (int)(sy * as + o);
	}

	/* same root (overlapping blit): read from a copy of the source */
	std::vector<uint32_t> tmp;
	const uint32_t *src_base = s->pixels;
	int src_pitch = s->pitch;
	if (root_of(s) == root_of(d)) {
		tmp.resize((size_t)SW * SH);
		for (int y = 0; y < SH; y++) memcpy(&tmp[(size_t)y * SW], row(s, y), (size_t)SW * 4);
		src_base = tmp.data();
		src_pitch = SW;
	}

	/* drawing old art onto remaster art: its pixels are opaque */
	const bool fix_a = d->alpha_sprite && !s->alpha_sprite;
	const bool over = d->alpha_sprite != 0;
	const bool fast_copy = (mode == COPY && box == 1 && nx == mx && !hflip && !fix_a);
	for (int Y = Y0; Y < Y1; Y++) {
		int SY = ymap[Y - Y0];
		if (SY < 0 || SY + box > SH) continue;
		uint32_t *dp = row(d, Y);
		if (fast_copy) {
			int SX0 = xmap[0];
			int a = X0, b = X1;
			if (SX0 < 0) a += -SX0, SX0 = 0;
			if (SX0 + (b - a) > SW) b = a + (SW - SX0);
			if (b > a) memcpy(dp + a, src_base + (size_t)SY * src_pitch + SX0, (size_t)(b - a) * 4);
			continue;
		}
		const uint32_t *sp = src_base + (size_t)SY * src_pitch;
		for (int X = X0; X < X1; X++) {
			int SX = xmap[X - X0];
			if (SX < 0 || SX + box > SW) continue;
			uint32_t c;
			if (box == 1) {
				c = sp[SX];
				if (mode != COPY && is_mask(c)) continue;
			} else {
				/* average the box; for masked transfers only the opaque part,
				   and leave the pixel alone when the box is mostly mask */
				unsigned r = 0, g = 0, bl = 0, al = 0, n = 0, tot = (unsigned)(box * box);
				if (mode == ALPHA) {
					/* alpha weighted average over the whole box */
					for (int j = 0; j < box; j++) {
						const uint32_t *q = sp + (size_t)j * src_pitch + SX;
						for (int i = 0; i < box; i++) {
							uint32_t p = q[i], a = p >> 24;
							r += ((p >> 16) & 255) * a; g += ((p >> 8) & 255) * a; bl += (p & 255) * a; al += a;
						}
					}
					if (al == 0) continue;
					c = ((al / tot) << 24) | ((r / al) << 16) | ((g / al) << 8) | (bl / al);
					dp[X] = over ? a4::blend_over(c, dp[X], c >> 24) : a4::blend(c, dp[X], c >> 24);
					continue;
				}
				for (int j = 0; j < box; j++) {
					const uint32_t *q = sp + (size_t)j * src_pitch + SX;
					for (int i = 0; i < box; i++) {
						uint32_t p = q[i];
						if (mode != COPY && is_mask(p)) continue;
						r += (p >> 16) & 255; g += (p >> 8) & 255; bl += p & 255; al += p >> 24; n++;
					}
				}
				if (mode != COPY && n * 2 < tot) continue;
				if (n == 0) continue;
				c = ((al / n) << 24) | ((r / n) << 16) | ((g / n) << 8) | (bl / n);
				if (is_mask(c)) c ^= 0x00010000u;   /* never produce the mask colour by averaging */
			}
			if (mode == ALPHA) {
				dp[X] = over ? a4::blend_over(c, dp[X], c >> 24) : a4::blend(c, dp[X], c >> 24);
			} else if (mode == TRANS) {
				unsigned a = g_alpha_blender ? (c >> 24) : (unsigned)g_trans_alpha;
				dp[X] = over ? a4::blend_over(c, dp[X], a) : a4::blend(c, dp[X], a);
			} else {
				dp[X] = (fix_a && (c >> 24) == 0) ? (c | 0xFF000000u) : c;
			}
		}
	}
	a4::touch(d);
}

} /* namespace */

/* clip a source rectangle against the source bounds and the destination
   clip rectangle (game coordinates); returns false when nothing is left */
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
	/* a whole-bitmap copy of an alpha sprite is an alpha sprite too
	   (the game builds button images by copying one and drawing on it) */
	if (!d->is_screen && !d->parent && dx == 0 && dy == 0 && w == d->w && h == d->h)
		d->alpha_sprite = s->alpha_sprite;
	transfer(s, d, sx, sy, w, h, dx, dy, w, h, COPY);
}

void masked_blit(BITMAP *s, BITMAP *d, int sx, int sy, int dx, int dy, int w, int h)
{
	if (!s || !d || !clip_blit(s, d, sx, sy, dx, dy, w, h)) return;
	transfer(s, d, sx, sy, w, h, dx, dy, w, h, MASK);
}

void stretch_blit(BITMAP *s, BITMAP *d, int s_x, int s_y, int s_w, int s_h, int d_x, int d_y, int d_w, int d_h)
{
	transfer(s, d, s_x, s_y, s_w, s_h, d_x, d_y, d_w, d_h, COPY);
}

void masked_stretch_blit(BITMAP *s, BITMAP *d, int s_x, int s_y, int s_w, int s_h, int d_x, int d_y, int d_w, int d_h)
{
	transfer(s, d, s_x, s_y, s_w, s_h, d_x, d_y, d_w, d_h, MASK);
}

void stretch_sprite(BITMAP *bmp, BITMAP *sprite, int x, int y, int w, int h)
{
	if (!sprite) return;
	transfer(sprite, bmp, 0, 0, sprite->w, sprite->h, x, y, w, h, MASK);
}

/* --------------------------------------------------------------- sprites */

void draw_sprite(BITMAP *bmp, BITMAP *sprite, int x, int y)
{
	if (sprite) transfer(sprite, bmp, 0, 0, sprite->w, sprite->h, x, y, sprite->w, sprite->h, MASK);
}
void draw_sprite_h_flip(BITMAP *bmp, BITMAP *sprite, int x, int y)
{
	if (sprite) transfer(sprite, bmp, 0, 0, sprite->w, sprite->h, x, y, sprite->w, sprite->h, MASK, true, false);
}
void draw_sprite_v_flip(BITMAP *bmp, BITMAP *sprite, int x, int y)
{
	if (sprite) transfer(sprite, bmp, 0, 0, sprite->w, sprite->h, x, y, sprite->w, sprite->h, MASK, false, true);
}
void draw_sprite_vh_flip(BITMAP *bmp, BITMAP *sprite, int x, int y)
{
	if (sprite) transfer(sprite, bmp, 0, 0, sprite->w, sprite->h, x, y, sprite->w, sprite->h, MASK, true, true);
}

/* Allegro rotates around the sprite centre, the sprite's top-left corner
   (before rotation) at x,y. Angles are fixed point with 256 units per
   full turn; positive is clockwise on screen. Done at the destination's
   storage resolution, sampling the source at its own resolution. */
void rotate_scaled_sprite(BITMAP *d, BITMAP *s, int x, int y, fixed angle, fixed scale)
{
	if (!s || !d || s->w <= 0 || s->h <= 0) return;
	double theta = fixtof(angle) * (2.0 * AL_PI / 256.0);
	double sc = fixtof(scale);
	if (sc <= 0) return;
	const int as = s->scale, ds = d->scale;
	double c = cos(theta), sn = sin(theta);
	double cx = x + s->w / 2.0, cy = y + s->h / 2.0;                     /* game coordinates */
	double rad = 0.5 * sqrt((double)s->w * s->w + (double)s->h * s->h) * sc + 1;
	int x0 = MAX((int)floor(cx - rad), d->cl), x1 = MIN((int)ceil(cx + rad), d->cr);
	int y0 = MAX((int)floor(cy - rad), d->ct), y1 = MIN((int)ceil(cy + rad), d->cb);
	const int SW = a4::sw(s), SH = a4::sh(s);
	for (int PY = y0 * ds; PY < y1 * ds; PY++) {
		uint32_t *dp = row(d, PY);
		double ry = (PY + 0.5) / ds - cy;
		for (int PX = x0 * ds; PX < x1 * ds; PX++) {
			double rx = (PX + 0.5) / ds - cx;
			double lx = ( c * rx + sn * ry) / sc + s->w / 2.0;
			double ly = (-sn * rx + c * ry) / sc + s->h / 2.0;
			int SX = (int)floor(lx * as), SY = (int)floor(ly * as);
			if (SX < 0 || SY < 0 || SX >= SW || SY >= SH) continue;
			uint32_t col = row(s, SY)[SX];
			if (!is_mask(col)) dp[PX] = col;
		}
	}
	a4::touch(d);
}

void rotate_sprite(BITMAP *bmp, BITMAP *sprite, int x, int y, fixed angle)
{
	rotate_scaled_sprite(bmp, sprite, x, y, angle, itofix(1));
}

/* ---------------------------------------------------------- translucency */

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
	if (s) transfer(s, d, 0, 0, s->w, s->h, x, y, s->w, s->h, TRANS);
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
