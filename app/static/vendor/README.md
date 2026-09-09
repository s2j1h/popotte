# Assets auto-hébergés

L'application ne fait **aucun appel réseau externe** : daisyUI, Tailwind, HTMX et les
polices sont servis depuis ce répertoire. C'est indispensable pour un usage purement
LAN, où le navigateur n'a pas forcément accès à Internet.

| Fichier | Version | Licence | Source |
|---|---|---|---|
| `daisyui.css` | 5.0.43 | MIT | `https://cdn.jsdelivr.net/npm/daisyui@5.0.43/daisyui.css` |
| `tailwindcss-browser.js` | 4.1.11 | MIT | `https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4.1.11/dist/index.global.js` |
| `htmx.min.js` | 2.0.4 | BSD 2-Clause | `https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js` |
| `fonts.css` + `fonts/*.woff2` | Fraunces v38, Work Sans v24 | SIL OFL 1.1 | Google Fonts (sous-ensembles `latin` et `latin-ext`) |

`tailwindcss-browser.js` génère les classes utilitaires directement dans le navigateur,
en observant le DOM : les fragments insérés par HTMX sont pris en compte automatiquement.
C'est ce qui permet de se passer de toute étape de build Node.

## Mise à jour

```bash
./scripts/update-vendor.sh
```

Le script re-télécharge les quatre dépendances aux versions indiquées en tête de
fichier. Après mise à jour, vérifier l'application à l'écran (le thème Popotte est
défini dans `static/css/popotte.css` via les variables de thème daisyUI, qui peuvent
changer d'une version majeure de daisyUI à l'autre).
