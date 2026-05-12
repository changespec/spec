import { z } from "zod";

// SPEC_VERSION is the ChangeSpec version this package implements.
export const SPEC_VERSION = "1.0" as const;

// DANGEROUS_KEYS are object keys that can cause prototype pollution in
// JavaScript when merged into objects. These are rejected even if they
// carry the ext: prefix, and are filtered out during ext field extraction.
const DANGEROUS_KEYS = new Set(["__proto__", "constructor", "prototype"]);

// --- Enum schemas ---

export const CategorySchema = z.enum([
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

export const SeveritySchema = z.enum([
  "critical",
  "high",
  "medium",
  "low",
  "informational",
]);

export const SourceTypeSchema = z.enum([
  "publisher_verified",
  "crawled",
  "community",
]);

export const ReviewerRoleSchema = z.enum([
  "engineering",
  "security",
  "legal",
  "compliance",
  "procurement",
  "management",
]);

// --- Signature schema ---

export const SignatureSchema = z.object({
  alg: z.literal("ed25519"),
  key_id: z.string().regex(/^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$/),
  value: z.string().regex(/^[A-Za-z0-9_-]+$/),
  signed_fields: z.array(z.string()).min(9),
  key_fingerprint: z
    .string()
    .regex(/^[A-Za-z0-9_-]{43}$/)
    .optional(),
});

// --- URL validator ---
// source_url and migration_url must use the https:// scheme per Section 1.3.
// Zod's .url() accepts any scheme. We add an explicit https-only check.
const httpsUrl = z
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

export const EventSchema = z
  .object({
    // Required fields
    specversion: z.literal("1.0"),
    id: z.string().min(1).max(128),
    vendor_id: z.string().min(1).max(256),
    category: CategorySchema,
    severity: SeveritySchema,
    title: z
      .string()
      .min(1)
      .max(200)
      .refine((s) => !s.includes("\n") && !s.includes("\r"), {
        message: "title must not contain newlines",
      }),
    summary: z.string().min(1).max(2000),
    published_at: z.string().datetime({ offset: true }),
    source_type: SourceTypeSchema,

    // Optional fields
    effective_date: z.string().date().optional(),
    source_url: httpsUrl.optional(),
    affected_versions: z.string().max(256).optional(),
    fixed_in_version: z.string().max(64).optional(),
    migration_hint: z.string().max(500).optional(),
    migration_url: httpsUrl.optional(),
    confidence_score: z.number().min(0).max(1).optional(),
    sunset_date: z.string().date().optional(),
    cve_id: z
      .string()
      .regex(/^CVE-[0-9]{4}-[0-9]{4,}$/)
      .optional(),
    cvss_score: z.number().min(0).max(10).optional(),
    cvss_vector: z
      .string()
      .regex(/^CVSS:[0-9]\.[0-9]\//)
      .max(128)
      .optional(),
    affected_systems: z
      .array(z.string().min(1).max(200))
      .max(50)
      .optional(),
    affected_sections: z
      .array(z.string().min(1).max(200))
      .max(50)
      .optional(),
    action_required: z.boolean().optional(),
    recommended_reviewers: z
      .array(ReviewerRoleSchema)
      .max(6)
      .optional(),
    tags: z
      .array(
        z
          .string()
          .min(1)
          .max(50)
          .regex(/^[a-z0-9][a-z0-9_-]*$/)
      )
      .max(20)
      .optional(),
    signature: SignatureSchema.optional(),
  })
  .strict(); // reject unknown non-ext fields (ext fields are stripped before validation)

// --- TypeScript types ---

export type Category = z.infer<typeof CategorySchema>;
export type Severity = z.infer<typeof SeveritySchema>;
export type SourceType = z.infer<typeof SourceTypeSchema>;
export type ReviewerRole = z.infer<typeof ReviewerRoleSchema>;
export type Signature = z.infer<typeof SignatureSchema>;

// RawEvent is the type of the parsed event object before extension field extraction.
export type RawEvent = z.infer<typeof EventSchema>;

// ParsedEvent is a ChangeSpec event with extension fields separated into a
// dedicated `extensions` map. Core event fields use their typed values.
export interface ParsedEvent {
  specversion: "1.0";
  id: string;
  vendor_id: string;
  category: Category;
  severity: Severity;
  title: string;
  summary: string;
  published_at: string;
  source_type: SourceType;

  // Optional fields
  effective_date?: string;
  source_url?: string;
  affected_versions?: string;
  fixed_in_version?: string;
  migration_hint?: string;
  migration_url?: string;
  confidence_score?: number;
  sunset_date?: string;
  cve_id?: string;
  cvss_score?: number;
  cvss_vector?: string;
  affected_systems?: string[];
  affected_sections?: string[];
  action_required?: boolean;
  recommended_reviewers?: ReviewerRole[];
  tags?: string[];
  signature?: Signature;

  // Extension fields: all keys starting with "ext:"
  extensions: Record<string, unknown>;
}

// isExtKey returns true if the key is a valid extension field key.
// Valid ext keys start with "ext:" and are not prototype-polluting names.
export function isExtKey(key: string): boolean {
  if (!key.startsWith("ext:")) return false;
  // Strip the "ext:" prefix and check the base name.
  const base = key.slice(4);
  return !DANGEROUS_KEYS.has(base) && !DANGEROUS_KEYS.has(key);
}
