#!/usr/bin/env python3
"""
Unified Emcure Super AI Data Apps API client.

Wraps the Power BI-backed NL→DAX query API with:
- 2-step token management (getUserToken → Bearer + data-source-token)
- Token caching with automatic refresh
- 5 query functions matching the Postman collection patterns
- Error handling with structured JSON output

Usage as library:
    from emcure_api import EmcureAPI
    api = EmcureAPI()
    result = api.get_employee_metrics(name="Somnath", division="Pharma", hq="Kolkata")

Usage as CLI:
    python3 emcure_api.py --query employee_metrics --name "Somnath" --division "Pharma" --hq "Kolkata"
    python3 emcure_api.py --query doctor_visits --name "Somnath" --division "Pharma" --hq "Kolkata"
    python3 emcure_api.py --query missed_doctors --name "Somnath" --division "Pharma" --hq "Kolkata"
    python3 emcure_api.py --query employee_brands --name "Somnath" --division "Pharma" --hq "Kolkata"
    python3 emcure_api.py --query get_employees --division "Pharma" --hq "Kolkata"
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

# ── API Configuration ─────────────────────────────────────────────────────────

BASE_URL = "https://super-ai-data-apps-api-pre-prod.azurewebsites.net"
TOKEN_ENDPOINT = f"{BASE_URL}/api/v1/api-token-manager/getUserToken"
QUERY_ENDPOINT = f"{BASE_URL}/super-report/executeQueryV2"

API_KEY = "1f3b0412d26e714ba4e21f10e75429b9ee5b333691f5fc9c0c17284164e270b3"
AUTH_EMAIL = "aryan.patel@emcure.com"
AUTH_HASH = "a3f1c9e0b47d6f2a9b8c0d3e"
AGENT_ID = (
    "ea8428a4ee64653862f22654268d3bbe322ef19f.1719eef7-6a27-40ff-bbac-5ab0b1e4251f"
)

# Token cache file (avoids re-auth on every script call)
TOKEN_CACHE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".emcure_token_cache.json"
)

# Token validity duration in seconds (refresh 5 min before assumed 1hr expiry)
TOKEN_TTL_SECONDS = 55 * 60

MANUAL_LOGIN_REQUIRED = "MANUAL_LOGIN_REQUIRED"
MANUAL_LOGIN_MESSAGE = (
    "The Emcure Super AI portal requires a one-time manual login before API queries work. "
    "Please log into the Super AI web portal, then retry."
)


# ── Token Management ──────────────────────────────────────────────────────────


def _load_cached_token():
    """Load token from disk cache if still valid."""
    if not os.path.exists(TOKEN_CACHE_FILE):
        return None
    try:
        with open(TOKEN_CACHE_FILE, "r") as f:
            cache = json.load(f)
        if time.time() - cache.get("timestamp", 0) < TOKEN_TTL_SECONDS:
            return cache
        return None
    except (json.JSONDecodeError, OSError):
        return None


def _save_token_cache(auth_token, pbi_token):
    """Persist tokens to disk for reuse across script calls."""
    cache = {
        "auth_token": auth_token,
        "pbi_token": pbi_token,
        "timestamp": time.time(),
    }
    try:
        with open(TOKEN_CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except OSError:
        pass  # Non-critical — token works in-memory regardless


def get_token(force_refresh=False):
    """
    Get auth_token and pbi_token. Uses cache unless expired or force_refresh.

    Returns: (auth_token, pbi_token, None) on success
             (None, None, error_message) on failure
    """
    if not force_refresh:
        cached = _load_cached_token()
        if cached:
            return cached["auth_token"], cached["pbi_token"], None

    body = json.dumps({"email": AUTH_EMAIL, "hash": AUTH_HASH}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "api-key": API_KEY,
    }

    try:
        req = urllib.request.Request(TOKEN_ENDPOINT, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        return None, None, f"Token HTTP {e.code}: {e.reason}. {error_body}"
    except urllib.error.URLError as e:
        return None, None, f"Token URL error: {e.reason}"
    except Exception as e:
        return None, None, f"Token error: {e}"

    if data.get("isSuccess") and isinstance(data.get("data"), dict):
        pbi_token = data["data"].get("accessToken")
        auth_token = pbi_token
    else:
        auth_token = data.get("token") or data.get("auth_token")
        pbi_token = data.get("accessToken") or data.get("pbi_token")

    if not auth_token:
        return (
            None,
            None,
            f"No auth_token in response. Full response: {json.dumps(data)}",
        )

    _save_token_cache(auth_token, pbi_token or "")
    return auth_token, pbi_token or "", None


# ── Query Execution ───────────────────────────────────────────────────────────


def _execute_query(question, retry_on_auth=True):
    """
    Execute a natural language query against the Emcure API.

    Returns: (result_data, None) on success
             (None, error_message) on failure
    """
    auth_token, pbi_token, err = get_token()
    if err:
        return None, f"Auth failed: {err}"

    body = json.dumps(
        {
            "agentId": AGENT_ID,
            "question": question,
        }
    ).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {auth_token}",
    }
    if pbi_token:
        headers["data-source-token"] = pbi_token

    try:
        req = urllib.request.Request(QUERY_ENDPOINT, data=body, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        if e.code == 401:
            try:
                err_data = json.loads(error_body)
                if "Not authorized 5" in err_data.get("message", ""):
                    return None, MANUAL_LOGIN_REQUIRED
            except Exception:
                pass
            if retry_on_auth:
                auth_token, pbi_token, err = get_token(force_refresh=True)
                if err:
                    return None, f"Token refresh failed: {err}"
                return _execute_query(question, retry_on_auth=False)
        return None, f"Query HTTP {e.code}: {e.reason}. {error_body}"
    except urllib.error.URLError as e:
        return None, f"Query URL error: {e.reason}"
    except Exception as e:
        return None, f"Query error: {e}"

    return data, None


def _get_current_month_year():
    """Get current month name and year for query defaults."""
    now = datetime.now()
    return now.strftime("%B"), str(now.year)


def _build_where_clause(name=None, division=None, hq=None):
    """Build the WHERE portion of query strings."""
    parts = []
    if name:
        parts.append(f"employee is ({name})")
    if division:
        parts.append(f"division is ({division})")
    if hq:
        parts.append(f"hq is ({hq})")
    return " ".join(parts)


# ── 5 Query Functions (matching Postman collection patterns) ──────────────────


def get_employee_metrics(name, division=None, hq=None, month=None, year=None):
    """
    Get employee performance metrics: designation, L1 employee, total doctors,
    met count, visits, coverage.

    Query: "employee, designation, l1 employee, total doctors, met, visit,
            coverage for {month} {year} where employee is ({name})
            division is ({division}) hq is ({hq})"
    """
    m, y = month or _get_current_month_year()[0], year or _get_current_month_year()[1]
    where = _build_where_clause(name, division, hq)
    question = f"employee, designation, l1 employee, total doctors, met, visit, coverage for {m} {y} where {where}"
    data, err = _execute_query(question)
    if err == MANUAL_LOGIN_REQUIRED:
        return {
            "status": "manual_login_required",
            "message": MANUAL_LOGIN_MESSAGE,
            "query": question,
        }
    if err:
        return {"status": "error", "message": err, "query": question}
    return {
        "status": "success",
        "source": "emcure_api",
        "query": question,
        "result": data,
    }


def get_doctor_visits(name, division=None, hq=None, month=None, year=None):
    """
    Get doctor visit details: name, speciality, qualification, area,
    frequency, potential, visit date.

    Query: "doctor name, speciality, qualification, area, frequency, potential,
            visit date for {month} {year} where employee is ({name})
            division is ({division}) hq is ({hq})"
    """
    m, y = month or _get_current_month_year()[0], year or _get_current_month_year()[1]
    where = _build_where_clause(name, division, hq)
    question = f"doctor name, speciality, qualification, area, frequency, potential, visit date for {m} {y} where {where}"
    data, err = _execute_query(question)
    if err == MANUAL_LOGIN_REQUIRED:
        return {
            "status": "manual_login_required",
            "message": MANUAL_LOGIN_MESSAGE,
            "query": question,
        }
    if err:
        return {"status": "error", "message": err, "query": question}
    return {
        "status": "success",
        "source": "emcure_api",
        "query": question,
        "result": data,
    }


def get_missed_doctors(name, division=None, hq=None, month=None, year=None):
    """
    Get doctors missed (not visited) in a period: speciality, qualification,
    city.

    Query: "doctor speciality qualification city missed for {month} {year}
            where employee is ({name}) division is ({division}) hq is ({hq})"
    """
    m, y = month or _get_current_month_year()[0], year or _get_current_month_year()[1]
    where = _build_where_clause(name, division, hq)
    question = f"doctor speciality qualification city missed for {m} {y} where {where}"
    data, err = _execute_query(question)
    if err == MANUAL_LOGIN_REQUIRED:
        return {
            "status": "manual_login_required",
            "message": MANUAL_LOGIN_MESSAGE,
            "query": question,
        }
    if err:
        return {"status": "error", "message": err, "query": question}
    return {
        "status": "success",
        "source": "emcure_api",
        "query": question,
        "result": data,
    }


def get_employee_brands(name, division=None, hq=None, month=None, year=None):
    """
    Get brands assigned to an employee.

    Query: "brands for {month} {year} where employee is ({name})
            division is ({division}) hq is ({hq})"
    """
    m, y = month or _get_current_month_year()[0], year or _get_current_month_year()[1]
    where = _build_where_clause(name, division, hq)
    question = f"brands for {m} {y} where {where}"
    data, err = _execute_query(question)
    if err == MANUAL_LOGIN_REQUIRED:
        return {
            "status": "manual_login_required",
            "message": MANUAL_LOGIN_MESSAGE,
            "query": question,
        }
    if err:
        return {"status": "error", "message": err, "query": question}
    return {
        "status": "success",
        "source": "emcure_api",
        "query": question,
        "result": data,
    }


def get_employees(division=None, hq=None, month=None, year=None):
    """
    Get employee list with designations (no specific employee filter).

    Query: "employee, designation for {month} {year}
            division is ({division}) hq is ({hq})"
    """
    m, y = month or _get_current_month_year()[0], year or _get_current_month_year()[1]
    parts = []
    if division:
        parts.append(f"division is ({division})")
    if hq:
        parts.append(f"hq is ({hq})")
    where = " ".join(parts) if parts else ""
    question = f"employee, designation for {m} {y} {where}".strip()
    data, err = _execute_query(question)
    if err == MANUAL_LOGIN_REQUIRED:
        return {
            "status": "manual_login_required",
            "message": MANUAL_LOGIN_MESSAGE,
            "query": question,
        }
    if err:
        return {"status": "error", "message": err, "query": question}
    return {
        "status": "success",
        "source": "emcure_api",
        "query": question,
        "result": data,
    }


# ── High-Level Convenience Functions ──────────────────────────────────────────


def lookup_mr_by_name(name, division=None, hq=None):
    """
    Fetch MR profile data by combining employee metrics + brands.
    Returns a unified profile dict or error.
    """
    metrics = get_employee_metrics(name, division, hq)
    brands = get_employee_brands(name, division, hq)

    if metrics.get("status") == "manual_login_required":
        return metrics
    if metrics.get("status") == "error" and brands.get("status") == "error":
        return {
            "status": "error",
            "message": f"Both queries failed. Metrics: {metrics.get('message')}. Brands: {brands.get('message')}",
        }

    return {
        "status": "success",
        "source": "emcure_api",
        "metrics": metrics.get("result"),
        "brands": brands.get("result"),
    }


def lookup_doctor_by_name(doctor_name, mr_name, division=None, hq=None):
    """
    Search for a specific doctor in the MR's visit data and missed doctors.
    Returns doctor info if found, or not_found status.
    """
    doctor_name_upper = doctor_name.strip().upper()

    visits = get_doctor_visits(mr_name, division, hq)
    if visits.get("status") == "manual_login_required":
        return visits
    if visits.get("status") == "success" and visits.get("result"):
        result_data = visits["result"]
        # The API returns structured data — search through it
        if isinstance(result_data, dict):
            # Try to find doctor in the result
            result_str = json.dumps(result_data).upper()
            if doctor_name_upper in result_str:
                return {
                    "status": "found",
                    "source": "emcure_api_visits",
                    "data": result_data,
                    "search_term": doctor_name,
                }

        if isinstance(result_data, list):
            for row in result_data:
                row_str = json.dumps(row).upper()
                if doctor_name_upper in row_str:
                    return {
                        "status": "found",
                        "source": "emcure_api_visits",
                        "data": row,
                        "search_term": doctor_name,
                    }

    missed = get_missed_doctors(mr_name, division, hq)
    if missed.get("status") == "manual_login_required":
        return missed
    if missed.get("status") == "success" and missed.get("result"):
        result_data = missed["result"]
        if isinstance(result_data, dict):
            result_str = json.dumps(result_data).upper()
            if doctor_name_upper in result_str:
                return {
                    "status": "found",
                    "source": "emcure_api_missed",
                    "data": result_data,
                    "search_term": doctor_name,
                }

        if isinstance(result_data, list):
            for row in result_data:
                row_str = json.dumps(row).upper()
                if doctor_name_upper in row_str:
                    return {
                        "status": "found",
                        "source": "emcure_api_missed",
                        "data": row,
                        "search_term": doctor_name,
                    }

    return {
        "status": "not_found",
        "message": f"Doctor '{doctor_name}' not found in API visit/missed data. Use web_search or ask the MR.",
        "search_term": doctor_name,
    }


# ── CLI Interface ─────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Emcure Super AI Data Apps API client")
    parser.add_argument(
        "--query",
        required=True,
        choices=[
            "employee_metrics",
            "doctor_visits",
            "missed_doctors",
            "employee_brands",
            "get_employees",
            "lookup_mr",
            "lookup_doctor",
        ],
        help="Query type to execute",
    )
    parser.add_argument("--name", help="Employee name (required for most queries)")
    parser.add_argument("--doctor-name", help="Doctor name (for lookup_doctor)")
    parser.add_argument("--division", help="Division filter")
    parser.add_argument("--hq", help="HQ/city filter")
    parser.add_argument("--month", help="Month name (default: current)")
    parser.add_argument("--year", help="Year (default: current)")

    args = parser.parse_args()

    try:
        if args.query == "employee_metrics":
            if not args.name:
                print(json.dumps({"status": "error", "message": "--name required"}))
                return 1
            result = get_employee_metrics(
                args.name, args.division, args.hq, args.month, args.year
            )
        elif args.query == "doctor_visits":
            if not args.name:
                print(json.dumps({"status": "error", "message": "--name required"}))
                return 1
            result = get_doctor_visits(
                args.name, args.division, args.hq, args.month, args.year
            )
        elif args.query == "missed_doctors":
            if not args.name:
                print(json.dumps({"status": "error", "message": "--name required"}))
                return 1
            result = get_missed_doctors(
                args.name, args.division, args.hq, args.month, args.year
            )
        elif args.query == "employee_brands":
            if not args.name:
                print(json.dumps({"status": "error", "message": "--name required"}))
                return 1
            result = get_employee_brands(
                args.name, args.division, args.hq, args.month, args.year
            )
        elif args.query == "get_employees":
            result = get_employees(args.division, args.hq, args.month, args.year)
        elif args.query == "lookup_mr":
            if not args.name:
                print(json.dumps({"status": "error", "message": "--name required"}))
                return 1
            result = lookup_mr_by_name(args.name, args.division, args.hq)
        elif args.query == "lookup_doctor":
            if not args.doctor_name or not args.name:
                print(
                    json.dumps(
                        {
                            "status": "error",
                            "message": "--doctor-name and --name (MR name) both required",
                        }
                    )
                )
                return 1
            result = lookup_doctor_by_name(
                args.doctor_name, args.name, args.division, args.hq
            )
        else:
            result = {"status": "error", "message": f"Unknown query: {args.query}"}

        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
