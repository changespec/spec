// Package main is the ChangeSpec conformance runner for Go.
//
// It loads YAML test vectors from the specified directory tree, runs each
// vector against the changespec-go reference implementation, and prints a
// conformance report.
//
// Usage:
//
//	go run runner.go <vectors-directory> [--level 1|2|3]
//
// Example:
//
//	go run runner.go ../../test-vectors
//	go run runner.go ../../test-vectors --level 1
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	changespec "github.com/changespec/changespec-go"
	"gopkg.in/yaml.v3"
)

const (
	defaultTimeoutMs = 5000
	version          = "1.0.0"
)

// VectorResult is the outcome of running a single test vector.
type VectorResult struct {
	VectorID    string
	Path        string
	Description string
	Level       int
	Status      string // PASS, FAIL, SKIP, WARN
	Reason      string
	Duration    time.Duration
}

// TestVector represents a parsed YAML test vector file.
type TestVector struct {
	ID          string         `yaml:"id"`
	Description string         `yaml:"description"`
	Level       int            `yaml:"level"`
	SpecClause  string         `yaml:"spec_clause"`
	InputType   string         `yaml:"input_type"`
	Input       map[string]any `yaml:"input"`
	InputJSON   string         `yaml:"input_json"`
	RawInput    string         `yaml:"raw_input"`
	Generate    *GenerateSpec  `yaml:"generate"`
	BaseInput   map[string]any `yaml:"base_input"`
	Expected    Expected       `yaml:"expected"`
	Notes       string         `yaml:"notes"`
}

// GenerateSpec describes how to generate a test input programmatically.
type GenerateSpec struct {
	Type       string `yaml:"type"`
	Field      string `yaml:"field"`
	Pattern    string `yaml:"pattern"`
	Repeat     int    `yaml:"repeat"`
	SizeBytes  int    `yaml:"size_bytes"`
	Count      int    `yaml:"count"`
	ItemValue  string `yaml:"item_value"`
	Depth      int    `yaml:"depth"`
}

// Expected is the expected outcome of a test vector.
type Expected struct {
	Valid              bool   `yaml:"valid"`
	Reason             string `yaml:"reason"`
	ErrorType          string `yaml:"error_type"`
	NoNetworkRequests  bool   `yaml:"no_network_requests"`
	NoFileAccess       bool   `yaml:"no_file_access"`
	NoCrash            bool   `yaml:"no_crash"`
	NoPrototypeCorrupt bool   `yaml:"no_prototype_corruption"`
	MaxMemoryMB        int    `yaml:"max_memory_mb"`
	MaxTimeMs          int    `yaml:"max_time_ms"`
}

func main() {
	var maxLevel int
	flag.IntVar(&maxLevel, "level", 3, "Maximum conformance level to test (1, 2, or 3)")
	flag.Parse()

	args := flag.Args()
	if len(args) < 1 {
		fmt.Fprintf(os.Stderr, "Usage: runner <vectors-directory> [--level 1|2|3]\n")
		os.Exit(1)
	}
	vectorDir := args[0]

	fmt.Printf("ChangeSpec Conformance Runner v%s\n", version)
	fmt.Printf("Testing: changespec-go v%s\n", changespec.SpecVersion)
	fmt.Printf("Vectors: %s\n", vectorDir)
	fmt.Printf("Max level: %d\n\n", maxLevel)

	vectors, err := loadVectors(vectorDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error loading vectors: %v\n", err)
		os.Exit(1)
	}

	results := runVectors(vectors, maxLevel)
	printReport(results)

	// Exit non-zero if any FAIL results.
	for _, r := range results {
		if r.Status == "FAIL" {
			os.Exit(1)
		}
	}
}

// loadVectors walks vectorDir and parses all .yml files.
func loadVectors(dir string) ([]*TestVector, error) {
	var vectors []*TestVector

	err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() || !strings.HasSuffix(path, ".yml") {
			return nil
		}

		data, err := os.ReadFile(path)
		if err != nil {
			return fmt.Errorf("reading %s: %w", path, err)
		}

		var v TestVector
		if err := yaml.Unmarshal(data, &v); err != nil {
			return fmt.Errorf("parsing %s: %w", path, err)
		}
		v.InputType = strings.TrimSpace(v.InputType)
		if v.InputType == "" {
			v.InputType = "yaml"
		}

		// Store relative path for reporting.
		rel, _ := filepath.Rel(dir, path)
		v.ID = rel

		vectors = append(vectors, &v)
		return nil
	})

	if err != nil {
		return nil, err
	}

	sort.Slice(vectors, func(i, j int) bool {
		return vectors[i].ID < vectors[j].ID
	})

	return vectors, nil
}

// runVectors executes all test vectors and returns results.
func runVectors(vectors []*TestVector, maxLevel int) []VectorResult {
	results := make([]VectorResult, 0, len(vectors))

	for _, v := range vectors {
		result := runVector(v, maxLevel)
		results = append(results, result)
	}

	return results
}

// runVector executes a single test vector.
func runVector(v *TestVector, maxLevel int) VectorResult {
	base := VectorResult{
		VectorID:    v.ID,
		Path:        v.ID,
		Description: v.Description,
		Level:       v.Level,
	}

	// Skip vectors above the max level.
	if v.Level > maxLevel {
		base.Status = "SKIP"
		base.Reason = fmt.Sprintf("level %d exceeds max level %d", v.Level, maxLevel)
		return base
	}

	// Build the input bytes.
	inputBytes, skipReason, err := buildInput(v)
	if err != nil {
		base.Status = "FAIL"
		base.Reason = fmt.Sprintf("failed to build input: %v", err)
		return base
	}
	if skipReason != "" {
		base.Status = "SKIP"
		base.Reason = skipReason
		return base
	}

	// Determine timeout.
	timeoutMs := defaultTimeoutMs
	if v.Expected.MaxTimeMs > 0 {
		timeoutMs = v.Expected.MaxTimeMs
	}

	// Run validation with timeout.
	type outcome struct {
		valid bool
		err   error
	}

	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeoutMs)*time.Millisecond)
	defer cancel()

	ch := make(chan outcome, 1)
	start := time.Now()

	go func() {
		_, valErr := changespec.Validate(inputBytes)
		ch <- outcome{valid: valErr == nil, err: valErr}
	}()

	var got outcome
	select {
	case got = <-ch:
	case <-ctx.Done():
		base.Status = "FAIL"
		base.Reason = fmt.Sprintf("timed out after %dms", timeoutMs)
		base.Duration = time.Since(start)
		return base
	}

	base.Duration = time.Since(start)

	// Compare result to expected.
	if got.valid == v.Expected.Valid {
		base.Status = "PASS"
		return base
	}

	base.Status = "FAIL"
	if v.Expected.Valid {
		base.Reason = fmt.Sprintf("expected valid=true but got validation error: %v", got.err)
	} else {
		base.Reason = "expected valid=false but validation succeeded (no error returned)"
	}

	return base
}

// buildInput constructs the JSON bytes for a test vector.
func buildInput(v *TestVector) ([]byte, string, error) {
	switch v.InputType {
	case "yaml", "":
		// Serialize the YAML input map to JSON.
		if v.Input == nil {
			return []byte("{}"), "", nil
		}
		b, err := json.Marshal(v.Input)
		if err != nil {
			return nil, "", fmt.Errorf("serializing input: %w", err)
		}
		return b, "", nil

	case "json_string":
		return []byte(v.InputJSON), "", nil

	case "raw_bytes":
		return []byte(v.RawInput), "", nil

	case "generated":
		if v.Generate == nil {
			return nil, "", fmt.Errorf("generate spec missing")
		}
		return buildGeneratedInput(v)

	default:
		return nil, fmt.Sprintf("unsupported input_type: %s", v.InputType), nil
	}
}

// buildGeneratedInput constructs inputs for security/edge-case vectors that
// require programmatic generation.
func buildGeneratedInput(v *TestVector) ([]byte, string, error) {
	if v.Generate == nil {
		return nil, "", fmt.Errorf("generate spec required")
	}

	base := v.BaseInput
	if base == nil {
		base = make(map[string]any)
	}

	// Copy base to avoid mutating the vector.
	m := make(map[string]any, len(base))
	for k, val := range base {
		m[k] = val
	}

	g := v.Generate

	switch g.Type {
	case "oversized_field":
		// Fill the specified field with 'A' characters of the given size.
		m[g.Field] = strings.Repeat("A", g.SizeBytes)

	case "array_overflow":
		// Fill the specified field with an array of Count items.
		items := make([]any, g.Count)
		val := g.ItemValue
		if val == "" {
			val = "item"
		}
		for i := range items {
			items[i] = val
		}
		m[g.Field] = items

	case "deeply_nested_ext", "deeply_nested_field":
		// Build a deeply nested object.
		depth := g.Depth
		if depth <= 0 {
			depth = 10
		}
		var nested any = "leaf"
		for i := 0; i < depth; i++ {
			nested = map[string]any{"child": nested}
		}
		m[g.Field] = nested

	default:
		return nil, fmt.Sprintf("unsupported generate type: %s", g.Type), nil
	}

	b, err := json.Marshal(m)
	if err != nil {
		return nil, "", fmt.Errorf("serializing generated input: %w", err)
	}
	return b, "", nil
}

// printReport prints the conformance report to stdout.
func printReport(results []VectorResult) {
	var passed, failed, skipped, warned int
	levelPass := map[int]int{}
	levelTotal := map[int]int{}

	for _, r := range results {
		switch r.Status {
		case "PASS":
			passed++
			levelPass[r.Level]++
			levelTotal[r.Level]++
		case "FAIL":
			failed++
			levelTotal[r.Level]++
		case "SKIP":
			skipped++
		case "WARN":
			warned++
			levelTotal[r.Level]++
		}
	}

	for _, r := range results {
		switch r.Status {
		case "PASS":
			fmt.Printf("PASS  %s\n", r.Path)
		case "SKIP":
			fmt.Printf("SKIP  %s - %s\n", r.Path, r.Reason)
		case "WARN":
			fmt.Printf("WARN  %s\n", r.Path)
			fmt.Printf("      %s\n", r.Reason)
		case "FAIL":
			fmt.Printf("FAIL  %s - %s\n", r.Path, r.Description)
			fmt.Printf("      %s\n", r.Reason)
		}
	}

	fmt.Printf("\nSummary:\n")
	fmt.Printf("  Vectors run:  %d\n", passed+failed+warned)
	fmt.Printf("  Passed:       %d\n", passed)
	fmt.Printf("  Failed:       %d\n", failed)
	fmt.Printf("  Warnings:     %d\n", warned)
	fmt.Printf("  Skipped:      %d\n\n", skipped)

	levelNames := map[int]string{
		1: "Syntactic",
		2: "Semantic",
		3: "Secure",
	}

	for level := 1; level <= 3; level++ {
		total := levelTotal[level]
		if total == 0 {
			continue
		}
		pass := levelPass[level]
		status := "PASS"
		if pass < total {
			status = "FAIL"
		}
		fmt.Printf("  Level %d (%s): %s (%d/%d)\n",
			level, levelNames[level], status, pass, total)
	}
	fmt.Println()
}
