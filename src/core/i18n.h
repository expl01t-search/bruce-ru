#ifndef __BRUCE_I18N_H__
#define __BRUCE_I18N_H__

#include <Arduino.h>

// Runtime UI translation (Russian).
//
// Russian text is stored in a single-byte encoding so that String::length(),
// substring() and every "chars * LW * size" layout computation in Bruce keep
// working unchanged:  А..Я -> 0x80..0x9F, а..я -> 0xA0..0xBF (Ё/ё folded to Е/е).
// The matching glyphs are patched into the TFT_eSPI GLCD font (lib/TFT_eSPI/Fonts/glcdfont.c).
//
// The dictionary lives in tools/i18n/ru.tsv (UTF-8, human editable) and is compiled
// by tools/i18n/gen_i18n.py into src/core/i18n_ru_data.h.
namespace i18n {

enum Lang : uint8_t { LANG_EN = 0, LANG_RU = 1 };

void setLanguage(uint8_t lang);
uint8_t getLanguage();
inline bool active() { return getLanguage() == LANG_RU; }

// Translate a UI string. Unknown strings are returned unchanged.
// Handles surrounding whitespace/newlines, ALL-CAPS variants, known prefixes
// ("Connecting to " + x) and suffixes (x + " networks").
String tr(const String &s);
String tr(const char *s);

// Allocation-free fast path for hot draw calls: returns `src` itself when there is
// nothing to translate (English mode, no Latin letters), otherwise fills `tmp`.
const String &maybe(const String &src, String &tmp);

// printf-style format strings: exact lookup only, returns a pointer into the
// dictionary (or `fmt` itself). Translations keep the same conversion specifiers.
const char *trf(const char *fmt);

// Upper-case conversion that also handles the single-byte Cyrillic range.
void toUpper(String &s);

// true if the string contains bytes of the single-byte Cyrillic range
bool hasCyrillic(const char *s);

// Firmware single-byte text -> UTF-8 (for serial output / logs).
String toUtf8(const String &s);

// Number of dictionary entries compiled in (exact, prefix, suffix).
int entryCount();

// Debug aid for the "i18n screen" serial command: tft_logger reports every string it
// draws (already translated); recentScreen() returns the last ones as UTF-8 lines.
void noteDrawn(const String &s);
String recentScreen();

} // namespace i18n

#endif
