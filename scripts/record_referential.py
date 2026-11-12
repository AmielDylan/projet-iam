"""Record an import of the ANSM thesaurus (or of the catalog) as a referential version.

Issued ordonnances freeze the latest version of each referential, so record a
version every time the thesaurus tables are reloaded:

    python scripts/record_referential.py thesaurus "Thésaurus ANSM septembre 2026" --published 2026-09-01

On Railway, prefix with `railway run`.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


from app.config import get_config  # noqa: E402
from app.services.database import DatabasePool  # noqa: E402
from app.services.referential import KINDS, ReferentialService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("kind", choices=KINDS)
    parser.add_argument("label", help="Human-readable name, e.g. 'Thésaurus ANSM septembre 2026'")
    parser.add_argument("--published", help="Publication date, YYYY-MM-DD")
    args = parser.parse_args()

    config = get_config()
    DatabasePool.initialize(host=config.DB_HOST, port=config.DB_PORT, user=config.DB_USER,
                            password=config.DB_PASSWORD, database=config.DB_NAME, pool_size=1,
                            pool_name="referential_cli")
    ReferentialService.record(args.kind, args.label, args.published)
    print(f"Recorded {args.kind}: {args.label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
