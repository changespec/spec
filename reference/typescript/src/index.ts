export { SPEC_VERSION } from "./types.js";
export type {
  Category,
  Severity,
  SourceType,
  ReviewerRole,
  Signature,
  ParsedEvent,
  RawEvent,
} from "./types.js";
export {
  CategorySchema,
  SeveritySchema,
  SourceTypeSchema,
  ReviewerRoleSchema,
  SignatureSchema,
  EventSchema,
} from "./types.js";
export { validate, validateOrThrow } from "./validate.js";
export type { ValidationResult } from "./validate.js";
