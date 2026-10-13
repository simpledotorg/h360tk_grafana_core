#!/usr/bin/env python3
"""Deterministic demo upload data for HEARTS360 PHC-style xlsx files."""

from __future__ import annotations

import argparse
import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

RNG_SEED = 42
TARGET_PATIENTS = 8000
DEFAULT_AS_OF = datetime(2026, 10, 13)

DATE_FMT = "%d-%m-%Y %H:%M:%S"
DATE_FMT_SHORT = "%d-%m-%Y"

COLUMNS = [
    "Registration Date",
    "Patient ID",
    "First Name",
    "Middle Name",
    "Last Name",
    "Date of Birth",
    "Gender",
    "Phone Number",
    "Region",
    "District",
    "Facility",
    "Sub Facility",
    "Systolic",
    "Diastolic",
    "Visit Time",
    "Blood Sugar Type",
    "Blood Sugar Value",
    "Diagnosis 1",
    "Diagnosis 2",
]

FACILITY_REGISTRY: list[dict[str, str]] = [
    {"Region": "Region-A", "District": "District-A", "Facility": "PHC-A", "Sub Facility": "SHC-A"},
    {"Region": "Region-A", "District": "District-A", "Facility": "PHC-A", "Sub Facility": "SHC-B"},
    {"Region": "Region-A", "District": "District-A", "Facility": "PHC-A", "Sub Facility": "SHC-C"},
    {"Region": "Region-A", "District": "District-A", "Facility": "PHC-A", "Sub Facility": "SHC-D"},
    {"Region": "Region-A", "District": "District-A", "Facility": "PHC-B", "Sub Facility": "SHC-E"},
    {"Region": "Region-A", "District": "District-A", "Facility": "PHC-B", "Sub Facility": "SHC-F"},
    {"Region": "Region-A", "District": "District-A", "Facility": "PHC-B", "Sub Facility": "SHC-G"},
    {"Region": "Region-A", "District": "District-A", "Facility": "PHC-B", "Sub Facility": "SHC-H"},
    {"Region": "Region-A", "District": "District-B", "Facility": "PHC-C", "Sub Facility": "SHC-I"},
    {"Region": "Region-A", "District": "District-B", "Facility": "PHC-C", "Sub Facility": "SHC-J"},
    {"Region": "Region-A", "District": "District-B", "Facility": "PHC-C", "Sub Facility": "SHC-K"},
    {"Region": "Region-A", "District": "District-B", "Facility": "PHC-C", "Sub Facility": "SHC-L"},
    {"Region": "Region-B", "District": "District-C", "Facility": "PHC-D", "Sub Facility": "SHC-M"},
    {"Region": "Region-B", "District": "District-C", "Facility": "PHC-D", "Sub Facility": "SHC-N"},
    {"Region": "Region-B", "District": "District-C", "Facility": "PHC-D", "Sub Facility": "SHC-O"},
    {"Region": "Region-B", "District": "District-C", "Facility": "PHC-D", "Sub Facility": "SHC-P"},
    {"Region": "Region-B", "District": "District-D", "Facility": "PHC-E", "Sub Facility": "SHC-Q"},
    {"Region": "Region-B", "District": "District-D", "Facility": "PHC-E", "Sub Facility": "SHC-R"},
    {"Region": "Region-B", "District": "District-D", "Facility": "PHC-E", "Sub Facility": "SHC-S"},
    {"Region": "Region-B", "District": "District-D", "Facility": "PHC-E", "Sub Facility": "SHC-T"},
    {"Region": "Region-B", "District": "District-D", "Facility": "PHC-F", "Sub Facility": "SHC-U"},
    {"Region": "Region-B", "District": "District-D", "Facility": "PHC-F", "Sub Facility": "SHC-V"},
    {"Region": "Region-B", "District": "District-D", "Facility": "PHC-F", "Sub Facility": "SHC-W"},
    {"Region": "Region-B", "District": "District-D", "Facility": "PHC-F", "Sub Facility": "SHC-X"},
]

TRAJECTORY_PROFILES: list[dict[str, float | int]] = [
    {"name": "improver", "weight": 0.45, "start_controlled_p": 0.15, "end_controlled_p": 0.82, "missed_p": 0.08},
    {"name": "stable_controlled", "weight": 0.25, "start_controlled_p": 0.75, "end_controlled_p": 0.88, "missed_p": 0.05},
    {"name": "persistent_uncontrolled", "weight": 0.18, "start_controlled_p": 0.1, "end_controlled_p": 0.22, "missed_p": 0.12},
    {"name": "intermittent", "weight": 0.12, "start_controlled_p": 0.4, "end_controlled_p": 0.55, "missed_p": 0.22},
]

VISIT_CADENCE_MONTHS = (3, 4)


@dataclass(frozen=True)
class PatientTrajectory:
    registration_date: datetime
    profile: dict[str, float | int | str]
    facility: dict[str, str]
    visit_interval_days: int
    dm_comorbid: bool


def parse_upload_datetime(value) -> datetime | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    for fmt in (DATE_FMT, DATE_FMT_SHORT, "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def format_upload_datetime(dt: datetime) -> str:
    return dt.strftime(DATE_FMT)


def add_months(dt: datetime, months: int) -> datetime:
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def month_shift_to_as_of(max_dt: datetime, as_of: datetime) -> int:
    return (as_of.year - max_dt.year) * 12 + (as_of.month - max_dt.month)


def cap_at_as_of(dt: datetime, as_of: datetime) -> datetime:
    cap = as_of.replace(hour=23, minute=59, second=59)
    return min(dt, cap)


def shift_column(series: pd.Series, months: int, as_of: datetime) -> pd.Series:
    def _shift(value):
        parsed = parse_upload_datetime(value)
        if parsed is None:
            return value
        shifted = cap_at_as_of(add_months(parsed, months), as_of)
        return format_upload_datetime(shifted)

    return series.map(_shift)


def max_datetime_in_frame(df: pd.DataFrame) -> datetime | None:
    candidates: list[datetime] = []
    for col in ("Visit Time", "Registration Date"):
        if col not in df.columns:
            continue
        for value in df[col]:
            parsed = parse_upload_datetime(value)
            if parsed is not None:
                candidates.append(parsed)
    return max(candidates) if candidates else None


def shift_phc_workbook(src: Path, dst: Path, as_of: datetime) -> datetime | None:
    df = pd.read_excel(src, header=0, dtype={"Patient ID": str, "Phone Number": str})
    anchor = max_datetime_in_frame(df)
    if anchor is None:
        df.to_excel(dst, index=False)
        return None

    months = month_shift_to_as_of(anchor, as_of)
    for col in ("Registration Date", "Visit Time", "Date of Birth"):
        if col in df.columns:
            df[col] = shift_column(df[col], months, as_of)

    dst.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(dst, index=False)
    return max_datetime_in_frame(df)


def quarter_starts_ending_at(as_of: datetime, count: int) -> list[datetime]:
    q_month = ((as_of.month - 1) // 3) * 3 + 1
    current = datetime(as_of.year, q_month, 1)
    quarters: list[datetime] = []
    for _ in range(count):
        quarters.append(current)
        current = add_months(current, -3)
    return list(reversed(quarters))


def pick_profile(rng: np.random.Generator) -> dict[str, float | int | str]:
    weights = np.array([p["weight"] for p in TRAJECTORY_PROFILES], dtype=float)
    idx = rng.choice(len(TRAJECTORY_PROFILES), p=weights / weights.sum())
    return TRAJECTORY_PROFILES[int(idx)]


def bp_for_state(rng: np.random.Generator, controlled: bool) -> tuple[int, int]:
    if controlled:
        return int(rng.integers(110, 136)), int(rng.integers(70, 86))
    return int(rng.integers(145, 181)), int(rng.integers(90, 111))


def controlled_probability(profile: dict[str, float | int | str], progress: float) -> float:
    start = float(profile["start_controlled_p"])
    end = float(profile["end_controlled_p"])
    return start + (end - start) * progress


def build_trajectories(rng: np.random.Generator, as_of: datetime) -> list[PatientTrajectory]:
    quarters = quarter_starts_ending_at(as_of, 8)
    facility_idx = rng.integers(0, len(FACILITY_REGISTRY), size=TARGET_PATIENTS)
    quarter_idx = rng.integers(0, len(quarters), size=TARGET_PATIENTS)

    trajectories: list[PatientTrajectory] = []
    for i in range(TARGET_PATIENTS):
        q_start = quarters[int(quarter_idx[i])]
        day_offset = int(rng.integers(0, 28))
        registration = q_start + timedelta(days=day_offset)
        registration = cap_at_as_of(registration.replace(hour=9, minute=0, second=0), as_of)
        cadence = int(rng.choice(VISIT_CADENCE_MONTHS))
        trajectories.append(
            PatientTrajectory(
                registration_date=registration,
                profile=pick_profile(rng),
                facility=FACILITY_REGISTRY[int(facility_idx[i])],
                visit_interval_days=cadence * 30,
                dm_comorbid=bool(rng.random() < 0.2),
            )
        )
    return trajectories


def visit_schedule(trajectory: PatientTrajectory, as_of: datetime, rng: np.random.Generator) -> list[datetime]:
    visits: list[datetime] = []
    cursor = trajectory.registration_date
    dense_start = cap_at_as_of(as_of - timedelta(days=183), as_of).replace(
        hour=0, minute=0, second=0
    )

    while cursor <= as_of:
        if cursor >= dense_start or rng.random() > 0.35:
            visits.append(cursor)
        cursor = cursor + timedelta(days=trajectory.visit_interval_days + int(rng.integers(-7, 8)))

    if not visits or visits[-1] < dense_start:
        extra = dense_start
        while extra <= as_of:
            if extra not in visits:
                visits.append(extra)
            extra = extra + timedelta(days=trajectory.visit_interval_days)

    visits = sorted(set(cap_at_as_of(v.replace(hour=10, minute=int(rng.integers(0, 59)), second=0), as_of) for v in visits))
    return [v for v in visits if v >= trajectory.registration_date]


def trajectory_to_rows(trajectory: PatientTrajectory, patient_index: int, rng: np.random.Generator, as_of: datetime) -> list[dict]:
    visits = visit_schedule(trajectory, as_of, rng)
    if not visits:
        visits = [trajectory.registration_date]

    patient_id = f"DEMO-{patient_index:05d}"
    first_name = f"Patient{patient_index % 1000}"
    last_name = str((patient_index % 500) + 1)
    gender = "Female" if patient_index % 2 == 0 else "Male"
    dob = datetime(1955 + (patient_index % 40), 1 + (patient_index % 12), 1 + (patient_index % 28))
    phone = f"9{patient_index:09d}"[-10:]
    reg_str = format_upload_datetime(trajectory.registration_date.replace(hour=0, minute=0, second=0))

    diagnosis_2 = "E11" if trajectory.dm_comorbid else ""
    total = len(visits)
    rows: list[dict] = []

    for visit_i, visit_dt in enumerate(visits):
        progress = visit_i / max(total - 1, 1)
        missed = rng.random() < float(trajectory.profile["missed_p"])
        if missed and visit_dt >= as_of - timedelta(days=120):
            missed = False
        if missed:
            continue

        controlled = rng.random() < controlled_probability(trajectory.profile, progress)
        systolic, diastolic = bp_for_state(rng, controlled)

        bs_type = ""
        bs_value = np.nan
        if trajectory.dm_comorbid and rng.random() < 0.65:
            bs_type = rng.choice(["FBS", "RBS", "HBA1C"])
            bs_value = float(rng.integers(110, 220))

        rows.append(
            {
                "Registration Date": reg_str,
                "Patient ID": patient_id,
                "First Name": first_name,
                "Middle Name": np.nan,
                "Last Name": last_name,
                "Date of Birth": dob.strftime(DATE_FMT_SHORT),
                "Gender": gender,
                "Phone Number": phone,
                "Region": trajectory.facility["Region"],
                "District": trajectory.facility["District"],
                "Facility": trajectory.facility["Facility"],
                "Sub Facility": trajectory.facility["Sub Facility"],
                "Systolic": systolic,
                "Diastolic": diastolic,
                "Visit Time": format_upload_datetime(visit_dt),
                "Blood Sugar Type": bs_type,
                "Blood Sugar Value": bs_value,
                "Diagnosis 1": "I10",
                "Diagnosis 2": diagnosis_2,
            }
        )

    if not rows:
        systolic, diastolic = bp_for_state(rng, False)
        rows.append(
            {
                "Registration Date": reg_str,
                "Patient ID": patient_id,
                "First Name": first_name,
                "Middle Name": np.nan,
                "Last Name": last_name,
                "Date of Birth": dob.strftime(DATE_FMT_SHORT),
                "Gender": gender,
                "Phone Number": phone,
                "Region": trajectory.facility["Region"],
                "District": trajectory.facility["District"],
                "Facility": trajectory.facility["Facility"],
                "Sub Facility": trajectory.facility["Sub Facility"],
                "Systolic": systolic,
                "Diastolic": diastolic,
                "Visit Time": format_upload_datetime(trajectory.registration_date),
                "Blood Sugar Type": "",
                "Blood Sugar Value": np.nan,
                "Diagnosis 1": "I10",
                "Diagnosis 2": diagnosis_2,
            }
        )
    return rows


def generate_demo_frame(rng: np.random.Generator, as_of: datetime) -> pd.DataFrame:
    trajectories = build_trajectories(rng, as_of)
    all_rows: list[dict] = []
    for idx, trajectory in enumerate(trajectories, start=1):
        all_rows.extend(trajectory_to_rows(trajectory, idx, rng, as_of))
    return pd.DataFrame(all_rows, columns=COLUMNS)


def summarize_dates(frames: Iterable[pd.DataFrame]) -> tuple[datetime | None, datetime | None]:
    parsed: list[datetime] = []
    for frame in frames:
        for col in ("Visit Time", "Registration Date"):
            if col not in frame.columns:
                continue
            for value in frame[col]:
                dt = parse_upload_datetime(value)
                if dt is not None:
                    parsed.append(dt)
    if not parsed:
        return None, None
    return min(parsed), max(parsed)


def default_as_of() -> datetime:
    today = datetime.now()
    if today.year == 2026 and today.month == 10:
        return today.replace(hour=23, minute=59, second=59)
    return DEFAULT_AS_OF


def write_verify_sql(path: Path) -> None:
    path.write_text(
        """-- Run after demo ingest and reporting refresh (psql -f test_data/demo/verify_demo.sql).

DO $$
DECLARE
  v_ref_month date;
  v_estimated_pct numeric;
  v_registered_pct numeric;
  v_under_care_pct numeric;
  v_controlled_pct numeric;
  v_quarter_count integer;
  est_pop numeric := 14500;
BEGIN
  SELECT MAX(ref_month) INTO v_ref_month
  FROM heart360tk_reporting.heart360_patients_category;

  IF v_ref_month IS NULL THEN
    RAISE EXCEPTION 'verify_demo: no rows in heart360_patients_category';
  END IF;

  SELECT
    100.0,
    100.0 * SUM(reg.cumulative_number_of_patients) / est_pop,
    100.0 * SUM(cat.nb_patients_under_care_registered_before_the_past_3_months) / est_pop,
    100.0 * SUM(cat.nb_patients_controlled) / est_pop
  INTO v_estimated_pct, v_registered_pct, v_under_care_pct, v_controlled_pct
  FROM heart360tk_reporting.heart360_patients_category cat
  JOIN heart360tk_reporting.heart360_patients_registered reg
    ON reg.ref_month = cat.ref_month AND reg.org_unit_id = cat.org_unit_id
  WHERE cat.ref_month = v_ref_month;

  IF COALESCE(v_registered_pct, 0) <= 0
     OR COALESCE(v_under_care_pct, 0) <= 0
     OR COALESCE(v_controlled_pct, 0) <= 0 THEN
    RAISE EXCEPTION
      'verify_demo cascade failed at %: estimated=%, registered_pct=%, under_care_pct=%, controlled_pct=%',
      v_ref_month, v_estimated_pct, v_registered_pct, v_under_care_pct, v_controlled_pct;
  END IF;

  SELECT COUNT(*) INTO v_quarter_count
  FROM (
    SELECT registration_quarter
    FROM heart360tk_reporting.heart360_cohort_patient_details
    GROUP BY registration_quarter
    HAVING COUNT(*) > 0
  ) q;

  IF v_quarter_count < 6 THEN
    RAISE EXCEPTION 'verify_demo cohort failed: only % quarters with patients', v_quarter_count;
  END IF;

  RAISE NOTICE 'verify_demo OK: ref_month=%, estimated=%, registered_pct=%, under_care_pct=%, controlled_pct=%, cohort_quarters=%',
    v_ref_month, v_estimated_pct, v_registered_pct, v_under_care_pct, v_controlled_pct, v_quarter_count;
END $$;
""",
        encoding="utf-8",
    )


def write_readme(path: Path) -> None:
    path.write_text(
        """# Demo PHC upload data

Deterministic synthetic and date-shifted PHC spreadsheets for local demo ingest.

## Regenerate

From the repository root:

```bash
python3 test_data/demo/build_demo_data.py
```

Optional as-of date (defaults to today when run in October 2026, otherwise `2026-10-13`):

```bash
python3 test_data/demo/build_demo_data.py --as-of 2026-10-13
```

## Outputs

- `out/shifted_*.xlsx` — source PHC files shifted so the latest visit falls in the as-of month.
- `demo_generated.xlsx` — ~1500 synthetic HTN patients with multi-visit rows.
- `verify_demo.sql` — post-ingest assertions for cascade and cohort reporting tables.

After ingest and a reporting refresh, run:

```bash
psql "$DATABASE_URL" -f test_data/demo/verify_demo.sql
```
""",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--as-of",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").replace(hour=23, minute=59, second=59),
        default=None,
        help="Anchor month for date shifting (YYYY-MM-DD)",
    )
    args = parser.parse_args()
    as_of = args.as_of or default_as_of()

    root = Path(__file__).resolve().parent
    source_dir = root / "source_phc"
    out_dir = root / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(RNG_SEED)

    shifted_paths: list[Path] = []
    shifted_max: list[datetime] = []
    for src in sorted(source_dir.glob("PHC-*.xlsx")):
        dst = out_dir / f"shifted_{src.name}"
        max_dt = shift_phc_workbook(src, dst, as_of)
        shifted_paths.append(dst)
        if max_dt is not None:
            shifted_max.append(max_dt)

    demo_path = root / "demo_generated.xlsx"
    demo_df = generate_demo_frame(rng, as_of)
    demo_df.to_excel(demo_path, index=False)

    write_verify_sql(root / "verify_demo.sql")
    write_readme(root / "README.md")

    gen_min, gen_max = summarize_dates([demo_df])
    shift_min, shift_max = summarize_dates(
        [pd.read_excel(p, header=0) for p in shifted_paths]
    )

    unique_patients = demo_df["Patient ID"].nunique()
    visit_rows = len(demo_df)

    print(f"as_of={as_of.date().isoformat()}")
    print(f"shifted_files={len(shifted_paths)}")
    print(f"shifted_date_range={shift_min} .. {shift_max}")
    print(f"generated_patients={unique_patients}")
    print(f"generated_visit_rows={visit_rows}")
    print(f"generated_date_range={gen_min} .. {gen_max}")
    print("outputs:")
    for p in shifted_paths:
        print(f"  {p}")
    print(f"  {demo_path}")
    print(f"  {root / 'verify_demo.sql'}")
    print(f"  {root / 'README.md'}")


if __name__ == "__main__":
    main()
