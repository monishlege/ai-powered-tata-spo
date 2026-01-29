import os
from sqlmodel import SQLModel, create_engine, Session, select
from app.db_models import AlertDB, TripConfigDB, TelemetryDB, DriverDB

sqlite_file_name = "tata_spo.db"

connect_args = {"check_same_thread": False}

def _db_path() -> str:
    vercel = os.environ.get("VERCEL") == "1"
    if vercel:
        return os.path.join("/tmp", sqlite_file_name)
    return sqlite_file_name

def _plain_sqlite_url(path: str) -> str:
    return f"sqlite:///{path}"
    
def _make_sqlcipher_engine(key: str, path: str):
    try:
        import sqlcipher3
    except ImportError as e:
        raise e

    def _creator():
        conn = sqlcipher3.connect(path, check_same_thread=False)
        cur = conn.cursor()
        cur.execute(f"PRAGMA key='{key}'")
        cur.execute("PRAGMA cipher = 'aes-256-gcm'")
        cur.execute("PRAGMA kdf_iter = 256000")
        cur.close()
        return conn

    return create_engine("sqlite://", creator=_creator)

def _is_plain_sqlite(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            header = f.read(16)
            return header.startswith(b"SQLite format 3")
    except FileNotFoundError:
        return False

def _migrate_plain_to_encrypted(key: str) -> None:
    temp_encrypted = sqlite_file_name + ".enc"
    if os.path.exists(temp_encrypted):
        os.remove(temp_encrypted)
    plain_engine = create_engine(_plain_sqlite_url(_db_path()), connect_args=connect_args)
    encrypted_engine = _make_sqlcipher_engine(key, temp_encrypted)

    SQLModel.metadata.create_all(encrypted_engine)

    with Session(plain_engine) as ps, Session(encrypted_engine) as es:
        for model in (TripConfigDB, TelemetryDB, AlertDB, DriverDB):
            rows = ps.exec(select(model)).all()
            for row in rows:
                es.add(model(**row.dict()))
        es.commit()

    # Ensure file handles are released before renaming
    plain_engine.dispose()
    encrypted_engine.dispose()

    backup = sqlite_file_name + ".bak"
    if os.path.exists(backup):
        os.remove(backup)
    src = _db_path()
    if os.path.exists(src):
        os.replace(src, backup)
    os.replace(temp_encrypted, src)

def _build_engine():
    key = os.environ.get("DB_ENCRYPTION_KEY")
    path = _db_path()
    if key:
        # Avoid migration on Vercel ephemeral FS; just use encrypted engine if available
        if not (os.environ.get("VERCEL") == "1") and _is_plain_sqlite(path):
            _migrate_plain_to_encrypted(key)
        try:
            return _make_sqlcipher_engine(key, path)
        except ImportError:
            # Fallback when sqlcipher3 is unavailable
            return create_engine(_plain_sqlite_url(path), connect_args=connect_args)
    else:
        return create_engine(_plain_sqlite_url(path), connect_args=connect_args)

engine = _build_engine()

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
