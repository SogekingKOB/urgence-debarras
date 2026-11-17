# Mettre le site en ligne : domaine chez OVH, site chez Cloudflare Pages

Ce guide est écrit pour être suivi seul, sans aide. Il compte **cinq parties** à faire dans l'ordre. Prévoir 1 h à 1 h 30 en tout. Les noms de boutons des sites OVH et Cloudflare changent parfois : suivre l'esprit des étapes.

**Ce qui est déjà prêt dans le dossier `dist/`** (c'est lui qu'on envoie à Cloudflare) :

| Fichier | Rôle |
|---|---|
| `_worker.js` | reçoit le formulaire (`/envoi`), le contrôle, envoie l'e-mail par la messagerie OVH (SMTP) |
| `_routes.json` | le worker ne s'occupe que de `/envoi` ; le reste du site est servi directement |
| `_headers` | sécurité et cache (remplace l'ancien `.htaccess`) |
| `_redirects` | redirections 301 depuis les anciennes adresses (`/contact`, `/tarifs`, `/qui-sommes-nous`…) |

Les mentions légales sont complètes (éditeur, SIRET, TVA, hébergeur Cloudflare). La page Confidentialité cite Cloudflare et OVH.

**Le principe retenu : le domaine et ses réglages DNS restent chez OVH.** On ne touche pas aux enregistrements de messagerie, donc `info@urgencesdebarras.fr` continue de fonctionner. On ajoute seulement une ligne pour que `www.urgencesdebarras.fr` pointe vers Cloudflare.

---

## Partie 1. Créer les comptes (15 min)

1. **Cloudflare** : créer un compte gratuit sur cloudflare.com. Aucune carte bancaire n'est nécessaire pour Pages.
2. **OVH** : rien à créer. Il faut seulement l'adresse e-mail offerte avec le domaine (par exemple `info@urgencesdebarras.fr`) et son mot de passe. Si elle n'existe pas encore : espace client OVH > Web Cloud > E-mails > la créer, puis vérifier qu'on peut s'y connecter (webmail OVH).

## Partie 2. Publier le site sur Cloudflare (15 min)

1. Dans Cloudflare : **Workers & Pages** > **Create** > onglet **Pages** > **Upload assets** (téléversement direct).
2. Nommer le projet, par exemple `urgences-debarras`. Cloudflare en déduit l'adresse de test `urgences-debarras.pages.dev` : **la noter**.
3. Envoyer le **contenu du dossier `dist/`** (glisser le dossier). Vérifier que `_worker.js`, `_headers`, `_redirects` et `_routes.json` sont bien envoyés, au même niveau que `index.html`.
4. Cliquer sur **Deploy**. Ouvrir l'adresse `…pages.dev` : le site doit s'afficher. Parcourir quelques pages.

## Partie 3. Brancher l'envoi des e-mails par la messagerie OVH (10 min)

Le formulaire envoie chaque demande **depuis** votre adresse OVH **vers** cette même adresse (ou une autre de votre choix). Aucun autre service n'est nécessaire.

1. Retrouver ces informations dans OVH (espace client > Web Cloud > E-mails > le domaine > l'adresse) :
   - **l'adresse e-mail** et **son mot de passe** ;
   - **le serveur sortant (SMTP)** : avec l'offre e-mail offerte (MX Plan) c'est `ssl0.ovh.net`, port **465**, connexion SSL/TLS. Avec Email Pro ou Exchange, le serveur est différent : il est indiqué dans OVH, rubrique « Configuration » de l'adresse.
2. Dans Cloudflare : le projet > **Settings** > **Variables and Secrets** > **Add** pour l'environnement **Production** :

   | Nom | Type | Valeur |
   |---|---|---|
   | `SMTP_USER` | Texte | l'adresse e-mail OVH, ex. `info@urgencesdebarras.fr` |
   | `SMTP_PASS` | Secret | le mot de passe de cette adresse |
   | `SMTP_HOST` | Texte | seulement si ce n'est pas `ssl0.ovh.net` (sinon ne pas créer cette ligne) |
   | `MAIL_TO` | Texte | seulement pour recevoir les demandes sur une autre adresse (sinon ne pas créer cette ligne) |

3. **Renvoyer `dist/`** (Deployments > **Create new deployment** > même envoi qu'en partie 2) : les variables ne s'appliquent qu'à partir du déploiement suivant.
4. **Essai réel** : sur l'adresse `…pages.dev/visite-gratuite/`, remplir et envoyer le formulaire avec ton propre téléphone et ton e-mail. Vérifier :
   - le message de confirmation apparaît ;
   - la demande arrive dans la boîte (regarder aussi les indésirables) ;
   - en cliquant « Répondre », la réponse part vers l'adresse saisie dans le formulaire.

   Si rien n'arrive : voir « En cas de problème » plus bas.

*Si l'adresse n'est pas hébergée chez OVH ou si OVH refuse la connexion* : tester d'abord la connexion SMTP avec un logiciel de messagerie (Thunderbird) en utilisant exactement les mêmes réglages. Si cela marche là, cela doit marcher ici.

## Partie 4. Faire pointer le domaine vers le site (15 min)

Avant : dans OVH > Zone DNS, **regarder les entrées existantes** pour `www` et pour la racine (`urgencesdebarras.fr`). Après le transfert, elles peuvent pointer vers l'ancien site ou vers un hébergement OVH. **Noter les MX** (messagerie) pour ne pas y toucher.

1. Dans Cloudflare : le projet > **Custom domains** > **Set up a custom domain** > saisir `www.urgencesdebarras.fr`. Cloudflare indique la cible à utiliser (ce sera `urgences-debarras.pages.dev`). S'il propose de transférer tout le DNS vers Cloudflare, ce n'est **pas obligatoire** : choisir la configuration avec une entrée CNAME.
2. Dans OVH > Zone DNS : **supprimer** les entrées `www` existantes de type A, AAAA ou CNAME, puis **ajouter une entrée CNAME** : sous-domaine `www`, cible `urgences-debarras.pages.dev.` (avec le point final si OVH le demande).
3. Attendre quelques minutes, puis ouvrir `https://www.urgencesdebarras.fr` : le site doit s'afficher en HTTPS. Le certificat est créé automatiquement par Cloudflare (parfois jusqu'à une heure).
4. **L'adresse sans www** : dans OVH > Noms de domaine > onglet **Redirection** > **Ajouter une redirection** : domaine `urgencesdebarras.fr`, type **visible permanente (301)**, cible `https://www.urgencesdebarras.fr`. Vérifier ensuite que `http://urgencesdebarras.fr` et, si possible, `https://urgencesdebarras.fr` arrivent bien sur le site avec www.
   - *Limite connue* : selon l'offre OVH, la redirection de la racine ne couvre pas toujours le HTTPS (un avertissement de certificat peut apparaître sur `https://urgencesdebarras.fr`). Si c'est le cas, la solution propre est de confier le DNS à Cloudflare (variante ci-dessous).

**Variante : tout le DNS chez Cloudflare** (si la redirection de la racine pose problème) : ajouter le domaine à Cloudflare, **recopier à l'identique chez Cloudflare toutes les entrées de la zone OVH** (surtout les MX et les TXT de la messagerie), puis remplacer les serveurs de noms dans OVH (Noms de domaine > Serveurs DNS). Ensuite, créer chez Cloudflare une règle de redirection (Rules > Redirect Rules) de la racine vers `https://www.urgencesdebarras.fr`. À ne faire qu'avec les entrées de messagerie bien recopiées : sinon les e-mails s'arrêtent.

## Partie 5. Vérifications finales (15 min)

- [ ] `https://www.urgencesdebarras.fr` s'affiche, avec le cadenas.
- [ ] Formulaire : un dernier envoi réel sur le vrai domaine, reçu dans `info@urgencesdebarras.fr`.
- [ ] Redirections des anciennes adresses : ouvrir `www.urgencesdebarras.fr/contact/`, `/tarifs/`, `/qui-sommes-nous/`, `/politique-de-confidentialite/`, `/retractation/`, `/parametres-des-cookies/`. Chacune doit arriver sur la bonne page du nouveau site.
- [ ] Mentions légales et Confidentialité : lues une fois, tout est exact.
- [ ] **Google Search Console** (search.google.com/search-console) : ajouter le domaine, valider par un enregistrement TXT à créer dans la zone DNS OVH, puis envoyer le sitemap `https://www.urgencesdebarras.fr/sitemap.xml` et demander l'inspection de l'accueil.
- [ ] **Fiche Google** : vérifier que le site indiqué est `https://www.urgencesdebarras.fr/`.
- [ ] Le téléphone de l'entreprise (06 65 30 14 90) et l'adresse (40 rue Jules Ferry, 29200 Brest) sont identiques sur le site et sur la fiche Google.

---

## En cas de problème

| Symptôme | Piste |
|---|---|
| Le formulaire affiche « L'envoi n'a pas abouti » | Dans Cloudflare : le projet > **Deployments** > **Functions** > journaux (logs). `SMTP_USER ou SMTP_PASS absent` : les variables manquent ou le site n'a pas été renvoyé après leur ajout (partie 3, étape 3). `535` : identifiant ou mot de passe refusé : vérifier le mot de passe dans le webmail OVH. `553` ou `550` : l'expéditeur n'est pas autorisé : `SMTP_USER` doit être l'adresse OVH qui se connecte. `délai dépassé` ou `connexion` : mauvais serveur SMTP (`SMTP_HOST`) : relire la configuration indiquée dans OVH. |
| Aucun e-mail reçu, mais le formulaire dit « envoyé » | Regarder les indésirables, puis le dossier « Envoyés » de l'adresse dans le webmail OVH, qui montre si le message est parti. |
| `https://www…` affiche une erreur de certificat | Attendre (jusqu'à une heure), puis vérifier que l'entrée CNAME `www` est bien celle indiquée par Cloudflare. |
| Une ancienne adresse donne une page introuvable | Ajouter une ligne dans `_redirects`, régénérer et renvoyer `dist/` (voir ci-dessous). |
| Les e-mails `info@…` ne sont plus reçus | Une entrée MX a été modifiée ou supprimée dans la zone DNS OVH : remettre celles d'origine (voir la sauvegarde notée en partie 4). |

## Mettre le site à jour plus tard

1. Modifier les textes dans `src/pages/` (un fichier par page) ou les informations dans `src/config.json`.
2. Dans le dossier `site`, lancer `python -I build.py` : cela régénère `dist/`.
3. Dans Cloudflare : le projet > **Deployments** > **Create new deployment** > envoyer le contenu de `dist/`.
4. En cas d'erreur, Cloudflare garde les déploiements précédents : on peut revenir à l'un d'eux en un clic (Deployments > les trois points > **Rollback**).

## Limites à connaître

- La messagerie OVH a ses propres limites d'envoi (largement suffisantes pour des demandes de visite) : en cas de doute, les consulter dans l'espace client OVH.
- L'ancien limiteur « 5 demandes par heure et par adresse » n'existe plus. Il reste le champ piège, le délai minimal de remplissage, et le blocage des messages pleins de liens.
- L'ancienne version Apache/PHP (`envoi.php`, `.htaccess`) est conservée dans `../hebergement-apache/`. Elle ne sert plus.
- Données encore à confirmer avec le dirigeant : délai d'intervention, horaires « ouvert 24h/24 » repris de la fiche Google.
