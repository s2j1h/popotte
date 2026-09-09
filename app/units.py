"""Unités de cuisine, normalisation et conversions.

Règle centrale : on ne convertit qu'à l'intérieur d'une même *famille*
(masse, volume, pièce...). Deux unités de familles différentes pour un même
ingrédient ne sont jamais fusionnées silencieusement.
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass

MASSE = "masse"
VOLUME = "volume"
PIECE = "piece"
LIBRE = "libre"  # "quantité suffisante" : sel, poivre, huile pour la poêle...


@dataclass(frozen=True)
class UnitDef:
    """Définition d'une unité.

    factor : conversion vers l'unité de base de la famille.
    countable : la quantité d'achat est un entier (on arrondit au supérieur).
    """

    canonical: str
    family: str
    factor: float
    countable: bool = False


def _u(canonical: str, family: str, factor: float = 1.0, countable: bool = False) -> UnitDef:
    return UnitDef(canonical, family, factor, countable)


# Unité de base de chaque famille convertible.
BASE_UNIT = {MASSE: "g", VOLUME: "ml"}

UNITS: dict[str, UnitDef] = {
    # --- masse (base : g) ---
    "g": _u("g", MASSE, 1.0),
    "kg": _u("kg", MASSE, 1000.0),
    # --- volume (base : ml) ---
    "ml": _u("ml", VOLUME, 1.0),
    "cl": _u("cl", VOLUME, 10.0),
    "dl": _u("dl", VOLUME, 100.0),
    "l": _u("l", VOLUME, 1000.0),
    # --- pièces et unités de cuisine (chacune sa propre famille) ---
    "pièce": _u("pièce", PIECE, 1.0, countable=True),
    "gousse": _u("gousse", "gousse", 1.0, countable=True),
    "botte": _u("botte", "botte", 1.0, countable=True),
    "bouquet": _u("bouquet", "bouquet", 1.0, countable=True),
    "sachet": _u("sachet", "sachet", 1.0, countable=True),
    "boîte": _u("boîte", "boîte", 1.0, countable=True),
    "tranche": _u("tranche", "tranche", 1.0, countable=True),
    "feuille": _u("feuille", "feuille", 1.0, countable=True),
    "brin": _u("brin", "brin", 1.0, countable=True),
    "cube": _u("cube", "cube", 1.0, countable=True),
    "pot": _u("pot", "pot", 1.0, countable=True),
    "rouleau": _u("rouleau", "rouleau", 1.0, countable=True),
    "c. à soupe": _u("c. à soupe", "c. à soupe", 1.0),
    "c. à café": _u("c. à café", "c. à café", 1.0),
    "pincée": _u("pincée", "pincée", 1.0),
    "poignée": _u("poignée", "poignée", 1.0),
    "goutte": _u("goutte", "goutte", 1.0),
    "trait": _u("trait", "trait", 1.0),
    # --- quantité laissée libre ---
    "": _u("", LIBRE, 1.0),
}

# Unités proposées dans les formulaires, dans l'ordre d'usage.
UNIT_CHOICES = [
    "g", "kg", "ml", "cl", "l", "pièce", "c. à soupe", "c. à café",
    "pincée", "gousse", "tranche", "botte", "bouquet", "sachet",
    "boîte", "feuille", "brin", "cube", "pot", "rouleau",
    "poignée", "goutte", "trait", "",
]

# Orthographes acceptées à la saisie -> unité canonique.
_ALIASES = {
    "gr": "g", "gramme": "g", "grammes": "g", "gramm": "g",
    "kilo": "kg", "kilos": "kg", "kilogramme": "kg", "kilogrammes": "kg",
    "millilitre": "ml", "millilitres": "ml",
    "centilitre": "cl", "centilitres": "cl",
    "decilitre": "dl", "décilitre": "dl", "decilitres": "dl", "décilitres": "dl",
    "litre": "l", "litres": "l", "lt": "l",
    "piece": "pièce", "pieces": "pièce", "pièces": "pièce", "p": "pièce",
    "unite": "pièce", "unité": "pièce", "unites": "pièce", "unités": "pièce", "u": "pièce",
    "cas": "c. à soupe", "càs": "c. à soupe", "cs": "c. à soupe",
    "c a soupe": "c. à soupe", "c. a soupe": "c. à soupe",
    "cuillere a soupe": "c. à soupe", "cuillère à soupe": "c. à soupe",
    "cuilleres a soupe": "c. à soupe", "cuillères à soupe": "c. à soupe",
    "cac": "c. à café", "càc": "c. à café", "cc": "c. à café",
    "c a cafe": "c. à café", "c. a cafe": "c. à café",
    "cuillere a cafe": "c. à café", "cuillère à café": "c. à café",
    "cuilleres a cafe": "c. à café", "cuillères à café": "c. à café",
    "pincee": "pincée", "pincees": "pincée", "pincées": "pincée",
    "gousses": "gousse", "bottes": "botte", "bouquets": "bouquet",
    "sachets": "sachet", "boite": "boîte", "boites": "boîte", "boîtes": "boîte",
    "tranches": "tranche", "feuilles": "feuille", "brins": "brin",
    "poignee": "poignée", "poignees": "poignée", "poignées": "poignée",
    "gouttes": "goutte", "traits": "trait", "cubes": "cube", "pots": "pot",
    "rouleaux": "rouleau",
    "qs": "", "-": "", "selon gout": "", "selon goût": "", "au gout": "", "au goût": "",
}


def strip_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn")


def canonical_unit(raw: str | None) -> str:
    """Ramène une unité saisie librement à sa forme canonique.

    Une unité inconnue est conservée telle quelle (en minuscules) : elle
    formera sa propre famille et ne sera donc jamais fusionnée à tort.
    """
    if raw is None:
        return ""
    value = " ".join(raw.strip().lower().split())
    if value in UNITS:
        return value
    if value in _ALIASES:
        return _ALIASES[value]
    flat = strip_accents(value)
    if flat in _ALIASES:
        return _ALIASES[flat]
    if flat in UNITS:
        return flat
    return value


def unit_def(unit: str) -> UnitDef:
    unit = canonical_unit(unit)
    known = UNITS.get(unit)
    if known:
        return known
    # Unité libre saisie par l'utilisateur : famille dédiée, non convertible.
    return _u(unit, f"autre:{unit}", 1.0)


def family_of(unit: str) -> str:
    return unit_def(unit).family


def to_base(quantity: float, unit: str) -> float:
    """Convertit vers l'unité de base de la famille (g, ml, ou l'unité elle-même)."""
    return quantity * unit_def(unit).factor


def best_display_unit(quantity_base: float, family: str, fallback_unit: str) -> tuple[float, str]:
    """Choisit l'unité la plus lisible pour une quantité exprimée en unité de base."""
    if family == MASSE:
        if quantity_base >= 1000:
            return quantity_base / 1000.0, "kg"
        return quantity_base, "g"
    if family == VOLUME:
        if quantity_base >= 1000:
            return quantity_base / 1000.0, "l"
        return quantity_base, "ml"
    return quantity_base, fallback_unit


def round_purchase(quantity: float, unit: str) -> float:
    """Arrondit à une quantité d'achat réaliste.

    - unités dénombrables (œufs, gousses...) : entier supérieur, jamais 3,5 œufs
    - g / ml : entier supérieur (on n'achète pas 212,5 g de farine)
    - kg / l : 2 décimales
    - reste (cuillères, pincées) : au demi supérieur
    """
    definition = unit_def(unit)
    if definition.countable:
        return float(math.ceil(round(quantity, 6)))
    if definition.canonical in ("g", "ml"):
        return float(math.ceil(round(quantity, 6)))
    if definition.canonical in ("kg", "l"):
        return math.ceil(round(quantity, 6) * 100) / 100
    return math.ceil(round(quantity, 6) * 2) / 2


def format_quantity(quantity: float | None) -> str:
    """Affichage à la française : 1,5 — 4 — 0,25."""
    if quantity is None:
        return ""
    rounded = round(quantity, 2)
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    return f"{rounded:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def parse_quantity(raw: str | None) -> float | None:
    """Accepte 1.5 comme 1,5. Vide -> None (quantité libre)."""
    if raw is None:
        return None
    value = raw.strip().replace(",", ".")
    if not value:
        return None
    try:
        quantity = float(value)
    except ValueError:
        return None
    return quantity if quantity > 0 else None


def format_amount(quantity: float | None, unit: str) -> str:
    """'200 g', '4 pièce' -> '4', 'au goût' quand rien n'est précisé."""
    unit = canonical_unit(unit)
    if quantity is None:
        return "au goût"
    text = format_quantity(quantity)
    if not unit:
        return text
    if unit == "pièce":
        return text
    return f"{text} {unit}"
