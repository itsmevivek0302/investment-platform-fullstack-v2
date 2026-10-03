import os
from decimal import Decimal


def _csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./investment.db")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
CORS_ORIGINS = _csv(os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"))
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com").lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@12345")
ADMIN_NAME = os.getenv("ADMIN_NAME", "Admin")
# Max amount allowed in a single deposit / withdrawal / order
MAX_TXN_AMOUNT = Decimal(os.getenv("MAX_TXN_AMOUNT", "10000000"))
