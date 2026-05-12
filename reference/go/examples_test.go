package changespec_test

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	changespec "github.com/changespec/changespec-go"
)

// examplesDir is the path to the examples directory relative to this test file.
const examplesDir = "../../examples"

// TestExampleFiles loads and validates every .json file in the examples directory.
// This test proves that all canonical examples conform to the ChangeSpec 1.0 schema.
func TestExampleFiles(t *testing.T) {
	entries, err := os.ReadDir(examplesDir)
	if err != nil {
		t.Fatalf("failed to read examples directory %q: %v", examplesDir, err)
	}

	found := 0
	for _, entry := range entries {
		if entry.IsDir() || filepath.Ext(entry.Name()) != ".json" {
			continue
		}
		found++

		name := entry.Name()
		t.Run(name, func(t *testing.T) {
			path := filepath.Join(examplesDir, name)

			data, err := os.ReadFile(path)
			if err != nil {
				t.Fatalf("failed to read %q: %v", path, err)
			}

			event, err := changespec.Validate(data)
			if err != nil {
				t.Fatalf("validation failed for %q: %v", name, err)
			}

			// Verify required fields are populated.
			if event.SpecVersion == "" {
				t.Errorf("%q: specversion is empty", name)
			}
			if event.SpecVersion != changespec.SpecVersion {
				t.Errorf("%q: specversion = %q, want %q", name, event.SpecVersion, changespec.SpecVersion)
			}
			if event.ID == "" {
				t.Errorf("%q: id is empty", name)
			}
			if event.VendorID == "" {
				t.Errorf("%q: vendor_id is empty", name)
			}
			if event.Category == "" {
				t.Errorf("%q: category is empty", name)
			}
			if event.Severity == "" {
				t.Errorf("%q: severity is empty", name)
			}
			if event.Title == "" {
				t.Errorf("%q: title is empty", name)
			}
			if event.Summary == "" {
				t.Errorf("%q: summary is empty", name)
			}
			if event.PublishedAt == "" {
				t.Errorf("%q: published_at is empty", name)
			}
			if event.SourceType == "" {
				t.Errorf("%q: source_type is empty", name)
			}

			t.Logf("OK: %s (vendor=%s category=%s severity=%s source=%s)",
				name, event.VendorID, event.Category, event.Severity, event.SourceType)
		})
	}

	if found == 0 {
		t.Fatalf("no .json files found in %q", examplesDir)
	}
	t.Logf("validated %d example files", found)
}

// TestExpectedExampleFiles verifies that the canonical set of examples exists.
// If a required example file is missing, this test fails loudly.
func TestExpectedExampleFiles(t *testing.T) {
	required := []string{
		"security-cve.json",
		"api-breaking.json",
		"api-deprecation.json",
		"tos-update.json",
		"data-handling.json",
		"pricing.json",
		"cosmetic.json",
	}

	for _, name := range required {
		path := filepath.Join(examplesDir, name)
		if _, err := os.Stat(path); os.IsNotExist(err) {
			t.Errorf("required example file missing: %q", path)
		}
	}
}

// TestInvalidEvents verifies that malformed events are rejected.
func TestInvalidEvents(t *testing.T) {
	cases := []struct {
		name string
		json string
	}{
		{
			name: "missing required field: id",
			json: `{
				"specversion": "1.0",
				"vendor_id": "stripe",
				"category": "api_breaking",
				"severity": "high",
				"title": "Test change",
				"summary": "A test change.",
				"published_at": "2026-04-10T14:00:00Z",
				"source_type": "crawled"
			}`,
		},
		{
			name: "invalid category",
			json: `{
				"specversion": "1.0",
				"id": "cs_test001",
				"vendor_id": "stripe",
				"category": "unknown_category",
				"severity": "high",
				"title": "Test change",
				"summary": "A test change.",
				"published_at": "2026-04-10T14:00:00Z",
				"source_type": "crawled"
			}`,
		},
		{
			name: "invalid severity",
			json: `{
				"specversion": "1.0",
				"id": "cs_test002",
				"vendor_id": "stripe",
				"category": "api_breaking",
				"severity": "extreme",
				"title": "Test change",
				"summary": "A test change.",
				"published_at": "2026-04-10T14:00:00Z",
				"source_type": "crawled"
			}`,
		},
		{
			name: "wrong specversion",
			json: `{
				"specversion": "2.0",
				"id": "cs_test003",
				"vendor_id": "stripe",
				"category": "api_breaking",
				"severity": "high",
				"title": "Test change",
				"summary": "A test change.",
				"published_at": "2026-04-10T14:00:00Z",
				"source_type": "crawled"
			}`,
		},
		{
			name: "title too long",
			json: `{
				"specversion": "1.0",
				"id": "cs_test004",
				"vendor_id": "stripe",
				"category": "api_breaking",
				"severity": "high",
				"title": "` + string(make([]byte, 201)) + `",
				"summary": "A test change.",
				"published_at": "2026-04-10T14:00:00Z",
				"source_type": "crawled"
			}`,
		},
		{
			name: "invalid source_type",
			json: `{
				"specversion": "1.0",
				"id": "cs_test005",
				"vendor_id": "stripe",
				"category": "api_breaking",
				"severity": "high",
				"title": "Test change",
				"summary": "A test change.",
				"published_at": "2026-04-10T14:00:00Z",
				"source_type": "ai_generated"
			}`,
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			_, err := changespec.Validate([]byte(tc.json))
			if err == nil {
				t.Errorf("expected validation error for %q, got nil", tc.name)
			}
			t.Logf("correctly rejected %q: %v", tc.name, err)
		})
	}
}

// TestMinimalValidEvent verifies that an event with only required fields is accepted.
func TestMinimalValidEvent(t *testing.T) {
	minimal := `{
		"specversion": "1.0",
		"id": "cs_minimal001",
		"vendor_id": "acme",
		"category": "informational",
		"severity": "informational",
		"title": "Documentation typo fix",
		"summary": "Corrected a typo. No behavior change.",
		"published_at": "2026-04-10T14:00:00Z",
		"source_type": "crawled"
	}`

	event, err := changespec.Validate([]byte(minimal))
	if err != nil {
		t.Fatalf("minimal event failed validation: %v", err)
	}
	if event.ID != "cs_minimal001" {
		t.Errorf("id = %q, want cs_minimal001", event.ID)
	}
}

// TestExtensionFields verifies that extension fields are parsed into Event.Extensions.
func TestExtensionFields(t *testing.T) {
	withExtensions := `{
		"specversion": "1.0",
		"id": "cs_ext001",
		"vendor_id": "twilio",
		"category": "data_handling",
		"severity": "medium",
		"title": "DPA updated: new subprocessor",
		"summary": "A new subprocessor was added.",
		"published_at": "2026-04-10T14:00:00Z",
		"source_type": "crawled",
		"ext:compliance.gdpr_article": "28",
		"ext:compliance.requires_dpa_review": true,
		"ext:internal.ticket_id": "ENG-4521"
	}`

	event, err := changespec.Validate([]byte(withExtensions))
	if err != nil {
		t.Fatalf("event with extensions failed validation: %v", err)
	}

	if len(event.Extensions) != 3 {
		t.Errorf("expected 3 extension fields, got %d", len(event.Extensions))
	}

	article, ok := event.Extensions["ext:compliance.gdpr_article"]
	if !ok {
		t.Error("ext:compliance.gdpr_article not found in Extensions")
	}
	if article != "28" {
		t.Errorf("ext:compliance.gdpr_article = %v, want \"28\"", article)
	}
}

// TestRoundTrip verifies that a parsed event can be re-serialized to valid JSON.
func TestRoundTrip(t *testing.T) {
	original := `{
		"specversion": "1.0",
		"id": "cs_roundtrip001",
		"vendor_id": "npm:express",
		"category": "security",
		"severity": "critical",
		"title": "CVE-2025-29999: path traversal vulnerability",
		"summary": "A path traversal vulnerability allows reading arbitrary files.",
		"published_at": "2026-04-10T09:00:00Z",
		"source_type": "crawled",
		"confidence_score": 0.97,
		"cve_id": "CVE-2025-29999",
		"cvss_score": 9.1,
		"action_required": true
	}`

	event, err := changespec.Validate([]byte(original))
	if err != nil {
		t.Fatalf("original event failed validation: %v", err)
	}

	// Re-serialize.
	serialized, err := json.Marshal(event)
	if err != nil {
		t.Fatalf("failed to marshal event: %v", err)
	}

	// Validate the re-serialized form.
	event2, err := changespec.Validate(serialized)
	if err != nil {
		t.Fatalf("re-serialized event failed validation: %v", err)
	}

	if event.ID != event2.ID {
		t.Errorf("round-trip ID mismatch: %q != %q", event.ID, event2.ID)
	}
}
