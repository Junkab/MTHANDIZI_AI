package mthandizi.workflow.test

import mthandizi.workflow.*

fun validationTests() {
    println("\n-- Validation --")

    val dateSlot = SlotDefinition("d", SlotType.DATE, required = true, label = "Date")
    val closedSlot = SlotDefinition("c", SlotType.CLOSED_SET, required = true, label = "Choice",
        choices = listOf("A", "B", "C"))
    val nameSlot = SlotDefinition("n", SlotType.OPEN_NAME, required = true, label = "Name")
    val numberSlot = SlotDefinition("num", SlotType.NUMBER, required = true, label = "Number")
    val freeSlot = SlotDefinition("f", SlotType.FREE_TEXT, required = true, label = "Free text")

    Check.test("valid calendar date is accepted") {
        Check.assertTrue(Validation.validate(dateSlot, "2024-03-15") is ValidationResult.Valid)
    }

    Check.test("Feb 30 is rejected - the whole point of semantic date validation") {
        val result = Validation.validate(dateSlot, "2024-02-30")
        Check.assertTrue(result is ValidationResult.Invalid)
    }

    Check.test("month 13 is rejected") {
        Check.assertTrue(Validation.validate(dateSlot, "2024-13-01") is ValidationResult.Invalid)
    }

    Check.test("Feb 29 is valid in a leap year") {
        Check.assertTrue(Validation.validate(dateSlot, "2024-02-29") is ValidationResult.Valid)  // 2024 is leap
    }

    Check.test("Feb 29 is invalid in a non-leap year") {
        Check.assertTrue(Validation.validate(dateSlot, "2023-02-29") is ValidationResult.Invalid)  // 2023 not leap
    }

    Check.test("year 1900 is NOT a leap year despite being divisible by 4 (div by 100, not 400)") {
        Check.assertTrue(Validation.validate(dateSlot, "1900-02-29") is ValidationResult.Invalid)
    }

    Check.test("year 2000 IS a leap year (div by 400)") {
        Check.assertTrue(Validation.validate(dateSlot, "2000-02-29") is ValidationResult.Valid)
    }

    Check.test("malformed date string is rejected") {
        Check.assertTrue(Validation.validate(dateSlot, "not-a-date") is ValidationResult.Invalid)
        Check.assertTrue(Validation.validate(dateSlot, "2024/03/15") is ValidationResult.Invalid)  // wrong separator
    }

    Check.test("closed-set value within choices is valid") {
        Check.assertTrue(Validation.validate(closedSlot, "B") is ValidationResult.Valid)
    }

    Check.test("closed-set value outside choices is invalid") {
        Check.assertTrue(Validation.validate(closedSlot, "Z") is ValidationResult.Invalid)
    }

    Check.test("empty value is always invalid regardless of type") {
        Check.assertTrue(Validation.validate(freeSlot, "") is ValidationResult.Invalid)
        Check.assertTrue(Validation.validate(freeSlot, "   ") is ValidationResult.Invalid)
    }

    Check.test("a name with letters is valid") {
        Check.assertTrue(Validation.validate(nameSlot, "Mathews Dube") is ValidationResult.Valid)
    }

    Check.test("a name that's pure punctuation is rejected") {
        Check.assertTrue(Validation.validate(nameSlot, "!!!") is ValidationResult.Invalid)
    }

    Check.test("numeric slot accepts numbers") {
        Check.assertTrue(Validation.validate(numberSlot, "42") is ValidationResult.Valid)
        Check.assertTrue(Validation.validate(numberSlot, "3.5") is ValidationResult.Valid)
    }

    Check.test("numeric slot rejects non-numbers") {
        Check.assertTrue(Validation.validate(numberSlot, "abc") is ValidationResult.Invalid)
    }

    Check.test("free text accepts anything non-blank") {
        Check.assertTrue(Validation.validate(freeSlot, "Ku mudzi wa Chilinde") is ValidationResult.Valid)
    }
}
