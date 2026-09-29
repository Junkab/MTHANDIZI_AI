package mthandizi.workflow.test

fun main() {
    println("MTHANDIZI Workflow Engine - Test Suite")
    println("=".repeat(60))

    jsonTests()
    definitionLoadingTests()
    validationTests()
    engineTests()

    val ok = Check.summary()
    if (!ok) kotlin.system.exitProcess(1)
}
