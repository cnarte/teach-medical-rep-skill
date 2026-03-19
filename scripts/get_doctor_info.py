#!/usr/bin/env python3
"""
Doctor info lookup. Priority: Emcure API → web search queries → ask MR.
Also parses web search results into structured profiles.

Usage:
    python3 get_doctor_info.py --name "ALKA SEN" --city "Kolkata" --specialty "Gynecologist" --mr-name "Somnath" --lookup
    python3 get_doctor_info.py --name "Dr. X" --city "Kolkata" --specialty "GP" --generate-queries
    python3 get_doctor_info.py --name "Dr. X" --city "Kolkata" --specialty "GP" --search-results '{"practo": "..."}'
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emcure_api import lookup_doctor_by_name


def normalize_name(name):
    return re.sub(r"[\s.]+", " ", name).strip().upper()


def _extract_doctor_from_api(api_result):
    """
    Convert Emcure API doctor data into standard profile format.
    The API returns visit rows or missed-doctor rows with different field names.
    """
    if api_result.get("status") != "found":
        return None

    data = api_result.get("data", {})
    source = api_result.get("source", "emcure_api")

    if isinstance(data, dict):
        doctor = {
            "name": data.get(
                "doctor name", data.get("Doctor Name", data.get("doctor", ""))
            ),
            "specialty": data.get("speciality", data.get("Speciality", "")),
            "qualification": data.get("qualification", data.get("Qualification", "")),
            "potential": data.get("potential", data.get("Potential", "")),
            "city": data.get("area", data.get("Area", data.get("city", ""))),
            "frequency": data.get("frequency", data.get("Frequency", "")),
            "visit_date": data.get("visit date", data.get("Visit Date", "")),
            "clinic": "",
            "hospital_affiliations": [],
            "best_visit_time": "",
            "prescribing_habits": "",
        }
    elif isinstance(data, list) and len(data) > 0:
        row = data[0] if isinstance(data[0], dict) else {}
        doctor = {
            "name": row.get("doctor name", row.get("Doctor Name", "")),
            "specialty": row.get("speciality", row.get("Speciality", "")),
            "qualification": row.get("qualification", row.get("Qualification", "")),
            "potential": row.get("potential", row.get("Potential", "")),
            "city": row.get("area", row.get("Area", "")),
            "frequency": row.get("frequency", row.get("Frequency", "")),
            "visit_date": row.get("visit date", row.get("Visit Date", "")),
            "clinic": "",
            "hospital_affiliations": [],
            "best_visit_time": "",
            "prescribing_habits": "",
        }
    else:
        return None

    return {
        "status": "found",
        "source": source,
        "confidence": "high",
        "doctor": doctor,
    }


def lookup_from_api(doctor_name, mr_name, division=None, hq=None):
    try:
        api_result = lookup_doctor_by_name(doctor_name, mr_name, division, hq)
        if api_result.get("status") == "manual_login_required":
            return api_result, None
        if api_result.get("status") == "found":
            return _extract_doctor_from_api(api_result), None
        return None, api_result.get("message", "Not found in API")
    except Exception as e:
        return None, f"API lookup failed: {e}"


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
    parser.add_argument("--mr-name", help="MR employee name (for API lookup)")
    parser.add_argument("--division", help="Division filter for API")
    parser.add_argument("--hq", help="HQ/city filter for API")
    parser.add_argument(
        "--lookup",
        action="store_true",
        default=False,
        help="Look up doctor in Emcure API first, then suggest web search if not found",
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
            if args.mr_name:
                api_result, api_err = lookup_from_api(
                    args.name, args.mr_name, args.division, args.hq
                )
                if api_result:
                    result = api_result
                else:
                    result = {
                        "status": "not_found_in_api",
                        "message": f"Doctor '{args.name}' not in API data. Use web_search or ask the MR.",
                        "suggested_queries": generate_queries(
                            args.name, args.city, args.specialty
                        )["queries"],
                        "doctor": args.name,
                    }
            else:
                result = {
                    "status": "not_found_in_api",
                    "message": "No --mr-name provided for API lookup. Use web_search or ask the MR.",
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
