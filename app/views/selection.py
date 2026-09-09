"""Panier de recettes (sélection en cours).

Stocké dans la session Flask : pas de compte utilisateur, une seule personne
à la fois, et la sélection survit à un redémarrage grâce à la clé persistée.
"""

from __future__ import annotations

from flask import session
from sqlalchemy import select

from ..db import db
from ..models import Recipe

KEY = "selection"


def current_selection() -> dict[int, int]:
    """{recipe_id: portions voulues}, dans l'ordre d'ajout."""
    raw = session.get(KEY) or {}
    return {int(recipe_id): int(servings) for recipe_id, servings in raw.items()}


def _store(selection: dict[int, int]) -> None:
    session[KEY] = {str(recipe_id): int(servings) for recipe_id, servings in selection.items()}
    session.modified = True


def add(recipe: Recipe) -> None:
    selection = current_selection()
    selection.setdefault(recipe.id, recipe.servings or 4)
    _store(selection)


def remove(recipe_id: int) -> None:
    selection = current_selection()
    selection.pop(recipe_id, None)
    _store(selection)


def toggle(recipe: Recipe) -> bool:
    """Retourne True si la recette est désormais dans le panier."""
    selection = current_selection()
    if recipe.id in selection:
        remove(recipe.id)
        return False
    add(recipe)
    return True


def set_servings(recipe_id: int, servings: int) -> None:
    selection = current_selection()
    if recipe_id in selection:
        selection[recipe_id] = max(1, min(50, servings))
        _store(selection)


def clear() -> None:
    session.pop(KEY, None)
    session.modified = True


def selected_recipes() -> list[tuple[Recipe, int]]:
    """[(recette, portions voulues)], en ignorant les recettes supprimées."""
    selection = current_selection()
    if not selection:
        return []
    recipes = db.scalars(select(Recipe).where(Recipe.id.in_(selection.keys()))).all()
    by_id = {recipe.id: recipe for recipe in recipes}
    pairs = [(by_id[rid], servings) for rid, servings in selection.items() if rid in by_id]
    if len(pairs) != len(selection):  # nettoyage des recettes disparues
        _store({recipe.id: servings for recipe, servings in pairs})
    return pairs
