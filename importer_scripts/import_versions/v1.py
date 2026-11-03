import logging
import os

from import_versions.base import INDICATORS_FILE, BaseImportVersion
from orgunit_mapping import MappingRule

log = logging.getLogger(__name__)


class ImportVersion1(BaseImportVersion):
    REPORTING_TABLES = [
        'heart360_patients_category',
        'heart360_patients_under_care',
        'heart360_patients_registered',
        'heart360_blood_sugar_controlled',
        'heart360_blood_sugar_severity',
        'heart360_blood_sugar_missed_visits',
        'heart360_dm_bp_control',
        'heart360_dm_patients_under_care',
        'heart360_overdue_start_of_month',
        'heart360_overdue_patients_called',
        'heart360_overdue_returned_to_care',
        'heart360_dm_patients_catagory',
    ]

    @classmethod
    def check_files(cls, names: list[str]) -> str | None:
        # The v2 indicators file would be skipped here as an unknown CSV and
        # the zip reported as imported with no data.
        if INDICATORS_FILE in map(str.lower, names):
            return (
                f'{INDICATORS_FILE} is a version 2 file but metadata.json has '
                'import_export_version 1; set it to 2'
            )
        return None

    def import_zip(
        self,
        conn,
        extract_dir: str,
        metadata: dict,
        mapping_rules: list[MappingRule] | None = None,
    ) -> None:
        source_key = metadata.get('source_key', '')
        log.info(
            'Importing zip for source_key=%s (import_export_version=%s)',
            source_key,
            metadata.get('import_export_version'),
        )

        self.import_org_units(
            conn, extract_dir, source_key, metadata, mapping_rules=mapping_rules
        )

        for filename in sorted(os.listdir(extract_dir)):
            if filename in self.SKIP_FILES:
                continue
            if not filename.lower().endswith('.csv'):
                log.debug('  Skipping non-CSV file: %s', filename)
                continue

            table_name = self.csv_to_table_name(filename)
            if table_name is None:
                log.warning('  Skipping unknown CSV: %s', filename)
                continue

            self.copy_csv_to_table(
                conn,
                table_name,
                os.path.join(extract_dir, filename),
                source_key,
            )
