#!/usr/bin/env python3
"""Patch cascade panel labels to match the design screenshot."""

from __future__ import annotations

import json
from pathlib import Path

DASHBOARD = Path(
    "grafana_provisioning/dashboards/HEARTS360 Dashboards/"
    "heart360.hypertension-diabetes.program.json"
)

ORG_FILTER = """org_unit_id IN (SELECT id FROM org_units
  WHERE NULLIF(NULLIF(TRIM(BOTH FROM '${org_unit}'), ''), '0') IS NULL
  UNION
  SELECT id FROM get_descendant_ids(
    (SELECT ou.id FROM org_units ou
     WHERE ou.id::text = NULLIF(NULLIF(TRIM(BOTH FROM '${org_unit}'), ''), '0')
     LIMIT 1)
  ))"""

BASE_CTE = f"""
  WITH base AS (
    SELECT
      ${{estimated_htn_population}}::numeric AS est,
      COALESCE(SUM(reg.cumulative_number_of_patients), 0)::numeric AS registered,
      COALESCE(SUM(cat.nb_patients_under_care_registered_before_the_past_3_months), 0)::numeric AS under_care,
      COALESCE(SUM(cat.nb_patients_controlled), 0)::numeric AS controlled
    FROM heart360_patients_category cat
    JOIN heart360_patients_registered reg
      ON reg.ref_month = cat.ref_month AND reg.org_unit_id = cat.org_unit_id
    WHERE cat.ref_month = to_timestamp(${{reference_month}}/1000.0)
      AND cat.{ORG_FILTER}
  )
"""

LABELS_SQL = f"""SELECT * FROM (
{BASE_CTE}
  SELECT
    est,
    registered,
    under_care,
    controlled,
    round(registered / NULLIF(est, 0) * 100, 1) AS registered_pct,
    round(under_care / NULLIF(est, 0) * 100, 1) AS under_care_pct,
    round(controlled / NULLIF(est, 0) * 100, 1) AS controlled_pct
  FROM base
) AS master_access_control WHERE '${{isAllowed}}' = '1'
"""

CASCADE_SQL = f"""SELECT * FROM (
  SELECT
    cat.ref_month,
    100.0 AS "Estimated people with hypertension",
    (SUM(reg.cumulative_number_of_patients)::numeric
      / NULLIF(${{estimated_htn_population}}::numeric, 0) * 100.0)
      AS "Cumulative registered patients",
    (SUM(cat.nb_patients_under_care_registered_before_the_past_3_months)::numeric
      / NULLIF(${{estimated_htn_population}}::numeric, 0) * 100.0)
      AS "Patients under care",
    (SUM(cat.nb_patients_controlled)::numeric
      / NULLIF(${{estimated_htn_population}}::numeric, 0) * 100.0)
      AS "Patients with BP controlled"
  FROM heart360_patients_category cat
  JOIN heart360_patients_registered reg
    ON reg.ref_month = cat.ref_month AND reg.org_unit_id = cat.org_unit_id
  WHERE cat.ref_month = to_timestamp(${{reference_month}}/1000.0)
    AND cat.{ORG_FILTER}
  GROUP BY 1
) AS master_access_control WHERE '${{isAllowed}}' = '1'
"""

LABELS = [
    ("Estimated people with hypertension", "#dae0e1"),
    ("Cumulative registered patients", "blue"),
    ("Patients under care", "purple"),
    ("Patients with BP controlled", "green"),
]

CONTENT = """\
<div style="display:flex;justify-content:space-between;gap:6px;padding:2px 0 0;text-align:center;">
  <div style="flex:1;border-right:1px solid #dde3e8;padding:0 4px;">
    <div style="font-size:20px;font-weight:600;line-height:1.15;color:#111827;">{{est | formatNumber}} <span style="font-size:13px;font-weight:500;color:#6b7280;">(100%)</span></div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px;line-height:1.25;">Estimated people with hypertension</div>
  </div>
  <div style="flex:1;border-right:1px solid #dde3e8;padding:0 4px;">
    <div style="font-size:20px;font-weight:600;line-height:1.15;color:#111827;">{{registered | formatNumber}} <span style="font-size:13px;font-weight:500;color:#6b7280;">({{registered_pct}}%)</span></div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px;line-height:1.25;">Cumulative registered patients</div>
  </div>
  <div style="flex:1;border-right:1px solid #dde3e8;padding:0 4px;">
    <div style="font-size:20px;font-weight:600;line-height:1.15;color:#111827;">{{under_care | formatNumber}} <span style="font-size:13px;font-weight:500;color:#6b7280;">({{under_care_pct}}%)</span></div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px;line-height:1.25;">Patients under care</div>
  </div>
  <div style="flex:1;padding:0 4px;">
    <div style="font-size:20px;font-weight:600;line-height:1.15;color:#111827;">{{controlled | formatNumber}} <span style="font-size:13px;font-weight:500;color:#6b7280;">({{controlled_pct}}%)</span></div>
    <div style="font-size:11px;color:#6b7280;margin-top:4px;line-height:1.25;">Patients with BP controlled</div>
  </div>
</div>
"""


def query(raw_sql: str) -> dict:
    return {
        "kind": "PanelQuery",
        "spec": {
            "hidden": False,
            "query": {
                "datasource": {"name": "postgres-hypertension-cached"},
                "group": "grafana-postgresql-datasource",
                "kind": "DataQuery",
                "spec": {
                    "dataset": "metrics_db",
                    "editorMode": "code",
                    "format": "table",
                    "rawQuery": True,
                    "rawSql": raw_sql,
                    "refId": "A",
                },
                "version": "v0",
            },
            "refId": "A",
        },
    }


def color_overrides() -> list[dict]:
    return [
        {
            "matcher": {"id": "byName", "options": name},
            "properties": [
                {"id": "color", "value": {"fixedColor": color, "mode": "fixed"}}
            ],
        }
        for name, color in LABELS
    ]


def main() -> None:
    data = json.loads(DASHBOARD.read_text())
    elements = data["spec"]["elements"]

    cascade = elements["panel-cascade"]["spec"]
    cascade["data"] = {
        "kind": "QueryGroup",
        "spec": {
            "queries": [query(CASCADE_SQL)],
            "queryOptions": {"percentile": 75},
            "transformations": [],
        },
    }
    cascade["description"] = (
        "Estimated population with hypertension is derived from Community Survey.\n\n"
        "Patients under care are patients with hypertension with at least 1 visit "
        "in the past 12 months."
    )
    viz = cascade["vizConfig"]["spec"]
    viz["options"]["showValue"] = "always"
    viz["options"]["legend"]["showLegend"] = False
    defaults = viz["fieldConfig"].setdefault("defaults", {})
    defaults["unit"] = "percent"
    defaults["decimals"] = 1
    viz["fieldConfig"]["overrides"] = color_overrides()

    elements["panel-cascade-labels"] = {
        "kind": "Panel",
        "spec": {
            "data": {
                "kind": "QueryGroup",
                "spec": {
                    "queries": [query(LABELS_SQL)],
                    "queryOptions": {"percentile": 75},
                    "transformations": [],
                },
            },
            "description": "",
            "id": 21,
            "links": [],
            "title": "",
            "vizConfig": {
                "group": "marcusolsson-dynamictext-panel",
                "kind": "VizConfig",
                "spec": {
                    "fieldConfig": {"defaults": {}, "overrides": []},
                    "options": {
                        "content": CONTENT,
                        "defaultContent": "Loading cascade summary…",
                        "editors": [],
                        "everyRow": True,
                    },
                },
                "version": "6.1.0",
            },
        },
    }

    htn = data["spec"]["layout"]["spec"]["rows"][1]["spec"]["layout"]["spec"]["tabs"][0][
        "spec"
    ]["layout"]
    htn["spec"]["rows"][0]["spec"]["layout"]["spec"]["items"] = [
        {
            "kind": "GridLayoutItem",
            "spec": {
                "element": {"kind": "ElementReference", "name": "panel-1"},
                "height": 10,
                "width": 16,
                "x": 0,
                "y": 0,
            },
        },
        {
            "kind": "GridLayoutItem",
            "spec": {
                "element": {
                    "kind": "ElementReference",
                    "name": "panel-cascade-labels",
                },
                "height": 3,
                "width": 8,
                "x": 16,
                "y": 0,
            },
        },
        {
            "kind": "GridLayoutItem",
            "spec": {
                "element": {"kind": "ElementReference", "name": "panel-cascade"},
                "height": 7,
                "width": 8,
                "x": 16,
                "y": 3,
            },
        },
    ]

    DASHBOARD.write_text(json.dumps(data, indent=2) + "\n")
    json.loads(DASHBOARD.read_text())
    print("patched cascade labels")


if __name__ == "__main__":
    main()
