import os
import json
import tempfile
import pytest
from hypothesis import given, strategies as st
from psycopg2 import OperationalError, ProgrammingError, Error as PsycopgError
import sys
from pathlib import Path
# Ensure src in path
src_path = Path(__file__).parent.parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
from src.database_manager import (
    Workflow,
    DatabaseManager,
    WorkflowError,
)

#-----------------------------------------------------------------------------#
# Fixtures & Stubs
#-----------------------------------------------------------------------------#
class DummyEmbeddingService:
    def get_embeddings(self, text: str):
        return [float(len(text))] * 8
    def normalize_embedding(self, emb):
        return [round(x / sum(emb), 3) if sum(emb) else 0.0 for x in emb]

class StubCursor:
    def __init__(self, exists=True, count=0, rows=None):
        self._exists = exists
        self._count = count
        self._rows = rows or []
        self._last = None
    def execute(self, sql, params=None):
        if 'SELECT EXISTS' in sql:
            self._last = 'exists'
        elif 'COUNT(*)' in sql:
            self._last = 'count'
        elif sql.strip().upper().startswith('INSERT INTO'): 
            self._last = 'insert'
        else:
            self._last = 'select'
    def fetchone(self):
        if self._last == 'exists': return (self._exists,)
        if self._last == 'count': return (self._count,)
        return (None,)
    def fetchall(self):
        return self._rows
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): pass

class StubConn:
    def __init__(self, cursor): self._cursor = cursor
    def cursor(self): return self._cursor
    def commit(self): pass
    def close(self): pass
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): pass

class StubPool:
    def __init__(self, conn, maxconn=5):
        self._conn = conn
        self.maxconn = maxconn
    def getconn(self): return self._conn
    def putconn(self, conn): pass
    def closeall(self): pass

@pytest.fixture
def db_manager(monkeypatch):
    dummy = DummyEmbeddingService()
    # default: table exists, count=0, one good row
    cursor = StubCursor(exists=True, count=0,
                        rows=[(1, 'd', json.dumps({'main':{'state':{},'nodes':[], 'edges':[]}}), 0.75)])
    conn = StubConn(cursor)
    pool = StubPool(conn)
    dm = DatabaseManager(embedding_service=dummy, db_pool=pool)
    return dm

#-----------------------------------------------------------------------------#
# Property-Based Testing for Workflow.normalize
#-----------------------------------------------------------------------------#
@given(
    state=st.one_of(st.dictionaries(st.text(), st.integers()), st.integers(), st.none()),
    nodes=st.one_of(st.lists(st.text()), st.text(), st.none()),
    edges=st.one_of(st.lists(st.text()), st.text(), st.none()),
    missing=st.one_of(st.lists(st.dictionaries(st.text(), st.text())), st.text(), st.none())
)
def test_normalize_properties(state, nodes, edges, missing):
    wf = Workflow(state=state, nodes=nodes, edges=edges, missing_nodes=missing)
    out = wf.normalize()
    assert isinstance(out['state'], dict)
    assert isinstance(out['nodes'], list)
    assert isinstance(out['edges'], list)
    assert isinstance(out['missing_nodes'], list)

#-----------------------------------------------------------------------------#
# load_sql_file Tests
#-----------------------------------------------------------------------------#
def test_load_sql_valid(tmp_path, db_manager):
    path = tmp_path / 'f.sql'
    path.write_text('SELECT 1;')
    assert 'SELECT' in db_manager.load_sql_file(str(path))

@pytest.mark.parametrize('name', ['nope.sql', ''] )
def test_load_sql_missing_or_blank(name, db_manager):
    with pytest.raises(Exception):
        db_manager.load_sql_file(name)

#-----------------------------------------------------------------------------#
# setup_database Tests
#-----------------------------------------------------------------------------#
def test_setup_database_default(tmp_path, db_manager, monkeypatch):
    # stub connect to return stub conn
    tmp = tmp_path / 'demo.sql'
    tmp.write_text('CREATE X;')
    monkeypatch.delenv('DB_USER', raising=False)
    # missing env causes KeyError
    with pytest.raises(KeyError):
        db_manager.setup_database(sql_file_path=str(tmp))

# override env and stub connect
@pytest.fixture(autouse=True)
def stub_connect(monkeypatch):
    def fake_connect(*args, **kw):
        return StubConn(StubCursor(exists=False, count=0))
    monkeypatch.setenv('DB_USER','u')
    monkeypatch.setenv('DB_PASSWORD','p')
    monkeypatch.setenv('DB_NAME','db')
    monkeypatch.setenv('DB_HOST','h')
    monkeypatch.setenv('DB_PORT','5432')
    monkeypatch.setattr('src.database_manager.connect', fake_connect)

def test_setup_database_idempotent(db_manager, tmp_path):
    f = tmp_path / 'x.sql'
    f.write_text('CREATE;')
    # no exception for exists=False
    db_manager.setup_database(sql_file_path=str(f))

def test_setup_database_success(db_manager, tmp_path, monkeypatch):
    # Test successful setup_database with valid SQL and env vars
    sql_file = tmp_path / 'valid.sql'
    sql_file.write_text('CREATE TABLE test_table(id INT);')
    monkeypatch.setenv('DB_USER', 'user')
    monkeypatch.setenv('DB_PASSWORD', 'pass')
    monkeypatch.setenv('DB_NAME', 'dbname')
    monkeypatch.setenv('DB_HOST', 'localhost')
    monkeypatch.setenv('DB_PORT', '5432')

    # Patch connect to simulate successful connection and execution
    class SuccessCursor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def execute(self, sql): pass
    class SuccessConn:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def cursor(self): return SuccessCursor()
        def close(self): pass
    def fake_connect(*args, **kwargs):
        return SuccessConn()
    monkeypatch.setattr('src.database_manager.connect', fake_connect)

    # Patch ThreadedConnectionPool to simulate pool creation
    class FakePool:
        def __init__(self): pass
    monkeypatch.setattr('src.database_manager.ThreadedConnectionPool', lambda **kwargs: FakePool())

    db_manager.setup_database(sql_file_path=str(sql_file))

def test_setup_database_invalid_sql(db_manager, tmp_path, monkeypatch):
    # Test setup_database with invalid SQL raising ProgrammingError
    sql_file = tmp_path / 'bad.sql'
    sql_file.write_text('INVALID SQL;')
    monkeypatch.setenv('DB_USER', 'user')
    monkeypatch.setenv('DB_PASSWORD', 'pass')
    monkeypatch.setenv('DB_NAME', 'dbname')
    monkeypatch.setenv('DB_HOST', 'localhost')
    monkeypatch.setenv('DB_PORT', '5432')

    class FailCursor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def execute(self, sql):
            from psycopg2 import ProgrammingError
            raise ProgrammingError("already exists")
    class FailConn:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def cursor(self): return FailCursor()
        def close(self): pass
        def rollback(self): pass
    def fake_connect(*args, **kwargs):
        return FailConn()
    monkeypatch.setattr('src.database_manager.connect', fake_connect)

    # Should not raise exception, just log and continue
    db_manager.setup_database(sql_file_path=str(sql_file))

def test_setup_database_connection_failure(db_manager, tmp_path, monkeypatch):
    # Test setup_database with connection failure raising OperationalError
    from psycopg2 import OperationalError
    monkeypatch.setenv('DB_USER', 'user')
    monkeypatch.setenv('DB_PASSWORD', 'pass')
    monkeypatch.setenv('DB_NAME', 'dbname')
    monkeypatch.setenv('DB_HOST', 'localhost')
    monkeypatch.setenv('DB_PORT', '5432')

    # Create a dummy SQL file to avoid FileNotFoundError
    dummy_sql = tmp_path / 'dummy.sql'
    dummy_sql.write_text('CREATE TABLE dummy(id INT);')

    def fake_connect(*args, **kwargs):
        raise OperationalError("could not connect to server")
    monkeypatch.setattr('src.database_manager.connect', fake_connect)

    with pytest.raises(OperationalError):
        db_manager.setup_database(sql_file_path=str(dummy_sql))

#-----------------------------------------------------------------------------#
# load_sql_file Tests
#-----------------------------------------------------------------------------#
def test_load_sql_file_missing(db_manager):
    import pytest
    with pytest.raises(FileNotFoundError):
        db_manager.load_sql_file("nonexistent.sql")

def test_load_sql_file_empty(tmp_path, db_manager):
    empty_file = tmp_path / "empty.sql"
    empty_file.write_text("")
    import pytest
    with pytest.raises(ValueError):
        db_manager.load_sql_file(str(empty_file))

#-----------------------------------------------------------------------------#
# setup_database Tests - additional error cases
#-----------------------------------------------------------------------------#
def test_setup_database_missing_env_vars(db_manager, tmp_path, monkeypatch):
    sql_file = tmp_path / "valid.sql"
    sql_file.write_text("CREATE TABLE test(id INT);")
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    monkeypatch.delenv("DB_NAME", raising=False)
    monkeypatch.delenv("DB_HOST", raising=False)
    monkeypatch.delenv("DB_PORT", raising=False)
    import pytest
    with pytest.raises(KeyError):
        db_manager.setup_database(sql_file_path=str(sql_file))

def test_setup_database_programming_error(db_manager, tmp_path, monkeypatch):
    sql_file = tmp_path / "valid.sql"
    sql_file.write_text("CREATE TABLE test(id INT);")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "dbname")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")

    class FailConn:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def cursor(self):
            class FailCursor:
                def execute(self, sql):
                    from psycopg2 import ProgrammingError
                    raise ProgrammingError("syntax error")
                def __enter__(self): return self
                def __exit__(self, exc_type, exc_val, exc_tb): return False
            return FailCursor()
        def close(self): pass
        def rollback(self): pass

    def fake_connect(*args, **kwargs):
        return FailConn()
    monkeypatch.setattr("src.database_manager.connect", fake_connect)

    import pytest
    with pytest.raises(Exception):
        db_manager.setup_database(sql_file_path=str(sql_file))

#-----------------------------------------------------------------------------#
# close_pool Tests - error case
#-----------------------------------------------------------------------------#
def test_close_pool_error(db_manager, monkeypatch):
    class FakePool:
        def closeall(self):
            raise Exception("Close pool error")
    db_manager.pool = FakePool()
    import pytest
    with pytest.raises(Exception):
        db_manager.close_pool()

def test_close_pool_success(db_manager):
    # Provide a fake pool with closeall method that does not raise
    class FakePool:
        def closeall(self):
            pass
    db_manager.pool = FakePool()
    import logging
    import pytest
    # Capture logs
    from io import StringIO
    import sys

    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    logger = logging.getLogger("src.database_manager")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        db_manager.close_pool()
        handler.flush()
        log_contents = log_stream.getvalue()
        assert "Connection pool closed." in log_contents
    finally:
        logger.removeHandler(handler)

#-----------------------------------------------------------------------------#
# save_workflow Tests - additional error cases
#-----------------------------------------------------------------------------#
def test_save_workflow_invalid_json(db_manager):
    import pytest
    with pytest.raises(ValueError):
        db_manager.save_workflow("desc", "{invalid_json}")

def test_get_db_pool_returns_pool(db_manager):
    pool = db_manager.get_db_pool()
    assert pool is not None

def test_save_workflow_db_insert_failure(db_manager, monkeypatch):
    class E(Exception):
        pgcode = "99999"
    def fake_exec(*args, **kwargs):
        raise E()
    class FakeCursor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def execute(self, sql, params=None):
            return fake_exec()
    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def cursor(self): return FakeCursor()
        def close(self): pass
    def fake_get_connection():
        return FakeConn()
    db_manager.pool = None
    monkeypatch.setattr(db_manager, "get_connection", fake_get_connection)
    import pytest
    with pytest.raises(Exception):
        db_manager.save_workflow("desc", '{"a":1}')

def test_save_workflow_db_insert_failure_explicit_logging(monkeypatch):
    from src.database_manager import DatabaseManager, WorkflowError
    # Fix dummy embedding to accept *args and **kwargs to avoid call errors
    def dummy_embedding(*args, **kwargs):
        return [0.1] * 8
    dbm = DatabaseManager(embedding_service=None)
    # Provide a fake pool with putconn method to avoid AttributeError
    class FakePool:
        def putconn(self, conn):
            pass
    dbm.pool = FakePool()

    from psycopg2 import Error as PsycopgError
    class E(PsycopgError):
        pgcode = "99999"
        def __str__(self):
            return "Simulated DB insert failure"

    class FakeCursor:
        def __init__(self):
            self.executed_insert = False
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def execute(self, sql, params=None):
            if sql.strip().upper().startswith("INSERT INTO"):
                self.executed_insert = True
                raise E()
            # For other SQL, do nothing
            return None

    class FakeConn:
        def __init__(self):
            self.cursor_obj = FakeCursor()
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def cursor(self): return self.cursor_obj
        def close(self): pass

    def fake_get_connection():
        return FakeConn()

    monkeypatch.setattr(dbm, "get_connection", fake_get_connection)
    monkeypatch.setattr(dbm, "embedding_service", type("DummyEmb", (), {
        "get_embeddings": dummy_embedding,
        "normalize_embedding": dummy_embedding
    })())

    import pytest
    import logging

    with pytest.raises(WorkflowError) as excinfo:
        dbm.save_workflow("desc", '{"a":1}')
    assert "Database insert failed" in str(excinfo.value)

#-----------------------------------------------------------------------------#
# retrieve_similar_workflow Tests
#-----------------------------------------------------------------------------#
def test_retrieve_happy(db_manager):
    res = db_manager.retrieve_similar_workflow('q', top_k=1, similarity_threshold=0.5)
    assert len(res)==1

@pytest.mark.parametrize('q', ['','   '])
def test_retrieve_empty_query(q, db_manager):
    with pytest.raises(ValueError):
        db_manager.retrieve_similar_workflow(q)

# simulate missing table
def test_retrieve_table_missing(db_manager, monkeypatch):
    # cursor.exists=False
    cursor = StubCursor(exists=False)
    conn = StubConn(cursor)
    db_manager.pool = StubPool(conn)
    assert db_manager.retrieve_similar_workflow('test')==[]

# beyond boundary top_k
def test_retrieve_high_topk(db_manager):
    # pool.maxconn=5, request 100
    res = db_manager.retrieve_similar_workflow('x', top_k=100)
    # returns at most pool.maxconn items
    assert len(res)<=5

# embedding timeout
def test_retrieve_embedding_timeout(db_manager, monkeypatch):
    monkeypatch.setattr(db_manager.embedding_service, 'get_embeddings', lambda x: (_ for _ in ()).throw(RuntimeError('timeout')))
    with pytest.raises(WorkflowError):
        db_manager.retrieve_similar_workflow('x')

def test_retrieve_json_decode_error(db_manager, monkeypatch):
    # Simulate JSONDecodeError when parsing workflow JSON
    bad_json = '{"main": "invalid json}'
    cursor = StubCursor(rows=[(1, 'desc', bad_json, 0.9)])
    conn = StubConn(cursor)
    db_manager.pool = StubPool(conn)
    monkeypatch.setattr(db_manager.embedding_service, 'get_embeddings', lambda x: [0.1]*8)
    results = db_manager.retrieve_similar_workflow('query')
    # The bad JSON row should be skipped, so results should be empty
    assert results == []

def test_retrieve_psycopg_error(db_manager, monkeypatch):
    # Simulate PsycopgError during DB query raising WorkflowError
    class FakeCursor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def execute(self, sql, params=None):
            from psycopg2 import Error
            raise Error("DB error")
    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def cursor(self): return FakeCursor()
        def close(self): pass
    def fake_get_connection():
        return FakeConn()
    db_manager.pool = StubPool(FakeConn())
    monkeypatch.setattr(db_manager, "get_connection", fake_get_connection)
    monkeypatch.setattr(db_manager.embedding_service, 'get_embeddings', lambda x: [0.1]*8)
    import pytest
    with pytest.raises(WorkflowError):
        db_manager.retrieve_similar_workflow('query')

#-----------------------------------------------------------------------------#
# initialize_node_store Tests
#-----------------------------------------------------------------------------#
def test_node_store_first(db_manager, monkeypatch):
    called={}
    def fake_store(n): called['ok']=True
    monkeypatch.setattr(db_manager, 'store_nodes_with_embeddings', fake_store)
    db_manager.initialize_node_store()
    assert 'ok' in called

# idempotent
def test_node_store_idempotent(db_manager):
    # stub count>0
    pool = StubPool(StubConn(StubCursor(count=2)))
    db_manager.pool = pool
    # store not called
    db_manager.initialize_node_store()

def test_initialize_node_store_exception_coverage(db_manager, monkeypatch):
    # Monkeypatch the connection cursor execute to raise Exception to trigger except block
    class ErrorCursor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def execute(self, sql):
            raise Exception("Simulated DB error")
    class ErrorConn:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def cursor(self):
            return ErrorCursor()
        def close(self): pass
    def fake_get_connection():
        return ErrorConn()
    monkeypatch.setattr(db_manager, "get_connection", fake_get_connection)
    import pytest
    from src.database_manager import WorkflowError
    with pytest.raises(WorkflowError) as excinfo:
        db_manager.initialize_node_store()
    assert "Node store initialization failed" in str(excinfo.value)

#-----------------------------------------------------------------------------#
# save_workflow Tests
#-----------------------------------------------------------------------------#
def test_save_workflow_happy(db_manager):
    # no exception
    db_manager.save_workflow('d', json.dumps({'a':1}))

@pytest.mark.parametrize('desc', ['','   '])
def test_save_blank_desc(desc, db_manager):
    with pytest.raises(ValueError):
        db_manager.save_workflow(desc, json.dumps({'a':1}))

@pytest.mark.parametrize('j', ['{bad}', ''])
def test_save_invalid_json(j, db_manager):
    with pytest.raises(ValueError):
        db_manager.save_workflow('d', j)

#-----------------------------------------------------------------------------#
# store_nodes_with_embeddings Tests
#-----------------------------------------------------------------------------#
def test_store_nodes_with_embeddings_success(db_manager, monkeypatch):
    nodes = [{"id": "node1"}, {"id": "node2"}]
    called = {"commit": False}
    class FakeCursor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def execute(self, sql, params=None):
            pass
    class FakeConn:
        def __init__(self):
            self.cursor_called = False
        def cursor(self):
            return FakeCursor()
        def commit(self):
            called["commit"] = True
        def close(self):
            pass
    def fake_get_connection():
        return FakeConn()
    monkeypatch.setattr(db_manager, "get_connection", fake_get_connection)
    monkeypatch.setattr(db_manager, "close_connection", lambda conn: None)
    monkeypatch.setattr(db_manager.embedding_service, "get_embeddings", lambda x: [1.0, 2.0, 3.0])
    monkeypatch.setattr(db_manager.embedding_service, "normalize_embedding", lambda emb: [0.1, 0.2, 0.3])
    db_manager.store_nodes_with_embeddings(nodes)
    assert called["commit"] is True

def test_store_nodes_with_embeddings_failure(db_manager, monkeypatch):
    nodes = [{"id": "node1"}]
    class FakeCursor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def execute(self, sql, params=None):
            raise Exception("DB error")
    class FakeConn:
        def __init__(self):
            self.cursor_called = False
        def cursor(self):
            return FakeCursor()
        def commit(self):
            pass
        def close(self):
            pass
    def fake_get_connection():
        return FakeConn()
    monkeypatch.setattr(db_manager, "get_connection", fake_get_connection)
    monkeypatch.setattr(db_manager, "close_connection", lambda conn: None)
    monkeypatch.setattr(db_manager.embedding_service, "get_embeddings", lambda x: [1.0, 2.0, 3.0])
    monkeypatch.setattr(db_manager.embedding_service, "normalize_embedding", lambda emb: [0.1, 0.2, 0.3])
    import pytest
    from src.database_manager import WorkflowError
    with pytest.raises(WorkflowError):
        db_manager.store_nodes_with_embeddings(nodes)

# table missing
def test_save_table_missing(db_manager, monkeypatch):
    class E(PsycopgError): pgcode='42P01'
    def fake_exec(*args,**kw): raise E('no-table')
    # stub cursor
    cur=StubCursor()
    conn=StubConn(cur)
    cur.execute=fake_exec
    db_manager.pool=StubPool(conn)
    db_manager.save_workflow('d', json.dumps({'a':1}))

# embedding failure
def test_save_embedding_fail(db_manager, monkeypatch):
    monkeypatch.setattr(db_manager.embedding_service, 'get_embeddings', lambda x: (_ for _ in ()).throw(ValueError('nope')))
    with pytest.raises(WorkflowError):
        db_manager.save_workflow('d', json.dumps({'a':1}))

#-----------------------------------------------------------------------------#
# Additional tests to improve coverage for connection pool creation and error handling
#-----------------------------------------------------------------------------#

def test_setup_database_creates_pool(monkeypatch, tmp_path):
    sql_file = tmp_path / "valid.sql"
    sql_file.write_text("CREATE TABLE test(id INT);")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "dbname")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")

    class SuccessConn:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def cursor(self): 
            class SuccessCursor:
                def execute(self, sql): pass
                def __enter__(self): return self
                def __exit__(self, exc_type, exc_val, exc_tb): return False
            return SuccessCursor()
        def close(self): pass

    def fake_connect(*args, **kwargs):
        return SuccessConn()

    class FakePool:
        def __init__(self):
            self.created = True

    monkeypatch.setattr("src.database_manager.connect", fake_connect)
    monkeypatch.setattr("src.database_manager.ThreadedConnectionPool", lambda **kwargs: FakePool())

    db_manager = DatabaseManager(embedding_service=None)
    db_manager.setup_database(sql_file_path=str(sql_file))
    assert hasattr(db_manager, "pool")
    assert db_manager.pool is not None

def test_setup_database_pool_creation_error(monkeypatch, tmp_path):
    sql_file = tmp_path / "valid.sql"
    sql_file.write_text("CREATE TABLE test(id INT);")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pass")
    monkeypatch.setenv("DB_NAME", "dbname")
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")

    class SuccessConn:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def cursor(self): 
            class SuccessCursor:
                def execute(self, sql): pass
                def __enter__(self): return self
                def __exit__(self, exc_type, exc_val, exc_tb): return False
            return SuccessCursor()
        def close(self): pass

    def fake_connect(*args, **kwargs):
        return SuccessConn()

    def fake_pool(*args, **kwargs):
        raise Exception("Pool creation failed")

    monkeypatch.setattr("src.database_manager.connect", fake_connect)
    monkeypatch.setattr("src.database_manager.ThreadedConnectionPool", fake_pool)

    db_manager = DatabaseManager(embedding_service=None)
    import pytest
    with pytest.raises(Exception):
        db_manager.setup_database(sql_file_path=str(sql_file))

def test_retrieve_similar_workflow_with_dict_workflow(db_manager, monkeypatch):
    # Mock database to return workflow column as a dict instead of JSON string
    class FakeCursor:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def execute(self, sql, params=None):
            pass
        def fetchone(self):
            return (True,)  # Table exists
        def fetchall(self):
            # Return a row with workflow as dict
            return [(1, "desc", {"main": {"state": {}, "nodes": [], "edges": []}}, 0.9)]
    class FakeConn:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): return False
        def cursor(self): return FakeCursor()
        def close(self): pass
    def fake_get_connection():
        return FakeConn()
    # Provide a fake pool with putconn and maxconn attributes to avoid AttributeError
    class FakePool:
        def putconn(self, conn): pass
        maxconn = 10
    db_manager.pool = FakePool()
    monkeypatch.setattr(db_manager, "get_connection", fake_get_connection)
    monkeypatch.setattr(db_manager.embedding_service, "get_embeddings", lambda x: [0.1]*8)
    results = db_manager.retrieve_similar_workflow("query")
    from src.database_manager import Workflow
    assert len(results) == 1
    assert isinstance(results[0][2], Workflow) or hasattr(results[0][2], "normalize")
