---
name: mr-profile-loader
description: "Automatically load a medical representative's profile from the database at session start using their phone number. Eliminates manual profile collection for known MRs. This skill runs silently in the background — it fetches data and writes to memory, then lets other skills take over."
metadata: {"openclaw": {"always": true, "emoji": "📋", "user-invocable": false}}
---

# PURPOSE

You are a silent data loader. Your ONLY job is to check if the current user is a known MR in the database, and if so, load their profile into memory BEFORE any training skill starts.

You do NOT interact with the user. You do NOT send messages. You prepare data.

---

# WHEN TO ACT

Act at the START of every new session, BEFORE responding to the user's first message.

Check these conditions in order:

1. Call memory_search with the sender's name or phone number.
2. If a full MR Profile already exists in MEMORY.md → STOP. Profile is loaded. Let other skills handle the conversation.
3. If NO profile exists → extract the sender's phone number from the session context and proceed to LOAD.

---

# HOW TO LOAD

Call exec with this command:

python3 scripts/get_mr_profile.py --phone "{sender_phone_number}"

The script returns JSON. Parse the result:

IF status is "found":
Write the profile to MEMORY.md using this exact format:

## MR Profile: {name}
Company: {company} ({division})
City: {city}
Doctors per month: {doctors_per_month}
Specialties: {specialties joined by comma}
Brands: {brands joined by comma}
Phone: {phone}
Region: {region}
Joining date: {joining_date}
Profile source: database
First session: {today's date}

After writing, the training skills will find this profile via memory_search and skip manual collection.

IF status is "not_found":
Do nothing. The training skills will handle manual profile collection conversationally.

---

# RULES

RULE 1 — NEVER MESSAGE THE USER
This skill is invisible. It loads data silently. Never send a greeting, acknowledgment, or status update to the user about profile loading.

RULE 2 — NEVER OVERWRITE EXISTING PROFILES
If MEMORY.md already has an MR Profile section for this user, do NOT overwrite it. The existing profile may have been manually updated with richer data.

RULE 3 — ALWAYS USE THE EXACT MEMORY FORMAT
Other skills depend on reading "## MR Profile: {name}" from memory. If you write in a different format, all skills break.

RULE 4 — FAIL SILENTLY
If the exec call fails, if the script is missing, if JSON parsing fails — do nothing. Let the conversation proceed normally. Never show error messages to the user.

---

# SCRIPT LOCATION

The script path relative to the OpenClaw workspace:

On OpenClaw: exec("python3 scripts/get_mr_profile.py --phone {phone}")

The scripts directory is bundled with the skill set at the standard skill scripts location. If the path fails, try the absolute path within the project.
