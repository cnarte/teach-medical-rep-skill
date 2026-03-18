#!/usr/bin/env python3
"""
Shared Google Sheets configuration and helpers.

READ: Uses public CSV export URL (no auth, no pip packages needed).
WRITE: Uses gspread + service account (optional — install gspread, set up credentials).

Sheet: https://docs.google.com/spreadsheets/d/1Ps_yZag5pbJiHEEJrF3sojVAjWUI0zoR
"""

import csv
import io
import json
import os
import urllib.request
import urllib.error

# ── Sheet Configuration ───────────────────────────────────────────────────────

SHEET_ID = "1Ps_yZag5pbJiHEEJrF3sojVAjWUI0zoR"

# GID 0 = first tab (Doctors). MR Profiles tab GID will be discovered or set.
DOCTOR_SHEET_GID = None
MR_SHEET_GID = None  # Set after creating the MR Profiles tab

# CSV export URL pattern (no auth needed for shared sheets)
CSV_EXPORT_BASE = "https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
CSV_EXPORT_WITH_GID = CSV_EXPORT_BASE + "&gid={gid}"


def get_csv_url(gid=None):
    if gid:
        return CSV_EXPORT_WITH_GID.format(sheet_id=SHEET_ID, gid=gid)
    return CSV_EXPORT_BASE.format(sheet_id=SHEET_ID)


# ── READ: CSV Export (no auth) ────────────────────────────────────────────────


def read_sheet_csv(gid=None, timeout=15):
    """
    Read a Google Sheet tab as a list of dicts via public CSV export.
    Returns (rows, None) on success or (None, error_message) on failure.
    No pip packages needed — uses urllib from stdlib.
    """
    url = get_csv_url(gid)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MedRepTools/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8-sig")  # BOM-safe
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        return rows, None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return None, f"URL error: {e.reason}"
    except Exception as e:
        return None, str(e)


# ── WRITE: gspread (optional) ────────────────────────────────────────────────


def get_gspread_client():
    """
    Get an authenticated gspread client. Returns (client, None) or (None, error).

    Auth priority:
    1. GOOGLE_SERVICE_ACCOUNT env var (JSON string — best for agents/CI)
    2. Service account file at ~/.config/gspread/service_account.json
    3. Service account file at scripts/service_account.json (local dev)
    """
    try:
        import gspread
    except ImportError:
        return None, "gspread not installed. Run: pip install gspread"

    try:
        from gspread.http_client import BackOffHTTPClient

        http_client = BackOffHTTPClient
    except ImportError:
        http_client = None

    # Try env var first
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT")
    if creds_json:
        try:
            info = json.loads(creds_json)
            kwargs = {"info": info}
            if http_client:
                kwargs["http_client"] = http_client
            gc = gspread.service_account_from_dict(**kwargs)
            return gc, None
        except Exception as e:
            return None, f"Env var auth failed: {e}"

    # Try file paths
    for path in [
        os.path.expanduser("~/.config/gspread/service_account.json"),
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "service_account.json"
        ),
    ]:
        if os.path.exists(path):
            try:
                kwargs = {"filename": path}
                if http_client:
                    kwargs["http_client"] = http_client
                gc = gspread.service_account(**kwargs)
                return gc, None
            except Exception as e:
                return None, f"File auth failed ({path}): {e}"

    return (
        None,
        "No credentials found. Set GOOGLE_SERVICE_ACCOUNT env var or place service_account.json",
    )


def open_spreadsheet(gc):
    """Open the MR training spreadsheet."""
    return gc.open_by_key(SHEET_ID)


def append_row_to_sheet(tab_name, row_data):
    """
    Append a row to a named sheet tab. Returns (success, message).
    row_data is a list of values matching the tab's column order.
    """
    gc, err = get_gspread_client()
    if err:
        return False, f"Cannot write: {err}"
    try:
        sh = open_spreadsheet(gc)
        ws = sh.worksheet(tab_name)
        ws.append_row(row_data, value_input_option="USER_ENTERED")
        return True, "Row appended"
    except Exception as e:
        return False, str(e)


def find_or_create_worksheet(tab_name, headers):
    """
    Find a worksheet by name, or create it with headers.
    Returns (worksheet, created, error).
    """
    gc, err = get_gspread_client()
    if err:
        return None, False, err
    try:
        sh = open_spreadsheet(gc)
        try:
            ws = sh.worksheet(tab_name)
            return ws, False, None
        except Exception:
            ws = sh.add_worksheet(title=tab_name, rows=100, cols=len(headers))
            ws.append_row(headers, value_input_option="USER_ENTERED")
            return ws, True, None
    except Exception as e:
        return None, False, str(e)
