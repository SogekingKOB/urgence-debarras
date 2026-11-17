# Site Urgences Débarras Brest

Site statique de 25 pages (design « sobre » : fond crème, blocs chocolat, orange pour les actions), mis en place le 16/11/2026. L'ancienne version (kraft et bleu nuit) est conservée dans `../site-avant-sobre/`.

## Organisation

| Dossier / fichier | Rôle |
|---|---|
| `build.py` | Générateur : assemble les pages, le menu, le pied de page, les données structurées, le sitemap |
| `src/config.json` | Coordonnées, mentions légales, avis clients à afficher, numéro de version des fichiers |
| `src/pages/*.html` | Contenu de chaque page (bloc `meta` en tête : titre, description, FAQ…) |
| `src/static/` | CSS, JavaScript, police, images, `_worker.js` (formulaire), `_headers`, `_redirects`, `_routes.json` |
| `dist/` | **Le site prêt à mettre en ligne** (généré, ne pas modifier à la main) |

## Régénérer le site

```bash
python -I build.py
```

Après une modification du CSS ou du JavaScript, augmenter `asset_version` dans `src/config.json` pour que les navigateurs rechargent les fichiers.

## Avant la mise en ligne

1. **Mentions légales** : complètes (entrepreneur individuel Jessie Fauveau, SIRET, TVA, hébergeur Cloudflare). À relire une fois avant la mise en ligne.
2. **Formulaire et hébergement** : le site est prévu pour Cloudflare Pages (gratuit). `dist/_worker.js` envoie les demandes par la messagerie OVH (SMTP). Suivre pas à pas `DEPLOIEMENT.md` (domaine chez OVH, compte Cloudflare, variables SMTP OVH, essai réel d'envoi, DNS). L'ancienne version Apache/PHP est dans `../hebergement-apache/`.
3. **Avis clients** : pour afficher des avis sur le site, les recopier tels quels depuis la fiche Google dans `src/config.json` → `reviews` (`{"author": "Prénom N.", "text": "..."}`). Sans avis renseignés, le site affiche un lien vers la fiche Google.
4. **Confidentialité** : la page indique une conservation des demandes de trois ans au plus après le dernier échange. À respecter, ou à modifier dans `src/pages/91-confidentialite.html`.
5. **Mise en ligne** : envoyer le contenu de `dist/` à Cloudflare Pages (voir `DEPLOIEMENT.md`). Les en-têtes et les redirections sont dans `_headers` et `_redirects`.
6. **Google** : déclarer `https://www.urgencesdebarras.fr/sitemap.xml` dans la Search Console, et ajouter le lien du site sur la fiche Google Business Profile.

## Contenu : règles suivies

- Aucun prix affiché. Le message porte sur la valeur des biens revendables, déduite d'un devis ferme établi lors d'une visite gratuite faite avec le client.
- Circuit de revalorisation mis en avant sur toutes les pages : revente, dons à chaque chantier (Emmaüs, Le Triporteur, Un peu d'R), recyclage.
- Les associations sont présentées comme bénéficiaires de dons, jamais comme partenaires.
- Aucune affirmation non confirmée : pas d'ancienneté, pas de nombre d'avis, pas de délai d'intervention.
