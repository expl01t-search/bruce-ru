# Bruce RU — русская сборка с интерфейсом «Фосфор»

Сборка прошивки [Bruce](https://github.com/BruceDevices/firmware) 1.17 для **M5StickC Plus2**:
русский интерфейс, новый терминальный стиль «Фосфор» и исправления ошибок оригинала.

## Что изменено

**Русский язык**
- Кириллица (64 буквы) добавлена во встроенный шрифт TFT_eSPI 5×8 — `tools/i18n/cyrillic_glyphs.txt`.
- Перевод на лету при выводе на экран, ~3000 строк интерфейса — `src/core/i18n.*`, словарь `tools/i18n/ru.d/*.tsv`.
- Переключатель: *Настройки → Экран и интерфейс → Язык*.
- Подробно: [tools/i18n/README.md](tools/i18n/README.md).

**Интерфейс «Фосфор»** (`src/core/ui_fosfor.*`)
- Зелёный терминал: статус-бар, главное меню, списки с инверсным выделением, сообщения,
  диалоги, прогресс, заставка в виде лога загрузки.
- Макеты и спецификация: `tools/ui/fosfor_preview.py`.
- Переключатель: *Настройки → Экран и интерфейс → Стиль* (Фосфор / Классика).

**Исправления ошибок Bruce**
- `USBSerial::vprintf` передавал `va_list` в вариадический `printf` — мусор вместо чисел и падение на `%s`.
- `display stop` освобождал буфер лога экрана во время записи в него (use-after-free), `display start` терял память.
- `display dump` держал 8 КБ на стеке serial-задачи.
- Гонка при остановке трансляции экрана (отправка в удалённую очередь).
- Гонка потоков с `menuOptionLabel` между меню и serial-командами.
- Логический анализатор (SUMP): переполнение счётчика буфера терял все отсчёты, кроме последних 255.

## Сборка и прошивка

```powershell
git submodule update --init --recursive
python -m platformio run -e m5stack-cplus2
python -m esptool --chip esp32 --port COM5 --baud 921600 write-flash -z 0x0 Bruce-m5stack-cplus2.bin
```

Готовый образ — в разделе Releases (`Bruce-m5stack-cplus2-ru.bin`, адрес `0x0`).

## Проверка

- Тесты перевода на компьютере: `tools/i18n/test/test_i18n.cpp` (см. tools/i18n/README.md).
- На устройстве через USB: `python tools/i18n/device_check.py COM5 status screen next screen`.

Лицензия — как у оригинального Bruce (см. `LICENSE`).
