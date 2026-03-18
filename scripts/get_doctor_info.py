#!/usr/bin/env python3
"""
Doctor info lookup. Priority: Google Sheet → web search queries → ask MR.
Also parses web search results into structured profiles.

Usage:
    python3 get_doctor_info.py --name "ALKA . SEN" --city "Kolkata" --specialty "Gynecologist" --lookup
    python3 get_doctor_info.py --name "Dr. X" --city "Kolkata" --specialty "GP" --generate-queries
    python3 get_doctor_info.py --name "Dr. X" --city "Kolkata" --specialty "GP" --search-results '{"practo": "..."}'
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sheets_config import read_sheet_csv, DOCTOR_SHEET_GID


def normalize_name(name):
    return re.sub(r"[\s.]+", " ", name).strip().upper()


def lookup_from_sheet(name, city=None, specialty=None):
    rows, err = read_sheet_csv(gid=DOCTOR_SHEET_GID)
    if err or rows is None:
        return None, f"Sheet read failed: {err}"

    name_norm = normalize_name(name)
    matches = []

    for row in rows:
        row_name = normalize_name(row.get("Doctor", ""))
        if name_norm == row_name or name_norm in row_name or row_name in name_norm:
            matches.append(row)

    if not matches:
        return None, "Not found in doctor sheet"

    # Deduplicate — same doctor has multiple visit rows. Take first for profile, aggregate visits.
    first = matches[0]
    visit_dates = sorted(
        set(
            row.get("Visit Date", "").split("T")[0]
            for row in matches
            if row.get("Visit Date")
        )
    )

    doctor = {
        "name": first.get("Doctor", ""),
        "specialty": first.get("Speciality", ""),
        "qualification": first.get("Qualification", ""),
        "potential": first.get("Potential", ""),
        "city": first.get("Area Patch", city or ""),
        "frequency": first.get("Frequency Name", ""),
        "total_visits_in_data": len(matches),
        "recent_visit_dates": visit_dates[-5:],
        "clinic": "",
        "hospital_affiliations": [],
        "best_visit_time": "",
        "prescribing_habits": "",
    }

    return {
        "status": "found",
        "source": "google_sheet",
        "confidence": "high",
        "doctor": doctor,
    }, None


def generate_queries(name, city, specialty):
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


def extract_clinic(text, name, city):
    patterns = [
        r"(?:clinic|practice|chamber)[:\s]+([A-Z][A-Za-z\s&'.,-]+)",
        r"(?:at|visits?)\s+([A-Z][A-Za-z\s&'.,-]{3,40}(?:Clinic|Hospital|Centre|Center|Chamber))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def extract_hospitals(text):
    patterns = [
        r"(?:affiliated?|associated|attached|works?\s+at|visits?)\s+(?:with\s+)?([A-Z][A-Za-z\s&'.,-]{3,50}(?:Hospital|Medical|Institute|Centre|Center))",
    ]
    hospitals = []
    for pattern in patterns:
        hospitals.extend(m.strip() for m in re.findall(pattern, text, re.IGNORECASE))
    return list(set(hospitals))


def extract_visit_time(text):
    patterns = [
        r"(?:OPD|visiting|consultation|available|timing)[:\s]+(\d{1,2}[\s:.-]*(?:am|pm|AM|PM)[\s]*(?:to|-)[\s]*\d{1,2}[\s:.-]*(?:am|pm|AM|PM))",
        r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\s*(?:to|-)\s*\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def extract_nmc_registration(text):
    patterns = [
        r"(?:registration|reg\.?\s*(?:no|number|#)|NMC|MCI)[:\s]+([A-Z]{2,5}[-/]?\d{3,10})",
        r"\b([A-Z]{2,4}[-/]\d{4,10})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""


def parse_search_results(name, city, specialty, search_results):
    all_text = " ".join(str(v) for v in search_results.values() if v)

    clinic = extract_clinic(all_text, name, city)
    hospitals = extract_hospitals(all_text)
    visit_time = extract_visit_time(all_text)
    nmc_reg = extract_nmc_registration(all_text)

    doctor = {
        "name": name,
        "specialty": specialty,
        "city": city,
        "clinic": clinic or "Not found — ask MR",
        "hospital_affiliations": hospitals,
        "best_visit_time": visit_time or "Not found — ask MR",
        "prescribing_habits": "Not yet collected — gather from MR conversations",
        "nmc_registration": nmc_reg or "Not found — verify via NMC portal",
    }

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


def main():
    parser = argparse.ArgumentParser(description="Look up or enrich doctor profile.")
    parser.add_argument("--name", required=True, help="Doctor name")
    parser.add_argument("--city", required=True, help="City")
    parser.add_argument("--specialty", required=True, help="Specialty")
    parser.add_argument(
        "--lookup",
        action="store_true",
        default=False,
        help="Look up doctor in Google Sheet first, then suggest web search if not found",
    )
    parser.add_argument(
        "--generate-queries",
        action="store_true",
        default=False,
        help="Return web search queries for the agent",
    )
    parser.add_argument(
        "--search-results",
        type=str,
        default=None,
        help="JSON string of pre-fetched search results to parse",
    )
    args = parser.parse_args()

    try:
        if args.lookup:
            sheet_result, sheet_err = lookup_from_sheet(
                args.name, args.city, args.specialty
            )
            if sheet_result:
                result = sheet_result
            else:
                result = {
                    "status": "not_found_in_sheet",
                    "message": f"Doctor '{args.name}' not in sheet. Use web_search or ask the MR.",
                    "suggested_queries": generate_queries(
                        args.name, args.city, args.specialty
                    )["queries"],
                    "doctor": args.name,
                }
        elif args.generate_queries:
            result = generate_queries(args.name, args.city, args.specialty)
        elif args.search_results:
            try:
                search_data = json.loads(args.search_results)
            except json.JSONDecodeError as exc:
                print(
                    json.dumps({"status": "error", "message": f"Invalid JSON: {exc}"})
                )
                return 1
            result = parse_search_results(
                args.name, args.city, args.specialty, search_data
            )
        else:
            result = generate_queries(args.name, args.city, args.specialty)

        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
