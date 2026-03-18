#!/usr/bin/env python3
"""
Look up MR profile. Priority: Google Sheet → SQLite fallback.
Usage: python3 scripts/get_mr_profile.py --phone "+919876543210"
"""

import argparse
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sheets_config import read_sheet_csv, MR_SHEET_GID

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mr_database.db")

SEED_DATA = [
    {
        "name": "Somnath",
        "company": "Emcure",
        "division": "Pharma",
        "city": "Kolkata",
        "doctors_per_month": 200,
        "specialties": ["Gynecologist", "Consultant Physician"],
        "brands": ["Orofer-XT", "Pause"],
        "phone": "+919876543210",
        "joining_date": "2023-06-15",
        "region": "East",
    },
    {
        "name": "Rahul Sharma",
        "company": "Sun Pharma",
        "division": "Cardiology",
        "city": "Delhi",
        "doctors_per_month": 150,
        "specialties": ["Cardiologist", "GP"],
        "brands": ["Amlodipine", "Telmisartan"],
        "phone": "+919876543211",
        "joining_date": "2022-03-01",
        "region": "North",
    },
    {
        "name": "Subramaniam K",
        "company": "Cipla",
        "division": "Respiratory",
        "city": "Chennai",
        "doctors_per_month": 120,
        "specialties": ["Pulmonologist", "GP"],
        "brands": ["Foracort", "Duolin"],
        "phone": "+919876543212",
        "joining_date": "2021-11-20",
        "region": "South",
    },
    {
        "name": "Priya Patil",
        "company": "Dr. Reddy's",
        "division": "Dermatology",
        "city": "Mumbai",
        "doctors_per_month": 180,
        "specialties": ["Dermatologist", "GP"],
        "brands": ["Cetaphil", "Ivermectin"],
        "phone": "+919876543213",
        "joining_date": "2024-01-10",
        "region": "West",
    },
    {
        "name": "Ankit Patel",
        "company": "Torrent",
        "division": "Diabetology",
        "city": "Ahmedabad",
        "doctors_per_month": 160,
        "specialties": ["Endocrinologist", "GP"],
        "brands": ["Glimepiride", "Metformin"],
        "phone": "+919939086064",
        "joining_date": "2023-09-05",
        "region": "West",
    },
    {
        "name": "Saurabh Moody",
        "company": "Dr. Reddy's",
        "division": "Oncology",
        "city": "Noida",
        "doctors_per_month": 90,
        "specialties": ["Oncologist", "Hematologist"],
        "brands": ["Grafeel", "Cresp"],
        "phone": "+14088278101",
        "joining_date": "2024-03-01",
        "region": "North",
    },
]


def normalize_phone(phone):
    return re.sub(r"[^+\d]", "", phone)


def lookup_from_sheet(phone):
    if not MR_SHEET_GID:
        return None, "MR sheet tab GID not configured"

    rows, err = read_sheet_csv(gid=MR_SHEET_GID)
    if err or rows is None:
        return None, f"Sheet read failed: {err}"

    phone_clean = normalize_phone(phone)
    for row in rows:
        row_phone = normalize_phone(row.get("Phone", row.get("phone", "")))
        if row_phone == phone_clean:
            specialties = [
                s.strip()
                for s in row.get("Specialties", row.get("specialties", "")).split(",")
                if s.strip()
            ]
            brands = [
                b.strip()
                for b in row.get("Brands", row.get("brands", "")).split(",")
                if b.strip()
            ]
            return {
                "status": "found",
                "source": "google_sheet",
                "profile": {
                    "name": row.get("Name", row.get("name", "")),
                    "company": row.get("Company", row.get("company", "")),
                    "division": row.get("Division", row.get("division", "")),
                    "city": row.get("City", row.get("city", "")),
                    "doctors_per_month": int(
                        row.get("Doctors Per Month", row.get("doctors_per_month", 0))
                        or 0
                    ),
                    "specialties": specialties,
                    "brands": brands,
                    "phone": row.get("Phone", row.get("phone", "")),
                    "joining_date": row.get(
                        "Joining Date", row.get("joining_date", "")
                    ),
                    "region": row.get("Region", row.get("region", "")),
                },
            }, None
    return None, "Not found in sheet"


def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mr_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, company TEXT NOT NULL, division TEXT NOT NULL,
            city TEXT NOT NULL, doctors_per_month INTEGER NOT NULL,
            specialties TEXT NOT NULL, brands TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL, joining_date TEXT NOT NULL, region TEXT NOT NULL
        )
    """)
    conn.commit()
    if conn.execute("SELECT COUNT(*) FROM mr_profiles").fetchone()[0] == 0:
        for mr in SEED_DATA:
            conn.execute(
                "INSERT INTO mr_profiles (name,company,division,city,doctors_per_month,specialties,brands,phone,joining_date,region) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    mr["name"],
                    mr["company"],
                    mr["division"],
                    mr["city"],
                    mr["doctors_per_month"],
                    json.dumps(mr["specialties"]),
                    json.dumps(mr["brands"]),
                    mr["phone"],
                    mr["joining_date"],
                    mr["region"],
                ),
            )
        conn.commit()


def lookup_from_sqlite(phone):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        row = conn.execute(
            "SELECT * FROM mr_profiles WHERE phone = ?", (phone,)
        ).fetchone()
        if row is None:
            return {"status": "not_found", "phone": phone}
        return {
            "status": "found",
            "source": "sqlite",
            "profile": {
                "name": row["name"],
                "company": row["company"],
                "division": row["division"],
                "city": row["city"],
                "doctors_per_month": row["doctors_per_month"],
                "specialties": json.loads(row["specialties"]),
                "brands": json.loads(row["brands"]),
                "phone": row["phone"],
                "joining_date": row["joining_date"],
                "region": row["region"],
            },
        }
    finally:
        conn.close()


def lookup_profile(phone):
    sheet_result, sheet_err = lookup_from_sheet(phone)
    if sheet_result:
        return sheet_result
    return lookup_from_sqlite(phone)


def main():
    parser = argparse.ArgumentParser(description="Look up MR profile by phone number.")
    parser.add_argument(
        "--phone", required=True, help='Phone in E.164 format, e.g. "+919876543210"'
    )
    args = parser.parse_args()

    try:
        result = lookup_profile(args.phone)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
