"""Algorithme d'agrégation de la liste de courses (logique métier centrale)."""

import pytest
from sqlalchemy import select

from app.db import db
from app.models import Ingredient, Recipe, RecipeIngredient
from app.seed import get_or_create_ingredient
from app.shopping import aggregate


def make_recipe(title, servings, items):
    recipe = Recipe(title=title, servings=servings, instructions="")
    db.add(recipe)
    db.flush()
    for position, (name, quantity, unit) in enumerate(items):
        ingredient = get_or_create_ingredient(name)
        recipe.items.append(
            RecipeIngredient(
                ingredient_id=ingredient.id, quantity=quantity, unit=unit, position=position
            )
        )
    db.flush()
    return recipe


def lines_by_name(lines):
    return {(line.ingredient.name, line.unit): line for line in lines}


def test_somme_simple_meme_unite(app):
    a = make_recipe("A", 4, [("œuf", 1, "pièce")])
    b = make_recipe("B", 4, [("œuf", 3, "pièce")])
    lines = aggregate([(a, 4), (b, 4)])
    assert len(lines) == 1
    assert lines[0].quantity == 4
    assert lines[0].unit == "pièce"


def test_exemple_du_document_de_conception(app):
    """Recette A (x1) : 1 œuf, 200 g farine — Recette B (x2) : 3 œufs, 50 g beurre."""
    a = make_recipe("A", 4, [("œuf", 1, "pièce"), ("farine", 200, "g")])
    b = make_recipe("B", 4, [("œuf", 3, "pièce"), ("beurre", 50, "g")])
    result = lines_by_name(aggregate([(a, 4), (b, 8)]))
    assert result[("œuf", "pièce")].quantity == 7  # 1 + 3*2
    assert result[("farine", "g")].quantity == 200
    assert result[("beurre", "g")].quantity == 100


def test_conversion_dans_une_famille_compatible(app):
    a = make_recipe("A", 4, [("farine", 800, "g")])
    b = make_recipe("B", 4, [("farine", 1, "kg")])
    lines = aggregate([(a, 4), (b, 4)])
    assert len(lines) == 1
    assert lines[0].unit == "kg"  # 1800 g -> affiché en kg
    assert lines[0].quantity == pytest.approx(1.8)
    assert lines[0].needs_check is False


def test_volumes_cl_ml_l(app):
    a = make_recipe("A", 4, [("lait", 30, "cl")])
    b = make_recipe("B", 4, [("lait", 200, "ml")])
    lines = aggregate([(a, 4), (b, 4)])
    assert (lines[0].quantity, lines[0].unit) == (500, "ml")


def test_unites_incompatibles_non_fusionnees(app):
    """« 1 pincée » + « 5 g » : deux lignes distinctes, signalées à vérifier."""
    a = make_recipe("A", 4, [("sel", 1, "pincée")])
    b = make_recipe("B", 4, [("sel", 5, "g")])
    lines = aggregate([(a, 4), (b, 4)])
    assert len(lines) == 2
    assert all(line.needs_check for line in lines)
    assert {line.unit for line in lines} == {"pincée", "g"}


def test_ratio_de_portions(app):
    recipe = make_recipe("A", 4, [("farine", 200, "g")])
    lines = aggregate([(recipe, 6)])
    assert lines[0].quantity == 300


def test_arrondi_a_lunite_dachat(app):
    """3 œufs pour 4 personnes, portés à 6 personnes -> 4,5 -> 5 œufs."""
    recipe = make_recipe("A", 4, [("œuf", 3, "pièce")])
    lines = aggregate([(recipe, 6)])
    assert lines[0].quantity == 5


def test_quantite_libre_absorbee_par_une_quantite_chiffree(app):
    a = make_recipe("A", 4, [("poivre", None, "")])
    b = make_recipe("B", 4, [("poivre", 2, "g")])
    lines = aggregate([(a, 4), (b, 4)])
    assert len(lines) == 1
    assert lines[0].quantity == 2
    assert lines[0].needs_check is False


def test_quantite_libre_seule(app):
    recipe = make_recipe("A", 4, [("sel", None, "")])
    lines = aggregate([(recipe, 4)])
    assert lines[0].quantity is None


def test_tri_par_rayon(app):
    farine = get_or_create_ingredient("farine")
    farine.category = "epicerie"
    tomate = get_or_create_ingredient("tomate")
    tomate.category = "fruits-legumes"
    db.flush()
    recipe = make_recipe("A", 4, [("farine", 100, "g"), ("tomate", 2, "pièce")])
    lines = aggregate([(recipe, 4)])
    assert [line.ingredient.name for line in lines] == ["tomate", "farine"]


def test_referentiel_dedoublonne_les_orthographes(app):
    first = get_or_create_ingredient("Œufs")
    second = get_or_create_ingredient("oeuf")
    assert first.id == second.id
    assert db.scalar(select(Ingredient).where(Ingredient.slug == "oeuf")) is not None
