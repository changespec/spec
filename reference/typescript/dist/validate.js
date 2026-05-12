"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.validate = validate;
exports.validateOrThrow = validateOrThrow;
const zod_1 = require("zod");
const types_js_1 = require("./types.js");
// DANGEROUS_KEYS are object property names that can cause prototype pollution
// if merged into objects via Object.assign or similar patterns.
const DANGEROUS_KEYS = new Set(["__proto__", "constructor", "prototype"]);
/**
 * validate parses and validates an unknown value as a ChangeSpec 1.0 event.
 *
 * Returns a ValidationResult discriminated union. On success, result.data is
 * the typed ParsedEvent with extension fields separated into result.data.extensions.
 * On failure, result.error is a Zod error with field-level detail.
 *
 * Extension fields (keys beginning with "ext:") are collected into the
 * `extensions` property and removed from the core event object before schema
 * validation. Unknown non-extension fields are rejected per the strict schema
 * (additionalProperties: false per Section 10).
 *
 * Prototype-polluting keys (__proto__, constructor, prototype) are rejected
 * even when they carry the ext: prefix.
 *
 * @param raw - The unknown value to validate (typically a parsed JSON object).
 */
function validate(raw) {
    // Guard: must be a plain object.
    if (typeof raw !== "object" || raw === null || Array.isArray(raw)) {
        return {
            success: false,
            error: new zod_1.z.ZodError([
                {
                    code: "custom",
                    path: [],
                    message: "Input must be a plain JSON object",
                },
            ]),
        };
    }
    const rawObj = raw;
    // Separate extension fields from core fields before schema validation.
    // This allows the strict schema to reject unknown non-ext fields while
    // still passing ext:* fields through to the consumer.
    const extensions = {};
    const coreInput = {};
    for (const [key, value] of Object.entries(rawObj)) {
        // Reject prototype-polluting keys outright.
        if (DANGEROUS_KEYS.has(key)) {
            return {
                success: false,
                error: new zod_1.z.ZodError([
                    {
                        code: "custom",
                        path: [key],
                        message: `Key "${key}" is not permitted (prototype pollution risk)`,
                    },
                ]),
            };
        }
        if ((0, types_js_1.isExtKey)(key)) {
            extensions[key] = value;
        }
        else {
            coreInput[key] = value;
        }
    }
    // Validate the core fields using the strict schema.
    // The strict schema rejects any non-ext keys not defined in the spec.
    const result = types_js_1.EventSchema.safeParse(coreInput);
    if (!result.success) {
        return { success: false, error: result.error };
    }
    const event = {
        ...result.data,
        extensions,
    };
    return { success: true, data: event };
}
/**
 * validateOrThrow is a convenience wrapper around validate() that throws on
 * validation failure instead of returning a result object.
 *
 * @param raw - The unknown value to validate.
 * @throws {z.ZodError} if validation fails.
 */
function validateOrThrow(raw) {
    const result = validate(raw);
    if (!result.success) {
        throw result.error;
    }
    return result.data;
}
//# sourceMappingURL=validate.js.map