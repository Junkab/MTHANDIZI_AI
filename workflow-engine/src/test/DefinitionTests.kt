package mthandizi.workflow.test

import mthandizi.workflow.*
import java.io.File

/** Loads the real JSON files from services/ - not inline test strings. If
 *  these fail to parse, it means the actual files the app would ship are
 *  broken, which is exactly what this needs to catch. */
object RealServices {
    private fun load(name: String): ServiceDefinition {
        val file = File("services/$name.json")
        check(file.exists()) { "Missing services/$name.json - run from workflow-engine/ root" }
        return ServiceDefinition.fromJsonString(file.readText())
    }

    val birthRegistration by lazy { load("birth_registration") }
    val hospitalQueue by lazy { load("hospital_queue") }
    val nationalId by lazy { load("national_id") }
    val immigration by lazy { load("immigration") }
}

fun definitionLoadingTests() {
    println("\n-- Loading the four real service definitions --")

    Check.test("birth_registration.json loads with 7 slots, father_name optional") {
        val svc = RealServices.birthRegistration
        Check.assertEquals("BIRTH_REGISTRATION", svc.id)
        Check.assertEquals(7, svc.slots.size)
        val father = svc.slots.find { it.id == "father_name" }
        Check.assertTrue(father != null, "father_name slot must exist")
        Check.assertFalse(father!!.required, "father_name must be optional")
        val mother = svc.slots.find { it.id == "mother_name" }
        Check.assertTrue(mother!!.required, "mother_name must be required")
    }

    Check.test("hospital_queue.json loads with 5 slots, contact_phone optional") {
        val svc = RealServices.hospitalQueue
        Check.assertEquals("HOSPITAL_QUEUE", svc.id)
        Check.assertEquals(5, svc.slots.size)
        val phone = svc.slots.find { it.id == "contact_phone" }
        Check.assertFalse(phone!!.required)
    }

    Check.test("national_id.json loads with 5 slots and a 3-choice reason") {
        val svc = RealServices.nationalId
        Check.assertEquals("NATIONAL_ID", svc.id)
        Check.assertEquals(5, svc.slots.size)
        val reason = svc.slots.find { it.id == "reason" }
        Check.assertEquals(listOf("NEW", "LOST", "DAMAGED"), reason!!.choices)
    }

    Check.test("immigration.json loads with 5 slots and a 2-choice doc_type") {
        val svc = RealServices.immigration
        Check.assertEquals("IMMIGRATION", svc.id)
        Check.assertEquals(5, svc.slots.size)
        val docType = svc.slots.find { it.id == "doc_type" }
        Check.assertEquals(listOf("NEW", "RENEWAL"), docType!!.choices)
    }

    Check.test("all four services have unique reference prefixes") {
        val prefixes = listOf(
            RealServices.birthRegistration, RealServices.hospitalQueue,
            RealServices.nationalId, RealServices.immigration
        ).map { it.referencePrefix }
        Check.assertEquals(4, prefixes.toSet().size)
    }
}
