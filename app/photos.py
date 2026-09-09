"""Upload et redimensionnement des photos de recettes.

Les fichiers sont stockés dans le volume de données, à côté du fichier SQLite :
sauvegarder l'application = copier ce répertoire.
"""

from __future__ import annotations

import secrets
from pathlib import Path

from PIL import Image, ImageOps

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif", ".bmp"}


def save_photo(file_storage, upload_dir: Path, max_size: int = 1280) -> str | None:
    """Enregistre une photo redimensionnée en JPEG et retourne son nom de fichier.

    Retourne None si aucun fichier n'a été envoyé ou si le format est refusé.
    """
    if file_storage is None or not file_storage.filename:
        return None

    extension = Path(file_storage.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Format d'image non supporté ({extension or 'inconnu'}).")

    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{secrets.token_hex(8)}.jpg"

    try:
        image = Image.open(file_storage.stream)
        image = ImageOps.exif_transpose(image)  # respecte l'orientation du téléphone
        image = image.convert("RGB")
        image.thumbnail((max_size, max_size))
        image.save(upload_dir / filename, "JPEG", quality=82, optimize=True)
    except OSError as error:  # fichier corrompu ou format non lisible par Pillow
        raise ValueError("Image illisible.") from error

    return filename


def delete_photo(filename: str | None, upload_dir: Path) -> None:
    if not filename:
        return
    target = upload_dir / Path(filename).name
    if target.exists():
        target.unlink()
