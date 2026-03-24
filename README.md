# Projet IAM — Interactions A Médicaments

Plateforme web de visualisation des interactions médicamenteuses, basée sur la base de données de l'ANSM.

**Production** : [projet-iam-web-production.up.railway.app](https://projet-iam-web-production.up.railway.app)

---

## Présentation

L'utilisateur saisit deux médicaments (spécialité, substance active ou classe pharmacologique). L'application interroge la base de données et affiche les interactions potentielles classées par niveau de criticité selon la classification ANSM :

| Sigle | Libellé | Couleur |
|-------|---------|---------|
| **CI** | Contre-indication | Rouge |
| **ASDEC** | Association déconseillée | Orange |
| **PE** | Précaution d'emploi | Jaune |
| **APEC** | À prendre en compte | Gris |

---

## Démarrage rapide

```bash
# 1. Cloner et installer
git clone https://github.com/AmielDylan/projet-iam.git
cd projet-iam
pip install -r requirements.txt

# 2. Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos identifiants MySQL

# 3. Lancer
python application.py
# ou : flask run
```

L'application est disponible sur `http://localhost:5000`.

---

## Architecture

```
projet-iam/
├── app/
│   ├── __init__.py          # Factory Flask (create_app)
│   ├── config.py            # Configuration par environnement
│   ├── services/
│   │   ├── database.py      # Pool de connexions MySQL
│   │   ├── interaction.py   # Recherche d'interactions (SQL direct)
│   │   ├── autocomplete.py  # Autocomplétion
│   │   └── summary.py       # Résumé IA via Groq
│   ├── api/
│   │   ├── routes.py        # Endpoints JSON /api/v1/*
│   │   └── validators.py    # Validation des entrées
│   └── web/
│       └── routes.py        # Routes HTML
├── static/
│   ├── css/                 # Design system Paper (variables, composants)
│   └── js/                  # Modules ES (api, form, autocomplete…)
├── templates/
│   ├── base.html            # Layout partagé (navbar, footer)
│   ├── index.html           # Page principale
│   ├── changelog.html       # Historique des versions
│   └── error.html           # Page d'erreur
├── migrations/              # Scripts SQL de migration
├── application.py           # Point d'entrée (compatibilité Railway/Gunicorn)
├── Procfile                 # Commande de démarrage Railway
└── requirements.txt
```

### Flux d'une requête

1. L'utilisateur saisit deux médicaments → autocomplétion via `GET /api/v1/autocomplete`
2. À la soumission, les deux médicaments sont validés en parallèle via `POST /api/v1/validate`
3. Si valides, `POST /api/v1/interactions` déclenche la requête SQL directe dans `interaction.py`
4. Les résultats sont triés par sévérité et rendus dans la carte résultat
5. Un résumé IA est chargé de façon asynchrone depuis `POST /api/v1/summary`

### Base de données

MySQL avec la structure ANSM. Tables principales :
- `classes` — classes pharmacologiques
- `substances` — substances actives
- `specialites` — spécialités (noms commerciaux)
- `interactions_classes` — interactions entre classes, avec niveau et textes
- `niveaux` — table de référence des niveaux (CI, ASDEC, PE, APEC, et combinaisons)
- `liaisons_cs`, `liaisons_ss` — relations substance↔classe et spécialité↔substance

---

## API

### `POST /api/v1/validate`
Valide un médicament et retourne son type.

```json
{ "medication": "ASPIRINE" }
→ { "is_valid": true, "is_substance": true, "classes": ["SALICYLÉS"] }
```

### `POST /api/v1/interactions`
Retourne les interactions entre deux médicaments, triées par criticité.

```json
{ "med1": "ASPIRINE", "med2": "IBUPROFÈNE" }
→ { "count": 1, "interactions": [ { "niveau": "CONTRE-INDICATION", ... } ] }
```

### `GET /api/v1/autocomplete?q=aspi`
Suggestions de médicaments pour l'autocomplétion.

### `POST /api/v1/summary`
Résumé IA de l'interaction (Groq, llama-3.1-8b-instant). Nécessite `GROQ_API_KEY`.

---

## Déploiement (Railway)

Le projet tourne sur [Railway](https://railway.app) avec un service MySQL séparé.

```bash
# Variables d'environnement à configurer dans Railway
SECRET_KEY=<valeur aléatoire>
FLASK_ENV=production
GROQ_API_KEY=<clé Groq>

# Les variables MySQL (MYSQLHOST, MYSQLUSER, etc.) sont
# automatiquement injectées par Railway depuis le service MySQL.
```

Le déploiement est automatique à chaque push sur `main`. Voir les logs dans l'onglet **Deployments** de Railway.

### Migrations

Pour appliquer une migration sur la base Railway :

```bash
railway run mysql -h $MYSQLHOST -u $MYSQLUSER -p$MYSQLPASSWORD $MYSQLDATABASE < migrations/005_optimized_procedures.sql
```

---

## Tests

```bash
pytest
pytest --cov=app   # avec couverture
```

---

## Variables d'environnement

Voir [`.env.example`](.env.example) pour la liste complète.

| Variable | Description |
|----------|-------------|
| `FLASK_ENV` | `development` ou `production` |
| `SECRET_KEY` | Clé secrète Flask |
| `DB_HOST` | Hôte MySQL |
| `DB_PORT` | Port MySQL (défaut : 3306) |
| `DB_USER` | Utilisateur MySQL |
| `DB_PASSWORD` | Mot de passe MySQL |
| `DB_NAME` | Nom de la base |
| `GROQ_API_KEY` | Clé API Groq (optionnel — désactive le résumé IA si absent) |
