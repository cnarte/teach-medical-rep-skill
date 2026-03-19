---
name: mr-profile-loader
description: "Silently fetch and persist a medical representative's profile from the Emcure API on their very first session. Writes a permanent MR Profile block to MEMORY.md that all training skills read. Never runs again once that block exists."
metadata: {"openclaw": {"always": true, "emoji": "📋", "user-invocable": false}}
---

# PURPOSE

You are a one-time silent data loader. Your ONLY job is to fetch the MR's basic profile from the Emcure API on their very first session and write it permanently to MEMORY.md.

You do NOT interact with the user. You do NOT send messages. You run once and never again.

---

# WHEN TO ACT

Act at the START of every new session. Check ONE condition first:

1. Call `memory_search` with the sender's name or phone number.
2. If `## MR Profile:` block ALREADY EXISTS in MEMORY.md → **STOP IMMEDIATELY.** Do nothing. Profile is permanent — never re-fetch, never overwrite.
3. If NO profile exists → this is their first session. Proceed to LOAD.

This check prevents redundant API calls on every session. The profile is fetched exactly once.

---

# HOW TO LOAD

Extract the MR's name from the session context (their greeting, contact name, or any prior message). If you also know their division or city, include those.

Call exec with:

```
python3 scripts/get_mr_profile.py --name "{mr_name}"
```

With optional filters for more precise results:

```
python3 scripts/get_mr_profile.py --name "{mr_name}" --division "{division}" --hq "{city}"
```

The script returns JSON. Parse the result:

**IF `status` is `"found"`:**
Write the profile permanently to MEMORY.md using this EXACT format:

```
## MR Profile: {name}
Designation: {designation}
L1 Manager: {l1_employee}
Doctors per month: {doctors_per_month}
Met: {met}
Visits: {visits}
Coverage: {coverage}
Brands: {brands joined by comma}
Phone: {phone}
Profile source: emcure_api
First session: {today's date}
```

**IF `status` is `"not_found"`:**
Do nothing. Training skills will collect the profile conversationally.

**IF `status` is `"manual_login_required"`:**
Write this note to MEMORY.md so other skills know:

```
## Emcure API Status
Status: manual login required
Note: Admin must log into the Emcure Super AI portal to activate API access.
```

Training skills will collect profile conversationally until API is available.

---

# RULES

RULE 1 — NEVER RUN IF PROFILE EXISTS
If `## MR Profile:` appears anywhere in MEMORY.md, stop immediately. Do not call the API, do not overwrite anything.

RULE 2 — NEVER MESSAGE THE USER
This skill is invisible. It loads data silently. Never send a greeting, acknowledgment, or status update.

RULE 3 — NEVER OVERWRITE EXISTING PROFILES
The profile block is permanent. Only the MR themselves or a manual admin update should change it.

RULE 4 — EXACT MEMORY FORMAT
Other skills depend on reading `## MR Profile: {name}` from memory. Wrong format breaks all skills.

RULE 5 — FAIL SILENTLY
If exec fails, JSON parsing fails, or the script is missing — do nothing. Let the conversation proceed normally.

---

# SCRIPT LOCATION

On OpenClaw: `exec("python3 scripts/get_mr_profile.py --name {name} --division {division} --hq {hq}")`
On Claude Code: use the `get_mr_profile` MCP tool.
