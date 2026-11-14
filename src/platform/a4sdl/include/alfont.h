/*
 * a4sdl: AllegroFont (alfont) API used by the game, on stb_truetype.
 *
 * y is the top of the text line, as in AllegroFont. Glyphs are rendered
 * anti-aliased and blended onto the destination. bg == -1 draws no
 * background; otherwise the text box is filled with bg first.
 */
#ifndef A4SDL_ALFONT_H
#define A4SDL_ALFONT_H

#include "allegro.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct ALFONT_FONT ALFONT_FONT;

#define ALFONT_OK     0
#define ALFONT_ERROR -1

int  alfont_init(void);
void alfont_exit(void);
ALFONT_FONT *alfont_load_font(const char *filepathname);
void alfont_destroy_font(ALFONT_FONT *f);
int  alfont_set_font_size(ALFONT_FONT *f, int h);
int  alfont_get_font_height(ALFONT_FONT *f);
int  alfont_text_height(ALFONT_FONT *f);
int  alfont_text_length(ALFONT_FONT *f, const char *str);

void alfont_textout(BITMAP *bmp, ALFONT_FONT *f, const char *s, int x, int y, int color);
void alfont_textout_ex(BITMAP *bmp, ALFONT_FONT *f, const char *s, int x, int y, int color, int bg);
void alfont_textout_centre(BITMAP *bmp, ALFONT_FONT *f, const char *s, int x, int y, int color);
void alfont_textout_centre_ex(BITMAP *bmp, ALFONT_FONT *f, const char *s, int x, int y, int color, int bg);
void alfont_textout_right(BITMAP *bmp, ALFONT_FONT *f, const char *s, int x, int y, int color);
void alfont_textout_right_ex(BITMAP *bmp, ALFONT_FONT *f, const char *s, int x, int y, int color, int bg);
void alfont_textprintf(BITMAP *bmp, ALFONT_FONT *f, int x, int y, int color, const char *format, ...);
void alfont_textprintf_ex(BITMAP *bmp, ALFONT_FONT *f, int x, int y, int color, int bg, const char *format, ...);
void alfont_textprintf_centre_ex(BITMAP *bmp, ALFONT_FONT *f, int x, int y, int color, int bg, const char *format, ...);
void alfont_textprintf_right_ex(BITMAP *bmp, ALFONT_FONT *f, int x, int y, int color, int bg, const char *format, ...);

#ifdef __cplusplus
}
#endif

#endif /* A4SDL_ALFONT_H */
