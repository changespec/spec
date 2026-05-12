import { z } from "zod";
export declare const SPEC_VERSION: "1.0";
export declare const CategorySchema: z.ZodEnum<{
    api_breaking: "api_breaking";
    api_deprecation: "api_deprecation";
    security: "security";
    data_handling: "data_handling";
    liability: "liability";
    pricing: "pricing";
    tos: "tos";
    cosmetic: "cosmetic";
    informational: "informational";
}>;
export declare const SeveritySchema: z.ZodEnum<{
    informational: "informational";
    critical: "critical";
    high: "high";
    medium: "medium";
    low: "low";
}>;
export declare const SourceTypeSchema: z.ZodEnum<{
    publisher_verified: "publisher_verified";
    crawled: "crawled";
    community: "community";
}>;
export declare const ReviewerRoleSchema: z.ZodEnum<{
    security: "security";
    engineering: "engineering";
    legal: "legal";
    compliance: "compliance";
    procurement: "procurement";
    management: "management";
}>;
export declare const SignatureSchema: z.ZodObject<{
    alg: z.ZodLiteral<"ed25519">;
    key_id: z.ZodString;
    value: z.ZodString;
    signed_fields: z.ZodArray<z.ZodString>;
    key_fingerprint: z.ZodOptional<z.ZodString>;
}, z.core.$strip>;
export declare const EventSchema: z.ZodObject<{
    specversion: z.ZodLiteral<"1.0">;
    id: z.ZodString;
    vendor_id: z.ZodString;
    category: z.ZodEnum<{
        api_breaking: "api_breaking";
        api_deprecation: "api_deprecation";
        security: "security";
        data_handling: "data_handling";
        liability: "liability";
        pricing: "pricing";
        tos: "tos";
        cosmetic: "cosmetic";
        informational: "informational";
    }>;
    severity: z.ZodEnum<{
        informational: "informational";
        critical: "critical";
        high: "high";
        medium: "medium";
        low: "low";
    }>;
    title: z.ZodString;
    summary: z.ZodString;
    published_at: z.ZodString;
    source_type: z.ZodEnum<{
        publisher_verified: "publisher_verified";
        crawled: "crawled";
        community: "community";
    }>;
    effective_date: z.ZodOptional<z.ZodString>;
    source_url: z.ZodOptional<z.ZodString>;
    affected_versions: z.ZodOptional<z.ZodString>;
    fixed_in_version: z.ZodOptional<z.ZodString>;
    migration_hint: z.ZodOptional<z.ZodString>;
    migration_url: z.ZodOptional<z.ZodString>;
    confidence_score: z.ZodOptional<z.ZodNumber>;
    sunset_date: z.ZodOptional<z.ZodString>;
    cve_id: z.ZodOptional<z.ZodString>;
    cvss_score: z.ZodOptional<z.ZodNumber>;
    cvss_vector: z.ZodOptional<z.ZodString>;
    affected_systems: z.ZodOptional<z.ZodArray<z.ZodString>>;
    affected_sections: z.ZodOptional<z.ZodArray<z.ZodString>>;
    action_required: z.ZodOptional<z.ZodBoolean>;
    recommended_reviewers: z.ZodOptional<z.ZodArray<z.ZodEnum<{
        security: "security";
        engineering: "engineering";
        legal: "legal";
        compliance: "compliance";
        procurement: "procurement";
        management: "management";
    }>>>;
    tags: z.ZodOptional<z.ZodArray<z.ZodString>>;
    signature: z.ZodOptional<z.ZodObject<{
        alg: z.ZodLiteral<"ed25519">;
        key_id: z.ZodString;
        value: z.ZodString;
        signed_fields: z.ZodArray<z.ZodString>;
        key_fingerprint: z.ZodOptional<z.ZodString>;
    }, z.core.$strip>>;
}, z.core.$strict>;
export type Category = z.infer<typeof CategorySchema>;
export type Severity = z.infer<typeof SeveritySchema>;
export type SourceType = z.infer<typeof SourceTypeSchema>;
export type ReviewerRole = z.infer<typeof ReviewerRoleSchema>;
export type Signature = z.infer<typeof SignatureSchema>;
export type RawEvent = z.infer<typeof EventSchema>;
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
    extensions: Record<string, unknown>;
}
export declare function isExtKey(key: string): boolean;
//# sourceMappingURL=types.d.ts.map