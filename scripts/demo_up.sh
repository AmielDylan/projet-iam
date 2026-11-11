#!/bin/bash
# Throwaway demo environment: MySQL in Docker (port 33100), real ANSM thesaurus (database_export.sql
# at the repository root, not versioned) and catalog (Excel file),
# two demo prescribers. Your own database (.env) is never touched.
#
#   scripts/demo_up.sh [path/to/catalog.xlsx]     # prepare (idempotent)
#   scripts/demo_run.sh                            # start the app on http://127.0.0.1:5001
#   docker stop digiremed-demo                     # stop; docker start digiremed-demo to resume
#   docker rm -f digiremed-demo && docker volume rm digiremed-demo-data   # delete everything
set -euo pipefail
cd "$(dirname "$0")/.."

CATALOG="${1:-$HOME/Downloads/Lien_SPECIALITES-SUBSTANCES_CLEANED_11-06-2026.xlsx}"
export MYSQL_URL="mysql://root:demo@127.0.0.1:33100/projet_ipa"
SQL() { docker exec -i digiremed-demo mysql -uroot -pdemo "$@" 2>&1 | grep -v "Using a password" || true; }

if ! docker ps -a --format '{{.Names}}' | grep -q '^digiremed-demo$'; then
  docker run -d --name digiremed-demo -e MYSQL_ROOT_PASSWORD=demo -p 127.0.0.1:33100:3306 \
    -v digiremed-demo-data:/var/lib/mysql mysql:8.0 >/dev/null
fi
docker start digiremed-demo >/dev/null
echo "Attente de MySQL…"
until docker exec digiremed-demo mysql -uroot -pdemo -e "SELECT 1" >/dev/null 2>&1; do sleep 1; done

if [ -z "$(SQL -N -e "SHOW DATABASES LIKE 'projet_ipa'")" ]; then
  echo "Import du thésaurus ANSM (database_export.sql)…"
  SQL < database_export.sql
  for f in 006_medication_catalog 007_auth_prescriber_patients 008_prescriber_requests_establishments; do
    SQL projet_ipa < "migrations/$f.sql"
  done
fi

echo "Migrations 010 et suivantes (démarrage de l'application)…"
.venv/bin/python -c "
from app import create_app
from app.config import DevelopmentConfig
create_app(DevelopmentConfig())
"

if [ "$(SQL -N projet_ipa -e "SELECT COUNT(*) FROM medication_catalog")" = "0" ]; then
  echo "Import du catalogue ($CATALOG)…"
  .venv/bin/python scripts/import_medication_catalog.py --file "$CATALOG" --apply-catalog
fi

if [ "$(SQL -N projet_ipa -e "SELECT COUNT(*) FROM referential_versions WHERE kind = 'thesaurus'")" = "0" ]; then
  .venv/bin/python scripts/record_referential.py thesaurus "Thésaurus ANSM (export du projet)"
fi
echo "Comptes de démonstration…"
.venv/bin/python scripts/seed_demo.py
echo "Prêt. Lancez scripts/demo_run.sh"
