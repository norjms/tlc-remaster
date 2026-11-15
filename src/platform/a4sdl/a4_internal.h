/* a4sdl internals shared between the implementation files. */
#pragma once

#include "allegro.h"
#include <string>

namespace a4 {

/* Resolution independence: the game works in its 1024x768 coordinates while
   every bitmap stores scale x scale real pixels per game pixel. 'scale' is
   chosen once from the display (see set_gfx_mode); bitmaps the game creates
   use it, images are loaded at the best art tier available (name@2x.png...),
   and blits resample between bitmaps of different scales. */
extern int g_scale;

/* set whenever something draws to 'screen' (or a sub-bitmap of it);
   cleared by a4_flip() */
extern bool screen_dirty;

inline void touch(BITMAP *b)
{
	if (b && b->is_screen) screen_dirty = true;
}

inline bool is_mask(uint32_t c) { return (c & 0x00FFFFFFu) == 0x00FF00FFu; }

/* storage row y (0 .. h*scale-1) */
inline uint32_t *row(BITMAP *b, int y) { return b->pixels + (size_t)y * b->pitch; }
inline int sw(const BITMAP *b) { return b->w * b->scale; }
inline int sh(const BITMAP *b) { return b->h * b->scale; }

/* a bitmap with an explicit storage scale (create_bitmap uses g_scale) */
BITMAP *create_bitmap_scaled(int width, int height, int scale);

/* blend src over dst with alpha 0..255; the result keeps dst's alpha byte */
inline uint32_t blend(uint32_t src, uint32_t dst, unsigned a)
{
	if (a >= 255) return (src & 0x00FFFFFFu) | (dst & 0xFF000000u);
	if (a == 0) return dst;
	unsigned na = 255 - a;
	unsigned rb = (((src & 0xFF00FFu) * a + (dst & 0xFF00FFu) * na + 0x800080u) >> 8) & 0xFF00FFu;
	unsigned g  = (((src & 0x00FF00u) * a + (dst & 0x00FF00u) * na + 0x008000u) >> 8) & 0x00FF00u;
	return rb | g | (dst & 0xFF000000u);
}

/* Resolve a game path to a real file: accepts '\' separators and, on
   case-sensitive file systems, matches each path component ignoring case
   (the game was written on Windows). Returns the input unchanged when
   nothing matches. */
std::string resolve_path(const char *path);

} /* namespace a4 */
