// Host unit tests for src/core/i18n.cpp
//   python -m ziglang c++ -std=c++17 -I tools/i18n/test -I src/core tools/i18n/test/test_i18n.cpp -o i18n_test.exe
#include "../../../src/core/i18n.cpp"
#include <cstdio>
#include <string>

static int g_fail = 0, g_total = 0;

// firmware single-byte encoding -> UTF-8 (for readable test expectations)
static std::string toUtf8(const std::string &s) {
    std::string o;
    for (unsigned char c : s) {
        if (c >= 0x80 && c <= 0xBF) {
            unsigned cp = (c < 0xA0) ? 0x410 + (c - 0x80) : 0x430 + (c - 0xA0);
            o += (char)(0xC0 | (cp >> 6));
            o += (char)(0x80 | (cp & 0x3F));
        } else o += (char)c;
    }
    return o;
}

static void expect(const char *what, const std::string &got, const std::string &want) {
    g_total++;
    std::string g = toUtf8(got);
    if (g != want) {
        g_fail++;
        printf("FAIL %-34s got [%s] want [%s]\n", what, g.c_str(), want.c_str());
    } else {
        printf("ok   %-34s [%s]\n", what, g.c_str());
    }
}

int main() {
    i18n::setLanguage(i18n::LANG_RU);
    expect("exact", i18n::tr("Back").d, "Назад");
    expect("whitespace kept", i18n::tr("  Back\n").d, "  Назад\n");
    expect("all caps -> upper ru", i18n::tr("BACK").d, "НАЗАД");
    expect("case-insensitive", i18n::tr("back").d, "Назад");
    expect("prefix", i18n::tr("Connecting to MyWiFi").d, "Подключение к MyWiFi");
    expect("prefix + println", i18n::tr("Connecting to Home\n").d, "Подключение к Home\n");
    expect("suffix", i18n::tr("5 networks").d, "5 сетей");
    expect("label: value", i18n::tr("Status: Connected").d, "Статус: Подключено");
    expect("label: data", i18n::tr("Status: xyz-42").d, "Статус: xyz-42");
    expect("unknown", i18n::tr("Totally unknown text").d, "Totally unknown text");
    expect("no letters", i18n::tr("12:34").d, "12:34");
    expect("empty", i18n::tr("").d, "");
    std::string ru = i18n::tr("Back").d;
    expect("already russian", i18n::tr(ru.c_str()).d, "Назад");
    expect("format", std::string(i18n::trf("Signal: %d dBm")), "Сигнал: %d дБм");
    expect("format unknown", std::string(i18n::trf("x=%d")), "x=%d");
    expect("format + newline", std::string(i18n::trf("Signal: %d dBm\n")), "Сигнал: %d дБм\n");
    String up = i18n::tr("Main Menu");
    i18n::toUpper(up);
    expect("toUpper", up.d, "ГЛАВНОЕ МЕНЮ");
    // UTF-8 Cyrillic from the outside world becomes one byte per letter
    expect("utf8 cyrillic kept", i18n::tr("Привет").d, "Привет");
    g_total++;
    if (i18n::tr("Привет, мир").length() != 11) {
        g_fail++;
        printf("FAIL utf8 cyrillic is one byte per letter (len %u)\n", (unsigned)i18n::tr("Привет, мир").length());
    } else printf("ok   utf8 cyrillic is one byte per letter\n");
    expect("utf8 yo -> ye", i18n::tr("Ёлка ёж").d, "Елка еж");
    expect("utf8 ssid + prefix", i18n::tr("Connecting to Дом_5G").d, "Подключение к Дом_5G");
    {
        String e("caf\xC3\xA9 \xF0\x9F\x98\xBA x"); // é and an emoji: not Cyrillic, kept as is
        String t = i18n::tr(e);
        i18n::toUpper(t);
        g_total++; // raw bytes: expect() would re-encode 0x80..0xBF
        if (t.d != std::string("CAF\xC3\xA9 \xF0\x9F\x98\xBA X")) {
            g_fail++;
            printf("FAIL other utf8 untouched by toUpper\n");
        } else printf("ok   other utf8 untouched by toUpper\n");
    }
    expect("mixed ru/en kept", i18n::tr(i18n::tr("Back").d + " Home").d, "Назад Home");
    expect("utf8 key (arrow)", i18n::tr("Go \xE2\x86\x92 There").d, "Туда");
    expect("no partial word prefix", i18n::tr("Backup").d, "Backup");
    // utf-8 conversion + recent screen buffer
    g_total++;
    if (i18n::toUtf8(i18n::tr("Back")).d != std::string("Назад")) {
        g_fail++;
        printf("FAIL toUtf8\n");
    } else printf("ok   toUtf8\n");
    i18n::noteDrawn(i18n::tr("Main Menu"));
    i18n::noteDrawn(i18n::tr("Main Menu")); // duplicate is skipped
    i18n::noteDrawn(String("  \n"));      // blank is skipped
    i18n::noteDrawn(i18n::tr("Back"));
    g_total++;
    if (i18n::recentScreen().d != std::string("  | Главное меню\n  | Назад\n")) {
        g_fail++;
        printf("FAIL recentScreen: [%s]\n", i18n::recentScreen().d.c_str());
    } else printf("ok   recentScreen\n");
    // maybe(): no copy when nothing to translate, translation otherwise
    {
        String tmp, num("12345"), word("Back");
        g_total++;
        if (&i18n::maybe(num, tmp) != &num) {
            g_fail++;
            printf("FAIL maybe returns src for numbers\n");
        } else printf("ok   maybe returns src for numbers\n");
        expect("maybe translates", i18n::maybe(word, tmp).d, "Назад");
    }
    i18n::setLanguage(i18n::LANG_EN);
    expect("english mode", i18n::tr("Back").d, "Back");
    expect("english fmt", std::string(i18n::trf("Signal: %d dBm")), "Signal: %d dBm");
    {
        String tmp, ssid("Сеть Home");
        const String &r = i18n::maybe(ssid, tmp);
        expect("english mode utf8 normalised", r.d, "Сеть Home");
        g_total++;
        if (r.length() != 9) {
            g_fail++;
            printf("FAIL english mode utf8 length %u\n", (unsigned)r.length());
        } else printf("ok   english mode utf8 length\n");
    }
    printf("\n%d/%d passed\n", g_total - g_fail, g_total);
    return g_fail ? 1 : 0;
}
