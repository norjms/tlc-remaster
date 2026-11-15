/*
 * a4sdl: the subset of the Allegro 4 API used by Starflight: The Lost Colony,
 * implemented on SDL3.
 *
 * Drop-in for <allegro.h>: same names, signatures and semantics for the calls
 * the game makes, so the game code builds unchanged on Windows, Linux and
 * macOS. Rendering is still software (32-bit bitmaps in memory); SDL only
 * presents the finished screen and supplies input.
 *
 * Pixels are 32-bit 0xAARRGGBB. makecol() returns alpha 0 and loaded
 * bitmaps without an alpha channel have alpha 0, exactly like Allegro's
 * 32-bit mode; only RGBA images (32-bit TGA, RGBA datafile objects) carry
 * alpha, which draw_trans_sprite() uses under set_alpha_blender().
 * MASK_COLOR (magenta, 0xFF00FF) is transparent for masked operations.
 */
#ifndef A4SDL_ALLEGRO_H
#define A4SDL_ALLEGRO_H

#include <stdint.h>
#include <stddef.h>
/* Allegro's header pulled these in; the game relies on that */
#include <errno.h>
#include <limits.h>
#include <math.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define A4SDL 1

/* Allegro's ASSERT/TRACE are no-ops unless DEBUGMODE is defined; the
   game shipped that way, so keep them off unless asked for */
#ifdef A4_ASSERTS
#include <assert.h>
#define ASSERT(x) assert(x)
#else
#define ASSERT(x) ((void)0)
#endif
#ifndef TRACE
#define TRACE(...) ((void)0)
#endif

/* ---------------------------------------------------------------- basics */

#define AL_CONST const
#ifndef TRUE
#define TRUE  -1
#define FALSE 0
#endif
#ifndef MIN
#define MIN(x,y)     (((x) < (y)) ? (x) : (y))
#define MAX(x,y)     (((x) > (y)) ? (x) : (y))
#define MID(x,y,z)   MAX((x), MIN((y), (z)))
#endif
#ifndef ABS
#define ABS(x)       (((x) >= 0) ? (x) : (-(x)))
#endif
#define AL_PI        3.14159265358979323846

#define END_OF_MAIN()

typedef int32_t fixed;
static inline fixed itofix(int x)      { return (fixed)((uint32_t)x << 16); }
static inline fixed ftofix(double x)   { return (fixed)(x * 65536.0 + (x < 0 ? -0.5 : 0.5)); }
static inline int   fixtoi(fixed x)    { return (x >> 16) + ((x & 0x8000) >> 15); }
static inline double fixtof(fixed x)   { return (double)x / 65536.0; }

/* --------------------------------------------------------------- bitmaps */

typedef struct BITMAP
{
   int w, h;               /* size in game (logical) pixels */
   int clip;               /* clipping enabled (always, kept for compatibility) */
   int cl, cr, ct, cb;     /* clip rectangle in game pixels: [cl,cr) x [ct,cb) */
   int scale;              /* storage pixels per game pixel (1..4); the game never sees it */
   uint32_t *pixels;       /* first storage pixel of row 0 (w*scale x h*scale) */
   int pitch;              /* storage row stride in pixels */
   int owns_pixels;        /* false for sub-bitmaps */
   struct BITMAP *parent;  /* for sub-bitmaps, the bitmap that owns the pixels */
   int is_screen;          /* drawing to it marks the display dirty */
} BITMAP;

typedef struct RGB { unsigned char r, g, b, filler; } RGB;
typedef RGB PALETTE[256];

#define MASK_COLOR_32 0x00FF00FF

#ifdef __cplusplus
extern "C" {
#endif

extern BITMAP *screen;
#define SCREEN_W (screen ? screen->w : 0)
#define SCREEN_H (screen ? screen->h : 0)

BITMAP *create_bitmap(int width, int height);
BITMAP *create_sub_bitmap(BITMAP *parent, int x, int y, int width, int height);
void destroy_bitmap(BITMAP *bitmap);
BITMAP *load_bitmap(const char *filename, RGB *pal);
void set_color_depth(int depth);
int bitmap_color_depth(BITMAP *bmp);
int bitmap_mask_color(BITMAP *bmp);

int makecol(int r, int g, int b);
int makeacol(int r, int g, int b, int a);
int makecol32(int r, int g, int b);
int makeacol32(int r, int g, int b, int a);
int getr(int c);
int getg(int c);
int getb(int c);
int geta(int c);

/* primitives (clipped to the destination's clip rectangle) */
void clear_bitmap(BITMAP *bitmap);
static inline void clear(BITMAP *bitmap) { clear_bitmap(bitmap); }  /* Allegro 3 name */
void clear_to_color(BITMAP *bitmap, int color);
void putpixel(BITMAP *bmp, int x, int y, int color);
int  getpixel(BITMAP *bmp, int x, int y);
void line(BITMAP *bmp, int x1, int y1, int x2, int y2, int color);
void hline(BITMAP *bmp, int x1, int y, int x2, int color);
void vline(BITMAP *bmp, int x, int y1, int y2, int color);
void rect(BITMAP *bmp, int x1, int y1, int x2, int y2, int color);
void rectfill(BITMAP *bmp, int x1, int y1, int x2, int y2, int color);
void circle(BITMAP *bmp, int x, int y, int radius, int color);
void circlefill(BITMAP *bmp, int x, int y, int radius, int color);
void ellipse(BITMAP *bmp, int x, int y, int rx, int ry, int color);
void ellipsefill(BITMAP *bmp, int x, int y, int rx, int ry, int color);
void triangle(BITMAP *bmp, int x1, int y1, int x2, int y2, int x3, int y3, int color);
void set_clip_rect(BITMAP *bitmap, int x1, int y1, int x2, int y2);

/* blits and sprites */
void blit(BITMAP *source, BITMAP *dest, int source_x, int source_y, int dest_x, int dest_y, int width, int height);
void masked_blit(BITMAP *source, BITMAP *dest, int source_x, int source_y, int dest_x, int dest_y, int width, int height);
void stretch_blit(BITMAP *s, BITMAP *d, int s_x, int s_y, int s_w, int s_h, int d_x, int d_y, int d_w, int d_h);
void masked_stretch_blit(BITMAP *s, BITMAP *d, int s_x, int s_y, int s_w, int s_h, int d_x, int d_y, int d_w, int d_h);
void stretch_sprite(BITMAP *bmp, BITMAP *sprite, int x, int y, int w, int h);
void draw_sprite(BITMAP *bmp, BITMAP *sprite, int x, int y);
void draw_sprite_h_flip(BITMAP *bmp, BITMAP *sprite, int x, int y);
void draw_sprite_v_flip(BITMAP *bmp, BITMAP *sprite, int x, int y);
void draw_sprite_vh_flip(BITMAP *bmp, BITMAP *sprite, int x, int y);
void rotate_sprite(BITMAP *bmp, BITMAP *sprite, int x, int y, fixed angle);
void rotate_scaled_sprite(BITMAP *bmp, BITMAP *sprite, int x, int y, fixed angle, fixed scale);

/* translucency: set_trans_blender(..., a) gives a constant alpha,
   set_alpha_blender() uses the sprite's own alpha channel */
void set_trans_blender(int r, int g, int b, int a);
void set_alpha_blender(void);
void draw_trans_sprite(BITMAP *bmp, BITMAP *sprite, int x, int y);

/* ----------------------------------------------------------------- text */

typedef struct FONT FONT;
extern FONT *font;   /* Allegro's built-in 8x8 font */

void textout_ex(BITMAP *bmp, const FONT *f, const char *str, int x, int y, int color, int bg);
void textout_centre_ex(BITMAP *bmp, const FONT *f, const char *str, int x, int y, int color, int bg);
void textout_right_ex(BITMAP *bmp, const FONT *f, const char *str, int x, int y, int color, int bg);
void textprintf_ex(BITMAP *bmp, const FONT *f, int x, int y, int color, int bg, const char *format, ...);
void textprintf_centre_ex(BITMAP *bmp, const FONT *f, int x, int y, int color, int bg, const char *format, ...);
void textprintf_right_ex(BITMAP *bmp, const FONT *f, int x, int y, int color, int bg, const char *format, ...);
int  text_length(const FONT *f, const char *str);
int  text_height(const FONT *f);

/* ------------------------------------------------------------ datafiles */

#define DAT_ID(a,b,c,d) (((a)<<24) | ((b)<<16) | ((c)<<8) | (d))
#define DAT_FILE   DAT_ID('F','I','L','E')
#define DAT_DATA   DAT_ID('D','A','T','A')
#define DAT_BITMAP DAT_ID('B','M','P',' ')
#define DAT_END    -1

typedef struct DATAFILE
{
   void *dat;
   int type;
   long size;
   void *prop;
} DATAFILE;

DATAFILE *load_datafile(const char *filename);
void unload_datafile(DATAFILE *dat);

/* --------------------------------------------------------------- system */

#define SYSTEM_AUTODETECT 0
int  allegro_init(void);
void allegro_exit(void);
void allegro_message(const char *msg, ...);
int  alert(const char *s1, const char *s2, const char *s3, const char *b1, const char *b2, int c1, int c2);
void rest(unsigned int ms);
int  install_timer(void);

/* graphics modes */
#define GFX_TEXT                  -1
#define GFX_AUTODETECT             0
#define GFX_AUTODETECT_FULLSCREEN  1
#define GFX_AUTODETECT_WINDOWED    2
#define GFX_SAFE                   DAT_ID('S','A','F','E')
#define GFX_DIRECTX                DAT_ID('D','X','A','C')
#define GFX_DIRECTX_ACCEL          DAT_ID('D','X','A','C')
#define GFX_DIRECTX_WIN            DAT_ID('D','X','W','N')
#define GFX_GDI                    DAT_ID('G','D','I','B')

typedef struct GFX_MODE { int width, height, bpp; } GFX_MODE;
typedef struct GFX_MODE_LIST { int num_modes; GFX_MODE *mode; } GFX_MODE_LIST;

int  set_gfx_mode(int card, int w, int h, int v_w, int v_h);
GFX_MODE_LIST *get_gfx_mode_list(int card);
void destroy_gfx_mode_list(GFX_MODE_LIST *gfx_mode_list);
int  get_desktop_resolution(int *width, int *height);
int  desktop_color_depth(void);
int  get_refresh_rate(void);
void set_window_title(const char *name);
int  show_os_cursor(int cursor);
void show_mouse(BITMAP *bmp);
void vsync(void);

/* a4sdl extensions (not in Allegro) */
void a4_init_paths(void);                /* chdir to the folder holding data/ */
void a4_use_user_dir_if_needed(void);    /* writable per-user game folder when needed */
void a4_set_logical_size(int w, int h);  /* size of 'screen'; the window scales it */
void a4_flip(void);                      /* present 'screen' now */
int  a4_close_requested(void);           /* window close button was pressed */

/* ------------------------------------------------------------- keyboard */

enum {
   KEY_A = 1, KEY_B, KEY_C, KEY_D, KEY_E, KEY_F, KEY_G, KEY_H, KEY_I, KEY_J, KEY_K, KEY_L, KEY_M,
   KEY_N, KEY_O, KEY_P, KEY_Q, KEY_R, KEY_S, KEY_T, KEY_U, KEY_V, KEY_W, KEY_X, KEY_Y, KEY_Z,
   KEY_0 = 27, KEY_1, KEY_2, KEY_3, KEY_4, KEY_5, KEY_6, KEY_7, KEY_8, KEY_9,
   KEY_0_PAD = 37, KEY_1_PAD, KEY_2_PAD, KEY_3_PAD, KEY_4_PAD, KEY_5_PAD, KEY_6_PAD, KEY_7_PAD, KEY_8_PAD, KEY_9_PAD,
   KEY_F1 = 47, KEY_F2, KEY_F3, KEY_F4, KEY_F5, KEY_F6, KEY_F7, KEY_F8, KEY_F9, KEY_F10, KEY_F11, KEY_F12,
   KEY_ESC = 59, KEY_TILDE, KEY_MINUS, KEY_EQUALS, KEY_BACKSPACE, KEY_TAB, KEY_OPENBRACE, KEY_CLOSEBRACE,
   KEY_ENTER = 67, KEY_COLON, KEY_QUOTE, KEY_BACKSLASH, KEY_BACKSLASH2, KEY_COMMA, KEY_STOP, KEY_SLASH,
   KEY_SPACE = 75, KEY_INSERT, KEY_DEL, KEY_HOME, KEY_END, KEY_PGUP, KEY_PGDN, KEY_LEFT, KEY_RIGHT,
   KEY_UP = 84, KEY_DOWN, KEY_SLASH_PAD, KEY_ASTERISK, KEY_MINUS_PAD, KEY_PLUS_PAD, KEY_DEL_PAD,
   KEY_ENTER_PAD = 91, KEY_PRTSCR, KEY_PAUSE, KEY_ABNT_C1, KEY_YEN, KEY_KANA, KEY_CONVERT, KEY_NOCONVERT,
   KEY_AT = 99, KEY_CIRCUMFLEX, KEY_COLON2, KEY_KANJI, KEY_EQUALS_PAD, KEY_BACKQUOTE, KEY_SEMICOLON,
   KEY_COMMAND = 106,
   KEY_MODIFIERS = 115, KEY_LSHIFT = 115, KEY_RSHIFT, KEY_LCONTROL, KEY_RCONTROL, KEY_ALT, KEY_ALTGR,
   KEY_LWIN = 121, KEY_RWIN, KEY_MENU, KEY_SCRLOCK, KEY_NUMLOCK, KEY_CAPSLOCK,
   KEY_MAX = 127
};

/* 256 entries (not KEY_MAX): the game copies 256 bytes out of it */
extern volatile char key[256];
extern volatile int key_shifts;
int install_keyboard(void);
int poll_keyboard(void);
int keypressed(void);
int readkey(void);
void clear_keybuf(void);
int scancode_to_ascii(int scancode);

/* ---------------------------------------------------------------- mouse */

extern volatile int mouse_x, mouse_y, mouse_z, mouse_b;
int install_mouse(void);   /* returns the number of buttons */
int poll_mouse(void);
void position_mouse(int x, int y);

/* ---------------------------------------------------------------- files */

#define FA_RDONLY 1
#define FA_HIDDEN 2
#define FA_SYSTEM 4
#define FA_LABEL  8
#define FA_DIREC  16
#define FA_ARCH   32
#define FA_ALL    63
int exists(const char *filename);
int file_exists(const char *filename, int attrib, int *aret);
int delete_file(const char *filename);

#ifdef __cplusplus
}
#endif

#endif /* A4SDL_ALLEGRO_H */
