"""Données initiales : référentiel d'ingrédients + quelques recettes d'exemple.

N'est appliqué qu'au tout premier démarrage (base vide).
"""

from __future__ import annotations

from sqlalchemy import select

from .db import db
from .models import Ingredient, Recipe, RecipeIngredient, ingredient_slug

# (nom, unité par défaut, rayon)
REFERENTIEL: list[tuple[str, str, str]] = [
    # Fruits & légumes
    ("ail", "gousse", "fruits-legumes"),
    ("basilic", "brin", "fruits-legumes"),
    ("carotte", "pièce", "fruits-legumes"),
    ("champignon de Paris", "g", "fruits-legumes"),
    ("citron", "pièce", "fruits-legumes"),
    ("courgette", "pièce", "fruits-legumes"),
    ("échalote", "pièce", "fruits-legumes"),
    ("épinard", "g", "fruits-legumes"),
    ("gingembre", "g", "fruits-legumes"),
    ("oignon", "pièce", "fruits-legumes"),
    ("persil", "brin", "fruits-legumes"),
    ("poireau", "pièce", "fruits-legumes"),
    ("poivron", "pièce", "fruits-legumes"),
    ("pomme", "pièce", "fruits-legumes"),
    ("pomme de terre", "g", "fruits-legumes"),
    ("salade", "pièce", "fruits-legumes"),
    ("thym", "brin", "fruits-legumes"),
    ("tomate", "pièce", "fruits-legumes"),
    ("banane", "pièce", "fruits-legumes"),
    ("brocoli", "pièce", "fruits-legumes"),
    # Boucherie & poissonnerie
    ("bœuf haché", "g", "boucherie"),
    ("blanc de poulet", "g", "boucherie"),
    ("poulet", "pièce", "boucherie"),
    ("lardon", "g", "boucherie"),
    ("jambon", "tranche", "boucherie"),
    ("saumon", "g", "boucherie"),
    ("crevette", "g", "boucherie"),
    ("saucisse", "pièce", "boucherie"),
    # Produits frais
    ("beurre", "g", "frais"),
    ("crème fraîche", "cl", "frais"),
    ("lait", "ml", "frais"),
    ("œuf", "pièce", "frais"),
    ("yaourt nature", "pièce", "frais"),
    ("gruyère râpé", "g", "frais"),
    ("parmesan", "g", "frais"),
    ("mozzarella", "g", "frais"),
    ("pâte brisée", "pièce", "frais"),
    ("pâte feuilletée", "pièce", "frais"),
    # Surgelés
    ("petit pois surgelé", "g", "surgeles"),
    ("épinard surgelé", "g", "surgeles"),
    ("glace vanille", "l", "surgeles"),
    # Épicerie
    ("farine", "g", "epicerie"),
    ("sucre", "g", "epicerie"),
    ("sucre vanillé", "sachet", "epicerie"),
    ("levure chimique", "sachet", "epicerie"),
    ("sel", "", "epicerie"),
    ("poivre", "", "epicerie"),
    ("huile d'olive", "c. à soupe", "epicerie"),
    ("huile de tournesol", "cl", "epicerie"),
    ("vinaigre balsamique", "c. à soupe", "epicerie"),
    ("moutarde", "c. à café", "epicerie"),
    ("riz", "g", "epicerie"),
    ("pâtes", "g", "epicerie"),
    ("lentille", "g", "epicerie"),
    ("tomate pelée", "boîte", "epicerie"),
    ("concentré de tomate", "c. à soupe", "epicerie"),
    ("bouillon de volaille", "cube", "epicerie"),
    ("chocolat noir", "g", "epicerie"),
    ("miel", "c. à soupe", "epicerie"),
    ("noix", "g", "epicerie"),
    ("paprika", "c. à café", "epicerie"),
    ("curry", "c. à café", "epicerie"),
    ("herbes de Provence", "c. à café", "epicerie"),
    ("pain", "pièce", "epicerie"),
    # Boissons
    ("vin blanc", "cl", "boissons"),
    ("vin rouge", "cl", "boissons"),
    ("jus d'orange", "l", "boissons"),
]

DEMO_RECIPES: list[dict] = [
    {
        "title": "Omelette aux champignons",
        "servings": 4,
        "prep_minutes": 20,
        "tags": "rapide, végé",
        "instructions": (
            "Nettoyer et émincer les champignons.\n"
            "Les faire revenir à la poêle dans l'huile d'olive pendant 8 minutes, "
            "jusqu'à ce qu'ils aient rendu leur eau.\n"
            "Battre les œufs en omelette, saler et poivrer.\n"
            "Ajouter le beurre dans la poêle, verser les œufs battus sur les champignons.\n"
            "Cuire 4 minutes à feu moyen, replier l'omelette et servir avec le persil ciselé."
        ),
        "items": [
            ("œuf", 6, "pièce"),
            ("champignon de Paris", 250, "g"),
            ("beurre", 20, "g"),
            ("huile d'olive", 1, "c. à soupe"),
            ("persil", 2, "brin"),
            ("sel", None, ""),
            ("poivre", None, ""),
        ],
    },
    {
        "title": "Gâteau au yaourt",
        "servings": 6,
        "prep_minutes": 45,
        "tags": "dessert, végé",
        "instructions": (
            "Préchauffer le four à 180 °C.\n"
            "Verser le yaourt dans un saladier, garder le pot comme mesure.\n"
            "Ajouter le sucre, les œufs et l'huile, mélanger.\n"
            "Incorporer la farine et la levure, mélanger jusqu'à obtenir une pâte lisse.\n"
            "Verser dans un moule beurré et enfourner 35 minutes."
        ),
        "items": [
            ("œuf", 3, "pièce"),
            ("yaourt nature", 1, "pièce"),
            ("farine", 200, "g"),
            ("sucre", 150, "g"),
            ("huile de tournesol", 10, "cl"),
            ("levure chimique", 1, "sachet"),
            ("beurre", 20, "g"),
        ],
    },
    {
        "title": "Poulet rôti et pommes de terre",
        "servings": 4,
        "prep_minutes": 90,
        "tags": "familial",
        "instructions": (
            "Préchauffer le four à 200 °C.\n"
            "Éplucher les pommes de terre et les couper en gros quartiers.\n"
            "Déposer le poulet dans un plat, le badigeonner d'huile d'olive, saler et poivrer.\n"
            "Disposer les pommes de terre autour avec l'ail en chemise et le thym.\n"
            "Enfourner 1 h 15 en arrosant le poulet toutes les 20 minutes."
        ),
        "items": [
            ("poulet", 1, "pièce"),
            ("pomme de terre", 1, "kg"),
            ("ail", 4, "gousse"),
            ("huile d'olive", 2, "c. à soupe"),
            ("beurre", 20, "g"),
            ("thym", 3, "brin"),
            ("sel", None, ""),
            ("poivre", None, ""),
        ],
    },
]


def get_or_create_ingredient(name: str, default_unit: str = "g", category: str = "autre") -> Ingredient:
    """Retrouve un ingrédient par sa clé normalisée, ou le crée."""
    slug = ingredient_slug(name)
    ingredient = db.scalar(select(Ingredient).where(Ingredient.slug == slug))
    if ingredient:
        return ingredient
    ingredient = Ingredient(
        name=name.strip(), slug=slug, default_unit=default_unit, category=category
    )
    db.add(ingredient)
    db.flush()
    return ingredient


def seed_if_empty(with_demo: bool = True) -> None:
    if db.scalar(select(Ingredient).limit(1)) is None:
        for name, unit, category in REFERENTIEL:
            get_or_create_ingredient(name, unit, category)
        db.commit()

    if with_demo and db.scalar(select(Recipe).limit(1)) is None:
        for data in DEMO_RECIPES:
            recipe = Recipe(
                title=data["title"],
                servings=data["servings"],
                prep_minutes=data["prep_minutes"],
                instructions=data["instructions"],
                tags=data["tags"],
            )
            db.add(recipe)
            db.flush()
            for position, (name, quantity, unit) in enumerate(data["items"]):
                ingredient = get_or_create_ingredient(name)
                db.add(
                    RecipeIngredient(
                        recipe_id=recipe.id,
                        ingredient_id=ingredient.id,
                        quantity=quantity,
                        unit=unit,
                        position=position,
                    )
                )
        db.commit()
