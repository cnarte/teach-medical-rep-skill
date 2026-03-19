# Emcure Pharma Sales Copilot

A WhatsApp-native AI coaching system for pharmaceutical medical representatives. Combines real field data from the Emcure Super AI API with conversational training to deliver personalized coaching, doctor visit preparation, objection handling practice, and product deep-dives.

---

## What It Does

- **First session**: Silently fetches the MR's profile from the Emcure API and builds a language profile from their messages
- **Every session**: Reads persistent memory, fetches only what the current conversation needs (visits, metrics, missed doctors)
- **Dynamically routes**: Infers from what the MR says whether they need field coaching, roleplay, objection practice, or product Q&A — never asks them to pick from a menu
- **Data discipline**: Doctor/MR data always from Emcure API. Medicine/clinical data always from web search. Never crossed.

---

## Prerequisites

- **OpenClaw** (for WhatsApp deployment) or **Claude Code** (for desktop use)
- Python 3.8+
- Node.js 18+ (for the MCP server, Claude Code only)
- Access to the Emcure Super AI Data Apps API (pre-prod environment)
- One-time manual login to the Emcure Super AI web portal to activate API access

---

## File Structure

```
/
├── SKILL.md                      ← Main orchestrator skill (install this first)
├── README.md                     ← This file
├── field-coaching/SKILL.md       ← Territory, daily planning, coverage coaching
├── doctor-roleplay/SKILL.md      ← Doctor call practice with realistic personas
├── objection-handler/SKILL.md    ← Handle doctor pushback, two-response method
├── qna-mode/SKILL.md             ← Quick product and strategy Q&A
├── product-deepdive/SKILL.md     ← 5-part product learning with quiz
├── language-engine/SKILL.md      ← Language detection and preference management
├── mr-profile-loader/SKILL.md    ← Silent one-time MR profile prefetch
├── scripts/
│   ├── emcure_api.py             ← Emcure API client
│   ├── get_mr_profile.py         ← MR profile lookup
│   ├── get_doctor_info.py        ← Doctor info from visit data
│   └── update_doctor.py          ← Write doctor notes to memory
└── mcp-server/
    ├── index.js                  ← MCP server (Claude Code only)
    └── package.json
```

---

## Setup: OpenClaw

### 1. Install all skills

Copy all skill directories to your OpenClaw skills folder:

```bash
for skill in SKILL.md field-coaching doctor-roleplay objection-handler qna-mode product-deepdive language-engine mr-profile-loader; do
  cp -r "$skill" ~/.openclaw/skills/
done
```

Or copy the whole project directory and symlink:

```bash
cp -r . ~/.openclaw/skills/pharma-copilot/
```

### 2. Copy scripts

The `scripts/` directory must be accessible from the OpenClaw workspace. Copy it alongside your skills:

```bash
cp -r scripts/ ~/.openclaw/workspace/scripts/
```

### 3. Enable required tools in OpenClaw config

The following tools must be enabled for the agent:

```yaml
tools:
  exec: true           # Required — runs Python scripts for API calls
  web_search: true     # Required — fetches medicine/clinical data
  memory_search: true  # Required — reads persistent MR profiles
  memory_get: true     # Required — reads stored memory blocks
  message: true        # Required — react and poll actions
```

### 4. Verify Python scripts work

```bash
python3 scripts/get_mr_profile.py --name "Test User"
# Expected: {"status": "not_found", ...} or {"status": "manual_login_required", ...}

python3 scripts/get_doctor_info.py --name "Dr. Test" --city "Mumbai" --specialty "GP" --generate-queries
# Expected: {"status": "queries_generated", "queries": [...]}
```

### 5. Manual portal login (one-time)

The Emcure API requires a one-time manual login to the Super AI web portal before `executeQueryV2` queries work. After login, the scripts will function automatically. Until then, the agent falls back to conversational profile collection.

---

## Setup: Claude Code (MCP)

### 1. Install MCP server dependencies

```bash
cd mcp-server
npm install
```

### 2. Configure `.mcp.json`

The `.mcp.json` file is already configured in the project root. Verify the path is correct:

```json
{
  "mcpServers": {
    "medical-rep-tools": {
      "command": "node",
      "args": ["mcp-server/index.js"]
    }
  }
}
```

### 3. Verify MCP server starts

```bash
node mcp-server/index.js
# Expected: "medical-rep-tools MCP server v2.0.0 running on stdio"
```

### 4. Available MCP tools

| Tool | Purpose |
|---|---|
| `get_mr_profile` | Fetch MR profile by name (+ optional division, hq) |
| `get_doctor_info` | Look up doctor in visit/missed data, generate web queries, parse search results |
| `update_doctor` | Write doctor notes to MEMORY.md |
| `query_emcure_api` | Direct query: employee_metrics, doctor_visits, missed_doctors, employee_brands, get_employees |

---

## API Credentials

The Emcure Super AI API credentials are configured via environment variables. **You must obtain the credentials from the project maintainer** before the system will work.

| Environment Variable | Purpose | Required |
|---|---|---|
| `EMCURE_API_KEY` | App-level authentication for all API calls | ✅ Yes |
| `EMCURE_AUTH_EMAIL` | User identity for token generation | ✅ Yes |
| `EMCURE_AUTH_HASH` | Credential hash for token generation | ✅ Yes |
| `EMCURE_AGENT_ID` | Identifies the Emcure data agent to query | ✅ Yes |
| `EMCURE_BASE_URL` | API base URL (optional, has default) | ❌ No |

### Getting Your Credentials

**Contact the project maintainer** to request the Emcure API credentials. You will receive:
- `EMCURE_API_KEY`
- `EMCURE_AUTH_EMAIL`
- `EMCURE_AUTH_HASH`
- `EMCURE_AGENT_ID`

Do NOT check these into version control. Store them securely and set them as environment variables only.

### Setting Environment Variables (After Receiving Credentials)

Once you receive the credentials from the maintainer, make them available to your scripts by adding them to your shell profile:

#### For Bash users (~/.bashrc or ~/.bash_profile):
```bash
export EMCURE_API_KEY="[ask-maintainer-for-value]"
export EMCURE_AUTH_EMAIL="[ask-maintainer-for-value]"
export EMCURE_AUTH_HASH="[ask-maintainer-for-value]"
export EMCURE_AGENT_ID="[ask-maintainer-for-value]"
export EMCURE_BASE_URL="https://super-ai-data-apps-api-pre-prod.azurewebsites.net"
```

Then run:
```bash
source ~/.bashrc
```

#### For Zsh users (~/.zshrc):
```bash
export EMCURE_API_KEY="[ask-maintainer-for-value]"
export EMCURE_AUTH_EMAIL="[ask-maintainer-for-value]"
export EMCURE_AUTH_HASH="[ask-maintainer-for-value]"
export EMCURE_AGENT_ID="[ask-maintainer-for-value]"
export EMCURE_BASE_URL="https://super-ai-data-apps-api-pre-prod.azurewebsites.net"
```

Then run:
```bash
source ~/.zshrc
```

#### For OpenClaw specifically:
If you're running from a terminal, either:
1. Source your profile first: `source ~/.bashrc` (or ~/.zshrc)
2. Or set them inline: `EMCURE_API_KEY="[value]" python3 scripts/emcure_api.py ...`
3. Or add exports to OpenClaw's startup environment

#### Verify Variables Are Set:
```bash
echo $EMCURE_API_KEY
echo $EMCURE_AUTH_EMAIL
```

If they're empty, you haven't set the environment variables yet. Contact the maintainer for credentials and try again.

### Token caching

Auth tokens are cached in `scripts/.emcure_token_cache.json` for 55 minutes. This file is gitignored. Delete it to force a fresh token fetch.

---

## How the System Works

### Session start

```
MR sends first message
       ↓
pharma-copilot (always-on) runs
       ↓
memory_search → profile found?
       │
       ├── YES → read profile + language profile → route based on message intent
       │
       └── NO → exec get_mr_profile.py (silent) → write to MEMORY.md
                        ↓
               language-engine: use name + HQ to infer language immediately
               (Subramaniam + Chennai → Tamil-English, Patel + Ahmedabad → Gujarati-English)
                        ↓
               Greet MR in their inferred language
                        ↓
               After 2-3 messages: refine Language Profile from actual text
```

### Dynamic routing (no menus, ever)

Routing is intent-based, not keyword-based. The same intents are detected in Hindi, Tamil, Bengali, Kannada, Telugu, Marathi, Gujarati, Malayalam, or English.

```
MR message → pharma-copilot reads INTENT
       │
       ├── Thinking about field work: today's plan, territory, doctors to visit,
       │   coverage gaps, route, RCPA, daily targets
       │     → field-coaching mode
       │         exec: employee_metrics + missed_doctors
       │
       ├── Doctor pushed back: competitor mentioned, price objection, asked for
       │   studies, said no, loyal to another brand
       │     → objection-handler mode
       │         exec: employee_brands
       │         web_search: clinical/competitor data
       │
       ├── Wants to practice: simulate a call, rehearse their pitch,
       │   mock doctor cabin scenario, get feedback
       │     → doctor-roleplay mode
       │         exec: doctor_visits
       │
       ├── Needs a quick answer: product question, composition, what to say,
       │   clinical comparison, data, side effects
       │     → qna-mode
       │         web_search: medicine/clinical only
       │
       └── Wants full learning: deep dive, teach me everything, part by part,
             quiz me, structured product knowledge
             → product-deepdive mode
                 exec: employee_brands
                 web_search: all product content
```

### Memory model

```
MEMORY.md (persistent, never re-fetched)
├── ## MR Profile: {name}          ← written once by pharma-copilot / mr-profile-loader
└── ### Language Profile            ← written once by language-engine

memory/YYYY-MM-DD.md (session logs)
├── Field Coaching: {name}
├── Roleplay: {name} - {specialty} doctor
├── Objection Practice: {name}
├── QnA: {name}
└── Deep-dive: {name} - {brand}
```

### Data sources

| Data | Source | Never use |
|---|---|---|
| MR profile, designation, brands | Emcure API (`get_mr_profile.py`) | web_search |
| Doctor names, speciality, visit dates | Emcure API (`emcure_api.py doctor_visits`) | web_search |
| Missed doctors | Emcure API (`emcure_api.py missed_doctors`) | web_search |
| Coverage %, met count, KPIs | Emcure API (`emcure_api.py employee_metrics`) | web_search |
| Drug MOA, clinical trials | web_search | Emcure API |
| Competitor comparisons | web_search | Emcure API |
| Drug pricing, side effects | web_search | Emcure API |

---

## Troubleshooting

**API returns `manual_login_required`**
The Emcure Super AI portal requires a one-time manual browser login. After logging in, retry. The agent falls back to conversational profile collection until login is completed.

**Token cache stale after login**
```bash
rm scripts/.emcure_token_cache.json
```

**MCP server not found**
Verify `node mcp-server/index.js` runs without error. Check Node.js version is 18+. Run `npm install` in `mcp-server/`.

**Skills not loading in OpenClaw**
Confirm all skill directories are in `~/.openclaw/skills/`. Each directory must contain a `SKILL.md` with valid frontmatter (`name`, `description`, `metadata`).

**Script path errors in exec calls**
Scripts must be in the working directory OpenClaw uses for exec. Confirm `scripts/` is at `~/.openclaw/workspace/scripts/` or adjust paths in SKILL.md exec commands.

---

## Emcure API — Available Queries

Once portal login is active, these queries work via `scripts/emcure_api.py`:

```bash
# MR performance metrics (coverage %, met, visits)
python3 scripts/emcure_api.py --query employee_metrics --name "Sunil Shinde" --division "Pharma" --hq "Pune"

# Doctors not visited this period
python3 scripts/emcure_api.py --query missed_doctors --name "Sunil Shinde" --division "Pharma" --hq "Pune"

# All visited doctors with area, frequency, potential
python3 scripts/emcure_api.py --query doctor_visits --name "Sunil Shinde" --division "Pharma" --hq "Pune"

# Brands assigned to MR
python3 scripts/emcure_api.py --query employee_brands --name "Sunil Shinde" --division "Pharma" --hq "Pune"

# All employees in a division/HQ
python3 scripts/emcure_api.py --query get_employees --division "Pharma" --hq "Pune"

# Look up a specific doctor in visit data
python3 scripts/get_doctor_info.py --lookup --name "Dr. Sharma" --mr-name "Sunil Shinde" --city "Pune" --specialty "Gynecologist"
```

---

## Test Users

| Name | Phone | Division | City |
|---|---|---|---|
| Ankit Patel | +919939086064 | Diabetology | Ahmedabad |
| Saurabh Moody | +14088278101 | Oncology | Noida |
