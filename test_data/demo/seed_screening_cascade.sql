-- Demo-only catchment for the Screening Cascade card.
-- Screened adults still come from heart360_patients_registered.
CREATE TABLE IF NOT EXISTS heart360tk_schema.demo_screening_cascade (
  id integer PRIMARY KEY,
  eligible_adults integer NOT NULL
);
INSERT INTO heart360tk_schema.demo_screening_cascade (id, eligible_adults)
VALUES (1, 30500)
ON CONFLICT (id) DO UPDATE SET eligible_adults = EXCLUDED.eligible_adults;
GRANT SELECT ON heart360tk_schema.demo_screening_cascade TO heart360tk;
GRANT SELECT ON heart360tk_schema.demo_screening_cascade TO heart360tk_cached;
