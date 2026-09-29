package mthandizi.workflow

/**
 * MTHANDIZI Workflow Engine.
 *
 * THE NON-NEGOTIABLE PRINCIPLE THIS FILE EXISTS TO ENFORCE
 * ------------------------------------------------------------
 * "The AI layer (speech recognition -> intent classification -> entity
 * extraction) only ever fills in a form. It never decides what fields exist,
 * what's valid, or what happens next... A low-confidence or wrong
 * transcription can trigger a re-ask; it can never corrupt a workflow, skip a
 * required field, or invent a government requirement."
 *
 * This class has ZERO speech dependencies - no import of anything from
 * speech-lab or speech-service. It is unit-testable, and IS unit-tested (see
 * WorkflowEngineTests.kt), driven purely by (value: String?, accepted:
 * Boolean) tuples, exactly as the build prompt specifies. Whatever produced
 * those tuples - a real ASR model, a touch keypad, a test harness typing
 * strings directly - is irrelevant to this class and always will be.
 */

sealed class AttemptOutcome {
    /** Slot filled successfully. nextSlotId is null if the whole service is now complete. */
    data class Advanced(val nextSlotId: String?) : AttemptOutcome()
    /** Rejected or invalid; try again. attemptNumber counts from 1. */
    data class ReAsk(val attemptNumber: Int) : AttemptOutcome()
    /** Three failed attempts on this slot - switch this slot's input mode to touch. */
    object EscalateToTouch : AttemptOutcome()
    /** A non-required slot was explicitly skipped. */
    object Skipped : AttemptOutcome()
    /** submitAttempt() or skip() called after the workflow was already complete. */
    object AlreadyComplete : AttemptOutcome()
}

enum class InputMode { SPEECH, TOUCH }

class WorkflowEngine(val service: ServiceDefinition) {
    private var currentIndex = 0
    private val filled = LinkedHashMap<String, String>()   // insertion order == review order
    private val attempts = HashMap<String, Int>()
    private val touchRequired = HashSet<String>()
    private val history = mutableListOf<Int>()

    fun currentSlot(): SlotDefinition? = service.slots.getOrNull(currentIndex)
    fun isComplete(): Boolean = currentIndex >= service.slots.size
    fun attemptCountFor(slotId: String): Int = attempts[slotId] ?: 0
    fun inputModeFor(slotId: String): InputMode =
        if (slotId in touchRequired) InputMode.TOUCH else InputMode.SPEECH

    /**
     * Submit one attempt at the current slot.
     *
     * @param value the value the recognition layer (or touch UI) produced, or null on rejection
     * @param accepted whether the upstream layer's own outcome was ACCEPT - a REJECT or
     *   DISAMBIGUATE-not-yet-confirmed from the matcher (Section 4.1-4.3) should be passed
     *   here as accepted=false, which is exactly the boundary this engine enforces: it never
     *   sees or cares WHY something was accepted, only whether it was, and it applies its own
     *   validation regardless (see Validation.kt for why that second check matters).
     */
    fun submitAttempt(value: String?, accepted: Boolean): AttemptOutcome {
        val slot = currentSlot() ?: return AttemptOutcome.AlreadyComplete

        if (!accepted || value == null) {
            return registerFailedAttempt(slot)
        }

        val validation = Validation.validate(slot, value)
        if (validation is ValidationResult.Invalid) {
            // A value the SPEECH layer accepted can still be semantically invalid (Section on
            // Validation.kt: an accepted date match can still be "31/02/2024"). This engine is
            // the final authority - an accepted-but-invalid value is still a failed attempt.
            return registerFailedAttempt(slot)
        }

        filled[slot.id] = value
        attempts.remove(slot.id)
        history.add(currentIndex)
        currentIndex++
        return AttemptOutcome.Advanced(currentSlot()?.id)
    }

    private fun registerFailedAttempt(slot: SlotDefinition): AttemptOutcome {
        val count = (attempts[slot.id] ?: 0) + 1
        attempts[slot.id] = count

        if (slot.id in touchRequired) {
            // Already escalated - a touch-mode failure (e.g. an impossible typed date) just
            // re-asks. No further escalation needed; there's nowhere further to escalate to.
            return AttemptOutcome.ReAsk(count)
        }
        return if (count >= 3) {
            touchRequired.add(slot.id)
            AttemptOutcome.EscalateToTouch
        } else {
            AttemptOutcome.ReAsk(count)
        }
    }

    /** Only valid for non-required slots - throws otherwise, deliberately loud rather than
     *  silently ignoring an attempt to skip something mandatory. */
    fun skip(): AttemptOutcome {
        val slot = currentSlot() ?: return AttemptOutcome.AlreadyComplete
        check(!slot.required) { "Cannot skip required slot '${slot.id}'" }
        filled.remove(slot.id)
        attempts.remove(slot.id)
        history.add(currentIndex)
        currentIndex++
        return AttemptOutcome.Skipped
    }

    /** Move to the previous slot. The old value (if any) is kept in place - the caller (UI
     *  layer) decides whether to show it as a pre-filled suggestion or ask fresh; this engine
     *  doesn't presume either way. Attempt counts are reset for BOTH the slot being abandoned
     *  (any in-progress failed attempts on it are moot now) and the slot being returned to
     *  (a fresh start), since goBack conceptually restarts the forward journey from that point. */
    fun goBack(): Boolean {
        if (history.isEmpty()) return false
        val abandonedSlotId = currentSlot()?.id
        currentIndex = history.removeAt(history.size - 1)
        abandonedSlotId?.let { attempts.remove(it) }
        attempts.remove(currentSlot()?.id)
        return true
    }

    /** Ordered (slot, filled-value-or-null) pairs for a review screen. */
    fun reviewList(): List<Pair<SlotDefinition, String?>> =
        service.slots.map { it to filled[it.id] }

    /** Fast single-field correction from the review screen, without re-walking the whole
     *  flow (Section 5's "fix only this one field" path). Re-validates before accepting. */
    fun editField(slotId: String, newValue: String): ValidationResult {
        val slot = service.slots.find { it.id == slotId }
            ?: throw IllegalArgumentException("Unknown slot '$slotId' for service '${service.id}'")
        val result = Validation.validate(slot, newValue)
        if (result is ValidationResult.Valid) {
            filled[slotId] = newValue
        }
        return result
    }

    /** A first-draft reference-number scheme for Phase 3 testing purposes only. Real
     *  generation (persisted counters, collision-proofing) is Phase 10 territory - this
     *  exists so submission tests have something concrete to assert on. */
    fun referenceNumber(): String {
        check(isComplete()) { "Cannot generate a reference number before the workflow is complete" }
        val hash = filled.entries.joinToString("|") { "${it.key}=${it.value}" }.hashCode()
        val suffix = (kotlin.math.abs(hash) % 1_000_000).toString().padStart(6, '0')
        return "${service.referencePrefix}-$suffix"
    }
}
