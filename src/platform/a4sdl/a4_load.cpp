/*
 * a4sdl loading: load_bitmap (BMP/TGA/PNG via stb_image), Allegro 4
 * datafiles, and file helpers with Windows-style path tolerance.
 *
 * The datafile reader follows Allegro 4.4's src/datafile.c, src/file.c and
 * src/lzss.c (giftware license). Only what the game's datafiles contain is
 * supported: nested FILE objects, 32-bit BMP objects (with or without
 * alpha), properties, and anything else kept as raw DATA.
 */
#include "a4_internal.h"

#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <system_error>
#include <vector>

#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_BMP
#define STBI_ONLY_TGA
#define STBI_ONLY_PNG
#define STBI_FAILURE_USERMSG
#include "stb/stb_image.h"

namespace fs = std::filesystem;

/* ----------------------------------------------------------------- paths */

std::string a4::resolve_path(const char *path)
{
	if (!path) return std::string();
	std::string p(path);
	for (auto &ch : p) if (ch == '\\') ch = '/';

	std::error_code ec;
	if (fs::exists(fs::u8path(p), ec)) return p;

	/* walk the path one component at a time, matching case-insensitively */
	fs::path in = fs::u8path(p);
	fs::path cur = in.is_absolute() ? in.root_path() : fs::path(".");
	bool first = true;
	for (const auto &part : in.relative_path()) {
		std::string want = part.u8string();
		if (want == "." ) continue;
		if (want == "..") { cur /= part; first = false; continue; }
		fs::path exact = cur / part;
		if (fs::exists(exact, ec)) { cur = exact; first = false; continue; }
		bool found = false;
		for (fs::directory_iterator it(cur, ec), end; !ec && it != end; it.increment(ec)) {
			std::string have = it->path().filename().u8string();
			if (have.size() == want.size() &&
			    std::equal(have.begin(), have.end(), want.begin(),
			               [](char a, char b) { return tolower((unsigned char)a) == tolower((unsigned char)b); })) {
				cur = it->path();
				found = true;
				break;
			}
		}
		if (!found) return p;
		first = false;
	}
	(void)first;
	std::string out = cur.u8string();
	if (!in.is_absolute() && out.rfind("./", 0) == 0) out = out.substr(2);
	return out;
}

/* ----------------------------------------------------------------- files */

int exists(const char *filename)
{
	std::error_code ec;
	return fs::is_regular_file(fs::u8path(a4::resolve_path(filename)), ec) ? 1 : 0;
}

int file_exists(const char *filename, int attrib, int *aret)
{
	std::error_code ec;
	fs::path p = fs::u8path(a4::resolve_path(filename));
	if (!fs::exists(p, ec)) return 0;
	bool dir = fs::is_directory(p, ec);
	if (dir && !(attrib & FA_DIREC)) return 0;
	if (aret) *aret = dir ? FA_DIREC : FA_ARCH;
	return 1;
}

int delete_file(const char *filename)
{
	std::error_code ec;
	return fs::remove(fs::u8path(a4::resolve_path(filename)), ec) ? 0 : -1;
}

static bool read_file(const std::string &path, std::vector<unsigned char> &out)
{
	FILE *f = fopen(path.c_str(), "rb");
	if (!f) return false;
	fseek(f, 0, SEEK_END);
	long n = ftell(f);
	fseek(f, 0, SEEK_SET);
	if (n < 0) { fclose(f); return false; }
	out.resize((size_t)n);
	size_t got = n ? fread(out.data(), 1, (size_t)n, f) : 0;
	fclose(f);
	return got == (size_t)n;
}

/* ---------------------------------------------------------------- images */

static unsigned char *decode(const std::string &path, int &w, int &h, int &comp)
{
	std::vector<unsigned char> data;
	if (!read_file(path, data)) return NULL;
	return stbi_load_from_memory(data.data(), (int)data.size(), &w, &h, &comp, 4);
}

/* High resolution art tiers: next to "ship.tga" may sit "ship@2x.png",
   "ship@4x.png"..., the same picture at 2x, 4x... the size. When the
   display scale is above 1 the best tier is resampled to exactly that
   scale. Tier transparency becomes the mask colour for images that use
   one (no alpha channel in the original). */
static std::string tier_path(const std::string &path, int n)
{
	size_t slash = path.find_last_of('/');
	size_t dot = path.find_last_of('.');
	std::string stem = (dot == std::string::npos || (slash != std::string::npos && dot < slash)) ? path : path.substr(0, dot);
	return stem + "@" + std::to_string(n) + "x.png";
}

static BITMAP *load_tier(const std::string &path, int w, int h, bool base_alpha)
{
	const int S = a4::g_scale;
	if (S <= 1) return NULL;
	/* prefer the smallest tier at or above S, else the largest below it */
	int order[8], n = 0;
	for (int k = S; k <= 8; k++) order[n++] = k;
	for (int k = S - 1; k >= 2 && n < 8; k--) order[n++] = k;
	for (int i = 0; i < n; i++) {
		int N = order[i];
		std::string tp = a4::resolve_path(tier_path(path, N).c_str());
		std::error_code ec;
		if (!fs::exists(fs::u8path(tp), ec)) continue;
		int tw = 0, th = 0, comp = 0;
		unsigned char *px = decode(tp, tw, th, comp);
		if (!px) continue;
		if (tw != w * N || th != h * N) {
			fprintf(stderr, "a4sdl: %s is %dx%d, expected %dx%d; ignored\n", tp.c_str(), tw, th, w * N, h * N);
			stbi_image_free(px);
			continue;
		}
		BITMAP *b = a4::create_bitmap_scaled(w, h, S);
		if (!b) { stbi_image_free(px); return NULL; }
		/* area resample N -> S per game pixel, alpha weighted */
		const int SW = w * S, SH = h * S;
		for (int Y = 0; Y < SH; Y++) {
			uint32_t *d = a4::row(b, Y);
			double y0 = (double)Y * N / S, y1 = (double)(Y + 1) * N / S;
			for (int X = 0; X < SW; X++) {
				double x0 = (double)X * N / S, x1 = (double)(X + 1) * N / S;
				double r = 0, g = 0, bl = 0, a = 0, area = 0;
				for (int sy = (int)y0; sy < (int)ceil(y1); sy++) {
					double wy = std::min(y1, sy + 1.0) - std::max(y0, (double)sy);
					if (wy <= 0) continue;
					const unsigned char *q = px + ((size_t)sy * tw) * 4;
					for (int sx = (int)x0; sx < (int)ceil(x1); sx++) {
						double wx = std::min(x1, sx + 1.0) - std::max(x0, (double)sx);
						if (wx <= 0) continue;
						const unsigned char *c = q + (size_t)sx * 4;
						double wgt = wx * wy, al = c[3] / 255.0;
						r += c[0] * al * wgt; g += c[1] * al * wgt; bl += c[2] * al * wgt;
						a += al * wgt; area += wgt;
					}
				}
				double alpha = area > 0 ? a / area : 0;
				uint32_t R = a > 0 ? (uint32_t)(r / a + 0.5) : 0;
				uint32_t G = a > 0 ? (uint32_t)(g / a + 0.5) : 0;
				uint32_t B = a > 0 ? (uint32_t)(bl / a + 0.5) : 0;
				uint32_t col = (R << 16) | (G << 8) | B;
				if (base_alpha) {
					d[X] = ((uint32_t)(alpha * 255 + 0.5) << 24) | col;
				} else if (alpha < 0.5) {
					d[X] = MASK_COLOR_32;
				} else {
					if (a4::is_mask(col)) col ^= 0x00010000u;
					d[X] = col;
				}
			}
		}
		stbi_image_free(px);
		return b;
	}
	return NULL;
}

BITMAP *load_bitmap(const char *filename, RGB *pal)
{
	(void)pal;
	std::string path = a4::resolve_path(filename);
	int w = 0, h = 0, comp = 0;
	unsigned char *px = decode(path, w, h, comp);
	if (!px) return NULL;

	/* Allegro keeps alpha only for images that have it */
	bool has_alpha = (comp == 2 || comp == 4);
	if (BITMAP *hd = load_tier(path, w, h, has_alpha)) { stbi_image_free(px); return hd; }

	BITMAP *b = a4::create_bitmap_scaled(w, h, 1);
	if (!b) { stbi_image_free(px); return NULL; }
	const unsigned char *s = px;
	for (int y = 0; y < h; y++) {
		uint32_t *d = a4::row(b, y);
		for (int x = 0; x < w; x++, s += 4) {
			uint32_t a = has_alpha ? s[3] : 0;
			d[x] = (a << 24) | ((uint32_t)s[0] << 16) | ((uint32_t)s[1] << 8) | s[2];
		}
	}
	stbi_image_free(px);
	return b;
}

/* ------------------------------------------------------------- datafiles */

namespace {

const uint32_t F_PACK_MAGIC   = 0x736C6821;  /* "slh!" whole file LZSS packed */
const uint32_t F_NOPACK_MAGIC = 0x736C682E;  /* "slh." stored */
const uint32_t DAT_MAGIC      = DAT_ID('A','L','L','.');
const uint32_t DAT_PROPERTY   = DAT_ID('p','r','o','p');

/* Allegro's LZSS (4k window, 18 byte max match), reading src[pos, end)
   and producing at most out_len bytes (or everything, when out_len < 0) */
std::vector<unsigned char> lzss_unpack(const unsigned char *src, size_t pos, size_t end, long out_len)
{
	const int N = 4096, F = 18, THRESHOLD = 2;
	std::vector<unsigned char> out;
	if (out_len > 0) out.reserve((size_t)out_len);
	unsigned char buf[4096];
	memset(buf, 0, sizeof buf);
	int r = N - F;
	unsigned flags = 0;
	auto full = [&]() { return out_len >= 0 && (long)out.size() >= out_len; };
	while (pos < end && !full()) {
		if (((flags >>= 1) & 256) == 0) {
			flags = src[pos++] | 0xFF00;
			if (pos >= end) break;
		}
		if (flags & 1) {
			unsigned char c = src[pos++];
			buf[r++] = c; r &= N - 1;
			out.push_back(c);
		} else {
			if (pos + 1 >= end) break;
			int i = src[pos], j = src[pos + 1];
			pos += 2;
			i |= (j & 0xF0) << 4;
			j = (j & 0x0F) + THRESHOLD;
			for (int k = 0; k <= j && !full(); k++) {
				unsigned char c = buf[(i + k) & (N - 1)];
				buf[r++] = c; r &= N - 1;
				out.push_back(c);
			}
		}
	}
	return out;
}

struct Reader
{
	const unsigned char *p;
	size_t pos, end;
	bool ok = true;

	bool need(size_t n) { if (pos + n > end) { ok = false; return false; } return true; }
	int32_t mgetl()
	{
		if (!need(4)) return 0;
		uint32_t v = ((uint32_t)p[pos] << 24) | ((uint32_t)p[pos + 1] << 16) | ((uint32_t)p[pos + 2] << 8) | p[pos + 3];
		pos += 4;
		return (int32_t)v;
	}
	int mgetw()
	{
		if (!need(2)) return 0;
		int v = (p[pos] << 8) | p[pos + 1];
		pos += 2;
		return (int16_t)v;
	}
	int getc_()
	{
		if (!need(1)) return 0;
		return p[pos++];
	}
};

void free_objects(DATAFILE *dat);

BITMAP *read_bitmap_object(Reader &rd)
{
	int bits = rd.mgetw();
	bool rgba = bits < 0;
	if (rgba) bits = -bits;
	int w = (uint16_t)rd.mgetw();
	int h = (uint16_t)rd.mgetw();
	if (!rd.ok) return NULL;
	BITMAP *b = a4::create_bitmap_scaled(w, h, 1);
	if (!b) return NULL;
	switch (bits) {
	case 32:
	case 24:
		for (int y = 0; y < h; y++) {
			uint32_t *d = a4::row(b, y);
			for (int x = 0; x < w; x++) {
				/* Allegro stores r,g,b and an alpha byte only for RGBA
				   objects (negative bit count), for both 24 and 32 bits */
				int r = rd.getc_(), g = rd.getc_(), bl = rd.getc_();
				int a = rgba ? rd.getc_() : 0;
				d[x] = ((uint32_t)a << 24) | ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)bl;
			}
		}
		break;
	case 16:
	case 15:
		for (int y = 0; y < h; y++) {
			uint32_t *d = a4::row(b, y);
			for (int x = 0; x < w; x++) {
				int c = rd.getc_() | (rd.getc_() << 8);  /* stored little-endian (pack_igetw) */
				int r = ((c >> 11) & 0x1F) * 255 / 31;
				int g = ((c >> 5) & 0x3F) * 255 / 63;
				int bl = (c & 0x1F) * 255 / 31;
				d[x] = ((uint32_t)r << 16) | ((uint32_t)g << 8) | (uint32_t)bl;
			}
		}
		break;
	default:
		/* 8-bit paletted and 4-bit ST images are not used by the game */
		destroy_bitmap(b);
		return NULL;
	}
	if (!rd.ok) { destroy_bitmap(b); return NULL; }
	return b;
}

DATAFILE *read_file_object(const unsigned char *p, size_t pos, size_t end, bool &ok);

/* one object's chunk: [file size][data size, negative if LZSS packed][data] */
bool read_object(Reader &rd, int32_t type, DATAFILE &obj)
{
	int32_t fsize = rd.mgetl();
	int32_t dsize = rd.mgetl();
	if (!rd.ok || fsize < 0 || !rd.need((size_t)fsize)) return false;

	std::vector<unsigned char> unpacked;
	const unsigned char *body = rd.p + rd.pos;
	size_t body_len = (size_t)fsize;
	if (dsize < 0) {
		unpacked = lzss_unpack(rd.p, rd.pos, rd.pos + (size_t)fsize, -dsize);
		body = unpacked.data();
		body_len = unpacked.size();
	} else if ((size_t)dsize < body_len) {
		body_len = (size_t)dsize;
	}
	rd.pos += (size_t)fsize;

	obj.type = type;
	obj.size = (long)body_len;
	obj.prop = NULL;
	if (type == DAT_BITMAP) {
		Reader sub{ body, 0, body_len };
		obj.dat = read_bitmap_object(sub);
		return obj.dat != NULL;
	}
	if (type == DAT_FILE) {
		bool ok = true;
		obj.dat = read_file_object(body, 0, body_len, ok);
		return ok && obj.dat;
	}
	/* anything else: keep the raw bytes */
	void *copy = malloc(body_len ? body_len : 1);
	if (!copy) return false;
	if (body_len) memcpy(copy, body, body_len);
	obj.dat = copy;
	return true;
}

DATAFILE *read_file_object(const unsigned char *p, size_t pos, size_t end, bool &ok)
{
	Reader rd{ p, pos, end };
	int32_t count = rd.mgetl();
	if (!rd.ok || count < 0 || count > 100000) { ok = false; return NULL; }
	DATAFILE *dat = (DATAFILE *)calloc((size_t)count + 1, sizeof(DATAFILE));
	if (!dat) { ok = false; return NULL; }
	int c = 0;
	while (c < count && rd.ok) {
		int32_t type = rd.mgetl();
		if (!rd.ok) break;
		if ((uint32_t)type == DAT_PROPERTY) {
			rd.mgetl();                      /* property type */
			int32_t size = rd.mgetl();       /* property value; not needed */
			if (size < 0 || !rd.need((size_t)size)) { rd.ok = false; break; }
			rd.pos += (size_t)size;
			continue;
		}
		if (!read_object(rd, type, dat[c])) { rd.ok = false; break; }
		c++;
	}
	dat[c].type = DAT_END;
	dat[c].dat = NULL;
	if (!rd.ok) { ok = false; free_objects(dat); return NULL; }
	return dat;
}

void free_objects(DATAFILE *dat)
{
	if (!dat) return;
	for (DATAFILE *d = dat; d->type != DAT_END; d++) {
		if (d->type == DAT_BITMAP) destroy_bitmap((BITMAP *)d->dat);
		else if (d->type == DAT_FILE) free_objects((DATAFILE *)d->dat);
		else free(d->dat);
	}
	free(dat);
}

} /* namespace */

/* The remaster keeps every image as a plain file. A module that asks for
   "data/x/x.dat" gets the objects listed, in order, in "data/x/x.assets":
   one path per line relative to that folder, '#' starts a comment, and a
   line starting with '?' stands for a non-image object (an empty slot that
   keeps the game's object numbers lined up). Original .dat files are still
   read when no .assets list exists. */
static DATAFILE *load_asset_list(const std::string &list_path)
{
	std::vector<unsigned char> text;
	if (!read_file(list_path, text)) return NULL;
	std::string dir = list_path.substr(0, list_path.find_last_of("/\\") + 1);
	std::vector<std::string> entries;
	std::string line;
	for (size_t i = 0; i <= text.size(); i++) {
		char c = i < text.size() ? (char)text[i] : '\n';
		if (c == '\r') continue;
		if (c != '\n') { line += c; continue; }
		size_t b = line.find_first_not_of(" \t"), e = line.find_last_not_of(" \t");
		std::string t = b == std::string::npos ? "" : line.substr(b, e - b + 1);
		if (!t.empty() && t[0] != '#') entries.push_back(t);
		line.clear();
	}
	DATAFILE *dat = (DATAFILE *)calloc(entries.size() + 1, sizeof(DATAFILE));
	if (!dat) return NULL;
	for (size_t i = 0; i < entries.size(); i++) {
		if (entries[i][0] == '?') {
			dat[i].type = DAT_ID('i', 'n', 'f', 'o');
			dat[i].dat = NULL;
			continue;
		}
		BITMAP *b = load_bitmap((dir + entries[i]).c_str(), NULL);
		if (!b) {
			fprintf(stderr, "a4sdl: %s: cannot load %s\n", list_path.c_str(), entries[i].c_str());
			dat[i].type = DAT_END;
			free_objects(dat);
			return NULL;
		}
		dat[i].type = DAT_BITMAP;
		dat[i].dat = b;
		dat[i].size = (long)b->w * b->h * 4;
	}
	dat[entries.size()].type = DAT_END;
	return dat;
}

DATAFILE *load_datafile(const char *filename)
{
	std::string fn = filename;
	if (fn.size() > 4 && (fn.compare(fn.size() - 4, 4, ".dat") == 0 || fn.compare(fn.size() - 4, 4, ".DAT") == 0)) {
		std::string list = a4::resolve_path((fn.substr(0, fn.size() - 4) + ".assets").c_str());
		std::error_code ec;
		if (std::filesystem::exists(std::filesystem::u8path(list), ec))
			return load_asset_list(list);
	}

	std::vector<unsigned char> file;
	if (!read_file(a4::resolve_path(filename), file) || file.size() < 8) return NULL;

	uint32_t magic = ((uint32_t)file[0] << 24) | ((uint32_t)file[1] << 16) | ((uint32_t)file[2] << 8) | file[3];
	std::vector<unsigned char> body;
	if (magic == F_PACK_MAGIC)        body = lzss_unpack(file.data(), 4, file.size(), -1);
	else if (magic == F_NOPACK_MAGIC) body.assign(file.begin() + 4, file.end());
	else return NULL;

	Reader rd{ body.data(), 0, body.size() };
	if ((uint32_t)rd.mgetl() != DAT_MAGIC) return NULL;
	bool ok = true;
	DATAFILE *dat = read_file_object(body.data(), 4, body.size(), ok);
	return ok ? dat : NULL;
}

void unload_datafile(DATAFILE *dat)
{
	free_objects(dat);
}
