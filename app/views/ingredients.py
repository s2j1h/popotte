"""Référentiel d'ingrédients : rayon et unité par défaut."""

from __future__ import annotations

from flask import Blueprint, abort, render_template, request
from sqlalchemy import func, select

from ..db import db
from ..models import CATEGORY_ORDER, DEFAULT_CATEGORY, Ingredient, RecipeIngredient
from ..units import canonical_unit

bp = Blueprint("ingredients", __name__)


@bp.get("/ingredients")
def list_ingredients():
    query = (request.args.get("q") or "").strip().lower()
    statement = select(Ingredient)
    if query:
        statement = statement.where(func.lower(Ingredient.name).like(f"%{query}%"))
    ingredients = list(db.scalars(statement).all())
    ingredients.sort(
        key=lambda i: (CATEGORY_ORDER.get(i.category, 99), i.name.lower())
    )
    usage = dict(
        db.execute(
            select(RecipeIngredient.ingredient_id, func.count(RecipeIngredient.id)).group_by(
                RecipeIngredient.ingredient_id
            )
        ).all()
    )
    unclassified = sum(1 for i in ingredients if i.category == DEFAULT_CATEGORY)
    return render_template(
        "ingredients/list.html",
        ingredients=ingredients,
        usage=usage,
        query=query,
        unclassified=unclassified,
    )


@bp.post("/ingredients/<int:ingredient_id>")
def update(ingredient_id: int):
    ingredient = db.get(Ingredient, ingredient_id)
    if ingredient is None:
        abort(404)
    category = request.form.get("category")
    if category in CATEGORY_ORDER:
        ingredient.category = category
    if "default_unit" in request.form:
        ingredient.default_unit = canonical_unit(request.form.get("default_unit"))
    if name := (request.form.get("name") or "").strip():
        ingredient.name = name
    db.commit()
    usage = db.scalar(
        select(func.count(RecipeIngredient.id)).where(
            RecipeIngredient.ingredient_id == ingredient.id
        )
    )
    return render_template("ingredients/_row.html", ingredient=ingredient, count=usage)
