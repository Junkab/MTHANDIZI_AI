package mthandizi.workflow

/**
 * What kind of answer a slot expects. This drives BOTH how the upstream
 * speech layer should constrain recognition (Section 4 of the build prompt -
 * never ask an open question you then have to parse) AND how this engine
 * validates a value before accepting it as filled.
 */
enum class SlotType {
    CLOSED_SET,   // a fixed list of valid keys (yes/no, district, month, a reason code)
    OPEN_NAME,    // a person's name - never trusted from speech alone, always confirmed
    NUMBER,
    DATE,         // day/month/year, validated as a real calendar date
    FREE_TEXT,    // anything else (a reason for a visit, an address)
}

data class SlotDefinition(
    val id: String,
    val type: SlotType,
    val required: Boolean,
    val label: String,               // for review/PDF display - the Chichewa text lives in
                                      // the language pack (a separate project); this is just
                                      // an identifying label for this engine's own output
    val choices: List<String> = emptyList(),   // valid keys, only meaningful for CLOSED_SET
) {
    companion object {
        fun fromJson(json: JsonValue.JsonObject): SlotDefinition {
            val typeStr = json.string("type")
            val type = SlotType.entries.find { it.name == typeStr }
                ?: throw JsonException("Unknown slot type '$typeStr' for slot '${json.stringOrNull("id")}'")
            val choices = json.arrayOrEmpty("choices").map {
                (it as? JsonValue.JsonString)?.value
                    ?: throw JsonException("choices must be strings")
            }
            if (type == SlotType.CLOSED_SET && choices.isEmpty()) {
                throw JsonException("Slot '${json.string("id")}' is CLOSED_SET but has no choices")
            }
            return SlotDefinition(
                id = json.string("id"),
                type = type,
                required = json.bool("required", default = true),
                label = json.string("label"),
                choices = choices,
            )
        }
    }
}

data class ServiceDefinition(
    val id: String,
    val referencePrefix: String,
    val slots: List<SlotDefinition>,
) {
    init {
        require(slots.isNotEmpty()) { "Service '$id' has no slots" }
        val ids = slots.map { it.id }
        require(ids.size == ids.toSet().size) { "Service '$id' has duplicate slot ids: $ids" }
    }

    companion object {
        fun fromJson(json: JsonValue.JsonObject): ServiceDefinition {
            val slots = json.array("slots").map {
                SlotDefinition.fromJson(it as? JsonValue.JsonObject
                    ?: throw JsonException("Each slot must be an object"))
            }
            return ServiceDefinition(
                id = json.string("id"),
                referencePrefix = json.string("referencePrefix"),
                slots = slots,
            )
        }

        fun fromJsonString(text: String): ServiceDefinition =
            fromJson(Json.parse(text) as? JsonValue.JsonObject
                ?: throw JsonException("Service definition root must be an object"))
    }
}
