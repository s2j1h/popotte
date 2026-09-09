"""Filtres et variables globales Jinja2."""

from __future__ import annotations

from flask import Flask

from .models import CATEGORIES, CATEGORY_COLORS, CATEGORY_LABELS
from .units import UNIT_CHOICES, format_amount, format_quantity, round_purchase, unit_def


def register(app: Flask) -> None:
    app.jinja_env.filters["qty"] = format_quantity

    @app.template_filter("amount_of")
    def amount_of(quantity, unit=""):
        return format_amount(quantity, unit)

    @app.template_filter("scaled_amount")
    def scaled_amount(quantity, unit=""):
        """Quantité d'une recette ramenée à un nombre de portions.

        Les unités dénombrables sont arrondies à l'entier supérieur : on ne
        cuisine pas avec 7,5 œufs.
        """
        if quantity is not None and unit_def(unit).countable:
            quantity = round_purchase(quantity, unit)
        return format_amount(quantity, unit)

    @app.context_processor
    def globals_():
        from .views.selection import current_selection

        selection = current_selection()
        return {
            "CATEGORIES": CATEGORIES,
            "CATEGORY_LABELS": CATEGORY_LABELS,
            "CATEGORY_COLORS": CATEGORY_COLORS,
            "UNIT_CHOICES": UNIT_CHOICES,
            "selection_count": len(selection),
        }
