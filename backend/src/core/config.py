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
