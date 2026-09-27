BEGIN;

SET ROLE heart360tk;

SET search_path TO heart360tk_schema;

CREATE TABLE IF NOT EXISTS programme_protocols (
    country_code   VARCHAR(64) NOT NULL,
    programme_code VARCHAR(64) NOT NULL,
    protocol_code  VARCHAR(16) NOT NULL,
    PRIMARY KEY (country_code, programme_code),
    CONSTRAINT programme_protocols_protocol_code_check
        CHECK (protocol_code IN ('AATTCC', 'ATTACC'))
);

CREATE TABLE IF NOT EXISTS protocol_drugs (
    country_code   VARCHAR(64)  NOT NULL,
    programme_code VARCHAR(64)  NOT NULL,
    drug_name      VARCHAR(255) NOT NULL,
    dosage         VARCHAR(64)  NOT NULL,
    rxnorm_code    VARCHAR(64)  NOT NULL,
    drug_category  VARCHAR(64)  NOT NULL,
    stock_tracked  BOOLEAN      NOT NULL,
    PRIMARY KEY (country_code, programme_code, rxnorm_code),
    CONSTRAINT protocol_drugs_programme_fkey
        FOREIGN KEY (country_code, programme_code)
        REFERENCES programme_protocols (country_code, programme_code)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

INSERT INTO programme_protocols (country_code, programme_code, protocol_code)
VALUES ('India', 'IHCI', 'AATTCC')
ON CONFLICT (country_code, programme_code) DO UPDATE
    SET protocol_code = EXCLUDED.protocol_code;

INSERT INTO protocol_drugs (
    country_code, programme_code, drug_name, dosage, rxnorm_code, drug_category, stock_tracked
) VALUES
    ('India', 'IHCI', 'Amlodipine',      '5 mg',    '329528', 'hypertension_ccb',      TRUE),
    ('India', 'IHCI', 'Amlodipine',      '10 mg',   '329526', 'hypertension_ccb',      TRUE),
    ('India', 'IHCI', 'Telmisartan',     '40 mg',   '316764', 'hypertension_arb',      TRUE),
    ('India', 'IHCI', 'Telmisartan',     '80 mg',   '316765', 'hypertension_arb',      TRUE),
    ('India', 'IHCI', 'Chlorthalidone',  '12.5 mg', '331132', 'hypertension_diuretic', TRUE),
    ('India', 'IHCI', 'Chlorthalidone',  '25 mg',   '197499', 'hypertension_diuretic', TRUE)
ON CONFLICT (country_code, programme_code, rxnorm_code) DO UPDATE
    SET drug_name     = EXCLUDED.drug_name,
        dosage        = EXCLUDED.dosage,
        drug_category = EXCLUDED.drug_category,
        stock_tracked = EXCLUDED.stock_tracked;

COMMIT;
