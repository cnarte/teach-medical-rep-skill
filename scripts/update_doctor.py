#!/usr/bin/env python3
"""
Update a doctor's profile in the MEMORY.md file with new information
from MR conversation notes or structured field updates.

Called via OpenClaw exec tool or wrapped as MCP tool for Claude Code.

Usage:
    python3 update_doctor.py --doctor "Dr. Rina Mukherjee" --field "prescribing_habits" --value "Prefers Orofer-XT for severe anemia"
    python3 update_doctor.py --doctor "Dr. Rina Mukherjee" --notes "Mentioned she prefers once-daily dosing"
    python3 update_doctor.py --doctor "Dr. Rina Mukherjee" --field "best_visit_time" --value "10am-12pm" --memory-file "/path/to/MEMORY.md"
"""

import argparse
import json
import os
import re
import sys
from datetime import date


DEFAULT_MEMORY_FILE = os.path.expanduser("~/.openclaw/workspace/MEMORY.md")

DOCTOR_TEMPLATE = """## Doctor: {name}
Specialty: {specialty}
City: {city}
Clinic: 
Hospital: 
Best visit time: 
Prescribing habits: 
NMC Registration: 
### MR Notes
"""

FIELD_MAP = {
    "specialty": "Specialty",
    "city": "City",
    "clinic": "Clinic",
    "hospital": "Hospital",
    "hospital_affiliations": "Hospital",
    "best_visit_time": "Best visit time",
    "prescribing_habits": "Prescribing habits",
    "nmc_registration": "NMC Registration",
    "qualifications": "Qualifications",
    "experience_years": "Experience",
    "consultation_fee": "Consultation fee",
}


def read_memory(filepath):
    """Read memory file, create if doesn't exist."""
    if not os.path.exists(filepath):
        directory = os.path.dirname(filepath)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        with open(filepath, "w") as f:
            f.write("# MEMORY.md - Long-Term Memory\n\n")
        return "# MEMORY.md - Long-Term Memory\n\n"
    with open(filepath, "r") as f:
        return f.read()


def write_memory(filepath, content):
    """Write updated content to memory file."""
    with open(filepath, "w") as f:
        f.write(content)


def find_doctor_section(content, doctor_name):
    """Find the start and end of a doctor's section in memory."""
    pattern = rf"## Doctor: {re.escape(doctor_name)}"
    match = re.search(pattern, content, re.IGNORECASE)
    if not match:
        return None, None

    start = match.start()
    # Find the next ## section or end of file
    next_section = re.search(r"\n## (?!#)", content[match.end() :])
    if next_section:
        end = match.end() + next_section.start()
    else:
        end = len(content)

    return start, end


def update_field(content, doctor_name, field, value, memory_file):
    """Update a specific field in a doctor's profile."""
    start, end = find_doctor_section(content, doctor_name)
    previous_value = ""

    if start is None:
        # Doctor doesn't exist — create new section
        display_field = FIELD_MAP.get(field, field.replace("_", " ").title())
        new_section = (
            f"\n## Doctor: {doctor_name}\n{display_field}: {value}\n### MR Notes\n"
        )
        content = content.rstrip() + "\n" + new_section
        write_memory(memory_file, content)
        return {
            "status": "created",
            "doctor": doctor_name,
            "field": field,
            "new_value": value,
        }

    section = content[start:end]
    display_field = FIELD_MAP.get(field, field.replace("_", " ").title())

    # Try to find and update the field
    field_pattern = rf"({re.escape(display_field)}:\s*)(.*)"
    field_match = re.search(field_pattern, section, re.IGNORECASE)

    if field_match:
        previous_value = field_match.group(2).strip()
        updated_section = (
            section[: field_match.start()]
            + f"{display_field}: {value}"
            + section[field_match.end() :]
        )
    else:
        # Field doesn't exist in section — add before MR Notes or at end
        notes_match = re.search(r"### MR Notes", section)
        if notes_match:
            insert_pos = notes_match.start()
            updated_section = (
                section[:insert_pos]
                + f"{display_field}: {value}\n"
                + section[insert_pos:]
            )
        else:
            updated_section = section.rstrip() + f"\n{display_field}: {value}\n"

    content = content[:start] + updated_section + content[end:]
    write_memory(memory_file, content)

    return {
        "status": "updated",
        "doctor": doctor_name,
        "field": field,
        "previous_value": previous_value,
        "new_value": value,
    }


def append_notes(content, doctor_name, notes, memory_file):
    """Append conversation notes to a doctor's MR Notes section."""
    today = date.today().isoformat()
    note_entry = f"- {today}: {notes}"

    start, end = find_doctor_section(content, doctor_name)

    if start is None:
        # Doctor doesn't exist — create with notes
        new_section = f"\n## Doctor: {doctor_name}\n### MR Notes\n{note_entry}\n"
        content = content.rstrip() + "\n" + new_section
        write_memory(memory_file, content)
        return {
            "status": "created_with_notes",
            "doctor": doctor_name,
            "note": note_entry,
        }

    section = content[start:end]
    notes_match = re.search(r"### MR Notes\n?", section)

    if notes_match:
        insert_pos = start + notes_match.end()
        content = content[:insert_pos] + note_entry + "\n" + content[insert_pos:]
    else:
        # No MR Notes section — add one
        end_of_section = end
        content = (
            content[:end_of_section].rstrip()
            + f"\n### MR Notes\n{note_entry}\n"
            + content[end_of_section:]
        )

    write_memory(memory_file, content)
    return {"status": "note_added", "doctor": doctor_name, "note": note_entry}


def main():
    parser = argparse.ArgumentParser(
        description="Update a doctor's profile in MEMORY.md"
    )
    parser.add_argument("--doctor", required=True, help="Doctor's full name")
    parser.add_argument(
        "--field", help="Field to update (e.g., prescribing_habits, best_visit_time)"
    )
    parser.add_argument("--value", help="New value for the field")
    parser.add_argument("--notes", help="Freeform conversation notes to append")
    parser.add_argument(
        "--memory-file",
        default=DEFAULT_MEMORY_FILE,
        help=f"Path to MEMORY.md (default: {DEFAULT_MEMORY_FILE})",
    )
    args = parser.parse_args()

    if not args.field and not args.notes:
        print(
            json.dumps(
                {"status": "error", "message": "Provide --field + --value or --notes"}
            )
        )
        sys.exit(1)

    if args.field and not args.value:
        print(json.dumps({"status": "error", "message": "--field requires --value"}))
        sys.exit(1)

    try:
        content = read_memory(args.memory_file)

        if args.notes:
            result = append_notes(content, args.doctor, args.notes, args.memory_file)
        else:
            result = update_field(
                content, args.doctor, args.field, args.value, args.memory_file
            )

        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
