#!/bin/bash
# Export database for Railway deployment
# Usage: ./scripts/export_database.sh

OUTPUT_FILE="database_export.sql"

echo "Exporting projet_ipa database..."

/usr/local/mysql/bin/mysqldump -u root -p \
    --databases projet_ipa \
    --add-drop-database \
    --add-drop-table \
    --routines \
    --triggers \
    --single-transaction \
    > "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    echo "Database exported successfully to $OUTPUT_FILE"
    echo "File size: $(du -h $OUTPUT_FILE | cut -f1)"
else
    echo "Export failed!"
    exit 1
fi
