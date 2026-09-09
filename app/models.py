"""Modèle de données (cf. conception-app-popotte.md §4)."""

from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base
from .units import canonical_unit, strip_accents

# Rayons de magasin : identifiant, libellé, couleur de la charte (design-UI.md §3).
CATEGORIES: list[tuple[str, str, str]] = [
    ("fruits-legumes", "Fruits & légumes", "sage"),
    ("boucherie", "Boucherie & poissonnerie", "navy"),
    ("frais", "Produits frais", "sage"),
    ("surgeles", "Surgelés", "navy"),
    ("epicerie", "Épicerie", "apricot"),
    ("boissons", "Boissons", "apricot"),
    ("autre", "Non classé", "neutral"),
]
CATEGORY_LABELS = {key: label for key, label, _ in CATEGORIES}
CATEGORY_COLORS = {key: color for key, _, color in CATEGORIES}
CATEGORY_ORDER = {key: index for index, (key, _, _) in enumerate(CATEGORIES)}
DEFAULT_CATEGORY = "autre"


def ingredient_slug(name: str) -> str:
    """Clé de dédoublonnage du référentiel : 'Œufs', 'oeuf', 'OEUF' -> 'oeuf'.

    Évite les doublons du type "œuf" / "oeufs" dans le référentiel partagé.
    """
    value = name.strip().lower().replace("œ", "oe").replace("æ", "ae")
    value = strip_accents(value)
    value = re.sub(r"[^a-z0-9]+", " ", value).strip()
    words = []
    for word in value.split():
        # dépluralisation minimale, suffisante pour du vocabulaire de cuisine
        if len(word) > 3 and word.endswith("aux"):
            word = word[:-3] + "al"
        elif len(word) > 3 and word.endswith(("s", "x")):
            word = word[:-1]
        words.append(word)
    return " ".join(words)


class Recipe(Base):
    __tablename__ = "recipe"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    servings: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    prep_minutes: Mapped[int | None] = mapped_column(Integer)
    instructions: Mapped[str] = mapped_column(Text, default="")
    photo_url: Mapped[str | None] = mapped_column(String(300))
    tags: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    items: Mapped[list["RecipeIngredient"]] = relationship(
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeIngredient.position",
    )

    @property
    def tag_list(self) -> list[str]:
        return [t.strip() for t in (self.tags or "").split(",") if t.strip()]

    @property
    def steps(self) -> list[str]:
        """Découpe les instructions en étapes pour le mode cuisine.

        Une étape = un paragraphe (ligne non vide). Les numéros déjà saisis
        ("1. ", "2) ") sont retirés pour éviter le doublon d'affichage.
        """
        steps = []
        for block in re.split(r"\n\s*\n|\n", self.instructions or ""):
            text = block.strip()
            if not text:
                continue
            steps.append(re.sub(r"^\s*\d+[\.\)]\s*", "", text))
        return steps


class Ingredient(Base):
    """Référentiel global, partagé par toutes les recettes."""

    __tablename__ = "ingredient"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    default_unit: Mapped[str] = mapped_column(String(20), default="g")
    category: Mapped[str] = mapped_column(String(40), default=DEFAULT_CATEGORY, index=True)

    @property
    def category_label(self) -> str:
        return CATEGORY_LABELS.get(self.category, CATEGORY_LABELS[DEFAULT_CATEGORY])

    @property
    def category_color(self) -> str:
        return CATEGORY_COLORS.get(self.category, "neutral")


class RecipeIngredient(Base):
    """Ligne d'ingrédient d'une recette.

    Conserve l'unité *telle qu'écrite dans la recette* : aucune conversion
    n'a lieu ici, uniquement au moment de générer la liste de courses.
    """

    __tablename__ = "recipe_ingredient"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id", ondelete="CASCADE"), index=True)
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredient.id"), index=True)
    quantity: Mapped[float | None] = mapped_column(Float)  # None = quantité libre (sel, poivre)
    unit: Mapped[str] = mapped_column(String(20), default="")
    position: Mapped[int] = mapped_column(Integer, default=0)

    recipe: Mapped[Recipe] = relationship(back_populates="items")
    ingredient: Mapped[Ingredient] = relationship(lazy="joined")

    @property
    def canonical_unit(self) -> str:
        return canonical_unit(self.unit)


class ShoppingList(Base):
    """Une session de courses = un panier de recettes sélectionnées."""

    __tablename__ = "shopping_list"

    id: Mapped[int] = mapped_column(primary_key=True)
    # heure locale : la date est affichée telle quelle dans l'historique
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    selections: Mapped[list["ShoppingListRecipe"]] = relationship(
        back_populates="shopping_list", cascade="all, delete-orphan"
    )
    items: Mapped[list["ShoppingListItem"]] = relationship(
        back_populates="shopping_list",
        cascade="all, delete-orphan",
        order_by="(ShoppingListItem.position)",
    )

    @property
    def checked_count(self) -> int:
        return sum(1 for item in self.items if item.checked)


class ShoppingListRecipe(Base):
    """recipe_selection[] : quelle recette, pour combien de portions."""

    __tablename__ = "shopping_list_recipe"
    __table_args__ = (UniqueConstraint("shopping_list_id", "recipe_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    shopping_list_id: Mapped[int] = mapped_column(
        ForeignKey("shopping_list.id", ondelete="CASCADE"), index=True
    )
    recipe_id: Mapped[int] = mapped_column(ForeignKey("recipe.id", ondelete="CASCADE"))
    servings: Mapped[int] = mapped_column(Integer, default=4)

    shopping_list: Mapped[ShoppingList] = relationship(back_populates="selections")
    recipe: Mapped[Recipe] = relationship(lazy="joined")


class ShoppingListItem(Base):
    """Résultat calculé et persisté (pour pouvoir cocher les articles)."""

    __tablename__ = "shopping_list_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    shopping_list_id: Mapped[int] = mapped_column(
        ForeignKey("shopping_list.id", ondelete="CASCADE"), index=True
    )
    ingredient_id: Mapped[int] = mapped_column(ForeignKey("ingredient.id"))
    quantity_total: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(20), default="")
    checked: Mapped[bool] = mapped_column(Boolean, default=False)
    # Unités incompatibles pour un même ingrédient : à vérifier à la main.
    needs_check: Mapped[bool] = mapped_column(Boolean, default=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    shopping_list: Mapped[ShoppingList] = relationship(back_populates="items")
    ingredient: Mapped[Ingredient] = relationship(lazy="joined")
