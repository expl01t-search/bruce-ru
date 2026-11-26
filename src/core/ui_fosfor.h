#ifndef __BRUCE_UI_FOSFOR_H__
#define __BRUCE_UI_FOSFOR_H__

// "ФОСФОР" UI style: green phosphor terminal look for the shared Bruce UI parts
// (status bar, main menu, lists, messages, dialogs, progress, titles, boot screen).
// Layout spec and pixel-exact previews: tools/ui/fosfor_preview.py
//
// Accents come from bruceConfig.priColor / secColor / bgColor; the neutral shades
// (text, dim, grid, panel) are derived from them, so any accent colour works.

#include "display.h"
#include <Arduino.h>
#include <vector>

class MenuItemInterface;

namespace fos {

enum UiStyle : uint8_t { UI_CLASSIC = 0, UI_FOSFOR = 1 };

// Default palette (RGB565) applied when the style is switched on
static const uint16_t DEF_PRI = 0x3FED; // #39FF6A phosphor green
static const uint16_t DEF_SEC = 0xCFE7; // #C8FF3A lime
static const uint16_t DEF_BG = 0x0040;  // #000A03
static const uint16_t RED = 0xFAC7;     // #FF5A3C error
static const uint16_t AMBER = 0xFE87;   // #FFD23C warning
static const uint16_t MINT = 0x7FFB;    // #7DFFDE info

bool active();

// derived palette
uint16_t cText();
uint16_t cDim();
uint16_t cGrid();
uint16_t cPanel();

// shared chrome
void statusBar();
void mainBorder(bool clear);
void footerHint();
void header(const String &title, const String &counter);

// lists (submenus, regular and popup menus). Returns the selected row's text box,
// which loopOptions() hands to displayScrollingText() for long labels.
Opt_Coord drawList(
    int index, std::vector<Option> &options, const char *title, bool firstRender, bool border, bool compact
);
// Forget what the list rows show; call after something else drew over the list.
void invalidateList();

// main menu (carousel style)
void mainMenu(MenuItemInterface *item, int idx, int total, const String &prev, const String &next);
void tick(); // blinks the main-menu block cursor, call from the menu loop

// messages / dialogs / progress / titles / boot
void toast(const String &text, uint16_t legacyBg);
int8_t dialog(const char *message, const char *left, const char *center, const char *right);
void progress(int progress, size_t total, const String &message);
void title(const String &title);
void boot();

} // namespace fos

#endif
