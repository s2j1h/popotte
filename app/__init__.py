"""Fabrique de l'application Flask."""

from __future__ import annotations

import fcntl
from contextlib import contextmanager
from pathlib import Path

from flask import Flask, redirect, render_template, url_for

from .config import Config
from .db import db, init_db


@contextmanager
def _init_lock(data_dir: Path):
    lock_file = data_dir / ".init.lock"
    with open(lock_file, "w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    data_dir = Path(app.config["DATA_DIR"])
    data_dir.mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)

    # Verrou inter-processus : avec plusieurs workers gunicorn, un seul doit
    # créer le schéma et insérer les données initiales.
    with _init_lock(data_dir):
        init_db(app.config["DATABASE_URL"])

        from .seed import seed_if_empty

        seed_if_empty(with_demo=app.config["SEED_DEMO"])

    from .views.ingredients import bp as ingredients_bp
    from .views.recipes import bp as recipes_bp
    from .views.shopping import bp as shopping_bp

    app.register_blueprint(recipes_bp)
    app.register_blueprint(shopping_bp)
    app.register_blueprint(ingredients_bp)

    from . import filters

    filters.register(app)

    @app.route("/")
    def index():
        return redirect(url_for("recipes.list_recipes"))

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="Cette page n'existe pas."), 404

    @app.errorhandler(413)
    def too_large(_error):
        return (
            render_template(
                "error.html", code=413, message="Photo trop volumineuse (16 Mo maximum)."
            ),
            413,
        )

    @app.teardown_appcontext
    def remove_session(exception=None):  # pragma: no cover - plomberie
        if exception:
            db.rollback()
        db.remove()

    return app
