"""Panier de recettes et liste de courses."""

from __future__ import annotations

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from sqlalchemy import select

from ..db import db
from ..models import Recipe, ShoppingList, ShoppingListItem, ShoppingListRecipe
from ..shopping import aggregate, build_items, group_by_category
from . import selection as sel

bp = Blueprint("shopping", __name__)


# --------------------------------------------------------------------------
# Panier (sélection multi-recettes)
# --------------------------------------------------------------------------


@bp.get("/panier")
def basket():
    return render_template("shopping/basket.html", pairs=sel.selected_recipes())


@bp.post("/selection/<int:recipe_id>/toggle")
def toggle_selection(recipe_id: int):
    recipe = db.get(Recipe, recipe_id)
    if recipe is None:
        abort(404)
    in_selection = sel.toggle(recipe)
    return render_template(
        "partials/_selection_button.html",
        recipe=recipe,
        in_selection=in_selection,
        style=request.args.get("style", "card"),
    )


@bp.post("/selection/<int:recipe_id>/servings")
def update_servings(recipe_id: int):
    servings = request.form.get("servings", type=int)
    if servings is None:
        delta = request.form.get("delta", type=int) or 0
        servings = (sel.current_selection().get(recipe_id) or 4) + delta
    sel.set_servings(recipe_id, servings)
    return render_template("shopping/_basket_list.html", pairs=sel.selected_recipes())


@bp.post("/selection/<int:recipe_id>/remove")
def remove_from_selection(recipe_id: int):
    sel.remove(recipe_id)
    return render_template("shopping/_basket_list.html", pairs=sel.selected_recipes())


@bp.post("/selection/clear")
def clear_selection():
    sel.clear()
    return render_template("shopping/_basket_list.html", pairs=sel.selected_recipes())


# --------------------------------------------------------------------------
# Liste de courses
# --------------------------------------------------------------------------


@bp.post("/shopping-list")
def generate():
    """Génère la liste à partir du panier et renvoie le fragment HTMX."""
    pairs = sel.selected_recipes()
    if not pairs:
        return render_template("shopping/_list.html", shopping_list=None, groups=[])

    shopping_list = ShoppingList()
    db.add(shopping_list)
    db.flush()

    for recipe, servings in pairs:
        db.add(
            ShoppingListRecipe(
                shopping_list_id=shopping_list.id, recipe_id=recipe.id, servings=servings
            )
        )

    lines = aggregate([(recipe, float(servings)) for recipe, servings in pairs])
    for item in build_items(shopping_list.id, lines):
        db.add(item)
    db.commit()

    response = current_app.make_response(_render_list(shopping_list))
    response.headers["HX-Push-Url"] = url_for("shopping.show_list", list_id=shopping_list.id)
    return response


@bp.get("/shopping-list")
def latest_list():
    shopping_list = db.scalar(select(ShoppingList).order_by(ShoppingList.created_at.desc()).limit(1))
    if shopping_list is None:
        return redirect(url_for("shopping.basket"))
    return redirect(url_for("shopping.show_list", list_id=shopping_list.id))


@bp.get("/shopping-list/<int:list_id>")
def show_list(list_id: int):
    shopping_list = db.get(ShoppingList, list_id)
    if shopping_list is None:
        abort(404)
    return render_template(
        "shopping/list.html",
        shopping_list=shopping_list,
        groups=group_by_category(shopping_list.items),
    )


@bp.patch("/shopping-list/items/<int:item_id>/toggle")
def toggle_item(item_id: int):
    """Coche/décoche un article : ne renvoie que la ligne concernée."""
    item = db.get(ShoppingListItem, item_id)
    if item is None:
        abort(404)
    item.checked = not item.checked
    db.commit()
    return render_template("shopping/_item.html", item=item, oob_progress=True)


@bp.get("/shopping-list/<int:list_id>/progress")
def list_progress(list_id: int):
    shopping_list = db.get(ShoppingList, list_id)
    if shopping_list is None:
        abort(404)
    return render_template("shopping/_progress.html", shopping_list=shopping_list)


@bp.post("/shopping-list/<int:list_id>/reset")
def reset_list(list_id: int):
    shopping_list = db.get(ShoppingList, list_id)
    if shopping_list is None:
        abort(404)
    for item in shopping_list.items:
        item.checked = False
    db.commit()
    return _render_list(shopping_list)


@bp.post("/shopping-list/<int:list_id>/delete")
def delete_list(list_id: int):
    shopping_list = db.get(ShoppingList, list_id)
    if shopping_list is None:
        abort(404)
    db.delete(shopping_list)
    db.commit()
    flash("Liste supprimée.", "success")
    if request.headers.get("HX-Request"):
        response = current_app.make_response("")
        response.headers["HX-Redirect"] = url_for("shopping.history")
        return response
    return redirect(url_for("shopping.history"))


@bp.get("/listes")
def history():
    lists = db.scalars(select(ShoppingList).order_by(ShoppingList.created_at.desc())).all()
    return render_template("shopping/history.html", lists=lists)


def _render_list(shopping_list: ShoppingList) -> str:
    return render_template(
        "shopping/_list.html",
        shopping_list=shopping_list,
        groups=group_by_category(shopping_list.items),
    )
