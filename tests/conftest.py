import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.db import db  # noqa: E402


@pytest.fixture()
def app():
    tmp = tempfile.TemporaryDirectory()
    data_dir = Path(tmp.name)
    application = create_app(
        {
            "DATA_DIR": data_dir,
            "UPLOAD_DIR": data_dir / "uploads",
            "DATABASE_URL": f"sqlite:///{data_dir / 'test.db'}",
            "SECRET_KEY": "test",
            "SEED_DEMO": True,
            "TESTING": True,
        }
    )
    with application.app_context():
        yield application
    db.remove()
    tmp.cleanup()


@pytest.fixture()
def client(app):
    return app.test_client()
