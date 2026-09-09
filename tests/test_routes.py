"""Parcours principaux : navigation, création de recette, panier, liste de courses."""

from sqlalchemy import select

from app.db import db
from app.models import Recipe, ShoppingList, ShoppingListItem

HX = {"HX-Request": "true"}


def test_accueil_redirige_vers_les_recettes(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/recipes")


def test_liste_des_recettes_affiche_les_exemples(client):
    body = client.get("/recipes").get_data(as_text=True)
    assert "Omelette aux champignons" in body
    assert "Gâteau au yaourt" in body


def test_recherche_par_ingredient(client):
    body = client.get("/recipes?q=champignon&fragment=1", headers=HX).get_data(as_text=True)
    assert "Omelette aux champignons" in body
    assert "Poulet rôti" not in body


def test_fiche_recette_et_ajustement_des_portions(client, app):
    recipe = db.scalar(select(Recipe).where(Recipe.title == "Omelette aux champignons"))
    body = client.get(f"/recipes/{recipe.id}").get_data(as_text=True)
    assert "champignon de Paris" in body
    assert "250 g" in body
    # 4 -> 8 portions : les quantités doublent
    fragment = client.get(f"/recipes/{recipe.id}/ingredients?servings=8", headers=HX)
    assert "500 g" in fragment.get_data(as_text=True)


def test_mode_cuisine_etape_par_etape(client, app):
    recipe = db.scalar(select(Recipe).where(Recipe.title == "Omelette aux champignons"))
    body = client.get(f"/recipes/{recipe.id}/cuisine").get_data(as_text=True)
    assert "Étape 1 /" in body
    assert "cook-screen" in body
    assert "pop-bottom-nav" not in body  # plein écran : aucune navigation


def test_creation_puis_suppression_dune_recette(client, app):
    response = client.post(
        "/recipes/new",
        data={
            "title": "Salade de tomates",
            "servings": "2",
            "prep_minutes": "10",
            "tags": "rapide, végé",
            "instructions": "Couper les tomates.\nAssaisonner.",
            "ing_name": ["tomate", "huile d'olive", "sel"],
            "ing_qty": ["4", "2", ""],
            "ing_unit": ["pièce", "c. à soupe", ""],
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    recipe = db.scalar(select(Recipe).where(Recipe.title == "Salade de tomates"))
    assert recipe is not None
    assert len(recipe.items) == 3
    assert recipe.steps == ["Couper les tomates.", "Assaisonner."]

    assert client.delete(f"/recipes/{recipe.id}", headers=HX).status_code == 200
    assert db.get(Recipe, recipe.id) is None


def test_titre_obligatoire(client):
    response = client.post("/recipes/new", data={"title": "  ", "servings": "4"})
    assert "obligatoire" in response.get_data(as_text=True)


def test_panier_puis_generation_de_la_liste(client, app):
    recipes = db.scalars(select(Recipe)).all()
    for recipe in recipes[:2]:
        assert client.post(f"/selection/{recipe.id}/toggle", headers=HX).status_code == 200

    basket = client.get("/panier").get_data(as_text=True)
    assert recipes[0].title in basket

    response = client.post("/shopping-list", headers=HX)
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Liste de courses" in body
    assert "HX-Push-Url" in response.headers

    shopping_list = db.scalar(select(ShoppingList))
    assert shopping_list is not None
    assert len(shopping_list.items) > 0
    # les deux recettes contiennent des œufs : une seule ligne agrégée
    eggs = [item for item in shopping_list.items if item.ingredient.name == "œuf"]
    assert len(eggs) == 1


def test_coche_dun_article_est_persistee(client, app):
    recipe = db.scalar(select(Recipe))
    client.post(f"/selection/{recipe.id}/toggle", headers=HX)
    client.post("/shopping-list", headers=HX)
    item = db.scalar(select(ShoppingListItem))

    response = client.patch(f"/shopping-list/items/{item.id}/toggle", headers=HX)
    assert response.status_code == 200
    assert "item-checked" in response.get_data(as_text=True)
    db.expire_all()
    assert db.get(ShoppingListItem, item.id).checked is True


def test_ajustement_des_portions_du_panier(client, app):
    recipe = db.scalar(select(Recipe).where(Recipe.title == "Omelette aux champignons"))
    client.post(f"/selection/{recipe.id}/toggle", headers=HX)
    client.post(f"/selection/{recipe.id}/servings", data={"servings": "8"}, headers=HX)
    client.post("/shopping-list", headers=HX)
    shopping_list = db.scalar(select(ShoppingList))
    eggs = next(item for item in shopping_list.items if item.ingredient.name == "œuf")
    assert eggs.quantity_total == 12  # 6 œufs pour 4 -> 12 pour 8


def test_liste_vide_si_panier_vide(client):
    body = client.post("/shopping-list", headers=HX).get_data(as_text=True)
    assert "Panier vide" in body


def test_referentiel_ingredients(client, app):
    body = client.get("/ingredients").get_data(as_text=True)
    assert "Fruits &amp; légumes" in body or "Fruits & légumes" in body

    from app.models import Ingredient

    ingredient = db.scalar(select(Ingredient).where(Ingredient.name == "farine"))
    response = client.post(
        f"/ingredients/{ingredient.id}", data={"category": "epicerie", "default_unit": "kg"}, headers=HX
    )
    assert response.status_code == 200
    db.expire_all()
    assert db.get(Ingredient, ingredient.id).default_unit == "kg"


def test_page_inconnue(client):
    response = client.get("/recipes/9999")
    assert response.status_code == 404
    assert "existe pas" in response.get_data(as_text=True).replace("&#39;", "'")
