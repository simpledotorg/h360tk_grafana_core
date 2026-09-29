-- ============================================================================
-- Migration: add Kemendagri administrative codes to org_units
-- Apply to an EXISTING 0.5.1 database that was initialised before this feature.
-- Idempotent and backward-compatible (existing 2/3-arg functions are untouched).
--
--   kode prov -> level 1 (Region), kode kab -> level 2 (District),
--   kode kec  -> level 3 (Facility), kode desa -> level 4 (Sub-Facility)
--
-- Usage (from the repo root, container running):
--   docker exec -i postgres psql -U h360tk_root -d heart360tk_database \
--     < pg_init_scripts/migrations/0.5.1_add_kemendagri_codes.sql
-- ============================================================================
SET ROLE heart360tk;
SET search_path TO heart360tk_schema;

ALTER TABLE org_units ADD COLUMN IF NOT EXISTS code VARCHAR(32);
CREATE INDEX IF NOT EXISTS idx_org_units_code ON org_units(code);

CREATE OR REPLACE FUNCTION upsert_org_unit(
    p_name VARCHAR, p_level INTEGER, p_parent_id INTEGER, p_code VARCHAR)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_id INTEGER;
BEGIN
    v_id := upsert_org_unit(p_name, p_level, p_parent_id);
    IF p_code IS NOT NULL AND btrim(p_code) <> '' THEN
        UPDATE org_units SET code = p_code
        WHERE id = v_id AND code IS DISTINCT FROM p_code;
    END IF;
    RETURN v_id;
END;
$$;

CREATE OR REPLACE FUNCTION upsert_org_unit_chain(
    p_names VARCHAR[], p_levels INTEGER[], p_codes VARCHAR[])
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_parent_id INTEGER := NULL;
    v_id INTEGER;
    i INTEGER;
    v_code VARCHAR;
BEGIN
    FOR i IN 1..array_length(p_names, 1) LOOP
        v_code := NULL;
        IF p_codes IS NOT NULL AND i <= array_length(p_codes, 1) THEN
            v_code := p_codes[i];
        END IF;
        v_id := upsert_org_unit(p_names[i], p_levels[i], v_parent_id, v_code);
        v_parent_id := v_id;
    END LOOP;
    RETURN v_id;
END;
$$;
