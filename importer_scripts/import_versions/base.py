import csv
import logging
import os
from datetime import datetime, timezone
from typing import NamedTuple

from psycopg2 import sql

from orgunit_mapping import MappingRule, find_matching_rule

log = logging.getLogger(__name__)

# Unique key of every monthly reporting table (see idx_*_org_month indexes).
AGGREGATE_KEY = ('org_unit_id', 'ref_month')


class ResolvedOrgUnit(NamedTuple): 
    """Where one leaf org unit ended up in the central hierarchy.

    ``level_shift`` is how far a mapping rule moved the org unit from the level
    its leaf node gave it.  Descendants inherit the shift so the subtree keeps
    its shape; it is 0 for everything that imports unmapped.
    """

    central_id: int
    level_shift: int


class BaseImportVersion:
    REPORTING_TABLES: list[str] = []
    SKIP_FILES = frozenset({'metadata.json', 'orgunit.csv'})

    @classmethod
    def truncate_reporting_tables(cls, conn) -> None:
        from import_versions import all_reporting_tables

        with conn.cursor() as cur:
            for table_name in all_reporting_tables():
                cur.execute(
                    sql.SQL('TRUNCATE TABLE heart360tk_reporting.{}').format(
                        sql.Identifier(table_name)
                    )
                )
                log.info('  Truncated heart360tk_reporting.%s', table_name)

    def import_zip(
        self,
        conn,
        extract_dir: str,
        metadata: dict,
        mapping_rules: list[MappingRule] | None = None,
    ) -> None:
        raise NotImplementedError

    def csv_to_table_name(self, csv_filename: str) -> str | None:
        table_name = os.path.splitext(csv_filename)[0].lower()
        if table_name in self.REPORTING_TABLES:
            return table_name
        return None

    def _read_orgunit_rows(self, csv_path: str) -> list[dict]:
        rows = []
        with open(csv_path, 'r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                parent_raw = (row.get('parent_id') or '').strip()
                rows.append({
                    'leaf_id': int(row['id']),
                    'name': row['name'].strip(),
                    'level': int(row['level']),
                    'leaf_parent_id': int(parent_raw) if parent_raw else None,
                })
        rows.sort(key=lambda item: (item['level'], item['leaf_id']))
        return rows

    def _upsert_org_unit_mapping(
        self,
        conn,
        source_key: str,
        leaf_org_unit_id: int,
        central_org_unit_id: int,
        metadata: dict,
    ) -> None:
        """Persist leaf→central org_unit id mapping (all hierarchy levels)."""
        extract_epoch = metadata.get('generated_at_epoch')
        last_extract_date = (
            datetime.fromtimestamp(extract_epoch, tz=timezone.utc)
            if extract_epoch is not None
            else None
        )

        with conn.cursor() as cur:
            cur.execute(
                '''
                INSERT INTO heart360tk_reporting.import_facility_mapping
                    (leaf_node_key, leaf_org_unit_id, central_org_unit_id,
                     last_updated_date, last_extract_date)
                VALUES (%s, %s, %s, NOW(), %s)
                ''',
                (source_key, leaf_org_unit_id, central_org_unit_id, last_extract_date),
            )

    def _upsert_org_unit(self, cur, name: str, level: int, parent_id: int | None) -> int:
        """Match or create one central org unit and return its id."""
        cur.execute(
            'SELECT heart360tk_schema.upsert_org_unit(%s, %s, %s)',
            (name, level, parent_id),
        )
        central_id = cur.fetchone()[0]
        if central_id is None:
            raise ValueError(
                f'Could not upsert org unit {name!r} '
                f'(level={level}, parent_id={parent_id})'
            )
        return central_id

    def _resolve_target_hierarchy(self, cur, hierarchy: tuple[str, ...]) -> int | None:
        """Resolve/create the ancestor chain of a mapping rule, top level first.

        Returns the central id of the last ancestor — the parent the mapped org
        unit is placed under — or None when the rule names no ancestors.
        """
        parent_id = None
        for level, ancestor_name in enumerate(hierarchy, start=1):
            parent_id = self._upsert_org_unit(cur, ancestor_name, level, parent_id)
        return parent_id

    def _sync_org_unit_id_sequence(self, cur) -> None:
        """Keep the SERIAL sequence ahead of explicitly inserted org unit ids."""
        cur.execute(
            '''
            SELECT setval(
                pg_get_serial_sequence('heart360tk_schema.org_units', 'id'),
                GREATEST(
                    nextval(pg_get_serial_sequence('heart360tk_schema.org_units', 'id')),
                    (SELECT COALESCE(MAX(id), 1) FROM heart360tk_schema.org_units)
                )
            )
            '''
        )

    def _place_mapped_org_unit(
        self,
        cur,
        rule: MappingRule,
        leaf_name: str,
    ) -> tuple[int, int]:
        """Pin an org unit onto the central record the rule names.

        The record sits directly under the last entry of targetOrgUnitHierarchy.
        With targetOrgUnitId it is that record; without one it is the record
        named targetOrgUnitName at that spot, created on first use and reused
        by later imports.
        Returns its (central id, central level).
        """
        parent_id = self._resolve_target_hierarchy(cur, rule.target_org_unit_hierarchy)
        if rule.target_org_unit_id is None:
            central_id = self._upsert_org_unit(
                cur, rule.target_org_unit_name, rule.target_level, parent_id
            )
        else:
            central_id = self._place_org_unit_by_id(cur, rule, leaf_name, parent_id)
        return central_id, rule.target_level

    def _place_org_unit_by_id(
        self,
        cur,
        rule: MappingRule,
        leaf_name: str,
        parent_id: int | None,
    ) -> int:
        """Create or move the record with id targetOrgUnitId under parent_id.

        An existing record always keeps its own name; targetOrgUnitName only
        names a record created here.
        """
        target_id = rule.target_org_unit_id

        cur.execute(
            '''
            SELECT name, level, parent_id
            FROM heart360tk_schema.org_units
            WHERE id = %s
            ''',
            (target_id,),
        )
        existing = cur.fetchone()

        if existing is None:
            # New record: use targetOrgUnitName if provided, otherwise the leaf name.
            name = rule.target_org_unit_name or leaf_name
            placement = (name, rule.target_level, parent_id)
            cur.execute(
                '''
                INSERT INTO heart360tk_schema.org_units (id, name, level, parent_id)
                VALUES (%s, %s, %s, %s)
                ''',
                (target_id, *placement),
            )
            self._sync_org_unit_id_sequence(cur)
            action = 'Created'
        else:
            # Existing record: always keep the central name as-is; targetOrgUnitName
            # is ignored so the central admin owns the name, not the leaf node.
            name = existing[0]
            placement = (name, rule.target_level, parent_id)
            if placement != tuple(existing):
                cur.execute(
                    '''
                    UPDATE heart360tk_schema.org_units
                    SET level = %s, parent_id = %s
                    WHERE id = %s
                    ''',
                    (rule.target_level, parent_id, target_id),
                )
                action = 'Moved'
            else:
                action = None

        if action is not None:
            log.info(
                '    %s central org unit id=%d (%s, level=%d, parent_id=%s)',
                action, target_id, *placement,
            )
        return target_id

    def _place_leaf_org_unit(
        self,
        cur,
        row: dict,
        parent: ResolvedOrgUnit | None,
    ) -> tuple[int, int]:
        """Resolve an unmapped org unit against the leaf node's own hierarchy.

        Returns its (central id, central level).
        """
        central_level = row['level'] + (parent.level_shift if parent else 0)
        if central_level < 1:
            raise ValueError(
                f'Org unit {row["name"]!r} (leaf id {row["leaf_id"]}) would land at '
                f'level {central_level} — a mapping rule placed an ancestor too '
                'high in the central hierarchy'
            )
        central_id = self._upsert_org_unit(
            cur, row['name'], central_level, parent.central_id if parent else None
        )
        return central_id, central_level

    def _resolve_parent(
        self,
        row: dict,
        resolved: dict[int, ResolvedOrgUnit],
        source_key: str,
    ) -> ResolvedOrgUnit | None:
        leaf_parent_id = row['leaf_parent_id']
        if leaf_parent_id is None:
            return None

        parent = resolved.get(leaf_parent_id)
        if parent is None:
            raise ValueError(
                f'orgunit.csv parent id {leaf_parent_id} for leaf id {row["leaf_id"]} '
                f'was not processed before its child (source_key={source_key})'
            )
        return parent

    def import_org_units(
        self,
        conn,
        extract_dir: str,
        source_key: str,
        metadata: dict,
        mapping_rules: list[MappingRule] | None = None,
    ) -> dict[int, int]:
        """Merge orgunit.csv into central org_units; return leaf_id -> central_id map.

        Each leaf node may define its own hierarchy depth (e.g. 2, 4, or 5 levels).
        Rows are processed parent-before-child using level order from the CSV.
        Every leaf org_unit id is recorded in import_facility_mapping for reporting
        table id remapping, regardless of level.

        An org unit matching one of mapping_rules is pinned onto the central
        record that rule names instead of being resolved against its leaf node's
        hierarchy.  Without a match — or without any rules — it imports exactly
        as it did before mapping existed.
        """
        csv_path = os.path.join(extract_dir, 'orgunit.csv')
        if not os.path.isfile(csv_path):
            raise FileNotFoundError('orgunit.csv not found in zip')

        org_rows = self._read_orgunit_rows(csv_path)
        mapping_rules = mapping_rules or []
        resolved: dict[int, ResolvedOrgUnit] = {}

        with conn.cursor() as cur:
            cur.execute(
                '''
                DELETE FROM heart360tk_reporting.import_facility_mapping
                WHERE leaf_node_key = %s
                ''',
                (source_key,),
            )

            for row in org_rows:
                leaf_id, name, level = row['leaf_id'], row['name'], row['level']
                parent = self._resolve_parent(row, resolved, source_key)
                rule = find_matching_rule(mapping_rules, leaf_id, name)

                if rule is not None:
                    central_id, central_level = self._place_mapped_org_unit(
                        cur, rule, name
                    )
                else:
                    central_id, central_level = self._place_leaf_org_unit(
                        cur, row, parent
                    )

                resolved[leaf_id] = ResolvedOrgUnit(central_id, central_level - level)
                self._upsert_org_unit_mapping(
                    conn, source_key, leaf_id, central_id, metadata
                )
                log.info(
                    '  Mapped org unit leaf_id=%d -> central_id=%d (%s, level=%d)%s',
                    leaf_id,
                    central_id,
                    name,
                    central_level,
                    f' by rule {rule.describe()}' if rule else '',
                )

        log.info(
            '  Merged %d org unit(s) for source_key=%s',
            len(resolved),
            source_key,
        )
        return {leaf_id: unit.central_id for leaf_id, unit in resolved.items()}

    def _get_table_columns(self, conn, table_name: str) -> list[str]:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'heart360tk_reporting'
                  AND table_name = %s
                ORDER BY ordinal_position
                ''',
                (table_name,),
            )
            return [row[0] for row in cur.fetchall()]

    def _mapped_insert_sql(
        self,
        table_name: str,
        table_columns: list[str],
        temp_table: str,
    ) -> sql.Composed:
        """INSERT that moves staged rows onto their central org units.

        When the table is keyed by (org_unit_id, ref_month), every other column
        is a patient count, so rows landing on the same central org unit and
        month are added together: within this zip by GROUP BY, and across leaf
        nodes imported earlier in the run by ON CONFLICT.  NULL + n keeps n.
        """
        target = sql.Identifier(table_name)
        temp = sql.Identifier(temp_table)
        mapped_from = sql.SQL(
            'FROM {temp} t '
            'JOIN heart360tk_reporting.import_facility_mapping m '
            '  ON m.leaf_node_key = %s '
            ' AND m.leaf_org_unit_id = t.org_unit_id'
        ).format(temp=temp)

        def staged(column: str) -> sql.Composable:
            if column == 'org_unit_id':
                return sql.SQL('m.central_org_unit_id')
            return sql.SQL('t.{}').format(sql.Identifier(column))

        columns = sql.SQL(', ').join(map(sql.Identifier, table_columns))

        if not set(AGGREGATE_KEY) <= set(table_columns):
            return sql.SQL('INSERT INTO heart360tk_reporting.{target} ({columns}) '
                           'SELECT {values} {mapped_from}').format(
                target=target,
                columns=columns,
                values=sql.SQL(', ').join(staged(c) for c in table_columns),
                mapped_from=mapped_from,
            )

        counts = [c for c in table_columns if c not in AGGREGATE_KEY]
        values = sql.SQL(', ').join(
            staged(c) if c in AGGREGATE_KEY
            else sql.SQL('SUM({})').format(staged(c))
            for c in table_columns
        )
        on_conflict = (
            sql.SQL('DO UPDATE SET {}').format(sql.SQL(', ').join(
                sql.SQL('{col} = COALESCE({target}.{col} + EXCLUDED.{col}, '
                        '{target}.{col}, EXCLUDED.{col})').format(
                    col=sql.Identifier(c), target=target,
                )
                for c in counts
            ))
            if counts else sql.SQL('DO NOTHING')
        )

        return sql.SQL(
            'INSERT INTO heart360tk_reporting.{target} ({columns}) '
            'SELECT {values} {mapped_from} '
            'GROUP BY {group_by} '
            'ON CONFLICT ({key}) {on_conflict}'
        ).format(
            target=target,
            columns=columns,
            values=values,
            mapped_from=mapped_from,
            group_by=sql.SQL(', ').join(staged(c) for c in AGGREGATE_KEY),
            key=sql.SQL(', ').join(map(sql.Identifier, AGGREGATE_KEY)),
            on_conflict=on_conflict,
        )

    def copy_csv_to_table(
        self,
        conn,
        table_name: str,
        csv_path: str,
        source_key: str,
    ) -> None:
        table_columns = self._get_table_columns(conn, table_name)
        if not table_columns:
            raise ValueError(f'No columns found for reporting table {table_name}')

        temp_table = f'tmp_import_{table_name}'

        with conn.cursor() as cur:
            cur.execute(
                sql.SQL(
                    'CREATE TEMP TABLE {} (LIKE heart360tk_reporting.{} INCLUDING DEFAULTS) '
                    'ON COMMIT DROP'
                ).format(
                    sql.Identifier(temp_table),
                    sql.Identifier(table_name),
                )
            )

            with open(csv_path, 'r', encoding='utf-8') as csv_file:
                cur.copy_expert(
                    sql.SQL(
                        'COPY {} FROM STDIN WITH (FORMAT CSV, HEADER TRUE)'
                    ).format(sql.Identifier(temp_table)).as_string(conn),
                    csv_file,
                )

            if 'org_unit_id' in table_columns:
                cur.execute(
                    self._mapped_insert_sql(table_name, table_columns, temp_table),
                    (source_key,),
                )
            else:
                cur.execute(
                    sql.SQL(
                        'INSERT INTO heart360tk_reporting.{target} '
                        'SELECT * FROM {temp}'
                    ).format(
                        target=sql.Identifier(table_name),
                        temp=sql.Identifier(temp_table),
                    )
                )

            inserted = cur.rowcount

        if inserted == 0:
            log.warning(
                '  No rows imported into %s from %s',
                table_name,
                os.path.basename(csv_path),
            )
        else:
            log.info(
                '  Imported %d row(s) into %s from %s',
                inserted,
                table_name,
                os.path.basename(csv_path),
            )
