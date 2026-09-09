# Design.md — Charte graphique Popotte

Directives visuelles de l'application. Toute évolution d'interface doit s'y référer pour rester cohérente.

---

## 1. Identité de marque

**Nom** : Popotte (minuscules dans toutes les utilisations en UI : `popotte`)

**Concept** : une toque de chef stylisée surmontant deux traits horizontaux évoquant une liste/checklist — le lien direct entre "cuisiner" et "faire ses courses" est le cœur du concept visuel.

**Ton** : chaleureux mais sobre. Ni "startup SaaS" froide, ni "blog cuisine" trop décoratif — quelque chose entre une app d'outil personnel bien pensée (type Things 3, Notion) et l'univers cuisine.

---

## 2. Logo

### Fichiers de référence
- `popotte-logo-full-128.png` — logo complet (icône + wordmark), pour en-têtes, écran de connexion, README
- `popotte-icon-128.png` / `popotte-icon-64.png` — icône seule (sans texte), pour favicon, icône PWA, petits espaces

### Construction
- Toque de chef en aplat, style géométrique épuré, aucune texture ni dégradé
- Bandeau horizontal à la base de la toque, dans une teinte bleu marine plus claire que le fond
- Deux traits horizontaux (longueurs différentes) sous la toque, en orange abricot — symbolisent la checklist
- Wordmark "popotte" en minuscules, police serif chaleureuse (Fraunces), uniquement accolé quand l'espace le permet (≥ 96px de large)

### Règles d'usage
- **En dessous de 96 px de large** : utiliser systématiquement l'icône seule (sans texte), le wordmark devient illisible
- Toujours conserver le fond transparent des fichiers PNG/SVG fournis — ne jamais recadrer serré sur la toque sans la zone de respiration autour
- Ne pas recolorer le logo en dehors de la palette définie ci-dessous
- Ne pas incliner, étirer, ni appliquer d'ombre portée ou d'effet 3D au logo

---

## 3. Palette de couleurs

| Rôle | Nom | Hex | Usage |
|---|---|---|---|
| Primaire | Navy | `#1C2541` | Header/navbar, fond du mode cuisine, texte de titre, boutons secondaires |
| Primaire (variante foncée) | Navy Deep | `#141B30` | Barre de navigation mobile, états hover sur fond navy |
| Fond | Cream | `#EFEAE0` | Fond général de l'application |
| Surface | Paper | `#FAF8F3` | Fond des cartes, panneaux, zones de contenu |
| Accent primaire | Apricot | `#E8935A` | Boutons d'action principaux (CTA), badges "rapide", éléments interactifs mis en avant |
| Accent secondaire | Sage | `#6B8F71` | Badges "végé"/"frais", indicateurs de succès, rayon fruits & légumes |
| Alerte | Alerte rouge | `#B23B3B` | Articles à vérifier manuellement (unités incompatibles), messages d'erreur |
| Texte courant | Charbon | `#232323` | Corps de texte sur fond clair |
| Texte atténué | Neutre 500 | `#737373` (Tailwind `neutral-500`) | Métadonnées, texte secondaire (ex. "4 portions · 30 min") |

### Règles d'usage des couleurs
- Le **navy** est réservé à la structure (nav, headers, mode cuisine) — ne pas l'utiliser pour du texte de contenu long, il est pensé pour de grands aplats
- L'**apricot** est LA couleur d'action : un seul bouton d'accent apricot par écran maximum, pour ne pas diluer sa fonction de repère visuel
- Le **sage** est réservé aux connotations positives/naturelles (végé, frais, coché) — ne pas l'utiliser comme couleur décorative générique
- Toujours garder un ratio de contraste suffisant texte/fond (viser AA minimum) : texte crème sur navy, texte charbon sur cream/paper

---

## 4. Typographie

| Rôle | Police | Usage |
|---|---|---|
| Titres / display | **Fraunces** (serif) | Titres de page, wordmark, texte du mode cuisine |
| Corps de texte / UI | **Work Sans** (sans-serif) | Paragraphes, labels, boutons, champs de formulaire |

### Règles
- Deux familles maximum, ne jamais en ajouter une troisième
- Les titres en Fraunces restent en casse normale (pas de tout-majuscules) — évite l'effet "eyebrow label" générique
- Poids Fraunces utilisés : 500 (texte long en mode cuisine), 600 (sous-titres), 700 (titres principaux)
- Poids Work Sans utilisés : 400 (corps), 500 (labels/boutons), 600 (emphase ponctuelle)
- Lignes de texte : viser un maximum de ~75-80 caractères de large pour la lisibilité, notamment dans le mode cuisine

---

## 5. Composants d'interface (via daisyUI)

L'application s'appuie sur **daisyUI (Tailwind) en CDN**, avec les couleurs ci-dessus injectées comme thème custom plutôt que les couleurs par défaut de daisyUI.

| Composant | Convention |
|---|---|
| Cartes (recette) | Fond `Paper`, coins arrondis généreux (`rounded-2xl`), ombre légère uniquement, jamais de bordure épaisse |
| Boutons primaires | Fond `Apricot`, texte blanc, `rounded-full` |
| Boutons secondaires / structurels | Fond `Navy`, texte `Cream`, `rounded-full` |
| Badges/tags | Pilule (`rounded-full`), fond en teinte pâle de la couleur sémantique (ex. sage à 15-20% d'opacité) + texte dans la couleur pleine |
| Champs de recherche/formulaire | `rounded-full` pour les champs courts (recherche), coins plus classiques pour les formulaires longs (création de recette) |
| Checkboxes (liste de courses) | Couleur de bordure alignée sur le rayon (sage pour frais, apricot pour épicerie, rouge alerte pour "à vérifier") |

### Principe de forme
- Les coins très arrondis (`rounded-2xl`/`rounded-full`) sont la signature visuelle de l'app — cohérent avec le ton "chaleureux, à la maison"
- Un seul niveau d'arrondi dominant par type de composant (pas de mélange arbitraire d'angles vifs et arrondis sur un même écran)

---

## 6. Écrans clés — principes

### Liste des recettes
- Grille de cartes avec image en aplat dégradé (pas de vraies photos requises au MVP, un dégradé de couleur de la palette peut suffire tant qu'il n'y a pas de photo)
- Sélection multiple visible via une bordure/anneau `Apricot` sur la carte active

### Fiche recette
- Instructions à gauche/au centre (contenu principal), ingrédients dans un panneau latéral avec ajusteur de portions
- Le bouton "Mode cuisine" est toujours en `Apricot`, seul CTA fort de l'écran

### Mode cuisine
- Plein écran, fond `Navy`, texte `Cream` en Fraunces, grande taille
- Une étape affichée à la fois, navigation par grands boutons circulaires
- Aucun élément d'interface secondaire visible (pas de menu, pas de nav) — l'écran est pensé pour être lu à distance, mains occupées

### Liste de courses
- Regroupement strict par rayon, avec un intitulé de section coloré selon le rayon (sage = frais/légumes, apricot = épicerie, rouge alerte = à vérifier)
- Articles cochés : texte barré, opacité réduite, jamais supprimés de la liste visuellement
- Optimisée mobile en priorité (gros tap-targets, une main)

---

## 7. Ce qu'on évite

- Dégradés décoratifs génériques sans lien avec la palette (pas de violet/bleu SaaS)
- Ombres grises fortes et identiques sur tous les éléments (`rgba(0,0,0,.1)` partout) — préférer des ombres légères et cohérentes avec les surfaces `Paper`
- Labels tout-majuscules avec tracking large sur chaque titre
- Emojis comme substituts d'icônes dans l'UI finale (acceptés uniquement en placeholder de mockup, ex. 🍳 dans les premières maquettes)
- Ajout d'une troisième police ou d'une couleur hors palette sans mise à jour de ce document
