#!/usr/bin/env python3
"""
Enrich a doctor's profile using search data or generate search queries for the agent.

Two modes of operation:

1. Generate queries (agent calls web_search with these):
   python3 scripts/get_doctor_info.py --name "Dr. Rina Mukherjee" --city "Kolkata" --specialty "Gynecologist" --generate-queries

2. Parse pre-fetched search results into structured profile:
   python3 scripts/get_doctor_info.py --name "Dr. Rina Mukherjee" --city "Kolkata" --specialty "Gynecologist" --search-results '{"practo": "...", "nmc": "...", "justdial": "..."}'

Outputs JSON to stdout.
"""

import argparse
import json
import re
import sys


def generate_queries(name: str, city: str, specialty: str) -> dict:
    """Generate search queries the agent should execute via web_search."""
    base = f"{name} {specialty} {city}"
    queries = [
        f"{base} Practo",
        f"{base} hospital affiliation",
        f"{name} NMC register doctor",
        f"{name} {city} clinic address",
        f"{base} JustDial",
        f"{name} {city} visiting hours OPD timing",
    ]
    return {"status": "queries_generated", "queries": queries, "doctor": name}


def extract_clinic(text: str, name: str, city: str) -> str:
    """Try to extract clinic name from search result text."""
    patterns = [
        r"(?:clinic|practice|chamber)[:\s]+([A-Z][A-Za-z\s&'.,-]+)",
        r"(?:at|visits?)\s+([A-Z][A-Za-z\s&'.,-]{3,40}(?:Clinic|Hospital|Centre|Center|Chamber))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def extract_hospitals(text: str) -> list:
    """Try to extract hospital affiliations from text."""
    hospitals = []
    patterns = [
        r"(?:affiliated?|associated|attached|works?\s+at|visits?)\s+(?:with\s+)?([A-Z][A-Za-z\s&'.,-]{3,50}(?:Hospital|Medical|Institute|Centre|Center))",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        hospitals.extend(m.strip() for m in matches)
    return list(set(hospitals)) if hospitals else []


def extract_visit_time(text: str) -> str:
    """Try to extract best visit / OPD timing from text."""
    patterns = [
        r"(?:OPD|visiting|consultation|available|timing)[:\s]+(\d{1,2}[\s:.-]*(?:am|pm|AM|PM)[\s]*(?:to|-)[\s]*\d{1,2}[\s:.-]*(?:am|pm|AM|PM))",
        r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\s*(?:to|-)\s*\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def extract_nmc_registration(text: str) -> str:
    """Try to extract NMC / MCI registration number."""
    patterns = [
        r"(?:registration|reg\.?\s*(?:no|number|#)|NMC|MCI)[:\s]+([A-Z]{2,5}[-/]?\d{3,10})",
        r"\b([A-Z]{2,4}[-/]\d{4,10})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def parse_search_results(
    name: str, city: str, specialty: str, search_results: dict
) -> dict:
    """Parse pre-fetched search results into a structured doctor profile."""
    all_text = " ".join(str(v) for v in search_results.values() if v)

    clinic = extract_clinic(all_text, name, city)
    hospitals = extract_hospitals(all_text)
    visit_time = extract_visit_time(all_text)
    nmc_reg = extract_nmc_registration(all_text)

    # Build profile with whatever we could extract
    doctor = {
        "name": name,
        "specialty": specialty,
        "city": city,
        "clinic": clinic if clinic else "Not found — ask MR for details",
        "hospital_affiliations": hospitals if hospitals else [],
        "best_visit_time": visit_time
        if visit_time
        else "Not found — ask MR for details",
        "prescribing_habits": "Not yet collected — gather from MR conversations",
        "nmc_registration": nmc_reg if nmc_reg else "Not found — verify via NMC portal",
    }

    # Determine confidence based on how many fields we extracted
    filled = sum(
        1
        for k in [
            "clinic",
            "hospital_affiliations",
            "best_visit_time",
            "nmc_registration",
        ]
        if doctor[k] and "Not found" not in str(doctor[k]) and doctor[k] != []
    )
    confidence = "high" if filled >= 3 else "medium" if filled >= 1 else "low"

    return {
        "status": "found",
        "confidence": confidence,
        "doctor": doctor,
        "fields_extracted": filled,
        "fields_total": 4,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enrich a doctor's profile from search data or generate search queries."
    )
    parser.add_argument(
        "--name",
        required=True,
        help='Doctor name, e.g. "Dr. Rina Mukherjee"',
    )
    parser.add_argument(
        "--city",
        required=True,
        help='City, e.g. "Kolkata"',
    )
    parser.add_argument(
        "--specialty",
        required=True,
        help='Specialty, e.g. "Gynecologist"',
    )
    parser.add_argument(
        "--generate-queries",
        action="store_true",
        default=False,
        help="Return search queries for the agent to execute via web_search",
    )
    parser.add_argument(
        "--search-results",
        type=str,
        default=None,
        help="JSON string of pre-fetched search results to parse into a profile",
    )

    args = parser.parse_args()

    try:
        if args.generate_queries:
            result = generate_queries(args.name, args.city, args.specialty)
        elif args.search_results:
            try:
                search_data = json.loads(args.search_results)
            except json.JSONDecodeError as exc:
                print(
                    json.dumps(
                        {
                            "status": "error",
                            "message": f"Invalid JSON in --search-results: {exc}",
                        }
                    )
                )
                return 1
            result = parse_search_results(
                args.name, args.city, args.specialty, search_data
            )
        else:
            # Default: generate queries so the agent knows what to search
            result = generate_queries(args.name, args.city, args.specialty)

        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
