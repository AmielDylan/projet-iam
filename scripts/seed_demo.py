"""Create two demo prescribers, their establishments and sample patients (demo database only).

Run through scripts/demo_up.sh, which points MYSQL_URL at the throwaway demo database.
Refuses to run against any other database.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from werkzeug.security import generate_password_hash  # noqa: E402

from app.config import DevelopmentConfig  # noqa: E402
from app.services import vault as vault_module  # noqa: E402
from app.services.auth import EstablishmentService  # noqa: E402
from app.services.database import DatabasePool  # noqa: E402
from app.services.patient import PatientService  # noqa: E402
from app.services.prescriber_code import PrescriberCodes  # noqa: E402

ACCOUNTS = [
    {"email": "awa.mensah@demo.local", "password": "Demo-Cotonou-2026", "first_name": "Awa", "last_name": "Mensah",
     "profession": "Médecin", "order_number": "BJ-2147", "phone": "+229 01 97 00 00 01",
     "establishment": {"name": "Cabinet médical Les Cocotiers", "type": "Médecine générale",
                       "address": "Lot 214, Haie Vive, Cotonou", "phone": "+229 01 97 00 00 00", "paper_format": "A5"},
     "patients": [
         {"title": "Mme", "first_name": "Afiavi", "last_name": "Sossou", "birthdate": "12/03/1958", "sex": "F",
          "weight_kg": "61", "weighed_on": "01/11/2026", "pregnancy": "none", "allergies": ["AMOXICILLINE"]},
         {"first_name": "Kossi", "last_name": "Houngbo", "birthdate": "04/06/2021", "sex": "M",
          "weight_kg": "17,5", "weighed_on": "15/07/2026"},
     ]},
    {"email": "kossi.agbo@demo.local", "password": "Demo-PortoNovo-2026", "first_name": "Kossi", "last_name": "Agbo",
     "profession": "Sage-femme", "order_number": "BJ-3310", "phone": "+229 01 96 00 00 02",
     "establishment": {"name": "Clinique Saint-Luc", "type": "Maternité", "address": "Quartier Ouando, Porto-Novo",
                       "phone": "+229 01 96 00 00 00", "paper_format": "A4"},
     "patients": [
         {"title": "Mme", "first_name": "Rosine", "last_name": "Dossou", "birthdate": "20/09/1994", "sex": "F",
          "weight_kg": "68", "weighed_on": "05/11/2026", "pregnancy": "pregnant"},
     ]},
]


ADMIN = {"email": "admin@demo.local", "password": "Demo-Admin-2026"}
PENDING = [
    # (email, first name, last name, profession, role, status)
    ("efua.adjovi@demo.local", "Efua", "Adjovi", "Médecin", "prescriber", "pending"),
    ("rachidi.bello@demo.local", "Rachidi", "Bello", "Pharmacien", "pharmacist", "waitlist"),
]


def seed_admin_side() -> None:
    """An administrator, one account request to review, one pharmacist on the waitlist."""
    with DatabasePool.get_cursor() as cursor:
        cursor.execute("SELECT id FROM iam_users WHERE email = %s", (ADMIN["email"],))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO iam_users (email, password_hash, role, status, first_name, last_name, must_change_password) "
                "VALUES (%s, %s, 'admin', 'approved', 'Admin', 'DigiRemed', 0)",
                (ADMIN["email"], generate_password_hash(ADMIN["password"])),
            )
            print(f"Créé : {ADMIN['email']}")
        for email, first, last, profession, role, status in PENDING:
            cursor.execute("SELECT id FROM iam_users WHERE email = %s", (email,))
            if cursor.fetchone():
                continue
            cursor.execute(
                "INSERT INTO iam_users (email, password_hash, role, status, first_name, last_name, birthdate, profession, "
                "order_number, phone, must_change_password) VALUES (%s, '', %s, %s, %s, %s, '1988-02-14', %s, 'BJ-9001', "
                "'+229 01 90 00 00 00', 0)",
                (email, role, status, first, last, profession),
            )
            if status == "pending":
                pdf = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj " \
                      b"3 0 obj<</Type/Page/MediaBox[0 0 300 200]/Parent 2 0 R>>endobj\ntrailer<</Root 1 0 R>>"
                import base64
                cursor.execute(
                    "INSERT INTO identity_documents (user_id, filename, mime_type, size_bytes, content) VALUES (%s, 'piece.pdf', "
                    "'application/pdf', %s, %s)",
                    (cursor.lastrowid, len(pdf), base64.b64encode(pdf).decode()),
                )
            print(f"Créé : {email} ({status})")


def main() -> int:
    url = os.environ.get("MYSQL_URL", "")
    if ":33100/" not in url:
        print("Refus : ce script ne s'exécute que sur la base de démonstration (port 33100).", file=sys.stderr)
        return 1
    config = DevelopmentConfig()
    vault_module.install(vault_module.Vault(config.DATA_ENCRYPTION_KEYS, config.DATA_INDEX_KEY))
    DatabasePool.initialize(host=config.DB_HOST, port=config.DB_PORT, user=config.DB_USER,
                            password=config.DB_PASSWORD, database=config.DB_NAME, pool_size=2, pool_name="seed")
    seed_admin_side()
    for account in ACCOUNTS:
        rows = DatabasePool.execute_query("SELECT id FROM iam_users WHERE email = %s", (account["email"],))
        if rows:
            print(f"Déjà présent : {account['email']}")
            continue
        with DatabasePool.get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO iam_users (email, password_hash, role, status, first_name, last_name, birthdate,
                                       profession, order_number, phone, must_change_password)
                VALUES (%s, %s, 'prescriber', 'approved', %s, %s, '1980-01-01', %s, %s, %s, 0)
                """,
                (account["email"], generate_password_hash(account["password"]), account["first_name"],
                 account["last_name"], account["profession"], account["order_number"], account["phone"]),
            )
            user_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO prescriber_profiles (user_id, title, first_name, last_name, profession, phone, email) "
                "VALUES (%s, 'Dr', %s, %s, %s, %s, %s)",
                (user_id, account["first_name"], account["last_name"], account["profession"], account["phone"], account["email"]),
            )
        PrescriberCodes.ensure(user_id)
        EstablishmentService.upsert(user_id, account["establishment"])
        for patient in account["patients"]:
            PatientService.create(user_id, patient)
        print(f"Créé : {account['email']} (code {PrescriberCodes.of(user_id)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
