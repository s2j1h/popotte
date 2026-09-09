#!/usr/bin/env bash
# Re-télécharge les dépendances front auto-hébergées (cf. app/static/vendor/README.md).
set -euo pipefail

DAISYUI_VERSION="5.0.43"
TAILWIND_VERSION="4.1.11"
HTMX_VERSION="2.0.4"
# Poids réellement utilisés par la charte : Fraunces 500-700, Work Sans 400-600.
FONTS_QUERY="family=Fraunces:opsz,wght@9..144,500..700&family=Work+Sans:wght@400..600&display=swap"

VENDOR_DIR="$(cd "$(dirname "$0")/.." && pwd)/app/static/vendor"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

mkdir -p "$VENDOR_DIR/fonts"

echo "daisyUI $DAISYUI_VERSION"
curl -fsSL "https://cdn.jsdelivr.net/npm/daisyui@${DAISYUI_VERSION}/daisyui.css" -o "$VENDOR_DIR/daisyui.css"

echo "Tailwind (browser) $TAILWIND_VERSION"
curl -fsSL "https://cdn.jsdelivr.net/npm/@tailwindcss/browser@${TAILWIND_VERSION}/dist/index.global.js" \
  -o "$VENDOR_DIR/tailwindcss-browser.js"

echo "HTMX $HTMX_VERSION"
curl -fsSL "https://cdn.jsdelivr.net/npm/htmx.org@${HTMX_VERSION}/dist/htmx.min.js" -o "$VENDOR_DIR/htmx.min.js"

echo "Polices (Fraunces, Work Sans)"
curl -fsSL -A "$UA" "https://fonts.googleapis.com/css2?${FONTS_QUERY}" -o "$VENDOR_DIR/.fonts-remote.css"

python3 - "$VENDOR_DIR" <<'PY'
import pathlib
import re
import sys
import urllib.request

vendor = pathlib.Path(sys.argv[1])
source = (vendor / ".fonts-remote.css").read_text(encoding="utf-8")
user_agent = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

blocks = re.findall(r"/\* (?P<subset>[a-z-]+) \*/\n(?P<face>@font-face \{.*?\n\})", source, re.S)
faces = []
for subset, face in blocks:
    if subset not in ("latin", "latin-ext"):  # inutile pour un usage français
        continue
    family = re.search(r"font-family: '([^']+)'", face).group(1)
    url = re.search(r"url\((https://[^)]+)\)", face).group(1)
    name = f"{family.lower().replace(' ', '-')}-{subset}.woff2"
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    (vendor / "fonts" / name).write_bytes(urllib.request.urlopen(request).read())
    faces.append(f"/* {subset} */\n" + face.replace(url, f"fonts/{name}"))
    print(f"  {name}")

header = (
    "/* Polices auto-hébergées (aucun appel réseau externe).\n"
    "   Fraunces et Work Sans — SIL Open Font License 1.1.\n"
    "   Fichiers récupérés depuis Google Fonts, voir vendor/README.md pour la mise à jour. */\n\n"
)
(vendor / "fonts.css").write_text(header + "\n\n".join(faces) + "\n", encoding="utf-8")
PY

rm -f "$VENDOR_DIR/.fonts-remote.css"
echo "Terminé."
