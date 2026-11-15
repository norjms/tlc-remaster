/*
 * a4sdl: AllegroFont (alfont) replacement on stb_truetype.
 *
 * Metrics follow AllegroFont/FreeType: the size is the pixel size of the
 * em square, y is the top of the line (baseline at y + ascender), advances
 * are whole pixels and there is no kerning. Glyphs are anti-aliased and
 * cached per (size, character).
 */
#include "a4_internal.h"
#include "alfont.h"

#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <vector>

#define STB_TRUETYPE_IMPLEMENTATION
#include "stb/stb_truetype.h"

namespace {

struct Glyph
{
	int w = 0, h = 0, xoff = 0, yoff = 0, advance = 0;
	std::vector<unsigned char> alpha;
};

} /* namespace */

struct ALFONT_FONT
{
	std::vector<unsigned char> data;
	stbtt_fontinfo info;
	int size = 12;
	float scale = 1;
	int ascender = 0;
	std::map<std::pair<int, int>, Glyph> cache;   /* (size*8 + storage scale, codepoint) */
};

/* AllegroFont's alfont_set_font_size() does not use h as the em size: it
   searches for the FreeType pixel size whose ascender + |descender| (as
   FreeType rounds them: ascender up, descender down) equals h, stepping
   one pixel at a time and stopping just short if it overshoots. Same here,
   so text sizes and layouts match the original game. */
static void apply_size(ALFONT_FONT *f, int h)
{
	if (h < 1) h = 1;
	f->size = h;
	int asc = 0, desc = 0, gap = 0;
	stbtt_GetFontVMetrics(&f->info, &asc, &desc, &gap);
	auto real_height = [&](int px, float &scale, int &ascender) {
		scale = stbtt_ScaleForMappingEmToPixels(&f->info, (float)px);
		ascender = (int)ceilf(asc * scale);
		int descender = (int)ceilf(-desc * scale);
		return ascender + descender;
	};
	int test = h, direction = 0;
	float scale = 1;
	int ascender = 0;
	for (int guard = 0; guard < 512; guard++) {
		int rh = real_height(test, scale, ascender);
		if (rh == h) break;
		if (direction == 0) direction = (rh > h) ? -1 : 1;
		else if (direction > 0 && rh > h) { test--; real_height(test, scale, ascender); break; }
		else if (direction < 0 && rh < h) break;
		if (test + direction <= 0) break;
		test += direction;
	}
	f->scale = scale;
	f->ascender = ascender;
	f->cache.clear();
}

/* Glyph for codepoint cp rasterized at storage scale s. The advance is
   always the scale-1 advance (game pixels) so layout never changes with
   the display; the bitmap is drawn at s times the size for sharp text. */
static const Glyph &glyph(ALFONT_FONT *f, int cp, int s = 1)
{
	auto k = std::make_pair(f->size * 8 + s, cp);
	auto it = f->cache.find(k);
	if (it != f->cache.end()) return it->second;
	Glyph g;
	int adv = 0, lsb = 0;
	stbtt_GetCodepointHMetrics(&f->info, cp, &adv, &lsb);
	g.advance = (int)floorf(adv * f->scale + 0.5f);
	float rs = f->scale * s;
	unsigned char *bm = stbtt_GetCodepointBitmap(&f->info, rs, rs, cp, &g.w, &g.h, &g.xoff, &g.yoff);
	if (bm) {
		g.alpha.assign(bm, bm + (size_t)g.w * g.h);
		stbtt_FreeBitmap(bm, NULL);
	}
	return f->cache.emplace(k, std::move(g)).first->second;
}

static int text_width(ALFONT_FONT *f, const char *s)
{
	int w = 0;
	for (const unsigned char *p = (const unsigned char *)s; p && *p; p++) w += glyph(f, *p).advance;
	return w;
}

static void draw_text(BITMAP *b, ALFONT_FONT *f, const char *s_, int x, int y, int color, int bg)
{
	if (!b || !f || !s_) return;
	if (bg >= 0) rectfill(b, x, y, x + text_width(f, s_) - 1, y + f->size - 1, bg);
	uint32_t c = (color == -1) ? 0x00FFFFFFu : (uint32_t)color;
	const int s = b->scale;
	const int CL = b->cl * s, CR = b->cr * s, CT = b->ct * s, CB = b->cb * s;
	int pen = x, base = y + f->ascender;
	for (const unsigned char *p = (const unsigned char *)s_; *p; p++) {
		const Glyph &adv = glyph(f, *p);
		const Glyph &g = s == 1 ? adv : glyph(f, *p, s);
		for (int gy = 0; gy < g.h; gy++) {
			int dy = base * s + g.yoff + gy;
			if (dy < CT || dy >= CB) continue;
			uint32_t *drow = a4::row(b, dy);
			const unsigned char *arow = &g.alpha[(size_t)gy * g.w];
			for (int gx = 0; gx < g.w; gx++) {
				int dx = pen * s + g.xoff + gx;
				if (dx < CL || dx >= CR || !arow[gx]) continue;
				drow[dx] = a4::blend(c, drow[dx], arow[gx]);
			}
		}
		pen += adv.advance;
	}
	a4::touch(b);
}

#define A4_FORMAT(buf, fmt) \
	char buf[2048]; \
	va_list ap; va_start(ap, fmt); vsnprintf(buf, sizeof buf, fmt, ap); va_end(ap)

int  alfont_init(void) { return 0; }
void alfont_exit(void) {}

ALFONT_FONT *alfont_load_font(const char *filepathname)
{
	std::string path = a4::resolve_path(filepathname);
	FILE *fp = fopen(path.c_str(), "rb");
	if (!fp) return NULL;
	ALFONT_FONT *f = new ALFONT_FONT;
	fseek(fp, 0, SEEK_END);
	long n = ftell(fp);
	fseek(fp, 0, SEEK_SET);
	f->data.resize(n > 0 ? (size_t)n : 0);
	size_t got = n > 0 ? fread(f->data.data(), 1, (size_t)n, fp) : 0;
	fclose(fp);
	if (n <= 0 || got != (size_t)n ||
	    !stbtt_InitFont(&f->info, f->data.data(), stbtt_GetFontOffsetForIndex(f->data.data(), 0))) {
		delete f;
		return NULL;
	}
	apply_size(f, 12);
	return f;
}

void alfont_destroy_font(ALFONT_FONT *f) { delete f; }

int alfont_set_font_size(ALFONT_FONT *f, int h)
{
	if (!f) return -1;
	apply_size(f, h);
	return 0;
}

int alfont_get_font_height(ALFONT_FONT *f) { return f ? f->size : 0; }
int alfont_text_height(ALFONT_FONT *f)     { return f ? f->size : 0; }
int alfont_text_length(ALFONT_FONT *f, const char *str) { return f ? text_width(f, str) : 0; }

void alfont_textout(BITMAP *b, ALFONT_FONT *f, const char *s, int x, int y, int color)
{
	draw_text(b, f, s, x, y, color, -1);
}

void alfont_textout_ex(BITMAP *b, ALFONT_FONT *f, const char *s, int x, int y, int color, int bg)
{
	draw_text(b, f, s, x, y, color, bg);
}

void alfont_textout_centre(BITMAP *b, ALFONT_FONT *f, const char *s, int x, int y, int color)
{
	if (f) draw_text(b, f, s, x - text_width(f, s) / 2, y, color, -1);
}

void alfont_textout_centre_ex(BITMAP *b, ALFONT_FONT *f, const char *s, int x, int y, int color, int bg)
{
	if (f) draw_text(b, f, s, x - text_width(f, s) / 2, y, color, bg);
}

void alfont_textout_right(BITMAP *b, ALFONT_FONT *f, const char *s, int x, int y, int color)
{
	if (f) draw_text(b, f, s, x - text_width(f, s), y, color, -1);
}

void alfont_textout_right_ex(BITMAP *b, ALFONT_FONT *f, const char *s, int x, int y, int color, int bg)
{
	if (f) draw_text(b, f, s, x - text_width(f, s), y, color, bg);
}

void alfont_textprintf(BITMAP *b, ALFONT_FONT *f, int x, int y, int color, const char *format, ...)
{
	A4_FORMAT(buf, format);
	draw_text(b, f, buf, x, y, color, -1);
}

void alfont_textprintf_ex(BITMAP *b, ALFONT_FONT *f, int x, int y, int color, int bg, const char *format, ...)
{
	A4_FORMAT(buf, format);
	draw_text(b, f, buf, x, y, color, bg);
}

void alfont_textprintf_centre_ex(BITMAP *b, ALFONT_FONT *f, int x, int y, int color, int bg, const char *format, ...)
{
	A4_FORMAT(buf, format);
	if (f) draw_text(b, f, buf, x - text_width(f, buf) / 2, y, color, bg);
}

void alfont_textprintf_right_ex(BITMAP *b, ALFONT_FONT *f, int x, int y, int color, int bg, const char *format, ...)
{
	A4_FORMAT(buf, format);
	if (f) draw_text(b, f, buf, x - text_width(f, buf), y, color, bg);
}
