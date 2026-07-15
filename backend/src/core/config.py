"""Environment-driven configuration for database and auth."""

import os

MARIADB_HOST = os.getenv("DATABASE_HOST", "localhost")
MARIADB_PORT = int(os.getenv("MARIADB_PORT", "3306"))
MARIADB_DATABASE = os.getenv("MARIADB_DATABASE", "sfsis")
MARIADB_USER = os.getenv("MARIADB_USER", "root")
MARIADB_PASSWORD = os.getenv("MARIADB_ROOT_PASSWORD", "")

DATABASE_URL = (
    f"mysql+pymysql://{MARIADB_USER}:{MARIADB_PASSWORD}"
    f"@{MARIADB_HOST}:{MARIADB_PORT}/{MARIADB_DATABASE}"
)

JWT_SECRET = os.getenv("JWT_SECRET", "")

# Bootstrap superuser seeded by alembic/versions/0004_seed_default_superuser.py.
# Falls back to the original hardcoded dev defaults if unset.
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin1234#")
ADMIN_TOTP_SECRET = os.getenv("ADMIN_TOTP_SECRET", "")
