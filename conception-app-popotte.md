# Document de design — Popotte: Application de gestion de recettes & liste de courses

## 1. Objectif du produit

Permettre de :
- Cataloguer des recettes (ingrédients quantifiés + mode opératoire)
- Sélectionner plusieurs recettes pour un repas / une semaine
- Générer automatiquement une liste de courses agrégée (ex. recette A = 1 œuf, recette B = 3 œufs → liste de courses = 4 œufs)

Contrainte de conception clé : l'agrégation doit gérer des **unités différentes pour un même ingrédient** (g / kg, ml / cl / l, pièce...) et les convertir avant de sommer.

---

## 2. Périmètre fonctionnel (MVP → V2)

| Fonction | MVP | V2 |
|---|---|---|
| CRUD recettes (titre, portions, ingrédients, étapes, photo) | ✅ | — |
| Unités multiples + conversion automatique | ✅ | — |
| Sélection multi-recettes → génération liste de courses | ✅ | — |
| Ajustement du nombre de portions par recette sélectionnée | ✅ | — |
| Coche des articles achetés | ✅ | — |
| Regroupement de la liste par rayon (épicerie, frais, fruits/légumes...) | ✅ | — |
| Mode "cuisine" plein écran (instructions étape par étape, lisible en cuisine) | ✅ | — |
| Tags / filtres (végé, rapide, saison...) | — | ✅ |
| Interconnexion avec Auchan Drive (envoi direct du panier) | — | ⏳ non prioritaire, à explorer |

**Écarté du périmètre pour l'instant** (usage mono-utilisateur, sur son propre réseau) :
- Gestion de stock / placard
- Planning de repas (calendrier)
- Import de recette par scraping d'URL
- Export PDF
- Multi-utilisateurs / partage temps réel
- Login / mot de passe (application non exposée publiquement, accès direct au réseau local)

---

## 3. Architecture technique

Compte tenu de l'usage mono-foyer, sans besoin de scalabilité ni de multi-utilisateurs, je propose une stack volontairement minimaliste : **un seul langage, un seul conteneur, pas de build frontend séparé**. L'objectif est de réduire au maximum ce qu'il y a à maintenir dans le temps (pas de synchronisation de versions front/back, pas de pipeline de build JS, pas de serveur de base de données à administrer).

### 3.1 Stack recommandée (simple)

| Couche | Choix | Justification |
|---|---|---|
| Langage / Backend | **Python + Flask** (ou FastAPI si tu préfères le typage/l'auto-doc, au choix — les deux conviennent) | Un seul langage pour toute l'appli, pas de couche API séparée à maintenir |
| Rendu des pages | **Jinja2 (server-side) + HTMX** | Pas de build React/Vite, pas de `npm install` à maintenir dans le temps ; HTMX permet des interactions dynamiques (cocher un article, générer la liste) sans écrire de JS complexe — juste des fragments HTML renvoyés par le serveur |
| Style | **daisyUI (Tailwind + composants sémantiques), via CDN** | Rendu nettement plus riche qu'un CSS classless (cards avec ombres, badges, modals, thèmes de couleurs prêts, dark mode) tout en restant pilotable en une balise `<link>`/`<script>`, sans étape de build Node/npm |
| Base de données | **SQLite** | Un seul fichier, zéro serveur à administrer, largement suffisant pour un usage mono-foyer ; sauvegarde = copier le fichier |
| ORM | **SQLAlchemy 2.0** | Migrations simples avec Alembic si besoin, ou même schéma géré à la main vu la taille du projet |
| Auth | Aucune (cf. périmètre retenu) | Réseau local uniquement |
| Déploiement | **1 seul conteneur Docker** (Flask/FastAPI sert directement le HTML + les assets), volume monté pour le fichier SQLite | Un seul `docker-compose.yml` avec un seul service ; redémarrage, mise à jour et sauvegarde triviaux |

Résultat concret : **1 dossier Python, 1 fichier SQLite, 1 conteneur**. Pas de frontend à builder ni à déployer séparément, pas de base de données à administrer, pas de gestion de comptes.

### 3.2 Ce que ça change par rapport à la V1 initiale

| Aspect | Version initiale (React + Postgres) | Version simplifiée retenue |
|---|---|---|
| Frontend | App React séparée, build Vite, PWA | Pages HTML rendues par le serveur (Jinja2 + HTMX) |
| Base de données | PostgreSQL (serveur dédié) | SQLite (fichier unique) |
| Conteneurs | 3 (backend, frontend, db) | 1 |
| Maintenance | Suivre 2 écosystèmes (Python + JS), gérer un serveur Postgres | Un seul écosystème Python, sauvegarde = copie de fichier |
| Pertinent si... | Multi-utilisateurs, forte charge, évolution vers appli mobile native | Usage mono-foyer, priorité à la simplicité |

C'est cohérent avec le reste du périmètre déjà simplifié (pas de login, pas de multi-utilisateurs) : autant aligner l'architecture sur le même niveau d'ambition.

### 3.3 Schéma d'architecture

```
┌─────────────────────────────┐
│ Navigateur (mobile ou desktop) │
└──────────────┬───────────────┘
               │ HTTPS (via Nginx Proxy Manager, *.lehavre.igny)
┌──────────────▼───────────────┐
│  Flask/FastAPI                 │
│  - rend les pages HTML (Jinja2)  │
│  - fragments HTMX pour l'interactif │
│  - logique d'agrégation des ingrédients │
└──────────────┬───────────────┘
               │
┌──────────────▼───────────────┐
│  SQLite (1 fichier, 1 volume)  │
└───────────────────────────────┘
```

Déploiement dans le LXC Docker existant, reverse-proxy via NPM comme le reste de ton infra, exposable en `recettes.lehavre.igny`.

---

## 4. Modèle de données

```
recipe
├─ id
├─ title
├─ servings (nb de portions de base)
├─ instructions (texte / markdown, étapes)
├─ photo_url
├─ tags[] (optionnel V2)

ingredient (référentiel global, pour éviter les doublons "œuf"/"oeufs")
├─ id
├─ name              -- "œuf"
├─ default_unit      -- unité "naturelle" (pièce, g, ml...)
├─ category          -- rayon : épicerie / frais / fruits-légumes / boucherie...

recipe_ingredient (table de liaison = la vraie donnée de la recette)
├─ id
├─ recipe_id
├─ ingredient_id
├─ quantity           -- ex: 1
├─ unit                -- ex: "pièce", "g", "cl"

shopping_list (une session de courses = un panier de recettes sélectionnées)
├─ id
├─ created_at
├─ recipe_selection[]  -- {recipe_id, servings_multiplier}

shopping_list_item (résultat calculé, persisté pour permettre de cocher)
├─ id
├─ shopping_list_id
├─ ingredient_id
├─ quantity_total     -- agrégée et convertie
├─ unit                -- unité de sortie choisie
├─ checked (bool)
```

**Point important** : `recipe_ingredient` conserve l'unité *telle qu'écrite dans la recette* (ex. "1 œuf" vs une autre recette qui dirait "3 œufs" — même unité ici, cas simple). La conversion n'intervient que lors de l'agrégation, entre unités *compatibles* (g/kg, ml/cl/l), jamais entre unités hétérogènes (on ne convertit pas "1 gousse d'ail" en grammes sauf si tu renseignes un poids moyen par pièce).

---

## 5. Algorithme de génération de la liste de courses

1. L'utilisateur sélectionne N recettes, avec pour chacune un multiplicateur de portions (ex. recette prévue pour 4, je veux 8 → x2).
2. Pour chaque recette sélectionnée, chaque `recipe_ingredient` est multiplié par le ratio (portions demandées / portions de base).
3. Regroupement par `ingredient_id`.
4. **Normalisation d'unité** par groupe :
   - Table de conversion interne (g↔kg, ml↔cl↔l, pièce=pièce).
   - Si toutes les occurrences sont dans la même famille d'unité → conversion vers l'unité la plus lisible (ex. total en g → afficher en kg si > 1000g).
   - Si unités incompatibles pour un même ingrédient (ex. "1 pincée" + "5g") → ne pas fusionner silencieusement, afficher les deux lignes avec une alerte visuelle "à vérifier manuellement".
5. Arrondi à l'unité d'achat réaliste (ex. œufs = entier supérieur, jamais 3.5 œufs → 4).
6. Tri par rayon (`ingredient.category`) pour un parcours efficace en magasin.

Exemple concret :
```
Recette A (x1) : 1 œuf, 200g farine
Recette B (x2) : 3 œufs, 50g beurre
──────────────────────────────────
Liste : 
  Frais       → 4 œufs, 100g beurre
  Épicerie    → 200g farine
```

---

## 6. Routes de l'application (pages + fragments HTMX)

Pas d'API JSON séparée : le serveur rend directement du HTML (pages complètes ou fragments partiels renvoyés à HTMX pour les mises à jour dynamiques).

| Méthode | Route | Rend |
|---|---|---|
| GET | `/recipes` | Page — liste des recettes |
| GET/POST | `/recipes/new` | Page/formulaire — création d'une recette |
| GET | `/recipes/{id}` | Page — fiche recette |
| POST | `/recipes/{id}/edit`, `DELETE /recipes/{id}` | Édition / suppression |
| POST | `/shopping-list` | Fragment HTMX — génère la liste à partir de la sélection `[{recipe_id, servings}]`, retourne le HTML de la liste groupée par rayon |
| PATCH | `/shopping-list/items/{item_id}/toggle` | Fragment HTMX — coche/décoche un article (met à jour uniquement cette ligne côté navigateur) |

Cette approche évite d'avoir à maintenir un contrat d'API séparé du rendu : une seule route sert à la fois la logique et l'affichage.

---

## 7. IHM / Écrans

1. **Accueil — Liste des recettes**
   - Grille de cartes (photo, titre, temps/portions)
   - Barre de recherche + filtres (tags, V2)
   - Bouton "+ Nouvelle recette"

2. **Fiche recette**
   - Ingrédients (liste à cocher pour info) + mode opératoire
   - Sélecteur de portions
   - Bouton "Ajouter à ma liste de courses"
   - Bouton "Mode cuisine" → bascule vers une vue plein écran, texte large, étapes affichées une par une ou en liste continue selon préférence, pensée pour être lue depuis l'autre bout du plan de travail

3. **Sélection multi-recettes**
   - Vue "panier" : recettes cochées avec ajusteur de portions par recette
   - Bouton "Générer la liste de courses"

4. **Liste de courses**
   - Groupée par rayon, checkboxes, quantités agrégées
   - Articles à "vérifier manuellement" mis en évidence (unités incompatibles)
   - Mode plein écran optimisé mobile, gros tap-targets (usage au supermarché, une main)

### Principes UX
- Mobile-first strict pour l'écran "liste de courses" (contexte magasin).
- Desktop/tablette plus confortable pour la saisie de recettes.
- Les mises à jour (cocher un article, générer la liste) se font sans rechargement de page grâce à HTMX, sans complexité JS côté navigateur.

---

## 8. Déploiement (intégration à ton infra)

- **1 seul conteneur** dans un LXC Docker existant (ou nouveau LXC léger) : l'appli Flask/FastAPI sert le HTML et les fragments HTMX directement.
- Volume Docker pour le fichier SQLite (persistance).
- Reverse-proxy via **Nginx Proxy Manager** existant → `recettes.lehavre.igny`, certificat interne comme le reste.
- Sauvegarde : copie régulière du fichier SQLite (cron simple, pas de dump de base nécessaire).
- Mise à jour : rebuild de l'unique image Docker, rien d'autre à synchroniser.

---

## 9. Roadmap suggérée

1. **V0 (1 week-end)** : modèle de données + CRUD recette + génération liste simple (sans conversion d'unité, juste somme brute) — valider l'usage réel.
2. **V1** : conversion d'unités, regroupement par rayon. → périmètre cible actuel.
3. **Piste future (non prioritaire)** : tags/filtres, puis exploration d'une interconnexion avec Auchan Drive (envoi automatique du panier généré vers leur site/appli, à condition qu'une API ou un moyen d'automatisation existe côté Auchan).
