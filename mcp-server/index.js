import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCRIPTS_DIR = path.resolve(__dirname, "..", "scripts");

/**
 * Run a Python script with arguments and return its stdout.
 * Rejects on non-zero exit or stderr-only output.
 */
function runPython(scriptName, args) {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(SCRIPTS_DIR, scriptName);
    const proc = spawn("python3", [scriptPath, ...args], {
      cwd: SCRIPTS_DIR,
      env: { ...process.env },
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });

    proc.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
      // Forward Python stderr to our stderr (not stdout — that's MCP protocol)
      process.stderr.write(chunk);
    });

    proc.on("error", (err) => {
      reject(new Error(`Failed to spawn python3: ${err.message}`));
    });

    proc.on("close", (code) => {
      if (code !== 0) {
        reject(
          new Error(
            `Script ${scriptName} exited with code ${code}. stderr: ${stderr}`
          )
        );
      } else {
        resolve(stdout.trim());
      }
    });
  });
}

// ── Server setup ──────────────────────────────────────────────────────────────

const server = new McpServer({
  name: "medical-rep-tools",
  version: "1.0.0",
});

// ── Tool 1: get_mr_profile ────────────────────────────────────────────────────

server.tool(
  "get_mr_profile",
  "Look up a pharmaceutical medical representative's profile from the database using their phone number",
  {
    phone: z.string().describe("Phone number in E.164 format, e.g. +919876543210"),
  },
  async ({ phone }) => {
    try {
      const result = await runPython("get_mr_profile.py", ["--phone", phone]);
      return { content: [{ type: "text", text: result }] };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Error: ${err.message}` }],
        isError: true,
      };
    }
  }
);

// ── Tool 2: get_doctor_info ───────────────────────────────────────────────────

server.tool(
  "get_doctor_info",
  "Get search queries for enriching a doctor's profile, or parse search results into structured doctor data",
  {
    name: z.string().describe("Doctor's full name"),
    city: z.string().describe("City where the doctor practices"),
    specialty: z.string().describe("Doctor's medical specialty"),
    mode: z
      .enum(["generate-queries", "parse-results"])
      .optional()
      .default("generate-queries")
      .describe('Operation mode: "generate-queries" to get search queries, "parse-results" to parse search results'),
    searchResults: z
      .string()
      .optional()
      .describe("Raw search results text to parse (required when mode is parse-results)"),
  },
  async ({ name, city, specialty, mode, searchResults }) => {
    try {
      const args = ["--name", name, "--city", city, "--specialty", specialty];

      if (mode === "generate-queries") {
        args.push("--generate-queries");
      } else if (mode === "parse-results") {
        if (!searchResults) {
          return {
            content: [
              {
                type: "text",
                text: 'Error: searchResults is required when mode is "parse-results"',
              },
            ],
            isError: true,
          };
        }
        args.push("--search-results", searchResults);
      }

      const result = await runPython("get_doctor_info.py", args);
      return { content: [{ type: "text", text: result }] };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Error: ${err.message}` }],
        isError: true,
      };
    }
  }
);

// ── Tool 3: update_doctor ─────────────────────────────────────────────────────

server.tool(
  "update_doctor",
  "Update a doctor's profile in memory with new information from MR conversation notes",
  {
    doctor: z.string().describe("Doctor's name to update"),
    field: z.string().optional().describe("Specific field to update"),
    value: z.string().optional().describe("New value for the field"),
    notes: z.string().optional().describe("Free-text conversation notes from the MR"),
    memoryFile: z
      .string()
      .optional()
      .describe("Path to memory file (defaults to ~/.openclaw/workspace/MEMORY.md)"),
  },
  async ({ doctor, field, value, notes, memoryFile }) => {
    try {
      const args = ["--doctor", doctor];

      if (field) {
        args.push("--field", field);
      }
      if (value) {
        args.push("--value", value);
      }
      if (notes) {
        args.push("--notes", notes);
      }

      const resolvedMemory =
        memoryFile || path.join(process.env.HOME || "~", ".openclaw", "workspace", "MEMORY.md");
      args.push("--memory-file", resolvedMemory);

      const result = await runPython("update_doctor.py", args);
      return { content: [{ type: "text", text: result }] };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Error: ${err.message}` }],
        isError: true,
      };
    }
  }
);

// ── Start server ──────────────────────────────────────────────────────────────

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  process.stderr.write("medical-rep-tools MCP server running on stdio\n");
}

main().catch((err) => {
  process.stderr.write(`Fatal: ${err.message}\n`);
  process.exit(1);
});
