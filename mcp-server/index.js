import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SCRIPTS_DIR = path.resolve(__dirname, "..", "scripts");

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

function parseAndCheckLoginRequired(raw) {
  try {
    const parsed = JSON.parse(raw);
    if (parsed.status === "manual_login_required") {
      return {
        loginRequired: true,
        content: [{
          type: "text",
          text: JSON.stringify({
            status: "manual_login_required",
            action: "Please log into the Emcure Super AI web portal to activate API access, then retry.",
            message: parsed.message,
          }),
        }],
      };
    }
    return { loginRequired: false };
  } catch {
    return { loginRequired: false };
  }
}

const server = new McpServer({
  name: "medical-rep-tools",
  version: "2.0.0",
});

server.tool(
  "get_mr_profile",
  "Look up a pharmaceutical MR's profile from the Emcure API using their name, division, and HQ.",
  {
    phone: z.string().optional().describe("Phone number in E.164 format (stored with profile, not used for lookup)"),
    name: z.string().describe("Employee name for Emcure API lookup"),
    division: z.string().optional().describe("Division filter for API query"),
    hq: z.string().optional().describe("HQ/city filter for API query"),
  },
  async ({ phone, name, division, hq }) => {
    try {
      if (!name) {
        return {
          content: [{ type: "text", text: "Error: name is required" }],
          isError: true,
        };
      }

      const args = ["--name", name];
      if (phone) args.push("--phone", phone);
      if (division) args.push("--division", division);
      if (hq) args.push("--hq", hq);

      const raw = await runPython("get_mr_profile.py", args);
      const check = parseAndCheckLoginRequired(raw);
      if (check.loginRequired) return { content: check.content };
      return { content: [{ type: "text", text: raw }] };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Error: ${err.message}` }],
        isError: true,
      };
    }
  }
);

server.tool(
  "get_doctor_info",
  "Look up doctor in Emcure API visit/missed data, generate web search queries, or parse search results into a structured profile",
  {
    name: z.string().describe("Doctor's full name"),
    city: z.string().describe("City where the doctor practices"),
    specialty: z.string().describe("Doctor's medical specialty"),
    mrName: z.string().optional().describe("MR employee name (needed for API lookup to find doctor in MR's visit data)"),
    division: z.string().optional().describe("Division filter for API query"),
    hq: z.string().optional().describe("HQ/city filter for API query"),
    mode: z
      .enum(["lookup", "generate-queries", "parse-results"])
      .optional()
      .default("lookup")
      .describe('"lookup" checks Emcure API then suggests web search, "generate-queries" for web search queries, "parse-results" to parse search results'),
    searchResults: z
      .string()
      .optional()
      .describe("Raw search results text to parse (required when mode is parse-results)"),
  },
  async ({ name, city, specialty, mrName, division, hq, mode, searchResults }) => {
    try {
      const args = ["--name", name, "--city", city, "--specialty", specialty];

      if (mrName) args.push("--mr-name", mrName);
      if (division) args.push("--division", division);
      if (hq) args.push("--hq", hq);

      if (mode === "lookup") {
        args.push("--lookup");
      } else if (mode === "generate-queries") {
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

      const raw = await runPython("get_doctor_info.py", args);
      const check = parseAndCheckLoginRequired(raw);
      if (check.loginRequired) return { content: check.content };
      return { content: [{ type: "text", text: raw }] };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Error: ${err.message}` }],
        isError: true,
      };
    }
  }
);

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

      if (field) args.push("--field", field);
      if (value) args.push("--value", value);
      if (notes) args.push("--notes", notes);

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

server.tool(
  "query_emcure_api",
  "Direct query to Emcure API for employee metrics, doctor visits, missed doctors, brands, or employee lists",
  {
    query: z
      .enum(["employee_metrics", "doctor_visits", "missed_doctors", "employee_brands", "get_employees"])
      .describe("Type of data to query from the Emcure API"),
    name: z.string().optional().describe("Employee name (required for most queries)"),
    division: z.string().optional().describe("Division filter"),
    hq: z.string().optional().describe("HQ/city filter"),
    month: z.string().optional().describe("Month name, e.g. January (default: current month)"),
    year: z.string().optional().describe("Year, e.g. 2025 (default: current year)"),
  },
  async ({ query, name, division, hq, month, year }) => {
    try {
      const args = ["--query", query];
      if (name) args.push("--name", name);
      if (division) args.push("--division", division);
      if (hq) args.push("--hq", hq);
      if (month) args.push("--month", month);
      if (year) args.push("--year", year);

      const raw = await runPython("emcure_api.py", args);
      const check = parseAndCheckLoginRequired(raw);
      if (check.loginRequired) return { content: check.content };
      return { content: [{ type: "text", text: raw }] };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Error: ${err.message}` }],
        isError: true,
      };
    }
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  process.stderr.write("medical-rep-tools MCP server v2.0.0 running on stdio\n");
}

main().catch((err) => {
  process.stderr.write(`Fatal: ${err.message}\n`);
  process.exit(1);
});
