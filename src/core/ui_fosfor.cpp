// "ФОСФОР" UI style. Spec: tools/ui/fosfor_preview.py (same coordinates and colours).
#include "ui_fosfor.h"
#include "core/i18n.h"
#include "core/mykeyboard.h"
#include "core/utils.h"
#include "core/wifi/wg.h"
#include "settings.h"
#include <MenuItemInterface.h>
#include <WiFi.h>
#include <globals.h>
#include <interface.h>

// defined in display.cpp
std::vector<String> wrapText(const String &text, int maxCharsPerLine);

namespace fos {

// ---------------------------------------------------------------- palette
static uint16_t blend(uint16_t a, uint16_t b, uint8_t wa) {
    // weighted mix of two RGB565 colours, wa = weight of `a` (0..255)
    uint16_t wb = 255 - wa;
    uint16_t r = (((a >> 11) & 31) * wa + ((b >> 11) & 31) * wb) / 255;
    uint16_t g = (((a >> 5) & 63) * wa + ((b >> 5) & 63) * wb) / 255;
    uint16_t bl = ((a & 31) * wa + (b & 31) * wb) / 255;
    return (r << 11) | (g << 5) | bl;
}

bool active() { return bruceConfig.uiStyle == UI_FOSFOR; }

static inline uint16_t PRI() { return bruceConfig.priColor; }
static inline uint16_t SEC() { return bruceConfig.secColor; }
static inline uint16_t BG() { return bruceConfig.bgColor; }
uint16_t cText() { return blend(PRI(), 0xFFFF, 115); }
uint16_t cDim() { return blend(PRI(), BG(), 140); }
uint16_t cGrid() { return blend(PRI(), BG(), 56); }
uint16_t cPanel() { return blend(PRI(), BG(), 18); }

// ---------------------------------------------------------------- primitives
static const int ROW_Y = 31, ROW_H = 18, ROWS = 5;

static void dashed(int x, int y, int w, uint16_t col) {
    for (int xx = x; xx < x + w; xx += 4) tft.drawFastHLine(xx, y, (x + w - xx) < 2 ? 1 : 2, col);
}

static void dbox(int x, int y, int w, int h, uint16_t outer, uint16_t inner, bool fill, uint16_t fillCol) {
    if (fill) tft.fillRect(x, y, w, h, fillCol);
    tft.drawRect(x, y, w, h, outer);
    tft.drawRect(x + 2, y + 2, w - 4, h - 4, inner);
}

// draw already-translated text, top-left datum, transparent or opaque background
static void text(const String &s, int x, int y, uint8_t size, uint16_t col) {
    tft.setTextDatum(0); // top-left: callers before us may leave TC/MC datum set
    tft.setTextSize(size);
    tft.setTextColor(col);
    tft.drawString(s, x, y, 1);
}

static void textRight(const String &s, int rx, int y, uint8_t size, uint16_t col) {
    text(s, rx - (int)s.length() * LW * size, y, size, col);
}

static void textCentre(const String &s, int cx, int y, uint8_t size, uint16_t col) {
    text(s, cx - (int)s.length() * LW * size / 2, y, size, col);
}

static String T(const String &s) { return i18n::tr(s); }

static String upper(const String &s) {
    String u = s;
    i18n::toUpper(u);
    return u;
}

// cut on a word boundary: "Проводные инстр." -> "Проводные"
static String shortName(const String &s, unsigned n) {
    if (s.length() <= n) return s;
    String cut = s.substring(0, n);
    int sp = cut.lastIndexOf(' ');
    if (sp > 2) return cut.substring(0, sp);
    return cut.substring(0, n - 1) + ".";
}

// main-menu cursor state (blinks in tick())
static bool s_cursorValid = false, s_cursorOn = true;
static int s_cursorX = 0, s_cursorY = 0;
static unsigned long s_cursorTs = 0;

// ---------------------------------------------------------------- chrome
void statusBar() {
    tft.fillRect(0, 0, tftWidth, 13, BG());
    String t;
    if (clock_set) {
#if defined(HAS_RTC)
        updateTimeStr(_rtc.getTimeStruct());
#else
        updateTimeStr(rtc.getTimeStruct());
#endif
        t = String(timeStr);
        t.trim();
        if (t.length() > 5) t = t.substring(0, 5); // HH:MM
    } else {
        t = "BRUCE";
    }
    text(t, 4, 3, FP, PRI());

    String tags = "";
    if (sdcardMounted) tags += "[SD] ";
    if (gpsConnected) tags += "[GPS] ";
#ifdef CONFIG_IDF_TARGET_ESP32P4
    if (WiFi.isConnected() || WiFi.AP.started()) tags += "[WIFI] ";
#else
    if (WiFi.getMode() != 0) tags += "[WIFI] ";
#endif
    if (isWebUIActive) tags += "[WEB] ";
    if (BLEConnected) tags += "[BLE] ";
    if (isConnectedWireguard) tags += "[WG] ";
    tags.trim();
    if (tags.length()) textCentre(tags, tftWidth / 2, 3, FP, cDim());

    uint8_t bat = getBattery();
    if (bat > 0) {
        int bx = tftWidth - 19, by = 3;
        String pct = isCharging() ? T("CHG") : String(bat) + "%";
        textRight(pct, tftWidth - 22, 3, FP, PRI());
        tft.drawRect(bx, by, 14, 7, PRI());
        tft.fillRect(bx + 14, by + 2, 1, 3, PRI());
        int fillW = bat * 10 / 100;
        if (fillW < 1) fillW = 1;
        tft.fillRect(bx + 2, by + 2, fillW, 3, bat > 15 ? PRI() : RED);
    }
    dashed(0, 13, tftWidth, cDim());
}

void mainBorder(bool clear) {
    if (clear) {
        tft.drawPixel(0, 0, 0);
        tft.fillScreen(BG());
        s_cursorValid = false;
    }
    statusBar();
    tft.setTextDatum(0);
    tft.setCursor(BORDER_PAD_X, BORDER_PAD_X);
    tft.setTextSize(FP);
    tft.setTextColor(PRI(), BG());
}

static void hintLine(const String &arrows, const String &rest) {
    tft.fillRect(0, 124, tftWidth, tftHeight - 124, BG());
    dashed(0, 123, tftWidth, cGrid());
    String r = T(rest);
    int total = (arrows.length() + r.length()) * LW;
    int x = (tftWidth - total) / 2;
    text(arrows, x, 126, FP, cDim());
    text(r, x + arrows.length() * LW, 126, FP, cDim());
}

void footerHint() { hintLine("\x1e\x1f ", "SELECT  M5 OK  PWR+B BACK"); }

void header(const String &title, const String &counter) {
    tft.fillRect(0, 14, tftWidth, 14, BG());
    String t = upper(T(title.length() ? title : String("Menu")));
    String full = "[ " + t + " ]";
    int maxChars = (tftWidth - 8) / LW - (int)counter.length() - 1;
    if ((int)full.length() > maxChars) full = full.substring(0, maxChars);
    text(full, 4, 17, FP, PRI());
    if (counter.length()) textRight(counter, tftWidth - 4, 17, FP, SEC());
    tft.drawFastHLine(4, 27, tftWidth - 8, cGrid());
}

// ---------------------------------------------------------------- lists
static int s_top = 0;

// per-row cache of the full-screen list (see drawList)
static String s_rowKey[ROWS];
static const Option *s_rowsOptions = nullptr;
static int s_rowsTotal = -1;
static String s_rowsTitle;
static bool s_rowsValid = false;

void invalidateList() { s_rowsValid = false; }

static void keepVisible(int index, int total, int rows, bool reset) {
    if (reset) s_top = index - rows + 1;
    if (index < s_top) s_top = index;
    if (index >= s_top + rows) s_top = index - rows + 1;
    if (s_top > total - rows) s_top = total - rows;
    if (s_top < 0) s_top = 0;
}

static uint16_t rowColor(const Option &o) {
    if (!o.enabled) return cDim();
    if (o.selected) return SEC();
    if (o.hasColor) return o.color;
    return cText();
}

Opt_Coord drawList(
    int index, std::vector<Option> &options, const char *title, bool firstRender, bool border, bool compact
) {
    s_cursorValid = false;
    Opt_Coord coord;
    int total = options.size();
    for (auto &o : options) {
        o.w = 0;
        o.h = 0;
    }

    if (border || compact) {
        // ---- popup / context menu: double-line box over the current screen
        int rows = total < ROWS ? total : ROWS;
        keepVisible(index, total, rows, firstRender);
        int bw = 204, bx = (tftWidth - bw) / 2;
        int bh = 8 + rows * ROW_H + 4;
        int by = (tftHeight - bh) / 2;
        if (by < 15) by = 15;
        if (firstRender) dbox(bx, by, bw, bh, PRI(), cGrid(), true, cPanel());
        int maxChars = (bw - 20) / (LW * FM);
        for (int k = 0; k < rows; k++) {
            int i = s_top + k;
            int y = by + 6 + k * ROW_H;
            tft.fillRect(bx + 4, y, bw - 8, 16, cPanel());
            options[i].x = bx;
            options[i].y = y;
            options[i].w = bw;
            options[i].h = ROW_H;
            String lab = T(options[i].label);
            if (i == index) {
                tft.fillRect(bx + 4, y, bw - 8, 16, PRI());
                text(">" + lab.substring(0, maxChars), bx + 6, y + 1, FM, BG());
                coord.x = bx + 6 + LW * FM;
                coord.y = y + 1;
                coord.size = maxChars + 1;
                coord.fgcolor = PRI();
                coord.bgcolor = BG();
            } else {
                text(" " + lab.substring(0, maxChars), bx + 6, y + 1, FM, rowColor(options[i]));
            }
        }
        tft.setTextSize(FM);
        return coord;
    }

    // ---- full-screen list (submenus and regular menus)
    keepVisible(index, total, ROWS, firstRender);
    // Moving the cursor inside the visible window changes only two rows. Each row remembers
    // what it shows (label, colour, highlight) and is repainted only when that changes, which
    // turns a 5-row repaint into a 2-row one and removes the flicker on long lists.
    const String ttl = title ? String(title) : String("");
    if (firstRender || s_rowsOptions != options.data() || s_rowsTotal != total || !s_rowsTitle.equals(ttl))
        s_rowsValid = false;
    if (firstRender) {
        tft.fillRect(0, 14, tftWidth, 109, BG());
        footerHint();
    }
    char cnt[12];
    snprintf(cnt, sizeof(cnt), "%02d/%02d", index + 1, total);
    header(ttl, String(cnt));
    if (!s_rowsValid) {
        for (auto &k : s_rowKey) k = "";
        s_rowsOptions = options.data();
        s_rowsTotal = total;
        s_rowsTitle = ttl;
        s_rowsValid = true;
    }

    for (int k = 0; k < ROWS; k++) {
        int i = s_top + k;
        int y = ROW_Y + k * ROW_H;
        if (i >= total) {
            if (s_rowKey[k] != "-") tft.fillRect(0, y, tftWidth - 10, ROW_H - 2, BG());
            s_rowKey[k] = "-";
            continue;
        }
        options[i].x = 0;
        options[i].y = y;
        options[i].w = tftWidth;
        options[i].h = ROW_H;
        String key = options[i].label;
        key += i == index ? '\x02' : '\x01';
        key += String(rowColor(options[i]), 16);
        if (key.equals(s_rowKey[k])) {
            if (i == index) { // the scroller draws over this row, so it still needs the coordinates
                coord.x = 4 + LW * FM;
                coord.y = y + 1;
                coord.size = 18;
                coord.fgcolor = PRI();
                coord.bgcolor = BG();
            }
            continue;
        }
        s_rowKey[k] = key;
        tft.fillRect(0, y, tftWidth - 10, ROW_H - 2, BG());
        String lab = T(options[i].label);
        if (i == index) {
            tft.fillRect(2, y, tftWidth - 12, 16, PRI()); // inverse video bar
            text(">" + lab.substring(0, 17), 4, y + 1, FM, BG());
            coord.x = 4 + LW * FM;
            coord.y = y + 1;
            coord.size = 18; // displayScrollingText shows size-1 chars and scrolls longer labels
            coord.fgcolor = PRI();
            coord.bgcolor = BG();
        } else if (lab.length() > 17) {
            text(" " + lab.substring(0, 15), 4, y + 1, FM, rowColor(options[i]));
            text("..", 4 + 16 * LW * FM + 1, y + 8, FP, cDim());
        } else {
            text(" " + lab, 4, y + 1, FM, rowColor(options[i]));
        }
    }
    // scroll hints, lit only when there is more in that direction
    tft.fillRect(tftWidth - 9, ROW_Y, 8, ROWS * ROW_H, BG());
    text("\x1e", tftWidth - 8, ROW_Y, FP, s_top > 0 ? PRI() : cGrid());
    text("\x1f", tftWidth - 8, ROW_Y + ROWS * ROW_H - 10, FP, s_top + ROWS < total ? PRI() : cGrid());
    tft.setTextSize(FM);
    return coord;
}

// ---------------------------------------------------------------- main menu
void mainMenu(MenuItemInterface *item, int idx, int total, const String &prev, const String &next) {
    tft.fillRect(0, 14, tftWidth, 109, BG());
    text("$ ls /bruce", 4, 17, FP, cDim());
    char cnt[12];
    snprintf(cnt, sizeof(cnt), "%02d/%02d", idx, total);
    textRight(cnt, tftWidth - 4, 17, FP, SEC());

    int bw = 76, bh = 54, bx = (tftWidth - bw) / 2, by = 30;
    dbox(bx, by, bw, bh, PRI(), cGrid(), false, 0);
    if (item) item->drawIconInBox(tftWidth / 2, by + bh / 2, 44, PRI(), BG());

    text("<<", 6, 52, FM, cDim());
    textRight(">>", tftWidth - 6, 52, FM, cDim());
    text(shortName(T(prev), 11), 6, 72, FP, cDim());
    textRight(shortName(T(next), 11), tftWidth - 6, 72, FP, cDim());

    String t = "> " + upper(T(item ? item->getName() : String("")));
    if (t.length() > 17) t = t.substring(0, 17);
    int tx = (tftWidth - ((int)t.length() + 1) * LW * FM) / 2;
    text(t, tx, 92, FM, PRI());
    s_cursorX = tx + t.length() * LW * FM + 2;
    s_cursorY = 92;
    s_cursorOn = true;
    s_cursorValid = true;
    s_cursorTs = millis();
    tft.fillRect(s_cursorX, s_cursorY, 10, 15, PRI());
    footerHint();
}

void tick() {
    if (!s_cursorValid || millis() - s_cursorTs < 500) return;
    s_cursorTs = millis();
    s_cursorOn = !s_cursorOn;
    tft.fillRect(s_cursorX, s_cursorY, 10, 15, s_cursorOn ? PRI() : BG());
}

// ---------------------------------------------------------------- messages
void toast(const String &txt, uint16_t legacyBg) {
    s_cursorValid = false;
    uint16_t col;
    const char *banner;
    if (legacyBg == TFT_RED) {
        col = RED;
        banner = "*** ERROR ***";
    } else if (legacyBg == TFT_YELLOW) {
        col = AMBER;
        banner = "!!! WARNING !!!";
    } else if (legacyBg == TFT_BLUE) {
        col = MINT;
        banner = "--- INFO ---";
    } else if (legacyBg == TFT_DARKGREEN) {
        col = PRI();
        banner = "+++ DONE +++";
    } else {
        col = SEC();
        banner = ">>> MESSAGE";
    }
    // split on explicit newlines, then word-wrap each part (32 chars at size 1)
    std::vector<String> lines;
    String s = T(txt);
    int start = 0;
    while (start <= (int)s.length()) {
        int nl = s.indexOf('\n', start);
        String part = nl < 0 ? s.substring(start) : s.substring(start, nl);
        part.trim();
        if (part.length()) {
            std::vector<String> w = wrapText(part, 32);
            lines.insert(lines.end(), w.begin(), w.end());
        }
        if (nl < 0) break;
        start = nl + 1;
    }
    if (lines.size() > 7) lines.resize(7);
    int bw = 216, bx = (tftWidth - bw) / 2;
    int bh = 30 + lines.size() * 10;
    int by = (14 + 122) / 2 - bh / 2;
    if (by < 15) by = 15;
    dbox(bx, by, bw, bh, col, col, true, cPanel());
    textCentre(T(banner), tftWidth / 2, by + 8, FP, col);
    for (size_t i = 0; i < lines.size(); i++) textCentre(lines[i], tftWidth / 2, by + 22 + i * 10, FP, cText());
    tft.setTextColor(PRI(), BG());
}

static void dialogDraw(const char *message, const std::vector<const char *> &btns, int sel, bool full) {
    if (full) {
        tft.fillRect(0, 14, tftWidth, 109, BG());
        header("Confirmation", "");
        std::vector<String> lines;
        String m = T(String(message));
        int start = 0;
        while (start <= (int)m.length()) {
            int nl = m.indexOf('\n', start);
            lines.push_back(nl < 0 ? m.substring(start) : m.substring(start, nl));
            if (nl < 0) break;
            start = nl + 1;
        }
        bool big = lines.size() <= 3;
        for (auto &l : lines)
            if (l.length() > 19) big = false;
        if (big) {
            for (size_t i = 0; i < lines.size(); i++) textCentre(lines[i], tftWidth / 2, 34 + i * 18, FM, cText());
        } else {
            std::vector<String> w;
            for (auto &l : lines) {
                std::vector<String> part = wrapText(l, 38);
                w.insert(w.end(), part.begin(), part.end());
            }
            if (w.size() > 5) w.resize(5);
            for (size_t i = 0; i < w.size(); i++) text(w[i], 6, 34 + i * 10, FP, i == 0 ? cText() : cDim());
        }
        hintLine("\x11\x10 ", "SELECT  M5 OK");
    }
    int n = btns.size();
    if (n == 0) return;
    int gap = 8;
    int bw = (tftWidth - 16 - (n - 1) * gap) / n;
    int maxChars = (bw - 8) / (LW * FM);
    tft.fillRect(0, 92, tftWidth, 24, BG());
    for (int i = 0; i < n; i++) {
        int x = 8 + i * (bw + gap);
        String lab = T(String(btns[i])).substring(0, maxChars);
        if (i == sel) {
            tft.fillRect(x, 94, bw, 20, PRI());
            textCentre(lab, x + bw / 2, 96, FM, BG());
        } else {
            tft.drawRect(x, 94, bw, 20, cGrid());
            textCentre(lab, x + bw / 2, 96, FM, cText());
        }
    }
}

int8_t dialog(const char *message, const char *left, const char *center, const char *right) {
    s_cursorValid = false;
    std::vector<const char *> btns;
    if (left) btns.push_back(left);
    if (center) btns.push_back(center);
    if (right) btns.push_back(right);
    int n = btns.size();
    int8_t selected = 0;
    dialogDraw(message, btns, selected, true);
    if (n == 0) return 0;
    while (true) {
        bool redraw = false;
        if (check(PrevPress) || check(EscPress)) {
            selected = (selected - 1 + n) % n;
            redraw = true;
        }
        if (check(NextPress)) {
            selected = (selected + 1) % n;
            redraw = true;
        }
        if (check(SelPress)) break;
        if (redraw) dialogDraw(message, btns, selected, false);
        delay(10);
    }
    return selected;
}

// ---------------------------------------------------------------- progress
void progress(int prog, size_t total, const String &message) {
    static int s_lastPct = -1;
    static String s_lastMsg;
    int pct = total ? (int)((int64_t)prog * 100 / (int64_t)total) : 0;
    if (pct < 0) pct = 0;
    if (pct > 100) pct = 100;
    // a new operation (restart, smaller value or another message) redraws the whole screen
    if (prog == 0 || s_lastPct < 0 || pct < s_lastPct || !s_lastMsg.equals(message)) {
        s_lastMsg = message;
        s_cursorValid = false;
        tft.fillRect(0, 14, tftWidth, 109, BG());
        header("Running, Wait", "");
        String m = T(message);
        if (m.length() <= 19) text(m, 6, 36, FM, cText());
        else {
            std::vector<String> w = wrapText(m, 38);
            for (size_t i = 0; i < w.size() && i < 2; i++) text(w[i], 6, 36 + i * 10, FP, cText());
        }
        s_lastPct = -1;
    }
    if (pct == s_lastPct) return;
    s_lastPct = pct;
    const int cells = 17;
    int filled = pct * cells / 100;
    String bar = "[";
    for (int i = 0; i < cells; i++) bar += (i < filled ? '#' : '.');
    bar += "]";
    tft.fillRect(0, 62, tftWidth, 16, BG());
    text(bar, 6, 62, FM, cDim());
    if (filled > 0) {
        String hashes = "";
        for (int i = 0; i < filled; i++) hashes += '#';
        text(hashes, 6 + LW * FM, 62, FM, PRI());
    }
    tft.fillRect(tftWidth - 60, 86, 60, 16, BG());
    textRight(String(pct) + "%", tftWidth - 6, 86, FM, SEC());
    if (pct >= 100) s_lastPct = -1;
}

// ---------------------------------------------------------------- titles
void title(const String &ttl) {
    s_cursorValid = false;
    String t = upper(T(ttl));
    String full = "[ " + t + " ]";
    int size = FM;
    while (size > FP && (int)(full.length() * size * LW) > tftWidth - 2 * BORDER_PAD_X) size--;
    if ((int)(full.length() * size * LW) > tftWidth - 8) full = t;
    tft.setTextColor(PRI(), BG());
    tft.setTextSize(size);
    tft.setCursor((tftWidth - (int)(full.length() * size * LW)) / 2, BORDER_PAD_Y);
    tft.println(full);
    tft.setTextSize(FP);
}

// ---------------------------------------------------------------- boot
static bool bootWait(unsigned ms) {
    unsigned long t0 = millis();
    while (millis() - t0 < ms) {
        if (check(AnyKeyPress)) return true;
        delay(5);
    }
    return false;
}

void boot() {
    tft.drawPixel(0, 0, 0);
    tft.fillScreen(BG());
    struct Line {
        const char *label;
        bool ok;
    };
    Line lines[] = {
        {"> init display .....", true                  },
        {"> mount littlefs ...", true                  },
        {"> sd card ..........", sdcardMounted         },
        {"> load bruce.conf ..", true                  },
        {i18n::active() ? "> lang ru .........." : "> lang en ..........", true},
    };
    text(String("BRUCE OS v") + BRUCE_VERSION, 6, 6, FP, cText());
    if (bootWait(150)) goto done;
    for (int i = 0; i < 5; i++) {
        int y = 17 + i * 11;
        text(lines[i].label, 6, y, FP, cDim());
        if (bootWait(90)) goto done;
        text(lines[i].ok ? "OK" : "--", 6 + 21 * LW, y, FP, lines[i].ok ? PRI() : AMBER);
        if (bootWait(60)) goto done;
    }
    {
        String t = T("PREDATORY FIRMWARE");
        text(t, 6, 80, FM, PRI());
        int cx = 6 + t.length() * LW * FM + 4;
        text("[" + String("...................").substring(0, 19) + "]", 6, 108, FP, cDim());
        for (int i = 0; i <= 19; i++) {
            tft.fillRect(cx, 80, 10, 15, (i / 3) % 2 ? BG() : PRI()); // blinking block cursor
            if (i > 0) text("#", 6 + i * LW, 108, FP, PRI());
            tft.fillRect(6 + 22 * LW, 108, 5 * LW, 8, BG());
            text(String(i * 100 / 19) + "%", 6 + 22 * LW, 108, FP, cDim());
            if (bootWait(55)) goto done;
        }
        tft.fillRect(cx, 80, 10, 15, PRI());
        bootWait(400);
    }
done:
    tft.fillScreen(BG());
}

} // namespace fos
