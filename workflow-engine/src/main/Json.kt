package mthandizi.workflow

/**
 * A minimal, dependency-free JSON parser.
 *
 * WHY THIS EXISTS RATHER THAN A LIBRARY
 * --------------------------------------
 * The normal choice here would be kotlinx.serialization or Moshi. Both need
 * Maven Central, which - like Hugging Face earlier in this project - is
 * blocked from the authoring sandbox (confirmed: `curl ... repo1.maven.org`
 * returns 403). Rather than write code that can't be proven to compile and
 * run, this is a small recursive-descent parser covering the JSON subset the
 * service-definition files actually need: objects, arrays, strings, numbers,
 * booleans, null. No dependencies, so it's provably testable right now.
 *
 * When the real Android build is set up (Phase 5+) with Gradle/Maven access,
 * swapping this for Moshi (the stack named in the original build prompt) is a
 * localised change - only `ServiceDefinition.fromJson()` touches this parser
 * directly; nothing else in the engine knows JSON exists at all. That
 * boundary is deliberate.
 */
sealed class JsonValue {
    data class JsonObject(val entries: Map<String, JsonValue>) : JsonValue() {
        operator fun get(key: String): JsonValue? = entries[key]
        fun string(key: String): String = (entries[key] as? JsonString)?.value
            ?: throw JsonException("Expected string field '$key'")
        fun stringOrNull(key: String): String? = (entries[key] as? JsonString)?.value
        fun bool(key: String, default: Boolean): Boolean = (entries[key] as? JsonBool)?.value ?: default
        fun array(key: String): List<JsonValue> = (entries[key] as? JsonArray)?.items
            ?: throw JsonException("Expected array field '$key'")
        fun arrayOrEmpty(key: String): List<JsonValue> = (entries[key] as? JsonArray)?.items ?: emptyList()
    }
    data class JsonArray(val items: List<JsonValue>) : JsonValue()
    data class JsonString(val value: String) : JsonValue()
    data class JsonNumber(val value: Double) : JsonValue()
    data class JsonBool(val value: Boolean) : JsonValue()
    object JsonNull : JsonValue()
}

class JsonException(message: String) : Exception(message)

object Json {
    fun parse(text: String): JsonValue {
        val parser = Parser(text)
        val value = parser.parseValue()
        parser.skipWhitespace()
        if (!parser.atEnd()) {
            throw JsonException("Unexpected trailing content at position ${parser.pos}")
        }
        return value
    }

    private class Parser(val text: String) {
        var pos = 0

        fun atEnd() = pos >= text.length
        fun peek(): Char = if (atEnd()) '\u0000' else text[pos]

        fun skipWhitespace() {
            while (!atEnd() && text[pos].isWhitespace()) pos++
        }

        fun expect(c: Char) {
            if (atEnd() || text[pos] != c) {
                throw JsonException("Expected '$c' at position $pos, found '${peek()}'")
            }
            pos++
        }

        fun parseValue(): JsonValue {
            skipWhitespace()
            if (atEnd()) throw JsonException("Unexpected end of input")
            return when (peek()) {
                '{' -> parseObject()
                '[' -> parseArray()
                '"' -> JsonValue.JsonString(parseStringRaw())
                't', 'f' -> parseBool()
                'n' -> parseNull()
                else -> parseNumber()
            }
        }

        fun parseObject(): JsonValue.JsonObject {
            expect('{')
            val entries = LinkedHashMap<String, JsonValue>()
            skipWhitespace()
            if (peek() == '}') { pos++; return JsonValue.JsonObject(entries) }
            while (true) {
                skipWhitespace()
                val key = parseStringRaw()
                skipWhitespace()
                expect(':')
                val value = parseValue()
                entries[key] = value
                skipWhitespace()
                when (peek()) {
                    ',' -> { pos++; continue }
                    '}' -> { pos++; break }
                    else -> throw JsonException("Expected ',' or '}' at position $pos")
                }
            }
            return JsonValue.JsonObject(entries)
        }

        fun parseArray(): JsonValue.JsonArray {
            expect('[')
            val items = mutableListOf<JsonValue>()
            skipWhitespace()
            if (peek() == ']') { pos++; return JsonValue.JsonArray(items) }
            while (true) {
                items.add(parseValue())
                skipWhitespace()
                when (peek()) {
                    ',' -> { pos++; continue }
                    ']' -> { pos++; break }
                    else -> throw JsonException("Expected ',' or ']' at position $pos")
                }
            }
            return JsonValue.JsonArray(items)
        }

        fun parseStringRaw(): String {
            expect('"')
            val sb = StringBuilder()
            while (true) {
                if (atEnd()) throw JsonException("Unterminated string")
                val c = text[pos]
                if (c == '"') { pos++; break }
                if (c == '\\') {
                    pos++
                    if (atEnd()) throw JsonException("Unterminated escape sequence")
                    when (val esc = text[pos]) {
                        '"' -> sb.append('"')
                        '\\' -> sb.append('\\')
                        '/' -> sb.append('/')
                        'n' -> sb.append('\n')
                        't' -> sb.append('\t')
                        'r' -> sb.append('\r')
                        'b' -> sb.append('\b')
                        'u' -> {
                            val hex = text.substring(pos + 1, pos + 5)
                            sb.append(hex.toInt(16).toChar())
                            pos += 4
                        }
                        else -> throw JsonException("Unknown escape sequence \\$esc")
                    }
                    pos++
                } else {
                    sb.append(c)
                    pos++
                }
            }
            return sb.toString()
        }

        fun parseBool(): JsonValue.JsonBool {
            return if (text.startsWith("true", pos)) {
                pos += 4; JsonValue.JsonBool(true)
            } else if (text.startsWith("false", pos)) {
                pos += 5; JsonValue.JsonBool(false)
            } else throw JsonException("Invalid literal at position $pos")
        }

        fun parseNull(): JsonValue {
            if (text.startsWith("null", pos)) { pos += 4; return JsonValue.JsonNull }
            throw JsonException("Invalid literal at position $pos")
        }

        fun parseNumber(): JsonValue.JsonNumber {
            val start = pos
            if (peek() == '-') pos++
            while (!atEnd() && text[pos].isDigit()) pos++
            if (!atEnd() && text[pos] == '.') {
                pos++
                while (!atEnd() && text[pos].isDigit()) pos++
            }
            if (!atEnd() && (text[pos] == 'e' || text[pos] == 'E')) {
                pos++
                if (!atEnd() && (text[pos] == '+' || text[pos] == '-')) pos++
                while (!atEnd() && text[pos].isDigit()) pos++
            }
            if (pos == start) throw JsonException("Invalid number at position $pos")
            return JsonValue.JsonNumber(text.substring(start, pos).toDouble())
        }
    }
}
