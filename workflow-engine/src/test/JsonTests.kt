package mthandizi.workflow.test

import mthandizi.workflow.Json
import mthandizi.workflow.JsonValue
import mthandizi.workflow.JsonException

fun jsonTests() {
    println("\n-- Json parser --")

    Check.test("parses an empty object") {
        val result = Json.parse("{}")
        Check.assertTrue(result is JsonValue.JsonObject)
        Check.assertEquals(0, (result as JsonValue.JsonObject).entries.size)
    }

    Check.test("parses strings, numbers, booleans, null") {
        val obj = Json.parse("""{"a":"hello","b":42,"c":true,"d":false,"e":null}""") as JsonValue.JsonObject
        Check.assertEquals("hello", obj.string("a"))
        Check.assertEquals(42.0, (obj["b"] as JsonValue.JsonNumber).value)
        Check.assertEquals(true, (obj["c"] as JsonValue.JsonBool).value)
        Check.assertEquals(false, (obj["d"] as JsonValue.JsonBool).value)
        Check.assertTrue(obj["e"] is JsonValue.JsonNull)
    }

    Check.test("parses nested objects and arrays") {
        val obj = Json.parse("""{"items":[{"id":"a"},{"id":"b"}]}""") as JsonValue.JsonObject
        val items = obj.array("items")
        Check.assertEquals(2, items.size)
        Check.assertEquals("a", (items[0] as JsonValue.JsonObject).string("id"))
        Check.assertEquals("b", (items[1] as JsonValue.JsonObject).string("id"))
    }

    Check.test("handles escaped characters in strings") {
        val obj = Json.parse("""{"text":"line1\nline2\ttabbed\"quoted\""}""") as JsonValue.JsonObject
        Check.assertEquals("line1\nline2\ttabbed\"quoted\"", obj.string("text"))
    }

    Check.test("handles negative and decimal numbers") {
        val obj = Json.parse("""{"a":-5,"b":3.14,"c":-2.5e3}""") as JsonValue.JsonObject
        Check.assertEquals(-5.0, (obj["a"] as JsonValue.JsonNumber).value)
        Check.assertEquals(3.14, (obj["b"] as JsonValue.JsonNumber).value)
        Check.assertEquals(-2500.0, (obj["c"] as JsonValue.JsonNumber).value)
    }

    Check.test("rejects malformed JSON rather than silently returning something wrong") {
        Check.assertThrows { Json.parse("{not valid") }
        Check.assertThrows { Json.parse("""{"a":}""") }
        Check.assertThrows { Json.parse("") }
    }

    Check.test("rejects trailing content after a valid value") {
        Check.assertThrows { Json.parse("""{"a":1} garbage""") }
    }

    Check.test("whitespace between tokens is tolerated") {
        val obj = Json.parse("""
            {
                "a" : 1 ,
                "b" : [ 1 , 2 , 3 ]
            }
        """.trimIndent()) as JsonValue.JsonObject
        Check.assertEquals(1.0, (obj["a"] as JsonValue.JsonNumber).value)
        Check.assertEquals(3, obj.array("b").size)
    }
}
