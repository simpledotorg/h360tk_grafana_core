import csv
import logging
import os
import shutil
import tempfile
from collections import defaultdict
from datetime import date

from import_versions.base import AGGREGATE_KEY
from import_versions.v1 import ImportVersion1
from orgunit_mapping import MappingRule

log = logging.getLogger(__name__)

# Rows of one v1 table: (ref_month, org_unit_id) -> {column: value}.
TableRows = dict[tuple[date, int], dict[str, int]]

# Distinct problems listed in one error, and line numbers shown per problem;
# the rest are only counted.
MAX_REPORTED_PROBLEMS = 10
MAX_REPORTED_LINES = 5


class ImportVersion2(ImportVersion1):
    """Pre-aggregated data from external systems, in long format.

    The zip holds metadata.json and orgunit.csv exactly as in v1, plus one
    heart360_merged_indicators.csv with a row per
    (ref_month, org_unit_id, indicator_key, value).
    The rows are rebuilt into the v1 reporting CSVs and imported through the v1
    path, so org unit mapping and aggregation behave exactly as for v1.

    indicator_key is the v1 column name.  A column name that several v1 tables
    share must name its table, e.g. ``patients_category.nb_patients_under_care``
    (the ``heart360_`` prefix is optional).
    """

    INDICATORS_FILE = 'heart360_merged_indicators.csv'
    INDICATOR_COLUMNS = ('ref_month', 'org_unit_id', 'indicator_key', 'value')
    TABLE_PREFIX = 'heart360_'

    def import_zip(
        self,
        conn,
        extract_dir: str,
        metadata: dict,
        mapping_rules: list[MappingRule] | None = None,
    ) -> None:
        orgunit_path = self._find_file(extract_dir, 'orgunit.csv')
        indicators_path = self._find_file(extract_dir, self.INDICATORS_FILE)

        table_columns = {
            table: self._get_table_columns(conn, table) for table in self.REPORTING_TABLES
        }
        org_ids = {row['leaf_id'] for row in self._read_orgunit_rows(orgunit_path)}
        tables = self._read_indicators(indicators_path, table_columns, org_ids)

        # Only the rebuilt files go to the v1 path, so nothing else in the zip is imported.
        staging_dir = tempfile.mkdtemp(prefix='v1_', dir=extract_dir)
        shutil.copyfile(orgunit_path, os.path.join(staging_dir, 'orgunit.csv'))
        for table, rows in tables.items():
            self._write_table_csv(
                os.path.join(staging_dir, f'{table}.csv'), table_columns[table], rows
            )
        log.info(
            '  Rebuilt %d v1 table(s) from %s: %s',
            len(tables),
            os.path.basename(indicators_path),
            ', '.join(sorted(tables)) or 'none',
        )

        super().import_zip(conn, staging_dir, metadata, mapping_rules=mapping_rules)

    @staticmethod
    def _find_file(directory: str, filename: str) -> str:
        """Path of ``filename`` in ``directory``, matched case-insensitively."""
        for name in os.listdir(directory):
            if name.lower() == filename:
                return os.path.join(directory, name)
        raise FileNotFoundError(f'{filename} not found in zip')

    def _indicator_catalog(
        self, table_columns: dict[str, list[str]]
    ) -> tuple[dict[str, tuple[str, str]], dict[str, list[str]]]:
        """Map each accepted indicator_key to its (table, column).

        Every column is reachable as ``<table>.<column>``; a column found in a
        single table also by its bare name.  Also returns the bare names that
        several tables share, with the qualified keys to use instead.
        """
        catalog: dict[str, tuple[str, str]] = {}
        qualified_by_column: dict[str, list[str]] = defaultdict(list)
        for table, columns in table_columns.items():
            dataset = table.removeprefix(self.TABLE_PREFIX)
            for column in columns:
                if column in AGGREGATE_KEY:
                    continue
                key = f'{dataset}.{column}'
                catalog[key] = (table, column)
                qualified_by_column[column].append(key)

        shared = {}
        for column, keys in qualified_by_column.items():
            if len(keys) == 1:
                catalog[column] = catalog[keys[0]]
            else:
                shared[column] = keys
        return catalog, shared

    def _resolve_indicator(
        self,
        key: str,
        catalog: dict[str, tuple[str, str]],
        shared: dict[str, list[str]],
    ) -> tuple[str, str]:
        dataset, dot, column = key.rpartition('.')
        if dot:
            key = f'{dataset.removeprefix(self.TABLE_PREFIX)}.{column}'
        if key in catalog:
            return catalog[key]
        if key in shared:
            raise ValueError(
                f'indicator_key {key!r} is in several datasets, use one of: '
                + ', '.join(shared[key])
            )
        raise ValueError(f'unknown indicator_key {key!r}')

    def _read_indicators(
        self,
        csv_path: str,
        table_columns: dict[str, list[str]],
        org_ids: set[int],
    ) -> dict[str, TableRows]:
        """Validate the indicators file and pivot it into rows per v1 table.

        Rows without an org_unit_id or value are skipped, as v1 imports those
        as nothing.  Every other problem is collected and raised together so
        the sender can fix the file in one go.
        """
        filename = os.path.basename(csv_path)
        catalog, shared = self._indicator_catalog(table_columns)
        tables: dict[str, TableRows] = defaultdict(lambda: defaultdict(dict))
        problems: dict[str, list[int]] = defaultdict(list)
        imported = skipped = 0

        with open(csv_path, 'r', encoding='utf-8-sig', newline='') as csv_file:
            reader = csv.DictReader(csv_file, skipinitialspace=True)
            reader.fieldnames = [name.strip().lower() for name in reader.fieldnames or []]
            missing = [c for c in self.INDICATOR_COLUMNS if c not in reader.fieldnames]
            if missing:
                raise ValueError(f'{filename} is missing column(s): {", ".join(missing)}')

            for line_no, row in enumerate(reader, start=2):
                ref_month, org_unit_id, key, value = (
                    (row.get(column) or '').strip() for column in self.INDICATOR_COLUMNS
                )
                if not org_unit_id or not value:
                    skipped += 1
                    continue
                try:
                    table, column = self._resolve_indicator(key.lower(), catalog, shared)
                    cell = (
                        self._parse_month(ref_month),
                        self._parse_org_unit(org_unit_id, org_ids),
                    )
                    count = self._parse_value(value)
                except ValueError as e:
                    problems[str(e)].append(line_no)
                    continue

                previous = tables[table][cell].setdefault(column, count)
                if previous != count:
                    problems[
                        f'{key} for org unit {cell[1]} in {cell[0]:%Y-%m} has values '
                        f'{previous} and {count}'
                    ].append(line_no)
                imported += 1

        if problems:
            raise ValueError(self._describe_problems(filename, problems))

        log.info(
            '  Read %d indicator value(s) from %s (%d row(s) without org unit or value skipped)',
            imported,
            filename,
            skipped,
        )
        return tables

    @staticmethod
    def _parse_month(raw: str) -> date:
        try:
            month = date.fromisoformat(raw)
        except ValueError:
            raise ValueError(f'ref_month {raw!r} is not a YYYY-MM-DD date') from None
        if month.day != 1:
            raise ValueError(f'ref_month {raw!r} must be the first day of the month')
        return month

    @staticmethod
    def _parse_whole_number(field: str, raw: str) -> int:
        try:
            return int(raw)
        except ValueError:
            raise ValueError(f'{field} {raw!r} is not a whole number') from None

    @classmethod
    def _parse_org_unit(cls, raw: str, org_ids: set[int]) -> int:
        org_unit_id = cls._parse_whole_number('org_unit_id', raw)
        if org_unit_id not in org_ids:
            raise ValueError(f'org_unit_id {org_unit_id} is not in orgunit.csv')
        return org_unit_id

    @classmethod
    def _parse_value(cls, raw: str) -> int:
        value = cls._parse_whole_number('value', raw)
        if value < 0:
            raise ValueError(f'value {value} is negative')
        return value

    @staticmethod
    def _describe_problems(filename: str, problems: dict[str, list[int]]) -> str:
        """One message listing each distinct problem with the lines it occurs on."""
        listed = []
        for message, lines in list(problems.items())[:MAX_REPORTED_PROBLEMS]:
            shown = ', '.join(map(str, lines[:MAX_REPORTED_LINES]))
            if len(lines) > MAX_REPORTED_LINES:
                shown += ', ...'
            listed.append(f'{message} (line {shown})')
        more = len(problems) - len(listed)
        return (
            f'{filename} has {len(problems)} problem(s): ' + '; '.join(listed)
            + (f'; and {more} more' if more else '')
        )

    @staticmethod
    def _write_table_csv(path: str, columns: list[str], rows: TableRows) -> None:
        """Write rows in the table's own column order, which the v1 COPY relies on.

        Columns the sender did not provide stay empty and load as NULL.
        """
        with open(path, 'w', encoding='utf-8', newline='') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(columns)
            for (ref_month, org_unit_id), values in sorted(rows.items()):
                record = {'ref_month': ref_month.isoformat(), 'org_unit_id': org_unit_id, **values}
                writer.writerow(record.get(column, '') for column in columns)
