package mthandizi.workflow.test

/**
 * A minimal test runner. No JUnit - same reason as Json.kt: Maven Central is
 * unreachable from this environment (confirmed 403), and code that can't be
 * proven to compile and run has no place in this project's evidence trail.
 * This is deliberately boring: register named test blocks, run them all,
 * print PASS/FAIL, exit non-zero if anything failed - enough to give the
 * same kind of real, checkable signal pytest has given every other phase.
 */
object Check {
    private var passed = 0
    private var failed = 0
    private val failures = mutableListOf<String>()

    fun test(name: String, block: () -> Unit) {
        try {
            block()
            passed++
            println("  PASS  $name")
        } catch (e: Throwable) {
            failed++
            failures.add("$name -> ${e.message}")
            println("  FAIL  $name -> ${e.message}")
        }
    }

    fun <T> assertEquals(expected: T, actual: T, msg: String = "") {
        if (expected != actual) {
            throw AssertionError("expected <$expected> but was <$actual> $msg")
        }
    }

    fun assertTrue(condition: Boolean, msg: String = "") {
        if (!condition) throw AssertionError("expected true $msg")
    }

    fun assertFalse(condition: Boolean, msg: String = "") {
        if (condition) throw AssertionError("expected false $msg")
    }

    fun assertThrows(msg: String = "", block: () -> Unit) {
        try {
            block()
        } catch (e: Throwable) {
            return  // expected
        }
        throw AssertionError("expected an exception to be thrown $msg")
    }

    fun summary(): Boolean {
        println("\n${"=".repeat(60)}")
        println("$passed passed, $failed failed")
        if (failures.isNotEmpty()) {
            println("\nFailures:")
            failures.forEach { println("  - $it") }
        }
        return failed == 0
    }
}
