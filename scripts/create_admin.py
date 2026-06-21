#!/usr/bin/env python3
"""Create or update the first IAM administrator account from environment variables."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import create_app
from app.services.auth import AuthService
from scripts.import_medication_catalog import load_env


def main() -> int:
    load_env(ROOT / ".env")
    app = create_app()
    with app.app_context():
        success, message = AuthService.create_admin(
            os.environ.get("ADMIN_EMAIL", ""),
            os.environ.get("ADMIN_PASSWORD", ""),
            os.environ.get("ADMIN_FIRST_NAME", ""),
            os.environ.get("ADMIN_LAST_NAME", ""),
        )
    print(message)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
