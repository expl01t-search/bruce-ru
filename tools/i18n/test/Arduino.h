// Minimal host-side stand-in for the Arduino String class, enough to unit-test core/i18n.cpp.
#pragma once
#include <cstdint>
#include <cstring>
#include <string>

class String {
public:
    String() {}
    String(const char *s) : d(s ? s : "") {}
    String(const std::string &s) : d(s) {}
    unsigned int length() const { return (unsigned int)d.size(); }
    const char *c_str() const { return d.c_str(); }
    bool concat(const char *s, unsigned int n) {
        d.append(s, n);
        return true;
    }
    void reserve(unsigned int n) { d.reserve(n); }
    void setCharAt(unsigned int i, char c) {
        if (i < d.size()) d[i] = c;
    }
    char operator[](unsigned int i) const { return i < d.size() ? d[i] : 0; }
    String &operator+=(const String &o) {
        d += o.d;
        return *this;
    }
    String &operator+=(const char *o) {
        d += o;
        return *this;
    }
    String &operator+=(char c) {
        d += c;
        return *this;
    }
    bool operator==(const String &o) const { return d == o.d; }
    String &operator=(const String &o) {
        d = o.d;
        return *this;
    }
    std::string d;
};
