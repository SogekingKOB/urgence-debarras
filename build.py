"""Générateur du site Urgences Débarras Brest.

Usage :  python -I build.py
Lit     :  src/config.json, src/pages/*.html, src/static/**
Écrit   :  dist/  (pages, sitemap.xml, robots.txt, llms.txt, assets)

Chaque page commence par un bloc <script type="application/json" id="meta"> … </script>
(chemin, titre, description, mise en page, photo, FAQ…), suivi de son contenu HTML.
Le contenu peut contenir des balises de composants, par exemple <!--@faq--> ou
<!--@gallery:grange-videe,garage-encombre-->, remplacées ici par le HTML commun.

Design « place nette » : blanc net, noir franc, bleu du logo, touches de jaune pour les actions.
Les animations passent par Framer Motion (src/static/assets/js/motion.js, API DOM) pilotée par site.js.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
DIST = ROOT / "dist"
TODAY = dt.date.today().isoformat()
TITLE_MAX = 60
DESC_RANGE = (110, 158)

CFG = json.loads((SRC / "config.json").read_text(encoding="utf-8"))
SITE = CFG["site"].rstrip("/")
TEL = CFG["phone"]
TEL_TXT = CFG["phone_display"]
VISIT_URL = "/visite-gratuite/"
ASSOCIATIONS = ["Emmaüs Brest", "Le Tri Porteur", "Un peu d'R"]

# Photos de chantier : texte alternatif, légende, précision (repris de la maquette)
PHOTOS = {
    "hangar-materiaux-encombrants": ("Amas de matériaux sous un hangar", "Hangar à évacuer", "Matériaux et encombrants"),
    "benne-bois-meubles": ("Benne remplie de bois et de meubles démontés", "Bois et meubles", "Benne complète"),
    "piece-cartons-meubles": ("Pièce encombrée de cartons et de meubles", "Cartons et meubles", "Avant tri"),
    "evacuation-escalier": ("Évacuation d'objets par l'escalier", "Sortie par l'escalier", "Étage sans ascenseur"),
    "gravats-platre": ("Pièce jonchée de plâtre et de gravats", "Gravats et plâtre", "Après travaux"),
    "piece-pierre-videe": ("Grande pièce en pierre vidée et balayée", "Pièce rendue propre", "Fin de chantier"),
    "garage-encombre": ("Garage encombré de caisses et d'objets", "Garage encombré", "Avant débarras"),
    "chargement-panneaux-benne": ("Chargement de panneaux dans une benne", "Chargement", "Panneaux et bois"),
    "grange-videe": ("Grange entièrement vidée", "Grange vidée", "Fin de chantier"),
    "sol-tomettes-degage": ("Pièce vide au sol en tomettes", "Sol dégagé", "Après nettoyage"),
    "materiaux-platre-evacuer": ("Matériaux et plâtre à évacuer", "Matériaux", "À évacuer"),
    "fourgon-meubles": ("Fourgon chargé de meubles débarrassés", "Fourgon chargé", "Petits volumes"),
}
SQUARE = 640  # toutes les photos de chantier font 640 × 640

# (adresse, nom, résumé, groupe) : « part » = particuliers, « pro » = professionnels
SITUATIONS = [
    ("/debarras-succession-brest/", "Succession, après un décès",
     "Vider la maison d'un proche, mettre de côté ce qui se garde, et laisser les lieux prêts pour le notaire ou la vente.", "part"),
    ("/debarras-ehpad-maison-de-retraite-brest/", "Départ en EHPAD ou maison de retraite",
     "Un parent entre en établissement : ce qui l'accompagne part avec lui, nous nous occupons du reste du logement.", "part"),
    ("/debarras-maison-appartement-brest/", "Vider un logement",
     "Déménagement, résidence secondaire, séparation, avant travaux : le logement vidé de fond en comble, puis balayé.", "part"),
    ("/debarras-fin-de-bail-vente-brest/", "Rendre les clés : fin de bail, vente",
     "Une date approche. Ce qui ne part pas avec vous, nous l'emportons, et le logement est rendu vide et propre.", "part"),
    ("/debarras-diogene-brest/", "Logement très encombré (Diogène)",
     "Accumulation importante, accès difficile. Nous intervenons sans jugement et en toute discrétion.", "part"),
    ("/debarras-insalubre-sinistre-brest/", "Logement insalubre, après un sinistre",
     "Incendie, dégât des eaux, logement dégradé : nous sortons tout ce qui doit l'être, puis les lieux sont rendus propres.", "part"),
    ("/debarras-ferme-grange-brest/", "Corps de ferme, grange, dépendances",
     "Longères, granges, hangars, ateliers : de grands volumes, du matériel ancien, et souvent de la valeur à déduire.", "part"),
    ("/debarras-cave-grenier-garage-brest/", "Cave, grenier, garage",
     "Encombrants, cartons, outillage, gravats : les pièces qu'on n'ouvre plus retrouvent de la place.", "part"),
    ("/debarras-proprietaire-bailleur-brest/", "Propriétaires bailleurs",
     "Locataire parti en laissant ses affaires, logement abandonné, après une expulsion : le bien remis en état de relouer.", "pro"),
    ("/debarras-local-professionnel-brest/", "Local professionnel",
     "Cessation d'activité, changement de locataire, bureaux, commerce ou entrepôt à libérer.", "pro"),
    ("/professionnels-notaires-agences-mandataires/", "Notaires, agences, mandataires",
     "Vous accompagnez un client, une succession ou une personne protégée : un seul interlocuteur pour vider le bien.", "pro"),
]
GROUPS = [("part", "Particuliers"), ("pro", "Propriétaires et professionnels")]

# Choix du formulaire de visite : doit rester identique à la constante MOTIFS de src/static/_worker.js
MOTIFS = ["Succession, après un décès", "Départ en EHPAD ou maison de retraite", "Maison ou appartement",
          "Fin de bail, état des lieux ou vente", "Diogène, logement très encombré",
          "Logement insalubre ou après un sinistre", "Corps de ferme, grange, dépendances",
          "Cave, grenier, garage", "Propriétaire bailleur", "Local professionnel",
          "Notaire, agence, mandataire", "Autre"]

NAV = [
    ("/#situations", "Situations"),
    ("/revalorisation-dons-associations/", "Revalorisation"),
    ("/comment-est-etabli-votre-devis/", "Votre devis"),
    ("/realisations/", "Réalisations"),
    ("/questions-frequentes/", "Questions"),
]
MORE_NAV = [
    ("/zone-intervention/", "Zone d'intervention"),
    ("/guides/encombrants-brest/", "Encombrants à Brest"),
    (VISIT_URL, "Visite gratuite"),
]

ZONES = [
    ("Pays de Brest", ["Brest", "Guipavas", "Plougastel-Daoulas", "Le Relecq-Kerhuon", "Guilers", "Gouesnou",
                       "Plouzané", "Saint-Renan", "Plabennec", "Landerneau"]),
    ("Nord et centre Finistère", ["Lesneven", "Lannilis", "Ploudalmézeau", "Landivisiau", "Morlaix",
                                  "Carhaix-Plouguer", "Châteaulin"]),
    ("Sud Finistère", ["Quimper", "Douarnenez", "Concarneau", "Quimperlé", "Pont-l'Abbé", "Crozon"]),
]

e = html.escape


# --------------------------------------------------------------------------- lecture des pages

META_RE = re.compile(r'<script type="application/json" id="meta">(.*?)</script>\s*', re.S)


def load_pages() -> list[dict]:
    pages = []
    for f in sorted((SRC / "pages").glob("*.html")):
        raw = f.read_text(encoding="utf-8")
        m = META_RE.search(raw)
        if not m:
            sys.exit(f"{f.name} : bloc meta manquant")
        meta = json.loads(m.group(1))
        meta["body"] = raw[m.end():]
        meta["file"] = f.name
        pages.append(meta)
    return pages


def check_meta(p: dict) -> list[str]:
    warn = []
    if len(p["title"]) > TITLE_MAX:
        warn.append(f"titre trop long ({len(p['title'])} car.)")
    lo, hi = DESC_RANGE
    if not lo <= len(p["description"]) <= hi:
        warn.append(f"description hors plage ({len(p['description'])} car.)")
    return warn


# --------------------------------------------------------------------------- composants

def img_tag(name: str, alt: str, w: int, h: int, lazy: bool = True, cls: str = "") -> str:
    loading = ' loading="lazy" decoding="async"' if lazy else ""
    c = f' class="{cls}"' if cls else ""
    return f'<img src="/assets/img/{name}.webp" alt="{e(alt)}" width="{w}" height="{h}"{loading}{c}>'


THUMB = 320  # vignettes « -s » générées pour les petits affichages


def gallery_img(name: str, alt: str, sizes: str) -> str:
    """Photo de galerie : vignette 320 px ou photo 640 px selon l'écran ; data-full sert à l'agrandissement."""
    full = f"/assets/img/{name}.webp"
    if not (SRC / "static" / "assets" / "img" / f"{name}-s.webp").exists():
        return img_tag(name, alt, SQUARE, SQUARE)
    return (f'<img src="{full}" srcset="/assets/img/{name}-s.webp {THUMB}w, {full} {SQUARE}w" sizes="{sizes}" '
            f'data-full="{full}" alt="{e(alt)}" width="{SQUARE}" height="{SQUARE}" loading="lazy" decoding="async">')


def c_gallery(arg: str) -> str:
    names, _, variant = arg.partition("|")
    keys = [n.strip() for n in names.split(",") if n.strip()] or list(PHOTOS)
    sizes = ("(min-width:640px) 31vw, 68vw" if variant == "g3"
             else "(min-width:1000px) 16vw, (min-width:640px) 31vw, 68vw")
    figs = []
    for k in keys:
        alt = PHOTOS[k][0]
        figs.append(f'<figure><button type="button" class="zbtn" aria-label="Agrandir la photo : {e(alt)}">'
                    f'{gallery_img(k, alt, sizes)}</button></figure>')
    swipe = '<p class="swipe">Faites glisser pour voir les photos.</p>'
    if variant == "track":
        # Bande horizontale : glisser à la souris ou au doigt, flèches, barre de progression
        arrows = "".join(
            f'<button type="button" data-dir="{d}" aria-label="{lab}">{icon(ic)}</button>'
            for d, lab, ic in (("-1", "Photos précédentes", "left"), ("1", "Photos suivantes", "arrow")))
        return (f'<div class="gwrap">{swipe}<div class="gal track">{"".join(figs)}</div>'
                f'<div class="gbar"><div class="gprog" aria-hidden="true"><i></i></div><div class="arrows">{arrows}</div></div></div>')
    cls = "gal g3" if variant == "g3" else "gal"
    return f'{swipe}<div class="{cls}">{"".join(figs)}</div>'


def c_beforeafter(_: str = "") -> str:
    """Avant / après : un curseur à glisser (le champ de saisie est invisible, il porte le clavier et le tactile)."""
    return (
        '<figure class="ba" style="--p:50%">'
        f'{img_tag("grange-avant", "Hangar ouvert encombré de débris, de matelas et de pneus avant l’intervention", 960, 720, cls="b")}'
        f'{img_tag("grange-apres", "Le même hangar entièrement vidé, au sol dégagé", 960, 720, cls="a")}'
        '<span class="tag l">Avant</span><span class="tag r">Après</span>'
        f'<span class="hd" aria-hidden="true"><span class="knob">{icon("drag")}</span></span>'
        '<input type="range" min="0" max="100" value="50" aria-label="Comparer avant et après">'
        '</figure><p class="cap">Un hangar vidé de tout ce qui l’encombrait, sol dégagé. Deux photos du même chantier : faites glisser le curseur.</p>'
    )


def c_bigquote(arg: str = "") -> str:
    """Citation plein cadre sur photo : « texte|auteur|photo ». Le texte doit être extrait tel quel d'un avis."""
    text, author, shot = (arg.split("|") + ["", "", ""])[:3]
    return ('<section class="big dk" aria-label="Avis d’un client">'
            f'<div class="bg" style="background-image:url(/assets/img/{e(shot)}.webp)"></div>'
            f'<div class="wrap"><blockquote data-rv>«&nbsp;{e(text)}&nbsp;»</blockquote>'
            f'<cite data-rv>{e(author)}, avis Google</cite></div></section>')


def c_reviews(_: str = "") -> str:
    items = []
    for r in CFG.get("reviews", []):
        items.append(
            f'<figure><p class="stars" aria-label="5 sur 5">★★★★★</p><blockquote>«&nbsp;{e(r["text"])}&nbsp;»</blockquote>'
            f'<cite>{e(r["author"])} · avis Google</cite></figure>'
        )
    if not items:
        items.append('<p class="say">Les avis de nos clients sont publiés sur notre fiche Google. '
                     'Vous pouvez les lire avant de nous appeler.</p>')
    link = f'<a class="lnk" href="{e(CFG["google_reviews_url"])}" rel="noopener">Lire nos avis sur Google</a>'
    return f'<div class="avis">{"".join(items)}{link}</div>'


def c_avisall(_: str = "") -> str:
    """Carrousel de tous les avis Google (bande à glisser, flèches, progression)."""
    revs = CFG.get("reviews_all", [])
    if not revs:
        return ""
    def card(r: dict) -> str:
        return (f'<figure class="rc"><p class="stars" aria-hidden="true">★★★★★</p>'
                f'<blockquote>«&nbsp;{e(r["text"])}&nbsp;»</blockquote>'
                f'<figcaption><span class="av" aria-hidden="true">{e(r["author"][0])}</span>{e(r["author"])}</figcaption></figure>')
    # Deux rangées qui défilent en sens inverse. Chaque avis n'est écrit qu'une fois dans le HTML :
    # site.js ajoute la copie (masquée aux lecteurs d'écran) qui boucle le défilement.
    half = (len(revs) + 1) // 2
    rows = "".join(
        f'<div class="mq-row{" rev" if n else ""}"><div class="mq-track">'
        f'{"".join(card(r) for r in part)}</div></div>'
        for n, part in enumerate((revs[:half], revs[half:])))
    gr = CFG.get("google_rating")
    rating_note = (f'<span class="mq-note">Note de {str(gr["value"]).replace(".", ",")} sur 5 · {gr["count"]} avis Google</span>'
                   if gr else "")
    return (f'<div class="marquee" role="region" aria-label="Avis Google de nos clients">{rows}</div>'
            f'<div class="mq-bar"><button type="button" class="mq-pause" aria-pressed="false">{icon("pause")}<span>Mettre en pause</span></button>'
            f'{rating_note}<a class="lnk" href="{e(CFG["google_reviews_url"])}" rel="noopener">Lire tous les avis sur Google</a></div>')


# Icônes au trait (24 × 24, couleur du texte), dessinées pour le site
ICONS = {
    "home": '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
    "heart": '<path d="M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.5-7 10-7 10z"/>',
    "users": '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.5 2.7-6 6-6s6 2.5 6 6"/><circle cx="17" cy="9" r="2.5"/><path d="M16.5 14.2c2.7.4 4.5 2.6 4.5 5.8"/>',
    "key": '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9"/><path d="M17 6l3 3"/><path d="M14 9l2 2"/>',
    "boxes": '<rect x="3" y="13" width="8" height="8"/><rect x="13" y="13" width="8" height="8"/><rect x="8" y="3" width="8" height="8"/>',
    "flame": '<path d="M12 3c1 3 5 5 5 10a5 5 0 0 1-10 0c0-2 1-3.2 2-4 0 2 1 3 2 3 0-3-1-5 1-9z"/>',
    "barn": '<path d="M3 21V10l9-6 9 6v11"/><path d="M9 21v-6h6v6"/><path d="M9 15l6 6"/><path d="M15 15l-6 6"/>',
    "garage": '<path d="M3 21V9l9-5 9 5v12"/><path d="M7 21v-8h10v8"/><path d="M7 16h10"/><path d="M7 18.5h10"/>',
    "building": '<rect x="5" y="3" width="14" height="18"/><path d="M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2"/><path d="M10 21v-3h4v3"/>',
    "briefcase": '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/><path d="M3 13h18"/>',
    "doc": '<path d="M6 3h9l4 4v14H6z"/><path d="M15 3v4h4"/><path d="M9 13h7"/><path d="M9 17h5"/>',
    "gift": '<rect x="3" y="9" width="18" height="4"/><path d="M5 13v8h14v-8"/><path d="M12 9v12"/><path d="M12 9c-2 0-4-1-4-3s3-2 4 3c1-5 4-5 4-3s-2 3-4 3"/>',
    "tag": '<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.5"/>',
    "recycle": '<path d="M4 12a8 8 0 0 1 14-5.3L20 9"/><path d="M20 4v5h-5"/><path d="M20 12a8 8 0 0 1-14 5.3L4 15"/><path d="M4 20v-5h5"/>',
    "arrow": '<path d="M5 12h14"/><path d="M13 6l6 6-6 6"/>',
    "sofa": '<path d="M5 11V8a3 3 0 0 1 3-3h8a3 3 0 0 1 3 3v3"/><path d="M3 12a2 2 0 0 1 4 0v2h10v-2a2 2 0 0 1 4 0v5H3z"/><path d="M6 17v2M18 17v2"/>',
    "dish": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/>',
    "tools": '<path d="M4 20l9-9"/><path d="M11 5l4-2 5 5-2 4-3-1-4-4z"/>',
    "rubble": '<rect x="3" y="5" width="18" height="14"/><path d="M3 12h18M9 5v7M15 12v7"/>',
    "leaf": '<path d="M5 19c0-8 5-14 15-14 0 10-6 15-14 15"/><path d="M5 19l8-8"/>',
    "flask": '<path d="M9 3h6"/><path d="M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/>',
    "gas": '<rect x="7" y="8" width="10" height="13" rx="3"/><path d="M10 8V5h4v3"/>',
    "warning": '<path d="M12 3l10 18H2z"/><path d="M12 10v5"/><path d="M12 18h.01"/>',
    "drop": '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
    "gem": '<path d="M6 4h12l4 5-10 12L2 9z"/><path d="M2 9h20"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "phone": '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/>',
    "cal": '<path d="M8 2v4M16 2v4M3 10h18"/><rect x="3" y="4" width="18" height="18" rx="2"/>',
    "mail": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 6l-10 7L2 6"/>',
    "pin": '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "left": '<path d="M19 12H5"/><path d="M11 18l-6-6 6-6"/>',
    "drag": '<path d="M9 6l-6 6 6 6"/><path d="M15 6l6 6-6 6"/>',
    "redo": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>',
    "pause": '<path d="M8 5v14M16 5v14"/>',
}


def icon(name: str, cls: str = "ico") -> str:
    """Icône décorative (masquée aux lecteurs d'écran : le texte voisin porte le sens)."""
    if name not in ICONS:
        sys.exit(f"icône inconnue « {name} »")
    return (f'<svg class="{cls}" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{ICONS[name]}</svg>')


def c_flow(_: str = "") -> str:
    """Schéma animé du circuit : logement → tri → revente, dons, recyclage."""
    def node(x: int, y: int, name: str, label: str, accent: bool = False) -> str:
        cls = "fnode acc" if accent else "fnode"
        # Les trois sorties sont empilées : leur libellé se place à droite du cercle, pas dessous
        text = (f'<text x="46" y="5">{e(label)}</text>' if accent
                else f'<text y="54" text-anchor="middle">{e(label)}</text>')
        return (f'<g class="{cls}" transform="translate({x} {y})"><circle r="30"/>'
                f'<g transform="translate(-12 -12)" fill="none" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>'
                f'{text}</g>')
    paths = ('<path class="fline" d="M100 130H390"/><path class="fline" d="M450 130H600C680 130 680 50 760 50H1000"/>'
             '<path class="fline" d="M450 130H1000"/><path class="fline" d="M450 130H600C680 130 680 210 760 210H1000"/>')
    return ('<div class="flow" data-rv><svg viewBox="0 0 1200 260" role="img" '
            'aria-label="Schéma du circuit : le logement est vidé, puis tout est trié. Ce qui se revend est déduit du devis, '
            'ce qui peut resservir est donné à des associations, le reste est recyclé.">'
            f'{paths}{node(70, 130, "home", "On vide tout")}{node(420, 130, "boxes", "On trie")}'
            f'{node(1030, 50, "tag", "Revente", True)}{node(1030, 130, "gift", "Dons", True)}{node(1030, 210, "recycle", "Recyclage", True)}'
            '</svg></div>')


def c_situations(_: str = "") -> str:
    """Situations en deux onglets (particuliers / professionnels), cartes compactes cliquables.
    Sans JavaScript, les deux listes s'affichent l'une sous l'autre avec leur titre."""
    tabs, panels = [], []
    for n, (key, label) in enumerate(GROUPS):
        first = n == 0
        tabs.append(f'<button type="button" role="tab" id="tab-{key}" aria-controls="panel-{key}" '
                    f'aria-selected="{"true" if first else "false"}"{"" if first else " tabindex=\"-1\""}>{e(label)}</button>')
        cards = "".join(
            f'<a class="scard" href="{path}"><b>{e(name)}</b><span>{e(txt)}</span>'
            f'<span class="go"><i>{icon("arrow")}</i>Voir la situation</span></a>'
            for path, name, txt, group in SITUATIONS if group == key)
        panels.append(f'<div class="tpanel" role="tabpanel" id="panel-{key}" aria-labelledby="tab-{key}">'
                      f'<p class="grp">{e(label)}</p><div class="sgrid rsc" tabindex="0" '
                      f'aria-label="{e(label)} : situations, défilement horizontal">{cards}</div></div>')
    # Bande horizontale : glisser au doigt ou à la souris, flèches, barre de progression (site.js)
    arrows = "".join(
        f'<button type="button" data-dir="{d}" aria-label="{lab}">{icon(ic)}</button>'
        for d, lab, ic in (("-1", "Situations précédentes", "left"), ("1", "Situations suivantes", "arrow")))
    return (f'<div class="tabs"><div class="tablist" role="tablist" aria-label="Votre profil">{"".join(tabs)}</div>'
            f'{"".join(panels)}<div class="gbar sbar"><div class="gprog" aria-hidden="true"><i></i></div>'
            f'<div class="arrows">{arrows}</div></div></div>'
            f'<p class="after-gal">Votre cas n\'est pas dans la liste ? <a class="lnk" href="tel:+33665301490">Appelez-nous au 06 65 30 14 90</a> '
            f'ou <a class="lnk" href="{VISIT_URL}">demandez une visite</a> : nous vous orienterons.</p>')


def c_circuit(arg: str = "") -> str:
    assos = ", ".join(ASSOCIATIONS[:-1]) + " et " + ASSOCIATIONS[-1]
    # Trois cartons scotchés : revente, dons, recyclage
    items = [("La revente", "Les meubles et objets revendables sont estimés avec vous lors de la visite. "
                            "Leur valeur est déduite de votre devis."),
             ("Les dons", f"À chaque chantier, ce qui peut resservir est donné à des associations : {assos}."),
             ("Le recyclage", "Ce qui ne peut être ni vendu ni donné est recyclé ou déposé en déchetterie.")]
    cols = ('<div class="boxes">' + "".join(
        f'<div class="carton"><span class="tape" aria-hidden="true"></span><h3>{e(t)}</h3><p>{e(d)}</p></div>'
        for t, d in items) + '</div>')
    if arg == "short":
        return cols
    if arg == "lead":
        # Accueil : les cartons, puis le bandeau « visite et estimation gratuites »
        return (cols + '<div class="lead" data-rv><b>Visite et estimation gratuites, devis ferme.</b>'
                f'<a class="btn" href="{VISIT_URL}">Demander une visite{icon("arrow")}</a></div>')
    link = '<p class="after-rows"><a class="lnk" href="/revalorisation-dons-associations/">Découvrir notre circuit de revalorisation</a></p>'
    return cols + link


def c_steps(_: str = "") -> str:
    steps = [
        ("Vous nous appelez", "Par téléphone ou par le formulaire. Dites-nous la commune, le type de bien et la situation."),
        ("Visite gratuite", "Nous venons sur place et faisons l'estimation avec vous. Ce qui se revend est déduit."),
        ("Devis ferme", "Vous recevez un devis dont le montant est fixé. Il reste le même après l'intervention."),
        ("On vide, on trie, on nettoie", "Tout est sorti, puis revendu, donné ou recyclé. Les lieux sont balayés et rendus propres."),
    ]
    lis = "".join(f'<li><span class="n" aria-hidden="true">{i}</span><h3>{e(t)}</h3><p>{e(p)}</p></li>'
                  for i, (t, p) in enumerate(steps, 1))
    return f'<ol class="steps">{lis}</ol>'


def c_yn(arg: str = "") -> str:
    """« Ce que nous emportons / à signaler » : listes avec une petite icône devant chaque ligne.
    Sans argument : les deux colonnes ; « yes » ou « tell » : une seule liste."""
    yes = [("sofa", "Meubles, literie, armoires, électroménager"), ("dish", "Vaisselle, linge, livres, bibelots"),
           ("boxes", "Cartons, papiers, jouets, vêtements"), ("tools", "Outillage, matériel informatique et électrique"),
           ("rubble", "Encombrants, gravats, matériaux de chantier"), ("leaf", "Déchets verts et ferraille")]
    tell = [("flask", "Produits chimiques, peintures, solvants"), ("gas", "Bouteilles de gaz et extincteurs"),
            ("warning", "Amiante ou matériaux suspects"), ("drop", "Cuves à fioul"),
            ("gem", "Objets de valeur ou papiers de famille à retrouver")]
    ul = lambda xs: "<ul>" + "".join(f"<li>{icon(i)}<span>{e(t)}</span></li>" for i, t in xs) + "</ul>"  # noqa: E731
    note = '<p class="note">Nous le prévoyons au devis : ces éléments suivent des filières particulières.</p>'
    if arg == "yes":
        cells = "".join(f"<div>{icon(i)}<span>{e(t)}</span></div>" for i, t in yes)
        return f'<div class="fgrid">{cells}</div>'
    if arg == "tell":
        return f'<div class="tell"><h3>À nous signaler à la visite</h3>{ul(tell)}{note}</div>'
    return (f'<div class="yn"><div><h3>Ce que nous emportons</h3>{ul(yes)}</div>'
            f'<div><h3>À nous signaler à la visite</h3>{ul(tell)}'
            '<p class="note">Nous le prévoyons au devis : ces éléments suivent des filières particulières.</p></div></div>')


def c_zone(_: str = "") -> str:
    blocks = "".join(f"<div><dt>{e(t)}</dt><dd>{e(', '.join(cs))}.</dd></div>" for t, cs in ZONES)
    return f'<dl class="cols">{blocks}</dl>'


def c_callout(arg: str = "") -> str:
    """Bandeau final bleu : grande phrase, appel, coordonnées à copier."""
    title = arg or "On passe, on estime avec vous. Le devis est ferme."
    addr = f'{CFG["street"]}, {CFG["postal"]} {CFG["city"]}'
    def row(ic: str, text: str, href: str, copy: bool) -> str:
        cp = f'<button type="button" class="cp" data-copy="{e(text)}">Copier</button>' if copy else ""
        return f'<div class="crow">{icon(ic)}<a href="{href}">{e(text)}</a>{cp}</div>'
    return (
        '<section class="final" id="contact" aria-label="Demander une visite"><div class="wrap">'
        f'<div class="fin-txt"><p class="kicker"><i></i>Une visite gratuite, chez vous</p><h2 class="big" data-rv>{e(title)}</h2>'
        f'<div class="cta"><a class="btn" href="tel:{TEL}">{icon("phone")}Appeler maintenant</a>'
        f'<a class="btn o" href="{VISIT_URL}">{icon("cal")}Demander une visite gratuite</a></div></div>'
        f'<div class="cbox">{row("phone", TEL_TXT, "tel:" + TEL, True)}{row("mail", CFG["email"], "mailto:" + CFG["email"], True)}'
        f'{row("pin", addr, CFG["google_reviews_url"], False)}</div>'
        '</div></section>'
    )


def c_side(current: str) -> str:
    links = "".join(
        f'<li><a href="{p}"{" aria-current=\"page\"" if p == current else ""}>{e(n)}</a></li>'
        for p, n, *_ in SITUATIONS)
    return (
        f'<aside><div class="side"><h2>Toutes les situations</h2><ul>{links}</ul>'
        '<div class="box"><p>Visite gratuite, estimation faite avec vous, devis ferme.</p>'
        f'<a class="btn" href="{VISIT_URL}">{icon("cal")}Demander une visite</a>'
        f'<a class="lnk" href="tel:{TEL}">{e(TEL_TXT)}</a></div></div></aside>'
    )


def c_faq(page: dict, all_pages: list[dict]) -> str:
    items = page.get("faq", [])
    return '<div class="faq">' + faq_items(items) + "</div>"


def faq_items(items: list, open_first: bool = False) -> str:
    out = []
    for i, (q, a) in enumerate(items):
        op = " open" if open_first and i == 0 else ""
        out.append(f"<details{op}><summary>{e(q)}</summary><p>{a}</p></details>")
    return "".join(out)


def c_faqall(page: dict, all_pages: list[dict]) -> str:
    seen, groups = set(page_q for page_q, _ in page.get("faq", [])), []
    for p in all_pages:
        if p is page or not p.get("faq") or p.get("noindex"):
            continue
        items = [(q, a) for q, a in p["faq"] if q not in seen]
        seen.update(q for q, _ in items)
        if items:
            groups.append(f'<h2 class="fgrp"><a class="lnk" href="{p["path"]}">{e(p.get("crumb") or p["h1_plain"])}</a></h2>'
                          + faq_items(items))
    return '<div class="faq">' + faq_items(page.get("faq", [])) + "".join(groups) + "</div>"


def c_form(_: str = "") -> str:
    motifs = MOTIFS
    opts = "".join(f"<option>{e(m)}</option>" for m in motifs)
    return f'''<div class="book">
  <aside class="book-side">
    <ul class="meta">
      <li><b>Visite gratuite</b>Nous venons voir sur place</li>
      <li><b>Estimation avec vous</b>Les biens revendables sont déduits</li>
      <li><b>Devis ferme</b>Montant fixé d'avance</li>
      <li><b>Finistère</b>Brest et tout le département</li>
    </ul>
    <p class="meta-note">Vous préférez parler de vive voix ?<br><a class="lnk" href="tel:{TEL}">{e(TEL_TXT)}</a></p>
  </aside>
  <div class="book-main">
    <form id="visiteForm" action="/envoi" method="post" novalidate>
      <div class="two-up">
        <label class="f">Prénom<input name="prenom" autocomplete="given-name" required maxlength="80"></label>
        <label class="f">Nom<input name="nom" autocomplete="family-name" required maxlength="80"></label>
      </div>
      <div class="two-up">
        <label class="f">Téléphone<input name="tel" type="tel" inputmode="tel" autocomplete="tel" placeholder="06 12 34 56 78" required maxlength="30"></label>
        <label class="f">E-mail <small>facultatif</small><input name="mail" type="email" inputmode="email" autocomplete="email" placeholder="prenom.nom@exemple.fr" maxlength="160"></label>
      </div>
      <label class="f">Votre situation
        <select name="motif" required><option value="">Choisissez une situation</option>{opts}</select>
      </label>
      <label class="f">Adresse du bien à visiter<input name="adresse" autocomplete="street-address" placeholder="Rue et commune" required maxlength="200"></label>
      <label class="f">Vos disponibilités pour la visite <small>facultatif</small><input name="dispo" placeholder="Ex. en semaine après 17 h, ou le samedi matin" maxlength="200"></label>
      <label class="f">Précisions <small>facultatif</small><textarea name="msg" placeholder="Ex. maison de 90 m² à vider avant la vente" maxlength="2000"></textarea></label>
      <label class="consent"><input type="checkbox" name="consent" value="1" required>
        <span>J’accepte que mes coordonnées servent à organiser la visite et le devis. <a href="/confidentialite/">En savoir plus</a></span></label>
      <div class="hp" aria-hidden="true"><label>Ne pas remplir<input name="site" tabindex="-1" autocomplete="off"></label></div>
      <input type="hidden" name="t" value="">
      <button class="btn" type="submit">Demander ma visite gratuite</button>
      <p class="state ko" id="ko" role="alert" tabindex="-1"></p>
    </form>
    <div class="state ok" id="ok" role="status" tabindex="-1"><span class="tick" aria-hidden="true">&#10003;</span><strong>Votre demande a bien été transmise</strong>Merci. Nous vous rappelons rapidement pour fixer la visite ensemble. Besoin d’aller plus vite ? Appelez-nous au <a href="tel:{TEL}">{e(TEL_TXT)}</a>.</div>
  </div>
</div>'''


def c_legal(_: str = "") -> str:
    L = CFG["legal"]
    rows = [
        ("Nom commercial", CFG["name"]),
        ("Raison sociale", L.get("raison_sociale")),
        ("Forme juridique", L.get("forme_juridique")),
        ("Capital social", L.get("capital")),
        ("SIRET", L.get("siret")),
        ("N° de TVA intracommunautaire", L.get("tva")),
        ("RCS ou RM", L.get("rcs")),
        ("Adresse", f'{CFG["street"]}, {CFG["postal"]} {CFG["city"]}'),
        ("Téléphone", TEL_TXT),
        ("E-mail", CFG["email"]),
        ("Directeur de la publication", L.get("directeur_publication")),
        ("Assurance responsabilité civile professionnelle", L.get("assurance")),
    ]
    host = [("Hébergeur", L.get("hebergeur")), ("Adresse de l’hébergeur", L.get("hebergeur_adresse"))]
    dl = lambda rs: "".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in rs if v)  # noqa: E731
    return (f'<h2>Éditeur du site</h2><dl class="cols c2">{dl(rows)}</dl>'
            + (f'<h2>Hébergement</h2><dl class="cols c2">{dl(host)}</dl>' if any(v for _, v in host) else ""))


def c_ticker(_: str = "") -> str:
    """Bandeau bleu qui défile sous le hero : nos engagements. site.js ajoute la copie qui boucle."""
    items = ["Visite gratuite", "Devis ferme", "Vidé et nettoyé", "Dons à chaque chantier", "Brest et tout le Finistère"]
    lis = "".join(f"<li>{e(t)}</li>" for t in items)
    return f'<div class="ticker" role="region" aria-label="Nos engagements"><ul class="tk">{lis}</ul></div>'


def c_bon(_: str = "") -> str:
    """Bon d'enlèvement : les lignes se cochent l'une après l'autre (site.js), tampon « Emporté » à la fin."""
    yes = ["Meubles, literie, armoires, électroménager", "Vaisselle, linge, livres, bibelots",
           "Cartons, papiers, jouets, vêtements", "Outillage, matériel informatique et électrique",
           "Encombrants, gravats, matériaux de chantier", "Déchets verts et ferraille"]
    lis = "".join(
        f'<li><span class="no" aria-hidden="true">{i:02d}</span><span>{e(t)}</span>'
        '<svg class="box" viewBox="0 0 28 28" aria-hidden="true" focusable="false">'
        '<path d="M6 14.5 L11.5 20 L22 8"/></svg></li>'
        for i, t in enumerate(yes, 1))
    return ('<div class="bon"><p class="bon-h"><span>Urgences Débarras · Brest</span><span>Bon d’enlèvement</span></p>'
            f'<ul aria-label="Ce que nous emportons">{lis}</ul><span class="stmp" aria-hidden="true">Emporté</span></div>')


MAP_DATA = json.loads((SRC / "data" / "finistere.json").read_text(encoding="utf-8"))
# Décalage des noms de villes sur la carte (x, y, ancrage)
MAP_LABELS = {"Brest": (-14, 6, "end"), "Landerneau": (12, 4, "start"), "Lesneven": (10, -6, "start"),
              "Lannilis": (-8, -12, "end"), "Ploudalmézeau": (-10, -4, "end"), "Saint-Renan": (-12, -6, "end"),
              "Plabennec": (8, -12, "start"), "Morlaix": (12, 4, "start"), "Landivisiau": (12, 4, "start"),
              "Carhaix-Plouguer": (-12, 4, "end"), "Châteaulin": (12, 4, "start"), "Crozon": (-12, 4, "end"),
              "Douarnenez": (-12, -6, "end"), "Quimper": (12, 4, "start"), "Pont-l'Abbé": (-12, 6, "end"),
              "Concarneau": (0, 24, "middle"), "Quimperlé": (-12, 22, "end")}


def c_map(_: str = "") -> str:
    """Carte du Finistère (contours IGN via france-geojson, simplifiés) : tout le département, villes desservies en bleu."""
    W, H = MAP_DATA["W"], MAP_DATA["H"]
    coms = "".join(
        f'<path class="com{" base" if n == "Brest" else ""}" d="{d}" style="transform-origin:{x}px {y}px"/>'
        for n, d, x, y in MAP_DATA["sel"])
    labels = []
    for n, _d, x, y in MAP_DATA["sel"]:
        if n not in MAP_LABELS:
            continue
        dx, dy, an = MAP_LABELS[n]
        base = n == "Brest"
        labels.append(f'<g class="lb"><circle cx="{x}" cy="{y}" r="{8 if base else 4.5}" class="dot{" base" if base else ""}"/>'
                      f'<text x="{x + dx}" y="{y + dy}" text-anchor="{an}" class="lbl{" big" if base else ""}">'
                      f'{"Brest, notre base" if base else e(n)}</text></g>')
    return ('<div class="map" data-map>'
            f'<svg viewBox="-30 -20 {W + 60} {H + 40}" role="img" aria-labelledby="map-t">'
            '<title id="map-t">Carte du Finistère : tout le département est couvert, les principales villes desservies sont en bleu.</title>'
            f'<path class="dep" d="{MAP_DATA["dep"]}"/>{coms}{"".join(labels)}</svg>'
            '<p class="legend"><span><i class="k1"></i>Tout le Finistère</span><span><i class="k2"></i>Principales villes desservies</span>'
            '<span><i class="k3"></i>Brest, notre base</span></p></div>')


COMPONENTS = {
    "gallery": c_gallery, "flow": c_flow, "beforeafter": c_beforeafter, "reviews": c_reviews, "situations": c_situations,
    "bigquote": c_bigquote, "avisall": c_avisall,
    "circuit": c_circuit, "steps": c_steps, "yn": c_yn, "zone": c_zone, "callout": c_callout,
    "form": c_form, "legal": c_legal, "ticker": c_ticker, "bon": c_bon, "map": c_map,
}
COMP_RE = re.compile(r"<!--@(\w+)(?::([^>]*?))?-->")


def expand(body: str, page: dict, pages: list[dict]) -> str:
    def repl(m: re.Match) -> str:
        name, arg = m.group(1), m.group(2) or ""
        if name == "faq":
            return c_faq(page, pages)
        if name == "faqall":
            return c_faqall(page, pages)
        if name == "side":
            return c_side(page["path"])
        if name not in COMPONENTS:
            sys.exit(f'{page["file"]} : composant inconnu « {name} »')
        return COMPONENTS[name](arg)
    return COMP_RE.sub(repl, body)


# --------------------------------------------------------------------------- en-tête, pied, hero

# Objets du hero d'accueil : (texte, gauche %, haut %). Ils tombent en tas puis sont évacués (site.js).
HERO_OBJECTS = [("Armoire", 2, 8), ("Cartons", 20, 4), ("Frigo", 40, 2), ("Matelas", 58, 5), ("Vélo", 78, 3),
                ("Bibelots", 90, 14), ("Outillage", 3, 30), ("Vaisselle", 88, 34), ("Livres", 1, 52), ("Gravats", 90, 56),
                ("Linge", 5, 74), ("Jouets", 86, 78), ("Ferraille", 16, 92), ("Électroménager", 34, 94), ("Buffet", 58, 92),
                ("Chaises", 74, 93), ("Bric-à-brac", 14, 16), ("Vieux journaux", 64, 18), ("Matériel de chantier", 44, 50),
                ("Tapis", 30, 40), ("Armoire à glace", 54, 64), ("Commode", 22, 62)]

def crumbs_list(p: dict) -> list[tuple[str, str]]:
    if p["path"] == "/":
        return []
    return [("/", "Accueil"), (p["path"], p.get("crumb") or p["h1_plain"])]


def c_crumbs(p: dict) -> str:
    cs = crumbs_list(p)
    if not cs:
        return ""
    lis = "".join(
        f'<li><a href="{u}">{e(n)}</a></li>' if i < len(cs) - 1 else f'<li aria-current="page">{e(n)}</li>'
        for i, (u, n) in enumerate(cs))
    return f'<nav class="crumbs" aria-label="Fil d’Ariane"><ol>{lis}</ol></nav>'


def header(p: dict) -> str:
    cur = p["path"]
    nav = "".join(f'<a href="{u}"{" aria-current=\"page\"" if u == cur else ""}>{e(n)}</a>' for u, n in NAV)
    sit = "".join(f'<li><a href="{u}"{" aria-current=\"page\"" if u == cur else ""}>{e(n)}</a></li>'
                  for u, n, *_ in SITUATIONS)
    rest = "".join(f'<li><a href="{u}"{" aria-current=\"page\"" if u == cur else ""}>{e(n)}</a></li>'
                   for u, n in NAV[1:] + MORE_NAV)
    return f'''<a class="skip" href="#contenu">Aller au contenu</a>
<header class="top" id="bar-top">
  <div class="wrap">
    <a class="brand" href="/"><img src="/assets/img/logo-urgences-debarras.webp" width="34" height="34" alt=""><span>Urgences Débarras</span></a>
    <nav class="nav" aria-label="Navigation principale">{nav}<span class="pill" aria-hidden="true"></span></nav>
    <div class="act">
      <a class="btn" href="tel:{TEL}">{icon("phone")}<span class="tel">{e(TEL_TXT)}</span><span class="sr">Appeler</span></a>
      <button class="menu-btn" id="menu-btn" type="button" aria-expanded="false" aria-controls="mnav" aria-label="Ouvrir le menu"><span></span></button>
    </div>
  </div>
  <div class="prog" id="prog" aria-hidden="true"></div>
</header>
<div class="mnav" id="mnav" hidden><div class="wrap"><ul>
  <li><a href="/">Accueil</a></li>
  <li><details><summary>Situations</summary><ul class="subs">{sit}</ul></details></li>{rest}
</ul></div></div>'''


def footer() -> str:
    svc = "".join(f'<li><a href="{u}">{e(n)}</a></li>' for u, n in [
        ("/revalorisation-dons-associations/", "Revalorisation et dons"),
        ("/comment-est-etabli-votre-devis/", "Comment est établi votre devis"),
        ("/realisations/", "Réalisations"),
        ("/zone-intervention/", "Zone d'intervention"),
        ("/questions-frequentes/", "Questions fréquentes"),
        (VISIT_URL, "Demander une visite gratuite"),
    ])
    guides = "".join(f'<li><a href="{u}">{e(n)}</a></li>' for u, n in [
        ("/guides/encombrants-brest/", "Encombrants à Brest"),
        ("/guides/vider-maison-apres-deces-brest/", "Vider la maison après un décès"),
        ("/guides/visite-gratuite-debarras-brest/", "Comment se passe la visite"),
        ("/guides/donner-meubles-emmaus-recyclerie-brest/", "Donner meubles et objets"),
    ])
    year = dt.date.today().year
    assos = ", ".join(ASSOCIATIONS[:-1]) + " et " + ASSOCIATIONS[-1]
    siret = CFG["legal"].get("siret")
    ei = f' · {e(CFG["legal"]["directeur_publication"])}, entrepreneur individuel · SIRET {e(siret)}' if siret else ""
    return f'''<footer class="site">
  <div class="wrap">
    <div class="foot">
      <div>
        <p class="fbrand"><img src="/assets/img/logo-urgences-debarras.webp" width="34" height="34" alt="" loading="lazy">{e(CFG["name"])}</p>
        <p>{e(CFG["street"])}, {e(CFG["postal"])} {e(CFG["city"])}<br><a class="tel" href="tel:{TEL}">{e(TEL_TXT)}</a> · <a href="mailto:{e(CFG["email"])}">{e(CFG["email"])}</a></p>
        <p class="note">Nous donnons à chaque chantier à {e(assos)}.</p>
      </div>
      <ul>{svc}</ul>
      <ul>{guides}</ul>
    </div>
    <p class="legal"><span>© {year} {e(CFG["name"])}{ei}</span><span>Mis à jour le {dt.date.today().strftime("%d/%m/%Y")}</span><a href="/mentions-legales/">Mentions légales</a><a href="/confidentialite/">Confidentialité</a></p>
  </div>
</footer>
<div class="bar" id="bar">
  <a class="btn" href="tel:{TEL}">{icon("phone")}Appeler</a>
  <a class="btn o" href="{VISIT_URL}">{icon("cal")}Visite gratuite</a>
</div>
<dialog class="zoom" id="zoom" aria-label="Photo agrandie"><img alt=""></dialog>'''


def title_lines(h1: str) -> str:
    """Le titre est découpé à chaque <br> : une ligne par bloc (voir .hero h1 .l dans site.css)."""
    return "".join(f'<span class="l">{line}</span>' for line in h1.split("<br>"))


def hero_photo(p: dict, lazy: bool = False) -> str:
    """Photo d'en-tête encadrée : version allégée « -m » sur mobile quand elle existe."""
    shot = p.get("shot", "equipe-benne-debarras-brest")
    alt = e(p.get("shot_alt", "Chantier de débarras Urgences Débarras"))
    full = f"/assets/img/{shot}.webp"
    w, h = webp_size(SRC / "static" / "assets" / "img" / f"{shot}.webp")
    srcset = (f' srcset="/assets/img/{shot}-m.webp 600w, {full} {w}w" sizes="(min-width:960px) 420px, 92vw"'
              if mobile_shot(shot) else "")
    load = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high"'
    return f'<img src="{full}"{srcset} alt="{alt}" width="{w}" height="{h}"{load}>'


def hero(p: dict) -> str:
    layout = p.get("layout", "hero")
    sub = f'<p class="sub">{p["sub"]}</p>' if p.get("sub") else ""
    h1 = title_lines(p["h1"])
    if layout == "plain":
        return (f'<section class="phead"><div class="wrap txt">{c_crumbs(p)}<h1>{h1}</h1>'
                f'{sub.replace("class=\"sub\"", "class=\"lede\"")}</div></section>')
    if p["path"] == "/":
        # Accueil : le tas d'objets se vide tout seul, puis « Place nette. » se surligne
        objs = "".join(f'<span class="obj" style="left:{x}%;top:{y}%">{e(t)}</span>' for t, x, y in HERO_OBJECTS)
        gr = CFG.get("google_rating")
        rating = (f'<a class="rating" href="{e(CFG["google_reviews_url"])}" rel="noopener"><span class="stars" aria-hidden="true">★★★★★</span>'
                  f'<b>{str(gr["value"]).replace(".", ",")} sur Google</b>Avis de nos clients</a>' if gr else "")
        return f'''<section class="hero home" id="haut">
  <div class="pile" aria-hidden="true">{objs}</div>
  <div class="wrap hero-in">
    <div class="txt">
      <p class="kicker"><i></i>Débarras et nettoyage · Brest et Finistère</p>
      <h1>{h1}</h1>{sub}
      <div class="cta"><a class="btn" href="{VISIT_URL}">{icon("cal")}Demander une visite gratuite</a><a class="btn o" href="tel:{TEL}">{icon("phone")}<span class="tel">{e(TEL_TXT)}</span></a></div>
      <button type="button" class="replay" hidden>{icon("redo")}Revoir le débarras</button>
    </div>
    <div class="frame">
      <div class="ph">{hero_photo(p)}</div>
      <p class="stamp">Visite gratuite<small>Devis ferme, établi avec vous</small></p>
      {rating}
    </div>
  </div>
</section>'''
    return f'''<section class="hero sub-page">
  <div class="wrap hero-in">
    <div class="txt">{c_crumbs(p)}
      <h1>{h1}</h1>{sub}
      <div class="cta"><a class="btn" href="{VISIT_URL}">{icon("cal")}Demander une visite gratuite</a><a class="btn o" href="tel:{TEL}">{icon("phone")}<span class="tel">{e(TEL_TXT)}</span></a></div>
    </div>
    <div class="frame"><div class="ph">{hero_photo(p)}</div></div>
  </div>
</section>'''


# --------------------------------------------------------------------------- données structurées

def business() -> dict:
    lat, lng = CFG["geo"]
    biz = {
        "@type": "LocalBusiness",
        "@id": f"{SITE}/#entreprise",
        "name": CFG["name"],
        "description": ("Débarras et nettoyage de maisons, appartements, caves, greniers, garages et locaux "
                        "professionnels à Brest et dans le Finistère. Visite gratuite, devis ferme, "
                        "valeur des biens revendables déduite, dons aux associations à chaque chantier."),
        "url": f"{SITE}/",
        "telephone": TEL,
        "email": CFG["email"],
        "logo": f"{SITE}/assets/img/logo-urgences-debarras.webp",
        "image": f"{SITE}/assets/img/equipe-benne-debarras-brest.webp",
        "address": {"@type": "PostalAddress", "streetAddress": CFG["street"], "postalCode": CFG["postal"],
                    "addressLocality": CFG["city"], "addressRegion": "Bretagne", "addressCountry": "FR"},
        "geo": {"@type": "GeoCoordinates", "latitude": lat, "longitude": lng},
        "areaServed": [{"@type": "City", "name": c} for _, cs in ZONES for c in cs],
        "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Prestations de débarras", "itemListElement": [
            {"@type": "Offer", "itemOffered": {"@type": "Service", "name": n, "url": f"{SITE}{u}"}}
            for u, n, *_ in SITUATIONS]},
    }
    # Pas d'aggregateRating : Google ignore les notes qu'une entreprise locale déclare sur son propre site
    # (avis « auto-attribués »). La note reste visible sur la page, les étoiles de recherche viennent de la fiche Google.
    if CFG.get("same_as"):
        biz["sameAs"] = CFG["same_as"]
    if CFG.get("founded"):
        biz["foundingDate"] = CFG["founded"]
    if CFG.get("founder"):
        biz["founder"] = {"@type": "Person", "name": CFG["founder"]}
    biz["openingHoursSpecification"] = [{
        "@type": "OpeningHoursSpecification", "opens": "00:00", "closes": "23:59",
        "dayOfWeek": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]}]
    if CFG["legal"].get("siret"):
        biz["identifier"] = {"@type": "PropertyValue", "propertyID": "SIRET", "value": CFG["legal"]["siret"]}
    return biz


def schema(p: dict) -> str:
    url = f'{SITE}{p["path"]}'
    graph = [
        {"@type": "WebSite", "@id": f"{SITE}/#site", "url": f"{SITE}/", "name": CFG["name"], "inLanguage": "fr-FR",
         "publisher": {"@id": f"{SITE}/#entreprise"}},
        business(),
        {"@type": "WebPage", "@id": f"{url}#page", "url": url, "name": p["title"], "description": p["description"],
         "dateModified": TODAY, "isPartOf": {"@id": f"{SITE}/#site"}, "about": {"@id": f"{SITE}/#entreprise"}, "inLanguage": "fr-FR"},
    ]
    cs = crumbs_list(p)
    if cs:
        graph.append({"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": f"{SITE}{u}"} for i, (u, n) in enumerate(cs)]})
    if p.get("service"):
        graph.append({"@type": "Service", "name": p["service"], "serviceType": "Débarras",
                      "url": url, "provider": {"@id": f"{SITE}/#entreprise"},
                      "areaServed": {"@type": "AdministrativeArea", "name": "Finistère"}})
    if p.get("faq"):
        graph.append({"@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": strip_tags(a)}}
            for q, a in p["faq"]]})
    data = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1)
    return '<script type="application/ld+json">' + data.replace("</", "<\\/") + "</script>"


_CSS_CACHE: list[str] = []


def inline_css() -> str:
    """Feuille de style compactée, intégrée dans chaque page pour éviter une requête bloquante."""
    if not _CSS_CACHE:
        css = (SRC / "static" / "assets" / "css" / "site.css").read_text(encoding="utf-8")
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        css = re.sub(r"\s+", " ", css)
        css = re.sub(r"\s*([{};,>])\s*", r"\1", css)
        css = css.replace(";}", "}").strip()
        if "</" in css:
            sys.exit("site.css contient « </ » : impossible de l'intégrer dans une balise <style>")
        _CSS_CACHE.append(css)
    return _CSS_CACHE[0]


def webp_size(path: Path) -> tuple[int, int]:
    """Largeur et hauteur d'une image WebP, lues dans son en-tête (VP8, VP8L ou VP8X)."""
    d = path.read_bytes()[:30]
    kind = d[12:16]
    if kind == b"VP8X":
        return 1 + int.from_bytes(d[24:27], "little"), 1 + int.from_bytes(d[27:30], "little")
    if kind == b"VP8L":
        b = int.from_bytes(d[21:25], "little")
        return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
    return int.from_bytes(d[26:28], "little") & 0x3FFF, int.from_bytes(d[28:30], "little") & 0x3FFF


def mobile_shot(shot: str) -> bool:
    """Une version allégée « -m » existe-t-elle pour les petits écrans ?"""
    return (SRC / "static" / "assets" / "img" / f"{shot}-m.webp").exists()


def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s))


# --------------------------------------------------------------------------- page complète

def head(p: dict) -> str:
    url = f'{SITE}{p["path"]}'
    robots = "noindex, follow" if p.get("noindex") else "index, follow, max-image-preview:large"
    # Pas d'adresse de référence pour les pages non indexées (404, merci) : elles n'ont pas d'URL publique propre
    canonical = "" if p.get("noindex") else f'<link rel="canonical" href="{url}">\n'
    og_url = "" if p.get("noindex") else f'<meta property="og:url" content="{url}">\n'
    og_img = f"{SITE}/assets/img/{p.get('og', 'equipe-benne-debarras-brest')}.webp"
    return f'''<!DOCTYPE html>
<html lang="fr" class="no-js">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(p["title"])}</title>
<meta name="description" content="{e(p["description"])}">
{canonical}<meta name="robots" content="{robots}">
<meta name="theme-color" content="#fbfbf8">
<meta name="geo.region" content="FR-29">
<meta name="geo.placename" content="Brest">
<meta property="og:type" content="website">
<meta property="og:locale" content="fr_FR">
<meta property="og:site_name" content="{e(CFG["name"])}">
<meta property="og:title" content="{e(p["title"])}">
<meta property="og:description" content="{e(p["description"])}">
{og_url}<meta property="og:image" content="{og_img}">
<meta property="og:image:alt" content="L’équipe d’Urgences Débarras devant une benne chargée">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(p["title"])}">
<meta name="twitter:description" content="{e(p["description"])}">
<meta name="twitter:image" content="{og_img}">
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/assets/img/logo-urgences-debarras.webp" type="image/webp">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="preload" href="/assets/fonts/bricolage-grotesque.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fonts/instrument-sans.woff2" as="font" type="font/woff2" crossorigin>
<style>{inline_css()}</style>
<script src="/assets/js/motion.js?v={CFG["asset_version"]}" defer></script>
<script src="/assets/js/site.js?v={CFG["asset_version"]}" defer></script>
{schema(p)}
</head>'''


def render(p: dict, pages: list[dict]) -> str:
    body = expand(p["body"], p, pages)
    return (f'{head(p)}\n<body>\n{header(p)}\n<main id="contenu">\n{hero(p)}\n{body}\n</main>\n'
            f'{footer()}\n</body>\n</html>\n')


# --------------------------------------------------------------------------- fichiers annexes

SITEMAP_SKIP = {"/mentions-legales/", "/confidentialite/"}  # pages obligatoires, sans valeur de recherche


def sitemap(pages: list[dict]) -> str:
    urls = []
    for p in pages:
        if p.get("noindex") or p["path"].endswith(".html") or p["path"] in SITEMAP_SKIP:
            continue
        urls.append(f'<url><loc>{SITE}{p["path"]}</loc><lastmod>{TODAY}</lastmod>'
                    f'<priority>{p.get("priority", "0.7")}</priority></url>')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n")


def robots() -> str:
    return f"User-agent: *\nAllow: /\nDisallow: /envoi\nDisallow: /merci/\n\nSitemap: {SITE}/sitemap.xml\n"


def llms(pages: list[dict]) -> str:
    lines = [f"# {CFG['name']}", "",
             "> Débarras et nettoyage de maisons, appartements, caves, greniers, garages et locaux professionnels "
             "à Brest et dans le Finistère. Visite gratuite, estimation faite avec le client, devis ferme. "
             "La valeur des biens revendables est déduite du devis. À chaque chantier, ce qui peut resservir est "
             f"donné à des associations ({', '.join(ASSOCIATIONS)}).", "",
             f"Téléphone : {TEL_TXT} · E-mail : {CFG['email']} · Adresse : {CFG['street']}, {CFG['postal']} {CFG['city']}",
             "", "## Pages", ""]
    for p in pages:
        if p.get("noindex") or p["path"].endswith(".html") or p["path"] in SITEMAP_SKIP:
            continue
        lines.append(f"- [{p['title']}]({SITE}{p['path']}) : {p['description']}")
    return "\n".join(lines) + "\n"


def out_path(p: dict) -> Path:
    if p["path"].endswith(".html"):
        return DIST / p["path"].lstrip("/")
    return DIST / p["path"].strip("/") / "index.html"


def motifs_mismatch() -> bool:
    """Vrai si la liste des situations du formulaire diffère de celle acceptée par _worker.js."""
    js = (SRC / "static" / "_worker.js").read_text(encoding="utf-8")
    block = re.search(r"const MOTIFS = \[(.*?)\];", js, re.S)
    worker_motifs = re.findall(r"'((?:[^'\\]|\\.)*)'", block.group(1)) if block else []
    return worker_motifs != MOTIFS


def legal_warnings() -> list[str]:
    needed = ["raison_sociale", "forme_juridique", "siret", "directeur_publication", "hebergeur"]
    return [k for k in needed if not CFG["legal"].get(k)]


def main() -> None:
    pages = load_pages()
    for p in pages:
        p["h1_plain"] = strip_tags(p["h1"].replace("<br>", " "))
    # On vide dist/ sans supprimer le dossier lui-même (il peut être ouvert par un serveur d'aperçu)
    DIST.mkdir(exist_ok=True)
    for child in DIST.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    shutil.copytree(SRC / "static", DIST, dirs_exist_ok=True)
    problems = 0
    for p in pages:
        dest = out_path(p)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(render(p, pages), encoding="utf-8")
        for w in check_meta(p):
            problems += 1
            print(f"  ! {p['path']} : {w}")
    (DIST / "sitemap.xml").write_text(sitemap(pages), encoding="utf-8")
    (DIST / "robots.txt").write_text(robots(), encoding="utf-8")
    (DIST / "llms.txt").write_text(llms(pages), encoding="utf-8")
    if motifs_mismatch():
        print("  ! Les situations du formulaire diffèrent entre build.py et _worker.js : les demandes seraient refusées.")
    missing = legal_warnings()
    print(f"{len(pages)} pages générées dans dist/ ({problems} avertissement(s) de balises).")
    if missing:
        print("  ! Mentions légales incomplètes dans src/config.json : " + ", ".join(missing))


if __name__ == "__main__":
    main()
