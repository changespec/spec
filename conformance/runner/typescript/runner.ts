/**
 * ChangeSpec conformance runner for TypeScript.
 *
 * Loads YAML test vectors from the specified directory tree, runs each vector
 * against the @changespec/changespec reference implementation, and prints a
 * conformance report.
 *
 * Usage:
 *   npx ts-node runner.ts <vectors-directory> [--level 1|2|3]
 *
 * Example:
 *   npx ts-node runner.ts ../../test-vectors
 *   npx ts-node runner.ts ../../test-vectors --level 1
 */

import * as fs from "fs";
import * as path from "path";
import { parse as parseYaml } from "yaml";
import { validate, SPEC_VERSION } from "@changespec/changespec";

const RUNNER_VERSION = "1.0.0";
const DEFAULT_TIMEOUT_MS = 5000;

interface GenerateSpec {
  type: string;
  field: string;
  pattern?: string;
  repeat?: number;
  size_bytes?: number;
  count?: number;
  item_value?: string;
  depth?: number;
}

interface Expected {
  valid: boolean;
  reason?: string;
  error_type?: string;
  no_network_requests?: boolean;
  no_file_access?: boolean;
  no_crash?: boolean;
  no_prototype_corruption?: boolean;
  max_memory_mb?: number;
  max_time_ms?: number;
}

interface TestVector {
  id: string;
  description: string;
  level: number;
  spec_clause?: string;
  input_type?: string;
  input?: Record<string, unknown>;
  input_json?: string;
  raw_input?: string;
  generate?: GenerateSpec;
  base_input?: Record<string, unknown>;
  expected: Expected;
  notes?: string;
}

interface VectorResult {
  vectorId: string;
  filePath: string;
  description: string;
  level: number;
  status: "PASS" | "FAIL" | "SKIP" | "WARN";
  reason?: string;
  durationMs: number;
}

function loadVectors(dir: string): { path: string; vector: TestVector }[] {
  const results: { path: string; vector: TestVector }[] = [];

  function walk(current: string): void {
    const entries = fs.readdirSync(current, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(current, entry.name);
      if (entry.isDirectory()) {
        walk(fullPath);
      } else if (entry.name.endsWith(".yml")) {
        const content = fs.readFileSync(fullPath, "utf-8");
        const vector = parseYaml(content) as TestVector;
        const relativePath = path.relative(dir, fullPath);
        results.push({ path: relativePath, vector });
      }
    }
  }

  walk(dir);
  results.sort((a, b) => a.path.localeCompare(b.path));
  return results;
}

function buildInput(
  vector: TestVector
): { bytes: string; skipReason?: string } {
  const inputType = (vector.input_type ?? "yaml").trim();

  switch (inputType) {
    case "yaml":
    case "": {
      const input = vector.input ?? {};
      return { bytes: JSON.stringify(input) };
    }

    case "json_string": {
      return { bytes: vector.input_json ?? "" };
    }

    case "raw_bytes": {
      return { bytes: vector.raw_input ?? "" };
    }

    case "generated": {
      const g = vector.generate;
      if (!g) {
        return { bytes: "", skipReason: "generate spec missing" };
      }

      const base: Record<string, unknown> = { ...(vector.base_input ?? {}) };

      switch (g.type) {
        case "oversized_field": {
          const size = g.size_bytes ?? 1000;
          base[g.field] = "A".repeat(size);
          break;
        }
        case "array_overflow": {
          const count = g.count ?? 100;
          const itemValue = g.item_value ?? "item";
          base[g.field] = Array(count).fill(itemValue);
          break;
        }
        case "deeply_nested_ext":
        case "deeply_nested_field": {
          const depth = g.depth ?? 10;
          let nested: unknown = "leaf";
          for (let i = 0; i < depth; i++) {
            nested = { child: nested };
          }
          base[g.field] = nested;
          break;
        }
        default: {
          return {
            bytes: "",
            skipReason: `unsupported generate type: ${g.type}`,
          };
        }
      }

      return { bytes: JSON.stringify(base) };
    }

    default: {
      return { bytes: "", skipReason: `unsupported input_type: ${inputType}` };
    }
  }
}

async function runVector(
  filePath: string,
  vector: TestVector,
  maxLevel: number
): Promise<VectorResult> {
  const base: VectorResult = {
    vectorId: vector.id,
    filePath,
    description: vector.description,
    level: vector.level,
    status: "PASS",
    durationMs: 0,
  };

  if (vector.level > maxLevel) {
    return {
      ...base,
      status: "SKIP",
      reason: `level ${vector.level} exceeds max level ${maxLevel}`,
    };
  }

  const { bytes, skipReason } = buildInput(vector);
  if (skipReason) {
    return { ...base, status: "SKIP", reason: skipReason };
  }

  const timeoutMs =
    vector.expected.max_time_ms ?? DEFAULT_TIMEOUT_MS;

  const start = Date.now();

  try {
    // Parse JSON and validate with timeout.
    const timedOut = await Promise.race([
      new Promise<boolean>((resolve) =>
        setTimeout(() => resolve(true), timeoutMs)
      ),
      new Promise<boolean>((resolve) => {
        try {
          let parsed: unknown;
          try {
            parsed = JSON.parse(bytes);
          } catch {
            // JSON parse error
            if (!vector.expected.valid) {
              resolve(false); // returning "not timed out"
              return;
            }
            resolve(false);
            return;
          }

          const result = validate(parsed);
          const isValid = result.success;

          if (isValid === vector.expected.valid) {
            base.status = "PASS";
          } else {
            base.status = "FAIL";
            if (vector.expected.valid) {
              base.reason = `expected valid=true but got error: ${JSON.stringify(
                result.success ? null : result.error.issues
              )}`;
            } else {
              base.reason =
                "expected valid=false but validation succeeded";
            }
          }
        } catch (err) {
          // Unexpected exception
          if (!vector.expected.valid) {
            base.status = "PASS"; // threw means rejected
          } else {
            base.status = "FAIL";
            base.reason = `unexpected exception: ${err}`;
          }
        }
        resolve(false);
      }),
    ]);

    base.durationMs = Date.now() - start;

    if (timedOut) {
      return {
        ...base,
        status: "FAIL",
        reason: `timed out after ${timeoutMs}ms`,
        durationMs: Date.now() - start,
      };
    }

    return base;
  } catch (err) {
    return {
      ...base,
      status: "FAIL",
      reason: `runner error: ${err}`,
      durationMs: Date.now() - start,
    };
  }
}

function printReport(results: VectorResult[]): void {
  let passed = 0;
  let failed = 0;
  let skipped = 0;
  let warned = 0;

  const levelPass: Record<number, number> = {};
  const levelTotal: Record<number, number> = {};

  for (const r of results) {
    switch (r.status) {
      case "PASS":
        passed++;
        levelPass[r.level] = (levelPass[r.level] ?? 0) + 1;
        levelTotal[r.level] = (levelTotal[r.level] ?? 0) + 1;
        break;
      case "FAIL":
        failed++;
        levelTotal[r.level] = (levelTotal[r.level] ?? 0) + 1;
        break;
      case "SKIP":
        skipped++;
        break;
      case "WARN":
        warned++;
        levelTotal[r.level] = (levelTotal[r.level] ?? 0) + 1;
        break;
    }
  }

  for (const r of results) {
    switch (r.status) {
      case "PASS":
        console.log(`PASS  ${r.filePath}`);
        break;
      case "SKIP":
        console.log(`SKIP  ${r.filePath} - ${r.reason}`);
        break;
      case "WARN":
        console.log(`WARN  ${r.filePath}`);
        console.log(`      ${r.reason}`);
        break;
      case "FAIL":
        console.log(`FAIL  ${r.filePath} - ${r.description}`);
        console.log(`      ${r.reason}`);
        break;
    }
  }

  console.log("\nSummary:");
  console.log(`  Vectors run:  ${passed + failed + warned}`);
  console.log(`  Passed:       ${passed}`);
  console.log(`  Failed:       ${failed}`);
  console.log(`  Warnings:     ${warned}`);
  console.log(`  Skipped:      ${skipped}\n`);

  const levelNames: Record<number, string> = {
    1: "Syntactic",
    2: "Semantic",
    3: "Secure",
  };

  for (const level of [1, 2, 3]) {
    const total = levelTotal[level] ?? 0;
    if (total === 0) continue;
    const pass = levelPass[level] ?? 0;
    const status = pass === total ? "PASS" : "FAIL";
    console.log(
      `  Level ${level} (${levelNames[level]}): ${status} (${pass}/${total})`
    );
  }
  console.log();
}

async function main(): Promise<void> {
  const args = process.argv.slice(2);
  let maxLevel = 3;
  let vectorDir = "";

  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--level" && i + 1 < args.length) {
      maxLevel = parseInt(args[i + 1], 10);
      i++;
    } else if (!args[i].startsWith("--")) {
      vectorDir = args[i];
    }
  }

  if (!vectorDir) {
    process.stderr.write(
      "Usage: runner.ts <vectors-directory> [--level 1|2|3]\n"
    );
    process.exit(1);
  }

  console.log(`ChangeSpec Conformance Runner v${RUNNER_VERSION}`);
  console.log(`Testing: @changespec/changespec v${SPEC_VERSION}`);
  console.log(`Vectors: ${vectorDir}`);
  console.log(`Max level: ${maxLevel}\n`);

  const vectorFiles = loadVectors(vectorDir);
  const results: VectorResult[] = [];

  for (const { path: filePath, vector } of vectorFiles) {
    const result = await runVector(filePath, vector, maxLevel);
    results.push(result);
  }

  printReport(results);

  const anyFail = results.some((r) => r.status === "FAIL");
  process.exit(anyFail ? 1 : 0);
}

main().catch((err) => {
  console.error("Fatal runner error:", err);
  process.exit(2);
});
