# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Prescripteurs** : médecins, chirurgiens-dentistes, sages-femmes et infirmiers d'Afrique francophone, d'abord au Bénin. Ils rédigent des ordonnances en consultation, souvent entre deux patients, sur ordinateur ou téléphone, parfois avec une connexion instable. Leur compte est ouvert après une demande accompagnée d'une pièce justificative, examinée par un administrateur.
- **Pharmaciens** : ne rédigent jamais d'ordonnance au Bénin. Leurs demandes rejoignent une liste d'attente pour une offre officine prévue plus tard.
- **Visiteurs publics** : toute personne qui vérifie l'interaction entre deux médicaments, sans compte.

## Product Purpose

DigiRemed aide un prescripteur à rédiger une ordonnance sûre : chaque médicament ajouté est confronté aux autres selon le thésaurus des interactions médicamenteuses de l'ANSM, pendant la saisie. L'ordonnance émise est numérotée, figée et retrouvable. Le volet public reste la recherche d'interaction entre deux médicaments. Réussir, c'est une ordonnance lisible, juste et tracée, rédigée en moins de temps qu'à la main.

## Positioning

L'analyse des interactions se fait pendant la rédaction, pas après : une contre-indication bloque l'émission, une association déconseillée exige un motif écrit conservé avec l'ordonnance. Le produit est conçu pour le Bénin (formats A5/A4, établissements, numéro d'ordre facultatif, heure locale) et non adapté après coup d'un outil français.

## Operating Context

- Consultation au cabinet, à la clinique ou à la maternité ; impression A5 ou A4, ou export PDF avec signature et cachet importés.
- Catalogue de médicaments importé d'un fichier de spécialités et substances (22 705 lignes en production au 12 novembre 2026) ; thésaurus ANSM pour les interactions.
- Brouillon gardé chiffré sur l'appareil pendant une coupure réseau.

## Capabilities and Constraints

- Ordonnance en trois étapes (patient, traitement, vérification), aperçu identique à l'impression, numérotation par code prescripteur.
- Niveaux ANSM : CI bloquante, ASDEC avec motif écrit, PE et APEC informatifs ; doublon de DCI et allergie déclarée signalés.
- Données de santé chiffrées au repos ; chaque prescripteur ne voit que ses patients ; double authentification optionnelle au pilote.
- Résumés et phrases en langage courant écrits par une IA (Groq), toujours présentés comme indicatifs, sans donnée patient envoyée.
- Hors périmètre actuel : grossesse et allaitement, fonction rénale et hépatique, doses, plantes et compléments, allergies à une classe, lignes en saisie libre (prévu en V2).
- Offre commerciale : rien à annoncer pour l'instant (ni prix, ni gratuité).
- Modèle de financement prévu pour une version ultérieure (V1.1, V1.2 ou V2, non fixée) : des crédits de vérification d'interaction offerts à l'inscription, rachetables une fois épuisés ; quelques essais gratuits pour un visiteur sans compte, puis invitation à s'inscrire. Nombre de crédits et prix non fixés. Rien de cela n'apparaît sur la page d'accueil tant que ce n'est pas construit.

## Brand Commitments

- Nom : DigiRemed. « Projet IAM » est un nom interne à ne plus afficher.
- Interface simple et sobre, exigée par le milieu médical ; français comme langue de l'interface.
- Une aide à la décision, qui ne remplace pas le jugement du prescripteur : cette mention accompagne toute analyse.

## Evidence on Hand

- Faits vérifiables : thésaurus des interactions de l'ANSM ; 22 705 médicaments au catalogue ; ordonnances numérotées et figées.
- Partenaires officiels : annoncés par le porteur du projet, noms et logos pas encore fournis. Ne rien afficher en leur nom avant de les avoir reçus.
- Aucun témoignage, aucun établissement pilote citable, aucun chiffre d'usage : ne pas en inventer.
- Photos : libres de droits (Pexels, Unsplash) en attendant des photos réelles du porteur du projet.

## Product Principles

1. La sécurité du patient d'abord : une contre-indication n'est jamais atténuée, ni dans l'interface ni dans un texte d'IA.
2. Dire ce que l'analyse ne vérifie pas, aussi clairement que ce qu'elle vérifie.
3. Le prescripteur garde la main : l'outil explique, il ne décide pas à sa place.
4. Fonctionner dans les conditions réelles : connexion instable, téléphone, papier A5.

## Accessibility & Inclusion

Lecture rapide en consultation : contrastes AA au minimum, texte lisible sur téléphone, niveaux ANSM distingués par le texte et pas seulement par la couleur.
