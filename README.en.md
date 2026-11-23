<div align="center">

<img src="docs/banner.svg" width="100%" alt="Bruce RU — Russian Bruce firmware with the Fosfor UI for M5StickC Plus2">

<p>
  <a href="https://github.com/expl01t-search/bruce-ru/releases/latest"><img src="https://img.shields.io/github/v/release/expl01t-search/bruce-ru?style=for-the-badge&color=39ff6a&labelColor=161b22&label=release" alt="Latest release"></a>
  <a href="https://github.com/expl01t-search/bruce-ru/actions/workflows/build.yml"><img src="https://img.shields.io/github/actions/workflow/status/expl01t-search/bruce-ru/build.yml?style=for-the-badge&color=39ff6a&labelColor=161b22&label=build" alt="Build"></a>
  <img src="https://img.shields.io/badge/M5StickC-Plus2-39ff6a?style=for-the-badge&labelColor=161b22" alt="M5StickC Plus2">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-39ff6a?style=for-the-badge&labelColor=161b22" alt="AGPL-3.0"></a>
</p>

<a href="https://github.com/expl01t-search/bruce-ru/releases/latest"><img src="https://img.shields.io/badge/⬇_Download-.bin_for_M5StickC_Plus2-39ff6a?style=for-the-badge&labelColor=0d1117" alt="Download firmware"></a>
<a href="README.md"><img src="https://img.shields.io/badge/Русский-README.md-161b22?style=for-the-badge" alt="Русский"></a>

<br><br>

<img src="docs/screens/main_wifi.png" width="49%" alt="Main menu">
<img src="docs/screens/list_config.png" width="49%" alt="Settings submenu">

</div>

<img src="docs/divider.svg" width="100%" alt="">

## `> what is it`

**Bruce RU** is a build of the open-source [Bruce](https://github.com/BruceDevices/firmware) 1.17 firmware for the **M5StickC Plus2** with:

| | |
|:--|:--|
| **Full Russian UI** | ~3000 strings: menus, messages, hints and titles. Cyrillic is baked into the built-in 5×8 font, so it costs no extra resources. Cyrillic file names and Wi‑Fi SSIDs render correctly too |
| **Fosfor interface** | A green phosphor-terminal look: status bar, main menu, inverse-highlight lists, toasts, dialogs, progress bars and a boot-log splash |
| **Upstream bug fixes** | Crashes in the `display start/stop/dump` serial commands, broken `printf` output, thread races and a sample-loss bug in the SUMP logic analyzer |
| **Toggles** | Language and style switch live in *Settings → Display & UI*. English and the classic Bruce look are one click away |

The translation layer is generic: a TSV dictionary compiled into a sorted table at build time, plus a font patch. It can be reused for **other Cyrillic languages** (Ukrainian, Belarusian, Kazakh, Serbian) — PRs welcome.

## `> screenshots`

<p align="center">
  <img src="docs/screens/boot.png" width="32%" alt="Boot splash">
  <img src="docs/screens/list_wifi.png" width="32%" alt="WiFi list">
  <img src="docs/screens/overlay_menu.png" width="32%" alt="Popup menu">
</p>
<p align="center">
  <img src="docs/screens/toast_error.png" width="32%" alt="Error toast">
  <img src="docs/screens/dialog.png" width="32%" alt="Confirmation dialog">
  <img src="docs/screens/progress.png" width="32%" alt="Progress">
</p>

## `> install`

Download `Bruce-m5stack-cplus2-ru.bin` from the [latest release](https://github.com/expl01t-search/bruce-ru/releases/latest) and flash it at `0x0`:

```powershell
pip install esptool
python -m esptool --chip esp32 --port COM5 --baud 921600 write-flash -z 0x0 Bruce-m5stack-cplus2-ru.bin
```

Device settings (LittleFS) are preserved.

**Controls:** `PWR` up, side `B` down, `M5` select, `PWR + B` back. Hold `PWR` for 3 s to power off.

<details>
<summary><b>Build from source</b></summary>

```bash
git clone --recurse-submodules https://github.com/expl01t-search/bruce-ru.git
cd bruce-ru
pip install platformio
pio run -e m5stack-cplus2
```

Translation internals: [tools/i18n/README.md](tools/i18n/README.md).

</details>

<img src="docs/divider.svg" width="100%" alt="">

## `> responsible use`

Bruce is a tool for studying wireless protocols and testing **your own** devices and networks. Only use it where you are authorised to.

## `> credits`

Based on [Bruce](https://github.com/BruceDevices/firmware) by BruceDevices and contributors — original README in [README_BRUCE.md](README_BRUCE.md). License: [AGPL-3.0](LICENSE).
