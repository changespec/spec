package changespec

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"net/url"
	"strings"
	"time"

	"github.com/santhosh-tekuri/jsonschema/v6"
)

// schemaJSON is the canonical ChangeSpec 1.0 JSON Schema embedded at build time.
// This file is generated from spec/schema.json in the ChangeSpec repository.
// It MUST NOT be hand-edited. Update schema.json in the spec directory instead.
//
//go:embed schema.json
var schemaJSON []byte

// ValidationError is returned when a JSON blob does not conform to the ChangeSpec schema.
type ValidationError struct {
	// Message is a human-readable description of the validation failure.
	Message string
	// Details contains individual field-level error messages, if available.
	Details []string
}

func (e *ValidationError) Error() string {
	if len(e.Details) == 0 {
		return fmt.Sprintf("changespec validation error: %s", e.Message)
	}
	return fmt.Sprintf("changespec validation error: %s (%s)", e.Message, strings.Join(e.Details, "; "))
}

// compiledSchema is the lazily-compiled JSON schema. It is initialized once and
// reused for all subsequent Validate calls.
var compiledSchema *jsonschema.Schema

func getSchema() (*jsonschema.Schema, error) {
	if compiledSchema != nil {
		return compiledSchema, nil
	}

	doc, err := jsonschema.UnmarshalJSON(strings.NewReader(string(schemaJSON)))
	if err != nil {
		return nil, fmt.Errorf("changespec: failed to unmarshal embedded schema: %w", err)
	}

	compiler := jsonschema.NewCompiler()

	// Enable format assertion. In JSON Schema 2020-12, format is an annotation
	// by default. AssertFormat() makes the compiler treat format violations as
	// validation errors, which is required for ChangeSpec conformance.
	compiler.AssertFormat()

	// Register format validators for date-time, date, and uri.
	// The canonical schema.json uses these formats; without registration the
	// santhosh-tekuri/jsonschema/v6 library treats them as annotations only.

	compiler.RegisterFormat(&jsonschema.Format{
		Name: "date-time",
		Validate: func(v any) error {
			s, ok := v.(string)
			if !ok {
				return nil
			}
			// RFC 3339 datetime: requires time component (not date-only).
			// Try the common UTC form first, then the offset form.
			if _, err := time.Parse(time.RFC3339, s); err == nil {
				return nil
			}
			if _, err := time.Parse("2006-01-02T15:04:05.999999999Z07:00", s); err == nil {
				return nil
			}
			return fmt.Errorf("not a valid RFC 3339 datetime: %q", s)
		},
	})

	compiler.RegisterFormat(&jsonschema.Format{
		Name: "date",
		Validate: func(v any) error {
			s, ok := v.(string)
			if !ok {
				return nil
			}
			// RFC 3339 full-date: YYYY-MM-DD only. Reject datetime strings.
			if _, err := time.Parse("2006-01-02", s); err != nil {
				return fmt.Errorf("not a valid RFC 3339 full-date (YYYY-MM-DD): %q", s)
			}
			// Reject strings longer than YYYY-MM-DD (catches datetime strings).
			if len(s) != 10 {
				return fmt.Errorf("date field must be exactly YYYY-MM-DD, got %q", s)
			}
			return nil
		},
	})

	compiler.RegisterFormat(&jsonschema.Format{
		Name: "uri",
		Validate: func(v any) error {
			s, ok := v.(string)
			if !ok {
				return nil
			}
			u, err := url.Parse(s)
			if err != nil || !u.IsAbs() || u.Host == "" {
				return fmt.Errorf("not a valid absolute URI: %q", s)
			}
			// Enforce https:// scheme for source_url and migration_url.
			// The schema also carries a pattern constraint, but we enforce
			// it here too so that the format validator catches the violation
			// with an informative error.
			if u.Scheme != "https" {
				return fmt.Errorf("URI must use https:// scheme, got %q", u.Scheme)
			}
			return nil
		},
	})

	// Use the canonical schema URL from the $id field.
	const schemaURL = "changespec-1.0.json"
	if err := compiler.AddResource(schemaURL, doc); err != nil {
		return nil, fmt.Errorf("changespec: failed to add schema resource: %w", err)
	}

	schema, err := compiler.Compile(schemaURL)
	if err != nil {
		return nil, fmt.Errorf("changespec: failed to compile schema: %w", err)
	}

	compiledSchema = schema
	return schema, nil
}

// Validate parses and validates a JSON blob as a ChangeSpec 1.0 event.
//
// Returns a parsed Event on success. Returns a *ValidationError if the input
// fails schema validation. Returns a standard error for JSON parse failures.
//
// Extension fields (keys starting with "ext:") are collected into Event.Extensions.
// Unknown non-extension fields are silently ignored per the ChangeSpec forward
// compatibility rules.
func Validate(data []byte) (*Event, error) {
	// Step 1: Parse the raw JSON into a generic value for schema validation.
	var v any
	if err := json.Unmarshal(data, &v); err != nil {
		return nil, fmt.Errorf("changespec: invalid JSON: %w", err)
	}

	// Step 2: JSON Schema validation.
	schema, err := getSchema()
	if err != nil {
		return nil, err
	}

	if err := schema.Validate(v); err != nil {
		ve, ok := err.(*jsonschema.ValidationError)
		if !ok {
			return nil, &ValidationError{Message: err.Error()}
		}
		details := collectErrors(ve)
		return nil, &ValidationError{
			Message: "schema validation failed",
			Details: details,
		}
	}

	// Step 3: Parse into the typed Event struct.
	event, err := parseEvent(data)
	if err != nil {
		return nil, fmt.Errorf("changespec: failed to parse event after schema validation: %w", err)
	}

	return event, nil
}

// collectErrors flattens a jsonschema.ValidationError tree into a string slice.
func collectErrors(ve *jsonschema.ValidationError) []string {
	var errs []string
	errs = append(errs, ve.Error())
	for _, cause := range ve.Causes {
		errs = append(errs, collectErrors(cause)...)
	}
	return errs
}

// parseEvent unmarshals the raw JSON into an Event, handling extension fields.
func parseEvent(data []byte) (*Event, error) {
	// First pass: parse into a generic map to extract extension fields.
	var raw map[string]json.RawMessage
	if err := json.Unmarshal(data, &raw); err != nil {
		return nil, err
	}

	// Collect extension fields before standard unmarshal.
	extensions := make(map[string]any)
	for key, val := range raw {
		if strings.HasPrefix(key, "ext:") {
			var ev any
			if err := json.Unmarshal(val, &ev); err == nil {
				extensions[key] = ev
			}
		}
	}

	// Second pass: unmarshal into the typed struct.
	var event Event
	if err := json.Unmarshal(data, &event); err != nil {
		return nil, err
	}

	if len(extensions) > 0 {
		event.Extensions = extensions
	}

	return &event, nil
}
