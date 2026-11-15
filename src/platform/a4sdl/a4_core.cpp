/*
 * a4sdl core: SDL3 window and presentation, keyboard and mouse state in
 * Allegro's form, timing, display mode queries and message boxes.
 *
 * 'screen' is a memory bitmap of the logical game size. a4_flip() uploads
 * it to a streaming texture and SDL scales it into the window with
 * letterboxing, so the game always sees its native resolution while the
 * window can be any size, fullscreen, or high-DPI. Mouse coordinates are
 * converted back into that logical space.
 */
#include "a4_internal.h"

#include <SDL3/SDL.h>

#include <cstdarg>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <vector>

BITMAP *screen = NULL;
volatile char key[256];
volatile int key_shifts = 0;
volatile int mouse_x = 0, mouse_y = 0, mouse_z = 0, mouse_b = 0;

namespace {

SDL_Window   *g_window = NULL;
SDL_Renderer *g_renderer = NULL;
SDL_Texture  *g_texture = NULL;
bool g_sdl_up = false;
bool g_close = false;
bool g_os_cursor = false;
int  g_logical_w = 0, g_logical_h = 0;
std::string g_title = "Starflight - The Lost Colony";

/* small keyboard buffer for keypressed()/readkey() */
int g_keybuf[64];
int g_keyhead = 0, g_keytail = 0;

bool sdl_up()
{
	if (g_sdl_up) return true;
	SDL_SetAppMetadata("Starflight - The Lost Colony", "2.x", "com.starflight.tlc");
	if (!SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS)) {
		fprintf(stderr, "a4sdl: SDL_Init failed: %s\n", SDL_GetError());
		return false;
	}
	g_sdl_up = true;
	return true;
}

int map_scancode(SDL_Scancode sc)
{
	if (sc >= SDL_SCANCODE_A && sc <= SDL_SCANCODE_Z) return KEY_A + (sc - SDL_SCANCODE_A);
	if (sc >= SDL_SCANCODE_1 && sc <= SDL_SCANCODE_9) return KEY_1 + (sc - SDL_SCANCODE_1);
	if (sc >= SDL_SCANCODE_F1 && sc <= SDL_SCANCODE_F12) return KEY_F1 + (sc - SDL_SCANCODE_F1);
	if (sc >= SDL_SCANCODE_KP_1 && sc <= SDL_SCANCODE_KP_9) return KEY_1_PAD + (sc - SDL_SCANCODE_KP_1);
	switch (sc) {
	case SDL_SCANCODE_0:            return KEY_0;
	case SDL_SCANCODE_KP_0:         return KEY_0_PAD;
	case SDL_SCANCODE_ESCAPE:       return KEY_ESC;
	case SDL_SCANCODE_GRAVE:        return KEY_TILDE;
	case SDL_SCANCODE_MINUS:        return KEY_MINUS;
	case SDL_SCANCODE_EQUALS:       return KEY_EQUALS;
	case SDL_SCANCODE_BACKSPACE:    return KEY_BACKSPACE;
	case SDL_SCANCODE_TAB:          return KEY_TAB;
	case SDL_SCANCODE_LEFTBRACKET:  return KEY_OPENBRACE;
	case SDL_SCANCODE_RIGHTBRACKET: return KEY_CLOSEBRACE;
	case SDL_SCANCODE_RETURN:       return KEY_ENTER;
	case SDL_SCANCODE_SEMICOLON:    return KEY_COLON;
	case SDL_SCANCODE_APOSTROPHE:   return KEY_QUOTE;
	case SDL_SCANCODE_BACKSLASH:    return KEY_BACKSLASH;
	case SDL_SCANCODE_NONUSBACKSLASH: return KEY_BACKSLASH2;
	case SDL_SCANCODE_COMMA:        return KEY_COMMA;
	case SDL_SCANCODE_PERIOD:       return KEY_STOP;
	case SDL_SCANCODE_SLASH:        return KEY_SLASH;
	case SDL_SCANCODE_SPACE:        return KEY_SPACE;
	case SDL_SCANCODE_INSERT:       return KEY_INSERT;
	case SDL_SCANCODE_DELETE:       return KEY_DEL;
	case SDL_SCANCODE_HOME:         return KEY_HOME;
	case SDL_SCANCODE_END:          return KEY_END;
	case SDL_SCANCODE_PAGEUP:       return KEY_PGUP;
	case SDL_SCANCODE_PAGEDOWN:     return KEY_PGDN;
	case SDL_SCANCODE_LEFT:         return KEY_LEFT;
	case SDL_SCANCODE_RIGHT:        return KEY_RIGHT;
	case SDL_SCANCODE_UP:           return KEY_UP;
	case SDL_SCANCODE_DOWN:         return KEY_DOWN;
	case SDL_SCANCODE_KP_DIVIDE:    return KEY_SLASH_PAD;
	case SDL_SCANCODE_KP_MULTIPLY:  return KEY_ASTERISK;
	case SDL_SCANCODE_KP_MINUS:     return KEY_MINUS_PAD;
	case SDL_SCANCODE_KP_PLUS:      return KEY_PLUS_PAD;
	case SDL_SCANCODE_KP_PERIOD:    return KEY_DEL_PAD;
	case SDL_SCANCODE_KP_ENTER:     return KEY_ENTER_PAD;
	case SDL_SCANCODE_KP_EQUALS:    return KEY_EQUALS_PAD;
	case SDL_SCANCODE_PRINTSCREEN:  return KEY_PRTSCR;
	case SDL_SCANCODE_PAUSE:        return KEY_PAUSE;
	case SDL_SCANCODE_LSHIFT:       return KEY_LSHIFT;
	case SDL_SCANCODE_RSHIFT:       return KEY_RSHIFT;
	case SDL_SCANCODE_LCTRL:        return KEY_LCONTROL;
	case SDL_SCANCODE_RCTRL:        return KEY_RCONTROL;
	case SDL_SCANCODE_LALT:         return KEY_ALT;
	case SDL_SCANCODE_RALT:         return KEY_ALTGR;
	case SDL_SCANCODE_LGUI:         return KEY_LWIN;
	case SDL_SCANCODE_RGUI:         return KEY_RWIN;
	case SDL_SCANCODE_APPLICATION:  return KEY_MENU;
	case SDL_SCANCODE_SCROLLLOCK:   return KEY_SCRLOCK;
	case SDL_SCANCODE_NUMLOCKCLEAR: return KEY_NUMLOCK;
	case SDL_SCANCODE_CAPSLOCK:     return KEY_CAPSLOCK;
	default:                        return 0;
	}
}

void update_mouse_from(float wx, float wy)
{
	if (!g_renderer) { mouse_x = (int)wx; mouse_y = (int)wy; return; }
	float lx = wx, ly = wy;
	SDL_RenderCoordinatesFromWindow(g_renderer, wx, wy, &lx, &ly);
	int x = (int)lx, y = (int)ly;
	if (screen) {
		x = MID(0, x, screen->w - 1);
		y = MID(0, y, screen->h - 1);
	}
	mouse_x = x;
	mouse_y = y;
}

void pump()
{
	if (!g_sdl_up) return;
	SDL_Event e;
	while (SDL_PollEvent(&e)) {
		switch (e.type) {
		case SDL_EVENT_QUIT:
		case SDL_EVENT_WINDOW_CLOSE_REQUESTED:
			g_close = true;
			break;
		case SDL_EVENT_KEY_DOWN:
		case SDL_EVENT_KEY_UP: {
			int k = map_scancode(e.key.scancode);
			if (k) key[k] = (e.type == SDL_EVENT_KEY_DOWN) ? 1 : 0;
			if (e.type == SDL_EVENT_KEY_DOWN && k) {
				int next = (g_keytail + 1) % 64;
				if (next != g_keyhead) { g_keybuf[g_keytail] = (k << 8) | (scancode_to_ascii(k) & 0xFF); g_keytail = next; }
			}
			SDL_Keymod m = SDL_GetModState();
			key_shifts = ((m & SDL_KMOD_SHIFT) ? 0x0001 : 0) | ((m & SDL_KMOD_CTRL) ? 0x0002 : 0) | ((m & SDL_KMOD_ALT) ? 0x0004 : 0);
			break;
		}
		case SDL_EVENT_MOUSE_MOTION:
			update_mouse_from(e.motion.x, e.motion.y);
			break;
		case SDL_EVENT_MOUSE_BUTTON_DOWN:
		case SDL_EVENT_MOUSE_BUTTON_UP: {
			int bit = 0;
			if (e.button.button == SDL_BUTTON_LEFT) bit = 1;
			else if (e.button.button == SDL_BUTTON_RIGHT) bit = 2;
			else if (e.button.button == SDL_BUTTON_MIDDLE) bit = 4;
			if (e.type == SDL_EVENT_MOUSE_BUTTON_DOWN) mouse_b |= bit; else mouse_b &= ~bit;
			update_mouse_from(e.button.x, e.button.y);
			break;
		}
		case SDL_EVENT_MOUSE_WHEEL:
			mouse_z += (e.wheel.integer_y != 0) ? e.wheel.integer_y : (int)e.wheel.y;
			break;
		case SDL_EVENT_WINDOW_FOCUS_LOST:
			/* avoid stuck keys and buttons when alt-tabbing away */
			memset((void *)key, 0, sizeof key);
			mouse_b = 0;
			break;
		default:
			break;
		}
	}
}

/* ---- automated testing hooks (environment variables, off by default) ----
   A4_SHOT_DIR=dir      save screen to dir/frame_NNNNN.bmp at the frames
   A4_SHOT_FRAMES=a,b,c listed here (default: every 120th frame)
   A4_INPUT="f:cmd;..." inject input at frame f. cmds: key=N (Allegro key
                        code, held for 3 frames), click=X,Y (left click in
                        game coordinates), move=X,Y, quit */
struct ScriptedInput { long frame; std::string cmd; };
long g_frame = 0;
std::vector<ScriptedInput> g_script;
std::vector<std::pair<long, int>> g_key_release;  /* (frame, key) */
long g_click_release = -1;
bool g_test_init = false;

void test_init()
{
	g_test_init = true;
	if (const char *s = getenv("A4_INPUT")) {
		std::string all(s);
		size_t pos = 0;
		while (pos < all.size()) {
			size_t end = all.find(';', pos);
			if (end == std::string::npos) end = all.size();
			std::string item = all.substr(pos, end - pos);
			size_t colon = item.find(':');
			if (colon != std::string::npos)
				g_script.push_back({ atol(item.substr(0, colon).c_str()), item.substr(colon + 1) });
			pos = end + 1;
		}
	}
}

void test_frame()
{
	if (!g_test_init) test_init();
	for (auto it = g_key_release.begin(); it != g_key_release.end();) {
		if (g_frame >= it->first) { key[it->second] = 0; it = g_key_release.erase(it); }
		else ++it;
	}
	if (g_click_release >= 0 && g_frame >= g_click_release) { mouse_b &= ~1; g_click_release = -1; }
	for (const auto &si : g_script) {
		if (si.frame != g_frame) continue;
		int a = 0, b = 0;
		if (sscanf(si.cmd.c_str(), "key=%d", &a) == 1) {
			key[a & 255] = 1;
			g_key_release.push_back({ g_frame + 3, a & 255 });
		} else if (sscanf(si.cmd.c_str(), "click=%d,%d", &a, &b) == 2) {
			mouse_x = a; mouse_y = b; mouse_b |= 1; g_click_release = g_frame + 3;
		} else if (sscanf(si.cmd.c_str(), "move=%d,%d", &a, &b) == 2) {
			mouse_x = a; mouse_y = b;
		} else if (si.cmd == "quit") {
			g_close = true;
		}
	}
	const char *dir = getenv("A4_SHOT_DIR");
	if (dir && screen) {
		bool want = false;
		if (const char *fr = getenv("A4_SHOT_FRAMES")) {
			std::string list = std::string(",") + fr + ",";
			want = list.find("," + std::to_string(g_frame) + ",") != std::string::npos;
		} else {
			want = g_frame % 120 == 0;
		}
		if (want) {
			SDL_Surface *s = SDL_CreateSurfaceFrom(a4::sw(screen), a4::sh(screen), SDL_PIXELFORMAT_XRGB8888, screen->pixels, screen->pitch * 4);
			if (s) {
				char name[512];
				snprintf(name, sizeof name, "%s/frame_%05ld.bmp", dir, g_frame);
				SDL_SaveBMP(s, name);
				SDL_DestroySurface(s);
			}
		}
	}
	g_frame++;
}

void present()
{
	test_frame();
	if (!g_renderer || !g_texture || !screen) return;
	SDL_UpdateTexture(g_texture, NULL, screen->pixels, screen->pitch * 4);
	SDL_SetRenderDrawColor(g_renderer, 0, 0, 0, 255);
	SDL_RenderClear(g_renderer);
	SDL_RenderTexture(g_renderer, g_texture, NULL, NULL);
	SDL_RenderPresent(g_renderer);
	a4::screen_dirty = false;
}

} /* namespace */

/* ---------------------------------------------------------------- system */

/* The game opens "data/..." relative to the working directory. If that
   folder isn't here, move to where it is: next to the executable, in a
   macOS bundle's Resources, or (dev builds) the source tree's bin/. */
void a4_init_paths(void)
{
	namespace fs = std::filesystem;
	std::error_code ec;
	if (fs::is_directory("data", ec)) { a4_use_user_dir_if_needed(); return; }
	std::vector<fs::path> candidates;
	if (const char *base = SDL_GetBasePath()) {
		fs::path b = fs::u8path(base);
		candidates.push_back(b);
		candidates.push_back(b / ".." / "Resources");
	}
#ifdef A4_DEV_DATA_DIR
	candidates.push_back(fs::u8path(A4_DEV_DATA_DIR));
#endif
	for (const auto &c : candidates) {
		if (fs::is_directory(c / "data", ec)) {
			fs::current_path(c, ec);
			if (!ec) { fprintf(stderr, "a4sdl: using data from %s\n", c.u8string().c_str()); break; }
		}
	}
	a4_use_user_dir_if_needed();
}

/* The game writes output.txt, data/config.lua (settings), the planet
   texture cache in data/planetorbit and saves/ next to its data. That is
   impossible inside a signed macOS .app (Gatekeeper may even run it from a
   read-only location) or a read-only install. In those cases build a
   per-user game folder (SDL_GetPrefPath: ~/Library/Application Support on
   macOS, ~/.local/share on Linux) where the read-only data is symlinked
   back to the install and the writable parts are real files, and run from
   there. A4_USER_DIR=1 forces this (for testing). */
void a4_use_user_dir_if_needed(void)
{
#ifndef _WIN32
	static bool done = false;   /* main() and allegro_init() both get here */
	if (done) return;
	done = true;
	namespace fs = std::filesystem;
	std::error_code ec;
	fs::path base = fs::current_path(ec);
	if (ec || !fs::is_directory(base / "data", ec)) return;

	bool in_bundle = base.u8string().find(".app/Contents/Resources") != std::string::npos;
	bool writable = false;
	{
		fs::path probe = base / ".a4_write_test";
		FILE *f = fopen(probe.u8string().c_str(), "wb");
		if (f) { fclose(f); fs::remove(probe, ec); writable = true; }
	}
	const char *force = getenv("A4_USER_DIR");
	if (!in_bundle && writable && !(force && *force == '1')) return;

	char *pref = SDL_GetPrefPath("Starflight", "The Lost Colony");
	if (!pref) { fprintf(stderr, "a4sdl: no user folder (%s); running in place\n", SDL_GetError()); return; }
	fs::path user = fs::u8path(pref);
	SDL_free(pref);
	if (fs::equivalent(user, base, ec)) return;   /* already running from it */

	/* point dst at src unless it already is (re-pointed if the app moved) */
	auto link = [&](const fs::path &src, const fs::path &dst) {
		std::error_code e;
		if (fs::is_symlink(dst, e)) {
			if (fs::read_symlink(dst, e) == src) return;
			fs::remove(dst, e);
		} else if (fs::exists(dst, e)) {
			return;   /* a real file the game wrote: keep it */
		}
		fs::create_symlink(src, dst, e);
		if (e) fprintf(stderr, "a4sdl: link %s: %s\n", dst.u8string().c_str(), e.message().c_str());
	};
	auto copy_missing = [&](const fs::path &src, const fs::path &dst) {
		std::error_code e;
		if (!fs::exists(dst, e)) fs::copy_file(src, dst, e);
	};

	fs::path udata = user / "data";
	fs::create_directories(udata, ec);
	for (fs::directory_iterator it(base / "data", ec), end; !ec && it != end; it.increment(ec)) {
		const fs::path &src = it->path();
		std::string name = src.filename().u8string();
		if (name == "config.lua") {
			copy_missing(src, udata / name);                 /* settings screen rewrites it */
		} else if (name == "planetorbit" && fs::is_directory(src)) {
			fs::path cache = udata / name;                   /* texture cache is written here */
			if (fs::is_symlink(cache)) fs::remove(cache);
			fs::create_directories(cache);
			std::error_code e2;
			for (fs::directory_iterator f(src, e2), fend; !e2 && f != fend; f.increment(e2))
				link(f->path(), cache / f->path().filename());
		} else {
			link(src, udata / name);
		}
	}
	fs::path saves = user / "saves";
	fs::create_directories(saves, ec);
	std::error_code e3;
	for (fs::directory_iterator f(base / "saves", e3), fend; !e3 && f != fend; f.increment(e3))
		copy_missing(f->path(), saves / f->path().filename());

	fs::current_path(user, ec);
	if (!ec) fprintf(stderr, "a4sdl: game folder %s (data from %s)\n", user.u8string().c_str(), base.u8string().c_str());
#endif
}

int allegro_init(void)
{
	memset((void *)key, 0, sizeof key);
	if (!sdl_up()) return -1;
	a4_init_paths();
	return 0;
}

void allegro_exit(void)
{
	if (g_texture)  { SDL_DestroyTexture(g_texture); g_texture = NULL; }
	if (g_renderer) { SDL_DestroyRenderer(g_renderer); g_renderer = NULL; }
	if (g_window)   { SDL_DestroyWindow(g_window); g_window = NULL; }
	if (screen) {
		BITMAP *s = screen;
		screen = NULL;
		destroy_bitmap(s);
	}
	if (g_sdl_up) { SDL_Quit(); g_sdl_up = false; }
}

void allegro_message(const char *msg, ...)
{
	char buf[2048];
	va_list ap;
	va_start(ap, msg);
	vsnprintf(buf, sizeof buf, msg, ap);
	va_end(ap);
	fprintf(stderr, "%s\n", buf);
	if (sdl_up()) SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_INFORMATION, g_title.c_str(), buf, g_window);
}

int alert(const char *s1, const char *s2, const char *s3, const char *b1, const char *b2, int, int)
{
	std::string text;
	for (const char *s : { s1, s2, s3 })
		if (s && *s) { if (!text.empty()) text += "\n"; text += s; }
	if (!sdl_up()) return 1;
	SDL_MessageBoxButtonData buttons[2];
	int n = 0;
	if (b1) buttons[n++] = { SDL_MESSAGEBOX_BUTTON_RETURNKEY_DEFAULT, 1, b1 };
	if (b2) buttons[n++] = { SDL_MESSAGEBOX_BUTTON_ESCAPEKEY_DEFAULT, 2, b2 };
	SDL_MessageBoxData data = { SDL_MESSAGEBOX_INFORMATION, g_window, g_title.c_str(), text.c_str(), n, buttons, NULL };
	int hit = 1;
	if (!SDL_ShowMessageBox(&data, &hit)) return 1;
	return hit > 0 ? hit : 1;
}

void rest(unsigned int ms)
{
	if (a4::screen_dirty) present();
	pump();
	if (ms) SDL_Delay(ms);
}

int install_timer(void) { return 0; }

/* -------------------------------------------------------------- graphics */

void a4_set_logical_size(int w, int h)
{
	g_logical_w = w;
	g_logical_h = h;
}

/* Storage scale: enough real pixels per game pixel to cover the display
   (1..4). A4_SCALE=n forces it; 1 reproduces the original rendering. */
static int choose_scale(int lh)
{
	if (const char *e = getenv("A4_SCALE")) {
		int n = atoi(e);
		if (n >= 1 && n <= 4) return n;
	}
	int S = 1;
	SDL_DisplayID d = g_window ? SDL_GetDisplayForWindow(g_window) : SDL_GetPrimaryDisplay();
	if (const SDL_DisplayMode *m = d ? SDL_GetDesktopDisplayMode(d) : NULL) {
		float density = m->pixel_density > 0 ? m->pixel_density : 1.0f;
		int ph = (int)(m->h * density + 0.5f);
		S = (ph + lh - 1) / lh;
	}
	if (S < 1) S = 1;
	if (S > 4) S = 4;
	return S;
}

int set_gfx_mode(int card, int w, int h, int, int)
{
	if (card == GFX_TEXT) return 0;   /* the game calls this before switching modes */
	if (!sdl_up() || w <= 0 || h <= 0) return -1;

	bool fullscreen = (card == GFX_AUTODETECT_FULLSCREEN || card == GFX_DIRECTX_ACCEL || card == GFX_DIRECTX);
	int lw = g_logical_w > 0 ? g_logical_w : w;
	int lh = g_logical_h > 0 ? g_logical_h : h;

	if (!g_window) {
		SDL_WindowFlags flags = SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY;
		g_window = SDL_CreateWindow(g_title.c_str(), w, h, flags);
		if (!g_window) { fprintf(stderr, "a4sdl: SDL_CreateWindow: %s\n", SDL_GetError()); return -1; }
		g_renderer = SDL_CreateRenderer(g_window, NULL);
		if (!g_renderer) g_renderer = SDL_CreateRenderer(g_window, SDL_SOFTWARE_RENDERER);
		if (!g_renderer) { fprintf(stderr, "a4sdl: SDL_CreateRenderer: %s\n", SDL_GetError()); return -1; }
		SDL_SetRenderVSync(g_renderer, 1);
	} else {
		SDL_SetWindowSize(g_window, w, h);
	}
	SDL_SetWindowFullscreen(g_window, fullscreen);
	SDL_SetRenderLogicalPresentation(g_renderer, lw, lh, SDL_LOGICAL_PRESENTATION_LETTERBOX);

	int S = choose_scale(lh);
	if (!screen || screen->w != lw || screen->h != lh || screen->scale != S) {
		if (g_texture) { SDL_DestroyTexture(g_texture); g_texture = NULL; }
		if (screen) { BITMAP *s = screen; screen = NULL; destroy_bitmap(s); }
		a4::g_scale = S;
		screen = a4::create_bitmap_scaled(lw, lh, S);
		if (!screen) return -1;
		screen->is_screen = 1;
		g_texture = SDL_CreateTexture(g_renderer, SDL_PIXELFORMAT_XRGB8888, SDL_TEXTUREACCESS_STREAMING, lw * S, lh * S);
		if (!g_texture) { fprintf(stderr, "a4sdl: SDL_CreateTexture: %s\n", SDL_GetError()); return -1; }
		SDL_SetTextureScaleMode(g_texture, SDL_SCALEMODE_LINEAR);
		fprintf(stderr, "a4sdl: drawing at %dx%d (%dx the game's %dx%d)\n", lw * S, lh * S, S, lw, lh);
	}
	clear_bitmap(screen);
	if (!g_os_cursor) SDL_HideCursor();
	present();
	return 0;
}

void a4_flip(void)
{
	present();
}

int a4_close_requested(void)
{
	pump();
	return g_close ? 1 : 0;
}

void vsync(void) {}

int get_desktop_resolution(int *width, int *height)
{
	if (!sdl_up()) return -1;
	const SDL_DisplayMode *m = SDL_GetDesktopDisplayMode(SDL_GetPrimaryDisplay());
	if (!m) return -1;
	if (width) *width = m->w;
	if (height) *height = m->h;
	return 0;
}

int desktop_color_depth(void) { return 32; }

int get_refresh_rate(void)
{
	if (!sdl_up()) return 0;
	const SDL_DisplayMode *m = SDL_GetDesktopDisplayMode(SDL_GetPrimaryDisplay());
	return m ? (int)(m->refresh_rate + 0.5f) : 0;
}

GFX_MODE_LIST *get_gfx_mode_list(int)
{
	if (!sdl_up()) return NULL;
	int count = 0;
	SDL_DisplayMode **modes = SDL_GetFullscreenDisplayModes(SDL_GetPrimaryDisplay(), &count);
	GFX_MODE_LIST *list = (GFX_MODE_LIST *)calloc(1, sizeof(GFX_MODE_LIST));
	if (!list) { SDL_free(modes); return NULL; }
	/* one extra zeroed entry: Allegro terminates the list and the game reads it */
	list->mode = (GFX_MODE *)calloc((size_t)count + 1, sizeof(GFX_MODE));
	int n = 0;
	for (int i = 0; i < count && list->mode; i++) {
		int w = modes[i]->w, h = modes[i]->h;
		bool dup = false;
		for (int j = 0; j < n; j++)
			if (list->mode[j].width == w && list->mode[j].height == h) { dup = true; break; }
		if (dup) continue;
		list->mode[n].width = w;
		list->mode[n].height = h;
		list->mode[n].bpp = 32;
		n++;
	}
	list->num_modes = n;
	SDL_free(modes);
	return list;
}

void destroy_gfx_mode_list(GFX_MODE_LIST *list)
{
	if (!list) return;
	free(list->mode);
	free(list);
}

void set_window_title(const char *name)
{
	g_title = name ? name : "";
	if (g_window) SDL_SetWindowTitle(g_window, g_title.c_str());
}

int show_os_cursor(int cursor)
{
	g_os_cursor = cursor != 0;
	if (g_sdl_up) { if (g_os_cursor) SDL_ShowCursor(); else SDL_HideCursor(); }
	return 0;
}

void show_mouse(BITMAP *) {}

/* ---------------------------------------------------------------- input */

int install_keyboard(void) { return 0; }
int install_mouse(void)    { return 3; }

int poll_keyboard(void)
{
	if (a4::screen_dirty) present();
	pump();
	return 0;
}

int poll_mouse(void)
{
	pump();
	return 0;
}

int keypressed(void)
{
	pump();
	return g_keyhead != g_keytail;
}

int readkey(void)
{
	while (g_keyhead == g_keytail && !g_close) { pump(); SDL_Delay(5); }
	if (g_keyhead == g_keytail) return 0;
	int k = g_keybuf[g_keyhead];
	g_keyhead = (g_keyhead + 1) % 64;
	return k;
}

void clear_keybuf(void) { g_keyhead = g_keytail = 0; }

void position_mouse(int x, int y)
{
	mouse_x = x;
	mouse_y = y;
	if (g_window && g_renderer) {
		float wx = 0, wy = 0;
		SDL_RenderCoordinatesToWindow(g_renderer, (float)x, (float)y, &wx, &wy);
		SDL_WarpMouseInWindow(g_window, wx, wy);
	}
}

/* unshifted US layout, as Allegro reports it */
int scancode_to_ascii(int k)
{
	if (k >= KEY_A && k <= KEY_Z) return 'a' + (k - KEY_A);
	if (k >= KEY_0 && k <= KEY_9) return '0' + (k - KEY_0);
	if (k >= KEY_0_PAD && k <= KEY_9_PAD) return '0' + (k - KEY_0_PAD);
	switch (k) {
	case KEY_SPACE:      return ' ';
	case KEY_MINUS:      return '-';
	case KEY_EQUALS:     return '=';
	case KEY_OPENBRACE:  return '[';
	case KEY_CLOSEBRACE: return ']';
	case KEY_COLON:      return ';';
	case KEY_QUOTE:      return '\'';
	case KEY_BACKSLASH:  return '\\';
	case KEY_COMMA:      return ',';
	case KEY_STOP:       return '.';
	case KEY_SLASH:      return '/';
	case KEY_TILDE:      return '`';
	case KEY_SLASH_PAD:  return '/';
	case KEY_ASTERISK:   return '*';
	case KEY_MINUS_PAD:  return '-';
	case KEY_PLUS_PAD:   return '+';
	case KEY_DEL_PAD:    return '.';
	case KEY_ENTER:
	case KEY_ENTER_PAD:  return '\r';
	case KEY_BACKSPACE:  return 8;
	case KEY_TAB:        return '\t';
	case KEY_ESC:        return 27;
	default:             return 0;
	}
}
