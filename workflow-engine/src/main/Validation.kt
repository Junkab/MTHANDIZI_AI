package mthandizi.workflow

/**
 * Deterministic, semantic validation of a value already ACCEPTED by whatever
 * upstream recognition layer produced it.
 *
 * WHY THIS EXISTS AS A SEPARATE STEP FROM SPEECH-LAYER ACCEPTANCE
 * -------------------------------------------------------------------
 * The build prompt's non-negotiable principle: "the AI layer only ever fills
 * in a form. It never decides what's valid." A speech/matcher layer (proven
 * in Python, Phase 0) accepting a transcript as matching some candidate
 * answer is necessary but not sufficient - the matcher for a DATE slot, say,
 * might correctly resolve spoken digits into "31/02/2024", a value that is
 * syntactically fine but not a real calendar date. This engine is the final,
 * deterministic authority on whether an accepted value is actually usable,
 * and it has zero speech dependencies - it operates purely on strings.
 */
sealed class ValidationResult {
    object Valid : ValidationResult()
    data class Invalid(val reason: String) : ValidationResult()
}

object Validation {
    fun validate(slot: SlotDefinition, value: String): ValidationResult {
        if (value.isBlank()) {
            return ValidationResult.Invalid("empty value for required slot '${slot.id}'")
        }
        return when (slot.type) {
            SlotType.CLOSED_SET -> validateClosedSet(slot, value)
            SlotType.DATE -> validateDate(value)
            SlotType.NUMBER -> validateNumber(value)
            SlotType.OPEN_NAME -> validateName(value)
            SlotType.FREE_TEXT -> ValidationResult.Valid  // anything non-blank is acceptable
        }
    }

    private fun validateClosedSet(slot: SlotDefinition, value: String): ValidationResult {
        return if (value in slot.choices) ValidationResult.Valid
        else ValidationResult.Invalid(
            "'$value' is not one of the valid choices for '${slot.id}': ${slot.choices}"
        )
    }

    /** Expects "YYYY-MM-DD". Rejects impossible dates (31/02, month 13, etc.),
     *  not just malformed strings - this is the whole point of this function. */
    private fun validateDate(value: String): ValidationResult {
        val parts = value.split("-")
        if (parts.size != 3) {
            return ValidationResult.Invalid("date must be YYYY-MM-DD, got '$value'")
        }
        val (yearStr, monthStr, dayStr) = parts
        val year = yearStr.toIntOrNull()
        val month = monthStr.toIntOrNull()
        val day = dayStr.toIntOrNull()
        if (year == null || month == null || day == null) {
            return ValidationResult.Invalid("date components must be numeric, got '$value'")
        }
        if (year < 1900 || year > 2100) {
            return ValidationResult.Invalid("year $year out of plausible range")
        }
        if (month < 1 || month > 12) {
            return ValidationResult.Invalid("month $month is not 1-12")
        }
        val daysInMonth = daysInMonth(year, month)
        if (day < 1 || day > daysInMonth) {
            return ValidationResult.Invalid(
                "day $day is not valid for month $month/$year (max $daysInMonth)"
            )
        }
        return ValidationResult.Valid
    }

    private fun daysInMonth(year: Int, month: Int): Int {
        val isLeap = (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0)
        return when (month) {
            1, 3, 5, 7, 8, 10, 12 -> 31
            4, 6, 9, 11 -> 30
            2 -> if (isLeap) 29 else 28
            else -> throw IllegalArgumentException("month $month out of range")
        }
    }

    private fun validateNumber(value: String): ValidationResult {
        return if (value.toDoubleOrNull() != null) ValidationResult.Valid
        else ValidationResult.Invalid("'$value' is not a number")
    }

    /** Deliberately permissive - see Section 4.4 of the build prompt: names
     *  are never trusted to ASR alone and are always confirmed on-screen
     *  before reaching this validator, so by the time a name arrives here it
     *  has already been through a human confirmation step. This function
     *  only guards against truly degenerate input (empty, pure punctuation). */
    private fun validateName(value: String): ValidationResult {
        val hasLetter = value.any { it.isLetter() }
        return if (hasLetter) ValidationResult.Valid
        else ValidationResult.Invalid("'$value' contains no letters - not a plausible name")
    }
}
