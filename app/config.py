"""Configuration de l'application. Tout est pilotable par variables d'environnement."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

# Répertoire de données : contient popotte.db et les photos uploadées.
# En Docker, c'est le volume monté (/data).
DATA_DIR = Path(os.environ.get("POPOTTE_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))


def _secret_key(data_dir: Path) -> str:
    """Clé de session persistée sur disque : le panier survit à un redémarrage.

    Pas d'authentification dans l'app, la session ne sert qu'à mémoriser la
    sélection de recettes en cours.
    """
    env = os.environ.get("POPOTTE_SECRET_KEY")
    if env:
        return env
    key_file = data_dir / "secret_key"
    if not key_file.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        key_file.write_text(secrets.token_hex(32), encoding="utf-8")
    return key_file.read_text(encoding="utf-8").strip()


class Config:
    DATA_DIR = DATA_DIR
    UPLOAD_DIR = DATA_DIR / "uploads"
    DATABASE_URL = os.environ.get("POPOTTE_DATABASE_URL") or f"sqlite:///{DATA_DIR / 'popotte.db'}"
    SECRET_KEY = _secret_key(DATA_DIR)
    SEED_DEMO = os.environ.get("POPOTTE_SEED_DEMO", "1") == "1"

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 Mo : photos de téléphone
    IMAGE_MAX_SIZE = 1280  # côté le plus long, en px
    SESSION_COOKIE_SAMESITE = "Lax"
    TEMPLATES_AUTO_RELOAD = os.environ.get("POPOTTE_DEBUG") == "1"
