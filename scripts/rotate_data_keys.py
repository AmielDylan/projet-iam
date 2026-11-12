"""Rotate health data keys. See app/services/key_rotation.py for the full procedure.

    python scripts/rotate_data_keys.py reseal    # after putting a new key first in DATA_ENCRYPTION_KEYS
    python scripts/rotate_data_keys.py reindex   # after replacing DATA_INDEX_KEY

On Railway, prefix with `railway run`.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


from app.config import get_config  # noqa: E402
from app.services import vault as vault_module  # noqa: E402
from app.services.database import DatabasePool  # noqa: E402
from app.services.key_rotation import reindex_patients, reseal_all  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("reseal", "reindex"))
    args = parser.parse_args()

    config = get_config()
    vault_module.install(vault_module.Vault(config.DATA_ENCRYPTION_KEYS, config.DATA_INDEX_KEY))
    DatabasePool.initialize(host=config.DB_HOST, port=config.DB_PORT, user=config.DB_USER,
                            password=config.DB_PASSWORD, database=config.DB_NAME, pool_size=1,
                            pool_name="rotation_cli")
    if args.action == "reseal":
        for (table, column), count in reseal_all().items():
            print(f"{table}.{column}: {count} rechiffré(s)")
        print("Relancez : quand tout affiche 0, l'ancienne clé peut être retirée.")
    else:
        print(f"Patients réindexés : {reindex_patients()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
