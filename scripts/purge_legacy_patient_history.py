"""Delete the clear-text patient_history rows already copied into `patients`.

patient_history (before Ordonnance V4) stores names and birthdates in clear.
Its rows are copied, sealed, into `patients` at every start. Once the copy is
verified in production, run this to remove the clear-text originals:

    python scripts/purge_legacy_patient_history.py            # dry run: counts only
    python scripts/purge_legacy_patient_history.py --apply

Only rows whose copy exists (patients.legacy_history_id) are deleted.
On Railway, prefix with `railway run`.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

from app.config import get_config  # noqa: E402
from app.services.database import DatabasePool  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="Delete for real")
    args = parser.parse_args()

    load_dotenv()
    config = get_config()
    DatabasePool.initialize(host=config.DB_HOST, port=config.DB_PORT, user=config.DB_USER,
                            password=config.DB_PASSWORD, database=config.DB_NAME, pool_size=1,
                            pool_name="purge_cli")
    copied = DatabasePool.execute_query(
        "SELECT COUNT(*) FROM patient_history h JOIN patients p ON p.legacy_history_id = h.id")[0][0]
    remaining = DatabasePool.execute_query(
        "SELECT COUNT(*) FROM patient_history h LEFT JOIN patients p ON p.legacy_history_id = h.id "
        "WHERE p.id IS NULL")[0][0]
    print(f"Lignes copiées, supprimables : {copied}. Lignes pas encore copiées, conservées : {remaining}.")
    if not args.apply:
        print("Simulation. Ajoutez --apply pour supprimer.")
        return 0
    with DatabasePool.get_cursor() as cursor:
        cursor.execute("DELETE h FROM patient_history h JOIN patients p ON p.legacy_history_id = h.id")
        print(f"Supprimées : {cursor.rowcount}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
