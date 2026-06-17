# HEARTS360 User Access Setup Guide – Release 0.4.0

> [!NOTE]
> **Purpose:** A clear, visual, step-by-step guide for admins to add users and control what data they can view across HEARTS360 Global and Facility Secure dashboards.

---

## Table of Contents
* [30-Second Summary](#30-second-summary)
* [What Dashboards Exist?](#what-dashboards-exist)
* [User Visibility Matrix](#user-visibility-matrix)
* [How Team Names Work](#how-team-names-work)
  * [Hierarchy Levels](#hierarchy-levels)
  * [How to get the location slug](#how-to-get-the-location-slug)
* [Step-by-Step: Add a New User](#step-by-step-add-a-new-user)
  * [Step 1 — Create the user](#step-1--create-the-user)
  * [Step 2 — Give location-specific access](#step-2--give-location-specific-access)
  * [Step 3 — Give all access of that hierarchy level (admins)](#step-3--give-all-access-of-that-hierarchy-level-admins)
* [What the User Sees on Login (Access Validation)](#what-the-user-sees-on-login-access-validation)
* [Common Scenarios](#common-scenarios)
* [Troubleshooting](#troubleshooting)
* [Quick Reference Card](#quick-reference-card)

---

## 30-Second Summary

> Log in as admin → Create user → Add user to a team → User logs in. Done.

* **Login** lets a person open HEARTS360.
* **Team** controls which locations’ data they can see.
* **Access cascades downwards:** assigning at region/district grants access to all child facilities and sub-facilities.

---

## What Dashboards Exist?

```text
HEARTS360
│
├── 🌐 GLOBAL Dashboards
│   ├── Hypertension
│   ├── Diabetes
│   └── Overdue Patients
│
└── 🔒 FACILITY SECURE Dashboards
    ├── Hypertension
    ├── Diabetes
    └── Overdue Patients
```

---

## User Visibility Matrix

| # | User Type | Sees Global Dashboard Panels? | Sees Secure Dashboards? | Sees Overdue Patients List? |
|---|---|---|---|---|
| 1 | **Not logged in** | ❌ NO | ❌ NO | ❌ NO |
| 2 | **Logged in, no team** | ⚠️ ACCESS DENIED (BANNER) | ⚠️ ACCESS DENIED | ❌ NO |
| 3 | **Logged in, on a specific team** (e.g., Facility/District) |  YES (authorized locations & descendants) |  YES (that facility only) |  YES (Facility/Sub-facility only) |
| 4 | **Logged in, on an `_ALL` team** |  YES (all at/below that level) |  YES (every facility) |  YES (Facility/Sub-facility only) |
| 5 | **Admin** |  YES (every location) |  YES (every facility) |  YES (Facility/Sub-facility only) |

---

## How Team Names Work

> [!IMPORTANT]
> **Rule:** Permissions are granted by adding users to Grafana Teams. Teams must follow this exact naming pattern.

```text
heart360tk_<LEVEL>_view_<TYPE>_<LOCATION_SLUG>
│          │       │      └─ Location name in lowercase
│          │       │         (spaces replaced with underscore)
│          │       │
│          │       └─ "patients"   = graphs access + overdue patient list (full access)
│          │          "aggregated" = graphs access only (patient/overdue details hidden)
│          │
│          └─ "region", "district", "facility", or "sub_facility"
```

### Hierarchy Levels
1. **`region`** — State
2. **`district`** — district
3. **`facility`** — Primary care clinics/Puskesmas
4. **`sub_facility`** — sub_facility

### How to get the location slug
* Take the location name shown in the dashboard dropdown.
* Convert to **lowercase**.
* Replace spaces with underscores `_`.

| Level | Location Name | Slug | Example Team Name (patients) |
|---|---|---|---|
| Region | West Java | `west_java` | `heart360tk_region_view_patients_west_java` |
| District | Bandung District | `bandung_district` | `heart360tk_district_view_patients_bandung_district` |
| Facility | PHC Garden | `phc_garden` | `heart360tk_facility_view_patients_phc_garden` |
| Sub-Facility | Pustu A | `pustu_a` | `heart360tk_sub_facility_view_patients_pustu_a` |

---

## Step-by-Step: Add a New User

### Step 1 — Create the user
1. Log in as **Admin**.
2. Sidebar → **Administration → Users**.
3. Click **New user**.
4. Fill in name, email, username, and password.
5. Click **Create user**.

### Step 2 — Give location-specific access
1. Determine the user’s organizational level, location name, and access type (`patients` or `aggregated`).
2. Construct the team name: `heart360tk_<level>_view_<type>_<slug>`.
3. Sidebar → **Administration → Teams**.
4. Search for the constructed team name.
5. **If the team exists** → Open it → **Add member** → Select the user → **Add**.
6. **If the team does not exist** → **New team** → Name it exactly → **Save** → Add the user.
7. Ask the user to log in. Done!

### Step 3 — Give all access of that hierarchy level (admins)
* Follow Step 2, but replace the specific location slug with `ALL` (e.g., `heart360tk_district_view_patients_ALL`).

---

## What the User Sees on Login (Access Validation)

1. The database checks if the user is an Admin, or belongs to a team matching the selected location or any parent level.
2. **Access Granted:** Panels load normally.
3. **Access Denied:** Panels remain empty and an **Access Denied** banner appears.

```text
┌──────────────────────────────────────────┐
│      User selects location in dropdown   │
└────────────────────┬─────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────┐
│     User is Admin OR belongs to the      │
│   location's team (or parent's team)?    │
└──────────────────┬─────────┬─────────────┘
                   │         │
              YES  │         │  NO
                   ▼         ▼
┌───────────────────┐       ┌──────────────────────────────┐
│  Panels Rendered  │       │    "Access Denied" Banner    │
│   (Data Shown)    │       │    (Empty/Hidden Panels)     │
└───────────────────┘       └──────────────────────────────┘
```

---

## Common Scenarios

* **Nurse should see only her facility** → Add to `heart360tk_facility_view_patients_<facility_slug>`.
* **Regional supervisor should see all facilities in region** → Add to `heart360tk_region_view_patients_<region_slug>`.
* **Graphs only, no patient list** → Use `_aggregated_` instead of `_patients_`.
* **User transferred to different facility:**
  a. Remove from old facility team.
  b. Add to new facility team.
  c. Have them log out and log back in.
* **User needs multiple facilities** → Add to each corresponding facility team.

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---|---|---|
| User sees “Access Denied” banner | Not on a team for the selected location/parent, or team name typo | Read team names shown in the banner. Add the user to a team named exactly like one of those options in Grafana. |
| User cannot see the overdue patient list | 1) They are in an `aggregated` team.<br>2) They selected a Region or District level. | 1) Add the user to a `patients` team.<br>2) Select a specific Facility or Sub-facility (patient lists are disabled above facility level). |

---

## Quick Reference Card

```text
TEAM NAME PATTERN
────────────────────────────────────────────────────────
heart360tk_<LEVEL>_view_<TYPE>_<LOCATION_SLUG>

LEVEL: region, district, facility, sub_facility
TYPE:  patients (full) or aggregated (graphs only)
SLUG:  lowercase location (spaces → "_") or ALL


COMMON TEAMS
────────────────────────────────────────────────────────
Single Facility, graphs + Overdue List  heart360tk_facility_view_patients_<slug>
Single Facility, graphs                 heart360tk_facility_view_aggregated_<slug>
District-wide, graphs + Overdue List    heart360tk_district_view_patients_<slug>
Region-wide, graphs                     heart360tk_region_view_aggregated_<slug>
All Facilities, graphs + Overdue List   heart360tk_facility_view_patients_ALL
All Districts, graphs                   heart360tk_district_view_aggregated_ALL


WORKFLOW
────────────────────────────────────────────────────────
1) Administration → Users → New user
2) Administration → Teams → Find or create matching team name
3) Open team → Add member → Pick user
4) Tell user to log in / refresh session
```
