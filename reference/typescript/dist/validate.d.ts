import { z } from "zod";
import { ParsedEvent } from "./types.js";
export type ValidationResult = {
    success: true;
    data: ParsedEvent;
} | {
    success: false;
    error: z.ZodError;
};
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
export declare function validate(raw: unknown): ValidationResult;
/**
 * validateOrThrow is a convenience wrapper around validate() that throws on
 * validation failure instead of returning a result object.
 *
 * @param raw - The unknown value to validate.
 * @throws {z.ZodError} if validation fails.
 */
export declare function validateOrThrow(raw: unknown): ParsedEvent;
//# sourceMappingURL=validate.d.ts.map