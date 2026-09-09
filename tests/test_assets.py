"""Aucune dépendance réseau externe : tout est servi par l'application."""

import re
from pathlib import Path

import pytest

TEMPLATES = Path(__file__).resolve().parent.parent / "app" / "templates"
VENDOR = Path(__file__).resolve().parent.parent / "app" / "static" / "vendor"


def test_aucune_url_externe_dans_les_templates():
    externes = []
    for template in TEMPLATES.rglob("*.html"):
        for match in re.findall(r'(?:src|href)="(https?://[^"]+)"', template.read_text("utf-8")):
            externes.append(f"{template.name}: {match}")
    assert externes == []


@pytest.mark.parametrize(
    "nom",
    ["daisyui.css", "tailwindcss-browser.js", "htmx.min.js", "fonts.css"],
)
def test_asset_present(nom):
    assert (VENDOR / nom).is_file()


def test_les_polices_referencees_existent():
    css = (VENDOR / "fonts.css").read_text("utf-8")
    fichiers = re.findall(r"url\((fonts/[^)]+)\)", css)
    assert fichiers
    for fichier in fichiers:
        assert (VENDOR / fichier).is_file(), fichier


def test_les_assets_sont_servis(client):
    for chemin in [
        "/static/vendor/daisyui.css",
        "/static/vendor/tailwindcss-browser.js",
        "/static/vendor/htmx.min.js",
        "/static/vendor/fonts.css",
        "/static/vendor/fonts/fraunces-latin.woff2",
    ]:
        assert client.get(chemin).status_code == 200, chemin
