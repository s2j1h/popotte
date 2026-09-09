# CLAUDE.md — Application de gestion de recettes & liste de courses

Directives de développement pour ce projet. À lire avant toute intervention sur le code.

## Contexte

Application self-hostée, **usage mono-foyer**, déployée sur un LXC Docker existant derrière Nginx Proxy Manager (`recettes.lehavre.igny`). Priorité absolue : **simplicité de développement et de maintenance** sur le long terme, plutôt que scalabilité ou richesse fonctionnelle.

Objectif produit : cataloguer des recettes (ingrédients + mode opératoire), sélectionner plusieurs recettes, générer automatiquement une liste de courses agrégée avec conversion d'unités (ex. 1 œuf + 3 œufs → 4 œufs à acheter).

## Stack imposée — ne pas dévier sans validation explicite

- **Langage unique : Python** (Flask ou FastAPI). Pas de frontend séparé, pas de second langage.
- **Rendu : Jinja2 (server-side) + HTMX.** Le serveur rend du HTML ; HTMX gère les mises à jour partielles (cocher un article, générer la liste). **Aucun JS custom complexe, aucun bundler, aucun `npm install`.**
- **Style : daisyUI (Tailwind + composants), fichiers auto-hébergés dans `app/static/vendor/`** (simples `<link>`/`<script>`, pas de build Node). Mise à jour via `./scripts/update-vendor.sh` — ne jamais réintroduire de dépendance CDN : l'app doit fonctionner sur un LAN sans Internet.
- **Base de données : SQLite**, un seul fichier, monté en volume Docker.
- **ORM : SQLAlchemy 2.0** (Alembic optionnel pour les migrations si besoin).
- **Aucune authentification** — l'appli n'est exposée que sur le réseau local, pas de login/mot de passe à implémenter.
- **Déploiement : 1 seul conteneur Docker.** Un seul `docker-compose.yml`, un seul service.

### Ce qui est explicitement refusé
Ne jamais proposer ou introduire, même "pour améliorer" :
- React, Vue, Svelte, ou tout framework JS avec étape de build
- PostgreSQL/MySQL ou tout serveur de base de données séparé
- Un backend API JSON séparé du rendu HTML (pas de contrat REST/OpenAPI à maintenir)
- Login, comptes utilisateurs, gestion de sessions, JWT
- Docker Compose multi-conteneurs pour ce projet

Si une évolution semble nécessiter l'un de ces éléments, le signaler et demander confirmation avant de l'implémenter — ne jamais le faire par défaut.

## Périmètre fonctionnel

### Dans le scope (MVP)
- CRUD recettes : titre, portions de base, ingrédients (quantité + unité), instructions, photo
- Référentiel d'ingrédients partagé (éviter les doublons du type "œuf" / "oeufs")
- Sélection multi-recettes avec ajustement des portions par recette
- Génération de liste de courses : agrégation par ingrédient, conversion d'unités compatibles (g/kg, ml/cl/l), pas de fusion silencieuse entre unités incompatibles (afficher séparément + alerte "à vérifier")
- Arrondi à l'unité d'achat réaliste (ex. jamais 3.5 œufs → arrondi à 4)
- Liste de courses groupée par rayon (`ingredient.category`)
- Coche des articles achetés (persistée)
- Mode "cuisine" plein écran : instructions affichées en gros caractères, lisibles à distance

### Hors scope pour l'instant (ne pas implémenter sans demande explicite)
- Gestion de stock / placard
- Planning de repas (calendrier)
- Import de recette par scraping d'URL
- Export PDF
- Multi-utilisateurs / partage temps réel
- Authentification

### Piste future non prioritaire
- Interconnexion avec Auchan Drive (envoi du panier généré) — à explorer plus tard, pas maintenant.

## Modèle de données de référence

```
recipe(id, title, servings, instructions, photo_url, tags[])
ingredient(id, name, default_unit, category)
recipe_ingredient(id, recipe_id, ingredient_id, quantity, unit)
shopping_list(id, created_at, recipe_selection[])
shopping_list_item(id, shopping_list_id, ingredient_id, quantity_total, unit, checked)
```

`recipe_ingredient` conserve l'unité telle qu'écrite dans la recette. La conversion/agrégation n'a lieu qu'au moment de la génération de la liste de courses, jamais en amont.

## Algorithme d'agrégation (logique métier centrale, à préserver)

1. Multiplier chaque `recipe_ingredient` par le ratio (portions demandées / portions de base) de sa recette.
2. Regrouper par `ingredient_id`.
3. Normaliser l'unité par groupe compatible (table de conversion interne g↔kg, ml↔cl↔l ; pièce reste pièce).
4. Ne jamais fusionner silencieusement des unités incompatibles (ex. "pincée" + "5g") — afficher les deux lignes séparément avec une alerte.
5. Arrondir à l'unité d'achat réaliste.
6. Trier le résultat par rayon.

## Conventions de routes

Pas d'API JSON séparée. Chaque route sert à la fois la logique et le rendu (HTML complet ou fragment HTMX) :

- `GET /recipes` — liste des recettes
- `GET/POST /recipes/new` — création
- `GET /recipes/{id}` — fiche recette
- `POST /recipes/{id}/edit`, `DELETE /recipes/{id}` — édition / suppression
- `POST /shopping-list` — génère la liste (fragment HTMX)
- `PATCH /shopping-list/items/{item_id}/toggle` — coche/décoche un article (fragment HTMX)

## Principes UX à respecter

- Écran "liste de courses" : mobile-first strict, gros tap-targets (usage au supermarché, une main).
- Écrans de saisie de recette : optimisés desktop/tablette, mais restent utilisables sur mobile.
- Toute interaction (cocher, générer, éditer) doit passer par HTMX sans rechargement de page complète.

## Déploiement

- 1 conteneur Docker, volume monté pour le fichier SQLite.
- Reverse-proxy via Nginx Proxy Manager (infra existante), exposé en `recettes.lehavre.igny`.
- Sauvegarde = copie du fichier SQLite (pas de dump de base nécessaire).
- Mise à jour = rebuild de l'image unique.

## Historique des décisions

Les assets front (daisyUI, Tailwind, HTMX, polices Fraunces/Work Sans) étaient initialement
chargés depuis un CDN. Ils ont été rapatriés dans `app/static/vendor/` pour que l'application
reste utilisable sur le réseau local sans accès Internet. Le principe reste inchangé : ce sont
des fichiers servis tels quels, aucune étape de build Node n'a été introduite.

Ce projet a délibérément été simplifié par rapport à une première ébauche (React + PostgreSQL + 3 conteneurs) pour privilégier la maintenabilité par une seule personne. Toute suggestion qui réintroduirait cette complexité doit être justifiée explicitement et validée avant d'être appliquée.
