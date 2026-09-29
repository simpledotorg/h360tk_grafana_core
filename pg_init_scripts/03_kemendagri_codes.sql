-- ============================================================================
-- Kemendagri administrative codes on org_units (additive, backward-compatible)
--
-- Attaches one optional Kemendagri code per hierarchy level:
--   kode prov -> level 1 (Region), kode kab -> level 2 (District),
--   kode kec  -> level 3 (Facility), kode desa -> level 4 (Sub-Facility)
--
-- Runs automatically on a fresh database init (after 01_heart360_tables.sql).
-- For an existing database, apply migrations/0.5.1_add_kemendagri_codes.sql.
-- ============================================================================
SET ROLE heart360tk;
SET search_path TO heart360tk_schema;

-- 1. Add the (nullable) code column to org_units.
ALTER TABLE org_units ADD COLUMN IF NOT EXISTS code VARCHAR(32);
CREATE INDEX IF NOT EXISTS idx_org_units_code ON org_units(code);

-- 2. Single-node upsert overload that also stores/refreshes the code.
--    Reuses the existing 3-argument upsert_org_unit for name/level/parent logic.
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

-- 3. Chain upsert overload carrying one code per level (top to bottom).
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
