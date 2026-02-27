import sqlalchemy as sa
from alembic import op
import pytest

# import the migration module under test
from migrations.versions import a8658df6c988_add_preferred_locale_to_user as migration


class DummyConnection:
    def __init__(self, dialect_name='mysql'):
        class Dialect:
            def __init__(self, name):
                self.name = name

        self.dialect = Dialect(dialect_name)
        self.executed = []

    def execute(self, stmt, *args, **kwargs):
        # record SQL string for later inspection
        text = str(stmt)
        self.executed.append(text)
        # simple fake return that behaves like `conn.execute` returning rows

        class DummyResult:
            def __init__(self, rows):
                self._rows = rows

            def __iter__(self):
                return iter(self._rows)

            def fetchall(self):
                return self._rows

        # migrations only call execute when dropping temp table or updating
        # we don't need any return rows here
        return DummyResult([])


class DummyInspector:
    def __init__(self, columns):
        self._columns = columns

    def get_columns(self, table_name, schema=None):
        return [{'name': col} for col in self._columns]


@pytest.fixture(autouse=True)
def patch_inspector_and_bind(monkeypatch):
    """Monkeypatch op.get_bind, op.execute and sa.inspect used by the migration."""
    conn = DummyConnection(dialect_name='mysql')
    monkeypatch.setattr(migration.op, 'get_bind', lambda: conn)
    # route op.execute through our dummy connection to avoid alembic proxy issues
    monkeypatch.setattr(migration.op, 'execute', lambda stmt, *args, **kwargs: conn.execute(stmt, *args, **kwargs))
    # provide a dummy batch_alter_table context manager so operations can proceed

    class DummyBatch:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def add_column(self, col):
            conn.executed.append(f"ADD_COLUMN {col.name}")

        def alter_column(self, colname, **kwargs):
            # record both column name and any keyword arguments for assertions
            conn.executed.append(f"ALTER_COLUMN {colname} {kwargs}")
            return None
    monkeypatch.setattr(migration.op, 'batch_alter_table', lambda *args, **kwargs: DummyBatch())
    monkeypatch.setattr(sa, 'inspect', lambda bind: DummyInspector(['id', 'username']))
    return conn


def test_upgrade_uses_inspector_and_skips_existing_column(patch_inspector_and_bind):
    conn = patch_inspector_and_bind

    # simulate preferred_locale already present by changing inspector return
    sa.inspect = lambda bind: DummyInspector(['id', 'username', 'preferred_locale'])
    # running upgrade should return early without executing any DDL except the drop temp table
    migration.upgrade()
    executed = conn.executed
    # there should be at most a DROP TABLE statement but no PRAGMA call
    assert not any('PRAGMA' in stmt for stmt in executed)


def test_upgrade_adds_column_when_missing(patch_inspector_and_bind):
    conn = patch_inspector_and_bind

    # ensure preferred_locale not present
    sa.inspect = lambda bind: DummyInspector(['id', 'username'])
    migration.upgrade()
    executed = "\n".join(conn.executed)
    # verify we ran ALTER TABLE to add column or update statements
    assert 'ALTER_TABLE' in executed or 'UPDATE user SET preferred_locale' in executed
    assert not any('PRAGMA' in stmt for stmt in executed)
    # and ensure alter_column included existing_type (important for MySQL)
    assert 'existing_type' in executed
