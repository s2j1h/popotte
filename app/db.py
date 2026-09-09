"""Session SQLAlchemy 2.0 partagée par l'application.

Volontairement minimal : un engine, une scoped_session nettoyée à la fin de
chaque requête Flask. Pas d'extension supplémentaire à maintenir.
"""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker


class Base(DeclarativeBase):
    pass


_session_factory = sessionmaker(expire_on_commit=False)
db = scoped_session(_session_factory)

engine = None


def init_db(database_url: str):
    """Crée l'engine, active les contraintes SQLite et le schéma si absent."""
    global engine
    engine = create_engine(database_url, future=True)

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_connection, _record):  # pragma: no cover - trivial
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    _session_factory.configure(bind=engine)

    from . import models  # noqa: F401  (enregistre les tables sur Base)

    Base.metadata.create_all(engine)
    return engine
