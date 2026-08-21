#include "json_value.h"

#include <cstdio>
#include <cstdlib>

JsonValue::JsonValue()
    : m_type(TypeNull)
    , m_bool(false)
    , m_number(0.0)
{
}

JsonValue::JsonValue(bool value)
    : m_type(TypeBool)
    , m_bool(value)
    , m_number(0.0)
{
}

JsonValue::JsonValue(double value)
    : m_type(TypeNumber)
    , m_bool(false)
    , m_number(value)
{
}

JsonValue::JsonValue(int value)
    : m_type(TypeNumber)
    , m_bool(false)
    , m_number(static_cast<double>(value))
{
}

JsonValue::JsonValue(const std::string& value)
    : m_type(TypeString)
    , m_bool(false)
    , m_number(0.0)
    , m_string(value)
{
}

JsonValue::JsonValue(const char* value)
    : m_type(TypeString)
    , m_bool(false)
    , m_number(0.0)
    , m_string(value ? value : "")
{
}

bool JsonValue::as_bool(bool fallback) const
{
    if (m_type == TypeBool)
    {
        return m_bool;
    }
    if (m_type == TypeNumber)
    {
        return m_number != 0.0;
    }
    return fallback;
}

double JsonValue::as_number(double fallback) const
{
    if (m_type == TypeNumber)
    {
        return m_number;
    }
    if (m_type == TypeBool)
    {
        return m_bool ? 1.0 : 0.0;
    }
    return fallback;
}

int JsonValue::as_int(int fallback) const
{
    if (m_type == TypeNumber)
    {
        return static_cast<int>(m_number);
    }
    return fallback;
}

std::string JsonValue::as_string(const std::string& fallback) const
{
    if (m_type == TypeString)
    {
        return m_string;
    }
    return fallback;
}

const JsonValue& JsonValue::at(std::size_t index) const
{
    static const JsonValue null_value;
    if (m_type != TypeArray || index >= m_array.size())
    {
        return null_value;
    }
    return m_array[index];
}

void JsonValue::push_back(const JsonValue& value)
{
    if (m_type != TypeArray)
    {
        m_type = TypeArray;
        m_array.clear();
    }
    m_array.push_back(value);
}

const JsonValue* JsonValue::find(const std::string& key) const
{
    if (m_type != TypeObject)
    {
        return 0;
    }
    for (std::size_t i = 0; i < m_object.size(); ++i)
    {
        if (m_object[i].first == key)
        {
            return &m_object[i].second;
        }
    }
    return 0;
}

void JsonValue::set(const std::string& key, const JsonValue& value)
{
    if (m_type != TypeObject)
    {
        m_type = TypeObject;
        m_object.clear();
    }
    for (std::size_t i = 0; i < m_object.size(); ++i)
    {
        if (m_object[i].first == key)
        {
            m_object[i].second = value;
            return;
        }
    }
    m_object.push_back(std::make_pair(key, value));
}

double JsonValue::member_number(const std::string& key, double fallback) const
{
    const JsonValue* v = find(key);
    return v ? v->as_number(fallback) : fallback;
}

int JsonValue::member_int(const std::string& key, int fallback) const
{
    const JsonValue* v = find(key);
    return v ? v->as_int(fallback) : fallback;
}

bool JsonValue::member_bool(const std::string& key, bool fallback) const
{
    const JsonValue* v = find(key);
    return v ? v->as_bool(fallback) : fallback;
}

std::string JsonValue::member_string(const std::string& key, const std::string& fallback) const
{
    const JsonValue* v = find(key);
    return v ? v->as_string(fallback) : fallback;
}

bool JsonValue::member_vec(const std::string& key, float* out, int count) const
{
    const JsonValue* v = find(key);
    if (!v || !v->is_array() || static_cast<int>(v->size()) != count)
    {
        return false;
    }
    for (int i = 0; i < count; ++i)
    {
        out[i] = static_cast<float>(v->at(static_cast<std::size_t>(i)).as_number(0.0));
    }
    return true;
}

JsonValue JsonValue::make_array()
{
    JsonValue v;
    v.m_type = TypeArray;
    return v;
}

JsonValue JsonValue::make_object()
{
    JsonValue v;
    v.m_type = TypeObject;
    return v;
}

JsonValue JsonValue::make_vec(const float* values, int count)
{
    JsonValue v = make_array();
    for (int i = 0; i < count; ++i)
    {
        v.push_back(JsonValue(static_cast<double>(values[i])));
    }
    return v;
}

namespace
{
    void append_escaped(std::string& out, const std::string& text)
    {
        out += '"';
        for (std::size_t i = 0; i < text.size(); ++i)
        {
            const char c = text[i];
            switch (c)
            {
            case '"': out += "\\\""; break;
            case '\\': out += "\\\\"; break;
            case '\n': out += "\\n"; break;
            case '\t': out += "\\t"; break;
            case '\r': out += "\\r"; break;
            default: out += c; break;
            }
        }
        out += '"';
    }

    void append_indent(std::string& out, int indent, int depth)
    {
        if (indent <= 0)
        {
            return;
        }
        out += '\n';
        for (int i = 0; i < indent * depth; ++i)
        {
            out += ' ';
        }
    }

    void format_number(std::string& out, double value)
    {
        char buffer[64];
        // Integers print without a trailing ".0"; otherwise use compact %g.
        if (value == static_cast<double>(static_cast<long long>(value)) &&
            value < 1e15 && value > -1e15)
        {
            std::sprintf(buffer, "%lld", static_cast<long long>(value));
        }
        else
        {
            std::sprintf(buffer, "%.6g", value);
        }
        out += buffer;
    }
}

void JsonValue::dump_to(std::string& out, int indent, int depth) const
{
    switch (m_type)
    {
    case TypeNull:
        out += "null";
        break;
    case TypeBool:
        out += (m_bool ? "true" : "false");
        break;
    case TypeNumber:
        format_number(out, m_number);
        break;
    case TypeString:
        append_escaped(out, m_string);
        break;
    case TypeArray:
        if (m_array.empty())
        {
            out += "[]";
            break;
        }
        out += '[';
        for (std::size_t i = 0; i < m_array.size(); ++i)
        {
            if (i > 0)
            {
                out += ',';
            }
            append_indent(out, indent, depth + 1);
            m_array[i].dump_to(out, indent, depth + 1);
        }
        append_indent(out, indent, depth);
        out += ']';
        break;
    case TypeObject:
        if (m_object.empty())
        {
            out += "{}";
            break;
        }
        out += '{';
        for (std::size_t i = 0; i < m_object.size(); ++i)
        {
            if (i > 0)
            {
                out += ',';
            }
            append_indent(out, indent, depth + 1);
            append_escaped(out, m_object[i].first);
            out += (indent > 0 ? ": " : ":");
            m_object[i].second.dump_to(out, indent, depth + 1);
        }
        append_indent(out, indent, depth);
        out += '}';
        break;
    }
}

std::string JsonValue::dump(int indent) const
{
    std::string out;
    dump_to(out, indent, 0);
    return out;
}

namespace
{
    struct Parser
    {
        const char* p;
        const char* end;
        std::string error;

        Parser(const std::string& text)
            : p(text.c_str())
            , end(text.c_str() + text.size())
        {
        }

        void skip_ws()
        {
            while (p < end && (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r'))
            {
                ++p;
            }
        }

        bool fail(const char* message)
        {
            if (error.empty())
            {
                error = message;
            }
            return false;
        }

        bool parse_value(JsonValue& out);
        bool parse_string(std::string& out);
        bool parse_number(JsonValue& out);
        bool parse_array(JsonValue& out);
        bool parse_object(JsonValue& out);
        bool match_literal(const char* literal);
    };

    bool Parser::match_literal(const char* literal)
    {
        const char* q = literal;
        while (*q)
        {
            if (p >= end || *p != *q)
            {
                return false;
            }
            ++p;
            ++q;
        }
        return true;
    }

    bool Parser::parse_string(std::string& out)
    {
        if (p >= end || *p != '"')
        {
            return fail("expected string");
        }
        ++p;
        out.clear();
        while (p < end && *p != '"')
        {
            char c = *p++;
            if (c == '\\' && p < end)
            {
                char esc = *p++;
                switch (esc)
                {
                case 'n': out += '\n'; break;
                case 't': out += '\t'; break;
                case 'r': out += '\r'; break;
                case '"': out += '"'; break;
                case '\\': out += '\\'; break;
                case '/': out += '/'; break;
                case 'b': out += '\b'; break;
                case 'f': out += '\f'; break;
                case 'u':
                    // Minimal: skip the 4 hex digits, emit '?' (paths/labels are ASCII).
                    for (int i = 0; i < 4 && p < end; ++i)
                    {
                        ++p;
                    }
                    out += '?';
                    break;
                default: out += esc; break;
                }
            }
            else
            {
                out += c;
            }
        }
        if (p >= end || *p != '"')
        {
            return fail("unterminated string");
        }
        ++p;
        return true;
    }

    bool Parser::parse_number(JsonValue& out)
    {
        char* stop = 0;
        double value = std::strtod(p, &stop);
        if (stop == p)
        {
            return fail("invalid number");
        }
        p = stop;
        out = JsonValue(value);
        return true;
    }

    bool Parser::parse_array(JsonValue& out)
    {
        ++p; // consume '['
        out = JsonValue::make_array();
        skip_ws();
        if (p < end && *p == ']')
        {
            ++p;
            return true;
        }
        for (;;)
        {
            JsonValue element;
            if (!parse_value(element))
            {
                return false;
            }
            out.push_back(element);
            skip_ws();
            if (p < end && *p == ',')
            {
                ++p;
                skip_ws();
                continue;
            }
            if (p < end && *p == ']')
            {
                ++p;
                return true;
            }
            return fail("expected ',' or ']' in array");
        }
    }

    bool Parser::parse_object(JsonValue& out)
    {
        ++p; // consume '{'
        out = JsonValue::make_object();
        skip_ws();
        if (p < end && *p == '}')
        {
            ++p;
            return true;
        }
        for (;;)
        {
            skip_ws();
            std::string key;
            if (!parse_string(key))
            {
                return false;
            }
            skip_ws();
            if (p >= end || *p != ':')
            {
                return fail("expected ':' in object");
            }
            ++p;
            JsonValue value;
            if (!parse_value(value))
            {
                return false;
            }
            out.set(key, value);
            skip_ws();
            if (p < end && *p == ',')
            {
                ++p;
                continue;
            }
            if (p < end && *p == '}')
            {
                ++p;
                return true;
            }
            return fail("expected ',' or '}' in object");
        }
    }

    bool Parser::parse_value(JsonValue& out)
    {
        skip_ws();
        if (p >= end)
        {
            return fail("unexpected end of input");
        }
        const char c = *p;
        if (c == '{')
        {
            return parse_object(out);
        }
        if (c == '[')
        {
            return parse_array(out);
        }
        if (c == '"')
        {
            std::string s;
            if (!parse_string(s))
            {
                return false;
            }
            out = JsonValue(s);
            return true;
        }
        if (c == 't')
        {
            if (match_literal("true")) { out = JsonValue(true); return true; }
            return fail("invalid literal");
        }
        if (c == 'f')
        {
            if (match_literal("false")) { out = JsonValue(false); return true; }
            return fail("invalid literal");
        }
        if (c == 'n')
        {
            if (match_literal("null")) { out = JsonValue(); return true; }
            return fail("invalid literal");
        }
        return parse_number(out);
    }
}

JsonValue JsonValue::parse(const std::string& text, std::string* error)
{
    Parser parser(text);
    JsonValue root;
    if (!parser.parse_value(root))
    {
        if (error)
        {
            *error = parser.error.empty() ? "parse error" : parser.error;
        }
        return JsonValue();
    }
    parser.skip_ws();
    if (parser.p != parser.end)
    {
        if (error)
        {
            *error = "trailing characters after JSON value";
        }
        return JsonValue();
    }
    return root;
}
