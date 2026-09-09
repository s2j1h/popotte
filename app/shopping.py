"""Génération de la liste de courses : agrégation des ingrédients.

Logique métier centrale (cf. CLAUDE.md § "Algorithme d'agrégation") :

1. multiplier chaque ligne par (portions demandées / portions de base)
2. regrouper par ingrédient
3. normaliser l'unité à l'intérieur d'une famille compatible
4. ne jamais fusionner des unités incompatibles -> lignes séparées + alerte
5. arrondir à une quantité d'achat réaliste
6. trier par rayon
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import CATEGORY_ORDER, DEFAULT_CATEGORY, Ingredient, Recipe, ShoppingListItem
from .units import BASE_UNIT, LIBRE, best_display_unit, family_of, round_purchase, to_base, unit_def


@dataclass
class Line:
    """Une ligne de liste de courses, avant persistance."""

    ingredient: Ingredient
    quantity: float | None
    unit: str
    needs_check: bool = False
    sources: list[str] = field(default_factory=list)  # d'où vient la quantité, pour l'alerte


def aggregate(selection: list[tuple[Recipe, float]]) -> list[Line]:
    """selection = [(recette, portions voulues), ...] -> lignes triées par rayon."""
    # {ingredient_id: {famille: {"total": float, "unit": str, "sources": [...]}}}
    groups: dict[int, dict[str, dict]] = {}
    ingredients: dict[int, Ingredient] = {}

    for recipe, wanted_servings in selection:
        base = recipe.servings or 1
        ratio = (wanted_servings or base) / base
        for item in recipe.items:
            ingredient = item.ingredient
            ingredients[ingredient.id] = ingredient
            unit = item.canonical_unit
            family = family_of(unit) if item.quantity is not None else LIBRE
            bucket = groups.setdefault(ingredient.id, {}).setdefault(
                family, {"total": 0.0, "unit": unit, "sources": []}
            )
            bucket["sources"].append(recipe.title)
            if item.quantity is None:
                continue
            bucket["total"] += to_base(item.quantity * ratio, unit)

    lines: list[Line] = []
    for ingredient_id, families in groups.items():
        ingredient = ingredients[ingredient_id]
        measured = {f: data for f, data in families.items() if f != LIBRE}
        # "au goût" seul -> on garde la ligne ; sinon la quantité chiffrée suffit.
        if not measured:
            lines.append(Line(ingredient, None, "", False, sorted(set(families[LIBRE]["sources"]))))
            continue

        # Unités incompatibles pour un même ingrédient : on ne fusionne pas.
        needs_check = len(measured) > 1
        for family, data in measured.items():
            fallback = unit_def(data["unit"]).canonical
            quantity, unit = best_display_unit(data["total"], family, fallback)
            quantity = round_purchase(quantity, unit)
            lines.append(Line(ingredient, quantity, unit, needs_check, sorted(set(data["sources"]))))

    lines.sort(key=_sort_key)
    return lines


def _sort_key(line: Line):
    category = line.ingredient.category or DEFAULT_CATEGORY
    return (
        0 if line.needs_check else 1,  # les lignes à vérifier remontent en tête de leur rayon
        CATEGORY_ORDER.get(category, CATEGORY_ORDER[DEFAULT_CATEGORY]),
        line.ingredient.name.lower(),
        line.unit,
    )


def build_items(shopping_list_id: int, lines: list[Line]) -> list[ShoppingListItem]:
    """Transforme les lignes calculées en articles persistables."""
    return [
        ShoppingListItem(
            shopping_list_id=shopping_list_id,
            ingredient_id=line.ingredient.id,
            quantity_total=line.quantity,
            unit=line.unit,
            checked=False,
            needs_check=line.needs_check,
            position=index,
        )
        for index, line in enumerate(lines)
    ]


def group_by_category(items) -> list[dict]:
    """Regroupe les articles par rayon, dans l'ordre du parcours en magasin."""
    from .models import CATEGORY_COLORS, CATEGORY_LABELS

    buckets: dict[str, list] = {}
    for item in items:
        category = item.ingredient.category or DEFAULT_CATEGORY
        buckets.setdefault(category, []).append(item)

    groups = []
    for category in sorted(buckets, key=lambda c: CATEGORY_ORDER.get(c, 99)):
        groups.append(
            {
                "key": category,
                "label": CATEGORY_LABELS.get(category, "Non classé"),
                "color": CATEGORY_COLORS.get(category, "neutral"),
                "lines": buckets[category],
            }
        )
    return groups


# Rappel des unités de base, importé ici pour rester dans le même module métier.
__all__ = ["Line", "aggregate", "build_items", "group_by_category", "BASE_UNIT"]
