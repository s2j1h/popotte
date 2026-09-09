"""Recettes : liste, fiche, création/édition, mode cuisine."""

from __future__ import annotations

from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from sqlalchemy import func, or_, select

from ..db import db
from ..models import DEFAULT_CATEGORY, Ingredient, Recipe, RecipeIngredient, ingredient_slug
from ..photos import delete_photo, save_photo
from ..seed import get_or_create_ingredient
from ..units import canonical_unit, format_quantity, parse_quantity
from . import selection as sel

bp = Blueprint("recipes", __name__)


def _get_recipe(recipe_id: int) -> Recipe:
    recipe = db.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    return recipe


@bp.get("/recipes")
def list_recipes():
    query = (request.args.get("q") or "").strip()
    statement = select(Recipe).order_by(Recipe.title)
    if query:
        pattern = f"%{query.lower()}%"
        matching_ids = select(RecipeIngredient.recipe_id).join(Ingredient).where(
            func.lower(Ingredient.name).like(pattern)
        )
        statement = statement.where(
            or_(
                func.lower(Recipe.title).like(pattern),
                func.lower(Recipe.tags).like(pattern),
                Recipe.id.in_(matching_ids),
            )
        )
    recipes = db.scalars(statement).all()
    context = {"recipes": recipes, "query": query, "selection": sel.current_selection()}
    if request.headers.get("HX-Request") and request.args.get("fragment"):
        return render_template("recipes/_grid.html", **context)
    return render_template("recipes/list.html", **context)


@bp.get("/recipes/<int:recipe_id>")
def detail(recipe_id: int):
    recipe = _get_recipe(recipe_id)
    servings = request.args.get("servings", type=int) or recipe.servings
    servings = max(1, min(50, servings))
    return render_template(
        "recipes/detail.html",
        recipe=recipe,
        servings=servings,
        ratio=servings / (recipe.servings or 1),
        in_selection=recipe.id in sel.current_selection(),
    )


@bp.get("/recipes/<int:recipe_id>/ingredients")
def ingredients_fragment(recipe_id: int):
    """Fragment HTMX : liste d'ingrédients recalculée quand on change les portions."""
    recipe = _get_recipe(recipe_id)
    servings = max(1, min(50, request.args.get("servings", type=int) or recipe.servings))
    return render_template(
        "recipes/_ingredients.html",
        recipe=recipe,
        servings=servings,
        ratio=servings / (recipe.servings or 1),
    )


@bp.get("/recipes/<int:recipe_id>/cuisine")
def cook(recipe_id: int):
    """Mode cuisine : plein écran, une étape à la fois."""
    recipe = _get_recipe(recipe_id)
    steps = recipe.steps or ["Aucune instruction saisie pour cette recette."]
    step = max(1, min(len(steps), request.args.get("step", type=int) or 1))
    servings = max(1, min(50, request.args.get("servings", type=int) or recipe.servings))
    context = {
        "recipe": recipe,
        "steps": steps,
        "step": step,
        "servings": servings,
        "ratio": servings / (recipe.servings or 1),
    }
    if request.headers.get("HX-Request"):
        return render_template("recipes/_cook_step.html", **context)
    return render_template("recipes/cook.html", **context)


# --------------------------------------------------------------------------
# Création / édition
# --------------------------------------------------------------------------


@bp.route("/recipes/new", methods=["GET", "POST"])
def new():
    if request.method == "POST":
        recipe = Recipe(title="", servings=4, instructions="")
        error = _apply_form(recipe, request)
        if error:
            flash(error, "error")
            return render_template("recipes/form.html", recipe=None, **_form_data(None, request.form))
        db.add(recipe)
        db.commit()
        _warn_unclassified()
        flash("Recette créée.", "success")
        return redirect(url_for("recipes.detail", recipe_id=recipe.id))
    return render_template("recipes/form.html", recipe=None, **_form_data(None))


@bp.route("/recipes/<int:recipe_id>/edit", methods=["GET", "POST"])
def edit(recipe_id: int):
    recipe = _get_recipe(recipe_id)
    if request.method == "POST":
        error = _apply_form(recipe, request)
        if error:
            db.rollback()
            flash(error, "error")
            return render_template(
                "recipes/form.html", recipe=recipe, **_form_data(recipe, request.form)
            )
        db.commit()
        _warn_unclassified()
        flash("Recette enregistrée.", "success")
        return redirect(url_for("recipes.detail", recipe_id=recipe.id))
    return render_template("recipes/form.html", recipe=recipe, **_form_data(recipe))


def _form_data(recipe: Recipe | None, form=None) -> dict:
    """Valeurs affichées dans le formulaire : celles soumises si erreur, sinon la recette."""
    if form is not None:
        rows = _rows_from_form(form)
        values = {
            "title": form.get("title", ""),
            "servings": form.get("servings", "4"),
            "prep_minutes": form.get("prep_minutes", ""),
            "instructions": form.get("instructions", ""),
            "tags": form.get("tags", ""),
        }
    elif recipe is not None:
        rows = [
            {
                "name": item.ingredient.name,
                "qty": format_quantity(item.quantity),
                "unit": item.unit,
            }
            for item in recipe.items
        ]
        values = {
            "title": recipe.title,
            "servings": recipe.servings,
            "prep_minutes": recipe.prep_minutes or "",
            "instructions": recipe.instructions or "",
            "tags": recipe.tags or "",
        }
    else:
        rows = []
        values = {"title": "", "servings": 4, "prep_minutes": "", "instructions": "", "tags": ""}

    while len(rows) < 3:  # quelques lignes vides prêtes à saisir
        rows.append({"name": "", "qty": "", "unit": ""})
    return {"values": values, "rows": rows, "all_ingredients": _all_ingredients()}


def _rows_from_form(form) -> list[dict]:
    names = form.getlist("ing_name")
    quantities = form.getlist("ing_qty")
    units = form.getlist("ing_unit")
    rows = []
    for index, name in enumerate(names):
        rows.append(
            {
                "name": name,
                "qty": quantities[index] if index < len(quantities) else "",
                "unit": units[index] if index < len(units) else "",
            }
        )
    return rows


def _warn_unclassified() -> None:
    """Signale les ingrédients créés à la volée qui restent à ranger dans un rayon."""
    count = db.scalar(
        select(func.count(Ingredient.id)).where(Ingredient.category == DEFAULT_CATEGORY)
    )
    if count:
        flash(
            f"{count} ingrédient(s) sans rayon : classez-les depuis la page Ingrédients "
            "pour un tri correct de la liste de courses.",
            "error",
        )


@bp.delete("/recipes/<int:recipe_id>")
def delete(recipe_id: int):
    recipe = _get_recipe(recipe_id)
    delete_photo(recipe.photo_url, Path(current_app.config["UPLOAD_DIR"]))
    sel.remove(recipe.id)
    db.delete(recipe)
    db.commit()
    flash("Recette supprimée.", "success")
    response = current_app.make_response("")
    response.headers["HX-Redirect"] = url_for("recipes.list_recipes")
    return response


def _all_ingredients() -> list[Ingredient]:
    return list(db.scalars(select(Ingredient).order_by(Ingredient.name)).all())


def _apply_form(recipe: Recipe, req) -> str | None:
    """Applique le formulaire à la recette. Retourne un message d'erreur ou None."""
    title = (req.form.get("title") or "").strip()
    if not title:
        return "Le titre est obligatoire."

    recipe.title = title
    recipe.servings = max(1, min(50, req.form.get("servings", type=int) or 4))
    recipe.prep_minutes = req.form.get("prep_minutes", type=int)
    recipe.instructions = (req.form.get("instructions") or "").strip()
    recipe.tags = ", ".join(
        tag.strip() for tag in (req.form.get("tags") or "").split(",") if tag.strip()
    )

    upload_dir = Path(current_app.config["UPLOAD_DIR"])
    if req.form.get("remove_photo") == "1":
        delete_photo(recipe.photo_url, upload_dir)
        recipe.photo_url = None
    try:
        filename = save_photo(
            req.files.get("photo"), upload_dir, current_app.config["IMAGE_MAX_SIZE"]
        )
    except ValueError as error:
        return str(error)
    if filename:
        delete_photo(recipe.photo_url, upload_dir)
        recipe.photo_url = filename

    _apply_items(recipe, req)
    return None


def _apply_items(recipe: Recipe, req) -> None:
    """Remplace les lignes d'ingrédients par celles du formulaire.

    Les ingrédients inconnus du référentiel sont créés à la volée (rayon
    "Non classé", à reclasser depuis la page Ingrédients).
    """
    names = req.form.getlist("ing_name")
    quantities = req.form.getlist("ing_qty")
    units = req.form.getlist("ing_unit")

    recipe.items.clear()
    db.flush()

    position = 0
    seen: set[tuple[int, str]] = set()
    for index, raw_name in enumerate(names):
        name = raw_name.strip()
        if not name:
            continue
        quantity = parse_quantity(quantities[index] if index < len(quantities) else None)
        unit = canonical_unit(units[index] if index < len(units) else "")
        ingredient = _resolve_ingredient(name)
        key = (ingredient.id, unit)
        if key in seen:  # même ingrédient, même unité, saisi deux fois
            continue
        seen.add(key)
        recipe.items.append(
            RecipeIngredient(
                ingredient_id=ingredient.id, quantity=quantity, unit=unit, position=position
            )
        )
        position += 1


def _resolve_ingredient(name: str) -> Ingredient:
    existing = db.scalar(select(Ingredient).where(Ingredient.slug == ingredient_slug(name)))
    if existing:
        return existing
    return get_or_create_ingredient(name, default_unit="g", category="autre")


# --------------------------------------------------------------------------
# Fragments utilitaires
# --------------------------------------------------------------------------


@bp.get("/fragments/ingredient-row")
def ingredient_row():
    """Nouvelle ligne vide dans le formulaire de recette (ajout sans JS custom)."""
    return render_template("recipes/_form_row.html", row={"name": "", "qty": "", "unit": ""})


@bp.get("/fragments/empty")
def empty_fragment():
    """Cible de suppression d'une ligne : HTMX remplace la ligne par du vide."""
    return ""


@bp.get("/uploads/<path:filename>")
def uploaded_photo(filename: str):
    return send_from_directory(Path(current_app.config["UPLOAD_DIR"]), filename)
