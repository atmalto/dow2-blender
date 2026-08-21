// Minimal, dependency-free JSON value + parser + serializer for the CLI.
//
// Qt 4.8 has no JSON support and we do not want to pull an external library into
// the VS2008 build, so this provides just enough JSON for the command driver:
// null/bool/number/string/array/object, order-preserving objects, a recursive
// descent parser, and a pretty serializer. C++03-only (no C++11 features).
#ifndef HAVOK_SIM_CLI_JSON_VALUE_H
#define HAVOK_SIM_CLI_JSON_VALUE_H

#include <string>
#include <utility>
#include <vector>

class JsonValue
{
public:
    enum Type
    {
        TypeNull,
        TypeBool,
        TypeNumber,
        TypeString,
        TypeArray,
        TypeObject
    };

    JsonValue();
    explicit JsonValue(bool value);
    explicit JsonValue(double value);
    explicit JsonValue(int value);
    explicit JsonValue(const std::string& value);
    explicit JsonValue(const char* value);

    Type type() const { return m_type; }
    bool is_null() const { return m_type == TypeNull; }
    bool is_object() const { return m_type == TypeObject; }
    bool is_array() const { return m_type == TypeArray; }

    // Scalar accessors with defaults for missing/mismatched values.
    bool as_bool(bool fallback = false) const;
    double as_number(double fallback = 0.0) const;
    int as_int(int fallback = 0) const;
    std::string as_string(const std::string& fallback = std::string()) const;

    // Array access.
    std::size_t size() const { return m_array.size(); }
    const JsonValue& at(std::size_t index) const;
    void push_back(const JsonValue& value);

    // Object access (order preserving).
    const JsonValue* find(const std::string& key) const;
    bool has(const std::string& key) const { return find(key) != 0; }
    void set(const std::string& key, const JsonValue& value);

    // Convenience readers for object members.
    double member_number(const std::string& key, double fallback = 0.0) const;
    int member_int(const std::string& key, int fallback = 0) const;
    bool member_bool(const std::string& key, bool fallback = false) const;
    std::string member_string(const std::string& key, const std::string& fallback = std::string()) const;

    // Read a numeric array of exactly N components into out[]; returns false if the
    // member is missing or not an array of the right length (out left untouched).
    bool member_vec(const std::string& key, float* out, int count) const;

    static JsonValue make_array();
    static JsonValue make_object();
    static JsonValue make_vec(const float* values, int count);

    // Serialize with indentation.
    std::string dump(int indent = 2) const;

    // Parse text; on failure returns a Null value and sets *error (if provided).
    static JsonValue parse(const std::string& text, std::string* error);

private:
    void dump_to(std::string& out, int indent, int depth) const;

    Type m_type;
    bool m_bool;
    double m_number;
    std::string m_string;
    std::vector<JsonValue> m_array;
    std::vector<std::pair<std::string, JsonValue> > m_object;
};

#endif
