package mthandizi.workflow.test

import mthandizi.workflow.*

fun engineTests() {
    println("\n-- WorkflowEngine: core behaviour --")

    Check.test("happy path: every slot accepted first try completes the workflow") {
        val engine = WorkflowEngine(RealServices.hospitalQueue)
        val outcome1 = engine.submitAttempt("Grace Banda", accepted = true)
        Check.assertTrue(outcome1 is AttemptOutcome.Advanced)
        engine.submitAttempt("2005-06-12", accepted = true)
        engine.submitAttempt("Stomach pain", accepted = true)
        engine.submitAttempt("General", accepted = true)
        val last = engine.submitAttempt("0991234567", accepted = true)
        Check.assertTrue(engine.isComplete())
        Check.assertTrue((last as AttemptOutcome.Advanced).nextSlotId == null)
        Check.assertTrue(engine.referenceNumber().startsWith("HQ-"))
    }

    Check.test("submitAttempt after completion returns AlreadyComplete, not a crash") {
        val engine = WorkflowEngine(RealServices.hospitalQueue)
        repeat(5) { engine.submitAttempt("x", accepted = true) }
        // patient_dob and department slots need valid values to actually advance;
        // use a minimal single-slot service instead for a clean AlreadyComplete check
        val tiny = ServiceDefinition("TINY", "TN", listOf(
            SlotDefinition("only", SlotType.FREE_TEXT, required = true, label = "Only field")
        ))
        val e2 = WorkflowEngine(tiny)
        e2.submitAttempt("done", accepted = true)
        Check.assertTrue(e2.isComplete())
        Check.assertTrue(e2.submitAttempt("anything", accepted = true) is AttemptOutcome.AlreadyComplete)
    }

    // --- the optional-father-name skip path -----------------------------------------------

    Check.test("optional father_name can be skipped, workflow still completes") {
        val engine = WorkflowEngine(RealServices.birthRegistration)
        engine.submitAttempt("Chikondi Phiri", accepted = true)    // child_name
        engine.submitAttempt("2024-03-10", accepted = true)         // child_dob
        engine.submitAttempt("Kamuzu Central Hospital", accepted = true)  // birth_place
        engine.submitAttempt("Grace Phiri", accepted = true)        // mother_name
        Check.assertEquals("father_name", engine.currentSlot()?.id)
        val skipOutcome = engine.skip()                              // father_name - optional
        Check.assertTrue(skipOutcome is AttemptOutcome.Skipped)
        Check.assertEquals("village", engine.currentSlot()?.id)
        engine.submitAttempt("Chilinde", accepted = true)            // village
        engine.submitAttempt("Lilongwe", accepted = true)            // district
        Check.assertTrue(engine.isComplete())
        val review = engine.reviewList()
        val fatherEntry = review.find { it.first.id == "father_name" }
        Check.assertTrue(fatherEntry!!.second == null, "skipped field should have no value")
    }

    Check.test("attempting to skip a REQUIRED slot throws rather than silently succeeding") {
        val engine = WorkflowEngine(RealServices.birthRegistration)
        // currentSlot is child_name, which IS required
        Check.assertThrows("skipping a required slot must be rejected loudly") {
            engine.skip()
        }
    }

    // --- invalid dates: accepted by the matcher, still rejected by validation --------------

    Check.test("a matcher-accepted but calendar-invalid date does NOT advance the workflow") {
        val engine = WorkflowEngine(RealServices.hospitalQueue)
        engine.submitAttempt("Grace Banda", accepted = true)   // patient_name - fine
        val stillOnDob = engine.submitAttempt("2024-02-30", accepted = true)  // accepted=true but impossible date
        Check.assertTrue(stillOnDob is AttemptOutcome.ReAsk,
            "an accepted-but-invalid date must be treated as a failed attempt, not silently corrupt the record")
        Check.assertEquals("patient_dob", engine.currentSlot()?.id,
            "engine must still be sitting on patient_dob, not have advanced past it")
    }

    Check.test("a matcher REJECT (accepted=false) is a failed attempt regardless of value") {
        val engine = WorkflowEngine(RealServices.hospitalQueue)
        val outcome = engine.submitAttempt("garbled nonsense", accepted = false)
        Check.assertTrue(outcome is AttemptOutcome.ReAsk)
        Check.assertEquals("patient_name", engine.currentSlot()?.id)
    }

    // --- three-strike escalation to touch ---------------------------------------------------

    Check.test("three consecutive failures escalate to touch on the third") {
        val engine = WorkflowEngine(RealServices.nationalId)
        Check.assertEquals(InputMode.SPEECH, engine.inputModeFor("name"))
        val a1 = engine.submitAttempt(null, accepted = false)
        Check.assertTrue(a1 is AttemptOutcome.ReAsk && a1.attemptNumber == 1)
        val a2 = engine.submitAttempt(null, accepted = false)
        Check.assertTrue(a2 is AttemptOutcome.ReAsk && a2.attemptNumber == 2)
        val a3 = engine.submitAttempt(null, accepted = false)
        Check.assertTrue(a3 is AttemptOutcome.EscalateToTouch, "third failure must escalate")
        Check.assertEquals(InputMode.TOUCH, engine.inputModeFor("name"))
    }

    Check.test("after escalation, further failures keep re-asking rather than escalating again") {
        val engine = WorkflowEngine(RealServices.nationalId)
        repeat(3) { engine.submitAttempt(null, accepted = false) }
        Check.assertEquals(InputMode.TOUCH, engine.inputModeFor("name"))
        val fourth = engine.submitAttempt(null, accepted = false)
        Check.assertTrue(fourth is AttemptOutcome.ReAsk, "no such outcome as escalating twice")
    }

    Check.test("a successful attempt after escalation still advances normally") {
        val engine = WorkflowEngine(RealServices.nationalId)
        repeat(3) { engine.submitAttempt(null, accepted = false) }
        Check.assertEquals(InputMode.TOUCH, engine.inputModeFor("name"))
        val success = engine.submitAttempt("Mathews Dube", accepted = true)  // typed via touch keypad
        Check.assertTrue(success is AttemptOutcome.Advanced)
        Check.assertEquals("dob", engine.currentSlot()?.id)
    }

    Check.test("a citizen NEVER gets stuck - every slot has a path forward (Section 4.5)") {
        // Simulate the worst case on every slot of every service: three rejects, then
        // one touch-provided value. The workflow must always complete.
        for (service in listOf(
            RealServices.birthRegistration, RealServices.hospitalQueue,
            RealServices.nationalId, RealServices.immigration,
        )) {
            val engine = WorkflowEngine(service)
            var guard = 0
            while (!engine.isComplete() && guard < 100) {
                guard++
                val slot = engine.currentSlot()!!
                repeat(3) { engine.submitAttempt(null, accepted = false) }
                val touchValue = when (slot.type) {
                    SlotType.DATE -> "2000-01-01"
                    SlotType.CLOSED_SET -> slot.choices.first()
                    SlotType.NUMBER -> "1"
                    SlotType.OPEN_NAME, SlotType.FREE_TEXT -> "test value"
                }
                engine.submitAttempt(touchValue, accepted = true)
            }
            Check.assertTrue(engine.isComplete(), "${service.id} must reach completion, guard=$guard")
        }
    }

    // --- back navigation --------------------------------------------------------------------

    Check.test("goBack returns to the previous slot and resets its attempt count") {
        val engine = WorkflowEngine(RealServices.immigration)
        engine.submitAttempt("Mathews Dube", accepted = true)   // name
        engine.submitAttempt(null, accepted = false)             // dob: one failed attempt
        Check.assertEquals(1, engine.attemptCountFor("dob"))
        val went = engine.goBack()
        Check.assertTrue(went)
        Check.assertEquals("name", engine.currentSlot()?.id, "should be back on the previous slot")
        // going forward again and reaching dob should have a clean attempt count
        engine.submitAttempt("Mathews Dube", accepted = true)
        Check.assertEquals(0, engine.attemptCountFor("dob"), "attempt count must reset after going back")
    }

    Check.test("goBack at the very start of a workflow returns false, doesn't crash") {
        val engine = WorkflowEngine(RealServices.immigration)
        Check.assertFalse(engine.goBack())
        Check.assertEquals("name", engine.currentSlot()?.id, "must still be on the first slot")
    }

    Check.test("goBack after multiple advances walks back one step at a time") {
        val engine = WorkflowEngine(RealServices.immigration)
        engine.submitAttempt("A", accepted = true)   // name
        engine.submitAttempt("2000-01-01", accepted = true)  // dob
        engine.submitAttempt("Malawian", accepted = true)  // nationality
        Check.assertEquals("doc_type", engine.currentSlot()?.id)
        engine.goBack()
        Check.assertEquals("nationality", engine.currentSlot()?.id)
        engine.goBack()
        Check.assertEquals("dob", engine.currentSlot()?.id)
    }

    // --- review and edit --------------------------------------------------------------------

    Check.test("editField updates a filled value without re-walking the flow") {
        val engine = WorkflowEngine(RealServices.nationalId)
        engine.submitAttempt("Mathews Dube", accepted = true)
        engine.submitAttempt("2000-01-01", accepted = true)
        engine.submitAttempt("Lilongwe", accepted = true)
        engine.submitAttempt("Area 25", accepted = true)
        engine.submitAttempt("LOST", accepted = true)
        Check.assertTrue(engine.isComplete())
        val result = engine.editField("reason", "DAMAGED")
        Check.assertTrue(result is ValidationResult.Valid)
        val entry = engine.reviewList().find { it.first.id == "reason" }
        Check.assertEquals("DAMAGED", entry!!.second)
    }

    Check.test("editField rejects an invalid replacement and leaves the old value in place") {
        val engine = WorkflowEngine(RealServices.nationalId)
        engine.submitAttempt("Mathews Dube", accepted = true)
        engine.submitAttempt("2000-01-01", accepted = true)
        engine.submitAttempt("Lilongwe", accepted = true)
        engine.submitAttempt("Area 25", accepted = true)
        engine.submitAttempt("LOST", accepted = true)
        val result = engine.editField("reason", "NOT_A_REAL_CHOICE")
        Check.assertTrue(result is ValidationResult.Invalid)
        val entry = engine.reviewList().find { it.first.id == "reason" }
        Check.assertEquals("LOST", entry!!.second, "invalid edit must not overwrite the valid old value")
    }

    // --- proving the "add a service = config only" architectural claim ----------------------

    Check.test("a brand-new fifth service works with ZERO engine code changes - config only") {
        // This is not one of the four real files - it's a throwaway definition written
        // entirely as a JSON string, to prove the engine has no per-service logic anywhere.
        val json = """
            {
              "id": "LAND_INFO",
              "referencePrefix": "LI",
              "slots": [
                { "id": "plot_number", "type": "FREE_TEXT", "required": true, "label": "Plot number" },
                { "id": "district", "type": "CLOSED_SET", "required": true, "label": "District",
                  "choices": ["Lilongwe", "Blantyre"] }
              ]
            }
        """.trimIndent()
        val service = ServiceDefinition.fromJsonString(json)
        val engine = WorkflowEngine(service)
        engine.submitAttempt("Plot 42", accepted = true)
        engine.submitAttempt("Blantyre", accepted = true)
        Check.assertTrue(engine.isComplete())
        Check.assertTrue(engine.referenceNumber().startsWith("LI-"))
    }
}
