#!/bin/bash
# Start the app on the demo database (see scripts/demo_up.sh). http://127.0.0.1:5001
cd "$(dirname "$0")/.."
export MYSQL_URL="mysql://root:demo@127.0.0.1:33100/projet_ipa"
export FLASK_ENV=development
exec .venv/bin/flask --app application run --port 5001
