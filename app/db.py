from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker


class Base(DeclarativeBase):
    pass


SessionLocal = scoped_session(sessionmaker(future=True, expire_on_commit=False))
_engine = None


def init_engine(db_path: str):
    global _engine
    url = "sqlite:///:memory:" if db_path == ":memory:" else f"sqlite:///{db_path}"
    # check_same_thread=False is safe here: scoped_session gives one session per thread,
    # and SQLite WAL serialises writes.
    _engine = create_engine(url, future=True, connect_args={"check_same_thread": False})

    @event.listens_for(_engine, "connect")
    def _pragmas(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()

    SessionLocal.configure(bind=_engine)
    return _engine


def get_engine():
    return _engine
