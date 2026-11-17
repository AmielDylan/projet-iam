---
name: DigiRemed
description: L'ordonnance vérifiée pendant que vous l'écrivez. Feuilles blanches sur vert d'eau, un seul vert d'action.
colors:
  ground: "#E6EEEA"
  canvas: "#F0F5F2"
  mint: "#EEF4F1"
  mint-2: "#DCEBE3"
  mint-pill-end: "#CFE7DA"
  panel: "#FFFFFF"
  field: "#F1F6F3"
  rule: "#D9E3DE"
  line: "#D6DBD7"
  line-soft: "#E6E9E6"
  ink: "#15191E"
  ink-2: "#4E5761"
  ink-3: "#5B646C"
  placeholder: "#5F6A72"
  act: "#0B7A55"
  act-hover: "#08603F"
  act-tint: "rgba(11, 122, 85, .08)"
  act-tint-2: "rgba(11, 122, 85, .16)"
  ci: "#B42318"
  ci-bg: "#FCEBE9"
  ci-line: "#F2C4BF"
  asdec: "#B54708"
  asdec-bg: "#FDF0E3"
  asdec-line: "#F3D2B0"
  pe: "#8A6A00"
  pe-bg: "#FBF4DC"
  apec: "#4E5761"
  apec-bg: "#EEF0F1"
  rx-ink: "#111111"
  rx-muted: "#4a4f55"
  rx-soft: "#f1f3f1"
  rx-rule: "#b9bfbb"
typography:
  display:
    fontFamily: "'Host Grotesk', 'Atkinson Hyperlegible Next', system-ui, sans-serif"
    fontSize: "clamp(40px, 4.7vw, 68px)"
    fontWeight: 400
    lineHeight: 1.0
    letterSpacing: "-0.035em"
  numeral:
    fontFamily: "'Host Grotesk', 'Atkinson Hyperlegible Next', system-ui, sans-serif"
    fontSize: "clamp(76px, 8.6vw, 132px)"
    fontWeight: 300
    lineHeight: 0.85
    letterSpacing: "-0.055em"
  headline:
    fontFamily: "'Host Grotesk', 'Atkinson Hyperlegible Next', system-ui, sans-serif"
    fontSize: "clamp(30px, 3.2vw, 44px)"
    fontWeight: 400
    lineHeight: 1.08
    letterSpacing: "-0.025em"
  title:
    fontFamily: "'Host Grotesk', 'Atkinson Hyperlegible Next', system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 400
    letterSpacing: "-0.02em"
  title-workspace:
    fontFamily: "'Host Grotesk', 'Atkinson Hyperlegible Next', system-ui, sans-serif"
    fontSize: "26px"
    fontWeight: 500
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  body-public:
    fontFamily: "'Atkinson Hyperlegible Next', 'Atkinson Hyperlegible', system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.55
  body:
    fontFamily: "'Atkinson Hyperlegible Next', 'Atkinson Hyperlegible', system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.45
    fontFeature: "tnum"
  label:
    fontFamily: "'Atkinson Hyperlegible Next', 'Atkinson Hyperlegible', system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 600
  level:
    fontFamily: "'Atkinson Hyperlegible Next', 'Atkinson Hyperlegible', system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    letterSpacing: "0.02em"
rounded:
  level: "5px"
  step: "6px"
  ctl: "10px"
  panel: "18px"
  card: "22px"
  photo: "28px"
  sheet-l: "32px"
  pill: "999px"
spacing:
  gutter: "12px"
  card: "20px"
  panel: "40px"
  panel-mobile: "26px 20px"
  ctl: "36px"
  ctl-touch: "44px"
  ctl-large: "46px"
components:
  button-primary:
    backgroundColor: "{colors.act}"
    textColor: "{colors.panel}"
    rounded: "{rounded.pill}"
    padding: "0 16px"
    height: "{spacing.ctl}"
  button-primary-hover:
    backgroundColor: "{colors.act-hover}"
  button-check:
    backgroundColor: "{colors.act}"
    textColor: "{colors.panel}"
    rounded: "{rounded.pill}"
    padding: "0 22px"
    height: "{spacing.ctl-large}"
  button-mint:
    backgroundColor: "{colors.mint-pill-end}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "14px 26px"
  button-dark:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.panel}"
    rounded: "{rounded.pill}"
    padding: "14px 26px"
  button-default:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 16px"
    height: "{spacing.ctl}"
  button-soft:
    backgroundColor: "{colors.act-tint}"
    textColor: "{colors.act}"
    rounded: "{rounded.pill}"
    padding: "0 16px"
    height: "{spacing.ctl}"
  button-ghost:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.pill}"
    padding: "0 16px"
    height: "{spacing.ctl}"
  link-quiet:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.pill}"
    padding: "12px 18px"
  input-public:
    backgroundColor: "{colors.mint}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 16px"
    height: "{spacing.ctl-large}"
  input-field:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink}"
    rounded: "{rounded.ctl}"
    padding: "0 12px"
    height: "40px"
  nav-pill:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.pill}"
    padding: "5px"
  nav-pill-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.panel}"
    rounded: "{rounded.pill}"
  verify-card:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.card}"
    padding: "{spacing.card}"
    width: "380px"
  mint-panel:
    backgroundColor: "{colors.mint}"
    rounded: "{rounded.photo}"
    padding: "{spacing.panel}"
  card:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.panel}"
    padding: "22px"
  level-ci:
    backgroundColor: "{colors.ci-bg}"
    textColor: "{colors.ci}"
    typography: "{typography.level}"
    rounded: "{rounded.level}"
    height: "22px"
  level-asdec:
    backgroundColor: "{colors.asdec-bg}"
    textColor: "{colors.asdec}"
    typography: "{typography.level}"
    rounded: "{rounded.level}"
    height: "22px"
  level-pe:
    backgroundColor: "{colors.pe-bg}"
    textColor: "{colors.pe}"
    typography: "{typography.level}"
    rounded: "{rounded.level}"
    height: "22px"
  level-apec:
    backgroundColor: "{colors.apec-bg}"
    textColor: "{colors.apec}"
    typography: "{typography.level}"
    rounded: "{rounded.level}"
    height: "22px"
---

# Design System: DigiRemed

## Overview

**Creative North Star: "La feuille sur la table de consultation"**

DigiRemed se présente comme une table de travail calme : de grandes feuilles blanches aux coins généreux posées sur un fond vert d'eau pâle, des panneaux intérieurs vert d'eau, une encre presque noire. Le public ne voit pas un site marketing puis un outil ; il voit la consultation elle-même, une grande photo de prescription dans laquelle la vérification d'interaction fonctionne déjà. L'espace prescripteur, la connexion et l'inscription reprennent le même vocabulaire : pilules, titres en Host Grotesk, onglet actif en noir.

La couleur est un signal, jamais un décor. Un seul vert, le vert pharmacie, porte l'action principale de chaque écran (Vérifier, Se connecter, Nouvelle ordonnance). Les couleurs ANSM n'existent que sur les étiquettes et blocs d'alerte. Tout le reste se joue en vert d'eau, blanc et encre. La densité est double : aérée sur l'accueil public (texte à 17px, panneaux à 40px de marge intérieure), resserrée dans l'espace de rédaction (texte à 15px, contrôles de 36px).

La feuille d'ordonnance imprimée a son propre système (sheet.css), en millimètres et en points, noir sur blanc, et ne suit pas le langage de l'écran : ce qui s'affiche dans l'aperçu est exactement ce qui s'imprime.

Les photos actuelles sont des photos libres (Unsplash, Pexels) en attente des photos réelles de DigiRemed ; leur source et leur licence sont listées dans `static/img/accueil/PROVENANCE.md`. Chaque photo n'apparaît qu'une fois sur le site.

**Key Characteristics:**
- Feuilles blanches à grands rayons (28 à 32px) sur fond vert d'eau, séparées par une gouttière de 12px.
- Un seul vert plein, réservé au bouton de l'action principale.
- Pilules partout : boutons, champs publics, navigation, onglet actif noir.
- Host Grotesk léger et serré pour les titres, Atkinson Hyperlegible Next pour tout le texte.
- Niveaux ANSM nommés en toutes lettres (CI, ASDEC, PE, APEC), jamais signalés par la seule couleur.
- Feuille d'ordonnance imprimée traitée comme un système à part.

## Colors

Une palette froide de vert d'eau et d'encre, avec un seul vert saturé et quatre couleurs d'alerte cantonnées aux niveaux ANSM.

### Primary
- **Vert pharmacie** (`act`) : le bouton plein de l'action principale, un par écran : Vérifier (carte de l'accueil et page Interactions), Se connecter, Envoyer la demande, Nouvelle ordonnance. Au survol il fonce en **Vert pharmacie profond** (`act-hover`). Le même vert sert aussi, en trait ou en teinte, aux signaux fonctionnels : anneau de focus, coches qui valident une promesse, état « enregistré » et ordonnance émise (`act-tint`), bouton secondaire teinté, lien Connexion sur téléphone.

### Secondary
- **Menthe de pilule** (`mint-pill-end`) : fin du dégradé de la pilule blanc-menthe (`linear-gradient(100deg, #F4F8F6 0%, #CFE7DA 100%)`), qui porte « Demander un accès » dans l'encoche de l'accueil et la barre de la page Interactions, ainsi que « Mes ordonnances » ou « Administration » une fois connecté.

### Tertiary
- **Rouge contre-indication** (`ci`, fond `ci-bg`, bord `ci-line`) : niveau CI, bloquant ; aussi les messages d'erreur de formulaire.
- **Orange déconseillé** (`asdec`, fond `asdec-bg`, bord `asdec-line`) : niveau ASDEC, doublon de DCI, allergie déclarée, compteur d'alertes à justifier.
- **Ocre précaution** (`pe`, fond `pe-bg`) : niveau PE ; le fond sert aussi aux notes d'avertissement.
- **Gris à prendre en compte** (`apec`, fond `apec-bg`) : niveau APEC et ordonnance annulée.

### Neutral
- **Vert d'eau du sol** (`ground`) : fond de l'accueil et des pages de connexion, autour des grandes feuilles.
- **Vert d'eau de l'atelier** (`canvas`) : fond de l'espace prescripteur.
- **Vert d'eau des panneaux** (`mint`) : panneaux intérieurs de l'accueil, champs publics au repos, survol des pilules de navigation.
- **Menthe soutenue** (`mint-2`) : fin des dégradés doux (carte « Pour qui », panneau latéral de connexion) et halo derrière l'ordonnance illustrée.
- **Blanc feuille** (`panel`) : feuilles, cartes, panneau de rédaction, champs en focus.
- **Champ teinté** (`field`) : champs secondaires et blocs de périmètre dans l'espace prescripteur.
- **Encre** (`ink`) : texte principal, pilule noire de l'état actif, bouton noir de clôture, repères numérotés.
- **Encre seconde** (`ink-2`) et **encre tierce** (`ink-3`) : texte courant secondaire, légendes, métadonnées. **Indication** (`placeholder`) : textes indicatifs des champs.
- **Filets** (`rule`, `line`, `line-soft`) : séparateurs de listes sur fond vert d'eau, bords des contrôles et des cartes, séparateurs intérieurs.

### Named Rules
**La règle du vert unique.** Le vert pharmacie plein ne remplit que le bouton de l'action principale. « Demander un accès » n'est jamais vert : il prend la pilule blanc-menthe, ou la pilule noire en clôture de page.

**La règle des niveaux.** Rouge, orange, ocre et gris n'apparaissent que sur une étiquette ou un bloc de niveau ANSM (ou une erreur, pour le rouge). Chaque étiquette porte son sigle en texte.

## Typography

**Display Font:** Host Grotesk (avec Atkinson Hyperlegible Next, puis system-ui)
**Body Font:** Atkinson Hyperlegible Next (avec Atkinson Hyperlegible, puis system-ui)

**Character:** un grotesque fin, légèrement serré, pour des titres posés et sans emphase ; une linéale conçue pour la lisibilité, qui garde le texte médical lisible sur téléphone et en consultation. Les chiffres sont tabulaires dans tout l'espace prescripteur.

### Hierarchy
- **Display** (Host Grotesk 400, clamp 40 à 68px, interligne 1.0) : le titre de l'accueil, dans l'encoche blanche en bas à gauche de la photo. Au-delà, il masque le sujet de la photo.
- **Numeral** (Host Grotesk 300, clamp 76 à 132px, interligne 0.85) : le chiffre de preuve unique (22 705 médicaments).
- **Headline** (Host Grotesk 400, clamp 30 à 44px, interligne 1.08) : titres de section de l'accueil ; variantes plus petites pour la carte « Pour qui » (clamp 28 à 38px), la clôture (clamp 32 à 54px) et le panneau de connexion (clamp 28 à 40px).
- **Title** (Host Grotesk 400, 22px) : titre de la carte Vérifier et du résultat d'interaction. **Title-workspace** (Host Grotesk 500, 26px) : titres de page de l'espace prescripteur ; 32px sur les formulaires de connexion.
- **Body-public** (Atkinson 400, 17px, interligne 1.55) : tout le texte de l'accueil ; paragraphes limités à 52 à 62ch.
- **Body** (Atkinson 400, 15px, interligne 1.45) : texte de l'espace prescripteur ; 14px dans les blocs denses, 70 à 75ch au plus.
- **Label** (Atkinson 600, 13px ; 14px sur l'accueil) : étiquettes de champ, au-dessus du champ, en casse normale.
- **Level** (Atkinson 700, 12px, espacement 0.02em) : sigles CI, ASDEC, PE, APEC ; 13px sur l'accueil.

### Named Rules
**La règle des titres posés.** Les titres Host Grotesk restent en graisse 400 (500 dans l'espace prescripteur, 600 pour la marque) avec un approche négatif ; pas de gras ni de capitales pour faire crier un titre.

## Layout

L'accueil est une seule grande feuille blanche (`max-width: 1320px`, marge intérieure 12px, rayon 32px) posée sur le sol vert d'eau. À l'intérieur, chaque bloc est une feuille ou un panneau séparé du suivant par une gouttière de 12px. Le premier écran est une photo pleine largeur (clamp 580 à 700px de haut, rayon 28px) dans laquelle s'insèrent : la navigation en pilule blanche en haut à gauche, une encoche blanche en haut à droite (Connexion et Demander un accès), une encoche blanche en bas à gauche pour le titre, une carte Vérifier flottante de 380px en bas à droite. Les encoches ont des coins inversés qui prolongent la feuille dans la photo.

Les sections suivent des grilles asymétriques en fractions (5/7, 6/5, 7/5), jamais une rangée de cartes égales : sécurité (chiffre et titre à gauche, liste de niveaux à droite), ordonnance illustrée (feuille inclinée à gauche, légende numérotée à droite), « Pour qui » (photo et carte en dégradé), confidentialité (texte en panneau et photo), clôture avec pastille « Haut de page ».

Les pages de connexion, d'inscription, de double authentification et d'erreur partagent une coquille : une feuille blanche (1040px, ou 1180px en version large) à deux colonnes, panneau latéral en dégradé menthe avec pilule de marque, photo et promesses cochées, formulaire de 420px (640px en large) à droite.

L'espace prescripteur est un bureau : panneau de rédaction blanc (contenu de 860px au plus, marge 24px 32px) et table de lecture vert d'eau à droite (520px) qui porte l'aperçu réduit de la feuille. Barre supérieure de 56px alignée sur le contenu (1120px). Grille de champs à 6 colonnes, espacement 16px 18px.

Points de rupture observés : 1180px (bureau sur une colonne), 980px (accueil sur une colonne, encoches à plat, carte Vérifier dans le flux), 860px (coquille de connexion sur une colonne, photo masquée), 720px et 640px (espace prescripteur sur téléphone : navigation sur une seconde ligne défilante, tableaux en cartes), 480px (photo de l'accueil réduite à 240px pour que Vérifier tienne dans le premier écran). Contrôles à 36px, 44px sur écran tactile.

## Elevation & Depth

Le système est plat par tonalité : la profondeur vient du blanc posé sur le vert d'eau, pas des ombres. Les ombres sont rares, douces, teintées du vert sombre `rgba(14, 33, 26, …)`, et réservées à ce qui flotte au-dessus de la photo ou de la page.

### Shadow Vocabulary
- **Carte flottante** (`box-shadow: 0 18px 40px -12px rgba(14, 33, 26, .30), 0 2px 6px rgba(14, 33, 26, .06)`) : la carte Vérifier posée sur la photo. Retirée sur téléphone, où la carte prend un bord.
- **Pilule posée** (`box-shadow: 0 6px 20px rgba(14, 33, 26, .10)`) : navigation en pilule sur la photo ; `.08` sur la pilule de la coquille de connexion.
- **Liste de suggestions** (`box-shadow: 0 14px 30px -10px rgba(14, 33, 26, .28)`) : suggestions sous les champs publics.
- **Feuille illustrée** (`box-shadow: 0 30px 60px -24px rgba(14, 33, 26, .35), 0 2px 6px rgba(14, 33, 26, .08)`) : l'ordonnance d'exemple inclinée de l'accueil.
- **Panneau** (`--panel-shadow`) et **feuille d'aperçu** (`--sheet-shadow`) : la poignée du bureau et la feuille dans la table de lecture.
- **Dialogue** (`box-shadow: 0 24px 64px rgba(0, 0, 0, .22)`).

### Named Rules
**La règle du plat par défaut.** Une feuille ou un panneau au repos n'a pas d'ombre. Seul ce qui flotte (carte sur photo, pilule sur photo, suggestions, dialogue) en reçoit une.

## Shapes

Une géométrie de feuilles arrondies, du plus grand au plus petit : grande feuille 32px (`sheet-l`), photos et panneaux de l'accueil 28px (`photo`), cartes flottantes 22px (`card`), panneaux et cartes de l'espace prescripteur 18px (`panel`), contrôles 10px (`ctl`), numéros d'étape 6px (`step`), étiquettes de niveau 5px (`level`). Tout ce qui se clique ou se choisit dans une barre est une pilule (999px) : boutons, champs publics, navigation, filtres, statuts. Les cercles portent les repères numérotés, les flèches rondes et la pastille « Haut de page ». Les encoches de l'accueil utilisent des coins inversés en dégradé radial. Les bords sont des filets d'un pixel ; la feuille d'ordonnance seule garde des rayons quasi nuls (1mm).

## Components

### Buttons
Des pilules nettes, sans relief, qui se distinguent par la couleur de remplissage et non par la taille.
- **Shape:** pilule (999px), hauteur 36px dans l'espace prescripteur (44px au toucher, 30px en petit), 46px sur l'accueil et les formulaires de connexion.
- **Primary:** vert pharmacie plein, texte blanc, Atkinson 600 à 14px (700 à 16px pour Vérifier sur l'accueil, avec flèche). Un seul par écran.
- **Hover / Focus:** le vert fonce en vert profond ; Vérifier descend de 1px à l'appui ; anneau de focus vert de 2px décalé de 2px.
- **Pilule blanc-menthe:** dégradé blanc vers menthe, texte encre 700 à 15px, filet intérieur à 6 %. Au survol, le filet passe à 16 % et une ombre douce apparaît. Porte « Demander un accès ».
- **Pilule noire:** encre pleine, texte blanc, avec une flèche ronde blanche intégrée à droite ; action de clôture de l'accueil.
- **Default / Soft / Ghost:** blanc avec filet (le filet fonce au survol) ; teinte verte à 8 % et texte vert pour une action secondaire positive ; transparent en encre seconde pour Copier le lien, Accueil, J'ai déjà un compte. Le bouton indisponible passe en gris `#E3E7E4`.
- **Lien discret:** pilule sans fond en encre seconde, fond menthe au survol ; Connexion.

### Chips
- **Statuts d'ordonnance:** pilules de 22px : brouillon (champ teinté avec filet), émise (teinte verte, texte vert), annulée (gris APEC, barré).
- **Filtres:** pilule blanche à filet avec bouton de retrait.

### Cards / Containers
- **Corner Style:** 28px pour les panneaux et photos de l'accueil, 22px pour la carte Vérifier et la photo de connexion, 18px pour les cartes et sections de l'espace prescripteur.
- **Background:** blanc sur vert d'eau, ou vert d'eau (`mint`) dans la grande feuille blanche ; dégradé `#F6FAF8` vers `mint-2` pour la carte « Pour qui » et le panneau de connexion.
- **Shadow Strategy:** aucune au repos (voir Elevation & Depth).
- **Border:** filet `line` d'un pixel dans l'espace prescripteur ; aucun sur l'accueil.
- **Internal Padding:** 40px sur l'accueil (26px 20px sur téléphone), 20px pour la carte Vérifier, 22px pour les cartes de l'espace prescripteur.

### Inputs / Fields
- **Style:** sur l'accueil, pilule de 46px en vert d'eau avec filet ; dans l'espace prescripteur, champ blanc de 40px au rayon de 10px ; sur les formulaires de connexion, 46px en vert d'eau au rayon de 10px. Étiquette au-dessus en 600.
- **Focus:** le fond passe au blanc, le bord au vert pharmacie, halo vert de 3px à 16 %.
- **Error:** message en rouge CI sous le champ ; bloc d'erreur en fond `ci-bg`.
- **Suggestions:** liste blanche au rayon de 16px, lignes au rayon de 10px, survol et sélection en vert d'eau, type (Classe, Substance, Spécialité) en petit à droite.

### Navigation
- **Accueil:** pilule blanche posée sur la photo, marque en Host Grotesk 600, liens en Atkinson 600 à 15px, survol vert d'eau, page courante en pilule noire. Sur téléphone, seule la marque reste.
- **Espace prescripteur:** barre de 56px, onglets dans une pilule vert d'eau, survol blanc, onglet actif en pilule noire. Sur téléphone, les onglets passent sur une seconde ligne défilante dont le bord droit s'estompe.

### Étiquettes de niveau ANSM
Rectangles de 22px (26px sur l'accueil), sigle en 700, couleur et fond du niveau. Dans les résultats d'interaction, chaque interaction est un bloc repliable au rayon de 10px dont l'en-tête prend le fond du niveau et le bord `ci-line` ou `asdec-line`.

### Carte Vérifier
Le composant signature : une carte blanche de 380px, deux champs en pilule avec suggestions, une mention « Une aide à la décision. Elle ne remplace pas votre jugement. » et le bouton Vérifier vert, séparés par un filet. Elle flotte sur la photo sur ordinateur et passe dans le flux, avec un bord, sur téléphone. Le résultat s'affiche sur la page Interactions.

### Feuille d'ordonnance (système d'impression)
Système autonome dans `sheet.css`, partagé par l'impression et l'aperçu, avec le même balisage : A5 (148 × 210mm, 9.5pt) ou A4 (210 × 297mm, 11pt), marges de 11 à 16mm, Atkinson Hyperlegible Next avec repli Arial, encre `rx-ink` sur blanc. En-tête prescripteur et établissement sous un filet de 0.35mm, bloc patient sur fond `rx-soft`, lignes numérotées séparées de pointillés `rx-rule`, étiquettes de bloc en petites capitales espacées (`rx-muted`), cadre de cachet et signature en pointillés, pied de page répété à chaque page imprimée, filigrane incliné (rouge pour une ordonnance annulée). L'aperçu réduit la feuille sans jamais la recomposer. Ce système ne reçoit ni pilules, ni vert d'eau, ni Host Grotesk.

## Do's and Don'ts

### Do:
- **Do** poser chaque nouvelle surface comme une feuille blanche à grands rayons (28 à 32px) sur `ground` ou `canvas`, avec une gouttière de 12px entre les feuilles.
- **Do** réserver le vert pharmacie plein (`act`) au bouton de l'action principale, un par écran.
- **Do** donner à « Demander un accès » la pilule blanc-menthe (ou la pilule noire en clôture).
- **Do** marquer l'état actif d'une navigation en pilule noire (`ink`, texte blanc).
- **Do** écrire le sigle ANSM en texte dans chaque étiquette de niveau.
- **Do** accompagner toute analyse d'interaction de la mention d'aide à la décision.
- **Do** tester chaque premier écran sur téléphone : l'action principale doit y tenir.
- **Do** utiliser des icônes SVG au trait (2 à 2.4px, bouts arrondis), coloré en `currentColor` ou en vert pour une coche.

### Don't:
- **Don't** remplir de vert un bouton secondaire, une inscription, un fond ou un décor.
- **Don't** utiliser le rouge, l'orange ou l'ocre ANSM hors d'une alerte de niveau ou d'une erreur.
- **Don't** aligner une rangée de cartes égales sous un titre et un bouton.
- **Don't** répéter une photo sur le site, ni montrer de capture d'interface, de logo de partenaire, de prix ou de témoignage.
- **Don't** porter le titre de l'accueil au-delà de 68px : il masque le sujet de la photo.
- **Don't** ajouter une ombre à une feuille ou un panneau au repos.
- **Don't** appliquer le langage écran (pilules, vert d'eau, Host Grotesk) à la feuille d'ordonnance imprimée.
