#!/usr/bin/env python3
"""
Look up a Medical Representative's profile from a local SQLite database.

Called by OpenClaw agent via exec:
    python3 scripts/get_mr_profile.py --phone "+919876543210"

Outputs JSON to stdout. Creates and seeds the DB on first run.
"""

import argparse
import json
import os
import sqlite3
import sys

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
        "phone": "+919876543214",
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
        "phone": "+919876543215",
        "joining_date": "2024-03-01",
        "region": "North",
    },
]


def init_db(conn: sqlite3.Connection) -> None:
    """Create the MR profiles table and seed with sample data."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mr_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT NOT NULL,
            division TEXT NOT NULL,
            city TEXT NOT NULL,
            doctors_per_month INTEGER NOT NULL,
            specialties TEXT NOT NULL,
            brands TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            joining_date TEXT NOT NULL,
            region TEXT NOT NULL
        )
        """
    )
    conn.commit()

    cursor = conn.execute("SELECT COUNT(*) FROM mr_profiles")
    if cursor.fetchone()[0] == 0:
        for mr in SEED_DATA:
            conn.execute(
                """
                INSERT INTO mr_profiles
                    (name, company, division, city, doctors_per_month,
                     specialties, brands, phone, joining_date, region)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
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


def lookup_profile(phone: str) -> dict:
    """Query the SQLite DB for an MR profile by phone number."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        init_db(conn)
        cursor = conn.execute("SELECT * FROM mr_profiles WHERE phone = ?", (phone,))
        row = cursor.fetchone()
        if row is None:
            return {"status": "not_found", "phone": phone}

        profile = {
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
        }
        return {"status": "found", "profile": profile}
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Look up a Medical Representative profile by phone number."
    )
    parser.add_argument(
        "--phone",
        required=True,
        help='Phone number in E.164 format, e.g. "+919876543210"',
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
