/*
 * miniaudio implementation unit.
 *
 * Compiled as C, in its own translation unit, so that miniaudio's
 * <windows.h> include never meets Allegro 4's headers (they clash on
 * BITMAP, RGB and friends). The rest of the game only sees the
 * declarations in miniaudio.h, via AudioSystem.cpp.
 *
 * stb_vorbis provides Ogg Vorbis decoding; the game's music is .ogg.
 */

#define STB_VORBIS_HEADER_ONLY
#include "stb_vorbis.c"

/* No MA_NO_* options here: they must match every unit that includes
 * miniaudio.h, or struct layouts (ma_engine, ma_sound) could differ. */
#define MINIAUDIO_IMPLEMENTATION
#include "miniaudio.h"

#undef STB_VORBIS_HEADER_ONLY
#include "stb_vorbis.c"
