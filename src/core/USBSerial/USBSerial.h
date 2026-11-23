#ifndef BRUCE_USBSERIAL_H
#define BRUCE_USBSERIAL_H

#include "SerialDevice.h"
#include <Arduino.h>

class USBSerial : public SerialDevice {
public:
    size_t println(const String &s) override { return out->println(s); }
    size_t print(const String &s) override { return out->print(s); }
    size_t print(const int n, int format) override { return out->print(n, format); }
    // Format here: passing a va_list on to the variadic Print::printf() is undefined
    // behaviour (it printed the va_list address and crashed on "%s" arguments).
    void vprintf(const char *fmt, va_list args) override {
        char small[128];
        va_list copy;
        va_copy(copy, args);
        int n = vsnprintf(small, sizeof(small), fmt, copy);
        va_end(copy);
        if (n <= 0) return;
        if (n < (int)sizeof(small)) {
            out->write(reinterpret_cast<const uint8_t *>(small), n);
            return;
        }
        char *big = static_cast<char *>(malloc(n + 1)); // long output: no truncation
        if (!big) {
            out->write(reinterpret_cast<const uint8_t *>(small), sizeof(small) - 1);
            return;
        }
        vsnprintf(big, n + 1, fmt, args);
        out->write(reinterpret_cast<const uint8_t *>(big), n);
        free(big);
    }
    size_t println() override { return out->println(); }
    size_t println(size_t n) override { return out->println(n); }
    size_t println(const uint32_t n) override { return out->println(n); }
    size_t println(const int n, int format) override { return out->println(n, format); }
    String readStringUntil(char terminator) override { return out->readStringUntil(terminator); }
    void flush() override { out->flush(); }
    int available() override { return out->available(); }
    size_t write(uint8_t *str, size_t size) override { return out->write(str, size); }
    int read() override { return out->read(); }
    void setSerialOutput(Stream *in) { out = in; }
    Stream *getSerialOutput() { return out; }
    USBSerial(Stream *in = &Serial) { out = in; }
    ~USBSerial() override = default;

private:
    Stream *out;
};

#endif // BRUCE_USBSERIAL_H
