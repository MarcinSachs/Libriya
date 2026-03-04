import pytest

from scripts.manage_db import check_migrations_needed


class DummyContext:
    def __init__(self, heads):
        self._heads = heads

    def get_current_heads(self):
        return self._heads

    def get_current_revision(self):
        # mimic old alembic behaviour
        if not self._heads:
            return None
        if len(self._heads) == 1:
            return self._heads[0]
        raise Exception("Version table 'alembic_version' has more than one head present; please use get_current_heads()")


class DummyScript:
    def __init__(self, head):
        self._head = head

    def get_current_head(self):
        return self._head


class DummyConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def make_context(monkeypatch, heads, head_rev):
    # monkeypatch alembic helpers imported in the function
    import alembic.script
    import alembic.runtime.migration

    monkeypatch.setattr(alembic.script.ScriptDirectory, 'from_config', lambda cfg: DummyScript(head_rev))
    monkeypatch.setattr(alembic.runtime.migration.MigrationContext, 'configure', lambda conn: DummyContext(heads))

    # also monkeypatch the entire ``db`` object used in the script with a
    # fake that implements the minimal interface expected by
    # ``create_app()`` and ``check_migrations_needed()``.
    class FakeDB:
        def init_app(self, app):
            # called by create_app; do nothing
            pass

        @property
        def engine(self):
            # return self so that ``db.engine.connect()`` works
            return self

        def connect(self):
            return DummyConnection()

    import scripts.manage_db as mdb
    monkeypatch.setattr(mdb, 'db', FakeDB())


def test_check_migrations_no_heads(monkeypatch):
    make_context(monkeypatch, [], 'c')
    needs, curr, head = check_migrations_needed()
    assert needs
    assert curr is None
    assert head == 'c'


def test_check_migrations_single_head_matching(monkeypatch):
    make_context(monkeypatch, ['c'], 'c')
    needs, curr, head = check_migrations_needed()
    assert not needs
    assert curr == 'c'
    assert head == 'c'


def test_check_migrations_multi_heads(monkeypatch):
    # script head returns normally
    make_context(monkeypatch, ['a', 'b'], 'c')
    needs, curr, head = check_migrations_needed()
    assert needs
    assert curr == 'a,b'
    assert head == 'c'

    # prepare for init_db: patch check_migrations_needed to simulate comma revision
    monkeypatch.setattr('scripts.manage_db.check_migrations_needed', lambda: (True, 'a,b', 'c'))

    # stub flask_migrate.upgrade to mimic error from multiple heads so the
    # script falls back to alembic.command.upgrade and that also fails
    import scripts.manage_db as mdb

    def raise_heads_error(rev=None):
        raise Exception('Multiple head revisions present')
    monkeypatch.setattr(mdb, 'upgrade', raise_heads_error)

    # have alembic.command.upgrade throw the "Path doesn't exist" message
    import alembic.command

    def fake_upgrade(cfg, rev):
        raise Exception('Path doesn\'t exist: heads')
    monkeypatch.setattr(alembic.command, 'upgrade', fake_upgrade)

    # run init_db w/ minimal fake db to avoid real connection - should return False
    from scripts.manage_db import init_db

    class DummyConn:
        def connect(self):
            class Ctx:
                def __enter__(self): return self
                def __exit__(self, *a): pass
            return Ctx()
    monkeypatch.setattr(mdb, 'db', DummyConn())

    assert init_db() is False


def test_check_migrations_script_multiple_heads(monkeypatch):
    # simulate script.get_current_head raising an exception due to branching
    class BrokenScript:
        def get_current_head(self):
            raise Exception(
                "The script directory has multiple heads (due to branching).Please use get_heads(), or merge the branches using alembic merge.")

        def get_heads(self):
            return ['x', 'y']
    import alembic.script
    import alembic.runtime.migration
    # patch context same as before
    make_context(monkeypatch, ['a'], 'c')
    # override previously set ScriptDirectory from_config to return our broken
    monkeypatch.setattr(alembic.script.ScriptDirectory, 'from_config', lambda cfg: BrokenScript())

    needs, curr, head = check_migrations_needed()
    assert needs
    assert curr == 'a'
    assert head == 'x'  # first entry of heads list returned


def test_init_db_with_comma_revision(monkeypatch):
    # ensure init_db uses upgrade('heads') when current_rev contains comma
    called = []

    # patch check_migrations_needed to enforce values
    monkeypatch.setattr('scripts.manage_db.check_migrations_needed', lambda: (True, 'a,b', 'a'))

    # track alembic.command.upgrade calls (flask-migrate upgrade not used in this branch)
    import alembic.command

    def fake_alembic_upgrade(cfg, rev):
        called.append(rev)

    monkeypatch.setattr(alembic.command, 'upgrade', fake_alembic_upgrade)

    # create connection helper used by FakeDB2
    class DummyConn2:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class FakeDB2:
        def init_app(self, app):
            pass

        @property
        def engine(self):
            return self

        def connect(self):
            return DummyConn2()

        def create_all(self):
            pass
    monkeypatch.setattr('scripts.manage_db.db', FakeDB2())
    # stub out sqlalchemy.inspect used earlier in init_db

    class DummyInspector:
        def get_table_names(self):
            # include alembic_version to simulate an existing migration table
            return ['alembic_version']
    import sqlalchemy
    monkeypatch.setattr(sqlalchemy, 'inspect', lambda engine: DummyInspector())

    assert __import__('scripts.manage_db').manage_db.init_db() is True
    assert called == ['heads']
