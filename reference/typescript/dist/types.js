"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.EventSchema = exports.SignatureSchema = exports.ReviewerRoleSchema = exports.SourceTypeSchema = exports.SeveritySchema = exports.CategorySchema = exports.SPEC_VERSION = void 0;
exports.isExtKey = isExtKey;
const zod_1 = require("zod");
// SPEC_VERSION is the ChangeSpec version this package implements.
exports.SPEC_VERSION = "1.0";
// DANGEROUS_KEYS are object keys that can cause prototype pollution in
// JavaScript when merged into objects. These are rejected even if they
// carry the ext: prefix, and are filtered out during ext field extraction.
const DANGEROUS_KEYS = new Set(["__proto__", "constructor", "prototype"]);
// --- Enum schemas ---
exports.CategorySchema = zod_1.z.enum([
    "api_breaking",
    "api_deprecation",
    "security",
    "data_handling",
    "liability",
    "pricing",
    "tos",
    "cosmetic",
    "informational",
]);
exports.SeveritySchema = zod_1.z.enum([
    "critical",
    "high",
    "medium",
    "low",
    "informational",
]);
exports.SourceTypeSchema = zod_1.z.enum([
    "publisher_verified",
    "crawled",
    "community",
]);
exports.ReviewerRoleSchema = zod_1.z.enum([
    "engineering",
    "security",
    "legal",
    "compliance",
    "procurement",
    "management",
]);
// --- Signature schema ---
exports.SignatureSchema = zod_1.z.object({
    alg: zod_1.z.literal("ed25519"),
    key_id: zod_1.z.string().regex(/^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$/),
    value: zod_1.z.string().regex(/^[A-Za-z0-9_-]+$/),
    signed_fields: zod_1.z.array(zod_1.z.string()).min(9),
    key_fingerprint: zod_1.z
        .string()
        .regex(/^[A-Za-z0-9_-]{43}$/)
        .optional(),
});
// --- URL validator ---
// source_url and migration_url must use the https:// scheme per Section 1.3.
// Zod's .url() accepts any scheme. We add an explicit https-only check.
const httpsUrl = zod_1.z
    .string()
    .url()
    .max(2048)
    .refine((s) => s.startsWith("https://"), {
    message: "URL must use the https:// scheme",
});
// --- Core event schema ---
//
// The EventSchema uses .strict() to reject unknown non-ext fields, matching
// the canonical schema.json's additionalProperties: false.
//
// Extension fields (ext:*) are handled in validate.ts before this schema is
// applied. Unknown non-ext keys are rejected.
//
// Note: .strict() in Zod rejects all keys not listed in the schema.
// Extension fields (ext:*) are stripped from the input before validation
// and re-attached via the validate() function.
exports.EventSchema = zod_1.z
    .object({
    // Required fields
    specversion: zod_1.z.literal("1.0"),
    id: zod_1.z.string().min(1).max(128),
    vendor_id: zod_1.z.string().min(1).max(256),
    category: exports.CategorySchema,
    severity: exports.SeveritySchema,
    title: zod_1.z
        .string()
        .min(1)
        .max(200)
        .refine((s) => !s.includes("\n") && !s.includes("\r"), {
        message: "title must not contain newlines",
    }),
    summary: zod_1.z.string().min(1).max(2000),
    published_at: zod_1.z.string().datetime({ offset: true }),
    source_type: exports.SourceTypeSchema,
    // Optional fields
    effective_date: zod_1.z.string().date().optional(),
    source_url: httpsUrl.optional(),
    affected_versions: zod_1.z.string().max(256).optional(),
    fixed_in_version: zod_1.z.string().max(64).optional(),
    migration_hint: zod_1.z.string().max(500).optional(),
    migration_url: httpsUrl.optional(),
    confidence_score: zod_1.z.number().min(0).max(1).optional(),
    sunset_date: zod_1.z.string().date().optional(),
    cve_id: zod_1.z
        .string()
        .regex(/^CVE-[0-9]{4}-[0-9]{4,}$/)
        .optional(),
    cvss_score: zod_1.z.number().min(0).max(10).optional(),
    cvss_vector: zod_1.z
        .string()
        .regex(/^CVSS:[0-9]\.[0-9]\//)
        .max(128)
        .optional(),
    affected_systems: zod_1.z
        .array(zod_1.z.string().min(1).max(200))
        .max(50)
        .optional(),
    affected_sections: zod_1.z
        .array(zod_1.z.string().min(1).max(200))
        .max(50)
        .optional(),
    action_required: zod_1.z.boolean().optional(),
    recommended_reviewers: zod_1.z
        .array(exports.ReviewerRoleSchema)
        .max(6)
        .optional(),
    tags: zod_1.z
        .array(zod_1.z
        .string()
        .min(1)
        .max(50)
        .regex(/^[a-z0-9][a-z0-9_-]*$/))
        .max(20)
        .optional(),
    signature: exports.SignatureSchema.optional(),
})
    .strict(); // reject unknown non-ext fields (ext fields are stripped before validation)
// isExtKey returns true if the key is a valid extension field key.
// Valid ext keys start with "ext:" and are not prototype-polluting names.
function isExtKey(key) {
    if (!key.startsWith("ext:"))
        return false;
    // Strip the "ext:" prefix and check the base name.
    const base = key.slice(4);
    return !DANGEROUS_KEYS.has(base) && !DANGEROUS_KEYS.has(key);
}
//# sourceMappingURL=types.js.map