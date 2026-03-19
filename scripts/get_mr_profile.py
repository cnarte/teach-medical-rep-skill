#!/usr/bin/env python3
"""
Look up MR profile via Emcure API.
Usage: python3 scripts/get_mr_profile.py --phone "+919876543210"
       python3 scripts/get_mr_profile.py --name "Somnath" --division "Pharma" --hq "Kolkata"
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emcure_api import get_employee_metrics, get_employee_brands


def normalize_phone(phone):
    return re.sub(r"[^+\d]", "", phone)


def _extract_profile_from_api(metrics_result, brands_result, phone=None):
    """
    Parse Emcure API NL-to-DAX responses into standard profile format.
    Handles both dict and list response shapes since the API structure varies.
    """
    profile = {}

    if metrics_result.get("status") == "success" and metrics_result.get("result"):
        data = metrics_result["result"]
        if isinstance(data, list) and len(data) > 0:
            row = data[0]
            profile["name"] = row.get("employee", row.get("Employee", ""))
            profile["designation"] = row.get("designation", row.get("Designation", ""))
            profile["l1_employee"] = row.get("l1 employee", row.get("L1 Employee", ""))
            profile["doctors_per_month"] = row.get(
                "total doctors", row.get("Total Doctors", 0)
            )
            profile["met"] = row.get("met", row.get("Met", 0))
            profile["visits"] = row.get("visit", row.get("Visit", 0))
            profile["coverage"] = row.get("coverage", row.get("Coverage", ""))
        elif isinstance(data, dict):
            profile["name"] = data.get("employee", data.get("Employee", ""))
            profile["designation"] = data.get(
                "designation", data.get("Designation", "")
            )
            profile["doctors_per_month"] = data.get(
                "total doctors", data.get("Total Doctors", 0)
            )
            profile["coverage"] = data.get("coverage", data.get("Coverage", ""))

    brands_list = []
    if brands_result.get("status") == "success" and brands_result.get("result"):
        data = brands_result["result"]
        if isinstance(data, list):
            for row in data:
                brand = row.get("brand", row.get("Brand", row.get("brands", "")))
                if brand:
                    brands_list.append(brand)
        elif isinstance(data, dict):
            for val in data.values():
                if val and isinstance(val, str):
                    brands_list.append(val)

    if profile.get("name"):
        return {
            "status": "found",
            "source": "emcure_api",
            "profile": {
                "name": profile.get("name", ""),
                "designation": profile.get("designation", ""),
                "l1_employee": profile.get("l1_employee", ""),
                "doctors_per_month": profile.get("doctors_per_month", 0),
                "met": profile.get("met", 0),
                "visits": profile.get("visits", 0),
                "coverage": profile.get("coverage", ""),
                "brands": brands_list,
                "phone": phone or "",
            },
        }
    return None


def lookup_from_api(name, division=None, hq=None, phone=None):
    try:
        metrics = get_employee_metrics(name, division, hq)
        if metrics.get("status") == "manual_login_required":
            return metrics, None
        brands = get_employee_brands(name, division, hq)
        if brands.get("status") == "manual_login_required":
            return brands, None
        result = _extract_profile_from_api(metrics, brands, phone)
        if result:
            return result, None
        return None, "Employee not found in API response"
    except Exception as e:
        return None, f"API lookup failed: {e}"


def lookup_profile(phone=None, name=None, division=None, hq=None):
    if name:
        api_result, api_err = lookup_from_api(name, division, hq, phone)
        if api_result:
            return api_result
        return {"status": "not_found", "name": name, "error": api_err}

    if phone:
        return {
            "status": "not_found",
            "phone": normalize_phone(phone),
            "message": "Phone-only lookup requires --name. Provide the MR's name for API query.",
        }

    return {
        "status": "error",
        "message": "Provide --name (and optionally --phone, --division, --hq)",
    }


def main():
    parser = argparse.ArgumentParser(description="Look up MR profile via Emcure API.")
    parser.add_argument("--phone", help='Phone in E.164 format, e.g. "+919876543210"')
    parser.add_argument(
        "--name", required=True, help="Employee name for Emcure API lookup"
    )
    parser.add_argument("--division", help="Division filter for API")
    parser.add_argument("--hq", help="HQ/city filter for API")
    args = parser.parse_args()

    try:
        result = lookup_profile(
            phone=args.phone, name=args.name, division=args.division, hq=args.hq
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
