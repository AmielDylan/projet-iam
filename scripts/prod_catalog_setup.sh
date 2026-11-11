#!/bin/bash
# One-time production setup after the Ordonnance V4 deploy (run it yourself, from the repo root):
#   1. migration 006 (medication catalog tables, additive),
#   2. catalog import from the Excel file (new rows in medication_catalog only),
#   3. record the thesaurus version (frozen in issued ordonnances).
# Needs: `railway link` to projet-iam / production, the mysql client, and the app deployed (for step 3).
#
#   scripts/prod_catalog_setup.sh [path/to/catalog.xlsx]
set -euo pipefail
cd "$(dirname "$0")/.."
CATALOG="${1:-$HOME/Downloads/Lien_SPECIALITES-SUBSTANCES_CLEANED_11-06-2026.xlsx}"
MYSQL=/opt/homebrew/opt/mysql-client/bin/mysql

URL=$(railway variables -s MySQL --json | python3 -c "import sys, json; print(json.load(sys.stdin)['MYSQL_PUBLIC_URL'])")
export MYSQL_URL="$URL"
eval "$(python3 - "$URL" <<'PY'
import shlex, sys
from urllib.parse import urlparse
u = urlparse(sys.argv[1])
print(f"H={shlex.quote(u.hostname)} P={u.port} U={shlex.quote(u.username)} D={shlex.quote(u.path.lstrip('/'))}")
print(f"export MYSQL_PWD={shlex.quote(u.password)}")
PY
)"

echo "1/3 Migration 006 (catalogue)…"
"$MYSQL" -h "$H" -P "$P" -u "$U" "$D" < migrations/006_medication_catalog.sql

echo "2/3 Import du catalogue ($CATALOG), quelques minutes…"
if [ "$("$MYSQL" -h "$H" -P "$P" -u "$U" "$D" -N -e "SELECT COUNT(*) FROM medication_catalog")" = "0" ]; then
  .venv/bin/python scripts/import_medication_catalog.py --file "$CATALOG" --apply-catalog
else
  echo "   catalogue déjà présent, import ignoré"
fi

echo "3/3 Version du thésaurus…"
if [ "$("$MYSQL" -h "$H" -P "$P" -u "$U" "$D" -N -e "SELECT COUNT(*) FROM referential_versions WHERE kind = 'thesaurus'")" = "0" ]; then
  FLASK_ENV=development .venv/bin/python scripts/record_referential.py thesaurus "Thésaurus ANSM (base de production)"
fi
echo "Terminé."
